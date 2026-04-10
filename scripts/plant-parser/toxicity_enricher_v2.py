"""
Toxicity enricher v2 — ASPCA recovery + TPPT full + Wikipedia multi + reconcile.

SAFETY CRITICAL: plant toxicity affects humans and animals.
Every result → source_data with source attribution.
NEVER mark safe without ASPCA/TPPT confirmation.

Steps:
1. ASPCA audit trail recovery (from care table → source_data)
2. TPPT full extraction (toxin names, parts, LD50)
3. Wikipedia HTML multi-page parsing
4. Reconcile enrichment (fill empty detail fields)

Usage:
    python3 toxicity_enricher_v2.py              # full run
    python3 toxicity_enricher_v2.py --dry-run
    python3 toxicity_enricher_v2.py --step 1     # specific step
"""
import sys
import os
import re
import json
import sqlite3
import time
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_query, turso_batch, store_source_data

UA = 'PlantApp/1.0 (plantapp.pro)'
TPPT_DB = os.path.join(os.path.dirname(__file__), 'data', 'TPPT_Database.db')

WIKI_TOXIC_PAGES = [
    'List_of_poisonous_plants',
    'List_of_plants_poisonous_to_livestock',
]


# =========================================================
# STEP 1: ASPCA audit trail recovery
# =========================================================
def step1_aspca_recovery(dry_run=False):
    """Recover ASPCA data from care table → source_data."""
    print(f"\n=== STEP 1: ASPCA audit trail recovery ===", flush=True)

    # Find plants with ASPCA-like toxicity notes
    aspca_plants = turso_query("""
        SELECT plant_id, toxic_to_pets, toxic_to_humans, toxicity_note,
               toxicity_symptoms, toxicity_severity, toxic_parts
        FROM care
        WHERE toxicity_note LIKE '%Clinical Signs%'
           OR toxicity_note LIKE '%ASPCA%'
           OR toxicity_note LIKE '%toxic to dogs%'
           OR toxicity_note LIKE '%toxic to cats%'
    """)
    print(f"  ASPCA-like plants in care: {len(aspca_plants)}", flush=True)

    stmts = []
    for p in aspca_plants:
        pid = p['plant_id']
        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'aspca', 'toxic_to_pets', ?, datetime('now'))",
                [pid, str(p.get('toxic_to_pets', ''))]
            ))
            if p.get('toxicity_note'):
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'aspca', 'toxicity_note', ?, datetime('now'))",
                    [pid, p['toxicity_note'][:300]]
                ))
            if p.get('toxicity_symptoms'):
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'aspca', 'symptoms', ?, datetime('now'))",
                    [pid, p['toxicity_symptoms'][:300]]
                ))
            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    # Also find PFAF confirmed safe (none known hazards)
    pfaf_safe = turso_query("""
        SELECT DISTINCT plant_id FROM source_data
        WHERE source = 'pfaf' AND field = 'known_hazards'
        AND LOWER(value) LIKE '%none known%'
    """)
    print(f"  PFAF confirmed safe: {len(pfaf_safe)}", flush=True)

    for p in pfaf_safe:
        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'pfaf', 'confirmed_safe', 'true', datetime('now'))",
                [p['plant_id']]
            ))
            if len(stmts) >= 200:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Done: {len(aspca_plants)} ASPCA + {len(pfaf_safe)} PFAF safe recovered", flush=True)


