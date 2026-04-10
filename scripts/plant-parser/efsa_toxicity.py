"""
EFSA + Wikipedia toxicity enrichment.

Step 1: EFSA Compendium — 599 plants matched, toxic substances → source_data + care
Step 2: Wikipedia List of Poisonous Plants — ~150 plants → source_data + care

Does NOT delete any data. Only adds/updates where empty.
Source: 'efsa' and 'wikipedia_toxic'

Usage:
    python3 efsa_toxicity.py              # full run
    python3 efsa_toxicity.py --dry-run
"""
import sys
import os
import json
import re
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

from turso_sync import turso_query, turso_batch

UA = 'PlantApp/1.0 (plantapp.pro)'


def step1_efsa(dry_run=False):
    """EFSA Compendium → source_data + care."""
    print(f"\n=== STEP 1: EFSA Compendium ===", flush=True)

    try:
        import xlrd
    except ImportError:
        print("  ERROR: xlrd not installed", flush=True)
        return

    # Load EFSA substances
    wb = xlrd.open_workbook(os.path.join(os.path.dirname(__file__), 'data', 'efsa_botanic.xls'))
    sh = wb.sheet_by_index(0)

    efsa_data = {}  # genus_species → {substances: [], parts: set()}
    for r in range(1, sh.nrows):
        plant_name = sh.cell_value(r, 7).strip().lower()
        substance = sh.cell_value(r, 13).strip()
        plant_part = sh.cell_value(r, 10).strip()
        if plant_name and substance:
            parts = plant_name.split()
            if len(parts) >= 2:
                key = ' '.join(parts[:2])
                if key not in efsa_data:
                    efsa_data[key] = {'substances': set(), 'parts': set()}
                efsa_data[key]['substances'].add(substance)
                if plant_part and plant_part != 'Live plants':
                    efsa_data[key]['parts'].add(plant_part)

    print(f"  EFSA: {len(efsa_data)} plants with substances", flush=True)

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
    stats = {'matched': 0, 'toxic_set': 0, 'parts_set': 0}

    for name, data in efsa_data.items():
        pid = our_by_name.get(name)
        if not pid:
            continue

        stats['matched'] += 1
        substances_str = ', '.join(sorted(data['substances']))[:300]
        parts_str = ', '.join(sorted(data['parts']))[:200] if data['parts'] else ''

        if not dry_run:
            # Raw to source_data
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'efsa', 'toxic_substances', ?, datetime('now'))",
                [pid, substances_str]
            ))
            if parts_str:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'efsa', 'toxic_parts', ?, datetime('now'))",
                    [pid, parts_str]
                ))

            # Update care: toxic_to_humans = 1 (EFSA = human safety authority)
            stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                          [pid]))
            stats['toxic_set'] += 1

            # Enrich toxic_parts if empty
            if parts_str:
                stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ? AND (toxic_parts IS NULL OR toxic_parts = '')",
                              [parts_str, pid]))
                stats['parts_set'] += 1

            # Enrich toxicity_note with substance info
            stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                          [f'Contains: {substances_str[:200]}', pid]))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched: {stats['matched']}, toxic set: {stats['toxic_set']}, parts enriched: {stats['parts_set']}", flush=True)


def step2_wikipedia(dry_run=False):
    """Wikipedia List of Poisonous Plants → source_data + care."""
    print(f"\n=== STEP 2: Wikipedia Poisonous Plants ===", flush=True)

    url = 'https://en.wikipedia.org/api/rest_v1/page/html/List_of_poisonous_plants'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode()
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        return

    class PlantParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_td = False
            self.current_text = ''
            self.current_row = []
            self.rows = []
            self.td_count = 0

        def handle_starttag(self, tag, attrs):
            if tag == 'td':
                self.in_td = True
                self.current_text = ''
            elif tag == 'tr':
                self.current_row = []
                self.td_count = 0

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

    parser = PlantParser()
    parser.feed(html)

    # Parse rows: [scientific_name, common_name, family, description/toxic_info]
    wiki_toxic = {}
    for row in parser.rows:
        sci = row[0].strip()
        if not sci or sci.startswith('This') or sci.startswith('Name'):
            continue
        # Clean: remove [1] references
        sci = re.sub(r'\[\d+\]', '', sci).strip()
        description = row[3] if len(row) > 3 else row[2] if len(row) > 2 else ''
        description = re.sub(r'\[\d+\]', '', description).strip()

        if sci:
            wiki_toxic[sci.lower()] = {
                'raw_name': sci,
                'common': row[1].strip() if len(row) > 1 else '',
                'family': row[2].strip() if len(row) > 2 else '',
                'description': description[:300],
            }

    print(f"  Wikipedia toxic plants: {len(wiki_toxic)}", flush=True)

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
    stats = {'matched': 0, 'toxic_set': 0}

    for sci, info in wiki_toxic.items():
        # Try exact match, then genus+species
        pid = our_by_name.get(sci)
        if not pid:
            parts = sci.split()
            if len(parts) >= 2:
                pid = our_by_name.get(' '.join(parts[:2]))
        # Try without "spp." suffix
        if not pid and 'spp' in sci:
            genus = sci.split()[0]
            for our_sci, our_pid in our_by_name.items():
                if our_sci.startswith(genus):
                    pid = our_pid
                    break

        if not pid:
            continue

        stats['matched'] += 1

        if not dry_run:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'listed_as_poisonous', 'true', datetime('now'))",
                [pid]
            ))
            if info['description']:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'toxicity_description', ?, datetime('now'))",
                    [pid, info['description']]
                ))

            # Update care
            stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                          [pid]))
            stats['toxic_set'] += 1

            # Enrich toxicity_note if empty
            if info['description']:
                stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ? AND (toxicity_note IS NULL OR toxicity_note = '')",
                              [info['description'][:200], pid]))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched: {stats['matched']}, toxic set: {stats['toxic_set']}", flush=True)


def show_results():
    """Show toxicity stats."""
    print(f"\n=== RESULTS ===", flush=True)
    sources = turso_query("""
        SELECT source, COUNT(DISTINCT plant_id) as c FROM source_data
        WHERE source IN ('efsa', 'wikipedia_toxic', 'tppt', 'pfaf', 'cbif')
        AND (field LIKE '%toxic%' OR field LIKE '%hazard%' OR field = 'listed_as_poisonous')
        GROUP BY source ORDER BY c DESC
    """)
    for s in sources:
        print(f"  {s['source']:25s} {s['c']:>5} plants", flush=True)

    tox = turso_query("SELECT toxic_to_humans, COUNT(*) as c FROM care GROUP BY toxic_to_humans")
    print(f"\ntoxic_to_humans:", flush=True)
    for t in tox:
        print(f"  {str(t['toxic_to_humans']):10s} {t['c']:>6}", flush=True)

    det = turso_query("SELECT COUNT(*) as c FROM care WHERE toxicity_note IS NOT NULL AND toxicity_note != ''")
    print(f"\ntoxicity_note filled: {det[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step1_efsa(dry_run)
    step2_wikipedia(dry_run)
    show_results()
