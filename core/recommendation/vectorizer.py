"""
TF-IDF 벡터화 및 유사도 계산
"""
import logging
import numpy as np
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import RECOMMENDATION_MAX_FEATURES

logger = logging.getLogger(__name__)


class DocumentVectorizer:
    """문서 벡터화 및 유사도 계산"""

    def __init__(self, max_features: int = RECOMMENDATION_MAX_FEATURES):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),  # unigram + bigram
            min_df=1,
            lowercase=True,
            sublinear_tf=True  # Use log(tf) + 1
        )
        self.user_vector = None
        self.user_text = None

    def build_user_profile(self, corpus: List[Dict]) -> np.ndarray:
        """
        사용자 문서 코퍼스로부터 프로필 벡터 생성

        Args:
            corpus: List of dicts with 'title', 'abstract', 'tags', 'annotations'

        Returns:
            User profile vector
        """
        if not corpus:
            logger.warning("Empty corpus provided")
            return np.array([])

        # Combine all text from user's documents
        combined_texts = []

        for doc in corpus:
            text_parts = []

            # Add title (weighted higher by repeating)
            if doc.get('title'):
                text_parts.extend([doc['title']] * 3)

            # Add abstract
            if doc.get('abstract'):
                text_parts.append(doc['abstract'])

            # Add tags (weighted)
            if doc.get('tags'):
                tags_text = ' '.join(doc['tags'])
                text_parts.extend([tags_text] * 2)

            # Add annotations
            if doc.get('annotations'):
                annotations_text = ' '.join(doc['annotations'])
                text_parts.append(annotations_text)

            combined_texts.append(' '.join(text_parts))

        # Combine all documents into one profile
        self.user_text = ' '.join(combined_texts)

        logger.info(f"Building user profile from {len(corpus)} documents")
        logger.debug(f"  Total text length: {len(self.user_text)} chars")

        # Fit vectorizer and transform
        try:
            # Fit on user text + dummy to avoid single-sample issue
            fit_texts = [self.user_text, "dummy document for fitting"]
            self.vectorizer.fit(fit_texts)

            # Transform only user text
            self.user_vector = self.vectorizer.transform([self.user_text])

            logger.info(f"User profile vector shape: {self.user_vector.shape}")
            logger.info(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")

            return self.user_vector

        except Exception as e:
            logger.error(f"Failed to build user profile: {e}")
            raise

    def compute_similarities(self, articles: List[Dict]) -> List[Tuple[int, float]]:
        """
        사용자 프로필과 논문들 간의 유사도 계산

        Args:
            articles: List of dicts with 'title', 'abstract'

        Returns:
            List of (index, similarity_score) tuples, sorted by score descending
        """
        if self.user_vector is None:
            raise ValueError("User profile not built yet. Call build_user_profile first.")

        if not articles:
            logger.warning("No articles to compare")
            return []

        # Prepare article texts
        article_texts = []
        for article in articles:
            text_parts = []

            if article.get('title'):
                text_parts.append(article['title'])

            if article.get('abstract'):
                text_parts.append(article['abstract'])

            article_texts.append(' '.join(text_parts))

        # Vectorize articles
        try:
            article_vectors = self.vectorizer.transform(article_texts)

            # Compute cosine similarities
            similarities = cosine_similarity(self.user_vector, article_vectors)[0]

            # Create (index, score) pairs and sort
            scored_articles = [(i, score) for i, score in enumerate(similarities)]
            scored_articles.sort(key=lambda x: x[1], reverse=True)

            logger.debug(f"Computed similarities for {len(articles)} articles")
            logger.debug(f"  Top score: {scored_articles[0][1]:.4f}")
            logger.debug(f"  Mean score: {np.mean(similarities):.4f}")

            return scored_articles

        except Exception as e:
            logger.error(f"Failed to compute similarities: {e}")
            raise

    def explain_similarity(self, article_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        유사도의 근거가 되는 상위 키워드 추출

        Args:
            article_text: 논문 텍스트
            top_k: 상위 몇 개 키워드

        Returns:
            List of (keyword, tfidf_score) tuples
        """
        if self.user_vector is None:
            return []

        try:
            # Vectorize article
            article_vector = self.vectorizer.transform([article_text])

            # Get feature names
            feature_names = self.vectorizer.get_feature_names_out()

            # Get article's TF-IDF scores
            article_scores = article_vector.toarray()[0]

            # Get top keywords for article
            top_indices = article_scores.argsort()[-top_k:][::-1]
            top_keywords = [(feature_names[i], article_scores[i]) for i in top_indices if article_scores[i] > 0]

            return top_keywords

        except Exception as e:
            logger.error(f"Failed to explain similarity: {e}")
            return []

    def get_common_keywords(self, article_text: str, top_k: int = 5) -> List[str]:
        """
        사용자 프로필과 논문 간 공통 키워드 추출

        Args:
            article_text: 논문 텍스트
            top_k: 상위 몇 개

        Returns:
            List of common keywords
        """
        if self.user_vector is None or not self.user_text:
            return []

        try:
            # Get article keywords
            article_keywords = self.explain_similarity(article_text, top_k * 2)
            article_keyword_set = {kw for kw, _ in article_keywords}

            # Get user profile keywords
            user_vector_dense = self.user_vector.toarray()[0]
            feature_names = self.vectorizer.get_feature_names_out()
            top_user_indices = user_vector_dense.argsort()[-top_k * 2:][::-1]
            user_keywords = {feature_names[i] for i in top_user_indices if user_vector_dense[i] > 0}

            # Find intersection
            common = list(article_keyword_set & user_keywords)[:top_k]

            return common

        except Exception as e:
            logger.error(f"Failed to get common keywords: {e}")
            return []

    def get_vocabulary_size(self) -> int:
        """Get vocabulary size"""
        if self.vectorizer.vocabulary_:
            return len(self.vectorizer.vocabulary_)
        return 0
