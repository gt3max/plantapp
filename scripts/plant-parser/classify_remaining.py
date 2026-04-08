"""
Classify remaining 3,604 plants (standard/herb/tropical) into WCVP 13 lifeform types.

Our classification (13 lifeform + 8 climate):
  Lifeform: tree, shrub, subshrub, perennial, annual, succulent, epiphyte,
            climber, bulb, aquatic, bamboo, parasitic, fern
  Climate:  temperate, subtropical, wet tropical, seasonally dry tropical,
            desert or dry shrubland, subalpine or subarctic, montane tropical,
            subtropical or tropical

4 steps, each saves source + method to source_data:
  Step 1: genus from our DB (unanimous or majority >70%)
  Step 2: genus from WCVP CSV
  Step 3: POWO API lookup
  Step 4: family fallback

Usage:
    python3 classify_remaining.py                # all 4 steps
    python3 classify_remaining.py --step 1       # genus from DB only
    python3 classify_remaining.py --step 2       # WCVP CSV only
    python3 classify_remaining.py --dry-run      # preview, don't write
"""
import sys
import os
import csv
import re
import time
import urllib.request
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

from turso_sync import turso_query, turso_batch, store_source_data

VALID_LIFEFORMS = {'tree', 'shrub', 'subshrub', 'perennial', 'annual', 'succulent',
                   'epiphyte', 'climber', 'bulb', 'aquatic', 'bamboo', 'parasitic', 'fern'}

OLD_PRESETS = ('standard', 'herb', 'tropical')

WCVP_CSV = '/private/tmp/wcvp_names.csv'

# Mapping compound WCVP lifeform_description → our 13 types
LIFEFORM_MAP = {
    'tree': 'tree',
    'shrub': 'shrub',
    'shrub or tree': 'tree',
    'tree or shrub': 'tree',
    'subshrub': 'subshrub',
    'subshrub or shrub': 'subshrub',
    'shrub or subshrub': 'shrub',
    'perennial': 'perennial',
    'annual': 'annual',
    'annual or perennial': 'perennial',
    'perennial or annual': 'perennial',
    'biennial': 'annual',
    'liana': 'climber',
    'climber': 'climber',
    'epiphyte': 'epiphyte',
    'succulent': 'succulent',
    'succulent subshrub': 'succulent',
    'succulent shrub': 'succulent',
    'succulent tree': 'succulent',
    'succulent perennial': 'succulent',
    'bulbous geophyte': 'bulb',
    'tuberous geophyte': 'bulb',
    'rhizomatous geophyte': 'bulb',
    'cormous geophyte': 'bulb',
    'geophyte': 'bulb',
    'aquatic': 'aquatic',
    'helophyte': 'aquatic',
    'hydrophyte': 'aquatic',
    'parasite': 'parasitic',
    'hemiparasite': 'parasitic',
    'hemiepiphyte': 'epiphyte',
    'bamboo': 'bamboo',
    'fern': 'fern',
    'tree fern': 'fern',
}

# Family → lifeform fallback (Step 4)
FAMILY_MAP = {
    'Orchidaceae': 'epiphyte',
    'Cactaceae': 'succulent',
    'Polypodiaceae': 'fern',
    'Pteridaceae': 'fern',
    'Aspleniaceae': 'fern',
    'Dryopteridaceae': 'fern',
    'Blechnaceae': 'fern',
    'Cyatheaceae': 'fern',
    'Bromeliaceae': 'epiphyte',
    'Araceae': 'perennial',
    'Arecaceae': 'tree',
    'Poaceae': 'perennial',
    'Fabaceae': 'perennial',
    'Asteraceae': 'perennial',
    'Solanaceae': 'perennial',
    'Lamiaceae': 'perennial',
    'Rosaceae': 'shrub',
    'Myrtaceae': 'tree',
    'Pinaceae': 'tree',
    'Cupressaceae': 'tree',
    'Fagaceae': 'tree',
    'Betulaceae': 'tree',
    'Salicaceae': 'tree',
}


