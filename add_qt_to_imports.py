"""
Add Qt constant to all qt_compat imports that don't have it
"""
import re
from pathlib import Path

def fix_file(file_path):
    """Add Qt to imports if missing"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if no qt_compat import
    if 'from qt_compat import' not in content:
        return False

    # Check if Qt is already imported
    if re.search(r'from qt_compat import.*\bQt\b', content, re.DOTALL):
        return False  # Already has Qt

    # Check if file uses Qt constant
    if not re.search(r'\bQt\.[A-Z]', content):
        return False  # Doesn't use Qt

    # Add Qt to the import
    # Handle both multi-line and single-line imports
    def add_qt(match):
        import_block = match.group(0)
        if ', Qt,' in import_block or ', Qt\n' in import_block or ', Qt)' in import_block:
            return import_block  # Already has Qt
        # Add Qt before QtCore
        if 'QtCore' in import_block:
            import_block = import_block.replace('QtCore', 'Qt, QtCore')
        return import_block

    content = re.sub(
        r'from qt_compat import \([^)]+\)',
        add_qt,
        content,
        flags=re.DOTALL
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] Added Qt to: {file_path.name}")
    return True

def main():
    """Fix all UI files"""
    ui_dir = Path(__file__).parent / 'ui'
    files = list(ui_dir.glob('*.py'))

    print(f"Processing {len(files)} files\n")

    fixed = 0
    for file_path in files:
        if fix_file(file_path):
            fixed += 1

    print(f"\n[DONE] Fixed {fixed} files")

if __name__ == '__main__':
    main()
