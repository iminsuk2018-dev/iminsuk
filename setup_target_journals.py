"""
Setup Target Journals and Keywords for Recommendation System
Configures journals and keywords for carbon capture, energy, and process optimization research
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.workspace import Workspace
from config import DEFAULT_WORKSPACE_DIR

# Initialize workspace
workspace = Workspace(DEFAULT_WORKSPACE_DIR)
workspace.initialize()

db = workspace.get_database()
conn = db.connect()
cursor = conn.cursor()

# Add keywords column to favorite_journals if it doesn't exist
try:
    cursor.execute("ALTER TABLE favorite_journals ADD COLUMN keywords TEXT")
    print("✓ Added 'keywords' column to favorite_journals table")
    conn.commit()
except Exception as e:
    # Column already exists or other error
    pass

# Keywords for carbon capture, energy systems, and process optimization
keywords = [
    "Direct Air Capture", "Calcium looping", "CO₂ capture", "Carbon neutrality",
    "Carbon capture and storage", "Techno-economic analysis", "Process modeling",
    "Process simulation", "Process optimization", "System integration",
    "Renewable energy", "Energy system optimization", "AI-based optimization",
    "Data-driven modeling", "AI based modeling", "Hydrogen", "Ammonia",
    "Aspen", "CO2", "NOx", "Power plant", "LCA"
]

keywords_str = ", ".join(keywords)

# Target journals with ISSN
journals = [
    {
        "name": "Energy Conversion and Management",
        "issn": "0196-8904",
        "publisher": "Elsevier",
        "description": "Energy conversion, management, and environmental aspects"
    },
    {
        "name": "Applied Energy",
        "issn": "0306-2619",
        "publisher": "Elsevier",
        "description": "Applied energy research and innovation"
    },
    {
        "name": "Chemical Engineering Journal",
        "issn": "1385-8947",
        "publisher": "Elsevier",
        "description": "Chemical engineering and environmental technology"
    },
    {
        "name": "Joule",
        "issn": "2542-4351",
        "publisher": "Cell Press",
        "description": "Sustainable energy research and innovation"
    },
    {
        "name": "Nature Energy",
        "issn": "2058-7546",
        "publisher": "Nature Publishing Group",
        "description": "Energy science and technology"
    },
    {
        "name": "Nature Climate Change",
        "issn": "1758-678X",
        "publisher": "Nature Publishing Group",
        "description": "Climate change science and impacts"
    },
    {
        "name": "Nature Sustainability",
        "issn": "2398-9629",
        "publisher": "Nature Publishing Group",
        "description": "Sustainability science and solutions"
    },
    {
        "name": "Energy & Environmental Science",
        "issn": "1754-5692",
        "publisher": "Royal Society of Chemistry",
        "description": "Energy and environmental research"
    },
]

print("=" * 60)
print("Setting up Target Journals for Recommendation System")
print("=" * 60)
print()

# Clear existing journals (optional - comment out if you want to keep existing)
# cursor.execute("DELETE FROM target_journals")
# print("✓ Cleared existing journals")

# Insert journals
inserted = 0
skipped = 0

for journal in journals:
    # Check if already exists
    cursor.execute("""
        SELECT journal_id FROM favorite_journals WHERE journal_name = ?
    """, (journal['name'],))

    existing = cursor.fetchone()

    if existing:
        print(f"[SKIP] Already exists: {journal['name']}")
        skipped += 1
    else:
        cursor.execute("""
            INSERT INTO favorite_journals (journal_name, issn, keywords, update_frequency, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (journal['name'], journal['issn'], keywords_str, 'weekly', 1))

        print(f"[OK] Added: {journal['name']}")
        print(f"     ISSN: {journal['issn']}")
        print(f"     Publisher: {journal['publisher']}")
        print()
        inserted += 1

conn.commit()

print()
print("=" * 60)
print(f"Summary:")
print(f"  [OK] Inserted: {inserted} journals")
print(f"  [SKIP] Skipped: {skipped} journals")
print(f"  [INFO] Total keywords: {len(keywords)}")
print("=" * 60)
print()

# Show keywords
print("Keywords configured:")
print("-" * 60)
for i, kw in enumerate(keywords, 1):
    print(f"{i:2d}. {kw}")

print()
print("=" * 60)
print("Setup complete!")
print()
print("Next steps:")
print("1. Run web server: python start_web_server.py")
print("2. Click 'Refresh' button to fetch papers")
print("3. Or run: python fetch_recommendations.py")
print("=" * 60)

conn.close()
