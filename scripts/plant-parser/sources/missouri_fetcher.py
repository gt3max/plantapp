"""
Missouri Botanical Garden PlantFinder parser.
Source: https://www.missouribotanicalgarden.org/PlantFinder/
8,000+ plants with Culture, Problems, Garden Uses, care data.
Uses Playwright (headless browser) — ASP.NET requires JS rendering.
Polite: 3 sec delay between requests.
"""
import json
import re
import time
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

BASE_URL = 'https://www.missouribotanicalgarden.org/PlantFinder'
DELAY = 3.0  # Polite: 3 seconds (JS-rendered pages are heavy)

_PEST_WORDS = ['aphid', 'beetle', 'mite', 'bug', 'caterpillar', 'fly', 'whitefl', 'thrip',
               'scale', 'mealybug', 'weevil', 'borer', 'worm', 'slug', 'snail', 'gnat', 'moth']
_DISEASE_WORDS = ['rot', 'wilt', 'blight', 'mildew', 'spot', 'rust', 'canker', 'scab',
                  'virus', 'fungal', 'bacterial', 'mold', 'mould', 'damping', 'anthracnose']


def parse_profile_text(text):
    """Parse Missouri BG plant profile text into structured data."""
    data = {}
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Extract key-value pairs
    for i, line in enumerate(lines):
        for field in ['Common Name', 'Type', 'Family', 'Zone', 'Height', 'Spread',
                      'Bloom Time', 'Bloom Description', 'Sun', 'Water', 'Maintenance',
                      'Suggested Use', 'Tolerate']:
            if line.startswith(f'{field}:'):
                data[field.lower().replace(' ', '_')] = line[len(field)+1:].strip()
                break

    # Extract text sections
    for section in ['Culture', 'Noteworthy Characteristics', 'Problems']:
        idx = text.find(section)
        if idx >= 0:
            # Get text until next section or end
            remaining = text[idx + len(section):]
            # Find next section header
            next_section = len(remaining)
            for ns in ['Culture', 'Noteworthy', 'Problems', 'Garden Uses', 'Native Range']:
                ns_idx = remaining.find(ns)
                if ns_idx > 0 and ns_idx < next_section:
                    next_section = ns_idx
            section_text = remaining[:next_section].strip()
            if section_text:
                data[section.lower().replace(' ', '_')] = section_text[:500]

    return data