def map_wcvp_lifeform(raw):
    """Map compound WCVP lifeform_description to our 13 types."""
    if not raw:
        return None
    raw_lower = raw.strip().lower()

    # Direct match
    if raw_lower in LIFEFORM_MAP:
        return LIFEFORM_MAP[raw_lower]

    # Try first part of compound
    for sep in [' or ', ', ']:
        if sep in raw_lower:
            first = raw_lower.split(sep)[0].strip()
            if first in LIFEFORM_MAP:
                return LIFEFORM_MAP[first]

    # Check if any keyword matches
    for keyword, lf in LIFEFORM_MAP.items():
        if keyword in raw_lower:
            return lf

    return None


def get_remaining():
    """Get plants that need classification."""
    rows = turso_query(
        "SELECT plant_id, scientific, genus, family FROM plants WHERE preset IN (?, ?, ?)",
        list(OLD_PRESETS)
    )
    print(f"[classify] {len(rows)} plants to classify (standard/herb/tropical)", flush=True)
    return rows


def step1_genus_from_db(remaining, dry_run=False):
    """Step 1: Classify by genus from already-classified plants in our DB."""
    print(f"\n=== STEP 1: Genus from DB ===", flush=True)

    # Build genus → lifeform map from classified plants
    genus_data = turso_query("""
        SELECT genus, preset, COUNT(*) as cnt
        FROM plants
        WHERE preset IN ('tree','shrub','subshrub','perennial','annual','succulent',
                         'epiphyte','climber','bulb','aquatic','bamboo','parasitic','fern')
        AND genus IS NOT NULL AND genus != ''
        GROUP BY genus, preset
    """)

    # Group by genus
    genus_map = {}
    for r in genus_data:
        g = r['genus']
        if g not in genus_map:
            genus_map[g] = {}
        genus_map[g][r['preset']] = r['cnt']

    stmts = []
    stats = {'unanimous': 0, 'majority': 0, 'ambiguous': 0, 'no_genus': 0}
    classified = set()

    for i, plant in enumerate(remaining):
        genus = plant.get('genus') or ''
        if not genus or genus not in genus_map:
            stats['no_genus'] += 1
            continue

        types = genus_map[genus]
        total = sum(types.values())

        if len(types) == 1:
            # Unanimous
            lifeform = list(types.keys())[0]
            method = 'genus_unanimous'
            stats['unanimous'] += 1
        else:
            # Check majority (>70%)
            dominant = max(types, key=types.get)
            if types[dominant] / total > 0.7:
                lifeform = dominant
                method = 'genus_majority_70pct'
                stats['majority'] += 1
            else:
                stats['ambiguous'] += 1
                continue

        pid = plant['plant_id']
        classified.add(pid)

        if not dry_run:
            stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [lifeform, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'genus_classify', 'lifeform_method', ?, datetime('now'))",
                [pid, method]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'genus_classify', 'lifeform', ?, datetime('now'))",
                [pid, lifeform]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(remaining)}] unanimous={stats['unanimous']} majority={stats['majority']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Step 1 done: unanimous={stats['unanimous']}, majority={stats['majority']}, "
          f"ambiguous={stats['ambiguous']}, no_genus={stats['no_genus']}", flush=True)

    return classified


