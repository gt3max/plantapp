"""
Polish light v3 — lifeform + family + climate for 5,458 unresolved plants.

Strategy 1: Lifeform hard rules (moss→Shade, succulent→Full sun)
Strategy 2: Family heuristics (≥65% pattern)
Strategy 3: Climate + lifeform combo (desert→Full sun, etc.)
Strategy 4: Flag remaining unresolved

Only processes plants NOT touched by light_v2.
Featured protected. All results → source_data.

Usage:
    python3 polish_light_v3.py --dry-run
    python3 polish_light_v3.py
"""
import sys
import os
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

FEATURED_FILE = '/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart'

# Lifeform hard rules
LIFEFORM_LIGHT = {
    'moss': 'Shade',
    'fern': 'Shade',
    'succulent': 'Full sun',
}

# Climate hard rules (only very strong signals)
CLIMATE_LIGHT = {
    'desert or dry shrubland': 'Full sun',
    'subalpine or subarctic': 'Full sun',
}

# Climate + lifeform combos
CLIMATE_LIFEFORM_LIGHT = {
    ('epiphyte', 'wet tropical'): 'Bright indirect light',
    ('epiphyte', 'seasonally dry tropical'): 'Bright indirect light',
    ('tree', 'desert or dry shrubland'): 'Full sun',
    ('shrub', 'desert or dry shrubland'): 'Full sun',
    ('perennial', 'desert or dry shrubland'): 'Full sun',
    ('annual', 'desert or dry shrubland'): 'Full sun',
    ('tree', 'subtropical'): 'Full sun',
    ('shrub', 'subtropical'): 'Full sun',
}


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            return set(re.findall(r"plantIdStr: '([^']+)'", f.read()))
    except:
        return set()


def build_family_light_map():
    """Build family → dominant light from already classified plants."""
    rows = turso_query("""
        SELECT p.family, c.light_preferred, COUNT(*) as cnt
        FROM plants p JOIN care c ON p.plant_id = c.plant_id
        WHERE c.light_preferred NOT IN ('Part sun', 'Bright indirect light')
        AND p.family IS NOT NULL AND p.family != ''
        GROUP BY p.family, c.light_preferred
    """)

    family_map = {}
    for r in rows:
        fam = r['family']
        if fam not in family_map:
            family_map[fam] = {}
        family_map[fam][r['light_preferred']] = r['cnt']

    result = {}
    for fam, lights in family_map.items():
        total = sum(lights.values())
        if total < 5:
            continue
        dominant = max(lights, key=lights.get)
        ratio = lights[dominant] / total
        if ratio >= 0.65:
            result[fam] = {'light': dominant, 'confidence': f'{ratio:.0%}', 'total': total}

    return result


def run(dry_run=False):
    featured = get_featured_ids()
    print(f"[light_v3] Protected: {len(featured)} featured", flush=True)

    # Get unresolved plants (not in light_v2)
    plants = turso_query("""
        SELECT c.plant_id, c.light_preferred, p.preset, p.climate, p.family
        FROM care c JOIN plants p ON c.plant_id = p.plant_id
        WHERE c.light_preferred IN ('Part sun', 'Bright indirect light')
        AND c.plant_id NOT IN (SELECT plant_id FROM source_data WHERE source = 'light_v2')
    """)
    print(f"[light_v3] Unresolved plants: {len(plants)}", flush=True)

    family_light = build_family_light_map()
    print(f"  Family light map: {len(family_light)} families with ≥65% pattern", flush=True)

    stmts = []
    stats = {
        'lifeform': 0, 'family': 0, 'climate': 0, 'climate_lifeform': 0,
        'unresolved': 0, 'protected': 0,
        'to_fullsun': 0, 'to_shade': 0, 'to_bright': 0,
    }

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        preset = plant.get('preset') or ''
        climate = (plant.get('climate') or '').lower()
        family = plant.get('family') or ''

        if pid in featured:
            stats['protected'] += 1
            continue

        new_light = None
        source = None
        detail = ''

        # Strategy 1: Lifeform hard rules
        if preset in LIFEFORM_LIGHT:
            new_light = LIFEFORM_LIGHT[preset]
            source = 'light_v3'
            detail = f'lifeform={preset}→{new_light}'
            stats['lifeform'] += 1

        # Strategy 2: Family heuristics
        if not new_light and family in family_light:
            fl = family_light[family]
            new_light = fl['light']
            source = 'light_v3'
            detail = f'family={family}→{new_light} ({fl["confidence"]} of {fl["total"]})'
            stats['family'] += 1

        # Strategy 3a: Climate+lifeform combo
        if not new_light:
            combo = (preset, climate) if climate else None
            if combo and combo in CLIMATE_LIFEFORM_LIGHT:
                new_light = CLIMATE_LIFEFORM_LIGHT[combo]
                source = 'light_v3'
                detail = f'{preset}+{climate}→{new_light}'
                stats['climate_lifeform'] += 1

        # Strategy 3b: Climate only (very strong)
        if not new_light and climate:
            for cl_key, light in CLIMATE_LIGHT.items():
                if cl_key in climate:
                    new_light = light
                    source = 'light_v3'
                    detail = f'climate={climate}→{new_light}'
                    stats['climate'] += 1
                    break

        if new_light:
            if new_light == 'Full sun':
                stats['to_fullsun'] += 1
            elif new_light == 'Shade':
                stats['to_shade'] += 1
            else:
                stats['to_bright'] += 1

            if not dry_run:
                stmts.append(("UPDATE care SET light_preferred = ? WHERE plant_id = ?", [new_light, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'light_changed', ?, datetime('now'))",
                    [pid, source, detail]
                ))
        else:
            stats['unresolved'] += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'light_v3_unresolved', ?, datetime('now'))",
                    [pid, f'{plant["light_preferred"]} — no pattern found for {preset}/{family}/{climate}']
                ))

        if len(stmts) >= 100:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

        if (i + 1) % 500 == 0:
            total = stats['lifeform'] + stats['family'] + stats['climate'] + stats['climate_lifeform']
            print(f"  [{i+1}/{len(plants)}] moved={total} (lf={stats['lifeform']} fam={stats['family']} cl={stats['climate']+stats['climate_lifeform']}) unres={stats['unresolved']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    total_moved = stats['lifeform'] + stats['family'] + stats['climate'] + stats['climate_lifeform']
    print(f"\n[light_v3] Done:", flush=True)
    print(f"  Lifeform:        {stats['lifeform']}", flush=True)
    print(f"  Family:          {stats['family']}", flush=True)
    print(f"  Climate+LF:      {stats['climate_lifeform']}", flush=True)
    print(f"  Climate:         {stats['climate']}", flush=True)
    print(f"  → Full sun:      {stats['to_fullsun']}", flush=True)
    print(f"  → Shade:         {stats['to_shade']}", flush=True)
    print(f"  → Bright ind:    {stats['to_bright']}", flush=True)
    print(f"  Total moved:     {total_moved}", flush=True)
    print(f"  Unresolved:      {stats['unresolved']} (flagged)", flush=True)
    print(f"  Protected:       {stats['protected']}", flush=True)

    if not dry_run:
        dist = turso_query("SELECT light_preferred, COUNT(*) as cnt FROM care GROUP BY light_preferred ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['light_preferred'] or '(empty)':<30s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
