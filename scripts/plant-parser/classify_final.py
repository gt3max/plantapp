"""
Final classification: 1,424 remaining plants (standard/herb/tropical) → 14 lifeform types.

Classification: tree, shrub, subshrub, perennial, annual, succulent, epiphyte,
climber, bulb, aquatic, bamboo, parasitic, fern, moss

Strategy:
1. Moss families → moss (14th type)
2. Expanded FAMILY_MAP for vascular plants
3. herb → perennial
4. tropical → by family
5. No family → IPNI lookup for family, then classify

Usage:
    python3 classify_final.py              # full run
    python3 classify_final.py --dry-run    # preview
"""
import sys
import os
import json
import urllib.request
import urllib.parse
import time

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

OLD_PRESETS = ('standard', 'herb', 'tropical')

# === MOSS FAMILIES ===
MOSS_FAMILIES = {
    # Mosses (Bryophyta)
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
    # Liverworts (Marchantiophyta)
    'Lejeuneaceae', 'Cephaloziaceae', 'Frullaniaceae', 'Porellaceae',
    'Radulaceae', 'Plagiochilaceae', 'Jungermanniaceae', 'Lophocoleaceae',
    'Scapaniaceae', 'Herbertaceae', 'Lepidoziaceae', 'Calypogeiaceae',
    'Geocalycaceae', 'Jubulaceae', 'Metzgeriaceae', 'Aneuraceae',
    'Pelliaceae', 'Pallaviciniaceae', 'Marchantiaceae', 'Ricciaceae',
    'Aytoniaceae', 'Conocephalaceae', 'Anastrophyllaceae', 'Trichocoleaceae',
    'Pseudolepicoleaceae', 'Cephaloziellaceae', 'Adelanthaceae',
    # Hornworts
    'Anthocerotaceae', 'Notothyladaceae',
    # Additional moss/liverwort families found in unclassified
    'Gymnomitriaceae', 'Leucodontaceae', 'Calliergonaceae', 'Acrobolbaceae',
    'Pylaisiaceae', 'Lophoziaceae', 'Pterigynandraceae', 'Theliaceae',
    'Fossombroniaceae', 'Solenostomataceae', 'Ptilidiaceae', 'Fabroniaceae',
    'Myliaceae', 'Arnelliaceae', 'Cleveaceae', 'Monocleaceae',
    'Wiesnerellaceae', 'Blasiaceae', 'Codoniaceae', 'Haplomitriaceae',
    # Remaining 91 — additional moss/liverwort families
    'Leucomiaceae', 'Moerckiaceae', 'Antheliaceae', 'Bruchiaceae',
    'Distichiaceae', 'Ephemeraceae', 'Harpanthaceae', 'Leptodontaceae',
    'Phyllogoniaceae', 'Stereophyllaceae', 'Blepharostomataceae',
    'Bryoxiphiaceae', 'Catoscopiaceae', 'Corsiniaceae', 'Diphysciaceae',
    'Disceliaceae', 'Dumortieraceae', 'Hygrobiellaceae', 'Hypopterygiaceae',
    'Leptostomataceae', 'Lunulariaceae', 'Myriniaceae', 'Myuriaceae',
    'Orthodontiaceae', 'Petalophyllaceae', 'Pleuroziaceae', 'Ptychomniaceae',
    'Rhacocarpaceae', 'Rhizogoniaceae', 'Saccogynaceae', 'Schistostegaceae',
    'Scouleriaceae', 'Sphaerocarpaceae', 'Targioniaceae', 'Isoetaceae',
}

