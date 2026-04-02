"""
Trefle API fetcher — bulk taxonomy import for plant database.
Free, 120 req/min, 437,255 species available.
Provides: scientific name, family, genus, common_name, image_url.
Care data: mostly null — use FAMILY_PRESETS for baseline care.
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

from config import TREFLE_API_KEY, TREFLE_DELAY
from models import PlantRecord, CareData
from turso_sync import turso_batch, turso_query

TREFLE_BASE = 'https://trefle.io/api/v1'

# Family → preset mapping (76 families)
FAMILY_PRESETS = {
    'Araceae': 'Tropical', 'Marantaceae': 'Tropical', 'Bromeliaceae': 'Tropical',
    'Gesneriaceae': 'Tropical', 'Piperaceae': 'Tropical', 'Polypodiaceae': 'Tropical',
    'Pteridaceae': 'Tropical', 'Commelinaceae': 'Tropical', 'Musaceae': 'Tropical',
    'Heliconiaceae': 'Tropical', 'Zingiberaceae': 'Tropical', 'Costaceae': 'Tropical',
    'Davalliaceae': 'Tropical', 'Aspleniaceae': 'Tropical', 'Nephrolepidaceae': 'Tropical',
    'Pandanaceae': 'Tropical', 'Passifloraceae': 'Tropical', 'Nepenthaceae': 'Tropical',
    'Sarraceniaceae': 'Tropical', 'Droseraceae': 'Tropical', 'Cannaceae': 'Tropical',
    'Acanthaceae': 'Tropical', 'Dryopteridaceae': 'Tropical', 'Blechnaceae': 'Tropical',
    'Cactaceae': 'Succulents', 'Crassulaceae': 'Succulents', 'Asphodelaceae': 'Succulents',
    'Aizoaceae': 'Succulents', 'Euphorbiaceae': 'Succulents', 'Portulacaceae': 'Succulents',
    'Didiereaceae': 'Succulents',
    'Lamiaceae': 'Herbs', 'Apiaceae': 'Herbs', 'Lauraceae': 'Herbs', 'Poaceae': 'Herbs',
    'Moraceae': 'Standard', 'Asparagaceae': 'Standard', 'Araliaceae': 'Standard',
    'Rutaceae': 'Standard', 'Apocynaceae': 'Standard', 'Orchidaceae': 'Standard',
    'Begoniaceae': 'Standard', 'Malvaceae': 'Standard', 'Arecaceae': 'Standard',
    'Urticaceae': 'Standard', 'Amaryllidaceae': 'Standard', 'Rubiaceae': 'Standard',
    'Oleaceae': 'Standard', 'Geraniaceae': 'Standard', 'Oxalidaceae': 'Standard',
    'Strelitziaceae': 'Standard', 'Solanaceae': 'Standard', 'Liliaceae': 'Standard',
    'Primulaceae': 'Standard', 'Rosaceae': 'Standard', 'Hydrangeaceae': 'Standard',
    'Myrtaceae': 'Standard', 'Asteraceae': 'Standard', 'Amaranthaceae': 'Standard',
    'Nyctaginaceae': 'Standard', 'Ericaceae': 'Standard', 'Cycadaceae': 'Standard',
    'Zamiaceae': 'Standard', 'Vitaceae': 'Standard', 'Onagraceae': 'Standard',
    'Theaceae': 'Standard', 'Balsaminaceae': 'Standard', 'Convolvulaceae': 'Standard',
    'Verbenaceae': 'Standard', 'Ranunculaceae': 'Standard', 'Plantaginaceae': 'Standard',
    'Campanulaceae': 'Standard', 'Gentianaceae': 'Standard', 'Sapindaceae': 'Standard',
    'Saxifragaceae': 'Standard', 'Lythraceae': 'Standard', 'Caryophyllaceae': 'Standard',
}

# Preset care defaults
PRESET_CARE = {
    'Succulents': CareData(
        water_frequency='Every 2-3 weeks', water_demand='Low',
        light_preferred='Bright direct or indirect light',
        temp_min_c=5, temp_max_c=35, humidity_level='Low (30-40%)',
    ),
    'Tropical': CareData(
        water_frequency='Every 5-7 days', water_demand='High',
        light_preferred='Bright indirect light, no direct sun',
        temp_min_c=15, temp_max_c=30, humidity_level='High (60-80%)',
    ),
    'Herbs': CareData(
        water_frequency='Every 2-3 days', water_demand='Medium',
        light_preferred='Full sun (6+ hours)',
        temp_min_c=10, temp_max_c=30, humidity_level='Average (40-60%)',
    ),
    'Standard': CareData(
        water_frequency='Every 7-10 days', water_demand='Medium',
        light_preferred='Bright indirect light',
        temp_min_c=10, temp_max_c=30, humidity_level='Average (40-60%)',
    ),
}

# Progress file — remember last page for resuming
PROGRESS_FILE = Path(__file__).parent.parent / '.trefle_progress'


def _load_progress():
    if PROGRESS_FILE.exists():
        return int(PROGRESS_FILE.read_text().strip())
    return 1


def _save_progress(page):
    PROGRESS_FILE.write_text(str(page))


def fetch_plants_page(page):
    """Fetch one page of plants from Trefle (20 per page)."""
    params = urllib.parse.urlencode({'token': TREFLE_API_KEY, 'page': page})
    url = f'{TREFLE_BASE}/plants?{params}'
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def map_to_plant_record(trefle_plant):
    """Map Trefle plant → PlantRecord with preset care based on family."""
    scientific = trefle_plant.get('scientific_name', '')
    if not scientific:
        return None

    plant_id = scientific.lower().replace(' ', '_').replace("'", '').replace('"', '')
    family = trefle_plant.get('family', '') or ''
    genus = trefle_plant.get('genus', '') or ''
    common_name = trefle_plant.get('common_name', '') or ''
    image_url = trefle_plant.get('image_url', '') or ''

    preset = FAMILY_PRESETS.get(family, 'Standard')
    care = CareData(**PRESET_CARE.get(preset, PRESET_CARE['Standard']).__dict__)

    tags = []
    # Indoor heuristic: tropical/standard families are typically indoor
    if preset in ('Tropical', 'Standard', 'Succulents'):
        tags.append('indoor')

    record = PlantRecord(
        plant_id=plant_id,
        scientific=scientific,
        family=family,
        genus=genus,
        preset=preset,
        image_url=image_url,
        sources=['trefle'],
        common_names={'en': [common_name]} if common_name else {},
        tags=tags,
        care=care,
    )
    return record


def batch_upsert(records):
    """Batch INSERT OR IGNORE plants into Turso. Skips existing records."""
    if not records:
        return 0

    statements = []
    for r in records:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        # INSERT OR IGNORE — don't overwrite Perenual data with Trefle skeleton
        statements.append((
            '''INSERT OR IGNORE INTO plants (plant_id, scientific, family, genus, category, indoor, edible, has_phases, preset, image_url, sources, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [r.plant_id, r.scientific, r.family, r.genus, r.category,
             int(r.indoor), int(r.edible), int(r.has_phases), r.preset,
             r.image_url, json.dumps(r.sources), now]
        ))

        # Care — INSERT OR IGNORE (don't overwrite existing care)
        cd = r.care.to_dict()
        cd['plant_id'] = r.plant_id
        cols = list(cd.keys())
        col_names = ', '.join(cols)
        placeholders = ', '.join(['?'] * len(cols))
        statements.append((
            f'INSERT OR IGNORE INTO care ({col_names}) VALUES ({placeholders})',
            [cd[c] for c in cols]
        ))

        # Common names
        for lang, names in r.common_names.items():
            for i, name in enumerate(names):
                statements.append((
                    'INSERT OR IGNORE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, ?, ?, ?)',
                    [r.plant_id, lang, name, 1 if i == 0 else 0]
                ))

    # Execute in batches of 50
    inserted = 0
    for i in range(0, len(statements), 50):
        try:
            turso_batch(statements[i:i+50])
            inserted += min(50, len(statements) - i)
        except Exception as e:
            print(f"  ! Batch error at offset {i}: {e}")

    return len(records)


def fetch_and_store(count=1000, resume=True):
    """Fetch plants from Trefle and store skeleton records in Turso."""
    start_page = _load_progress() if resume else 1
    page = start_page
    stored = 0
    skipped = 0
    per_page = 20  # Trefle returns 20 per page

    print(f"[Trefle] Fetching up to {count} plants, starting from page {page}...")

    while stored < count:
        try:
            data = fetch_plants_page(page)
            time.sleep(TREFLE_DELAY)

            plants = data.get('data', [])
            if not plants:
                print(f"[Trefle] No more plants at page {page}")
                break

            records = []
            for p in plants:
                rec = map_to_plant_record(p)
                if rec:
                    records.append(rec)

            if records:
                batch_upsert(records)
                stored += len(records)

            page += 1
            _save_progress(page)

            if stored % 100 == 0 and stored > 0:
                print(f"[Trefle] Progress: {stored}/{count} plants (page {page})")

        except Exception as e:
            print(f"[Trefle] Error at page {page}: {e}")
            time.sleep(2)
            continue

    print(f"[Trefle] Done: {stored} plants stored (pages {start_page}-{page})")
    return stored


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    resume = '--fresh' not in sys.argv
    fetch_and_store(count, resume=resume)
