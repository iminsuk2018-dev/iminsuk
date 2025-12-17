"""
Web-based Recommendation System - Flask Backend
Fetches papers from target journals based on keywords
"""
import logging
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.workspace import Workspace
from config import DEFAULT_WORKSPACE_DIR

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize workspace
workspace = Workspace(DEFAULT_WORKSPACE_DIR)
workspace.initialize()

# Get database connection
db = workspace.get_database()


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/journals')
def get_journals():
    """Get all target journals"""
    try:
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT journal_id, journal_name, issn, keywords, is_active
            FROM favorite_journals
            WHERE is_active = 1
            ORDER BY journal_name
        """)

        columns = [desc[0] for desc in cursor.description]
        journals = []

        for row in cursor.fetchall():
            journal = dict(zip(columns, row))
            journals.append(journal)

        return jsonify({
            'success': True,
            'journals': journals,
            'count': len(journals)
        })

    except Exception as e:
        logger.error(f"Failed to fetch journals: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/keywords')
def get_keywords():
    """Get all unique keywords from target journals"""
    try:
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT keywords
            FROM favorite_journals
            WHERE is_active = 1 AND keywords IS NOT NULL
        """)

        # Parse keywords from comma-separated strings
        all_keywords = set()
        for row in cursor.fetchall():
            if row[0]:
                keywords = [k.strip() for k in row[0].split(',')]
                all_keywords.update(keywords)

        return jsonify({
            'success': True,
            'keywords': sorted(list(all_keywords)),
            'count': len(all_keywords)
        })

    except Exception as e:
        logger.error(f"Failed to fetch keywords: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/papers')
def get_papers():
    """Get papers from recommendation cache with filtering"""
    try:
        # Get query parameters
        journal_id = request.args.get('journal_id', type=int)
        keyword = request.args.get('keyword', type=str)
        sort_by = request.args.get('sort', 'newest')  # newest or oldest
        limit = request.args.get('limit', 50, type=int)

        conn = db.connect()
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT
                rc.cache_id,
                rc.article_title,
                rc.article_abstract,
                rc.article_doi,
                rc.article_year,
                rc.similarity_score,
                rc.category,
                rc.status,
                rc.fetched_at as cached_at,
                tj.journal_name,
                tj.journal_id,
                rc.common_keywords as keywords_list
            FROM recommendation_cache rc
            JOIN favorite_journals tj ON rc.journal_id = tj.journal_id
            WHERE 1=1
        """
        params = []

        # Get offset for pagination
        offset = request.args.get('offset', 0, type=int)

        # Filter by journal
        if journal_id:
            query += " AND rc.journal_id = ?"
            params.append(journal_id)

        # Filter by keyword
        if keyword:
            query += " AND rc.common_keywords LIKE ?"
            params.append(f'%{keyword}%')

        # Sort - always newest first for timeline view
        query += " ORDER BY rc.fetched_at DESC"

        # Limit with pagination
        query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        papers = []

        for row in cursor.fetchall():
            paper = dict(zip(columns, row))
            papers.append(paper)

        # Get total count
        count_query = """
            SELECT COUNT(*) FROM recommendation_cache rc
            JOIN favorite_journals tj ON rc.journal_id = tj.journal_id
            WHERE 1=1
        """
        count_params = []
        if journal_id:
            count_query += " AND rc.journal_id = ?"
            count_params.append(journal_id)
        if keyword:
            count_query += " AND rc.common_keywords LIKE ?"
            count_params.append(f'%{keyword}%')

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]

        return jsonify({
            'success': True,
            'papers': papers,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(papers)) < total_count
            },
            'filters': {
                'journal_id': journal_id,
                'keyword': keyword,
                'sort': sort_by
            }
        })

    except Exception as e:
        logger.error(f"Failed to fetch papers: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/papers/<int:cache_id>/status', methods=['POST'])
def update_paper_status(cache_id):
    """Update paper status (confirmed/dismissed)"""
    try:
        data = request.get_json()
        status = data.get('status', 'unread')

        if status not in ['unread', 'confirmed', 'dismissed']:
            return jsonify({
                'success': False,
                'error': 'Invalid status'
            }), 400

        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE recommendation_cache
            SET status = ?
            WHERE cache_id = ?
        """, (status, cache_id))

        conn.commit()

        return jsonify({
            'success': True,
            'cache_id': cache_id,
            'status': status
        })

    except Exception as e:
        logger.error(f"Failed to update paper status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh_recommendations():
    """Trigger recommendation refresh"""
    try:
        from core.recommendation.auto_recommendation_manager import AutoRecommendationManager

        auto_rec_manager = AutoRecommendationManager(workspace)

        # Refresh all active journals
        stats = auto_rec_manager.fetch_and_recommend(
            journal_id=None,  # All active journals
            days_back=30,     # Last 30 days
            min_score=0.2     # Lowered threshold for keyword matching
        )

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Failed to refresh recommendations: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_statistics():
    """Get recommendation statistics"""
    try:
        conn = db.connect()
        cursor = conn.cursor()

        # Get total counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM recommendation_cache
            GROUP BY status
        """)

        stats = {
            'total': 0,
            'unread': 0,
            'confirmed': 0,
            'dismissed': 0
        }

        for row in cursor.fetchall():
            status, count = row
            stats[status] = count
            stats['total'] += count

        # Get counts by journal
        cursor.execute("""
            SELECT tj.journal_name, COUNT(*) as count
            FROM recommendation_cache rc
            JOIN favorite_journals tj ON rc.journal_id = tj.journal_id
            GROUP BY tj.journal_name
            ORDER BY count DESC
            LIMIT 10
        """)

        journals = []
        for row in cursor.fetchall():
            journals.append({
                'name': row[0],
                'count': row[1]
            })

        stats['by_journal'] = journals

        # Get last update time
        cursor.execute("""
            SELECT MAX(fetched_at) as last_update
            FROM recommendation_cache
        """)

        last_update_row = cursor.fetchone()
        stats['last_update'] = last_update_row[0] if last_update_row and last_update_row[0] else None

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Run Flask development server
    app.run(host='127.0.0.1', port=5000, debug=True)
