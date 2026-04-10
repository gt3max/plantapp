"""
Toxicity v3 — mass enrichment from PFAF full rescan + family inference.

Step 1: PFAF full rescan — parse ALL 8,504 known_hazards (safe + toxic)
Step 2: Family-based toxicity inference for HIGH confidence families
Step 3: CalPoison list scrape (1,310 species)

Usage:
    python3 toxicity_v3_mass.py              # full run
    python3 toxicity_v3_mass.py --dry-run
    python3 toxicity_v3_mass.py --step 1
"""
import sys
import os
import re
import json
import sqlite3
import time
import urllib.request

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

PFAF_DB = os.path.join(os.path.dirname(__file__), 'data', 'pfaf', 'data.sqlite')
UA = 'PlantApp/1.0 (plantapp.pro)'

# Toxic substance keywords for PFAF parsing
TOXIC_SUBSTANCES = {
    'calcium oxalate': 'calcium oxalate crystals',
    'oxalate': 'calcium oxalate',
    'alkaloid': 'alkaloids',
    'glycoside': 'glycosides',
    'cardiac glycoside': 'cardiac glycosides',
    'cyanogenic': 'cyanogenic glycosides',
    'saponin': 'saponins',
    'ricin': 'ricin',
    'solanine': 'solanine',
    'atropine': 'tropane alkaloids',
    'pyrrolizidine': 'pyrrolizidine alkaloids',
    'grayanotoxin': 'grayanotoxins',
    'diterpene': 'diterpene esters',
    'latex': 'irritant latex',
    'protoanemonin': 'protoanemonin',
    'colchicine': 'colchicine',
    'digitalis': 'cardiac glycosides',
    'taxine': 'taxine alkaloids',
    'aconitine': 'aconitine alkaloids',
    'strychnine': 'strychnine',
}

TOXIC_PARTS_KEYWORDS = {
    'seed': 'Seeds', 'fruit': 'Fruit', 'berr': 'Berries', 'root': 'Roots',
    'bulb': 'Bulbs', 'leaf': 'Leaves', 'leav': 'Leaves', 'bark': 'Bark',
    'sap': 'Sap', 'latex': 'Latex/sap', 'flower': 'Flowers', 'stem': 'Stems',
    'all parts': 'All parts', 'whole plant': 'All parts',
}

# Family toxicity inference (HIGH confidence only)
TOXIC_FAMILIES = {
    'Araceae': {
        'toxic_to_humans': 1, 'toxic_to_pets': 1,
        'substance': 'calcium oxalate crystals',
        'parts': 'All parts (leaves, stems, sap)',
        'severity': 'Moderate',
        'symptoms': 'Oral irritation, swelling of mouth/tongue, difficulty swallowing, drooling',
        'confidence': 'HIGH',
    },
    'Euphorbiaceae': {
        'toxic_to_humans': 1, 'toxic_to_pets': 1,
        'substance': 'diterpene esters, irritant latex',
        'parts': 'Sap, leaves, stems',
        'severity': 'Moderate',
        'symptoms': 'Skin irritation, eye damage if contact, vomiting if ingested',
        'confidence': 'HIGH',
    },
    'Apocynaceae': {
        'toxic_to_humans': 1, 'toxic_to_pets': 1,
        'substance': 'cardiac glycosides',
        'parts': 'All parts',
        'severity': 'Severe',
        'symptoms': 'Nausea, vomiting, cardiac arrhythmia, potentially fatal',
        'confidence': 'HIGH',
    },
    'Ranunculaceae': {
        'toxic_to_humans': 1, 'toxic_to_pets': 1,
        'substance': 'protoanemonin, ranunculin',
        'parts': 'All parts, especially sap',
        'severity': 'Moderate',
        'symptoms': 'Skin irritation, mouth blistering, gastrointestinal upset',
        'confidence': 'HIGH',
    },
    'Taxaceae': {
        'toxic_to_humans': 1, 'toxic_to_pets': 1,
        'substance': 'taxine alkaloids',
        'parts': 'All parts except aril',
        'severity': 'Severe',
        'symptoms': 'Cardiac arrest, tremors, seizures, potentially fatal',
        'confidence': 'VERY_HIGH',
    },
}

# Families where MOST members are safe (for confirming safe)
SAFE_FAMILIES = {
    'Poaceae': 'Most grasses are non-toxic',
    'Asteraceae': 'Most composites are non-toxic (exceptions: ragwort, tansy)',
    'Brassicaceae': 'Most crucifers are edible',
    'Rosaceae': 'Most rose family is non-toxic (except Prunus seeds)',
    'Fabaceae': 'Most legumes are non-toxic (exceptions: lupine, laburnum)',
}


