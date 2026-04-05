"""
verify_photos.py — Verify that plant photos match the correct species.

Sends each photo from plant_images to PlantNet identify API.
If identification doesn't match plant_id → flags as wrong.

Usage:
    python3 verify_photos.py                          # verify all featured
    python3 verify_photos.py --plant monstera_deliciosa  # verify one plant
    python3 verify_photos.py --dry-run                # just show what would be checked
"""
import json
import sys
import os
import time
import urllib.request
import urllib.parse
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch
from pathlib import Path

# Load API key
PLANTNET_API_KEY = ''
for line in Path(__file__).parent.joinpath('.env').read_text().splitlines():
    if line.startswith('PLANTNET_API_KEY'):
        PLANTNET_API_KEY = line.split('=', 1)[1].strip()

PLANTNET_URL = 'https://my-api.plantnet.org/v2/identify/all'


def identify_photo(image_url):
    """Send image URL to PlantNet and return top species match."""
    try:
        params = urllib.parse.urlencode({
            'images': image_url,
            'organs': 'auto',
            'include-related-images': 'false',
            'no-reject': 'false',
            'nb-results': 3,
            'lang': 'en',
            'api-key': PLANTNET_API_KEY,
        })
        url = f'{PLANTNET_URL}?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        results = data.get('results', [])
        if not results:
            return None, 0.0

        top = results[0]
        species = top.get('species', {})
        sci_name = species.get('scientificNameWithoutAuthor', '')
        score = top.get('score', 0.0)
        return sci_name, score
    except Exception as e:
        return None, 0.0


def check_match(plant_id, scientific, identified_name):
    """Check if identified species matches expected plant."""
    if not identified_name:
        return 'unknown'

    # Normalize
    expected = scientific.lower().strip()
    got = identified_name.lower().strip()

    # Exact match
    if expected == got:
        return 'match'

    # Genus match (first word)
    exp_genus = expected.split()[0]
    got_genus = got.split()[0]
    if exp_genus == got_genus:
        return 'genus_match'

    # Known synonyms (e.g. Sansevieria = Dracaena trifasciata)
    synonyms = {
        'dracaena trifasciata': ['sansevieria trifasciata', 'sansevieria'],
        'salvia rosmarinus': ['rosmarinus officinalis'],
        'epipremnum aureum': ['pothos aureus', 'scindapsus aureus'],
        'calathea orbifolia': ['goeppertia orbifolia'],
    }
    for canon, syns in synonyms.items():
        if expected == canon or expected in syns:
            if got == canon or got in syns:
                return 'synonym_match'

    return 'mismatch'


def verify_plant_photos(plant_id, dry_run=False):
    """Verify all photos for a plant. Returns (total, matched, mismatched)."""
    plant = turso_query('SELECT scientific FROM plants WHERE plant_id = ?', [plant_id])
    if not plant:
        print(f'  Plant {plant_id} not found')
        return 0, 0, 0

    scientific = plant[0]['scientific']
    photos = turso_query(
        'SELECT image_url, source, sort_order FROM plant_images WHERE plant_id = ? ORDER BY sort_order',
        [plant_id]
    )

    if not photos:
        print(f'  {plant_id}: no photos')
        return 0, 0, 0

    total = len(photos)
    matched = 0
    mismatched = 0

    print(f'  {plant_id} ({scientific}): {total} photos')

    if dry_run:
        return total, 0, 0

    for photo in photos:
        url = photo['image_url']
        sort = photo['sort_order']

        identified, score = identify_photo(url)
        time.sleep(1)  # Rate limit

        result = check_match(plant_id, scientific, identified)
        score_pct = int(score * 100)

        if result in ('match', 'synonym_match'):
            matched += 1
            print(f'    ✅ #{sort}: {identified} ({score_pct}%) — {result}')
        elif result == 'genus_match':
            matched += 1  # Close enough
            print(f'    ⚠️  #{sort}: {identified} ({score_pct}%) — genus match only')
        elif result == 'unknown':
            print(f'    ❓ #{sort}: could not identify')
        else:
            mismatched += 1
            print(f'    ❌ #{sort}: MISMATCH — expected {scientific}, got {identified} ({score_pct}%)')
            # Flag in DB
            turso_batch([(
                "UPDATE plant_images SET image_type = 'flagged' WHERE plant_id = ? AND sort_order = ?",
                [plant_id, sort]
            )])

    return total, matched, mismatched


def verify_featured(dry_run=False):
    """Verify photos for all 28 featured plants."""
    featured = turso_query('''
        SELECT DISTINCT plant_id FROM plant_images ORDER BY plant_id
    ''')

    total_photos = 0
    total_matched = 0
    total_mismatched = 0

    for row in featured:
        t, m, mm = verify_plant_photos(row['plant_id'], dry_run=dry_run)
        total_photos += t
        total_matched += m
        total_mismatched += mm

    print(f'\n=== SUMMARY ===')
    print(f'Plants checked: {len(featured)}')
    print(f'Photos total: {total_photos}')
    print(f'Matched: {total_matched}')
    print(f'Mismatched: {total_mismatched}')
    print(f'Unverified: {total_photos - total_matched - total_mismatched}')


if __name__ == '__main__':
    if '--dry-run' in sys.argv:
        verify_featured(dry_run=True)
    elif '--plant' in sys.argv:
        idx = sys.argv.index('--plant')
        pid = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else ''
        verify_plant_photos(pid)
    else:
        # Check if PlantNet is available
        try:
            urllib.request.urlopen(f'https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}', timeout=5)
        except Exception as e:
            if 'nodename' in str(e) or 'Name or service' in str(e):
                print('PlantNet API unavailable (DNS error). Try again later.')
                sys.exit(1)

        verify_featured()
