"""
추천 시스템 다이얼로그
"""
import logging
from typing import Optional

from qt_compat import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QSpinBox,
    QTextBrowser, QThread, QVBoxLayout, Qt, QtCore, QtWidgets, Signal, Slot
)

logger = logging.getLogger(__name__)


class RecommendationWorker(QThread):
    """백그라운드에서 추천 생성"""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, recommendation_engine, journal_name, days_back, parent=None):
        super().__init__(parent)
        self.recommendation_engine = recommendation_engine
        self.journal_name = journal_name
        self.days_back = days_back

    def run(self):
        try:
            self.progress.emit("사용자 프로필 생성 중...")

            self.progress.emit("저널 논문 수집 중...")

            recommendations = self.recommendation_engine.generate_recommendations(
                self.journal_name,
                self.days_back
            )

            self.finished.emit(recommendations)

        except Exception as e:
            logger.error(f"Recommendation failed: {e}", exc_info=True)
            self.error.emit(str(e))


class RecommendationDialog(QDialog):
    """추천 시스템 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.recommendation_engine = None
        self.worker: Optional[RecommendationWorker] = None
        self.recommendations = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Paper Recommendations")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)

        # Journal input
        journal_group = QGroupBox("Journal Selection")
        journal_layout = QVBoxLayout(journal_group)

        input_layout = QHBoxLayout()

        journal_label = QLabel("Journal Name:")
        input_layout.addWidget(journal_label)

        self.journal_input = QLineEdit()
        self.journal_input.setPlaceholderText("e.g., Energy & Environmental Science, Nature, Science...")
        input_layout.addWidget(self.journal_input)

        days_label = QLabel("Days back:")
        input_layout.addWidget(days_label)

        self.days_spin = QSpinBox()
        self.days_spin.setMinimum(7)
        self.days_spin.setMaximum(365)
        self.days_spin.setValue(30)
        input_layout.addWidget(self.days_spin)

        self.recommend_button = QPushButton("Get Recommendations")
        self.recommend_button.clicked.connect(self._on_recommend)
        input_layout.addWidget(self.recommend_button)

        journal_layout.addLayout(input_layout)

        # Popular journals
        popular_label = QLabel("Popular Journals:")
        journal_layout.addWidget(popular_label)

        popular_layout = QHBoxLayout()
        for journal in [
            "Nature",
            "Science",
            "Energy & Environmental Science",
            "Chemical Engineering Journal",
            "Applied Energy"
        ]:
            btn = QPushButton(journal)
            btn.clicked.connect(lambda checked, j=journal: self.journal_input.setText(j))
            popular_layout.addWidget(btn)
        journal_layout.addLayout(popular_layout)

        layout.addWidget(journal_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results
        results_label = QLabel("Recommendations:")
        layout.addWidget(results_label)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self.results_list)

        # Details
        details_label = QLabel("Article Details:")
        layout.addWidget(details_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setMaximumHeight(200)
        layout.addWidget(self.details_browser)

        # Status
        self.status_label = QLabel("Select a journal and click 'Get Recommendations'")
        self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def set_recommendation_engine(self, engine):
        """Set recommendation engine instance"""
        self.recommendation_engine = engine

    def _on_recommend(self):
        """Generate recommendations"""
        journal_name = self.journal_input.text().strip()

        if not journal_name:
            QMessageBox.warning(self, "No Journal", "Please enter a journal name")
            return

        if not self.recommendation_engine:
            QMessageBox.critical(self, "Error", "Recommendation engine not initialized")
            return

        # Disable button
        self.recommend_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Generating recommendations...")

        # Clear previous results
        self.results_list.clear()
        self.details_browser.clear()

        # Start worker thread
        days_back = self.days_spin.value()

        self.worker = RecommendationWorker(
            self.recommendation_engine,
            journal_name,
            days_back,
            self
        )

        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_recommendations_ready)
        self.worker.error.connect(self._on_error)

        self.worker.start()

        logger.info(f"Started recommendation generation for '{journal_name}'")

    def _on_progress(self, message: str):
        """Update progress"""
        self.status_label.setText(message)

    def _on_recommendations_ready(self, recommendations):
        """Handle recommendations ready"""
        self.recommendations = recommendations

        # Enable button
        self.recommend_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if not recommendations:
            self.status_label.setText("No recommendations found")
            QMessageBox.information(
                self,
                "No Results",
                "No matching articles found. Try a different journal or increase the time range."
            )
            return

        # Display recommendations
        for i, rec in enumerate(recommendations):
            item_text = f"[{rec.similarity_score:.2f}] {rec.article_title}"

            if rec.article_year:
                item_text += f" ({rec.article_year})"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.results_list.addItem(item)

        self.status_label.setText(f"Found {len(recommendations)} recommendations")

        logger.info(f"Displayed {len(recommendations)} recommendations")

    def _on_error(self, error_message: str):
        """Handle error"""
        self.recommend_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Recommendation failed")

        QMessageBox.critical(self, "Error", f"Recommendation failed:\n{error_message}")

    def _on_result_clicked(self, item: QListWidgetItem):
        """Show article details"""
        idx = item.data(Qt.UserRole)

        if idx is None or idx >= len(self.recommendations):
            return

        rec = self.recommendations[idx]

        # Build HTML
        html = f"<h3>{rec.article_title}</h3>"

        if rec.article_authors:
            authors_str = ', '.join(rec.article_authors[:5])
            if len(rec.article_authors) > 5:
                authors_str += f" et al. ({len(rec.article_authors)} authors)"
            html += f"<p><b>Authors:</b> {authors_str}</p>"

        if rec.article_year:
            html += f"<p><b>Year:</b> {rec.article_year}</p>"

        html += f"<p><b>Journal:</b> {rec.journal_name}</p>"

        if rec.article_doi:
            doi_link = f"https://doi.org/{rec.article_doi}"
            html += f'<p><b>DOI:</b> <a href="{doi_link}">{rec.article_doi}</a></p>'

        html += f"<p><b>Similarity Score:</b> {rec.similarity_score:.4f}</p>"

        html += f"<p><b>Why recommended:</b> {rec.reason}</p>"

        if rec.common_keywords:
            keywords_str = ', '.join(rec.common_keywords)
            html += f"<p><b>Common keywords:</b> {keywords_str}</p>"

        if rec.article_abstract:
            html += f"<hr><p><b>Abstract:</b></p><p>{rec.article_abstract[:500]}"
            if len(rec.article_abstract) > 500:
                html += "..."
            html += "</p>"

        self.details_browser.setHtml(html)
        self.details_browser.setOpenExternalLinks(True)