def parse_pfaf_hazards(text):
    """Parse PFAF known_hazards text → structured toxicity data."""
    if not text:
        return None

    lower = text.lower().strip()

    # Check if safe
    if 'none known' in lower or lower == 'no known hazards':
        return {'safe': True}

    # Only irritation, not toxicity?
    only_irritant = False
    if any(w in lower for w in ['irritant', 'irritation', 'stinging', 'thorns', 'spines', 'sharp']):
        if not any(w in lower for w in ['toxic', 'poison', 'fatal', 'death', 'lethal', 'alkaloid', 'glycoside']):
            only_irritant = True

    # Extract substances
    substances = []
    for keyword, substance in TOXIC_SUBSTANCES.items():
        if keyword in lower:
            substances.append(substance)

    # Extract parts
    parts = []
    for keyword, part in TOXIC_PARTS_KEYWORDS.items():
        if keyword in lower:
            parts.append(part)

    # Severity
    severity = 'Mild'
    if any(w in lower for w in ['fatal', 'death', 'lethal', 'potentially fatal', 'highly toxic']):
        severity = 'Severe'
    elif any(w in lower for w in ['toxic', 'poisonous', 'dangerous']):
        severity = 'Moderate'

    is_toxic = not only_irritant and (substances or any(w in lower for w in ['toxic', 'poison', 'fatal', 'death']))

    return {
        'safe': False,
        'toxic': is_toxic,
        'irritant_only': only_irritant,
        'substances': list(set(substances)),
        'parts': list(set(parts)),
        'severity': severity,
        'raw_text': text[:300],
    }


def step1_pfaf_full(dry_run=False):
    """Full PFAF rescan — all 8,504 plants."""
    print(f"\n=== STEP 1: PFAF full toxicity rescan ===", flush=True)

    conn = sqlite3.connect(PFAF_DB)
    conn.row_factory = sqlite3.Row
    pfaf_plants = conn.execute("SELECT latin_name, known_hazards FROM plants WHERE known_hazards IS NOT NULL AND known_hazards != ''").fetchall()
    conn.close()

    print(f"  PFAF plants with hazards: {len(pfaf_plants)}", flush=True)

    # Our DB lookup
    our = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our:
        sci = p['scientific'].lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    stmts = []
    stats = {'matched': 0, 'safe_confirmed': 0, 'toxic_found': 0, 'irritant': 0, 'substances': 0}

    for i, plant in enumerate(pfaf_plants):
        latin = plant['latin_name'].strip().lower()
        pid = our_by_name.get(latin)
        if not pid:
            parts = latin.split()
            if len(parts) >= 2:
                pid = our_by_name.get(' '.join(parts[:2]))
        if not pid:
            continue

        stats['matched'] += 1
        parsed = parse_pfaf_hazards(plant['known_hazards'])
        if not parsed:
            continue

        if not dry_run:
            if parsed.get('safe'):
                # Confirmed safe by PFAF
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_toxicity', 'confirmed_safe', 'true', datetime('now'))",
                    [pid]
                ))
                stats['safe_confirmed'] += 1
            elif parsed.get('toxic'):
                # Toxic
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_toxicity', 'toxic', 'true', datetime('now'))",
                    [pid]
                ))
                stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                              [pid]))
                stats['toxic_found'] += 1

                if parsed['substances']:
                    subst_str = ', '.join(parsed['substances'])[:200]
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_toxicity', 'toxic_substances', ?, datetime('now'))",
                        [pid, subst_str]
                    ))
                    stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                                  [f'Contains: {subst_str}', pid]))
                    stats['substances'] += 1

                if parsed['parts']:
                    parts_str = ', '.join(parsed['parts'])[:200]
                    stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ? AND (toxic_parts IS NULL OR toxic_parts = '')",
                                  [parts_str, pid]))

                stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ? AND (toxicity_severity IS NULL OR toxicity_severity = '')",
                              [parsed['severity'], pid]))

            elif parsed.get('irritant_only'):
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_toxicity', 'irritant', ?, datetime('now'))",
                    [pid, parsed['raw_text'][:200]]
                ))
                stats['irritant'] += 1

            # Always store raw text
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf_toxicity', 'known_hazards_parsed', ?, datetime('now'))",
                [pid, json.dumps(parsed, default=str)[:500]]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(pfaf_plants)}] matched={stats['matched']} safe={stats['safe_confirmed']} toxic={stats['toxic_found']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Done:", flush=True)
    for k, v in stats.items():
        print(f"    {k}: {v}", flush=True)


def step2_family_inference(dry_run=False):
    """Family-based toxicity inference for HIGH confidence families."""
    print(f"\n=== STEP 2: Family toxicity inference ===", flush=True)

    stmts = []
    stats = {'toxic_tagged': 0, 'already_toxic': 0, 'safe_tagged': 0}

    for family, info in TOXIC_FAMILIES.items():
        plants = turso_query("SELECT plant_id FROM plants WHERE family = ? AND plant_id IN (SELECT plant_id FROM care WHERE toxic_to_humans = 0 OR toxic_to_humans IS NULL)", [family])

        for p in plants:
            pid = p['plant_id']
            stats['toxic_tagged'] += 1

            if not dry_run:
                stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ?", [pid]))
                stmts.append(("UPDATE care SET toxic_to_pets = 1 WHERE plant_id = ? AND (toxic_to_pets = 0 OR toxic_to_pets IS NULL)", [pid]))
                stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ? AND (toxic_parts IS NULL OR toxic_parts = '')",
                              [info['parts'], pid]))
                stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ? AND (toxicity_severity IS NULL OR toxicity_severity = '')",
                              [info['severity'], pid]))
                stmts.append(("UPDATE care SET toxicity_symptoms = ? WHERE plant_id = ? AND (toxicity_symptoms IS NULL OR toxicity_symptoms = '')",
                              [info['symptoms'], pid]))
                stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                              [f"Contains {info['substance']}. Family {family} is known toxic.", pid]))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'family_toxicity_inference', 'toxic', ?, datetime('now'))",
                    [pid, f'{family}:{info["confidence"]}:{info["substance"]}']
                ))

                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

        # Count already toxic
        already = turso_query("SELECT COUNT(*) as c FROM plants WHERE family = ? AND plant_id IN (SELECT plant_id FROM care WHERE toxic_to_humans = 1)", [family])
        stats['already_toxic'] += already[0]['c']

        print(f"  {family}: {len(plants)} new, {already[0]['c']} already toxic", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Total tagged: {stats['toxic_tagged']}, already toxic: {stats['already_toxic']}", flush=True)


def step3_calpoison(dry_run=False):
    """Scrape CalPoison/Calflora toxic plant list."""
    print(f"\n=== STEP 3: CalPoison list ===", flush=True)

    url = 'https://www.calflora.org/app/ipl?list_id=px3140&family=t&fmt=simple'
    req = urllib.request.Request(url, headers={'User-Agent': UA})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode()
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        return

    # Parse HTML — look for scientific names in <i> tags
    names = re.findall(r'<i[^>]*>([^<]+)</i>', html)
    # Also try table rows
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)

    print(f"  CalPoison: {len(names)} italic names, {len(rows)} table rows", flush=True)

    if not names:
        print(f"  No plants found in CalPoison HTML", flush=True)
        return

    # Match with our DB
    our = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our:
        sci = p['scientific'].lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    stmts = []
    matched = 0
    for name in names:
        clean = name.strip().lower()
        pid = our_by_name.get(clean)
        if not pid:
            parts = clean.split()
            if len(parts) >= 2:
                pid = our_by_name.get(' '.join(parts[:2]))

        if pid:
            matched += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'calpoison', 'listed_toxic', 'true', datetime('now'))",
                    [pid]
                ))
                stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                              [pid]))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched: {matched}", flush=True)


