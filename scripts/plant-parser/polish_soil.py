"""
Polish soil — reconcile soil sources, fill repot_frequency, fix pH.
Sources: NC State > lifeform default > existing care data.

Rules:
- Don't overwrite existing good soil_types
- Fill repot_frequency from lifeform if empty
- Fix pH 0.0 → from NC State or lifeform default
- Record all sources in source_data
- Flag conflicts

Usage:
    python3 polish_soil.py --featured    # 56 featured only
    python3 polish_soil.py --with-photos # plants with photos (~1800)
"""
import sys
import os
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

from turso_sync import turso_query, turso_batch, store_source_data

# Lifeform → default soil data
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
}


def polish_soil(mode='featured'):
    if mode == 'featured':
        with open('/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart') as f:
            text = f.read()
        plant_ids = re.findall(r"plantIdStr: '([^']+)'", text)
    elif mode == 'with-photos':
        rows = turso_query("SELECT DISTINCT plant_id FROM plant_images")
        plant_ids = [r['plant_id'] for r in rows]
    else:
        plant_ids = []

    print(f"[polish_soil] Processing {len(plant_ids)} plants ({mode})...", flush=True)

    stmts = []
    stats = {'ph_fixed': 0, 'repot_filled': 0, 'signs_filled': 0, 'conflict': 0, 'already_ok': 0}

    for pid in plant_ids:
        # Get current care data
        care = turso_query("SELECT soil_types, soil_ph_min, soil_ph_max, repot_frequency, repot_signs FROM care WHERE plant_id = ?", [pid])
        if not care:
            continue
        c = care[0]

        # Get plant lifeform
        plant = turso_query("SELECT preset FROM plants WHERE plant_id = ?", [pid])
        lifeform = plant[0]['preset'] if plant else 'perennial'
        defaults = LIFEFORM_SOIL.get(lifeform, LIFEFORM_SOIL['perennial'])

        # Get NC State data
        ncstate = turso_query("SELECT field, value FROM source_data WHERE plant_id = ? AND source = ? AND (field LIKE ? OR field LIKE ?)",
                              [pid, 'ncstate', '%soil%', '%ph%'])
        nc = {r['field']: r['value'] for r in ncstate}

        # --- Fix pH ---
        ph_min = c.get('soil_ph_min') or 0
        ph_max = c.get('soil_ph_max') or 0

        if not ph_min or ph_min == 0 or ph_min == ph_max:
            # Try NC State
            nc_ph = nc.get('soil_ph', '')
            if nc_ph:
                nums = re.findall(r'(\d+\.?\d*)', nc_ph)
                if len(nums) >= 2:
                    new_min, new_max = float(nums[0]), float(nums[1])
                elif len(nums) == 1:
                    new_min = new_max = float(nums[0])
                else:
                    new_min, new_max = defaults['ph_min'], defaults['ph_max']
                source = 'ncstate'
            else:
                new_min, new_max = defaults['ph_min'], defaults['ph_max']
                source = 'lifeform_default'

            if new_min > 0:
                stmts.append(("UPDATE care SET soil_ph_min = ?, soil_ph_max = ? WHERE plant_id = ?",
                              [new_min, new_max, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'soil_reconcile', 'ph_source', ?, datetime('now'))",
                    [pid, source]
                ))
                stats['ph_fixed'] += 1

        # --- Fill repot_frequency ---
        if not c.get('repot_frequency') or c.get('repot_frequency') == '':
            repot = defaults['repot']
            stmts.append(("UPDATE care SET repot_frequency = ? WHERE plant_id = ? AND (repot_frequency IS NULL OR repot_frequency = '')",
                          [repot, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'soil_reconcile', 'repot_source', 'lifeform_default', datetime('now'))",
                [pid]
            ))
            stats['repot_filled'] += 1

        # --- Fill repot_signs ---
        if not c.get('repot_signs') or c.get('repot_signs') == '':
            signs = defaults['signs']
            stmts.append(("UPDATE care SET repot_signs = ? WHERE plant_id = ? AND (repot_signs IS NULL OR repot_signs = '')",
                          [signs, pid]))
            stats['signs_filled'] += 1

        # --- Check soil_types conflict ---
        nc_soil = nc.get('soil_types', '')
        current_soil = c.get('soil_types') or ''
        if nc_soil and current_soil and nc_soil.lower() not in current_soil.lower() and current_soil.lower() not in nc_soil.lower():
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'conflict', 'soil_types_conflict', ?, datetime('now'))",
                [pid, f"NCState={nc_soil}, care={current_soil[:50]}"]
            ))
            stats['conflict'] += 1
        else:
            stats['already_ok'] += 1

        # Batch write
        if len(stmts) >= 40:
            turso_batch(stmts)
            stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"\n[polish_soil] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    # Show sample results
    print(f"\nSample results:", flush=True)
    for pid in plant_ids[:10]:
        r = turso_query("SELECT soil_types, soil_ph_min, soil_ph_max, repot_frequency FROM care WHERE plant_id = ?", [pid])
        if r:
            c = r[0]
            print(f"  {pid:30s} | soil={str(c.get('soil_types',''))[:30]:30s} | pH={c.get('soil_ph_min','?')}-{c.get('soil_ph_max','?')} | repot={c.get('repot_frequency','?')}", flush=True)


if __name__ == '__main__':
    if '--featured' in sys.argv:
        polish_soil(mode='featured')
    elif '--with-photos' in sys.argv:
        polish_soil(mode='with-photos')
    else:
        polish_soil(mode='featured')
