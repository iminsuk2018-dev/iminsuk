"""
Configuration file for PDF Research App
"""
import os
from pathlib import Path
from typing import Optional

# Application Info
APP_NAME = "PDF Research Assistant"
APP_VERSION = "0.2.0"
APP_AUTHOR = "Research Team"

# Default Settings
DEFAULT_WORKSPACE_NAME = "MyResearch"

# Use environment variable for workspace directory if available (for deployment)
# Otherwise use default local path
if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER'):
    # Cloud deployment - use current directory
    DEFAULT_WORKSPACE_DIR = Path.cwd() / "workspace"
else:
    # Local development - use user's Documents folder
    DEFAULT_WORKSPACE_DIR = Path.home() / "Documents" / "PDFResearch"

# Database Settings
DB_NAME = "main.db"
DB_JOURNAL_MODE = "WAL"  # Write-Ahead Logging for better concurrency
DB_SYNCHRONOUS = "NORMAL"  # Balance between safety and speed
DB_CACHE_SIZE = 10000  # Number of pages to cache
DB_TEMP_STORE = "MEMORY"  # Store temp tables in memory

# Directory Names (relative to workspace root)
DIR_DATABASE = "database"
DIR_PDFS = "pdfs"
DIR_EXPORTS = "exports"
SYNC_FILE = ".pdfsync"

# UI Settings
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

# PDF Viewer Settings
PDF_DEFAULT_ZOOM = 1.0
PDF_MIN_ZOOM = 0.25
PDF_MAX_ZOOM = 4.0
PDF_ZOOM_STEP = 0.25
PDF_CACHE_PAGES = 5  # Number of pages to cache in memory

# Search Settings
SEARCH_MIN_QUERY_LENGTH = 2
SEARCH_MAX_RESULTS = 100
SEARCH_HIGHLIGHT_COLOR = "#FFFF00"

# Tag Settings
TAG_DEFAULT_COLOR = "#3498db"
TAG_MAX_NAME_LENGTH = 50

# Annotation Settings
ANNOTATION_DEFAULT_COLOR = "#FFFF00"
ANNOTATION_MAX_LENGTH = 10000

# Recommendation Settings
RECOMMENDATION_TOP_K = 20
RECOMMENDATION_MIN_SCORE = 0.3
RECOMMENDATION_CACHE_DAYS = 7
RECOMMENDATION_MAX_FEATURES = 5000  # For TF-IDF

# Journal API Settings
CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_RATE_LIMIT = 50  # requests per second
JOURNAL_FETCH_DAYS = 30  # Fetch articles from last N days
JOURNAL_FETCH_MAX = 100  # Maximum articles to fetch per request

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "app.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 3

# File Settings
PDF_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
SUPPORTED_PDF_EXTENSIONS = [".pdf"]

# Performance Settings
INDEXING_BATCH_SIZE = 10  # Number of documents to index at once
MAX_WORKER_THREADS = 4  # For background tasks


class AppConfig:
    """Runtime configuration manager"""

    def __init__(self):
        self._workspace_path: Optional[Path] = None
        self._settings = {}

    @property
    def workspace_path(self) -> Path:
        """Get current workspace path"""
        if self._workspace_path is None:
            # Load from settings or use default
            return DEFAULT_WORKSPACE_DIR
        return self._workspace_path

    @workspace_path.setter
    def workspace_path(self, path: Path):
        """Set workspace path"""
        self._workspace_path = Path(path)

    @property
    def db_path(self) -> Path:
        """Get database path"""
        return self.workspace_path / DIR_DATABASE / DB_NAME

    @property
    def pdf_dir(self) -> Path:
        """Get PDF storage directory"""
        return self.workspace_path / DIR_PDFS

    @property
    def export_dir(self) -> Path:
        """Get exports directory"""
        return self.workspace_path / DIR_EXPORTS

    @property
    def sync_file(self) -> Path:
        """Get sync metadata file path"""
        return self.workspace_path / SYNC_FILE

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set configuration value"""
        self._settings[key] = value


# Global config instance
config = AppConfig()
