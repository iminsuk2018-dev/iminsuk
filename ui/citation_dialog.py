"""
Citation Manager Dialog
Export citations in various formats
"""
import logging
from pathlib import Path
from typing import List, Dict

from qt_compat import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, Qt, QtCore, QtWidgets
)

from core.citation.bibtex_generator import BibTeXGenerator
from core.citation.citation_formatter import CitationFormatter, CitationStyle
from data.dao.document_dao import DocumentDAO

logger = logging.getLogger(__name__)


class CitationDialog(QDialog):
    """Dialog for managing and exporting citations"""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)

        self.workspace = workspace
        self.document_dao = DocumentDAO(workspace.get_database())
        self.bibtex_generator = BibTeXGenerator()
        self.citation_formatter = CitationFormatter()

        self.selected_documents = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Citation Manager")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)

        # Document selection
        doc_group = QGroupBox("Select Documents")
        doc_layout = QVBoxLayout(doc_group)

        self.document_list = QListWidget()
        self.document_list.setSelectionMode(QListWidget.MultiSelection)
        doc_layout.addWidget(self.document_list)

        # Select all/none buttons
        select_layout = QHBoxLayout()

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self._on_select_all)
        select_layout.addWidget(self.select_all_button)

        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self._on_select_none)
        select_layout.addWidget(self.select_none_button)

        select_layout.addStretch()

        doc_layout.addLayout(select_layout)

        layout.addWidget(doc_group)

        # Citation style selection
        style_group = QGroupBox("Citation Style")
        style_layout = QHBoxLayout(style_group)

        style_label = QLabel("Style:")
        style_layout.addWidget(style_label)

        self.style_combo = QComboBox()
        self.style_combo.addItem("BibTeX", "bibtex")
        self.style_combo.addItem("APA (7th ed.)", CitationStyle.APA)
        self.style_combo.addItem("MLA (9th ed.)", CitationStyle.MLA)
        self.style_combo.addItem("Chicago (Author-Date)", CitationStyle.CHICAGO)
        self.style_combo.addItem("IEEE", CitationStyle.IEEE)
        self.style_combo.addItem("Harvard", CitationStyle.HARVARD)
        self.style_combo.addItem("Vancouver", CitationStyle.VANCOUVER)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_layout.addWidget(self.style_combo)

        self.generate_button = QPushButton("Generate Citations")
        self.generate_button.clicked.connect(self._on_generate)
        style_layout.addWidget(self.generate_button)

        style_layout.addStretch()

        layout.addWidget(style_group)

        # Preview
        preview_label = QLabel("Preview:")
        layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFontFamily("Courier New")
        layout.addWidget(self.preview_text)

        # Options
        options_layout = QHBoxLayout()

        self.include_abstract_check = QCheckBox("Include Abstract")
        self.include_abstract_check.setChecked(False)
        options_layout.addWidget(self.include_abstract_check)

        self.alphabetical_check = QCheckBox("Sort Alphabetically")
        self.alphabetical_check.setChecked(True)
        options_layout.addWidget(self.alphabetical_check)

        options_layout.addStretch()

        layout.addLayout(options_layout)

        # Action buttons
        button_layout = QHBoxLayout()

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self._on_copy)
        self.copy_button.setEnabled(False)
        button_layout.addWidget(self.copy_button)

        self.export_button = QPushButton("Export to File...")
        self.export_button.clicked.connect(self._on_export)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # Load documents
        self._load_documents()

    def _load_documents(self):
        """Load all documents from database"""
        try:
            documents = self.document_dao.get_all()

            self.document_list.clear()

            for doc in documents:
                title = doc.get('title') or f"Document {doc['doc_id']}"
                if doc.get('year'):
                    title += f" ({doc['year']})"

                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, doc['doc_id'])
                self.document_list.addItem(item)

            logger.info(f"Loaded {len(documents)} documents")

        except Exception as e:
            logger.error(f"Failed to load documents: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load documents:\n{e}")

    def _on_select_all(self):
        """Select all documents"""
        self.document_list.selectAll()

    def _on_select_none(self):
        """Deselect all documents"""
        self.document_list.clearSelection()

    def _on_style_changed(self, index):
        """Handle style change"""
        # Clear preview when style changes
        if self.preview_text.toPlainText():
            self.preview_text.setPlainText("Click 'Generate Citations' to see preview")

    def _on_generate(self):
        """Generate citations for selected documents"""
        # Get selected documents
        selected_items = self.document_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one document")
            return

        # Get document IDs
        doc_ids = [item.data(Qt.UserRole) for item in selected_items]

        # Fetch full document data
        documents = []
        for doc_id in doc_ids:
            doc = self.document_dao.get_by_id(doc_id)
            if doc:
                documents.append(doc)

        if not documents:
            QMessageBox.warning(self, "Error", "No documents found")
            return

        # Sort if requested
        if self.alphabetical_check.isChecked():
            documents.sort(key=lambda d: (d.get('authors') or 'ZZZ', d.get('year') or 9999))

        # Generate citations
        style_data = self.style_combo.currentData()

        try:
            if style_data == "bibtex":
                # Generate BibTeX
                citations_text = self.bibtex_generator.generate_batch(documents)
            else:
                # Generate formatted citations
                citation_style = style_data
                citations = self.citation_formatter.format_batch(documents, citation_style)
                citations_text = "\n\n".join(citations)

            self.preview_text.setPlainText(citations_text)

            # Enable action buttons
            self.copy_button.setEnabled(True)
            self.export_button.setEnabled(True)

            logger.info(f"Generated {len(documents)} citations")

        except Exception as e:
            logger.error(f"Failed to generate citations: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to generate citations:\n{e}")

    def _on_copy(self):
        """Copy citations to clipboard"""
        text = self.preview_text.toPlainText()

        if not text:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        QMessageBox.information(self, "Copied", "Citations copied to clipboard")

    def _on_export(self):
        """Export citations to file"""
        text = self.preview_text.toPlainText()

        if not text:
            return

        # Determine file extension
        style_data = self.style_combo.currentData()
        if style_data == "bibtex":
            file_filter = "BibTeX Files (*.bib);;Text Files (*.txt);;All Files (*.*)"
            default_ext = ".bib"
        else:
            file_filter = "Text Files (*.txt);;All Files (*.*)"
            default_ext = ".txt"

        # Ask for file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Citations",
            str(Path.home() / f"citations{default_ext}"),
            file_filter
        )

        if not file_path:
            return

        try:
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            QMessageBox.information(
                self,
                "Exported",
                f"Citations exported to:\n{file_path}"
            )

            logger.info(f"Exported citations to: {file_path}")

        except Exception as e:
            logger.error(f"Failed to export citations: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Failed", f"Failed to export:\n{e}")
