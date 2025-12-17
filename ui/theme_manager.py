"""
Theme Manager
Handles light/dark mode and theme switching
"""
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

from qt_compat import (
    QApplication, QColor, QPalette, QSettings, QtCore, QtGui, QtWidgets
)

logger = logging.getLogger(__name__)


class Theme(Enum):
    """Available themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system


class ThemeManager:
    """Manages application themes"""

    def __init__(self, app: QApplication):
        self.app = app
        self.settings = QSettings("PDFResearch", "Theme")
        self.current_theme = Theme.LIGHT

        # Load saved theme
        saved_theme = self.settings.value("theme", "light")
        try:
            self.current_theme = Theme(saved_theme)
        except ValueError:
            self.current_theme = Theme.LIGHT

    def get_current_theme(self) -> Theme:
        """Get current theme"""
        return self.current_theme

    def set_theme(self, theme: Theme):
        """Set and apply theme"""
        self.current_theme = theme
        self.settings.setValue("theme", theme.value)

        if theme == Theme.AUTO:
            # TODO: Detect system theme
            # For now, default to light
            self._apply_light_theme()
        elif theme == Theme.DARK:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

        logger.info(f"Applied theme: {theme.value}")

    def _apply_light_theme(self):
        """Apply light theme"""
        # Reset to default palette
        self.app.setPalette(self.app.style().standardPalette())

        # Try to load modern QSS first (optimized for wide monitors)
        stylesheet = self._load_qss_file("modern_light.qss")
        if not stylesheet:
            # Fallback to built-in stylesheet
            stylesheet = self._get_light_stylesheet()

        self.app.setStyleSheet(stylesheet)

    def _apply_dark_theme(self):
        """Apply dark theme"""
        # Create dark palette
        dark_palette = QPalette()

        # Window colors
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.WindowText, QColor(245, 245, 247))

        # Base colors
        dark_palette.setColor(QPalette.Base, QColor(44, 44, 46))
        dark_palette.setColor(QPalette.AlternateBase, QColor(58, 58, 60))

        # Text colors
        dark_palette.setColor(QPalette.Text, QColor(245, 245, 247))
        dark_palette.setColor(QPalette.PlaceholderText, QColor(152, 152, 157))

        # Button colors
        dark_palette.setColor(QPalette.Button, QColor(44, 44, 46))
        dark_palette.setColor(QPalette.ButtonText, QColor(245, 245, 247))

        # Bright text
        dark_palette.setColor(QPalette.BrightText, QColor(255, 69, 58))

        # Highlight colors
        dark_palette.setColor(QPalette.Highlight, QColor(10, 132, 255))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        # Link colors
        dark_palette.setColor(QPalette.Link, QColor(10, 132, 255))
        dark_palette.setColor(QPalette.LinkVisited, QColor(191, 90, 242))

        # Tooltip colors
        dark_palette.setColor(QPalette.ToolTipBase, QColor(245, 245, 247))
        dark_palette.setColor(QPalette.ToolTipText, QColor(29, 29, 31))

        # Disabled colors
        dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(99, 99, 102))
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(99, 99, 102))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(99, 99, 102))

        self.app.setPalette(dark_palette)

        # Try to load modern QSS first (optimized for wide monitors)
        stylesheet = self._load_qss_file("modern_dark.qss")
        if not stylesheet:
            # Fallback to built-in stylesheet
            stylesheet = self._get_dark_stylesheet()

        self.app.setStyleSheet(stylesheet)

    def _get_light_stylesheet(self) -> str:
        """Get light theme stylesheet"""
        return """
            QMainWindow {
                background-color: #f5f5f5;
            }

            QMenuBar {
                background-color: #ffffff;
                color: #000000;
            }

            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }

            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }

            QMenu::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QToolBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #cccccc;
                spacing: 3px;
                padding: 3px;
            }

            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px 15px;
                color: #000000;
            }

            QPushButton:hover {
                background-color: #d0d0d0;
            }

            QPushButton:pressed {
                background-color: #c0c0c0;
            }

            QPushButton:checked {
                background-color: #2a82da;
                color: #ffffff;
            }

            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                color: #000000;
            }

            QListWidget::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QTextEdit, QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                color: #000000;
            }

            QLineEdit, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px;
                color: #000000;
            }

            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }

            QGroupBox::title {
                color: #000000;
            }

            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }

            QTabBar::tab {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 5px 10px;
            }

            QTabBar::tab:selected {
                background-color: #ffffff;
            }

            QStatusBar {
                background-color: #f0f0f0;
                color: #000000;
            }
        """

    def _get_dark_stylesheet(self) -> str:
        """Get dark theme stylesheet"""
        return """
            QMainWindow {
                background-color: #2b2b2b;
            }

            QMenuBar {
                background-color: #353535;
                color: #ffffff;
            }

            QMenuBar::item:selected {
                background-color: #454545;
            }

            QMenu {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
            }

            QMenu::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QToolBar {
                background-color: #353535;
                border-bottom: 1px solid #555555;
                spacing: 3px;
                padding: 3px;
            }

            QPushButton {
                background-color: #454545;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                color: #ffffff;
            }

            QPushButton:hover {
                background-color: #505050;
            }

            QPushButton:pressed {
                background-color: #3a3a3a;
            }

            QPushButton:checked {
                background-color: #2a82da;
                color: #ffffff;
            }

            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #808080;
            }

            QListWidget {
                background-color: #232323;
                border: 1px solid #555555;
                color: #ffffff;
            }

            QListWidget::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QTextEdit, QTextBrowser {
                background-color: #232323;
                border: 1px solid #555555;
                color: #ffffff;
            }

            QLineEdit, QSpinBox {
                background-color: #232323;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
            }

            QComboBox {
                background-color: #454545;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
            }

            QComboBox::drop-down {
                border: none;
            }

            QComboBox QAbstractItemView {
                background-color: #353535;
                color: #ffffff;
                selection-background-color: #2a82da;
            }

            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }

            QGroupBox::title {
                color: #ffffff;
            }

            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }

            QTabBar::tab {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px 10px;
            }

            QTabBar::tab:selected {
                background-color: #2b2b2b;
            }

            QStatusBar {
                background-color: #353535;
                color: #ffffff;
            }

            QLabel {
                color: #ffffff;
            }

            QCheckBox {
                color: #ffffff;
            }

            QRadioButton {
                color: #ffffff;
            }

            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
            }

            QProgressBar::chunk {
                background-color: #2a82da;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 15px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 7px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }

            QScrollBar:horizontal {
                background-color: #2b2b2b;
                height: 15px;
                border: none;
            }

            QScrollBar::handle:horizontal {
                background-color: #555555;
                border-radius: 7px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #666666;
            }

            QScrollBar::add-line, QScrollBar::sub-line {
                background: none;
                border: none;
            }

            QSplitter::handle {
                background-color: #555555;
            }

            QSplitter::handle:hover {
                background-color: #666666;
            }
        """

    def _load_qss_file(self, filename: str) -> Optional[str]:
        """
        Load QSS file from styles directory

        Args:
            filename: QSS filename (e.g., 'apple_light.qss')

        Returns:
            QSS content or None if file not found
        """
        # Try multiple possible paths
        possible_paths = [
            Path(__file__).parent.parent / "styles" / filename,
            Path(__file__).parent / "styles" / filename,
            Path.cwd() / "styles" / filename
        ]

        for qss_path in possible_paths:
            if qss_path.exists():
                try:
                    with open(qss_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"Loaded QSS file: {qss_path}")
                    return content
                except Exception as e:
                    logger.error(f"Failed to read QSS file {qss_path}: {e}")
                    continue

        logger.warning(f"QSS file not found: {filename}")
        return None

    def toggle_theme(self):
        """Toggle between light and dark"""
        if self.current_theme == Theme.DARK:
            self.set_theme(Theme.LIGHT)
        else:
            self.set_theme(Theme.DARK)
