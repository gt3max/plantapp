"""
Open Plantbook — fetch lux, soil moisture, temp, humidity for indoor plants.
200 requests/day. Source: open.plantbook.io

Rules:
- Only indoor plants with Medium demand (priority)
- Round-robin by lifeform type
- 1 request per plant (detail endpoint)
- All data → source_data as source='openplantbook'
- Compare with existing → flag conflicts
- Never overwrite care directly

Usage:
    python3 openplantbook_check.py              # run 200 plants
    python3 openplantbook_check.py --dry-run    # preview
    python3 openplantbook_check.py --limit 50
"""
import urllib.request
import urllib.parse
import json
import time
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

TOKEN = os.environ.get('OPENPLANTBOOK_TOKEN', '')
API_BASE = 'https://open.plantbook.io/api/v1'
MAX_DAILY = 200

LIFEFORM_TYPES = ['tree','perennial','annual','subshrub','herb','shrub','bulb','climber','tropical','epiphyte','succulent','fern','aquatic']


def fetch_plant(scientific):
    """Fetch plant data from Open Plantbook. Returns dict or None (rate limited) or {} (not found)."""
    pid_encoded = urllib.parse.quote(scientific.lower())
    url = f'{API_BASE}/plant/detail/{pid_encoded}/'
    req = urllib.request.Request(url, headers={'Authorization': f'Token {TOKEN}', 'User-Agent': 'PlantApp/1.0 (plantapp.pro)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}  # not found
        if e.code == 429:
            return None  # rate limited
        return {}
    except:
        return {}


def compare_light(lux_min, lux_max, our_light):
    """Compare Open Plantbook lux with our light_preferred."""
    mid = (lux_min + lux_max) / 2
    if mid > 30000:
        opb_cat = 'Full sun'
    elif mid > 10000:
        opb_cat = 'Part sun'
    elif mid > 2500:
        opb_cat = 'Part sun'
    else:
        opb_cat = 'Shade'

    our_cat = 'Full sun' if 'full sun' in our_light.lower() else ('Part sun' if 'part sun' in our_light.lower() else our_light)
    return opb_cat == our_cat, opb_cat, our_cat


def compare_moisture(moist_min, moist_max, our_demand):
    """Compare soil moisture with our water_demand."""
    mid = (moist_min + moist_max) / 2
    if mid > 50:
        opb_demand = 'High'
    elif mid > 30:
        opb_demand = 'Medium'
    elif mid > 15:
        opb_demand = 'Low'
    else:
        opb_demand = 'Minimum'

    return opb_demand == our_demand, opb_demand, our_demand


def run(limit=200, dry_run=False):
    # Get candidates: indoor + Medium demand + no openplantbook data yet
    already = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = ?", ['openplantbook'])
    already_set = set(r['plant_id'] for r in already)

    candidates = []
    for typ in LIFEFORM_TYPES:
        per_type = limit // len(LIFEFORM_TYPES) + 1
        rows = turso_query("""
            SELECT p.plant_id, p.scientific, p.preset, c.water_demand, c.light_preferred
            FROM plants p JOIN care c ON p.plant_id = c.plant_id
            WHERE p.indoor = 1 AND p.preset = ?
            AND p.scientific IS NOT NULL
            ORDER BY LENGTH(COALESCE(p.description,'')) DESC
            LIMIT ?
        """, [typ, per_type * 3])  # fetch extra to filter

        added = 0
        for r in rows:
            if r['plant_id'] in already_set:
                continue
            if added >= per_type:
                break
            candidates.append(r)
            added += 1

    candidates = candidates[:limit]
    print(f"[openplantbook] Candidates: {len(candidates)} plants", flush=True)

    if dry_run:
        for c in candidates[:20]:
            print(f"  {c['plant_id']:35s} | {c['preset']:12s} | demand={c['water_demand']}", flush=True)
        return

    stats = {'found': 0, 'not_found': 0, 'light_match': 0, 'light_conflict': 0, 'demand_match': 0, 'demand_conflict': 0}
    requests_made = 0

    for i, c in enumerate(candidates):
        data = fetch_plant(c['scientific'])
        requests_made += 1

        if data is None:
            print(f"  [{i+1}] Rate limited. Stopping.", flush=True)
            break

        if not data or not data.get('display_pid'):
            stats['not_found'] += 1
            time.sleep(1)
            continue

        stats['found'] += 1

        # Extract fields
        fields = {}
        for key in ['min_light_lux', 'max_light_lux', 'min_soil_moist', 'max_soil_moist',
                     'min_temp', 'max_temp', 'min_env_humid', 'max_env_humid']:
            val = data.get(key)
            if val is not None:
                fields[key] = str(val)

        if data.get('display_pid'):
            fields['display_pid'] = data['display_pid']

        # Store raw data in source_data (always)
        store_source_data(c['plant_id'], 'openplantbook', fields)

        # Compare light
        lux_min = data.get('min_light_lux', 0) or 0
        lux_max = data.get('max_light_lux', 0) or 0
        if lux_min and lux_max and c.get('light_preferred'):
            match, opb, ours = compare_light(lux_min, lux_max, c['light_preferred'])
            if match:
                stats['light_match'] += 1
            else:
                stats['light_conflict'] += 1
                store_source_data(c['plant_id'], 'conflict', {'openplantbook_vs_light': f'OPB={opb} (lux {lux_min}-{lux_max}), ours={ours}'})

        # Compare moisture/demand
        moist_min = data.get('min_soil_moist', 0) or 0
        moist_max = data.get('max_soil_moist', 0) or 0
        if moist_min and moist_max and c.get('water_demand'):
            match, opb, ours = compare_moisture(moist_min, moist_max, c['water_demand'])
            if match:
                stats['demand_match'] += 1
            else:
                stats['demand_conflict'] += 1
                store_source_data(c['plant_id'], 'conflict', {'openplantbook_vs_demand': f'OPB={opb} (moist {moist_min}-{moist_max}%), ours={ours}'})

        # Fill empty care fields from Open Plantbook
        pid = c['plant_id']
        care_row = turso_query("SELECT * FROM care WHERE plant_id = ?", [pid])
        if care_row:
            cr = care_row[0]
            fill_stmts = []
            # PPFD from lux (1 lux ≈ 0.015 µmol for sunlight)
            if lux_min and lux_max and not (cr.get('ppfd_min') or 0):
                ppfd_min = round(lux_min * 0.015)
                ppfd_max = round(lux_max * 0.015)
                fill_stmts.append(("UPDATE care SET ppfd_min = ?, ppfd_max = ? WHERE plant_id = ?", [ppfd_min, ppfd_max, pid]))
            # Humidity min pct
            env_min = data.get('min_env_humid') or 0
            env_max = data.get('max_env_humid') or 0
            if env_min and not (cr.get('humidity_min_pct') or 0):
                fill_stmts.append(("UPDATE care SET humidity_min_pct = ? WHERE plant_id = ?", [env_min, pid]))
            # Temperature
            temp_min = data.get('min_temp')
            temp_max = data.get('max_temp')
            if temp_min is not None and not (cr.get('temp_min_c') or 0):
                fill_stmts.append(("UPDATE care SET temp_min_c = ? WHERE plant_id = ?", [temp_min, pid]))
            if temp_max is not None and not (cr.get('temp_max_c') or 0):
                fill_stmts.append(("UPDATE care SET temp_max_c = ? WHERE plant_id = ?", [temp_max, pid]))
            if fill_stmts:
                turso_batch(fill_stmts)
                stats['filled'] = stats.get('filled', 0) + len(fill_stmts)

        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(candidates)}] found={stats['found']} miss={stats['not_found']} l_ok={stats['light_match']} l_conflict={stats['light_conflict']} d_ok={stats['demand_match']} d_conflict={stats['demand_conflict']}", flush=True)

        time.sleep(1)

    print(f"\n[openplantbook] Done: {requests_made} requests", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)


if __name__ == '__main__':
    limit = MAX_DAILY
    dry_run = '--dry-run' in sys.argv
    for arg in sys.argv[1:]:
        if arg.isdigit():
            limit = int(arg)
    run(limit=limit, dry_run=dry_run)
