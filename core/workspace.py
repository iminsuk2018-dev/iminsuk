"""
Workspace management module
Handles workspace initialization, path management, and integrity checks
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import hashlib
import uuid

from config import DIR_DATABASE, DIR_PDFS, DIR_EXPORTS, SYNC_FILE, DB_NAME, APP_VERSION
from data.database import Database, create_database

logger = logging.getLogger(__name__)


class Workspace:
    """
    Workspace manages all data for the PDF research app.
    It can be placed in Google Drive, OneDrive, etc. for cloud sync.
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / DIR_DATABASE / DB_NAME
        self.pdf_dir = self.workspace_path / DIR_PDFS
        self.export_dir = self.workspace_path / DIR_EXPORTS
        self.sync_file = self.workspace_path / SYNC_FILE

        self._database: Optional[Database] = None
        self._device_id = self._get_or_create_device_id()

    def _get_or_create_device_id(self) -> str:
        """Get or create unique device identifier"""
        device_file = Path.home() / ".pdf_research_device_id"
        if device_file.exists():
            return device_file.read_text().strip()
        else:
            device_id = str(uuid.uuid4())
            device_file.write_text(device_id)
            return device_id

    def initialize(self) -> None:
        """
        Initialize workspace directory structure and database.
        Safe to call on existing workspace.
        """
        logger.info(f"Initializing workspace at: {self.workspace_path}")

        # Create directories
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        (self.workspace_path / DIR_DATABASE).mkdir(exist_ok=True)
        self.pdf_dir.mkdir(exist_ok=True)
        self.export_dir.mkdir(exist_ok=True)

        # Initialize database
        self._database = create_database(self.db_path)

        # Create or update sync file
        self._update_sync_file()

        logger.info("Workspace initialized successfully")

    def get_database(self) -> Database:
        """Get database instance"""
        if self._database is None:
            self._database = Database(self.db_path)
            self._database.connect()
        return self._database

    def get_relative_path(self, absolute_path: Path) -> str:
        """
        Convert absolute path to workspace-relative path.
        Used for storing paths in database.
        """
        absolute_path = Path(absolute_path)
        try:
            relative = absolute_path.relative_to(self.workspace_path)
            return str(relative).replace("\\", "/")  # Use forward slashes for cross-platform
        except ValueError:
            # Path is not under workspace
            logger.warning(f"Path {absolute_path} is not under workspace")
            return str(absolute_path)

    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert workspace-relative path to absolute path"""
        return self.workspace_path / relative_path

    def validate_integrity(self) -> Dict:
        """
        Validate integrity between database records and file system.
        Returns dict with validation results.
        """
        logger.info("Validating workspace integrity...")

        results = {
            "missing_files": [],
            "orphaned_files": [],
            "hash_mismatches": [],
            "total_documents": 0,
            "total_files": 0,
        }

        db = self.get_database()
        cursor = db.connect().cursor()

        # Get all documents from database
        docs = cursor.execute(
            "SELECT doc_id, file_path, file_hash FROM documents"
        ).fetchall()

        results["total_documents"] = len(docs)

        # Check if files exist and hashes match
        for doc in docs:
            file_path = self.get_absolute_path(doc["file_path"])
            if not file_path.exists():
                results["missing_files"].append({
                    "doc_id": doc["doc_id"],
                    "path": doc["file_path"]
                })
            else:
                # Verify hash
                actual_hash = self._compute_file_hash(file_path)
                if actual_hash != doc["file_hash"]:
                    results["hash_mismatches"].append({
                        "doc_id": doc["doc_id"],
                        "path": doc["file_path"],
                        "expected": doc["file_hash"],
                        "actual": actual_hash
                    })

        # Find orphaned PDF files
        if self.pdf_dir.exists():
            db_files = {self.get_absolute_path(doc["file_path"]) for doc in docs}
            for pdf_file in self.pdf_dir.glob("*.pdf"):
                results["total_files"] += 1
                if pdf_file not in db_files:
                    results["orphaned_files"].append(str(pdf_file.name))

        logger.info(f"Integrity check complete: {results}")
        return results

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _update_sync_file(self) -> None:
        """Update .pdfsync metadata file"""
        sync_data = {
            "workspace_version": APP_VERSION,
            "last_modified": datetime.now().isoformat(),
            "device_id": self._device_id,
            "db_path": str(self.db_path.relative_to(self.workspace_path)),
        }

        with open(self.sync_file, "w", encoding="utf-8") as f:
            json.dump(sync_data, f, indent=2)

        logger.debug(f"Updated sync file: {self.sync_file}")

    def check_for_conflicts(self) -> Optional[Dict]:
        """
        Check if workspace has been modified by another device.
        Returns conflict info if detected, None otherwise.
        """
        if not self.sync_file.exists():
            return None

        try:
            with open(self.sync_file, "r", encoding="utf-8") as f:
                sync_data = json.load(f)

            # Check if last modifier was a different device
            if sync_data.get("device_id") != self._device_id:
                return {
                    "last_device": sync_data.get("device_id"),
                    "last_modified": sync_data.get("last_modified"),
                    "version": sync_data.get("workspace_version"),
                }

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read sync file: {e}")

        return None

    def export_metadata(self, output_path: Path) -> None:
        """
        Export all metadata to JSON for backup/migration.
        Does not include PDF files.
        """
        db = self.get_database()
        cursor = db.connect().cursor()

        export_data = {
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(),
            "documents": [],
            "tags": [],
        }

        # Export documents
        docs = cursor.execute(
            "SELECT * FROM documents ORDER BY doc_id"
        ).fetchall()

        for doc in docs:
            doc_data = dict(doc)

            # Get tags for this document
            tags = cursor.execute(
                """
                SELECT t.tag_name
                FROM tags t
                JOIN document_tags dt ON t.tag_id = dt.tag_id
                WHERE dt.doc_id = ?
                """,
                (doc["doc_id"],)
            ).fetchall()
            doc_data["tags"] = [t["tag_name"] for t in tags]

            # Get annotations
            annotations = cursor.execute(
                "SELECT * FROM annotations WHERE doc_id = ?",
                (doc["doc_id"],)
            ).fetchall()
            doc_data["annotations"] = [dict(a) for a in annotations]

            export_data["documents"].append(doc_data)

        # Export all tags
        tags = cursor.execute("SELECT * FROM tags ORDER BY tag_id").fetchall()
        export_data["tags"] = [dict(t) for t in tags]

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Metadata exported to: {output_path}")

    def close(self):
        """Close workspace and database connection"""
        if self._database:
            self._database.close()
        self._update_sync_file()
        logger.info("Workspace closed")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
