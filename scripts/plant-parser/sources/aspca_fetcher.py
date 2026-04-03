"""
ASPCA Animal Poison Control — toxicity data for plants.
Source: https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants
~1,000+ plants with toxic/non-toxic status for dogs, cats, horses.
Uses Playwright (JS-rendered pages). Polite: 2 sec delay.
"""
import json
import re
import time
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

BASE_URL = 'https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants'
DELAY = 2.0


def get_plant_links(page_obj, page_num=0):
    """Get plant links from ASPCA listing page."""
    url = BASE_URL if page_num == 0 else f'{BASE_URL}?page={page_num}'
    page_obj.goto(url, timeout=30000)
    page_obj.wait_for_timeout(3000)

    links = page_obj.query_selector_all('a[href*="toxic-and-non-toxic-plants/"]')
    results = []
    seen = set()
    for l in links:
        href = l.get_attribute('href') or ''
        name = l.inner_text().strip()
        # Filter: only plant pages (not letter pages, not pagination)
        slug = href.split('/')[-1] if href else ''
        if name and slug and len(slug) > 2 and slug not in seen and not slug.isdigit() and slug not in ('search', 'a', 'b', 'c'):
            seen.add(slug)
            results.append((name, href, slug))
    return results


def parse_plant_detail(page_obj, url):
    """Parse individual ASPCA plant page for toxicity data."""
    page_obj.goto(url, timeout=30000)
    page_obj.wait_for_timeout(2000)

    body = page_obj.inner_text('body')
    data = {}

    # Non-Toxic FIRST (check before Toxic to avoid false positives)
    nontoxic_match = re.search(r'Non-Toxic to ([^\n]+)', body)
    if nontoxic_match:
        data['nontoxic_to'] = nontoxic_match.group(1).strip()
        data['toxic_to_pets'] = False

    # Toxic to (only match lines that DON'T start with "Non-")
    toxic_lines = re.findall(r'(?<!Non-)Toxic to ([^\n]+)', body)
    if toxic_lines:
        toxic_text = toxic_lines[0].strip()
        # Remove "Toxic to" fragments that are part of "Non-Toxic to" listings
        data['toxic_to'] = toxic_text
        if 'dog' in toxic_text.lower() or 'cat' in toxic_text.lower():
            data['toxic_to_pets'] = True

    data.setdefault('toxic_to_pets', False)

    # Scientific Name
    sci_match = re.search(r'Scientific Name:\s*([^\n]+)', body)
    if sci_match:
        data['scientific'] = sci_match.group(1).strip()

    # Family
    fam_match = re.search(r'Family:\s*([^\n]+)', body)
    if fam_match:
        data['family'] = fam_match.group(1).strip()

    # Clinical Signs
    signs_match = re.search(r'Clinical Signs:\s*([^\n]+)', body)
    if signs_match:
        data['clinical_signs'] = signs_match.group(1).strip()

    # Additional Common Names
    names_match = re.search(r'Additional Common Names:\s*([^\n]+)', body)
    if names_match:
        data['common_names'] = names_match.group(1).strip()

    return data


def enrich_toxicity(max_pages=70):
    """Scrape ASPCA for toxicity data and enrich our DB."""
    from playwright.sync_api import sync_playwright

    print(f"[ASPCA] Starting toxicity enrichment, up to {max_pages} pages...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(30000)

        enriched = 0
        total_checked = 0

        for page_num in range(0, max_pages):
            try:
                plants = get_plant_links(page, page_num)
                time.sleep(DELAY)

                if not plants:
                    print(f"[ASPCA] No more plants at page {page_num}")
                    break

                for name, href, slug in plants:
                    total_checked += 1
                    try:
                        full_url = href if href.startswith('http') else f'https://www.aspca.org{href}'
                        data = parse_plant_detail(page, full_url)
                        time.sleep(DELAY)

                        if not data.get('scientific') and not data.get('toxic_to'):
                            continue

                        # Match to our DB
                        scientific = data.get('scientific', '')
                        plant_id = scientific.lower().replace(' ', '_').replace("'", '').replace('"', '') if scientific else ''

                        existing = None
                        if plant_id:
                            existing = turso_query('SELECT plant_id FROM plants WHERE plant_id = ?', [plant_id])

                        if not existing and scientific:
                            # Try partial match by genus
                            genus = scientific.split()[0] if ' ' in scientific else scientific
                            existing = turso_query('SELECT plant_id FROM plants WHERE plant_id LIKE ?', [f'{genus.lower()}%'])

                        if not existing:
                            continue

                        pid = existing[0]['plant_id']

                        statements = []

                        # Toxicity — always update (ASPCA is authoritative)
                        is_toxic_pets = 1 if data.get('toxic_to_pets') else 0
                        toxic_note = ''
                        if data.get('toxic_to'):
                            toxic_note = f"Toxic to {data['toxic_to']}."
                        elif data.get('nontoxic_to'):
                            toxic_note = f"Non-toxic to {data['nontoxic_to']}."
                        if data.get('clinical_signs'):
                            toxic_note += f" Signs: {data['clinical_signs']}"

                        # ASPCA is authoritative — overwrite if we only had empty/basic data
                        statements.append((
                            "UPDATE care SET toxic_to_pets = ?, toxicity_note = CASE WHEN toxicity_note IS NULL OR toxicity_note = '' OR toxicity_note = 'Toxic to pets and/or humans' THEN ? ELSE toxicity_note END WHERE plant_id = ?",
                            [is_toxic_pets, toxic_note[:300], pid]
                        ))

                        # Also mark non-toxic explicitly
                        if not data.get('toxic_to_pets'):
                            statements.append((
                                "UPDATE care SET toxic_to_pets = 0 WHERE plant_id = ? AND (toxic_to_pets IS NULL OR toxic_to_pets = 0)",
                                [pid]
                            ))

                        if statements:
                            turso_batch(statements)
                            enriched += 1
                            if enriched <= 10:
                                status = 'TOXIC' if data.get('toxic_to_pets') else 'SAFE'
                                print(f"  + {scientific or name}: {status} — {data.get('toxic_to', data.get('nontoxic_to', ''))}")

                    except Exception as e:
                        continue

                if (page_num + 1) % 5 == 0:
                    print(f"[ASPCA] Page {page_num+1}/{max_pages}, checked: {total_checked}, enriched: {enriched}")

            except Exception as e:
                print(f"  ! Page {page_num} error: {e}")
                time.sleep(3)
                continue

        browser.close()

    print(f"[ASPCA] Done: {enriched} enriched with toxicity data from {total_checked} checked")
    return enriched


if __name__ == '__main__':
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 70
    enrich_toxicity(max_pages)