# === EXPANDED FAMILY MAP for vascular plants ===
FAMILY_MAP = {
    # Ferns
    'Aspleniaceae': 'fern', 'Pteridaceae': 'fern', 'Polypodiaceae': 'fern',
    'Dryopteridaceae': 'fern', 'Blechnaceae': 'fern', 'Cyatheaceae': 'fern',
    'Dennstaedtiaceae': 'fern', 'Thelypteridaceae': 'fern',
    'Selaginellaceae': 'fern', 'Lycopodiaceae': 'fern',
    'Ophioglossaceae': 'fern', 'Osmundaceae': 'fern',
    'Hymenophyllaceae': 'fern', 'Gleicheniaceae': 'fern',
    'Schizaeaceae': 'fern', 'Marattiaceae': 'fern',
    # Trees
    'Arecaceae': 'tree', 'Pinaceae': 'tree', 'Cupressaceae': 'tree',
    'Fagaceae': 'tree', 'Betulaceae': 'tree', 'Salicaceae': 'tree',
    'Myrtaceae': 'tree', 'Juglandaceae': 'tree', 'Sapindaceae': 'tree',
    'Meliaceae': 'tree', 'Moraceae': 'tree', 'Ulmaceae': 'tree',
    'Platanaceae': 'tree', 'Magnoliaceae': 'tree', 'Lauraceae': 'tree',
    'Podocarpaceae': 'tree', 'Araucariaceae': 'tree', 'Taxaceae': 'tree',
    'Casuarinaceae': 'tree',
    # Shrubs
    'Rosaceae': 'shrub', 'Ericaceae': 'shrub', 'Rhamnaceae': 'shrub',
    'Caprifoliaceae': 'shrub', 'Thymelaeaceae': 'shrub',
    'Polygalaceae': 'shrub', 'Proteaceae': 'shrub',
    'Melastomataceae': 'shrub', 'Goodeniaceae': 'shrub',
    # Epiphytes
    'Orchidaceae': 'epiphyte', 'Bromeliaceae': 'epiphyte',
    # Succulents
    'Cactaceae': 'succulent', 'Aizoaceae': 'succulent',
    # Perennials
    'Araceae': 'perennial', 'Begoniaceae': 'perennial', 'Piperaceae': 'perennial',
    'Acanthaceae': 'perennial', 'Gesneriaceae': 'perennial',
    'Commelinaceae': 'perennial', 'Urticaceae': 'perennial',
    'Asteraceae': 'perennial', 'Apiaceae': 'perennial',
    'Campanulaceae': 'perennial', 'Gentianaceae': 'perennial',
    'Iridaceae': 'perennial', 'Liliaceae': 'perennial',
    'Ranunculaceae': 'perennial', 'Caryophyllaceae': 'perennial',
    'Primulaceae': 'perennial', 'Saxifragaceae': 'perennial',
    'Violaceae': 'perennial', 'Boraginaceae': 'perennial',
    'Plantaginaceae': 'perennial', 'Orobanchaceae': 'perennial',
    'Scrophulariaceae': 'perennial',
    # Perennial/shrub (defaulting to more common)
    'Lamiaceae': 'perennial', 'Solanaceae': 'perennial',
    'Fabaceae': 'perennial', 'Rubiaceae': 'shrub',
    'Malvaceae': 'shrub', 'Euphorbiaceae': 'shrub',
    'Verbenaceae': 'shrub',
    # Grasses
    'Poaceae': 'perennial', 'Cyperaceae': 'perennial', 'Juncaceae': 'perennial',
    # Climbers
    'Convolvulaceae': 'climber', 'Vitaceae': 'climber',
    'Passifloraceae': 'climber', 'Cucurbitaceae': 'climber',
    # Aquatic
    'Nymphaeaceae': 'aquatic', 'Hydrocharitaceae': 'aquatic',
    'Pontederiaceae': 'aquatic',
    # Parasitic
    'Loranthaceae': 'parasitic', 'Viscaceae': 'parasitic',
    'Rafflesiaceae': 'parasitic',
    # Additional vascular families from unclassified
    'Papaveraceae': 'perennial', 'Polygonaceae': 'perennial',
    'Montiaceae': 'perennial', 'Onagraceae': 'perennial',
    'Balsaminaceae': 'perennial', 'Droseraceae': 'perennial',
    'Crassulaceae': 'succulent', 'Didiereaceae': 'succulent',
    'Zingiberaceae': 'perennial', 'Costaceae': 'perennial',
    'Marantaceae': 'perennial', 'Cannaceae': 'perennial',
    'Strelitziaceae': 'perennial', 'Musaceae': 'perennial',
    'Heliconiaceae': 'perennial',
    # Remaining 91 — additional vascular families
    'Asparagaceae': 'perennial', 'Rutaceae': 'tree', 'Phyllanthaceae': 'shrub',
    'Amaranthaceae': 'perennial', 'Buxaceae': 'shrub', 'Geraniaceae': 'perennial',
    'Juncaginaceae': 'aquatic', 'Loganiaceae': 'shrub', 'Lonchitidaceae': 'fern',
    'Malpighiaceae': 'climber', 'Menyanthaceae': 'aquatic', 'Myricaceae': 'shrub',
    'Nitrariaceae': 'shrub', 'Polemoniaceae': 'perennial',
}


