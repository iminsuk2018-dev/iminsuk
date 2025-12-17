"""
추천 엔진 메인 로직
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from core.recommendation.vectorizer import DocumentVectorizer
from core.recommendation.journal_fetcher import JournalFetcher
from config import RECOMMENDATION_TOP_K, RECOMMENDATION_MIN_SCORE

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """추천 결과 항목"""
    article_title: str
    article_abstract: str
    article_authors: List[str]
    article_year: Optional[int]
    article_doi: str
    journal_name: str
    similarity_score: float
    reason: str
    common_keywords: List[str]


class RecommendationEngine:
    """논문 추천 엔진"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.vectorizer = DocumentVectorizer()
        self.journal_fetcher = JournalFetcher()
        self._user_corpus = None

    def generate_recommendations(
        self,
        journal_name: str,
        days_back: int = 30,
        top_k: int = RECOMMENDATION_TOP_K
    ) -> List[Recommendation]:
        """
        저널의 최근 논문 중에서 추천 생성

        Args:
            journal_name: 저널 이름
            days_back: 최근 며칠 간의 논문
            top_k: 상위 몇 개 추천

        Returns:
            List of Recommendation objects
        """
        logger.info(f"Generating recommendations for journal: {journal_name}")

        # Step 1: Build user profile
        if self._user_corpus is None:
            self._user_corpus = self._get_user_corpus()

        if not self._user_corpus:
            logger.warning("No user documents found")
            return []

        logger.info(f"User corpus: {len(self._user_corpus)} documents")

        try:
            self.vectorizer.build_user_profile(self._user_corpus)
        except Exception as e:
            logger.error(f"Failed to build user profile: {e}")
            return []

        # Step 2: Fetch journal articles
        logger.info("Fetching journal articles...")
        articles = self.journal_fetcher.fetch_recent_articles(journal_name, days_back)

        if not articles:
            logger.warning("No articles fetched from journal")
            return []

        logger.info(f"Fetched {len(articles)} articles")

        # Step 3: Compute similarities
        logger.info("Computing similarities...")
        try:
            similarities = self.vectorizer.compute_similarities(articles)
        except Exception as e:
            logger.error(f"Failed to compute similarities: {e}")
            return []

        # Step 4: Generate recommendations
        recommendations = []

        for idx, score in similarities[:top_k]:
            if score < RECOMMENDATION_MIN_SCORE:
                logger.debug(f"Skipping article {idx} with score {score:.4f} (below threshold)")
                continue

            article = articles[idx]

            # Generate explanation
            reason, keywords = self._explain_recommendation(article, score)

            recommendation = Recommendation(
                article_title=article.get('title', 'Untitled'),
                article_abstract=article.get('abstract', ''),
                article_authors=article.get('authors', []),
                article_year=article.get('year'),
                article_doi=article.get('doi', ''),
                journal_name=article.get('journal', journal_name),
                similarity_score=score,
                reason=reason,
                common_keywords=keywords
            )

            recommendations.append(recommendation)

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations

    def _get_user_corpus(self) -> List[Dict]:
        """사용자 문서 코퍼스 가져오기"""
        from core.document_manager import DocumentManager

        doc_manager = DocumentManager(self.workspace)
        return doc_manager.get_user_corpus()

    def _explain_recommendation(self, article: Dict, score: float) -> tuple[str, List[str]]:
        """
        추천 이유 생성

        Args:
            article: 논문 dict
            score: 유사도 점수

        Returns:
            (reason_text, common_keywords)
        """
        # Get common keywords
        article_text = f"{article.get('title', '')} {article.get('abstract', '')}"
        common_keywords = self.vectorizer.get_common_keywords(article_text, top_k=5)

        # Build reason text
        if score > 0.7:
            relevance = "매우 높은"
        elif score > 0.5:
            relevance = "높은"
        elif score > 0.3:
            relevance = "중간"
        else:
            relevance = "낮은"

        if common_keywords:
            keywords_str = ', '.join(common_keywords[:3])
            reason = f"{relevance} 관련성 (유사도: {score:.2f}). 공통 키워드: {keywords_str}"
        else:
            reason = f"{relevance} 관련성 (유사도: {score:.2f})"

        # Find most similar user document
        similar_doc = self._find_most_similar_user_doc(article)
        if similar_doc:
            reason += f". '{similar_doc[:40]}...'와(과) 유사"

        return reason, common_keywords

    def _find_most_similar_user_doc(self, article: Dict) -> Optional[str]:
        """가장 유사한 사용자 문서 찾기"""
        if not self._user_corpus:
            return None

        # Simple heuristic: find doc with most keyword overlap
        article_text = f"{article.get('title', '')} {article.get('abstract', '')}".lower()
        article_words = set(article_text.split())

        best_match = None
        best_score = 0

        for doc in self._user_corpus:
            doc_text = f"{doc.get('title', '')} {doc.get('abstract', '')}".lower()
            doc_words = set(doc_text.split())

            overlap = len(article_words & doc_words)
            if overlap > best_score:
                best_score = overlap
                best_match = doc.get('title', '')

        return best_match

    def refresh_user_corpus(self):
        """사용자 코퍼스 새로고침"""
        self._user_corpus = None
        logger.info("User corpus cache cleared")

    def get_recommendation_stats(self) -> Dict:
        """추천 시스템 통계"""
        stats = {
            'user_documents': len(self._user_corpus) if self._user_corpus else 0,
            'vocabulary_size': self.vectorizer.get_vocabulary_size(),
            'vectorizer_ready': self.vectorizer.user_vector is not None
        }
        return stats
