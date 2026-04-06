"""
Wikidata SPARQL fetcher — multilingual common names for plants.
Uses Wikidata Query Service (WDQS) to fetch labels in 15 languages.

Rate limit: polite 1 req/sec with proper User-Agent.
Batch: 50 plants per SPARQL query (VALUES clause).
"""
import json
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

WDQS_URL = 'https://query.wikidata.org/sparql'
USER_AGENT = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'

# Languages we want (ISO 639-1)
LANGUAGES = ['en', 'ru', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'ja', 'zh', 'ko', 'ar', 'hi', 'tr']


def _sparql_query(query: str) -> list[dict]:
    """Execute SPARQL query against Wikidata Query Service."""
    params = urllib.parse.urlencode({'query': query, 'format': 'json'})
    req = urllib.request.Request(
        f'{WDQS_URL}?{params}',
        headers={'User-Agent': USER_AGENT, 'Accept': 'application/sparql-results+json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data.get('results', {}).get('bindings', [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  [WARN] Rate limited (429), waiting 60s...", flush=True)
            time.sleep(60)
            return _sparql_query(query)  # retry once
        raise
    except Exception as e:
        print(f"  [ERROR] SPARQL query failed: {e}", flush=True)
        return []


def _fetch_names_batch(scientific_names: list[str]) -> dict[str, dict[str, str]]:
    """Fetch common names for a batch of plants from Wikidata.

    Uses taxon name (P225) to find Wikidata items, then gets labels.
    Returns: {scientific_name: {lang: name, ...}, ...}
    """
    # Build VALUES clause
    values = ' '.join(f'"{name}"' for name in scientific_names)

    # SPARQL: find items by taxon name, get labels in all target languages
    lang_list = ' '.join(f'"{l}"' for l in LANGUAGES)
    query = f"""
    SELECT ?taxonName ?label ?lang WHERE {{
      VALUES ?taxonName {{ {values} }}
      ?item wdt:P225 ?taxonName .
      ?item rdfs:label ?label .
      BIND(LANG(?label) AS ?lang)
      FILTER(LANG(?label) IN ({', '.join(f'"{l}"' for l in LANGUAGES)}))
    }}
    """

    results = _sparql_query(query)

    names_map = {}
    for row in results:
        sci = row.get('taxonName', {}).get('value', '')
        lang = row.get('lang', {}).get('value', '')
        label = row.get('label', {}).get('value', '')
        if sci and lang and label:
            if sci not in names_map:
                names_map[sci] = {}
            names_map[sci][lang] = label

    return names_map


def _scientific_to_plant_id(scientific: str) -> str:
    """Convert scientific name to plant_id format."""
    return scientific.lower().replace(' ', '_').replace("'", '').replace('-', '_')


def fetch_all_names(batch_size=50, sparql_delay=2.0, pause_every=500, pause_seconds=30):
    """Fetch multilingual names for all plants missing them.

    Args:
        batch_size: plants per SPARQL query (max ~100 for VALUES clause)
        sparql_delay: seconds between SPARQL requests
        pause_every: take a break after this many plants
        pause_seconds: seconds to pause
    """
    # Get plants that need names
    # Plants with < 3 languages in common_names
    rows = turso_query('''
        SELECT p.plant_id, p.scientific
        FROM plants p
        WHERE p.scientific IS NOT NULL AND p.scientific != ''
        AND p.plant_id NOT IN (
            SELECT plant_id FROM common_names
            GROUP BY plant_id
            HAVING COUNT(DISTINCT lang) >= 5
        )
        ORDER BY p.plant_id
    ''')

    if not rows:
        print("[Wikidata] All plants have sufficient names", flush=True)
        return 0

    total = len(rows)
    print(f"[Wikidata] {total} plants need multilingual names", flush=True)
    print(f"[Wikidata] Settings: batch={batch_size}, delay={sparql_delay}s, pause every {pause_every} ({pause_seconds}s)", flush=True)

    updated = 0
    processed = 0

    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        sci_names = [r['scientific'] for r in batch]
        plant_ids = {r['scientific']: r['plant_id'] for r in batch}

        try:
            names_map = _fetch_names_batch(sci_names)
        except Exception as e:
            print(f"  [ERROR] Batch {i}-{i+batch_size}: {e}", flush=True)
            time.sleep(sparql_delay * 5)
            continue

        # Prepare INSERT statements
        stmts = []
        for sci, langs in names_map.items():
            pid = plant_ids.get(sci)
            if not pid:
                # Try matching by plant_id conversion
                pid_guess = _scientific_to_plant_id(sci)
                pid = next((r['plant_id'] for r in batch if r['plant_id'] == pid_guess), None)
            if not pid:
                continue

            for lang, name in langs.items():
                is_primary = 1 if lang == 'en' else 0
                stmts.append((
                    "INSERT OR IGNORE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, ?, ?, ?)",
                    [pid, lang, name, is_primary]
                ))

            # Also store wikidata_id info in source_data for tracking
            updated += 1

        # Write to DB in sub-batches (Turso pipeline limit)
        for j in range(0, len(stmts), 50):
            chunk = stmts[j:j+50]
            if chunk:
                try:
                    turso_batch(chunk)
                except Exception as e:
                    print(f"  [ERROR] DB write: {e}", flush=True)

        processed += len(batch)

        if processed % 100 == 0 or processed == total:
            print(f"[Wikidata] {processed}/{total} processed, {updated} with names", flush=True)

        # Pause between SPARQL requests
        time.sleep(sparql_delay)

        # Longer pause periodically
        if processed % pause_every == 0 and processed < total:
            print(f"[Wikidata] Pause {pause_seconds}s after {processed} plants...", flush=True)
            time.sleep(pause_seconds)

    print(f"[Wikidata] Done: {updated}/{total} plants got multilingual names", flush=True)
    return updated


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch multilingual plant names from Wikidata')
    parser.add_argument('--batch', type=int, default=50, help='Plants per SPARQL query')
    parser.add_argument('--delay', type=float, default=2.0, help='Seconds between queries')
    parser.add_argument('--pause-every', type=int, default=500, help='Pause after N plants')
    parser.add_argument('--pause-seconds', type=int, default=30, help='Pause duration')
    args = parser.parse_args()

    fetch_all_names(
        batch_size=args.batch,
        sparql_delay=args.delay,
        pause_every=args.pause_every,
        pause_seconds=args.pause_seconds,
    )
