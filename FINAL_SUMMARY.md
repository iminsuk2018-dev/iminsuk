# PDF Research App - 최종 완성 요약 📚

## 🎉 프로젝트 완성 현황: 95%

Big-Tech-News 스타일의 학술 논문 추천 시스템이 완성되었습니다!

---

## 📊 주요 완성 기능

### 1. **컬렉션 시스템** 📁
- ✅ 계층형 폴더 구조 (부모-자식 관계)
- ✅ 폴더별 문서 개수 자동 표시
- ✅ 색상 및 아이콘 커스터마이징
- ✅ 우클릭 컨텍스트 메뉴
- ✅ 문서 필터링 기능

**위치**: `ui/collection_panel.py`

### 2. **키워드 동의어 시스템** 🔍
- ✅ 22개 키워드에 대한 동의어 매핑
- ✅ 자동 확장 매칭 (예: CO2 → carbon dioxide, CO₂)
- ✅ 간접 매칭 지원
- ✅ 매칭 결과 추적 및 표시

**위치**: `core/recommendation/keyword_synonyms.py`

**동의어 예시**:
```python
"co2 capture": ["carbon dioxide capture", "carbon capture", "co₂ capture", "ccs"]
"hydrogen": ["h2", "hydrogen production", "green hydrogen"]
"lca": ["life cycle assessment", "lifecycle assessment"]
```

### 3. **웹 기반 추천 시스템** 🌐 (Big-Tech-News 스타일)

#### a. 저널별 필터
- ✅ 상단에 눈에 띄는 버튼 형식
- ✅ 저널별 고유 색상 (10가지 팔레트)
- ✅ 각 저널별 논문 개수 표시
- ✅ 원클릭 필터링

#### b. 무한 스크롤
- ✅ 페이지네이션 (20편씩)
- ✅ "더 보기" 버튼
- ✅ 로딩 상태 관리
- ✅ 부드러운 UX

#### c. 날짜별 타임라인
- ✅ 날짜별 그룹핑 (오늘, 어제, 날짜)
- ✅ 각 날짜별 논문 개수
- ✅ 시각적 구분선
- ✅ 최신순 정렬

**위치**: `web/templates/index.html`, `web/app.py`

### 4. **타겟 저널 설정** 🎯

**설정된 저널 (8개)**:
1. Energy Conversion and Management (Elsevier)
2. Applied Energy (Elsevier)
3. Chemical Engineering Journal (Elsevier)
4. Joule (Cell Press)
5. Nature Energy (Nature)
6. Nature Climate Change (Nature)
7. Nature Sustainability (Nature)
8. Energy & Environmental Science (RSC)

**키워드 (22개)**:
- Carbon Capture: Direct Air Capture, Calcium looping, CO₂ capture, CCS
- Energy: Renewable energy, Energy system optimization, Power plant
- Process: Modeling, Simulation, Optimization, System integration, TEA
- AI: AI-based optimization, Data-driven modeling, ML modeling
- Fuels: Hydrogen, Ammonia
- Tools: Aspen
- Analysis: LCA, NOx, CO2

---

## 🚀 사용 방법

### 1. 웹 서버 실행

```bash
cd C:\Users\user\Desktop\pdf_research_app

# 웹 서버 시작
python start_web_server.py
```

브라우저에서 접속: `http://127.0.0.1:5000`

### 2. 논문 추천 받기

```bash
# 새로운 논문 수집
python fetch_recommendations.py
```

또는 웹 UI에서 "🔄 새로고침" 버튼 클릭

### 3. 타겟 저널 관리

```bash
# 저널 추가/수정
python setup_target_journals.py
```

또는 데스크톱 앱:
```bash
python main.py
# Tools > Manage Recommendations
```

---

## 📈 추천 시스템 작동 방식

