"""
Recommendations Panel - Big Tech News Style
Shows automatically recommended papers from target journals in modern card layout
"""
import logging
from typing import Optional, List, Dict

from qt_compat import (
    QCheckBox, QComboBox, QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QTextBrowser, QVBoxLayout, QWidget, Qt, QtCore, QtGui, QtWidgets, Signal
)

logger = logging.getLogger(__name__)


class RecommendationCard(QFrame):
    """Modern card widget for displaying a single recommendation"""

    clicked = Signal(dict)
    action_requested = Signal(int, str)  # cache_id, action

    def __init__(self, recommendation: Dict, parent=None):
        super().__init__(parent)

        self.rec = recommendation
        self.cache_id = recommendation['cache_id']

        self._init_ui()

    def _init_ui(self):
        """Initialize card UI"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)

        # Modern card styling
        self.setStyleSheet("""
            RecommendationCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px;
                margin: 8px 0;
            }
            RecommendationCard:hover {
                background-color: #f7fafc;
                border-color: #cbd5e0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: Category badge + Score
        header_layout = QHBoxLayout()

        # Category badge
        category = self.rec['category']
        category_label = QLabel()
        if category == 'highly_relevant':
            category_label.setText("HIGHLY RELEVANT")
            category_label.setStyleSheet("""
                background-color: #48bb78;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 11px;
            """)
        elif category == 'relevant':
            category_label.setText("RELEVANT")
            category_label.setStyleSheet("""
                background-color: #4299e1;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 11px;
            """)
        else:
            category_label.setText("MODERATELY RELEVANT")
            category_label.setStyleSheet("""
                background-color: #718096;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 11px;
            """)

        header_layout.addWidget(category_label)

        # Score label
        score = self.rec['similarity_score']
        score_label = QLabel(f"Score: {score:.3f}")
        score_label.setStyleSheet("color: #718096; font-size: 12px; font-weight: 500;")
        header_layout.addWidget(score_label)

        # Status badge
        status = self.rec['status']
        if status == 'confirmed':
            status_label = QLabel("CONFIRMED")
            status_label.setStyleSheet("""
                background-color: #38a169;
                color: white;
                padding: 4px 10px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            """)
            header_layout.addWidget(status_label)
        elif status == 'dismissed':
            status_label = QLabel("DISMISSED")
            status_label.setStyleSheet("""
                background-color: #a0aec0;
                color: white;
                padding: 4px 10px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            """)
            header_layout.addWidget(status_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Title
        title = self.rec['article_title']
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #2d3748;
            line-height: 1.4;
        """)
        layout.addWidget(title_label)

        # Meta info: Journal + Year
        meta_layout = QHBoxLayout()

        journal_name = self.rec['journal_name']
        journal_label = QLabel(f"{journal_name}")
        journal_label.setStyleSheet("color: #4a5568; font-size: 13px;")
        meta_layout.addWidget(journal_label)

        if self.rec.get('article_year'):
            year_label = QLabel(f"• {self.rec['article_year']}")
            year_label.setStyleSheet("color: #718096; font-size: 13px;")
            meta_layout.addWidget(year_label)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Keywords (if available)
        if self.rec.get('keywords_list'):
            keywords_layout = QHBoxLayout()
            keywords_layout.setSpacing(6)

            for keyword in self.rec['keywords_list'][:4]:  # Show max 4 keywords
                keyword_label = QLabel(keyword)
                keyword_label.setStyleSheet("""
                    background-color: #edf2f7;
                    color: #4a5568;
                    padding: 3px 10px;
                    border-radius: 10px;
                    font-size: 11px;
                """)
                keywords_layout.addWidget(keyword_label)

            keywords_layout.addStretch()
            layout.addLayout(keywords_layout)

        # Abstract preview
        if self.rec.get('article_abstract'):
            abstract = self.rec['article_abstract']
            preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
            abstract_label = QLabel(preview)
            abstract_label.setWordWrap(True)
            abstract_label.setStyleSheet("color: #718096; font-size: 12px; line-height: 1.5;")
            layout.addWidget(abstract_label)

        # Action buttons
        if status == 'unread':
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)

            confirm_btn = QPushButton("Confirm")
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background-color: #48bb78;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #38a169;
                }
            """)
            confirm_btn.clicked.connect(lambda: self.action_requested.emit(self.cache_id, 'confirmed'))
            button_layout.addWidget(confirm_btn)

            dismiss_btn = QPushButton("Dismiss")
            dismiss_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e2e8f0;
                    color: #4a5568;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #cbd5e0;
                }
            """)
            dismiss_btn.clicked.connect(lambda: self.action_requested.emit(self.cache_id, 'dismissed'))
            button_layout.addWidget(dismiss_btn)

            # DOI link button
            if self.rec.get('article_doi'):
                doi_btn = QPushButton("View DOI")
                doi_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3182ce;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 16px;
                        font-weight: 500;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #2c5282;
                    }
                """)
                doi_btn.clicked.connect(self._open_doi)
                button_layout.addWidget(doi_btn)

            button_layout.addStretch()
            layout.addLayout(button_layout)

    def _open_doi(self):
        """Open DOI link in browser"""
        doi = self.rec.get('article_doi', '')
        if doi:
            import webbrowser
            webbrowser.open(f"https://doi.org/{doi}")

    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.rec)
        super().mousePressEvent(event)


