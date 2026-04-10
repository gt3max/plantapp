"""
Polish taxonomy — fill synonyms, difficulty, order, origin from existing sources.

Step 1: WCVP synonyms (from CSV, no API)
Step 2: Difficulty from PFAF growth + lifeform defaults
Step 3: Order from family→order APG IV mapping
Step 4: Origin from PFAF range + WCVP geographic_area
Step 5: Flag remaining

Usage:
    python3 polish_taxonomy.py --dry-run
    python3 polish_taxonomy.py
    python3 polish_taxonomy.py --step 1
"""
import sys
import os
import csv
import re
import json

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

WCVP_CSV = '/private/tmp/wcvp_names.csv'

# Lifeform → default difficulty
LIFEFORM_DIFFICULTY = {
    'succulent': 'Easy',
    'moss': 'Easy',
    'annual': 'Easy',
    'perennial': 'Medium',
    'tree': 'Medium',
    'shrub': 'Medium',
    'subshrub': 'Medium',
    'climber': 'Medium',
    'bulb': 'Medium',
    'bamboo': 'Medium',
    'fern': 'Medium',
    'epiphyte': 'Hard',
    'aquatic': 'Hard',
    'parasitic': 'Hard',
}

# APG IV: Family → Order mapping (major families)
FAMILY_TO_ORDER = {
    # Monocots
    'Araceae': 'Alismatales', 'Hydrocharitaceae': 'Alismatales', 'Juncaginaceae': 'Alismatales',
    'Asparagaceae': 'Asparagales', 'Orchidaceae': 'Asparagales', 'Iridaceae': 'Asparagales',
    'Amaryllidaceae': 'Asparagales', 'Asphodelaceae': 'Asparagales',
    'Arecaceae': 'Arecales',
    'Commelinaceae': 'Commelinales', 'Pontederiaceae': 'Commelinales',
    'Bromeliaceae': 'Poales', 'Poaceae': 'Poales', 'Cyperaceae': 'Poales',
    'Juncaceae': 'Poales', 'Typhaceae': 'Poales',
    'Dioscoreaceae': 'Dioscoreales',
    'Liliaceae': 'Liliales', 'Colchicaceae': 'Liliales', 'Melanthiaceae': 'Liliales',
    'Musaceae': 'Zingiberales', 'Zingiberaceae': 'Zingiberales', 'Strelitziaceae': 'Zingiberales',
    'Heliconiaceae': 'Zingiberales', 'Costaceae': 'Zingiberales', 'Marantaceae': 'Zingiberales',
    'Cannaceae': 'Zingiberales',
    # Eudicots - Rosids
    'Rosaceae': 'Rosales', 'Moraceae': 'Rosales', 'Ulmaceae': 'Rosales',
    'Urticaceae': 'Rosales', 'Rhamnaceae': 'Rosales', 'Cannabaceae': 'Rosales',
    'Fabaceae': 'Fabales', 'Polygalaceae': 'Fabales',
    'Fagaceae': 'Fagales', 'Betulaceae': 'Fagales', 'Juglandaceae': 'Fagales',
    'Myricaceae': 'Fagales', 'Casuarinaceae': 'Fagales',
    'Cucurbitaceae': 'Cucurbitales', 'Begoniaceae': 'Cucurbitales',
    'Euphorbiaceae': 'Malpighiales', 'Salicaceae': 'Malpighiales', 'Violaceae': 'Malpighiales',
    'Passifloraceae': 'Malpighiales', 'Phyllanthaceae': 'Malpighiales',
    'Crassulaceae': 'Saxifragales', 'Saxifragaceae': 'Saxifragales',
    'Vitaceae': 'Vitales',
    'Myrtaceae': 'Myrtales', 'Onagraceae': 'Myrtales', 'Melastomataceae': 'Myrtales',
    'Brassicaceae': 'Brassicales', 'Caricaceae': 'Brassicales',
    'Malvaceae': 'Malvales', 'Thymelaeaceae': 'Malvales',
    'Sapindaceae': 'Sapindales', 'Rutaceae': 'Sapindales', 'Meliaceae': 'Sapindales',
    'Anacardiaceae': 'Sapindales', 'Burseraceae': 'Sapindales',
    'Geraniaceae': 'Geraniales',
    'Combretaceae': 'Myrtales', 'Lythraceae': 'Myrtales',
    # Eudicots - Asterids
    'Asteraceae': 'Asterales', 'Campanulaceae': 'Asterales',
    'Apiaceae': 'Apiales', 'Araliaceae': 'Apiales',
    'Lamiaceae': 'Lamiales', 'Verbenaceae': 'Lamiales', 'Acanthaceae': 'Lamiales',
    'Plantaginaceae': 'Lamiales', 'Gesneriaceae': 'Lamiales', 'Bignoniaceae': 'Lamiales',
    'Oleaceae': 'Lamiales', 'Orobanchaceae': 'Lamiales', 'Scrophulariaceae': 'Lamiales',
    'Solanaceae': 'Solanales', 'Convolvulaceae': 'Solanales',
    'Boraginaceae': 'Boraginales',
    'Gentianaceae': 'Gentianales', 'Rubiaceae': 'Gentianales', 'Apocynaceae': 'Gentianales',
    'Ericaceae': 'Ericales', 'Primulaceae': 'Ericales', 'Theaceae': 'Ericales',
    'Caprifoliaceae': 'Dipsacales',
    # Basal angiosperms
    'Lauraceae': 'Laurales', 'Magnoliaceae': 'Magnoliales',
    'Piperaceae': 'Piperales', 'Aristolochiaceae': 'Piperales',
    'Nymphaeaceae': 'Nymphaeales',
    # Gymnosperms
    'Pinaceae': 'Pinales', 'Cupressaceae': 'Pinales', 'Taxaceae': 'Pinales',
    'Araucariaceae': 'Araucariales', 'Podocarpaceae': 'Araucariales',
    'Cycadaceae': 'Cycadales', 'Zamiaceae': 'Cycadales',
    # Ferns
    'Polypodiaceae': 'Polypodiales', 'Dryopteridaceae': 'Polypodiales',
    'Aspleniaceae': 'Polypodiales', 'Pteridaceae': 'Polypodiales',
    'Blechnaceae': 'Polypodiales', 'Dennstaedtiaceae': 'Polypodiales',
    'Thelypteridaceae': 'Polypodiales',
    'Cyatheaceae': 'Cyatheales',
    'Osmundaceae': 'Osmundales',
    'Selaginellaceae': 'Selaginellales',
    'Lycopodiaceae': 'Lycopodiales',
    # Proteaceae etc
    'Proteaceae': 'Proteales', 'Platanaceae': 'Proteales',
    'Ranunculaceae': 'Ranunculales', 'Papaveraceae': 'Ranunculales',
    'Berberidaceae': 'Ranunculales',
    'Cactaceae': 'Caryophyllales', 'Aizoaceae': 'Caryophyllales',
    'Amaranthaceae': 'Caryophyllales', 'Caryophyllaceae': 'Caryophyllales',
    'Polygonaceae': 'Caryophyllales', 'Droseraceae': 'Caryophyllales',
    'Nyctaginaceae': 'Caryophyllales',
}


