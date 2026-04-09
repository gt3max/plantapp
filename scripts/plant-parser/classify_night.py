"""
Night classification run: POWO API + moss flagging + verification + climate fill.

Part 1: POWO API for unclassified vascular plants (~478)
Part 2: Flag mosses/liverworts as not_relevant (~758)
Part 3: Verify 459 family_fallback via POWO
Part 4: Fill climate for 997 plants missing it

All results → source_data. Progress every 50, flush=True.
~20 minutes total.

Usage:
    python3 classify_night.py           # all 4 parts
    python3 classify_night.py --part 1  # POWO only
"""
import sys
import os
import csv
import time
import json
import urllib.request
import urllib.parse

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

VALID_LIFEFORMS = {'tree', 'shrub', 'subshrub', 'perennial', 'annual', 'succulent',
                   'epiphyte', 'climber', 'bulb', 'aquatic', 'bamboo', 'parasitic', 'fern'}

OLD_PRESETS = ('standard', 'herb', 'tropical')

WCVP_CSV = '/private/tmp/wcvp_names.csv'

# Compound WCVP lifeform → our 13 types
LIFEFORM_MAP = {
    'tree': 'tree', 'shrub': 'shrub', 'shrub or tree': 'tree',
    'tree or shrub': 'tree', 'subshrub': 'subshrub',
    'subshrub or shrub': 'subshrub', 'shrub or subshrub': 'shrub',
    'perennial': 'perennial', 'annual': 'annual',
    'annual or perennial': 'perennial', 'perennial or annual': 'perennial',
    'biennial': 'annual', 'liana': 'climber', 'climber': 'climber',
    'epiphyte': 'epiphyte', 'succulent': 'succulent',
    'succulent subshrub': 'succulent', 'succulent shrub': 'succulent',
    'succulent tree': 'succulent', 'succulent perennial': 'succulent',
    'bulbous geophyte': 'bulb', 'tuberous geophyte': 'bulb',
    'rhizomatous geophyte': 'bulb', 'cormous geophyte': 'bulb',
    'geophyte': 'bulb', 'aquatic': 'aquatic', 'helophyte': 'aquatic',
    'hydrophyte': 'aquatic', 'parasite': 'parasitic',
    'hemiparasite': 'parasitic', 'hemiepiphyte': 'epiphyte',
    'bamboo': 'bamboo', 'fern': 'fern', 'tree fern': 'fern',
    'scrambling subshrub': 'subshrub', 'scrambling shrub': 'shrub',
}

# Moss/liverwort families — not vascular, flag as not_relevant
MOSS_FAMILIES = {
    'Pottiaceae', 'Bryaceae', 'Sphagnaceae', 'Dicranaceae', 'Brachytheciaceae',
    'Grimmiaceae', 'Orthotrichaceae', 'Fissidentaceae', 'Amblystegiaceae',
    'Hypnaceae', 'Mniaceae', 'Polytrichaceae', 'Thuidiaceae', 'Neckeraceae',
    'Sematophyllaceae', 'Leucobryaceae', 'Funariaceae', 'Bartramiaceae',
    'Hookeriaceae', 'Pilotrichaceae', 'Calymperaceae', 'Meteoriaceae',
    'Ptychomitriaceae', 'Cryphaeaceae', 'Anomodontaceae', 'Lembophyllaceae',
    'Entodontaceae', 'Plagiotheciaceae', 'Pylaisiadelphaceae', 'Fontinalaceae',
    'Racopilaceae', 'Daltoniaceae', 'Pterobryaceae', 'Hylocomiaceae',
    'Rhytidiaceae', 'Climaciaceae', 'Hedwigiaceae',
    # Liverworts
    'Lejeuneaceae', 'Cephaloziaceae', 'Frullaniaceae', 'Porellaceae',
    'Radulaceae', 'Plagiochilaceae', 'Jungermanniaceae', 'Lophocoleaceae',
    'Scapaniaceae', 'Herbertaceae', 'Lepidoziaceae', 'Calypogeiaceae',
    'Geocalycaceae', 'Jubulaceae', 'Metzgeriaceae', 'Aneuraceae',
    'Pelliaceae', 'Pallaviciniaceae', 'Marchantiaceae', 'Ricciaceae',
    'Aytoniaceae', 'Conocephalaceae',
    # Hornworts
    'Anthocerotaceae', 'Notothyladaceae',
}


def map_lifeform(raw):
    """Map compound lifeform description to our 13 types."""
    if not raw:
        return None
    raw_lower = raw.strip().lower()
    if raw_lower in LIFEFORM_MAP:
        return LIFEFORM_MAP[raw_lower]
    for sep in [' or ', ', ']:
        if sep in raw_lower:
            first = raw_lower.split(sep)[0].strip()
            if first in LIFEFORM_MAP:
                return LIFEFORM_MAP[first]
    for keyword, lf in LIFEFORM_MAP.items():
        if keyword in raw_lower:
            return lf
    return None


