"""
Welcome Dialog
Shown on first run to introduce the application
"""
from qt_compat import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QSettings, QTextBrowser,
    QVBoxLayout, Qt, QtCore, QtWidgets
)
from ui.styles import get_dialog_style, set_primary_button


class WelcomeDialog(QDialog):
    """Welcome dialog for new users"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(get_dialog_style())
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Welcome to PDF Research Assistant")
        self.setMinimumSize(700, 550)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("👋 Welcome to PDF Research Assistant!")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Your intelligent PDF library and research companion")
        subtitle.setStyleSheet("font-size: 12pt; color: #666; margin-bottom: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Content browser
        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.setHtml("""
        <style>
            h3 { color: #2c3e50; margin-top: 15px; }
            ul { margin-left: 20px; }
            li { margin: 5px 0; }
            .feature { background: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }
        </style>

        <h3>🚀 Getting Started</h3>
        <ol>
            <li><b>Add PDFs</b>: Click "File > Add PDF" (Ctrl+O) or drag & drop PDF files</li>
            <li><b>Read & Annotate</b>: Click a document to view, add notes, and highlight text</li>
            <li><b>Organize</b>: Use tags to categorize your papers</li>
            <li><b>Search</b>: Press Ctrl+F to search across all documents</li>
        </ol>

        <h3>✨ Key Features</h3>

        <div class="feature">
            <b>📝 Annotations & Notes</b>
            <ul>
                <li>Add notes to any page of your PDFs</li>
                <li>Highlight important text</li>
                <li>Bookmark pages for quick access</li>
            </ul>
        </div>

        <div class="feature">
            <b>🏷️ Smart Tagging</b>
            <ul>
                <li>Organize papers with custom tags</li>
                <li>Get AI-powered tag suggestions</li>
                <li>Search by tags to find related papers</li>
            </ul>
        </div>

        <div class="feature">
            <b>🔍 Powerful Search</b>
            <ul>
                <li>Search document titles, content, and annotations</li>
                <li>Filter by content type</li>
                <li>Quick jump to results</li>
            </ul>
        </div>

        <div class="feature">
            <b>🎨 Customization</b>
            <ul>
                <li>Light & Dark themes (Ctrl+T to toggle)</li>
                <li>PDF color filters for comfortable reading</li>
                <li>Customizable layout</li>
            </ul>
        </div>

        <div class="feature">
            <b>🧠 Smart Features</b>
            <ul>
                <li>Automatic duplicate detection</li>
                <li>Reference extraction from PDFs</li>
                <li>Citation management</li>
                <li>Paper recommendations</li>
            </ul>
        </div>

        <h3>💡 Tips</h3>
        <ul>
            <li>Press <b>F1</b> anytime to view all keyboard shortcuts</li>
            <li>Hover over buttons to see helpful tooltips</li>
            <li>Right-click items for context menus with more options</li>
            <li>Use <b>Ctrl+D</b> for dark mode - easier on the eyes!</li>
        </ul>

        <h3>📚 Next Steps</h3>
        <p>Start by adding your first PDF document! You can:</p>
        <ul>
            <li>Use <b>File > Add PDF</b> menu</li>
            <li>Press <b>Ctrl+O</b></li>
            <li>Drag and drop PDF files into the document list</li>
        </ul>
        """)
        layout.addWidget(content)

        # Don't show again checkbox
        checkbox_layout = QHBoxLayout()
        self.dont_show_checkbox = QCheckBox("Don't show this again")
        checkbox_layout.addWidget(self.dont_show_checkbox)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        shortcuts_button = QPushButton("View Shortcuts (F1)")
        shortcuts_button.clicked.connect(self._on_show_shortcuts)
        button_layout.addWidget(shortcuts_button)

        get_started_button = QPushButton("Get Started!")
        get_started_button.setDefault(True)
        get_started_button.clicked.connect(self.accept)
        set_primary_button(get_started_button)
        button_layout.addWidget(get_started_button)

        layout.addLayout(button_layout)

    def _on_show_shortcuts(self):
        """Show shortcuts dialog"""
        from ui.shortcuts_dialog import ShortcutsDialog
        shortcuts = ShortcutsDialog(self)
        shortcuts.exec()

    def closeEvent(self, event):
        """Handle dialog close"""
        if self.dont_show_checkbox.isChecked():
            settings = QSettings("PDFResearch", "Welcome")
            settings.setValue("show_welcome", False)
        super().closeEvent(event)

    def accept(self):
        """Handle accept"""
        if self.dont_show_checkbox.isChecked():
            settings = QSettings("PDFResearch", "Welcome")
            settings.setValue("show_welcome", False)
        super().accept()

    @staticmethod
    def should_show():
        """Check if welcome dialog should be shown"""
        settings = QSettings("PDFResearch", "Welcome")
        return settings.value("show_welcome", True, type=bool)
