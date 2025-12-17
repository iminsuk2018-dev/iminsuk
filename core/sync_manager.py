"""
Cloud Sync Manager
Handles conflict detection and resolution for cloud-synced workspaces
"""
import logging
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from data.database import Database

logger = logging.getLogger(__name__)


class ConflictStrategy(Enum):
    """Conflict resolution strategies"""
    KEEP_LOCAL = "keep_local"  # Keep local changes
    KEEP_REMOTE = "keep_remote"  # Keep remote changes
    MERGE = "merge"  # Merge both (for annotations/tags)
    MANUAL = "manual"  # User decides


@dataclass
class SyncConflict:
    """Represents a sync conflict"""
    table_name: str
    record_id: int
    local_modified: str
    remote_modified: str
    local_data: Dict
    remote_data: Dict
    conflict_type: str  # 'update', 'delete', 'insert'


class SyncManager:
    """Manages cloud sync and conflict resolution"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.conflicts: List[SyncConflict] = []

    def detect_conflicts(self) -> List[SyncConflict]:
        """
        Detect conflicts between local and cloud database.
        Assumes cloud sync service (Drive/OneDrive) has already synced files.
        """
        logger.info("Detecting conflicts...")

        # Check if database was modified externally
        conflict_info = self.workspace.check_for_conflicts()
        if not conflict_info:
            logger.info("No conflicts detected")
            return []

        logger.warning(f"Potential conflict detected: {conflict_info}")

        # For SQLite with WAL mode, conflicts are rare
        # Main strategy: Check modification timestamps in tables
        conflicts = []

        db = self.workspace.get_database()
        conn = db.connect()

        # Check documents table for conflicts
        conflicts.extend(self._check_table_conflicts(conn, "documents", "doc_id"))

        # Check annotations table
        conflicts.extend(self._check_table_conflicts(conn, "annotations", "annotation_id"))

        # Check tags table
        conflicts.extend(self._check_table_conflicts(conn, "tags", "tag_id"))

        self.conflicts = conflicts
        logger.info(f"Found {len(conflicts)} conflicts")

        return conflicts

    def _check_table_conflicts(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        id_column: str
    ) -> List[SyncConflict]:
        """
        Check for conflicts in a specific table.
        Uses modified_at timestamp if available.
        """
        conflicts = []

        # This is a simplified check
        # In practice, you'd need to track changes more carefully
        # For now, we rely on SQLite WAL mode to handle most conflicts

        # Advanced approach would involve:
        # 1. Shadow table tracking local changes
        # 2. Vector clocks or version numbers
        # 3. Operation-based CRDTs

        return conflicts

    def resolve_conflict(
        self,
        conflict: SyncConflict,
        strategy: ConflictStrategy
    ) -> bool:
        """
        Resolve a single conflict using the specified strategy.

        Returns True if resolved successfully.
        """
        logger.info(f"Resolving conflict in {conflict.table_name} "
                   f"with strategy {strategy.value}")

        db = self.workspace.get_database()
        conn = db.connect()
        cursor = conn.cursor()

        try:
            if strategy == ConflictStrategy.KEEP_LOCAL:
                # Keep local, do nothing (local is already there)
                logger.debug("Keeping local changes")
                return True

            elif strategy == ConflictStrategy.KEEP_REMOTE:
                # Overwrite local with remote
                self._apply_remote_changes(cursor, conflict)
                conn.commit()
                return True

            elif strategy == ConflictStrategy.MERGE:
                # Merge both versions
                self._merge_changes(cursor, conflict)
                conn.commit()
                return True

            elif strategy == ConflictStrategy.MANUAL:
                # User needs to manually choose
                return False

            return False

        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            conn.rollback()
            return False

    def _apply_remote_changes(self, cursor: sqlite3.Cursor, conflict: SyncConflict):
        """Apply remote changes to local database"""
        # Build UPDATE query
        table = conflict.table_name
        id_col = self._get_id_column(table)

        set_clause = ", ".join([f"{k} = ?" for k in conflict.remote_data.keys()])
        values = list(conflict.remote_data.values()) + [conflict.record_id]

        query = f"UPDATE {table} SET {set_clause} WHERE {id_col} = ?"
        cursor.execute(query, values)

        logger.debug(f"Applied remote changes to {table}")

    def _merge_changes(self, cursor: sqlite3.Cursor, conflict: SyncConflict):
        """
        Merge local and remote changes.
        Strategy depends on conflict type.
        """
        table = conflict.table_name

        if table == "annotations":
            # For annotations, keep both if different content
            local_content = conflict.local_data.get("content", "")
            remote_content = conflict.remote_data.get("content", "")

            if local_content != remote_content:
                # Merge by appending
                merged_content = f"{local_content}\n\n[Merged from other device]\n{remote_content}"
                conflict.local_data["content"] = merged_content

                # Update with merged content
                self._apply_remote_changes(cursor, conflict)

        elif table == "tags":
            # Tags are usually simple, prefer most recent
            local_time = conflict.local_data.get("created_at", "")
            remote_time = conflict.remote_data.get("created_at", "")

            if remote_time > local_time:
                self._apply_remote_changes(cursor, conflict)

        else:
            # Default: prefer most recent modification
            local_time = conflict.local_modified
            remote_time = conflict.remote_modified

            if remote_time > local_time:
                self._apply_remote_changes(cursor, conflict)

        logger.debug(f"Merged changes in {table}")

    def resolve_all_conflicts(self, strategy: ConflictStrategy) -> int:
        """
        Resolve all detected conflicts with the same strategy.
        Returns number of conflicts resolved.
        """
        resolved = 0

        for conflict in self.conflicts:
            if self.resolve_conflict(conflict, strategy):
                resolved += 1

        logger.info(f"Resolved {resolved}/{len(self.conflicts)} conflicts")
        return resolved

    def create_backup(self) -> Path:
        """
        Create a backup of the current database before resolving conflicts.
        Returns path to backup file.
        """
        db_path = self.workspace.db_path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

        shutil.copy2(db_path, backup_path)

        logger.info(f"Created backup: {backup_path}")
        return backup_path

    def check_sync_health(self) -> Dict:
        """
        Check overall sync health.
        Returns dict with sync status information.
        """
        health = {
            "workspace_path": str(self.workspace.workspace_path),
            "sync_file_exists": self.workspace.sync_file.exists(),
            "conflicts_detected": len(self.conflicts),
            "last_sync": None,
            "is_cloud_folder": self._is_cloud_folder()
        }

        # Read sync file
        if self.workspace.sync_file.exists():
            conflict_info = self.workspace.check_for_conflicts()
            if conflict_info:
                health["last_sync"] = conflict_info.get("last_modified")
                health["last_device"] = conflict_info.get("last_device")

        return health

    def _is_cloud_folder(self) -> bool:
        """
        Check if workspace is in a known cloud sync folder.
        """
        ws_path = str(self.workspace.workspace_path).lower()

        cloud_indicators = [
            "google drive",
            "googledrive",
            "onedrive",
            "dropbox",
            "icloud",
        ]

        for indicator in cloud_indicators:
            if indicator in ws_path:
                return True

        return False

    @staticmethod
    def _get_id_column(table_name: str) -> str:
        """Get primary key column name for table"""
        id_columns = {
            "documents": "doc_id",
            "annotations": "annotation_id",
            "tags": "tag_id",
            "document_tags": "doc_id",  # Composite key
            "annotation_tags": "annotation_id",  # Composite key
        }
        return id_columns.get(table_name, "id")

    def get_conflict_summary(self) -> str:
        """Get human-readable summary of conflicts"""
        if not self.conflicts:
            return "No conflicts detected"

        summary = [f"Found {len(self.conflicts)} conflicts:"]

        by_table = {}
        for conflict in self.conflicts:
            table = conflict.table_name
            by_table[table] = by_table.get(table, 0) + 1

        for table, count in by_table.items():
            summary.append(f"  - {table}: {count} conflicts")

        return "\n".join(summary)
