"""
Polish watering v5 — family heuristics + PFAF+climate + MiFloraDB.

Strategy 1: Family patterns (Poaceae→High, Fabaceae→Low, etc.)
Strategy 2: PFAF moisture + climate disambiguation
Strategy 3: MiFloraDB non-default soil_moist → Low

Only Medium plants. Featured 32 protected. Source attribution everywhere.

Usage:
    python3 polish_watering_v5.py --dry-run
    python3 polish_watering_v5.py
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

from turso_sync import turso_query, turso_batch

FEATURED_FILE = '/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart'

# Family → water demand (only families with ≥60% pattern among non-Medium members)
FAMILY_WATERING = {
    # Strong signals
    'Poaceae': 'High',       # 64% High among non-Medium grasses
    'Fabaceae': 'Low',       # 89% Low among non-Medium legumes
    'Cactaceae': 'Low',      # 99% Low
    'Crassulaceae': 'Low',   # 99% Low (succulents)
    'Aizoaceae': 'Low',      # 99% Low (succulents)
    'Cyperaceae': 'High',    # Sedges = wet habitats
    'Juncaceae': 'High',     # Rushes = wet habitats
    'Nymphaeaceae': 'High',  # Water lilies
    'Hydrocharitaceae': 'High',  # Aquatic
    'Typhaceae': 'High',     # Cattails
    # Moderate signals
    'Asteraceae': 'Low',     # 73% Low among non-Medium
    'Lamiaceae': 'Low',      # Mediterranean herbs, mostly drought tolerant
    'Apiaceae': 'Low',       # Most herbs are moderate-low
    'Boraginaceae': 'Low',   # Mostly dry-adapted
    'Ericaceae': 'Low',      # Heath family, adapted to poor soils
    'Proteaceae': 'Low',     # Adapted to poor/dry soils
    'Myrtaceae': 'Low',      # Eucalyptus etc, drought adapted
}

# PFAF moisture + climate → demand
PFAF_CLIMATE_RULES = {
    # PFAF=DM (Dry-Moist)
    ('DM', 'desert or dry shrubland'): 'Low',
    ('DM', 'seasonally dry tropical'): 'Low',
    ('DM', 'subalpine or subarctic'): 'Low',
    ('DM', 'temperate'): 'Low',
    # PFAF=M (Moist) — only shift with extreme climates
    ('M', 'desert or dry shrubland'): 'Low',
    ('M', 'wet tropical'): 'High',
    # PFAF=MWe (Moist-Wet)
    ('MWe', 'temperate'): 'High',
    ('MWe', 'wet tropical'): 'High',
    ('MWe', 'subtropical'): 'High',
}


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            return set(re.findall(r"plantIdStr: '([^']+)'", f.read()))
    except:
        return set()


def run(dry_run=False):
    featured = get_featured_ids()
    print(f"[watering_v5] Protected: {len(featured)} featured", flush=True)

    # Get all Medium plants with family + climate
    medium = turso_query("""
        SELECT c.plant_id, p.family, p.climate, p.preset
        FROM care c JOIN plants p ON c.plant_id = p.plant_id
        WHERE c.water_demand = 'Medium'
    """)
    print(f"[watering_v5] Medium plants: {len(medium)}", flush=True)

    # Pre-load PFAF moisture
    pfaf_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf' AND field = 'moisture'")
    pfaf_by_pid = {r['plant_id']: r['value'].strip().upper() for r in pfaf_data}

    # Pre-load MiFloraDB min_soil_moist
    mfdb_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'xiaomi_mifloradb' AND field = 'min_soil_moist'")
    mfdb_by_pid = {}
    for r in mfdb_data:
        try:
            mfdb_by_pid[r['plant_id']] = float(r['value'])
        except:
            pass

    stmts = []
    stats = {
        'family': 0, 'pfaf_climate': 0, 'mifloradb': 0,
        'stays': 0, 'no_data': 0, 'protected': 0,
        'to_low': 0, 'to_high': 0,
    }

    for i, plant in enumerate(medium):
        pid = plant['plant_id']
        family = plant.get('family') or ''
        climate = (plant.get('climate') or '').lower()

        if pid in featured:
            stats['protected'] += 1
            continue

        new_demand = None
        source = None
        detail = ''

        # Strategy 1: Family heuristics
        if family in FAMILY_WATERING:
            new_demand = FAMILY_WATERING[family]
            source = 'family_watering'
            detail = f'family={family}→{new_demand}'
            stats['family'] += 1

        # Strategy 2: PFAF + climate (override family if more specific)
        if not new_demand:
            pfaf_m = pfaf_by_pid.get(pid, '')
            if pfaf_m and climate:
                for (pm, cl), demand in PFAF_CLIMATE_RULES.items():
                    if pfaf_m == pm and cl in climate:
                        new_demand = demand
                        source = 'pfaf_climate_watering'
                        detail = f'pfaf={pfaf_m}+climate={climate}→{demand}'
                        stats['pfaf_climate'] += 1
                        break

        # Strategy 3: MiFloraDB non-default
        if not new_demand:
            mfdb_val = mfdb_by_pid.get(pid)
            if mfdb_val is not None and mfdb_val != 15.0 and mfdb_val <= 20.0:
                new_demand = 'Low'
                source = 'mifloradb_watering'
                detail = f'min_soil_moist={mfdb_val}→Low'
                stats['mifloradb'] += 1

        if new_demand:
            if new_demand == 'Low':
                stats['to_low'] += 1
            else:
                stats['to_high'] += 1

            if not dry_run:
                stmts.append(("UPDATE care SET water_demand = ? WHERE plant_id = ? AND water_demand = 'Medium'",
                              [new_demand, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'watering_changed', ?, datetime('now'))",
                    [pid, source, detail]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []
        else:
            stats['stays'] += 1

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(medium)}] family={stats['family']} pfaf_cl={stats['pfaf_climate']} mfdb={stats['mifloradb']} low={stats['to_low']} high={stats['to_high']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    total_moved = stats['to_low'] + stats['to_high']
    print(f"\n[watering_v5] Done:", flush=True)
    print(f"  Family:       {stats['family']}", flush=True)
    print(f"  PFAF+climate: {stats['pfaf_climate']}", flush=True)
    print(f"  MiFloraDB:    {stats['mifloradb']}", flush=True)
    print(f"  → Low:        {stats['to_low']}", flush=True)
    print(f"  → High:       {stats['to_high']}", flush=True)
    print(f"  Total moved:  {total_moved}", flush=True)
    print(f"  Stays Medium: {stats['stays']}", flush=True)
    print(f"  Protected:    {stats['protected']}", flush=True)

    if not dry_run:
        dist = turso_query("SELECT water_demand, COUNT(*) as cnt FROM care GROUP BY water_demand ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['water_demand'] or '(empty)':<15s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
