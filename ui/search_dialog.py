"""
통합 검색 다이얼로그
"""
import logging
from typing import Optional

from qt_compat import (
    QCheckBox, QColor, QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextBrowser,
    QVBoxLayout, QtCore, QtGui, QtWidgets, Signal, Slot
)
from qt_compat import (
    QCheckBox, QColor, QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextBrowser,
    QVBoxLayout, QtCore, QtGui, QtWidgets, Signal, Slot
)
from ui.styles import get_dialog_style, set_primary_button

logger = logging.getLogger(__name__)


class SearchDialog(QDialog):
    """통합 검색 다이얼로그"""

    # Signals
    document_selected = Signal(int)  # doc_id
    annotation_selected = Signal(int, int)  # doc_id, annotation_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(get_dialog_style())

        self.search_results = None
        self.is_searching = False  # Prevent concurrent searches

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Search")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        # Search input
        search_layout = QHBoxLayout()

        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query...")
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_button)

        layout.addLayout(search_layout)

        # Search options
        options_group = QGroupBox("Search In:")
        options_layout = QHBoxLayout(options_group)

        self.search_titles = QCheckBox("Titles")
        self.search_titles.setChecked(True)
        options_layout.addWidget(self.search_titles)

        self.search_abstracts = QCheckBox("Abstracts")
        self.search_abstracts.setChecked(True)
        options_layout.addWidget(self.search_abstracts)

        self.search_annotations = QCheckBox("Notes")
        self.search_annotations.setChecked(True)
        options_layout.addWidget(self.search_annotations)

        self.search_tags = QCheckBox("Tags")
        self.search_tags.setChecked(True)
        options_layout.addWidget(self.search_tags)

        options_layout.addStretch()

        layout.addWidget(options_group)

        # Results
        results_label = QLabel("Results:")
        layout.addWidget(results_label)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self.results_list)

        # Result details
        details_label = QLabel("Preview:")
        layout.addWidget(details_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setMaximumHeight(150)
        layout.addWidget(self.details_browser)

        # Status
        self.status_label = QLabel("Enter a search query")
        self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def set_search_engine(self, search_engine):
        """Set search engine instance"""
        self.search_engine = search_engine

    def _get_search_types(self):
        """Get selected search types"""
        types = []
        if self.search_titles.isChecked():
            types.append('title')
        if self.search_abstracts.isChecked():
            types.append('abstract')
        if self.search_annotations.isChecked():
            types.append('annotation')
        if self.search_tags.isChecked():
            types.append('tag')
        return types if types else None

    def _on_search(self):
        """Perform search"""
        # Prevent concurrent searches
        if self.is_searching:
            return

        query = self.search_input.text().strip()

        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a search query")
            return

        if not hasattr(self, 'search_engine'):
            QMessageBox.critical(self, "Error", "Search engine not initialized")
            return

        # Set searching state
        self.is_searching = True
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.status_label.setText("🔍 Searching...")
        self.results_list.clear()
        self.details_browser.clear()

        try:
            # Get search types
            search_types = self._get_search_types()

            # Perform search
            results = self.search_engine.search(query, content_types=search_types)
            self.search_results = results

            # Display results
            self._display_results(results)

            self.status_label.setText(f"Found {results.total_count} results")

            logger.info(f"Search '{query}' returned {results.total_count} results")

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Search Error", f"Search failed:\n{str(e)}")
            self.status_label.setText("❌ Search failed")

        finally:
            # Always restore search state
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)

    def _display_results(self, results):
        """Display search results"""
        self.results_list.clear()

        # Check if empty
        if results.total_count == 0:
            empty_item = QListWidgetItem("🔍 No results found\n\nTry:\n• Different keywords\n• Check spelling\n• Use broader search terms\n• Search in different content types")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setForeground(QColor("#808080"))
            self.results_list.addItem(empty_item)
            return

        # Group by type
        for result_type, result_list in results.results_by_type.items():
            # Add type header
            header_item = QListWidgetItem(f"── {result_type.upper()} ({len(result_list)}) ──")
            header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
            header_item.setBackground(Qt.lightGray)
            self.results_list.addItem(header_item)

            # Add results
            for result in result_list:
                if result_type == 'annotation':
                    item_text = f"  [Page {result.page_number + 1}] {result.title}: {result.matched_text[:60]}..."
                elif result_type == 'tag':
                    item_text = f"  🏷️ {result.matched_text} - {result.title}"
                else:
                    item_text = f"  {result.title} ({result.year or 'N/A'})"

                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, result)
                self.results_list.addItem(item)

    def _on_result_clicked(self, item: QListWidgetItem):
        """Handle result selection - show preview"""
        result = item.data(Qt.UserRole)

        if result is None:  # Header item
            return

        # Show details
        html = f"<h3>{result.title}</h3>"

        if result.year:
            html += f"<p><b>Year:</b> {result.year}</p>"

        if result.authors:
            html += f"<p><b>Authors:</b> {result.authors}</p>"

        html += f"<p><b>Type:</b> {result.result_type}</p>"

        if result.result_type == 'annotation' and result.page_number is not None:
            html += f"<p><b>Page:</b> {result.page_number + 1}</p>"

        html += f"<hr><p>{result.matched_text}</p>"

        self.details_browser.setHtml(html)

    def _on_result_double_clicked(self, item: QListWidgetItem):
        """Handle result double-click - open document"""
        result = item.data(Qt.UserRole)

        if result is None:  # Header item
            return

        if result.result_type == 'annotation':
            self.annotation_selected.emit(result.doc_id, result.annotation_id)
        else:
            self.document_selected.emit(result.doc_id)

        logger.info(f"Result double-clicked: doc={result.doc_id}, type={result.result_type}")

    def show_and_search(self, query: str):
        """Show dialog and perform search"""
        self.search_input.setText(query)
        self.show()
        self._on_search()
