"""
Target Journals Dialog
Manage journals to monitor for automatic recommendations
"""
import logging
from typing import Optional

from qt_compat import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QPushButton, QTextBrowser, QVBoxLayout, Qt, QtCore, QtWidgets
)

logger = logging.getLogger(__name__)


class TargetJournalsDialog(QDialog):
    """Dialog for managing target journals"""

    def __init__(self, auto_rec_manager, parent=None):
        super().__init__(parent)

        self.auto_rec_manager = auto_rec_manager

        self._init_ui()
        self._load_journals()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("타겟 저널 관리")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Description
        desc_label = QLabel(
            "자동으로 신간 논문을 모니터링할 저널 목록입니다.\n"
            "저널에서 새로운 논문이 발표되면 자동으로 관련성을 분석하여 추천합니다."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Journal list
        list_label = QLabel("타겟 저널 목록:")
        layout.addWidget(list_label)

        self.journal_list = QListWidget()
        self.journal_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.journal_list)

        # Action buttons
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("+ Add Journal")
        self.add_button.clicked.connect(self._on_add_journal)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("- Remove")
        self.remove_button.clicked.connect(self._on_remove_journal)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)

        self.toggle_button = QPushButton("Toggle Active")
        self.toggle_button.clicked.connect(self._on_toggle_journal)
        self.toggle_button.setEnabled(False)
        button_layout.addWidget(self.toggle_button)

        button_layout.addStretch()

        self.fetch_button = QPushButton("Update Now")
        self.fetch_button.clicked.connect(self._on_fetch_now)
        button_layout.addWidget(self.fetch_button)

        layout.addLayout(button_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status
        self.status_text = QTextBrowser()
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)

        # Popular journals quick add
        popular_group = QGroupBox("자주 사용하는 저널 빠른 추가")
        popular_layout = QVBoxLayout(popular_group)

        popular_journals = [
            "Nature",
            "Science",
            "Energy & Environmental Science",
            "Applied Energy",
            "Renewable and Sustainable Energy Reviews",
            "Journal of Power Sources",
            "International Journal of Hydrogen Energy",
            "Chemical Engineering Journal"
        ]

        quick_buttons_layout = QHBoxLayout()
        for i, journal in enumerate(popular_journals[:4]):
            btn = QPushButton(journal)
            btn.clicked.connect(lambda checked, j=journal: self._quick_add_journal(j))
            quick_buttons_layout.addWidget(btn)
        popular_layout.addLayout(quick_buttons_layout)

        quick_buttons_layout2 = QHBoxLayout()
        for i, journal in enumerate(popular_journals[4:]):
            btn = QPushButton(journal)
            btn.clicked.connect(lambda checked, j=journal: self._quick_add_journal(j))
            quick_buttons_layout2.addWidget(btn)
        popular_layout.addLayout(quick_buttons_layout2)

        layout.addWidget(popular_group)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)

        layout.addLayout(close_layout)

    def _load_journals(self):
        """Load target journals"""
        self.journal_list.clear()

        try:
            journals = self.auto_rec_manager.get_target_journals(active_only=False)

            for journal in journals:
                journal_name = journal['journal_name']
                is_active = journal['is_active']
                last_fetched = journal.get('last_fetched', 'Never')

                # Status icon
                status_icon = "✓" if is_active else "✗"

                display_text = f"{status_icon} {journal_name}"
                if last_fetched and last_fetched != 'Never':
                    display_text += f" (마지막 업데이트: {last_fetched.split('.')[0]})"

                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, journal['journal_id'])

                # Color by status
                if not is_active:
                    item.setForeground(QtCore.Qt.gray)

                self.journal_list.addItem(item)

            self.status_text.append(f"<font color='green'>{len(journals)}개의 타겟 저널</font>")
            logger.info(f"Loaded {len(journals)} target journals")

        except Exception as e:
            logger.error(f"Failed to load journals: {e}", exc_info=True)
            self.status_text.append(f"<font color='red'>오류: {e}</font>")

    def _on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.journal_list.selectedItems()) > 0
        self.remove_button.setEnabled(has_selection)
        self.toggle_button.setEnabled(has_selection)

    def _on_add_journal(self):
        """Add new journal"""
        from qt_compat import QDialog, QLabel, QLineEdit, QVBoxLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("저널 추가")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("저널 이름:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("예: Nature Energy")
        layout.addWidget(name_input)

        layout.addWidget(QLabel("ISSN (선택사항):"))
        issn_input = QLineEdit()
        issn_input.setPlaceholderText("예: 2058-7546")
        layout.addWidget(issn_input)

        layout.addWidget(QLabel("업데이트 주기:"))
        freq_combo = QComboBox()
        freq_combo.addItem("매일", "daily")
        freq_combo.addItem("매주", "weekly")
        freq_combo.addItem("매월", "monthly")
        freq_combo.setCurrentIndex(1)  # Weekly default
        layout.addWidget(freq_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() != QDialog.Accepted:
            return

        journal_name = name_input.text().strip()
        if not journal_name:
            QMessageBox.warning(self, "입력 오류", "저널 이름을 입력하세요")
            return

        issn = issn_input.text().strip() or None
        freq = freq_combo.currentData()

        try:
            journal_id = self.auto_rec_manager.add_target_journal(
                journal_name, issn, freq
            )

            self.status_text.append(f"<font color='green'>저널 추가됨: {journal_name}</font>")
            self._load_journals()

            logger.info(f"Added target journal: {journal_name} (ID: {journal_id})")

        except Exception as e:
            logger.error(f"Failed to add journal: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"저널 추가 실패:\n{e}")

    def _quick_add_journal(self, journal_name: str):
        """Quick add popular journal"""
        try:
            # Check if already exists
            journals = self.auto_rec_manager.get_target_journals(active_only=False)
            if any(j['journal_name'] == journal_name for j in journals):
                QMessageBox.information(self, "정보", f"{journal_name}은(는) 이미 추가되어 있습니다")
                return

            journal_id = self.auto_rec_manager.add_target_journal(
                journal_name, None, 'weekly'
            )

            self.status_text.append(f"<font color='green'>저널 추가됨: {journal_name}</font>")
            self._load_journals()

            logger.info(f"Quick added: {journal_name}")

        except Exception as e:
            logger.error(f"Failed to quick add: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"저널 추가 실패:\n{e}")

    def _on_remove_journal(self):
        """Remove selected journal"""
        selected_items = self.journal_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        journal_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "저널 제거",
            "이 저널을 타겟 목록에서 제거하시겠습니까?\n\n"
            "기존 추천 논문은 유지됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.auto_rec_manager.remove_target_journal(journal_id)
            self.status_text.append("<font color='green'>저널 제거됨</font>")
            self._load_journals()

            logger.info(f"Removed journal: {journal_id}")

        except Exception as e:
            logger.error(f"Failed to remove journal: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"저널 제거 실패:\n{e}")

    def _on_toggle_journal(self):
        """Toggle journal active status"""
        selected_items = self.journal_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        journal_id = item.data(Qt.UserRole)

        # Get current status
        journals = self.auto_rec_manager.get_target_journals(active_only=False)
        journal = next((j for j in journals if j['journal_id'] == journal_id), None)

        if not journal:
            return

        new_status = not journal['is_active']

        try:
            self.auto_rec_manager.toggle_journal(journal_id, new_status)

            status_text = "활성화" if new_status else "비활성화"
            self.status_text.append(f"<font color='green'>저널 {status_text}됨</font>")
            self._load_journals()

            logger.info(f"Toggled journal {journal_id} to {new_status}")

        except Exception as e:
            logger.error(f"Failed to toggle journal: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"상태 변경 실패:\n{e}")

    def _on_fetch_now(self):
        """Fetch recommendations now"""
        reply = QMessageBox.question(
            self,
            "업데이트 확인",
            "모든 활성 저널에서 신간 논문을 가져오시겠습니까?\n\n"
            "시간이 다소 걸릴 수 있습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.fetch_button.setEnabled(False)
        self.status_text.append("<b>신간 논문 검색 중...</b>")

        try:
            # Fetch and recommend
            stats = self.auto_rec_manager.fetch_and_recommend(days_back=7)

            self.progress_bar.setVisible(False)
            self.fetch_button.setEnabled(True)

            # Show results
            result_html = f"""
            <font color='green'><b>업데이트 완료</b></font><br>
            - 검색된 논문: {stats.get('fetched', 0)}개<br>
            - 추천된 논문: {stats.get('recommended', 0)}개<br>
            - 처리된 저널: {stats.get('journals_processed', 0)}개
            """

            self.status_text.append(result_html)

            if stats.get('recommended', 0) > 0:
                QMessageBox.information(
                    self,
                    "업데이트 완료",
                    f"{stats['recommended']}개의 새로운 논문이 추천되었습니다!"
                )

            logger.info(f"Fetched recommendations: {stats}")

        except Exception as e:
            self.progress_bar.setVisible(False)
            self.fetch_button.setEnabled(True)
            logger.error(f"Failed to fetch recommendations: {e}", exc_info=True)
            self.status_text.append(f"<font color='red'>오류: {e}</font>")
            QMessageBox.critical(self, "오류", f"업데이트 실패:\n{e}")
