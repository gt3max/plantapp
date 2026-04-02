"""
Perenual v2 API fetcher — full care data for plant database.
Free plan: 3,000 species (ID 1-3000), 100 requests/day.
"""
import json
import time
import urllib.request
import urllib.parse
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before importing config
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from config import PERENUAL_API_KEY, PERENUAL_DELAY
from models import PlantRecord, CareData
from turso_sync import turso_execute, turso_batch, turso_query

PERENUAL_V2_BASE = 'https://perenual.com/api/v2'
MAX_FREE_ID = 3000
DAILY_LIMIT = 100

# Progress file — remember last page for resuming
PROGRESS_FILE = Path(__file__).parent.parent / '.perenual_progress'


def _load_progress():
    if PROGRESS_FILE.exists():
        return int(PROGRESS_FILE.read_text().strip())
    return 1


def _save_progress(page):
    PROGRESS_FILE.write_text(str(page))


# Family → preset mapping (same as Lambda)
FAMILY_PRESETS = {
    'Araceae': 'Tropical', 'Marantaceae': 'Tropical', 'Bromeliaceae': 'Tropical',
    'Gesneriaceae': 'Tropical', 'Piperaceae': 'Tropical', 'Polypodiaceae': 'Tropical',
    'Pteridaceae': 'Tropical', 'Commelinaceae': 'Tropical', 'Musaceae': 'Tropical',
    'Cactaceae': 'Succulents', 'Crassulaceae': 'Succulents', 'Asphodelaceae': 'Succulents',
    'Aizoaceae': 'Succulents', 'Euphorbiaceae': 'Succulents',
    'Lamiaceae': 'Herbs', 'Apiaceae': 'Herbs', 'Poaceae': 'Herbs',
}


def fetch_species_list(page=1, indoor_only=False):
    """Fetch species list page from Perenual v2."""
    params = {'key': PERENUAL_API_KEY, 'page': page}
    if indoor_only:
        params['indoor'] = 1
    url = f'{PERENUAL_V2_BASE}/species-list?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_species_detail(species_id):
    """Fetch full species detail from Perenual v2."""
    if species_id > MAX_FREE_ID:
        return None
    url = f'{PERENUAL_V2_BASE}/species/details/{species_id}?key={PERENUAL_API_KEY}'
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def map_to_plant_record(data):
    """Map Perenual v2 species detail → PlantRecord + CareData."""
    if not data or not data.get('scientific_name'):
        return None

    scientific = data['scientific_name']
    if isinstance(scientific, list):
        scientific = scientific[0]
    scientific = scientific.strip()
    if not scientific:
        return None

    plant_id = scientific.lower().replace(' ', '_').replace("'", '').replace('"', '')
    family = data.get('family', '') or ''
    preset = FAMILY_PRESETS.get(family, 'Standard')

    # Image
    img = data.get('default_image', {}) or {}
    image_url = img.get('regular_url', '') or img.get('medium_url', '') or img.get('original_url', '') or ''

    # Watering frequency from benchmark
    wb = data.get('watering_general_benchmark', {}) or {}
    water_freq = ''
    if wb and wb.get('value'):
        val = str(wb['value']).strip('"')
        unit = wb.get('unit', 'days')
        water_freq = f'Every {val} {unit}'

    # Temperature from hardiness
    hardiness = data.get('hardiness', {}) or {}
    temp_min = 0
    temp_max = 0
    if hardiness.get('min'):
        try:
            temp_min = int(str(hardiness['min']).strip('"'))
        except (ValueError, TypeError):
            pass
    if hardiness.get('max'):
        try:
            temp_max = int(str(hardiness['max']).strip('"'))
        except (ValueError, TypeError):
            pass

    # Dimensions
    dims = data.get('dimensions', {}) or {}
    height_min = 0
    height_max = 0
    if isinstance(dims, dict):
        height_min = _safe_int(dims.get('min_value', 0))
        height_max = _safe_int(dims.get('max_value', 0))
        # Convert feet to cm if unit is feet
        if dims.get('unit', '').lower() in ('feet', 'ft'):
            height_min = int(height_min * 30.48)
            height_max = int(height_max * 30.48)

    # Sunlight
    sunlight = data.get('sunlight', []) or []
    light_preferred = sunlight[0] if sunlight else ''

    # Soil
    soil_list = data.get('soil', []) or []
    soil_types = ', '.join(soil_list) if isinstance(soil_list, list) else str(soil_list)

    # Pests
    pests_raw = data.get('pest_susceptibility', []) or []
    pests = [p.strip() for p in pests_raw if p and p.strip()] if isinstance(pests_raw, list) else []

    # Propagation → tags
    propagation = data.get('propagation', []) or []
    tags = []
    if data.get('indoor'):
        tags.append('indoor')
    if data.get('edible_fruit') or data.get('edible_leaf'):
        tags.append('edible')
    if not data.get('poisonous_to_pets') and not data.get('poisonous_to_humans'):
        tags.append('pet-safe')

    # Common names
    common_name = data.get('common_name', '')
    other_names = data.get('other_name', []) or []
    names_en = [common_name] if common_name else []
    if other_names:
        names_en.extend(other_names[:3])

    # Category
    plant_type = data.get('type', '') or ''
    cycle = data.get('cycle', '') or ''
    edible = bool(data.get('edible_fruit') or data.get('edible_leaf'))
    if edible and data.get('edible_fruit'):
        category = 'fruiting'
    elif edible:
        category = 'greens'
    else:
        category = 'decorative'

    care = CareData(
        water_frequency=water_freq,
        water_demand=data.get('watering', '') or '',
        light_preferred=light_preferred,
        difficulty=data.get('care_level', '') or '',
        growth_rate=data.get('growth_rate', '') or '',
        lifecycle=cycle,
        soil_types=soil_types,
        temp_min_c=temp_min,
        temp_max_c=temp_max,
        height_min_cm=height_min,
        height_max_cm=height_max,
        toxic_to_pets=bool(data.get('poisonous_to_pets')),
        toxic_to_humans=bool(data.get('poisonous_to_humans')),
        toxicity_note='Toxic to pets and/or humans' if data.get('poisonous_to_pets') or data.get('poisonous_to_humans') else '',
        common_pests=pests,
        tips=data.get('description', '')[:200] if data.get('description') else '',
    )

    record = PlantRecord(
        plant_id=plant_id,
        scientific=scientific,
        family=family,
        genus=data.get('genus', '') or '',
        category=category,
        indoor=bool(data.get('indoor')),
        edible=edible,
        preset=preset,
        image_url=image_url,
        description=data.get('description', '') or '',
        sources=['perenual'],
        common_names={'en': names_en} if names_en else {},
        tags=tags,
        care=care,
        external_ids={'perenual': str(data.get('id', ''))},
    )
    return record


