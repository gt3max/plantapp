"""
Polish fertilizer v2 — lifeform defaults + family NPK + PFAF + warnings for all 20K.

Step 1: Extract NPK from existing fertilizer_type text
Step 2: Lifeform defaults for ALL empty
Step 3: Family-specific NPK refinement
Step 4: PFAF cultivation_details → feed intensity
Step 5: Warnings by lifeform
Step 6: Flag remaining

Usage:
    python3 polish_fertilizer_v2.py --dry-run
    python3 polish_fertilizer_v2.py
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

LIFEFORM_FERT = {
    'succulent': {
        'type': 'Diluted cactus/succulent formula',
        'freq': 'Monthly during growing season (spring-summer), none in winter',
        'season': 'Spring, Summer',
        'npk': '2-7-7',
        'warning': 'Never fertilize in winter dormancy. Over-fertilization causes etiolation and weak growth.',
    },
    'epiphyte': {
        'type': 'Weak orchid fertilizer (20-20-20 diluted to 1/4 strength)',
        'freq': 'Every 2 weeks during active growth, monthly in winter',
        'season': 'Spring, Summer, Fall',
        'npk': '20-20-20 (1/4 strength)',
        'warning': 'Use diluted formula only. Concentrated fertilizer burns aerial roots.',
    },
    'climber': {
        'type': 'Balanced liquid fertilizer',
        'freq': 'Every 2-4 weeks during growing season',
        'season': 'Spring, Summer',
        'npk': '20-20-20',
        'warning': 'Reduce feeding in winter. Yellow leaves may indicate over-fertilization.',
    },
    'tree': {
        'type': 'Balanced slow-release granular fertilizer',
        'freq': 'Every 4-6 weeks during growing season',
        'season': 'Spring, Summer',
        'npk': '10-10-10',
        'warning': 'Do not fertilize newly transplanted trees for first year.',
    },
    'shrub': {
        'type': 'Balanced liquid fertilizer',
        'freq': 'Monthly during growing season',
        'season': 'Spring, Summer',
        'npk': '10-10-10',
        'warning': 'Avoid late-season fertilizing which promotes tender growth before winter.',
    },
    'subshrub': {
        'type': 'Balanced liquid fertilizer',
        'freq': 'Every 2-4 weeks during growing season',
        'season': 'Spring, Summer',
        'npk': '10-10-10',
        'warning': 'Reduce to half-strength for compact growth.',
    },
    'perennial': {
        'type': 'Balanced liquid fertilizer',
        'freq': 'Every 2-4 weeks during growing season',
        'season': 'Spring, Summer',
        'npk': '10-10-10',
        'warning': 'Stop fertilizing 6 weeks before first frost.',
    },
    'annual': {
        'type': 'Balanced fertilizer, higher in phosphorus for flowering',
        'freq': 'Weekly to biweekly during growing season',
        'season': 'Spring, Summer',
        'npk': '10-20-10',
        'warning': 'Stop fertilizing when fruiting/seeding begins.',
    },
    'bulb': {
        'type': 'Bone meal or bulb-specific fertilizer (low nitrogen)',
        'freq': 'At planting and when shoots emerge',
        'season': 'Spring',
        'npk': '5-10-10',
        'warning': 'Do not fertilize during dormancy. Avoid high-nitrogen which promotes leaves over flowers.',
    },
    'aquatic': {
        'type': 'Aquatic plant fertilizer tabs',
        'freq': 'Monthly during growing season',
        'season': 'Spring, Summer',
        'npk': 'Aquatic tabs',
        'warning': 'Over-fertilization causes algae bloom. Use aquatic-specific products only.',
    },
    'fern': {
        'type': 'Diluted balanced liquid fertilizer (half strength)',
        'freq': 'Monthly during growing season, none in winter',
        'season': 'Spring, Summer',
        'npk': '10-10-10 (half strength)',
        'warning': 'Avoid high-nitrogen fertilizers. Ferns are sensitive — use half-strength only.',
    },
    'bamboo': {
        'type': 'High-nitrogen fertilizer',
        'freq': 'Monthly during growing season',
        'season': 'Spring, Summer',
        'npk': '30-10-10',
        'warning': 'Heavy feeder. Lawn fertilizer works well. Avoid fertilizing in winter.',
    },
    'moss': {
        'type': 'None needed',
        'freq': 'Rarely if ever',
        'season': '',
        'npk': '',
        'warning': 'Do not fertilize — promotes competing species that outgrow moss.',
    },
    'parasitic': None,  # Depends on host
}

# Family NPK refinements (override lifeform NPK where family is more specific)
FAMILY_NPK = {
    'Araceae': {'npk': '20-10-10', 'note': 'Foliage plants — high nitrogen for leaf growth'},
    'Orchidaceae': {'npk': '20-20-20 (1/4 strength)', 'note': 'Delicate — dilute only'},
    'Cactaceae': {'npk': '2-7-7', 'note': 'Minimal nitrogen, more phosphorus/potassium'},
    'Crassulaceae': {'npk': '2-7-7', 'note': 'Succulent — very low nitrogen'},
    'Poaceae': {'npk': '20-10-10', 'note': 'Grasses — high nitrogen for vigorous growth'},
    'Fabaceae': {'npk': '5-20-20', 'note': 'Legumes fix own nitrogen — need phosphorus/potassium'},
    'Rosaceae': {'npk': '10-20-20', 'note': 'Flowering — high phosphorus/potassium for blooms'},
    'Solanaceae': {'npk': '10-20-20', 'note': 'Fruiting — high phosphorus/potassium'},
    'Ericaceae': {'npk': '10-10-10 (acidic formula)', 'note': 'Acid-loving — use azalea/rhododendron fertilizer'},
    'Bromeliaceae': {'npk': '10-10-10 (1/4 strength)', 'note': 'Epiphytic — very dilute foliar feeding'},
    'Marantaceae': {'npk': '10-10-10 (1/2 strength)', 'note': 'Sensitive roots — half strength'},
    'Begoniaceae': {'npk': '15-30-15', 'note': 'Flowering — high phosphorus'},
    'Gesneriaceae': {'npk': '14-12-14', 'note': 'African violet formula'},
}


def step1_extract_npk(dry_run=False):
    """Extract NPK from existing fertilizer_type text."""
    print(f"\n=== STEP 1: Extract NPK from text ===", flush=True)

    plants = turso_query("""
        SELECT plant_id, fertilizer_type FROM care
        WHERE fertilizer_type IS NOT NULL AND fertilizer_type != ''
        AND (fertilizer_npk IS NULL OR fertilizer_npk = '')
    """)
    print(f"  Plants with type but no NPK: {len(plants)}", flush=True)

    stmts = []
    found = 0
    for p in plants:
        text = p['fertilizer_type']
        # Match patterns: (10-10-10), 20-20-20, 2-7-7
        npk_match = re.search(r'(\d+-\d+-\d+)', text)
        if npk_match:
            npk = npk_match.group(1)
            # Check for dilution
            if '1/4' in text or 'quarter' in text.lower():
                npk += ' (1/4 strength)'
            elif '1/2' in text or 'half' in text.lower():
                npk += ' (half strength)'

            found += 1
            if not dry_run:
                stmts.append(("UPDATE care SET fertilizer_npk = ? WHERE plant_id = ?", [npk, p['plant_id']]))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  NPK extracted: {found}", flush=True)


def step2_lifeform_defaults(dry_run=False):
    """Apply lifeform defaults for ALL empty fertilizer fields."""
    print(f"\n=== STEP 2: Lifeform fertilizer defaults ===", flush=True)

    plants = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.fertilizer_freq IS NULL OR c.fertilizer_freq = '')
    """)
    print(f"  Plants without fertilizer: {len(plants)}", flush=True)

    stmts = []
    stats = {'filled': 0, 'no_default': 0}

    for i, plant in enumerate(plants):
        preset = plant.get('preset') or ''
        defaults = LIFEFORM_FERT.get(preset)
        if not defaults:
            stats['no_default'] += 1
            continue

        stats['filled'] += 1
        pid = plant['plant_id']

        if not dry_run:
            stmts.append(("UPDATE care SET fertilizer_type = ? WHERE plant_id = ? AND (fertilizer_type IS NULL OR fertilizer_type = '')",
                          [defaults['type'], pid]))
            stmts.append(("UPDATE care SET fertilizer_freq = ? WHERE plant_id = ? AND (fertilizer_freq IS NULL OR fertilizer_freq = '')",
                          [defaults['freq'], pid]))
            if defaults['season']:
                stmts.append(("UPDATE care SET fertilizer_season = ? WHERE plant_id = ? AND (fertilizer_season IS NULL OR fertilizer_season = '')",
                              [defaults['season'], pid]))
            if defaults['npk']:
                stmts.append(("UPDATE care SET fertilizer_npk = ? WHERE plant_id = ? AND (fertilizer_npk IS NULL OR fertilizer_npk = '')",
                              [defaults['npk'], pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'lifeform_fert_default', 'fertilizer', ?, datetime('now'))",
                [pid, f"{preset}→{defaults['npk'] or 'none'}"]
            ))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 2000 == 0:
            print(f"  [{i+1}/{len(plants)}] filled={stats['filled']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  Filled: {stats['filled']}, no default: {stats['no_default']}", flush=True)


