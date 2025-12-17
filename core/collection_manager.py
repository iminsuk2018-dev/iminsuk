"""
Collection Manager
Manages document collections (folders/groups)
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manages document collections (folders)"""

    def __init__(self, workspace):
        self.workspace = workspace

    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        color: str = '#3498db',
        icon: str = 'folder'
    ) -> int:
        """
        Create a new collection.

        Args:
            name: Collection name
            description: Optional description
            parent_id: Parent collection ID (for nested collections)
            color: Collection color
            icon: Icon identifier

        Returns:
            collection_id
        """
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            # Get max order_index for this level
            if parent_id:
                max_order = cursor.execute("""
                    SELECT MAX(order_index) FROM collections WHERE parent_id = ?
                """, (parent_id,)).fetchone()[0]
            else:
                max_order = cursor.execute("""
                    SELECT MAX(order_index) FROM collections WHERE parent_id IS NULL
                """).fetchone()[0]

            order_index = (max_order or 0) + 1

            cursor.execute("""
                INSERT INTO collections (name, description, parent_id, color, icon, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, parent_id, color, icon, order_index))

            collection_id = cursor.lastrowid

        logger.info(f"Created collection: {name} (ID: {collection_id})")
        return collection_id

    def get_collection(self, collection_id: int) -> Optional[Dict]:
        """Get collection by ID"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        row = cursor.execute("""
            SELECT * FROM collections WHERE collection_id = ?
        """, (collection_id,)).fetchone()

        return dict(row) if row else None

    def get_all_collections(self, parent_id: Optional[int] = None) -> List[Dict]:
        """
        Get all collections, optionally filtered by parent.

        Args:
            parent_id: If None, returns root collections. If provided, returns children.
        """
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        if parent_id is None:
            rows = cursor.execute("""
                SELECT * FROM collections
                WHERE parent_id IS NULL
                ORDER BY order_index, name
            """).fetchall()
        else:
            rows = cursor.execute("""
                SELECT * FROM collections
                WHERE parent_id = ?
                ORDER BY order_index, name
            """, (parent_id,)).fetchall()

        return [dict(row) for row in rows]

    def get_collection_tree(self) -> List[Dict]:
        """Get collection hierarchy as a tree"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        # Get all collections
        rows = cursor.execute("""
            SELECT * FROM collections ORDER BY parent_id, order_index, name
        """).fetchall()

        collections = [dict(row) for row in rows]

        # Build tree structure
        collection_map = {c['collection_id']: c for c in collections}

        for collection in collections:
            collection['children'] = []

        root_collections = []

        for collection in collections:
            parent_id = collection['parent_id']
            if parent_id is None:
                root_collections.append(collection)
            elif parent_id in collection_map:
                collection_map[parent_id]['children'].append(collection)

        return root_collections

    def update_collection(
        self,
        collection_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None
    ) -> bool:
        """Update collection properties"""
        updates = {}
        if name is not None:
            updates['name'] = name
        if description is not None:
            updates['description'] = description
        if color is not None:
            updates['color'] = color
        if icon is not None:
            updates['icon'] = icon

        if not updates:
            return False

        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            set_clause += ", modified_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [collection_id]

            cursor.execute(f"""
                UPDATE collections
                SET {set_clause}
                WHERE collection_id = ?
            """, values)

        logger.info(f"Updated collection {collection_id}")
        return True

    def delete_collection(self, collection_id: int, delete_documents: bool = False) -> bool:
        """
        Delete a collection.

        Args:
            collection_id: Collection to delete
            delete_documents: If True, also delete documents in collection.
                            If False, only remove association.
        """
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            if delete_documents:
                # Get all documents in this collection
                doc_ids = cursor.execute("""
                    SELECT doc_id FROM document_collections WHERE collection_id = ?
                """, (collection_id,)).fetchall()

                # Delete documents
                for (doc_id,) in doc_ids:
                    cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            else:
                # Just remove associations
                cursor.execute("""
                    DELETE FROM document_collections WHERE collection_id = ?
                """, (collection_id,))

            # Delete collection (CASCADE will handle children)
            cursor.execute("DELETE FROM collections WHERE collection_id = ?", (collection_id,))

        logger.info(f"Deleted collection {collection_id}")
        return True

    def add_document_to_collection(self, doc_id: int, collection_id: int) -> bool:
        """Add a document to a collection"""
        db = self.workspace.get_database()

        try:
            with db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO document_collections (doc_id, collection_id)
                    VALUES (?, ?)
                """, (doc_id, collection_id))

            logger.info(f"Added document {doc_id} to collection {collection_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add document to collection: {e}")
            return False

    def remove_document_from_collection(self, doc_id: int, collection_id: int) -> bool:
        """Remove a document from a collection"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM document_collections
                WHERE doc_id = ? AND collection_id = ?
            """, (doc_id, collection_id))

        logger.info(f"Removed document {doc_id} from collection {collection_id}")
        return True

    def get_document_collections(self, doc_id: int) -> List[Dict]:
        """Get all collections that contain this document"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        rows = cursor.execute("""
            SELECT c.* FROM collections c
            JOIN document_collections dc ON c.collection_id = dc.collection_id
            WHERE dc.doc_id = ?
            ORDER BY c.name
        """, (doc_id,)).fetchall()

        return [dict(row) for row in rows]

    def get_collection_documents(self, collection_id: int) -> List[Dict]:
        """Get all documents in a collection"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        rows = cursor.execute("""
            SELECT d.* FROM documents d
            JOIN document_collections dc ON d.doc_id = dc.doc_id
            WHERE dc.collection_id = ?
            ORDER BY d.title
        """, (collection_id,)).fetchall()

        return [dict(row) for row in rows]

    def get_collection_count(self, collection_id: int) -> int:
        """Get number of documents in a collection"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        count = cursor.execute("""
            SELECT COUNT(*) FROM document_collections WHERE collection_id = ?
        """, (collection_id,)).fetchone()[0]

        return count

    def move_collection(self, collection_id: int, new_parent_id: Optional[int]) -> bool:
        """Move collection to a different parent"""
        db = self.workspace.get_database()

        # Prevent circular references
        if new_parent_id is not None:
            if self._is_descendant(collection_id, new_parent_id):
                logger.warning("Cannot move collection: would create circular reference")
                return False

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE collections
                SET parent_id = ?, modified_at = CURRENT_TIMESTAMP
                WHERE collection_id = ?
            """, (new_parent_id, collection_id))

        logger.info(f"Moved collection {collection_id} to parent {new_parent_id}")
        return True

    def _is_descendant(self, ancestor_id: int, potential_descendant_id: int) -> bool:
        """Check if potential_descendant is a descendant of ancestor"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        current_id = potential_descendant_id
        while current_id is not None:
            if current_id == ancestor_id:
                return True

            row = cursor.execute("""
                SELECT parent_id FROM collections WHERE collection_id = ?
            """, (current_id,)).fetchone()

            current_id = row[0] if row and row[0] else None

        return False

    def reorder_collections(self, collection_ids: List[int]) -> bool:
        """
        Reorder collections by providing list of IDs in desired order.
        All collections must have the same parent.
        """
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            for index, collection_id in enumerate(collection_ids):
                cursor.execute("""
                    UPDATE collections
                    SET order_index = ?, modified_at = CURRENT_TIMESTAMP
                    WHERE collection_id = ?
                """, (index, collection_id))

        logger.info(f"Reordered {len(collection_ids)} collections")
        return True
