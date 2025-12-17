"""
Keyboard Shortcuts Dialog
Shows all available keyboard shortcuts
"""
from qt_compat import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTabWidget, QTextBrowser,
    QVBoxLayout, QtCore, QtWidgets
)
from ui.styles import get_dialog_style


class ShortcutsDialog(QDialog):
    """Dialog showing keyboard shortcuts"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(get_dialog_style())
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("⌨️ Keyboard Shortcuts")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # Tabs for different categories
        tabs = QTabWidget()

        # General shortcuts
        general_html = """
        <h3>General</h3>
        <table width="100%" style="border-collapse: collapse;">
            <tr><td width="40%"><b>Ctrl+O</b></td><td>Add PDF file</td></tr>
            <tr><td><b>Ctrl+F</b></td><td>Search documents</td></tr>
            <tr><td><b>Ctrl+Q</b></td><td>Quit application</td></tr>
        </table>
        """
        general_browser = QTextBrowser()
        general_browser.setHtml(general_html)
        general_browser.setOpenExternalLinks(False)
        tabs.addTab(general_browser, "General")

        # PDF Viewer shortcuts
        pdf_html = """
        <h3>PDF Viewer</h3>
        <table width="100%" style="border-collapse: collapse;">
            <tr><td width="40%"><b>←/→</b></td><td>Previous/Next page</td></tr>
            <tr><td><b>PageUp/PageDown</b></td><td>Previous/Next page</td></tr>
            <tr><td><b>Ctrl++</b></td><td>Zoom in</td></tr>
            <tr><td><b>Ctrl+-</b></td><td>Zoom out</td></tr>
            <tr><td><b>Ctrl+0</b></td><td>Fit to width</td></tr>
            <tr><td><b>H</b></td><td>Toggle highlight mode</td></tr>
            <tr><td><b>B</b></td><td>Toggle bookmark</td></tr>
            <tr><td><b>F11</b></td><td>Fullscreen</td></tr>
            <tr><td><b>Esc</b></td><td>Exit fullscreen</td></tr>
        </table>
        """
        pdf_browser = QTextBrowser()
        pdf_browser.setHtml(pdf_html)
        tabs.addTab(pdf_browser, "PDF Viewer")

        # Theme shortcuts
        theme_html = """
        <h3>Theme & Appearance</h3>
        <table width="100%" style="border-collapse: collapse;">
            <tr><td width="40%"><b>Ctrl+D</b></td><td>Switch to dark theme</td></tr>
            <tr><td><b>Ctrl+T</b></td><td>Toggle theme</td></tr>
        </table>
        """
        theme_browser = QTextBrowser()
        theme_browser.setHtml(theme_html)
        tabs.addTab(theme_browser, "Theme")

        # Tools shortcuts
        tools_html = """
        <h3>Tools</h3>
        <table width="100%" style="border-collapse: collapse;">
            <tr><td width="40%"><b>Ctrl+Shift+C</b></td><td>Citation Manager</td></tr>
            <tr><td><b>Ctrl+Shift+R</b></td><td>Reference Manager</td></tr>
        </table>
        """
        tools_browser = QTextBrowser()
        tools_browser.setHtml(tools_html)
        tabs.addTab(tools_browser, "Tools")

        layout.addWidget(tabs)

        # Tip section
        tip = QLabel("💡 Tip: Hover over buttons to see tooltips with keyboard shortcuts")
        tip.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        layout.addWidget(tip)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
