"""
reconcile.py — Consensus engine for plant data quality.

Reads raw data from source_data table, compares values across sources,
applies majority rule + sanity checks, writes verified data to care/plants.

Confidence levels:
  - 'confirmed'  : ≥2 sources agree
  - 'majority'   : >50% of sources agree, some disagree
  - 'single'     : only 1 source, no verification possible
  - 'conflict'   : sources disagree, no majority — needs manual review

Usage:
    python3 reconcile.py                    # reconcile all plants with source_data
    python3 reconcile.py --plant "crassula_ovata"  # reconcile one plant
    python3 reconcile.py --stats            # show reconciliation stats
"""
import json
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch, turso_execute

# ── Normalization maps ──
GROWTH_RATE_MAP = {
    'slow': 'slow', 'slowly': 'slow',
    'medium': 'medium', 'moderate': 'medium', 'moderately': 'medium',
    'fast': 'fast', 'rapid': 'fast', 'quickly': 'fast',
}

DIFFICULTY_MAP = {
    'easy': 'easy', 'low': 'easy', 'beginner': 'easy',
    'medium': 'medium', 'moderate': 'medium', 'intermediate': 'medium',
    'hard': 'hard', 'high': 'hard', 'difficult': 'hard', 'expert': 'hard',
}

LIFECYCLE_MAP = {
    'annual': 'annual',
    'biennial': 'biennial',
    'perennial': 'perennial',
    'woody': 'perennial', 'shrub': 'perennial', 'tree': 'perennial',
    'sub-shrub': 'perennial', 'subshrub': 'perennial',
    'vine': 'perennial', 'liana': 'perennial',
}

LIGHT_MAP = {
    'full sun': 'full sun',
    'partial shade': 'partial shade', 'part shade': 'partial shade',
    'partial sun': 'partial shade',
    'bright indirect': 'bright indirect',
    'low light': 'low light', 'shade': 'low light', 'deep shade': 'low light',
}

# ── Sanity ranges ──
SANE_RANGES = {
    'temp_min_c': (-60, 20),
    'temp_max_c': (15, 55),
    'height_min_cm': (1, 5000),
    'height_max_cm': (1, 10000),
    'spread_max_cm': (1, 5000),
    'soil_ph_min': (3.0, 9.0),
    'soil_ph_max': (3.0, 9.5),
}

# ── Fields that go to care table vs plants table ──
PLANTS_FIELDS = {'origin', 'order_name', 'synonyms', 'description', 'image_url'}


def normalize_value(field, value):
    """Normalize a value for cross-source comparison."""
    if value is None or value == '':
        return None
    v = str(value).strip().lower()

    if field == 'growth_rate':
        return GROWTH_RATE_MAP.get(v, v)
    if field == 'difficulty':
        return DIFFICULTY_MAP.get(v, v)
    if field == 'lifecycle':
        return LIFECYCLE_MAP.get(v, v)
    if field == 'light_preferred':
        for key, norm in LIGHT_MAP.items():
            if key in v:
                return norm
        return v

    # Numeric fields — try to parse
    if field in SANE_RANGES:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return v


def is_sane(field, value):
    """Check if numeric value is within reasonable range."""
    if field not in SANE_RANGES or value is None:
        return True
    try:
        v = float(value)
        lo, hi = SANE_RANGES[field]
        return lo <= v <= hi
    except (TypeError, ValueError):
        return False


