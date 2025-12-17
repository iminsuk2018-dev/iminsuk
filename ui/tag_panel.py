"""
Tag 관리 패널
"""
import logging
from typing import Optional, List

from qt_compat import (
    QAction, QColor, QCompleter, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QStringListModel, QVBoxLayout,
    QWidget, Qt, QtCore, QtGui, QtWidgets, Signal, Slot
)

logger = logging.getLogger(__name__)


class TagPanel(QWidget):
    """태그 관리 패널"""

    # Signals
    tag_added = Signal(int, str)  # doc_id, tag_name
    tag_removed = Signal(int, int)  # doc_id, tag_id
    tag_clicked = Signal(int)  # tag_id

    def __init__(self):
        super().__init__()

        self.current_doc_id: Optional[int] = None
        self.current_file_path: Optional[str] = None
        self.document_tags: List = []
        self.all_tags: List = []
        self.tag_suggester = None  # Will be set by app controller

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Tags")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Document tags section
        doc_tags_label = QLabel("Document Tags:")
        layout.addWidget(doc_tags_label)

        self.doc_tag_list = QListWidget()
        self.doc_tag_list.setMaximumHeight(150)
        self.doc_tag_list.setToolTip("Tags assigned to this document\nRight-click to remove")
        self.doc_tag_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.doc_tag_list.customContextMenuRequested.connect(self._show_tag_context_menu)
        layout.addWidget(self.doc_tag_list)

        # Add tag section
        add_layout = QHBoxLayout()

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tag name...")
        self.tag_input.setToolTip("Type a tag name and press Enter or click Add Tag\nAutocomplete suggestions from existing tags")
        self.tag_input.returnPressed.connect(self._on_add_tag)

        # Add autocomplete
        self.tag_completer = QCompleter()
        self.tag_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tag_completer.setFilterMode(Qt.MatchContains)
        self.tag_input.setCompleter(self.tag_completer)

        add_layout.addWidget(self.tag_input)

        self.add_tag_button = QPushButton("Add Tag")
        self.add_tag_button.setToolTip("Add a new tag to this document")
        self.add_tag_button.clicked.connect(self._on_add_tag)
        self.add_tag_button.setEnabled(False)
        add_layout.addWidget(self.add_tag_button)

        layout.addLayout(add_layout)

        # Suggested tags section
        suggest_header = QHBoxLayout()
        suggested_tags_label = QLabel("Suggested Tags:")
        suggested_tags_label.setStyleSheet("margin-top: 10px;")
        suggest_header.addWidget(suggested_tags_label)

        self.suggest_button = QPushButton("Get Suggestions")
        self.suggest_button.setToolTip("Analyze document content and suggest relevant tags")
        self.suggest_button.setEnabled(False)
        self.suggest_button.setMaximumWidth(120)
        self.suggest_button.clicked.connect(self._on_get_suggestions)
        suggest_header.addWidget(self.suggest_button)

        layout.addLayout(suggest_header)

        self.suggested_tag_list = QListWidget()
        self.suggested_tag_list.setMaximumHeight(120)
        self.suggested_tag_list.setToolTip("AI-suggested tags based on document content\nDouble-click to add")
        self.suggested_tag_list.itemDoubleClicked.connect(self._on_suggested_tag_double_clicked)
        layout.addWidget(self.suggested_tag_list)

        # All tags section
        all_tags_label = QLabel("All Tags:")
        all_tags_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(all_tags_label)

        self.all_tag_list = QListWidget()
        self.all_tag_list.setToolTip("All tags in your library\nDouble-click to add to current document")
        self.all_tag_list.itemDoubleClicked.connect(self._on_all_tag_double_clicked)
        layout.addWidget(self.all_tag_list)

        # Info label
        self.info_label = QLabel("No document selected")
        self.info_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.info_label)

    def set_document(self, doc_id: int, doc_title: str, file_path: str = None):
        """Set current document"""
        self.current_doc_id = doc_id
        self.current_file_path = file_path
        self.info_label.setText(f"Document: {doc_title[:30]}...")
        self.add_tag_button.setEnabled(True)
        self.suggest_button.setEnabled(True if self.tag_suggester else False)

        # Clear suggested tags when document changes
        self.suggested_tag_list.clear()

        logger.debug(f"Set document: {doc_id}")

    def load_document_tags(self, tags: List[dict]):
        """Load tags for current document"""
        self.document_tags = tags
        self.doc_tag_list.clear()

        for tag in tags:
            item = QListWidgetItem(f"🏷️ {tag['tag_name']}")
            item.setData(Qt.UserRole, tag['tag_id'])

            # Set color if available
            if tag.get('color'):
                try:
                    color = QColor(tag['color'])
                    item.setForeground(color)
                except:
                    pass

            self.doc_tag_list.addItem(item)

        logger.debug(f"Loaded {len(tags)} document tags")

    def load_all_tags(self, tags: List[dict]):
        """Load all available tags"""
        self.all_tags = tags
        self.all_tag_list.clear()

        # Update autocomplete with tag names
        tag_names = [tag['tag_name'] for tag in tags]
        completer_model = QStringListModel(tag_names)
        self.tag_completer.setModel(completer_model)

        for tag in tags:
            # Show tag with usage count if available
            tag_text = tag['tag_name']
            if 'doc_count' in tag:
                tag_text += f" ({tag['doc_count']})"

            item = QListWidgetItem(tag_text)
            item.setData(Qt.UserRole, tag['tag_id'])

            # Set color
            if tag.get('color'):
                try:
                    color = QColor(tag['color'])
                    item.setForeground(color)
                except:
                    pass

            self.all_tag_list.addItem(item)

        logger.debug(f"Loaded {len(tags)} total tags (autocomplete updated)")

    def _on_add_tag(self):
        """Handle add tag button"""
        tag_name = self.tag_input.text().strip()

        if not tag_name:
            QMessageBox.warning(self, "Empty Tag", "Please enter a tag name")
            return

        if self.current_doc_id is None:
            QMessageBox.warning(self, "No Document", "Please select a document first")
            return

        # Check if already tagged
        if any(t['tag_name'].lower() == tag_name.lower() for t in self.document_tags):
            QMessageBox.information(self, "Tag Exists", "This document already has this tag")
            return

        self.tag_added.emit(self.current_doc_id, tag_name)

        # Clear input
        self.tag_input.clear()

        logger.info(f"Add tag requested: '{tag_name}' to doc {self.current_doc_id}")

    def _on_all_tag_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on all tags list - add to document"""
        if self.current_doc_id is None:
            return

        tag_id = item.data(Qt.UserRole)

        # Find tag name
        tag = next((t for t in self.all_tags if t['tag_id'] == tag_id), None)
        if tag:
            # Check if already tagged
            if any(t['tag_id'] == tag_id for t in self.document_tags):
                QMessageBox.information(self, "Tag Exists", "This document already has this tag")
                return

            self.tag_added.emit(self.current_doc_id, tag['tag_name'])

    def _show_tag_context_menu(self, position):
        """Show context menu for document tag"""
        item = self.doc_tag_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        remove_action = QAction("Remove Tag", self)
        remove_action.triggered.connect(lambda: self._remove_tag(item))
        menu.addAction(remove_action)

        menu.exec(self.doc_tag_list.mapToGlobal(position))

    def _remove_tag(self, item: QListWidgetItem):
        """Remove tag from document"""
        if self.current_doc_id is None:
            return

        tag_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Remove Tag",
            "Remove this tag from the document?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.tag_removed.emit(self.current_doc_id, tag_id)
            logger.info(f"Remove tag requested: {tag_id} from doc {self.current_doc_id}")

    def _on_get_suggestions(self):
        """Get smart tag suggestions for current document"""
        if not self.current_doc_id or not self.tag_suggester:
            return

        # Disable button during processing
        self.suggest_button.setEnabled(False)
        self.suggest_button.setText("Analyzing...")

        try:
            # Get suggestions
            suggestions = self.tag_suggester.suggest_tags(
                self.current_doc_id,
                self.current_file_path,
                limit=10
            )

            # Display suggestions
            self.suggested_tag_list.clear()

            if not suggestions:
                item = QListWidgetItem("No suggestions found")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                self.suggested_tag_list.addItem(item)
            else:
                for suggestion in suggestions:
                    # Format: confidence indicator + tag name + reason
                    confidence = suggestion['confidence']
                    confidence_icon = "⭐" if confidence > 0.8 else "✓" if confidence > 0.6 else "→"

                    display_text = f"{confidence_icon} {suggestion['tag_name']}"

                    if suggestion.get('exists'):
                        display_text += " (exists)"

                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, suggestion)  # Store full suggestion

                    # Color based on confidence
                    if confidence > 0.8:
                        item.setForeground(QColor("#2ecc71"))  # Green
                    elif confidence > 0.6:
                        item.setForeground(QColor("#3498db"))  # Blue
                    else:
                        item.setForeground(QColor("#95a5a6"))  # Gray

                    # Tooltip with reason
                    item.setToolTip(f"{suggestion['reason']}\nConfidence: {confidence:.0%}")

                    self.suggested_tag_list.addItem(item)

            logger.info(f"Generated {len(suggestions)} tag suggestions")

        except Exception as e:
            logger.error(f"Failed to get tag suggestions: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to generate tag suggestions:\n{str(e)}"
            )
        finally:
            # Re-enable button
            self.suggest_button.setEnabled(True)
            self.suggest_button.setText("Get Suggestions")

    def _on_suggested_tag_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on suggested tag - add to document"""
        if self.current_doc_id is None:
            return

        suggestion = item.data(Qt.UserRole)
        if not suggestion:
            return

        tag_name = suggestion['tag_name']

        # Check if already tagged
        if any(t['tag_name'].lower() == tag_name.lower() for t in self.document_tags):
            QMessageBox.information(self, "Tag Exists", "This document already has this tag")
            return

        # Add tag
        self.tag_added.emit(self.current_doc_id, tag_name)

        # Remove from suggestions
        self.suggested_tag_list.takeItem(self.suggested_tag_list.row(item))

        logger.info(f"Added suggested tag: '{tag_name}' to doc {self.current_doc_id}")

    def clear(self):
        """Clear all data"""
        self.current_doc_id = None
        self.document_tags = []
        self.doc_tag_list.clear()
        self.tag_input.clear()
        self.info_label.setText("No document selected")
        self.add_tag_button.setEnabled(False)
