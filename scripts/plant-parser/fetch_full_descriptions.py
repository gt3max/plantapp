"""
Fetch FULL descriptions from Wikipedia + GBIF → source_data (no truncation).
Does NOT touch plants.description. Only writes to source_data.

Our encyclopedia: full raw texts from every source, preserved forever.

Usage:
    python3 fetch_full_descriptions.py              # all plants
    python3 fetch_full_descriptions.py --limit 500  # limited
    python3 fetch_full_descriptions.py --dry-run
"""
import sys
import os
import json
import time
import re
import html
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

UA = 'PlantApp/1.0 (plantapp.pro; encyclopedia project)'
WIKI_LANGUAGES = ['en', 'de', 'fr', 'ru', 'es', 'pt', 'ja', 'zh', 'it']


def clean_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_wikipedia_full(scientific):
    """Fetch FULL Wikipedia extract (no truncation). Returns {lang: text} dict."""
    title = scientific.replace(' ', '_')
    results = {}

    for lang in WIKI_LANGUAGES:
        try:
            url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}'
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            extract = data.get('extract', '').strip()
            if extract and len(extract) >= 50:
                results[lang] = extract  # FULL text, no truncation

        except Exception:
            pass

        time.sleep(0.1)

        # If we got English, don't need all languages
        if 'en' in results and len(results['en']) > 200:
            break

    return results


def fetch_gbif_full(scientific):
    """Fetch ALL GBIF descriptions (no truncation). Returns list of descriptions."""
    try:
        q = urllib.parse.quote(scientific)
        url = f'https://api.gbif.org/v1/species/match?name={q}'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        key = data.get('usageKey')
        if not key:
            return []

        url2 = f'https://api.gbif.org/v1/species/{key}/descriptions'
        req2 = urllib.request.Request(url2, headers={'User-Agent': UA})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            descs = json.loads(resp2.read().decode())

        results = []
        for d in descs.get('results', []):
            text = clean_html(d.get('description', ''))
            lang = d.get('language', 'eng')
            source = d.get('source', '')
            if text and len(text) >= 50:
                results.append({
                    'text': text,  # FULL text, no truncation
                    'language': lang,
                    'source': source,
                })

        return results
    except Exception:
        return []


def run(dry_run=False, limit=None):
    # Get all plants with scientific names
    plants = turso_query("""
        SELECT plant_id, scientific FROM plants
        WHERE scientific IS NOT NULL AND scientific != ''
        ORDER BY plant_id
    """)

    # Filter out already done
    already = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'wikipedia_full'")
    already_set = set(r['plant_id'] for r in already)
    plants = [p for p in plants if p['plant_id'] not in already_set]

    # Prioritize plants with photos
    photo_plants = turso_query("SELECT DISTINCT plant_id FROM plant_images")
    photo_set = set(r['plant_id'] for r in photo_plants)
    plants.sort(key=lambda p: (0 if p['plant_id'] in photo_set else 1, p['plant_id']))

    if limit:
        plants = plants[:limit]

    print(f"[full_desc] {len(plants)} plants to fetch (skipping already done)", flush=True)

    stmts = []
    stats = {'wiki': 0, 'gbif': 0, 'both': 0, 'none': 0}

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        sci = plant['scientific']

        # Wikipedia
        wiki = fetch_wikipedia_full(sci)
        has_wiki = bool(wiki)

        # GBIF
        gbif = fetch_gbif_full(sci)
        has_gbif = bool(gbif)

        if has_wiki:
            stats['wiki'] += 1
        if has_gbif:
            stats['gbif'] += 1
        if has_wiki and has_gbif:
            stats['both'] += 1
        if not has_wiki and not has_gbif:
            stats['none'] += 1

        if not dry_run:
            # Store Wikipedia extracts (all languages found)
            for lang, text in wiki.items():
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_full', ?, ?, datetime('now'))",
                    [pid, f'extract_{lang}', text]
                ))

            # Store GBIF descriptions (all found)
            for j, desc in enumerate(gbif):
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'gbif_full', ?, ?, datetime('now'))",
                    [pid, f'description_{j}_{desc["language"]}', desc['text']]
                ))

            # Mark as processed even if nothing found
            if not wiki and not gbif:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'wikipedia_full', 'not_found', 'true', datetime('now'))",
                    [pid]
                ))

            if len(stmts) >= 50:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(plants)}] wiki={stats['wiki']} gbif={stats['gbif']} both={stats['both']} none={stats['none']}", flush=True)

        time.sleep(0.3)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[full_desc] Done:", flush=True)
    print(f"  Wikipedia: {stats['wiki']}", flush=True)
    print(f"  GBIF:      {stats['gbif']}", flush=True)
    print(f"  Both:      {stats['both']}", flush=True)
    print(f"  None:      {stats['none']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    limit = None
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    run(dry_run=dry_run, limit=limit)
