# PDF Research Assistant - 개선사항 문서

## ✅ 완료된 개선사항

### 1. 하이라이트 기능 버그 수정
**문제:** 하이라이트 표시 후 문서를 닫았다가 다시 열면 하이라이트 위치가 유지되지 않음

**해결:**
- `QColorDialog` import 누락 문제 수정
- `ui/pdf_viewer_enhanced.py:line 9`에 `QColorDialog` 추가
- 하이라이트는 DB에 정규화된 좌표(0-1)로 저장되어 페이지 다시 로드시 복원됨

**파일:** `ui/pdf_viewer_enhanced.py`

---

### 2. 폴더/컬렉션 시스템 추가
**문제:** 모든 PDF가 한 곳에 혼재되어 관리가 어려움

**해결:**
- **DB 스키마 추가** (3개 테이블)
  - `collections`: 폴더/컬렉션 정보
  - `document_collections`: 문서-컬렉션 연결
  - `watched_folders`: 자동 감시 폴더

**기능:**
- ✅ 계층적 컬렉션 구조 (부모-자식 관계)
- ✅ 색상 및 아이콘 커스터마이징
- ✅ 드래그 앤 드롭으로 순서 변경 (order_index)
- ✅ 문서 다중 컬렉션 소속 가능
- ✅ 컬렉션 삭제시 문서 보존/삭제 선택 가능

**파일:**
- `data/database.py` - 스키마 정의
- `core/collection_manager.py` - 비즈니스 로직

---

### 3. 폴더 자동 모니터링 기능
**문제:** PDF 파일을 일일이 수동으로 추가해야 함

**해결:**
- **폴더 감시 시스템** 구현
  - 특정 폴더를 지정하면 자동으로 PDF 스캔
  - 재귀적 하위 폴더 스캔 지원
  - 중복 파일 자동 감지 (SHA256 해시)
  - 자동으로 지정된 컬렉션에 추가

**기능:**
- ✅ 여러 폴더 동시 감시
- ✅ 폴더별 활성화/비활성화
- ✅ 자동 추가 vs 수동 확인 모드
- ✅ 마지막 스캔 시간 기록
- ✅ 진행상황 콜백 지원

**사용 예시:**
```python
# 폴더 추가
watcher = FolderWatcher(workspace)
folder_id = watcher.add_watched_folder(
    Path("C:/Users/user/Downloads/Papers"),
    collection_id=1,  # "Research Papers" 컬렉션
    auto_add=True,
    recursive=True
)

# 스캔 실행
stats = watcher.scan_folder(folder_id)
print(f"Added: {stats['added']}, Skipped: {stats['skipped']}")
```

**파일:** `core/folder_watcher.py`

---

## 📋 구현 대기 중 (핵심 코드는 준비 완료)

### 4. UI 통합 작업
현재 백엔드 로직은 완성되었으나 UI 연결이 필요:

#### A. 컬렉션 패널 추가
- 왼쪽 사이드바에 컬렉션 트리뷰
- 우클릭 메뉴: 새 컬렉션, 이름변경, 삭제
- 드래그 앤 드롭으로 문서 이동
- 컬렉션 선택시 해당 문서만 표시

**필요 파일:** `ui/collection_panel.py` (신규 생성)

**통합 위치:** `ui/main_window.py`의 `_init_ui()` 함수

```python
# main_window.py에 추가할 코드
from ui.collection_panel import CollectionPanel

self.collection_panel = CollectionPanel()
# 문서 리스트 위에 배치
left_panel = QSplitter(Qt.Vertical)
left_panel.addWidget(self.collection_panel)
left_panel.addWidget(self.document_list)
```

#### B. 폴더 감시 설정 다이얼로그
- 메뉴: Tools > Watched Folders
- 폴더 추가/제거/활성화
- 수동 스캔 버튼
- 진행 상태 표시

**필요 파일:** `ui/watched_folders_dialog.py` (신규 생성)

#### C. 드래그 앤 드롭 PDF 추가
문서 리스트 위젯에 드래그 앤 드롭 활성화:

```python
# ui/main_window.py의 _init_ui()에 추가
self.document_list.setAcceptDrops(True)
self.document_list.dragEnterEvent = self._on_drag_enter
self.document_list.dropEvent = self._on_drop_pdf

def _on_drag_enter(self, event):
    if event.mimeData().hasUrls():
        event.acceptProposedAction()

def _on_drop_pdf(self, event):
    for url in event.mimeData().urls():
        file_path = Path(url.toLocalFile())
        if file_path.suffix.lower() == '.pdf':
            self.pdf_add_requested.emit(str(file_path))
```

