"""
Perenual smart check — zero wasted credits.

RULES:
1. Only plants with Perenual ID ≤ 3000 (external_ids)
2. Priority: conflicts → featured → indoor popular
3. Data → source_data only, never overwrite care
4. Compare with existing data, flag conflicts
5. 2 credits per plant (details + care guide)
6. Stop on rate limit

Usage:
    python3 perenual_smart_check.py              # run with default priority
    python3 perenual_smart_check.py --dry-run    # show what would be checked
"""
import urllib.request
import json
import time
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_query, turso_batch, store_source_data

PERENUAL_KEY = os.environ.get('PERENUAL_API_KEY', '')
MAX_FREE_ID = 3000
MAX_CREDITS = 100  # daily limit
CREDITS_PER_PLANT = 2  # details + care guide


def get_priority_list():
    """Build priority list: conflicts → featured → indoor popular. Only Perenual free tier."""
    # All plants with Perenual free tier ID
    all_perenual = turso_query("""
        SELECT ei.plant_id, ei.external_id
        FROM external_ids ei
        WHERE ei.source = 'perenual' AND CAST(ei.external_id AS INTEGER) <= ?
    """, [MAX_FREE_ID])

    perenual_map = {r['plant_id']: int(r['external_id']) for r in all_perenual}
    print(f"Perenual free tier plants: {len(perenual_map)}", flush=True)

    # Already checked today (or ever with perenual_smart source)
    already = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'perenual_smart'")
    already_set = set(r['plant_id'] for r in already)

    # Filter out already checked
    available = {pid: eid for pid, eid in perenual_map.items() if pid not in already_set}
    print(f"Not yet smart-checked: {len(available)}", flush=True)

    # Priority 1: Conflicts
    conflicts = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'conflict'")
    conflict_ids = [r['plant_id'] for r in conflicts if r['plant_id'] in available]

    # Priority 2: Featured
    with open('/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart') as f:
        text = f.read()
    featured_ids = [pid for pid in re.findall(r"plantIdStr: '([^']+)'", text) if pid in available and pid not in conflict_ids]

    # Priority 3: Indoor with photos
    indoor = turso_query("""
        SELECT DISTINCT p.plant_id FROM plants p
        JOIN plant_images pi ON p.plant_id = pi.plant_id
        WHERE p.indoor = 1 AND p.description IS NOT NULL
    """)
    indoor_ids = [r['plant_id'] for r in indoor if r['plant_id'] in available and r['plant_id'] not in conflict_ids and r['plant_id'] not in featured_ids]

    # Priority 4: Rest
    rest = [pid for pid in available if pid not in conflict_ids and pid not in featured_ids and pid not in indoor_ids]

    priority = []
    for pid in conflict_ids:
        priority.append((pid, available[pid], 'conflict'))
    for pid in featured_ids:
        priority.append((pid, available[pid], 'featured'))
    for pid in indoor_ids:
        priority.append((pid, available[pid], 'indoor'))
    for pid in rest:
        priority.append((pid, available[pid], 'other'))

    print(f"Priority: {len(conflict_ids)} conflicts, {len(featured_ids)} featured, {len(indoor_ids)} indoor, {len(rest)} other", flush=True)
    return priority


def fetch_perenual(plant_id, perenual_id):
    """Fetch details + care guide from Perenual. Returns dict of fields or None."""
    fields = {}

    # Details
    url = f"https://perenual.com/api/species/details/{perenual_id}?key={PERENUAL_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        # Always save common_name if available
        if data.get('common_name'):
            fields['common_name'] = data['common_name']
        if data.get('family'):
            fields['family'] = data['family']
        sunlight = data.get('sunlight', [])
        if sunlight:
            fields['sunlight'] = ', '.join(sunlight) if isinstance(sunlight, list) else str(sunlight)
        if data.get('watering'):
            fields['watering'] = str(data['watering'])
        if data.get('poisonous_to_pets') is not None:
            fields['toxic_to_pets'] = str(int(data['poisonous_to_pets']))
        if data.get('poisonous_to_humans') is not None:
            fields['toxic_to_humans'] = str(int(data['poisonous_to_humans']))
        if data.get('poisonous_to_pets_symptoms'):
            fields['toxicity_symptoms_pets'] = str(data['poisonous_to_pets_symptoms'])
        if data.get('poisonous_to_humans_symptoms'):
            fields['toxicity_symptoms_humans'] = str(data['poisonous_to_humans_symptoms'])
        if data.get('drought_tolerant') is not None:
            fields['drought_tolerant'] = str(data['drought_tolerant'])
        if data.get('salt_tolerant') is not None:
            fields['salt_tolerant'] = str(data['salt_tolerant'])
        if data.get('indoor') is not None:
            fields['indoor'] = str(data['indoor'])
        if data.get('care_level'):
            fields['care_level'] = str(data['care_level'])
        if data.get('flowers') is not None:
            fields['flowers'] = str(data['flowers'])
        if data.get('fruits') is not None:
            fields['fruits'] = str(data['fruits'])
        if data.get('leaf') is not None:
            fields['leaf'] = str(data['leaf'])
        if data.get('growth_rate'):
            fields['growth_rate'] = str(data['growth_rate'])
        if data.get('type'):
            fields['type'] = str(data['type'])
        if data.get('cycle'):
            fields['cycle'] = str(data['cycle'])
        if data.get('propagation'):
            fields['propagation'] = ', '.join(data['propagation']) if isinstance(data['propagation'], list) else str(data['propagation'])
        if data.get('hardiness', {}).get('min'):
            fields['hardiness_min'] = data['hardiness']['min']
        if data.get('dimension'):
            fields['dimension'] = data['dimension']
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None  # rate limited
        return {}
    except:
        return {}

    time.sleep(1)

    # Care guide
    url2 = f"https://perenual.com/api/species-care-guide-list?key={PERENUAL_KEY}&species_id={perenual_id}"
    try:
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'PlantApp/1.0'})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            care_data = json.loads(resp2.read().decode())
        for section in care_data.get('data', []):
            for s in section.get('section', []):
                stype = s.get('type', '').lower()
                sdesc = s.get('description', '')
                if sdesc and 'Upgrade' not in sdesc:
                    if stype == 'watering':
                        fields['watering_guide'] = sdesc[:500]
                    elif stype == 'sunlight':
                        fields['sunlight_guide'] = sdesc[:500]
                    elif stype == 'pruning':
                        fields['pruning_guide'] = sdesc[:500]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None
    except:
        pass

    return fields