def step2_wcvp_csv(remaining, already_done, dry_run=False):
    """Step 2: Classify by genus lookup in WCVP CSV."""
    print(f"\n=== STEP 2: WCVP CSV by genus ===", flush=True)

    todo = [p for p in remaining if p['plant_id'] not in already_done]
    print(f"  {len(todo)} plants remaining after Step 1", flush=True)

    if not os.path.exists(WCVP_CSV):
        print(f"  ERROR: WCVP CSV not found at {WCVP_CSV}", flush=True)
        return set()

    # Parse WCVP CSV — build genus → (lifeform, climate) from Accepted records
    print(f"  Parsing WCVP CSV...", flush=True)
    wcvp_genus = {}  # genus → {lifeform: count}
    wcvp_climate = {}  # genus → {climate: count}

    with open(WCVP_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        header = next(reader)

        # Find column indices (from WCVP CSV header)
        genus_idx = 6   # genus
        status_idx = 3  # taxon_status
        lf_idx = 19     # lifeform_description
        cl_idx = 20     # climate_description

        for row_num, row in enumerate(reader):
            if len(row) <= max(genus_idx, status_idx, lf_idx, cl_idx):
                continue
            if row[status_idx] != 'Accepted':
                continue

            genus = row[genus_idx].strip()
            raw_lf = row[lf_idx].strip()
            raw_cl = row[cl_idx].strip()

            if genus and raw_lf:
                mapped = map_wcvp_lifeform(raw_lf)
                if mapped:
                    if genus not in wcvp_genus:
                        wcvp_genus[genus] = {}
                    wcvp_genus[genus][mapped] = wcvp_genus[genus].get(mapped, 0) + 1

            if genus and raw_cl:
                if genus not in wcvp_climate:
                    wcvp_climate[genus] = {}
                wcvp_climate[genus][raw_cl] = wcvp_climate[genus].get(raw_cl, 0) + 1

            if (row_num + 1) % 200000 == 0:
                print(f"    parsed {row_num+1} rows...", flush=True)

    print(f"  WCVP: {len(wcvp_genus)} genera with lifeform, {len(wcvp_climate)} with climate", flush=True)

    stmts = []
    stats = {'classified': 0, 'climate_filled': 0, 'not_found': 0}
    classified = set()

    for i, plant in enumerate(todo):
        genus = plant.get('genus') or ''
        pid = plant['plant_id']

        if not genus:
            # Try extracting genus from scientific name
            sci = plant.get('scientific') or ''
            if ' ' in sci:
                genus = sci.split()[0]

        lifeform = None
        climate = None

        if genus and genus in wcvp_genus:
            types = wcvp_genus[genus]
            if len(types) == 1:
                lifeform = list(types.keys())[0]
                method = 'wcvp_genus_unanimous'
            else:
                dominant = max(types, key=types.get)
                total = sum(types.values())
                if types[dominant] / total > 0.6:
                    lifeform = dominant
                    method = 'wcvp_genus_majority'
                else:
                    method = 'wcvp_genus_ambiguous'

        if genus and genus in wcvp_climate:
            cl_types = wcvp_climate[genus]
            dominant_cl = max(cl_types, key=cl_types.get)
            climate = dominant_cl

        if lifeform:
            classified.add(pid)
            stats['classified'] += 1

            if not dry_run:
                stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [lifeform, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wcvp_genus', 'lifeform_method', ?, datetime('now'))",
                    [pid, method]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wcvp_genus', 'lifeform', ?, datetime('now'))",
                    [pid, lifeform]
                ))
        else:
            stats['not_found'] += 1

        if climate and not dry_run:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ? AND (climate IS NULL OR climate = '')",
                          [climate, pid]))
            stats['climate_filled'] += 1

        if len(stmts) >= 100:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(todo)}] classified={stats['classified']} climate={stats['climate_filled']} miss={stats['not_found']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Step 2 done: classified={stats['classified']}, climate={stats['climate_filled']}, not_found={stats['not_found']}", flush=True)
    return classified


def step3_powo_api(remaining, already_done, dry_run=False):
    """Step 3: POWO API lookup for remaining plants."""
    print(f"\n=== STEP 3: POWO API ===", flush=True)

    todo = [p for p in remaining if p['plant_id'] not in already_done]
    print(f"  {len(todo)} plants remaining after Steps 1-2", flush=True)

    if dry_run:
        print(f"  Dry run — skipping API calls", flush=True)
        return set()

    stmts = []
    stats = {'classified': 0, 'not_found': 0, 'error': 0}
    classified = set()

    for i, plant in enumerate(todo):
        pid = plant['plant_id']
        sci = plant.get('scientific') or ''
        if not sci:
            stats['not_found'] += 1
            continue

        # POWO API lookup
        try:
            query = urllib.parse.quote(sci)
            url = f'https://powo.science.kew.org/api/2/search?q={query}&pageSize=1'
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            results = data.get('results', [])
            if not results:
                stats['not_found'] += 1
                time.sleep(0.5)
                continue

            r = results[0]
            # Extract lifeform from rank/accepted info
            fqId = r.get('fqId', '')
            # Need detail endpoint for lifeform
            detail_url = f'https://powo.science.kew.org/api/2/taxon/{fqId}'
            req2 = urllib.request.Request(detail_url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                detail = json.loads(resp2.read().decode())

            raw_lf = detail.get('lifeform', {}).get('freeformValue', '') if isinstance(detail.get('lifeform'), dict) else ''
            raw_cl = detail.get('climate', '') or ''

            lifeform = map_wcvp_lifeform(raw_lf) if raw_lf else None
            if lifeform:
                classified.add(pid)
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

        except Exception as e:
            stats['error'] += 1

        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(todo)}] classified={stats['classified']} miss={stats['not_found']} err={stats['error']}", flush=True)

        time.sleep(0.5)

    if stmts:
        turso_batch(stmts)

    print(f"  Step 3 done: classified={stats['classified']}, not_found={stats['not_found']}, error={stats['error']}", flush=True)
    return classified


