"""
Data Access Object for documents table
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentDAO:
    """Handle database operations for documents"""

    def __init__(self, database):
        self.db = database

    def create(self, **kwargs) -> int:
        """
        Create new document record.
        Returns: doc_id
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        fields = [
            'file_path', 'file_hash', 'title', 'authors', 'abstract',
            'year', 'journal', 'doi', 'page_count', 'file_size', 'metadata'
        ]

        # Filter only provided fields
        data = {k: v for k, v in kwargs.items() if k in fields}

        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' for _ in data)

        query = f"""
            INSERT INTO documents ({columns})
            VALUES ({placeholders})
        """

        cursor.execute(query, list(data.values()))
        conn.commit()

        doc_id = cursor.lastrowid
        logger.info(f"Created document: {doc_id}")
        return doc_id

    def get_by_id(self, doc_id: int) -> Optional[Dict]:
        """Get document by ID"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM documents WHERE doc_id = ?",
            (doc_id,)
        ).fetchone()

        return dict(result) if result else None

    def get_by_path(self, file_path: str) -> Optional[Dict]:
        """Get document by file path"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM documents WHERE file_path = ?",
            (file_path,)
        ).fetchone()

        return dict(result) if result else None

    def get_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Get document by file hash (check for duplicates)"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT * FROM documents WHERE file_hash = ?",
            (file_hash,)
        ).fetchone()

        return dict(result) if result else None

    def get_all(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Get all documents with optional pagination"""
        conn = self.db.connect()
        cursor = conn.cursor()

        query = "SELECT * FROM documents ORDER BY added_at DESC"

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        results = cursor.execute(query).fetchall()
        return [dict(row) for row in results]

    def update(self, doc_id: int, **kwargs) -> None:
        """Update document fields"""
        conn = self.db.connect()
        cursor = conn.cursor()

        # Add modified timestamp
        kwargs['modified_at'] = datetime.now().isoformat()

        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [doc_id]

        query = f"UPDATE documents SET {set_clause} WHERE doc_id = ?"

        cursor.execute(query, values)
        conn.commit()

        logger.info(f"Updated document: {doc_id}")

    def delete(self, doc_id: int) -> None:
        """Delete document (cascades to annotations and tags)"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()

        logger.info(f"Deleted document: {doc_id}")

    def search(self, **filters) -> List[Dict]:
        """
        Search documents with filters.
        Supported filters: title, year, journal, tags
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        conditions = []
        values = []

        if 'title' in filters:
            conditions.append("title LIKE ?")
            values.append(f"%{filters['title']}%")

        if 'year' in filters:
            conditions.append("year = ?")
            values.append(filters['year'])

        if 'journal' in filters:
            conditions.append("journal LIKE ?")
            values.append(f"%{filters['journal']}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"SELECT * FROM documents WHERE {where_clause} ORDER BY added_at DESC"

        results = cursor.execute(query, values).fetchall()
        return [dict(row) for row in results]

    def count(self) -> int:
        """Get total document count"""
        conn = self.db.connect()
        cursor = conn.cursor()

        result = cursor.execute("SELECT COUNT(*) FROM documents").fetchone()
        return result[0] if result else 0
