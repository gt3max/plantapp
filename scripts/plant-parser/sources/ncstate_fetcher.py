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

from turso_sync import turso_query, turso_batch, upsert_care_fields, upsert_plant_fields

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

            # Propagation → proper field now
            if data.get('propagation'):
                methods = [m.strip() for m in data['propagation'].split(',')]
                statements.append((
                    "UPDATE care SET propagation_methods = CASE WHEN propagation_methods IS NULL OR propagation_methods = '' OR propagation_methods = '[]' THEN ? ELSE propagation_methods END WHERE plant_id = ?",
                    [json.dumps(methods), pid]
                ))
                statements.append((
                    "UPDATE care SET propagation_detail = CASE WHEN propagation_detail IS NULL OR propagation_detail = '' THEN ? ELSE propagation_detail END WHERE plant_id = ?",
                    [f"NC State recommends: {data['propagation']}", pid]
                ))

            # Insects & diseases → split into pests and problems separately
            if data.get('insects_diseases'):
                text = data['insects_diseases']
                # Split by sentences, classify each
                _disease_words = ['rot', 'wilt', 'blight', 'mildew', 'spot', 'rust', 'canker', 'scab', 'virus', 'fungal', 'bacterial', 'disease', 'mold']
                _pest_words = ['aphid', 'beetle', 'mite', 'bug', 'caterpillar', 'fly', 'whitefl', 'thrip', 'scale', 'mealybug', 'weevil', 'borer', 'insect', 'pest', 'worm', 'slug', 'snail']
                sentences = [s.strip() for s in text.replace('. ', '.\n').split('\n') if s.strip()]
                pest_items = []
                disease_items = []
                for s in sentences:
                    sl = s.lower()
                    if any(p in sl for p in _pest_words):
                        pest_items.append(s)
                    if any(d in sl for d in _disease_words):
                        disease_items.append(s)
                    if not any(p in sl for p in _pest_words) and not any(d in sl for d in _disease_words):
                        disease_items.append(s)  # default to problems
                if pest_items:
                    statements.append((
                        "UPDATE care SET common_pests = CASE WHEN common_pests IS NULL OR common_pests = '' OR common_pests = '[]' THEN ? ELSE common_pests END WHERE plant_id = ?",
                        [json.dumps(pest_items), pid]
                    ))
                if disease_items:
                    statements.append((
                        "UPDATE care SET common_problems = CASE WHEN common_problems IS NULL OR common_problems = '' OR common_problems = '[]' THEN ? ELSE common_problems END WHERE plant_id = ?",
                        [json.dumps(disease_items), pid]
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
                        "UPDATE care SET height_min_cm = CASE WHEN height_min_cm IS NULL OR height_min_cm = 0 THEN ? ELSE height_min_cm END, height_max_cm = CASE WHEN height_max_cm IS NULL OR height_max_cm = 0 THEN ? ELSE height_max_cm END WHERE plant_id = ?",
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

            # Origin → plants.origin
            if data.get('origin'):
                statements.append((
                    "UPDATE plants SET origin = CASE WHEN origin IS NULL OR origin = '' THEN ? ELSE origin END WHERE plant_id = ?",
                    [data['origin'], pid]
                ))

            # Soil pH
            if data.get('soil_ph'):
                ph_text = data['soil_ph']
                ph_nums = re.findall(r'(\d+\.?\d*)', ph_text)
                if ph_nums:
                    ph_min = float(ph_nums[0])
                    ph_max = float(ph_nums[-1]) if len(ph_nums) > 1 else ph_min
                    statements.append((
                        "UPDATE care SET soil_ph_min = CASE WHEN soil_ph_min IS NULL OR soil_ph_min = 0 THEN ? ELSE soil_ph_min END, soil_ph_max = CASE WHEN soil_ph_max IS NULL OR soil_ph_max = 0 THEN ? ELSE soil_ph_max END WHERE plant_id = ?",
                        [ph_min, ph_max, pid]
                    ))

            # Dimensions → also parse spread (Width)
            if data.get('dimensions'):
                dims = data['dimensions']
                spread_m = re.search(r'Width:\s*(\d+)\s*ft', dims)
                if spread_m:
                    spread_vals = re.findall(r'Width:.*?(\d+)\s*ft', dims)
                    if spread_vals:
                        spread_cm = int(spread_vals[-1]) * 30
                        statements.append((
                            "UPDATE care SET spread_max_cm = CASE WHEN spread_max_cm IS NULL OR spread_max_cm = 0 THEN ? ELSE spread_max_cm END WHERE plant_id = ?",
                            [spread_cm, pid]
                        ))

            # Hardiness zone → more precise temp_min_c
            if data.get('hardiness_zone'):
                zone_text = data['hardiness_zone']
                zone_nums = re.findall(r'(\d+)', zone_text)
                if zone_nums:
                    zone_min = int(zone_nums[0])
                    zone_temps = {1:-51,2:-45,3:-40,4:-34,5:-29,6:-23,7:-18,8:-12,9:-7,10:-1,11:4,12:10,13:15}
                    if zone_min in zone_temps:
                        statements.append((
                            "UPDATE care SET temp_min_c = CASE WHEN temp_min_c IS NULL OR temp_min_c = 0 THEN ? ELSE temp_min_c END WHERE plant_id = ?",
                            [zone_temps[zone_min], pid]
                        ))

            # Uses → used_for
            if data.get('uses'):
                uses_list = [u.strip() for u in data['uses'].split(',')]
                statements.append((
                    "UPDATE care SET used_for = CASE WHEN used_for IS NULL OR used_for = '' OR used_for = '[]' THEN ? ELSE used_for END WHERE plant_id = ?",
                    [json.dumps(uses_list), pid]
                ))
                statements.append((
                    "UPDATE care SET used_for_details = CASE WHEN used_for_details IS NULL OR used_for_details = '' THEN ? ELSE used_for_details END WHERE plant_id = ?",
                    [data['uses'], pid]
                ))

            # Edibility → edible_parts
            if data.get('edibility'):
                statements.append((
                    "UPDATE care SET edible_parts = CASE WHEN edible_parts IS NULL OR edible_parts = '' THEN ? ELSE edible_parts END WHERE plant_id = ?",
                    [data['edibility'], pid]
                ))

            # Habit/Form → can inform difficulty_note
            if data.get('habit_form'):
                statements.append((
                    "UPDATE care SET difficulty_note = CASE WHEN difficulty_note IS NULL OR difficulty_note = '' THEN ? ELSE difficulty_note END WHERE plant_id = ?",
                    [f"Growth habit: {data['habit_form']}", pid]
                ))

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
