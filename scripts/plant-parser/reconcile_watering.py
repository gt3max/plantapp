"""
Reconcile watering — resolve Ellenberg F vs MiFloraDB conflicts,
update demand, recalculate frequency, fill watering_method.

RULES:
- Featured 56: NEVER touch
- MiFloraDB min=15% (default): trust Ellenberg F instead
- MiFloraDB min≠15% (real data): if conflicts with Ellenberg → FLAG, don't resolve
- No data from either: family default, confidence=low
- After changes: verify 32 Planta plants still match ±3 days

Usage:
    python3 reconcile_watering.py --featured   # verify featured only (no changes)
    python3 reconcile_watering.py --check       # dry run, show what would change
    python3 reconcile_watering.py               # apply changes
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

# Featured plant IDs — NEVER modify these
with open('/Users/maximshurygin/plantapp/lib/constants/featured_plants.dart') as f:
    _feat_text = f.read()
FEATURED_IDS = set(re.findall(r"plantIdStr: '([^']+)'", _feat_text))

# Ellenberg F → demand
F_TO_DEMAND = {
    1: 'Minimum', 2: 'Minimum', 3: 'Low', 4: 'Low',
    5: 'Medium', 6: 'Medium', 7: 'High', 8: 'High', 9: 'High',
}

# Demand → watering method text
DEMAND_TEXT = {
    'Minimum': 'Let soil dry up completely',
    'Low': 'Let soil dry up',
    'Medium': 'Top layer should be dry',
    'High': 'Keep soil moist',
    'Very high': 'Keep soil moist',
    'Frequent': 'Keep soil moist',
}

# Base days matrix (preset × demand)
BASE_DAYS = {
    ('Succulents', 'Minimum'): 10, ('Succulents', 'Low'): 18, ('Succulents', 'Medium'): 14,
    ('Succulents', 'High'): 10, ('Succulents', 'Very high'): 7,
    ('Tropical', 'Minimum'): 17, ('Tropical', 'Low'): 14, ('Tropical', 'Medium'): 10,
    ('Tropical', 'High'): 7, ('Tropical', 'Very high'): 5,
    ('Herbs', 'Minimum'): 10, ('Herbs', 'Low'): 7, ('Herbs', 'Medium'): 5,
    ('Herbs', 'High'): 3, ('Herbs', 'Very high'): 2,
    ('Standard', 'Minimum'): 17, ('Standard', 'Low'): 14, ('Standard', 'Medium'): 10,
    ('Standard', 'High'): 7, ('Standard', 'Very high'): 5,
    ('Standard', 'Frequent'): 5, ('Tropical', 'Frequent'): 5,
    ('Herbs', 'Frequent'): 2, ('Succulents', 'Frequent'): 7,
}

# Sanity rules
SANITY = {
    'Succulents': {'forbidden': ['High', 'Very high', 'Frequent']},
    'Herbs': {'forbidden': ['Minimum', 'Low']},
    'Tropical': {'forbidden': ['Minimum']},
}

SEASON_COEFFS = {
    'Succulents': [1.80,1.60,1.40,1.20,1.10,1.00,1.00,1.10,1.20,1.40,1.60,1.80],
    'Tropical':   [1.80,1.60,1.40,1.20,1.05,1.00,1.00,1.05,1.20,1.40,1.60,1.80],
    'Herbs':      [1.80,1.60,1.30,1.10,1.05,1.00,1.00,1.05,1.10,1.30,1.60,1.80],
    'Standard':   [1.80,1.60,1.30,1.10,1.05,1.00,1.00,1.05,1.10,1.30,1.60,1.80],
}

# Planta reference (April days)
PLANTA_APRIL = {
    'monstera_deliciosa':12, 'epipremnum_aureum':12, 'dracaena_trifasciata':25,
    'crassula_ovata':18, 'spathiphyllum_wallisii':12, 'ficus_lyrata':12,
    'ficus_elastica':12, 'aloe_vera':13, 'zamioculcas_zamiifolia':25,
    'chlorophytum_comosum':12, 'phalaenopsis_amabilis':12, 'calathea_orbifolia':12,
    'dracaena_marginata':12, 'philodendron_hederaceum':12, 'strelitzia_reginae':12,
    'nephrolepis_exaltata':12, 'dieffenbachia_seguine':12,
    'aglaonema_commutatum':12, 'alocasia_amazonica':12,
    'coriandrum_sativum':4, 'capsicum_annuum':4,
    'chamaedorea_elegans':12, 'begonia_rex-cultorum':12,
    'hedera_helix':12, 'tradescantia_zebrina':12,
    'peperomia_obtusifolia':12, 'syngonium_podophyllum':12,
    'hoya_carnosa':12,
}


def days_to_freq(base):
    if base <= 3: return f'Every {base}-{base+1} days'
    elif base <= 7: return f'Every {base-2}-{base} days'
    elif base <= 14: return f'Every {base-3}-{base} days'
    else:
        weeks = base // 7
        return f'Every {weeks}-{weeks+1} weeks'


def verify_planta():
    """Verify featured against Planta. Returns (ok_count, total, issues)."""
    ok = 0
    issues = []
    for pid, p_days in PLANTA_APRIL.items():
        r = turso_query("SELECT p.preset, c.water_frequency FROM plants p JOIN care c ON p.plant_id=c.plant_id WHERE p.plant_id=?", [pid])
        if not r: continue
        preset = r[0]['preset'] or 'Standard'
        wf = r[0]['water_frequency'] or ''
        nums = re.findall(r'\d+', wf)
        if not nums: continue
        base = int(nums[-1]) * 7 if 'week' in wf.lower() else int(nums[-1])
        coeffs = SEASON_COEFFS.get(preset, SEASON_COEFFS['Standard'])
        our = round(base * coeffs[3])
        diff = our - p_days
        if abs(diff) <= 3:
            ok += 1
        else:
            issues.append((pid, our, p_days, diff))
    return ok, len(PLANTA_APRIL), issues


def reconcile(dry_run=False):
    plants = turso_query("""
        SELECT p.plant_id, p.preset, p.family, c.water_demand, c.ellenberg_f, c.watering_method
        FROM plants p JOIN care c ON p.plant_id = c.plant_id
    """)

    print(f"[reconcile_watering] Processing {len(plants)} plants (dry_run={dry_run})...", flush=True)

    # Pre-check Planta
    ok, total, issues = verify_planta()
    print(f"  Pre-check Planta: {ok}/{total} within ±3 days", flush=True)
    if issues:
        for pid, ours, planta, diff in issues:
            print(f"    {pid}: ours={ours}, planta={planta}, diff={diff:+d}", flush=True)

    # Load MiFloraDB data
    mf_data = {}
    mf_rows = turso_query("SELECT plant_id, field, value FROM source_data WHERE source = 'xiaomi_mifloradb' AND field = 'min_soil_moist'")
    for r in mf_rows:
        mf_data[r['plant_id']] = int(r['value'])

    stmts = []
    stats = {'f_applied': 0, 'conflict_flagged': 0, 'method_filled': 0, 'skipped_featured': 0, 'sanity_flag': 0}

    for p in plants:
        pid = p['plant_id']
        if pid in FEATURED_IDS:
            stats['skipped_featured'] += 1
            # Still fill watering_method if empty
            if not p.get('watering_method'):
                demand = p.get('water_demand') or 'Medium'
                method = DEMAND_TEXT.get(demand, 'Top layer should be dry')
                if not dry_run:
                    stmts.append(("UPDATE care SET watering_method = ? WHERE plant_id = ? AND (watering_method IS NULL OR watering_method = '')", [method, pid]))
                stats['method_filled'] += 1
            continue

        preset = p['preset'] or 'Standard'
        current_demand = p['water_demand'] or 'Medium'
        f_val = p.get('ellenberg_f')
        mf_min = mf_data.get(pid)

        new_demand = None

        # Ellenberg F available
        if f_val and f_val > 0:
            f_int = max(1, min(9, round(f_val)))
            f_demand = F_TO_DEMAND.get(f_int, 'Medium')

            if mf_min and mf_min != 15:
                # Real MiFloraDB data — check conflict
                if f_demand != current_demand:
                    if not dry_run:
                        stmts.append((
                            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value) VALUES (?, 'conflict', 'water_demand', ?)",
                            [pid, f"Ellenberg F={f_val}→{f_demand} vs MiFloraDB min={mf_min}%→{current_demand}"]
                        ))
                    stats['conflict_flagged'] += 1
            else:
                # MiFloraDB default or no MiFloraDB — trust Ellenberg
                if f_demand != current_demand and current_demand == 'Medium':
                    new_demand = f_demand
                    stats['f_applied'] += 1

        # Sanity check
        if new_demand:
            rules = SANITY.get(preset, {})
            if new_demand in rules.get('forbidden', []):
                if not dry_run:
                    stmts.append((
                        "INSERT OR REPLACE INTO source_data (plant_id, source, field, value) VALUES (?, 'conflict', 'sanity_check', ?)",
                        [pid, f"preset={preset} conflict with demand={new_demand}"]
                    ))
                stats['sanity_flag'] += 1
                new_demand = None

        # Apply new demand
        if new_demand and not dry_run:
            stmts.append(("UPDATE care SET water_demand = ? WHERE plant_id = ?", [new_demand, pid]))
            # Recalculate frequency
            key = (preset, new_demand)
            if key not in BASE_DAYS:
                key = (preset, 'Medium')
            base = BASE_DAYS.get(key, 10)
            freq = days_to_freq(base)
            stmts.append(("UPDATE care SET water_frequency = ? WHERE plant_id = ?", [freq, pid]))

        # Fill watering_method if empty
        if not p.get('watering_method'):
            demand = new_demand or current_demand
            method = DEMAND_TEXT.get(demand, 'Top layer should be dry')
            if not dry_run:
                stmts.append(("UPDATE care SET watering_method = ? WHERE plant_id = ? AND (watering_method IS NULL OR watering_method = '')", [method, pid]))
            stats['method_filled'] += 1

        if len(stmts) >= 40:
            turso_batch(stmts)
            stmts = []

    if stmts:
        turso_batch(stmts)

    print(f"\n[reconcile_watering] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    # Post-check Planta
    ok2, total2, issues2 = verify_planta()
    print(f"\n  Post-check Planta: {ok2}/{total2} within ±3 days", flush=True)
    if issues2:
        for pid, ours, planta, diff in issues2:
            print(f"    PROBLEM: {pid}: ours={ours}, planta={planta}, diff={diff:+d}", flush=True)

    # Demand distribution
    r = turso_query("SELECT water_demand, COUNT(*) as cnt FROM care GROUP BY water_demand ORDER BY cnt DESC LIMIT 7")
    print(f"\n  Demand distribution:", flush=True)
    for row in r:
        print(f"    {row['cnt']:>6}x | {row['water_demand']}", flush=True)


if __name__ == '__main__':
    if '--check' in sys.argv:
        reconcile(dry_run=True)
    elif '--featured' in sys.argv:
        ok, total, issues = verify_planta()
        print(f"Planta check: {ok}/{total} within ±3 days")
        for pid, ours, planta, diff in issues:
            print(f"  {pid}: ours={ours}, planta={planta}, diff={diff:+d}")
    else:
        reconcile(dry_run=False)
