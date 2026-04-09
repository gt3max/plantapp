"""
Polish watering v4 — lifeform+climate as base, sources as confirmation.

Level 1: Hard rules (succulent→Low, aquatic/fern/bamboo→High)
Level 2: Classification bias (desert→Low(3), wet tropical→High(1), epiphyte→High(1))
Level 3: Source votes (Ellenberg F, USDA, Niinemets, PFAF, MiFloraDB, OPB)
Decision: total_low vs total_high, threshold ≥ 2

Sources saved to source_data. Featured 32 protected (votes recorded, demand not changed).

Usage:
    python3 polish_watering_v4.py --dry-run --with-photos
    python3 polish_watering_v4.py --with-photos
    python3 polish_watering_v4.py              # all Medium plants
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

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
FEATURED_FILE = '/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart'

# === Level 1: Hard rules ===
HARD_RULES = {
    'succulent': 'Low',
    'aquatic': 'High',
    'fern': 'High',
    'bamboo': 'High',
}

# === Level 2: Climate bias ===
CLIMATE_BIAS = {
    'desert or dry shrubland': ('low', 3),
    'seasonally dry tropical': ('low', 1),
    'subalpine or subarctic': ('low', 1),
    'wet tropical': ('high', 1),
    'temperate': (None, 0),
    'subtropical': (None, 0),
    'montane tropical': (None, 0),
    'subtropical or tropical': (None, 0),
}

# Lifeform bias (for non-hard-rule types)
LIFEFORM_BIAS = {
    'epiphyte': ('high', 1),
    'bulb': ('low', 1),
}

# === Keyword extraction for MiFloraDB ===
LOW_KEYWORDS = ['drought', 'dry out', 'water sparingly', 'very little water', 'let dry',
                'infrequent', 'rarely water', 'drought resistant', 'drought tolerant']
HIGH_KEYWORDS = ['keep moist', 'keep soil moist', 'never dry', 'constantly moist',
                 'water frequently', 'loves moisture', 'bog', 'wet', 'plenty of water']


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            return set(re.findall(r"plantIdStr: '([^']+)'", f.read()))
    except:
        return set()


def load_csv_sources():
    """Load USDA, Niinemets, MiFloraDB from CSV files."""
    usda = {}
    path = os.path.join(DATA_DIR, 'usda_plant_characteristics.csv')
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                sci = row.get('scientific_name', '').strip().lower()
                if sci:
                    usda[sci] = {
                        'moisture_use': row.get('moisture_use', '').strip(),
                        'drought_tolerance': row.get('drought_tolerance', '').strip()
                    }
    print(f"  USDA: {len(usda)}", flush=True)

    niinemets = {}
    path = os.path.join(DATA_DIR, 'niinemets_drought_tolerance_806.csv')
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                species = row.get('species', '').strip()
                species_clean = re.sub(r'\(.*?\)', '', species).replace('×', '').strip().lower()
                species_clean = ' '.join(species_clean.split()[:2])
                dt = row.get('drought_tolerance', '').strip()
                if species_clean and dt:
                    try:
                        niinemets[species_clean] = float(dt.split('±')[0].strip())
                    except ValueError:
                        pass
    print(f"  Niinemets: {len(niinemets)}", flush=True)

    mifloradb = {}
    path = os.path.join(DATA_DIR, 'mifloradb_5335.csv')
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                pid = row.get('pid', '').strip().lower().replace("'", '').replace('"', '')
                watering = row.get('watering', '').strip()
                if pid and watering:
                    mifloradb[pid] = watering
    print(f"  MiFloraDB watering: {len(mifloradb)}", flush=True)

    return usda, niinemets, mifloradb


def save_raw_sources(usda, niinemets, our_by_name):
    """Save raw CSV data to source_data (one time)."""
    stmts = []
    for sci, vals in usda.items():
        pid = our_by_name.get(sci)
        if not pid:
            continue
        if vals['moisture_use']:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'moisture_use', ?, datetime('now'))",
                          [pid, vals['moisture_use']]))
        if vals['drought_tolerance']:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'drought_tolerance', ?, datetime('now'))",
                          [pid, vals['drought_tolerance']]))
        if len(stmts) >= 100:
            turso_batch(stmts); stmts = []

    for sci, dt_val in niinemets.items():
        pid = our_by_name.get(sci)
        if pid:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'niinemets', 'drought_tolerance', ?, datetime('now'))",
                          [pid, str(dt_val)]))
        if len(stmts) >= 100:
            turso_batch(stmts); stmts = []

    if stmts:
        turso_batch(stmts)


def get_votes(plant, usda, niinemets, mifloradb, pfaf_by_pid, opb_by_pid):
    """Get all votes for a Medium plant. Returns (low, high, votes_list)."""
    pid = plant['plant_id']
    sci = (plant.get('scientific') or '').strip().lower()
    sci_short = ' '.join(sci.split()[:2]) if sci else ''
    preset = plant.get('preset') or ''
    climate = (plant.get('climate') or '').lower()

    low = 0
    high = 0
    votes = []

    # === Level 1: Hard rules ===
    if preset in HARD_RULES:
        demand = HARD_RULES[preset]
        if demand == 'Low':
            low += 10  # overwhelming
            votes.append(f'HARD:{preset}→Low(10)')
        else:
            high += 10
            votes.append(f'HARD:{preset}→High(10)')
        return low, high, votes

    # === Level 2: Classification bias ===
    for cl_key, (direction, weight) in CLIMATE_BIAS.items():
        if cl_key in climate and direction and weight:
            if direction == 'low':
                low += weight
                votes.append(f'climate={cl_key}→L({weight})')
            else:
                high += weight
                votes.append(f'climate={cl_key}→H({weight})')
            break

    if preset in LIFEFORM_BIAS:
        direction, weight = LIFEFORM_BIAS[preset]
        if direction == 'low':
            low += weight
            votes.append(f'lf={preset}→L({weight})')
        else:
            high += weight
            votes.append(f'lf={preset}→H({weight})')

    # === Level 3: Source votes ===

    # Ellenberg F (weight 3)
    ef = plant.get('ellenberg_f') or 0
    if ef > 0:
        if ef <= 3:
            low += 3; votes.append(f'ell_f={ef}→L(3)')
        elif ef == 4:
            low += 2; votes.append(f'ell_f={ef}→L(2)')
        elif ef <= 6:
            votes.append(f'ell_f={ef}→M')
        elif ef <= 8:
            high += 3; votes.append(f'ell_f={ef}→H(3)')
        else:
            high += 4; votes.append(f'ell_f={ef}→H(4)')

    # USDA (weight 3 moisture + 2 drought)
    usda_val = usda.get(sci) or usda.get(sci_short)
    if usda_val:
        mu = usda_val.get('moisture_use', '')
        dt = usda_val.get('drought_tolerance', '')
        if mu == 'Low':
            low += 3; votes.append(f'usda_m=Low→L(3)')
        elif mu == 'High':
            high += 3; votes.append(f'usda_m=High→H(3)')

        if dt == 'High':
            low += 2; votes.append(f'usda_dt=High→L(2)')
        elif dt == 'Low':
            high += 2; votes.append(f'usda_dt=Low→H(2)')

    # Niinemets (weight 2)
    niinem = niinemets.get(sci_short)
    if niinem is not None:
        if niinem >= 2.5:
            low += 2; votes.append(f'niinem={niinem}→L(2)')
        elif niinem <= 1.0:
            high += 2; votes.append(f'niinem={niinem}→H(2)')
        else:
            votes.append(f'niinem={niinem}→M')

    # PFAF moisture (weight 2)
    pfaf_m = pfaf_by_pid.get(pid, '').upper()
    if pfaf_m:
        if pfaf_m == 'D':
            low += 2; votes.append(f'pfaf=D→L(2)')
        elif pfaf_m == 'DM':
            low += 1; votes.append(f'pfaf=DM→L(1)')
        elif pfaf_m in ('WE', 'WA', 'WEWA', 'MWEWA'):
            high += 2; votes.append(f'pfaf={pfaf_m}→H(2)')
        elif pfaf_m == 'MWE':
            high += 1; votes.append(f'pfaf=MWe→H(1)')

    # MiFloraDB text (weight 1)
    mfdb_text = mifloradb.get(sci) or mifloradb.get(sci_short)
    if mfdb_text:
        lower = mfdb_text.lower()
        if any(w in lower for w in LOW_KEYWORDS):
            low += 1; votes.append(f'mfdb→L(1)')
        elif any(w in lower for w in HIGH_KEYWORDS):
            high += 1; votes.append(f'mfdb→H(1)')

    # Open Plantbook (weight 1)
    opb_val = opb_by_pid.get(pid)
    if opb_val:
        try:
            moist = float(opb_val)
            if moist > 50:
                high += 1; votes.append(f'opb={moist}→H(1)')
            elif moist < 20:
                low += 1; votes.append(f'opb={moist}→L(1)')
        except:
            pass

    return low, high, votes


def run(dry_run=False, with_photos=False):
    featured = get_featured_ids()
    print(f"[watering_v4] Protected: {len(featured)} featured", flush=True)
    print(f"[watering_v4] Loading sources...", flush=True)

    usda, niinemets, mifloradb = load_csv_sources()

    # Build name lookup
    our_plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our_plants:
        sci = p['scientific'].strip().lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    # Save raw sources (step 1) — skip if already saved
    skip_save = '--skip-save' in sys.argv
    if not dry_run and not skip_save:
        print(f"[watering_v4] Saving raw sources to source_data...", flush=True)
        save_raw_sources(usda, niinemets, our_by_name)
    elif skip_save:
        print(f"[watering_v4] Skipping raw save (already in DB)", flush=True)

    # Load PFAF + OPB
    pfaf_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf' AND field = 'moisture'")
    pfaf_by_pid = {r['plant_id']: r['value'] for r in pfaf_data}
    opb_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'openplantbook' AND field = 'min_soil_moist'")
    opb_by_pid = {r['plant_id']: r['value'] for r in opb_data}

    # Get Medium plants
    if with_photos:
        medium = turso_query("""
            SELECT c.plant_id, c.ellenberg_f, p.scientific, p.preset, p.climate
            FROM care c JOIN plants p ON c.plant_id = p.plant_id
            JOIN plant_images pi ON c.plant_id = pi.plant_id
            WHERE c.water_demand = 'Medium'
            GROUP BY c.plant_id
        """)
    else:
        medium = turso_query("""
            SELECT c.plant_id, c.ellenberg_f, p.scientific, p.preset, p.climate
            FROM care c JOIN plants p ON c.plant_id = p.plant_id
            WHERE c.water_demand = 'Medium'
        """)

    print(f"[watering_v4] Medium plants: {len(medium)}", flush=True)

    stmts = []
    stats = {'hard_low': 0, 'hard_high': 0, 'vote_low': 0, 'vote_high': 0,
             'stays': 0, 'no_votes': 0, 'protected': 0}

    for i, plant in enumerate(medium):
        pid = plant['plant_id']
        is_featured = pid in featured

        low, high, votes = get_votes(plant, usda, niinemets, mifloradb, pfaf_by_pid, opb_by_pid)

        if not votes:
            stats['no_votes'] += 1
            continue

        # Decision
        is_hard = any(v.startswith('HARD:') for v in votes)
        new_demand = None

        if is_hard:
            new_demand = 'Low' if low > high else 'High'
            if new_demand == 'Low':
                stats['hard_low'] += 1
            else:
                stats['hard_high'] += 1
        elif low > high and low >= 2:
            new_demand = 'Low'
            stats['vote_low'] += 1
        elif high > low and high >= 2:
            new_demand = 'High'
            stats['vote_high'] += 1
        else:
            stats['stays'] += 1

        votes_str = ', '.join(votes)

        if not dry_run:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v4', 'votes', ?, datetime('now'))",
                          [pid, votes_str]))
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v4', 'score', ?, datetime('now'))",
                          [pid, f'low={low} high={high}']))

            if new_demand and not is_featured:
                stmts.append(("UPDATE care SET water_demand = ? WHERE plant_id = ? AND water_demand = 'Medium'",
                              [new_demand, pid]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v4', 'changed_to', ?, datetime('now'))",
                              [pid, new_demand]))
            elif is_featured:
                stats['protected'] += 1
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v4', 'featured_would_be', ?, datetime('now'))",
                              [pid, new_demand or 'Medium']))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 500 == 0:
            total_moved = stats['hard_low'] + stats['hard_high'] + stats['vote_low'] + stats['vote_high']
            print(f"  [{i+1}/{len(medium)}] moved={total_moved} (hard={stats['hard_low']+stats['hard_high']} vote={stats['vote_low']+stats['vote_high']}) stays={stats['stays']} no_data={stats['no_votes']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    total_moved = stats['hard_low'] + stats['hard_high'] + stats['vote_low'] + stats['vote_high']
    print(f"\n[watering_v4] Done:", flush=True)
    print(f"  Hard rules:  {stats['hard_low']} Low + {stats['hard_high']} High = {stats['hard_low']+stats['hard_high']}", flush=True)
    print(f"  Voted:       {stats['vote_low']} Low + {stats['vote_high']} High = {stats['vote_low']+stats['vote_high']}", flush=True)
    print(f"  Total moved: {total_moved}", flush=True)
    print(f"  Stays Medium: {stats['stays']}", flush=True)
    print(f"  No data:     {stats['no_votes']}", flush=True)
    print(f"  Protected:   {stats['protected']}", flush=True)

    if not dry_run:
        dist = turso_query("SELECT water_demand, COUNT(*) as cnt FROM care GROUP BY water_demand ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['water_demand'] or '(empty)':<15s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    with_photos = '--with-photos' in sys.argv
    run(dry_run=dry_run, with_photos=with_photos)
