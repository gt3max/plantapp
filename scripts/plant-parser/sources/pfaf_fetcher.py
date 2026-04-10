"""
PFAF (Plants For A Future) — 8,504 plants with habit, soil, moisture, propagation, edible.
Source: SQLite from github.com/saulshanabrook/pfaf-data

Pipeline:
1. Match PFAF plants with our DB by scientific name
2. Store raw data in source_data (source='pfaf')
3. Verify lifeform classification (habit vs our preset)
4. Enrich care fields where empty (soil, propagation, edible, height)
5. Flag conflicts

Usage:
    python3 sources/pfaf_fetcher.py              # full run
    python3 sources/pfaf_fetcher.py --dry-run    # preview matches
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_query, turso_batch, store_source_data

PFAF_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'pfaf', 'data.sqlite')

HABIT_MAP = {
    'shrub': 'shrub',
    'tree': 'tree',
    'climber': 'climber',
    'bulb': 'bulb',
    'fern': 'fern',
    'perennial': 'perennial',
    'annual': 'annual',
    'biennial': 'annual',
    'annual/biennial': 'annual',
    'perennial climber': 'climber',
    'annual/perennial': 'perennial',
    'annual climber': 'climber',
}

# PFAF soil codes: L=light(sandy), M=medium(loamy), H=heavy(clay)
SOIL_MAP = {
    'L': 'Light (sandy)',
    'M': 'Medium (loamy)',
    'H': 'Heavy (clay)',
    'LM': 'Light to medium (sandy-loam)',
    'MH': 'Medium to heavy (loam-clay)',
    'LMH': 'All soil types',
}

# PFAF shade codes: F=full shade, S=semi-shade, N=no shade (full sun)
SHADE_MAP = {
    'F': 'Full shade',
    'S': 'Semi-shade',
    'N': 'Full sun',
    'FS': 'Full shade to semi-shade',
    'SN': 'Semi-shade to full sun',
    'FSN': 'Any light conditions',
    'FN': 'Full shade to full sun',
}

# PFAF moisture codes: D=dry, M=moist, We=wet
MOISTURE_MAP = {
    'D': 'Dry',
    'M': 'Moist',
    'We': 'Wet',
    'DM': 'Dry to moist',
    'MWe': 'Moist to wet',
    'DM We': 'Dry to wet',
    'DMWe': 'Dry to wet',
}


def run(dry_run=False):
    if not os.path.exists(PFAF_DB):
        print(f"ERROR: PFAF database not found at {PFAF_DB}", flush=True)
        return

    conn = sqlite3.connect(PFAF_DB)
    conn.row_factory = sqlite3.Row

    pfaf_plants = conn.execute("SELECT * FROM plants").fetchall()
    print(f"[pfaf] Loaded {len(pfaf_plants)} PFAF plants", flush=True)

    # Build lookup by latin name (lowercase)
    pfaf_by_name = {}
    for p in pfaf_plants:
        name = (p['latin_name'] or '').strip().lower()
        if name:
            pfaf_by_name[name] = dict(p)

    # Get our plants
    our_plants = turso_query("SELECT plant_id, scientific, preset, family FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    print(f"[pfaf] Our plants: {len(our_plants)}", flush=True)

    stmts = []
    stats = {
        'matched': 0, 'not_found': 0,
        'lifeform_confirmed': 0, 'lifeform_conflict': 0, 'lifeform_new': 0,
        'soil_enriched': 0, 'propagation_enriched': 0, 'edible_enriched': 0,
        'height_enriched': 0
    }

    for i, plant in enumerate(our_plants):
        sci = (plant['scientific'] or '').strip().lower()
        if sci not in pfaf_by_name:
            stats['not_found'] += 1
            continue

        pfaf = pfaf_by_name[sci]
        pid = plant['plant_id']
        stats['matched'] += 1

        if dry_run:
            if stats['matched'] <= 10:
                print(f"  MATCH: {pid:35s} habit={pfaf.get('habit','?'):15s} soil={pfaf.get('soil','?'):5s} moisture={pfaf.get('moisture','?')}", flush=True)
            continue

        # Store raw PFAF data in source_data
        raw_fields = {}
        for field in ['habit', 'height', 'hardiness', 'growth', 'soil', 'shade', 'moisture',
                       'edibility_rating', 'medicinal_rating', 'propagation', 'edible_uses',
                       'known_hazards', 'cultivation_details']:
            val = pfaf.get(field)
            if val is not None and str(val).strip():
                raw_fields[field] = str(val).strip()

        store_source_data(pid, 'pfaf', raw_fields)

        # --- Verify/assign lifeform ---
        pfaf_habit = (pfaf.get('habit') or '').strip().lower()
        mapped_lf = HABIT_MAP.get(pfaf_habit)
        our_preset = plant.get('preset') or ''

        if mapped_lf:
            if our_preset in ('standard', 'herb', 'tropical') or not our_preset:
                # Not classified — assign from PFAF
                stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [mapped_lf, pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'lifeform_assigned', ?, datetime('now'))",
                    [pid, mapped_lf]
                ))
                stats['lifeform_new'] += 1
            elif mapped_lf == our_preset:
                # Confirmed
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'lifeform_confirmed', 'true', datetime('now'))",
                    [pid]
                ))
                stats['lifeform_confirmed'] += 1
            else:
                # Conflict
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'conflict', 'pfaf_vs_lifeform', ?, datetime('now'))",
                    [pid, f"pfaf={mapped_lf} (habit={pfaf_habit}), ours={our_preset}"]
                ))
                stats['lifeform_conflict'] += 1

        # --- Enrich care fields where empty ---
        care = turso_query("SELECT soil_types, propagation_methods, used_for, edible_parts, height_min_cm, height_max_cm FROM care WHERE plant_id = ?", [pid])
        if care:
            c = care[0]

            # Soil
            pfaf_soil = pfaf.get('soil') or ''
            if pfaf_soil and (not c.get('soil_types') or c.get('soil_types') in ('', 'Well-drained')):
                soil_text = SOIL_MAP.get(pfaf_soil, pfaf_soil)
                pfaf_moisture = pfaf.get('moisture') or ''
                moisture_text = MOISTURE_MAP.get(pfaf_moisture, pfaf_moisture)
                full_soil = f"{soil_text}, {moisture_text}" if moisture_text else soil_text
                stmts.append(("UPDATE care SET soil_types = ? WHERE plant_id = ? AND (soil_types IS NULL OR soil_types = '' OR soil_types = 'Well-drained')",
                              [full_soil, pid]))
                stats['soil_enriched'] += 1

            # Propagation
            pfaf_prop = pfaf.get('propagation') or ''
            if pfaf_prop and not c.get('propagation_methods'):
                # Take first sentence
                short_prop = pfaf_prop[:200].split('.')[0] + '.' if '.' in pfaf_prop[:200] else pfaf_prop[:200]
                stmts.append(("UPDATE care SET propagation_methods = ? WHERE plant_id = ? AND (propagation_methods IS NULL OR propagation_methods = '')",
                              [short_prop, pid]))
                stats['propagation_enriched'] += 1

            # Edible
            pfaf_edible = pfaf.get('edible_uses') or ''
            if pfaf_edible and pfaf_edible != 'None known' and not c.get('edible_parts'):
                stmts.append(("UPDATE care SET edible_parts = ? WHERE plant_id = ? AND (edible_parts IS NULL OR edible_parts = '')",
                              [pfaf_edible[:300], pid]))
                stats['edible_enriched'] += 1

            # Height
            pfaf_height = pfaf.get('height')
            if pfaf_height and pfaf_height > 0 and not c.get('height_max_cm'):
                height_cm = int(pfaf_height * 100)
                stmts.append(("UPDATE care SET height_max_cm = ? WHERE plant_id = ? AND (height_max_cm IS NULL OR height_max_cm = 0)",
                              [height_cm, pid]))
                stats['height_enriched'] += 1

        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(our_plants)}] matched={stats['matched']} confirmed={stats['lifeform_confirmed']} conflict={stats['lifeform_conflict']} new={stats['lifeform_new']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    conn.close()

    print(f"\n[pfaf] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
