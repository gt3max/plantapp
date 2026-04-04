"""
verify.py — Cross-source verification for plant data quality.

Queries multiple sources for a plant, compares values, applies majority rule.
Flags anomalies, single-source data, and conflicts.

Usage:
    python3 verify.py "Crassula ovata"           # verify one plant
    python3 verify.py --top 10                     # verify 10 most popular
    python3 verify.py --all --limit 100            # verify 100 plants from DB
"""
import json
import re
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turso_sync import turso_query
from sources.ncstate_fetcher import fetch_plant_page, parse_plant_page
from sources.powo_fetcher import search_powo, get_powo_detail
from sources.wikipedia_fetcher import fetch_summary

# ── Sanity ranges for numeric fields ──
SANE_RANGES = {
    'temp_min_c': (-60, 20),     # survival min: -60 to +20
    'temp_max_c': (20, 50),      # survival max: 20 to 50
    'height_max_cm': (1, 10000), # 1cm to 100m (trees)
    'height_min_cm': (1, 5000),
    'soil_ph_min': (3.0, 9.0),
    'soil_ph_max': (3.0, 9.0),
    'ppfd_min': (10, 2000),
    'ppfd_max': (50, 2500),
}

# ── Growth rate normalization ──
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


def normalize(field, value):
    """Normalize a value for comparison."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().lower()
    if field == 'growth_rate':
        return GROWTH_RATE_MAP.get(value, value)
    if field == 'difficulty':
        return DIFFICULTY_MAP.get(value, value)
    if field == 'lifecycle':
        return LIFECYCLE_MAP.get(value, value)
    if field == 'light':
        # Normalize light descriptions to categories
        v = value.lower() if isinstance(value, str) else str(value).lower()
        if 'full sun' in v or '6+' in v or '6 or more' in v:
            return 'full sun'
        elif 'partial' in v or 'part shade' in v or '2-6' in v:
            return 'partial shade'
        elif 'bright indirect' in v:
            return 'bright indirect'
        elif 'low' in v or 'shade' in v:
            return 'low light'
        return value
    return value


def check_sanity(field, value):
    """Check if a numeric value is within sane range."""
    if field not in SANE_RANGES or value is None:
        return True, ''
    lo, hi = SANE_RANGES[field]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False, f'not a number: {value}'
    if v < lo or v > hi:
        return False, f'{value} outside sane range [{lo}, {hi}]'
    return True, ''


def fetch_all_sources(scientific):
    """Fetch data from all available sources for a plant."""
    sources = {}
    slug = scientific.lower().replace(' ', '-').replace("'", '').replace('"', '')

    # 1. NC State
    try:
        html = fetch_plant_page(slug)
        time.sleep(1)
        if len(html) > 1000 and '404' not in html[:500]:
            data = parse_plant_page(html)
            if data:
                sources['ncstate'] = data
    except Exception:
        pass

    # 2. POWO
    try:
        fq = search_powo(scientific)
        time.sleep(0.5)
        if fq:
            detail = get_powo_detail(fq)
            time.sleep(0.5)
            sources['powo'] = detail
    except Exception:
        pass

    # 3. Wikipedia
    try:
        desc, img = fetch_summary(scientific)
        time.sleep(0.5)
        if desc:
            sources['wikipedia'] = {'description': desc, 'image_url': img}
    except Exception:
        pass

    # 4. Our DB (Turso)
    plant_id = scientific.lower().replace(' ', '_').replace("'", '').replace('"', '')
    p = turso_query('SELECT * FROM plants WHERE plant_id = ?', [plant_id])
    c = turso_query('SELECT * FROM care WHERE plant_id = ?', [plant_id])
    if p:
        sources['turso_plants'] = p[0]
    if c:
        sources['turso_care'] = c[0]

    return sources


def extract_comparable(sources):
    """Extract comparable field values from each source into a unified format."""
    fields = {}

    def add(field, source, value):
        if value is not None and value != '' and value != 0:
            if field not in fields:
                fields[field] = {}
            fields[field][source] = value

    # NC State
    nc = sources.get('ncstate', {})
    if nc:
        add('growth_rate', 'ncstate', normalize('growth_rate', nc.get('growth_rate', '')))
        add('difficulty', 'ncstate', normalize('difficulty', nc.get('maintenance', '')))
        add('lifecycle', 'ncstate', normalize('lifecycle', nc.get('life_cycle', '')))
        add('light', 'ncstate', normalize('light', nc.get('light', '')))
        add('origin', 'ncstate', nc.get('origin', ''))
        add('propagation', 'ncstate', nc.get('propagation', ''))
        if nc.get('dimensions'):
            heights = re.findall(r'(\d+)\s*ft', nc['dimensions'])
            if heights:
                add('height_max_cm', 'ncstate', int(heights[-1]) * 30)
        if nc.get('soil_ph'):
            ph_nums = re.findall(r'(\d+\.?\d*)', nc['soil_ph'])
            if ph_nums:
                add('soil_ph_min', 'ncstate', float(ph_nums[0]))

    # POWO
    pw = sources.get('powo', {})
    if pw:
        lf = pw.get('lifeform', '')
        if lf:
            for key, val in LIFECYCLE_MAP.items():
                if key in lf.lower():
                    add('lifecycle', 'powo', val)
                    break
        add('climate', 'powo', pw.get('climate', ''))
        add('order', 'powo', pw.get('order', ''))
        locs = pw.get('locations', []) or []
        native = []
        if locs and isinstance(locs[0], dict):
            native = [l.get('name', '') for l in locs if l.get('establishment') == 'Native']
        elif locs and isinstance(locs[0], str):
            native = [l.replace('_', ' ') for l in locs[:5]]
        if native:
            # Filter codes
            readable = [n for n in native if len(n.replace('_','').replace(' ','')) > 4 or not n.replace('_','').replace(' ','').isupper()]
            if readable:
                add('origin', 'powo', ', '.join(readable[:3]))

    # Turso (our DB)
    tc = sources.get('turso_care', {})
    if tc:
        add('growth_rate', 'turso', normalize('growth_rate', str(tc.get('growth_rate', ''))))
        add('difficulty', 'turso', normalize('difficulty', str(tc.get('difficulty', ''))))
        add('lifecycle', 'turso', normalize('lifecycle', str(tc.get('lifecycle', ''))))
        add('height_max_cm', 'turso', tc.get('height_max_cm'))
        add('height_min_cm', 'turso', tc.get('height_min_cm'))
        add('temp_min_c', 'turso', tc.get('temp_min_c'))
        add('temp_max_c', 'turso', tc.get('temp_max_c'))
        add('soil_ph_min', 'turso', tc.get('soil_ph_min'))
        add('water_demand', 'turso', str(tc.get('water_demand', '')).lower())
        add('light', 'turso', normalize('light', tc.get('light_preferred', '')))

    tp = sources.get('turso_plants', {})
    if tp:
        add('origin', 'turso', tp.get('origin', ''))
        add('family', 'turso', tp.get('family', ''))

    return fields


def verify_plant(scientific, verbose=True):
    """Verify a single plant across all sources. Returns report dict."""
    if verbose:
        print(f'\n{"="*70}')
        print(f'  VERIFY: {scientific}')
        print(f'{"="*70}')

    sources = fetch_all_sources(scientific)
    available = [s for s in sources if s not in ('turso_plants', 'turso_care')]

    if verbose:
        print(f'  Sources found: {", ".join(sources.keys())}')

    fields = extract_comparable(sources)

    issues = []
    consensus = {}

    for field, source_values in sorted(fields.items()):
        n_sources = len(source_values)
        values = list(source_values.values())
        src_names = list(source_values.keys())

        # Sanity check
        for src, val in source_values.items():
            sane, reason = check_sanity(field, val)
            if not sane:
                issues.append(f'INSANE: {field} from {src}: {reason}')
                if verbose:
                    print(f'  ❌ {field:20s}: {src}={val} — {reason}')

        # Single source
        if n_sources == 1:
            consensus[field] = {'value': values[0], 'confidence': 'single', 'source': src_names[0]}
            if verbose:
                print(f'  ⚠️  {field:20s}: {values[0]} (single source: {src_names[0]})')
            continue

        # Multiple sources — find consensus
        # Normalize for comparison
        norm_values = {}
        for src, val in source_values.items():
            nv = str(val).lower().strip() if val else ''
            if nv not in norm_values:
                norm_values[nv] = []
            norm_values[nv].append(src)

        # Find majority
        best_val = max(norm_values.items(), key=lambda x: len(x[1]))
        majority_count = len(best_val[1])
        total = sum(len(v) for v in norm_values.values())

        if len(norm_values) == 1:
            # All agree
            consensus[field] = {'value': values[0], 'confidence': 'confirmed', 'sources': src_names}
            if verbose:
                print(f'  ✅ {field:20s}: {values[0]} (all {n_sources} sources agree)')
        elif majority_count > total / 2:
            # Majority agrees
            dissenters = {s: v for nv, srcs in norm_values.items() for s, v in zip(srcs, [source_values[s] for s in srcs]) if nv != best_val[0]}
            consensus[field] = {'value': source_values[best_val[1][0]], 'confidence': 'majority', 'sources': best_val[1]}
            if verbose:
                print(f'  ⚠️  {field:20s}: {source_values[best_val[1][0]]} (majority: {best_val[1]})')
                for ds, dv in dissenters.items():
                    print(f'       ↳ {ds} disagrees: {dv}')
                    issues.append(f'CONFLICT: {field}: {ds}={dv} vs majority={source_values[best_val[1][0]]}')
        else:
            # No consensus
            consensus[field] = {'value': None, 'confidence': 'conflict', 'sources': src_names}
            if verbose:
                print(f'  ❌ {field:20s}: NO CONSENSUS')
                for src, val in source_values.items():
                    print(f'       {src:12s}: {val}')
            issues.append(f'NO CONSENSUS: {field}: {dict(source_values)}')

    if verbose:
        print(f'\n  Summary: {len(consensus)} fields checked, {len(issues)} issues')
        for issue in issues:
            print(f'    ! {issue}')

    return {
        'scientific': scientific,
        'sources_count': len(sources),
        'fields_checked': len(consensus),
        'issues': issues,
        'consensus': consensus,
    }


def verify_top(n=10):
    """Verify top N plants (by most data in DB)."""
    rows = turso_query('''
        SELECT p.scientific FROM plants p
        JOIN care c ON p.plant_id = c.plant_id
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN p.sources LIKE '%verified%' THEN 0
                 WHEN p.sources LIKE '%perenual%' THEN 1
                 ELSE 2 END,
            p.scientific
        LIMIT ?
    ''', [n])

    results = []
    for row in rows:
        r = verify_plant(row['scientific'])
        results.append(r)
        time.sleep(1)

    # Summary
    total_issues = sum(len(r['issues']) for r in results)
    print(f'\n{"="*70}')
    print(f'  TOTAL: {len(results)} plants verified, {total_issues} issues found')
    print(f'{"="*70}')

    return results


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--top':
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            verify_top(n)
        elif sys.argv[1] == '--all':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            verify_top(limit)
        else:
            # Single plant by scientific name
            name = ' '.join(sys.argv[1:])
            verify_plant(name)
    else:
        # Default: verify our 6 gold standard plants
        gold = [
            'Crassula ovata', 'Ocimum basilicum', 'Salvia rosmarinus',
            'Solanum lycopersicum', 'Phalaenopsis amabilis', 'Dracaena trifasciata',
        ]
        for plant in gold:
            verify_plant(plant)
            time.sleep(1)
