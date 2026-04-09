"""
Polish light v2 — reclassify Part sun + verify Bright indirect using multi-source voting.

Sources:
  Ellenberg L (weight 4): L≤2→Shade, L=3-4→Bright indirect, L=5-6→Part sun, L≥7→Full sun
  PPFD/DLI (weight 3): recalculate category from existing numeric values
  PFAF shade (weight 2): N→Full sun, SN→Part sun, S→Bright indirect, FS/F→Shade
  MiFloraDB lux (weight 2): >30K→Full sun, 10-30K→Part sun, <10K→Bright indirect
  Lifeform+climate (weight 1): succulent+desert→Full sun, epiphyte→Bright indirect

Featured 32 protected. All votes saved to source_data.

Usage:
    python3 polish_light_v2.py --dry-run
    python3 polish_light_v2.py
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

LIGHT_LEVELS = ['Shade', 'Bright indirect light', 'Part sun', 'Full sun']
# Numeric index: Shade=0, Bright indirect=1, Part sun=2, Full sun=3


def get_featured_ids():
    try:
        with open(FEATURED_FILE) as f:
            return set(re.findall(r"plantIdStr: '([^']+)'", f.read()))
    except:
        return set()


def light_to_index(light):
    """Convert light string to numeric index 0-3."""
    mapping = {'Shade': 0, 'Bright indirect light': 1, 'Part sun': 2, 'Full sun': 3}
    return mapping.get(light, 2)


def index_to_light(idx):
    """Convert numeric index to light string."""
    if idx <= 0:
        return 'Shade'
    elif idx <= 1:
        return 'Bright indirect light'
    elif idx <= 2:
        return 'Part sun'
    else:
        return 'Full sun'


def get_votes(plant, pfaf_shade, mifloradb_lux):
    """Collect votes for light classification. Returns (weighted_sum, weight_total, votes_list)."""
    pid = plant['plant_id']
    votes = []
    # Each vote: (light_index 0-3, weight)
    weighted = []

    # 1. Ellenberg L (weight 4)
    el = plant.get('ellenberg_l') or 0
    if el > 0:
        if el <= 2:
            weighted.append((0, 4))  # Shade
            votes.append(f'ell_L={el}→Shade(4)')
        elif el <= 4:
            weighted.append((1, 4))  # Bright indirect
            votes.append(f'ell_L={el}→BrightInd(4)')
        elif el <= 6:
            weighted.append((2, 4))  # Part sun
            votes.append(f'ell_L={el}→PartSun(4)')
        else:
            weighted.append((3, 4))  # Full sun
            votes.append(f'ell_L={el}→FullSun(4)')

    # 2. PPFD (weight 3)
    ppfd_min = plant.get('ppfd_min') or 0
    ppfd_max = plant.get('ppfd_max') or 0
    if ppfd_max > 0:
        mid_ppfd = (ppfd_min + ppfd_max) / 2
        if mid_ppfd >= 400:
            weighted.append((3, 3))
            votes.append(f'ppfd={mid_ppfd:.0f}→FullSun(3)')
        elif mid_ppfd >= 200:
            weighted.append((2, 3))
            votes.append(f'ppfd={mid_ppfd:.0f}→PartSun(3)')
        elif mid_ppfd >= 50:
            weighted.append((1, 3))
            votes.append(f'ppfd={mid_ppfd:.0f}→BrightInd(3)')
        else:
            weighted.append((0, 3))
            votes.append(f'ppfd={mid_ppfd:.0f}→Shade(3)')

    # 3. PFAF shade (weight 2)
    shade = pfaf_shade.get(pid, '')
    if shade:
        shade_map = {
            'N': (3, 'FullSun'), 'SN': (2, 'PartSun'), 'NS': (2, 'PartSun'),
            'S': (1, 'BrightInd'), 'FS': (1, 'BrightInd'), 'FSN': (2, 'PartSun'),
            'F': (0, 'Shade'),
        }
        if shade in shade_map:
            idx, label = shade_map[shade]
            weighted.append((idx, 2))
            votes.append(f'pfaf={shade}→{label}(2)')

    # 4. MiFloraDB lux (weight 2)
    lux = mifloradb_lux.get(pid)
    if lux:
        try:
            max_lux = float(lux)
            if max_lux >= 30000:
                weighted.append((3, 2))
                votes.append(f'mfdb_lux={max_lux:.0f}→FullSun(2)')
            elif max_lux >= 10000:
                weighted.append((2, 2))
                votes.append(f'mfdb_lux={max_lux:.0f}→PartSun(2)')
            elif max_lux >= 2500:
                weighted.append((1, 2))
                votes.append(f'mfdb_lux={max_lux:.0f}→BrightInd(2)')
            else:
                weighted.append((0, 2))
                votes.append(f'mfdb_lux={max_lux:.0f}→Shade(2)')
        except:
            pass

    # 5. Lifeform + climate (weight 1)
    preset = plant.get('preset') or ''
    climate = (plant.get('climate') or '').lower()

    if preset == 'succulent':
        weighted.append((3, 1))
        votes.append(f'lf=succulent→FullSun(1)')
    elif preset == 'epiphyte':
        weighted.append((1, 1))
        votes.append(f'lf=epiphyte→BrightInd(1)')
    elif preset == 'fern':
        weighted.append((1, 1))
        votes.append(f'lf=fern→BrightInd(1)')
    elif preset == 'moss':
        weighted.append((0, 1))
        votes.append(f'lf=moss→Shade(1)')
    elif 'desert' in climate:
        weighted.append((3, 1))
        votes.append(f'climate=desert→FullSun(1)')

    if not weighted:
        return None, None, votes

    # Weighted average → nearest category
    total_weight = sum(w for _, w in weighted)
    weighted_avg = sum(idx * w for idx, w in weighted) / total_weight

    return weighted_avg, total_weight, votes


def run(dry_run=False):
    featured = get_featured_ids()
    print(f"[light_v2] Protected: {len(featured)} featured", flush=True)

    # Load all care + plants data for Part sun + Bright indirect
    plants = turso_query("""
        SELECT c.plant_id, c.light_preferred, c.ellenberg_l, c.ppfd_min, c.ppfd_max,
               p.preset, p.climate
        FROM care c JOIN plants p ON c.plant_id = p.plant_id
        WHERE c.light_preferred IN ('Part sun', 'Bright indirect light')
    """)
    print(f"[light_v2] Plants to check: {len(plants)} (Part sun + Bright indirect)", flush=True)

    # Pre-load PFAF shade
    pfaf_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf' AND field = 'shade'")
    pfaf_shade = {r['plant_id']: r['value'] for r in pfaf_data}

    # Pre-load MiFloraDB max_light_lux
    mfdb_data = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'xiaomi_mifloradb' AND field = 'max_light_lux'")
    mifloradb_lux = {r['plant_id']: r['value'] for r in mfdb_data}

    print(f"  PFAF shade: {len(pfaf_shade)}, MiFloraDB lux: {len(mifloradb_lux)}", flush=True)

    stmts = []
    stats = {
        'part_to_full': 0, 'part_to_bright': 0, 'part_to_shade': 0, 'part_stays': 0,
        'bright_to_full': 0, 'bright_to_part': 0, 'bright_to_shade': 0, 'bright_stays': 0,
        'no_data': 0, 'protected': 0,
    }

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        current = plant['light_preferred']
        is_featured = pid in featured

        avg, total_w, votes = get_votes(plant, pfaf_shade, mifloradb_lux)

        if avg is None:
            stats['no_data'] += 1
            continue

        # Determine new category
        new_light = index_to_light(round(avg))
        changed = new_light != current

        # Track stats
        if current == 'Part sun':
            if new_light == 'Full sun':
                stats['part_to_full'] += 1
            elif new_light == 'Bright indirect light':
                stats['part_to_bright'] += 1
            elif new_light == 'Shade':
                stats['part_to_shade'] += 1
            else:
                stats['part_stays'] += 1
        elif current == 'Bright indirect light':
            if new_light == 'Full sun':
                stats['bright_to_full'] += 1
            elif new_light == 'Part sun':
                stats['bright_to_part'] += 1
            elif new_light == 'Shade':
                stats['bright_to_shade'] += 1
            else:
                stats['bright_stays'] += 1

        votes_str = ', '.join(votes)

        if not dry_run:
            # Always save votes
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v2', 'votes', ?, datetime('now'))",
                          [pid, votes_str]))
            stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v2', 'score', ?, datetime('now'))",
                          [pid, f'avg={avg:.2f} weight={total_w}']))

            if changed and not is_featured:
                stmts.append(("UPDATE care SET light_preferred = ? WHERE plant_id = ?",
                              [new_light, pid]))
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v2', 'changed', ?, datetime('now'))",
                              [pid, f'{current}→{new_light}']))
            elif is_featured:
                stats['protected'] += 1
                stmts.append(("INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v2', 'featured_would_be', ?, datetime('now'))",
                              [pid, new_light]))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 500 == 0:
            total_moved = stats['part_to_full'] + stats['part_to_bright'] + stats['part_to_shade'] + stats['bright_to_full'] + stats['bright_to_part'] + stats['bright_to_shade']
            print(f"  [{i+1}/{len(plants)}] moved={total_moved} no_data={stats['no_data']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[light_v2] Done:", flush=True)
    print(f"  Part sun → Full sun:             {stats['part_to_full']}", flush=True)
    print(f"  Part sun → Bright indirect:      {stats['part_to_bright']}", flush=True)
    print(f"  Part sun → Shade:                {stats['part_to_shade']}", flush=True)
    print(f"  Part sun stays:                  {stats['part_stays']}", flush=True)
    print(f"  Bright indirect → Full sun:      {stats['bright_to_full']}", flush=True)
    print(f"  Bright indirect → Part sun:      {stats['bright_to_part']}", flush=True)
    print(f"  Bright indirect → Shade:         {stats['bright_to_shade']}", flush=True)
    print(f"  Bright indirect stays:           {stats['bright_stays']}", flush=True)
    print(f"  No data:                         {stats['no_data']}", flush=True)
    print(f"  Protected:                       {stats['protected']}", flush=True)

    if not dry_run:
        dist = turso_query("SELECT light_preferred, COUNT(*) as cnt FROM care GROUP BY light_preferred ORDER BY cnt DESC")
        print(f"\nNew distribution:", flush=True)
        for d in dist:
            print(f"  {d['light_preferred'] or '(empty)':<30s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
