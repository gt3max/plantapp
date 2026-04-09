"""
Verify care data against PFAF — read-only comparison.
Writes ONLY to source_data (source='pfaf_verify'). NEVER modifies care table.

Compares 5 sections:
1. moisture vs water_demand
2. shade vs light_preferred
3. known_hazards vs toxic_to_humans
4. habit vs lifecycle
5. height vs height_max_cm

Results: confirmed / conflict / ambiguous per field.

Usage:
    python3 pfaf_verify.py              # full run
    python3 pfaf_verify.py --dry-run    # preview only
"""
import sys
import os
import json

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


# --- Moisture → Water demand ---
# Based on actual data distribution in our DB
MOISTURE_MAP = {
    'D':     {'primary': 'Low',    'also_ok': set()},
    'DM':    {'primary': 'Low',    'also_ok': {'Medium'}},  # ambiguous: 48% vs 45%
    'M':     {'primary': 'Medium', 'also_ok': {'Low'}},     # 63% Medium, 25% Low
    'MWe':   {'primary': 'High',   'also_ok': {'Medium'}},  # 54% High, 34% Medium
    'We':    {'primary': 'High',   'also_ok': set()},
    'Wa':    {'primary': 'High',   'also_ok': set()},
    'WeWa':  {'primary': 'High',   'also_ok': set()},
    'MWeWa': {'primary': 'High',   'also_ok': set()},
    'DMWe':  {'primary': 'Medium', 'also_ok': {'Low', 'High'}},  # wide range
}

# --- Shade → Light ---
SHADE_MAP = {
    'N':   {'primary': 'Full sun',              'also_ok': {'Part sun', 'Bright indirect light'}},
    'SN':  {'primary': 'Part sun',              'also_ok': {'Full sun', 'Bright indirect light'}},
    'S':   {'primary': 'Part sun',              'also_ok': {'Bright indirect light'}},
    'FS':  {'primary': 'Part sun',              'also_ok': {'Shade', 'Bright indirect light'}},
    'FSN': {'primary': 'Part sun',              'also_ok': {'Full sun', 'Bright indirect light'}},
    'F':   {'primary': 'Shade',                 'also_ok': set()},
    'NS':  {'primary': 'Part sun',              'also_ok': {'Full sun'}},
}

# --- Habit → Lifecycle ---
HABIT_LIFECYCLE = {
    'annual':            {'primary': 'annual',    'also_ok': set()},
    'biennial':          {'primary': 'biennial',  'also_ok': {'annual'}},
    'perennial':         {'primary': 'perennial', 'also_ok': set()},
    'tree':              {'primary': 'perennial', 'also_ok': {'woody'}},
    'shrub':             {'primary': 'perennial', 'also_ok': {'woody'}},
    'climber':           {'primary': 'perennial', 'also_ok': set()},
    'bulb':              {'primary': 'bulb',      'also_ok': {'perennial'}},
    'fern':              {'primary': 'perennial', 'also_ok': set()},
    'bamboo':            {'primary': 'perennial', 'also_ok': set()},
    'perennial climber': {'primary': 'perennial', 'also_ok': set()},
    'annual/biennial':   {'primary': 'annual',    'also_ok': {'biennial'}},
    'annual/perennial':  {'primary': 'perennial', 'also_ok': {'annual'}},
    'corm':              {'primary': 'bulb',      'also_ok': {'perennial'}},
}

# Toxicity keywords (same strict set as pfaf_enrich)
TOXIC_WORDS = ['toxic', 'poison', 'poisonous', 'fatal', 'lethal', 'death']
EXCLUDE_WORDS = ['irritant', 'skin contact', 'stinging', 'thorns', 'spines',
                 'no records of toxicity', 'although no specific']


def compare_field(pfaf_val, care_val, mapping):
    """Compare using mapping dict with primary + also_ok. Returns confirmed/conflict/ambiguous."""
    if not pfaf_val or pfaf_val not in mapping:
        return 'no_map', f'pfaf={pfaf_val} not in mapping'

    m = mapping[pfaf_val]
    expected = m['primary']
    also_ok = m['also_ok']

    if care_val == expected:
        return 'confirmed', f'pfaf={pfaf_val}→{expected}, care={care_val}'
    elif care_val in also_ok:
        return 'ambiguous', f'pfaf={pfaf_val}→{expected}, care={care_val} (acceptable)'
    else:
        return 'conflict', f'pfaf={pfaf_val}→{expected}, care={care_val}'


def check_toxicity(hazards_text, care_toxic):
    """Compare PFAF known_hazards with toxic_to_humans (0/1/NULL)."""
    if not hazards_text:
        return 'no_data', ''

    lower = hazards_text.lower()

    has_toxic = any(w in lower for w in TOXIC_WORDS)
    is_excluded = any(w in lower for w in EXCLUDE_WORDS) and not has_toxic

    if is_excluded or not has_toxic:
        # PFAF doesn't indicate toxicity — nothing to verify
        return 'no_data', f'pfaf=not clearly toxic'

    # PFAF says toxic
    if care_toxic == 1:
        return 'confirmed', f'pfaf=toxic, care=1'
    elif care_toxic == 0:
        return 'conflict', f'pfaf=toxic, care=0 (marked safe but PFAF says toxic)'
    else:
        return 'conflict', f'pfaf=toxic, care=NULL (not marked)'


