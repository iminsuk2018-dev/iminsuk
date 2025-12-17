"""
통합 검색 엔진 (FTS5 기반)
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """검색 결과 항목"""
    result_type: str  # 'title', 'abstract', 'annotation', 'tag'
    doc_id: int
    title: str
    matched_text: str
    rank: float
    page_number: Optional[int] = None  # For annotations
    annotation_id: Optional[int] = None  # For annotations
    tag_id: Optional[int] = None  # For tags
    year: Optional[int] = None
    authors: Optional[str] = None


@dataclass
class SearchResults:
    """검색 결과 그룹"""
    query: str
    total_count: int
    results_by_type: Dict[str, List[SearchResult]] = field(default_factory=dict)

    def add_result(self, result: SearchResult):
        """결과 추가"""
        if result.result_type not in self.results_by_type:
            self.results_by_type[result.result_type] = []
        self.results_by_type[result.result_type].append(result)
        self.total_count += 1


class SearchEngine:
    """통합 검색 엔진"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.db = workspace.get_database()

    def search(self, query: str, content_types: List[str] = None, limit: int = 100) -> SearchResults:
        """
        통합 검색 수행

        Args:
            query: 검색 쿼리
            content_types: 검색 대상 타입 리스트 (None이면 전체)
                          ['title', 'abstract', 'annotation', 'tag']
            limit: 최대 결과 개수

        Returns:
            SearchResults 객체
        """
        if not query or not query.strip():
            return SearchResults(query="", total_count=0)

        query = query.strip()
        results = SearchResults(query=query, total_count=0)

        conn = self.db.connect()
        cursor = conn.cursor()

        # Build FTS5 query
        fts_query = self._build_fts_query(query)

        # Build WHERE clause for content types
        where_conditions = ["search_index MATCH ?"]
        params = [fts_query]

        if content_types:
            placeholders = ','.join(['?' for _ in content_types])
            where_conditions.append(f"content_type IN ({placeholders})")
            params.extend(content_types)

        where_clause = " AND ".join(where_conditions)

        # Execute search
        sql = f"""
            SELECT
                si.content_type,
                si.content,
                si.doc_id,
                si.annotation_id,
                si.tag_id,
                si.rank,
                d.title,
                d.year,
                d.authors,
                a.page_number
            FROM search_index si
            JOIN documents d ON si.doc_id = d.doc_id
            LEFT JOIN annotations a ON si.annotation_id = a.annotation_id
            WHERE {where_clause}
            ORDER BY si.rank
            LIMIT ?
        """

        params.append(limit)

        try:
            rows = cursor.execute(sql, params).fetchall()

            for row in rows:
                result = SearchResult(
                    result_type=row[0],
                    matched_text=row[1],
                    doc_id=row[2],
                    annotation_id=row[3],
                    tag_id=row[4],
                    rank=row[5],
                    title=row[6] or "Untitled",
                    year=row[7],
                    authors=row[8],
                    page_number=row[9]
                )
                results.add_result(result)

            logger.info(f"Search '{query}' returned {results.total_count} results")

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)

        return results

    def search_documents_only(self, query: str, limit: int = 50) -> List[Dict]:
        """
        문서만 검색 (제목, 초록)
        간단한 인터페이스용
        """
        results = self.search(query, content_types=['title', 'abstract'], limit=limit)

        # Deduplicate by doc_id
        seen_docs = set()
        documents = []

        for result_type, result_list in results.results_by_type.items():
            for result in result_list:
                if result.doc_id not in seen_docs:
                    seen_docs.add(result.doc_id)
                    documents.append({
                        'doc_id': result.doc_id,
                        'title': result.title,
                        'year': result.year,
                        'authors': result.authors,
                        'matched_in': result_type,
                        'matched_text': result.matched_text[:100]
                    })

        return documents

    def search_annotations(self, query: str, doc_id: int = None) -> List[Dict]:
        """
        메모 검색

        Args:
            query: 검색어
            doc_id: 특정 문서로 제한 (None이면 전체)
        """
        results = self.search(query, content_types=['annotation'])

        annotations = []
        for result in results.results_by_type.get('annotation', []):
            if doc_id is None or result.doc_id == doc_id:
                annotations.append({
                    'annotation_id': result.annotation_id,
                    'doc_id': result.doc_id,
                    'title': result.title,
                    'content': result.matched_text,
                    'page_number': result.page_number
                })

        return annotations

    def search_by_tag(self, tag_name: str) -> List[int]:
        """
        태그로 문서 검색
        Returns: doc_id 리스트
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT DISTINCT dt.doc_id
            FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE t.tag_name LIKE ?
        """, (f"%{tag_name}%",)).fetchall()

        return [row[0] for row in results]

    def _build_fts_query(self, query: str) -> str:
        """
        FTS5 쿼리 문자열 생성

        간단한 버전: 각 단어를 OR로 연결
        """
        # Split query into words
        words = query.split()

        # Escape special characters
        escaped_words = []
        for word in words:
            # Remove special FTS5 characters
            word = word.replace('"', '')
            if word:
                escaped_words.append(word)

        # Join with OR
        if len(escaped_words) == 1:
            return escaped_words[0]
        else:
            return ' OR '.join(escaped_words)

    def rebuild_index(self):
        """
        전체 FTS 인덱스 재구축
        문서 추가/삭제 후 문제가 있을 때 사용
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        logger.info("Rebuilding search index...")

        # Clear existing index
        cursor.execute("DELETE FROM search_index")

        # Re-index documents
        self._index_all_documents(cursor)

        # Re-index annotations
        self._index_all_annotations(cursor)

        # Re-index tags
        self._index_all_tags(cursor)

        conn.commit()
        logger.info("Search index rebuilt successfully")

    def _index_all_documents(self, cursor):
        """문서 제목, 초록 인덱싱"""
        docs = cursor.execute("SELECT doc_id, title, abstract FROM documents").fetchall()

        for doc in docs:
            doc_id, title, abstract = doc

            # Index title
            if title:
                cursor.execute("""
                    INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                    VALUES ('title', ?, ?, NULL, NULL)
                """, (title, doc_id))

            # Index abstract
            if abstract:
                cursor.execute("""
                    INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                    VALUES ('abstract', ?, ?, NULL, NULL)
                """, (abstract, doc_id))

        logger.debug(f"Indexed {len(docs)} documents")

    def _index_all_annotations(self, cursor):
        """모든 메모 인덱싱"""
        annotations = cursor.execute("""
            SELECT annotation_id, doc_id, content FROM annotations
        """).fetchall()

        for ann in annotations:
            annotation_id, doc_id, content = ann
            cursor.execute("""
                INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                VALUES ('annotation', ?, ?, ?, NULL)
            """, (content, doc_id, annotation_id))

        logger.debug(f"Indexed {len(annotations)} annotations")

    def _index_all_tags(self, cursor):
        """모든 태그 인덱싱"""
        # Document tags
        cursor.execute("""
            INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
            SELECT 'tag', t.tag_name, dt.doc_id, NULL, t.tag_id
            FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
        """)

        logger.debug("Indexed all tags")

    def get_index_stats(self) -> Dict:
        """인덱스 통계"""
        conn = self.db.connect()
        cursor = conn.cursor()

        stats = {}

        # Count by type
        results = cursor.execute("""
            SELECT content_type, COUNT(*) as count
            FROM search_index
            GROUP BY content_type
        """).fetchall()

        for row in results:
            stats[row[0]] = row[1]

        stats['total'] = sum(stats.values())

        return stats
