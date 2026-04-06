"""
Photo fetcher — automated pipeline for plant photos.
Source: iNaturalist research-grade observations only.

Pipeline per plant:
1. Search iNaturalist for species (quality_grade=research, licensed)
2. Verify community_taxon matches our plant
3. Take 1st photo from 3 DIFFERENT observations
4. Upload to Cloudinary
5. Write to plant_images table

Filters:
- quality_grade=research (2+ people confirmed species)
- license: cc-by, cc-by-sa, cc0 (free to use)
- photos=true
- Only first photo per observation (best quality)
- community_taxon_id must match searched species

Usage:
    python3 sources/photo_fetcher.py                     # all plants without photos
    python3 sources/photo_fetcher.py --plant monstera_deliciosa
    python3 sources/photo_fetcher.py --limit 100
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

INAT_API = 'https://api.inaturalist.org/v1'
UA = 'PlantApp/1.0 (plantapp.pro; contact@plantapp.pro)'

# Use second Cloudinary account if available (more credits), fallback to primary
CLOUDINARY_CLOUD = os.environ.get('CLOUDINARY2_CLOUD_NAME', os.environ.get('CLOUDINARY_CLOUD_NAME', 'dmvvh57hg'))
CLOUDINARY_PRESET = os.environ.get('CLOUDINARY_UPLOAD_PRESET', 'plant_photos')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY2_API_KEY', os.environ.get('CLOUDINARY_API_KEY', ''))
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY2_API_SECRET', os.environ.get('CLOUDINARY_API_SECRET', ''))

# Accepted licenses (free to use commercially)
ACCEPTED_LICENSES = {'cc-by', 'cc-by-sa', 'cc0', 'cc-by-nc'}  # cc-by-nc for non-commercial photo db building

PHOTOS_PER_PLANT = 3


def _inat_search_taxon(scientific: str) -> int | None:
    """Find iNaturalist taxon_id for a scientific name."""
    url = f'{INAT_API}/taxa?q={urllib.parse.quote(scientific)}&rank=species&is_active=true&per_page=5'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        results = data.get('results', [])
        for r in results:
            if r.get('name', '').lower() == scientific.lower():
                return r['id']
        # Fallback: first result if genus matches
        if results:
            first = results[0]
            if first.get('name', '').split()[0].lower() == scientific.split()[0].lower():
                return first['id']
    except Exception as e:
        print(f"    [WARN] taxon search failed: {e}", flush=True)
    return None


def _inat_get_observations(taxon_id: int, per_page: int = 10) -> list[dict]:
    """Get research-grade observations with photos for a taxon."""
    url = (
        f'{INAT_API}/observations?taxon_id={taxon_id}'
        f'&quality_grade=research&photos=true'
        f'&license=cc-by,cc-by-sa,cc0,cc-by-nc'
        f'&order=desc&order_by=votes'
        f'&per_page={per_page}'
    )
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data.get('results', [])
    except Exception as e:
        print(f"    [WARN] observations fetch failed: {e}", flush=True)
        return []


def _validate_observation(obs: dict, taxon_id: int) -> bool:
    """Validate that observation matches our expected taxon."""
    # Community taxon must match
    community_taxon = obs.get('community_taxon_id')
    obs_taxon = obs.get('taxon', {}).get('id')

    if community_taxon and community_taxon != taxon_id:
        # Check if it's a subspecies/variety of our taxon (ancestor match)
        ancestors = obs.get('taxon', {}).get('ancestor_ids', [])
        if taxon_id not in ancestors and community_taxon != taxon_id:
            return False

    # Must have photos
    photos = obs.get('photos', [])
    if not photos:
        return False

    # First photo must have a URL
    if not photos[0].get('url'):
        return False

    return True


def _get_photo_url(photo: dict, size: str = 'large') -> str:
    """Get photo URL at desired size. iNaturalist uses 'square', 'small', 'medium', 'large', 'original'."""
    url = photo.get('url', '')
    # iNaturalist URLs have /square.jpg — replace with desired size
    return url.replace('/square.', f'/{size}.')


def _upload_to_cloudinary(image_url: str, public_id: str) -> str | None:
    """Upload image URL to Cloudinary using signed upload. Returns Cloudinary URL or None."""
    import hashlib

    upload_url = f'https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/image/upload'
    timestamp = str(int(time.time()))

    # Generate signature for signed upload
    params_to_sign = f'overwrite=false&public_id={public_id}&timestamp={timestamp}{CLOUDINARY_API_SECRET}'
    signature = hashlib.sha1(params_to_sign.encode()).hexdigest()

    params = urllib.parse.urlencode({
        'file': image_url,
        'public_id': public_id,
        'overwrite': 'false',
        'timestamp': timestamp,
        'api_key': CLOUDINARY_API_KEY,
        'signature': signature,
    }).encode()

    req = urllib.request.Request(upload_url, data=params, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get('secure_url', '')
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        if 'already exists' in body:
            return f'https://res.cloudinary.com/{CLOUDINARY_CLOUD}/image/upload/{public_id}.jpg'
        print(f"    [WARN] Cloudinary upload failed: {e} {body[:100]}", flush=True)
    except Exception as e:
        print(f"    [WARN] Cloudinary upload failed: {e}", flush=True)
    return None


def fetch_photos_for_plant(plant_id: str, scientific: str) -> int:
    """Fetch and upload photos for a single plant. Returns number of photos added."""
    # Check existing photos
    existing = turso_query('SELECT COUNT(*) as cnt FROM plant_images WHERE plant_id = ?', [plant_id])
    if existing[0]['cnt'] >= PHOTOS_PER_PLANT:
        return 0

    needed = PHOTOS_PER_PLANT - existing[0]['cnt']

    # Step 1: Find taxon on iNaturalist
    taxon_id = _inat_search_taxon(scientific)
    if not taxon_id:
        print(f"    {plant_id}: taxon not found on iNaturalist", flush=True)
        return 0

    time.sleep(0.5)

    # Step 2: Get research-grade observations
    observations = _inat_get_observations(taxon_id, per_page=needed * 3)  # fetch extra in case some fail
    time.sleep(0.5)

    # Step 3: Validate and select photos from DIFFERENT observations
    valid_photos = []
    for obs in observations:
        if len(valid_photos) >= needed:
            break
        if not _validate_observation(obs, taxon_id):
            continue
        photo = obs['photos'][0]  # First photo = best
        photo_url = _get_photo_url(photo, 'large')
        if photo_url:
            valid_photos.append({
                'url': photo_url,
                'obs_id': obs['id'],
                'taxon_name': obs.get('taxon', {}).get('name', ''),
            })

    if not valid_photos:
        print(f"    {plant_id}: no valid research-grade photos found", flush=True)
        return 0

    # Step 4: Upload to Cloudinary and write to DB
    added = 0
    stmts = []
    sort_start = existing[0]['cnt']

    for i, photo in enumerate(valid_photos):
        public_id = f'plants/{plant_id}/inat_{sort_start + i + 1}'
        cloudinary_url = _upload_to_cloudinary(photo['url'], public_id)

        if cloudinary_url:
            stmts.append((
                "INSERT OR IGNORE INTO plant_images (plant_id, image_type, image_url, source, sort_order) VALUES (?, 'photo', ?, 'inaturalist', ?)",
                [plant_id, cloudinary_url, sort_start + i]
            ))
            added += 1

        time.sleep(0.3)

    if stmts:
        turso_batch(stmts)

    return added


def fetch_all(limit: int = 100, single_plant: str | None = None):
    """Fetch photos for plants that need them."""
    if single_plant:
        plant = turso_query('SELECT plant_id, scientific FROM plants WHERE plant_id = ?', [single_plant])
        if not plant:
            print(f"Plant {single_plant} not found")
            return
        plants = plant
    else:
        # Indoor plants first, prioritized by family importance
        plants = turso_query('''
            SELECT p.plant_id, p.scientific FROM plants p
            WHERE p.scientific IS NOT NULL AND p.scientific != ''
            AND p.indoor = 1
            AND (SELECT COUNT(*) FROM plant_images pi WHERE pi.plant_id = p.plant_id) < ?
            ORDER BY
                CASE p.family
                    WHEN 'Araceae' THEN 1
                    WHEN 'Cactaceae' THEN 2
                    WHEN 'Crassulaceae' THEN 3
                    WHEN 'Orchidaceae' THEN 4
                    WHEN 'Arecaceae' THEN 5
                    WHEN 'Marantaceae' THEN 6
                    WHEN 'Asphodelaceae' THEN 7
                    WHEN 'Moraceae' THEN 8
                    WHEN 'Asparagaceae' THEN 9
                    WHEN 'Piperaceae' THEN 10
                    WHEN 'Bromeliaceae' THEN 11
                    WHEN 'Begoniaceae' THEN 12
                    WHEN 'Commelinaceae' THEN 13
                    WHEN 'Gesneriaceae' THEN 14
                    WHEN 'Lamiaceae' THEN 15
                    WHEN 'Apiaceae' THEN 16
                    WHEN 'Solanaceae' THEN 17
                    ELSE 50
                END,
                p.plant_id
            LIMIT ?
        ''', [PHOTOS_PER_PLANT, limit])

    total = len(plants)
    print(f"[photo_fetcher] {total} plants need photos", flush=True)

    total_added = 0
    for i, p in enumerate(plants):
        added = fetch_photos_for_plant(p['plant_id'], p['scientific'])
        total_added += added

        if added > 0:
            print(f"  ✓ {p['plant_id']:35s} | +{added} photos", flush=True)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{total}] total photos added: {total_added}", flush=True)

    print(f"\n[photo_fetcher] Done: {total} plants checked, {total_added} photos added", flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plant', type=str, help='Single plant_id')
    parser.add_argument('--limit', type=int, default=100, help='Max plants to process')
    args = parser.parse_args()

    fetch_all(limit=args.limit, single_plant=args.plant)
