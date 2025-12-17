"""
Enhanced PDF Viewer with Highlights, Annotations, and Bookmarks
"""
import logging
from pathlib import Path
from typing import Optional, List

from qt_compat import (
    QBrush, QColor, QColorDialog, QComboBox, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsView, QImage, QKeySequence, QLabel, QPen, QPixmap, QPushButton,
    QRect, QRectF, QShortcut, QSpinBox, QToolBar, QVBoxLayout, QWidget, Qt, QtCore, QtGui,
    QtWidgets, Signal, Slot
)

from config import PDF_DEFAULT_ZOOM, PDF_MIN_ZOOM, PDF_MAX_ZOOM, PDF_ZOOM_STEP
from data.pdf_handler import PDFHandler
from core.highlight_manager import HighlightManager, Highlight
from ui.pdf_night_mode import PDFNightModeFilter, PDFFilter

logger = logging.getLogger(__name__)


class HighlightGraphicsView(QGraphicsView):
    """Custom QGraphicsView for drawing highlights"""

    highlight_drawn = Signal(QRectF)  # Emitted when user draws a highlight
    zoom_requested = Signal(int)  # Emitted when Ctrl+Wheel zoom is requested

    def __init__(self, parent=None):
        super().__init__(parent)

        self.drawing = False
        self.start_point = None
        self.current_rect: Optional[QGraphicsRectItem] = None
        self.highlight_mode = False  # Enable/disable highlight drawing

        # Drawing pen
        self.draw_pen = QPen(QColor(255, 255, 0, 128), 2, Qt.DashLine)
        self.draw_brush = QBrush(QColor(255, 255, 0, 50))

    def set_highlight_mode(self, enabled: bool):
        """Enable/disable highlight drawing mode"""
        self.highlight_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if self.highlight_mode and event.button() == Qt.LeftButton:
            # Start drawing highlight
            self.drawing = True
            self.start_point = self.mapToScene(event.pos())

            # Create temporary rectangle
            self.current_rect = QGraphicsRectItem()
            self.current_rect.setPen(self.draw_pen)
            self.current_rect.setBrush(self.draw_brush)
            self.scene().addItem(self.current_rect)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing and self.current_rect:
            # Update rectangle while dragging
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_rect.setRect(rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drawing and event.button() == Qt.LeftButton:
            self.drawing = False

            if self.current_rect:
                final_rect = self.current_rect.rect()

                # Only emit if rectangle has meaningful size
                if final_rect.width() > 5 and final_rect.height() > 5:
                    self.highlight_drawn.emit(final_rect)

                # Remove temporary rectangle
                self.scene().removeItem(self.current_rect)
                self.current_rect = None

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Handle wheel events for zoom (Ctrl+Wheel) or scrolling"""
        # Check if Ctrl is pressed
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+Wheel = Zoom
            delta = event.angleDelta().y()
            self.zoom_requested.emit(delta)
            event.accept()
        else:
            # Normal scrolling
            super().wheelEvent(event)


class EnhancedPDFViewer(QWidget):
    """Enhanced PDF viewer with highlights, annotations, and bookmarks"""

    # Signals
    page_changed = Signal(int)  # New page number
    zoom_changed = Signal(float)  # New zoom level
    highlight_added = Signal(Highlight)  # New highlight created
    bookmark_toggled = Signal(int, bool)  # page_number, is_bookmarked

    def __init__(self, workspace=None):
        super().__init__()

        self.workspace = workspace
        self.pdf_handler = PDFHandler()
        self.highlight_manager: Optional[HighlightManager] = None

        if workspace:
            self.highlight_manager = HighlightManager(workspace)

        self.current_pdf_path: Optional[Path] = None
        self.current_doc_id: Optional[int] = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = PDF_DEFAULT_ZOOM

        # Current highlights on page
        self.current_highlights: List[Highlight] = []
        self.highlight_items: List[QGraphicsRectItem] = []

        # Current highlight color
        self.highlight_color = QColor(255, 255, 0)  # Yellow

        # PDF filter
        self.pdf_filter = PDFFilter.NONE

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top toolbar
        toolbar = QToolBar()

        # Page navigation
        self.prev_button = QPushButton("◀")
        self.prev_button.clicked.connect(self._on_previous_page)
        self.prev_button.setEnabled(False)
        self.prev_button.setToolTip("Previous Page")

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setToolTip("Jump to page number")
        self.page_spin.valueChanged.connect(self._on_page_changed)

        self.page_label = QLabel("/ 1")

        self.next_button = QPushButton("▶")
        self.next_button.clicked.connect(self._on_next_page)
        self.next_button.setEnabled(False)
        self.next_button.setToolTip("Next Page")

        toolbar.addWidget(self.prev_button)
        toolbar.addWidget(QLabel("Page:"))
        toolbar.addWidget(self.page_spin)
        toolbar.addWidget(self.page_label)
        toolbar.addWidget(self.next_button)

        toolbar.addSeparator()

        # Zoom controls
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_out_button.setToolTip("Zoom Out")

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_in_button.setFixedWidth(30)
        self.zoom_in_button.setToolTip("Zoom In")

        self.fit_button = QPushButton("Fit")
        self.fit_button.setToolTip("Fit page to window width")
        self.fit_button.clicked.connect(self._on_fit_width)

        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_button)

        toolbar.addSeparator()

        # Highlight tools
        self.highlight_button = QPushButton("Highlight")
        self.highlight_button.setCheckable(True)
        self.highlight_button.clicked.connect(self._on_toggle_highlight_mode)
        self.highlight_button.setToolTip("Toggle Highlight Mode (H)")

        self.color_button = QPushButton("Color")
        self.color_button.clicked.connect(self._on_choose_color)
        self.color_button.setToolTip("Choose Highlight Color")

        toolbar.addWidget(self.highlight_button)
        toolbar.addWidget(self.color_button)

        toolbar.addSeparator()

        # Bookmark button
        self.bookmark_button = QPushButton("★ Bookmark")
        self.bookmark_button.setCheckable(True)
        self.bookmark_button.clicked.connect(self._on_toggle_bookmark)
        self.bookmark_button.setToolTip("Toggle Bookmark (B)")

        toolbar.addWidget(self.bookmark_button)

        toolbar.addSeparator()

        # PDF Filter
        filter_label = QLabel("Filter:")
        toolbar.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("None", PDFFilter.NONE)
        self.filter_combo.addItem("Dark Mode", PDFFilter.DARK)
        self.filter_combo.addItem("Sepia", PDFFilter.SEPIA)
        self.filter_combo.addItem("Grayscale", PDFFilter.GRAYSCALE)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setToolTip("PDF Color Filter")
        toolbar.addWidget(self.filter_combo)

        toolbar.addSeparator()

        # Fullscreen button
        self.fullscreen_button = QPushButton("Fullscreen")
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.clicked.connect(self._on_toggle_fullscreen)
        self.fullscreen_button.setToolTip("Toggle Fullscreen (F11)")

        toolbar.addWidget(self.fullscreen_button)

        layout.addWidget(toolbar)

        # Graphics view for PDF rendering
        self.graphics_view = HighlightGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setAlignment(Qt.AlignCenter)

        # Connect highlight drawing signal
        self.graphics_view.highlight_drawn.connect(self._on_highlight_drawn)

        # Connect zoom wheel signal
        self.graphics_view.zoom_requested.connect(self._on_wheel_zoom)

        layout.addWidget(self.graphics_view)

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Highlight mode: H
        highlight_shortcut = QShortcut(QKeySequence("H"), self)
        highlight_shortcut.activated.connect(self.highlight_button.click)

        # Bookmark: B
        bookmark_shortcut = QShortcut(QKeySequence("B"), self)
        bookmark_shortcut.activated.connect(self.bookmark_button.click)

        # Fullscreen: F11
        fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        fullscreen_shortcut.activated.connect(self.fullscreen_button.click)

        # Page navigation
        prev_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        prev_shortcut.activated.connect(self._on_previous_page)

        next_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        next_shortcut.activated.connect(self._on_next_page)

    def load_pdf(self, pdf_path: Path, doc_id: int):
        """Load PDF file"""
        self.current_pdf_path = Path(pdf_path)
        self.current_doc_id = doc_id

        try:
            logger.info(f"Loading PDF: {pdf_path}")

            # Get page count
            self.total_pages = self.pdf_handler.get_page_count(pdf_path)

            # Update UI
            self.page_spin.setMaximum(self.total_pages)
            self.page_label.setText(f"/ {self.total_pages}")
            self.page_spin.setValue(1)

            # Load first page
            self.current_page = 0
            self._render_current_page()

            # Enable navigation
            self._update_navigation_buttons()

            logger.info(f"Successfully loaded PDF: {pdf_path.name}")

        except Exception as e:
            logger.error(f"Failed to load PDF: {e}", exc_info=True)
            raise

    def _render_current_page(self):
        """Render current page with highlights and annotations"""
        if not self.current_pdf_path:
            return

        try:
            # Render page to image
            img_data = self.pdf_handler.render_page(
                self.current_pdf_path,
                self.current_page,
                self.zoom_level
            )

            # Convert to QImage
            image = QImage.fromData(img_data)

            # Apply PDF filter
            if self.pdf_filter != PDFFilter.NONE:
                image = PDFNightModeFilter.apply_filter(image, self.pdf_filter)

            # Convert to QPixmap
            pixmap = QPixmap.fromImage(image)

            # Clear scene and add pixmap
            self.graphics_scene.clear()
            self.highlight_items.clear()

            pixmap_item = QGraphicsPixmapItem(pixmap)
            self.graphics_scene.addItem(pixmap_item)

            # Adjust scene size
            self.graphics_scene.setSceneRect(pixmap_item.boundingRect())

            # Load and draw highlights
            if self.highlight_manager and self.current_doc_id:
                self._load_highlights()

            logger.info(f"Rendered page {self.current_page + 1}")

        except Exception as e:
            logger.error(f"Failed to render page: {e}", exc_info=True)

    def _load_highlights(self):
        """Load highlights for current page and draw them"""
        self.current_highlights = self.highlight_manager.get_page_highlights(
            self.current_doc_id,
            self.current_page
        )

        # Get pixmap dimensions
        pixmap_item = self.graphics_scene.items()[0]  # First item is pixmap
        pixmap_rect = pixmap_item.boundingRect()

        for highlight in self.current_highlights:
            # Convert normalized coords to actual coords
            x = highlight.x * pixmap_rect.width()
            y = highlight.y * pixmap_rect.height()
            width = highlight.width * pixmap_rect.width()
            height = highlight.height * pixmap_rect.height()

            # Create highlight rectangle
            rect_item = QGraphicsRectItem(x, y, width, height)

            color = QColor(highlight.color)
            color.setAlphaF(highlight.opacity)

            rect_item.setBrush(QBrush(color))
            rect_item.setPen(QPen(Qt.NoPen))

            self.graphics_scene.addItem(rect_item)
            self.highlight_items.append(rect_item)

    def _on_highlight_drawn(self, rect: QRectF):
        """Handle user drawing a new highlight"""
        if not self.highlight_manager or not self.current_doc_id:
            logger.warning("Cannot add highlight: no document loaded")
            return

        # Get pixmap dimensions for normalization
        pixmap_item = self.graphics_scene.items()[0]
        pixmap_rect = pixmap_item.boundingRect()

        # Normalize coordinates (0-1)
        x = rect.x() / pixmap_rect.width()
        y = rect.y() / pixmap_rect.height()
        width = rect.width() / pixmap_rect.width()
        height = rect.height() / pixmap_rect.height()

        # Add to database
        highlight_id = self.highlight_manager.add_highlight(
            doc_id=self.current_doc_id,
            page_number=self.current_page,
            x=x,
            y=y,
            width=width,
            height=height,
            color=self.highlight_color.name(),
            opacity=0.3
        )

        # Reload highlights to show the new one
        self._load_highlights()

        logger.info(f"Added highlight {highlight_id}")

    def _on_toggle_highlight_mode(self, checked: bool):
        """Toggle highlight drawing mode"""
        self.graphics_view.set_highlight_mode(checked)

    def _on_choose_color(self):
        """Choose highlight color"""
        color = QColorDialog.getColor(self.highlight_color, self, "Choose Highlight Color")
        if color.isValid():
            self.highlight_color = color

    def _on_toggle_bookmark(self, checked: bool):
        """Toggle bookmark for current page"""
        if self.current_doc_id is not None:
            self.bookmark_toggled.emit(self.current_page, checked)

    def _on_filter_changed(self, index: int):
        """Handle PDF filter change"""
        filter_data = self.filter_combo.currentData()
        self.pdf_filter = filter_data
        self._render_current_page()
        logger.info(f"PDF filter changed to: {filter_data.value}")

    def _on_toggle_fullscreen(self, checked: bool):
        """Toggle fullscreen mode"""
        if checked:
            self.window().showFullScreen()
        else:
            self.window().showNormal()

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
        self.set_zoom(1.0)

    def _on_wheel_zoom(self, delta: int):
        """Handle Ctrl+Wheel zoom"""
        if delta > 0:
            # Wheel up = Zoom in
            self._on_zoom_in()
        else:
            # Wheel down = Zoom out
            self._on_zoom_out()

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
