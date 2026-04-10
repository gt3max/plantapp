"""
Polish toxicity v2 — flag unverified + Wikipedia + Wikidata enrichment.

Step 1: Flag unverified toxic=0 (NOT delete!)
Step 2: Wikipedia List of Poisonous Plants → source_data
Step 3: Wikidata SPARQL → plants tagged as poisonous
Step 4: Match + update care where new toxic data found

Does NOT delete any data. Source attribution on everything.

Usage:
    python3 polish_toxicity_v2.py              # full run
    python3 polish_toxicity_v2.py --dry-run
    python3 polish_toxicity_v2.py --step 1     # only flag unverified
"""
import sys
import os
import json
import re
import time
import urllib.request
import urllib.parse

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


def step1_flag_unverified(dry_run=False):
    """Flag plants with toxic=0 but no confirmed source."""
    print(f"\n=== STEP 1: Flag unverified toxic=0 ===", flush=True)

    # Plants with confirmed toxicity source
    confirmed = turso_query("""
        SELECT DISTINCT plant_id FROM source_data
        WHERE source IN ('tppt', 'aspca', 'cbif')
        OR (source = 'pfaf' AND field = 'known_hazards')
    """)
    confirmed_set = set(r['plant_id'] for r in confirmed)
    print(f"  Confirmed by source: {len(confirmed_set)}", flush=True)

    # Plants with toxic=0 but NOT confirmed
    unverified = turso_query("""
        SELECT plant_id FROM care
        WHERE toxic_to_humans = 0 OR toxic_to_pets = 0
    """)

    stmts = []
    count = 0
    for r in unverified:
        if r['plant_id'] not in confirmed_set:
            count += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'flag', 'toxicity_unverified', 'toxic=0 without confirmed source', datetime('now'))",
                    [r['plant_id']]
                ))
                if len(stmts) >= 200:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Flagged unverified: {count}", flush=True)


def step2_wikipedia_toxic(dry_run=False):
    """Parse Wikipedia List of Poisonous Plants."""
    print(f"\n=== STEP 2: Wikipedia Poisonous Plants ===", flush=True)

    url = 'https://en.wikipedia.org/w/api.php?action=parse&page=List_of_poisonous_plants&prop=wikitext&format=json'
    req = urllib.request.Request(url, headers={'User-Agent': UA})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR fetching Wikipedia: {e}", flush=True)
        return {}

    wikitext = data.get('parse', {}).get('wikitext', {}).get('*', '')

    # Parse table rows: | [[Scientific name]] || Common name || Toxic parts || ...
    toxic_plants = {}
    # Look for lines with scientific names in [[...]]
    for line in wikitext.split('\n'):
        if '||' in line and '[[' in line:
            parts = [p.strip().strip('|').strip() for p in line.split('||')]
            if len(parts) >= 2:
                # Extract scientific name from [[...]]
                name_match = re.search(r'\[\[([^\]|]+)', parts[0])
                if name_match:
                    sci_name = name_match.group(1).strip()
                    toxic_parts_text = parts[2] if len(parts) > 2 else ''
                    symptoms = parts[3] if len(parts) > 3 else ''
                    toxic_plants[sci_name.lower()] = {
                        'raw_name': sci_name,
                        'toxic_parts': toxic_parts_text[:200],
                        'symptoms': symptoms[:200],
                    }

    print(f"  Wikipedia toxic plants found: {len(toxic_plants)}", flush=True)

    if not toxic_plants:
        return {}

    # Match with our DB
    our_plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our_plants:
        our_by_name[p['scientific'].lower()] = p['plant_id']

    stmts = []
    matched = 0
    for sci, info in toxic_plants.items():
        pid = our_by_name.get(sci)
        if not pid:
            # Try genus match
            genus = sci.split()[0] if ' ' in sci else sci
            for our_sci, our_pid in our_by_name.items():
                if our_sci.startswith(genus.lower()):
                    pid = our_pid
                    break

        if pid:
            matched += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'toxic', 'true', datetime('now'))",
                    [pid]
                ))
                if info['toxic_parts']:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'toxic_parts', ?, datetime('now'))",
                        [pid, info['toxic_parts']]
                    ))
                if info['symptoms']:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_toxic', 'symptoms', ?, datetime('now'))",
                        [pid, info['symptoms']]
                    ))

                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched with our DB: {matched}", flush=True)
    return toxic_plants


