"""
Duplicate Papers Dialog
Shows detected duplicates and allows merging
"""
import logging
from typing import List, Dict, Optional

from qt_compat import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout,
    QtCore, QtWidgets, Signal, Slot
)
from qt_compat import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout,
    QtCore, QtWidgets, Signal, Slot
)

from core.smart.duplicate_detector import DuplicateDetector
from ui.styles import get_dialog_style

logger = logging.getLogger(__name__)


class DuplicateDetectorWorker(QThread):
    """Background duplicate detection"""
    progress = Signal(str)
    finished = Signal(list)  # duplicate groups
    error = Signal(str)

    def __init__(self, detector: DuplicateDetector, parent=None):
        super().__init__(parent)
        self.detector = detector

    def run(self):
        try:
            self.progress.emit("Scanning for duplicates...")

            duplicates = self.detector.find_duplicates()

            self.finished.emit(duplicates)

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}", exc_info=True)
            self.error.emit(str(e))


class DuplicateDialog(QDialog):
    """Dialog for managing duplicate papers"""

    duplicates_merged = Signal()  # Emitted when duplicates are merged

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.setStyleSheet(get_dialog_style())

        self.workspace = workspace
        self.detector = DuplicateDetector(workspace)
        self.worker: Optional[DuplicateDetectorWorker] = None

        self.duplicate_groups = []
        self.current_group_index = -1
        self.is_scanning = False  # Prevent concurrent scans
        self.is_merging = False  # Prevent concurrent merges

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Duplicate Papers")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Status
        self.status_label = QLabel("Click 'Scan for Duplicates' to start")
        self.status_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Duplicate groups list
        groups_label = QLabel("Duplicate Groups:")
        layout.addWidget(groups_label)

        self.groups_list = QListWidget()
        self.groups_list.itemClicked.connect(self._on_group_selected)
        layout.addWidget(self.groups_list)

        # Details
        details_group = QGroupBox("Group Details")
        details_layout = QVBoxLayout(details_group)

        self.details_browser = QTextBrowser()
        self.details_browser.setMaximumHeight(250)
        details_layout.addWidget(self.details_browser)

        # Merge options
        merge_layout = QHBoxLayout()

        merge_label = QLabel("Select primary document (to keep):")
        merge_layout.addWidget(merge_label)

        self.primary_combo = QListWidget()
        self.primary_combo.setMaximumHeight(100)
        merge_layout.addWidget(self.primary_combo)

        details_layout.addLayout(merge_layout)

        layout.addWidget(details_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.scan_button = QPushButton("Scan for Duplicates")
        self.scan_button.clicked.connect(self._on_scan)
        button_layout.addWidget(self.scan_button)

        self.merge_button = QPushButton("Merge Selected Group")
        self.merge_button.clicked.connect(self._on_merge_group)
        self.merge_button.setEnabled(False)
        button_layout.addWidget(self.merge_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def showEvent(self, event):
        """Auto-scan when dialog is shown"""
        super().showEvent(event)
        # Don't auto-scan, let user trigger it

    def _on_scan(self):
        """Scan for duplicates"""
        # Prevent concurrent scans
        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_button.setEnabled(False)
        self.merge_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Clear previous results
        self.groups_list.clear()
        self.details_browser.clear()
        self.primary_combo.clear()
        self.duplicate_groups = []

        # Start worker
        self.worker = DuplicateDetectorWorker(self.detector, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        logger.info("Started duplicate scan")

    def _on_progress(self, message: str):
        """Update progress"""
        self.status_label.setText(message)

    def _on_scan_finished(self, duplicate_groups: List[Dict]):
        """Handle scan complete"""
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        self.duplicate_groups = duplicate_groups

        if not duplicate_groups:
            self.status_label.setText("✓ No duplicates found")
            QMessageBox.information(
                self,
                "No Duplicates",
                "No duplicate papers found in your library."
            )
            return

        # Display groups
        for i, group in enumerate(duplicate_groups):
            docs = group['docs']
            reason = group['reason']
            confidence = group['confidence']

            item_text = f"Group {i + 1}: {len(docs)} documents - {reason}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.groups_list.addItem(item)

        self.status_label.setText(f"Found {len(duplicate_groups)} duplicate groups")

        logger.info(f"Scan complete: {len(duplicate_groups)} groups found")

    def _on_error(self, error_message: str):
        """Handle error"""
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Scan failed")

        QMessageBox.critical(self, "Error", f"Failed to scan:\n{error_message}")

    def _on_group_selected(self, item: QListWidgetItem):
        """Show group details"""
        group_index = item.data(Qt.UserRole)

        if group_index is None or group_index >= len(self.duplicate_groups):
            return

        self.current_group_index = group_index
        group = self.duplicate_groups[group_index]

        docs = group['docs']
        reason = group['reason']
        confidence = group['confidence']

        # Build HTML
        html = f"<h3>Duplicate Group {group_index + 1}</h3>"
        html += f"<p><b>Reason:</b> {reason}</p>"
        html += f"<p><b>Confidence:</b> {confidence:.2%}</p>"
        html += "<hr>"

        html += "<h4>Documents in this group:</h4>"

        for i, doc in enumerate(docs):
            html += f"<p><b>Document {i + 1}:</b><br>"
            html += f"Title: {doc.get('title') or 'Untitled'}<br>"
            html += f"Authors: {doc.get('authors') or 'Unknown'}<br>"
            html += f"Year: {doc.get('year') or 'N/A'}<br>"
            html += f"DOI: {doc.get('doi') or 'N/A'}<br>"
            html += f"File: {doc.get('file_path')}<br>"
            html += "</p>"

        self.details_browser.setHtml(html)

        # Populate primary combo
        self.primary_combo.clear()
        for i, doc in enumerate(docs):
            title = doc.get('title') or f"Document {doc['doc_id']}"
            item = QListWidgetItem(f"[{i + 1}] {title}")
            item.setData(Qt.UserRole, doc['doc_id'])
            self.primary_combo.addItem(item)

        # Enable merge
        self.merge_button.setEnabled(True)

    def _on_merge_group(self):
        """Merge selected duplicate group"""
        # Prevent concurrent merges
        if self.is_merging or self.is_scanning:
            return

        if self.current_group_index < 0:
            return

        # Get selected primary
        selected_items = self.primary_combo.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a primary document to keep")
            return

        primary_doc_id = selected_items[0].data(Qt.UserRole)

        group = self.duplicate_groups[self.current_group_index]
        docs = group['docs']

        # Get IDs
        all_ids = [doc['doc_id'] for doc in docs]
        ids_to_remove = [doc_id for doc_id in all_ids if doc_id != primary_doc_id]

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Merge",
            f"Merge {len(ids_to_remove)} duplicate(s) into the selected document?\n\n"
            "This will:\n"
            "- Keep the selected document\n"
            "- Move all annotations, tags, highlights to it\n"
            "- Delete the duplicate files\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Set merging state
        self.is_merging = True
        self.merge_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.status_label.setText("⏳ Merging duplicates...")

        # Perform merge
        try:
            success = self.detector.merge_duplicates([primary_doc_id], ids_to_remove)

            if success:
                QMessageBox.information(
                    self,
                    "Merge Complete",
                    f"Successfully merged {len(ids_to_remove)} duplicate(s)"
                )

                # Remove from list
                self.groups_list.takeItem(self.current_group_index)
                self.duplicate_groups.pop(self.current_group_index)
                self.current_group_index = -1

                # Clear details
                self.details_browser.clear()
                self.primary_combo.clear()
                self.merge_button.setEnabled(False)

                # Emit signal
                self.duplicates_merged.emit()

                logger.info(f"Merged duplicate group successfully")
            else:
                QMessageBox.critical(self, "Merge Failed", "Failed to merge duplicates")

        except Exception as e:
            logger.error(f"Merge error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Merge error:\n{e}")

        finally:
            # Always restore merge state
            self.is_merging = False
            self.scan_button.setEnabled(True)
            if len(self.duplicate_groups) > 0:
                self.status_label.setText(f"Found {len(self.duplicate_groups)} duplicate groups")
            else:
                self.status_label.setText("Ready")
