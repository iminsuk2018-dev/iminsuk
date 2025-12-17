"""
Document 관리 비즈니스 로직
"""
import logging
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional

from data.dao.document_dao import DocumentDAO
from data.pdf_handler import PDFHandler
from utils.pdf_extractor import PDFMetadataExtractor

logger = logging.getLogger(__name__)


class DocumentManager:
    """문서 관리 클래스"""

    def __init__(self, workspace):
        self.workspace = workspace
        db = workspace.get_database()
        self.document_dao = DocumentDAO(db)
        self.pdf_handler = PDFHandler()
        self.metadata_extractor = PDFMetadataExtractor()

    def add_document(self, pdf_path: Path, auto_extract: bool = True) -> int:
        """
        PDF 문서 추가

        Args:
            pdf_path: PDF 파일 경로
            auto_extract: 자동으로 메타데이터 추출 여부

        Returns:
            doc_id
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Compute file hash
        file_hash = self._compute_file_hash(pdf_path)

        # Check for duplicates
        existing = self.document_dao.get_by_hash(file_hash)
        if existing:
            logger.warning(f"Duplicate PDF detected: {existing['title']}")
            raise ValueError(f"This PDF already exists: {existing['title']}")

        # Copy PDF to workspace
        dest_path = self._copy_to_workspace(pdf_path)

        # Get relative path
        relative_path = self.workspace.get_relative_path(dest_path)

        # Extract metadata
        metadata = {}
        if auto_extract:
            logger.info("Extracting metadata...")
            metadata = self.metadata_extractor.extract_all_metadata(dest_path)

        # Get page count and file size
        page_count = self.pdf_handler.get_page_count(dest_path)
        file_size = dest_path.stat().st_size

        # Create document record
        doc_id = self.document_dao.create(
            file_path=relative_path,
            file_hash=file_hash,
            title=metadata.get('title') or pdf_path.stem,
            authors=str(metadata.get('authors')) if metadata.get('authors') else None,
            abstract=metadata.get('abstract'),
            year=metadata.get('year'),
            doi=metadata.get('doi'),
            page_count=page_count,
            file_size=file_size
        )

        # Update search index
        self._update_search_index(doc_id, metadata)

        logger.info(f"Added document {doc_id}: {metadata.get('title') or pdf_path.name}")
        return doc_id

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """문서 조회"""
        return self.document_dao.get_by_id(doc_id)

    def get_all_documents(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """모든 문서 조회"""
        return self.document_dao.get_all(limit, offset)

    def update_metadata(self, doc_id: int, **kwargs) -> None:
        """메타데이터 수정"""
        self.document_dao.update(doc_id, **kwargs)

        # Update search index if title or abstract changed
        if 'title' in kwargs or 'abstract' in kwargs:
            doc = self.document_dao.get_by_id(doc_id)
            if doc:
                self._update_search_index(doc_id, doc)

        logger.info(f"Updated document {doc_id}")

    def delete_document(self, doc_id: int, delete_file: bool = False) -> None:
        """
        문서 삭제

        Args:
            doc_id: 문서 ID
            delete_file: PDF 파일도 삭제할지 여부
        """
        doc = self.document_dao.get_by_id(doc_id)

        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        # Remove from search index
        self._remove_from_search_index(doc_id)

        # Delete database record (cascades to annotations and tags)
        self.document_dao.delete(doc_id)

        # Optionally delete file
        if delete_file:
            pdf_path = self.workspace.get_absolute_path(doc['file_path'])
            if pdf_path.exists():
                pdf_path.unlink()
                logger.info(f"Deleted file: {pdf_path}")

        logger.info(f"Deleted document {doc_id}")

    def search_documents(self, **filters) -> List[Dict]:
        """문서 검색 (필터 기반)"""
        return self.document_dao.search(**filters)

    def get_document_count(self) -> int:
        """전체 문서 개수"""
        return self.document_dao.count()

    def get_documents_with_tag(self, tag_id: int) -> List[Dict]:
        """특정 태그가 있는 문서 조회"""
        from core.tag_manager import TagManager

        tag_manager = TagManager(self.workspace)
        doc_ids = tag_manager.get_documents_by_tag(tag_id)

        documents = []
        for doc_id in doc_ids:
            doc = self.document_dao.get_by_id(doc_id)
            if doc:
                documents.append(doc)

        return documents

    def get_user_corpus(self) -> List[Dict]:
        """
        추천 시스템용 사용자 문서 코퍼스 생성

        Returns:
            List of dicts with title, abstract, tags, annotations
        """
        from core.annotation_manager import AnnotationManager
        from core.tag_manager import TagManager

        annotation_manager = AnnotationManager(self.workspace)
        tag_manager = TagManager(self.workspace)

        documents = self.get_all_documents()
        corpus = []

        for doc in documents:
            # Get tags
            tags = tag_manager.get_document_tags(doc['doc_id'])
            tag_names = [tag['tag_name'] for tag in tags]

            # Get annotations
            annotations = annotation_manager.get_document_annotations(doc['doc_id'])
            annotation_texts = [ann['content'] for ann in annotations]

            corpus.append({
                'doc_id': doc['doc_id'],
                'title': doc.get('title', ''),
                'abstract': doc.get('abstract', ''),
                'tags': tag_names,
                'annotations': annotation_texts,
                'year': doc.get('year'),
                'authors': doc.get('authors')
            })

        logger.debug(f"Generated corpus with {len(corpus)} documents")
        return corpus

    def _copy_to_workspace(self, pdf_path: Path) -> Path:
        """PDF를 workspace로 복사"""
        dest_path = self.workspace.pdf_dir / pdf_path.name

        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            dest_path = self.workspace.pdf_dir / f"{pdf_path.stem}_{counter}{pdf_path.suffix}"
            counter += 1

        shutil.copy2(pdf_path, dest_path)
        logger.debug(f"Copied PDF to: {dest_path}")

        return dest_path

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """파일 해시 계산"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _update_search_index(self, doc_id: int, metadata: dict):
        """검색 인덱스 업데이트"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        # Remove existing entries
        cursor.execute("""
            DELETE FROM search_index
            WHERE doc_id = ? AND content_type IN ('title', 'abstract')
        """, (doc_id,))

        # Add title
        if metadata.get('title'):
            cursor.execute("""
                INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                VALUES ('title', ?, ?, NULL, NULL)
            """, (metadata['title'], doc_id))

        # Add abstract
        if metadata.get('abstract'):
            cursor.execute("""
                INSERT INTO search_index (content_type, content, doc_id, annotation_id, tag_id)
                VALUES ('abstract', ?, ?, NULL, NULL)
            """, (metadata['abstract'], doc_id))

        conn.commit()
        logger.debug(f"Updated search index for document {doc_id}")

    def _remove_from_search_index(self, doc_id: int):
        """검색 인덱스에서 제거"""
        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM search_index WHERE doc_id = ?", (doc_id,))
        conn.commit()

        logger.debug(f"Removed document {doc_id} from search index")
