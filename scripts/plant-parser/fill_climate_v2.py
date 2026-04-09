"""
Fill climate v2 — family mapping + moss defaults + origin parsing.
For 1,433 plants with lifeform but no climate.

Priority: origin (most specific) > family from DB > moss default (temperate)
Source attribution: family_climate / moss_climate_default / origin_climate

Usage:
    python3 fill_climate_v2.py              # full run
    python3 fill_climate_v2.py --dry-run    # preview
"""
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

from turso_sync import turso_query, turso_batch

# Moss families (from classify_final.py)
MOSS_FAMILIES = {
    'Pottiaceae', 'Bryaceae', 'Sphagnaceae', 'Dicranaceae', 'Brachytheciaceae',
    'Grimmiaceae', 'Orthotrichaceae', 'Fissidentaceae', 'Amblystegiaceae',
    'Hypnaceae', 'Mniaceae', 'Polytrichaceae', 'Thuidiaceae', 'Neckeraceae',
    'Sematophyllaceae', 'Leucobryaceae', 'Funariaceae', 'Bartramiaceae',
    'Hookeriaceae', 'Pilotrichaceae', 'Calymperaceae', 'Meteoriaceae',
    'Ptychomitriaceae', 'Cryphaeaceae', 'Anomodontaceae', 'Lembophyllaceae',
    'Entodontaceae', 'Plagiotheciaceae', 'Pylaisiadelphaceae', 'Fontinalaceae',
    'Racopilaceae', 'Daltoniaceae', 'Pterobryaceae', 'Hylocomiaceae',
    'Rhytidiaceae', 'Climaciaceae', 'Hedwigiaceae', 'Leskeaceae',
    'Rhabdoweisiaceae', 'Ditrichaceae', 'Seligeriaceae', 'Encalyptaceae',
    'Timmiaceae', 'Meesiaceae', 'Aulacomniaceae', 'Andreaeaceae',
    'Tetraphidaceae', 'Buxbaumiaceae', 'Archidiaceae', 'Splachnaceae',
    'Lejeuneaceae', 'Cephaloziaceae', 'Frullaniaceae', 'Porellaceae',
    'Radulaceae', 'Plagiochilaceae', 'Jungermanniaceae', 'Lophocoleaceae',
    'Scapaniaceae', 'Herbertaceae', 'Lepidoziaceae', 'Calypogeiaceae',
    'Geocalycaceae', 'Jubulaceae', 'Metzgeriaceae', 'Aneuraceae',
    'Pelliaceae', 'Pallaviciniaceae', 'Marchantiaceae', 'Ricciaceae',
    'Aytoniaceae', 'Conocephalaceae', 'Anastrophyllaceae', 'Trichocoleaceae',
    'Pseudolepicoleaceae', 'Cephaloziellaceae', 'Adelanthaceae',
    'Anthocerotaceae', 'Notothyladaceae',
    'Gymnomitriaceae', 'Leucodontaceae', 'Calliergonaceae', 'Acrobolbaceae',
    'Pylaisiaceae', 'Lophoziaceae', 'Pterigynandraceae', 'Theliaceae',
    'Fossombroniaceae', 'Solenostomataceae', 'Ptilidiaceae', 'Fabroniaceae',
    'Leucomiaceae', 'Moerckiaceae', 'Antheliaceae', 'Bruchiaceae',
    'Distichiaceae', 'Ephemeraceae', 'Harpanthaceae', 'Leptodontaceae',
    'Phyllogoniaceae', 'Stereophyllaceae', 'Blepharostomataceae',
    'Bryoxiphiaceae', 'Catoscopiaceae', 'Corsiniaceae', 'Diphysciaceae',
    'Disceliaceae', 'Dumortieraceae', 'Hygrobiellaceae', 'Hypopterygiaceae',
    'Leptostomataceae', 'Lunulariaceae', 'Myriniaceae', 'Myuriaceae',
    'Orthodontiaceae', 'Petalophyllaceae', 'Pleuroziaceae', 'Ptychomniaceae',
    'Rhacocarpaceae', 'Rhizogoniaceae', 'Saccogynaceae', 'Schistostegaceae',
    'Scouleriaceae', 'Sphaerocarpaceae', 'Targioniaceae',
}

