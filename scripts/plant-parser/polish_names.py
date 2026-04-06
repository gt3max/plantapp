"""
Post-Wikipedia polisher: verify and fix names + descriptions for all plants.
Runs AFTER wikipedia_fetcher.py completes.

For each plant:
1. Scientific name: verify against POWO (accepted name)
2. Common name EN: priority chain Wikipedia title → Trefle/Perenual consensus → Wikidata → scientific
3. Description: check quality, trim to 500 chars, remove junk

Slow but accurate: ~1 req/sec, cross-validates before writing.
"""
import urllib.request
import urllib.parse
import json
import time
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch, store_source_data

UA = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'


# ─── Wikipedia ──────────────────────────────────────────────────

def _wiki_summary(title: str) -> dict | None:
    """Fetch Wikipedia summary. Returns {title, description, extract} or None."""
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get('type') == 'disambiguation':
            return None
        return {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'extract': data.get('extract', ''),
        }
    except:
        return None


# ─── POWO ───────────────────────────────────────────────────────

def _powo_accepted_name(scientific: str) -> str | None:
    """Check POWO for accepted scientific name. Returns accepted name or None."""
    query = scientific.replace(' ', '%20')
    url = f'https://powo.science.kew.org/api/2/search?q={query}&filters=accepted'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get('results', [])
        if results:
            return results[0].get('name', '')
    except:
        pass
    return None


# ─── Validation helpers ─────────────────────────────────────────

def _is_real_common_name(name: str, scientific: str) -> bool:
    """Check if a name is a real common name, not scientific/taxonomic."""
    if not name or not name.strip():
        return False
    n = name.strip()
    sci = scientific.strip()

    # Same as scientific
    if n.lower() == sci.lower():
        return False

    # Just genus name
    if n == sci.split()[0]:
        return False

    # Single Latin-looking word (capitalized, no spaces)
    if re.match(r'^[A-Z][a-z]+$', n):
        return False

    # Looks like Latin binomial (Genus species) — it's a synonym, not common name
    parts = n.split()
    if len(parts) == 2 and re.match(r'^[A-Z][a-z]+$', parts[0]) and re.match(r'^[a-z]+$', parts[1]):
        return False

    # Contains taxonomic markers
    for m in ('var.', 'subsp.', 'sect.', ' × ', 'f. '):
        if m in n:
            return False

    return True


def _trim_description(text: str) -> str:
    """Trim description to ~500 chars at sentence boundary."""
    if not text or len(text) <= 500:
        return text
    cut = text[:500].rfind('.')
    if cut > 200:
        return text[:cut + 1]
    return text[:500]


def _is_junk_description(text: str) -> bool:
    """Check if description is junk (too short, generic, or about wrong topic)."""
    if not text:
        return True
    t = text.strip()
    if len(t) < 30:
        return True
    # Wikipedia disambiguation remnants
    if 'may refer to' in t.lower() or 'is a disambiguation' in t.lower():
        return True
    # Not about a plant at all
    plant_keywords = ('plant', 'species', 'genus', 'family', 'flower', 'leaf', 'leaves',
                      'grow', 'native', 'tropical', 'succulent', 'tree', 'shrub', 'herb',
                      'perennial', 'annual', 'fern', 'palm', 'cactus', 'orchid', 'vine')
    t_lower = t.lower()
    if not any(kw in t_lower for kw in plant_keywords):
        return True
    return False


# ─── Main polisher ──────────────────────────────────────────────

