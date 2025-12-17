"""
Watched Folders Dialog
Manage folders that are automatically monitored for new PDFs
"""
import logging
from pathlib import Path
from typing import Optional

from qt_compat import (
    QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QTextBrowser,
    QVBoxLayout, Qt, QtCore, QtWidgets
)

logger = logging.getLogger(__name__)


class WatchedFoldersDialog(QDialog):
    """Dialog for managing watched folders"""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)

        self.workspace = workspace
        self.folder_watcher = None
        self.collection_manager = None

        self._init_ui()
        self._load_folders()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Watched Folders")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)

        # Description
        desc_label = QLabel(
            "Automatically monitor folders for new PDF files. "
            "PDFs found in these folders will be added to your library."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Folder list
        list_label = QLabel("Watched Folders:")
        layout.addWidget(list_label)

        self.folder_list = QListWidget()
        self.folder_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.folder_list)

        # Action buttons
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Folder...")
        self.add_button.clicked.connect(self._on_add_folder)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._on_remove_folder)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)

        self.scan_button = QPushButton("Scan Now")
        self.scan_button.clicked.connect(self._on_scan_folder)
        self.scan_button.setEnabled(False)
        button_layout.addWidget(self.scan_button)

        self.scan_all_button = QPushButton("Scan All")
        self.scan_all_button.clicked.connect(self._on_scan_all)
        button_layout.addWidget(self.scan_all_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status area
        status_label = QLabel("Status:")
        layout.addWidget(status_label)

        self.status_text = QTextBrowser()
        self.status_text.setMaximumHeight(120)
        layout.addWidget(self.status_text)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)

        layout.addLayout(close_layout)

    def set_folder_watcher(self, watcher):
        """Set folder watcher instance"""
        self.folder_watcher = watcher
        self._load_folders()

    def set_collection_manager(self, manager):
        """Set collection manager instance"""
        self.collection_manager = manager

    def _load_folders(self):
        """Load watched folders into list"""
        self.folder_list.clear()

        if not self.folder_watcher:
            return

        try:
            folders = self.folder_watcher.get_watched_folders()

            for folder in folders:
                path = folder['folder_path']
                is_active = folder['is_active']
                recursive = folder['recursive']
                last_scan = folder.get('last_scan')  # Use .get() to handle missing column

                # Build display text
                status = "✓" if is_active else "✗"
                recursive_mark = " (recursive)" if recursive else ""

                if last_scan:
                    last_scan_str = last_scan.split('.')[0]  # Remove microseconds
                    display_text = f"{status} {path}{recursive_mark} - Last scan: {last_scan_str}"
                else:
                    display_text = f"{status} {path}{recursive_mark} - Never scanned"

                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, folder['folder_id'])
                self.folder_list.addItem(item)

            logger.info(f"Loaded {len(folders)} watched folders")

        except Exception as e:
            logger.error(f"Failed to load folders: {e}", exc_info=True)
            self.status_text.append(f"<font color='red'>Error loading folders: {e}</font>")

    def _on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.folder_list.selectedItems()) > 0
        self.remove_button.setEnabled(has_selection)
        self.scan_button.setEnabled(has_selection)

    def _on_add_folder(self):
        """Add new watched folder"""
        if not self.folder_watcher:
            QMessageBox.critical(self, "Error", "Folder watcher not initialized")
            return

        # Ask user to select folder
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Watch",
            str(Path.home())
        )

        if not folder_path:
            return

        folder_path = Path(folder_path)

        # Check if already watching
        existing = self.folder_watcher.get_watched_folders()
        for folder in existing:
            if Path(folder['folder_path']) == folder_path:
                QMessageBox.information(
                    self,
                    "Already Watching",
                    f"This folder is already being watched:\n{folder_path}"
                )
                return

        # Ask for options
        from qt_compat import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        options_dialog = QDialog(self)
        options_dialog.setWindowTitle("Folder Options")
        options_layout = QVBoxLayout(options_dialog)

        options_layout.addWidget(QLabel(f"Adding folder:\n{folder_path}"))

        recursive_check = QCheckBox("Include subfolders (recursive)")
        recursive_check.setChecked(True)
        options_layout.addWidget(recursive_check)

        auto_add_check = QCheckBox("Automatically add PDFs (no confirmation)")
        auto_add_check.setChecked(False)
        options_layout.addWidget(auto_add_check)

        from qt_compat import QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(options_dialog.accept)
        button_box.rejected.connect(options_dialog.reject)
        options_layout.addWidget(button_box)

        if options_dialog.exec() != QDialog.Accepted:
            return

        # Add folder
        try:
            folder_id = self.folder_watcher.add_watched_folder(
                folder_path,
                collection_id=None,  # No collection for now
                auto_add=auto_add_check.isChecked(),
                recursive=recursive_check.isChecked()
            )

            self.status_text.append(f"<font color='green'>Added watched folder: {folder_path}</font>")
            logger.info(f"Added watched folder: {folder_id} - {folder_path}")

            # Reload list
            self._load_folders()

            # Ask to scan now
            reply = QMessageBox.question(
                self,
                "Scan Now?",
                "Would you like to scan this folder now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self._scan_folder_by_id(folder_id)

        except Exception as e:
            logger.error(f"Failed to add folder: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to add folder:\n{e}")

    def _on_remove_folder(self):
        """Remove selected watched folder"""
        selected_items = self.folder_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        folder_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Remove Folder?",
            "Remove this folder from watched list?\n\n"
            "Existing documents will not be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.folder_watcher.remove_watched_folder(folder_id)
            self.status_text.append(f"<font color='green'>Removed watched folder</font>")
            logger.info(f"Removed watched folder: {folder_id}")

            # Reload list
            self._load_folders()

        except Exception as e:
            logger.error(f"Failed to remove folder: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to remove folder:\n{e}")

    def _on_scan_folder(self):
        """Scan selected folder"""
        selected_items = self.folder_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        folder_id = item.data(Qt.UserRole)

        self._scan_folder_by_id(folder_id)

    def _scan_folder_by_id(self, folder_id: int):
        """Scan specific folder"""
        if not self.folder_watcher:
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.status_text.append(f"<b>Scanning folder...</b>")

            # Create progress callback
            def progress_callback(current, total, message):
                self.status_text.append(f"{message}")
                QtWidgets.QApplication.processEvents()

            # Scan
            stats = self.folder_watcher.scan_folder(
                folder_id,
                progress_callback=progress_callback
            )

            self.progress_bar.setVisible(False)

            # Show results
            result_html = f"""
            <font color='green'><b>Scan Complete</b></font><br>
            - Added: {stats['added']} new PDFs<br>
            - Skipped: {stats['skipped']} duplicates<br>
            - Errors: {stats['errors']}
            """

            self.status_text.append(result_html)

            if stats['errors'] > 0:
                QMessageBox.warning(
                    self,
                    "Scan Complete with Errors",
                    f"Added {stats['added']} PDFs\n"
                    f"Skipped {stats['skipped']} duplicates\n"
                    f"Errors: {stats['errors']}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Scan Complete",
                    f"Added {stats['added']} new PDFs\n"
                    f"Skipped {stats['skipped']} duplicates"
                )

            # Reload folder list
            self._load_folders()

            logger.info(f"Scanned folder {folder_id}: {stats}")

        except Exception as e:
            self.progress_bar.setVisible(False)
            logger.error(f"Failed to scan folder: {e}", exc_info=True)
            self.status_text.append(f"<font color='red'>Error: {e}</font>")
            QMessageBox.critical(self, "Error", f"Failed to scan folder:\n{e}")

    def _on_scan_all(self):
        """Scan all active folders"""
        if not self.folder_watcher:
            return

        try:
            folders = self.folder_watcher.get_watched_folders()
            active_folders = [f for f in folders if f['is_active']]

            if not active_folders:
                QMessageBox.information(self, "No Active Folders", "No active watched folders to scan")
                return

            reply = QMessageBox.question(
                self,
                "Scan All?",
                f"Scan {len(active_folders)} active folder(s)?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply != QMessageBox.Yes:
                return

            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_text.append(f"<b>Scanning {len(active_folders)} folders...</b>")

            # Progress callback
            def progress_callback(current, total, message):
                self.status_text.append(f"{message}")
                QtWidgets.QApplication.processEvents()

            # Scan all
            stats = self.folder_watcher.scan_all_folders(progress_callback=progress_callback)

            self.progress_bar.setVisible(False)

            # Show results
            result_html = f"""
            <font color='green'><b>All Folders Scanned</b></font><br>
            - Found: {stats['found']} PDFs<br>
            - Added: {stats['added']} new<br>
            - Skipped: {stats['skipped']} duplicates<br>
            - Errors: {stats['errors']}
            """

            self.status_text.append(result_html)

            QMessageBox.information(
                self,
                "Scan Complete",
                f"Scanned {len(active_folders)} folders\n\n"
                f"Added {stats['added']} new PDFs\n"
                f"Skipped {stats['skipped']} duplicates\n"
                f"Errors: {stats['errors']}"
            )

            # Reload folder list
            self._load_folders()

            logger.info(f"Scanned all folders: {stats}")

        except Exception as e:
            self.progress_bar.setVisible(False)
            logger.error(f"Failed to scan all folders: {e}", exc_info=True)
            self.status_text.append(f"<font color='red'>Error: {e}</font>")
            QMessageBox.critical(self, "Error", f"Failed to scan folders:\n{e}")