def enrich_from_missouri(plants_to_check, browser_page):
    """Search and enrich plants from Missouri BG."""
    enriched = 0

    for scientific, pid in plants_to_check:
        search_term = scientific.split()[0]  # Use genus for broader search

        try:
            url = f'{BASE_URL}/PlantFinderProfileResults.aspx?basic={search_term}'
            browser_page.goto(url, timeout=30000)
            browser_page.wait_for_timeout(3000)

            # Find matching link
            link = browser_page.query_selector(f'a:has-text("{scientific}")')
            if not link:
                # Try partial match
                links = browser_page.query_selector_all('a')
                for l in links:
                    text = l.inner_text().strip()
                    if scientific.lower() in text.lower():
                        link = l
                        break

            if not link:
                continue

            link.click()
            browser_page.wait_for_timeout(3000)

            body = browser_page.inner_text('body')
            data = parse_profile_text(body)

            if not data:
                continue

            statements = []

            # Sun → light_preferred
            if data.get('sun'):
                statements.append((
                    "UPDATE care SET light_preferred = CASE WHEN light_preferred IS NULL OR light_preferred = '' THEN ? ELSE light_preferred END WHERE plant_id = ?",
                    [data['sun'], pid]
                ))

            # Water → water_demand
            if data.get('water'):
                statements.append((
                    "UPDATE care SET water_demand = CASE WHEN water_demand IS NULL OR water_demand = '' THEN ? ELSE water_demand END WHERE plant_id = ?",
                    [data['water'], pid]
                ))

            # Maintenance → difficulty
            if data.get('maintenance'):
                statements.append((
                    "UPDATE care SET difficulty = CASE WHEN difficulty IS NULL OR difficulty = '' THEN ? ELSE difficulty END WHERE plant_id = ?",
                    [data['maintenance'], pid]
                ))

            # Height
            if data.get('height'):
                heights = re.findall(r'(\d+(?:\.\d+)?)', data['height'])
                if heights:
                    h_min = int(float(heights[0]) * 30.48)  # feet to cm
                    h_max = int(float(heights[-1]) * 30.48) if len(heights) > 1 else h_min
                    statements.append((
                        "UPDATE care SET height_min_cm = CASE WHEN height_min_cm = 0 THEN ? ELSE height_min_cm END, height_max_cm = CASE WHEN height_max_cm = 0 THEN ? ELSE height_max_cm END WHERE plant_id = ?",
                        [h_min, h_max, pid]
                    ))

            # Culture → watering_guide (care instructions)
            if data.get('culture'):
                statements.append((
                    "UPDATE care SET watering_guide = CASE WHEN watering_guide IS NULL OR watering_guide = '' THEN ? ELSE watering_guide END WHERE plant_id = ?",
                    [f"Missouri BG: {data['culture'][:300]}", pid]
                ))

            # Noteworthy → description supplement
            if data.get('noteworthy_characteristics'):
                statements.append((
                    "UPDATE plants SET description = CASE WHEN description IS NULL OR description = '' THEN ? ELSE description END WHERE plant_id = ?",
                    [data['noteworthy_characteristics'][:500], pid]
                ))

            # Problems → split into pests and diseases
            if data.get('problems'):
                text = data['problems']
                sentences = [s.strip() for s in re.split(r'[.!]', text) if s.strip()]
                pests = [s for s in sentences if any(p in s.lower() for p in _PEST_WORDS)]
                diseases = [s for s in sentences if any(d in s.lower() for d in _DISEASE_WORDS)]
                others = [s for s in sentences if s not in pests and s not in diseases and len(s) > 10]

                if pests:
                    statements.append((
                        "UPDATE care SET common_pests = CASE WHEN common_pests IS NULL OR common_pests = '' OR common_pests = '[]' THEN ? ELSE common_pests END WHERE plant_id = ?",
                        [json.dumps(pests[:5]), pid]
                    ))
                if diseases or others:
                    all_problems = diseases + others
                    statements.append((
                        "UPDATE care SET common_problems = CASE WHEN common_problems IS NULL OR common_problems = '' OR common_problems = '[]' THEN ? ELSE common_problems END WHERE plant_id = ?",
                        [json.dumps(all_problems[:5]), pid]
                    ))

            # Zone → temp ranges
            if data.get('zone'):
                zones = re.findall(r'(\d+)', data['zone'])
                if zones:
                    # USDA zone to approximate min temp
                    zone_to_temp = {1: -51, 2: -45, 3: -40, 4: -34, 5: -29, 6: -23, 7: -18, 8: -12, 9: -7, 10: -1, 11: 4, 12: 10, 13: 15}
                    min_zone = int(zones[0])
                    temp_min = zone_to_temp.get(min_zone, 0)
                    statements.append((
                        "UPDATE care SET temp_min_c = CASE WHEN temp_min_c = 0 THEN ? ELSE temp_min_c END WHERE plant_id = ?",
                        [temp_min, pid]
                    ))

            if statements:
                turso_batch(statements)
                enriched += 1
                print(f"  + {scientific}: {list(data.keys())}")

            time.sleep(DELAY)

        except Exception as e:
            print(f"  ! {scientific}: {e}")
            time.sleep(DELAY)
            continue

    return enriched


def run(limit=100):
    """Main entry point — get plants from DB and enrich from Missouri BG."""
    from playwright.sync_api import sync_playwright

    # Get plants that need enrichment — prioritize Perenual plants
    rows = turso_query('''
        SELECT p.plant_id, p.scientific
        FROM plants p
        LEFT JOIN care c ON p.plant_id = c.plant_id
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN p.sources LIKE ? THEN 0 ELSE 1 END,
            p.scientific
        LIMIT ?
    ''', ['%perenual%', limit])

    plants = [(r['scientific'], r['plant_id']) for r in rows]
    print(f"[Missouri BG] Checking {len(plants)} plants...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(20000)

        enriched = enrich_from_missouri(plants, page)

        browser.close()

    print(f"[Missouri BG] Done: {enriched} plants enriched")
    return enriched


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(limit)
