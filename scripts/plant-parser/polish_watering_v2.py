"""
Polish watering v2 — reclassify Medium demand using multi-source voting.

Sources (weighted):
  Ellenberg F (weight 3): F≤3→Low, F=4→Low(2), F=5-6→Medium, F=7-8→High, F≥9→High(4)
  PFAF moisture (weight 2): D→Low, DM→Low(1), M→Medium, MWe→High(1), We→High
  MiFloraDB (weight 1): >20% real data only (15%=default, skip)
  Lifeform+climate (weight 1): succulent→Low, aquatic→High, etc.
  Open Plantbook (weight 1): min/max soil moisture

Only processes plants with water_demand = 'Medium'.
Protected: 28 featured plants (already verified with Planta).

Usage:
    python3 polish_watering_v2.py              # full run
    python3 polish_watering_v2.py --dry-run    # preview
    python3 polish_watering_v2.py --with-photos # only plants with photos
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

# Protected plants (verified with Planta)
FEATURED_FILE = '/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart'


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            text = f.read()
        return set(re.findall(r"plantIdStr: '([^']+)'", text))
    except:
        return set()


def get_votes(pid, care, plant, source_data):
    """Collect weighted votes from all sources. Returns (low_score, high_score, votes_detail)."""
    low = 0
    high = 0
    votes = []

    # 1. Ellenberg F (weight 3)
    ef = care.get('ellenberg_f') or 0
    if ef > 0:
        if ef <= 3:
            low += 3
            votes.append(f'ellenberg_f={ef}→Low(3)')
        elif ef == 4:
            low += 2
            votes.append(f'ellenberg_f={ef}→Low(2)')
        elif ef <= 6:
            votes.append(f'ellenberg_f={ef}→Medium(0)')
        elif ef <= 8:
            high += 3
            votes.append(f'ellenberg_f={ef}→High(3)')
        else:
            high += 4
            votes.append(f'ellenberg_f={ef}→High(4)')

    # 2. PFAF moisture (weight 2)
    pfaf_m = ''
    for sd in source_data:
        if sd['source'] == 'pfaf' and sd['field'] == 'moisture':
            pfaf_m = sd['value']
            break

    if pfaf_m:
        pfaf_lower = pfaf_m.strip().upper()
        if pfaf_lower == 'D':
            low += 2
            votes.append(f'pfaf={pfaf_m}→Low(2)')
        elif pfaf_lower == 'DM':
            low += 1
            votes.append(f'pfaf={pfaf_m}→Low(1)')
        elif pfaf_lower == 'M':
            votes.append(f'pfaf={pfaf_m}→Medium(0)')
        elif pfaf_lower in ('MWE', 'MWe'):
            high += 1
            votes.append(f'pfaf={pfaf_m}→High(1)')
        elif pfaf_lower in ('WE', 'We'):
            high += 2
            votes.append(f'pfaf={pfaf_m}→High(2)')

    # 3. MiFloraDB (weight 1, skip defaults)
    for sd in source_data:
        if sd['source'] == 'mifloradb' and sd['field'] == 'min_soil_moist':
            try:
                moist = float(sd['value'])
                if moist > 20:  # Not default
                    if moist > 50:
                        high += 1
                        votes.append(f'mifloradb={moist}%→High(1)')
                    elif moist > 30:
                        votes.append(f'mifloradb={moist}%→Medium(0)')
                    else:
                        low += 1
                        votes.append(f'mifloradb={moist}%→Low(1)')
            except:
                pass
            break

    # 4. Open Plantbook (weight 1)
    for sd in source_data:
        if sd['source'] == 'openplantbook' and sd['field'] == 'min_soil_moist':
            try:
                moist = float(sd['value'])
                if moist > 50:
                    high += 1
                    votes.append(f'opb={moist}%→High(1)')
                elif moist < 20:
                    low += 1
                    votes.append(f'opb={moist}%→Low(1)')
                else:
                    votes.append(f'opb={moist}%→Medium(0)')
            except:
                pass
            break

    # 5. Lifeform + climate (weight 1)
    preset = plant.get('preset') or ''
    climate = plant.get('climate') or ''

    if preset == 'succulent':
        if 'desert' in climate.lower():
            low += 2
            votes.append(f'lifeform=succulent+desert→Low(2)')
        else:
            low += 1
            votes.append(f'lifeform=succulent→Low(1)')
    elif preset == 'aquatic':
        high += 2
        votes.append(f'lifeform=aquatic→High(2)')
    elif preset == 'epiphyte' and 'wet tropical' in climate.lower():
        high += 1
        votes.append(f'lifeform=epiphyte+wet_tropical→High(1)')
    elif preset in ('tree', 'shrub') and 'desert' in climate.lower():
        low += 1
        votes.append(f'lifeform={preset}+desert→Low(1)')

    return low, high, votes


def run(dry_run=False, with_photos=False):
    featured = get_featured_ids()
    print(f"[watering_v2] Protected featured: {len(featured)}", flush=True)

    # Get Medium plants
    if with_photos:
        medium_plants = turso_query("""
            SELECT c.plant_id, c.water_demand, c.ellenberg_f, p.preset, p.climate
            FROM care c JOIN plants p ON c.plant_id = p.plant_id
            JOIN plant_images pi ON c.plant_id = pi.plant_id
            WHERE c.water_demand = 'Medium'
            GROUP BY c.plant_id
        """)
    else:
        medium_plants = turso_query("""
            SELECT c.plant_id, c.water_demand, c.ellenberg_f, p.preset, p.climate
            FROM care c JOIN plants p ON c.plant_id = p.plant_id
            WHERE c.water_demand = 'Medium'
        """)

    print(f"[watering_v2] Medium plants: {len(medium_plants)}", flush=True)

    # Pre-fetch all relevant source_data
    print(f"[watering_v2] Loading source data...", flush=True)
    all_sd = turso_query("""
        SELECT plant_id, source, field, value FROM source_data
        WHERE (source = 'pfaf' AND field = 'moisture')
           OR (source = 'mifloradb' AND field = 'min_soil_moist')
           OR (source = 'openplantbook' AND field = 'min_soil_moist')
    """)

    # Group by plant_id
    sd_by_plant = {}
    for sd in all_sd:
        pid = sd['plant_id']
        if pid not in sd_by_plant:
            sd_by_plant[pid] = []
        sd_by_plant[pid].append(sd)

    print(f"[watering_v2] Source data loaded: {len(all_sd)} records", flush=True)

    stmts = []
    stats = {'to_low': 0, 'to_high': 0, 'to_minimum': 0, 'stays_medium': 0, 'no_data': 0, 'protected': 0}

    for i, plant in enumerate(medium_plants):
        pid = plant['plant_id']

        # Skip featured
        if pid in featured:
            stats['protected'] += 1
            continue

        care = {'ellenberg_f': plant.get('ellenberg_f') or 0}
        plant_info = {'preset': plant.get('preset') or '', 'climate': plant.get('climate') or ''}
        sd = sd_by_plant.get(pid, [])

        low, high, votes = get_votes(pid, care, plant_info, sd)

        if not votes:
            stats['no_data'] += 1
            continue

        # Decision
        new_demand = None
        if low > high and low >= 2:
            if low >= 4:
                new_demand = 'Low'
            else:
                new_demand = 'Low'
            stats['to_low'] += 1
        elif high > low and high >= 2:
            new_demand = 'High'
            stats['to_high'] += 1
        else:
            stats['stays_medium'] += 1

        votes_str = ', '.join(votes)

        if not dry_run:
            # Always record votes
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v2', 'votes', ?, datetime('now'))",
                [pid, votes_str]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v2', 'score', ?, datetime('now'))",
                [pid, f'low={low} high={high}']
            ))

            if new_demand:
                stmts.append((
                    "UPDATE care SET water_demand = ? WHERE plant_id = ? AND water_demand = 'Medium'",
                    [new_demand, pid]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v2', 'changed_to', ?, datetime('now'))",
                    [pid, new_demand]
                ))
            else:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'watering_medium_unresolved', ?, datetime('now'))",
                    [pid, f'votes: {votes_str}']
                ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(medium_plants)}] low={stats['to_low']} high={stats['to_high']} stays={stats['stays_medium']} no_data={stats['no_data']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[watering_v2] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    # Show new distribution
    if not dry_run:
        dist = turso_query("SELECT water_demand, COUNT(*) as cnt FROM care GROUP BY water_demand ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['water_demand'] or '(empty)':<15s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    with_photos = '--with-photos' in sys.argv
    run(dry_run=dry_run, with_photos=with_photos)