def step4_family_fallback(remaining, already_done, dry_run=False):
    """Step 4: Family-based fallback for remaining plants."""
    print(f"\n=== STEP 4: Family fallback ===", flush=True)

    todo = [p for p in remaining if p['plant_id'] not in already_done]
    print(f"  {len(todo)} plants remaining after Steps 1-3", flush=True)

    stmts = []
    stats = {'classified': 0, 'no_family': 0, 'unknown_family': 0}

    for plant in todo:
        pid = plant['plant_id']
        family = plant.get('family') or ''

        if not family:
            stats['no_family'] += 1
            continue

        lifeform = FAMILY_MAP.get(family)
        if not lifeform:
            stats['unknown_family'] += 1
            continue

        stats['classified'] += 1
        if not dry_run:
            stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [lifeform, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'family_classify', 'lifeform', ?, datetime('now'))",
                [pid, lifeform]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'family_classify', 'lifeform_method', ?, datetime('now'))",
                [pid, f'family={family}']
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Step 4 done: classified={stats['classified']}, no_family={stats['no_family']}, unknown_family={stats['unknown_family']}", flush=True)


def show_results():
    """Show final classification results."""
    print(f"\n=== FINAL RESULTS ===", flush=True)
    rows = turso_query("SELECT preset, COUNT(*) as cnt FROM plants GROUP BY preset ORDER BY cnt DESC")
    for r in rows:
        marker = ' ✓' if r['preset'] in VALID_LIFEFORMS else ' ✗ OLD'
        print(f"  {r['preset'] or '(empty)':<15s} {r['cnt']:>6}{marker}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step_only = None
    if '--step' in sys.argv:
        idx = sys.argv.index('--step')
        if idx + 1 < len(sys.argv):
            step_only = int(sys.argv[idx + 1])

    remaining = get_remaining()
    if not remaining:
        print("Nothing to classify!", flush=True)
        sys.exit(0)

    all_done = set()

    if step_only is None or step_only == 1:
        done1 = step1_genus_from_db(remaining, dry_run)
        all_done |= done1

    if step_only is None or step_only == 2:
        done2 = step2_wcvp_csv(remaining, all_done, dry_run)
        all_done |= done2

    if step_only is None or step_only == 3:
        done3 = step3_powo_api(remaining, all_done, dry_run)
        all_done |= done3

    if step_only is None or step_only == 4:
        step4_family_fallback(remaining, all_done, dry_run)

    show_results()
