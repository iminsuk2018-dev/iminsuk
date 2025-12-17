# 📚 학술 논문 추천 시스템 (PDF Research App)

Big-Tech-News 스타일의 학술 논문 추천 시스템입니다.

## ✨ 주요 기능

- 🔍 **키워드 기반 추천**: 22개 키워드로 자동 논문 추천
- 🔄 **동의어 확장**: CO2 → carbon dioxide, H2 → hydrogen 등
- 🚫 **촉매 논문 제외**: 금속 촉매 관련 논문 자동 필터링
- 📊 **저널별 필터**: 8개 주요 저널 색상 코딩
- 📅 **타임라인 뷰**: 날짜별 그룹핑 (오늘, 어제, 날짜)
- ♾️ **무한 스크롤**: 20편씩 로드

## 🎯 타겟 저널

1. Energy Conversion and Management
2. Applied Energy
3. Chemical Engineering Journal
4. Joule
5. Nature Energy
6. Nature Climate Change
7. Nature Sustainability
8. Energy & Environmental Science

## 🔑 추천 키워드

**Carbon Capture**: Direct Air Capture, Calcium looping, CO₂ capture, Carbon neutrality, CCS

**Process Engineering**: TEA, Process modeling, Process simulation, Process optimization, System integration

**Energy**: Renewable energy, Energy system optimization, Power plant

**AI/Data**: AI-based optimization, Data-driven modeling

**Fuels**: Hydrogen, Ammonia

**Tools**: Aspen

**Analysis**: LCA, NOx, CO2

## 🚀 로컬 실행

### 1. 의존성 설치

```bash
pip install -r requirements-web.txt
```

### 2. 논문 수집

```bash
python fetch_recommendations.py
```

### 3. 웹 서버 실행

```bash
python start_web_server.py
```

http://127.0.0.1:5000 에서 확인

## 🌐 배포하기

### Railway 배포 (추천)

**1단계: GitHub에 코드 푸시**

```bash
cd C:\Users\user\Desktop\pdf_research_app
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pdf-research-app.git
git push -u origin main
```

**2단계: Railway 배포**
1. https://railway.app 접속 및 GitHub 로그인
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. 저장소 선택 (pdf-research-app)
5. 자동 배포 시작 (railway.json 설정 자동 적용)

**3단계: 도메인 확인**
- 배포 완료 후 `https://your-app.railway.app` 도메인 생성
- Settings → Generate Domain에서 커스텀 도메인 설정 가능

### Render 배포 (대안)

**1단계: GitHub에 코드 푸시** (위와 동일)

**2단계: Render 배포**
1. https://render.com 접속 및 GitHub 로그인
2. "New" → "Web Service" 클릭
3. GitHub 저장소 연결
4. 자동 배포 시작 (render.yaml 설정 자동 적용)

## 📁 프로젝트 구조

```
pdf_research_app/
├── web/
│   ├── app.py                    # Flask 서버
│   └── templates/
│       └── index.html            # 웹 UI (Big-Tech-News 스타일)
├── core/
│   ├── recommendation/
│   │   ├── auto_recommendation_manager.py
│   │   ├── keyword_synonyms.py   # 동의어 시스템 ★
│   │   ├── journal_fetcher.py    # Crossref API
│   │   └── vectorizer.py
│   └── workspace.py
├── requirements-web.txt          # 웹 배포용 의존성
├── Procfile                      # Railway/Render 실행 명령
├── railway.json                  # Railway 설정
└── render.yaml                   # Render 설정
```

## 👨‍💻 제작자

**Minsuk Lim** (PIDJB / JBNU)
📧 iminsuk2018@jbnu.ac.kr

## 📄 라이선스

MIT License

### 첫 실행
1. 앱을 처음 실행하면 Workspace 생성 여부를 묻습니다
2. 기본 경로는 `C:\Users\user\Documents\PDFResearch`입니다
3. 또는 Google Drive, OneDrive 등의 폴더를 선택할 수 있습니다

### PDF 추가
1. `File > Add PDF...` 또는 툴바의 "Add PDF" 버튼 클릭
2. PDF 파일 선택
3. 자동으로 메타데이터가 추출되고 데이터베이스에 저장됩니다

### PDF 보기
1. 왼쪽 문서 목록에서 PDF 선택
2. 중앙 뷰어에서 PDF 확인
3. 줌 버튼으로 확대/축소
4. Previous/Next 버튼으로 페이지 이동

