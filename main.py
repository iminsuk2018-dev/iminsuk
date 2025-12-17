"""
PDF Research Assistant - Main Entry Point
"""
import sys
import logging
from pathlib import Path
import hashlib
import shutil

from qt_compat import QtWidgets, QtCore
from qt_compat import QT_API

QApplication = QtWidgets.QApplication
QMessageBox = QtWidgets.QMessageBox
QFileDialog = QtWidgets.QFileDialog
Qt = QtCore.Qt

# Import app modules
from config import config, DEFAULT_WORKSPACE_DIR, APP_NAME
from core.workspace import Workspace
from core.document_manager import DocumentManager
from core.annotation_manager import AnnotationManager
from core.tag_manager import TagManager
from core.search_engine import SearchEngine
from core.recommendation.engine import RecommendationEngine
from core.folder_manager import FolderManager
from data.dao.document_dao import DocumentDAO
from data.pdf_handler import PDFHandler
from utils.pdf_extractor import PDFMetadataExtractor
from utils.logger import setup_logging
from ui.main_window import MainWindow
from ui.pdf_viewer_enhanced import EnhancedPDFViewer
from ui.search_dialog import SearchDialog
from ui.sync_dialog import SyncDialog
from ui.citation_dialog import CitationDialog
from ui.duplicate_dialog import DuplicateDialog
from ui.reference_dialog import ReferenceDialog
from ui.watched_folders_dialog import WatchedFoldersDialog
from ui.target_journals_dialog import TargetJournalsDialog
from ui.web_recommendations_dialog import WebRecommendationsDialog
from ui.theme_manager import ThemeManager, Theme
from core.highlight_manager import HighlightManager
from core.bookmark_manager import BookmarkManager
from core.smart.tag_suggester import TagSuggester
from core.folder_watcher import FolderWatcher
from core.recommendation.auto_recommendation_manager import AutoRecommendationManager

logger = logging.getLogger(__name__)


