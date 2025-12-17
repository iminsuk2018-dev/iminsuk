"""
Web-based Recommendations Dialog
Displays the web recommendation system in a Qt dialog
"""
import logging
import subprocess
import sys
from pathlib import Path

from qt_compat import (
    QDialog, QHBoxLayout, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout,
    Qt, QtCore, QtWidgets
)

logger = logging.getLogger(__name__)

# Try to import QWebEngineView
try:
    from qt_compat import QtWebEngineWidgets
    QWebEngineView = QtWebEngineWidgets.QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    logger.warning("QtWebEngine not available. Web view will use external browser.")


class WebRecommendationsDialog(QDialog):
    """Dialog for web-based recommendation system"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.web_server_process = None
        self.web_url = "http://127.0.0.1:5000"

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("논문 추천 시스템 (웹)")
        self.setMinimumSize(1200, 800)

        layout = QVBoxLayout(self)

        if WEB_ENGINE_AVAILABLE:
            # Use embedded web view
            self.web_view = QWebEngineView()
            self.web_view.setUrl(QtCore.QUrl(self.web_url))
            layout.addWidget(self.web_view)

            # Reload button
            button_layout = QHBoxLayout()

            reload_btn = QPushButton("새로고침")
            reload_btn.clicked.connect(lambda: self.web_view.reload())
            button_layout.addWidget(reload_btn)

            open_browser_btn = QPushButton("브라우저에서 열기")
            open_browser_btn.clicked.connect(self._open_in_browser)
            button_layout.addWidget(open_browser_btn)

            button_layout.addStretch()

            close_btn = QPushButton("닫기")
            close_btn.clicked.connect(self.close)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

        else:
            # Fallback: Show message and button to open in browser
            info_text = QTextBrowser()
            info_text.setHtml(f"""
                <h2>웹 기반 논문 추천 시스템</h2>
                <p>웹 엔진을 사용할 수 없습니다. 외부 브라우저에서 추천 시스템을 사용하세요.</p>
                <p><b>URL:</b> <a href="{self.web_url}">{self.web_url}</a></p>
                <hr>
                <h3>기능:</h3>
                <ul>
                    <li>타겟 저널에서 키워드 기반 논문 자동 추천</li>
                    <li>저널별, 키워드별 필터링</li>
                    <li>최신순/오래된순 정렬</li>
                    <li>논문 확인/무시 상태 관리</li>
                    <li>DOI 링크로 원문 바로 가기</li>
                </ul>
            """)
            info_text.setOpenExternalLinks(True)
            layout.addWidget(info_text)

            button_layout = QHBoxLayout()

            open_browser_btn = QPushButton("브라우저에서 열기")
            open_browser_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3182ce;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #2c5282;
                }
            """)
            open_browser_btn.clicked.connect(self._open_in_browser)
            button_layout.addWidget(open_browser_btn)

            button_layout.addStretch()

            close_btn = QPushButton("닫기")
            close_btn.clicked.connect(self.close)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

    def showEvent(self, event):
        """Handle show event - ensure web server is running"""
        super().showEvent(event)
        self._ensure_web_server_running()

    def _ensure_web_server_running(self):
        """Start web server if not running"""
        import socket

        # Check if server is already running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()

        if result != 0:
            # Server not running, start it
            logger.info("Starting web server...")
            self._start_web_server()
        else:
            logger.info("Web server already running")

    def _start_web_server(self):
        """Start the Flask web server in background"""
        try:
            web_app_path = Path(__file__).parent.parent / "web" / "app.py"

            if not web_app_path.exists():
                QMessageBox.critical(
                    self,
                    "오류",
                    f"웹 서버 파일을 찾을 수 없습니다:\n{web_app_path}"
                )
                return

            # Start server as subprocess
            self.web_server_process = subprocess.Popen(
                [sys.executable, str(web_app_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            logger.info(f"Web server started with PID: {self.web_server_process.pid}")

            # Wait a moment for server to start
            import time
            time.sleep(2)

            # Reload web view if available
            if WEB_ENGINE_AVAILABLE and hasattr(self, 'web_view'):
                self.web_view.reload()

        except Exception as e:
            logger.error(f"Failed to start web server: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"웹 서버 시작 실패:\n{e}"
            )

    def _open_in_browser(self):
        """Open recommendation system in external browser"""
        import webbrowser
        webbrowser.open(self.web_url)

    def closeEvent(self, event):
        """Handle close event - cleanup"""
        # Don't kill the server - let it run in background
        # Users can access it directly via browser
        super().closeEvent(event)

    def __del__(self):
        """Cleanup when dialog is destroyed"""
        # Optionally stop the web server when dialog is destroyed
        # Commented out to keep server running
        # if self.web_server_process:
        #     self.web_server_process.terminate()
        pass
