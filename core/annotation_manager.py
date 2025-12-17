"""
Annotation (메모/주석) 관리 비즈니스 로직
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path

from data.dao.annotation_dao import AnnotationDAO
from data.dao.tag_dao import TagDAO

logger = logging.getLogger(__name__)


class AnnotationManager:
    """메모/주석 관리 클래스"""

    def __init__(self, workspace):
        self.workspace = workspace
        db = workspace.get_database()
        self.annotation_dao = AnnotationDAO(db)
        self.tag_dao = TagDAO(db)

    def add_annotation(self, doc_id: int, page_number: int, content: str, **kwargs) -> int:
        """
        메모 추가

        Args:
            doc_id: 문서 ID
            page_number: 페이지 번호 (0-based)
            content: 메모 내용
            **kwargs: position_data, color, annotation_type 등

        Returns:
            annotation_id
        """
        # Validate content
        if not content or not content.strip():
            raise ValueError("Annotation content cannot be empty")

        # Create annotation
        annotation_id = self.annotation_dao.create(
            doc_id=doc_id,
            page_number=page_number,
            content=content.strip(),
            **kwargs
        )

        # Update FTS index
        self._update_search_index(annotation_id, doc_id, content)

        logger.info(f"Added annotation {annotation_id} to doc {doc_id}, page {page_number}")
        return annotation_id

    def update_annotation(self, annotation_id: int, content: str, **kwargs) -> None:
        """
        메모 수정

        Args:
            annotation_id: 메모 ID
            content: 새 내용
            **kwargs: color 등 기타 필드
        """
        if not content or not content.strip():
            raise ValueError("Annotation content cannot be empty")

        # Get annotation to find doc_id
        annotation = self.annotation_dao.get_by_id(annotation_id)
        if not annotation:
            raise ValueError(f"Annotation not found: {annotation_id}")

        # Update annotation
        self.annotation_dao.update(
            annotation_id=annotation_id,
            content=content.strip(),
            **kwargs
        )

        # Update FTS index
        self._update_search_index(annotation_id, annotation['doc_id'], content)

        logger.info(f"Updated annotation {annotation_id}")

    def delete_annotation(self, annotation_id: int) -> None:
        """메모 삭제"""
        # Remove from FTS index
        self._remove_from_search_index(annotation_id)

        # Delete annotation (cascades to tags)
        self.annotation_dao.delete(annotation_id)

        logger.info(f"Deleted annotation {annotation_id}")

    def get_annotation(self, annotation_id: int) -> Optional[Dict]:
        """메모 조회"""
        return self.annotation_dao.get_by_id(annotation_id)

    def get_document_annotations(self, doc_id: int) -> List[Dict]:
        """문서의 모든 메모 조회"""
        return self.annotation_dao.get_by_document(doc_id)

    def get_page_annotations(self, doc_id: int, page_number: int) -> List[Dict]:
        """특정 페이지의 메모 조회"""
        return self.annotation_dao.get_by_page(doc_id, page_number)

    def add_tag_to_annotation(self, annotation_id: int, tag_name: str) -> None:
        """메모에 태그 추가"""
        # Get or create tag
        tag_id = self.tag_dao.get_or_create(tag_name)

        # Add tag to annotation
        self.tag_dao.tag_annotation(annotation_id, tag_id)

        # Update FTS index with tag
        annotation = self.annotation_dao.get_by_id(annotation_id)
        if annotation:
            self._update_search_index_with_tag(annotation_id, annotation['doc_id'], tag_name)

        logger.info(f"Added tag '{tag_name}' to annotation {annotation_id}")

    def remove_tag_from_annotation(self, annotation_id: int, tag_id: int) -> None:
        """메모에서 태그 제거"""
        self.tag_dao.untag_annotation(annotation_id, tag_id)

        # TODO: Update FTS index (remove tag entry)

        logger.info(f"Removed tag {tag_id} from annotation {annotation_id}")

    def get_annotation_tags(self, annotation_id: int) -> List[Dict]:
        """메모의 태그 목록"""
        return self.tag_dao.get_annotation_tags(annotation_id)

    def _update_search_index(self, annotation_id: int, doc_id: int, content: str):
        """FTS 검색 인덱스 업데이트"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        # Remove existing entries for this annotation
        cursor.execute("""
            DELETE FROM search_index
            WHERE content_type = 'annotation' AND annotation_id = ?
        """, (annotation_id,))

        # Add new entry
        cursor.execute("""
            INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
            VALUES ('annotation', ?, ?, ?, NULL)
        """, (content, doc_id, annotation_id))

        conn.commit()
        logger.debug(f"Updated FTS index for annotation {annotation_id}")

    def _update_search_index_with_tag(self, annotation_id: int, doc_id: int, tag_name: str):
        """FTS 인덱스에 태그 추가"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
            VALUES ('tag', ?, ?, ?, NULL)
        """, (tag_name, doc_id, annotation_id))

        conn.commit()

    def _remove_from_search_index(self, annotation_id: int):
        """FTS 인덱스에서 제거"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM search_index WHERE annotation_id = ?
        """, (annotation_id,))

        conn.commit()
        logger.debug(f"Removed annotation {annotation_id} from FTS index")

    def count_annotations(self, doc_id: int) -> int:
        """문서의 메모 개수"""
        return self.annotation_dao.count_by_document(doc_id)
