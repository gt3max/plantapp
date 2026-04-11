"""
Polish humidity — fix humidity classification using multiple sources.

Problem: 91.8% plants = "Average (40-60%)" — crude default.
wet tropical forests and deserts both marked "Average". Wrong.

Sources: MiFloraDB env_humid, Ellenberg F, PFAF moisture, Climate zone, Lifeform.
Only overwrites "Average (40-60%)". Never touches already-refined values.
All sources logged to source_data. Featured 40 protected.

Usage:
    python3 polish_humidity.py --dry-run
    python3 polish_humidity.py
"""
import sys
import os
import re
import csv
import sqlite3
import time

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

DEFAULT_HUMIDITY = 'Average (40-60%)'

FEATURED_PLANTS = {
    'monstera_deliciosa', 'epipremnum_aureum', 'dracaena_trifasciata', 'crassula_ovata',
    'spathiphyllum_wallisii', 'ficus_lyrata', 'ficus_elastica', 'aloe_vera',
    'zamioculcas_zamiifolia', 'chlorophytum_comosum', 'phalaenopsis_amabilis', 'calathea_orbifolia',
    'dracaena_marginata', 'philodendron_hederaceum', 'monstera_adansonii', 'ocimum_basilicum',
    'rosmarinus_officinalis', 'solanum_lycopersicum', 'nephrolepis_exaltata', 'anthurium_andraeanum',
    'strelitzia_reginae', 'echeveria_elegans', 'mentha_spicata', 'dieffenbachia_seguine',
    'lavandula_angustifolia', 'dracaena_fragrans', 'dypsis_lutescens', 'cycas_revoluta',
    'aglaonema_commutatum', 'alocasia_amazonica', 'maranta_leuconeura', 'haworthia_fasciata',
    'sedum_morganianum', 'opuntia_microdasys', 'begonia_rex-cultorum', 'saintpaulia_ionantha',
    'hibiscus_rosa-sinensis', 'adiantum_raddianum', 'asplenium_nidus', 'platycerium_bifurcatum',
}

# Humidity levels
HUMIDITY_LOW = 'Low (20-40%)'
HUMIDITY_AVG = 'Average (40-60%)'
HUMIDITY_HIGH = 'High (60-80%)'
HUMIDITY_VERY_HIGH = 'Very high (70-90%)'

# Climate → humidity mapping
CLIMATE_HUMIDITY = {
    'wet tropical': HUMIDITY_HIGH,
    'montane tropical': HUMIDITY_HIGH,
    'seasonally dry tropical': HUMIDITY_AVG,
    'subtropical': HUMIDITY_AVG,
    'subtropical or tropical': HUMIDITY_AVG,
    'temperate': HUMIDITY_AVG,
    'desert or dry shrubland': HUMIDITY_LOW,
    'subalpine or subarctic': HUMIDITY_LOW,
}

# Lifeform overrides (stronger than climate for these types)
LIFEFORM_HUMIDITY = {
    'epiphyte': HUMIDITY_HIGH,
    'fern': HUMIDITY_HIGH,
    'moss': HUMIDITY_VERY_HIGH,
    'aquatic': HUMIDITY_VERY_HIGH,
    'succulent': HUMIDITY_LOW,
    'cactus': HUMIDITY_LOW,
}

# PFAF moisture codes → humidity
PFAF_MOISTURE_MAP = {
    'D': HUMIDITY_LOW,
    'DM': HUMIDITY_AVG,
    'M': HUMIDITY_HIGH,
    'MWe': HUMIDITY_HIGH,
    'We': HUMIDITY_HIGH,
    'WeWa': HUMIDITY_VERY_HIGH,
    'Wa': HUMIDITY_VERY_HIGH,
}


def normalize_name(name):
    if not name:
        return ''
    return re.sub(r'\s+', ' ', name.lower().strip().split(' var.')[0].split(' subsp.')[0])


def retry_query(sql, params=None, retries=3):
    for attempt in range(retries):
        try:
            return turso_query(sql, params)
        except Exception as e:
            if attempt < retries - 1 and 'timeout' in str(e).lower():
                print(f"  [retry {attempt+1}] Turso timeout, waiting 10s...", flush=True)
                time.sleep(10)
            else:
                raise


