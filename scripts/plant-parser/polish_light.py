"""
Polish light — reconcile all light sources, calculate hours, PPFD/DLI.

Sources priority: MiFloraDB lux > Ellenberg L > NC State > family default.
Calculates recommended hours from DLI ÷ PPFD.

Usage:
    python3 polish_light.py              # all plants
    python3 polish_light.py --featured   # 56 featured only
    python3 polish_light.py --limit 500
"""
import sys
import os
import re
import math

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

# Ellenberg L → PPFD/DLI ranges
L_TO_LIGHT = {
    1: ('Shade', 25, 75, 1.0, 3.0),
    2: ('Shade', 25, 100, 1.0, 4.0),
    3: ('Shade', 50, 150, 2.0, 6.0),
    4: ('Part sun', 75, 200, 3.0, 8.0),
    5: ('Part sun', 100, 300, 4.0, 12.0),
    6: ('Part sun', 150, 400, 6.0, 14.0),
    7: ('Full sun', 200, 500, 8.0, 18.0),
    8: ('Full sun', 300, 600, 12.0, 20.0),
    9: ('Full sun', 400, 800, 14.0, 25.0),
}

# Family defaults for light
FAMILY_LIGHT = {
    'Cactaceae': ('Full sun', 400, 800, 14.0, 25.0),
    'Crassulaceae': ('Full sun', 300, 600, 12.0, 20.0),
    'Aizoaceae': ('Full sun', 400, 800, 14.0, 25.0),
    'Orchidaceae': ('Part sun', 100, 300, 4.0, 12.0),
    'Araceae': ('Part sun', 75, 300, 3.0, 12.0),
    'Marantaceae': ('Part sun', 75, 200, 3.0, 8.0),
    'Polypodiaceae': ('Part sun', 50, 200, 2.0, 8.0),
    'Pteridaceae': ('Part sun', 50, 200, 2.0, 8.0),
    'Aspleniaceae': ('Part sun', 75, 250, 3.0, 10.0),
    'Arecaceae': ('Part sun', 100, 400, 4.0, 14.0),
    'Bromeliaceae': ('Part sun', 100, 400, 4.0, 14.0),
    'Lamiaceae': ('Full sun', 300, 600, 12.0, 20.0),
    'Apiaceae': ('Full sun', 200, 500, 8.0, 18.0),
    'Solanaceae': ('Full sun', 300, 600, 12.0, 20.0),
    'Moraceae': ('Part sun', 100, 400, 4.0, 14.0),
    'Asparagaceae': ('Part sun', 75, 300, 3.0, 12.0),
    'Piperaceae': ('Part sun', 75, 250, 3.0, 10.0),
    'Begoniaceae': ('Part sun', 75, 250, 3.0, 10.0),
    'Gesneriaceae': ('Part sun', 100, 300, 4.0, 12.0),
    'Commelinaceae': ('Part sun', 100, 400, 4.0, 14.0),
    'Strelitziaceae': ('Full sun', 200, 600, 8.0, 20.0),
    'Musaceae': ('Full sun', 200, 600, 8.0, 20.0),
    'Rutaceae': ('Full sun', 300, 600, 12.0, 20.0),
}


def ppfd_to_hours(ppfd_min, ppfd_max, dli_min, dli_max):
    """Calculate recommended light hours from PPFD and DLI."""
    if not ppfd_min or not dli_min:
        return None, None
    avg_ppfd = (ppfd_min + ppfd_max) / 2
    if avg_ppfd <= 0:
        return None, None
    # hours = DLI × 1,000,000 / (PPFD × 3600)
    hours_min = round(dli_min * 1000000 / (avg_ppfd * 3600))
    hours_max = round(dli_max * 1000000 / (avg_ppfd * 3600))
    return max(4, min(hours_min, 16)), max(6, min(hours_max, 18))


