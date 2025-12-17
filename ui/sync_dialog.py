"""
Sync Status and Conflict Resolution Dialog
"""
import logging
from typing import Optional

from qt_compat import (
    QComboBox, QDialog, QFont, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout, QtCore, QtGui,
    QtWidgets, Signal, Slot
)
from qt_compat import (
    QComboBox, QDialog, QFont, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout, QtCore, QtGui,
    QtWidgets, Signal, Slot
)

from core.sync_manager import SyncManager, ConflictStrategy

logger = logging.getLogger(__name__)


class SyncWorker(QThread):
    """Background sync conflict detection"""
    progress = Signal(str)
    finished = Signal(dict)  # Sync health info
    error = Signal(str)

    def __init__(self, sync_manager: SyncManager, parent=None):
        super().__init__(parent)
        self.sync_manager = sync_manager

    def run(self):
        try:
            self.progress.emit("Checking sync status...")

            # Detect conflicts
            conflicts = self.sync_manager.detect_conflicts()

            self.progress.emit(f"Found {len(conflicts)} conflicts")

            # Get health info
            health = self.sync_manager.check_sync_health()
            health["conflicts"] = conflicts

            self.finished.emit(health)

        except Exception as e:
            logger.error(f"Sync check failed: {e}", exc_info=True)
            self.error.emit(str(e))


