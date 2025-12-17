"""
Tag 관리 비즈니스 로직
"""
import logging
from typing import List, Dict, Optional

from data.dao.tag_dao import TagDAO

logger = logging.getLogger(__name__)


class TagManager:
    """태그 관리 클래스"""

    def __init__(self, workspace):
        self.workspace = workspace
        db = workspace.get_database()
        self.tag_dao = TagDAO(db)

    def create_tag(self, tag_name: str, parent_id: int = None, color: str = None) -> int:
        """
        태그 생성

        Args:
            tag_name: 태그 이름
            parent_id: 부모 태그 ID (계층형 태그용)
            color: 태그 색상 (hex)

        Returns:
            tag_id
        """
        # Validate tag name
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")

        tag_name = tag_name.strip()

        # Check if already exists
        existing = self.tag_dao.get_by_name(tag_name)
        if existing:
            logger.warning(f"Tag '{tag_name}' already exists")
            return existing['tag_id']

        # Create tag
        tag_id = self.tag_dao.create(tag_name, parent_id, color)

        logger.info(f"Created tag: {tag_id} - {tag_name}")
        return tag_id

    def get_or_create_tag(self, tag_name: str, **kwargs) -> int:
        """태그가 있으면 반환, 없으면 생성"""
        tag_name = tag_name.strip()
        return self.tag_dao.get_or_create(tag_name, **kwargs)

    def get_tag(self, tag_id: int) -> Optional[Dict]:
        """태그 조회"""
        return self.tag_dao.get_by_id(tag_id)

    def get_tag_by_name(self, tag_name: str) -> Optional[Dict]:
        """이름으로 태그 조회"""
        return self.tag_dao.get_by_name(tag_name)

    def get_all_tags(self) -> List[Dict]:
        """모든 태그 조회"""
        return self.tag_dao.get_all()

    def update_tag(self, tag_id: int, **kwargs) -> None:
        """태그 수정 (이름, 색상 등)"""
        self.tag_dao.update(tag_id, **kwargs)
        logger.info(f"Updated tag: {tag_id}")

    def delete_tag(self, tag_id: int) -> None:
        """태그 삭제 (문서/메모 연결도 함께 삭제됨)"""
        self.tag_dao.delete(tag_id)
        logger.info(f"Deleted tag: {tag_id}")

    # Document tagging

    def tag_document(self, doc_id: int, tag_name: str) -> None:
        """
        문서에 태그 추가

        Args:
            doc_id: 문서 ID
            tag_name: 태그 이름 (없으면 자동 생성)
        """
        tag_id = self.get_or_create_tag(tag_name)
        self.tag_dao.tag_document(doc_id, tag_id)

        # Update FTS index
        self._add_tag_to_search_index(doc_id, tag_name, tag_id)

        logger.info(f"Tagged document {doc_id} with '{tag_name}'")

    def untag_document(self, doc_id: int, tag_id: int) -> None:
        """문서에서 태그 제거"""
        self.tag_dao.untag_document(doc_id, tag_id)

        # TODO: Remove from FTS index

        logger.info(f"Untagged document {doc_id} from tag {tag_id}")

    def get_document_tags(self, doc_id: int) -> List[Dict]:
        """문서의 태그 목록"""
        return self.tag_dao.get_document_tags(doc_id)

    def get_documents_by_tag(self, tag_id: int) -> List[int]:
        """특정 태그가 붙은 문서 ID 목록"""
        return self.tag_dao.get_documents_by_tag(tag_id)

    def bulk_tag_documents(self, doc_ids: List[int], tag_name: str) -> None:
        """여러 문서에 한 번에 태그 추가"""
        tag_id = self.get_or_create_tag(tag_name)

        for doc_id in doc_ids:
            self.tag_dao.tag_document(doc_id, tag_id)
            self._add_tag_to_search_index(doc_id, tag_name, tag_id)

        logger.info(f"Tagged {len(doc_ids)} documents with '{tag_name}'")

    # Annotation tagging

    def tag_annotation(self, annotation_id: int, tag_name: str) -> None:
        """메모에 태그 추가"""
        tag_id = self.get_or_create_tag(tag_name)
        self.tag_dao.tag_annotation(annotation_id, tag_id)

        logger.info(f"Tagged annotation {annotation_id} with '{tag_name}'")

    def untag_annotation(self, annotation_id: int, tag_id: int) -> None:
        """메모에서 태그 제거"""
        self.tag_dao.untag_annotation(annotation_id, tag_id)

        logger.info(f"Untagged annotation {annotation_id} from tag {tag_id}")

    def get_annotation_tags(self, annotation_id: int) -> List[Dict]:
        """메모의 태그 목록"""
        return self.tag_dao.get_annotation_tags(annotation_id)

    # Hierarchical tags (Phase 2)

    def get_tag_hierarchy(self) -> List[Dict]:
        """계층형 태그 트리 구조"""
        return self.tag_dao.get_tag_hierarchy()

    def get_child_tags(self, parent_tag_id: int) -> List[Dict]:
        """자식 태그 목록"""
        return self.tag_dao.get_children(parent_tag_id)

    # Tag statistics

    def get_tag_usage_stats(self) -> List[Dict]:
        """태그 사용 통계 (문서 개수 포함)"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT
                t.tag_id,
                t.tag_name,
                t.color,
                COUNT(DISTINCT dt.doc_id) as doc_count,
                COUNT(DISTINCT at.annotation_id) as annotation_count
            FROM tags t
            LEFT JOIN document_tags dt ON t.tag_id = dt.tag_id
            LEFT JOIN annotation_tags at ON t.tag_id = at.tag_id
            GROUP BY t.tag_id
            ORDER BY doc_count DESC, t.tag_name
        """).fetchall()

        return [dict(row) for row in results]

    def get_popular_tags(self, limit: int = 10) -> List[Dict]:
        """가장 많이 사용된 태그"""
        stats = self.get_tag_usage_stats()
        return stats[:limit]

    def search_tags(self, query: str) -> List[Dict]:
        """태그 이름 검색"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        results = cursor.execute("""
            SELECT * FROM tags
            WHERE tag_name LIKE ?
            ORDER BY tag_name
        """, (f"%{query}%",)).fetchall()

        return [dict(row) for row in results]

    # FTS index management

    def _add_tag_to_search_index(self, doc_id: int, tag_name: str, tag_id: int):
        """FTS 검색 인덱스에 태그 추가"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
            VALUES ('tag', ?, ?, NULL, ?)
        """, (tag_name, doc_id, tag_id))

        conn.commit()
        logger.debug(f"Added tag '{tag_name}' to FTS index for doc {doc_id}")

    def rebuild_tag_index(self):
        """태그 인덱스 재구축"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        # Remove all tag entries
        cursor.execute("DELETE FROM search_index WHERE content_type = 'tag'")

        # Re-add all document tags
        cursor.execute("""
            INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
            SELECT 'tag', t.tag_name, dt.doc_id, NULL, t.tag_id
            FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
        """)

        conn.commit()
        logger.info("Rebuilt tag index")