# =========================================================
# STEP 2: TPPT full extraction
# =========================================================
def step2_tppt_full(dry_run=False):
    """Extract full toxicity details from TPPT SQLite."""
    print(f"\n=== STEP 2: TPPT full extraction ===", flush=True)

    if not os.path.exists(TPPT_DB):
        print(f"  ERROR: TPPT DB not found at {TPPT_DB}", flush=True)
        return

    conn = sqlite3.connect(TPPT_DB)
    conn.row_factory = sqlite3.Row

    # Get all toxic plants with their toxins
    plants = conn.execute("""
        SELECT t.Plant_number, t.Latin_plant_name, t.Plant_genus, t.Plant_family,
               t.Toxic_plant_part, t.Human_toxicity, t.Animal_toxicity
        FROM Toxic_plant_species t
    """).fetchall()
    print(f"  TPPT plants: {len(plants)}", flush=True)

    # Get toxin relationships
    toxin_rels = conn.execute("""
        SELECT r.Plant_number, p.Trivial_name, p.PSM_class, r.Composition_type
        FROM Phytotoxin_toxic_plant_species_relationships r
        JOIN Phytotoxins p ON r.Phytotoxin_number = p.Phytotoxin_number
    """).fetchall()

    # Group toxins by plant
    plant_toxins = {}
    for rel in toxin_rels:
        pn = rel['Plant_number']
        if pn not in plant_toxins:
            plant_toxins[pn] = []
        plant_toxins[pn].append({
            'name': rel['Trivial_name'],
            'class': rel['PSM_class'],
            'type': rel['Composition_type']
        })

    # Get LD50 data
    ld50_data = conn.execute("""
        SELECT td.Phytotoxin_number, td.Test_animal, td.Exposure_route, td.LD50_dose, td.Dose_unit
        FROM Toxicity_data td
    """).fetchall()

    conn.close()

    print(f"  Toxin relationships: {len(toxin_rels)}", flush=True)
    print(f"  LD50 records: {len(ld50_data)}", flush=True)

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
    stats = {'matched': 0, 'toxins_added': 0, 'parts_added': 0}

    for plant in plants:
        latin = (plant['Latin_plant_name'] or '').strip().lower()
        genus = (plant['Plant_genus'] or '').strip().lower()

        pid = our_by_name.get(latin)
        if not pid and genus:
            # Try genus + first species word
            for key, val in our_by_name.items():
                if key.startswith(genus):
                    pid = val
                    break

        if not pid:
            continue

        stats['matched'] += 1
        pn = plant['Plant_number']

        # Human toxicity
        human_tox = plant['Human_toxicity'] or ''
        animal_tox = plant['Animal_toxicity'] or ''
        toxic_part = plant['Toxic_plant_part'] or ''

        if not dry_run:
            # Store raw TPPT data
            if human_tox:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'tppt', 'human_toxicity', ?, datetime('now'))",
                    [pid, human_tox]
                ))
            if animal_tox:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'tppt', 'animal_toxicity', ?, datetime('now'))",
                    [pid, animal_tox]
                ))

            # Toxin names
            toxins = plant_toxins.get(pn, [])
            if toxins:
                toxin_names = ', '.join(sorted(set(t['name'] for t in toxins if t['name'])))[:300]
                toxin_classes = ', '.join(sorted(set(t['class'] for t in toxins if t['class'])))[:200]
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'tppt', 'toxin_names', ?, datetime('now'))",
                    [pid, toxin_names]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'tppt', 'toxin_classes', ?, datetime('now'))",
                    [pid, toxin_classes]
                ))
                stats['toxins_added'] += 1

                # Enrich care.toxicity_note with specific toxin names
                stmts.append((
                    "UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                    [f'Contains: {toxin_names[:200]}. Class: {toxin_classes[:100]}', pid]
                ))

            # Enrich toxic_parts
            if toxic_part:
                stmts.append((
                    "UPDATE care SET toxic_parts = ? WHERE plant_id = ? AND (toxic_parts IS NULL OR toxic_parts = '')",
                    [toxic_part[:200], pid]
                ))
                stats['parts_added'] += 1

            # Set toxic flags based on TPPT severity
            is_toxic_human = human_tox and any(w in human_tox.lower() for w in ['toxic', 'strong', 'very', 'lethal'])
            is_toxic_animal = animal_tox and any(w in animal_tox.lower() for w in ['toxic', 'strong', 'very', 'lethal'])

            if is_toxic_human:
                stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                              [pid]))
            if is_toxic_animal:
                stmts.append(("UPDATE care SET toxic_to_pets = 1 WHERE plant_id = ? AND (toxic_to_pets = 0 OR toxic_to_pets IS NULL)",
                              [pid]))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched: {stats['matched']}, toxins: {stats['toxins_added']}, parts: {stats['parts_added']}", flush=True)


