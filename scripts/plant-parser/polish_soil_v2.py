"""
Polish soil v2 — USDA texture/pH + lifeform defaults for ALL 20K plants.

Step 1: USDA soil texture + pH → source_data + care
Step 2: Lifeform defaults for ALL empty soil_types
Step 3: Lifeform defaults for ALL empty repot_frequency + repot_signs
Step 4: Lifeform defaults for ALL empty soil_ph
Step 5: Flag remaining empty

Does NOT overwrite existing data. Source attribution everywhere.

Usage:
    python3 polish_soil_v2.py --dry-run
    python3 polish_soil_v2.py
"""
import sys
import os
import csv
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_query, turso_batch

USDA_CSV = os.path.join(os.path.dirname(__file__), 'data', 'usda_plant_characteristics.csv')

LIFEFORM_SOIL = {
    'succulent': {
        'soil': 'Cactus/succulent mix (sand, perlite, minimal organic)',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Every 2-3 years',
        'signs': 'Plant becomes top-heavy, roots visible at surface, soil depleted.',
    },
    'epiphyte': {
        'soil': 'Orchid bark mix, sphagnum moss (no regular soil)',
        'ph_min': 5.5, 'ph_max': 6.5,
        'repot': 'Every 1-2 years when bark decomposes',
        'signs': 'Bark breaks down and holds too much moisture, roots rotting.',
    },
    'climber': {
        'soil': 'Chunky aroid mix (bark, perlite, peat, charcoal)',
        'ph_min': 5.5, 'ph_max': 7.0,
        'repot': 'Every 1-2 years',
        'signs': 'Roots growing out of drainage holes, growth slows down.',
    },
    'tree': {
        'soil': 'Standard potting mix with perlite for drainage',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Every 2-3 years',
        'signs': 'Roots circling inside pot, water runs straight through.',
    },
    'shrub': {
        'soil': 'Standard potting mix with perlite',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Every 2-3 years',
        'signs': 'Root-bound, soil dries out quickly after watering.',
    },
    'subshrub': {
        'soil': 'Well-draining potting mix with perlite',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Every 1-2 years',
        'signs': 'Roots visible at drainage holes, plant outgrows pot.',
    },
    'perennial': {
        'soil': 'Standard potting mix with perlite',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Every 1-2 years in spring',
        'signs': 'Roots growing out of drainage holes, soil compacted.',
    },
    'annual': {
        'soil': 'Light seed-starting or potting mix',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'Not needed (completes lifecycle in one season)',
        'signs': 'N/A — annual plant.',
    },
    'bulb': {
        'soil': 'Well-draining mix with sand and organic matter',
        'ph_min': 6.0, 'ph_max': 7.0,
        'repot': 'After dormancy period or when crowded',
        'signs': 'Bulbs crowding, fewer flowers, pushing out of soil.',
    },
    'aquatic': {
        'soil': 'Heavy clay or aquatic planting media',
        'ph_min': 6.5, 'ph_max': 7.5,
        'repot': 'When plant outgrows container',
        'signs': 'Roots filling entire container, plant lifting out.',
    },
    'fern': {
        'soil': 'Peat-based mix with perlite, moisture-retentive',
        'ph_min': 5.0, 'ph_max': 6.0,
        'repot': 'Every 1-2 years in spring',
        'signs': 'Roots filling pot, fronds becoming smaller.',
    },
    'bamboo': {
        'soil': 'Rich organic mix, moisture-retentive with good drainage',
        'ph_min': 5.5, 'ph_max': 6.5,
        'repot': 'Every 2-3 years or when root-bound',
        'signs': 'Roots pushing through drainage, growth stalling.',
    },
    'moss': {
        'soil': 'Acidic peat-based mix, moisture-retentive',
        'ph_min': 4.5, 'ph_max': 6.0,
        'repot': 'Not typically repotted',
        'signs': 'N/A — moss grows on substrate surface.',
    },
    'parasitic': None,  # Depends on host, don't fill
}


def step1_usda(dry_run=False):
    """Import USDA soil texture + pH."""
    print(f"\n=== STEP 1: USDA soil texture + pH ===", flush=True)

    if not os.path.exists(USDA_CSV):
        print(f"  ERROR: USDA CSV not found", flush=True)
        return

    # Load USDA
    usda = {}
    with open(USDA_CSV) as f:
        for row in csv.DictReader(f):
            sci = row.get('scientific_name', '').strip().lower()
            if not sci:
                continue
            textures = []
            if row.get('adapted_to_coarse_textured_soils', '').strip() == 'Yes':
                textures.append('Sandy')
            if row.get('adapted_to_medium_textured_soils', '').strip() == 'Yes':
                textures.append('Loamy')
            if row.get('adapted_to_fine_textured_soils', '').strip() == 'Yes':
                textures.append('Clay')
            ph_min = row.get('ph_minimum', '').strip()
            ph_max = row.get('ph_maximum', '').strip()
            if textures or ph_min:
                usda[sci] = {
                    'texture': ', '.join(textures) if textures else '',
                    'ph_min': float(ph_min) if ph_min else 0,
                    'ph_max': float(ph_max) if ph_max else 0,
                }

    print(f"  USDA soil records: {len(usda)}", flush=True)

    # Match
    our = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our:
        sci = p['scientific'].lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    stmts = []
    stats = {'matched': 0, 'texture': 0, 'ph': 0}

    for sci, data in usda.items():
        pid = our_by_name.get(sci)
        if not pid:
            parts = sci.split()
            if len(parts) >= 2:
                pid = our_by_name.get(' '.join(parts[:2]))
        if not pid:
            continue

        stats['matched'] += 1

        if not dry_run:
            if data['texture']:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda_soil', 'texture', ?, datetime('now'))",
                    [pid, data['texture']]
                ))
                stmts.append(("UPDATE care SET soil_types = ? WHERE plant_id = ? AND (soil_types IS NULL OR soil_types = '')",
                              [f"Adapted to: {data['texture']}", pid]))
                stats['texture'] += 1

            if data['ph_min'] > 0:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda_soil', 'ph_range', ?, datetime('now'))",
                    [pid, f"{data['ph_min']}-{data['ph_max']}"]
                ))
                stmts.append(("UPDATE care SET soil_ph_min = ?, soil_ph_max = ? WHERE plant_id = ? AND (soil_ph_min IS NULL OR soil_ph_min = 0)",
                              [data['ph_min'], data['ph_max'], pid]))
                stats['ph'] += 1

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched: {stats['matched']}, texture: {stats['texture']}, pH: {stats['ph']}", flush=True)