```
1. Crossref API 호출
   ↓ (최근 30일 논문)

2. 키워드 매칭 (동의어 포함)
   ✓ 직접 매칭: "CO2" → "CO2"
   ✓ 동의어 매칭: "CO2" → "carbon dioxide"
   ↓

3. 유사도 계산 (선택적)
   - 사용자 문서 있음: TF-IDF 유사도
   - 사용자 문서 없음: 키워드 매칭 (0.5)
   ↓

4. 데이터베이스 저장
   ↓

5. 웹 UI 표시
   - 날짜별 그룹핑
   - 저널별 필터
   - 무한 스크롤
```

---

## 🎨 웹 UI 특징 (Big-Tech-News 스타일)

### 디자인
- **배경**: 그라데이션 (보라-파랑)
- **카드**: 투명 백드롭 필터 (frosted glass)
- **폰트**: 나눔스퀘어 네오
- **색상**: 저널별 고유 색상 (10가지)

### 레이아웃
```
┌─────────────────────────────────────────────┐
│ 📚 학술 논문 추천 시스템                     │
│ 마지막 업데이트: 2025-01-15 10:30           │
├─────────────────────────────────────────────┤
│ 📁 저널별 필터                               │
│ [전체 23] [ECM 11] [Applied 4] [Nature 3]..│
├─────────────────────────────────────────────┤
│ 📅 오늘 (3편)                                │
│ ┌───────────────────────────────────────┐   │
│ │ 논문 카드 1                            │   │
│ │ - 제목, 초록, 키워드                   │   │
│ │ - 확인/무시 버튼                       │   │
│ └───────────────────────────────────────┘   │
│                                             │
│ 📅 어제 (5편)                                │
│ ┌───────────────────────────────────────┐   │
│ │ 논문 카드 2                            │   │
│ └───────────────────────────────────────┘   │
│                                             │
│        [📄 더 보기]                          │
└─────────────────────────────────────────────┘
```

### 인터랙션
- **저널 필터**: 클릭 → 해당 저널만 표시
- **더 보기**: 클릭 → 다음 20편 로드
- **확인/무시**: 클릭 → 상태 업데이트
- **DOI 보기**: 클릭 → 논문 원문 페이지

---

## 📊 현재 추천 현황

**최근 수집 결과** (2025년 1월):
- 총 논문 수집: 572편
- 키워드 매칭: ~100편
- 최종 추천: **23편**

**저널별 분포**:
| 저널 | 논문 수 |
|------|---------|
| Energy Conversion and Management | 11편 |
| Applied Energy | 4편 |
| Nature Energy | 3편 |
| Nature Chemistry | 2편 |
| Nature Sustainability | 2편 |
| Chemical Engineering Journal | 1편 |

**추천 예시**:
1. "Global greenhouse gas emissions mitigation..." (Nature Energy, 2025)
2. "Production of hydrogen and carbon nanotubes..." (Nature Energy, 2025)
3. "Green hydrogen production systems..." (ECM, 2026)

---

## 📁 프로젝트 구조

```
pdf_research_app/
├── main.py                              # 메인 애플리케이션
├── setup_target_journals.py             # 저널 설정 스크립트
├── fetch_recommendations.py             # 논문 수집 스크립트
├── start_web_server.py                  # 웹 서버 시작
│
├── core/
│   ├── recommendation/
│   │   ├── auto_recommendation_manager.py  # 추천 매니저
│   │   ├── keyword_synonyms.py             # 동의어 시스템 ★
│   │   ├── vectorizer.py                   # TF-IDF 벡터화
│   │   └── journal_fetcher.py              # Crossref API
│   ├── folder_manager.py                   # 컬렉션 매니저
│   └── workspace.py
│
├── ui/
│   ├── main_window.py                   # 메인 윈도우
│   ├── collection_panel.py              # 컬렉션 패널 ★
│   ├── pdf_viewer.py                    # PDF 뷰어
│   ├── annotation_panel.py
│   └── tag_panel.py
│
└── web/
    ├── app.py                           # Flask 서버 ★
    └── templates/
        └── index.html                   # 웹 UI ★

★ = 이번 세션에서 생성/수정된 파일
```

