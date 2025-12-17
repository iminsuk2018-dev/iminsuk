"""
Highlight Manager
Handles PDF highlights/marks
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Highlight:
    """Represents a highlight on a PDF page"""
    highlight_id: Optional[int]
    doc_id: int
    page_number: int
    x: float
    y: float
    width: float
    height: float
    color: str = '#FFFF00'
    opacity: float = 0.3
    highlight_type: str = 'rectangle'
    note: Optional[str] = None


class HighlightManager:
    """Manages PDF highlights"""

    def __init__(self, workspace):
        self.workspace = workspace

    def add_highlight(
        self,
        doc_id: int,
        page_number: int,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = '#FFFF00',
        opacity: float = 0.3,
        highlight_type: str = 'rectangle',
        note: Optional[str] = None
    ) -> int:
        """
        Add a new highlight.

        Args:
            doc_id: Document ID
            page_number: Page number (0-based)
            x, y: Top-left corner coordinates (normalized 0-1)
            width, height: Size (normalized 0-1)
            color: Highlight color
            opacity: Opacity (0-1)
            highlight_type: Type ('rectangle', 'underline', 'strikeout')
            note: Optional note text

        Returns:
            highlight_id
        """
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO highlights (
                    doc_id, page_number, x, y, width, height,
                    color, opacity, highlight_type, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id, page_number, x, y, width, height,
                color, opacity, highlight_type, note
            ))

            highlight_id = cursor.lastrowid

        logger.info(f"Added highlight {highlight_id} on page {page_number}")
        return highlight_id

    def get_page_highlights(self, doc_id: int, page_number: int) -> List[Highlight]:
        """Get all highlights for a specific page"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        rows = cursor.execute("""
            SELECT * FROM highlights
            WHERE doc_id = ? AND page_number = ?
            ORDER BY created_at
        """, (doc_id, page_number)).fetchall()

        highlights = []
        for row in rows:
            highlight = Highlight(
                highlight_id=row['highlight_id'],
                doc_id=row['doc_id'],
                page_number=row['page_number'],
                x=row['x'],
                y=row['y'],
                width=row['width'],
                height=row['height'],
                color=row['color'],
                opacity=row['opacity'],
                highlight_type=row['highlight_type'],
                note=row['note']
            )
            highlights.append(highlight)

        return highlights

    def get_document_highlights(self, doc_id: int) -> List[Highlight]:
        """Get all highlights for a document"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        rows = cursor.execute("""
            SELECT * FROM highlights
            WHERE doc_id = ?
            ORDER BY page_number, created_at
        """, (doc_id,)).fetchall()

        highlights = []
        for row in rows:
            highlight = Highlight(
                highlight_id=row['highlight_id'],
                doc_id=row['doc_id'],
                page_number=row['page_number'],
                x=row['x'],
                y=row['y'],
                width=row['width'],
                height=row['height'],
                color=row['color'],
                opacity=row['opacity'],
                highlight_type=row['highlight_type'],
                note=row['note']
            )
            highlights.append(highlight)

        return highlights

    def update_highlight(
        self,
        highlight_id: int,
        **kwargs
    ) -> bool:
        """
        Update highlight properties.

        Allowed kwargs: color, opacity, note
        """
        allowed_fields = ['color', 'opacity', 'note']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            logger.warning("No valid fields to update")
            return False

        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [highlight_id]

            cursor.execute(f"""
                UPDATE highlights
                SET {set_clause}
                WHERE highlight_id = ?
            """, values)

        logger.info(f"Updated highlight {highlight_id}")
        return True

    def delete_highlight(self, highlight_id: int) -> bool:
        """Delete a highlight"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM highlights WHERE highlight_id = ?", (highlight_id,))

        logger.info(f"Deleted highlight {highlight_id}")
        return True

    def delete_page_highlights(self, doc_id: int, page_number: int) -> int:
        """Delete all highlights on a page. Returns count deleted."""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM highlights
                WHERE doc_id = ? AND page_number = ?
            """, (doc_id, page_number))
            count = cursor.rowcount

        logger.info(f"Deleted {count} highlights from page {page_number}")
        return count

    def get_highlight_colors(self) -> List[Dict]:
        """Get predefined highlight colors"""
        return [
            {'name': 'Yellow', 'color': '#FFFF00'},
            {'name': 'Green', 'color': '#00FF00'},
            {'name': 'Blue', 'color': '#00BFFF'},
            {'name': 'Pink', 'color': '#FF69B4'},
            {'name': 'Orange', 'color': '#FFA500'},
            {'name': 'Red', 'color': '#FF0000'},
        ]