def polish_light(mode='all', limit=20000):
    """Reconcile light from all sources."""
    if mode == 'featured':
        with open('/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart') as f:
            text = f.read()
        featured_ids = re.findall(r"plantIdStr: '([^']+)'", text)
        plants = turso_query(f"""
            SELECT p.plant_id, p.family, c.light_preferred, c.ellenberg_l,
                   c.ppfd_min, c.ppfd_max, c.dli_min, c.dli_max
            FROM plants p JOIN care c ON p.plant_id = c.plant_id
            WHERE p.plant_id IN ({','.join(['?' for _ in featured_ids])})
        """, featured_ids)
    else:
        plants = turso_query("""
            SELECT p.plant_id, p.family, c.light_preferred, c.ellenberg_l,
                   c.ppfd_min, c.ppfd_max, c.dli_min, c.dli_max
            FROM plants p JOIN care c ON p.plant_id = c.plant_id
            LIMIT ?
        """, [limit])

    print(f"[polish_light] Processing {len(plants)} plants...", flush=True)

    stmts = []
    stats = {'mifloradb': 0, 'ellenberg': 0, 'family': 0, 'already_ok': 0, 'hours_added': 0}

    for i, p in enumerate(plants):
        pid = p['plant_id']
        family = p.get('family') or ''
        current_light = p.get('light_preferred') or ''
        el_l = p.get('ellenberg_l')
        has_ppfd = p.get('ppfd_min') and p.get('ppfd_min') > 0

        # Source 1: MiFloraDB (check source_data)
        mf = turso_query(
            "SELECT field, value FROM source_data WHERE plant_id = ? AND source = 'xiaomi_mifloradb' AND field IN ('min_light_lux','max_light_lux')",
            [pid]
        )
        mf_data = {r['field']: r['value'] for r in mf}

        if mf_data.get('min_light_lux') and mf_data.get('max_light_lux'):
            try:
                min_lux = int(mf_data['min_light_lux'])
                max_lux = int(mf_data['max_light_lux'])
                ppfd_min = round(min_lux * 0.0185)
                ppfd_max = round(max_lux * 0.0185)
                dli_min = round(ppfd_min * 12 * 3600 / 1000000, 1)
                dli_max = round(ppfd_max * 12 * 3600 / 1000000, 1)
                mid = (min_lux + max_lux) / 2
                if mid > 30000:
                    pref, also = 'Full sun', 'Part sun'
                elif mid > 10000:
                    pref, also = 'Part sun', 'Full sun'
                elif mid > 2500:
                    pref, also = 'Part sun', 'Shade'
                else:
                    pref, also = 'Shade', 'Part sun'

                if current_light == 'Bright indirect light':
                    stmts.append(("UPDATE care SET light_preferred = ?, light_also_ok = ? WHERE plant_id = ?", [pref, also, pid]))
                if not has_ppfd:
                    stmts.append(("UPDATE care SET ppfd_min = ?, ppfd_max = ?, dli_min = ?, dli_max = ? WHERE plant_id = ?",
                                  [ppfd_min, ppfd_max, dli_min, dli_max, pid]))
                stats['mifloradb'] += 1
                # Calculate hours
                h_min, h_max = ppfd_to_hours(ppfd_min, ppfd_max, dli_min, dli_max)
                if h_min:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value) VALUES (?, 'calculated', 'light_hours', ?)",
                        [pid, f"{h_min}-{h_max}"]
                    ))
                    stats['hours_added'] += 1
                continue
            except:
                pass

        # Source 2: Ellenberg L
        if el_l and el_l > 0:
            l_int = max(1, min(9, round(el_l)))
            data = L_TO_LIGHT.get(l_int)
            if data:
                pref, ppfd_min, ppfd_max, dli_min, dli_max = data
                if current_light == 'Bright indirect light':
                    stmts.append(("UPDATE care SET light_preferred = ? WHERE plant_id = ?", [pref, pid]))
                if not has_ppfd:
                    stmts.append(("UPDATE care SET ppfd_min = ?, ppfd_max = ?, dli_min = ?, dli_max = ? WHERE plant_id = ?",
                                  [ppfd_min, ppfd_max, dli_min, dli_max, pid]))
                h_min, h_max = ppfd_to_hours(ppfd_min, ppfd_max, dli_min, dli_max)
                if h_min:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value) VALUES (?, 'calculated', 'light_hours', ?)",
                        [pid, f"{h_min}-{h_max}"]
                    ))
                    stats['hours_added'] += 1
                stats['ellenberg'] += 1
                continue

        # Source 3: Family default
        if family in FAMILY_LIGHT and current_light == 'Bright indirect light':
            pref, ppfd_min, ppfd_max, dli_min, dli_max = FAMILY_LIGHT[family]
            stmts.append(("UPDATE care SET light_preferred = ? WHERE plant_id = ?", [pref, pid]))
            if not has_ppfd:
                stmts.append(("UPDATE care SET ppfd_min = ?, ppfd_max = ?, dli_min = ?, dli_max = ? WHERE plant_id = ?",
                              [ppfd_min, ppfd_max, dli_min, dli_max, pid]))
            h_min, h_max = ppfd_to_hours(ppfd_min, ppfd_max, dli_min, dli_max)
            if h_min:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value) VALUES (?, 'calculated', 'light_hours', ?)",
                    [pid, f"{h_min}-{h_max}"]
                ))
                stats['hours_added'] += 1
            stats['family'] += 1
            continue

        stats['already_ok'] += 1

        # Batch write
        if len(stmts) >= 40:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(plants)}] {stats}", flush=True)

    if stmts:
        turso_batch(stmts)

    print(f"\n[polish_light] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    # Report
    r1 = turso_query("SELECT light_preferred, COUNT(*) as cnt FROM care GROUP BY light_preferred ORDER BY cnt DESC LIMIT 5")
    print(f"\nLight distribution:", flush=True)
    for row in r1:
        print(f"  {row['cnt']:>6}x | {row['light_preferred']}", flush=True)

    r2 = turso_query("SELECT COUNT(*) as cnt FROM care WHERE ppfd_min IS NOT NULL AND ppfd_min > 0")
    print(f"\nPPFD filled: {r2[0]['cnt']}", flush=True)

    r3 = turso_query("SELECT COUNT(DISTINCT plant_id) as cnt FROM source_data WHERE field = 'light_hours'")
    print(f"Hours calculated: {r3[0]['cnt']}", flush=True)


if __name__ == '__main__':
    if '--featured' in sys.argv:
        polish_light(mode='featured')
    else:
        limit = 20000
        for arg in sys.argv[1:]:
            if arg.isdigit():
                limit = int(arg)
        polish_light(mode='all', limit=limit)
