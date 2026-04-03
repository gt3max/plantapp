"""
Permapeople.org website parser — companions, propagation, used_for.
Parses HTML directly (API pagination broken).
9,032 plants, 181 pages × 50 per page.
Polite: 1.5 sec between requests.
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

BASE = 'https://permapeople.org'
DELAY = 1.5


def fetch_page(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def get_plant_slugs(page_num):
    """Get plant slugs from search page."""
    html = fetch_page(f'{BASE}/search?page={page_num}')
    links = re.findall(r'href=\"(/plants/[^\"]+)\"', html)
    unique = list(dict.fromkeys(links))
    # Filter out sub-pages like /history, /edit
    slugs = [l for l in unique if l.count('/') == 2]
    return slugs


def parse_plant_page(html):
    """Extract companion, propagation, used_for data from plant page."""
    data = {}

    # Scientific name
    sci = re.search(r'<i[^>]*>([A-Z][a-z]+ [a-z]+)', html)
    if sci:
        data['scientific'] = sci.group(1)

    # Companion plants — links use full URLs
    comp_match = re.search(r'companion to\s*</h\d>\s*(.*?)(?:antagonist|</section|<h[2345])', html, re.DOTALL)
    if comp_match:
        comp_text = comp_match.group(1)
        companions = re.findall(r'result-name\">([^<]+)', comp_text)
        if companions:
            data['companions'] = list(dict.fromkeys([c.strip() for c in companions if c.strip()]))

    # Antagonist / bad companions
    antag_match = re.search(r'antagonist to\s*</h\d>\s*(.*?)(?:</section|<h[2345])', html, re.DOTALL)
    if antag_match:
        antag_text = antag_match.group(1)
        antagonists = re.findall(r'result-name\">([^<]+)', antag_text)
        if antagonists:
            data['antagonists'] = list(dict.fromkeys([a.strip() for a in antagonists if a.strip()]))

    # Data fields (same key-value structure as API)
    kv_pairs = re.findall(r'<div[^>]*class=\"[^\"]*key[^\"]*\"[^>]*>([^<]+)</div>\s*<div[^>]*class=\"[^\"]*value[^\"]*\"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not kv_pairs:
        # Try th/td pattern
        kv_pairs = re.findall(r'<th[^>]*>([^<]+)</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL)

    for key, val in kv_pairs:
        key = key.strip()
        val = re.sub(r'<[^>]+>', ' ', val).strip()
        if val:
            key_lower = key.lower()
            if 'propagation' in key_lower:
                data['propagation'] = val
            elif 'edible' in key_lower and 'part' in key_lower:
                data['edible_parts'] = val
            elif 'edible' in key_lower:
                data['edible'] = val
            elif 'medicinal' in key_lower:
                data['medicinal'] = val
            elif 'utility' in key_lower or 'use' in key_lower:
                data['used_for'] = val

    return data


def enrich_from_permapeople_web(max_pages=10):
    """Scrape Permapeople website for companion + propagation data."""
    print(f"[Permapeople Web] Scraping up to {max_pages} pages...")
    enriched = 0
    total_checked = 0

    for page_num in range(1, max_pages + 1):
        try:
            slugs = get_plant_slugs(page_num)
            time.sleep(DELAY)

            if not slugs:
                print(f"[Permapeople Web] No more plants at page {page_num}")
                break

            for slug in slugs:
                total_checked += 1
                try:
                    html = fetch_page(f'{BASE}{slug}')
                    time.sleep(DELAY)

                    data = parse_plant_page(html)
                    if not data.get('scientific') and not data.get('companions'):
                        continue

                    # Match to our DB
                    scientific = data.get('scientific', '')
                    if not scientific:
                        # Extract from slug: /plants/solanum-lycopersicum-tomato → solanum lycopersicum
                        parts = slug.split('/')[-1].split('-')
                        if len(parts) >= 2:
                            scientific = f'{parts[0].capitalize()} {parts[1]}'

                    plant_id = scientific.lower().replace(' ', '_').replace("'", '')
                    existing = turso_query('SELECT plant_id FROM plants WHERE plant_id = ?', [plant_id])

                    if not existing:
                        # Try partial match
                        genus = scientific.split()[0] if ' ' in scientific else scientific
                        existing = turso_query(
                            'SELECT plant_id FROM plants WHERE plant_id LIKE ?',
                            [f'{genus.lower()}%']
                        )

                    if not existing:
                        continue

                    pid = existing[0]['plant_id']
                    statements = []

                    # Companions → proper columns now!
                    if data.get('companions'):
                        good = data['companions'][:10]
                        statements.append((
                            "UPDATE care SET good_companions = CASE WHEN good_companions IS NULL OR good_companions = '' OR good_companions = '[]' THEN ? ELSE good_companions END WHERE plant_id = ?",
                            [json.dumps(good), pid]
                        ))
                    if data.get('antagonists'):
                        bad = data['antagonists'][:5]
                        statements.append((
                            "UPDATE care SET bad_companions = CASE WHEN bad_companions IS NULL OR bad_companions = '' OR bad_companions = '[]' THEN ? ELSE bad_companions END WHERE plant_id = ?",
                            [json.dumps(bad), pid]
                        ))

                    # Propagation → proper column
                    if data.get('propagation'):
                        methods = [m.strip() for m in data['propagation'].split(',')]
                        statements.append((
                            "UPDATE care SET propagation_methods = CASE WHEN propagation_methods IS NULL OR propagation_methods = '' OR propagation_methods = '[]' THEN ? ELSE propagation_methods END WHERE plant_id = ?",
                            [json.dumps(methods), pid]
                        ))
                        statements.append((
                            "UPDATE care SET propagation_detail = CASE WHEN propagation_detail IS NULL OR propagation_detail = '' THEN ? ELSE propagation_detail END WHERE plant_id = ?",
                            [data['propagation'], pid]
                        ))

                    # Edible parts
                    if data.get('edible_parts'):
                        statements.append((
                            "UPDATE care SET edible_parts = CASE WHEN edible_parts IS NULL OR edible_parts = '' THEN ? ELSE edible_parts END WHERE plant_id = ?",
                            [data['edible_parts'], pid]
                        ))

                    # Used for
                    if data.get('used_for'):
                        uses_list = [u.strip() for u in data['used_for'].split(',')]
                        statements.append((
                            "UPDATE care SET used_for = CASE WHEN used_for IS NULL OR used_for = '' OR used_for = '[]' THEN ? ELSE used_for END WHERE plant_id = ?",
                            [json.dumps(uses_list), pid]
                        ))

                    if statements:
                        turso_batch(statements)
                        enriched += 1
                        if enriched <= 10:
                            comp = data.get('companions', [])[:3]
                            print(f"  + {scientific}: companions={comp}")

                except Exception as e:
                    continue

            print(f"[Permapeople Web] Page {page_num}/{max_pages}, checked: {total_checked}, enriched: {enriched}")

        except Exception as e:
            print(f"  ! Page {page_num} error: {e}")
            time.sleep(3)
            continue

    print(f"[Permapeople Web] Done: {enriched} enriched from {total_checked} checked")
    return enriched


if __name__ == '__main__':
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    enrich_from_permapeople_web(max_pages)
