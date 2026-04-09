"""
Fetch descriptions for plants without them.
Priority: GBIF → Wikipedia multilingual → PFAF → iNaturalist

Does NOT overwrite existing descriptions. Source attribution on every description.

Usage:
    python3 fetch_descriptions.py              # full run (~2 hours)
    python3 fetch_descriptions.py --dry-run    # preview
    python3 fetch_descriptions.py --limit 500  # limit
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

UA = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'
MIN_DESC_LENGTH = 100
MAX_DESC_LENGTH = 500
WIKI_LANGUAGES = ['en', 'de', 'fr', 'ru', 'es', 'pt', 'ja', 'zh', 'it', 'pl']


def clean_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_gbif_description(scientific):
    """GBIF: species match → descriptions. Returns (description, source_detail) or (None, None)."""
    try:
        q = urllib.parse.quote(scientific)
        url = f'https://api.gbif.org/v1/species/match?name={q}'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        key = data.get('usageKey')
        if not key:
            return None, None

        url2 = f'https://api.gbif.org/v1/species/{key}/descriptions'
        req2 = urllib.request.Request(url2, headers={'User-Agent': UA})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            descs = json.loads(resp2.read().decode())

        results = descs.get('results', [])
        if not results:
            return None, None

        # Prefer English, longer descriptions
        best = None
        best_len = 0
        for d in results:
            text = clean_html(d.get('description', ''))
            lang = d.get('language', '')
            source = d.get('source', '')
            if len(text) >= MIN_DESC_LENGTH and len(text) > best_len:
                # Prefer English
                if lang in ('eng', 'en', '') or best is None:
                    best = text[:MAX_DESC_LENGTH]
                    best_len = len(text)
                    best_source = f'gbif:{source}:{lang}'

        if best:
            return best, best_source
        return None, None
    except Exception:
        return None, None


def fetch_wikipedia_description(scientific, languages=None):
    """Wikipedia multilingual fallback. Returns (description, source_detail) or (None, None)."""
    if languages is None:
        languages = WIKI_LANGUAGES

    title = scientific.replace(' ', '_')

    for lang in languages:
        try:
            url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}'
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            extract = data.get('extract', '').strip()
            if len(extract) >= MIN_DESC_LENGTH:
                return extract[:MAX_DESC_LENGTH], f'wikipedia_{lang}'

        except Exception:
            pass

        time.sleep(0.2)

    return None, None


def fetch_pfaf_description(plant_id):
    """Get PFAF cultivation_details from source_data."""
    rows = turso_query(
        "SELECT value FROM source_data WHERE plant_id = ? AND source = 'pfaf' AND field IN ('summary', 'cultivation_details') ORDER BY LENGTH(value) DESC LIMIT 1",
        [plant_id]
    )
    if rows and len(rows[0]['value']) >= MIN_DESC_LENGTH:
        return rows[0]['value'][:MAX_DESC_LENGTH], 'pfaf_desc'
    return None, None


def run(dry_run=False, limit=None):
    plants = turso_query("""
        SELECT plant_id, scientific FROM plants
        WHERE (description IS NULL OR description = '')
        AND scientific IS NOT NULL AND scientific != ''
        ORDER BY
            CASE WHEN plant_id IN (SELECT DISTINCT plant_id FROM plant_images) THEN 0 ELSE 1 END,
            plant_id
    """)

    if limit:
        plants = plants[:limit]

    print(f"[descriptions] {len(plants)} plants need descriptions", flush=True)

    # Pre-load PFAF plant_ids for quick check
    pfaf_plants = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'pfaf' AND field IN ('summary', 'cultivation_details')")
    pfaf_set = set(r['plant_id'] for r in pfaf_plants)
    print(f"  PFAF available for: {len(pfaf_set)} plants", flush=True)

    stmts = []
    stats = {'gbif': 0, 'wikipedia': 0, 'pfaf': 0, 'not_found': 0}
    consecutive_errors = 0

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        sci = plant['scientific']
        desc = None
        source = None

        # Priority 1: GBIF
        desc, source = fetch_gbif_description(sci)
        if desc:
            stats['gbif'] += 1
            consecutive_errors = 0
        else:
            # Priority 2: Wikipedia multilingual
            desc, source = fetch_wikipedia_description(sci)
            if desc:
                stats['wikipedia'] += 1
                consecutive_errors = 0
            else:
                # Priority 3: PFAF
                if pid in pfaf_set:
                    desc, source = fetch_pfaf_description(pid)
                    if desc:
                        stats['pfaf'] += 1

                if not desc:
                    stats['not_found'] += 1
                    consecutive_errors += 1

        if desc and not dry_run:
            stmts.append(("UPDATE plants SET description = ? WHERE plant_id = ? AND (description IS NULL OR description = '')",
                          [desc, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'description_source', ?, datetime('now'))",
                [pid, source.split(':')[0] if ':' in source else source, source]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 100 == 0:
            total_found = stats['gbif'] + stats['wikipedia'] + stats['pfaf']
            print(f"  [{i+1}/{len(plants)}] gbif={stats['gbif']} wiki={stats['wikipedia']} pfaf={stats['pfaf']} miss={stats['not_found']}", flush=True)

        # Stop on sustained errors (API down)
        if consecutive_errors >= 20:
            print(f"  20 consecutive misses at [{i+1}] — stopping", flush=True)
            break

        time.sleep(0.5)

    if stmts and not dry_run:
        turso_batch(stmts)

    total_found = stats['gbif'] + stats['wikipedia'] + stats['pfaf']
    print(f"\n[descriptions] Done:", flush=True)
    print(f"  GBIF:       {stats['gbif']}", flush=True)
    print(f"  Wikipedia:  {stats['wikipedia']}", flush=True)
    print(f"  PFAF:       {stats['pfaf']}", flush=True)
    print(f"  Not found:  {stats['not_found']}", flush=True)
    print(f"  Total:      {total_found}", flush=True)

    if not dry_run:
        filled = turso_query("SELECT COUNT(*) as c FROM plants WHERE description IS NOT NULL AND description != ''")
        print(f"  Descriptions in DB: {filled[0]['c']} / 20261", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    limit = None
    for arg in sys.argv[1:]:
        if arg.startswith('--limit'):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
    run(dry_run=dry_run, limit=limit)
