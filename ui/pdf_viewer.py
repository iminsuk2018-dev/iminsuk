"""
PDF Viewer widget using QGraphicsView
"""
import logging
from pathlib import Path
from typing import Optional

from qt_compat import (
    QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QtCore, QtGui, QtWidgets, Signal,
    Slot
)
from qt_compat import (
    QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QtCore, QtGui, QtWidgets, Signal,
    Slot
)

from config import PDF_DEFAULT_ZOOM, PDF_MIN_ZOOM, PDF_MAX_ZOOM, PDF_ZOOM_STEP
from data.pdf_handler import PDFHandler

logger = logging.getLogger(__name__)


class PDFViewer(QWidget):
    """PDF viewer widget with zoom and navigation controls"""

    # Signals
    page_changed = Signal(int)  # New page number
    zoom_changed = Signal(float)  # New zoom level

    def __init__(self):
        super().__init__()

        self.pdf_handler = PDFHandler()
        self.current_pdf_path: Optional[Path] = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = PDF_DEFAULT_ZOOM

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top toolbar
        toolbar = QHBoxLayout()

        # Page navigation
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self._on_previous_page)
        self.prev_button.setEnabled(False)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(self._on_page_changed)

        self.page_label = QLabel("/ 1")

        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self._on_next_page)
        self.next_button.setEnabled(False)

        toolbar.addWidget(self.prev_button)
        toolbar.addWidget(QLabel("Page:"))
        toolbar.addWidget(self.page_spin)
        toolbar.addWidget(self.page_label)
        toolbar.addWidget(self.next_button)

        toolbar.addStretch()

        # Zoom controls
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.zoom_out_button.setFixedWidth(30)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_in_button.setFixedWidth(30)

        self.fit_button = QPushButton("Fit Width")
        self.fit_button.clicked.connect(self._on_fit_width)

        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_button)

        layout.addLayout(toolbar)

        # Graphics view for PDF rendering
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.graphics_view)

    def load_pdf(self, pdf_path: Path):
        """Load PDF file"""
        self.current_pdf_path = Path(pdf_path)

        try:
            logger.info(f"Loading PDF: {pdf_path}")

            # Get page count
            self.total_pages = self.pdf_handler.get_page_count(pdf_path)
            logger.debug(f"  Total pages: {self.total_pages}")

            # Update UI
            self.page_spin.setMaximum(self.total_pages)
            self.page_label.setText(f"/ {self.total_pages}")
            self.page_spin.setValue(1)

            # Load first page
            self.current_page = 0
            logger.debug("  Rendering first page...")
            self._render_current_page()

            # Enable navigation
            self._update_navigation_buttons()

            logger.info(f"Successfully loaded PDF: {pdf_path.name} ({self.total_pages} pages)")

        except Exception as e:
            logger.error(f"Failed to load PDF: {e}", exc_info=True)
            raise

    def _render_current_page(self):
        """Render current page to graphics view"""
        if not self.current_pdf_path:
            logger.warning("No PDF loaded")
            return

        try:
            logger.debug(f"Rendering page {self.current_page + 1}/{self.total_pages} at {self.zoom_level}x")

            # Render page to image
            img_data = self.pdf_handler.render_page(
                self.current_pdf_path,
                self.current_page,
                self.zoom_level
            )
            logger.debug(f"  Got image data: {len(img_data)} bytes")

            # Convert to QPixmap
            image = QImage.fromData(img_data)
            if image.isNull():
                logger.error("  QImage is null! Image data may be corrupted")
                return

            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                logger.error("  QPixmap is null!")
                return

            logger.debug(f"  Pixmap size: {pixmap.width()}x{pixmap.height()}")

            # Clear scene and add pixmap
            self.graphics_scene.clear()
            pixmap_item = QGraphicsPixmapItem(pixmap)
            self.graphics_scene.addItem(pixmap_item)

            # Adjust scene size
            self.graphics_scene.setSceneRect(pixmap_item.boundingRect())

            logger.info(f"Successfully rendered page {self.current_page + 1}")

        except Exception as e:
            logger.error(f"Failed to render page: {e}", exc_info=True)

    def _on_previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_spin.setValue(self.current_page + 1)
            self._render_current_page()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)

    def _on_next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.page_spin.setValue(self.current_page + 1)
            self._render_current_page()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)

    def _on_page_changed(self, page: int):
        """Handle page number change from spinbox"""
        new_page = page - 1  # Convert to 0-based
        if 0 <= new_page < self.total_pages and new_page != self.current_page:
            self.current_page = new_page
            self._render_current_page()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)

    def _on_zoom_in(self):
        """Increase zoom"""
        new_zoom = min(self.zoom_level + PDF_ZOOM_STEP, PDF_MAX_ZOOM)
        self.set_zoom(new_zoom)

    def _on_zoom_out(self):
        """Decrease zoom"""
        new_zoom = max(self.zoom_level - PDF_ZOOM_STEP, PDF_MIN_ZOOM)
        self.set_zoom(new_zoom)

    def _on_fit_width(self):
        """Fit page to view width"""
        # TODO: Calculate zoom to fit width
        # For now, just set to 1.0
        self.set_zoom(1.0)

    def set_zoom(self, zoom: float):
        """Set zoom level"""
        self.zoom_level = max(PDF_MIN_ZOOM, min(zoom, PDF_MAX_ZOOM))
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        self._render_current_page()
        self.zoom_changed.emit(self.zoom_level)

    def _update_navigation_buttons(self):
        """Update navigation button states"""
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)

    def goto_page(self, page: int):
        """Go to specific page (0-based)"""
        if 0 <= page < self.total_pages:
            self.current_page = page
            self.page_spin.setValue(page + 1)
            self._render_current_page()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)

    def close_pdf(self):
        """Close current PDF"""
        self.current_pdf_path = None
        self.current_page = 0
        self.total_pages = 0
        self.graphics_scene.clear()
        self.page_spin.setMaximum(1)
        self.page_label.setText("/ 1")
        self._update_navigation_buttons()