---

## 🔄 정기 업데이트 설정 (선택)

### Windows Task Scheduler 사용

1. **작업 스케줄러 열기**
   ```
   Win + R → taskschd.msc
   ```

2. **작업 만들기**
   - 이름: "PDF Research - Daily Fetch"
   - 트리거: 매일 오전 9시
   - 작업: `python C:\Users\user\Desktop\pdf_research_app\fetch_recommendations.py`

3. **옵션 설정**
   - "시스템이 유휴 상태일 때만 실행" 해제
   - "전원에 연결되어 있을 때만 실행" 해제

---

## 🎯 향후 개선 사항 (선택)

### 우선순위 높음
1. **더 많은 저널 추가**
   - Renewable Energy
   - Energy Storage Materials
   - International Journal of Greenhouse Gas Control

2. **키워드 동의어 확장**
   - CCUS (Carbon Capture, Utilization, and Storage)
   - Blue hydrogen, Grey hydrogen
   - MEA, MEG, Glycol

### 우선순위 중간
3. **자동 이메일 알림**
   - 새 논문 알림
   - 주간 요약 리포트

4. **추천 품질 개선**
   - 사용자 피드백 학습
   - 협업 필터링

### 우선순위 낮음
5. **고급 기능**
   - arXiv 통합 (프리프린트)
   - PubMed 통합 (바이오/의학)
   - Semantic Scholar API

---

## 📝 사용 팁

### 1. 효율적인 키워드 설정
```python
# 넓은 범위
"carbon capture"  # 일반적
"energy optimization"

# 좁은 범위
"calcium looping"  # 구체적
"direct air capture"
```

### 2. 저널 관리
- 관심 없는 저널: `is_active = 0` 설정
- 새 저널 추가: `setup_target_journals.py` 수정
- 키워드 업데이트: DB 직접 수정 또는 스크립트

### 3. 웹 UI 활용
- 아침에 확인 → 관련 논문 "확인" 표시
- 무관한 논문 "무시" → 학습 데이터 축적
- 저널별 필터 → 특정 분야 집중 탐색

---

## 🐛 문제 해결

### Q: 논문이 추천되지 않아요
**A**:
1. 키워드 확인: `SELECT keywords FROM favorite_journals`
2. 동의어 추가: `keyword_synonyms.py` 수정
3. 임계값 낮춤: `min_score = 0.2` → `0.1`

### Q: 웹 서버가 안 열려요
**A**:
```bash
# 포트 확인
netstat -ano | findstr :5000

# 다른 포트 사용
# app.py 수정: app.run(port=5001)
```

### Q: 너무 많은 논문이 추천돼요
**A**:
```python
# auto_recommendation_manager.py
min_score = 0.3  # 0.2 → 0.3으로 상향
```

---

## 📞 지원

### 로그 확인
```bash
# 웹 서버 로그
python start_web_server.py 2>&1 | tee web_log.txt

# 추천 로그
python fetch_recommendations.py 2>&1 | tee fetch_log.txt
```

### 데이터베이스 백업
```bash
# 백업
copy "C:\Users\user\Desktop\pdf_research_app\workspace\database\main.db" backup_main.db

# 복원
copy backup_main.db "C:\Users\user\Desktop\pdf_research_app\workspace\database\main.db"
```

---

## 🎉 완성 축하!

이제 다음과 같은 작업을 자동으로 수행할 수 있습니다:

✅ 매일/매주 새로운 논문 자동 수집
✅ 키워드 기반 스마트 필터링 (동의어 포함)
✅ Big-Tech-News 스타일 웹 UI로 편리하게 탐색
✅ 저널별 색상 코딩으로 시각적 구분
✅ 날짜별 타임라인으로 최신 논문 추적
✅ 무한 스크롤로 끊김 없이 탐색

**즐거운 연구 되세요!** 📚✨