def reconcile_field(plant_id, field, source_values):
    """
    Decide the best value for a field given multiple source values.
    Returns (value, confidence, sources_used, conflict_info).
    """
    # Filter None/empty
    valid = {src: val for src, val in source_values.items() if val is not None and val != ''}

    if not valid:
        return None, 'empty', '', ''

    # Sanity filter for numeric fields
    if field in SANE_RANGES:
        sane = {src: val for src, val in valid.items() if is_sane(field, val)}
        insane = {src: val for src, val in valid.items() if not is_sane(field, val)}
        if insane:
            valid = sane if sane else valid  # keep insane only if nothing else

    if len(valid) == 1:
        src, val = next(iter(valid.items()))
        return val, 'single', src, ''

    # Normalize for comparison
    norm_groups = {}
    for src, val in valid.items():
        nv = normalize_value(field, val)
        nv_key = str(nv)
        if nv_key not in norm_groups:
            norm_groups[nv_key] = []
        norm_groups[nv_key].append((src, val))

    if len(norm_groups) == 1:
        # All agree
        all_sources = [src for src, _ in next(iter(norm_groups.values()))]
        best_val = next(iter(norm_groups.values()))[0][1]  # original value from first source
        return best_val, 'confirmed', ','.join(all_sources), ''

    # Find majority
    best_group = max(norm_groups.values(), key=len)
    total = sum(len(g) for g in norm_groups.values())

    if len(best_group) > total / 2:
        # Majority wins
        majority_sources = [src for src, _ in best_group]
        best_val = best_group[0][1]
        # Record dissent
        dissenters = {src: val for nv, group in norm_groups.items()
                      for src, val in group if (src, val) not in best_group}
        conflict = json.dumps(dissenters) if dissenters else ''
        return best_val, 'majority', ','.join(majority_sources), conflict

    # No majority — for numeric fields, take median
    if field in SANE_RANGES:
        nums = []
        for src, val in valid.items():
            try:
                nums.append((float(val), src))
            except (TypeError, ValueError):
                pass
        if nums:
            nums.sort()
            mid = nums[len(nums) // 2]
            conflict = json.dumps({src: str(val) for src, val in valid.items()})
            return str(int(mid[0])), 'median', mid[1], conflict

    # Special handling for text fields where values differ in wording but mean the same
    # e.g. origin: "South Africa" vs "Southern Africa" vs "KwaZulu-Natal, South Africa"
    if field in ('origin', 'description'):
        # Check if there's a common substring (fuzzy agreement)
        vals_lower = [str(v).lower() for v in valid.values()]
        # Find the shortest value, check if it appears in most others
        shortest = min(vals_lower, key=len)
        # Split into key words and check overlap
        keywords = set(shortest.split())
        # Remove generic words
        keywords -= {'and', 'the', 'of', 'in', 'to', 'a', 'an', 'from'}
        if keywords:
            matches = 0
            for vl in vals_lower:
                matching_words = sum(1 for kw in keywords if kw in vl)
                if matching_words >= len(keywords) * 0.5:
                    matches += 1
            if matches > len(valid) / 2:
                # Most sources share key words — pick the most detailed one
                best_src = max(valid.items(), key=lambda x: len(str(x[1])))
                all_src = ','.join(valid.keys())
                return best_src[1], 'fuzzy_match', all_src, ''

    # No consensus — flag for review
    conflict = json.dumps({src: str(val) for src, val in valid.items()})
    return None, 'conflict', '', conflict


def reconcile_plant(plant_id, verbose=False):
    """Reconcile all source_data for a single plant."""
    rows = turso_query(
        'SELECT source, field, value FROM source_data WHERE plant_id = ? ORDER BY field, source',
        [plant_id]
    )

    if not rows:
        return 0, 0

    # Group by field
    fields = {}
    for row in rows:
        f = row['field']
        if f not in fields:
            fields[f] = {}
        fields[f][row['source']] = row['value']

    decisions = []
    confirmed = 0
    conflicts = 0

    for field, source_values in fields.items():
        value, confidence, sources, conflict = reconcile_field(plant_id, field, source_values)

        if confidence == 'conflict':
            conflicts += 1
            if verbose:
                print(f'  ❌ {field}: CONFLICT — {conflict}')
        elif confidence in ('confirmed', 'majority', 'median'):
            confirmed += 1
            if verbose:
                print(f'  ✅ {field}: {value} ({confidence}, {sources})')
        elif verbose:
            print(f'  ⚠️  {field}: {value} ({confidence}, {sources})')

        # Save decision
        decisions.append((
            '''INSERT OR REPLACE INTO reconciled (plant_id, field, value, confidence, sources, conflict_values, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
            [plant_id, field, str(value) if value is not None else None,
             confidence, sources, conflict]
        ))

        # Write confirmed/majority/single to actual care/plants table
        if value is not None and confidence in ('confirmed', 'majority', 'median', 'single'):
            table = 'plants' if field in PLANTS_FIELDS else 'care'
            decisions.append((
                f"UPDATE {table} SET {field} = CASE WHEN {field} IS NULL OR {field} = '' THEN ? ELSE {field} END WHERE plant_id = ?",
                [str(value), plant_id]
            ))

    if decisions:
        turso_batch(decisions)

    return confirmed, conflicts


def reconcile_all(limit=None, verbose=False):
    """Reconcile all plants that have source_data."""
    plant_ids = turso_query('SELECT DISTINCT plant_id FROM source_data ORDER BY plant_id')

    if limit:
        plant_ids = plant_ids[:limit]

    print(f'[Reconcile] Processing {len(plant_ids)} plants...')
    total_confirmed = 0
    total_conflicts = 0
    total_plants = 0

    for i, row in enumerate(plant_ids):
        pid = row['plant_id']
        c, f = reconcile_plant(pid, verbose=verbose)
        total_confirmed += c
        total_conflicts += f
        total_plants += 1

        if (i + 1) % 100 == 0:
            print(f'  Progress: {i+1}/{len(plant_ids)}, confirmed={total_confirmed}, conflicts={total_conflicts}')

    print(f'[Reconcile] Done: {total_plants} plants, {total_confirmed} confirmed, {total_conflicts} conflicts')
    return total_confirmed, total_conflicts


def show_stats():
    """Show reconciliation statistics."""
    total = turso_query('SELECT COUNT(DISTINCT plant_id) as cnt FROM source_data')
    print(f'Plants with source data: {total[0]["cnt"]}')

    by_conf = turso_query('''
        SELECT confidence, COUNT(*) as cnt
        FROM reconciled
        GROUP BY confidence
        ORDER BY cnt DESC
    ''')
    print('\nReconciled fields by confidence:')
    for r in by_conf:
        print(f'  {r["confidence"]:12s}: {r["cnt"]:6d}')

    conflicts = turso_query('''
        SELECT plant_id, field, conflict_values
        FROM reconciled
        WHERE confidence = 'conflict'
        ORDER BY plant_id
        LIMIT 20
    ''')
    if conflicts:
        print(f'\nTop conflicts ({len(conflicts)}):')
        for r in conflicts:
            print(f'  {r["plant_id"]}.{r["field"]}: {r["conflict_values"][:80]}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            show_stats()
        elif sys.argv[1] == '--plant':
            pid = sys.argv[2] if len(sys.argv) > 2 else ''
            reconcile_plant(pid, verbose=True)
        else:
            reconcile_all(verbose='--verbose' in sys.argv)
    else:
        reconcile_all()
