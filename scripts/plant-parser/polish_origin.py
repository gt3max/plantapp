"""
Polish origin — fill geographic origin for all plants from multiple sources.

Priority: WCVP geographic_area > PFAF range > MiFloraDB origin > GBIF
Does NOT overwrite existing origin. Sources logged to source_data.

Step 1: WCVP geographic_area (400K records, highest coverage)
Step 2: PFAF range (8,500 records)
Step 3: MiFloraDB origin (5,534 records)
Step 4: Stats

Usage:
    python3 polish_origin.py --dry-run
    python3 polish_origin.py
"""
import sys
import os
import re
import csv
import sqlite3

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

DATA_DIR = Path(__file__).parent / 'data'
WCVP_PATH = Path('/private/tmp/wcvp_names.csv')


def normalize_name(name):
    if not name:
        return ''
    return re.sub(r'\s+', ' ', name.lower().strip().split(' var.')[0].split(' subsp.')[0])


def step1_wcvp(dry_run, filled):
    """Extract origin from WCVP geographic_area."""
    print("\n=== STEP 1: WCVP Geographic Area ===", flush=True)

    if not WCVP_PATH.exists():
        print("  WCVP file not found, skipping", flush=True)
        return

    # Load plants without origin
    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    need_origin = turso_query("SELECT plant_id FROM plants WHERE origin IS NULL OR origin = ''")
    need_set = set(r['plant_id'] for r in need_origin)

    # Build name → plant_id mapping
    name_to_pid = {}
    for p in plants:
        norm = normalize_name(p['scientific'])
        if norm:
            name_to_pid[norm] = p['plant_id']

    print(f"  Plants needing origin: {len(need_set)}", flush=True)
    print(f"  Loading WCVP (large file)...", flush=True)

    matched = 0
    stmts = []

    with open(WCVP_PATH, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='|')
        for row in reader:
            status = (row.get('taxon_status') or '').strip()
            if status != 'Accepted':
                continue

            taxon_name = (row.get('taxon_name') or '').strip()
            geo = (row.get('geographic_area') or '').strip()
            if not taxon_name or not geo:
                continue

            norm = normalize_name(taxon_name)
            pid = name_to_pid.get(norm)
            if not pid or pid not in need_set:
                continue

            # Already filled this session
            if pid in filled:
                continue

            filled[pid] = geo
            matched += 1

            if not dry_run:
                stmts.append((
                    "UPDATE plants SET origin = ? WHERE plant_id = ? AND (origin IS NULL OR origin = '')",
                    [geo, pid]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wcvp', 'origin', ?, datetime('now'))",
                    [pid, geo]
                ))

                if len(stmts) >= 200:
                    turso_batch(stmts)
                    stmts = []

            if matched % 500 == 0:
                print(f"  [{matched}] matched...", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  WCVP origin filled: {matched}", flush=True)


def step2_pfaf(dry_run, filled):
    """Extract origin from PFAF range."""
    print("\n=== STEP 2: PFAF Range ===", flush=True)

    pfaf_db = DATA_DIR / 'pfaf' / 'data.sqlite'
    if not pfaf_db.exists():
        print("  PFAF database not found, skipping", flush=True)
        return

    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    need_origin = turso_query("SELECT plant_id FROM plants WHERE origin IS NULL OR origin = ''")
    need_set = set(r['plant_id'] for r in need_origin) - set(filled.keys())

    conn = sqlite3.connect(str(pfaf_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT latin_name, range FROM plants WHERE range IS NOT NULL AND range != ''").fetchall()
    conn.close()

    matched = 0
    stmts = []

    for row in rows:
        pid = name_to_pid.get(normalize_name(row['latin_name']))
        if not pid or pid not in need_set or pid in filled:
            continue

        range_text = row['range'].strip()
        if not range_text or range_text.lower() in ('not known', 'unknown', 'the original habitat is obscure.'):
            continue

        filled[pid] = range_text
        matched += 1

        if not dry_run:
            stmts.append((
                "UPDATE plants SET origin = ? WHERE plant_id = ? AND (origin IS NULL OR origin = '')",
                [range_text, pid]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_origin', 'origin', ?, datetime('now'))",
                [pid, range_text]
            ))

            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  PFAF origin filled: {matched}", flush=True)


def step3_miflora(dry_run, filled):
    """Extract origin from MiFloraDB."""
    print("\n=== STEP 3: MiFloraDB Origin ===", flush=True)

    csv_path = DATA_DIR / 'mifloradb_5335.csv'
    if not csv_path.exists():
        print("  MiFloraDB CSV not found, skipping", flush=True)
        return

    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    need_origin = turso_query("SELECT plant_id FROM plants WHERE origin IS NULL OR origin = ''")
    need_set = set(r['plant_id'] for r in need_origin) - set(filled.keys())

    matched = 0
    stmts = []

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid_csv = (row.get('pid') or '').strip()
            origin = (row.get('origin') or '').strip()
            if not pid_csv or not origin:
                continue

            pid = name_to_pid.get(normalize_name(pid_csv))
            if not pid or pid not in need_set or pid in filled:
                continue

            filled[pid] = origin
            matched += 1

            if not dry_run:
                stmts.append((
                    "UPDATE plants SET origin = ? WHERE plant_id = ? AND (origin IS NULL OR origin = '')",
                    [origin, pid]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'miflora_origin', 'origin', ?, datetime('now'))",
                    [pid, origin]
                ))

                if len(stmts) >= 200:
                    turso_batch(stmts)
                    stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  MiFloraDB origin filled: {matched}", flush=True)


def step4_stats(filled):
    """Show final stats."""
    print("\n=== STEP 4: Results ===", flush=True)

    total = turso_query("SELECT COUNT(*) as c FROM plants")[0]['c']
    has_origin = turso_query("SELECT COUNT(*) as c FROM plants WHERE origin IS NOT NULL AND origin != ''")[0]['c']

    print(f"  Origin coverage: {has_origin}/{total} ({100*has_origin//total}%)", flush=True)
    print(f"  Filled this run: {len(filled)}", flush=True)

    # By lifeform
    dist = turso_query(
        "SELECT p.preset, COUNT(*) as total, SUM(CASE WHEN p.origin IS NOT NULL AND p.origin != '' THEN 1 ELSE 0 END) as has_origin FROM plants p WHERE p.preset IS NOT NULL AND p.preset != '' GROUP BY p.preset ORDER BY total DESC"
    )
    print(f"\n  {'Lifeform':15s} {'Total':>7s} {'Origin':>7s} {'%':>5s}", flush=True)
    for d in dist:
        pct = 100 * d['has_origin'] // d['total'] if d['total'] > 0 else 0
        print(f"  {d['preset']:15s} {d['total']:7d} {d['has_origin']:7d} {pct:4d}%", flush=True)

    # Source breakdown
    sources = {}
    for pid, val in filled.items():
        # Determine source from order of priority
        pass

    # Samples
    print(f"\n  Sample origins:", flush=True)
    samples = turso_query(
        "SELECT plant_id, origin FROM plants WHERE origin IS NOT NULL AND origin != '' ORDER BY RANDOM() LIMIT 10"
    )
    for s in samples:
        print(f"    {s['plant_id']:35s} {s['origin'][:60]}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    filled = {}  # {plant_id: origin_text}

    step1_wcvp(dry_run, filled)
    step2_pfaf(dry_run, filled)
    step3_miflora(dry_run, filled)
    step4_stats(filled)
