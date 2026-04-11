"""
verify_encyclopedia.py — Cross-validate encyclopedia texts + extract light/humidity.

Step 1: Identity verification (scientific name in text)
Step 2: Family/genus check (text vs plants table vs WCVP)
Step 3: Extract light keywords → compare with care.light_preferred
Step 4: Extract humidity keywords → compare with care.humidity_level
Step 5: Extract origin from text → fill gaps / flag contradictions
Step 6: Report

Does NOT delete data. All results → source_data with source='encyclopedia_verify'.
Featured 40 — verify only, never modify care.

Usage:
    python3 verify_encyclopedia.py --dry-run
    python3 verify_encyclopedia.py
"""
import sys
import os
import re
import csv
import json
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

WCVP_PATH = Path('/private/tmp/wcvp_names.csv')
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

# ── Light keywords (from polish_light_v4.py, expanded) ────────────
SHADE_KW = [
    'dense forest', 'deep shade', 'understory', 'under trees', 'forest floor',
    'shaded', 'heavily shaded', 'dense woodland', 'dark forest',
    'grows in shade', 'shade-loving', 'shade tolerant', 'sciophyte',
]
BRIGHT_INDIRECT_KW = [
    'forest', 'woodland', 'rainforest', 'tropical forest', 'cloud forest',
    'moist forest', 'humid forest', 'montane forest', 'jungle',
    'damp places', 'stream bank', 'riverside', 'ravine',
    'partial shade', 'semi-shade', 'light shade', 'filtered light',
    'epiphyte', 'epiphytic', 'grows on trees',
]
PART_SUN_KW = [
    'forest edge', 'forest margin', 'woodland edge', 'clearing',
    'hedgerow', 'thicket', 'scrub', 'rocky slope', 'mountain meadow',
    'open woodland', 'light woodland', 'meadow', 'field margin',
]
FULL_SUN_KW = [
    'open grassland', 'steppe', 'prairie', 'desert', 'dry scrub',
    'full sun', 'exposed', 'open places', 'dry slopes', 'sandy coast',
    'dune', 'arid', 'semi-arid', 'savanna', 'dry hillside',
    'open habitat', 'open field', 'sun-loving',
]

# ── Humidity keywords ─────────────────────────────────────────────
HIGH_HUMID_KW = [
    'tropical', 'rainforest', 'humid', 'moisture-loving', 'wet habitat',
    'aquatic', 'bog', 'marsh', 'swamp', 'riparian', 'streamside',
    'cloud forest', 'montane forest', 'wet forest', 'mangrove',
    'high humidity', 'moist environment',
]
LOW_HUMID_KW = [
    'desert', 'arid', 'drought-tolerant', 'xeric', 'dry habitat',
    'xerophyte', 'semi-arid', 'dry climate', 'low humidity',
    'succulent', 'drought resistant', 'dry conditions',
]

# ── Family patterns in text ───────────────────────────────────────
FAMILY_PATTERNS = [
    r'(?:family|familia)\s+(\w+aceae)',
    r'in\s+the\s+(?:\w+\s+)?family\s+(\w+aceae)',
    r'belongs?\s+to\s+(?:the\s+)?(?:\w+\s+)?family\s+(\w+aceae)',
    r'of\s+the\s+(?:\w+\s+)?family\s+(\w+aceae)',
    r'(\w+aceae)\s+family',
]

# ── Origin patterns ───────────────────────────────────────────────
ORIGIN_PATTERNS = [
    r'native\s+to\s+([^\.]{5,80})',
    r'originat(?:es|ing)\s+(?:from|in)\s+([^\.]{5,80})',
    r'endemic\s+to\s+([^\.]{5,60})',
    r'indigenous\s+to\s+([^\.]{5,60})',
    r'found\s+(?:naturally\s+)?in\s+([^\.]{5,80})',
    r'distributed\s+(?:across|in|throughout)\s+([^\.]{5,80})',
]


def retry_query(sql, params=None, retries=3):
    for attempt in range(retries):
        try:
            return turso_query(sql, params)
        except Exception as e:
            if attempt < retries - 1 and 'timeout' in str(e).lower():
                time.sleep(10)
            else:
                raise


def count_keywords(text, keywords):
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def extract_light(text):
    """Extract light level from text. Returns (index 0-3, confidence) or (None, 0)."""
    scores = [
        count_keywords(text, SHADE_KW),
        count_keywords(text, BRIGHT_INDIRECT_KW),
        count_keywords(text, PART_SUN_KW),
        count_keywords(text, FULL_SUN_KW),
    ]
    total = sum(scores)
    if total == 0:
        return None, 0
    weighted = sum(i * s for i, s in enumerate(scores)) / total
    confidence = max(scores) / total
    return round(weighted), confidence