### 메모 작성
1. PDF를 열고 원하는 페이지로 이동
2. 오른쪽 "Notes" 탭에서 메모 작성
3. "Add Note" 버튼으로 메모 추가
4. 메모 클릭 후 수정/삭제 가능

### 태그 관리
1. 문서를 선택한 상태에서 오른쪽 "Tags" 탭 클릭
2. 태그 입력란에 태그 이름 입력 후 "Add Tag"
3. 또는 "All Tags" 목록에서 기존 태그 더블클릭
4. 태그 우클릭으로 제거 가능

### 검색
1. `Ctrl+F` 또는 툴바의 "Search" 버튼 클릭
2. 검색어 입력
3. 검색 대상 선택 (제목, 초록, 메모, 태그)
4. 결과 더블클릭으로 해당 문서 열기

## Workspace 구조

```
<Workspace>/
├── database/
│   └── main.db          # SQLite 데이터베이스
├── pdfs/
│   └── *.pdf            # PDF 파일들
├── exports/             # 내보내기 결과
└── .pdfsync             # 동기화 메타데이터
```

## Google Drive 동기화

1. Google Drive 폴더 내에 Workspace 생성
2. 앱에서 해당 폴더를 Workspace로 선택
3. Google Drive가 자동으로 동기화합니다

**주의**: 여러 기기에서 동시에 앱을 실행하면 충돌이 발생할 수 있습니다.

## 개발

### 프로젝트 구조

```
pdf_research_app/
├── main.py              # 앱 진입점
├── config.py            # 설정
├── requirements.txt     # 의존성
│
├── ui/                  # PySide6 UI
│   ├── main_window.py
│   ├── pdf_viewer.py
│   └── widgets/
│
├── core/                # 비즈니스 로직
│   ├── workspace.py
│   └── recommendation/
│
├── data/                # 데이터 레이어
│   ├── database.py
│   ├── pdf_handler.py
│   └── dao/
│
└── utils/               # 유틸리티
    ├── pdf_extractor.py
    └── logger.py
```

### 로깅

로그는 다음 위치에 저장됩니다:
- 콘솔: INFO 레벨 이상
- 파일: `<Workspace>/app.log` (DEBUG 레벨 이상)

## 문제 해결

### 앱 실행 테스트

먼저 디버그 모드로 기본 기능을 테스트하세요:

```bash
cd C:\Users\user\Desktop\pdf_research_app
python debug_app.py
```

모든 항목이 [OK]로 표시되면 정상입니다.

### PyMuPDF 설치 실패
```bash
pip install --upgrade pip
pip install PyMuPDF
```

### PySide6 DLL 로드 실패

이 에러는 무시해도 됩니다. 앱이 실행되면 정상입니다.

또는 conda로 재설치:
```bash
conda install -c conda-forge pyside6
```

### PDF가 로드되지 않음

1. **콘솔 로그 확인**:
   - 터미널에서 `python main.py` 실행
   - 에러 메시지 확인

2. **테스트 스크립트 실행**:
   ```bash
   python test_pdf.py
   ```

3. **일반적인 원인**:
   - PDF 파일이 손상되었을 수 있음
   - 매우 큰 PDF 파일 (100MB 이상)
   - 암호화된 PDF

4. **로그 파일 확인**:
   ```
   C:\Users\user\Documents\PDFResearch\app.log
   ```

### 자세한 디버그 로그 보기

main.py를 실행하면 콘솔에 자세한 로그가 출력됩니다:
```bash
python main.py
```

PDF 추가/로드 시 나오는 로그를 확인하세요.

## 라이선스

MIT License

## 🌐 웹 기반 추천 시스템 (NEW!)

Big-Tech-News 스타일의 웹 인터페이스가 추가되었습니다!

### 실행 방법
```bash
# 웹 서버 시작
python start_web_server.py

# 브라우저에서 접속
http://127.0.0.1:5000
```

### 주요 기능
- 📁 **저널별 필터**: 상단에 눈에 띄는 버튼 형식
- 🔄 **실시간 업데이트**: 최신 논문 자동 수집
- 🎯 **스마트 필터링**: 키워드, 정렬, 유사도 기반
- 📱 **반응형 디자인**: 모바일/태블릿 최적화
- ⏰ **마지막 업데이트 시간**: 데이터 신선도 확인

### 데스크톱 앱과의 연동
- 같은 데이터베이스 공유 (SQLite)
- 앱에서 설정한 타겟 저널 사용
- 웹에서 상태 관리 (확인/무시)
- 실시간 동기화

자세한 내용은 [web/README.md](web/README.md)를 참고하세요.

## 개발자

Research Team
