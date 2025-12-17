"""
Database connection and schema management
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from config import DB_JOURNAL_MODE, DB_SYNCHRONOUS, DB_CACHE_SIZE, DB_TEMP_STORE

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Create or get database connection"""
        if self._connection is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
                timeout=30.0  # Wait up to 30 seconds for locks
            )

            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")

            # Configure for performance and concurrency
            self._connection.execute(f"PRAGMA journal_mode = {DB_JOURNAL_MODE}")
            self._connection.execute(f"PRAGMA synchronous = {DB_SYNCHRONOUS}")
            self._connection.execute(f"PRAGMA cache_size = {DB_CACHE_SIZE}")
            self._connection.execute(f"PRAGMA temp_store = {DB_TEMP_STORE}")

            # Row factory for dict-like access
            self._connection.row_factory = sqlite3.Row

            logger.info(f"Connected to database: {self.db_path}")

        return self._connection

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def initialize_schema(self):
        """Create all tables and indexes"""
        conn = self.connect()
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                year INTEGER,
                journal TEXT,
                doi TEXT,
                page_count INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                metadata TEXT
            )
        """)

        # Annotations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                annotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                position_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                color TEXT DEFAULT '#FFFF00',
                annotation_type TEXT DEFAULT 'note',
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Highlights table (for visual highlights/marks on PDF)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highlights (
                highlight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                width REAL NOT NULL,
                height REAL NOT NULL,
                color TEXT DEFAULT '#FFFF00',
                opacity REAL DEFAULT 0.3,
                highlight_type TEXT DEFAULT 'rectangle',
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Bookmarks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL UNIQUE,
                parent_tag_id INTEGER,
                color TEXT DEFAULT '#3498db',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_tag_id) REFERENCES tags(tag_id) ON DELETE SET NULL
            )
        """)

        # Document-Tag junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (doc_id, tag_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            )
        """)

        # Annotation-Tag junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS annotation_tags (
                annotation_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (annotation_id, tag_id),
                FOREIGN KEY (annotation_id) REFERENCES annotations(annotation_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            )
        """)

        # FTS5 virtual table for search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                content_type,
                content,
                doc_id UNINDEXED,
                annotation_id UNINDEXED,
                tag_id UNINDEXED,
                tokenize='porter unicode61'
            )
        """)

        # Favorite journals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorite_journals (
                journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_name TEXT NOT NULL UNIQUE,
                issn TEXT,
                api_source TEXT,
                update_frequency TEXT DEFAULT 'weekly',
                last_fetched TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Recommendation cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_cache (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_id INTEGER NOT NULL,
                article_title TEXT NOT NULL,
                article_abstract TEXT,
                article_authors TEXT,
                article_year INTEGER,
                article_doi TEXT,
                similarity_score REAL,
                reason TEXT,
                category TEXT DEFAULT 'general',
                common_keywords TEXT,
                status TEXT DEFAULT 'unread',
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (journal_id) REFERENCES favorite_journals(journal_id) ON DELETE CASCADE
            )
        """)

        # Add missing columns to existing table (migration)
        try:
            cursor.execute("ALTER TABLE recommendation_cache ADD COLUMN category TEXT DEFAULT 'general'")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE recommendation_cache ADD COLUMN common_keywords TEXT")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE recommendation_cache ADD COLUMN status TEXT DEFAULT 'unread'")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE recommendation_cache ADD COLUMN reviewed_at TIMESTAMP")
        except:
            pass

        # References table (extracted from PDFs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_references (
                reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                reference_text TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                year INTEGER,
                doi TEXT,
                reference_type TEXT,
                order_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Collections (Folders) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                parent_id INTEGER,
                color TEXT DEFAULT '#3498db',
                icon TEXT DEFAULT 'folder',
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES collections(collection_id) ON DELETE CASCADE
            )
        """)

        # Document-Collection junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_collections (
                doc_id INTEGER NOT NULL,
                collection_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (doc_id, collection_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (collection_id) REFERENCES collections(collection_id) ON DELETE CASCADE
            )
        """)

        # Watched folders table (for auto-import)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watched_folders (
                folder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL UNIQUE,
                collection_id INTEGER,
                auto_add INTEGER DEFAULT 1,
                recursive INTEGER DEFAULT 1,
                last_scanned TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(collection_id) ON DELETE SET NULL
            )
        """)

        # App settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_doc ON annotations(doc_id, page_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_doc ON highlights(doc_id, page_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_doc ON bookmarks(doc_id, page_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(tag_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_journal ON recommendation_cache(journal_id, fetched_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_references_doc ON document_references(doc_id, order_index)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_parent ON collections(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_order ON collections(order_index)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_watched_folders_active ON watched_folders(is_active)")

        conn.commit()
        logger.info("Database schema initialized successfully")

    def vacuum(self):
        """Optimize database"""
        conn = self.connect()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def get_schema_version(self) -> int:
        """Get current schema version"""
        cursor = self.connect().cursor()
        try:
            result = cursor.execute(
                "SELECT value FROM app_settings WHERE key = 'schema_version'"
            ).fetchone()
            return int(result[0]) if result else 0
        except sqlite3.OperationalError:
            return 0

    def set_schema_version(self, version: int):
        """Set schema version"""
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, modified_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                ("schema_version", str(version))
            )


def create_database(db_path: Path) -> Database:
    """Factory function to create and initialize database"""
    db = Database(db_path)
    db.initialize_schema()
    return db
