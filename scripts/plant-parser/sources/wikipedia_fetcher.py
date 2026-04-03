"""
Wikipedia REST API fetcher — descriptions and images for plants.
Free, unlimited. Polite rate: 0.1s between requests.
"""
import json
import time
import urllib.request
import urllib.parse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from config import WIKIPEDIA_DELAY
from turso_sync import turso_query, turso_batch

WIKI_REST = 'https://en.wikipedia.org/api/rest_v1'


def fetch_summary(scientific_name):
    """Fetch Wikipedia summary for a plant. Returns (description, image_url) or (None, None)."""
    title = scientific_name.replace(' ', '_')
    url = f'{WIKI_REST}/page/summary/{urllib.parse.quote(title)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0 (plantapp.pro)'}, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get('type') == 'disambiguation':
            return None, None
        description = data.get('extract', '')
        if len(description) > 500:
            cut = description[:500].rfind('.')
            if cut > 200:
                description = description[:cut + 1]
        image = data.get('originalimage', {}).get('source', '') or data.get('thumbnail', {}).get('source', '')
        return description, image
    except Exception:
        return None, None


def enrich_descriptions(limit=500):
    """Fetch Wikipedia descriptions for plants that don't have one.
    Tries scientific name first, then common name as fallback."""
    rows = turso_query('''
        SELECT p.plant_id, p.scientific, cn.name as common_name
        FROM plants p
        LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.is_primary = 1
        WHERE (p.description IS NULL OR p.description = '')
        LIMIT ?
    ''', [limit])
    if not rows:
        print("[Wikipedia] All plants have descriptions")
        return 0

    print(f"[Wikipedia] Enriching {len(rows)} plants with descriptions...")
    updated = 0
    statements = []

    for i, row in enumerate(rows):
        # Try scientific name first
        desc, img = fetch_summary(row['scientific'])
        time.sleep(WIKIPEDIA_DELAY)

        # Fallback: try common name
        if not desc and row.get('common_name'):
            desc, img = fetch_summary(row['common_name'])
            time.sleep(WIKIPEDIA_DELAY)

        if desc:
            statements.append((
                "UPDATE plants SET description = ? WHERE plant_id = ? AND (description IS NULL OR description = '')",
                [desc, row['plant_id']]
            ))
            # Also update image if plant has no image
            if img:
                statements.append((
                    "UPDATE plants SET image_url = ? WHERE plant_id = ? AND (image_url IS NULL OR image_url = '')",
                    [img, row['plant_id']]
                ))
            updated += 1

        # Batch execute every 25
        if len(statements) >= 25:
            turso_batch(statements)
            statements = []

        if (i + 1) % 50 == 0:
            print(f"[Wikipedia] Progress: {i+1}/{len(rows)} checked, {updated} updated")

    # Flush remaining
    if statements:
        turso_batch(statements)

    print(f"[Wikipedia] Done: {updated}/{len(rows)} plants enriched with descriptions")
    return updated


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    enrich_descriptions(limit)
