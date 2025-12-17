"""
Duplicate Paper Detector
Detects duplicate documents using various methods
"""
import logging
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate papers in the library"""

    def __init__(self, workspace):
        self.workspace = workspace

    def find_duplicates(self) -> List[Dict]:
        """
        Find all duplicate documents.

        Returns list of duplicate groups.
        Each group is a dict with:
            - 'docs': List of doc dicts that are duplicates
            - 'reason': Why they're considered duplicates
            - 'confidence': Confidence score (0-1)
        """
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        # Get all documents
        docs = cursor.execute("SELECT * FROM documents").fetchall()
        docs = [dict(doc) for doc in docs]

        logger.info(f"Checking {len(docs)} documents for duplicates")

        duplicate_groups = []

        # 1. Check by file hash (exact duplicates)
        hash_groups = self._group_by_hash(docs)
        for group in hash_groups:
            if len(group) > 1:
                duplicate_groups.append({
                    'docs': group,
                    'reason': 'Identical file (same hash)',
                    'confidence': 1.0
                })

        # 2. Check by DOI
        doi_groups = self._group_by_doi(docs)
        for group in doi_groups:
            if len(group) > 1:
                # Check if not already found by hash
                if not self._already_grouped(group, duplicate_groups):
                    duplicate_groups.append({
                        'docs': group,
                        'reason': 'Same DOI',
                        'confidence': 1.0
                    })

        # 3. Check by title similarity
        title_duplicates = self._find_similar_titles(docs)
        for group_info in title_duplicates:
            if not self._already_grouped(group_info['docs'], duplicate_groups):
                duplicate_groups.append(group_info)

        # 4. Check by title + authors
        author_duplicates = self._find_similar_title_author(docs)
        for group_info in author_duplicates:
            if not self._already_grouped(group_info['docs'], duplicate_groups):
                duplicate_groups.append(group_info)

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")

        return duplicate_groups

    def _group_by_hash(self, docs: List[Dict]) -> List[List[Dict]]:
        """Group documents by file hash"""
        hash_map = {}

        for doc in docs:
            file_hash = doc.get('file_hash')
            if file_hash:
                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(doc)

        return [group for group in hash_map.values() if len(group) > 1]

    def _group_by_doi(self, docs: List[Dict]) -> List[List[Dict]]:
        """Group documents by DOI"""
        doi_map = {}

        for doc in docs:
            doi = doc.get('doi')
            if doi and doi.strip():
                doi_normalized = self._normalize_doi(doi)
                if doi_normalized not in doi_map:
                    doi_map[doi_normalized] = []
                doi_map[doi_normalized].append(doc)

        return [group for group in doi_map.values() if len(group) > 1]

    def _find_similar_titles(self, docs: List[Dict], threshold: float = 0.9) -> List[Dict]:
        """Find documents with very similar titles"""
        duplicates = []

        for i, doc1 in enumerate(docs):
            title1 = doc1.get('title')
            if not title1:
                continue

            title1_normalized = self._normalize_title(title1)

            for doc2 in docs[i + 1:]:
                title2 = doc2.get('title')
                if not title2:
                    continue

                title2_normalized = self._normalize_title(title2)

                # Calculate similarity
                similarity = self._string_similarity(title1_normalized, title2_normalized)

                if similarity >= threshold:
                    duplicates.append({
                        'docs': [doc1, doc2],
                        'reason': f'Very similar titles (similarity: {similarity:.2f})',
                        'confidence': similarity
                    })

        return duplicates

    def _find_similar_title_author(self, docs: List[Dict], threshold: float = 0.85) -> List[Dict]:
        """Find documents with similar title AND same first author"""
        duplicates = []

        for i, doc1 in enumerate(docs):
            title1 = doc1.get('title')
            authors1 = doc1.get('authors', '')

            if not title1 or not authors1:
                continue

            title1_normalized = self._normalize_title(title1)
            first_author1 = self._get_first_author(authors1)

            for doc2 in docs[i + 1:]:
                title2 = doc2.get('title')
                authors2 = doc2.get('authors', '')

                if not title2 or not authors2:
                    continue

                title2_normalized = self._normalize_title(title2)
                first_author2 = self._get_first_author(authors2)

                # Check if same first author
                if first_author1 and first_author2:
                    author_similarity = self._string_similarity(first_author1, first_author2)

                    if author_similarity > 0.8:
                        # Calculate title similarity
                        title_similarity = self._string_similarity(title1_normalized, title2_normalized)

                        if title_similarity >= threshold:
                            combined_confidence = (title_similarity + author_similarity) / 2
                            duplicates.append({
                                'docs': [doc1, doc2],
                                'reason': f'Similar title + same author (confidence: {combined_confidence:.2f})',
                                'confidence': combined_confidence
                            })

        return duplicates

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for comparison"""
        # Lowercase
        title = title.lower()

        # Remove punctuation
        title = re.sub(r'[^\w\s]', ' ', title)

        # Remove extra whitespace
        title = ' '.join(title.split())

        return title

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI"""
        doi = doi.lower().strip()

        # Remove common prefixes
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://dx.doi.org/', '')
        doi = doi.replace('doi:', '')

        return doi.strip()

    @staticmethod
    def _get_first_author(authors_str: str) -> Optional[str]:
        """Extract first author from authors string"""
        if not authors_str:
            return None

        # Try to split by common separators
        separators = [';', ',', ' and ', '&']

        for sep in separators:
            if sep in authors_str:
                parts = authors_str.split(sep)
                if parts:
                    return parts[0].strip().lower()

        return authors_str.strip().lower()

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0-1)"""
        if not s1 or not s2:
            return 0.0

        return SequenceMatcher(None, s1, s2).ratio()

    @staticmethod
    def _already_grouped(docs: List[Dict], existing_groups: List[Dict]) -> bool:
        """Check if these docs are already in a duplicate group"""
        doc_ids = {doc['doc_id'] for doc in docs}

        for group in existing_groups:
            group_ids = {doc['doc_id'] for doc in group['docs']}

            # If any overlap, consider already grouped
            if doc_ids & group_ids:
                return True

        return False

    def merge_duplicates(self, doc_ids_to_keep: List[int], doc_ids_to_remove: List[int]) -> bool:
        """
        Merge duplicate documents.

        Keeps documents in doc_ids_to_keep, removes duplicates in doc_ids_to_remove.
        Merges annotations, tags, highlights, etc.

        Returns True if successful.
        """
        if not doc_ids_to_keep or not doc_ids_to_remove:
            logger.warning("Invalid merge parameters")
            return False

        primary_doc_id = doc_ids_to_keep[0]

        db = self.workspace.get_database()

        try:
            with db.transaction() as conn:
                cursor = conn.cursor()

                # For each document to remove
                for doc_id in doc_ids_to_remove:
                    # Move annotations
                    cursor.execute("""
                        UPDATE annotations
                        SET doc_id = ?
                        WHERE doc_id = ?
                    """, (primary_doc_id, doc_id))

                    # Move highlights
                    cursor.execute("""
                        UPDATE highlights
                        SET doc_id = ?
                        WHERE doc_id = ?
                    """, (primary_doc_id, doc_id))

                    # Move bookmarks
                    cursor.execute("""
                        UPDATE bookmarks
                        SET doc_id = ?
                        WHERE doc_id = ?
                    """, (primary_doc_id, doc_id))

                    # Copy tags (avoid duplicates)
                    cursor.execute("""
                        INSERT OR IGNORE INTO document_tags (doc_id, tag_id, added_at)
                        SELECT ?, tag_id, added_at
                        FROM document_tags
                        WHERE doc_id = ?
                    """, (primary_doc_id, doc_id))

                    # Delete the duplicate document
                    cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

                logger.info(f"Merged {len(doc_ids_to_remove)} duplicates into doc {primary_doc_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to merge duplicates: {e}", exc_info=True)
            return False
