"""
NC State Extension Plant Toolbox parser.
Source: https://plants.ces.ncsu.edu/plants/
5,000+ plants with scientific care data from university researchers.
Free, public website. Polite scraping with delays.
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

BASE_URL = 'https://plants.ces.ncsu.edu'
DELAY = 1.0  # Polite: 1 second between requests


def fetch_plant_page(slug):
    """Fetch single plant HTML page from NC State."""
    url = f'{BASE_URL}/plants/{slug}/'
    req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0 (plantapp.pro, educational use)'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def parse_plant_page(html):
    """Extract structured data from NC State plant page."""
    data = {}

    # Pattern: field name followed by content
    patterns = {
        'description': r'Description:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{10,500})',
        'light': r'Light:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{5,200})',
        'soil_texture': r'Soil Texture:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
        'soil_ph': r'Soil pH:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'soil_drainage': r'Soil Drainage:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'maintenance': r'Maintenance:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,50})',
        'growth_rate': r'Growth Rate:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,50})',
        'texture': r'Texture:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,50})',
        'habit_form': r'Habit/Form:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'life_cycle': r'Life Cycle:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,50})',
        'propagation': r'Recommended Propagation Strategy:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
        'edibility': r'Edibility:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,300})',
        'uses': r'Uses \(Ethnobotany\):\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,300})',
        'insects_diseases': r'Insects,?\s*Disease[^:]*:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,500})',
        'dimensions': r'Dimensions:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
        'origin': r'Country Or Region Of Origin:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
        'hardiness_zone': r'USDA Plant Hardiness Zone:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'family': r'Family:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'genus': r'Genus:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'species': r'Species:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,100})',
        'tags': r'Tags:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
        'similar_plants': r'Plants that fill a similar niche:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,300})',
        'play_value': r'Play Value:\s*</?\w+>\s*(?:<[^>]+>\s*)*([^<]{3,200})',
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, html)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'&\w+;', ' ', val).strip()  # Remove HTML entities
            if val:
                data[key] = val

    return data


def enrich_from_ncstate(limit=100):
    """Fetch NC State data and enrich existing Turso records."""
    # Get plants from our DB that need enrichment
    rows = turso_query('''
        SELECT p.plant_id, p.scientific, p.family
        FROM plants p
        LEFT JOIN care c ON p.plant_id = c.plant_id
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN p.sources LIKE ? THEN 0 ELSE 1 END,
            p.scientific
        LIMIT ?
    ''', ['%perenual%', limit])

    print(f"[NC State] Enriching up to {len(rows)} plants...")
    enriched = 0
    not_found = 0
    errors = 0

    for i, row in enumerate(rows):
        scientific = row['scientific']
        pid = row['plant_id']

        # Build slug: "Monstera deliciosa" → "monstera-deliciosa"
        slug = scientific.lower().replace(' ', '-').replace("'", '').replace('"', '')

        try:
            html = fetch_plant_page(slug)
            time.sleep(DELAY)

            if len(html) < 1000 or '404' in html[:500]:
                not_found += 1
                continue

            data = parse_plant_page(html)
            if not data:
                not_found += 1
                continue

            statements = []

            # Light
            if data.get('light'):
                statements.append((
                    "UPDATE care SET light_preferred = CASE WHEN light_preferred IS NULL OR light_preferred = '' THEN ? ELSE light_preferred END WHERE plant_id = ?",
                    [data['light'], pid]
                ))
                # Also set light_guide
                statements.append((
                    "UPDATE care SET light_guide = CASE WHEN light_guide IS NULL OR light_guide = '' THEN ? ELSE light_guide END WHERE plant_id = ?",
                    [f"NC State: {data['light']}", pid]
                ))

            # Propagation
            if data.get('propagation'):
                # This is propagation detail we've been missing!
                statements.append((
                    "UPDATE care SET watering_guide = CASE WHEN watering_guide IS NULL OR watering_guide = '' THEN ? ELSE watering_guide END WHERE plant_id = ?",
                    [f"Propagation: {data['propagation']}", pid]
                ))

            # Insects & diseases → common_problems + common_pests
            if data.get('insects_diseases'):
                text = data['insects_diseases']
                statements.append((
                    "UPDATE care SET common_problems = CASE WHEN common_problems IS NULL OR common_problems = '' OR common_problems = '[]' THEN ? ELSE common_problems END WHERE plant_id = ?",
                    [json.dumps([text]), pid]
                ))

            # Maintenance → difficulty
            if data.get('maintenance'):
                diff_map = {'low': 'Easy', 'medium': 'Medium', 'high': 'Hard'}
                diff = diff_map.get(data['maintenance'].lower().strip(), data['maintenance'])
                statements.append((
                    "UPDATE care SET difficulty = CASE WHEN difficulty IS NULL OR difficulty = '' THEN ? ELSE difficulty END WHERE plant_id = ?",
                    [diff, pid]
                ))

            # Growth rate
            if data.get('growth_rate'):
                statements.append((
                    "UPDATE care SET growth_rate = CASE WHEN growth_rate IS NULL OR growth_rate = '' THEN ? ELSE growth_rate END WHERE plant_id = ?",
                    [data['growth_rate'], pid]
                ))

            # Life cycle
            if data.get('life_cycle'):
                statements.append((
                    "UPDATE care SET lifecycle = CASE WHEN lifecycle IS NULL OR lifecycle = '' THEN ? ELSE lifecycle END WHERE plant_id = ?",
                    [data['life_cycle'].lower(), pid]
                ))

            # Soil
            soil_parts = []
            if data.get('soil_texture'):
                soil_parts.append(data['soil_texture'])
            if data.get('soil_drainage'):
                soil_parts.append(data['soil_drainage'])
            if soil_parts:
                soil_text = ', '.join(soil_parts)
                statements.append((
                    "UPDATE care SET soil_types = CASE WHEN soil_types IS NULL OR soil_types = '' THEN ? ELSE soil_types END WHERE plant_id = ?",
                    [soil_text, pid]
                ))

            # Description
            if data.get('description'):
                desc = data['description'][:500]
                statements.append((
                    "UPDATE plants SET description = CASE WHEN description IS NULL OR description = '' THEN ? ELSE description END WHERE plant_id = ?",
                    [desc, pid]
                ))

            # Dimensions → height
            if data.get('dimensions'):
                dims = data['dimensions']
                # Parse "Height: 0 ft. 4 in. - 3 ft. 0 in."
                heights = re.findall(r'(\d+)\s*ft', dims)
                if heights:
                    h_min = int(heights[0]) * 30  # ft to cm
                    h_max = int(heights[-1]) * 30 if len(heights) > 1 else h_min
                    statements.append((
                        "UPDATE care SET height_min_cm = CASE WHEN height_min_cm = 0 THEN ? ELSE height_min_cm END, height_max_cm = CASE WHEN height_max_cm = 0 THEN ? ELSE height_max_cm END WHERE plant_id = ?",
                        [h_min, h_max, pid]
                    ))

            # Similar plants → we can use as pseudo-companions
            # Store in tips field as reference
            if data.get('similar_plants'):
                similar = data['similar_plants']
                statements.append((
                    "UPDATE care SET tips = CASE WHEN tips IS NULL OR tips = '' THEN ? WHEN tips NOT LIKE ? THEN tips || ? ELSE tips END WHERE plant_id = ?",
                    [f"Similar plants: {similar}", f"%Similar plants%", f" | Similar plants: {similar}", pid]
                ))

            # Uses/Edibility
            uses_parts = []
            if data.get('uses'):
                uses_parts.append(data['uses'])
            if data.get('edibility'):
                uses_parts.append(f"Edible: {data['edibility']}")
            # Store in watering_guide as temp field (or we need a used_for column)

            if statements:
                turso_batch(statements)
                enriched += 1

            if (i + 1) % 20 == 0:
                print(f"[NC State] Progress: {i+1}/{len(rows)}, enriched: {enriched}, not found: {not_found}")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                not_found += 1
            else:
                errors += 1
                if errors <= 5:
                    print(f"  ! HTTP {e.code} for {slug}")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ! Error for {slug}: {e}")
            continue

    print(f"[NC State] Done: {enriched} enriched, {not_found} not found, {errors} errors")
    return enriched


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    enrich_from_ncstate(limit)
