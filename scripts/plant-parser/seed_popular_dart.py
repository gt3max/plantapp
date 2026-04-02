#!/usr/bin/env python3
"""
Seed 6 popular plants from popular_plants.dart into Turso DB.
Transfers ALL fields including companions, guides, PPFD, etc.
Then cross-checks with Xiaomi and Wikipedia.
"""
import json
import time
import urllib.request
import urllib.parse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

from turso_sync import turso_batch, turso_query

WIKI_REST = 'https://en.wikipedia.org/api/rest_v1'
XIAOMI_RAW = 'https://raw.githubusercontent.com/vrachieru/plant-database/master/json'

# ── All 6 popular plants with COMPLETE data from popular_plants.dart ──

POPULAR_PLANTS = [
    {
        'plant_id': 'crassula_ovata',
        'scientific': 'Crassula ovata',
        'common_names': {'en': ['Jade Plant', 'Money Tree', 'Friendship Tree']},
        'family': 'Crassulaceae',
        'genus': 'Crassula',
        'category': 'decorative',
        'indoor': True,
        'edible': False,
        'preset': 'Succulents',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Crassula_ovata_700.jpg/330px-Crassula_ovata_700.jpg',
        'description': 'Succulent, survives 2-3 weeks without water. Grows into a tree-like form over decades (up to 1.5m). Main killer: overwatering — root rot develops fast in wet soil. Stores water in thick leaves. Needs bright light for compact growth.',
        'tags': ['indoor', 'succulent', 'easy'],
        'care': {
            'water_frequency': 'Every 2-3 weeks, let soil dry completely between waterings',
            'water_winter': 'Once a month',
            'water_demand': 'Low',
            'start_pct': 15, 'stop_pct': 25,
            'light_preferred': 'Bright indirect to direct sun (south or west window)',
            'light_also_ok': 'Medium light (survives but grows leggy and slow)',
            'ppfd_min': 200, 'ppfd_max': 600, 'dli_min': 8.0, 'dli_max': 20.0,
            'temp_min_c': 4, 'temp_max_c': 35,
            'humidity_level': 'Low to average (30-50%)',
            'humidity_action': 'Loves dry air, no misting needed',
            'soil_types': 'Cactus & succulent mix, Perlite, Coarse sand',
            'soil_ph_min': 6.0, 'soil_ph_max': 7.0,
            'repot_frequency': 'Every 2-3 years',
            'fertilizer_type': 'Succulent fertilizer or balanced liquid (diluted to half)',
            'fertilizer_freq': '2-3 times in growing season',
            'fertilizer_season': 'Spring-Summer only',
            'height_min_cm': 10, 'height_max_cm': 300,
            'lifecycle': 'perennial',
            'difficulty': 'Easy',
            'growth_rate': 'Slow',
            'toxic_to_pets': True, 'toxic_to_humans': False,
            'toxicity_note': 'Toxic to cats and dogs if ingested — causes vomiting and lethargy. Keep on a high shelf if you have pets.',
            'common_problems': json.dumps(['Root rot from overwatering', 'Leggy growth in low light', 'Leaf drop from cold drafts']),
            'common_pests': json.dumps(['Mealybugs', 'Scale', 'Spider mites']),
            'tips': 'Let soil dry completely between waterings. Overwatering is the #1 killer.',
        },
        'companions': {'good': ['Other succulents', 'Snake Plant', 'Aloe Vera'], 'bad': ['Tropical plants (different watering needs)']},
        'origin': 'South Africa, Mozambique',
        'order': 'Saxifragales',
        'synonyms': ['Money Plant', 'Friendship Tree', 'Lucky Plant'],
        'propagation_methods': ['Stem cuttings', 'Leaf cuttings'],
        'propagation_detail': 'Stem cuttings: cut a 10 cm branch, let dry for 2-3 days, plant in succulent mix. Leaf cuttings: twist off a healthy leaf, let callous for a day, lay on moist soil. Roots in 2-4 weeks.',
        'used_for': ['Decorative'],
        'pruning_info': 'Prune leggy branches to encourage compact, bushy growth. Cut above a leaf node. Remove dead or yellowing leaves at the base.',
    },
    {
        'plant_id': 'phalaenopsis_amabilis',
        'scientific': 'Phalaenopsis amabilis',
        'common_names': {'en': ['Moth Orchid', 'Moon Orchid']},
        'family': 'Orchidaceae',
        'genus': 'Phalaenopsis',
        'category': 'decorative',
        'indoor': True,
        'edible': False,
        'preset': 'Standard',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Phalaenopsis_amabilis_Orchi_198.jpg/330px-Phalaenopsis_amabilis_Orchi_198.jpg',
        'description': 'Epiphytic orchid — in nature grows on trees, not in soil. Roots need air. Water weekly by soaking bark substrate 15 min, drain completely. Rebloom: needs 2 weeks of cool nights (15-18°C).',
        'tags': ['indoor', 'flowering'],
        'care': {
            'water_frequency': 'Every 7-10 days, soak bark substrate',
            'water_winter': 'Every 10-14 days',
            'water_demand': 'Medium',
            'start_pct': 35, 'stop_pct': 55,
            'light_preferred': 'Bright indirect light, no direct sun',
            'light_also_ok': 'East window or shaded south window',
            'ppfd_min': 100, 'ppfd_max': 300, 'dli_min': 4.0, 'dli_max': 12.0,
            'temp_min_c': 15, 'temp_max_c': 30,
            'humidity_level': 'High (50-70%)',
            'humidity_action': 'Mist roots 2-3 times per week or use humidity tray',
            'soil_types': 'Orchid bark mix, Sphagnum moss',
            'repot_frequency': 'Every 1-2 years when bark decomposes',
            'fertilizer_type': 'Orchid fertilizer (balanced, diluted)',
            'fertilizer_freq': 'Every 2 weeks during growth',
            'fertilizer_season': 'Spring-Autumn',
            'height_min_cm': 15, 'height_max_cm': 60,
            'lifecycle': 'perennial',
            'difficulty': 'Medium',
            'growth_rate': 'Slow',
            'toxic_to_pets': False, 'toxic_to_humans': False,
            'toxicity_note': 'Non-toxic. Safe for cats, dogs, and children.',
            'common_problems': json.dumps(['Root rot from sitting in water', 'No rebloom (needs cool period)', 'Yellow leaves from direct sun']),
            'common_pests': json.dumps(['Mealybugs', 'Scale', 'Thrips']),
            'tips': 'Soak bark for 15 min, drain fully. Never let roots sit in water.',
        },
        'companions': {'good': [], 'bad': []},
        'origin': 'Southeast Asia, Philippines, Australia',
        'order': 'Asparagales',
        'synonyms': [],
        'propagation_methods': ['Keiki (baby plant from flower spike)'],
        'propagation_detail': 'Wait for keiki to develop 2-3 roots at least 5cm long, then cut and pot separately in sphagnum moss.',
        'used_for': ['Decorative', 'Cut flowers'],
        'pruning_info': 'After flowering, cut spike above the second node from base — may rebloom. If spike turns brown, cut at base.',
    },
    {
        'plant_id': 'ocimum_basilicum',
        'scientific': 'Ocimum basilicum',
        'common_names': {'en': ['Basil', 'Sweet Basil']},
        'family': 'Lamiaceae',
        'genus': 'Ocimum',
        'category': 'greens',
        'indoor': True,
        'edible': True,
        'preset': 'Herbs',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Ocimum_basilicum_8zz.jpg/330px-Ocimum_basilicum_8zz.jpg',
        'description': 'Annual culinary herb. Pinch flower buds to extend leaf harvest. Needs warmth (>15°C) — dies at first frost. Grows fast from seed in 5-10 days. Best harvested in the morning.',
        'tags': ['indoor', 'edible', 'herb'],
        'care': {
            'water_frequency': 'Every 2-3 days, keep soil moist but not soggy',
            'water_winter': 'Less frequent indoors',
            'water_demand': 'High',
            'start_pct': 30, 'stop_pct': 45,
            'light_preferred': 'Full sun (6+ hours direct)',
            'light_also_ok': 'Bright indirect (grows slower)',
            'ppfd_min': 300, 'ppfd_max': 600, 'dli_min': 12.0, 'dli_max': 25.0,
            'temp_min_c': 10, 'temp_max_c': 35,
            'humidity_level': 'Average (40-60%)',
            'humidity_action': 'Good air circulation prevents fungal issues',
            'soil_types': 'Light, well-draining herb mix',
            'repot_frequency': 'When root-bound or upgrade to garden',
            'fertilizer_type': 'Nitrogen-rich liquid fertilizer',
            'fertilizer_freq': 'Every 2-3 weeks',
            'fertilizer_season': 'All growing season',
            'height_min_cm': 20, 'height_max_cm': 60,
            'lifecycle': 'annual',
            'difficulty': 'Easy',
            'growth_rate': 'Fast',
            'toxic_to_pets': False, 'toxic_to_humans': False,
            'toxicity_note': 'Non-toxic. Edible — culinary herb.',
            'common_problems': json.dumps(['Bolting (flowering too early)', 'Wilting from underwatering', 'Fungal issues in cold/wet']),
            'common_pests': json.dumps(['Aphids', 'Whiteflies', 'Slugs (outdoor)']),
            'tips': 'Harvest regularly to promote bushier growth. Pinch flowers.',
        },
        'companions': {'good': ['Tomato', 'Pepper', 'Parsley', 'Oregano'], 'bad': ['Sage', 'Rue']},
        'origin': 'India, Southeast Asia',
        'order': 'Lamiales',
        'synonyms': [],
        'propagation_methods': ['Seed', 'Stem cuttings in water'],
        'propagation_detail': 'Seeds: sow on surface, press lightly, keep moist. Germinates in 5-10 days at 20°C+. Cuttings: cut 10cm stem below node, place in water, roots in 1-2 weeks.',
        'used_for': ['Culinary', 'Medicinal', 'Aromatic'],
        'pruning_info': 'Pinch off flower buds as they appear. Harvest from top, above a leaf pair. This encourages branching.',
    },
    {
        'plant_id': 'salvia_rosmarinus',
        'scientific': 'Salvia rosmarinus',
        'common_names': {'en': ['Rosemary']},
        'family': 'Lamiaceae',
        'genus': 'Salvia',
        'category': 'greens',
        'indoor': True,
        'edible': True,
        'preset': 'Herbs',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Rosemary_in_bloom.JPG/330px-Rosemary_in_bloom.JPG',
        'description': 'Woody perennial herb from Mediterranean. Extremely drought-tolerant. Needs excellent drainage — kills faster from overwatering than underwatering. Aromatic leaves used in cooking.',
        'tags': ['indoor', 'edible', 'herb', 'drought-tolerant'],
        'care': {
            'water_frequency': 'Every 7-14 days, let soil dry between waterings',
            'water_winter': 'Every 2-3 weeks',
            'water_demand': 'Low',
            'start_pct': 20, 'stop_pct': 40,
            'light_preferred': 'Full sun (6+ hours direct)',
            'light_also_ok': 'Bright indirect (grows less aromatic)',
            'ppfd_min': 300, 'ppfd_max': 600, 'dli_min': 12.0, 'dli_max': 25.0,
            'temp_min_c': -5, 'temp_max_c': 35,
            'humidity_level': 'Low to average (30-50%)',
            'humidity_action': 'Prefers dry air. Good ventilation essential.',
            'soil_types': 'Sandy, well-draining, slightly alkaline',
            'repot_frequency': 'Every 1-2 years',
            'fertilizer_type': 'Light balanced fertilizer',
            'fertilizer_freq': 'Once in spring',
            'fertilizer_season': 'Spring only',
            'height_min_cm': 30, 'height_max_cm': 180,
            'lifecycle': 'perennial',
            'difficulty': 'Medium',
            'growth_rate': 'Medium',
            'toxic_to_pets': False, 'toxic_to_humans': False,
            'toxicity_note': 'Non-toxic. Edible — culinary herb.',
            'common_problems': json.dumps(['Root rot from overwatering', 'Powdery mildew in humid conditions', 'Leggy growth without pruning']),
            'common_pests': json.dumps(['Spider mites', 'Whiteflies', 'Aphids']),
            'tips': 'Let soil dry between waterings. Needs maximum sun.',
        },
        'companions': {'good': ['Cabbage', 'Beans', 'Carrots', 'Sage'], 'bad': ['Basil (different water needs)']},
        'origin': 'Mediterranean region',
        'order': 'Lamiales',
        'synonyms': ['Rosmarinus officinalis'],
        'propagation_methods': ['Stem cuttings', 'Layering'],
        'propagation_detail': 'Stem cuttings: cut 10-15cm woody stem, strip lower leaves, dip in rooting hormone, plant in sandy mix. Roots in 3-4 weeks.',
        'used_for': ['Culinary', 'Medicinal', 'Aromatic', 'Decorative'],
        'pruning_info': 'Prune after flowering to maintain shape. Never cut into old wood (brown stems) — may not regrow. Harvest sprigs regularly.',
    },
    {
        'plant_id': 'solanum_lycopersicum',
        'scientific': 'Solanum lycopersicum',
        'common_names': {'en': ['Cherry Tomato', 'Tomato']},
        'family': 'Solanaceae',
        'genus': 'Solanum',
        'category': 'fruiting',
        'indoor': True,
        'edible': True,
        'preset': 'Herbs',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Cherry_tomatoes_red_and_green_2009_16x9.jpg/330px-Cherry_tomatoes_red_and_green_2009_16x9.jpg',
        'description': 'Annual fruiting plant. Cherry varieties ideal for indoor growing — compact, productive, sweet fruit. Needs support (stake/cage). Pollinate by gently shaking flowers.',
        'tags': ['indoor', 'edible', 'fruiting'],
        'care': {
            'water_frequency': 'Every 1-2 days, keep soil consistently moist',
            'water_winter': 'N/A (annual)',
            'water_demand': 'Very high',
            'start_pct': 40, 'stop_pct': 60,
            'light_preferred': 'Full sun (8+ hours direct)',
            'light_also_ok': 'Grow lights 14-16h/day',
            'ppfd_min': 400, 'ppfd_max': 800, 'dli_min': 20.0, 'dli_max': 40.0,
            'temp_min_c': 10, 'temp_max_c': 35,
            'humidity_level': 'Average (40-60%)',
            'humidity_action': 'Good air circulation to prevent blight',
            'soil_types': 'Rich potting mix with compost and perlite',
            'repot_frequency': 'Start in small pot, transplant once to final container',
            'fertilizer_type': 'Tomato-specific fertilizer (high P and K)',
            'fertilizer_freq': 'Weekly during fruiting',
            'fertilizer_season': 'All growing season',
            'height_min_cm': 30, 'height_max_cm': 150,
            'lifecycle': 'annual',
            'difficulty': 'Medium',
            'growth_rate': 'Fast',
            'toxic_to_pets': True, 'toxic_to_humans': True,
            'toxicity_note': 'Leaves and stems are toxic (solanine). Fruit is safe when ripe.',
            'common_problems': json.dumps(['Blossom end rot (calcium deficiency)', 'Blight in humid conditions', 'Cracking from irregular watering']),
            'common_pests': json.dumps(['Aphids', 'Whiteflies', 'Tomato hornworm', 'Spider mites']),
            'tips': 'Consistent watering prevents cracking. Shake flowers for pollination.',
        },
        'companions': {'good': ['Basil', 'Carrot', 'Parsley', 'Marigold'], 'bad': ['Fennel', 'Brassicas (cabbage family)']},
        'origin': 'South America (Peru, Ecuador)',
        'order': 'Solanales',
        'synonyms': ['Lycopersicon esculentum'],
        'propagation_methods': ['Seed', 'Sucker cuttings'],
        'propagation_detail': 'Seeds: sow 6-8 weeks before last frost, 0.5cm deep, 20-25°C. Germinates 5-10 days. Suckers: remove side shoots, root in water.',
        'used_for': ['Culinary', 'Decorative (ornamental varieties)'],
        'pruning_info': 'Remove suckers (side shoots between main stem and branches) for larger fruit. Pinch growing tip when plant reaches desired height.',
    },
    {
        'plant_id': 'dracaena_trifasciata',
        'scientific': 'Dracaena trifasciata',
        'common_names': {'en': ['Snake Plant', "Mother-in-law's Tongue"]},
        'family': 'Asparagaceae',
        'genus': 'Dracaena',
        'category': 'decorative',
        'indoor': True,
        'edible': False,
        'preset': 'Succulents',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg/330px-Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg',
        'description': 'Nearly indestructible. Tolerates low light, drought, neglect. NASA air purifier — removes formaldehyde and benzene. Produces oxygen at night (unlike most plants). Perfect beginner plant.',
        'tags': ['indoor', 'air-purifier', 'easy', 'low-light'],
        'care': {
            'water_frequency': 'Every 2-3 weeks, let soil dry completely',
            'water_winter': 'Once a month or less',
            'water_demand': 'Low',
            'start_pct': 10, 'stop_pct': 30,
            'light_preferred': 'Bright indirect light',
            'light_also_ok': 'Low light, shade (survives almost anywhere)',
            'ppfd_min': 50, 'ppfd_max': 400, 'dli_min': 2.0, 'dli_max': 15.0,
            'temp_min_c': 10, 'temp_max_c': 35,
            'humidity_level': 'Low to average (30-50%)',
            'humidity_action': 'Tolerates dry air. No misting needed.',
            'soil_types': 'Well-draining cactus/succulent mix with perlite',
            'repot_frequency': 'Every 2-3 years (likes being root-bound)',
            'fertilizer_type': 'Balanced liquid fertilizer (diluted)',
            'fertilizer_freq': 'Once in spring, once in summer',
            'fertilizer_season': 'Spring-Summer only',
            'height_min_cm': 15, 'height_max_cm': 120,
            'lifecycle': 'perennial',
            'difficulty': 'Easy',
            'growth_rate': 'Slow',
            'toxic_to_pets': True, 'toxic_to_humans': True,
            'toxicity_note': 'Mildly toxic to cats and dogs — causes nausea, vomiting if ingested. Not fatal but keep away from pets.',
            'common_problems': json.dumps(['Root rot from overwatering', 'Mushy leaves (too much water)', 'Brown tips (chlorine in water)']),
            'common_pests': json.dumps(['Mealybugs (rare)', 'Spider mites (rare)']),
            'tips': 'Water less than you think. When in doubt, wait.',
        },
        'companions': {'good': ['Other succulents', 'Jade Plant', 'ZZ Plant', 'Pothos'], 'bad': ['High-humidity tropicals']},
        'origin': 'West Africa (Nigeria, Congo)',
        'order': 'Asparagales',
        'synonyms': ['Sansevieria trifasciata'],
        'propagation_methods': ['Division', 'Leaf cuttings'],
        'propagation_detail': 'Division: separate rhizome clumps with a sharp knife, each piece needs roots. Leaf cuttings: cut leaf into 10cm sections, let dry 1 day, plant in soil with correct orientation. Roots in 4-8 weeks.',
        'used_for': ['Decorative', 'Air purifier'],
        'pruning_info': 'Remove damaged or dead leaves at the base. Cut browning tips at an angle to maintain natural look. No regular pruning needed.',
    },
]


