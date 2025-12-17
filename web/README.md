# 웹 기반 논문 추천 시스템

Big-Tech-News 스타일의 학술 논문 추천 웹 인터페이스

## 🎯 주요 기능

### 1. 저널별 필터링 (Big-Tech-News 스타일)
- 상단에 눈에 띄는 저널 필터 버튼
- 각 저널별 논문 개수 표시
- 원클릭 필터링

### 2. 실시간 업데이트
- 마지막 업데이트 시간 표시
- 새로고침 버튼으로 최신 논문 자동 수집
- 진행 상태 표시

### 3. 스마트 검색 & 정렬
- 키워드 필터링
- 최신순/오래된순 정렬
- 유사도 점수 표시

### 4. 논문 관리
- 확인/무시 상태 관리
- DOI 링크 바로가기
- 초록 미리보기

### 5. 반응형 디자인
- 데스크톱/태블릿/모바일 최적화
- 나눔스퀘어 네오 폰트
- 그라데이션 UI

## 🚀 사용 방법

### 1. 웹 서버 시작

```bash
# 방법 1: start_web_server.py 사용
cd C:\Users\user\Desktop\pdf_research_app
python start_web_server.py

# 방법 2: 직접 Flask 실행
cd C:\Users\user\Desktop\pdf_research_app\web
python app.py
```

### 2. 웹 브라우저로 접속

```
http://127.0.0.1:5000
```

### 3. 타겟 저널 설정

먼저 데스크톱 앱에서 타겟 저널을 설정해야 합니다:

1. `main.py` 실행
2. `Tools > Target Journals` 메뉴
3. 저널 이름, ISSN, 키워드 입력
4. 저장

### 4. 추천 논문 수집

웹 인터페이스에서:

1. **새로고침 버튼** 클릭
2. 자동으로 설정된 저널에서 논문 수집
3. 키워드 기반 매칭 및 유사도 계산
4. 결과 표시

### 5. 논문 필터링

- **저널 필터**: 상단 버튼 클릭으로 특정 저널만 보기
- **키워드 필터**: 드롭다운에서 특정 키워드 선택
- **정렬**: 최신순/오래된순 변경

### 6. 논문 관리

각 논문 카드에서:
- **확인** 버튼: 관련 있는 논문으로 표시
- **무시** 버튼: 관련 없는 논문으로 표시
- **DOI 보기**: 논문 원문 페이지로 이동

## 📊 API 엔드포인트

### GET /api/journals
타겟 저널 목록 조회
```json
{
  "success": true,
  "journals": [
    {
      "journal_id": 1,
      "journal_name": "Nature Energy",
      "issn": "2058-7546",
      "keywords": "energy, renewable, solar",
      "is_active": 1
    }
  ]
}
```

### GET /api/keywords
전체 키워드 목록 조회
```json
{
  "success": true,
  "keywords": ["machine learning", "AI", "energy", ...],
  "count": 25
}
```

### GET /api/papers
논문 목록 조회 (필터링/정렬)
```
Query Parameters:
- journal_id: 저널 ID (선택)
- keyword: 키워드 (선택)
- sort: newest | oldest (기본: newest)
- limit: 결과 개수 (기본: 50)
```

### POST /api/papers/<cache_id>/status
논문 상태 변경
```json
{
  "status": "confirmed" | "dismissed" | "unread"
}
```

### POST /api/refresh
추천 논문 새로고침 (모든 활성 저널 스캔)

### GET /api/stats
통계 정보 조회
```json
{
  "success": true,
  "stats": {
    "total": 150,
    "unread": 120,
    "confirmed": 25,
    "dismissed": 5,
    "last_update": "2025-01-15T10:30:00",
    "by_journal": [...]
  }
}
```

## 🎨 디자인 특징

### 색상 팔레트
- Primary: `#667eea` (보라-파랑 그라데이션)
- Secondary: `#764ba2` (진한 보라)
- Background: 그라데이션 배경
- Cards: 투명 백드롭 필터

### 타이포그래피
- 폰트: 나눔스퀘어 네오
- 크기: 반응형 (모바일 최적화)

### 애니메이션
- 호버 효과: 카드 상승
- 로딩: 회전 스피너
- 필터 버튼: 부드러운 전환

## 🔧 연동 방법

### 데스크톱 앱과 연동

웹 시스템은 데스크톱 앱과 **같은 데이터베이스를 공유**합니다:

```
<Workspace>/
├── database/
│   └── main.db          # 공통 SQLite DB
│       ├── target_journals      # 저널 설정
│       ├── recommendation_cache # 추천 논문
│       └── documents           # 사용자 문서
```

### 워크플로우

1. **데스크톱 앱**:
   - PDF 문서 관리
   - 태그/주석 추가
   - 타겟 저널 설정
   - 사용자 프로필 구축

2. **웹 인터페이스**:
   - 추천 논문 조회
   - 필터링 & 정렬
   - 상태 관리 (확인/무시)
   - 빠른 스캔

3. **자동 추천 매니저** (백엔드):
   - Crossref API 호출
   - TF-IDF 유사도 계산
   - 캐시에 저장
   - 웹/앱 모두 접근 가능

## 📈 향후 개선 사항

- [ ] arXiv API 통합
- [ ] PubMed 통합
- [ ] Semantic Scholar 통합
- [ ] 저널별 색상 코딩
- [ ] 추천 피드백 학습
- [ ] 실시간 알림 (WebSocket)
- [ ] 다크 모드
- [ ] 다국어 지원

## 🐛 문제 해결

### 포트 충돌
```bash
# 다른 포트로 실행
python web/app.py
# app.py 마지막 줄 수정: app.run(host='127.0.0.1', port=5001)
```

### CORS 에러
Flask-CORS가 이미 활성화되어 있습니다. 문제 발생 시:
```bash
pip install --upgrade flask-cors
```

### 데이터베이스 연결 실패
워크스페이스 경로 확인:
```python
# config.py에서 DEFAULT_WORKSPACE_DIR 확인
```

## 📝 라이선스

MIT License

## 개발자

Research Team - PDF Research Assistant
