"""
PDF Night Mode Filter
Applies color filters to PDF for comfortable reading in dark mode
"""
import logging
from enum import Enum

from qt_compat import (
    QColor, QImage, QPainter, QtCore, QtGui
)

logger = logging.getLogger(__name__)


class PDFFilter(Enum):
    """Available PDF color filters"""
    NONE = "none"
    DARK = "dark"  # Invert colors
    SEPIA = "sepia"  # Warm tones
    GRAYSCALE = "grayscale"  # Black and white


class PDFNightModeFilter:
    """Applies night mode filters to PDF images"""

    @staticmethod
    def apply_filter(image: QImage, filter_type: PDFFilter) -> QImage:
        """
        Apply filter to PDF image.

        Args:
            image: Source QImage
            filter_type: PDFFilter enum

        Returns:
            Filtered QImage
        """
        if filter_type == PDFFilter.NONE:
            return image

        elif filter_type == PDFFilter.DARK:
            return PDFNightModeFilter._apply_dark_filter(image)

        elif filter_type == PDFFilter.SEPIA:
            return PDFNightModeFilter._apply_sepia_filter(image)

        elif filter_type == PDFFilter.GRAYSCALE:
            return PDFNightModeFilter._apply_grayscale_filter(image)

        return image

    @staticmethod
    def _apply_dark_filter(image: QImage) -> QImage:
        """
        Apply dark mode filter (invert colors).
        Makes white backgrounds dark and dark text light.
        """
        # Create a copy
        filtered = image.copy()

        # Invert colors
        filtered.invertPixels()

        # Reduce brightness slightly to avoid harsh whites
        painter = QPainter(filtered)
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.fillRect(filtered.rect(), QColor(230, 230, 230))
        painter.end()

        return filtered

    @staticmethod
    def _apply_sepia_filter(image: QImage) -> QImage:
        """
        Apply sepia filter for warm reading experience.
        """
        filtered = image.copy()

        width = filtered.width()
        height = filtered.height()

        for y in range(height):
            for x in range(width):
                color = QColor(filtered.pixel(x, y))

                r = color.red()
                g = color.green()
                b = color.blue()

                # Sepia formula
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)

                # Clamp values
                tr = min(255, tr)
                tg = min(255, tg)
                tb = min(255, tb)

                # Make it darker for night reading
                tr = int(tr * 0.8)
                tg = int(tg * 0.8)
                tb = int(tb * 0.8)

                filtered.setPixel(x, y, QColor(tr, tg, tb).rgb())

        return filtered

    @staticmethod
    def _apply_grayscale_filter(image: QImage) -> QImage:
        """
        Convert to grayscale.
        """
        return image.convertToFormat(QImage.Format_Grayscale8)

    @staticmethod
    def get_filter_description(filter_type: PDFFilter) -> str:
        """Get human-readable filter description"""
        descriptions = {
            PDFFilter.NONE: "No filter",
            PDFFilter.DARK: "Dark mode (inverted colors)",
            PDFFilter.SEPIA: "Sepia (warm tones)",
            PDFFilter.GRAYSCALE: "Grayscale"
        }
        return descriptions.get(filter_type, "Unknown")