class SyncDialog(QDialog):
    """Sync status and conflict resolution dialog"""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)

        self.workspace = workspace
        self.sync_manager = SyncManager(workspace)
        self.worker: Optional[SyncWorker] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Cloud Sync Status")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        # Sync status group
        status_group = QGroupBox("Sync Status")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("Checking sync status...")
        status_layout.addWidget(self.status_label)

        self.cloud_label = QLabel()
        cloud_font = QFont()
        cloud_font.setBold(True)
        self.cloud_label.setFont(cloud_font)
        status_layout.addWidget(self.cloud_label)

        self.last_sync_label = QLabel()
        status_layout.addWidget(self.last_sync_label)

        layout.addWidget(status_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Conflicts group
        conflicts_group = QGroupBox("Conflicts")
        conflicts_layout = QVBoxLayout(conflicts_group)

        self.conflicts_label = QLabel("No conflicts detected")
        conflicts_layout.addWidget(self.conflicts_label)

        self.conflicts_browser = QTextBrowser()
        self.conflicts_browser.setMaximumHeight(150)
        conflicts_layout.addWidget(self.conflicts_browser)

        # Conflict resolution strategy
        strategy_layout = QHBoxLayout()

        strategy_label = QLabel("Resolution Strategy:")
        strategy_layout.addWidget(strategy_label)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Keep Local Changes", ConflictStrategy.KEEP_LOCAL)
        self.strategy_combo.addItem("Keep Remote Changes", ConflictStrategy.KEEP_REMOTE)
        self.strategy_combo.addItem("Merge Both", ConflictStrategy.MERGE)
        strategy_layout.addWidget(self.strategy_combo)

        self.resolve_button = QPushButton("Resolve Conflicts")
        self.resolve_button.clicked.connect(self._on_resolve_conflicts)
        self.resolve_button.setEnabled(False)
        strategy_layout.addWidget(self.resolve_button)

        conflicts_layout.addLayout(strategy_layout)

        layout.addWidget(conflicts_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)

        self.backup_button = QPushButton("Create Backup")
        self.backup_button.clicked.connect(self._on_create_backup)
        actions_layout.addWidget(self.backup_button)

        self.integrity_button = QPushButton("Check Integrity")
        self.integrity_button.clicked.connect(self._on_check_integrity)
        actions_layout.addWidget(self.integrity_button)

        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self._on_refresh)
        actions_layout.addWidget(self.refresh_button)

        layout.addWidget(actions_group)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def showEvent(self, event):
        """Auto-refresh when dialog is shown"""
        super().showEvent(event)
        self._on_refresh()

    def _on_refresh(self):
        """Refresh sync status"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Checking...")

        # Disable buttons
        self.refresh_button.setEnabled(False)
        self.resolve_button.setEnabled(False)

        # Start worker
        self.worker = SyncWorker(self.sync_manager, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_sync_checked)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message: str):
        """Update progress"""
        self.status_label.setText(message)

    def _on_sync_checked(self, health: dict):
        """Handle sync check complete"""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

        # Update status
        if health.get("is_cloud_folder"):
            self.cloud_label.setText("✓ Workspace is in cloud sync folder")
            self.cloud_label.setStyleSheet("color: green;")
        else:
            self.cloud_label.setText("⚠ Workspace is NOT in cloud sync folder")
            self.cloud_label.setStyleSheet("color: orange;")

        # Last sync
        last_sync = health.get("last_sync")
        if last_sync:
            self.last_sync_label.setText(f"Last sync: {last_sync}")
        else:
            self.last_sync_label.setText("Last sync: Unknown")

        # Conflicts
        conflicts = health.get("conflicts", [])
        if conflicts:
            self.conflicts_label.setText(f"⚠ {len(conflicts)} conflicts detected")
            self.conflicts_label.setStyleSheet("color: red; font-weight: bold;")

            summary = self.sync_manager.get_conflict_summary()
            self.conflicts_browser.setText(summary)

            self.resolve_button.setEnabled(True)
            self.status_label.setText("Conflicts need resolution")
        else:
            self.conflicts_label.setText("✓ No conflicts")
            self.conflicts_label.setStyleSheet("color: green;")
            self.conflicts_browser.clear()
            self.resolve_button.setEnabled(False)
            self.status_label.setText("Sync status: OK")

        logger.info(f"Sync check complete: {health}")

    def _on_error(self, error_message: str):
        """Handle error"""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

        self.status_label.setText("Error checking sync status")
        QMessageBox.critical(self, "Sync Error", f"Failed to check sync:\n{error_message}")

    def _on_resolve_conflicts(self):
        """Resolve conflicts with selected strategy"""
        strategy_data = self.strategy_combo.currentData()
        strategy = ConflictStrategy(strategy_data)

        # Confirm
        reply = QMessageBox.question(
            self,
            "Resolve Conflicts",
            f"Resolve all conflicts using strategy:\n{strategy.value}\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Create backup first
        try:
            backup_path = self.sync_manager.create_backup()
            logger.info(f"Backup created: {backup_path}")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Backup Failed",
                f"Failed to create backup:\n{e}\n\nContinue anyway?",
            )

        # Resolve
        try:
            resolved = self.sync_manager.resolve_all_conflicts(strategy)

            QMessageBox.information(
                self,
                "Conflicts Resolved",
                f"Resolved {resolved} conflicts using {strategy.value}"
            )

            # Refresh
            self._on_refresh()

        except Exception as e:
            logger.error(f"Failed to resolve conflicts: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Resolution Failed",
                f"Failed to resolve conflicts:\n{e}"
            )

    def _on_create_backup(self):
        """Create database backup"""
        try:
            backup_path = self.sync_manager.create_backup()

            QMessageBox.information(
                self,
                "Backup Created",
                f"Database backup created:\n{backup_path}"
            )

        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Backup Failed",
                f"Failed to create backup:\n{e}"
            )

    def _on_check_integrity(self):
        """Check workspace integrity"""
        try:
            results = self.workspace.validate_integrity()

            # Build message
            message = f"Integrity Check Results:\n\n"
            message += f"Total documents: {results['total_documents']}\n"
            message += f"Total PDF files: {results['total_files']}\n\n"

            if results['missing_files']:
                message += f"⚠ Missing files: {len(results['missing_files'])}\n"
            else:
                message += "✓ All files present\n"

            if results['orphaned_files']:
                message += f"⚠ Orphaned files: {len(results['orphaned_files'])}\n"
            else:
                message += "✓ No orphaned files\n"

            if results['hash_mismatches']:
                message += f"⚠ Hash mismatches: {len(results['hash_mismatches'])}\n"
            else:
                message += "✓ All hashes match\n"

            QMessageBox.information(self, "Integrity Check", message)

        except Exception as e:
            logger.error(f"Integrity check failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Check Failed",
                f"Failed to check integrity:\n{e}"
            )
