"""
PDF file handling and processing using PyMuPDF
"""
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from io import BytesIO

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF is not installed. Run: pip install PyMuPDF")

logger = logging.getLogger(__name__)


class PDFHandler:
    """Wrapper for PyMuPDF operations"""

    def __init__(self):
        self._cache = {}  # Simple document cache

    def open_pdf(self, pdf_path: Path) -> fitz.Document:
        """Open PDF document"""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(str(pdf_path))
            logger.debug(f"Opened PDF: {pdf_path} ({doc.page_count} pages)")
            return doc
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            raise

    def get_page_count(self, pdf_path: Path) -> int:
        """Get number of pages in PDF"""
        with self.open_pdf(pdf_path) as doc:
            return doc.page_count

    def extract_text(self, pdf_path: Path, page_number: Optional[int] = None) -> str:
        """
        Extract text from PDF.
        If page_number is None, extract from all pages.
        """
        doc = self.open_pdf(pdf_path)

        try:
            if page_number is not None:
                # Extract from specific page
                if 0 <= page_number < doc.page_count:
                    page = doc[page_number]
                    return page.get_text()
                else:
                    raise ValueError(f"Invalid page number: {page_number}")
            else:
                # Extract from all pages
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                return "\n\n".join(text_parts)
        finally:
            doc.close()

    def render_page(self, pdf_path: Path, page_number: int, zoom: float = 1.0) -> bytes:
        """
        Render PDF page to image (PNG format).
        Returns image data as bytes.
        """
        doc = self.open_pdf(pdf_path)

        try:
            if not (0 <= page_number < doc.page_count):
                raise ValueError(f"Invalid page number: {page_number}")

            page = doc[page_number]

            # Create transformation matrix for zoom
            mat = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Convert to PNG bytes
            img_data = pix.tobytes("png")

            logger.debug(f"Rendered page {page_number} at {zoom}x zoom")
            return img_data

        finally:
            doc.close()

    def get_page_size(self, pdf_path: Path, page_number: int) -> Tuple[float, float]:
        """Get page dimensions (width, height) in points"""
        doc = self.open_pdf(pdf_path)

        try:
            if not (0 <= page_number < doc.page_count):
                raise ValueError(f"Invalid page number: {page_number}")

            page = doc[page_number]
            rect = page.rect
            return (rect.width, rect.height)

        finally:
            doc.close()

    def extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract PDF metadata (title, author, etc.)"""
        doc = self.open_pdf(pdf_path)

        try:
            metadata = doc.metadata

            # Clean up metadata
            cleaned = {
                "title": metadata.get("title", "").strip(),
                "author": metadata.get("author", "").strip(),
                "subject": metadata.get("subject", "").strip(),
                "keywords": metadata.get("keywords", "").strip(),
                "creator": metadata.get("creator", "").strip(),
                "producer": metadata.get("producer", "").strip(),
                "creationDate": metadata.get("creationDate", ""),
                "modDate": metadata.get("modDate", ""),
            }

            return cleaned

        finally:
            doc.close()

    def create_thumbnail(self, pdf_path: Path, max_size: int = 200) -> bytes:
        """Create thumbnail of first page"""
        doc = self.open_pdf(pdf_path)

        try:
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            page = doc[0]

            # Calculate zoom to fit max_size
            rect = page.rect
            zoom = min(max_size / rect.width, max_size / rect.height)

            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            return pix.tobytes("png")

        finally:
            doc.close()

    def search_text(self, pdf_path: Path, query: str, page_number: Optional[int] = None) -> List[Dict]:
        """
        Search for text in PDF.
        Returns list of matches with page number and bounding box.
        """
        doc = self.open_pdf(pdf_path)
        results = []

        try:
            pages = [doc[page_number]] if page_number is not None else doc

            for page in pages:
                # Search returns list of Rect objects
                matches = page.search_for(query)

                for rect in matches:
                    results.append({
                        "page": page.number,
                        "bbox": (rect.x0, rect.y0, rect.x1, rect.y1),
                        "text": query
                    })

            logger.debug(f"Found {len(results)} matches for '{query}'")
            return results

        finally:
            doc.close()

    def get_toc(self, pdf_path: Path) -> List[Dict]:
        """
        Extract table of contents (outline/bookmarks).
        Returns list of TOC entries with level, title, and page.
        """
        doc = self.open_pdf(pdf_path)

        try:
            toc = doc.get_toc()  # Returns list of [level, title, page]

            formatted_toc = []
            for entry in toc:
                formatted_toc.append({
                    "level": entry[0],
                    "title": entry[1],
                    "page": entry[2] - 1  # Convert to 0-based
                })

            return formatted_toc

        finally:
            doc.close()

    def close_all(self):
        """Close all cached documents"""
        self._cache.clear()
