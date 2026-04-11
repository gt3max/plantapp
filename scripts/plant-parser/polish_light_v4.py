"""
Polish light v4 — cross-validate light classification with new sources.

Problem: 74% plants marked Full sun, 42% of those with ZERO evidence.
Solution: Add PFAF habitats, MiFloraDB sunlight, USDA shade_tolerance as new votes.
Fix only where multiple sources unanimously contradict current classification.

Step 1: Extract PFAF habitats + range → light vote + raw data to source_data
Step 2: Extract MiFloraDB sunlight + origin → light vote
Step 3: Extract USDA shade_tolerance → light vote
Step 4: Cross-validate all sources, flag contradictions
Step 5: Fix proven errors (≥3 sources disagree OR Ellenberg L < 5 + Full sun)
Step 6: Stats

Usage:
    python3 polish_light_v4.py --dry-run
    python3 polish_light_v4.py
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

# Light levels: 0=Shade, 1=Bright indirect, 2=Part sun, 3=Full sun
LIGHT_LEVELS = ['Shade', 'Bright indirect light', 'Part sun', 'Full sun']

FEATURED_PLANTS = [
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
]


def normalize_name(name):
    if not name:
        return ''
    return re.sub(r'\s+', ' ', name.lower().strip().split(' var.')[0].split(' subsp.')[0])


def light_index(level):
    try:
        return LIGHT_LEVELS.index(level)
    except ValueError:
        return -1


def index_to_light(idx):
    idx = max(0, min(3, round(idx)))
    return LIGHT_LEVELS[idx]


# ── Habitat keyword → light mapping ──────────────────────────────────
SHADE_KEYWORDS = [
    'dense forest', 'deep shade', 'dark forest', 'understory', 'under trees',
    'forest floor', 'shaded', 'heavily shaded', 'dense woodland',
]
BRIGHT_INDIRECT_KEYWORDS = [
    'forest', 'woodland', 'rainforest', 'tropical forest', 'cloud forest',
    'moist forest', 'humid forest', 'montane forest', 'jungle',
    'damp places', 'stream bank', 'riverside', 'ravine',
    'partial shade', 'semi-shade', 'light shade', 'filtered light',
]
PART_SUN_KEYWORDS = [
    'forest edge', 'forest margin', 'woodland edge', 'clearing',
    'hedgerow', 'thicket', 'scrub', 'rocky slope', 'mountain meadow',
    'open woodland', 'light woodland', 'meadow', 'field margin',
]
FULL_SUN_KEYWORDS = [
    'open grassland', 'steppe', 'prairie', 'desert', 'dry scrub',
    'full sun', 'exposed', 'open places', 'dry slopes', 'sandy coast',
    'dune', 'arid', 'semi-arid', 'savanna', 'dry hillside',
]


def parse_habitat_light(habitat_text):
    """Extract light preference from habitat description. Returns (light_index, confidence)."""
    if not habitat_text:
        return None, 0
    t = habitat_text.lower()

    # Check keywords in order of specificity
    shade_score = sum(1 for kw in SHADE_KEYWORDS if kw in t)
    bright_score = sum(1 for kw in BRIGHT_INDIRECT_KEYWORDS if kw in t)
    part_score = sum(1 for kw in PART_SUN_KEYWORDS if kw in t)
    full_score = sum(1 for kw in FULL_SUN_KEYWORDS if kw in t)

    scores = [shade_score, bright_score, part_score, full_score]
    total = sum(scores)
    if total == 0:
        return None, 0

    # Weighted average
    weighted = (0 * shade_score + 1 * bright_score + 2 * part_score + 3 * full_score) / total
    confidence = max(scores) / total  # How dominant is the winner
    return round(weighted), confidence


def parse_miflora_sunlight(text):
    """Parse MiFloraDB sunlight text → light_index."""
    if not text:
        return None
    t = text.lower()

    # Strong shade indicators
    if 'not resistant to shade' in t and 'like sunshine' in t:
        return 3  # Full sun, can't handle shade
    if 'like strong light' in t and 'not resistant' in t:
        return 3

    # Shade tolerant
    if 'strong resistant to shade' in t or 'very resistant to shade' in t:
        return 0  # Shade
    if 'relatively strong resistant to shade' in t:
        return 1  # Bright indirect

    # Partial shade
    if 'like half shade' in t or 'prefer half shade' in t:
        return 1  # Bright indirect
    if 'resistant to half shade' in t or 'slight shade tolerance' in t:
        return 2  # Part sun
    if 'half shade' in t:
        return 1

    # Full sun
    if 'enjoy sufficient sunlight' in t or 'like sunshine' in t:
        return 3  # Full sun (default for "like sunshine" without shade tolerance)

    # Fallback
    if 'sun' in t or 'light' in t:
        return 3
    if 'shade' in t:
        return 1

    return None


def parse_usda_shade(tolerance):
    """Parse USDA shade_tolerance → light_index."""
    if not tolerance:
        return None
    t = tolerance.strip().lower()
    if t == 'high':
        return 1  # Bright indirect (tolerates shade well)
    elif t == 'medium':
        return 2  # Part sun
    elif t == 'low':
        return 3  # Full sun (can't handle shade)
    return None


# ═══════════════════════════════════════════════════════════════════════

def step1_pfaf_habitats(dry_run, votes):
    """Extract PFAF habitats + range → light vote + save raw data."""
    print("\n=== STEP 1: PFAF Habitats ===", flush=True)

    pfaf_db = DATA_DIR / 'pfaf' / 'data.sqlite'
    if not pfaf_db.exists():
        print("  PFAF database not found, skipping", flush=True)
        return

    # Load plant name mapping
    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    conn = sqlite3.connect(str(pfaf_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT latin_name, habitats, range, shade FROM plants").fetchall()
    conn.close()

    matched = 0
    voted = 0
    stmts = []

    for row in rows:
        latin = row['latin_name']
        pid = name_to_pid.get(normalize_name(latin))
        if not pid:
            continue
        matched += 1

        habitat = row['habitats'] or ''
        range_text = row['range'] or ''

        # Save raw data to source_data
        if not dry_run:
            if habitat:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_habitat', 'habitats', ?, datetime('now'))",
                    [pid, habitat]
                ))
            if range_text:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_habitat', 'range', ?, datetime('now'))",
                    [pid, range_text]
                ))

        # Extract light vote from habitat
        light_idx, confidence = parse_habitat_light(habitat)
        if light_idx is not None and confidence >= 0.5:
            if pid not in votes:
                votes[pid] = []
            votes[pid].append(('pfaf_habitat', light_idx, 2))  # weight 2
            voted += 1

            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_habitat', 'light_vote', ?, datetime('now'))",
                    [pid, f'{LIGHT_LEVELS[light_idx]} (conf={confidence:.2f})']
                ))

        if len(stmts) >= 200:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  PFAF matched: {matched}", flush=True)
    print(f"  Habitat light votes: {voted}", flush=True)


def step2_miflora_sunlight(dry_run, votes):
    """Extract MiFloraDB sunlight + origin → light vote."""
    print("\n=== STEP 2: MiFloraDB Sunlight ===", flush=True)

    csv_path = DATA_DIR / 'mifloradb_5335.csv'
    if not csv_path.exists():
        print("  MiFloraDB CSV not found, skipping", flush=True)
        return

    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    matched = 0
    voted = 0
    stmts = []

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid_csv = row.get('pid', '').strip()
            pid = name_to_pid.get(normalize_name(pid_csv))
            if not pid:
                continue
            matched += 1

            sunlight = row.get('sunlight', '').strip()
            origin = row.get('origin', '').strip()

            # Save origin
            if origin and not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'miflora', 'origin', ?, datetime('now'))",
                    [pid, origin]
                ))

            # Light vote
            light_idx = parse_miflora_sunlight(sunlight)
            if light_idx is not None:
                if pid not in votes:
                    votes[pid] = []
                votes[pid].append(('miflora_sunlight', light_idx, 2))  # weight 2
                voted += 1

                if not dry_run:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'miflora', 'light_vote', ?, datetime('now'))",
                        [pid, f'{LIGHT_LEVELS[light_idx]} (from: {sunlight[:60]})']
                    ))

            if len(stmts) >= 200:
                if not dry_run:
                    turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  MiFloraDB matched: {matched}", flush=True)
    print(f"  Sunlight votes: {voted}", flush=True)


def step3_usda_shade(dry_run, votes):
    """Extract USDA shade_tolerance → light vote."""
    print("\n=== STEP 3: USDA Shade Tolerance ===", flush=True)

    usda_path = DATA_DIR / 'usda_plant_characteristics.csv'
    if not usda_path.exists():
        print("  USDA CSV not found, skipping", flush=True)
        return

    plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL AND scientific != ''")
    name_to_pid = {normalize_name(p['scientific']): p['plant_id'] for p in plants if p['scientific']}

    matched = 0
    voted = 0
    stmts = []

    with open(usda_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sci = row.get('scientific_name', '').strip()
            shade = row.get('shade_tolerance', '').strip()
            pid = name_to_pid.get(normalize_name(sci))
            if not pid or not shade:
                continue
            matched += 1

            light_idx = parse_usda_shade(shade)
            if light_idx is not None:
                if pid not in votes:
                    votes[pid] = []
                votes[pid].append(('usda_shade', light_idx, 2))  # weight 2
                voted += 1

                if not dry_run:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'shade_tolerance', ?, datetime('now'))",
                        [pid, shade]
                    ))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'usda', 'light_vote', ?, datetime('now'))",
                        [pid, f'{LIGHT_LEVELS[light_idx]} (shade_tol={shade})']
                    ))

            if len(stmts) >= 200:
                if not dry_run:
                    turso_batch(stmts)
                stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  USDA matched: {matched}", flush=True)
    print(f"  Shade tolerance votes: {voted}", flush=True)


def step4_cross_validate(dry_run, votes):
    """Cross-validate all sources, flag contradictions."""
    print("\n=== STEP 4: Cross-Validate ===", flush=True)

    # Load existing data
    care_data = turso_query(
        "SELECT plant_id, light_preferred, ellenberg_l, ppfd_min, ppfd_max FROM care"
    )

    # Load existing PFAF shade from source_data
    pfaf_shade_rows = turso_query("SELECT plant_id, value FROM source_data WHERE field = 'shade'")
    pfaf_shade_map = {r['plant_id']: r['value'] for r in pfaf_shade_rows}

    PFAF_SHADE_TO_IDX = {
        'N': 3, 'SN': 2, 'NS': 2, 'S': 1, 'FS': 1, 'FSN': 2, 'F': 0, 'FN': 1,
    }

    contradictions = 0
    total_with_votes = 0

    for row in care_data:
        pid = row['plant_id']
        current = row['light_preferred']
        current_idx = light_index(current)
        if current_idx < 0:
            continue

        # Collect ALL votes for this plant
        all_votes = list(votes.get(pid, []))

        # Add Ellenberg L (weight 4)
        el = row.get('ellenberg_l') or 0
        if el > 0:
            if el <= 2:
                all_votes.append(('ellenberg', 0, 4))
            elif el <= 4:
                all_votes.append(('ellenberg', 1, 4))
            elif el <= 6:
                all_votes.append(('ellenberg', 2, 4))
            else:
                all_votes.append(('ellenberg', 3, 4))

        # Add PFAF shade code (weight 2)
        shade = pfaf_shade_map.get(pid, '')
        if shade in PFAF_SHADE_TO_IDX:
            all_votes.append(('pfaf_shade', PFAF_SHADE_TO_IDX[shade], 2))

        # Add PPFD (weight 3)
        ppfd_min = row.get('ppfd_min') or 0
        ppfd_max = row.get('ppfd_max') or 0
        if ppfd_max > 0:
            mid = (ppfd_min + ppfd_max) / 2
            if mid >= 400:
                all_votes.append(('ppfd', 3, 3))
            elif mid >= 200:
                all_votes.append(('ppfd', 2, 3))
            elif mid >= 50:
                all_votes.append(('ppfd', 1, 3))
            else:
                all_votes.append(('ppfd', 0, 3))

        if not all_votes:
            continue

        total_with_votes += 1

        # Weighted average
        total_weight = sum(w for _, _, w in all_votes)
        weighted_sum = sum(idx * w for _, idx, w in all_votes)
        consensus_idx = round(weighted_sum / total_weight)
        consensus = LIGHT_LEVELS[max(0, min(3, consensus_idx))]

        # Count how many sources disagree with current
        disagree_count = sum(1 for _, idx, _ in all_votes if abs(idx - current_idx) >= 2)
        agree_count = sum(1 for _, idx, _ in all_votes if abs(idx - current_idx) <= 1)

        # Store votes for step 5
        votes[pid] = all_votes
        # Store consensus
        if pid not in votes:
            votes[pid] = all_votes
        # Attach metadata
        votes[f'{pid}__consensus'] = consensus_idx
        votes[f'{pid}__disagree'] = disagree_count
        votes[f'{pid}__current'] = current_idx

        # Flag contradiction if ≥2 sources strongly disagree
        if disagree_count >= 2 and abs(consensus_idx - current_idx) >= 1:
            contradictions += 1

    print(f"  Plants with votes: {total_with_votes}", flush=True)
    print(f"  Contradictions flagged: {contradictions}", flush=True)


def step5_fix_errors(dry_run, votes):
    """Fix proven errors."""
    print("\n=== STEP 5: Fix Proven Errors ===", flush=True)

    care_data = turso_query("SELECT plant_id, light_preferred, ellenberg_l FROM care")

    fixes = []
    for row in care_data:
        pid = row['plant_id']
        current = row['light_preferred']
        current_idx = light_index(current)
        if current_idx < 0:
            continue

        # Skip featured plants — those were manually set
        if pid in FEATURED_PLANTS:
            continue

        consensus_idx = votes.get(f'{pid}__consensus')
        disagree_count = votes.get(f'{pid}__disagree', 0)

        if consensus_idx is None:
            continue

        el = row.get('ellenberg_l') or 0
        should_fix = False
        reason = ''

        # Rule 1: Full sun but Ellenberg says NOT full sun (L < 7)
        if current_idx == 3 and el > 0 and el < 7:
            should_fix = True
            reason = f'Ellenberg L={el} contradicts Full sun'

        # Rule 2: ≥2 sources disagree strongly
        elif disagree_count >= 2 and abs(consensus_idx - current_idx) >= 2:
            should_fix = True
            reason = f'{disagree_count} sources disagree, consensus={LIGHT_LEVELS[consensus_idx]}'

        # Rule 3: Full sun with no evidence + consensus says otherwise
        elif current_idx == 3 and el == 0:
            all_v = votes.get(pid, [])
            if len(all_v) >= 2 and consensus_idx <= 1:
                should_fix = True
                reason = f'Full sun no evidence, {len(all_v)} sources say {LIGHT_LEVELS[consensus_idx]}'

        if should_fix:
            new_light = LIGHT_LEVELS[max(0, min(3, consensus_idx))]
            fixes.append((pid, current, new_light, reason))

    print(f"  Fixes identified: {len(fixes)}", flush=True)

    if dry_run:
        # Show distribution of fixes
        from collections import Counter
        changes = Counter()
        for pid, old, new, reason in fixes:
            changes[f'{old} → {new}'] += 1
        print("  Fix distribution:", flush=True)
        for change, count in changes.most_common():
            print(f"    {change}: {count}", flush=True)

        # Show samples
        print("\n  Sample fixes:", flush=True)
        for pid, old, new, reason in fixes[:15]:
            print(f"    {pid:35s} {old:25s} → {new:25s} | {reason}", flush=True)
        return fixes

    # Apply fixes
    stmts = []
    for pid, old, new, reason in fixes:
        stmts.append((
            "UPDATE care SET light_preferred = ? WHERE plant_id = ?",
            [new, pid]
        ))
        stmts.append((
            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'light_v4', 'changed', ?, datetime('now'))",
            [pid, f'{old} → {new}: {reason}']
        ))

        if len(stmts) >= 200:
            turso_batch(stmts)
            stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"  Applied: {len(fixes)} fixes", flush=True)
    return fixes


def step6_stats(fixes):
    """Show final stats."""
    print("\n=== STEP 6: Results ===", flush=True)

    dist = turso_query(
        "SELECT light_preferred, COUNT(*) as c FROM care GROUP BY light_preferred ORDER BY c DESC"
    )
    total = sum(d['c'] for d in dist)
    print("  Light distribution:", flush=True)
    for d in dist:
        pct = 100 * d['c'] // total
        print(f"    {d['light_preferred']:25s} {d['c']:6d} ({pct}%)", flush=True)

    # Check featured plants unchanged
    featured_check = turso_query(
        f"SELECT plant_id, light_preferred FROM care WHERE plant_id IN ({','.join('?' for _ in FEATURED_PLANTS)})",
        FEATURED_PLANTS
    )
    print(f"\n  Featured plants: {len(featured_check)} checked (should be unchanged)", flush=True)

    # Contradictions remaining
    contrad = turso_query(
        "SELECT COUNT(DISTINCT plant_id) as c FROM source_data WHERE source = 'light_v4' AND field = 'changed'"
    )
    print(f"  Total changed by v4: {contrad[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    votes = {}  # {plant_id: [(source, light_idx, weight), ...]}

    step1_pfaf_habitats(dry_run, votes)
    step2_miflora_sunlight(dry_run, votes)
    step3_usda_shade(dry_run, votes)
    step4_cross_validate(dry_run, votes)
    fixes = step5_fix_errors(dry_run, votes)
    step6_stats(fixes)
