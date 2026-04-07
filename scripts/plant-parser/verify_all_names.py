"""
Cross-verify scientific + common names for all plants.
Uses POWO, GBIF, Wikipedia, iNaturalist for cross-validation.

Confidence levels:
- confirmed: 2+ sources agree
- probable: 1 authoritative source (POWO/GBIF)
- unverified: only Trefle
- flagged: conflict between sources

Usage:
    python3 verify_all_names.py --featured     # 56 featured only
    python3 verify_all_names.py --indoor        # 4K indoor
    python3 verify_all_names.py --limit 500     # first 500
"""
import urllib.request
import urllib.parse
import json
import time
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch

UA = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'


def _powo_check(scientific: str) -> dict | None:
    """Check POWO for accepted name."""
    q = urllib.parse.quote(scientific)
    url = f'https://powo.science.kew.org/api/2/search?q={q}&filters=accepted'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get('results', [])
        if results:
            r = results[0]
            return {'name': r.get('name', ''), 'author': r.get('author', ''), 'family': r.get('family', '')}
    except:
        pass
    return None


def _gbif_check(scientific: str) -> dict | None:
    """Check GBIF for accepted name."""
    q = urllib.parse.quote(scientific)
    url = f'https://api.gbif.org/v1/species/match?name={q}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get('matchType') != 'NONE':
            return {
                'name': data.get('canonicalName', ''),
                'status': data.get('status', ''),
                'family': data.get('family', ''),
                'synonym': data.get('synonym', False),
            }
    except:
        pass
    return None


def _wikipedia_check(scientific: str) -> dict | None:
    """Check Wikipedia for article title (= best common name)."""
    title = scientific.replace(' ', '_')
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get('type') != 'disambiguation':
            return {
                'title': data.get('title', ''),
                'description': data.get('description', ''),
            }
    except:
        pass
    return None


def _inaturalist_check(scientific: str) -> dict | None:
    """Check iNaturalist for preferred common name."""
    q = urllib.parse.quote(scientific)
    url = f'https://api.inaturalist.org/v1/taxa?q={q}&rank=species&is_active=true&per_page=3'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get('results', [])
        for r in results:
            if r.get('name', '').lower() == scientific.lower():
                return {
                    'name': r.get('name', ''),
                    'preferred_common_name': r.get('preferred_common_name', ''),
                    'wikipedia_url': r.get('wikipedia_url', ''),
                }
    except:
        pass
    return None


def _is_real_common(name: str, scientific: str) -> bool:
    """Check if name is a real common name (not just scientific repeated)."""
    if not name:
        return False
    if name.lower() == scientific.lower():
        return False
    if re.match(r'^[A-Z][a-z]+ [a-z]+$', name):
        return False  # Looks like Latin binomial
    return True


def verify_plant(plant_id: str, scientific: str, current_common: str) -> dict:
    """Verify one plant. Returns verification result."""
    result = {
        'plant_id': plant_id,
        'scientific': scientific,
        'current_common': current_common,
        'sci_confirmed': False,
        'common_best': None,
        'common_alternatives': [],
        'confidence': 'unverified',
        'issues': [],
        'sources': {},
    }

    # 1. POWO
    powo = _powo_check(scientific)
    time.sleep(0.3)
    if powo:
        result['sources']['powo'] = powo['name']
        if powo['name'].lower() != scientific.lower():
            result['issues'].append(f"POWO accepted: {powo['name']} (ours: {scientific})")
        else:
            result['sci_confirmed'] = True

    # 2. GBIF
    gbif = _gbif_check(scientific)
    time.sleep(0.3)
    if gbif:
        result['sources']['gbif'] = gbif['name']
        if gbif.get('synonym'):
            result['issues'].append(f"GBIF says synonym, accepted: {gbif['name']}")
        elif gbif['name'].lower() == scientific.lower():
            result['sci_confirmed'] = True

    # 3. Wikipedia
    wiki = _wikipedia_check(scientific)
    time.sleep(0.3)
    if wiki:
        title = wiki['title']
        result['sources']['wikipedia'] = title
        if _is_real_common(title, scientific):
            result['common_alternatives'].append(('wikipedia', title))

    # 4. iNaturalist
    inat = _inaturalist_check(scientific)
    time.sleep(0.3)
    if inat:
        result['sources']['inaturalist'] = inat.get('preferred_common_name', '')
        pcn = inat.get('preferred_common_name', '')
        if _is_real_common(pcn, scientific):
            result['common_alternatives'].append(('inaturalist', pcn))

    # Determine confidence
    sci_sources = sum(1 for s in ['powo', 'gbif'] if s in result['sources'])
    if sci_sources >= 2 and result['sci_confirmed']:
        result['confidence'] = 'confirmed'
    elif sci_sources >= 1 and result['sci_confirmed']:
        result['confidence'] = 'probable'
    elif result['issues']:
        result['confidence'] = 'flagged'

    # Determine best common name
    candidates = {}
    for source, name in result['common_alternatives']:
        key = name.lower()
        if key not in candidates:
            candidates[key] = []
        candidates[key].append((source, name))

    # Add current
    if _is_real_common(current_common, scientific):
        key = current_common.lower()
        if key not in candidates:
            candidates[key] = []
        candidates[key].append(('current', current_common))

    # Pick best: most sources agree, or Wikipedia title
    best = None
    for key, sources in sorted(candidates.items(), key=lambda x: -len(x[1])):
        if len(sources) >= 2:
            best = sources[0][1]
            break
    if not best:
        # Prefer Wikipedia title
        for source, name in result['common_alternatives']:
            if source == 'wikipedia':
                best = name
                break
    if not best:
        # Prefer iNaturalist
        for source, name in result['common_alternatives']:
            if source == 'inaturalist':
                best = name
                break
    if not best and _is_real_common(current_common, scientific):
        best = current_common

    result['common_best'] = best
    result['all_common'] = list(set(name for _, name in result['common_alternatives']))

    return result


