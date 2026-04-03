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


def parse_care_sections(html):
    """Extract care sections beyond just pests: propagation, pruning, soil, watering, fertilizer."""
    sections = {}

    # Pattern: heading followed by content until next heading
    # GardenersWorld uses h2/h3 for section titles
    headings_map = {
        'propagat': 'propagation',
        'prun': 'pruning',
        'soil': 'soil',
        'water': 'watering',
        'feed': 'fertilizer',
        'fertili': 'fertilizer',
        'plant': 'planting',
        'harvest': 'harvest',
    }

    # Find all h2/h3 sections
    for m in re.finditer(r'<h[23][^>]*>([^<]+)</h[23]>\s*(.*?)(?=<h[23]|</article|</section)', html, re.DOTALL):
        heading = m.group(1).strip().lower()
        content = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
        content = re.sub(r'\s+', ' ', content)

        if len(content) < 15:
            continue

        for keyword, section_name in headings_map.items():
            if keyword in heading:
                sections[section_name] = content[:500]
                break

    return sections


def enrich_from_gardenersworld(limit=100):
    """Fetch GardenersWorld data for plants in our DB."""
    rows = turso_query('''
        SELECT p.plant_id, p.scientific, cn.name as common_name
        FROM plants p
        LEFT JOIN care c ON p.plant_id = c.plant_id
        LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.is_primary = 1
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN c.common_pests IS NULL OR c.common_pests = '' OR c.common_pests = '[]' THEN 0 ELSE 1 END,
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
            care_sections = parse_care_sections(html)

            if not pests and not diseases and not care_sections:
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

            # New care sections
            if care_sections.get('propagation'):
                statements.append((
                    "UPDATE care SET propagation_detail = CASE WHEN propagation_detail IS NULL OR propagation_detail = '' THEN ? ELSE propagation_detail END WHERE plant_id = ?",
                    [care_sections['propagation'], pid]
                ))
            if care_sections.get('pruning'):
                statements.append((
                    "UPDATE care SET pruning_info = CASE WHEN pruning_info IS NULL OR pruning_info = '' THEN ? ELSE pruning_info END WHERE plant_id = ?",
                    [care_sections['pruning'], pid]
                ))
            if care_sections.get('soil'):
                statements.append((
                    "UPDATE care SET soil_types = CASE WHEN soil_types IS NULL OR soil_types = '' THEN ? ELSE soil_types END WHERE plant_id = ?",
                    [care_sections['soil'][:200], pid]
                ))
            if care_sections.get('watering'):
                statements.append((
                    "UPDATE care SET watering_method = CASE WHEN watering_method IS NULL OR watering_method = '' THEN ? ELSE watering_method END WHERE plant_id = ?",
                    [care_sections['watering'][:300], pid]
                ))
            if care_sections.get('fertilizer'):
                statements.append((
                    "UPDATE care SET fertilizer_type = CASE WHEN fertilizer_type IS NULL OR fertilizer_type = '' THEN ? ELSE fertilizer_type END WHERE plant_id = ?",
                    [care_sections['fertilizer'][:200], pid]
                ))
            if care_sections.get('harvest'):
                statements.append((
                    "UPDATE care SET harvest_info = CASE WHEN harvest_info IS NULL OR harvest_info = '' THEN ? ELSE harvest_info END WHERE plant_id = ?",
                    [care_sections['harvest'][:300], pid]
                ))

            if statements:
                turso_batch(statements)
                enriched += 1
                extras = list(care_sections.keys())
                if enriched <= 5:
                    print(f"  + {scientific}: pests={len(pests)}, diseases={len(diseases)}, sections={extras}")

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
