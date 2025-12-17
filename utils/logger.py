"""
Logging configuration
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config import LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE, LOG_BACKUP_COUNT


def setup_logging(log_dir: Path = None):
    """
    Configure application logging.
    Logs to both console and rotating file.
    """

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG for troubleshooting
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_dir provided)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / LOG_FILE

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger
