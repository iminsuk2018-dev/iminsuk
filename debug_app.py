"""
디버깅용 간단한 앱
"""
import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("="*50)
print("PDF Research App - Debug Mode")
print("="*50)

# 1. Import 테스트
print("\n[1] Testing imports...")
try:
    import fitz
    print(f"  [OK] PyMuPDF: {fitz.version}")
except Exception as e:
    print(f"  [ERROR] PyMuPDF: {e}")
    sys.exit(1)

try:
from qt_compat import QtCore, QtWidgets
    print(f"  [OK] PySide6")
except Exception as e:
    print(f"  [ERROR] PySide6: {e}")
    print("\n  Trying to continue anyway...")

# 2. Workspace 초기화 테스트
print("\n[2] Testing workspace initialization...")
try:
    from core.workspace import Workspace
    from config import DEFAULT_WORKSPACE_DIR

    test_workspace = DEFAULT_WORKSPACE_DIR / "test"
    test_workspace.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(test_workspace)
    workspace.initialize()
    print(f"  [OK] Workspace at: {test_workspace}")
    print(f"  [OK] DB at: {workspace.db_path}")

except Exception as e:
    print(f"  [ERROR] Workspace: {e}")
    import traceback
    traceback.print_exc()

# 3. PDF 핸들러 테스트
print("\n[3] Testing PDF handler...")
try:
    from data.pdf_handler import PDFHandler

    pdf_handler = PDFHandler()

    # 샘플 PDF 찾기
    test_paths = [
        Path.home() / "Downloads",
        Path.home() / "Documents"
    ]

    sample_pdf = None
    for path in test_paths:
        if path.exists():
            pdfs = list(path.glob("*.pdf"))
            if pdfs:
                sample_pdf = pdfs[0]
                break

    if sample_pdf:
        print(f"  Testing with: {sample_pdf.name}")

        page_count = pdf_handler.get_page_count(sample_pdf)
        print(f"  [OK] Page count: {page_count}")

        img_data = pdf_handler.render_page(sample_pdf, 0, 1.0)
        print(f"  [OK] Rendered page 1, size: {len(img_data)} bytes")

    else:
        print(f"  [WARN] No PDF found for testing")

except Exception as e:
    print(f"  [ERROR] PDF handler: {e}")
    import traceback
    traceback.print_exc()

# 4. 메타데이터 추출 테스트
if sample_pdf:
    print("\n[4] Testing metadata extraction...")
    try:
        from utils.pdf_extractor import PDFMetadataExtractor

        extractor = PDFMetadataExtractor()
        metadata = extractor.extract_all_metadata(sample_pdf)

        print(f"  Title: {metadata.get('title')}")
        print(f"  Authors: {metadata.get('authors')}")
        print(f"  Year: {metadata.get('year')}")
        print(f"  [OK] Metadata extracted")

    except Exception as e:
        print(f"  [ERROR] Metadata: {e}")

# 5. DAO 테스트
print("\n[5] Testing DAO...")
try:
    from data.dao.document_dao import DocumentDAO

    db = workspace.get_database()
    doc_dao = DocumentDAO(db)

    count = doc_dao.count()
    print(f"  [OK] Document count: {count}")

except Exception as e:
    print(f"  [ERROR] DAO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Debug test complete!")
print("="*50)
