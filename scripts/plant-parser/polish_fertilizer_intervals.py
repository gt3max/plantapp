"""
Polish fertilizer intervals — convert text frequencies to numeric days + active months.

Step 1: MiFloraDB fertilization text → interval_days + active_months
Step 2: Parse care.fertilizer_freq → interval_days (fallback)
Step 3: Parse care.fertilizer_season → active_months (for all)
Step 4: Cross-validate with PFAF feed_intensity + USDA fertility_requirement
Step 5: Lifeform defaults for remaining
Step 6: Write to care table

Usage:
    python3 polish_fertilizer_intervals.py --dry-run
    python3 polish_fertilizer_intervals.py
"""
import sys
import os
import re
import csv
import json
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

# ── Season → months mapping ──────────────────────────────────────────
SEASON_MONTHS = {
    'spring': [3, 4, 5],
    'summer': [6, 7, 8],
    'fall': [9, 10, 11],
    'autumn': [9, 10, 11],
    'winter': [12, 1, 2],
    'growing season': [3, 4, 5, 6, 7, 8, 9],
    'active growth': [3, 4, 5, 6, 7, 8],
}

MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

# ── Lifeform defaults (from polish_fertilizer_v2.py) ─────────────────
LIFEFORM_DEFAULTS = {
    'succulent':  {'interval': 30, 'months': [4, 5, 6, 7, 8]},
    'epiphyte':   {'interval': 14, 'months': [3, 4, 5, 6, 7, 8, 9, 10]},
    'climber':    {'interval': 21, 'months': [3, 4, 5, 6, 7, 8]},
    'tree':       {'interval': 35, 'months': [3, 4, 5, 6, 7, 8]},
    'shrub':      {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'subshrub':   {'interval': 21, 'months': [3, 4, 5, 6, 7, 8]},
    'perennial':  {'interval': 21, 'months': [3, 4, 5, 6, 7, 8]},
    'annual':     {'interval': 10, 'months': [3, 4, 5, 6, 7, 8]},
    'bulb':       {'interval': 0,  'months': [3]},
    'aquatic':    {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'fern':       {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'bamboo':     {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'moss':       {'interval': 0,  'months': []},
    'palm':       {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'grass':      {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'cycad':      {'interval': 30, 'months': [3, 4, 5, 6, 7, 8]},
    'cactus':     {'interval': 30, 'months': [4, 5, 6, 7, 8]},
    'parasite':   {'interval': 0,  'months': []},
}

# ── Fertility adjustment ─────────────────────────────────────────────
FERTILITY_ADJUST = {
    'high': 0.75,
    'medium': 1.0,
    'low': 1.5,
}


def normalize_name(name):
    """Normalize scientific name for matching."""
    if not name:
        return ''
    return re.sub(r'\s+', ' ', name.lower().strip().split(' var.')[0].split(' subsp.')[0])


def extract_months_from_text(text):
    """Extract active months from text mentioning seasons or month names."""
    t = text.lower()
    months = set()

    # Check season keywords
    for season, ms in SEASON_MONTHS.items():
        if season in t:
            months.update(ms)

    # Check month names
    for name, num in MONTH_NAMES.items():
        if name in t:
            months.add(num)

    # "spring and summer", "spring to autumn" patterns
    if 'spring' in t and ('summer' in t or 'autumn' in t or 'fall' in t):
        months.update([3, 4, 5, 6, 7, 8])
        if 'autumn' in t or 'fall' in t:
            months.update([9, 10, 11])

    return sorted(months) if months else None


def parse_miflora_interval(text):
    """Parse MiFloraDB fertilization text → (interval_days, active_months)."""
    t = text.lower()
    interval = None

    # No fertilizer needed
    if any(x in t for x in ['no much requirement', 'no need', 'no requirement']):
        return 0, []

    # "base fertilizers" only = at planting, no recurring
    if 'base fertilizer' in t and 'top-dress' not in t and 'monthly' not in t:
        return 0, []

    # N-M times monthly
    m = re.search(r'(\d+)\s*-\s*(\d+)\s*times?\s*monthly', t)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        mid = (lo + hi) / 2
        interval = round(30 / mid)

    # N times monthly
    if interval is None:
        m = re.search(r'(\d+)\s*times?\s*monthly', t)
        if m:
            interval = round(30 / int(m.group(1)))

    # every N-M days
    if interval is None:
        m = re.search(r'every\s*(\d+)\s*-\s*(\d+)\s*days?', t)
        if m:
            interval = round((int(m.group(1)) + int(m.group(2))) / 2)

    # every N days
    if interval is None:
        m = re.search(r'every\s*(\d+)\s*days?', t)
        if m:
            interval = int(m.group(1))

    # once every 10-15 days
    if interval is None:
        m = re.search(r'once\s+every\s+(\d+)\s*-\s*(\d+)\s*days?', t)
        if m:
            interval = round((int(m.group(1)) + int(m.group(2))) / 2)

    # half month / every 2 weeks
    if interval is None:
        if 'half month' in t or 'every 2 weeks' in t or 'every two weeks' in t:
            interval = 15

    # every N-M months
    if interval is None:
        m = re.search(r'every\s*(\d+)\s*-\s*(\d+)\s*months?', t)
        if m:
            interval = round((int(m.group(1)) + int(m.group(2))) / 2 * 30)

    # once monthly / once a month
    if interval is None:
        if re.search(r'once\s+(?:a\s+)?month', t) or t.strip().endswith('once monthly'):
            interval = 30

    # "monthly" as standalone
    if interval is None and 'monthly' in t and 'times' not in t:
        interval = 30

    # weekly
    if interval is None:
        if re.search(r'\bweekly\b', t):
            interval = 7

    # Generic "apply fertilizer during growing time" — no specific interval
    if interval is None and ('apply fertilizer' in t or 'enjoy much fertilizer' in t):
        interval = 21  # default moderate

    months = extract_months_from_text(text)
    if months is None:
        months = [3, 4, 5, 6, 7, 8]  # default growing season

    if interval is not None:
        interval = max(7, min(90, interval))

    return interval, months


def parse_freq_text(text):
    """Parse care.fertilizer_freq text → interval_days."""
    t = text.lower().strip()

    if 'rarely' in t or 'never' in t:
        return 0

    if 'at planting' in t and 'week' not in t and 'month' not in t:
        return 0

    # "Every N-M weeks"
    m = re.search(r'every\s+(\d+)\s*-\s*(\d+)\s*weeks?', t)
    if m:
        lo, hi = int(m.group(1)) * 7, int(m.group(2)) * 7
        return round((lo + hi) / 2)

    # "Every N weeks"
    m = re.search(r'every\s+(\d+)\s*weeks?', t)
    if m:
        return int(m.group(1)) * 7

    # "Weekly to biweekly"
    if 'weekly to biweekly' in t:
        return 10

    if 'biweekly' in t or 'bi-weekly' in t:
        return 14

    if re.search(r'\bweekly\b', t):
        return 7

    # "Every N-M months"
    m = re.search(r'every\s+(\d+)\s*-\s*(\d+)\s*months?', t)
    if m:
        return round((int(m.group(1)) + int(m.group(2))) / 2 * 30)

    # Monthly
    if 'monthly' in t or 'every month' in t or 'once a month' in t:
        return 30

    # "2-3 times in growing season"
    m = re.search(r'(\d+)\s*-\s*(\d+)\s*times?\s*(?:in|during)', t)
    if m:
        mid = (int(m.group(1)) + int(m.group(2))) / 2
        return round(180 / mid)  # spread over ~6 months growing season

    # "Once in spring, once in summer" = 2 times over ~6 months = ~90 days
    if re.search(r'once\s+in\s+spring.*once\s+in\s+summer', t):
        return 90

    # "Once in spring" alone = single application
    if re.search(r'once\s+in\s+spring', t) and 'once in summer' not in t:
        return 90  # single but seasonal, remind next season

    return None


def parse_season_to_months(text):
    """Parse fertilizer_season text → list of month numbers."""
    if not text:
        return None
    t = text.lower().strip()

    months = set()

    # Split on comma and process each part
    for part in re.split(r'[,/&]+', t):
        part = part.strip()
        if not part:
            continue

        # Direct season match
        for season, ms in SEASON_MONTHS.items():
            if season in part:
                months.update(ms)
                break

        # "spring-summer" or "spring through fall"
        if 'through' in part or '-' in part:
            parts = re.split(r'\s*(?:through|-|to)\s*', part)
            for p in parts:
                p = p.strip()
                for season, ms in SEASON_MONTHS.items():
                    if season == p:
                        months.update(ms)

    # Year-round
    if 'year' in t and 'round' in t:
        months = set(range(1, 13))

    # "All growing season"
    if 'all' in t and 'growing' in t:
        months.update([3, 4, 5, 6, 7, 8, 9])

    # "Spring-Summer" compound
    if 'spring-summer' in t or 'spring summer' in t:
        months.update([3, 4, 5, 6, 7, 8])

    # "Spring-Autumn"
    if 'spring-autumn' in t or 'spring-fall' in t:
        months.update([3, 4, 5, 6, 7, 8, 9, 10, 11])

    return sorted(months) if months else None


# ═══════════════════════════════════════════════════════════════════════

def step1_miflora(dry_run, results):
    """Step 1: Parse MiFloraDB fertilization → interval + months."""
    print("\n=== STEP 1: MiFloraDB Fertilization ===", flush=True)

    # Load all plant scientific names from DB
    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {}
    for p in plants:
        norm = normalize_name(p['scientific'])
        if norm:
            name_to_pid[norm] = p['plant_id']

    csv_path = DATA_DIR / 'mifloradb_5335.csv'
    if not csv_path.exists():
        print("  MiFloraDB CSV not found, skipping", flush=True)
        return

    matched = 0
    parsed = 0
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid_csv = row.get('pid', '').strip()
            fert_text = row.get('fertilization', '').strip()
            if not pid_csv or not fert_text:
                continue

            norm = normalize_name(pid_csv)
            plant_id = name_to_pid.get(norm)
            if not plant_id:
                continue

            matched += 1
            interval, months = parse_miflora_interval(fert_text)
            if interval is not None:
                results[plant_id] = {
                    'interval_days': interval,
                    'active_months': months,
                    'source': 'miflora',
                }
                parsed += 1

    print(f"  CSV matched to DB: {matched}", flush=True)
    print(f"  Intervals parsed:  {parsed}", flush=True)


def step2_care_freq(dry_run, results):
    """Step 2: Parse care.fertilizer_freq text → interval_days."""
    print("\n=== STEP 2: Parse care.fertilizer_freq ===", flush=True)

    rows = turso_query("SELECT plant_id, fertilizer_freq FROM care WHERE fertilizer_freq IS NOT NULL AND fertilizer_freq != ''")
    parsed = 0
    skipped_already = 0

    for row in rows:
        pid = row['plant_id']
        if pid in results:
            skipped_already += 1
            continue

        interval = parse_freq_text(row['fertilizer_freq'])
        if interval is not None:
            # Clamp
            if interval > 0:
                interval = max(7, min(90, interval))
            results[pid] = {
                'interval_days': interval,
                'active_months': results.get(pid, {}).get('active_months', [3, 4, 5, 6, 7, 8]),
                'source': 'care_freq_text',
            }
            parsed += 1

    print(f"  Already from Step 1: {skipped_already}", flush=True)
    print(f"  Parsed from freq text: {parsed}", flush=True)


def step3_season(dry_run, results):
    """Step 3: Parse fertilizer_season → active_months for ALL plants."""
    print("\n=== STEP 3: Parse fertilizer_season ===", flush=True)

    rows = turso_query("SELECT plant_id, fertilizer_season FROM care WHERE fertilizer_season IS NOT NULL AND fertilizer_season != ''")
    updated = 0

    for row in rows:
        pid = row['plant_id']
        months = parse_season_to_months(row['fertilizer_season'])
        if months:
            if pid in results:
                # Always prefer fertilizer_season if it has more months or current is sparse
                cur = results[pid].get('active_months', [])
                if len(months) >= len(cur) or len(cur) <= 1:
                    results[pid]['active_months'] = months
                    updated += 1
            else:
                # Plant has season but no interval yet — store months, interval will come from step 5
                results[pid] = {
                    'interval_days': None,
                    'active_months': months,
                    'source': 'season_only',
                }
                updated += 1

    print(f"  Months updated/set: {updated}", flush=True)


def step4_cross_validate(dry_run, results):
    """Step 4: Adjust intervals using PFAF feed_intensity + USDA fertility_requirement."""
    print("\n=== STEP 4: Cross-validate PFAF + USDA ===", flush=True)

    # PFAF feed intensity from source_data
    pfaf_rows = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf_fertilizer' AND field = 'feed_intensity'")
    pfaf_fert = {r['plant_id']: r['value'].lower() for r in pfaf_rows}
    print(f"  PFAF feed_intensity: {len(pfaf_fert)} plants", flush=True)

    # USDA fertility_requirement
    usda_fert = {}
    usda_path = DATA_DIR / 'usda_plant_characteristics.csv'
    if usda_path.exists():
        plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
        name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

        with open(usda_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sci = row.get('Scientific Name', row.get('scientific_name', '')).strip()
                fert = row.get('fertility_requirement', row.get('Fertility Requirement', '')).strip()
                if sci and fert:
                    pid = name_to_pid.get(normalize_name(sci))
                    if pid:
                        usda_fert[pid] = fert.lower()
        print(f"  USDA fertility_req: {len(usda_fert)} matched", flush=True)

    adjusted_up = 0
    adjusted_down = 0

    for pid, data in results.items():
        interval = data.get('interval_days')
        if interval is None or interval == 0:
            continue

        # Get fertility level from either source
        level = pfaf_fert.get(pid) or usda_fert.get(pid)
        if not level:
            continue

        factor = FERTILITY_ADJUST.get(level, 1.0)
        if factor == 1.0:
            continue

        new_interval = max(7, min(90, round(interval * factor)))
        if new_interval != interval:
            if new_interval < interval:
                adjusted_up += 1
            else:
                adjusted_down += 1
            data['interval_days'] = new_interval
            data['source'] += '+cross_validate'

    print(f"  Adjusted more frequent: {adjusted_up}", flush=True)
    print(f"  Adjusted less frequent: {adjusted_down}", flush=True)


def step5_lifeform_defaults(dry_run, results):
    """Step 5: Fill remaining from lifeform defaults."""
    print("\n=== STEP 5: Lifeform Defaults ===", flush=True)

    rows = turso_query("SELECT c.plant_id, p.preset FROM care c JOIN plants p ON c.plant_id = p.plant_id")
    filled = 0
    no_default = 0

    for row in rows:
        pid = row['plant_id']

        # Skip if already has interval
        if pid in results and results[pid].get('interval_days') is not None:
            continue

        preset = (row.get('preset') or '').lower().strip()
        default = LIFEFORM_DEFAULTS.get(preset)
        if default:
            if pid in results:
                # Has months from step 3, just needs interval
                results[pid]['interval_days'] = default['interval']
                results[pid]['source'] = results[pid].get('source', '') + '+lifeform_default'
            else:
                results[pid] = {
                    'interval_days': default['interval'],
                    'active_months': default['months'],
                    'source': 'lifeform_default',
                }
            filled += 1
        else:
            # Generic default
            if pid not in results or results[pid].get('interval_days') is None:
                results[pid] = {
                    'interval_days': 21,  # moderate default
                    'active_months': [3, 4, 5, 6, 7, 8],
                    'source': 'generic_default',
                }
                no_default += 1

    print(f"  Filled from lifeform: {filled}", flush=True)
    print(f"  Generic default: {no_default}", flush=True)


def step6_write(dry_run, results):
    """Step 6: Write fertilizer_interval_days + fertilizer_active_months to care."""
    print("\n=== STEP 6: Write to care ===", flush=True)

    if dry_run:
        # Show distribution
        intervals = {}
        for data in results.values():
            d = data.get('interval_days')
            if d is not None:
                intervals[d] = intervals.get(d, 0) + 1
        print("  Interval distribution (dry-run):", flush=True)
        for d in sorted(intervals.keys()):
            print(f"    {d:3d} days: {intervals[d]:5d} plants", flush=True)

        sources = {}
        for data in results.values():
            s = data.get('source', 'unknown')
            # Simplify source name
            base = s.split('+')[0]
            sources[base] = sources.get(base, 0) + 1
        print("  Source breakdown:", flush=True)
        for s, c in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"    {s:25s} {c:5d}", flush=True)

        # Sample
        print("\n  Samples:", flush=True)
        samples = ['monstera_deliciosa', 'crassula_ovata', 'ocimum_basilicum',
                    'phalaenopsis_amabilis', 'solanum_lycopersicum', 'dracaena_trifasciata']
        for pid in samples:
            if pid in results:
                d = results[pid]
                print(f"    {pid:30s} → {d['interval_days']:3d}d  months={d['active_months']}  src={d['source']}", flush=True)
        return

    # Add columns if missing
    for col, typ in [('fertilizer_interval_days', 'INTEGER'), ('fertilizer_active_months', 'TEXT')]:
        try:
            turso_query(f"SELECT {col} FROM care LIMIT 1")
        except Exception:
            print(f"  Adding column: {col} {typ}", flush=True)
            turso_query(f"ALTER TABLE care ADD COLUMN {col} {typ}")

    # Batch write
    stmts = []
    written = 0
    for pid, data in results.items():
        interval = data.get('interval_days')
        months = data.get('active_months', [])
        if interval is None:
            continue

        months_json = json.dumps(months)
        stmts.append((
            "UPDATE care SET fertilizer_interval_days = ?, fertilizer_active_months = ? WHERE plant_id = ?",
            [interval, months_json, pid]
        ))

        if len(stmts) >= 100:
            turso_batch(stmts)
            written += len(stmts)
            stmts = []
            if written % 500 == 0:
                print(f"  [{written}] written...", flush=True)

    if stmts:
        turso_batch(stmts)
        written += len(stmts)

    print(f"  Total written: {written}", flush=True)


def show_results():
    """Print final coverage stats."""
    print("\n=== FERTILIZER INTERVALS STATUS ===", flush=True)
    total = turso_query("SELECT COUNT(*) as c FROM care")[0]['c']

    for col in ['fertilizer_interval_days', 'fertilizer_active_months']:
        try:
            r = turso_query(f"SELECT COUNT(*) as c FROM care WHERE {col} IS NOT NULL")
            print(f"  {col:35s} {r[0]['c']:>6} / {total} ({100*r[0]['c']//total}%)", flush=True)
        except Exception:
            print(f"  {col:35s} column not yet created", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    limit = None
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    results = {}

    step1_miflora(dry_run, results)
    step2_care_freq(dry_run, results)
    step3_season(dry_run, results)
    step4_cross_validate(dry_run, results)
    step5_lifeform_defaults(dry_run, results)
    step6_write(dry_run, results)
    show_results()
