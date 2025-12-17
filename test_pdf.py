"""
간단한 PDF 테스트 스크립트
"""
import sys
from pathlib import Path

# PyMuPDF 테스트
try:
    import fitz
    print("[OK] PyMuPDF (fitz) imported successfully")
    print(f"  Version: {fitz.version}")
except ImportError as e:
    print(f"[ERROR] PyMuPDF import failed: {e}")
    sys.exit(1)

# PySide6 테스트
try:
from qt_compat import QtWidgets
    print("[OK] PySide6 imported successfully")
except ImportError as e:
    print(f"[ERROR] PySide6 import failed: {e}")
    sys.exit(1)

# PDF 파일 확인
print("\nTesting PDF operations...")

# 테스트용 샘플 PDF 경로 (Downloads에 PDF가 있다면)
test_paths = [
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Desktop"
]

pdf_files = []
for path in test_paths:
    if path.exists():
        pdfs = list(path.glob("*.pdf"))
        if pdfs:
            print(f"  Found {len(pdfs)} PDF(s) in {path}")
            pdf_files.extend(pdfs[:1])  # 첫 번째만

if pdf_files:
    test_pdf = pdf_files[0]
    print(f"\nTesting with: {test_pdf.name}")

    try:
        doc = fitz.open(str(test_pdf))
        print(f"[OK] PDF opened successfully")
        print(f"  Pages: {doc.page_count}")

        # 첫 페이지 렌더링 테스트
        if doc.page_count > 0:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            print(f"[OK] Page rendered successfully")
            print(f"  Size: {pix.width}x{pix.height}")

        doc.close()
        print("\n[OK] All tests passed!")

    except Exception as e:
        print(f"[ERROR] PDF test failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n[WARN] No PDF files found for testing")
    print("  Please place a PDF file in Downloads, Documents, or Desktop")

print("\nTest complete.")
