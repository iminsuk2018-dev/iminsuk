"""
Application-wide styles and themes
Provides consistent styling across all UI components
"""

# Color Palette
COLORS = {
    'primary': '#3498db',
    'primary_hover': '#2980b9',
    'primary_dark': '#2c3e50',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'info': '#3498db',
    'light_gray': '#ecf0f1',
    'medium_gray': '#95a5a6',
    'dark_gray': '#7f8c8d',
    'border': '#bdc3c7',
    'text': '#2c3e50',
    'text_muted': '#7f8c8d',
    'background': '#ffffff',
    'background_alt': '#f8f9fa',
}

# Typography
FONTS = {
    'h1': '20pt',
    'h2': '16pt',
    'h3': '14pt',
    'body': '10pt',
    'small': '9pt',
}

# Spacing
SPACING = {
    'xs': '4px',
    'sm': '8px',
    'md': '12px',
    'lg': '16px',
    'xl': '24px',
}


def get_dialog_style():
    """Get standard dialog stylesheet"""
    return f"""
        QDialog {{
            background-color: {COLORS['background']};
        }}

        QLabel {{
            color: {COLORS['text']};
        }}

        QPushButton {{
            background-color: {COLORS['light_gray']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 6px 16px;
            color: {COLORS['text']};
            min-width: 80px;
        }}

        QPushButton:hover {{
            background-color: {COLORS['border']};
        }}

        QPushButton:pressed {{
            background-color: {COLORS['medium_gray']};
        }}

        QPushButton:disabled {{
            background-color: {COLORS['light_gray']};
            color: {COLORS['text_muted']};
        }}

        QPushButton[primary="true"] {{
            background-color: {COLORS['primary']};
            color: white;
            font-weight: bold;
        }}

        QPushButton[primary="true"]:hover {{
            background-color: {COLORS['primary_hover']};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 6px;
            background-color: white;
            selection-background-color: {COLORS['primary']};
        }}

        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {COLORS['primary']};
            padding: 5px;
        }}

        QListWidget, QTreeWidget, QTableWidget {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            background-color: white;
            outline: none;
        }}

        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {COLORS['primary']};
            color: white;
        }}

        QListWidget::item:hover {{
            background-color: {COLORS['light_gray']};
        }}

        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 8px;
            font-weight: bold;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}

        QProgressBar {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            text-align: center;
            background-color: {COLORS['light_gray']};
        }}

        QProgressBar::chunk {{
            background-color: {COLORS['primary']};
            border-radius: 3px;
        }}

        QComboBox {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 4px 8px;
            background-color: white;
        }}

        QComboBox:focus {{
            border: 2px solid {COLORS['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
        }}

        QTabWidget::pane {{
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
        }}

        QTabBar::tab {{
            background-color: {COLORS['light_gray']};
            border: 1px solid {COLORS['border']};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 12px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: white;
            font-weight: bold;
        }}

        QTabBar::tab:hover {{
            background-color: {COLORS['background_alt']};
        }}
    """


def get_toolbar_style():
    """Get toolbar stylesheet"""
    return f"""
        QToolBar {{
            background-color: {COLORS['background_alt']};
            border-bottom: 1px solid {COLORS['border']};
            spacing: 6px;
            padding: 4px;
        }}

        QToolBar QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 8px;
        }}

        QToolBar QToolButton:hover {{
            background-color: {COLORS['light_gray']};
            border: 1px solid {COLORS['border']};
        }}

        QToolBar QToolButton:pressed {{
            background-color: {COLORS['border']};
        }}
    """


def get_header_style(size='h2'):
    """Get header label style"""
    font_size = FONTS.get(size, FONTS['h2'])
    return f"""
        QLabel {{
            font-size: {font_size};
            font-weight: bold;
            color: {COLORS['primary_dark']};
            padding: {SPACING['sm']} 0;
        }}
    """


def get_status_label_style(status='info'):
    """Get status label style"""
    colors = {
        'success': COLORS['success'],
        'warning': COLORS['warning'],
        'error': COLORS['danger'],
        'info': COLORS['info'],
    }
    color = colors.get(status, COLORS['text_muted'])

    return f"""
        QLabel {{
            color: {color};
            font-size: {FONTS['small']};
            font-style: italic;
            padding: {SPACING['xs']};
        }}
    """


def get_empty_state_style():
    """Get empty state message style"""
    return f"""
        QLabel {{
            color: {COLORS['text_muted']};
            font-size: {FONTS['body']};
            padding: {SPACING['xl']};
        }}
    """


def set_primary_button(button):
    """Mark a button as primary"""
    button.setProperty("primary", "true")
    button.setStyle(button.style())  # Force style refresh