# =========================================================
# STEP 3: Wikipedia multi-page HTML parsing
# =========================================================
class WikiTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.current_text = ''
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            self.in_td = True
            self.current_text = ''
        elif tag == 'tr':
            self.current_row = []

    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_td = False
            self.current_row.append(self.current_text.strip())
        elif tag == 'tr':
            if len(self.current_row) >= 3:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_td:
            self.current_text += data


def step3_wikipedia_multi(dry_run=False):
    """Parse multiple Wikipedia toxic plant lists."""
    print(f"\n=== STEP 3: Wikipedia multi-page ===", flush=True)

    # Build our name lookup once
    our = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our:
        sci = p['scientific'].lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    all_toxic = {}  # scientific → {parts, symptoms, source_page}
    stmts = []
    total_matched = 0

    for page in WIKI_TOXIC_PAGES:
        url = f'https://en.wikipedia.org/api/rest_v1/page/html/{page}'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode()
        except Exception as e:
            print(f"  ERROR fetching {page}: {e}", flush=True)
            continue

        parser = WikiTableParser()
        parser.feed(html)
        print(f"  {page}: {len(parser.rows)} rows", flush=True)

        for row in parser.rows:
            sci = re.sub(r'\[\d+\]', '', row[0]).strip()
            if not sci or len(sci) < 3 or sci.startswith('This') or sci.startswith('Name') or sci.startswith('Scientific'):
                continue

            description = ''
            if len(row) > 3:
                description = re.sub(r'\[\d+\]', '', row[3]).strip()
            elif len(row) > 2:
                description = re.sub(r'\[\d+\]', '', row[2]).strip()

            sci_lower = sci.lower()
            pid = our_by_name.get(sci_lower)
            if not pid:
                parts = sci_lower.split()
                if len(parts) >= 2:
                    pid = our_by_name.get(' '.join(parts[:2]))
            # Try genus match for "spp."
            if not pid and 'spp' in sci_lower:
                genus = sci_lower.split()[0]
                for key, val in our_by_name.items():
                    if key.startswith(genus):
                        pid = val
                        break

            if pid and pid not in all_toxic:
                all_toxic[pid] = {
                    'sci': sci,
                    'description': description[:300],
                    'page': page,
                }
                total_matched += 1

                if not dry_run:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'listed_as_poisonous', 'true', datetime('now'))",
                        [pid]
                    ))
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'wiki_page', ?, datetime('now'))",
                        [pid, page]
                    ))
                    if description:
                        stmts.append((
                            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'toxicity_description', ?, datetime('now'))",
                            [pid, description]
                        ))
                    # Update care
                    stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                                  [pid]))
                    if description:
                        stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                                      [description[:200], pid]))

                    if len(stmts) >= 100:
                        turso_batch(stmts); stmts = []

        time.sleep(1)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Total matched across all pages: {total_matched}", flush=True)