def verify_batch(mode='featured', limit=500):
    """Verify names for a batch of plants."""
    if mode == 'featured':
        with open('/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart') as f:
            text = f.read()
        featured_ids = re.findall(r"plantIdStr: '([^']+)'", text)
        plants = turso_query(f"""
            SELECT p.plant_id, p.scientific, cn.name as common_name
            FROM plants p
            LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.lang = 'en' AND cn.is_primary = 1
            WHERE p.plant_id IN ({','.join(['?' for _ in featured_ids])})
        """, featured_ids)
    elif mode == 'indoor':
        plants = turso_query("""
            SELECT p.plant_id, p.scientific, cn.name as common_name
            FROM plants p
            LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.lang = 'en' AND cn.is_primary = 1
            WHERE p.indoor = 1
            LIMIT ?
        """, [limit])
    else:
        plants = turso_query("""
            SELECT p.plant_id, p.scientific, cn.name as common_name
            FROM plants p
            LEFT JOIN common_names cn ON p.plant_id = cn.plant_id AND cn.lang = 'en' AND cn.is_primary = 1
            LIMIT ?
        """, [limit])

    total = len(plants)
    print(f"[verify_names] Verifying {total} plants...", flush=True)

    stats = {'confirmed': 0, 'probable': 0, 'unverified': 0, 'flagged': 0, 'common_fixed': 0}
    stmts = []

    for i, p in enumerate(plants):
        pid = p['plant_id']
        sci = p['scientific'] or ''
        cn = p.get('common_name') or ''

        if not sci:
            continue

        result = verify_plant(pid, sci, cn)

        stats[result['confidence']] += 1

        # Record alternative common names (DO NOT change primary — only log for review)
        if result['common_best'] and result['common_best'].lower() != cn.lower():
            # Add as non-primary alternative, never overwrite primary
            stmts.append(("INSERT OR IGNORE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, 'en', ?, 0)", [pid, result['common_best']]))
            stats['common_fixed'] += 1

        # Store verification in source_data
        stmts.append((
            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'name_verify', 'confidence', ?, datetime('now'))",
            [pid, result['confidence']]
        ))
        for src, val in result['sources'].items():
            if val:
                stmts.append((
                    "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'scientific_check', ?, datetime('now'))",
                    [pid, src, val]
                ))

        # Log issues and progress
        flag = ''
        if result['issues']:
            flag = f" ⚠️ {'; '.join(result['issues'])}"
        if result['common_best'] and result['common_best'] != cn:
            flag += f" → name: '{cn}' → '{result['common_best']}'"

        if flag or (i + 1) % 10 == 0:
            print(f"  [{i+1}/{total}] {pid:35s} | {result['confidence']:10s} | sci={len(result['sources'])} sources{flag}", flush=True)

        # Batch write
        if len(stmts) >= 40:
            turso_batch(stmts)
            stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"\n[verify_names] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)


if __name__ == '__main__':
    if '--featured' in sys.argv:
        verify_batch(mode='featured')
    elif '--indoor' in sys.argv:
        limit = 500
        for arg in sys.argv:
            if arg.startswith('--limit='):
                limit = int(arg.split('=')[1])
        verify_batch(mode='indoor', limit=limit)
    else:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 500
        verify_batch(mode='all', limit=limit)
