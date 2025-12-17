"""
Data Access Object for annotations table
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class AnnotationDAO:
    """Handle database operations for annotations"""

    def __init__(self, database):
        self.db = database

    def create(self, doc_id: int, page_number: int, content: str, **kwargs) -> int:
        """
        Create new annotation.
        Returns: annotation_id
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO annotations (doc_id, page_number, content, position_data, color, annotation_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            page_number,
            content,
            kwargs.get('position_data'),
            kwargs.get('color', '#FFFF00'),
            kwargs.get('annotation_type', 'note')
        ))

        conn.commit()
        annotation_id = cursor.lastrowid

        logger.info(f"Created annotation: {annotation_id} for doc {doc_id}, page {page_number}")
        return annotation_id

    def get_by_id(self, annotation_id: int) -> Optional[Dict]:
        """Get annotation by ID"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM annotations WHERE annotation_id = ?",
            (annotation_id,)
        ).fetchone()

        return dict(result) if result else None

    def get_by_document(self, doc_id: int) -> List[Dict]:
        """Get all annotations for a document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute(
            "SELECT * FROM annotations WHERE doc_id = ? ORDER BY page_number, created_at",
            (doc_id,)
        ).fetchall()

        return [dict(row) for row in results]

    def get_by_page(self, doc_id: int, page_number: int) -> List[Dict]:
        """Get annotations for a specific page"""
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute(
            "SELECT * FROM annotations WHERE doc_id = ? AND page_number = ? ORDER BY created_at",
            (doc_id, page_number)
        ).fetchall()

        return [dict(row) for row in results]

    def update(self, annotation_id: int, **kwargs) -> None:
        """Update annotation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        kwargs['modified_at'] = datetime.now().isoformat()

        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [annotation_id]

        query = f"UPDATE annotations SET {set_clause} WHERE annotation_id = ?"

        cursor.execute(query, values)
        conn.commit()

        logger.info(f"Updated annotation: {annotation_id}")

    def delete(self, annotation_id: int) -> None:
        """Delete annotation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM annotations WHERE annotation_id = ?", (annotation_id,))
        conn.commit()

        logger.info(f"Deleted annotation: {annotation_id}")

    def count_by_document(self, doc_id: int) -> int:
        """Get annotation count for document"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT COUNT(*) FROM annotations WHERE doc_id = ?",
            (doc_id,)
        ).fetchone()

        return result[0] if result else 0