def powo_lookup(scientific):
    """IPNI search → POWO detail. Returns (lifeform, climate, family) or (None, None, None).
    POWO search API is broken (always returns 0), so we use IPNI to get fqId first."""
    try:
        # Step 1: IPNI search (Kew Gardens) → get fqId
        q = urllib.parse.quote(scientific)
        url = f'https://www.ipni.org/api/1/search?q={q}&perPage=1'
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        results = data.get('results', [])
        if not results:
            return None, None, None

        fqId = results[0].get('fqId', '')
        if not fqId:
            return None, None, None

        # Step 2: POWO detail with fqId from IPNI
        detail_url = f'https://powo.science.kew.org/api/2/taxon/{fqId}'
        req2 = urllib.request.Request(detail_url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            detail = json.loads(resp2.read().decode())

        # Follow accepted name if this is a synonym
        if detail.get('synonym') and detail.get('accepted'):
            acc_fqId = detail['accepted'].get('fqId', '')
            if acc_fqId:
                req3 = urllib.request.Request(
                    f'https://powo.science.kew.org/api/2/taxon/{acc_fqId}',
                    headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
                with urllib.request.urlopen(req3, timeout=15) as resp3:
                    detail = json.loads(resp3.read().decode())

        raw_lf = detail.get('lifeform', '') or ''
        raw_cl = detail.get('climate', '') or ''
        family = detail.get('family', '') or ''

        return raw_lf, raw_cl, family
    except Exception:
        return None, None, None


def part1_powo_unclassified():
    """Part 1: POWO API for unclassified vascular plants."""
    print(f"\n=== PART 1: POWO API for unclassified ===", flush=True)

    plants = turso_query(
        "SELECT plant_id, scientific, family FROM plants WHERE preset IN (?, ?, ?)",
        list(OLD_PRESETS)
    )

    # Filter out mosses/liverworts
    vascular = [p for p in plants if (p.get('family') or '') not in MOSS_FAMILIES]
    print(f"  Total unclassified: {len(plants)}, vascular (not moss): {len(vascular)}", flush=True)

    stmts = []
    stats = {'classified': 0, 'not_found': 0, 'error': 0, 'family_filled': 0}

    for i, plant in enumerate(vascular):
        pid = plant['plant_id']
        sci = plant.get('scientific') or ''
        if not sci:
            stats['not_found'] += 1
            continue

        raw_lf, raw_cl, family = powo_lookup(sci)
        lifeform = map_lifeform(raw_lf) if raw_lf else None

        if lifeform:
            stats['classified'] += 1
            stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [lifeform, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'powo', 'lifeform', ?, datetime('now'))",
                [pid, lifeform]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'powo', 'lifeform_raw', ?, datetime('now'))",
                [pid, raw_lf]
            ))
        else:
            stats['not_found'] += 1

        if raw_cl:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ? AND (climate IS NULL OR climate = '')",
                          [raw_cl, pid]))

        if family and not plant.get('family'):
            stmts.append(("UPDATE plants SET family = ? WHERE plant_id = ? AND (family IS NULL OR family = '')",
                          [family, pid]))
            stats['family_filled'] += 1

        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(vascular)}] classified={stats['classified']} miss={stats['not_found']}", flush=True)

        time.sleep(0.5)

    if stmts:
        turso_batch(stmts)

    print(f"  Part 1 done: classified={stats['classified']}, not_found={stats['not_found']}, family_filled={stats['family_filled']}", flush=True)


def part2_flag_mosses():
    """Part 2: Flag mosses/liverworts as not_relevant."""
    print(f"\n=== PART 2: Flag mosses/liverworts ===", flush=True)

    plants = turso_query(
        "SELECT plant_id, family FROM plants WHERE preset IN (?, ?, ?)",
        list(OLD_PRESETS)
    )

    stmts = []
    count = 0
    for plant in plants:
        family = plant.get('family') or ''
        if family in MOSS_FAMILIES:
            pid = plant['plant_id']
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'not_relevant', ?, datetime('now'))",
                [pid, f'moss/liverwort family={family}']
            ))
            count += 1
            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"  Flagged {count} mosses/liverworts as not_relevant", flush=True)