def step3_family_npk(dry_run=False):
    """Refine NPK by family."""
    print(f"\n=== STEP 3: Family NPK refinement ===", flush=True)

    stmts = []
    total = 0

    for family, info in FAMILY_NPK.items():
        plants = turso_query("""
            SELECT c.plant_id FROM care c
            JOIN plants p ON c.plant_id = p.plant_id
            WHERE p.family = ? AND (c.fertilizer_npk IS NULL OR c.fertilizer_npk = '' OR c.fertilizer_npk = '10-10-10')
        """, [family])

        for p in plants:
            total += 1
            if not dry_run:
                stmts.append(("UPDATE care SET fertilizer_npk = ? WHERE plant_id = ?",
                              [info['npk'], p['plant_id']]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'family_npk', 'npk', ?, datetime('now'))",
                    [p['plant_id'], f"{family}→{info['npk']}: {info['note']}"]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

        if plants:
            print(f"  {family}: {len(plants)} plants → {info['npk']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  Total NPK refined: {total}", flush=True)


def step4_pfaf_fertilizer(dry_run=False):
    """Parse PFAF cultivation_details for feed intensity."""
    print(f"\n=== STEP 4: PFAF fertilizer parsing ===", flush=True)

    plants = turso_query("""
        SELECT sd.plant_id, sd.value FROM source_data sd
        WHERE sd.source = 'pfaf' AND sd.field = 'cultivation_details'
        AND (LOWER(sd.value) LIKE '%fertil%' OR LOWER(sd.value) LIKE '%feed%'
             OR LOWER(sd.value) LIKE '%manure%' OR LOWER(sd.value) LIKE '%nitrogen%'
             OR LOWER(sd.value) LIKE '%compost%')
    """)
    print(f"  PFAF with fertilizer mentions: {len(plants)}", flush=True)

    stmts = []
    tagged = 0

    for p in plants:
        text = p['value'].lower()
        pid = p['plant_id']
        intensity = None

        if any(w in text for w in ['heavy feeder', 'gross feeder', 'rich soil', 'very fertile', 'heavy manuring']):
            intensity = 'high'
        elif any(w in text for w in ['poor soil', 'light feeder', 'low fertility', 'infertile', 'thin soil']):
            intensity = 'low'
        elif any(w in text for w in ['moderate', 'average fertility']):
            intensity = 'medium'

        if intensity:
            tagged += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_fertilizer', 'feed_intensity', ?, datetime('now'))",
                    [pid, intensity]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  Tagged with intensity: {tagged}", flush=True)


def step5_warnings(dry_run=False):
    """Add fertilizer warnings by lifeform."""
    print(f"\n=== STEP 5: Fertilizer warnings ===", flush=True)

    plants = turso_query("""
        SELECT c.plant_id, p.preset FROM care c
        JOIN plants p ON c.plant_id = p.plant_id
        WHERE (c.fertilizer_warning IS NULL OR c.fertilizer_warning = '')
    """)
    print(f"  Plants without warning: {len(plants)}", flush=True)

    stmts = []
    filled = 0

    for plant in plants:
        preset = plant.get('preset') or ''
        defaults = LIFEFORM_FERT.get(preset)
        if not defaults or not defaults.get('warning'):
            continue

        filled += 1
        if not dry_run:
            stmts.append(("UPDATE care SET fertilizer_warning = ? WHERE plant_id = ? AND (fertilizer_warning IS NULL OR fertilizer_warning = '')",
                          [defaults['warning'], plant['plant_id']]))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  Warnings added: {filled}", flush=True)


def step6_flag_remaining(dry_run=False):
    """Flag plants still without fertilizer data."""
    print(f"\n=== STEP 6: Flag remaining ===", flush=True)

    remaining = turso_query("""
        SELECT plant_id FROM care
        WHERE fertilizer_freq IS NULL OR fertilizer_freq = ''
    """)

    stmts = []
    for r in remaining:
        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'fertilizer_no_data', 'no lifeform default available', datetime('now'))",
                [r['plant_id']]
            ))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)
    print(f"  Flagged: {len(remaining)}", flush=True)


def show_results():
    """Show fertilizer stats."""
    print(f"\n=== FERTILIZER STATUS ===", flush=True)
    total = 20261
    for f in ['fertilizer_freq', 'fertilizer_type', 'fertilizer_season', 'fertilizer_npk', 'fertilizer_warning']:
        r = turso_query(f"SELECT COUNT(*) as c FROM care WHERE {f} IS NOT NULL AND {f} != ''")
        print(f"  {f:25s} {r[0]['c']:>6} / {total} ({r[0]['c']*100//total}%)", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    step1_extract_npk(dry_run)
    step2_lifeform_defaults(dry_run)
    step3_family_npk(dry_run)
    step4_pfaf_fertilizer(dry_run)
    step5_warnings(dry_run)
    step6_flag_remaining(dry_run)
    show_results()
