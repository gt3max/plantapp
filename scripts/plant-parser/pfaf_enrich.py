"""
Enrich care fields from PFAF raw data already in source_data.
Only fills EMPTY fields. Source attribution: source='pfaf' for every field.

Sections:
1. Toxicity — known_hazards → toxic_to_humans ONLY (integer 1, NOT pets, NOT safe)
2. Light — shade (F/S/N) → light_preferred (Full sun/Part sun/Shade/Bright indirect light)
3. Used for — edible/medicinal/other → used_for (JSON array), edible_parts
4. Difficulty — cultivation_details keywords → Easy/Medium/Hard
5. Lifecycle — habit → perennial/annual/biennial (lowercase)

Usage:
    python3 pfaf_enrich.py              # full run
    python3 pfaf_enrich.py --dry-run    # preview
"""
import sys
import os
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


# --- 1. TOXICITY ---
# Only mark toxic_to_humans=1 if PFAF clearly says toxic/poisonous
# NEVER mark safe (0). NEVER touch toxic_to_pets (PFAF = human only).
# Exclude: irritant, allergen, stinging, thorns — not toxicity.
TOXIC_WORDS = ['toxic', 'poison', 'poisonous', 'fatal', 'lethal', 'death']
EXCLUDE_WORDS = ['irritant', 'skin contact', 'stinging', 'thorns', 'spines', 'sharp edges',
                 'allergen', 'allergic', 'dermatitis', 'no records of toxicity',
                 'although no specific mentions']


def map_toxicity(text):
    """Returns (toxic_to_humans, toxicity_severity, toxicity_note) or (None, None, None)."""
    if not text:
        return None, None, None
    lower = text.lower().strip()

    # Skip if only about irritation, not toxicity
    has_toxic = any(w in lower for w in TOXIC_WORDS)
    is_excluded = any(w in lower for w in EXCLUDE_WORDS) and not has_toxic

    if is_excluded or not has_toxic:
        return None, None, None

    # Determine severity
    if any(w in lower for w in ['fatal', 'lethal', 'death', 'highly toxic']):
        severity = 'Severe'
    elif any(w in lower for w in ['toxic if eaten', 'large quantities', 'raw']):
        severity = 'Moderate'
    else:
        severity = 'Mild'

    return 1, severity, text[:200]


# --- 2. LIGHT ---
SHADE_MAP = {
    'F': 'Shade',
    'S': 'Part sun',
    'N': 'Full sun',
    'FS': 'Shade',
    'SN': 'Part sun',
    'NS': 'Part sun',
    'FSN': 'Part sun',
    'FN': 'Part sun',
}


# --- 3. USED FOR ---
def map_used_for(edible, medicinal, other):
    """Returns JSON array string or None."""
    uses = []
    if edible and edible.lower() != 'none known':
        uses.append('Edible')
    if medicinal and medicinal.lower() != 'none known':
        uses.append('Medicinal')
    if other and other.lower() != 'none known':
        uses.append('Other uses')
    return json.dumps(uses) if uses else None


# --- 4. DIFFICULTY ---
def map_difficulty(cultivation_text):
    """Returns Easy/Medium/Hard or None. Conservative — only clear markers."""
    if not cultivation_text:
        return None
    lower = cultivation_text.lower()

    # Strong easy markers
    if any(w in lower for w in ['very easy', 'extremely easy', 'low maintenance',
                                 'undemanding', 'practically indestructible']):
        return 'Easy'

    # Strong hard markers (exclude "difficult to propagate" — that's not care difficulty)
    if any(w in lower for w in ['difficult to grow', 'very demanding', 'specialist',
                                 'expert grower', 'challenging to maintain']):
        return 'Hard'

    # Moderate easy markers (but not if also mentions problems)
    if 'easy' in lower and 'not easy' not in lower and 'difficult' not in lower:
        return 'Easy'

    return None


# --- 5. LIFECYCLE ---
LIFECYCLE_MAP = {
    'annual': 'annual',
    'biennial': 'biennial',
    'perennial': 'perennial',
    'tree': 'perennial',
    'shrub': 'perennial',
    'fern': 'perennial',
    'climber': 'perennial',
    'bulb': 'bulb',
    'annual/biennial': 'annual',
    'annual/perennial': 'perennial',
    'perennial climber': 'perennial',
}