def part3_verify_family_fallback():
    """Part 3: Verify 459 family_fallback classifications via POWO."""
    print(f"\n=== PART 3: Verify family_fallback via POWO ===", flush=True)

    family_plants = turso_query("""
        SELECT DISTINCT sd.plant_id FROM source_data sd
        JOIN plants p ON sd.plant_id = p.plant_id
        WHERE sd.source = 'family_classify' AND sd.field = 'lifeform'
    """)

    plant_ids = [r['plant_id'] for r in family_plants]
    print(f"  {len(plant_ids)} family_fallback plants to verify", flush=True)

    stmts = []
    stats = {'confirmed': 0, 'conflict': 0, 'not_found': 0}

    for i, pid in enumerate(plant_ids):
        plant = turso_query("SELECT scientific, preset FROM plants WHERE plant_id = ?", [pid])
        if not plant:
            continue
        sci = plant[0].get('scientific') or ''
        current_lf = plant[0].get('preset') or ''

        raw_lf, raw_cl, _ = powo_lookup(sci)
        powo_lf = map_lifeform(raw_lf) if raw_lf else None

        if powo_lf:
            if powo_lf == current_lf:
                stats['confirmed'] += 1
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'powo_verify', 'lifeform_confirmed', 'true', datetime('now'))",
                    [pid]
                ))
                # Remove low confidence flag
                stmts.append((
                    "DELETE FROM source_data WHERE plant_id = ? AND source = 'flag' AND field = 'classification_low_confidence'",
                    [pid]
                ))
            else:
                stats['conflict'] += 1
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'conflict', 'family_vs_powo', ?, datetime('now'))",
                    [pid, f'family={current_lf}, powo={powo_lf} (raw={raw_lf})']
                ))
                # Update to POWO value (higher trust)
                stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [powo_lf, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'powo', 'lifeform', ?, datetime('now'))",
                    [pid, powo_lf]
                ))
        else:
            stats['not_found'] += 1

        if raw_cl:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ? AND (climate IS NULL OR climate = '')",
                          [raw_cl, pid]))

        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(plant_ids)}] confirmed={stats['confirmed']} conflict={stats['conflict']} miss={stats['not_found']}", flush=True)

        time.sleep(0.5)

    if stmts:
        turso_batch(stmts)

    print(f"  Part 3 done: confirmed={stats['confirmed']}, conflict={stats['conflict']}, not_found={stats['not_found']}", flush=True)


def part4_fill_climate():
    """Part 4: Fill climate for plants that have lifeform but no climate."""
    print(f"\n=== PART 4: Fill climate ===", flush=True)

    plants = turso_query("""
        SELECT plant_id, scientific FROM plants
        WHERE preset IN ('tree','shrub','subshrub','perennial','annual','succulent',
                         'epiphyte','climber','bulb','aquatic','bamboo','parasitic','fern')
        AND (climate IS NULL OR climate = '')
    """)
    print(f"  {len(plants)} plants with lifeform but no climate", flush=True)

    # First try WCVP CSV exact match
    wcvp_exact = {}
    if os.path.exists(WCVP_CSV):
        print(f"  Loading WCVP CSV for exact match...", flush=True)
        with open(WCVP_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # skip header
            for row in reader:
                if len(row) > 21 and row[3] == 'Accepted':
                    taxon = row[21].strip().lower()  # taxon_name
                    climate = row[20].strip()  # climate_description
                    if taxon and climate:
                        wcvp_exact[taxon] = climate
        print(f"  WCVP exact: {len(wcvp_exact)} accepted names with climate", flush=True)

    stmts = []
    stats = {'wcvp_exact': 0, 'powo': 0, 'not_found': 0}

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        sci = (plant.get('scientific') or '').lower()
        climate = None

        # Try WCVP exact
        if sci in wcvp_exact:
            climate = wcvp_exact[sci]
            source = 'wcvp_exact'
            stats['wcvp_exact'] += 1
        else:
            # Try POWO
            _, raw_cl, _ = powo_lookup(plant.get('scientific') or '')
            if raw_cl:
                climate = raw_cl
                source = 'powo'
                stats['powo'] += 1
            else:
                stats['not_found'] += 1
            time.sleep(0.5)

        if climate:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ?", [climate, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'climate', ?, datetime('now'))",
                [pid, f'climate_fill_{source}', climate]
            ))

        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(plants)}] wcvp={stats['wcvp_exact']} powo={stats['powo']} miss={stats['not_found']}", flush=True)

    if stmts:
        turso_batch(stmts)

    print(f"  Part 4 done: wcvp_exact={stats['wcvp_exact']}, powo={stats['powo']}, not_found={stats['not_found']}", flush=True)


def show_final():
    """Show final state."""
    print(f"\n=== FINAL STATE ===", flush=True)
    rows = turso_query("SELECT preset, COUNT(*) as cnt FROM plants GROUP BY preset ORDER BY cnt DESC")
    for r in rows:
        marker = ' ✓' if r['preset'] in VALID_LIFEFORMS else ' ✗'
        print(f"  {r['preset'] or '(empty)':<15s} {r['cnt']:>6}{marker}", flush=True)

    both = turso_query("SELECT COUNT(*) as c FROM plants WHERE preset IN ('tree','shrub','subshrub','perennial','annual','succulent','epiphyte','climber','bulb','aquatic','bamboo','parasitic','fern') AND climate IS NOT NULL AND climate != ''")[0]['c']
    print(f"\n  Оба тега: {both} / 20261", flush=True)

    flags = turso_query("SELECT field, COUNT(*) as c FROM source_data WHERE source = 'flag' GROUP BY field ORDER BY c DESC")
    print(f"\n  Flags:", flush=True)
    for f in flags:
        print(f"    {f['field']}: {f['c']}", flush=True)


if __name__ == '__main__':
    part_only = None
    if '--part' in sys.argv:
        idx = sys.argv.index('--part')
        if idx + 1 < len(sys.argv):
            part_only = int(sys.argv[idx + 1])

    if part_only is None or part_only == 1:
        part1_powo_unclassified()

    if part_only is None or part_only == 2:
        part2_flag_mosses()

    if part_only is None or part_only == 3:
        part3_verify_family_fallback()

    if part_only is None or part_only == 4:
        part4_fill_climate()

    show_final()
