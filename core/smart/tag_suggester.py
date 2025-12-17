"""
Smart Tag Suggester
Suggests relevant tags based on document content
"""
import logging
import re
from typing import List, Dict, Set
from collections import Counter
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class TagSuggester:
    """Suggests tags based on document content analysis"""

    # Common academic keywords and domains
    DOMAIN_KEYWORDS = {
        'machine learning': ['neural', 'deep learning', 'cnn', 'rnn', 'lstm', 'transformer', 'training', 'model'],
        'computer vision': ['image', 'vision', 'object detection', 'segmentation', 'recognition', 'visual'],
        'nlp': ['natural language', 'text', 'nlp', 'language model', 'bert', 'gpt', 'tokenization'],
        'robotics': ['robot', 'autonomous', 'control', 'manipulation', 'navigation', 'sensor'],
        'data science': ['data', 'analysis', 'statistics', 'visualization', 'mining', 'dataset'],
        'algorithms': ['algorithm', 'complexity', 'optimization', 'sorting', 'graph', 'dynamic programming'],
        'security': ['security', 'encryption', 'privacy', 'authentication', 'vulnerability', 'attack'],
        'databases': ['database', 'sql', 'query', 'nosql', 'transaction', 'indexing'],
        'networks': ['network', 'protocol', 'tcp', 'routing', 'wireless', 'communication'],
        'systems': ['operating system', 'kernel', 'memory', 'process', 'scheduling', 'distributed'],
    }

    METHOD_KEYWORDS = {
        'supervised learning': ['supervised', 'classification', 'regression', 'labeled'],
        'unsupervised learning': ['unsupervised', 'clustering', 'dimensionality', 'unlabeled'],
        'reinforcement learning': ['reinforcement', 'reward', 'agent', 'policy', 'q-learning'],
        'simulation': ['simulation', 'monte carlo', 'modeling', 'synthetic'],
        'experimental': ['experiment', 'empirical', 'trial', 'measurement'],
        'theoretical': ['theorem', 'proof', 'theoretical', 'mathematical', 'formal'],
        'survey': ['survey', 'review', 'literature', 'state-of-the-art'],
        'benchmark': ['benchmark', 'evaluation', 'comparison', 'baseline'],
    }

    def __init__(self, workspace):
        self.workspace = workspace

    def suggest_tags(self, doc_id: int, file_path: str = None, limit: int = 10) -> List[Dict]:
        """
        Suggest tags for a document.

        Returns list of tag suggestions with:
            - tag_name: Suggested tag name
            - confidence: Confidence score (0-1)
            - reason: Why this tag was suggested
            - exists: Whether this tag already exists in the system
        """
        try:
            db = self.workspace.get_database()
            conn = db.connect()
            cursor = conn.cursor()

            # Get document metadata
            doc = cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()

            if not doc:
                logger.error(f"Document {doc_id} not found")
                return []

            doc = dict(doc)

            # Extract text content
            text_content = self._extract_text_sample(file_path or doc['file_path'])

            # Combine metadata and content
            full_text = ' '.join(filter(None, [
                doc.get('title', ''),
                doc.get('abstract', ''),
                doc.get('authors', ''),
                text_content
            ])).lower()

            # Generate suggestions from multiple sources
            suggestions = []

            # 1. Domain-based suggestions
            domain_tags = self._suggest_domain_tags(full_text)
            suggestions.extend(domain_tags)

            # 2. Method-based suggestions
            method_tags = self._suggest_method_tags(full_text)
            suggestions.extend(method_tags)

            # 3. Keyword extraction
            keyword_tags = self._extract_keyword_tags(full_text, doc.get('title', ''))
            suggestions.extend(keyword_tags)

            # 4. Year tag
            if doc.get('year'):
                suggestions.append({
                    'tag_name': str(doc['year']),
                    'confidence': 1.0,
                    'reason': 'Publication year'
                })

            # 5. Journal/venue tag
            if doc.get('journal'):
                journal_tag = self._clean_tag_name(doc['journal'])
                if journal_tag:
                    suggestions.append({
                        'tag_name': journal_tag,
                        'confidence': 0.9,
                        'reason': 'Journal/venue'
                    })

            # Remove duplicates and sort by confidence
            seen = set()
            unique_suggestions = []

            for suggestion in sorted(suggestions, key=lambda x: x['confidence'], reverse=True):
                tag_name_lower = suggestion['tag_name'].lower()
                if tag_name_lower not in seen:
                    seen.add(tag_name_lower)
                    unique_suggestions.append(suggestion)

            # Check which tags already exist
            existing_tags = cursor.execute("SELECT tag_name FROM tags").fetchall()
            existing_tag_names = {tag['tag_name'].lower() for tag in existing_tags}

            for suggestion in unique_suggestions:
                suggestion['exists'] = suggestion['tag_name'].lower() in existing_tag_names

            # Limit results
            unique_suggestions = unique_suggestions[:limit]

            logger.info(f"Generated {len(unique_suggestions)} tag suggestions for doc {doc_id}")

            return unique_suggestions

        except Exception as e:
            logger.error(f"Failed to suggest tags: {e}", exc_info=True)
            return []

    def _extract_text_sample(self, file_path: str, max_pages: int = 3) -> str:
        """Extract text sample from first few pages"""
        try:
            doc = fitz.open(file_path)
            text = ""

            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += page.get_text()

            doc.close()

            # Limit length
            return text[:5000]

        except Exception as e:
            logger.warning(f"Failed to extract text from {file_path}: {e}")
            return ""

    def _suggest_domain_tags(self, text: str) -> List[Dict]:
        """Suggest domain tags based on keyword matching"""
        suggestions = []

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword in text)

            if matches > 0:
                # Calculate confidence based on match count
                confidence = min(0.5 + (matches * 0.1), 1.0)

                suggestions.append({
                    'tag_name': domain,
                    'confidence': confidence,
                    'reason': f'Domain keyword matches ({matches})'
                })

        return suggestions

    def _suggest_method_tags(self, text: str) -> List[Dict]:
        """Suggest methodology tags"""
        suggestions = []

        for method, keywords in self.METHOD_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text)

            if matches > 0:
                confidence = min(0.4 + (matches * 0.15), 1.0)

                suggestions.append({
                    'tag_name': method,
                    'confidence': confidence,
                    'reason': f'Methodology keyword matches ({matches})'
                })

        return suggestions

    def _extract_keyword_tags(self, text: str, title: str = '') -> List[Dict]:
        """Extract important keywords as tags"""
        suggestions = []

        # Extract title keywords (higher weight)
        if title:
            title_words = self._extract_important_words(title)

            for word in title_words[:3]:  # Top 3 from title
                suggestions.append({
                    'tag_name': word,
                    'confidence': 0.7,
                    'reason': 'Key term from title'
                })

        # Extract content keywords
        content_words = self._extract_important_words(text, limit=5)

        for word in content_words:
            suggestions.append({
                'tag_name': word,
                'confidence': 0.5,
                'reason': 'Frequent term in content'
            })

        return suggestions

    def _extract_important_words(self, text: str, limit: int = 10) -> List[str]:
        """Extract important words using simple frequency analysis"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'can', 'this', 'that', 'these', 'those', 'we', 'our', 'they',
            'their', 'it', 'its', 'from', 'by', 'as', 'which', 'who', 'when',
            'where', 'how', 'why', 'what', 'such', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'also', 'than', 'then', 'so', 'if', 'about',
            'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up',
            'down', 'out', 'over', 'under', 'again', 'further', 'once', 'here',
            'there', 'all', 'any', 'both', 'each', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'than', 'too', 'very'
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())  # At least 4 characters
        words = [w for w in words if w not in stop_words]

        # Count frequencies
        word_counts = Counter(words)

        # Get most common
        common_words = [word for word, count in word_counts.most_common(limit * 3)]

        # Filter out generic terms
        generic_terms = {'paper', 'study', 'research', 'method', 'result', 'conclusion',
                        'introduction', 'abstract', 'figure', 'table', 'show', 'propose',
                        'present', 'approach', 'problem', 'solution', 'system', 'based'}

        filtered_words = [w for w in common_words if w not in generic_terms]

        return filtered_words[:limit]

    @staticmethod
    def _clean_tag_name(name: str) -> str:
        """Clean and normalize tag name"""
        # Remove extra whitespace
        name = ' '.join(name.split())

        # Limit length
        if len(name) > 50:
            return None

        # Remove special characters except hyphen and underscore
        name = re.sub(r'[^\w\s-]', '', name)

        return name.strip()
