"""
POWO (Plants of the World Online) — Kew Gardens.
Source: https://powo.science.kew.org/
Free API, no key needed.
Gives: climate, lifeform, native distribution, synonyms.
For cross-verification and enrichment.
"""
import json
import re
import time
import urllib.request
import urllib.parse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_query, turso_batch

POWO_API = 'https://powo.science.kew.org/api/2'
DELAY = 0.5  # Polite


def search_powo(scientific_name):
    """Search POWO for a plant, return fqId."""
    params = urllib.parse.urlencode({'q': scientific_name})
    url = f'{POWO_API}/search?{params}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    results = data.get('results', [])
    if results:
        # Prefer accepted name exact match
        for r in results:
            if r.get('accepted') and r.get('name', '').lower() == scientific_name.lower():
                return r.get('fqId')
        return results[0].get('fqId')
    return None


def get_powo_detail(fq_id):
    """Get taxon detail from POWO."""
    url = f'{POWO_API}/taxon/{urllib.parse.quote(fq_id)}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def enrich_from_powo(limit=500):
    """Enrich plants with POWO climate, lifeform, distribution data."""
    rows = turso_query('''
        SELECT p.plant_id, p.scientific
        FROM plants p
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        ORDER BY
            CASE WHEN p.sources LIKE ? THEN 0 ELSE 1 END,
            p.scientific
        LIMIT ?
    ''', ['%perenual%', limit])

    print(f"[POWO] Checking {len(rows)} plants...")
    enriched = 0
    not_found = 0

    for i, row in enumerate(rows):
        scientific = row['scientific']
        pid = row['plant_id']

        try:
            fq_id = search_powo(scientific)
            time.sleep(DELAY)

            if not fq_id:
                not_found += 1
                continue

            detail = get_powo_detail(fq_id)
            time.sleep(DELAY)

            climate = detail.get('climate', '')
            lifeform = detail.get('lifeform', '')
            locations = detail.get('locations', []) or []
            # Locations can be list of strings or list of dicts
            native = []
            if locations and isinstance(locations[0], dict):
                native = [l.get('name', '') for l in locations if l.get('establishment') == 'Native']
            elif locations and isinstance(locations[0], str):
                native = [l.replace('_', ' ') for l in locations[:5]]

            if not climate and not lifeform and not native:
                not_found += 1
                continue

            statements = []

            # Climate → can help determine indoor/outdoor, preset
            # Map climate to humidity hint
            if climate:
                climate_hint = ''
                cl = climate.lower()
                if 'tropical' in cl or 'wet' in cl:
                    climate_hint = 'High humidity preferred (tropical climate)'
                elif 'desert' in cl or 'dry' in cl or 'arid' in cl:
                    climate_hint = 'Low humidity, drought-tolerant (arid climate)'
                elif 'temperate' in cl:
                    climate_hint = 'Average humidity (temperate climate)'

                if climate_hint:
                    statements.append((
                        "UPDATE care SET humidity_action = CASE WHEN humidity_action IS NULL OR humidity_action = '' THEN ? ELSE humidity_action END WHERE plant_id = ?",
                        [climate_hint, pid]
                    ))

                # Store climate as light_guide supplement
                statements.append((
                    "UPDATE care SET light_guide = CASE WHEN light_guide IS NULL OR light_guide = '' THEN ? WHEN light_guide NOT LIKE ? THEN light_guide || ? ELSE light_guide END WHERE plant_id = ?",
                    [f"Climate: {climate}", f"%Climate%", f" | Climate: {climate}", pid]
                ))

            # Lifeform → lifecycle/category hint
            if lifeform:
                lifecycle_map = {
                    'annual': 'annual', 'biennial': 'biennial',
                    'perennial': 'perennial', 'shrub': 'perennial',
                    'tree': 'perennial', 'liana': 'perennial',
                }
                for key, val in lifecycle_map.items():
                    if key in lifeform.lower():
                        statements.append((
                            "UPDATE care SET lifecycle = CASE WHEN lifecycle IS NULL OR lifecycle = '' THEN ? ELSE lifecycle END WHERE plant_id = ?",
                            [val, pid]
                        ))
                        break

            # Native distribution → plants.origin (proper field now!)
            if native:
                origin_text = ', '.join(native[:5])
                statements.append((
                    "UPDATE plants SET origin = CASE WHEN origin IS NULL OR origin = '' THEN ? ELSE origin END WHERE plant_id = ?",
                    [origin_text, pid]
                ))

            # Synonyms
            synonyms = detail.get('synonyms', []) or []
            if synonyms:
                syn_names = [s.get('name', '') for s in synonyms if s.get('name')][:10]
                if syn_names:
                    statements.append((
                        "UPDATE plants SET synonyms = CASE WHEN synonyms IS NULL OR synonyms = '' THEN ? ELSE synonyms END WHERE plant_id = ?",
                        [json.dumps(syn_names), pid]
                    ))

            # Taxonomic order
            taxon_order = detail.get('order', '') or ''
            if taxon_order:
                statements.append((
                    "UPDATE plants SET order_name = CASE WHEN order_name IS NULL OR order_name = '' THEN ? ELSE order_name END WHERE plant_id = ?",
                    [taxon_order, pid]
                ))

            if statements:
                turso_batch(statements)
                enriched += 1

            if (i + 1) % 50 == 0:
                print(f"[POWO] Progress: {i+1}/{len(rows)}, enriched: {enriched}, not found: {not_found}")

        except Exception as e:
            not_found += 1
            if not_found <= 3:
                print(f"  ! {scientific}: {e}")
            continue

    print(f"[POWO] Done: {enriched} enriched, {not_found} not found")
    return enriched


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    enrich_from_powo(limit)