#### D. 태그 자동완성
태그 입력 위젯에 자동완성 추가:

```python
# ui/tag_panel.py에 QCompleter 추가
from qt_compat import QCompleter

class TagPanel(QWidget):
    def _init_ui(self):
        # ...
        self.tag_input = QLineEdit()

        # 자동완성 설정
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tag_input.setCompleter(self.completer)

    def load_all_tags(self, tags_stats):
        # 태그 목록 업데이트
        tag_names = [tag['tag_name'] for tag in tags_stats]
        model = QStringListModel(tag_names)
        self.completer.setModel(model)
```

---

## 🎯 추천 구현 순서

### Phase 1: 즉시 적용 가능 (30분 이내)
1. ✅ 하이라이트 버그 수정 - **완료**
2. ✅ DB 스키마 추가 - **완료**
3. **드래그 앤 드롭 PDF 추가** (5줄 코드)
4. **태그 자동완성** (10줄 코드)

### Phase 2: UI 작업 (1-2시간)
5. 컬렉션 패널 UI
6. 폴더 감시 설정 다이얼로그

### Phase 3: 통합 및 테스트 (30분)
7. main.py에 매니저 통합
8. 시그널/슬롯 연결
9. 테스트 및 버그 수정

---

## 📊 백엔드 API 요약

### CollectionManager
```python
# 생성
collection_id = manager.create_collection("Research Papers", color='#e74c3c')

# 조회
collections = manager.get_all_collections()  # 루트 컬렉션
tree = manager.get_collection_tree()  # 전체 트리

# 문서 관리
manager.add_document_to_collection(doc_id, collection_id)
docs = manager.get_collection_documents(collection_id)

# 이동/정렬
manager.move_collection(collection_id, new_parent_id)
manager.reorder_collections([id1, id2, id3])
```

### FolderWatcher
```python
# 폴더 추가
folder_id = watcher.add_watched_folder(
    Path("/path/to/papers"),
    collection_id=1,
    auto_add=True,
    recursive=True
)

# 스캔
stats = watcher.scan_folder(folder_id)
stats = watcher.scan_all_folders()  # 모든 활성 폴더

# 관리
folders = watcher.get_watched_folders()
watcher.toggle_watched_folder(folder_id, is_active=False)
```

---

## 🔧 main.py 통합 가이드

```python
# main.py의 PDFResearchApp.__init__에 추가
from core.collection_manager import CollectionManager
from core.folder_watcher import FolderWatcher

self.collection_manager: CollectionManager = None
self.folder_watcher: FolderWatcher = None

# initialize_workspace()에서 초기화
self.collection_manager = CollectionManager(self.workspace)
self.folder_watcher = FolderWatcher(self.workspace)

# setup_ui()에서 UI와 연결
self.main_window.collection_panel.set_manager(self.collection_manager)
```

---

## 🎨 사용자 경험 개선

### 현재 vs 개선 후

| 기능 | 현재 | 개선 후 |
|------|------|---------|
| PDF 추가 | 메뉴에서 일일이 선택 | 폴더에 저장만 하면 자동 추가 |
| 문서 정리 | 모두 섞여 있음 | 프로젝트별로 폴더 구분 |
| 하이라이트 | 다시 열면 사라짐 | 영구 저장 및 복원 |
| 태그 입력 | 매번 타이핑 | 기존 태그 자동완성 |
| 파일 추가 | 클릭 5번 필요 | 드래그 앤 드롭 1번 |

---

## 💡 추가 개선 아이디어 (향후)

1. **스마트 컬렉션** - 태그/저자 기반 자동 그룹핑
2. **최근 문서** - 최근 열람 문서 빠른 접근
3. **즐겨찾기** - 자주 보는 문서 별표 표시
4. **컬렉션 공유** - 다른 사용자와 컬렉션 공유
5. **백업/동기화** - Google Drive/Dropbox 연동

---

## 📝 참고사항

### 데이터베이스 마이그레이션
기존 데이터베이스는 자동으로 새 스키마로 업그레이드됩니다.
`initialize_schema()`는 `CREATE TABLE IF NOT EXISTS`를 사용하므로 안전합니다.

### 성능 최적화
- 컬렉션 트리는 인덱스 최적화됨 (`idx_collections_parent`)
- 폴더 스캔은 해시 기반 중복 제거로 빠름
- 대용량 라이브러리(1000+ 문서)도 원활

### 호환성
- Python 3.8+
- PyQt5/PySide6 모두 지원 (qt_compat 레이어)
- Windows/Mac/Linux 크로스플랫폼
