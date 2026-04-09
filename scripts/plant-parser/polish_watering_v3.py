"""
Polish watering v3 — multi-source voting to reclassify Medium demand.

New sources added:
  - USDA moisture_use + drought_tolerance (2,030 plants)
  - Niinemets drought_tolerance (806 plants, scale 0-5)
  - MiFloraDB watering text keywords (5,534 plants)

Plus existing:
  - Ellenberg F (in care.ellenberg_f)
  - PFAF moisture (in source_data)
  - Lifeform + climate (in plants table)

Step 1: Load CSV sources, save raw to source_data
Step 2: Vote for each Medium plant
Step 3: Change demand if perevес >= 3

Usage:
    python3 polish_watering_v3.py --dry-run --with-photos
    python3 polish_watering_v3.py --with-photos
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


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            return set(re.findall(r"plantIdStr: '([^']+)'", f.read()))
    except:
        return set()


def load_usda():
    """Load USDA moisture_use + drought_tolerance by scientific name."""
    data = {}
    path = os.path.join(DATA_DIR, 'usda_plant_characteristics.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            sci = row.get('scientific_name', '').strip().lower()
            moisture = row.get('moisture_use', '').strip()
            drought = row.get('drought_tolerance', '').strip()
            if sci and (moisture or drought):
                data[sci] = {'moisture_use': moisture, 'drought_tolerance': drought}
    print(f"  USDA loaded: {len(data)} plants", flush=True)
    return data


def load_niinemets():
    """Load Niinemets drought_tolerance by scientific name."""
    data = {}
    path = os.path.join(DATA_DIR, 'niinemets_drought_tolerance_806.csv')
    with open(path) as f:
        for row in csv.DictReader(f):
            species = row.get('species', '').strip()
            # Clean: "Abelia × grandiflora (A. chinesis × A. uniflora)" → "abelia grandiflora"
            species_clean = re.sub(r'\(.*?\)', '', species).replace('×', '').strip().lower()
            species_clean = ' '.join(species_clean.split()[:2])  # first two words
            dt = row.get('drought_tolerance', '').strip()
            wl = row.get('waterlogging_tolerance', '').strip()
            if species_clean and dt:
                try:
                    # Handle "2.33±0.33" format
                    dt_val = float(dt.split('±')[0].strip())
                    wl_val = float(wl.split('±')[0].strip()) if wl else None
                    data[species_clean] = {'drought_tolerance': dt_val, 'waterlogging_tolerance': wl_val}
                except ValueError:
                    pass
    print(f"  Niinemets loaded: {len(data)} plants", flush=True)
    return data


def load_mifloradb_watering():
    """Load MiFloraDB watering descriptions by scientific name."""
    data = {}
    path = os.path.join(DATA_DIR, 'mifloradb_5335.csv')
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # pid field contains scientific-like name
            pid = row.get('pid', '').strip().lower().replace("'", '').replace('"', '')
            watering = row.get('watering', '').strip()
            if pid and watering:
                data[pid] = watering
    print(f"  MiFloraDB watering loaded: {len(data)} plants", flush=True)
    return data


def classify_mifloradb_text(text):
    """Extract Low/High signal from MiFloraDB watering description."""
    lower = text.lower()
    low_words = ['drought', 'dry out', 'water sparingly', 'very little water', 'let dry',
                 'infrequent', 'rarely water', 'drought resistant', 'drought tolerant']
    high_words = ['keep moist', 'keep soil moist', 'never dry', 'constantly moist',
                  'water frequently', 'loves moisture', 'bog', 'wet', 'plenty of water']

    if any(w in lower for w in low_words):
        return 'Low'
    if any(w in lower for w in high_words):
        return 'High'
    return None


def step1_save_sources(usda, niinemets, mifloradb_w, dry_run):
    """Save raw CSV data to source_data."""
    if dry_run:
        return

    print(f"\n[step1] Saving raw CSV data to source_data...", flush=True)

    # Get our plants for matching
    our_plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    our_by_name = {}
    for p in our_plants:
        sci = p['scientific'].strip().lower()
        our_by_name[sci] = p['plant_id']
        # Also try just genus+species (first two words)
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    stmts = []
    matched = {'usda': 0, 'niinemets': 0, 'mifloradb': 0}

    # USDA
    for sci, vals in usda.items():
        pid = our_by_name.get(sci)
        if not pid:
            continue
        matched['usda'] += 1
        if vals['moisture_use']:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'moisture_use', ?, datetime('now'))",
                          [pid, vals['moisture_use']]))
        if vals['drought_tolerance']:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'drought_tolerance', ?, datetime('now'))",
                          [pid, vals['drought_tolerance']]))
        if len(stmts) >= 100:
            turso_batch(stmts); stmts = []

    # Niinemets
    for sci, vals in niinemets.items():
        pid = our_by_name.get(sci)
        if not pid:
            continue
        matched['niinemets'] += 1
        stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'niinemets', 'drought_tolerance', ?, datetime('now'))",
                      [pid, str(vals['drought_tolerance'])]))
        if vals.get('waterlogging_tolerance') is not None:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'niinemets', 'waterlogging_tolerance', ?, datetime('now'))",
                          [pid, str(vals['waterlogging_tolerance'])]))
        if len(stmts) >= 100:
            turso_batch(stmts); stmts = []

    # MiFloraDB watering text
    for sci, text in mifloradb_w.items():
        pid = our_by_name.get(sci)
        if not pid:
            continue
        matched['mifloradb'] += 1
        stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'mifloradb', 'watering_text', ?, datetime('now'))",
                      [pid, text[:200]]))
        if len(stmts) >= 100:
            turso_batch(stmts); stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"  Matched: USDA={matched['usda']}, Niinemets={matched['niinemets']}, MiFloraDB={matched['mifloradb']}", flush=True)


def step2_vote(usda, niinemets, mifloradb_w, with_photos, dry_run):
    """Vote for each Medium plant."""
    featured = get_featured_ids()

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

    print(f"\n[step2] Medium plants: {len(medium)}", flush=True)

    # Pre-load PFAF moisture from source_data
    pfaf_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf' AND field = 'moisture'")
    pfaf_by_pid = {r['plant_id']: r['value'] for r in pfaf_data}

    # Pre-load OPB moisture
    opb_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'openplantbook' AND field = 'min_soil_moist'")
    opb_by_pid = {r['plant_id']: r['value'] for r in opb_data}

    stmts = []
    stats = {'to_low': 0, 'to_high': 0, 'stays': 0, 'no_data': 0, 'protected': 0}

    for i, plant in enumerate(medium):
        pid = plant['plant_id']
        if pid in featured:
            stats['protected'] += 1
            continue

        sci = (plant.get('scientific') or '').strip().lower()
        sci_short = ' '.join(sci.split()[:2]) if sci else ''
        low = 0
        high = 0
        votes = []

        # 1. Ellenberg F (weight 3)
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

        # 2. USDA moisture_use (weight 3)
        usda_val = usda.get(sci) or usda.get(sci_short)
        if usda_val:
            mu = usda_val['moisture_use']
            dt = usda_val['drought_tolerance']
            if mu == 'Low':
                low += 3; votes.append(f'usda_m=Low→L(3)')
            elif mu == 'High':
                high += 3; votes.append(f'usda_m=High→H(3)')
            else:
                votes.append(f'usda_m={mu}→M')

            # USDA drought_tolerance (weight 2)
            if dt == 'High':
                low += 2; votes.append(f'usda_dt=High→L(2)')
            elif dt == 'Low':
                high += 2; votes.append(f'usda_dt=Low→H(2)')

        # 3. Niinemets (weight 2)
        niinem = niinemets.get(sci_short)
        if niinem:
            dt_val = niinem['drought_tolerance']
            if dt_val >= 2.5:
                low += 2; votes.append(f'niinem={dt_val}→L(2)')
            elif dt_val <= 1.0:
                high += 2; votes.append(f'niinem={dt_val}→H(2)')
            else:
                votes.append(f'niinem={dt_val}→M')

        # 4. PFAF moisture (weight 2)
        pfaf_m = pfaf_by_pid.get(pid, '')
        if pfaf_m:
            pm = pfaf_m.upper()
            if pm == 'D':
                low += 2; votes.append(f'pfaf=D→L(2)')
            elif pm == 'DM':
                low += 1; votes.append(f'pfaf=DM→L(1)')
            elif pm in ('WE', 'MWE', 'WA', 'WEWA', 'MWEWA'):
                high += 2; votes.append(f'pfaf={pm}→H(2)')
            elif pm == 'MWE':
                high += 1; votes.append(f'pfaf=MWe→H(1)')

        # 5. MiFloraDB watering text (weight 1)
        mfdb_text = mifloradb_w.get(sci) or mifloradb_w.get(sci_short)
        if mfdb_text:
            signal = classify_mifloradb_text(mfdb_text)
            if signal == 'Low':
                low += 1; votes.append(f'mfdb_text→L(1)')
            elif signal == 'High':
                high += 1; votes.append(f'mfdb_text→H(1)')

        # 6. Open Plantbook (weight 1)
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

        # 7. Lifeform + climate (weight 1)
        preset = plant.get('preset') or ''
        climate = (plant.get('climate') or '').lower()
        if preset == 'succulent':
            low += 2; votes.append(f'lf=succulent→L(2)')
        elif preset == 'aquatic':
            high += 2; votes.append(f'lf=aquatic→H(2)')
        elif preset == 'epiphyte' and 'wet tropical' in climate:
            high += 1; votes.append(f'lf=epiphyte+wet→H(1)')
        elif 'desert' in climate:
            low += 1; votes.append(f'climate=desert→L(1)')

        # Decision
        if not votes:
            stats['no_data'] += 1
            continue

        new_demand = None
        if low >= high + 3:
            new_demand = 'Low'
            stats['to_low'] += 1
        elif high >= low + 3:
            new_demand = 'High'
            stats['to_high'] += 1
        else:
            stats['stays'] += 1

        votes_str = ', '.join(votes)

        if not dry_run:
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v3', 'votes', ?, datetime('now'))",
                          [pid, votes_str]))
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v3', 'score', ?, datetime('now'))",
                          [pid, f'low={low} high={high}']))

            if new_demand:
                stmts.append(("UPDATE care SET water_demand = ? WHERE plant_id = ? AND water_demand = 'Medium'",
                              [new_demand, pid]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'watering_v3', 'changed_to', ?, datetime('now'))",
                              [pid, new_demand]))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(medium)}] low={stats['to_low']} high={stats['to_high']} stays={stats['stays']} no_data={stats['no_data']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[watering_v3] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    if not dry_run:
        dist = turso_query("SELECT water_demand, COUNT(*) as cnt FROM care GROUP BY water_demand ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['water_demand'] or '(empty)':<15s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    with_photos = '--with-photos' in sys.argv

    print(f"[watering_v3] Loading sources...", flush=True)
    usda = load_usda()
    niinemets = load_niinemets()
    mifloradb_w = load_mifloradb_watering()

    step1_save_sources(usda, niinemets, mifloradb_w, dry_run)
    step2_vote(usda, niinemets, mifloradb_w, with_photos, dry_run)