class PDFResearchApp:
    """Main application controller"""

    def __init__(self, theme_manager: ThemeManager):
        # Setup logging
        setup_logging()

        self.theme_manager = theme_manager
        self.workspace: Workspace = None
        self.main_window: MainWindow = None
        self.pdf_viewer: EnhancedPDFViewer = None
        self.search_dialog: SearchDialog = None
        self.sync_dialog: SyncDialog = None
        self.citation_dialog: CitationDialog = None
        self.duplicate_dialog: DuplicateDialog = None
        self.reference_dialog: ReferenceDialog = None
        self.watched_folders_dialog: WatchedFoldersDialog = None
        self.target_journals_dialog: TargetJournalsDialog = None
        self.web_recommendations_dialog: WebRecommendationsDialog = None

        # Business logic managers
        self.document_manager: DocumentManager = None
        self.annotation_manager: AnnotationManager = None
        self.tag_manager: TagManager = None
        self.search_engine: SearchEngine = None
        self.recommendation_engine: RecommendationEngine = None
        self.highlight_manager: HighlightManager = None
        self.bookmark_manager: BookmarkManager = None
        self.folder_watcher: FolderWatcher = None
        self.auto_rec_manager: AutoRecommendationManager = None

        # DAOs
        self.document_dao: DocumentDAO = None

        # PDF handling
        self.pdf_handler: PDFHandler = PDFHandler()
        self.metadata_extractor: PDFMetadataExtractor = PDFMetadataExtractor()

    def initialize_workspace(self):
        """Initialize or select workspace"""
        workspace_path = DEFAULT_WORKSPACE_DIR

        # Create workspace if doesn't exist
        if not workspace_path.exists():
            reply = QMessageBox.question(
                None,
                "Create Workspace",
                f"Workspace not found at:\n{workspace_path}\n\nCreate new workspace?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                logger.info(f"Creating new workspace at: {workspace_path}")
            else:
                # Let user select custom path
                custom_path = QFileDialog.getExistingDirectory(
                    None,
                    "Select Workspace Directory",
                    str(Path.home())
                )

                if custom_path:
                    workspace_path = Path(custom_path)
                else:
                    return False

        # Initialize workspace
        self.workspace = Workspace(workspace_path)
        self.workspace.initialize()

        # Initialize DAOs and managers
        db = self.workspace.get_database()
        self.document_dao = DocumentDAO(db)
        self.document_manager = DocumentManager(self.workspace)
        self.annotation_manager = AnnotationManager(self.workspace)
        self.tag_manager = TagManager(self.workspace)
        self.search_engine = SearchEngine(self.workspace)
        self.recommendation_engine = RecommendationEngine(self.workspace)
        self.highlight_manager = HighlightManager(self.workspace)
        self.bookmark_manager = BookmarkManager(self.workspace)
        self.tag_suggester = TagSuggester(self.workspace)
        self.folder_watcher = FolderWatcher(self.workspace)
        self.auto_rec_manager = AutoRecommendationManager(self.workspace)

        # Initialize folder manager and add to workspace
        folder_manager = FolderManager(db)
        self.workspace.folder_manager = folder_manager
        self.workspace.document_dao = self.document_dao

        config.workspace_path = workspace_path

        logger.info(f"Workspace initialized: {workspace_path}")
        return True

    def setup_ui(self):
        """Setup main window and connections"""
        self.main_window = MainWindow(self.workspace)

        # Create Enhanced PDF viewer and replace placeholder
        self.pdf_viewer = EnhancedPDFViewer(self.workspace)

        # Replace placeholder in main window
        splitter = self.main_window.main_splitter
        splitter.replaceWidget(1, self.pdf_viewer)

        # Create search dialog
        self.search_dialog = SearchDialog(self.main_window)
        self.search_dialog.set_search_engine(self.search_engine)

        # Create sync dialog
        self.sync_dialog = SyncDialog(self.workspace, self.main_window)

        # Create citation dialog
        self.citation_dialog = CitationDialog(self.workspace, self.main_window)

        # Create duplicate dialog
        self.duplicate_dialog = DuplicateDialog(self.workspace, self.main_window)

        # Create reference dialog
        self.reference_dialog = ReferenceDialog(self.workspace, self.main_window)

        # Create watched folders dialog
        self.watched_folders_dialog = WatchedFoldersDialog(self.workspace, self.main_window)
        self.watched_folders_dialog.set_folder_watcher(self.folder_watcher)

        # Create target journals dialog
        self.target_journals_dialog = TargetJournalsDialog(self.auto_rec_manager, self.main_window)

        # Create web recommendations dialog
        self.web_recommendations_dialog = WebRecommendationsDialog(self.main_window)

        # Connect recommendations panel to manager
        self.main_window.recommendations_panel.set_manager(self.auto_rec_manager)

        # Connect collection panel to folder manager
        self.main_window.collection_panel.set_folder_manager(self.workspace.folder_manager)

        # Connect signals
        self._connect_signals()

        # Load existing documents
        self.refresh_document_list()

        # Load all tags
        self.refresh_all_tags()

        self.main_window.show()

        logger.info("UI initialized")

    def _connect_signals(self):
        """Connect all signals between components"""
        # Main window
        self.main_window.pdf_add_requested.connect(self.on_add_pdf)
        self.main_window.document_selected.connect(self.on_document_selected)

        # PDF viewer
        self.pdf_viewer.page_changed.connect(self.on_page_changed)

        # Annotation panel
        self.main_window.annotation_panel.annotation_added.connect(self.on_annotation_added)
        self.main_window.annotation_panel.annotation_updated.connect(self.on_annotation_updated)
        self.main_window.annotation_panel.annotation_deleted.connect(self.on_annotation_deleted)

        # Tag panel
        self.main_window.tag_panel.tag_added.connect(self.on_tag_added)
        self.main_window.tag_panel.tag_removed.connect(self.on_tag_removed)
        # Set tag suggester
        self.main_window.tag_panel.tag_suggester = self.tag_suggester

        # Collection panel
        self.main_window.collection_panel.collection_selected.connect(self.on_collection_selected)
        self.main_window.collection_panel.collection_created.connect(self.on_collection_created)
        self.main_window.collection_panel.collection_renamed.connect(self.on_collection_renamed)
        self.main_window.collection_panel.collection_deleted.connect(self.on_collection_deleted)
        self.main_window.collection_panel.collection_color_changed.connect(self.on_collection_color_changed)
        self.main_window.collection_panel.show_all_documents.connect(self.refresh_document_list)

        # Search dialog
        self.search_dialog.document_selected.connect(self.on_search_result_selected)

        # Connect search action
        def show_search():
            self.search_dialog.show()

        self.main_window._on_search = show_search

        # Connect sync actions
        def show_sync_status():
            self.sync_dialog.show()

        self.main_window._on_sync_status = show_sync_status

        def check_integrity():
            self.sync_dialog._on_check_integrity()

        self.main_window._on_check_integrity = check_integrity

        # Connect citation action
        def show_citations():
            self.citation_dialog.show()

        self.main_window._on_citations = show_citations

        # Connect reference manager action
        def show_references():
            # Set current document if one is selected
            if self.main_window.current_doc_id:
                doc = self.document_dao.get_document(self.main_window.current_doc_id)
                if doc:
                    self.reference_dialog.set_document(
                        doc['doc_id'],
                        doc.get('title', 'Untitled'),
                        doc['file_path']
                    )
            self.reference_dialog.show()

        self.main_window._on_references = show_references

        # Connect duplicate detection action
        def show_duplicates():
            self.duplicate_dialog.show()

        self.main_window._on_find_duplicates = show_duplicates

        # Connect duplicates merged signal to refresh
        self.duplicate_dialog.duplicates_merged.connect(self.refresh_document_list)

        # Connect watched folders action
        def show_watched_folders():
            self.watched_folders_dialog.show()

        self.main_window._on_watched_folders = show_watched_folders

        # Connect target journals action
        def show_target_journals():
            self.target_journals_dialog.show()

        self.main_window._on_target_journals = show_target_journals

        # Connect web recommendations action
        def show_web_recommendations():
            self.web_recommendations_dialog.show()

        self.main_window._on_web_recommendations = show_web_recommendations

        # Connect PDF viewer bookmark signal
        self.pdf_viewer.bookmark_toggled.connect(self.on_bookmark_toggled)

        # Connect theme actions
        def change_theme(theme_str: str):
            if theme_str == "light":
                self.theme_manager.set_theme(Theme.LIGHT)
            elif theme_str == "dark":
                self.theme_manager.set_theme(Theme.DARK)

        self.main_window._on_theme_change = change_theme

        def toggle_theme():
            self.theme_manager.toggle_theme()

        self.main_window._on_toggle_theme = toggle_theme

    def refresh_document_list(self):
        """Refresh document list from database"""
        documents = self.document_dao.get_all()
        self.main_window.refresh_document_list(documents)

        logger.debug(f"Loaded {len(documents)} documents")

    def refresh_all_tags(self):
        """Refresh all tags list"""
        tags_stats = self.tag_manager.get_tag_usage_stats()
        self.main_window.tag_panel.load_all_tags(tags_stats)

    def on_add_pdf(self, file_path: str):
        """Handle adding new PDF"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                self.main_window.show_error("Error", "File not found")
                return

            self.main_window.show_status_message("Adding PDF...")

            # Compute file hash
            file_hash = self._compute_file_hash(file_path)

            # Check for duplicates
            existing = self.document_dao.get_by_hash(file_hash)
            if existing:
                self.main_window.show_info(
                    "Duplicate",
                    f"This PDF is already in your library:\n{existing['title'] or 'Untitled'}"
                )
                return

            # Copy PDF to workspace
            dest_path = self.workspace.pdf_dir / file_path.name
            counter = 1
            while dest_path.exists():
                dest_path = self.workspace.pdf_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                counter += 1

            shutil.copy2(file_path, dest_path)

            # Get relative path
            relative_path = self.workspace.get_relative_path(dest_path)

            # Extract metadata
            logger.info("Extracting metadata...")
            metadata = self.metadata_extractor.extract_all_metadata(dest_path)

            # Get page count
            page_count = self.pdf_handler.get_page_count(dest_path)

            # Get file size
            file_size = dest_path.stat().st_size

            # Create document record
            doc_id = self.document_dao.create(
                file_path=relative_path,
                file_hash=file_hash,
                title=metadata.get('title') or file_path.stem,
                authors=str(metadata.get('authors')) if metadata.get('authors') else None,
                abstract=metadata.get('abstract'),
                year=metadata.get('year'),
                doi=metadata.get('doi'),
                page_count=page_count,
                file_size=file_size
            )

            # Update search index
            self._index_document(doc_id, metadata)

            # Add to UI
            self.main_window.add_document_to_list(
                doc_id,
                metadata.get('title') or file_path.stem,
                year=metadata.get('year')
            )

            self.main_window.show_status_message(f"Added: {file_path.name}", 5000)

            logger.info(f"Successfully added PDF: {doc_id}")

        except Exception as e:
            logger.error(f"Failed to add PDF: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to add PDF:\n{str(e)}")

    def on_document_selected(self, doc_id: int):
        """Handle document selection"""
        try:
            # Get document from database
            doc = self.document_dao.get_by_id(doc_id)

            if not doc:
                logger.error(f"Document not found: {doc_id}")
                return

            # Get absolute path
            pdf_path = self.workspace.get_absolute_path(doc['file_path'])

            if not pdf_path.exists():
                self.main_window.show_error(
                    "File Not Found",
                    f"PDF file not found:\n{pdf_path}\n\nThe file may have been moved or deleted."
                )
                return

            # Load PDF in viewer (Enhanced PDF Viewer requires doc_id)
            self.pdf_viewer.load_pdf(pdf_path, doc_id)

            # Update bookmark button state
            has_bookmark = self.bookmark_manager.has_bookmark(doc_id, 0)
            self.pdf_viewer.bookmark_button.setChecked(has_bookmark)

            # Load annotations
            annotations = self.annotation_manager.get_document_annotations(doc_id)
            self.main_window.annotation_panel.set_document(doc_id, doc['title'] or 'Untitled')
            self.main_window.annotation_panel.load_annotations(annotations)

            # Load tags
            tags = self.tag_manager.get_document_tags(doc_id)
            self.main_window.tag_panel.set_document(doc_id, doc['title'] or 'Untitled', str(pdf_path))
            self.main_window.tag_panel.load_document_tags(tags)

            self.main_window.show_status_message(f"Loaded: {doc['title'] or 'Untitled'}")

            logger.info(f"Loaded document: {doc_id}")

        except Exception as e:
            logger.error(f"Failed to load document: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to load PDF:\n{str(e)}")

    def on_page_changed(self, page_number: int):
        """Handle page change in PDF viewer"""
        self.main_window.annotation_panel.set_page(page_number)

    def on_annotation_added(self, doc_id: int, page_number: int, content: str):
        """Handle annotation addition"""
        try:
            annotation_id = self.annotation_manager.add_annotation(doc_id, page_number, content)

            # Refresh annotations list
            annotations = self.annotation_manager.get_document_annotations(doc_id)
            self.main_window.annotation_panel.load_annotations(annotations)

            self.main_window.show_status_message("Note added", 3000)

            logger.info(f"Added annotation: {annotation_id}")

        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            self.main_window.show_error("Error", f"Failed to add note:\n{str(e)}")

    def on_annotation_updated(self, annotation_id: int, content: str):
        """Handle annotation update"""
        try:
            self.annotation_manager.update_annotation(annotation_id, content)

            # Refresh annotations list
            annotation = self.annotation_manager.get_annotation(annotation_id)
            if annotation:
                annotations = self.annotation_manager.get_document_annotations(annotation['doc_id'])
                self.main_window.annotation_panel.load_annotations(annotations)

            self.main_window.show_status_message("Note updated", 3000)

            logger.info(f"Updated annotation: {annotation_id}")

        except Exception as e:
            logger.error(f"Failed to update annotation: {e}")
            self.main_window.show_error("Error", f"Failed to update note:\n{str(e)}")

    def on_annotation_deleted(self, annotation_id: int):
        """Handle annotation deletion"""
        try:
            annotation = self.annotation_manager.get_annotation(annotation_id)
            if annotation:
                doc_id = annotation['doc_id']
                self.annotation_manager.delete_annotation(annotation_id)

                # Refresh annotations list
                annotations = self.annotation_manager.get_document_annotations(doc_id)
                self.main_window.annotation_panel.load_annotations(annotations)

                self.main_window.show_status_message("Note deleted", 3000)

                logger.info(f"Deleted annotation: {annotation_id}")

        except Exception as e:
            logger.error(f"Failed to delete annotation: {e}")
            self.main_window.show_error("Error", f"Failed to delete note:\n{str(e)}")

    def on_tag_added(self, doc_id: int, tag_name: str):
        """Handle tag addition to document"""
        try:
            self.tag_manager.tag_document(doc_id, tag_name)

            # Refresh tag lists
            tags = self.tag_manager.get_document_tags(doc_id)
            self.main_window.tag_panel.load_document_tags(tags)

            self.refresh_all_tags()

            self.main_window.show_status_message(f"Tagged with '{tag_name}'", 3000)

            logger.info(f"Tagged document {doc_id} with '{tag_name}'")

        except Exception as e:
            logger.error(f"Failed to add tag: {e}")
            self.main_window.show_error("Error", f"Failed to add tag:\n{str(e)}")

    def on_tag_removed(self, doc_id: int, tag_id: int):
        """Handle tag removal from document"""
        try:
            self.tag_manager.untag_document(doc_id, tag_id)

            # Refresh tag lists
            tags = self.tag_manager.get_document_tags(doc_id)
            self.main_window.tag_panel.load_document_tags(tags)

            self.refresh_all_tags()

            self.main_window.show_status_message("Tag removed", 3000)

            logger.info(f"Removed tag {tag_id} from document {doc_id}")

        except Exception as e:
            logger.error(f"Failed to remove tag: {e}")
            self.main_window.show_error("Error", f"Failed to remove tag:\n{str(e)}")

    def on_search_result_selected(self, doc_id: int):
        """Handle search result selection"""
        # Find and select document in tree
        def find_document_in_tree(parent_item, target_doc_id):
            """Recursively search for document in tree"""
            # Check root level items if no parent
            if parent_item is None:
                for i in range(self.main_window.document_tree.topLevelItemCount()):
                    item = self.main_window.document_tree.topLevelItem(i)
                    if item.data(0, Qt.UserRole) == 'document' and item.data(0, Qt.UserRole + 1) == target_doc_id:
                        return item
                    # Check children
                    found = find_document_in_tree(item, target_doc_id)
                    if found:
                        return found
            else:
                # Check children of parent
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    if child.data(0, Qt.UserRole) == 'document' and child.data(0, Qt.UserRole + 1) == target_doc_id:
                        return child
                    # Check descendants
                    found = find_document_in_tree(child, target_doc_id)
                    if found:
                        return found
            return None

        found_item = find_document_in_tree(None, doc_id)
        if found_item:
            self.main_window.document_tree.setCurrentItem(found_item)
            self.main_window.document_tree.scrollToItem(found_item)

    def on_bookmark_toggled(self, page_number: int, is_bookmarked: bool):
        """Handle bookmark toggle"""
        if not self.pdf_viewer.current_doc_id:
            return

        try:
            if is_bookmarked:
                # Add bookmark
                self.bookmark_manager.add_bookmark(
                    self.pdf_viewer.current_doc_id,
                    page_number
                )
                logger.info(f"Added bookmark on page {page_number + 1}")
                self.main_window.show_status_message(f"Bookmarked page {page_number + 1}", 2000)
            else:
                # Remove bookmark
                bookmark = self.bookmark_manager.get_bookmark_on_page(
                    self.pdf_viewer.current_doc_id,
                    page_number
                )
                if bookmark:
                    self.bookmark_manager.delete_bookmark(bookmark['bookmark_id'])
                    logger.info(f"Removed bookmark from page {page_number + 1}")
                    self.main_window.show_status_message(f"Removed bookmark from page {page_number + 1}", 2000)

        except Exception as e:
            logger.error(f"Failed to toggle bookmark: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to toggle bookmark:\n{str(e)}")

    def on_collection_selected(self, collection_id: int):
        """Handle collection selection - filter documents"""
        try:
            # Get documents in this collection
            doc_ids = self.workspace.folder_manager.get_documents_in_folder(collection_id, recursive=False)

            # Get document details
            documents = []
            for doc_id in doc_ids:
                doc = self.document_dao.get_by_id(doc_id)
                if doc:
                    documents.append(doc)

            # Refresh document list with filtered documents
            self.main_window.refresh_document_list(documents)

            # Get collection name
            collection = self.workspace.folder_manager.get_folder_by_id(collection_id)
            if collection:
                self.main_window.show_status_message(f"Showing collection: {collection['name']}", 3000)

            logger.info(f"Selected collection {collection_id}: {len(documents)} documents")

        except Exception as e:
            logger.error(f"Failed to filter by collection: {e}", exc_info=True)

    def on_collection_created(self, name: str, parent_id):
        """Handle collection creation"""
        try:
            collection_id = self.workspace.folder_manager.create_folder(name, parent_id)

            # Refresh collection panel
            self.main_window.collection_panel.refresh()

            self.main_window.show_status_message(f"Created collection: {name}", 3000)
            logger.info(f"Created collection: {name} (ID: {collection_id})")

        except Exception as e:
            logger.error(f"Failed to create collection: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to create collection:\n{str(e)}")

    def on_collection_renamed(self, collection_id: int, new_name: str):
        """Handle collection rename"""
        try:
            self.workspace.folder_manager.rename_folder(collection_id, new_name)

            # Refresh collection panel
            self.main_window.collection_panel.refresh()

            self.main_window.show_status_message(f"Renamed to: {new_name}", 3000)
            logger.info(f"Renamed collection {collection_id} to: {new_name}")

        except Exception as e:
            logger.error(f"Failed to rename collection: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to rename collection:\n{str(e)}")

    def on_collection_deleted(self, collection_id: int):
        """Handle collection deletion"""
        try:
            # TODO: Ask user if they want to delete documents or keep them
            self.workspace.folder_manager.delete_folder(collection_id, delete_documents=False)

            # Refresh collection panel
            self.main_window.collection_panel.refresh()

            # Refresh document list to show all documents
            self.refresh_document_list()

            self.main_window.show_status_message("Collection deleted", 3000)
            logger.info(f"Deleted collection {collection_id}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}", exc_info=True)
            self.main_window.show_error("Error", f"Failed to delete collection:\n{str(e)}")

    def on_collection_color_changed(self, collection_id: int, color: str):
        """Handle collection color change"""
        try:
            # Update color in database
            db = self.workspace.get_database()
            conn = db.connect()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE collections
                SET color = ?, modified_at = CURRENT_TIMESTAMP
                WHERE collection_id = ?
            """, (color, collection_id))

            conn.commit()

            # Refresh collection panel
            self.main_window.collection_panel.refresh()

            logger.info(f"Changed collection {collection_id} color to {color}")

        except Exception as e:
            logger.error(f"Failed to change collection color: {e}", exc_info=True)

    def _index_document(self, doc_id: int, metadata: dict):
        """Add document to search index"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        # Index title
        if metadata.get('title'):
            cursor.execute("""
                INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                VALUES ('title', ?, ?, NULL, NULL)
            """, (metadata['title'], doc_id))

        # Index abstract
        if metadata.get('abstract'):
            cursor.execute("""
                INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                VALUES ('abstract', ?, ?, NULL, NULL)
            """, (metadata['abstract'], doc_id))

        conn.commit()

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def run(self):
        """Run the application"""
        # Initialize workspace
        if not self.initialize_workspace():
            logger.error("Failed to initialize workspace")
            return 1

        # Setup UI
        self.setup_ui()

        # Show welcome dialog on first run
        from ui.welcome_dialog import WelcomeDialog
        if WelcomeDialog.should_show():
            welcome = WelcomeDialog(self.main_window)
            welcome.exec()

        return 0

    def cleanup(self):
        """Cleanup on exit"""
        if self.workspace:
            self.workspace.close()

        logger.info("Application closed")


def main():
    """Main entry point"""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Note: High DPI is enabled by default in Qt6

    # Create theme manager
    theme_manager = ThemeManager(app)

    # Apply saved theme
    theme_manager.set_theme(theme_manager.get_current_theme())

    # Create app controller with theme manager
    pdf_app = PDFResearchApp(theme_manager)

    # Run
    exit_code = pdf_app.run()

    if exit_code == 0:
        # Start event loop
        exit_code = app.exec()

    # Cleanup
    pdf_app.cleanup()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