class RecommendationsPanel(QWidget):
    """Panel for viewing and managing paper recommendations"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.auto_rec_manager = None
        self.current_recommendations = []
        self.card_widgets = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI with modern card-based layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Modern header
        header_layout = QHBoxLayout()

        title_label = QLabel("Recommended Papers")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #2d3748;
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Statistics label (moved to header)
        self.stats_label = QLabel("0 papers")
        self.stats_label.setStyleSheet("color: #718096; font-size: 14px; font-weight: 500;")
        header_layout.addWidget(self.stats_label)

        # Refresh button with modern styling
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2c5282;
            }
        """)
        self.refresh_button.clicked.connect(self._on_refresh)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        # Status filter
        status_label = QLabel("Status:")
        status_label.setStyleSheet("color: #4a5568; font-weight: 500;")
        filter_layout.addWidget(status_label)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Unread", "unread")
        self.status_combo.addItem("Confirmed", "confirmed")
        self.status_combo.addItem("Dismissed", "dismissed")
        self.status_combo.addItem("All", None)
        self.status_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 120px;
            }
        """)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_combo)

        # Category filter
        category_label = QLabel("Relevance:")
        category_label.setStyleSheet("color: #4a5568; font-weight: 500;")
        filter_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All Levels", None)
        self.category_combo.addItem("Highly Relevant", "highly_relevant")
        self.category_combo.addItem("Relevant", "relevant")
        self.category_combo.addItem("Moderately Relevant", "moderately_relevant")
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 150px;
            }
        """)
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.category_combo)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        # Container for cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

    def set_manager(self, manager):
        """Set auto recommendation manager"""
        self.auto_rec_manager = manager
        self._load_recommendations()

    def _load_recommendations(self):
        """Load recommendations from database"""
        if not self.auto_rec_manager:
            return

        # Get filter values
        status = self.status_combo.currentData()
        category = self.category_combo.currentData()

        try:
            self.current_recommendations = self.auto_rec_manager.get_recommendations(
                status=status,
                category=category
            )

            self._display_recommendations()
            self._update_statistics()

        except Exception as e:
            logger.error(f"Failed to load recommendations: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"추천 논문 로딩 실패:\n{e}")

    def _display_recommendations(self):
        """Display recommendations as modern cards"""
        # Clear existing cards
        for card in self.card_widgets:
            card.deleteLater()
        self.card_widgets.clear()

        # Remove stretch
        if self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(self.cards_layout.count() - 1)
            if item:
                item.invalidate()

        # Create cards
        if not self.current_recommendations:
            # Empty state
            empty_label = QLabel("No recommendations found.\n\nAdd target journals and click Refresh to get recommendations.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("""
                color: #a0aec0;
                font-size: 14px;
                padding: 40px;
            """)
            self.cards_layout.addWidget(empty_label)
            self.card_widgets.append(empty_label)
        else:
            for rec in self.current_recommendations:
                card = RecommendationCard(rec)
                card.action_requested.connect(self._on_card_action)
                self.cards_layout.addWidget(card)
                self.card_widgets.append(card)

        # Add stretch at end
        self.cards_layout.addStretch()

        logger.info(f"Displayed {len(self.current_recommendations)} recommendation cards")

    def _update_statistics(self):
        """Update statistics label"""
        if not self.auto_rec_manager:
            return

        try:
            stats = self.auto_rec_manager.get_statistics()

            unread = stats.get('unread', 0)
            total = stats.get('total', 0)

            # Modern stats display
            if unread > 0:
                self.stats_label.setText(f"{total} papers ({unread} unread)")
            else:
                self.stats_label.setText(f"{total} papers")

        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")

    def _on_filter_changed(self):
        """Handle filter change"""
        self._load_recommendations()

    def _on_refresh(self):
        """Refresh recommendations"""
        self._load_recommendations()

    def _on_card_action(self, cache_id: int, action: str):
        """Handle action from recommendation card"""
        try:
            self.auto_rec_manager.update_recommendation_status(cache_id, action)

            # Refresh to update UI
            self._load_recommendations()

            action_text = "confirmed" if action == 'confirmed' else "dismissed"
            logger.info(f"Recommendation {cache_id} marked as {action_text}")

        except Exception as e:
            logger.error(f"Failed to update recommendation: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to update status:\n{e}")

    def refresh(self):
        """Public method to refresh panel"""
        self._load_recommendations()