def step1_synonyms(dry_run=False):
    """Extract synonyms from WCVP CSV."""
    print(f"\n=== STEP 1: WCVP Synonyms ===", flush=True)

    if not os.path.exists(WCVP_CSV):
        print(f"  ERROR: WCVP CSV not found", flush=True)
        return

    # Build accepted_id → accepted_name mapping
    # Then synonym → accepted_id mapping
    print(f"  Parsing WCVP CSV...", flush=True)
    accepted_names = {}  # plant_name_id → taxon_name
    synonym_groups = {}  # accepted_plant_name_id → [synonym_names]

    with open(WCVP_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        next(reader)  # skip header
        for row in reader:
            if len(row) < 25:
                continue
            pid = row[0].strip()
            status = row[3].strip()
            taxon_name = row[21].strip()
            accepted_id = row[23].strip()

            if status == 'Accepted':
                accepted_names[pid] = taxon_name
            elif status == 'Synonym' and accepted_id:
                if accepted_id not in synonym_groups:
                    synonym_groups[accepted_id] = []
                synonym_groups[accepted_id].append(taxon_name)

    print(f"  Accepted: {len(accepted_names)}, Synonym groups: {len(synonym_groups)}", flush=True)

    # Build accepted_name → [synonyms]
    name_synonyms = {}
    for acc_id, syns in synonym_groups.items():
        acc_name = accepted_names.get(acc_id)
        if acc_name:
            # Clean to genus + species
            parts = acc_name.split()
            if len(parts) >= 2:
                key = ' '.join(parts[:2]).lower()
                name_synonyms[key] = [s for s in syns[:10]]  # max 10 synonyms

    print(f"  Name → synonyms mappings: {len(name_synonyms)}", flush=True)

    # Match with our DB
    our = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND (synonyms IS NULL OR synonyms = '')")
    print(f"  Plants without synonyms: {len(our)}", flush=True)

    stmts = []
    matched = 0

    for i, plant in enumerate(our):
        sci = plant['scientific'].lower()
        parts = sci.split()
        key = ' '.join(parts[:2]) if len(parts) >= 2 else sci

        syns = name_synonyms.get(key)
        if syns:
            matched += 1
            # Format: comma-separated
            syn_str = ', '.join(syns[:5])  # max 5 in plants.synonyms
            if not dry_run:
                stmts.append(("UPDATE plants SET synonyms = ? WHERE plant_id = ? AND (synonyms IS NULL OR synonyms = '')",
                              [syn_str, plant['plant_id']]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wcvp_synonyms', 'synonyms', ?, datetime('now'))",
                    [plant['plant_id'], syn_str[:200]]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

        if (i + 1) % 2000 == 0:
            print(f"  [{i+1}/{len(our)}] matched={matched}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Synonyms added: {matched}", flush=True)


def step2_difficulty(dry_run=False):
    """Fill difficulty from PFAF growth + lifeform defaults."""
    print(f"\n=== STEP 2: Difficulty ===", flush=True)

    # PFAF growth → difficulty
    pfaf_growth = turso_query("SELECT plant_id, value FROM source_data WHERE source = 'pfaf' AND field = 'growth'")
    growth_map = {'F': 'Easy', 'M': 'Medium', 'S': 'Hard'}

    stmts = []
    stats = {'pfaf': 0, 'lifeform': 0}

    for g in pfaf_growth:
        diff = growth_map.get(g['value'])
        if diff:
            if not dry_run:
                stmts.append(("UPDATE care SET difficulty = ? WHERE plant_id = ? AND (difficulty IS NULL OR difficulty = '')",
                              [diff, g['plant_id']]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_difficulty', 'difficulty', ?, datetime('now'))",
                    [g['plant_id'], f"growth={g['value']}→{diff}"]
                ))
            stats['pfaf'] += 1

    if stmts and not dry_run:
        turso_batch(stmts); stmts = []

    # Lifeform defaults for remaining
    remaining = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.difficulty IS NULL OR c.difficulty = '')
    """)

    for plant in remaining:
        diff = LIFEFORM_DIFFICULTY.get(plant.get('preset') or '')
        if diff:
            stats['lifeform'] += 1
            if not dry_run:
                stmts.append(("UPDATE care SET difficulty = ? WHERE plant_id = ? AND (difficulty IS NULL OR difficulty = '')",
                              [diff, plant['plant_id']]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'lifeform_difficulty', 'difficulty', ?, datetime('now'))",
                    [plant['plant_id'], f"{plant['preset']}→{diff}"]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  PFAF growth: {stats['pfaf']}, lifeform default: {stats['lifeform']}", flush=True)


def step3_order(dry_run=False):
    """Fill order from family → APG IV mapping."""
    print(f"\n=== STEP 3: Order (APG IV) ===", flush=True)

    plants = turso_query("SELECT plant_id, family FROM plants WHERE (order_name IS NULL OR order_name = '') AND family IS NOT NULL AND family != ''")
    print(f"  Plants without order: {len(plants)}", flush=True)

    stmts = []
    filled = 0

    for plant in plants:
        order = FAMILY_TO_ORDER.get(plant['family'])
        if order:
            filled += 1
            if not dry_run:
                stmts.append(("UPDATE plants SET order_name = ? WHERE plant_id = ?",
                              [order, plant['plant_id']]))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Order filled: {filled}", flush=True)


def step4_origin(dry_run=False):
    """Fill origin from PFAF range."""
    print(f"\n=== STEP 4: Origin from PFAF ===", flush=True)

    pfaf_range = turso_query("""
        SELECT sd.plant_id, sd.value FROM source_data sd
        JOIN plants p ON sd.plant_id = p.plant_id
        WHERE sd.source = 'pfaf' AND sd.field = 'range'
        AND (p.origin IS NULL OR p.origin = '')
        AND sd.value IS NOT NULL AND sd.value != ''
    """)
    print(f"  PFAF range for plants without origin: {len(pfaf_range)}", flush=True)

    stmts = []
    filled = 0

    for r in pfaf_range:
        origin = r['value'][:200]
        if len(origin) > 10:
            filled += 1
            if not dry_run:
                stmts.append(("UPDATE plants SET origin = ? WHERE plant_id = ? AND (origin IS NULL OR origin = '')",
                              [origin, r['plant_id']]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_origin', 'origin', ?, datetime('now'))",
                    [r['plant_id'], origin[:100]]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Origin filled: {filled}", flush=True)


def step5_flag(dry_run=False):
    """Flag remaining empty fields."""
    print(f"\n=== STEP 5: Flag remaining ===", flush=True)

    for field, table, col in [
        ('synonyms', 'plants', 'synonyms'),
        ('difficulty', 'care', 'difficulty'),
        ('order', 'plants', 'order_name'),
        ('origin', 'plants', 'origin'),
    ]:
        remaining = turso_query(f"SELECT COUNT(*) as c FROM {table} WHERE ({col} IS NULL OR {col} = '')")
        cnt = remaining[0]['c']
        if cnt > 0:
            print(f"  {field}: {cnt} still empty", flush=True)


def show_results():
    """Show final stats."""
    print(f"\n=== TAXONOMY STATUS ===", flush=True)
    total = 20261
    for field, table, col in [
        ('synonyms', 'plants', 'synonyms'),
        ('difficulty', 'care', 'difficulty'),
        ('order', 'plants', 'order_name'),
        ('origin', 'plants', 'origin'),
    ]:
        r = turso_query(f"SELECT COUNT(*) as c FROM {table} WHERE {col} IS NOT NULL AND {col} != ''")
        print(f"  {field:15s} {r[0]['c']:>6} / {total} ({r[0]['c']*100//total}%)", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step_only = None
    if '--step' in sys.argv:
        idx = sys.argv.index('--step')
        if idx + 1 < len(sys.argv):
            step_only = int(sys.argv[idx + 1])

    if step_only is None or step_only == 1:
        step1_synonyms(dry_run)
    if step_only is None or step_only == 2:
        step2_difficulty(dry_run)
    if step_only is None or step_only == 3:
        step3_order(dry_run)
    if step_only is None or step_only == 4:
        step4_origin(dry_run)
    if step_only is None or step_only == 5:
        step5_flag(dry_run)

    show_results()
