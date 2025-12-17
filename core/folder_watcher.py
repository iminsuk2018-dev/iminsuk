"""
Folder Watcher
Monitors folders for new PDF files and auto-imports them
"""
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class FolderWatcher:
    """Watches folders for new PDF files"""

    def __init__(self, workspace):
        self.workspace = workspace

    def add_watched_folder(
        self,
        folder_path: Path,
        collection_id: Optional[int] = None,
        auto_add: bool = True,
        recursive: bool = True
    ) -> int:
        """
        Add a folder to watch for new PDFs.

        Args:
            folder_path: Path to watch
            collection_id: Optional collection to add files to
            auto_add: Automatically add new PDFs
            recursive: Watch subdirectories too

        Returns:
            folder_id
        """
        folder_path = Path(folder_path).resolve()

        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO watched_folders
                (folder_path, collection_id, auto_add, recursive, last_scanned, is_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            """, (str(folder_path), collection_id, int(auto_add), int(recursive)))

            folder_id = cursor.lastrowid

        logger.info(f"Added watched folder: {folder_path} (ID: {folder_id})")
        return folder_id

    def remove_watched_folder(self, folder_id: int) -> bool:
        """Remove a watched folder"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watched_folders WHERE folder_id = ?", (folder_id,))

        logger.info(f"Removed watched folder {folder_id}")
        return True

    def get_watched_folders(self, active_only: bool = True) -> List[Dict]:
        """Get all watched folders"""
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        if active_only:
            rows = cursor.execute("""
                SELECT * FROM watched_folders WHERE is_active = 1
                ORDER BY folder_path
            """).fetchall()
        else:
            rows = cursor.execute("""
                SELECT * FROM watched_folders
                ORDER BY folder_path
            """).fetchall()

        return [dict(row) for row in rows]

    def toggle_watched_folder(self, folder_id: int, is_active: bool) -> bool:
        """Enable/disable a watched folder"""
        db = self.workspace.get_database()

        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE watched_folders
                SET is_active = ?
                WHERE folder_id = ?
            """, (int(is_active), folder_id))

        logger.info(f"{'Enabled' if is_active else 'Disabled'} watched folder {folder_id}")
        return True

    def scan_folder(
        self,
        folder_id: int,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, int]:
        """
        Scan a watched folder for new PDFs.

        Args:
            folder_id: Folder to scan
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with counts: {'added': int, 'skipped': int, 'errors': int}
        """
        db = self.workspace.get_database()
        cursor = db.connect().cursor()

        # Get folder info
        folder_info = cursor.execute("""
            SELECT * FROM watched_folders WHERE folder_id = ?
        """, (folder_id,)).fetchone()

        if not folder_info:
            logger.error(f"Watched folder {folder_id} not found")
            return {'added': 0, 'skipped': 0, 'errors': 0}

        folder_path = Path(folder_info['folder_path'])
        collection_id = folder_info['collection_id']
        recursive = bool(folder_info['recursive'])

        if not folder_path.exists():
            logger.warning(f"Watched folder does not exist: {folder_path}")
            return {'added': 0, 'skipped': 0, 'errors': 0}

        # Find PDF files
        if recursive:
            pdf_files = list(folder_path.rglob('*.pdf'))
        else:
            pdf_files = list(folder_path.glob('*.pdf'))

        logger.info(f"Found {len(pdf_files)} PDF files in {folder_path}")

        stats = {'added': 0, 'skipped': 0, 'errors': 0}

        # Get existing file hashes
        existing_hashes = set()
        rows = cursor.execute("SELECT file_hash FROM documents").fetchall()
        for row in rows:
            existing_hashes.add(row[0])

        # Process each PDF
        for pdf_path in pdf_files:
            try:
                if progress_callback:
                    progress_callback(f"Processing: {pdf_path.name}")

                # Compute hash
                file_hash = self._compute_hash(pdf_path)

                # Skip if already exists
                if file_hash in existing_hashes:
                    stats['skipped'] += 1
                    logger.debug(f"Skipping duplicate: {pdf_path.name}")
                    continue

                # Import PDF (simplified - you'd integrate with document_manager)
                doc_id = self._import_pdf(pdf_path, file_hash, collection_id)

                if doc_id:
                    stats['added'] += 1
                    existing_hashes.add(file_hash)
                    logger.info(f"Imported: {pdf_path.name} (doc_id: {doc_id})")
                else:
                    stats['errors'] += 1

            except Exception as e:
                logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
                stats['errors'] += 1

        # Update last_scanned
        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE watched_folders
                SET last_scanned = CURRENT_TIMESTAMP
                WHERE folder_id = ?
            """, (folder_id,))

        logger.info(f"Scan complete: Added {stats['added']}, Skipped {stats['skipped']}, Errors {stats['errors']}")
        return stats

    def scan_all_folders(
        self,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, int]:
        """Scan all active watched folders"""
        folders = self.get_watched_folders(active_only=True)

        total_stats = {'added': 0, 'skipped': 0, 'errors': 0}

        for folder in folders:
            if progress_callback:
                progress_callback(f"Scanning folder: {folder['folder_path']}")

            stats = self.scan_folder(folder['folder_id'], progress_callback)

            total_stats['added'] += stats['added']
            total_stats['skipped'] += stats['skipped']
            total_stats['errors'] += stats['errors']

        return total_stats

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _import_pdf(
        self,
        pdf_path: Path,
        file_hash: str,
        collection_id: Optional[int]
    ) -> Optional[int]:
        """
        Import a PDF file into the library.
        This is a simplified version - integrate with DocumentManager for full import.
        """
        try:
            # Copy file to workspace
            dest_path = self.workspace.pdf_dir / pdf_path.name

            # Handle name conflicts
            counter = 1
            while dest_path.exists():
                dest_path = self.workspace.pdf_dir / f"{pdf_path.stem}_{counter}{pdf_path.suffix}"
                counter += 1

            import shutil
            shutil.copy2(pdf_path, dest_path)

            # Get relative path
            relative_path = self.workspace.get_relative_path(dest_path)

            # Basic metadata extraction
            from utils.pdf_extractor import PDFMetadataExtractor
            extractor = PDFMetadataExtractor()
            metadata = extractor.extract_all_metadata(dest_path)

            # Get page count
            from data.pdf_handler import PDFHandler
            pdf_handler = PDFHandler()
            page_count = pdf_handler.get_page_count(dest_path)

            # Get file size
            file_size = dest_path.stat().st_size

            # Insert into database
            db = self.workspace.get_database()
            with db.transaction() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO documents
                    (file_path, file_hash, title, authors, abstract, year, doi, page_count, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    relative_path,
                    file_hash,
                    metadata.get('title') or pdf_path.stem,
                    str(metadata.get('authors')) if metadata.get('authors') else None,
                    metadata.get('abstract'),
                    metadata.get('year'),
                    metadata.get('doi'),
                    page_count,
                    file_size
                ))

                doc_id = cursor.lastrowid

                # Add to collection if specified
                if collection_id:
                    cursor.execute("""
                        INSERT INTO document_collections (doc_id, collection_id)
                        VALUES (?, ?)
                    """, (doc_id, collection_id))

                # Index for search
                if metadata.get('title'):
                    cursor.execute("""
                        INSERT INTO search_index (content_type, content, doc_id)
                        VALUES ('title', ?, ?)
                    """, (metadata['title'], doc_id))

                if metadata.get('abstract'):
                    cursor.execute("""
                        INSERT INTO search_index (content_type, content, doc_id)
                        VALUES ('abstract', ?, ?)
                    """, (metadata['abstract'], doc_id))

            return doc_id

        except Exception as e:
            logger.error(f"Failed to import PDF {pdf_path}: {e}", exc_info=True)
            return None