def upsert_plant(record):
    """INSERT OR REPLACE plant into Turso DB."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    statements = []

    # Plants table
    statements.append((
        '''INSERT OR REPLACE INTO plants (plant_id, scientific, family, genus, category, indoor, edible, has_phases, preset, image_url, description, sources, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        [record.plant_id, record.scientific, record.family, record.genus,
         record.category, int(record.indoor), int(record.edible), int(record.has_phases),
         record.preset, record.image_url, record.description,
         json.dumps(record.sources), now]
    ))

    # Care table
    cd = record.care.to_dict()
    cd['plant_id'] = record.plant_id
    cols = list(cd.keys())
    placeholders = ', '.join(['?'] * len(cols))
    col_names = ', '.join(cols)
    statements.append((
        f'INSERT OR REPLACE INTO care ({col_names}) VALUES ({placeholders})',
        [cd[c] for c in cols]
    ))

    # Common names
    for lang, names in record.common_names.items():
        for i, name in enumerate(names):
            statements.append((
                'INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, ?, ?, ?)',
                [record.plant_id, lang, name, 1 if i == 0 else 0]
            ))

    # Tags
    for tag in record.tags:
        statements.append((
            'INSERT OR REPLACE INTO plant_tags (plant_id, tag) VALUES (?, ?)',
            [record.plant_id, tag]
        ))

    # External IDs
    for source, ext_id in record.external_ids.items():
        statements.append((
            'INSERT OR REPLACE INTO external_ids (plant_id, source, external_id) VALUES (?, ?, ?)',
            [record.plant_id, source, ext_id]
        ))

    # Batch execute (max 50 per pipeline)
    for i in range(0, len(statements), 50):
        turso_batch(statements[i:i+50])


def fetch_and_store(count=100, indoor_first=True, resume=True):
    """Fetch NEW plants from Perenual and store in Turso. Skips already fetched. Returns number stored."""
    stored = 0
    skipped = 0
    page = _load_progress() if resume else 1
    request_count = 0

    print(f"[Perenual] Fetching up to {count} NEW plants, starting from page {page}...")

    while stored < count and request_count < DAILY_LIMIT:
        try:
            data = fetch_species_list(page, indoor_only=indoor_first)
            request_count += 1
            time.sleep(PERENUAL_DELAY)

            species_list = data.get('data', [])
            if not species_list:
                if indoor_first:
                    print(f"[Perenual] No more indoor plants, switching to all...")
                    indoor_first = False
                    page = 1
                    _save_progress(page)
                    continue
                break

            for sp in species_list:
                if stored >= count or request_count >= DAILY_LIMIT:
                    break

                species_id = sp.get('id', 0)
                if species_id > MAX_FREE_ID:
                    continue

                # Skip if already fetched from Perenual
                sci_name = sp.get('scientific_name', [''])
                if isinstance(sci_name, list):
                    sci_name = sci_name[0] if sci_name else ''
                plant_id = sci_name.lower().replace(' ', '_').replace("'", '').replace('"', '')

                existing = turso_query(
                    "SELECT sources FROM plants WHERE plant_id = ?",
                    [plant_id]
                )
                if existing and 'perenual' in (existing[0].get('sources', '') or ''):
                    skipped += 1
                    continue

                try:
                    detail = fetch_species_detail(species_id)
                    request_count += 1
                    time.sleep(PERENUAL_DELAY)

                    if not detail:
                        continue

                    record = map_to_plant_record(detail)
                    if not record:
                        continue

                    upsert_plant(record)
                    stored += 1

                    if stored % 10 == 0:
                        print(f"[Perenual] Stored {stored}/{count} new (skipped: {skipped}, requests: {request_count}/{DAILY_LIMIT}, page: {page})")
                    elif stored <= 5:
                        print(f"  + {record.scientific} ({record.family})")

                except Exception as e:
                    print(f"  ! Error on ID {species_id}: {e}")
                    continue

            page += 1
            _save_progress(page)

        except Exception as e:
            print(f"[Perenual] Page {page} error: {e}")
            _save_progress(page)
            break

    print(f"[Perenual] Done: {stored} new plants stored, {skipped} skipped (already had), {request_count} API requests used")
    print(f"[Perenual] Progress saved at page {page}. Next run continues from here.")
    return stored


def _safe_int(val, default=0):
    try:
        return int(float(str(val).strip('"')))
    except (ValueError, TypeError):
        return default


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    resume = '--fresh' not in sys.argv
    fetch_and_store(count, resume=resume)
