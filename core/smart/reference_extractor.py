"""
Reference Extractor
Extracts bibliographic references from PDF documents
"""
import logging
import re
from typing import List, Dict, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class ReferenceExtractor:
    """Extracts and parses references from PDF documents"""

    def __init__(self, workspace):
        self.workspace = workspace

    def extract_references(self, doc_id: int, file_path: str) -> List[Dict]:
        """
        Extract references from a PDF file.

        Returns list of reference dicts with:
            - reference_text: Full text of the reference
            - title: Extracted title (if possible)
            - authors: Extracted authors (if possible)
            - year: Extracted year (if possible)
            - doi: Extracted DOI (if possible)
            - reference_type: Type of reference (article, book, etc.)
            - order_index: Position in reference list
        """
        try:
            # Open PDF
            doc = fitz.open(file_path)

            # Extract text from all pages (focus on last pages where references usually are)
            full_text = ""
            start_page = max(0, len(doc) - 10)  # Last 10 pages

            for page_num in range(start_page, len(doc)):
                page = doc[page_num]
                full_text += page.get_text()

            doc.close()

            # Find references section
            references_text = self._find_references_section(full_text)

            if not references_text:
                logger.warning(f"No references section found in doc {doc_id}")
                return []

            # Parse individual references
            references = self._parse_references(references_text)

            logger.info(f"Extracted {len(references)} references from doc {doc_id}")

            return references

        except Exception as e:
            logger.error(f"Failed to extract references from {file_path}: {e}", exc_info=True)
            return []

    def _find_references_section(self, text: str) -> Optional[str]:
        """Find the references/bibliography section in text"""
        # Common reference section headers
        patterns = [
            r'(?i)\n\s*References?\s*\n',
            r'(?i)\n\s*Bibliography\s*\n',
            r'(?i)\n\s*Literature Cited\s*\n',
            r'(?i)\n\s*Works Cited\s*\n',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # Get text from this point onwards
                start_pos = match.end()

                # Try to find end of references (next section)
                end_patterns = [
                    r'(?i)\n\s*Appendix',
                    r'(?i)\n\s*Supplementary',
                    r'(?i)\n\s*Acknowledgment',
                    r'(?i)\n\s*Author Contributions',
                ]

                end_pos = len(text)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, text[start_pos:])
                    if end_match:
                        end_pos = start_pos + end_match.start()
                        break

                return text[start_pos:end_pos]

        return None

    def _parse_references(self, references_text: str) -> List[Dict]:
        """Parse individual references from references section"""
        references = []

        # Split by numbered references [1], [2], etc. or by double newlines
        # Pattern for numbered references: [1] or 1. or (1)
        split_pattern = r'\n\s*(?:\[\d+\]|\d+\.|\(\d+\))\s+'

        # Split the text
        parts = re.split(split_pattern, references_text)

        # Remove empty parts
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) < 2:
            # Try alternative split (by double newlines)
            parts = [p.strip() for p in references_text.split('\n\n') if p.strip()]

        for i, ref_text in enumerate(parts):
            # Clean up the reference text
            ref_text = ' '.join(ref_text.split())  # Remove extra whitespace

            if len(ref_text) < 20:  # Too short to be a valid reference
                continue

            # Parse the reference
            parsed = self._parse_single_reference(ref_text)
            parsed['order_index'] = i

            references.append(parsed)

        return references

    def _parse_single_reference(self, ref_text: str) -> Dict:
        """Parse a single reference to extract metadata"""
        result = {
            'reference_text': ref_text,
            'title': None,
            'authors': None,
            'year': None,
            'doi': None,
            'reference_type': 'unknown'
        }

        # Extract DOI
        doi_match = re.search(r'(?i)doi:?\s*([^\s,]+)', ref_text)
        if doi_match:
            result['doi'] = doi_match.group(1).strip()

        # Extract year (4 digits in parentheses or standalone)
        year_match = re.search(r'\((\d{4})\)|,\s*(\d{4})[,.]', ref_text)
        if year_match:
            result['year'] = int(year_match.group(1) or year_match.group(2))

        # Extract authors (text before year)
        if year_match:
            authors_text = ref_text[:year_match.start()].strip()
            # Remove leading numbers/brackets
            authors_text = re.sub(r'^[\[\(]?\d+[\]\)]?\s*', '', authors_text)
            result['authors'] = authors_text[:200]  # Limit length

        # Extract title (text in quotes or after authors)
        # Look for text in quotes
        title_match = re.search(r'[""]([^""]+)[""]', ref_text)
        if title_match:
            result['title'] = title_match.group(1).strip()
        elif year_match:
            # Title is likely after year until period or comma
            title_start = year_match.end()
            remaining = ref_text[title_start:].strip()
            # Remove leading punctuation
            remaining = re.sub(r'^[,.\s]+', '', remaining)
            # Get text until next period (but not DOI or URL)
            title_match = re.search(r'^([^.]+\.)', remaining)
            if title_match:
                result['title'] = title_match.group(1).strip(' .')[:300]

        # Determine reference type (simple heuristic)
        if 'journal' in ref_text.lower() or re.search(r'\d+\(\d+\)', ref_text):
            result['reference_type'] = 'article'
        elif 'proc.' in ref_text.lower() or 'conference' in ref_text.lower():
            result['reference_type'] = 'conference'
        elif 'book' in ref_text.lower() or 'publisher' in ref_text.lower():
            result['reference_type'] = 'book'

        return result

    def save_references(self, doc_id: int, references: List[Dict]) -> bool:
        """Save extracted references to database"""
        if not references:
            return True

        db = self.workspace.get_database()

        try:
            with db.transaction() as conn:
                cursor = conn.cursor()

                # Delete existing references for this document
                cursor.execute("DELETE FROM document_references WHERE doc_id = ?", (doc_id,))

                # Insert new references
                for ref in references:
                    cursor.execute("""
                        INSERT INTO document_references (
                            doc_id, reference_text, title, authors, year, doi,
                            reference_type, order_index
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        ref['reference_text'],
                        ref.get('title'),
                        ref.get('authors'),
                        ref.get('year'),
                        ref.get('doi'),
                        ref.get('reference_type', 'unknown'),
                        ref.get('order_index', 0)
                    ))

                logger.info(f"Saved {len(references)} references for doc {doc_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to save references: {e}", exc_info=True)
            return False

    def get_references(self, doc_id: int) -> List[Dict]:
        """Get saved references for a document"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        refs = cursor.execute("""
            SELECT * FROM document_references
            WHERE doc_id = ?
            ORDER BY order_index
        """, (doc_id,)).fetchall()

        return [dict(ref) for ref in refs]

    def extract_and_save(self, doc_id: int, file_path: str) -> int:
        """
        Extract references from PDF and save to database.
        Returns number of references extracted.
        """
        references = self.extract_references(doc_id, file_path)

        if references:
            self.save_references(doc_id, references)

        return len(references)
