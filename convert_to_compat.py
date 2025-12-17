"""
Script to convert PySide6 imports to use qt_compat layer
"""
import re
from pathlib import Path

def convert_file(file_path):
    """Convert a single file"""
    print(f"Converting: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Pattern to match PySide6 imports
    # Match: from PySide6.QtXxx import (...)
    pattern1 = r'from PySide6\.Qt(\w+) import \('
    # Match: from PySide6.QtXxx import A, B, C
    pattern2 = r'from PySide6\.Qt(\w+) import ([^\n]+)'

    # Check if file already uses qt_compat
    if 'from qt_compat import' in content:
        print(f"  Skipping (already uses qt_compat): {file_path.name}")
        return False

    # Check if it's the qt_compat file itself
    if file_path.name == 'qt_compat.py':
        print(f"  Skipping (is qt_compat): {file_path.name}")
        return False

    # Find all PySide6 imports
    imports_to_add = set()

    # Match all from PySide6.QtXxx import statements
    matches = re.finditer(r'from PySide6\.(Qt\w+) import', content)
    for match in matches:
        qt_module = match.group(1)
        imports_to_add.add(qt_module)

    if not imports_to_add:
        print(f"  No PySide6 imports found: {file_path.name}")
        return False

    # Build new import statement
    new_imports = ', '.join(sorted(imports_to_add))
    new_import_line = f"from qt_compat import {new_imports}\n"

    # Remove all PySide6 import lines
    lines = content.split('\n')
    new_lines = []
    import_added = False
    skip_next = False

    for i, line in enumerate(lines):
        # Check if this is a PySide6 import
        if 'from PySide6' in line:
            # Check if it's a multi-line import
            if line.rstrip().endswith('(') or (i > 0 and lines[i-1].rstrip().endswith('(')):
                # Start of multi-line import, skip until we find the closing paren
                skip_next = True
                continue

            # Add compat import if not yet added
            if not import_added:
                new_lines.append(new_import_line.rstrip())
                import_added = True
            continue

        # Check if we're skipping multi-line import
        if skip_next:
            if ')' in line:
                skip_next = False
            continue

        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Replace Signal and Slot if present
    if 'Signal' in content or 'Slot' in content:
        # Add Signal and Slot to imports if they're used
        if 'from qt_compat import' in content:
            # Find the import line and add Signal/Slot
            content = content.replace(
                new_import_line.rstrip(),
                new_import_line.rstrip() + '\nfrom qt_compat import Signal, Slot'
            )

    # Write back
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Converted: {file_path.name}")
        return True
    else:
        print(f"  No changes: {file_path.name}")
        return False

def main():
    """Convert all Python files in the project"""
    project_dir = Path(__file__).parent

    # Find all .py files
    py_files = list(project_dir.rglob('*.py'))

    print(f"Found {len(py_files)} Python files\n")

    converted = 0
    for py_file in py_files:
        if convert_file(py_file):
            converted += 1

    print(f"\n[DONE] Converted {converted} files")

if __name__ == '__main__':
    main()
