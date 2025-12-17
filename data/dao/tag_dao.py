"""
Data Access Object for tags and tag relationships
"""
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class TagDAO:
    """Handle database operations for tags"""

    def __init__(self, database):
        self.db = database

    def create(self, tag_name: str, parent_tag_id: int = None, color: str = '#3498db') -> int:
        """
        Create new tag.
        Returns: tag_id
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO tags (tag_name, parent_tag_id, color)
                VALUES (?, ?, ?)
            """, (tag_name, parent_tag_id, color))

            conn.commit()
            tag_id = cursor.lastrowid

            logger.info(f"Created tag: {tag_id} - {tag_name}")
            return tag_id

        except Exception as e:
            logger.error(f"Failed to create tag: {e}")
            raise

    def get_by_id(self, tag_id: int) -> Optional[Dict]:
        """Get tag by ID"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM tags WHERE tag_id = ?",
            (tag_id,)
        ).fetchone()

        return dict(result) if result else None

    def get_by_name(self, tag_name: str) -> Optional[Dict]:
        """Get tag by name"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM tags WHERE tag_name = ?",
            (tag_name,)
        ).fetchone()

        return dict(result) if result else None

    def get_or_create(self, tag_name: str, **kwargs) -> int:
        """Get tag ID if exists, otherwise create it"""
        existing = self.get_by_name(tag_name)
        if existing:
            return existing['tag_id']
        else:
            return self.create(tag_name, **kwargs)

    def get_all(self) -> List[Dict]:
        """Get all tags"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute(
            "SELECT * FROM tags ORDER BY tag_name"
        ).fetchall()

        return [dict(row) for row in results]

    def update(self, tag_id: int, **kwargs) -> None:
        """Update tag"""
        conn = self.db.connect()
        cursor = conn.cursor()

        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [tag_id]

        query = f"UPDATE tags SET {set_clause} WHERE tag_id = ?"

        cursor.execute(query, values)
        conn.commit()

        logger.info(f"Updated tag: {tag_id}")

    def delete(self, tag_id: int) -> None:
        """Delete tag (cascades to document_tags and annotation_tags)"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tags WHERE tag_id = ?", (tag_id,))
        conn.commit()

        logger.info(f"Deleted tag: {tag_id}")

    # Document-Tag relationships

    def tag_document(self, doc_id: int, tag_id: int) -> None:
        """Add tag to document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO document_tags (doc_id, tag_id)
                VALUES (?, ?)
            """, (doc_id, tag_id))

            conn.commit()
            logger.info(f"Tagged document {doc_id} with tag {tag_id}")

        except Exception as e:
            # Ignore duplicate constraint errors
            if "UNIQUE constraint" not in str(e):
                logger.error(f"Failed to tag document: {e}")
                raise

    def untag_document(self, doc_id: int, tag_id: int) -> None:
        """Remove tag from document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM document_tags
            WHERE doc_id = ? AND tag_id = ?
        """, (doc_id, tag_id))

        conn.commit()
        logger.info(f"Untagged document {doc_id} from tag {tag_id}")

    def get_document_tags(self, doc_id: int) -> List[Dict]:
        """Get all tags for a document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT t.*
            FROM tags t
            JOIN document_tags dt ON t.tag_id = dt.tag_id
            WHERE dt.doc_id = ?
            ORDER BY t.tag_name
        """, (doc_id,)).fetchall()

        return [dict(row) for row in results]

    def get_documents_by_tag(self, tag_id: int) -> List[int]:
        """Get all document IDs with this tag"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT doc_id
            FROM document_tags
            WHERE tag_id = ?
        """, (tag_id,)).fetchall()

        return [row[0] for row in results]

    # Annotation-Tag relationships

    def tag_annotation(self, annotation_id: int, tag_id: int) -> None:
        """Add tag to annotation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO annotation_tags (annotation_id, tag_id)
                VALUES (?, ?)
            """, (annotation_id, tag_id))

            conn.commit()
            logger.info(f"Tagged annotation {annotation_id} with tag {tag_id}")

        except Exception as e:
            if "UNIQUE constraint" not in str(e):
                logger.error(f"Failed to tag annotation: {e}")
                raise

    def untag_annotation(self, annotation_id: int, tag_id: int) -> None:
        """Remove tag from annotation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM annotation_tags
            WHERE annotation_id = ? AND tag_id = ?
        """, (annotation_id, tag_id))

        conn.commit()
        logger.info(f"Untagged annotation {annotation_id} from tag {tag_id}")

    def get_annotation_tags(self, annotation_id: int) -> List[Dict]:
        """Get all tags for an annotation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT t.*
            FROM tags t
            JOIN annotation_tags at ON t.tag_id = at.tag_id
            WHERE at.annotation_id = ?
            ORDER BY t.tag_name
        """, (annotation_id,)).fetchall()

        return [dict(row) for row in results]

    # Hierarchical tags (for Phase 2)

    def get_children(self, parent_tag_id: int) -> List[Dict]:
        """Get child tags"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT * FROM tags
            WHERE parent_tag_id = ?
            ORDER BY tag_name
        """, (parent_tag_id,)).fetchall()

        return [dict(row) for row in results]

    def get_tag_hierarchy(self) -> List[Dict]:
        """
        Get all tags organized in hierarchy.
        Returns root tags with nested children.
        """
        all_tags = self.get_all()

        # Build tree structure
        tag_dict = {tag['tag_id']: {**tag, 'children': []} for tag in all_tags}

        roots = []
        for tag in all_tags:
            if tag['parent_tag_id'] is None:
                roots.append(tag_dict[tag['tag_id']])
            else:
                parent = tag_dict.get(tag['parent_tag_id'])
                if parent:
                    parent['children'].append(tag_dict[tag['tag_id']])

        return roots