def extract_humidity(text):
    """Extract humidity level from text. Returns ('high'/'low'/'average', confidence) or (None, 0)."""
    high = count_keywords(text, HIGH_HUMID_KW)
    low = count_keywords(text, LOW_HUMID_KW)
    total = high + low
    if total == 0:
        return None, 0
    if high > low:
        return 'high', high / total
    elif low > high:
        return 'low', low / total
    return 'average', 0.5


def extract_family(text):
    """Extract family name from text."""
    for pattern in FAMILY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
    return None


def extract_origin(text):
    """Extract geographic origin from text."""
    for pattern in ORIGIN_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            origin = m.group(1).strip().rstrip(',;:')
            if len(origin) > 5 and not origin.lower().startswith('the '):
                return origin
    return None


def run(dry_run=False):
    print("=== STEP 1: Load Encyclopedia Texts ===", flush=True)

    # Get all Wikipedia texts
    wiki_rows = retry_query("SELECT plant_id, value FROM source_data WHERE source = 'wikipedia_full' AND field = 'extract_en'")
    wiki_texts = {r['plant_id']: r['value'] for r in wiki_rows}
    print(f"  Wikipedia texts: {len(wiki_texts)}", flush=True)

    # Get GBIF texts (first description per plant)
    gbif_rows = retry_query("SELECT plant_id, value FROM source_data WHERE source = 'gbif_full' AND field LIKE 'description_0%'")
    gbif_texts = {}
    for r in gbif_rows:
        if r['plant_id'] not in gbif_texts:
            gbif_texts[r['plant_id']] = r['value']
    print(f"  GBIF texts: {len(gbif_texts)}", flush=True)

    # Merge — prefer Wikipedia, supplement with GBIF
    all_pids = set(wiki_texts.keys()) | set(gbif_texts.keys())
    print(f"  Plants with any text: {len(all_pids)}", flush=True)

    # Load plant data
    plants = retry_query("SELECT plant_id, scientific, family, genus, origin FROM plants")
    plant_data = {p['plant_id']: p for p in plants}

    # Load care data
    care = retry_query("SELECT plant_id, light_preferred, humidity_level FROM care")
    care_data = {c['plant_id']: c for c in care}

    # Load unverified fullsun set
    unverified = retry_query("SELECT DISTINCT plant_id FROM source_data WHERE field = 'unverified_fullsun'")
    unverified_set = set(r['plant_id'] for r in unverified)

    # Stats
    stats = {
        'identity_exact': 0, 'identity_genus': 0, 'identity_fail': 0,
        'family_match': 0, 'family_contradiction': 0, 'family_extracted': 0,
        'light_extracted': 0, 'light_contradiction': 0, 'light_fixable': 0,
        'humidity_extracted': 0, 'humidity_contradiction': 0, 'humidity_fixable': 0,
        'origin_extracted': 0, 'origin_new': 0, 'origin_contradiction': 0,
    }

    stmts = []
    contradictions = []

    print("\n=== STEP 2-5: Analyze Texts ===", flush=True)

    for i, pid in enumerate(all_pids):
        wiki = wiki_texts.get(pid, '')
        gbif = gbif_texts.get(pid, '')
        combined = f"{wiki} {gbif}"
        plant = plant_data.get(pid)
        if not plant:
            continue

        scientific = plant['scientific'] or ''
        family = plant['family'] or ''
        genus = plant['genus'] or ''
        origin = plant['origin'] or ''
        care_row = care_data.get(pid, {})
        current_light = care_row.get('light_preferred', '')
        current_humidity = care_row.get('humidity_level', '')

        # ── Identity Check ──
        sci_lower = scientific.lower()
        text_lower = combined.lower()
        if sci_lower and sci_lower in text_lower:
            stats['identity_exact'] += 1
            id_result = 'exact'
        elif genus.lower() in text_lower:
            stats['identity_genus'] += 1
            id_result = 'genus'
        else:
            stats['identity_fail'] += 1
            id_result = 'not_found'

        # ── Family Check ──
        text_family = extract_family(combined)
        if text_family:
            stats['family_extracted'] += 1
            if family and text_family.lower() == family.lower():
                stats['family_match'] += 1
            elif family and text_family.lower() != family.lower():
                stats['family_contradiction'] += 1
                contradictions.append((pid, 'family', f'DB={family}, text={text_family}'))

        # ── Light ──
        light_idx, light_conf = extract_light(combined)
        if light_idx is not None and light_conf >= 0.4:
            stats['light_extracted'] += 1
            text_light = LIGHT_LEVELS[light_idx]
            current_idx = LIGHT_LEVELS.index(current_light) if current_light in LIGHT_LEVELS else -1

            if current_idx >= 0 and abs(light_idx - current_idx) >= 2:
                stats['light_contradiction'] += 1
                contradictions.append((pid, 'light', f'DB={current_light}, text={text_light} (conf={light_conf:.2f})'))

            if pid in unverified_set and light_idx < 3:
                stats['light_fixable'] += 1

            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'encyclopedia_verify', 'light_estimate', ?, datetime('now'))",
                    [pid, f'{text_light} (conf={light_conf:.2f})']
                ))

        # ── Humidity ──
        hum_level, hum_conf = extract_humidity(combined)
        if hum_level and hum_conf >= 0.5:
            stats['humidity_extracted'] += 1

            is_contradiction = False
            if hum_level == 'high' and current_humidity and 'low' in current_humidity.lower():
                is_contradiction = True
            elif hum_level == 'low' and current_humidity and 'high' in current_humidity.lower():
                is_contradiction = True

            if is_contradiction:
                stats['humidity_contradiction'] += 1
                contradictions.append((pid, 'humidity', f'DB={current_humidity}, text={hum_level} (conf={hum_conf:.2f})'))

            if current_humidity == 'Average (40-60%)' and hum_level != 'average':
                stats['humidity_fixable'] += 1

            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'encyclopedia_verify', 'humidity_estimate', ?, datetime('now'))",
                    [pid, f'{hum_level} (conf={hum_conf:.2f})']
                ))

        # ── Origin ──
        text_origin = extract_origin(wiki) or extract_origin(gbif)
        if text_origin:
            stats['origin_extracted'] += 1
            if not origin:
                stats['origin_new'] += 1
            elif origin and not any(w in origin.lower() for w in text_origin.lower().split()[:3]):
                stats['origin_contradiction'] += 1
                contradictions.append((pid, 'origin', f'DB={origin[:40]}, text={text_origin[:40]}'))

            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'encyclopedia_verify', 'origin_text', ?, datetime('now'))",
                    [pid, text_origin]
                ))

        # ── Identity result ──
        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'encyclopedia_verify', 'identity_check', ?, datetime('now'))",
                [pid, id_result]
            ))

        # Batch write
        if len(stmts) >= 200 and not dry_run:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 2000 == 0:
            print(f"  [{i+1}/{len(all_pids)}] processed...", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    # ── Report ──
    print("\n=== STEP 6: Report ===", flush=True)
    print(f"\n  Identity verification:", flush=True)
    print(f"    Exact match:  {stats['identity_exact']}", flush=True)
    print(f"    Genus match:  {stats['identity_genus']}", flush=True)
    print(f"    NOT found:    {stats['identity_fail']}", flush=True)

    print(f"\n  Family check:", flush=True)
    print(f"    Extracted:    {stats['family_extracted']}", flush=True)
    print(f"    Match:        {stats['family_match']}", flush=True)
    print(f"    Contradiction:{stats['family_contradiction']}", flush=True)

    print(f"\n  Light:", flush=True)
    print(f"    Extracted:    {stats['light_extracted']}", flush=True)
    print(f"    Contradictions:{stats['light_contradiction']}", flush=True)
    print(f"    Fixable (unverified fullsun): {stats['light_fixable']}", flush=True)

    print(f"\n  Humidity:", flush=True)
    print(f"    Extracted:    {stats['humidity_extracted']}", flush=True)
    print(f"    Contradictions:{stats['humidity_contradiction']}", flush=True)
    print(f"    Fixable (Average→other): {stats['humidity_fixable']}", flush=True)

    print(f"\n  Origin:", flush=True)
    print(f"    Extracted:    {stats['origin_extracted']}", flush=True)
    print(f"    New (fill gap):{stats['origin_new']}", flush=True)
    print(f"    Contradictions:{stats['origin_contradiction']}", flush=True)

    print(f"\n  Total contradictions: {len(contradictions)}", flush=True)
    if contradictions:
        print(f"\n  Sample contradictions:", flush=True)
        for pid, ctype, detail in contradictions[:20]:
            print(f"    {pid:35s} [{ctype:8s}] {detail}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run)