# =========================================================
# STEP 4: Reconcile — fill empty detail fields from all sources
# =========================================================
def step4_reconcile(dry_run=False):
    """Fill empty toxicity detail fields from source_data."""
    print(f"\n=== STEP 4: Reconcile ===", flush=True)

    # Find toxic plants with missing details
    missing = turso_query("""
        SELECT plant_id FROM care
        WHERE toxic_to_humans = 1
        AND (toxic_parts IS NULL OR toxic_parts = ''
             OR toxicity_symptoms IS NULL OR toxicity_symptoms = ''
             OR toxicity_severity IS NULL OR toxicity_severity = '')
    """)
    print(f"  Toxic plants with missing details: {len(missing)}", flush=True)

    stmts = []
    stats = {'parts_filled': 0, 'symptoms_filled': 0, 'severity_filled': 0}

    for m in missing:
        pid = m['plant_id']
        care = turso_query("SELECT toxic_parts, toxicity_symptoms, toxicity_severity FROM care WHERE plant_id = ?", [pid])
        if not care:
            continue
        c = care[0]

        # Get all toxicity source data for this plant
        sd = turso_query("""
            SELECT source, field, value FROM source_data
            WHERE plant_id = ? AND (source IN ('tppt','efsa','wikipedia_toxic','pfaf','aspca'))
        """, [pid])

        sd_dict = {}
        for s in sd:
            key = f"{s['source']}_{s['field']}"
            sd_dict[key] = s['value']

        # Fill toxic_parts
        if not c.get('toxic_parts'):
            parts = sd_dict.get('tppt_toxic_parts') or sd_dict.get('efsa_toxic_parts') or sd_dict.get('wikipedia_toxic_toxicity_description', '')
            if parts and len(parts) > 10:
                if not dry_run:
                    stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ?", [parts[:200], pid]))
                stats['parts_filled'] += 1

        # Fill toxicity_severity from TPPT
        if not c.get('toxicity_severity'):
            human_tox = sd_dict.get('tppt_human_toxicity', '')
            if human_tox:
                if any(w in human_tox.lower() for w in ['very strong', 'lethal', 'fatal']):
                    severity = 'Severe'
                elif any(w in human_tox.lower() for w in ['strong', 'toxic']):
                    severity = 'Moderate'
                else:
                    severity = 'Mild'
                if not dry_run:
                    stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ?", [severity, pid]))
                stats['severity_filled'] += 1

        # Fill symptoms from ASPCA or TPPT
        if not c.get('toxicity_symptoms'):
            symptoms = sd_dict.get('aspca_symptoms') or sd_dict.get('wikipedia_toxic_toxicity_description', '')
            if symptoms and len(symptoms) > 10:
                if not dry_run:
                    stmts.append(("UPDATE care SET toxicity_symptoms = ? WHERE plant_id = ?", [symptoms[:300], pid]))
                stats['symptoms_filled'] += 1

        if len(stmts) >= 100:
            if not dry_run:
                turso_batch(stmts)
            stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Parts filled: {stats['parts_filled']}", flush=True)
    print(f"  Severity filled: {stats['severity_filled']}", flush=True)
    print(f"  Symptoms filled: {stats['symptoms_filled']}", flush=True)


def show_results():
    """Show final toxicity stats."""
    print(f"\n=== FINAL TOXICITY STATUS ===", flush=True)

    sources = turso_query("""
        SELECT source, COUNT(DISTINCT plant_id) as c FROM source_data
        WHERE source IN ('aspca','tppt','efsa','wikipedia_toxic','pfaf','cbif')
        AND (field LIKE '%toxic%' OR field LIKE '%hazard%' OR field LIKE '%poison%'
             OR field = 'listed_as_poisonous' OR field = 'confirmed_safe'
             OR field = 'human_toxicity' OR field = 'animal_toxicity' OR field = 'toxin_names')
        GROUP BY source ORDER BY c DESC
    """)
    print(f"\nSources:", flush=True)
    for s in sources:
        print(f"  {s['source']:20s} {s['c']:>5}", flush=True)

    tox = turso_query("SELECT toxic_to_humans, COUNT(*) as c FROM care GROUP BY toxic_to_humans")
    print(f"\ntoxic_to_humans:", flush=True)
    for t in tox:
        print(f"  {str(t['toxic_to_humans']):10s} {t['c']:>6}", flush=True)

    for f in ['toxic_parts', 'toxicity_severity', 'toxicity_symptoms', 'toxicity_note']:
        r = turso_query(f"SELECT COUNT(*) as c FROM care WHERE {f} IS NOT NULL AND {f} != ''")
        print(f"  {f}: {r[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step_only = None
    if '--step' in sys.argv:
        idx = sys.argv.index('--step')
        if idx + 1 < len(sys.argv):
            step_only = int(sys.argv[idx + 1])

    if step_only is None or step_only == 1:
        step1_aspca_recovery(dry_run)
    if step_only is None or step_only == 2:
        step2_tppt_full(dry_run)
    if step_only is None or step_only == 3:
        step3_wikipedia_multi(dry_run)
    if step_only is None or step_only == 4:
        step4_reconcile(dry_run)

    show_results()