def step3_wikidata_toxic(dry_run=False):
    """Wikidata SPARQL: plants tagged as poisonous."""
    print(f"\n=== STEP 3: Wikidata SPARQL poisonous plants ===", flush=True)

    query = """
    SELECT ?item ?itemLabel ?scientificName WHERE {
      ?item wdt:P31 wd:Q184623 .
      OPTIONAL { ?item wdt:P225 ?scientificName . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    LIMIT 5000
    """

    url = 'https://query.wikidata.org/sparql'
    params = urllib.parse.urlencode({'query': query, 'format': 'json'})
    req = urllib.request.Request(f'{url}?{params}', headers={'User-Agent': UA, 'Accept': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR fetching Wikidata: {e}", flush=True)
        return

    results = data.get('results', {}).get('bindings', [])
    print(f"  Wikidata poisonous plants: {len(results)}", flush=True)

    # Build lookup
    wikidata_toxic = {}
    for r in results:
        sci = r.get('scientificName', {}).get('value', '').strip().lower()
        label = r.get('itemLabel', {}).get('value', '')
        if sci:
            wikidata_toxic[sci] = label

    # Match with our DB
    our_plants = turso_query("SELECT plant_id, scientific FROM plants WHERE scientific IS NOT NULL")
    our_by_name = {}
    for p in our_plants:
        sci = p['scientific'].lower()
        our_by_name[sci] = p['plant_id']
        parts = sci.split()
        if len(parts) >= 2:
            our_by_name[' '.join(parts[:2])] = p['plant_id']

    stmts = []
    matched = 0
    for sci, label in wikidata_toxic.items():
        pid = our_by_name.get(sci) or our_by_name.get(' '.join(sci.split()[:2]))
        if pid:
            matched += 1
            if not dry_run:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikidata_toxic', 'poisonous_plant', 'true', datetime('now'))",
                    [pid]
                ))
                if len(stmts) >= 100:
                    turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Matched with our DB: {matched}", flush=True)


def step4_update_care(dry_run=False):
    """Update care table where new toxic sources found but care says 0."""
    print(f"\n=== STEP 4: Update care from new sources ===", flush=True)

    # Find plants that new sources say toxic but care says 0 or NULL
    new_toxic = turso_query("""
        SELECT DISTINCT sd.plant_id FROM source_data sd
        JOIN care c ON sd.plant_id = c.plant_id
        WHERE sd.source IN ('wikipedia_toxic', 'wikidata_toxic')
        AND (c.toxic_to_humans = 0 OR c.toxic_to_humans IS NULL)
    """)

    print(f"  Plants with new toxic data + care=0/NULL: {len(new_toxic)}", flush=True)

    stmts = []
    for r in new_toxic:
        pid = r['plant_id']
        if not dry_run:
            # Set toxic_to_humans = 1 (new source says toxic)
            stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ? AND (toxic_to_humans = 0 OR toxic_to_humans IS NULL)",
                          [pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'toxicity_v2', 'updated_from', 'wikipedia_toxic/wikidata_toxic', datetime('now'))",
                [pid]
            ))

            # Enrich toxic_parts from Wikipedia if available
            wp = turso_query("SELECT value FROM source_data WHERE plant_id = ? AND source = 'wikipedia_toxic' AND field = 'toxic_parts'", [pid])
            if wp and wp[0]['value']:
                stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ? AND (toxic_parts IS NULL OR toxic_parts = '')",
                              [wp[0]['value'], pid]))

            # Enrich symptoms
            symp = turso_query("SELECT value FROM source_data WHERE plant_id = ? AND source = 'wikipedia_toxic' AND field = 'symptoms'", [pid])
            if symp and symp[0]['value']:
                stmts.append(("UPDATE care SET toxicity_symptoms = ? WHERE plant_id = ? AND (toxicity_symptoms IS NULL OR toxicity_symptoms = '')",
                              [symp[0]['value'], pid]))

            if len(stmts) >= 100:
                turso_batch(stmts); stmts = []

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"  Updated: {len(new_toxic)}", flush=True)


def show_results():
    """Show toxicity statistics."""
    print(f"\n=== RESULTS ===", flush=True)
    # Count by source
    sources = turso_query("""
        SELECT source, COUNT(DISTINCT plant_id) as c FROM source_data
        WHERE source IN ('tppt','aspca','pfaf','wikipedia_toxic','wikidata_toxic','cbif','flag')
        AND (field LIKE '%toxic%' OR field LIKE '%hazard%' OR field = 'poisonous_plant' OR field = 'toxicity_unverified')
        GROUP BY source ORDER BY c DESC
    """)
    for s in sources:
        print(f"  {s['source']:25s} {s['c']:>5} plants", flush=True)

    tox = turso_query("SELECT toxic_to_humans, COUNT(*) as c FROM care GROUP BY toxic_to_humans")
    print(f"\ntoxic_to_humans distribution:", flush=True)
    for t in tox:
        print(f"  {str(t['toxic_to_humans']):10s} {t['c']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    step_only = None
    if '--step' in sys.argv:
        idx = sys.argv.index('--step')
        if idx + 1 < len(sys.argv):
            step_only = int(sys.argv[idx + 1])

    if step_only is None or step_only == 1:
        step1_flag_unverified(dry_run)
    if step_only is None or step_only == 2:
        step2_wikipedia_toxic(dry_run)
    if step_only is None or step_only == 3:
        step3_wikidata_toxic(dry_run)
    if step_only is None or step_only == 4:
        step4_update_care(dry_run)

    show_results()
