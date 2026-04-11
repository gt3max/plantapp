"""
Polish light v5 — climate+origin→light reclassification.

Fixes Full sun plants with NO light evidence where climate zone
strongly suggests a different classification.

Rules:
  wet tropical + Full sun + no evidence → Bright indirect
  temperate + fern/moss/epiphyte + Full sun + no evidence → Bright indirect
  temperate + Full sun + habitat=forest → Part sun
  desert/subtropical/subalpine + Full sun → leave (correct)

Featured 40 plants NEVER touched.

Usage:
    python3 polish_light_v5.py --dry-run
    python3 polish_light_v5.py
"""
import sys
import os
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

LIGHT_LEVELS = ['Shade', 'Bright indirect light', 'Part sun', 'Full sun']

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

# Shade-indicating lifeforms for temperate climate
SHADE_LIFEFORMS = {'fern', 'moss', 'epiphyte'}

# Forest-indicating keywords in habitat text
FOREST_KEYWORDS = ['forest', 'woodland', 'understory', 'under trees', 'shaded', 'ravine',
                   'damp places', 'stream bank', 'humid forest', 'moist forest']


def retry_query(sql, params=None, retries=3):
    """Query with retries for Turso timeout."""
    for attempt in range(retries):
        try:
            return turso_query(sql, params)
        except Exception as e:
            if attempt < retries - 1 and 'timeout' in str(e).lower():
                print(f"  [retry {attempt+1}] Turso timeout, waiting 10s...", flush=True)
                time.sleep(10)
            else:
                raise


def run(dry_run=False):
    print("=== STEP 1: Load Data ===", flush=True)

    # All Full sun plants with climate and lifeform
    plants = retry_query("""
        SELECT c.plant_id, c.light_preferred, c.ellenberg_l, c.ppfd_min,
               p.climate, p.preset
        FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE c.light_preferred = 'Full sun'
    """)
    print(f"  Full sun plants: {len(plants)}", flush=True)

    # Plants with any light evidence (PFAF shade, USDA shade, light_vote)
    evidence_rows = retry_query("""
        SELECT DISTINCT plant_id FROM source_data
        WHERE field IN ('shade', 'shade_tolerance', 'light_vote')
    """)
    has_evidence = set(r['plant_id'] for r in evidence_rows)

    # PFAF habitat texts
    habitat_rows = retry_query("""
        SELECT plant_id, value FROM source_data
        WHERE source = 'pfaf_habitat' AND field = 'habitats'
    """)
    habitats = {r['plant_id']: r['value'].lower() for r in habitat_rows}

    print(f"  Plants with light evidence: {len(has_evidence)}", flush=True)
    print(f"  Plants with habitat data: {len(habitats)}", flush=True)

    print("\n=== STEP 2: Identify Fixes ===", flush=True)

    fixes = []
    stats = {'wet_tropical': 0, 'temperate_shade_lf': 0, 'temperate_forest': 0, 'skipped_evidence': 0, 'skipped_featured': 0}

    for p in plants:
        pid = p['plant_id']
        climate = (p['climate'] or '').lower()
        preset = (p['preset'] or '').lower()
        el = p.get('ellenberg_l') or 0
        ppfd = p.get('ppfd_min') or 0

        # Skip featured
        if pid in FEATURED_PLANTS:
            stats['skipped_featured'] += 1
            continue

        # Skip if has Ellenberg or PPFD (already handled by v4)
        if el > 0 or ppfd > 0:
            stats['skipped_evidence'] += 1
            continue

        # Skip if has any light evidence from sources
        if pid in has_evidence:
            stats['skipped_evidence'] += 1
            continue

        # Rule 1: wet tropical + understory lifeform → Bright indirect
        # Trees and shrubs in tropics often DO need full sun (canopy level)
        # But climbers, epiphytes, ferns, perennials, aquatics are understory
        if climate == 'wet tropical' and preset in ('climber', 'epiphyte', 'fern', 'perennial', 'aquatic', 'bulb', 'moss'):
            fixes.append((pid, 'Bright indirect light', f'wet tropical {preset}, likely understory'))
            stats['wet_tropical'] += 1
            continue

        # Rule 2: temperate + shade lifeform → Bright indirect
        if climate == 'temperate' and preset in SHADE_LIFEFORMS:
            fixes.append((pid, 'Bright indirect light', f'temperate {preset}, no evidence for Full sun'))
            stats['temperate_shade_lf'] += 1
            continue

        # Rule 3: temperate + habitat=forest → Part sun
        if climate == 'temperate' and pid in habitats:
            hab = habitats[pid]
            if any(kw in hab for kw in FOREST_KEYWORDS):
                fixes.append((pid, 'Part sun', f'temperate + forest habitat ({hab[:50]}...)'))
                stats['temperate_forest'] += 1
                continue

    total_fixes = len(fixes)
    print(f"  Fixes identified: {total_fixes}", flush=True)
    print(f"    wet tropical → Bright indirect: {stats['wet_tropical']}", flush=True)
    print(f"    temperate shade lifeform → Bright indirect: {stats['temperate_shade_lf']}", flush=True)
    print(f"    temperate forest habitat → Part sun: {stats['temperate_forest']}", flush=True)
    print(f"    Skipped (has evidence): {stats['skipped_evidence']}", flush=True)
    print(f"    Skipped (featured): {stats['skipped_featured']}", flush=True)

    if dry_run:
        print("\n  Sample fixes:", flush=True)
        for pid, new_light, reason in fixes[:20]:
            print(f"    {pid:35s} → {new_light:25s} | {reason[:60]}", flush=True)
    else:
        print("\n=== STEP 3: Apply Fixes ===", flush=True)
        stmts = []
        for pid, new_light, reason in fixes:
            stmts.append((
                "UPDATE care SET light_preferred = ? WHERE plant_id = ?",
                [new_light, pid]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v5', 'changed', ?, datetime('now'))",
                [pid, f'Full sun → {new_light}: {reason}']
            ))

            if len(stmts) >= 200:
                turso_batch(stmts)
                stmts = []

        if stmts:
            turso_batch(stmts)
        print(f"  Applied: {total_fixes} fixes", flush=True)

    print("\n=== STEP 4: Stats ===", flush=True)
    dist = retry_query("SELECT light_preferred, COUNT(*) as c FROM care GROUP BY light_preferred ORDER BY c DESC")
    total = sum(d['c'] for d in dist)
    print("  Light distribution:", flush=True)
    for d in dist:
        pct = 100 * d['c'] // total
        print(f"    {d['light_preferred']:25s} {d['c']:6d} ({pct}%)", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run)