def run(dry_run=False):
    # Single query: get all PFAF plants with their raw data + current care
    print(f"[pfaf_enrich] Loading PFAF data from source_data...", flush=True)

    pfaf_raw = turso_query("""
        SELECT sd.plant_id, sd.field, sd.value
        FROM source_data sd
        WHERE sd.source = 'pfaf'
    """)

    # Group by plant_id
    plants_data = {}
    for r in pfaf_raw:
        pid = r['plant_id']
        if pid not in plants_data:
            plants_data[pid] = {}
        plants_data[pid][r['field']] = r['value']

    plant_ids = list(plants_data.keys())
    print(f"[pfaf_enrich] {len(plant_ids)} plants with PFAF data", flush=True)

    # Batch load care data
    care_data = {}
    batch_size = 200
    for i in range(0, len(plant_ids), batch_size):
        batch = plant_ids[i:i+batch_size]
        placeholders = ','.join(['?' for _ in batch])
        rows = turso_query(f"""
            SELECT plant_id, toxic_to_humans, toxicity_severity, toxicity_note,
                   light_preferred, used_for, edible_parts, difficulty, lifecycle
            FROM care WHERE plant_id IN ({placeholders})
        """, batch)
        for r in rows:
            care_data[r['plant_id']] = r

    print(f"[pfaf_enrich] Loaded care for {len(care_data)} plants", flush=True)

    stmts = []
    stats = {
        'tox_set': 0, 'tox_skip': 0,
        'light_set': 0, 'light_skip': 0,
        'used_for_set': 0, 'edible_set': 0,
        'diff_set': 0, 'diff_skip': 0,
        'lifecycle_set': 0, 'lifecycle_skip': 0,
    }

    for i, pid in enumerate(plant_ids):
        pfaf = plants_data[pid]
        care = care_data.get(pid)
        if not care:
            continue

        # === 1. TOXICITY ===
        hazards = pfaf.get('known_hazards', '')
        if hazards:
            tox_val, severity, note = map_toxicity(hazards)
            if tox_val is not None and (care.get('toxic_to_humans') is None):
                stats['tox_set'] += 1
                if not dry_run:
                    stmts.append(("UPDATE care SET toxic_to_humans = ? WHERE plant_id = ? AND toxic_to_humans IS NULL",
                                  [tox_val, pid]))
                    if severity:
                        stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ? AND (toxicity_severity IS NULL OR toxicity_severity = '')",
                                      [severity, pid]))
                    if note:
                        stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                                      [note, pid]))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'toxicity_mapped', 'toxic_to_humans=1', datetime('now'))",
                        [pid]))
            else:
                stats['tox_skip'] += 1

        # === 2. LIGHT ===
        shade = pfaf.get('shade', '')
        current_light = care.get('light_preferred') or ''
        if shade and not current_light:
            light = SHADE_MAP.get(shade)
            if light:
                stats['light_set'] += 1
                if not dry_run:
                    stmts.append(("UPDATE care SET light_preferred = ? WHERE plant_id = ? AND (light_preferred IS NULL OR light_preferred = '')",
                                  [light, pid]))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'light_mapped', ?, datetime('now'))",
                        [pid, f'shade={shade}→{light}']))
            else:
                stats['light_skip'] += 1

        # === 3. USED FOR ===
        edible = pfaf.get('edible_uses', '')
        medicinal = pfaf.get('medicinal_uses', '')
        other = pfaf.get('other_uses', '')
        current_used = care.get('used_for') or ''

        if not current_used:
            used_json = map_used_for(edible, medicinal, other)
            if used_json:
                stats['used_for_set'] += 1
                if not dry_run:
                    stmts.append(("UPDATE care SET used_for = ? WHERE plant_id = ? AND (used_for IS NULL OR used_for = '')",
                                  [used_json, pid]))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'used_for_mapped', ?, datetime('now'))",
                        [pid, used_json]))

        current_edible = care.get('edible_parts') or ''
        if edible and edible.lower() != 'none known' and not current_edible:
            stats['edible_set'] += 1
            if not dry_run:
                stmts.append(("UPDATE care SET edible_parts = ? WHERE plant_id = ? AND (edible_parts IS NULL OR edible_parts = '')",
                              [edible[:300], pid]))

        # === 4. DIFFICULTY ===
        cultivation = pfaf.get('cultivation_details', '')
        current_diff = care.get('difficulty') or ''
        if not current_diff:
            diff = map_difficulty(cultivation)
            if diff:
                stats['diff_set'] += 1
                if not dry_run:
                    stmts.append(("UPDATE care SET difficulty = ? WHERE plant_id = ? AND (difficulty IS NULL OR difficulty = '')",
                                  [diff, pid]))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'difficulty_mapped', ?, datetime('now'))",
                        [pid, diff]))
            else:
                stats['diff_skip'] += 1

        # === 5. LIFECYCLE ===
        habit = pfaf.get('habit', '')
        current_life = care.get('lifecycle') or ''
        if not current_life and habit:
            lifecycle = LIFECYCLE_MAP.get(habit.lower().strip())
            if lifecycle:
                stats['lifecycle_set'] += 1
                if not dry_run:
                    stmts.append(("UPDATE care SET lifecycle = ? WHERE plant_id = ? AND (lifecycle IS NULL OR lifecycle = '')",
                                  [lifecycle, pid]))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'lifecycle_mapped', ?, datetime('now'))",
                        [pid, f'habit={habit}→{lifecycle}']))
            else:
                stats['lifecycle_skip'] += 1

        # Batch
        if len(stmts) >= 100:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(plant_ids)}] tox={stats['tox_set']} light={stats['light_set']} used={stats['used_for_set']} diff={stats['diff_set']} life={stats['lifecycle_set']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[pfaf_enrich] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