def step1_miflora(dry_run, votes):
    """Extract MiFloraDB min/max_env_humid → humidity_min_pct + vote."""
    print("\n=== STEP 1: MiFloraDB Humidity ===", flush=True)

    csv_path = DATA_DIR / 'mifloradb_5335.csv'
    if not csv_path.exists():
        print("  MiFloraDB not found, skipping", flush=True)
        return

    plants = retry_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    matched = 0
    stmts = []

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid_csv = (row.get('pid') or '').strip()
            min_h = (row.get('min_env_humid') or '').strip()
            max_h = (row.get('max_env_humid') or '').strip()
            if not pid_csv or not min_h or not max_h:
                continue

            pid = name_to_pid.get(normalize_name(pid_csv))
            if not pid:
                continue

            try:
                min_val = int(min_h)
                max_val = int(max_h)
            except ValueError:
                continue

            matched += 1
            mid = (min_val + max_val) // 2

            # Vote based on midpoint
            if mid <= 35:
                vote = HUMIDITY_LOW
            elif mid <= 55:
                vote = HUMIDITY_AVG
            elif mid <= 75:
                vote = HUMIDITY_HIGH
            else:
                vote = HUMIDITY_VERY_HIGH

            if pid not in votes:
                votes[pid] = []
            votes[pid].append(('miflora', vote, 3))  # weight 3

            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'miflora_humidity', 'env_humid_range', ?, datetime('now'))",
                    [pid, f'{min_val}-{max_val}%']
                ))
                # Update humidity_min_pct only if currently 0
                stmts.append((
                    "UPDATE care SET humidity_min_pct = CASE WHEN humidity_min_pct IS NULL OR humidity_min_pct = 0 THEN ? ELSE humidity_min_pct END WHERE plant_id = ?",
                    [min_val, pid]
                ))

                if len(stmts) >= 200:
                    turso_batch(stmts)
                    stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  MiFloraDB matched: {matched}", flush=True)


def step2_ellenberg(dry_run, votes):
    """Ellenberg F → humidity vote."""
    print("\n=== STEP 2: Ellenberg F ===", flush=True)

    rows = retry_query("SELECT plant_id, ellenberg_f FROM care WHERE ellenberg_f IS NOT NULL AND ellenberg_f > 0")

    voted = 0
    stmts = []

    for r in rows:
        pid = r['plant_id']
        f = r['ellenberg_f']

        if f <= 2:
            vote = HUMIDITY_LOW
        elif f <= 5:
            vote = HUMIDITY_AVG
        elif f <= 8:
            vote = HUMIDITY_HIGH
        else:
            vote = HUMIDITY_VERY_HIGH

        if pid not in votes:
            votes[pid] = []
        votes[pid].append(('ellenberg_f', vote, 4))  # weight 4 — scientific
        voted += 1

        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'ellenberg_humidity', 'humidity_vote', ?, datetime('now'))",
                [pid, f'{vote} (F={f})']
            ))

            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Ellenberg F votes: {voted}", flush=True)


def step3_pfaf(dry_run, votes):
    """PFAF moisture → humidity vote."""
    print("\n=== STEP 3: PFAF Moisture ===", flush=True)

    rows = retry_query("SELECT plant_id, value FROM source_data WHERE field = 'moisture'")

    voted = 0
    stmts = []

    for r in rows:
        pid = r['plant_id']
        moisture = r['value'].strip()

        vote = PFAF_MOISTURE_MAP.get(moisture)
        if not vote:
            continue

        if pid not in votes:
            votes[pid] = []
        votes[pid].append(('pfaf_moisture', vote, 2))  # weight 2
        voted += 1

        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_humidity', 'humidity_vote', ?, datetime('now'))",
                [pid, f'{vote} (moisture={moisture})']
            ))

            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  PFAF moisture votes: {voted}", flush=True)


