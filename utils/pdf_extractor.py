"""
Advanced PDF metadata extraction utilities
Attempts to extract title, authors, abstract from PDF content
"""
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict

try:
    import fitz
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class PDFMetadataExtractor:
    """Extract academic metadata from PDF content"""

    def __init__(self):
        self.max_pages_to_scan = 3  # Scan first N pages for metadata

    def extract_title(self, pdf_path: Path) -> Optional[str]:
        """
        Attempt to extract title from PDF.
        Strategy:
        1. Check PDF metadata
        2. Find largest font text on first page
        3. Heuristic: first line that looks like a title
        """
        if fitz is None:
            logger.warning("PyMuPDF not available")
            return None

        try:
            doc = fitz.open(str(pdf_path))

            # Strategy 1: PDF metadata
            title = doc.metadata.get("title", "").strip()
            if title and len(title) > 5:
                doc.close()
                return title

            # Strategy 2: Largest font on first page
            if doc.page_count > 0:
                title = self._extract_title_from_first_page(doc[0])
                if title:
                    doc.close()
                    return title

            doc.close()
            return None

        except Exception as e:
            logger.error(f"Failed to extract title: {e}")
            return None

    def _extract_title_from_first_page(self, page: fitz.Page) -> Optional[str]:
        """Extract title by finding largest font text"""
        try:
            blocks = page.get_text("dict")["blocks"]

            max_size = 0
            title = ""

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        size = span.get("size", 0)
                        text = span.get("text", "").strip()

                        # Title is usually the largest font
                        if size > max_size and len(text) > 10:
                            max_size = size
                            title = text

            return title if title else None

        except Exception as e:
            logger.error(f"Error extracting title from page: {e}")
            return None

    def extract_authors(self, pdf_path: Path) -> Optional[List[str]]:
        """
        Attempt to extract authors.
        Returns list of author names if found.
        """
        if fitz is None:
            return None

        try:
            doc = fitz.open(str(pdf_path))

            # Check metadata first
            authors_str = doc.metadata.get("author", "").strip()
            doc.close()

            if authors_str:
                # Split by common separators
                authors = re.split(r'[,;]|\sand\s', authors_str)
                return [a.strip() for a in authors if a.strip()]

            # TODO: Extract from first page using patterns
            # This is complex and often unreliable for academic papers

            return None

        except Exception as e:
            logger.error(f"Failed to extract authors: {e}")
            return None

    def extract_abstract(self, pdf_path: Path) -> Optional[str]:
        """
        Attempt to extract abstract from PDF.
        Looks for section labeled "Abstract" or "ABSTRACT"
        """
        if fitz is None:
            return None

        try:
            doc = fitz.open(str(pdf_path))

            # Search first few pages
            for page_num in range(min(self.max_pages_to_scan, doc.page_count)):
                page = doc[page_num]
                text = page.get_text()

                # Find abstract section
                abstract = self._extract_abstract_from_text(text)
                if abstract:
                    doc.close()
                    return abstract

            doc.close()
            return None

        except Exception as e:
            logger.error(f"Failed to extract abstract: {e}")
            return None

    def _extract_abstract_from_text(self, text: str) -> Optional[str]:
        """Extract abstract using regex patterns"""

        # Pattern: "Abstract" followed by text until next section
        patterns = [
            r'(?:Abstract|ABSTRACT)\s*[:\-]?\s*\n(.*?)(?:\n\s*\n|\n(?:Keywords|KEYWORDS|Introduction|INTRODUCTION|1\.|I\.))',
            r'(?:Abstract|ABSTRACT)\s*[:\-]?\s+(.*?)(?:\n\s*\n)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()

                # Clean up
                abstract = re.sub(r'\s+', ' ', abstract)  # Normalize whitespace
                abstract = abstract[:2000]  # Limit length

                if len(abstract) > 50:  # Minimum length check
                    return abstract

        return None

    def extract_doi(self, pdf_path: Path) -> Optional[str]:
        """Extract DOI from PDF text"""
        if fitz is None:
            return None

        try:
            doc = fitz.open(str(pdf_path))

            # Search first page
            if doc.page_count > 0:
                text = doc[0].get_text()
                doi = self._find_doi_in_text(text)
                doc.close()
                return doi

            doc.close()
            return None

        except Exception as e:
            logger.error(f"Failed to extract DOI: {e}")
            return None

    def _find_doi_in_text(self, text: str) -> Optional[str]:
        """Find DOI using regex"""
        # DOI pattern: 10.xxxx/xxxxx
        pattern = r'10\.\d{4,}/[^\s]+'
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None

    def extract_year(self, pdf_path: Path) -> Optional[int]:
        """Extract publication year"""
        if fitz is None:
            return None

        try:
            doc = fitz.open(str(pdf_path))

            # Check creation date in metadata
            creation_date = doc.metadata.get("creationDate", "")
            year_match = re.search(r'(\d{4})', creation_date)
            if year_match:
                year = int(year_match.group(1))
                if 1900 <= year <= 2100:
                    doc.close()
                    return year

            # Search first page for year pattern
            if doc.page_count > 0:
                text = doc[0].get_text()

                # Look for patterns like "2024", "(2024)", "Published: 2024"
                year_patterns = [
                    r'\((\d{4})\)',
                    r'(?:Published|Copyright|©)\s*:?\s*(\d{4})',
                    r'\b(20\d{2})\b'
                ]

                for pattern in year_patterns:
                    match = re.search(pattern, text)
                    if match:
                        year = int(match.group(1))
                        if 2000 <= year <= 2100:
                            doc.close()
                            return year

            doc.close()
            return None

        except Exception as e:
            logger.error(f"Failed to extract year: {e}")
            return None

    def extract_all_metadata(self, pdf_path: Path) -> Dict:
        """
        Extract all available metadata.
        Returns dict with title, authors, abstract, doi, year, etc.
        """
        return {
            "title": self.extract_title(pdf_path),
            "authors": self.extract_authors(pdf_path),
            "abstract": self.extract_abstract(pdf_path),
            "doi": self.extract_doi(pdf_path),
            "year": self.extract_year(pdf_path),
        }
