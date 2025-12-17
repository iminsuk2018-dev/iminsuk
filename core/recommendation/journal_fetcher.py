"""
학술 저널 논문 수집 (Crossref API 사용)
"""
import logging
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

from config import CROSSREF_API_URL, CROSSREF_RATE_LIMIT, JOURNAL_FETCH_DAYS, JOURNAL_FETCH_MAX

logger = logging.getLogger(__name__)


def clean_jats_tags(text: str) -> str:
    """
    Remove JATS XML tags from abstract text

    Args:
        text: Text containing JATS tags

    Returns:
        Clean text without JATS tags
    """
    if not text:
        return text

    # Remove JATS tags like <jats:p>, <jats:title>, <jats:sub>, etc.
    # Replace <jats:sub> and <jats:sup> with subscript/superscript symbols when possible
    text = re.sub(r'<jats:sub>(\d+)</jats:sub>', r'�\1', text)  # subscript numbers
    text = re.sub(r'<jats:sup>(\d+)</jats:sup>', r'^\1', text)  # superscript as ^N

    # Remove all other JATS tags
    text = re.sub(r'<jats:[^>]+>', '', text)
    text = re.sub(r'</jats:[^>]+>', '', text)

    # Remove any remaining XML/HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


class JournalFetcher:
    """학술 저널에서 최근 논문 수집"""

    def __init__(self):
        self.api_url = CROSSREF_API_URL
        self.rate_limit = CROSSREF_RATE_LIMIT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PDFResearchApp/0.2 (mailto:research@example.com)'
        })

    def fetch_recent_articles(
        self,
        journal_name: str,
        issn: Optional[str] = None,
        days_back: int = JOURNAL_FETCH_DAYS,
        max_results: int = JOURNAL_FETCH_MAX
    ) -> List[Dict]:
        """
        저널의 최근 논문 가져오기

        Args:
            journal_name: 저널 이름 (예: "Energy & Environmental Science")
            issn: 저널 ISSN (있으면 우선 사용)
            days_back: 최근 며칠 간의 논문
            max_results: 최대 결과 개수

        Returns:
            List of article dicts
        """
        logger.info(f"Fetching articles from '{journal_name}' (ISSN: {issn}, last {days_back} days)")

        # Calculate date range - 더 넓은 범위로 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back * 2)  # 2배로 확장

        # Build query - ISSN을 우선 사용
        filter_parts = [f'from-pub-date:{start_date.strftime("%Y-%m-%d")}']

        if issn:
            # ISSN이 있으면 정확한 매칭
            filter_parts.append(f'issn:{issn}')
            logger.info(f"Using ISSN filter: {issn}")
        else:
            # 저널명으로 검색 (부분 매칭은 불가능하므로 정확한 이름 필요)
            filter_parts.append(f'container-title:"{journal_name}"')
            logger.info(f"Using journal name filter: {journal_name}")

        params = {
            'filter': ','.join(filter_parts),
            'rows': max_results,
            'select': 'title,abstract,author,published,DOI,container-title,ISSN',
            'sort': 'published',
            'order': 'desc'
        }

        try:
            logger.debug(f"Crossref API request params: {params}")
            response = self.session.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'message' not in data or 'items' not in data['message']:
                logger.warning("Unexpected API response format")
                return []

            items = data['message']['items']
            logger.info(f"Received {len(items)} articles from Crossref")

            if len(items) == 0:
                logger.warning(f"No articles found for '{journal_name}'. Try different search parameters.")
                # ISSN 없이 재시도
                if issn and not journal_name.startswith("Unknown"):
                    logger.info("Retrying without ISSN...")
                    return self.fetch_recent_articles(journal_name, issn=None, days_back=days_back, max_results=max_results)

            # Parse articles
            articles = []
            for item in items:
                article = self._parse_crossref_item(item)
                if article:
                    articles.append(article)

            logger.info(f"Successfully parsed {len(articles)} articles")
            return articles

        except requests.RequestException as e:
            logger.error(f"Failed to fetch articles: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error while fetching articles: {e}", exc_info=True)
            return []

    def _parse_crossref_item(self, item: Dict) -> Optional[Dict]:
        """Crossref API 응답을 논문 dict로 변환"""
        try:
            # Extract title
            title = ""
            if 'title' in item and item['title']:
                title = item['title'][0] if isinstance(item['title'], list) else item['title']

            if not title:
                return None

            # Extract abstract and clean JATS tags
            abstract = item.get('abstract', '')
            abstract = clean_jats_tags(abstract)

            # Extract authors
            authors = []
            if 'author' in item:
                for author in item['author']:
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)

            # Extract publication date
            year = None
            if 'published' in item:
                date_parts = item['published'].get('date-parts', [[]])[0]
                if date_parts:
                    year = date_parts[0]

            # Extract DOI
            doi = item.get('DOI', '')

            # Extract journal name
            journal = ""
            if 'container-title' in item and item['container-title']:
                journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']

            return {
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'year': year,
                'doi': doi,
                'journal': journal
            }

        except Exception as e:
            logger.error(f"Failed to parse article: {e}")
            return None

    def search_journal_by_issn(self, issn: str) -> Optional[Dict]:
        """ISSN으로 저널 정보 조회"""
        url = f"https://api.crossref.org/journals/{issn}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'message' in data:
                journal_info = data['message']
                return {
                    'title': journal_info.get('title', ''),
                    'issn': issn,
                    'publisher': journal_info.get('publisher', '')
                }

        except Exception as e:
            logger.error(f"Failed to fetch journal info: {e}")

        return None

    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """DOI로 특정 논문 검색"""
        url = f"https://api.crossref.org/works/{quote(doi)}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'message' in data:
                return self._parse_crossref_item(data['message'])

        except Exception as e:
            logger.error(f"Failed to fetch article by DOI: {e}")

        return None


class ArxivFetcher:
    """
    arXiv 논문 수집 (선택적 구현)
    나중에 확장 가능
    """

    def __init__(self):
        self.api_url = "http://export.arxiv.org/api/query"

    def fetch_recent_articles(
        self,
        category: str,
        max_results: int = 50
    ) -> List[Dict]:
        """
        arXiv 카테고리에서 최근 논문 가져오기

        Args:
            category: arXiv 카테고리 (예: "cs.AI", "physics.chem-ph")
            max_results: 최대 결과 개수

        Returns:
            List of article dicts
        """
        logger.info(f"Fetching articles from arXiv category: {category}")

        params = {
            'search_query': f'cat:{category}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()

            # Parse XML response
            # TODO: Implement XML parsing
            # For now, return empty list
            logger.warning("arXiv parsing not implemented yet")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch from arXiv: {e}")
            return []
