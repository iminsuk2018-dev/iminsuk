"""
Automatically fix Qt imports in all files
Scans files for Qt class usage and adds necessary imports from qt_compat
"""
import re
from pathlib import Path
from collections import defaultdict

# List of all Qt classes exported from qt_compat
QT_CLASSES = {
    # Widgets
    'QApplication', 'QMainWindow', 'QWidget', 'QDialog',
    'QVBoxLayout', 'QHBoxLayout', 'QFormLayout', 'QGridLayout',
    'QSplitter', 'QLabel', 'QPushButton', 'QLineEdit',
    'QTextEdit', 'QPlainTextEdit', 'QTextBrowser',
    'QListWidget', 'QListWidgetItem', 'QTreeWidget', 'QTreeWidgetItem',
    'QTableWidget', 'QTableWidgetItem', 'QComboBox', 'QCheckBox',
    'QRadioButton', 'QSpinBox', 'QDoubleSpinBox', 'QSlider',
    'QProgressBar', 'QGroupBox', 'QTabWidget', 'QTabBar',
    'QScrollArea', 'QScrollBar', 'QMenu', 'QMenuBar',
    'QToolBar', 'QStatusBar', 'QAction', 'QFileDialog',
    'QMessageBox', 'QInputDialog', 'QColorDialog', 'QFontDialog',
    'QGraphicsView', 'QGraphicsScene', 'QGraphicsPixmapItem',
    'QGraphicsRectItem', 'QGraphicsTextItem', 'QFrame',
    # Core
    'Qt', 'QThread', 'QTimer', 'QSettings', 'QUrl',
    'QPoint', 'QPointF', 'QRect', 'QRectF', 'QSize', 'QSizeF',
    'QEvent', 'QObject',
    # Gui
    'QPixmap', 'QImage', 'QIcon', 'QPainter', 'QBrush', 'QPen',
    'QColor', 'QFont', 'QKeySequence', 'QCursor', 'QTransform',
    'QPalette', 'QTextCursor', 'QTextDocument',
    # Signals
    'Signal', 'Slot'
}

def find_used_qt_classes(content):
    """Find all Qt classes used in the content"""
    used_classes = set()

    # Pattern to find Qt class usage (class names followed by ( or :)
    for qt_class in QT_CLASSES:
        # Match class instantiation, inheritance, or type hints
        patterns = [
            rf'\b{qt_class}\s*\(',  # Instantiation
            rf'\b{qt_class}\s*\)',  # Type hint
            rf'\({qt_class}\)',  # Inheritance
            rf':\s*{qt_class}',  # Type annotation
            rf'->\s*{qt_class}',  # Return type
            rf'\[{qt_class}\]',  # Generic type
        ]

        for pattern in patterns:
            if re.search(pattern, content):
                used_classes.add(qt_class)
                break

    return used_classes

def fix_file_imports(file_path):
    """Fix imports in a single file"""
    print(f"Processing: {file_path.name}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if no qt_compat import
    if 'from qt_compat import' not in content:
        print(f"  Skipping (no qt_compat import)")
        return False

    # Find all Qt classes used in the file
    used_classes = find_used_qt_classes(content)

    if not used_classes:
        print(f"  No Qt classes found")
        return False

    # Extract existing imports from qt_compat
    existing_imports = set()
    import_pattern = r'from qt_compat import \((.*?)\)|from qt_compat import ([^\n]+)'
    matches = re.findall(import_pattern, content, re.DOTALL)

    for match in matches:
        import_str = match[0] if match[0] else match[1]
        # Parse imported names
        imports = re.findall(r'(\w+)', import_str)
        existing_imports.update(imports)

    # Find new classes to add
    new_classes = used_classes - existing_imports

    if not new_classes:
        print(f"  All classes already imported")
        return False

    # Combine all imports
    all_imports = sorted(existing_imports | used_classes)

    # Build new import statement
    # Group into lines of reasonable length
    import_lines = []
    current_line = []
    line_length = 0

    for cls in all_imports:
        if line_length + len(cls) + 2 > 80 and current_line:  # 80 char limit
            import_lines.append(', '.join(current_line) + ',')
            current_line = []
            line_length = 0

        current_line.append(cls)
        line_length += len(cls) + 2

    if current_line:
        import_lines.append(', '.join(current_line))

    new_import = 'from qt_compat import (\n    ' + '\n    '.join(import_lines) + '\n)'

    # Replace existing qt_compat imports
    content = re.sub(
        r'from qt_compat import \(.*?\)\n',
        new_import + '\n',
        content,
        flags=re.DOTALL
    )

    # Also replace single-line imports
    content = re.sub(
        r'from qt_compat import [^\n]+\n',
        new_import + '\n',
        content
    )

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [OK] Added {len(new_classes)} new imports: {', '.join(sorted(new_classes))}")
    return True

def main():
    """Fix all Python files in the project"""
    project_dir = Path(__file__).parent

    # Find all .py files in ui directory
    ui_files = list((project_dir / 'ui').glob('*.py'))

    print(f"Found {len(ui_files)} UI files\n")

    fixed = 0
    for py_file in ui_files:
        if fix_file_imports(py_file):
            fixed += 1

    print(f"\n[DONE] Fixed {fixed} files")

if __name__ == '__main__':
    main()
