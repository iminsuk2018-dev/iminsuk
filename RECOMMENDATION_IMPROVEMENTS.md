# 추천 시스템 개선 사항

## 현재 구현 상태

### ✅ 완성된 기능

1. **TF-IDF 벡터화 기반 추천**
   - `vectorizer.py`: sklearn TF-IDF 기반 문서 유사도 계산
   - 사용자 프로필 생성 (문서 제목, 초록, 태그, 주석 포함)
   - Cosine similarity를 통한 추천 스코어링

2. **Crossref API 통합**
   - `journal_fetcher.py`: 학술 저널 최근 논문 수집
   - 저널명, 날짜 범위로 필터링
   - DOI, ISSN 검색 기능

3. **추천 엔진**
   - `engine.py`: 통합 추천 로직
   - 사용자 코퍼스 자동 생성
   - 추천 이유 설명 (공통 키워드, 유사 문서)

4. **추천 UI**
   - `recommendation_dialog.py`: 추천 다이얼로그
   - 백그라운드 스레드 처리
   - 진행상황 표시

## 🔴 미완성/문제점

### 1. arXiv API 통합 미구현
**파일:** `core/recommendation/journal_fetcher.py:184-231`

```python
# TODO: Implement XML parsing
logger.warning("arXiv parsing not implemented yet")
return []
```

**문제:**
- ArxivFetcher 클래스는 있지만 XML 파싱이 구현되지 않음
- arXiv는 무료 프리프린트 저장소로 매우 유용함

**해결 방법:**
```python
import xml.etree.ElementTree as ET

def fetch_recent_articles(self, category: str, max_results: int = 50):
    # ... API 호출 ...

    # Parse XML
    root = ET.fromstring(response.content)
    namespace = {'atom': 'http://www.w3.org/2005/Atom'}

    articles = []
    for entry in root.findall('atom:entry', namespace):
        title = entry.find('atom:title', namespace).text
        abstract = entry.find('atom:summary', namespace).text
        # ... 파싱 로직 ...
```

### 2. 저널 즐겨찾기 관리 미완성
**DB 테이블:** `favorite_journals` (존재)

**현재 상태:**
- DB에 테이블은 있지만 매니저 클래스가 없음
- UI에서 즐겨찾기 관리 불가능

**필요 기능:**
- 저널 추가/제거 (`FavoriteJournalManager`)
- 정기 자동 스캔 (매주/매일)
- 새 논문 알림

### 3. 추천 캐싱 미구현
**DB 테이블:** `recommendation_cache` (존재)

**문제:**
- Crossref API는 rate limit 있음
- 매번 API 호출하면 느림
- 캐시 테이블이 있지만 사용되지 않음

**해결:**
```python
def generate_recommendations(self, journal_name, days_back):
    # Check cache first
    cached = self._get_cached_recommendations(journal_name, max_age_hours=24)
    if cached:
        return cached

    # Generate new recommendations
    recommendations = ...

    # Save to cache
    self._save_to_cache(journal_name, recommendations)

    return recommendations
```

### 4. 추천 설명 개선 필요
**파일:** `core/recommendation/engine.py:128-164`

**현재 문제:**
- 설명이 단순함 ("높은 관련성 (유사도: 0.75)")
- 왜 추천되는지 명확하지 않음

**개선:**
- 더 구체적인 설명
- 시각적 표현 (진행 바, 아이콘)
- 추천 근거를 여러 측면에서 제시
  - 내용 유사도
  - 저자 겹침
  - 인용 관계
  - 태그 유사성

### 5. 사용자 피드백 수집 없음
**문제:**
- 추천이 유용한지 피드백 수집 안 함
- 추천 알고리즘 개선 불가능

**필요 기능:**
- 추천 항목에 👍/👎 버튼
- 피드백 DB 저장
- 피드백 기반 재학습

### 6. 다양한 추천 소스 부족
**현재:** Crossref만 지원

**개선 방향:**
- arXiv (프리프린트)
- PubMed (생명과학)
- IEEE Xplore (공학)
- Google Scholar (통합)
- Semantic Scholar (AI 강화)

