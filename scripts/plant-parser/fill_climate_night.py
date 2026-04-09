"""
Fill climate for 2,169 plants that have lifeform but no climate tag.
Uses IPNI→POWO for exact species climate, WCVP CSV genus fallback.
Only fills climate — does NOT touch lifeform/preset.

Usage:
    python3 fill_climate_night.py              # full run (~55 min)
    python3 fill_climate_night.py --dry-run    # preview
"""
import sys
import os
import csv
import json
import time
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

from turso_sync import turso_query, turso_batch

WCVP_CSV = '/private/tmp/wcvp_names.csv'


def ipni_powo_climate(scientific):
    """IPNI search → POWO detail → climate. Returns climate string or None."""
    try:
        q = urllib.parse.quote(scientific)
        url = f'https://www.ipni.org/api/1/search?q={q}&perPage=1'
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        results = data.get('results', [])
        if not results:
            return None

        fqId = results[0].get('fqId', '')
        if not fqId:
            return None

        detail_url = f'https://powo.science.kew.org/api/2/taxon/{fqId}'
        req2 = urllib.request.Request(detail_url, headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            detail = json.loads(resp2.read().decode())

        # Follow accepted name if synonym
        if detail.get('synonym') and detail.get('accepted'):
            acc_fqId = detail['accepted'].get('fqId', '')
            if acc_fqId:
                req3 = urllib.request.Request(
                    f'https://powo.science.kew.org/api/2/taxon/{acc_fqId}',
                    headers={'Accept': 'application/json', 'User-Agent': 'PlantApp/1.0'})
                with urllib.request.urlopen(req3, timeout=15) as resp3:
                    detail = json.loads(resp3.read().decode())

        return detail.get('climate', '') or None
    except Exception:
        return None


def load_wcvp_genus_climate():
    """Load WCVP CSV → genus → dominant climate."""
    if not os.path.exists(WCVP_CSV):
        print(f"  WCVP CSV not found at {WCVP_CSV}", flush=True)
        return {}

    print(f"  Loading WCVP CSV for genus climate fallback...", flush=True)
    genus_climate = {}  # genus → {climate: count}

    with open(WCVP_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)  # skip header
        for row in reader:
            if len(row) > 20 and row[3] == 'Accepted':
                genus = row[6].strip()  # column 6 = genus
                climate = row[20].strip()  # column 20 = climate_description
                if genus and climate:
                    if genus not in genus_climate:
                        genus_climate[genus] = {}
                    genus_climate[genus][climate] = genus_climate[genus].get(climate, 0) + 1

    # Convert to dominant climate per genus
    result = {}
    for genus, climates in genus_climate.items():
        dominant = max(climates, key=climates.get)
        total = sum(climates.values())
        # Only use if >50% dominant
        if climates[dominant] / total > 0.5:
            result[genus] = dominant

    print(f"  WCVP genus climate: {len(result)} genera", flush=True)
    return result


def run(dry_run=False):
    # Get plants with lifeform but no climate
    plants = turso_query("""
        SELECT plant_id, scientific, genus, preset
        FROM plants
        WHERE preset NOT IN ('standard', 'herb', 'tropical')
        AND (climate IS NULL OR climate = '')
        AND scientific IS NOT NULL AND scientific != ''
    """)
    print(f"[fill_climate] {len(plants)} plants need climate", flush=True)

    # Load WCVP genus fallback
    wcvp_genus = load_wcvp_genus_climate()

    stmts = []
    stats = {'powo': 0, 'wcvp_genus': 0, 'not_found': 0, 'error': 0}
    consecutive_errors = 0

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        sci = plant.get('scientific') or ''
        genus = plant.get('genus') or ''
        if not genus and ' ' in sci:
            genus = sci.split()[0]

        climate = None
        source = None

        # Step 1: IPNI → POWO
        climate = ipni_powo_climate(sci)
        if climate:
            source = 'powo_climate'
            stats['powo'] += 1
            consecutive_errors = 0
        else:
            # Step 2: WCVP genus fallback
            if genus and genus in wcvp_genus:
                climate = wcvp_genus[genus]
                source = 'wcvp_genus_climate'
                stats['wcvp_genus'] += 1
            else:
                stats['not_found'] += 1

        if climate and not dry_run:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ?", [climate, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'climate', ?, datetime('now'))",
                [pid, source, climate]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        # Rate limit for POWO
        time.sleep(0.5)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(plants)}] powo={stats['powo']} wcvp_genus={stats['wcvp_genus']} miss={stats['not_found']}", flush=True)

        # Stop on 5 consecutive POWO failures (API down)
        if not climate and source is None:
            consecutive_errors += 1
            if consecutive_errors >= 10:
                print(f"  10 consecutive misses — might be API issue, continuing with WCVP only", flush=True)
                # Switch to WCVP-only mode for remaining
                for j in range(i + 1, len(plants)):
                    p2 = plants[j]
                    g2 = p2.get('genus') or ''
                    if not g2 and ' ' in (p2.get('scientific') or ''):
                        g2 = p2['scientific'].split()[0]
                    if g2 and g2 in wcvp_genus:
                        cl2 = wcvp_genus[g2]
                        stats['wcvp_genus'] += 1
                        if not dry_run:
                            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ?", [cl2, p2['plant_id']]))
                            stmts.append((
                                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wcvp_genus_climate', 'climate', ?, datetime('now'))",
                                [p2['plant_id'], cl2]
                            ))
                            if len(stmts) >= 100:
                                turso_batch(stmts)
                                stmts = []
                    else:
                        stats['not_found'] += 1
                break
        else:
            consecutive_errors = 0

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[fill_climate] Done:", flush=True)
    print(f"  POWO:        {stats['powo']}", flush=True)
    print(f"  WCVP genus:  {stats['wcvp_genus']}", flush=True)
    print(f"  Not found:   {stats['not_found']}", flush=True)

    if not dry_run:
        remaining = turso_query("SELECT COUNT(*) as c FROM plants WHERE preset NOT IN ('standard') AND (climate IS NULL OR climate = '')")
        print(f"  Still without climate: {remaining[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
