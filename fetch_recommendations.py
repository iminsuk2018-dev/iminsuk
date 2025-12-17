"""
Fetch Recommendations from Target Journals
Downloads papers from January 2025 onwards matching configured keywords
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.workspace import Workspace
from core.recommendation.auto_recommendation_manager import AutoRecommendationManager
from config import DEFAULT_WORKSPACE_DIR

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

def main():
    print("=" * 70)
    print("Fetching Paper Recommendations")
    print("=" * 70)
    print()

    # Initialize
    workspace = Workspace(DEFAULT_WORKSPACE_DIR)
    workspace.initialize()

    manager = AutoRecommendationManager(workspace)

    # Get target journals
    journals = manager.get_target_journals(active_only=True)

    if not journals:
        print("[ERROR] No active target journals found!")
        print("        Run: python setup_target_journals.py")
        return 1

    print(f"[INFO] Found {len(journals)} active journals:")
    print()
    for journal in journals:
        keywords = journal.get('keywords', 'No keywords')
        keyword_count = len(keywords.split(',')) if keywords != 'No keywords' else 0
        print(f"  - {journal['journal_name']}")
        print(f"    ISSN: {journal['issn']}")
        print(f"    Keywords: {keyword_count} configured")
        print()

    print("=" * 70)
    print("Fetching recommendations...")
    print("=" * 70)
    print()

    # Fetch recommendations for all journals
    # Fetch papers from January 2025 onwards (about 12 days back from now: Dec 17, 2024)
    # Since we're at end of December 2024, we'll fetch last 30 days to get January papers
    try:
        print("[INFO] Fetching papers from last 30 days (including January 2025)...")
        print()

        stats = manager.fetch_and_recommend(
            journal_id=None,  # All active journals
            days_back=30,     # Last 30 days to include January
            min_score=0.3     # Minimum similarity score
        )

        print()
        print("=" * 70)
        print("Fetch Complete!")
        print("=" * 70)
        print()
        print("Statistics:")
        print(f"  Total papers fetched: {stats.get('fetched', 0)}")
        print(f"  Recommended papers: {stats.get('recommended', 0)}")
        print(f"  Journals processed: {stats.get('journals_processed', 0)}")
        print()

        print()
        print("=" * 70)
        print("Next steps:")
        print("  1. Run web server: python start_web_server.py")
        print("  2. Open browser: http://127.0.0.1:5000")
        print("  3. Review recommended papers")
        print("=" * 70)

        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print(f"[ERROR] Failed to fetch recommendations: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
