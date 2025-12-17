"""
Folder Manager
Manages hierarchical folder structure (collections) for organizing documents
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FolderManager:
    """Manages folder/collection hierarchy for document organization"""

    def __init__(self, database):
        self.db = database

    def create_folder(
        self,
        name: str,
        parent_id: Optional[int] = None,
        description: str = "",
        color: str = "#3498db",
        icon: str = "folder"
    ) -> int:
        """
        Create a new folder

        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root level)
            description: Optional description
            color: Folder color
            icon: Folder icon

        Returns:
            folder_id (collection_id)
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            # Get max order_index for siblings
            if parent_id:
                cursor.execute(
                    "SELECT COALESCE(MAX(order_index), -1) FROM collections WHERE parent_id = ?",
                    (parent_id,)
                )
            else:
                cursor.execute(
                    "SELECT COALESCE(MAX(order_index), -1) FROM collections WHERE parent_id IS NULL"
                )

            max_order = cursor.fetchone()[0]
            new_order = max_order + 1

            cursor.execute("""
                INSERT INTO collections (name, parent_id, description, color, icon, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, parent_id, description, color, icon, new_order))

            folder_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created folder: {name} (ID: {folder_id}, Parent: {parent_id})")
            return folder_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create folder: {e}", exc_info=True)
            raise

    def get_all_folders(self) -> List[Dict]:
        """Get all folders with their hierarchy information"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                collection_id, name, parent_id, description,
                color, icon, order_index, created_at, modified_at
            FROM collections
            ORDER BY order_index ASC
        """)

        columns = [desc[0] for desc in cursor.description]
        folders = []

        for row in cursor.fetchall():
            folder = dict(zip(columns, row))
            folders.append(folder)

        return folders

    def get_folder_by_id(self, folder_id: int) -> Optional[Dict]:
        """Get a specific folder by ID"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                collection_id, name, parent_id, description,
                color, icon, order_index, created_at, modified_at
            FROM collections
            WHERE collection_id = ?
        """, (folder_id,))

        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_root_folders(self) -> List[Dict]:
        """Get all root-level folders"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                collection_id, name, parent_id, description,
                color, icon, order_index, created_at, modified_at
            FROM collections
            WHERE parent_id IS NULL
            ORDER BY order_index ASC
        """)

        columns = [desc[0] for desc in cursor.description]
        folders = []

        for row in cursor.fetchall():
            folder = dict(zip(columns, row))
            folders.append(folder)

        return folders

    def get_child_folders(self, parent_id: int) -> List[Dict]:
        """Get all child folders of a parent"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                collection_id, name, parent_id, description,
                color, icon, order_index, created_at, modified_at
            FROM collections
            WHERE parent_id = ?
            ORDER BY order_index ASC
        """, (parent_id,))

        columns = [desc[0] for desc in cursor.description]
        folders = []

        for row in cursor.fetchall():
            folder = dict(zip(columns, row))
            folders.append(folder)

        return folders

    def rename_folder(self, folder_id: int, new_name: str):
        """Rename a folder"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE collections
            SET name = ?, modified_at = CURRENT_TIMESTAMP
            WHERE collection_id = ?
        """, (new_name, folder_id))

        conn.commit()
        logger.info(f"Renamed folder {folder_id} to: {new_name}")

    def delete_folder(self, folder_id: int, delete_documents: bool = False):
        """
        Delete a folder

        Args:
            folder_id: Folder to delete
            delete_documents: If True, delete documents in folder. If False, just remove associations.
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            if delete_documents:
                # Get all documents in this folder
                cursor.execute("""
                    SELECT doc_id FROM document_collections WHERE collection_id = ?
                """, (folder_id,))
                doc_ids = [row[0] for row in cursor.fetchall()]

                # Delete documents
                for doc_id in doc_ids:
                    cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

            # Delete folder (CASCADE will handle child folders and document_collections)
            cursor.execute("DELETE FROM collections WHERE collection_id = ?", (folder_id,))

            conn.commit()
            logger.info(f"Deleted folder: {folder_id}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete folder: {e}", exc_info=True)
            raise

    def move_folder(self, folder_id: int, new_parent_id: Optional[int]):
        """Move a folder to a different parent"""
        conn = self.db.connect()
        cursor = conn.cursor()

        # Prevent circular references
        if new_parent_id:
            if self._is_descendant(folder_id, new_parent_id):
                raise ValueError("Cannot move folder into its own descendant")

        cursor.execute("""
            UPDATE collections
            SET parent_id = ?, modified_at = CURRENT_TIMESTAMP
            WHERE collection_id = ?
        """, (new_parent_id, folder_id))

        conn.commit()
        logger.info(f"Moved folder {folder_id} to parent: {new_parent_id}")

    def add_document_to_folder(self, doc_id: int, folder_id: int):
        """Add a document to a folder"""
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO document_collections (doc_id, collection_id)
                VALUES (?, ?)
            """, (doc_id, folder_id))

            conn.commit()
            logger.debug(f"Added document {doc_id} to folder {folder_id}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add document to folder: {e}")
            raise

    def remove_document_from_folder(self, doc_id: int, folder_id: int):
        """Remove a document from a folder"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM document_collections
            WHERE doc_id = ? AND collection_id = ?
        """, (doc_id, folder_id))

        conn.commit()
        logger.debug(f"Removed document {doc_id} from folder {folder_id}")

    def get_documents_in_folder(self, folder_id: int, recursive: bool = False) -> List[int]:
        """
        Get all document IDs in a folder

        Args:
            folder_id: Folder ID
            recursive: If True, include documents from subfolders

        Returns:
            List of document IDs
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        if recursive:
            # Get this folder and all descendants
            folder_ids = [folder_id] + self._get_all_descendants(folder_id)
            placeholders = ','.join('?' * len(folder_ids))

            cursor.execute(f"""
                SELECT DISTINCT doc_id
                FROM document_collections
                WHERE collection_id IN ({placeholders})
            """, folder_ids)
        else:
            cursor.execute("""
                SELECT doc_id FROM document_collections WHERE collection_id = ?
            """, (folder_id,))

        return [row[0] for row in cursor.fetchall()]

    def get_document_folders(self, doc_id: int) -> List[int]:
        """Get all folder IDs that contain a document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT collection_id FROM document_collections WHERE doc_id = ?
        """, (doc_id,))

        return [row[0] for row in cursor.fetchall()]

    def get_folder_count(self, folder_id: int) -> int:
        """Get number of documents in a folder (non-recursive)"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM document_collections WHERE collection_id = ?
        """, (folder_id,))

        return cursor.fetchone()[0]

    def _is_descendant(self, ancestor_id: int, potential_descendant_id: int) -> bool:
        """Check if a folder is a descendant of another"""
        descendants = self._get_all_descendants(ancestor_id)
        return potential_descendant_id in descendants

    def _get_all_descendants(self, folder_id: int) -> List[int]:
        """Get all descendant folder IDs recursively"""
        conn = self.db.connect()
        cursor = conn.cursor()

        descendants = []
        to_process = [folder_id]

        while to_process:
            current_id = to_process.pop(0)

            cursor.execute("""
                SELECT collection_id FROM collections WHERE parent_id = ?
            """, (current_id,))

            children = [row[0] for row in cursor.fetchall()]
            descendants.extend(children)
            to_process.extend(children)

        return descendants

    def get_folder_path(self, folder_id: int) -> str:
        """Get the full path of a folder (e.g., 'Parent / Child / Grandchild')"""
        conn = self.db.connect()
        cursor = conn.cursor()

        path_parts = []
        current_id = folder_id

        while current_id:
            cursor.execute("""
                SELECT name, parent_id FROM collections WHERE collection_id = ?
            """, (current_id,))

            row = cursor.fetchone()
            if not row:
                break

            path_parts.insert(0, row[0])
            current_id = row[1]

        return " / ".join(path_parts) if path_parts else ""
