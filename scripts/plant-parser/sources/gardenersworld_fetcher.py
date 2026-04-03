"""
GardenersWorld.com (BBC) parser — pests, diseases, care guides.
Source: https://www.gardenersworld.com/how-to/grow-plants/
Rich care content with structured pests & diseases sections.
Polite scraping: 2 sec delay.
"""
import json
import re
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

from turso_sync import turso_query, turso_batch

BASE_URL = 'https://www.gardenersworld.com'
DELAY = 2.0  # Polite: 2 seconds

# Known pest and disease keywords for classification
_PEST_WORDS = ['aphid', 'beetle', 'mite', 'bug', 'caterpillar', 'fly', 'whitefl', 'thrip',
               'scale', 'mealybug', 'weevil', 'borer', 'worm', 'slug', 'snail', 'gnat',
               'moth', 'sawfly', 'leafhopper', 'psyllid', 'nematode', 'earwig', 'ant']
_DISEASE_WORDS = ['rot', 'wilt', 'blight', 'mildew', 'spot', 'rust', 'canker', 'scab',
                  'virus', 'fungal', 'bacterial', 'mold', 'mould', 'damping', 'mosaic',
                  'botrytis', 'fusarium', 'anthracnose', 'chlorosis']


def fetch_page(url):
    """Fetch HTML page with browser-like headers."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def parse_pests_diseases(html):
    """Extract pests and diseases from GardenersWorld page."""
    # Find pests section — GardenersWorld uses different headings:
    # "Pests and diseases", "problem solving", "Pests", "Problems"
    m = re.search(r'(?:[Pp]ests and diseases|[Pp]roblem solving|[Pp]ests|[Pp]roblems)</h[23]>\s*(.*?)(?:<h[23]|</article|</section)', html, re.DOTALL)
    if not m:
        return [], []

    text = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
    text = re.sub(r'\s+', ' ', text)

    if not text or len(text) < 10:
        return [], []

    # Split into sentences and classify
    sentences = [s.strip() for s in re.split(r'[.!]', text) if s.strip() and len(s.strip()) > 5]

    pests = []
    diseases = []
    for s in sentences:
        sl = s.lower()
        is_pest = any(p in sl for p in _PEST_WORDS)
        is_disease = any(d in sl for d in _DISEASE_WORDS)
        if is_pest:
            pests.append(s.strip())
        if is_disease:
            diseases.append(s.strip())
        if not is_pest and not is_disease and len(s) > 20:
            diseases.append(s.strip())  # default to problems

    return pests, diseases


def enrich_from_gardenersworld(limit=100):
    """Fetch GardenersWorld data for plants in our DB."""
    # Get plants that need pests/diseases data
    rows = turso_query('''
        SELECT p.plant_id, p.scientific, cn.name as common_name
        FROM plants p
        LEFT JOIN care c ON p.plant_id = c.plant_id
        LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.is_primary = 1
        WHERE (c.common_pests IS NULL OR c.common_pests = '' OR c.common_pests = '[]')
          AND p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN p.sources LIKE ? THEN 0 ELSE 1 END,
            p.scientific
        LIMIT ?
    ''', ['%perenual%', limit])

    print(f"[GardenersWorld] Checking {len(rows)} plants for pests/diseases...")
    enriched = 0
    not_found = 0

    for i, row in enumerate(rows):
        scientific = row['scientific']
        pid = row['plant_id']

        # Get common name from DB
        cn_rows = turso_query(
            "SELECT name FROM common_names WHERE plant_id = ? AND is_primary = 1 LIMIT 1",
            [pid]
        )
        common = cn_rows[0]['name'] if cn_rows else ''
        if not common:
            common = scientific.split()[-1]  # species epithet

        common_slug = common.lower().replace(' ', '-').replace("'", '').replace('"', '')
        url = f'{BASE_URL}/how-to/grow-plants/how-to-grow-{common_slug}/'

        try:
            html = fetch_page(url)
            time.sleep(DELAY)

            if len(html) < 5000:
                not_found += 1
                continue

            pests, diseases = parse_pests_diseases(html)

            if not pests and not diseases:
                not_found += 1
                continue

            statements = []
            if pests:
                statements.append((
                    "UPDATE care SET common_pests = CASE WHEN common_pests IS NULL OR common_pests = '' OR common_pests = '[]' THEN ? ELSE common_pests END WHERE plant_id = ?",
                    [json.dumps(pests[:5]), pid]
                ))
            if diseases:
                statements.append((
                    "UPDATE care SET common_problems = CASE WHEN common_problems IS NULL OR common_problems = '' OR common_problems = '[]' THEN ? ELSE common_problems END WHERE plant_id = ?",
                    [json.dumps(diseases[:5]), pid]
                ))

            if statements:
                turso_batch(statements)
                enriched += 1
                if enriched <= 5:
                    print(f"  + {scientific}: pests={len(pests)}, diseases={len(diseases)}")

            if (i + 1) % 20 == 0:
                print(f"[GardenersWorld] Progress: {i+1}/{len(rows)}, enriched: {enriched}")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                not_found += 1
            else:
                if enriched + not_found < 5:
                    print(f"  ! HTTP {e.code} for {slug}")
        except Exception as e:
            not_found += 1
            continue

    print(f"[GardenersWorld] Done: {enriched} enriched, {not_found} not found")
    return enriched


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    enrich_from_gardenersworld(limit)