def show_results():
    """Show toxicity stats."""
    print(f"\n=== TOXICITY STATUS ===", flush=True)

    sources = turso_query("""
        SELECT source, COUNT(DISTINCT plant_id) as c FROM source_data
        WHERE source IN ('aspca','tppt','efsa','wikipedia_toxic','pfaf','pfaf_toxicity','cbif','calpoison','family_toxicity_inference')
        AND (field LIKE '%toxic%' OR field LIKE '%hazard%' OR field LIKE '%poison%'
             OR field = 'listed_as_poisonous' OR field = 'confirmed_safe' OR field = 'listed_toxic'
             OR field = 'toxic' OR field = 'irritant' OR field = 'known_hazards_parsed')
        GROUP BY source ORDER BY c DESC
    """)
    print(f"\nSources:", flush=True)
    for s in sources:
        print(f"  {s['source']:30s} {s['c']:>5}", flush=True)

    tox = turso_query("SELECT toxic_to_humans, COUNT(*) as c FROM care GROUP BY toxic_to_humans")
    print(f"\ntoxic_to_humans:", flush=True)
    for t in tox:
        print(f"  {str(t['toxic_to_humans']):10s} {t['c']:>6}", flush=True)

    for f in ['toxic_parts', 'toxicity_severity', 'toxicity_symptoms', 'toxicity_note']:
        r = turso_query(f"SELECT COUNT(*) as c FROM care WHERE {f} IS NOT NULL AND {f} != ''")
        print(f"  {f}: {r[0]['c']}", flush=True)

    # Confirmed safe
    safe = turso_query("SELECT COUNT(DISTINCT plant_id) as c FROM source_data WHERE field = 'confirmed_safe'")
    print(f"\nConfirmed safe: {safe[0]['c']}", flush=True)

    # Unverified
    unv = turso_query("SELECT COUNT(*) as c FROM source_data WHERE source = 'flag' AND field = 'toxicity_unverified'")
    print(f"Still unverified: {unv[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step_only = None
    if '--step' in sys.argv:
        idx = sys.argv.index('--step')
        if idx + 1 < len(sys.argv):
            step_only = int(sys.argv[idx + 1])

    if step_only is None or step_only == 1:
        step1_pfaf_full(dry_run)
    if step_only is None or step_only == 2:
        step2_family_inference(dry_run)
    if step_only is None or step_only == 3:
        step3_calpoison(dry_run)

    show_results()
