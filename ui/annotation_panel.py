"""
Annotation (메모) 관리 패널
"""
import logging
from typing import Optional, List

from qt_compat import (
    QAction, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget, Qt, QtCore, QtGui, QtWidgets, Signal,
    Slot
)

logger = logging.getLogger(__name__)


class AnnotationPanel(QWidget):
    """메모 관리 패널"""

    # Signals
    annotation_selected = Signal(int)  # annotation_id
    annotation_added = Signal(int, int, str)  # doc_id, page, content
    annotation_updated = Signal(int, str)  # annotation_id, content
    annotation_deleted = Signal(int)  # annotation_id

    def __init__(self):
        super().__init__()

        self.current_doc_id: Optional[int] = None
        self.current_page: Optional[int] = None
        self.annotations: List = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Annotations")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Annotation list
        self.annotation_list = QListWidget()
        self.annotation_list.setToolTip("Your notes and annotations\nClick to view or edit")
        self.annotation_list.itemClicked.connect(self._on_annotation_clicked)
        self.annotation_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.annotation_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.annotation_list)

        # Content editor
        editor_label = QLabel("Note Content:")
        layout.addWidget(editor_label)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Write your note here...")
        self.content_edit.setToolTip("Write or edit your annotation text")
        self.content_edit.setMaximumHeight(150)
        layout.addWidget(self.content_edit)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Note")
        self.add_button.setToolTip("Add a new note to the current page")
        self.add_button.clicked.connect(self._on_add_note)
        self.add_button.setEnabled(False)
        button_layout.addWidget(self.add_button)

        self.update_button = QPushButton("Update")
        self.update_button.setToolTip("Save changes to the selected note")
        self.update_button.clicked.connect(self._on_update_note)
        self.update_button.setEnabled(False)
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Delete the selected note")
        self.delete_button.clicked.connect(self._on_delete_note)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        # Info label
        self.info_label = QLabel("No document loaded")
        self.info_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.info_label)

    def set_document(self, doc_id: int, doc_title: str):
        """Set current document"""
        self.current_doc_id = doc_id
        self.current_page = None
        self.annotations = []
        self.annotation_list.clear()
        self.content_edit.clear()

        self.info_label.setText(f"Document: {doc_title}")
        self.add_button.setEnabled(False)

        logger.debug(f"Set document: {doc_id}")

    def set_page(self, page_number: int):
        """Set current page"""
        self.current_page = page_number
        self.add_button.setEnabled(True)

        self.info_label.setText(
            f"Document ID: {self.current_doc_id} | Page: {page_number + 1}"
        )

        logger.debug(f"Set page: {page_number}")

    def load_annotations(self, annotations: List[dict]):
        """Load annotations for current document/page"""
        self.annotations = annotations
        self.annotation_list.clear()

        for ann in annotations:
            item_text = f"[Page {ann['page_number'] + 1}] {ann['content'][:50]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ann['annotation_id'])
            self.annotation_list.addItem(item)

        logger.debug(f"Loaded {len(annotations)} annotations")

    def _on_annotation_clicked(self, item: QListWidgetItem):
        """Handle annotation selection"""
        annotation_id = item.data(Qt.UserRole)

        # Find annotation data
        annotation = next((a for a in self.annotations if a['annotation_id'] == annotation_id), None)

        if annotation:
            self.content_edit.setText(annotation['content'])
            self.update_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.annotation_selected.emit(annotation_id)

    def _on_add_note(self):
        """Handle add note button"""
        content = self.content_edit.toPlainText().strip()

        if not content:
            QMessageBox.warning(self, "Empty Note", "Please enter note content")
            return

        if self.current_doc_id is None:
            QMessageBox.warning(self, "No Document", "Please select a document first")
            return

        # Use current page or ask user
        page = self.current_page
        if page is None:
            page, ok = QInputDialog.getInt(
                self,
                "Page Number",
                "Enter page number (1-based):",
                1, 1, 1000
            )
            if not ok:
                return
            page = page - 1  # Convert to 0-based

        self.annotation_added.emit(self.current_doc_id, page, content)

        # Clear editor
        self.content_edit.clear()

        logger.info(f"Add note requested: doc={self.current_doc_id}, page={page}")

    def _on_update_note(self):
        """Handle update note button"""
        current_item = self.annotation_list.currentItem()
        if not current_item:
            return

        annotation_id = current_item.data(Qt.UserRole)
        content = self.content_edit.toPlainText().strip()

        if not content:
            QMessageBox.warning(self, "Empty Note", "Note content cannot be empty")
            return

        self.annotation_updated.emit(annotation_id, content)

        logger.info(f"Update note requested: {annotation_id}")

    def _on_delete_note(self):
        """Handle delete note button"""
        current_item = self.annotation_list.currentItem()
        if not current_item:
            return

        annotation_id = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Delete Note",
            "Are you sure you want to delete this note?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.annotation_deleted.emit(annotation_id)

            # Clear selection
            self.content_edit.clear()
            self.update_button.setEnabled(False)
            self.delete_button.setEnabled(False)

            logger.info(f"Delete note requested: {annotation_id}")

    def _show_context_menu(self, position):
        """Show context menu for annotation"""
        item = self.annotation_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self._on_annotation_clicked(item))
        menu.addAction(edit_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._on_delete_note)
        menu.addAction(delete_action)

        menu.exec(self.annotation_list.mapToGlobal(position))

    def clear(self):
        """Clear all data"""
        self.current_doc_id = None
        self.current_page = None
        self.annotations = []
        self.annotation_list.clear()
        self.content_edit.clear()
        self.info_label.setText("No document loaded")
        self.add_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