def step2_lifeform_soil(dry_run=False):
    """Apply lifeform defaults for ALL empty soil_types."""
    print(f"\n=== STEP 2: Lifeform soil defaults ===", flush=True)

    plants = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.soil_types IS NULL OR c.soil_types = '')
    """)
    print(f"  Plants without soil: {len(plants)}", flush=True)

    stmts = []
    stats = {'filled': 0, 'no_default': 0}

    for i, plant in enumerate(plants):
        preset = plant.get('preset') or ''
        defaults = LIFEFORM_SOIL.get(preset)

        if not defaults:
            stats['no_default'] += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'soil_no_default', ?, datetime('now'))",
                    [plant['plant_id'], f'preset={preset}, no soil default']
                ))
            continue

        stats['filled'] += 1
        if not dry_run:
            stmts.append(("UPDATE care SET soil_types = ? WHERE plant_id = ? AND (soil_types IS NULL OR soil_types = '')",
                          [defaults['soil'], plant['plant_id']]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'lifeform_soil_default', 'soil_types', ?, datetime('now'))",
                [plant['plant_id'], f"{preset}→{defaults['soil'][:50]}"]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(plants)}] filled={stats['filled']} no_default={stats['no_default']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Filled: {stats['filled']}, no default: {stats['no_default']}", flush=True)


def step3_lifeform_repot(dry_run=False):
    """Apply lifeform defaults for ALL empty repot_frequency + repot_signs."""
    print(f"\n=== STEP 3: Lifeform repot defaults ===", flush=True)

    plants = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.repot_frequency IS NULL OR c.repot_frequency = '')
    """)
    print(f"  Plants without repot: {len(plants)}", flush=True)

    stmts = []
    filled = 0

    for i, plant in enumerate(plants):
        preset = plant.get('preset') or ''
        defaults = LIFEFORM_SOIL.get(preset)
        if not defaults:
            continue

        filled += 1
        if not dry_run:
            stmts.append(("UPDATE care SET repot_frequency = ? WHERE plant_id = ? AND (repot_frequency IS NULL OR repot_frequency = '')",
                          [defaults['repot'], plant['plant_id']]))
            stmts.append(("UPDATE care SET repot_signs = ? WHERE plant_id = ? AND (repot_signs IS NULL OR repot_signs = '')",
                          [defaults['signs'], plant['plant_id']]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'lifeform_soil_default', 'repot', ?, datetime('now'))",
                [plant['plant_id'], f"{preset}→{defaults['repot'][:40]}"]
            ))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(plants)}] filled={filled}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Filled: {filled}", flush=True)


def step4_lifeform_ph(dry_run=False):
    """Apply lifeform pH defaults for ALL empty soil_ph."""
    print(f"\n=== STEP 4: Lifeform pH defaults ===", flush=True)

    plants = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.soil_ph_min IS NULL OR c.soil_ph_min = 0)
    """)
    print(f"  Plants without pH: {len(plants)}", flush=True)

    stmts = []
    filled = 0

    for plant in plants:
        preset = plant.get('preset') or ''
        defaults = LIFEFORM_SOIL.get(preset)
        if not defaults:
            continue

        filled += 1
        if not dry_run:
            stmts.append(("UPDATE care SET soil_ph_min = ?, soil_ph_max = ? WHERE plant_id = ? AND (soil_ph_min IS NULL OR soil_ph_min = 0)",
                          [defaults['ph_min'], defaults['ph_max'], plant['plant_id']]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'lifeform_soil_default', 'ph', ?, datetime('now'))",
                [plant['plant_id'], f"{preset}→pH {defaults['ph_min']}-{defaults['ph_max']}"]
            ))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Filled: {filled}", flush=True)


def show_results():
    """Show soil stats."""
    print(f"\n=== SOIL STATUS ===", flush=True)
    total = 20261
    soil = turso_query("SELECT COUNT(*) as c FROM care WHERE soil_types IS NOT NULL AND soil_types != ''")[0]['c']
    ph = turso_query("SELECT COUNT(*) as c FROM care WHERE soil_ph_min > 0")[0]['c']
    repot = turso_query("SELECT COUNT(*) as c FROM care WHERE repot_frequency IS NOT NULL AND repot_frequency != ''")[0]['c']
    print(f"  soil_types:      {soil:>6} / {total} ({soil*100//total}%)", flush=True)
    print(f"  soil_ph:         {ph:>6} / {total} ({ph*100//total}%)", flush=True)
    print(f"  repot_frequency: {repot:>6} / {total} ({repot*100//total}%)", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    step1_usda(dry_run)
    step2_lifeform_soil(dry_run)
    step3_lifeform_repot(dry_run)
    step4_lifeform_ph(dry_run)
    show_results()
