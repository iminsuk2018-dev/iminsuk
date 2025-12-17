"""
Citation Formatter
Supports multiple citation styles: APA, MLA, Chicago, IEEE, etc.
"""
import logging
import re
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CitationStyle(Enum):
    """Supported citation styles"""
    APA = "apa"  # American Psychological Association
    MLA = "mla"  # Modern Language Association
    CHICAGO = "chicago"  # Chicago Manual of Style
    IEEE = "ieee"  # Institute of Electrical and Electronics Engineers
    HARVARD = "harvard"  # Harvard referencing
    VANCOUVER = "vancouver"  # Vancouver system


class CitationFormatter:
    """Format citations in various styles"""

    def __init__(self):
        self.formatters = {
            CitationStyle.APA: self._format_apa,
            CitationStyle.MLA: self._format_mla,
            CitationStyle.CHICAGO: self._format_chicago,
            CitationStyle.IEEE: self._format_ieee,
            CitationStyle.HARVARD: self._format_harvard,
            CitationStyle.VANCOUVER: self._format_vancouver,
        }

    def format(self, document: Dict, style: CitationStyle) -> str:
        """
        Format citation for a document in the specified style.

        Args:
            document: Document dict with metadata
            style: CitationStyle enum

        Returns:
            Formatted citation string
        """
        formatter = self.formatters.get(style)
        if not formatter:
            logger.warning(f"Unsupported style: {style}")
            return self._format_apa(document)  # Default to APA

        try:
            return formatter(document)
        except Exception as e:
            logger.error(f"Failed to format citation: {e}")
            return f"Error formatting citation: {str(e)}"

    def format_batch(self, documents: List[Dict], style: CitationStyle) -> List[str]:
        """Format multiple citations"""
        citations = []
        for doc in documents:
            citation = self.format(doc, style)
            citations.append(citation)
        return citations

    def _format_apa(self, doc: Dict) -> str:
        """
        Format in APA style (7th edition).

        Format: Author, A. A. (Year). Title. Journal, volume(issue), pages. DOI

        Example:
        Smith, J., & Johnson, M. (2023). Machine learning applications.
        Nature Machine Intelligence, 5(2), 123-145. https://doi.org/10.1038/xxx
        """
        parts = []

        # Authors
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            if len(authors) == 1:
                parts.append(f"{authors[0]}.")
            elif len(authors) == 2:
                parts.append(f"{authors[0]}, & {authors[1]}.")
            elif len(authors) > 2:
                parts.append(f"{authors[0]}, et al.")
        else:
            parts.append("Author unknown.")

        # Year
        year = doc.get('year', 'n.d.')
        parts.append(f"({year}).")

        # Title (italicized in print, plain here)
        if doc.get('title'):
            parts.append(f"{doc['title']}.")

        # Journal/Source
        if doc.get('journal'):
            journal_part = f"*{doc['journal']}*"

            # Volume/Issue
            if doc.get('volume'):
                journal_part += f", {doc['volume']}"
                if doc.get('issue'):
                    journal_part += f"({doc['issue']})"

            # Pages
            if doc.get('pages'):
                journal_part += f", {doc['pages']}"

            journal_part += "."
            parts.append(journal_part)

        # DOI
        if doc.get('doi'):
            parts.append(f"https://doi.org/{doc['doi']}")

        return " ".join(parts)

    def _format_mla(self, doc: Dict) -> str:
        """
        Format in MLA style (9th edition).

        Format: Author. "Title." Journal, vol. X, no. Y, Year, pp. Z-ZZ.

        Example:
        Smith, John, and Mary Johnson. "Machine Learning Applications."
        Nature Machine Intelligence, vol. 5, no. 2, 2023, pp. 123-145.
        """
        parts = []

        # Authors
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            if len(authors) == 1:
                parts.append(f"{authors[0]}.")
            elif len(authors) == 2:
                parts.append(f"{authors[0]}, and {authors[1]}.")
            elif len(authors) > 2:
                parts.append(f"{authors[0]}, et al.")

        # Title
        if doc.get('title'):
            parts.append(f'\"{doc["title"]}.\"')

        # Journal
        if doc.get('journal'):
            journal_part = f"*{doc['journal']}*"

            if doc.get('volume'):
                journal_part += f", vol. {doc['volume']}"

            if doc.get('issue'):
                journal_part += f", no. {doc['issue']}"

            if doc.get('year'):
                journal_part += f", {doc['year']}"

            if doc.get('pages'):
                journal_part += f", pp. {doc['pages']}"

            journal_part += "."
            parts.append(journal_part)

        return " ".join(parts)

    def _format_chicago(self, doc: Dict) -> str:
        """
        Format in Chicago style (author-date).

        Format: Author, First. Year. "Title." Journal vol, no. issue: pages.

        Example:
        Smith, John, and Mary Johnson. 2023. "Machine Learning Applications."
        Nature Machine Intelligence 5, no. 2: 123-145.
        """
        parts = []

        # Authors
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            if len(authors) == 1:
                parts.append(f"{authors[0]}.")
            elif len(authors) <= 3:
                parts.append(", and ".join(authors) + ".")
            else:
                parts.append(f"{authors[0]}, et al.")

        # Year
        if doc.get('year'):
            parts.append(f"{doc['year']}.")

        # Title
        if doc.get('title'):
            parts.append(f'\"{doc["title"]}.\"')

        # Journal
        if doc.get('journal'):
            journal_part = f"*{doc['journal']}*"

            if doc.get('volume'):
                journal_part += f" {doc['volume']}"

            if doc.get('issue'):
                journal_part += f", no. {doc['issue']}"

            if doc.get('pages'):
                journal_part += f": {doc['pages']}"

            journal_part += "."
            parts.append(journal_part)

        return " ".join(parts)

    def _format_ieee(self, doc: Dict) -> str:
        """
        Format in IEEE style.

        Format: [1] A. Author, "Title," Journal, vol. X, no. Y, pp. Z-ZZ, Year.

        Example:
        J. Smith and M. Johnson, "Machine learning applications,"
        Nat. Mach. Intell., vol. 5, no. 2, pp. 123-145, 2023.
        """
        parts = []

        # Authors (abbreviated first names)
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            author_parts = []
            for author in authors[:3]:  # Max 3 authors
                # Abbreviate first names
                name_parts = author.split()
                if len(name_parts) >= 2:
                    first_initial = name_parts[0][0] + "."
                    last_name = name_parts[-1]
                    author_parts.append(f"{first_initial} {last_name}")
                else:
                    author_parts.append(author)

            if len(authors) > 3:
                parts.append(", ".join(author_parts) + ", et al.,")
            else:
                parts.append(" and ".join(author_parts) + ",")

        # Title
        if doc.get('title'):
            parts.append(f'"{doc["title"]},"')

        # Journal (abbreviated)
        if doc.get('journal'):
            journal = doc['journal']
            # Simple abbreviation (you could expand this)
            journal_abbr = self._abbreviate_journal(journal)
            journal_part = f"*{journal_abbr}*"

            if doc.get('volume'):
                journal_part += f", vol. {doc['volume']}"

            if doc.get('issue'):
                journal_part += f", no. {doc['issue']}"

            if doc.get('pages'):
                journal_part += f", pp. {doc['pages']}"

            parts.append(journal_part + ",")

        # Year
        if doc.get('year'):
            parts.append(f"{doc['year']}.")

        return " ".join(parts)

    def _format_harvard(self, doc: Dict) -> str:
        """
        Format in Harvard style.

        Format: Author (Year) Title. Journal, volume(issue), pp.pages.

        Example:
        Smith, J. and Johnson, M. (2023) Machine learning applications.
        Nature Machine Intelligence, 5(2), pp.123-145.
        """
        parts = []

        # Authors
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            if len(authors) <= 2:
                parts.append(" and ".join(authors))
            else:
                parts.append(f"{authors[0]}, et al.")

        # Year
        year = doc.get('year', 'n.d.')
        parts.append(f"({year})")

        # Title
        if doc.get('title'):
            parts.append(f"*{doc['title']}*.")

        # Journal
        if doc.get('journal'):
            journal_part = f"{doc['journal']}"

            if doc.get('volume'):
                journal_part += f", {doc['volume']}"
                if doc.get('issue'):
                    journal_part += f"({doc['issue']})"

            if doc.get('pages'):
                journal_part += f", pp.{doc['pages']}"

            journal_part += "."
            parts.append(journal_part)

        return " ".join(parts)

    def _format_vancouver(self, doc: Dict) -> str:
        """
        Format in Vancouver style (numbered).

        Format: Author(s). Title. Journal. Year;volume(issue):pages.

        Example:
        Smith J, Johnson M. Machine learning applications.
        Nat Mach Intell. 2023;5(2):123-145.
        """
        parts = []

        # Authors (last name, initials)
        if doc.get('authors'):
            authors = self._parse_authors(doc['authors'])
            author_parts = []
            for author in authors[:6]:  # Max 6 authors
                name_parts = author.split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1]
                    initials = "".join([n[0] for n in name_parts[:-1]])
                    author_parts.append(f"{last_name} {initials}")
                else:
                    author_parts.append(author)

            if len(authors) > 6:
                parts.append(", ".join(author_parts) + ", et al.")
            else:
                parts.append(", ".join(author_parts) + ".")

        # Title
        if doc.get('title'):
            parts.append(f"{doc['title']}.")

        # Journal (abbreviated)
        if doc.get('journal'):
            journal_abbr = self._abbreviate_journal(doc['journal'])
            journal_part = f"{journal_abbr}."

            # Year;volume(issue):pages
            citation_details = []
            if doc.get('year'):
                citation_details.append(str(doc['year']))

            if doc.get('volume'):
                vol_part = f"{doc['volume']}"
                if doc.get('issue'):
                    vol_part += f"({doc['issue']})"
                citation_details.append(vol_part)

            if doc.get('pages'):
                citation_details.append(doc['pages'])

            if citation_details:
                journal_part += ";".join(citation_details[:1]) + ";"
                if len(citation_details) > 1:
                    journal_part += ":".join(citation_details[1:])
                journal_part += "."

            parts.append(journal_part)

        return " ".join(parts)

    @staticmethod
    def _parse_authors(authors_str: str) -> List[str]:
        """Parse authors string into list"""
        if not authors_str:
            return []

        separators = [';', ',', ' and ', '&']
        for sep in separators:
            if sep in authors_str:
                return [a.strip() for a in authors_str.split(sep) if a.strip()]

        return [authors_str.strip()]

    @staticmethod
    def _abbreviate_journal(journal: str) -> str:
        """Simple journal abbreviation"""
        # This is a simplified version
        # In a real system, you'd use a journal abbreviation database

        abbr_map = {
            'Nature': 'Nature',
            'Science': 'Science',
            'Nature Machine Intelligence': 'Nat. Mach. Intell.',
            'Journal of Machine Learning Research': 'J. Mach. Learn. Res.',
            # Add more...
        }

        return abbr_map.get(journal, journal)
