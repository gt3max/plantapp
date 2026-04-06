"""
Polish watering demand — extract keywords from descriptions/care guides
to refine water_demand from default "Medium" to actual value.

Keywords:
  → Low/Minimum: drought tolerant, let dry, overwatering kills, root rot,
                  store water, succulent, dry between, xeric
  → High/Frequent: keep moist, never dry, water-loving, bog, marsh,
                    constantly moist, high humidity, aquatic, semi-aquatic
  → Medium stays Medium if no keywords found

Also sets watering_avoid for plants with specific warnings.

Runs after initial data collection. Safe to re-run.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch

# Keywords that indicate LOW water demand (drought-tolerant)
LOW_KEYWORDS = [
    'drought.tolerant', 'drought.resistant', 'let.dry', 'allow.to.dry',
    'dry.between', 'dry.out.between', 'overwatering.kill', 'root.rot',
    'store.water', 'stores.water', 'water.storage', 'xeric',
    'very.dry', 'completely.dry', 'dry.completely',
    'susceptible.to.overwatering', 'sensitive.to.overwatering',
    'prone.to.root.rot', 'easily.overwater',
    'thick.leaves', 'fleshy.leaves', 'waxy.leaves',
    'caudex', 'tuberous.root', 'rhizome.stores',
    'desert.plant', 'arid.region', 'dry.habitat',
]

# Keywords that indicate HIGH water demand (moisture-loving)
HIGH_KEYWORDS = [
    'keep.moist', 'constantly.moist', 'consistently.moist',
    'never.dry', 'never.let.dry', 'do.not.let.dry', 'don.t.let.dry',
    'water.loving', 'water.hungry', 'thirsty.plant',
    'bog.plant', 'marsh', 'swamp', 'wetland', 'riparian',
    'aquatic', 'semi.aquatic', 'marginal.plant',
    'high.humidity', 'humidity.loving', 'moisture.loving',
    'frequent.watering', 'water.frequently', 'water.often',
    'keep.soil.damp', 'evenly.moist', 'uniformly.moist',
    'shallow.roots', 'surface.roots',
]

# Keywords for watering_avoid (specific warnings)
AVOID_KEYWORDS = {
    'sensitive.to.lime': 'Sensitive to lime in water — use filtered or rainwater',
    'sensitive.to.chlorine': 'Sensitive to chlorine — let tap water sit 24h before watering',
    'sensitive.to.fluoride': 'Sensitive to fluoride — use distilled or rainwater',
    'cold.water': 'Avoid cold water — use room temperature water',
    'crown.rot': 'Never water into the crown — water from below or around the base',
    'leaf.rot': 'Avoid getting water on leaves — water at soil level',
    'wet.feet': 'Never leave standing in water — ensure good drainage',
    'waterlog': 'Never waterlog — ensure pot has drainage holes',
}


def _normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    return re.sub(r'[^a-z0-9\s]', '.', text.lower())


def _check_keywords(text: str, keywords: list[str]) -> list[str]:
    """Check which keywords match in text. Returns matched keywords."""
    norm = _normalize_text(text)
    matched = []
    for kw in keywords:
        pattern = kw.replace('.', r'[\s\-\.]+')
        if re.search(pattern, norm):
            matched.append(kw)
    return matched


def _check_avoid(text: str) -> list[str]:
    """Check for watering avoid warnings. Returns warning texts."""
    norm = _normalize_text(text)
    warnings = []
    for kw, warning in AVOID_KEYWORDS.items():
        pattern = kw.replace('.', r'[\s\-\.]+')
        if re.search(pattern, norm):
            warnings.append(warning)
    return warnings


def polish_watering(limit=20000):
    """Refine water_demand based on descriptions and care text."""
    rows = turso_query("""
        SELECT p.plant_id, p.description, p.preset,
               c.water_demand, c.watering_method, c.watering_avoid,
               c.light_guide, c.watering_guide, c.tips
        FROM plants p
        JOIN care c ON p.plant_id = c.plant_id
        WHERE c.water_demand = 'Medium' OR c.water_demand = 'Average'
        LIMIT ?
    """, [limit])

    print(f"[polish_watering] Checking {len(rows)} plants with Medium/Average demand...", flush=True)

    demand_changed = 0
    avoid_added = 0
    stmts = []

    for i, r in enumerate(rows):
        pid = r['plant_id']
        # Combine all text sources
        texts = []
        for field in ['description', 'light_guide', 'watering_guide', 'tips']:
            val = r.get(field)
            if val:
                texts.append(val)

        if not texts:
            continue

        combined = ' '.join(texts)

        # Check demand keywords
        low_matches = _check_keywords(combined, LOW_KEYWORDS)
        high_matches = _check_keywords(combined, HIGH_KEYWORDS)

        new_demand = None
        if low_matches and not high_matches:
            new_demand = 'Low'
        elif high_matches and not low_matches:
            new_demand = 'High'
        elif low_matches and high_matches:
            # Conflicting — keep Medium but log
            pass

        if new_demand:
            stmts.append(("UPDATE care SET water_demand = ? WHERE plant_id = ?", [new_demand, pid]))
            demand_changed += 1
            if demand_changed <= 20:
                kws = (low_matches or high_matches)[:3]
                print(f"  {pid:35s} | Medium → {new_demand:6s} | keywords: {', '.join(kws)}", flush=True)

        # Check avoid warnings
        if not r.get('watering_avoid'):
            avoid_warnings = _check_avoid(combined)
            if avoid_warnings:
                stmts.append((
                    "UPDATE care SET watering_avoid = ? WHERE plant_id = ?",
                    ['; '.join(avoid_warnings), pid]
                ))
                avoid_added += 1

        # Batch write
        if len(stmts) >= 40:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 2000 == 0:
            print(f"  [{i+1}/{len(rows)}] demand_changed={demand_changed}, avoid_added={avoid_added}", flush=True)

    if stmts:
        turso_batch(stmts)

    # Now recalculate water_frequency for changed plants
    if demand_changed > 0:
        print(f"\nRecalculating water_frequency for {demand_changed} plants...", flush=True)
        _recalc_watering()

    print(f"\n[polish_watering] Done:", flush=True)
    print(f"  Demand refined: {demand_changed} plants", flush=True)
    print(f"  Avoid warnings added: {avoid_added} plants", flush=True)


def _recalc_watering():
    """Recalculate water_frequency from preset + demand for recently changed plants."""
    BASE_DAYS = {
        ('Succulents', 'Low'): 18, ('Succulents', 'Medium'): 14, ('Succulents', 'High'): 10,
        ('Succulents', 'Average'): 14, ('Succulents', 'Minimum'): 10,
        ('Tropical', 'Low'): 14, ('Tropical', 'Medium'): 10, ('Tropical', 'High'): 7,
        ('Tropical', 'Average'): 10, ('Tropical', 'Minimum'): 17,
        ('Herbs', 'Low'): 7, ('Herbs', 'Medium'): 5, ('Herbs', 'High'): 3,
        ('Herbs', 'Average'): 5, ('Herbs', 'Minimum'): 10,
        ('Standard', 'Low'): 14, ('Standard', 'Medium'): 10, ('Standard', 'High'): 7,
        ('Standard', 'Average'): 10, ('Standard', 'Minimum'): 17,
        ('Standard', 'Very high'): 5, ('Tropical', 'Very high'): 5,
        ('Herbs', 'Very high'): 2, ('Succulents', 'Very high'): 7,
        ('Standard', 'Frequent'): 5, ('Tropical', 'Frequent'): 5,
        ('Herbs', 'Frequent'): 2, ('Succulents', 'Frequent'): 7,
    }

    rows = turso_query("""
        SELECT p.plant_id, p.preset, c.water_demand
        FROM plants p JOIN care c ON p.plant_id = c.plant_id
        WHERE c.water_demand IN ('Low', 'High') AND p.preset IS NOT NULL
    """)

    stmts = []
    for r in rows:
        key = (r['preset'], r['water_demand'])
        if key not in BASE_DAYS:
            key = (r['preset'], 'Medium')
        base = BASE_DAYS.get(key, 10)

        if base <= 3:
            freq = f'Every {base}-{base+1} days'
        elif base <= 7:
            freq = f'Every {base-2}-{base} days'
        elif base <= 14:
            freq = f'Every {base-3}-{base} days'
        else:
            weeks = base // 7
            freq = f'Every {weeks}-{weeks+1} weeks'

        stmts.append(("UPDATE care SET water_frequency = ? WHERE plant_id = ?", [freq, r['plant_id']]))

    for i in range(0, len(stmts), 50):
        turso_batch(stmts[i:i+50])

    print(f"  Recalculated {len(stmts)} water frequencies", flush=True)


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    polish_watering(limit)
