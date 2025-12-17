"""
Main application window
"""
import logging
from pathlib import Path
from typing import Optional

from qt_compat import (
    QAction, QColor, QFileDialog, QHBoxLayout, QInputDialog, QKeySequence, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QSplitter,
    QStatusBar, QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget, Qt, QtCore, QtGui, QtWidgets, Signal, Slot
)

from config import (
    APP_NAME, APP_VERSION,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""

    # Signals
    document_selected = Signal(int)  # doc_id
    pdf_add_requested = Signal(str)  # file_path

    def __init__(self, workspace=None):
        super().__init__()

        self.workspace = workspace
        self.current_doc_id: Optional[int] = None

        self._init_ui()
        self._create_menubar()
        self._create_toolbar()
        self._create_statusbar()

        logger.info("Main window initialized")

    def _init_ui(self):
        """Initialize UI layout"""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create main splitter (horizontal split)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Left panel: Collection panel + Document tree (vertical split)
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setMaximumWidth(350)
        left_splitter.setMinimumWidth(250)

        # Collection panel (top)
        self.collection_panel = CollectionPanel()

        # Document tree (bottom)
        self.document_tree = QTreeWidget()
        self.document_tree.setHeaderLabel("Documents")
        self.document_tree.setToolTip("Your PDF document library\nRight-click to manage\nDrag & drop PDFs to add or organize")
        self.document_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.document_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.document_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Enable drag and drop
        self.document_tree.setAcceptDrops(True)
        self.document_tree.setDragEnabled(True)
        self.document_tree.setDragDropMode(QTreeWidget.DragDrop)
        self.document_tree.setDefaultDropAction(Qt.MoveAction)

        # Store original methods before overriding
        self._tree_drag_enter_event = self.document_tree.dragEnterEvent
        self._tree_drag_move_event = self.document_tree.dragMoveEvent
        self._tree_drop_event = self.document_tree.dropEvent

        # Override drag and drop events
        self.document_tree.dragEnterEvent = self._on_tree_drag_enter
        self.document_tree.dragMoveEvent = self._on_tree_drag_move
        self.document_tree.dropEvent = self._on_tree_drop

        # Add to left splitter
        left_splitter.addWidget(self.collection_panel)
        left_splitter.addWidget(self.document_tree)
        left_splitter.setSizes([200, 400])  # Collection: 200px, Documents: 400px

        # Center: PDF viewer (placeholder for now)
        self.pdf_viewer_placeholder = QLabel("No PDF loaded\n\nUse File > Add PDF to get started")
        self.pdf_viewer_placeholder.setAlignment(Qt.AlignCenter)
        self.pdf_viewer_placeholder.setStyleSheet("color: gray; font-size: 14pt;")

        # Right panel: Annotations and tags
        from ui.annotation_panel import AnnotationPanel
        from ui.tag_panel import TagPanel
        from ui.recommendations_panel import RecommendationsPanel
        from ui.collection_panel import CollectionPanel

        self.right_panel = QTabWidget()

        # Annotation panel
        self.annotation_panel = AnnotationPanel()
        self.right_panel.addTab(self.annotation_panel, "Notes")

        # Tag panel
        self.tag_panel = TagPanel()
        self.right_panel.addTab(self.tag_panel, "Tags")

        # Recommendations panel
        self.recommendations_panel = RecommendationsPanel()
        self.right_panel.addTab(self.recommendations_panel, "Recommendations")

        self.right_panel.setMaximumWidth(350)
        self.right_panel.setMinimumWidth(250)

        # Add to main splitter
        self.main_splitter.addWidget(left_splitter)
        self.main_splitter.addWidget(self.pdf_viewer_placeholder)
        self.main_splitter.addWidget(self.right_panel)

        # Set initial sizes (40% - 60% - 40%)
        self.main_splitter.setSizes([300, 800, 300])

        layout.addWidget(self.main_splitter)

    def _create_menubar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        add_pdf_action = QAction("&Add PDF...", self)
        add_pdf_action.setShortcut("Ctrl+O")
        add_pdf_action.setStatusTip("Add PDF documents to your research library")
        add_pdf_action.triggered.connect(self._on_add_pdf)
        file_menu.addAction(add_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        search_action = QAction("&Search...", self)
        search_action.setShortcut("Ctrl+F")
        search_action.setStatusTip("Search through documents, annotations, and tags")
        search_action.triggered.connect(self._on_search)
        edit_menu.addAction(search_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        toggle_left_action = QAction("Toggle Document List", self)
        toggle_left_action.triggered.connect(self._toggle_document_list)
        view_menu.addAction(toggle_left_action)

        toggle_right_action = QAction("Toggle Annotations Panel", self)
        toggle_right_action.triggered.connect(self._toggle_annotations_panel)
        view_menu.addAction(toggle_right_action)

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        light_theme_action = QAction("&Light", self)
        light_theme_action.triggered.connect(lambda: self._on_theme_change("light"))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setShortcut("Ctrl+D")
        dark_theme_action.triggered.connect(lambda: self._on_theme_change("dark"))
        theme_menu.addAction(dark_theme_action)

        toggle_theme_action = QAction("&Toggle Theme", self)
        toggle_theme_action.setShortcut("Ctrl+T")
        toggle_theme_action.triggered.connect(self._on_toggle_theme)
        theme_menu.addAction(toggle_theme_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        target_journals_action = QAction("&Manage Recommendations...", self)
        target_journals_action.setShortcut("Ctrl+R")
        target_journals_action.setStatusTip("Manage target journals and paper recommendations")
        target_journals_action.triggered.connect(self._on_target_journals)
        tools_menu.addAction(target_journals_action)

        web_rec_action = QAction("&Web Recommendations...", self)
        web_rec_action.setShortcut("Ctrl+W")
        web_rec_action.setStatusTip("Open web-based recommendation system")
        web_rec_action.triggered.connect(self._on_web_recommendations)
        tools_menu.addAction(web_rec_action)

        tools_menu.addSeparator()

        citation_action = QAction("&Citation Manager...", self)
        citation_action.setShortcut("Ctrl+Shift+C")
        citation_action.triggered.connect(self._on_citations)
        tools_menu.addAction(citation_action)

        reference_action = QAction("&Reference Manager...", self)
        reference_action.setShortcut("Ctrl+Shift+R")
        reference_action.triggered.connect(self._on_references)
        tools_menu.addAction(reference_action)

        tools_menu.addSeparator()

        duplicate_action = QAction("Find &Duplicates...", self)
        duplicate_action.triggered.connect(self._on_find_duplicates)
        tools_menu.addAction(duplicate_action)

        tools_menu.addSeparator()

        watched_folders_action = QAction("&Watched Folders...", self)
        watched_folders_action.setStatusTip("Manage folders that are automatically monitored for new PDFs")
        watched_folders_action.triggered.connect(self._on_watched_folders)
        tools_menu.addAction(watched_folders_action)

        tools_menu.addSeparator()

        sync_action = QAction("&Sync Status...", self)
        sync_action.triggered.connect(self._on_sync_status)
        tools_menu.addAction(sync_action)

        integrity_action = QAction("Check &Integrity...", self)
        integrity_action.triggered.connect(self._on_check_integrity)
        tools_menu.addAction(integrity_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.setStatusTip("View all keyboard shortcuts")
        shortcuts_action.triggered.connect(self._on_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add PDF action
        add_action = QAction("Add PDF", self)
        add_action.setToolTip("Add a new PDF document to your library (Ctrl+O)")
        add_action.setStatusTip("Add PDF files to your research library")
        add_action.triggered.connect(self._on_add_pdf)
        toolbar.addAction(add_action)

        toolbar.addSeparator()

        # Search action
        search_action = QAction("Search", self)
        search_action.setToolTip("Search through all documents and annotations (Ctrl+F)")
        search_action.setStatusTip("Search your entire library")
        search_action.triggered.connect(self._on_search)
        toolbar.addAction(search_action)

    def _create_statusbar(self):
        """Create status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.statusbar.showMessage("Ready")

    # Event handlers

    def _on_add_pdf(self):
        """Handle Add PDF action"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF file",
            str(Path.home()),
            "PDF Files (*.pdf)"
        )

        if file_path:
            logger.info(f"User selected PDF: {file_path}")
            self.pdf_add_requested.emit(file_path)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click (folder or document)"""
        item_type = item.data(0, Qt.UserRole)  # 'folder' or 'document'
        item_id = item.data(0, Qt.UserRole + 1)  # folder_id or doc_id

        if item_type == 'document' and item_id:
            self.current_doc_id = item_id
            self.document_selected.emit(item_id)
            logger.debug(f"Document selected: {item_id}")
        elif item_type == 'folder':
            logger.debug(f"Folder clicked: {item_id}")

    def _on_tree_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.document_tree.itemAt(position)

        menu = QMenu()

        if item is None:
            # Clicked on empty area - show root level actions
            create_folder_action = QAction("Create Folder", self)
            create_folder_action.triggered.connect(lambda: self._on_create_folder(None))
            menu.addAction(create_folder_action)
        else:
            item_type = item.data(0, Qt.UserRole)
            item_id = item.data(0, Qt.UserRole + 1)

            if item_type == 'folder':
                # Folder actions
                create_subfolder_action = QAction("Create Subfolder", self)
                create_subfolder_action.triggered.connect(lambda: self._on_create_folder(item_id))
                menu.addAction(create_subfolder_action)

                menu.addSeparator()

                rename_action = QAction("Rename", self)
                rename_action.triggered.connect(lambda: self._on_rename_folder(item_id, item))
                menu.addAction(rename_action)

                delete_action = QAction("Delete Folder", self)
                delete_action.triggered.connect(lambda: self._on_delete_folder(item_id))
                menu.addAction(delete_action)

            elif item_type == 'document':
                # Document actions
                remove_action = QAction("Remove from Folder", self)
                remove_action.triggered.connect(lambda: self._on_remove_from_folder(item_id, item))
                menu.addAction(remove_action)

        menu.exec_(self.document_tree.viewport().mapToGlobal(position))

    def _on_create_folder(self, parent_id: Optional[int]):
        """Create new folder"""
        folder_name, ok = QInputDialog.getText(
            self,
            "Create Folder",
            "Folder name:",
            text="New Folder"
        )

        if ok and folder_name:
            # Will be handled by app controller
            logger.info(f"Creating folder: {folder_name} under parent: {parent_id}")
            if hasattr(self.workspace, 'folder_manager'):
                try:
                    self.workspace.folder_manager.create_folder(folder_name, parent_id)
                    self.refresh_document_tree()
                except Exception as e:
                    logger.error(f"Failed to create folder: {e}", exc_info=True)
                    self.show_error("Error", f"Failed to create folder:\n{e}")

    def _on_rename_folder(self, folder_id: int, item: QTreeWidgetItem):
        """Rename folder"""
        current_name = item.text(0)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Folder",
            "New folder name:",
            text=current_name
        )

        if ok and new_name and new_name != current_name:
            logger.info(f"Renaming folder {folder_id} to: {new_name}")
            if hasattr(self.workspace, 'folder_manager'):
                try:
                    self.workspace.folder_manager.rename_folder(folder_id, new_name)
                    self.refresh_document_tree()
                except Exception as e:
                    logger.error(f"Failed to rename folder: {e}", exc_info=True)
                    self.show_error("Error", f"Failed to rename folder:\n{e}")

    def _on_delete_folder(self, folder_id: int):
        """Delete folder"""
        reply = self.confirm(
            "Delete Folder",
            "Delete this folder?\n\nDocuments will not be deleted, only the folder organization."
        )

        if reply:
            logger.info(f"Deleting folder: {folder_id}")
            if hasattr(self.workspace, 'folder_manager'):
                try:
                    self.workspace.folder_manager.delete_folder(folder_id, delete_documents=False)
                    self.refresh_document_tree()
                except Exception as e:
                    logger.error(f"Failed to delete folder: {e}", exc_info=True)
                    self.show_error("Error", f"Failed to delete folder:\n{e}")

    def _on_remove_from_folder(self, doc_id: int, item: QTreeWidgetItem):
        """Remove document from current folder"""
        parent_item = item.parent()
        if parent_item:
            folder_id = parent_item.data(0, Qt.UserRole + 1)
            logger.info(f"Removing document {doc_id} from folder {folder_id}")
            if hasattr(self.workspace, 'folder_manager'):
                try:
                    self.workspace.folder_manager.remove_document_from_folder(doc_id, folder_id)
                    self.refresh_document_tree()
                except Exception as e:
                    logger.error(f"Failed to remove document: {e}", exc_info=True)
                    self.show_error("Error", f"Failed to remove document:\n{e}")

    def _on_search(self):
        """Handle search action"""
        # Will be connected by app controller
        pass  # Dialog will be shown by main app

    def _on_citations(self):
        """Handle citation manager action"""
        # Will be connected by app controller
        pass

    def _on_references(self):
        """Handle reference manager action"""
        # Will be connected by app controller
        pass

    def _on_find_duplicates(self):
        """Handle find duplicates action"""
        # Will be connected by app controller
        pass

    def _on_watched_folders(self):
        """Handle watched folders action"""
        # Will be connected by app controller
        pass

    def _on_target_journals(self):
        """Handle target journals action"""
        # Will be connected by app controller
        pass

    def _on_web_recommendations(self):
        """Handle web recommendations action"""
        # Will be connected by app controller
        pass

    def _on_sync_status(self):
        """Handle sync status action"""
        # Will be connected by app controller
        pass

    def _on_check_integrity(self):
        """Handle check integrity action"""
        # Will be connected by app controller
        pass

    def _on_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        from ui.shortcuts_dialog import ShortcutsDialog
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def _on_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A PDF research assistant for organizing, annotating, and discovering academic papers.\n\n"
            "Built with PySide6 and PyMuPDF"
        )

    def _toggle_document_list(self):
        """Toggle document tree visibility"""
        self.document_tree.setVisible(not self.document_tree.isVisible())

    def _toggle_annotations_panel(self):
        """Toggle annotations panel visibility"""
        self.right_panel.setVisible(not self.right_panel.isVisible())

    def _on_theme_change(self, theme: str):
        """Handle theme change"""
        # Will be connected by app controller
        pass

    def _on_toggle_theme(self):
        """Toggle theme"""
        # Will be connected by app controller
        pass

    # Public methods

    def add_document_to_list(self, doc_id: int, title: str, **kwargs):
        """Add document to tree (deprecated - use refresh_document_tree)"""
        # This method is kept for backward compatibility
        # Just refresh the whole tree instead
        self.refresh_document_tree()

    def clear_document_list(self):
        """Clear document tree (deprecated - use refresh_document_tree)"""
        # This method is kept for backward compatibility
        self.document_tree.clear()

    def refresh_document_list(self, documents: list):
        """Refresh document list with new data (deprecated - use refresh_document_tree)"""
        # Keep for backward compatibility
        self.refresh_document_tree()

    def refresh_document_tree(self):
        """Refresh document tree with folders and documents"""
        self.document_tree.clear()

        if not hasattr(self.workspace, 'folder_manager'):
            return

        try:
            # Get all folders
            folders = self.workspace.folder_manager.get_all_folders()

            # Create folder items map
            folder_items = {}

            # First pass: Create all folder items
            for folder in folders:
                folder_id = folder['collection_id']
                folder_name = folder['name']

                item = QTreeWidgetItem()
                item.setText(0, f"📁 {folder_name}")
                item.setData(0, Qt.UserRole, 'folder')
                item.setData(0, Qt.UserRole + 1, folder_id)
                item.setExpanded(True)  # Expand by default

                folder_items[folder_id] = {
                    'item': item,
                    'parent_id': folder['parent_id']
                }

            # Second pass: Build hierarchy
            for folder_id, folder_data in folder_items.items():
                parent_id = folder_data['parent_id']
                item = folder_data['item']

                if parent_id is None:
                    # Root level folder
                    self.document_tree.addTopLevelItem(item)
                elif parent_id in folder_items:
                    # Child folder
                    parent_item = folder_items[parent_id]['item']
                    parent_item.addChild(item)

            # Third pass: Add documents to folders
            for folder_id, folder_data in folder_items.items():
                doc_ids = self.workspace.folder_manager.get_documents_in_folder(folder_id, recursive=False)

                for doc_id in doc_ids:
                    # Get document info
                    doc = self.workspace.document_dao.get_by_id(doc_id)
                    if doc:
                        title = doc.get('title', f'Document {doc_id}')
                        year = doc.get('year')

                        display_text = f"📄 {title}"
                        if year:
                            display_text += f" ({year})"

                        doc_item = QTreeWidgetItem()
                        doc_item.setText(0, display_text)
                        doc_item.setData(0, Qt.UserRole, 'document')
                        doc_item.setData(0, Qt.UserRole + 1, doc_id)

                        folder_data['item'].addChild(doc_item)

            # Add documents not in any folder to root level
            all_docs = self.workspace.document_dao.get_all()
            for doc in all_docs:
                doc_id = doc['doc_id']

                # Check if document is in any folder
                folders_with_doc = self.workspace.folder_manager.get_document_folders(doc_id)

                if not folders_with_doc:
                    # Not in any folder - add to root
                    title = doc.get('title', f'Document {doc_id}')
                    year = doc.get('year')

                    display_text = f"📄 {title}"
                    if year:
                        display_text += f" ({year})"

                    doc_item = QTreeWidgetItem()
                    doc_item.setText(0, display_text)
                    doc_item.setData(0, Qt.UserRole, 'document')
                    doc_item.setData(0, Qt.UserRole + 1, doc_id)

                    self.document_tree.addTopLevelItem(doc_item)

            logger.debug(f"Refreshed document tree with {len(folders)} folders and {len(all_docs)} documents")

        except Exception as e:
            logger.error(f"Failed to refresh document tree: {e}", exc_info=True)
            self.show_error("Error", f"Failed to refresh tree:\n{e}")

    def show_status_message(self, message: str, timeout: int = 3000):
        """Show message in status bar"""
        self.statusbar.showMessage(message, timeout)

    def show_error(self, title: str, message: str):
        """Show error dialog"""
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        """Show info dialog"""
        QMessageBox.information(self, title, message)

    def confirm(self, title: str, message: str) -> bool:
        """Show confirmation dialog"""
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    # Drag and drop handlers

    def _on_tree_drag_enter(self, event):
        """Handle drag enter event on tree widget"""
        # Accept both external files and internal tree items
        if event.mimeData().hasUrls() or event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def _on_tree_drag_move(self, event):
        """Handle drag move event on tree widget"""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def _on_tree_drop(self, event):
        """Handle drop event - both external PDFs and internal document movement"""
        # Check if it's an external file drop
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() == '.pdf':
                    logger.info(f"PDF dropped: {file_path}")
                    self.pdf_add_requested.emit(str(file_path))
                else:
                    logger.warning(f"Ignored non-PDF file: {file_path}")
            event.acceptProposedAction()

        # Check if it's an internal tree item drag
        elif event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            drop_indicator = self.document_tree.dropIndicatorPosition()
            target_item = self.document_tree.itemAt(event.pos())

            # Get dragged items
            dragged_items = self.document_tree.selectedItems()

            if not dragged_items or not target_item:
                event.ignore()
                return

            # Process each dragged item
            for dragged_item in dragged_items:
                dragged_type = dragged_item.data(0, Qt.UserRole)
                dragged_id = dragged_item.data(0, Qt.UserRole + 1)

                # Only allow dragging documents (not folders for now)
                if dragged_type != 'document':
                    continue

                target_type = target_item.data(0, Qt.UserRole)
                target_id = target_item.data(0, Qt.UserRole + 1)

                # Determine target folder
                target_folder_id = None

                if target_type == 'folder':
                    # Dropped on a folder
                    target_folder_id = target_id
                elif target_type == 'document':
                    # Dropped on a document - use parent folder
                    parent = target_item.parent()
                    if parent:
                        parent_type = parent.data(0, Qt.UserRole)
                        if parent_type == 'folder':
                            target_folder_id = parent.data(0, Qt.UserRole + 1)

                # Add document to target folder
                if target_folder_id is not None and hasattr(self.workspace, 'folder_manager'):
                    try:
                        self.workspace.folder_manager.add_document_to_folder(dragged_id, target_folder_id)
                        logger.info(f"Moved document {dragged_id} to folder {target_folder_id}")
                    except Exception as e:
                        logger.error(f"Failed to move document: {e}", exc_info=True)
                        self.show_error("Error", f"Failed to move document:\n{e}")

            # Refresh tree
            self.refresh_document_tree()
            event.acceptProposedAction()
        else:
            event.ignore()
