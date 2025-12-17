"""
Collection Panel - Hierarchical folder structure for organizing documents
"""
import logging
from typing import Optional, List, Dict

from qt_compat import (
    QAction, QColor, QColorDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget, Qt, QtCore, QtGui, Signal, Slot
)

logger = logging.getLogger(__name__)


class CollectionPanel(QWidget):
    """컬렉션(폴더) 관리 패널"""

    # Signals
    collection_selected = Signal(int)  # collection_id
    collection_created = Signal(str, object)  # name, parent_id
    collection_renamed = Signal(int, str)  # collection_id, new_name
    collection_deleted = Signal(int)  # collection_id
    collection_color_changed = Signal(int, str)  # collection_id, color
    document_moved_to_collection = Signal(int, int)  # doc_id, collection_id
    show_all_documents = Signal()  # Show all documents (no filter)

    def __init__(self):
        super().__init__()

        self.folder_manager = None  # Will be set by app controller
        self.current_collection_id: Optional[int] = None
        self.collections: List[Dict] = []

        # Color palette for folders
        self.colors = [
            "#e74c3c",  # Red
            "#3498db",  # Blue
            "#2ecc71",  # Green
            "#f39c12",  # Orange
            "#9b59b6",  # Purple
            "#1abc9c",  # Turquoise
            "#e67e22",  # Carrot
            "#95a5a6",  # Gray
        ]

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with title and add button
        header_layout = QHBoxLayout()

        header = QLabel("📁 Collections")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.add_folder_button = QPushButton("+")
        self.add_folder_button.setToolTip("Create new collection")
        self.add_folder_button.setMaximumWidth(30)
        self.add_folder_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 14pt;
                background-color: #3498db;
                color: white;
                border-radius: 15px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.add_folder_button.clicked.connect(self._on_add_root_folder)
        header_layout.addWidget(self.add_folder_button)

        layout.addLayout(header_layout)

        # "All Documents" button
        self.all_docs_button = QPushButton("📚 All Documents")
        self.all_docs_button.setToolTip("Show all documents")
        self.all_docs_button.setCheckable(True)
        self.all_docs_button.setChecked(True)
        self.all_docs_button.clicked.connect(self._on_show_all_documents)
        self.all_docs_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
            QPushButton:checked:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(self.all_docs_button)

        # Collection tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setToolTip("Right-click for options\nDrag documents here to organize")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #ecf0f1;
            }
        """)
        layout.addWidget(self.tree)

        # Info label
        self.info_label = QLabel("No collections")
        self.info_label.setStyleSheet("color: gray; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.info_label)

    def set_folder_manager(self, folder_manager):
        """Set folder manager"""
        self.folder_manager = folder_manager
        self.refresh()

    def refresh(self):
        """Refresh collection tree"""
        if not self.folder_manager:
            return

        try:
            self.collections = self.folder_manager.get_all_folders()
            self._rebuild_tree()

            # Update info
            self.info_label.setText(f"{len(self.collections)} collections")

            logger.debug(f"Refreshed {len(self.collections)} collections")

        except Exception as e:
            logger.error(f"Failed to refresh collections: {e}", exc_info=True)

    def _rebuild_tree(self):
        """Rebuild tree from collections data"""
        self.tree.clear()

        # Build tree structure
        root_collections = [c for c in self.collections if c['parent_id'] is None]

        for collection in root_collections:
            item = self._create_tree_item(collection)
            self.tree.addTopLevelItem(item)
            self._add_children(item, collection['collection_id'])

        # Expand all by default
        self.tree.expandAll()

    def _create_tree_item(self, collection: Dict) -> QTreeWidgetItem:
        """Create tree widget item for a collection"""
        # Get document count
        doc_count = 0
        if self.folder_manager:
            doc_count = self.folder_manager.get_folder_count(collection['collection_id'])

        # Create item text with icon and count
        icon = collection.get('icon', 'folder')
        icon_map = {
            'folder': '📁',
            'project': '📂',
            'archive': '📦',
            'star': '⭐',
        }
        icon_emoji = icon_map.get(icon, '📁')

        text = f"{icon_emoji} {collection['name']} ({doc_count})"

        item = QTreeWidgetItem([text])
        item.setData(0, Qt.UserRole, collection['collection_id'])
        item.setData(0, Qt.UserRole + 1, collection)

        # Set color
        color = collection.get('color', '#3498db')
        try:
            qcolor = QColor(color)
            item.setForeground(0, qcolor)
        except:
            pass

        return item

    def _add_children(self, parent_item: QTreeWidgetItem, parent_id: int):
        """Recursively add child collections"""
        children = [c for c in self.collections if c['parent_id'] == parent_id]

        for child in children:
            child_item = self._create_tree_item(child)
            parent_item.addChild(child_item)
            self._add_children(child_item, child['collection_id'])

    def _on_show_all_documents(self):
        """Show all documents"""
        # Unselect tree items
        self.tree.clearSelection()
        self.current_collection_id = None
        self.all_docs_button.setChecked(True)

        self.show_all_documents.emit()
        logger.debug("Show all documents")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click"""
        collection_id = item.data(0, Qt.UserRole)
        self.current_collection_id = collection_id

        # Uncheck "All Documents" button
        self.all_docs_button.setChecked(False)

        self.collection_selected.emit(collection_id)
        logger.debug(f"Selected collection: {collection_id}")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click - rename"""
        self._rename_collection(item)

    def _on_add_root_folder(self):
        """Add new root-level folder"""
        self._add_folder(parent_id=None)

    def _add_folder(self, parent_id: Optional[int] = None):
        """Add new folder"""
        name, ok = QInputDialog.getText(
            self,
            "New Collection",
            "Enter collection name:",
            QLineEdit.Normal,
            ""
        )

        if ok and name:
            # Choose color
            color = self.colors[len(self.collections) % len(self.colors)]

            self.collection_created.emit(name, parent_id)
            logger.info(f"Created collection: {name} (parent: {parent_id})")

    def _rename_collection(self, item: QTreeWidgetItem):
        """Rename collection"""
        collection_id = item.data(0, Qt.UserRole)
        collection = item.data(0, Qt.UserRole + 1)
        current_name = collection['name']

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Collection",
            "Enter new name:",
            QLineEdit.Normal,
            current_name
        )

        if ok and new_name and new_name != current_name:
            self.collection_renamed.emit(collection_id, new_name)
            logger.info(f"Renamed collection {collection_id}: {new_name}")

    def _delete_collection(self, item: QTreeWidgetItem):
        """Delete collection"""
        collection_id = item.data(0, Qt.UserRole)
        collection = item.data(0, Qt.UserRole + 1)

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Collection",
            f"Delete collection '{collection['name']}'?\n\n"
            "Choose 'Yes' to delete documents inside.\n"
            "Choose 'No' to keep documents.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if reply == QMessageBox.Cancel:
            return

        delete_documents = (reply == QMessageBox.Yes)

        self.collection_deleted.emit(collection_id)
        logger.info(f"Deleted collection {collection_id} (delete_documents={delete_documents})")

    def _change_color(self, item: QTreeWidgetItem):
        """Change collection color"""
        collection_id = item.data(0, Qt.UserRole)
        collection = item.data(0, Qt.UserRole + 1)
        current_color = collection.get('color', '#3498db')

        color = QColorDialog.getColor(QColor(current_color), self, "Choose Collection Color")

        if color.isValid():
            color_hex = color.name()
            self.collection_color_changed.emit(collection_id, color_hex)
            logger.info(f"Changed collection {collection_id} color to {color_hex}")

    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.tree.itemAt(position)

        menu = QMenu(self)

        if item:
            # Collection item context menu
            collection_id = item.data(0, Qt.UserRole)

            add_subfolder_action = QAction("➕ Add Subfolder", self)
            add_subfolder_action.triggered.connect(lambda: self._add_folder(parent_id=collection_id))
            menu.addAction(add_subfolder_action)

            menu.addSeparator()

            rename_action = QAction("✏️ Rename", self)
            rename_action.triggered.connect(lambda: self._rename_collection(item))
            menu.addAction(rename_action)

            color_action = QAction("🎨 Change Color", self)
            color_action.triggered.connect(lambda: self._change_color(item))
            menu.addAction(color_action)

            menu.addSeparator()

            delete_action = QAction("🗑️ Delete", self)
            delete_action.triggered.connect(lambda: self._delete_collection(item))
            menu.addAction(delete_action)

        else:
            # Empty space context menu
            add_action = QAction("➕ New Collection", self)
            add_action.triggered.connect(self._on_add_root_folder)
            menu.addAction(add_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def get_selected_collection_id(self) -> Optional[int]:
        """Get currently selected collection ID"""
        return self.current_collection_id

    def select_collection(self, collection_id: int):
        """Programmatically select a collection"""
        # Find and select item
        def find_item(parent_item, target_id):
            if parent_item is None:
                # Search top-level items
                for i in range(self.tree.topLevelItemCount()):
                    item = self.tree.topLevelItem(i)
                    if item.data(0, Qt.UserRole) == target_id:
                        return item
                    # Search children
                    found = find_item(item, target_id)
                    if found:
                        return found
            else:
                # Search children
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    if child.data(0, Qt.UserRole) == target_id:
                        return child
                    # Search descendants
                    found = find_item(child, target_id)
                    if found:
                        return found
            return None

        item = find_item(None, collection_id)
        if item:
            self.tree.setCurrentItem(item)
            self.current_collection_id = collection_id
            self.all_docs_button.setChecked(False)