def step4_climate_lifeform(dry_run, votes):
    """Climate + Lifeform defaults for remaining."""
    print("\n=== STEP 4: Climate + Lifeform ===", flush=True)

    rows = retry_query("SELECT c.plant_id, p.climate, p.preset FROM care c JOIN plants p ON c.plant_id = p.plant_id")

    added = 0
    stmts = []

    for r in rows:
        pid = r['plant_id']

        # Skip if already has votes from better sources
        if pid in votes:
            continue

        climate = (r['climate'] or '').lower().strip()
        preset = (r['preset'] or '').lower().strip()

        # Lifeform override first
        vote = LIFEFORM_HUMIDITY.get(preset)
        source = f'lifeform={preset}'

        # Then climate
        if not vote:
            vote = CLIMATE_HUMIDITY.get(climate)
            source = f'climate={climate}'

        if not vote:
            continue

        votes[pid] = [('climate_lifeform', vote, 1)]  # weight 1
        added += 1

        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'humidity_climate_default', 'humidity_vote', ?, datetime('now'))",
                [pid, f'{vote} ({source})']
            ))

            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Climate/lifeform defaults: {added}", flush=True)


def step5_apply(dry_run, votes):
    """Apply fixes — only change 'Average (40-60%)'."""
    print("\n=== STEP 5: Apply Fixes ===", flush=True)

    # Get all plants with default humidity
    defaults = retry_query(f"SELECT plant_id, humidity_level FROM care WHERE humidity_level = '{DEFAULT_HUMIDITY}'")
    default_set = set(r['plant_id'] for r in defaults)

    fixes = []
    for pid, vote_list in votes.items():
        if pid.endswith('__') or pid not in default_set:
            continue
        if pid in FEATURED_PLANTS:
            continue

        # Weighted vote
        level_scores = {}
        total_weight = 0
        for source, vote, weight in vote_list:
            level_scores[vote] = level_scores.get(vote, 0) + weight
            total_weight += weight

        if not level_scores:
            continue

        # Winner
        winner = max(level_scores, key=level_scores.get)

        # Only fix if winner is NOT Average
        if winner != HUMIDITY_AVG:
            sources_str = ', '.join(f'{s}({w})' for s, v, w in vote_list)
            fixes.append((pid, DEFAULT_HUMIDITY, winner, sources_str))

    print(f"  Fixes identified: {len(fixes)}", flush=True)

    if dry_run:
        from collections import Counter
        changes = Counter()
        for _, old, new, _ in fixes:
            changes[f'{old} → {new}'] += 1
        print("  Distribution:", flush=True)
        for change, count in changes.most_common():
            print(f"    {change}: {count}", flush=True)

        print("\n  Samples:", flush=True)
        for pid, old, new, sources in fixes[:15]:
            print(f"    {pid:35s} → {new:25s} | {sources[:60]}", flush=True)
        return

    stmts = []
    for pid, old, new, sources in fixes:
        stmts.append((
            "UPDATE care SET humidity_level = ? WHERE plant_id = ?",
            [new, pid]
        ))
        stmts.append((
            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'humidity_polish', 'changed', ?, datetime('now'))",
            [pid, f'{old} → {new}: {sources[:200]}']
        ))

        if len(stmts) >= 200:
            turso_batch(stmts)
            stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"  Applied: {len(fixes)} fixes", flush=True)


def step6_stats():
    """Show final stats."""
    print("\n=== STEP 6: Results ===", flush=True)

    dist = retry_query("SELECT humidity_level, COUNT(*) as c FROM care WHERE humidity_level IS NOT NULL AND humidity_level != '' GROUP BY humidity_level ORDER BY c DESC")
    total = sum(d['c'] for d in dist)
    print("  Humidity distribution:", flush=True)
    for d in dist:
        pct = 100 * d['c'] // total
        print(f"    {d['humidity_level']:25s} {d['c']:6d} ({pct}%)", flush=True)

    # humidity_min_pct coverage
    min_pct = retry_query("SELECT COUNT(*) as c FROM care WHERE humidity_min_pct IS NOT NULL AND humidity_min_pct > 0")[0]['c']
    print(f"\n  humidity_min_pct filled: {min_pct}/{total}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    votes = {}

    step1_miflora(dry_run, votes)
    step2_ellenberg(dry_run, votes)
    step3_pfaf(dry_run, votes)
    step4_climate_lifeform(dry_run, votes)
    step5_apply(dry_run, votes)
    step6_stats()