def check_height(pfaf_height_m, care_height_cm):
    """Compare heights with ±30% tolerance."""
    try:
        pfaf_cm = float(pfaf_height_m) * 100
        care_cm = float(care_height_cm)
    except (ValueError, TypeError):
        return 'no_data', ''

    if pfaf_cm <= 0 or care_cm <= 0:
        return 'no_data', ''

    ratio = pfaf_cm / care_cm
    if 0.7 <= ratio <= 1.3:
        return 'confirmed', f'pfaf={pfaf_cm:.0f}cm, care={care_cm:.0f}cm (ratio={ratio:.2f})'
    else:
        return 'conflict', f'pfaf={pfaf_cm:.0f}cm, care={care_cm:.0f}cm (ratio={ratio:.2f})'


def run(dry_run=False):
    # Load all PFAF raw data
    print(f"[pfaf_verify] Loading PFAF data...", flush=True)
    pfaf_raw = turso_query("SELECT plant_id, field, value FROM source_data WHERE source = 'pfaf'")

    plants_data = {}
    for r in pfaf_raw:
        pid = r['plant_id']
        if pid not in plants_data:
            plants_data[pid] = {}
        plants_data[pid][r['field']] = r['value']

    plant_ids = list(plants_data.keys())
    print(f"[pfaf_verify] {len(plant_ids)} plants with PFAF data", flush=True)

    # Batch load care
    care_data = {}
    for i in range(0, len(plant_ids), 200):
        batch = plant_ids[i:i+200]
        placeholders = ','.join(['?' for _ in batch])
        rows = turso_query(f"""
            SELECT plant_id, water_demand, light_preferred, toxic_to_humans,
                   lifecycle, height_max_cm
            FROM care WHERE plant_id IN ({placeholders})
        """, batch)
        for r in rows:
            care_data[r['plant_id']] = r

    print(f"[pfaf_verify] Loaded care for {len(care_data)} plants", flush=True)

    stmts = []
    stats = {}
    for section in ['water', 'light', 'toxicity', 'lifecycle', 'height']:
        for result in ['confirmed', 'conflict', 'ambiguous', 'no_data', 'no_map']:
            stats[f'{section}_{result}'] = 0

    for i, pid in enumerate(plant_ids):
        pfaf = plants_data[pid]
        care = care_data.get(pid)
        if not care:
            continue

        # --- 1. Moisture vs water_demand ---
        moisture = pfaf.get('moisture', '')
        demand = care.get('water_demand') or ''
        if moisture and demand:
            result, detail = compare_field(moisture, demand, MOISTURE_MAP)
            stats[f'water_{result}'] += 1
            if not dry_run:
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'water_demand_result', ?, datetime('now'))", [pid, result]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'water_demand_detail', ?, datetime('now'))", [pid, detail]))

        # --- 2. Shade vs light_preferred ---
        shade = pfaf.get('shade', '')
        light = care.get('light_preferred') or ''
        if shade and light:
            result, detail = compare_field(shade, light, SHADE_MAP)
            stats[f'light_{result}'] += 1
            if not dry_run:
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'light_result', ?, datetime('now'))", [pid, result]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'light_detail', ?, datetime('now'))", [pid, detail]))

        # --- 3. Toxicity ---
        hazards = pfaf.get('known_hazards', '')
        toxic_h = care.get('toxic_to_humans')
        if hazards:
            result, detail = check_toxicity(hazards, toxic_h)
            stats[f'toxicity_{result}'] += 1
            if result != 'no_data' and not dry_run:
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'toxicity_result', ?, datetime('now'))", [pid, result]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'toxicity_detail', ?, datetime('now'))", [pid, detail]))

        # --- 4. Lifecycle ---
        habit = (pfaf.get('habit') or '').lower().strip()
        lifecycle = (care.get('lifecycle') or '').lower().strip()
        if habit and lifecycle:
            result, detail = compare_field(habit, lifecycle, HABIT_LIFECYCLE)
            stats[f'lifecycle_{result}'] += 1
            if not dry_run:
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'lifecycle_result', ?, datetime('now'))", [pid, result]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'lifecycle_detail', ?, datetime('now'))", [pid, detail]))

        # --- 5. Height ---
        pfaf_h = pfaf.get('height', '')
        care_h = care.get('height_max_cm')
        if pfaf_h and care_h:
            result, detail = check_height(pfaf_h, care_h)
            stats[f'height_{result}'] += 1
            if result != 'no_data' and not dry_run:
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'height_result', ?, datetime('now'))", [pid, result]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_verify', 'height_detail', ?, datetime('now'))", [pid, detail]))

        if len(stmts) >= 100:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(plant_ids)}]", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    # Print results
    print(f"\n[pfaf_verify] Results:", flush=True)
    for section in ['water', 'light', 'toxicity', 'lifecycle', 'height']:
        conf = stats.get(f'{section}_confirmed', 0)
        confl = stats.get(f'{section}_conflict', 0)
        amb = stats.get(f'{section}_ambiguous', 0)
        total = conf + confl + amb
        if total > 0:
            print(f"\n  {section}:", flush=True)
            print(f"    confirmed:  {conf:>5} ({conf*100//total}%)", flush=True)
            print(f"    conflict:   {confl:>5} ({confl*100//total}%)", flush=True)
            print(f"    ambiguous:  {amb:>5} ({amb*100//total}%)", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
