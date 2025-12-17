"""
Bookmark Manager
Handles PDF page bookmarks
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    """Represents a bookmark"""
    bookmark_id: Optional[int]
    doc_id: int
    page_number: int
    label: Optional[str] = None


class BookmarkManager:
    """Manages PDF bookmarks"""

    def __init__(self, workspace):
        self.workspace = workspace

    def add_bookmark(
        self,
        doc_id: int,
        page_number: int,
        label: Optional[str] = None
    ) -> int:
        """
        Add a bookmark to a page.

        Args:
            doc_id: Document ID
            page_number: Page number (0-based)
            label: Optional label

        Returns:
            bookmark_id
        """
        db = self.workspace.get_database()

        # Check if bookmark already exists
        existing = self.get_bookmark_on_page(doc_id, page_number)
        if existing:
            logger.warning(f"Bookmark already exists on page {page_number}")
            return existing['bookmark_id']

        with db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO bookmarks (doc_id, page_number, label)
                VALUES (?, ?, ?)
            """, (doc_id, page_number, label))

            bookmark_id = cursor.lastrowid

        logger.info(f"Added bookmark {bookmark_id} on page {page_number}")
        return bookmark_id

    def get_document_bookmarks(self, doc_id: int) -> List[Bookmark]:
        """Get all bookmarks for a document"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        rows = cursor.execute("""
            SELECT * FROM bookmarks
            WHERE doc_id = ?
            ORDER BY page_number
        """, (doc_id,)).fetchall()

        bookmarks = []
        for row in rows:
            bookmark = Bookmark(
                bookmark_id=row['bookmark_id'],
                doc_id=row['doc_id'],
                page_number=row['page_number'],
                label=row['label']
            )
            bookmarks.append(bookmark)

        return bookmarks

    def get_bookmark_on_page(self, doc_id: int, page_number: int) -> Optional[Dict]:
        """Check if a bookmark exists on a page"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        row = cursor.execute("""
            SELECT * FROM bookmarks
            WHERE doc_id = ? AND page_number = ?
        """, (doc_id, page_number)).fetchone()

        return dict(row) if row else None

    def update_bookmark_label(self, bookmark_id: int, label: str) -> bool:
        """Update bookmark label"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bookmarks
                SET label = ?
                WHERE bookmark_id = ?
            """, (label, bookmark_id))

        logger.info(f"Updated bookmark {bookmark_id} label")
        return True

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bookmarks WHERE bookmark_id = ?", (bookmark_id,))

        logger.info(f"Deleted bookmark {bookmark_id}")
        return True

    def toggle_bookmark(self, doc_id: int, page_number: int) -> bool:
        """
        Toggle bookmark on/off for a page.

        Returns True if bookmark was added, False if removed.
        """
        existing = self.get_bookmark_on_page(doc_id, page_number)

        if existing:
            self.delete_bookmark(existing['bookmark_id'])
            return False
        else:
            self.add_bookmark(doc_id, page_number)
            return True

    def has_bookmark(self, doc_id: int, page_number: int) -> bool:
        """Check if page has a bookmark"""
        return self.get_bookmark_on_page(doc_id, page_number) is not None
