"""
Xiaomi Flower Care plant database fetcher.
Source: https://github.com/vrachieru/plant-database
1,000 plants with maintenance data, light/humidity/temp parameters.
Free, open source, no API limits.
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

GITHUB_API = 'https://api.github.com/repos/vrachieru/plant-database/contents/json'
GITHUB_RAW = 'https://raw.githubusercontent.com/vrachieru/plant-database/master/json'


def fetch_file_list():
    """Get list of all plant JSON files from GitHub."""
    req = urllib.request.Request(GITHUB_API, headers={'User-Agent': 'PlantApp/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        files = json.loads(resp.read().decode())
    return [f['name'] for f in files if f['name'].endswith('.json')]


def fetch_plant_data(filename):
    """Fetch single plant JSON from GitHub raw."""
    url = f'{GITHUB_RAW}/{urllib.parse.quote(filename)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'PlantApp/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def enrich_from_xiaomi(limit=1000):
    """Fetch Xiaomi plant data and enrich existing Turso records."""
    print("[Xiaomi] Fetching file list...")
    files = fetch_file_list()
    print(f"[Xiaomi] {len(files)} plants available")

    enriched = 0
    not_found = 0
    errors = 0

    for i, filename in enumerate(files[:limit]):
        try:
            data = fetch_plant_data(filename)
            time.sleep(0.15)  # Polite rate

            pid = data.get('pid', '').strip()
            display = data.get('display_pid', pid)
            if not pid:
                continue

            # Normalize scientific name for matching
            scientific_lower = pid.lower().strip()
            plant_id = scientific_lower.replace(' ', '_').replace("'", '').replace('"', '')

            # Check if plant exists in our DB
            existing = turso_query(
                "SELECT plant_id FROM plants WHERE LOWER(scientific) = ? OR plant_id = ?",
                [scientific_lower, plant_id]
            )

            if not existing:
                # Try partial match (genus only)
                genus = scientific_lower.split()[0] if ' ' in scientific_lower else scientific_lower
                existing = turso_query(
                    "SELECT plant_id FROM plants WHERE LOWER(scientific) LIKE ?",
                    [f'{genus}%']
                )

            if not existing:
                not_found += 1
                continue

            db_plant_id = existing[0]['plant_id']

            # Extract Xiaomi data
            maint = data.get('maintenance', {}) or {}
            param = data.get('parameter', {}) or {}
            basic = data.get('basic', {}) or {}

            statements = []

            # Fertilizing
            fert_text = maint.get('fertilization', '')
            if fert_text:
                statements.append((
                    "UPDATE care SET fertilizer_type = COALESCE(NULLIF(fertilizer_type, ''), ?) WHERE plant_id = ?",
                    [fert_text, db_plant_id]
                ))

            # Pruning text
            pruning_text = maint.get('pruning', '')
            if pruning_text:
                statements.append((
                    "UPDATE care SET tips = CASE WHEN tips IS NULL OR tips = '' THEN ? ELSE tips END WHERE plant_id = ?",
                    [pruning_text, db_plant_id]
                ))

            # PPFD (mmol → our ppfd_min/max)
            ppfd_min = param.get('min_light_mmol')
            ppfd_max = param.get('max_light_mmol')
            if ppfd_min and ppfd_max:
                # Xiaomi mmol is daily light integral in mmol — convert to PPFD approximation
                # mmol/day ÷ 12h ÷ 3.6 ≈ PPFD in µmol/m²/s
                ppfd_min_val = max(1, int(ppfd_min / 43.2))  # 12h * 3600s / 1000
                ppfd_max_val = max(ppfd_min_val + 1, int(ppfd_max / 43.2))
                statements.append((
                    "UPDATE care SET ppfd_min = CASE WHEN ppfd_min = 0 OR ppfd_min IS NULL THEN ? ELSE ppfd_min END, ppfd_max = CASE WHEN ppfd_max = 0 OR ppfd_max IS NULL THEN ? ELSE ppfd_max END WHERE plant_id = ?",
                    [ppfd_min_val, ppfd_max_val, db_plant_id]
                ))

            # DLI from mmol
            if ppfd_min and ppfd_max:
                dli_min = round(ppfd_min / 1000 * 0.0864, 1)  # rough conversion
                dli_max = round(ppfd_max / 1000 * 0.0864, 1)
                if dli_min > 0:
                    statements.append((
                        "UPDATE care SET dli_min = CASE WHEN dli_min = 0 OR dli_min IS NULL THEN ? ELSE dli_min END, dli_max = CASE WHEN dli_max = 0 OR dli_max IS NULL THEN ? ELSE dli_max END WHERE plant_id = ?",
                        [dli_min, dli_max, db_plant_id]
                    ))

            # Humidity min/max
            hum_min = param.get('min_env_humid')
            hum_max = param.get('max_env_humid')
            if hum_min is not None and hum_max is not None:
                hum_text = f'{hum_min}-{hum_max}%'
                if hum_min >= 60:
                    hum_level = 'High'
                elif hum_min >= 40:
                    hum_level = 'Average'
                else:
                    hum_level = 'Low'
                statements.append((
                    "UPDATE care SET humidity_min_pct = CASE WHEN humidity_min_pct = 0 OR humidity_min_pct IS NULL THEN ? ELSE humidity_min_pct END, humidity_level = CASE WHEN humidity_level IS NULL OR humidity_level = '' THEN ? ELSE humidity_level END WHERE plant_id = ?",
                    [hum_min, f'{hum_level} ({hum_text})', db_plant_id]
                ))

            # Humidity action from watering text
            watering_text = maint.get('watering', '')
            if watering_text and ('spray' in watering_text.lower() or 'mist' in watering_text.lower()):
                statements.append((
                    "UPDATE care SET humidity_action = COALESCE(NULLIF(humidity_action, ''), ?) WHERE plant_id = ?",
                    [watering_text, db_plant_id]
                ))

            # Temperature (more precise than hardiness zones)
            temp_min = param.get('min_temp')
            temp_max = param.get('max_temp')
            if temp_min is not None and temp_max is not None:
                statements.append((
                    "UPDATE care SET temp_min_c = CASE WHEN temp_min_c IS NULL OR temp_min_c = 0 THEN ? ELSE temp_min_c END, temp_max_c = CASE WHEN temp_max_c IS NULL OR temp_max_c = 0 THEN ? ELSE temp_max_c END WHERE plant_id = ?",
                    [int(temp_min), int(temp_max), db_plant_id]
                ))

            # Soil moisture (for Polivalka: start_pct / stop_pct)
            soil_min = param.get('min_soil_moist')
            soil_max = param.get('max_soil_moist')
            if soil_min is not None and soil_max is not None:
                statements.append((
                    "UPDATE care SET start_pct = CASE WHEN start_pct IS NULL OR start_pct = 0 THEN ? ELSE start_pct END, stop_pct = CASE WHEN stop_pct IS NULL OR stop_pct = 0 THEN ? ELSE stop_pct END WHERE plant_id = ?",
                    [int(soil_min), int(soil_max), db_plant_id]
                ))

            # Soil text
            soil_text = maint.get('soil', '')
            if soil_text:
                statements.append((
                    "UPDATE care SET soil_types = CASE WHEN soil_types IS NULL OR soil_types = '' THEN ? ELSE soil_types END WHERE plant_id = ?",
                    [soil_text, db_plant_id]
                ))

            # Execute updates
            if statements:
                turso_batch(statements)
                enriched += 1

            if (i + 1) % 50 == 0:
                print(f"[Xiaomi] Progress: {i+1}/{min(limit, len(files))}, enriched: {enriched}, not found: {not_found}")

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ! Error on {filename}: {e}")
            continue

    print(f"[Xiaomi] Done: {enriched} enriched, {not_found} not in DB, {errors} errors")
    return enriched


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    enrich_from_xiaomi(limit)
