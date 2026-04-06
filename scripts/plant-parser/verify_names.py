"""
Verify and fix common names for plants where common_name = scientific_name.
Uses Wikipedia to find real common names, with strict validation.

Validation rules:
1. REJECT if Wikipedia title is just genus name (one word, Latin-looking)
2. REJECT if title contains taxonomic markers (var., subsp., sect., ×)
3. REJECT if title = scientific name (redirect to same page)
4. REJECT if description says "genus of" or "species of" (genus/family page)
5. ACCEPT only if title looks like a real common name (2+ words, not Latin)
6. Cross-validate with Trefle/Perenual common_name in source_data if available
"""
import urllib.request
import json
import time
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch

WIKI_API = 'https://en.wikipedia.org/api/rest_v1/page/summary'
UA = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'

# Latin-looking patterns (genus names, taxonomic terms)
LATIN_PATTERN = re.compile(r'^[A-Z][a-z]+$')  # Single capitalized Latin word
TAXONOMIC_MARKERS = ('var.', 'subsp.', 'sect.', ' × ', 'f.', 'cv.')
GENUS_DESCRIPTIONS = ('genus of', 'is a genus', 'family of', 'is a family',
                      'order of', 'is an order', 'section of', 'is a section')


def _is_valid_common_name(title: str, scientific: str, description: str) -> bool:
    """Check if a Wikipedia title is a valid common name."""
    t = title.strip()
    sci = scientific.strip()

    # Same as scientific
    if t.lower() == sci.lower():
        return False

    # Taxonomic markers
    for marker in TAXONOMIC_MARKERS:
        if marker in t:
            return False

    # Single Latin-looking word (probably genus name)
    if LATIN_PATTERN.match(t):
        return False

    # Just first word of scientific name (genus only)
    if t == sci.split()[0]:
        return False

    # Description says it's a genus/family page
    desc_lower = (description or '').lower()
    for marker in GENUS_DESCRIPTIONS:
        if marker in desc_lower:
            return False

    # Contains parentheses (disambiguation or qualifier)
    if '(' in t:
        return False

    # All caps or all lowercase (weird)
    if t == t.upper() or t == t.lower():
        # Allow lowercase if it's multi-word like "bird's-nest fern"
        if ' ' not in t and '-' not in t:
            return False

    return True


def _get_cross_source_name(plant_id: str) -> str | None:
    """Check if Trefle/Perenual already has a common name for this plant."""
    rows = turso_query(
        "SELECT value FROM source_data WHERE plant_id = ? AND field = 'common_name' AND source IN ('trefle', 'perenual')",
        [plant_id]
    )
    if rows:
        return rows[0]['value']
    # Also check common_name_en from other sources
    rows2 = turso_query(
        "SELECT value FROM source_data WHERE plant_id = ? AND field = 'common_name_en'",
        [plant_id]
    )
    if rows2:
        return rows2[0]['value']
    return None


def verify_and_fix_names(limit=500, delay=0.15):
    """Find plants where common_name = scientific and try to fix via Wikipedia."""
    # Get plants with sci_copy names
    rows = turso_query('''
        SELECT cn.plant_id, cn.name as common_name, p.scientific
        FROM common_names cn
        JOIN plants p ON cn.plant_id = p.plant_id
        WHERE cn.lang = 'en' AND cn.is_primary = 1
        AND cn.name = p.scientific
        LIMIT ?
    ''', [limit])

    if not rows:
        print("[verify_names] No sci_copy names to fix")
        return

    total = len(rows)
    print(f"[verify_names] Checking {total} plants with sci_copy names...", flush=True)

    fixed = 0
    rejected = 0
    no_article = 0
    cross_source_fixed = 0
    stmts = []

    for i, r in enumerate(rows):
        pid = r['plant_id']
        sci = r['scientific']

        # Step 1: Check cross-source names first (no API call needed)
        cross_name = _get_cross_source_name(pid)
        if cross_name and cross_name.lower() != sci.lower():
            stmts.append((
                "INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, 'en', ?, 1)",
                [pid, cross_name]
            ))
            stmts.append((
                "UPDATE common_names SET is_primary = 0 WHERE plant_id = ? AND lang = 'en' AND name = ? AND is_primary = 1",
                [pid, sci]
            ))
            cross_source_fixed += 1
            fixed += 1
            continue

        # Step 2: Check Wikipedia
        title_url = sci.replace(' ', '_')
        url = f'{WIKI_API}/{urllib.parse.quote(title_url)}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            wiki_title = data.get('title', '')
            wiki_desc = data.get('description', '')
            page_type = data.get('type', '')

            if page_type == 'disambiguation':
                no_article += 1
                continue

            if _is_valid_common_name(wiki_title, sci, wiki_desc):
                stmts.append((
                    "INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, 'en', ?, 1)",
                    [pid, wiki_title]
                ))
                stmts.append((
                    "UPDATE common_names SET is_primary = 0 WHERE plant_id = ? AND lang = 'en' AND name = ? AND is_primary = 1",
                    [pid, sci]
                ))
                fixed += 1
                if fixed <= 30:
                    print(f"  ✓ {pid:35s} | {sci:30s} -> {wiki_title}", flush=True)
            else:
                rejected += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                no_article += 1
            else:
                time.sleep(1)
        except Exception:
            pass

        time.sleep(delay)

        # Batch write every 50
        if len(stmts) >= 50:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 200 == 0:
            print(f"  Progress: {i+1}/{total}, fixed={fixed} (cross={cross_source_fixed}), rejected={rejected}, no_article={no_article}", flush=True)

    if stmts:
        turso_batch(stmts)

    print(f"\n[verify_names] Done: {total} checked", flush=True)
    print(f"  Fixed: {fixed} ({fixed*100//max(total,1)}%)", flush=True)
    print(f"    - from cross-source: {cross_source_fixed}", flush=True)
    print(f"    - from Wikipedia: {fixed - cross_source_fixed}", flush=True)
    print(f"  Rejected (failed validation): {rejected}", flush=True)
    print(f"  No Wikipedia article: {no_article}", flush=True)
    print(f"  Remaining sci_copy: {total - fixed}", flush=True)


if __name__ == '__main__':
    import urllib.parse
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
    verify_and_fix_names(limit=limit, delay=delay)