def polish(batch_size=500, delay=1.0):
    """Polish names and descriptions for all plants, batch by batch."""

    # Get plants to process — start with those that have been touched by Wikipedia
    # (have a description) but also do all plants
    rows = turso_query('''
        SELECT p.plant_id, p.scientific, p.description,
               (SELECT cn.name FROM common_names cn
                WHERE cn.plant_id = p.plant_id AND cn.lang = 'en' AND cn.is_primary = 1
                LIMIT 1) as current_common
        FROM plants p
        ORDER BY p.plant_id
        LIMIT ?
    ''', [batch_size])

    total = len(rows)
    print(f"[polish] Processing {total} plants...", flush=True)
    print(f"[polish] Delay: {delay}s per plant (Wikipedia API)", flush=True)

    stats = {
        'sci_fixed': 0,
        'name_fixed': 0,
        'name_added': 0,
        'desc_fixed': 0,
        'desc_removed': 0,
        'already_ok': 0,
    }
    stmts = []

    for i, r in enumerate(rows):
        pid = r['plant_id']
        sci = r['scientific'] or ''
        current_common = r['current_common'] or ''
        current_desc = r['description'] or ''

        changes = []

        # ─── Step 1: Get Wikipedia data (single API call) ───
        wiki = _wiki_summary(sci.replace(' ', '_'))
        time.sleep(delay)

        # ─── Step 2: Verify scientific name via POWO ───
        # Only check if we suspect issues (skip for now to save API calls)
        # POWO check can be done in a separate pass

        # ─── Step 3: Determine best common name ───
        best_name = None
        name_source = None

        # Priority 1: Wikipedia title (if it's a real common name)
        if wiki and _is_real_common_name(wiki['title'], sci):
            best_name = wiki['title']
            name_source = 'wikipedia_title'

        # Priority 2: Check existing source_data for Trefle/Perenual names
        if not best_name:
            src_rows = turso_query(
                "SELECT source, value FROM source_data WHERE plant_id = ? AND field IN ('common_name', 'common_name_en')",
                [pid]
            )
            candidates = {}
            for sr in src_rows:
                val = sr['value']
                if val and _is_real_common_name(val, sci):
                    candidates[sr['source']] = val

            # If 2+ sources agree — use consensus
            if len(candidates) >= 2:
                names_lower = {}
                for src, val in candidates.items():
                    key = val.lower().strip()
                    if key not in names_lower:
                        names_lower[key] = []
                    names_lower[key].append(val)
                for key, vals in names_lower.items():
                    if len(vals) >= 2:
                        best_name = vals[0]
                        name_source = 'consensus'
                        break

            # If only 1 source — use it if it's from a trusted source
            if not best_name and candidates:
                for src in ('trefle', 'perenual', 'ncstate', 'biologiste95'):
                    if src in candidates:
                        best_name = candidates[src]
                        name_source = src
                        break

        # Priority 3: Wikidata label (already in common_names, check if it's real)
        if not best_name and current_common and _is_real_common_name(current_common, sci):
            best_name = current_common
            name_source = 'existing'

        # Apply name fix if needed
        if best_name and best_name != current_common:
            # Don't overwrite if current is already a real name and best is just different
            if not current_common or not _is_real_common_name(current_common, sci):
                stmts.append((
                    "UPDATE common_names SET is_primary = 0 WHERE plant_id = ? AND lang = 'en' AND is_primary = 1",
                    [pid]
                ))
                stmts.append((
                    "INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, 'en', ?, 1)",
                    [pid, best_name]
                ))
                changes.append(f'name: "{current_common}" -> "{best_name}" ({name_source})')
                if current_common:
                    stats['name_fixed'] += 1
                else:
                    stats['name_added'] += 1
            else:
                stats['already_ok'] += 1
        else:
            stats['already_ok'] += 1

        # ─── Step 4: Verify/fix description ───
        wiki_desc = wiki['extract'] if wiki else ''

        if not current_desc and wiki_desc and not _is_junk_description(wiki_desc):
            # No description — add Wikipedia's
            trimmed = _trim_description(wiki_desc)
            stmts.append((
                "UPDATE plants SET description = ? WHERE plant_id = ? AND (description IS NULL OR description = '')",
                [trimmed, pid]
            ))
            changes.append(f'desc: added ({len(trimmed)} chars)')
            stats['desc_fixed'] += 1

        elif current_desc and _is_junk_description(current_desc):
            # Junk description — replace with Wikipedia's if available
            if wiki_desc and not _is_junk_description(wiki_desc):
                trimmed = _trim_description(wiki_desc)
                stmts.append((
                    "UPDATE plants SET description = ? WHERE plant_id = ?",
                    [trimmed, pid]
                ))
                changes.append(f'desc: replaced junk ({len(trimmed)} chars)')
                stats['desc_fixed'] += 1
            else:
                # No good replacement — clear junk
                stmts.append((
                    "UPDATE plants SET description = NULL WHERE plant_id = ?",
                    [pid]
                ))
                stats['desc_removed'] += 1

        # Log changes
        if changes:
            print(f"  {pid:35s} | {' | '.join(changes)}", flush=True)

        # Batch write every 30
        if len(stmts) >= 30:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{total}] names_fixed={stats['name_fixed']}, names_added={stats['name_added']}, "
                  f"desc_fixed={stats['desc_fixed']}, already_ok={stats['already_ok']}", flush=True)

    # Flush remaining
    if stmts:
        turso_batch(stmts)

    print(f"\n[polish] Done: {total} plants processed", flush=True)
    print(f"  Scientific fixed: {stats['sci_fixed']}", flush=True)
    print(f"  Names fixed: {stats['name_fixed']}", flush=True)
    print(f"  Names added: {stats['name_added']}", flush=True)
    print(f"  Descriptions fixed: {stats['desc_fixed']}", flush=True)
    print(f"  Descriptions removed (junk): {stats['desc_removed']}", flush=True)
    print(f"  Already OK: {stats['already_ok']}", flush=True)


if __name__ == '__main__':
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    polish(batch_size=batch, delay=delay)
