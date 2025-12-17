"""
Auto Recommendation Manager
Automatically monitors target journals and recommends relevant papers
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from core.recommendation.vectorizer import DocumentVectorizer
from core.recommendation.journal_fetcher import JournalFetcher
from core.recommendation.keyword_synonyms import match_keywords_in_text, expand_keywords, should_exclude_paper

logger = logging.getLogger(__name__)


class AutoRecommendationManager:
    """Manages automatic paper recommendations from target journals"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.db = workspace.get_database()
        self.vectorizer = DocumentVectorizer()
        self.journal_fetcher = JournalFetcher()
        self._user_corpus = None

    def add_target_journal(
        self,
        journal_name: str,
        issn: Optional[str] = None,
        update_frequency: str = 'weekly'
    ) -> int:
        """
        Add a journal to target list

        Args:
            journal_name: Name of the journal
            issn: ISSN if known
            update_frequency: 'daily', 'weekly', 'monthly'

        Returns:
            journal_id
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO favorite_journals (journal_name, issn, update_frequency, is_active)
                VALUES (?, ?, ?, 1)
            """, (journal_name, issn, update_frequency))

            journal_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added target journal: {journal_name} (ID: {journal_id})")
            return journal_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add target journal: {e}")
            raise

    def get_target_journals(self, active_only: bool = True) -> List[Dict]:
        """Get list of target journals"""
        conn = self.db.connect()
        cursor = conn.cursor()

        query = "SELECT * FROM favorite_journals"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY journal_name"

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]

        journals = []
        for row in cursor.fetchall():
            journals.append(dict(zip(columns, row)))

        return journals

    def remove_target_journal(self, journal_id: int):
        """Remove a journal from target list"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM favorite_journals WHERE journal_id = ?", (journal_id,))
        conn.commit()

        logger.info(f"Removed target journal: {journal_id}")

    def toggle_journal(self, journal_id: int, is_active: bool):
        """Activate or deactivate a journal"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE favorite_journals SET is_active = ? WHERE journal_id = ?",
            (1 if is_active else 0, journal_id)
        )
        conn.commit()

        logger.info(f"Journal {journal_id} set to {'active' if is_active else 'inactive'}")

    def fetch_and_recommend(
        self,
        journal_id: Optional[int] = None,
        days_back: int = 7,
        min_score: float = 0.3
    ) -> Dict:
        """
        Fetch new papers and generate recommendations

        Args:
            journal_id: Specific journal ID, or None for all active
            days_back: How many days back to fetch
            min_score: Minimum similarity score

        Returns:
            Statistics dict
        """
        # Build user profile if available (optional for keyword-based recommendations)
        if self._user_corpus is None:
            self._user_corpus = self._get_user_corpus()

        if self._user_corpus:
            try:
                self.vectorizer.build_user_profile(self._user_corpus)
                logger.info("Using user profile for similarity calculation")
            except Exception as e:
                logger.warning(f"Failed to build user profile: {e}. Using keyword-only matching.")
                self._user_corpus = None
        else:
            logger.info("No user documents found. Using keyword-only recommendations.")

        # Get target journals
        if journal_id:
            journals = [j for j in self.get_target_journals() if j['journal_id'] == journal_id]
        else:
            journals = self.get_target_journals(active_only=True)

        if not journals:
            logger.warning("No active target journals")
            return {'fetched': 0, 'recommended': 0, 'error': 'No target journals'}

        total_fetched = 0
        total_recommended = 0

        conn = self.db.connect()
        cursor = conn.cursor()

        # Process each journal
        for journal in journals:
            journal_id = journal['journal_id']
            journal_name = journal['journal_name']
            issn = journal.get('issn')

            logger.info(f"Processing journal: {journal_name} (ISSN: {issn})")

            # Fetch recent articles
            try:
                articles = self.journal_fetcher.fetch_recent_articles(journal_name, issn=issn, days_back=days_back)
                total_fetched += len(articles)

                if not articles:
                    logger.info(f"No articles found for {journal_name}")
                    continue

                # Get keywords for this journal
                journal_keywords = journal.get('keywords', '')
                keywords_list = [kw.strip() for kw in journal_keywords.split(',') if kw.strip()]

                # Filter articles by keywords (including synonyms) and exclusion keywords
                relevant_articles = []
                excluded_count = 0
                for idx, article in enumerate(articles):
                    article_text = f"{article.get('title', '')} {article.get('abstract', '')}"

                    # First, check exclusion keywords (catalyst, metal-related)
                    should_exclude, exclusion_matches = should_exclude_paper(article_text)
                    if should_exclude:
                        excluded_count += 1
                        logger.debug(f"Excluded paper '{article.get('title', '')[:50]}...' due to: {exclusion_matches[:3]}")
                        continue

                    # Use synonym matching for inclusion keywords
                    match_result = match_keywords_in_text(article_text, keywords_list)

                    if match_result['match_count'] > 0:
                        # Store matched info with article
                        article['_match_info'] = match_result
                        relevant_articles.append((idx, article))

                logger.info(f"Found {len(relevant_articles)} articles matching keywords (with synonyms) out of {len(articles)}")
                logger.info(f"Excluded {excluded_count} articles due to catalyst/metal keywords")

                # For keyword-matched articles, use keyword match score
                # If user corpus exists, we can optionally enhance with TF-IDF, but keyword match is primary
                similarities = []
                for idx, article in relevant_articles:
                    # Use keyword match count as the base score
                    match_info = article.get('_match_info', {})
                    keyword_match_count = match_info.get('match_count', 0)

                    # Score based on number of keyword matches (normalized to 0-1 range)
                    # More matched keywords = higher score
                    keyword_score = min(1.0, 0.5 + (keyword_match_count * 0.1))

                    similarities.append((idx, keyword_score))

                # Save recommendations
                for idx, score in similarities:
                    # Very low threshold since keywords already filtered
                    # Articles that match keywords should be recommended
                    if score < 0.3:  # Minimal threshold for keyword matches
                        continue

                    article = articles[idx]

                    # Check if already exists
                    cursor.execute("""
                        SELECT cache_id FROM recommendation_cache
                        WHERE article_doi = ? AND journal_id = ?
                    """, (article.get('doi', ''), journal_id))

                    if cursor.fetchone():
                        continue  # Already recommended

                    # Determine category
                    category = self._categorize_recommendation(score)

                    # Get matched keywords from article
                    match_info = article.get('_match_info', {})
                    matched_terms = match_info.get('matched_terms', [])

                    # Format: "keyword (via synonym)"
                    keywords_str = ', '.join([f"{orig} (via {syn})" if orig.lower() != syn else orig
                                               for orig, syn in matched_terms[:5]])

                    # Generate reason with matched keywords
                    reason = self._generate_reason_with_keywords(score, matched_terms)

                    # Insert recommendation
                    cursor.execute("""
                        INSERT INTO recommendation_cache (
                            journal_id, article_title, article_abstract, article_authors,
                            article_year, article_doi, similarity_score, reason,
                            category, common_keywords, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unread')
                    """, (
                        journal_id,
                        article.get('title', 'Untitled'),
                        article.get('abstract', ''),
                        str(article.get('authors', [])),
                        article.get('year'),
                        article.get('doi', ''),
                        score,
                        reason,
                        category,
                        keywords_str
                    ))

                    total_recommended += 1

                # Update last_fetched
                cursor.execute("""
                    UPDATE favorite_journals
                    SET last_fetched = CURRENT_TIMESTAMP
                    WHERE journal_id = ?
                """, (journal_id,))

                conn.commit()

                logger.info(f"Recommended {total_recommended} papers from {journal_name}")

            except Exception as e:
                logger.error(f"Error processing {journal_name}: {e}", exc_info=True)
                continue

        return {
            'fetched': total_fetched,
            'recommended': total_recommended,
            'journals_processed': len(journals)
        }

    def get_recommendations(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recommendations with optional filters

        Args:
            status: 'unread', 'confirmed', 'dismissed', or None for all
            category: 'highly_relevant', 'relevant', 'moderately_relevant', or None
            limit: Maximum number of results

        Returns:
            List of recommendation dicts
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        query = """
            SELECT rc.*, fj.journal_name
            FROM recommendation_cache rc
            JOIN favorite_journals fj ON rc.journal_id = fj.journal_id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND rc.status = ?"
            params.append(status)

        if category:
            query += " AND rc.category = ?"
            params.append(category)

        query += " ORDER BY rc.similarity_score DESC, rc.fetched_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]

        recommendations = []
        for row in cursor.fetchall():
            rec = dict(zip(columns, row))
            # Parse keywords
            if rec.get('common_keywords'):
                rec['keywords_list'] = rec['common_keywords'].split(',')
            else:
                rec['keywords_list'] = []
            recommendations.append(rec)

        return recommendations

    def update_recommendation_status(
        self,
        cache_id: int,
        status: str
    ):
        """
        Update recommendation status

        Args:
            cache_id: Recommendation cache ID
            status: 'unread', 'confirmed', 'dismissed'
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE recommendation_cache
            SET status = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE cache_id = ?
        """, (status, cache_id))

        conn.commit()
        logger.info(f"Updated recommendation {cache_id} to {status}")

    def delete_recommendation(self, cache_id: int):
        """Permanently delete a recommendation"""
        conn = self.db.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM recommendation_cache WHERE cache_id = ?", (cache_id,))
        conn.commit()

        logger.info(f"Deleted recommendation: {cache_id}")

    def get_statistics(self) -> Dict:
        """Get recommendation statistics"""
        conn = self.db.connect()
        cursor = conn.cursor()

        stats = {}

        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM recommendation_cache
            GROUP BY status
        """)
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Count by category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM recommendation_cache
            WHERE status = 'unread'
            GROUP BY category
        """)
        stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Total count
        cursor.execute("SELECT COUNT(*) FROM recommendation_cache")
        stats['total'] = cursor.fetchone()[0]

        # Unread count
        cursor.execute("SELECT COUNT(*) FROM recommendation_cache WHERE status = 'unread'")
        stats['unread'] = cursor.fetchone()[0]

        return stats

    def _get_user_corpus(self) -> List[Dict]:
        """Get user's document corpus for profile building"""
        from core.document_manager import DocumentManager
        doc_manager = DocumentManager(self.workspace)
        return doc_manager.get_user_corpus()

    def _categorize_recommendation(self, score: float) -> str:
        """Categorize recommendation by score"""
        if score >= 0.7:
            return 'highly_relevant'
        elif score >= 0.5:
            return 'relevant'
        else:
            return 'moderately_relevant'

    def _generate_reason_with_keywords(self, score: float, matched_terms: List[tuple]) -> str:
        """Generate recommendation reason with matched keywords"""
        if not matched_terms:
            return f"Similarity score: {score:.2f}"

        # Extract unique keywords
        unique_keywords = list(set([orig for orig, _ in matched_terms[:3]]))

        reason_parts = []
        reason_parts.append(f"Matches {len(matched_terms)} keywords")
        reason_parts.append(f"Key topics: {', '.join(unique_keywords)}")

        if score > 0.3:
            reason_parts.append(f"High relevance (score: {score:.2f})")

        return " | ".join(reason_parts)

    def _generate_reason(self, score: float, keywords: List[str]) -> str:
        """Generate human-readable reason for recommendation"""
        if score >= 0.7:
            relevance = "매우 높은 관련성"
        elif score >= 0.5:
            relevance = "높은 관련성"
        else:
            relevance = "중간 관련성"

        if keywords:
            keywords_str = ', '.join(keywords[:3])
            return f"{relevance} (유사도: {score:.2f}) - 공통 키워드: {keywords_str}"
        else:
            return f"{relevance} (유사도: {score:.2f})"

    def clear_old_recommendations(self, days: int = 90):
        """Delete old reviewed recommendations"""
        conn = self.db.connect()
        cursor = conn.cursor()

        threshold = datetime.now() - timedelta(days=days)

        cursor.execute("""
            DELETE FROM recommendation_cache
            WHERE status IN ('confirmed', 'dismissed')
            AND reviewed_at < ?
        """, (threshold.isoformat(),))

        deleted = cursor.rowcount
        conn.commit()

        logger.info(f"Deleted {deleted} old recommendations")
        return deleted