def compare_with_existing(plant_id, perenual_data):
    """Compare Perenual data with existing care data. Return list of (field, status, detail)."""
    care = turso_query("SELECT * FROM care WHERE plant_id = ?", [plant_id])
    if not care:
        return [('no_care', 'missing', '')]
    c = care[0]

    results = []

    # Light
    per_sun = (perenual_data.get('sunlight') or '').lower()
    our_light = (c.get('light_preferred') or '').lower()
    if per_sun and 'upgrade' not in per_sun:
        per_cat = 'full sun' if 'full sun' in per_sun else ('part sun' if 'part shade' in per_sun or 'part sun' in per_sun else 'unknown')
        our_cat = 'full sun' if 'full sun' in our_light else ('part sun' if 'part sun' in our_light else our_light)
        if per_cat == our_cat or per_cat == 'unknown':
            results.append(('light', 'match', f'{per_cat}={our_cat}'))
        else:
            results.append(('light', 'conflict', f'perenual={per_cat}, ours={our_cat}'))

    # Watering
    per_water = (perenual_data.get('watering') or '').lower()
    our_demand = (c.get('water_demand') or '').lower()
    if per_water and 'upgrade' not in per_water:
        results.append(('watering', 'info', f'perenual={per_water}, ours={our_demand}'))

    # Toxicity — pets
    per_toxic_pets = perenual_data.get('toxic_to_pets')
    our_toxic_pets = c.get('toxic_to_pets')
    if per_toxic_pets is not None:
        if str(per_toxic_pets) == str(our_toxic_pets or 0):
            results.append(('toxicity_pets', 'match', f'both={per_toxic_pets}'))
        else:
            results.append(('toxicity_pets', 'conflict', f'perenual={per_toxic_pets}, ours={our_toxic_pets}'))

    # Toxicity — humans
    per_toxic_humans = perenual_data.get('toxic_to_humans')
    our_toxic_humans = c.get('toxic_to_humans')
    if per_toxic_humans is not None:
        if str(per_toxic_humans) == str(our_toxic_humans or 0):
            results.append(('toxicity_humans', 'match', f'both={per_toxic_humans}'))
        else:
            results.append(('toxicity_humans', 'conflict', f'perenual={per_toxic_humans}, ours={our_toxic_humans}'))

    # Care level vs difficulty
    per_care = perenual_data.get('care_level', '')
    our_diff = c.get('difficulty', '')
    if per_care:
        results.append(('difficulty', 'info', f'perenual={per_care}, ours={our_diff}'))

    # Cycle vs lifecycle
    per_cycle = perenual_data.get('cycle', '')
    our_lifecycle = c.get('lifecycle', '')
    if per_cycle:
        results.append(('lifecycle', 'info', f'perenual={per_cycle}, ours={our_lifecycle}'))

    return results


def run(dry_run=False):
    priority = get_priority_list()
    max_plants = MAX_CREDITS // CREDITS_PER_PLANT

    to_check = priority[:max_plants]
    print(f"\nWill check {len(to_check)} plants (max {max_plants} from {MAX_CREDITS} credits)", flush=True)

    if dry_run:
        for pid, eid, reason in to_check:
            print(f"  {pid:35s} | id={eid:>4} | {reason}", flush=True)
        return

    credits_used = 0
    stats = {'match': 0, 'conflict': 0, 'info': 0, 'error': 0}

    for i, (pid, eid, reason) in enumerate(to_check):
        data = fetch_perenual(pid, eid)

        if data is None:
            print(f"  [{i+1}] Rate limited. Stopping.", flush=True)
            break

        if data is None:
            print(f"  [{i+1}] Rate limited. Stopping.", flush=True)
            break
        if not data:
            # Still count as checked even if empty
            pass

        credits_used += CREDITS_PER_PLANT

        # Store in source_data
        store_source_data(pid, 'perenual_smart', data)

        # Compare
        comparisons = compare_with_existing(pid, data)
        has_conflict = any(s == 'conflict' for _, s, _ in comparisons)

        if has_conflict:
            stats['conflict'] += 1
            comp_str = ' | '.join(f'{f}:{s}' for f, s, d in comparisons)
            print(f"  [{i+1}] ⚠️  {pid:35s} ({reason}) | {comp_str}", flush=True)
        else:
            stats['match'] += 1

        # Flag conflicts in source_data
        for field, status, detail in comparisons:
            if status == 'conflict':
                store_source_data(pid, 'conflict', {f'perenual_vs_{field}': detail})

        time.sleep(1)

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(to_check)}] credits={credits_used} match={stats['match']} conflict={stats['conflict']}", flush=True)

    print(f"\nDone: credits={credits_used}, match={stats['match']}, conflict={stats['conflict']}, error={stats['error']}", flush=True)


if __name__ == '__main__':
    if '--dry-run' in sys.argv:
        run(dry_run=True)
    else:
        run()