def run(dry_run=False):
    plants = turso_query(
        "SELECT plant_id, scientific, family, genus, preset FROM plants WHERE preset IN (?, ?, ?)",
        list(OLD_PRESETS)
    )
    print(f"[classify_final] {len(plants)} plants to classify", flush=True)

    stmts = []
    stats = {'moss': 0, 'family_map': 0, 'herb_to_perennial': 0, 'no_family': 0, 'unknown_family': 0}
    unknown_families = {}

    for i, plant in enumerate(plants):
        pid = plant['plant_id']
        family = plant.get('family') or ''
        preset = plant.get('preset') or ''
        new_lifeform = None
        method = ''

        # 1. Moss families → moss
        if family in MOSS_FAMILIES:
            new_lifeform = 'moss'
            method = f'moss_family={family}'
            stats['moss'] += 1

        # 2. Family map for vascular
        elif family in FAMILY_MAP:
            new_lifeform = FAMILY_MAP[family]
            method = f'family_map={family}→{new_lifeform}'
            stats['family_map'] += 1

        # 3. herb → perennial
        elif preset == 'herb':
            new_lifeform = 'perennial'
            method = 'herb→perennial'
            stats['herb_to_perennial'] += 1

        # 4. No family or unknown family
        elif not family:
            stats['no_family'] += 1
            continue
        else:
            stats['unknown_family'] += 1
            unknown_families[family] = unknown_families.get(family, 0) + 1
            continue

        if new_lifeform and not dry_run:
            stmts.append(("UPDATE plants SET preset = ? WHERE plant_id = ?", [new_lifeform, pid]))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'classify_final', 'lifeform', ?, datetime('now'))",
                [pid, new_lifeform]
            ))
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'classify_final', 'method', ?, datetime('now'))",
                [pid, method]
            ))

            if len(stmts) >= 100:
                turso_batch(stmts)
                stmts = []

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(plants)}] moss={stats['moss']} family={stats['family_map']} herb={stats['herb_to_perennial']}", flush=True)

    if stmts and not dry_run:
        turso_batch(stmts)

    print(f"\n[classify_final] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    if unknown_families:
        print(f"\nUnknown families (not in FAMILY_MAP or MOSS_FAMILIES):", flush=True)
        for fam, cnt in sorted(unknown_families.items(), key=lambda x: -x[1])[:15]:
            print(f"  {fam:25s} {cnt}", flush=True)

    # Final check
    if not dry_run:
        remaining = turso_query("SELECT preset, COUNT(*) as c FROM plants WHERE preset IN ('standard','herb','tropical') GROUP BY preset")
        if remaining:
            print(f"\nStill remaining:", flush=True)
            for r in remaining:
                print(f"  {r['preset']}: {r['c']}", flush=True)
        else:
            print(f"\n✓ Standard/herb/tropical = 0!", flush=True)

        dist = turso_query("SELECT preset, COUNT(*) as cnt FROM plants GROUP BY preset ORDER BY cnt DESC")
        print(f"\nFinal distribution:", flush=True)
        for d in dist:
            print(f"  {d['preset']:<15s} {d['cnt']:>6}", flush=True)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run(dry_run=dry_run)