### 7. 협업 필터링 없음
**현재:** Content-based만 (사용자 문서 기반)

**개선:** Hybrid 추천
- 비슷한 연구자가 읽은 논문
- 자주 함께 인용되는 논문
- 같은 주제 클러스터

## 🎯 우선순위 개선 사항

### Phase 1: 즉시 구현 가능 (1-2시간)

#### A. arXiv API 완성
```python
# core/recommendation/journal_fetcher.py

def fetch_recent_articles(self, category, max_results=50):
    response = requests.get(self.api_url, params=params, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    namespace = {'atom': 'http://www.w3.org/2005/Atom',
                 'arxiv': 'http://arxiv.org/schemas/atom'}

    articles = []
    for entry in root.findall('atom:entry', namespace):
        article = {
            'title': entry.find('atom:title', namespace).text.strip(),
            'abstract': entry.find('atom:summary', namespace).text.strip(),
            'authors': [author.find('atom:name', namespace).text
                       for author in entry.findall('atom:author', namespace)],
            'year': int(entry.find('atom:published', namespace).text[:4]),
            'doi': entry.find('atom:id', namespace).text,
            'journal': 'arXiv'
        }
        articles.append(article)

    return articles
```

#### B. 추천 캐싱 구현
```python
# core/recommendation/engine.py

def _get_cached_recommendations(self, journal_name, max_age_hours=24):
    db = self.workspace.get_database()
    cursor = db.connect().cursor()

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

    rows = cursor.execute("""
        SELECT * FROM recommendation_cache
        WHERE journal_name = ? AND fetched_at > ?
        ORDER BY similarity_score DESC
    """, (journal_name, cutoff_time.isoformat())).fetchall()

    return [dict(row) for row in rows]

def _save_to_cache(self, journal_name, recommendations):
    db = self.workspace.get_database()

    with db.transaction() as conn:
        cursor = conn.cursor()

        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendation_cache
                (journal_name, article_title, article_abstract, article_authors,
                 article_year, article_doi, similarity_score, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (journal_name, rec.article_title, rec.article_abstract,
                  str(rec.article_authors), rec.article_year, rec.article_doi,
                  rec.similarity_score, rec.reason))
```

#### C. 저널 즐겨찾기 매니저
```python
# core/favorite_journal_manager.py (신규 생성)

class FavoriteJournalManager:
    def __init__(self, workspace):
        self.workspace = workspace

    def add_favorite(self, journal_name, issn=None, update_frequency='weekly'):
        db = self.workspace.get_database()
        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO favorite_journals
                (journal_name, issn, update_frequency, is_active)
                VALUES (?, ?, ?, 1)
            """, (journal_name, issn, update_frequency))

        return cursor.lastrowid

    def get_all_favorites(self):
        db = self.workspace.get_database()
        cursor = db.connect().cursor()
        rows = cursor.execute("""
            SELECT * FROM favorite_journals WHERE is_active = 1
            ORDER BY journal_name
        """).fetchall()
        return [dict(row) for row in rows]

    def update_last_fetched(self, journal_id):
        db = self.workspace.get_database()
        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE favorite_journals
                SET last_fetched = CURRENT_TIMESTAMP
                WHERE journal_id = ?
            """, (journal_id,))

    def scan_all_favorites(self, recommendation_engine):
        """모든 즐겨찾기 저널에서 추천 생성"""
        favorites = self.get_all_favorites()
        all_recommendations = []

        for journal in favorites:
            logger.info(f"Scanning journal: {journal['journal_name']}")

            recommendations = recommendation_engine.generate_recommendations(
                journal['journal_name'],
                days_back=30
            )

            all_recommendations.extend(recommendations)
            self.update_last_fetched(journal['journal_id'])

        return all_recommendations
```

### Phase 2: UI 개선 (1-2시간)

#### D. 추천 다이얼로그 개선
- 즐겨찾기 저널 목록 추가
- 여러 소스 선택 (Crossref, arXiv)
- 추천 결과에 피드백 버튼
- 논문 상세 미리보기