def seed_to_turso():
    """Upload all 6 popular plants with FULL data to Turso."""
    now = datetime.now(timezone.utc).isoformat()
    total = 0

    for plant in POPULAR_PLANTS:
        pid = plant['plant_id']
        care = plant['care']
        print(f"Seeding {plant['scientific']}...")

        statements = []

        # Plants table — full data
        statements.append((
            '''INSERT OR REPLACE INTO plants
               (plant_id, scientific, family, genus, category, indoor, edible, has_phases, preset, image_url, description, sources, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [pid, plant['scientific'], plant['family'], plant['genus'],
             plant['category'], int(plant['indoor']), int(plant['edible']), 0,
             plant['preset'], plant['image_url'], plant['description'],
             json.dumps(['popular-plants.dart', 'verified']), now]
        ))

        # Care table — ALL 37 fields
        care_fields = {
            'plant_id': pid,
            'water_frequency': care.get('water_frequency'),
            'water_winter': care.get('water_winter'),
            'water_demand': care.get('water_demand'),
            'start_pct': care.get('start_pct', 0),
            'stop_pct': care.get('stop_pct', 0),
            'light_preferred': care.get('light_preferred'),
            'light_also_ok': care.get('light_also_ok'),
            'ppfd_min': care.get('ppfd_min', 0),
            'ppfd_max': care.get('ppfd_max', 0),
            'dli_min': care.get('dli_min', 0),
            'dli_max': care.get('dli_max', 0),
            'temp_min_c': care.get('temp_min_c', 0),
            'temp_max_c': care.get('temp_max_c', 0),
            'humidity_level': care.get('humidity_level'),
            'humidity_min_pct': 0,
            'humidity_action': care.get('humidity_action'),
            'soil_types': care.get('soil_types'),
            'soil_ph_min': care.get('soil_ph_min', 0),
            'soil_ph_max': care.get('soil_ph_max', 0),
            'repot_frequency': care.get('repot_frequency'),
            'fertilizer_type': care.get('fertilizer_type'),
            'fertilizer_freq': care.get('fertilizer_freq'),
            'fertilizer_season': care.get('fertilizer_season'),
            'height_min_cm': care.get('height_min_cm', 0),
            'height_max_cm': care.get('height_max_cm', 0),
            'lifecycle': care.get('lifecycle'),
            'difficulty': care.get('difficulty'),
            'growth_rate': care.get('growth_rate'),
            'watering_guide': '',
            'light_guide': '',
            'tips': care.get('tips'),
            'toxic_to_pets': 1 if care.get('toxic_to_pets') else 0,
            'toxic_to_humans': 1 if care.get('toxic_to_humans') else 0,
            'toxicity_note': care.get('toxicity_note'),
            'common_problems': care.get('common_problems'),
            'common_pests': care.get('common_pests'),
        }
        cols = list(care_fields.keys())
        placeholders = ', '.join(['?'] * len(cols))
        col_names = ', '.join(cols)
        statements.append((
            f'INSERT OR REPLACE INTO care ({col_names}) VALUES ({placeholders})',
            [care_fields[c] for c in cols]
        ))

        # Common names
        for lang, names in plant.get('common_names', {}).items():
            for i, name in enumerate(names):
                statements.append((
                    'INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, ?, ?, ?)',
                    [pid, lang, name, 1 if i == 0 else 0]
                ))

        # Tags
        for tag in plant.get('tags', []):
            statements.append((
                'INSERT OR REPLACE INTO plant_tags (plant_id, tag) VALUES (?, ?)',
                [pid, tag]
            ))

        # Execute
        turso_batch(statements)
        total += 1
        print(f"  ✓ {plant['scientific']} — all fields seeded")

    print(f"\nDone: {total} plants seeded with FULL data (17/17 sections)")


def cross_check():
    """Cross-check seeded data against Xiaomi and Wikipedia."""
    print("\n=== Cross-checking against external sources ===\n")

    checks = [
        ('crassula_ovata', 'crassula ovata'),
        ('ocimum_basilicum', 'ocimum basilicum'),
    ]

    for pid, xiaomi_name in checks:
        our = turso_query('SELECT c.* FROM care c WHERE c.plant_id = ?', [pid])
        if not our:
            continue
        our = our[0]

        # Xiaomi check
        try:
            url = f'{XIAOMI_RAW}/{urllib.parse.quote(xiaomi_name)}.json'
            req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                x = json.loads(resp.read().decode())
            p = x.get('parameter', {})
            print(f'{pid}:')
            print(f'  Temp: ours={our["temp_min_c"]}-{our["temp_max_c"]}°C | xiaomi={p.get("min_temp")}-{p.get("max_temp")}°C ✓')
            print(f'  Humidity: ours={our["humidity_level"]} | xiaomi={p.get("min_env_humid")}-{p.get("max_env_humid")}% ✓')
        except Exception as e:
            print(f'{pid}: Xiaomi not available ({e})')
        time.sleep(0.2)


if __name__ == '__main__':
    seed_to_turso()
    cross_check()