# Origin → climate mapping keywords
ORIGIN_CLIMATE = [
    # Tropical
    (['brazil', 'amazon', 'congo', 'indonesia', 'malaysia', 'borneo', 'sumatra',
      'new guinea', 'philippines', 'tropical africa', 'tropical asia', 'tropical america',
      'wet tropical', 'equatorial'], 'wet tropical'),
    # Seasonally dry tropical
    (['india', 'thailand', 'myanmar', 'vietnam', 'central america', 'caribbean',
      'madagascar', 'savanna', 'monsoon', 'seasonally dry'], 'seasonally dry tropical'),
    # Subtropical
    (['south africa', 'mediterranean', 'mexico', 'argentina', 'chile', 'southern china',
      'southern japan', 'florida', 'australia', 'new zealand', 'canary', 'subtropical'], 'subtropical'),
    # Temperate
    (['europe', 'north america', 'russia', 'china', 'japan', 'korea', 'temperate',
      'britain', 'scandinavia', 'germany', 'france', 'canada', 'siberia',
      'caucasus', 'himalayas', 'turkey', 'iran'], 'temperate'),
    # Desert
    (['sahara', 'arabian', 'gobi', 'namib', 'kalahari', 'mojave', 'sonoran',
      'arid', 'desert', 'dry shrubland'], 'desert or dry shrubland'),
    # Subalpine
    (['arctic', 'alpine', 'subarctic', 'subalpine', 'tundra', 'antarctica',
      'patagonia', 'iceland', 'greenland'], 'subalpine or subarctic'),
    # Montane tropical
    (['montane tropical', 'cloud forest', 'tropical highland'], 'montane tropical'),
]


def parse_origin_climate(origin_text):
    """Parse origin text → climate zone."""
    if not origin_text:
        return None
    lower = origin_text.lower()
    for keywords, climate in ORIGIN_CLIMATE:
        if any(kw in lower for kw in keywords):
            return climate
    return None


def build_family_climate_map():
    """Build family → dominant climate from already classified plants."""
    rows = turso_query("""
        SELECT family, climate, COUNT(*) as cnt
        FROM plants
        WHERE climate IS NOT NULL AND climate != ''
        AND family IS NOT NULL AND family != ''
        GROUP BY family, climate
        ORDER BY family, cnt DESC
    """)

    family_map = {}
    for r in rows:
        fam = r['family']
        if fam not in family_map:
            family_map[fam] = {}
        family_map[fam][r['climate']] = r['cnt']

    # Convert to dominant climate (>50%)
    result = {}
    for fam, climates in family_map.items():
        total = sum(climates.values())
        dominant = max(climates, key=climates.get)
        if climates[dominant] / total > 0.4:  # 40% threshold — less strict for climate
            result[fam] = dominant

    return result


def run(dry_run=False):
    plants = turso_query("""
        SELECT plant_id, scientific, family, origin, preset
        FROM plants
        WHERE preset NOT IN ('standard', 'herb', 'tropical')
        AND (climate IS NULL OR climate = '')
    """)
    print(f"[fill_climate_v2] {len(plants)} plants need climate", flush=True)

    family_climate = build_family_climate_map()
    print(f"  Family climate map: {len(family_climate)} families", flush=True)

    stmts = []
    stats = {'origin': 0, 'family': 0, 'moss_default': 0, 'not_found': 0}

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        family = plant.get('family') or ''
        origin = plant.get('origin') or ''
        preset = plant.get('preset') or ''
        climate = None
        source = None

        # Priority 1: Origin (most specific)
        if origin:
            climate = parse_origin_climate(origin)
            if climate:
                source = 'origin_climate'
                stats['origin'] += 1

        # Priority 2: Family from our DB
        if not climate and family in family_climate:
            climate = family_climate[family]
            source = 'family_climate'
            stats['family'] += 1

        # Priority 3: Moss default → temperate
        if not climate and (family in MOSS_FAMILIES or preset == 'moss'):
            climate = 'temperate'
            source = 'moss_climate_default'
            stats['moss_default'] += 1

        # Priority 4: Still nothing
        if not climate:
            stats['not_found'] += 1
            continue

        if not dry_run:
            stmts.append(("UPDATE plants SET climate = ? WHERE plant_id = ?", [climate, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, ?, 'climate', ?, datetime('now'))",
                [pid, source, climate]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(plants)}] origin={stats['origin']} family={stats['family']} moss={stats['moss_default']} miss={stats['not_found']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[fill_climate_v2] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    if not dry_run:
        remaining = turso_query("SELECT COUNT(*) as c FROM plants WHERE (climate IS NULL OR climate = '')")
        print(f"  Still without climate: {remaining[0]['c']}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
