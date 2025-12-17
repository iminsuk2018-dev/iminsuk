"""
Reference Manager Dialog
Shows extracted references from PDFs
"""
import logging
from typing import List, Dict, Optional

from qt_compat import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout,
    QtCore, QtGui, QtWidgets, Signal, Slot
)
from qt_compat import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QTextBrowser, QThread, QVBoxLayout,
    QtCore, QtGui, QtWidgets, Signal, Slot
)

from core.smart.reference_extractor import ReferenceExtractor

logger = logging.getLogger(__name__)


class ReferenceExtractorWorker(QThread):
    """Background reference extraction"""
    progress = Signal(str)
    finished = Signal(int)  # number of references found
    error = Signal(str)

    def __init__(self, extractor: ReferenceExtractor, doc_id: int, file_path: str, parent=None):
        super().__init__(parent)
        self.extractor = extractor
        self.doc_id = doc_id
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit("Extracting references from PDF...")

            count = self.extractor.extract_and_save(self.doc_id, self.file_path)

            self.finished.emit(count)

        except Exception as e:
            logger.error(f"Reference extraction failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ReferenceDialog(QDialog):
    """Dialog for managing references"""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)

        self.workspace = workspace
        self.extractor = ReferenceExtractor(workspace)
        self.worker: Optional[ReferenceExtractorWorker] = None

        self.current_doc_id: Optional[int] = None
        self.current_file_path: Optional[str] = None
        self.references: List[Dict] = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Reference Manager")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)

        # Document info
        doc_info_layout = QHBoxLayout()
        doc_info_layout.addWidget(QLabel("Current Document:"))
        self.doc_label = QLabel("No document selected")
        self.doc_label.setStyleSheet("font-weight: bold;")
        doc_info_layout.addWidget(self.doc_label)
        doc_info_layout.addStretch()
        layout.addLayout(doc_info_layout)

        # Status
        self.status_label = QLabel("Select a document to view references")
        self.status_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Main content (split view)
        content_layout = QHBoxLayout()

        # Left: Reference list
        left_group = QGroupBox("References")
        left_layout = QVBoxLayout(left_group)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter references...")
        self.search_box.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_box)
        left_layout.addLayout(search_layout)

        self.reference_list = QListWidget()
        self.reference_list.itemClicked.connect(self._on_reference_selected)
        left_layout.addWidget(self.reference_list)

        content_layout.addWidget(left_group, 2)

        # Right: Reference details
        right_group = QGroupBox("Reference Details")
        right_layout = QVBoxLayout(right_group)

        self.details_browser = QTextBrowser()
        right_layout.addWidget(self.details_browser)

        # Copy button
        copy_layout = QHBoxLayout()
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self._on_copy_reference)
        self.copy_button.setEnabled(False)
        copy_layout.addStretch()
        copy_layout.addWidget(self.copy_button)
        right_layout.addLayout(copy_layout)

        content_layout.addWidget(right_group, 3)

        layout.addLayout(content_layout)

        # Action buttons
        button_layout = QHBoxLayout()

        self.extract_button = QPushButton("Extract References")
        self.extract_button.clicked.connect(self._on_extract)
        self.extract_button.setEnabled(False)
        button_layout.addWidget(self.extract_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._on_refresh)
        self.refresh_button.setEnabled(False)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def set_document(self, doc_id: int, title: str, file_path: str):
        """Set the current document"""
        self.current_doc_id = doc_id
        self.current_file_path = file_path

        self.doc_label.setText(title or f"Document {doc_id}")
        self.extract_button.setEnabled(True)
        self.refresh_button.setEnabled(True)

        # Load existing references
        self._load_references()

    def _load_references(self):
        """Load references from database"""
        if not self.current_doc_id:
            return

        self.references = self.extractor.get_references(self.current_doc_id)

        self._update_reference_list()

        if self.references:
            self.status_label.setText(f"Found {len(self.references)} references")
        else:
            self.status_label.setText("No references found. Click 'Extract References' to scan the PDF.")

    def _update_reference_list(self):
        """Update reference list widget"""
        self.reference_list.clear()
        self.details_browser.clear()
        self.copy_button.setEnabled(False)

        search_text = self.search_box.text().lower()

        for ref in self.references:
            # Filter by search
            if search_text:
                ref_text_lower = ref['reference_text'].lower()
                if search_text not in ref_text_lower:
                    continue

            # Create display text
            display_text = f"[{ref['order_index'] + 1}] "

            if ref.get('authors'):
                authors = ref['authors'][:50]
                if len(ref['authors']) > 50:
                    authors += '...'
                display_text += authors

            if ref.get('year'):
                display_text += f" ({ref['year']})"

            if ref.get('title'):
                title = ref['title'][:80]
                if len(ref.get('title', '')) > 80:
                    title += '...'
                display_text += f" - {title}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, ref['reference_id'])
            self.reference_list.addItem(item)

    def _on_search_changed(self, text: str):
        """Handle search text change"""
        self._update_reference_list()

    def _on_reference_selected(self, item: QListWidgetItem):
        """Show reference details"""
        ref_id = item.data(Qt.UserRole)

        # Find reference
        ref = None
        for r in self.references:
            if r['reference_id'] == ref_id:
                ref = r
                break

        if not ref:
            return

        # Build HTML
        html = f"<h3>Reference [{ref['order_index'] + 1}]</h3>"
        html += "<hr>"

        html += f"<p><b>Full Text:</b><br>{ref['reference_text']}</p>"
        html += "<hr>"

        if ref.get('title'):
            html += f"<p><b>Title:</b> {ref['title']}</p>"

        if ref.get('authors'):
            html += f"<p><b>Authors:</b> {ref['authors']}</p>"

        if ref.get('year'):
            html += f"<p><b>Year:</b> {ref['year']}</p>"

        if ref.get('doi'):
            html += f"<p><b>DOI:</b> {ref['doi']}</p>"

        if ref.get('reference_type'):
            html += f"<p><b>Type:</b> {ref['reference_type']}</p>"

        self.details_browser.setHtml(html)
        self.copy_button.setEnabled(True)

        # Store current reference for copy
        self.current_reference = ref

    def _on_copy_reference(self):
        """Copy current reference to clipboard"""
        if hasattr(self, 'current_reference'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_reference['reference_text'])

            self.status_label.setText("Reference copied to clipboard")

    def _on_extract(self):
        """Extract references from current document"""
        if not self.current_doc_id or not self.current_file_path:
            return

        reply = QMessageBox.question(
            self,
            "Extract References",
            "Extract references from this PDF?\n\n"
            "This will scan the document and attempt to parse the references section.\n"
            "Any existing references will be replaced.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        # Start extraction
        self.extract_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Start worker
        self.worker = ReferenceExtractorWorker(
            self.extractor,
            self.current_doc_id,
            self.current_file_path,
            self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_extract_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        logger.info(f"Started reference extraction for doc {self.current_doc_id}")

    def _on_progress(self, message: str):
        """Update progress"""
        self.status_label.setText(message)

    def _on_extract_finished(self, count: int):
        """Handle extraction complete"""
        self.extract_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if count == 0:
            self.status_label.setText("No references found in PDF")
            QMessageBox.warning(
                self,
                "No References",
                "Could not find a references section in this PDF.\n\n"
                "Make sure the PDF has a References or Bibliography section."
            )
        else:
            self.status_label.setText(f"Extracted {count} references")
            QMessageBox.information(
                self,
                "Extraction Complete",
                f"Successfully extracted {count} references from the PDF."
            )

            # Reload references
            self._load_references()

        logger.info(f"Extraction complete: {count} references")

    def _on_error(self, error_message: str):
        """Handle error"""
        self.extract_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Extraction failed")

        QMessageBox.critical(self, "Error", f"Failed to extract references:\n{error_message}")

    def _on_refresh(self):
        """Refresh references from database"""
        self._load_references()