#### E. 추천 설명 개선
```python
def _explain_recommendation(self, article, score):
    explanation = []

    # 유사도 점수
    if score > 0.7:
        explanation.append("⭐⭐⭐ 매우 높은 관련성")
    elif score > 0.5:
        explanation.append("⭐⭐ 높은 관련성")
    else:
        explanation.append("⭐ 중간 관련성")

    # 공통 키워드
    keywords = self.vectorizer.get_common_keywords(article_text, top_k=3)
    if keywords:
        explanation.append(f"공통 키워드: {', '.join(keywords)}")

    # 유사 문서
    similar_doc = self._find_most_similar_user_doc(article)
    if similar_doc:
        explanation.append(f"'{similar_doc[:40]}...'와(과) 유사")

    # 저자 겹침
    common_authors = self._find_common_authors(article)
    if common_authors:
        explanation.append(f"공통 저자: {', '.join(common_authors)}")

    return ' | '.join(explanation), keywords
```

### Phase 3: 고급 기능 (3-5시간)

#### F. 다중 소스 통합
- PubMed, Semantic Scholar API 추가
- 소스별 가중치 조정
- 중복 제거 (DOI 기반)

#### G. 협업 필터링
- 유사 사용자 찾기 (태그, 저자 기반)
- 함께 인용되는 논문 추천
- 논문 클러스터링 (topic modeling)

#### H. 사용자 피드백 학습
- 피드백 DB 설계
- 추천 스코어에 피드백 반영
- A/B 테스트 프레임워크

## 📊 성능 최적화

### 1. 캐싱 전략
- 추천 결과 캐싱 (24시간)
- 벡터화 결과 캐싱
- API 응답 캐싱

### 2. 병렬 처리
- 여러 저널 동시 스캔
- 벡터화 병렬 처리

### 3. 인덱싱
- 추천 캐시에 인덱스 추가
```sql
CREATE INDEX IF NOT EXISTS idx_cache_journal_date
ON recommendation_cache(journal_name, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_cache_score
ON recommendation_cache(similarity_score DESC);
```

## 🧪 테스트 계획

### 단위 테스트
- Vectorizer 정확도
- API 파싱 로직
- 캐싱 동작

### 통합 테스트
- 전체 추천 파이프라인
- 여러 소스 통합
- UI 워크플로우

### 성능 테스트
- 100+ 문서 코퍼스
- 1000+ 추천 후보
- API rate limit 처리

## 🎨 UX 개선

### 추천 카드 디자인
```
┌─────────────────────────────────────────────────────┐
│ ⭐⭐⭐ 높은 관련성 (92% 유사도)                      │
│                                                     │
│ 📄 Title: Deep Learning for Energy Prediction      │
│ ✍️ Authors: John Doe, Jane Smith                   │
│ 📅 2024 | 📚 Energy & Environmental Science         │
│                                                     │
│ 🔑 Keywords: machine learning, energy, prediction  │
│ 💡 이유: 'ML for Buildings'와(과) 유사            │
│                                                     │
│ [👍 Useful]  [👎 Not Useful]  [📥 Download]  [🔗 DOI] │
└─────────────────────────────────────────────────────┘
```

### 필터링/정렬
- 유사도 점수로 정렬
- 연도 필터
- 저널 필터
- 키워드 필터

## 📝 구현 체크리스트

### Immediate (완료 목표)
- [ ] arXiv XML 파싱 구현
- [ ] 추천 캐싱 구현
- [ ] FavoriteJournalManager 클래스 생성
- [ ] 추천 설명 개선

### Short-term (1주)
- [ ] 즐겨찾기 UI 추가
- [ ] 피드백 버튼 추가
- [ ] 추천 다이얼로그 개선
- [ ] 성능 테스트

### Long-term (1달)
- [ ] PubMed, Semantic Scholar 통합
- [ ] 협업 필터링
- [ ] 피드백 기반 학습
- [ ] 자동 추천 알림

## 🔗 참고 자료

- [Crossref API 문서](https://api.crossref.org/)
- [arXiv API 문서](http://arxiv.org/help/api/)
- [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [Semantic Scholar API](https://api.semanticscholar.org/)
- [scikit-learn TF-IDF](https://scikit-learn.org/stable/modules/feature_extraction.html#tfidf-term-weighting)
