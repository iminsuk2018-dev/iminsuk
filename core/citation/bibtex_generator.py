"""
BibTeX Citation Generator
"""
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BibTeXGenerator:
    """Generate BibTeX citations from document metadata"""

    def __init__(self):
        pass

    def generate(self, document: Dict) -> str:
        """
        Generate BibTeX entry for a document.

        Args:
            document: Document dict with metadata

        Returns:
            BibTeX entry string
        """
        # Determine entry type
        entry_type = self._determine_entry_type(document)

        # Generate cite key
        cite_key = self._generate_cite_key(document)

        # Build BibTeX entry
        bibtex = f"@{entry_type}{{{cite_key},\n"

        # Add fields
        fields = self._extract_fields(document)

        for key, value in fields.items():
            if value:
                # Escape special characters
                value = self._escape_bibtex(value)
                bibtex += f"  {key} = {{{value}}},\n"

        # Remove trailing comma and close
        bibtex = bibtex.rstrip(",\n") + "\n}\n"

        return bibtex

    def generate_batch(self, documents: List[Dict]) -> str:
        """Generate BibTeX for multiple documents"""
        entries = []

        for doc in documents:
            try:
                entry = self.generate(doc)
                entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to generate BibTeX for doc {doc.get('doc_id')}: {e}")

        return "\n".join(entries)

    def _determine_entry_type(self, document: Dict) -> str:
        """
        Determine BibTeX entry type from document metadata.

        Common types: article, book, inproceedings, phdthesis, misc
        """
        # Check for journal
        if document.get('journal'):
            return 'article'

        # Check for publisher (books)
        if document.get('publisher'):
            return 'book'

        # Check for booktitle (conference papers)
        if document.get('booktitle'):
            return 'inproceedings'

        # Default to misc
        return 'misc'

    def _generate_cite_key(self, document: Dict) -> str:
        """
        Generate BibTeX citation key.

        Format: FirstAuthorLastName_Year
        Example: Smith_2023
        """
        # Get first author
        authors_str = document.get('authors', '')
        year = document.get('year', datetime.now().year)

        if authors_str:
            # Parse first author
            authors = self._parse_authors(authors_str)
            if authors:
                first_author = authors[0]
                # Extract last name
                parts = first_author.split()
                last_name = parts[-1] if parts else "Unknown"
            else:
                last_name = "Unknown"
        else:
            last_name = "Unknown"

        # Clean last name
        last_name = re.sub(r'[^a-zA-Z0-9]', '', last_name)

        cite_key = f"{last_name}_{year}"

        return cite_key

    def _extract_fields(self, document: Dict) -> Dict[str, str]:
        """Extract BibTeX fields from document metadata"""
        fields = {}

        # Title (required)
        if document.get('title'):
            fields['title'] = document['title']

        # Authors (required for most types)
        if document.get('authors'):
            fields['author'] = self._format_authors(document['authors'])

        # Year
        if document.get('year'):
            fields['year'] = str(document['year'])

        # Journal
        if document.get('journal'):
            fields['journal'] = document['journal']

        # DOI
        if document.get('doi'):
            fields['doi'] = document['doi']

        # Abstract
        if document.get('abstract'):
            fields['abstract'] = document['abstract']

        # Volume, number, pages (if available in metadata)
        for field in ['volume', 'number', 'pages', 'publisher', 'booktitle', 'editor']:
            if document.get(field):
                fields[field] = str(document[field])

        # Add file path as note
        if document.get('file_path'):
            fields['file'] = document['file_path']

        return fields

    def _parse_authors(self, authors_str: str) -> List[str]:
        """Parse authors string into list of names"""
        if not authors_str:
            return []

        # Try different separators
        separators = [';', ',', ' and ', '&']

        for sep in separators:
            if sep in authors_str:
                return [a.strip() for a in authors_str.split(sep) if a.strip()]

        # Single author
        return [authors_str.strip()]

    def _format_authors(self, authors_str: str) -> str:
        """
        Format authors for BibTeX.

        BibTeX format: "Last1, First1 and Last2, First2 and ..."
        """
        authors = self._parse_authors(authors_str)

        formatted = []
        for author in authors:
            # Already formatted or simple name
            formatted.append(author)

        return " and ".join(formatted)

    @staticmethod
    def _escape_bibtex(text: str) -> str:
        """Escape special BibTeX characters"""
        # Escape %
        text = text.replace('%', '\\%')

        # Escape &
        text = text.replace('&', '\\&')

        # Escape $
        text = text.replace('$', '\\$')

        # Escape #
        text = text.replace('#', '\\#')

        # Escape _
        text = text.replace('_', '\\_')

        # Escape {
        text = text.replace('{', '\\{')

        # Escape }
        text = text.replace('}', '\\}')

        return text

    def validate_bibtex(self, bibtex: str) -> bool:
        """
        Validate BibTeX syntax.

        Returns True if valid, False otherwise.
        """
        # Basic validation
        if not bibtex.strip():
            return False

        # Check for @ entry
        if not bibtex.strip().startswith('@'):
            return False

        # Check for balanced braces
        if bibtex.count('{') != bibtex.count('}'):
            return False

        return True

    def parse_bibtex(self, bibtex: str) -> Optional[Dict]:
        """
        Parse BibTeX entry into dict.

        Returns dict with entry_type, cite_key, and fields.
        """
        try:
            # Extract entry type and cite key
            match = re.match(r'@(\w+)\{([^,]+),', bibtex)
            if not match:
                return None

            entry_type = match.group(1).lower()
            cite_key = match.group(2).strip()

            # Extract fields
            fields = {}
            field_pattern = r'(\w+)\s*=\s*\{([^}]*)\}'

            for match in re.finditer(field_pattern, bibtex):
                field_name = match.group(1)
                field_value = match.group(2)
                fields[field_name] = field_value

            return {
                'entry_type': entry_type,
                'cite_key': cite_key,
                'fields': fields
            }

        except Exception as e:
            logger.error(f"Failed to parse BibTeX: {e}")
            return None
