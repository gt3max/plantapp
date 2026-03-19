#!/usr/bin/env python3
"""
Seed 25 popular plants from popular-plants.ts into Turso DB.
Reads the TypeScript file, extracts plant data, and uploads to Turso.

Usage: python3 seed_popular.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from turso_sync import turso_batch, turso_query
from config import POPULAR_PLANTS_TS


def parse_popular_plants_ts(filepath: Path) -> list[dict]:
    """Parse popular-plants.ts and extract plant objects."""
    content = filepath.read_text(encoding='utf-8')

    # Extract the array content between POPULAR_PLANTS: PopularPlant[] = [ ... ];
    match = re.search(r'POPULAR_PLANTS:\s*PopularPlant\[\]\s*=\s*\[', content)
    if not match:
        raise ValueError("Could not find POPULAR_PLANTS array in file")

    # Find matching bracket
    start = match.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
        i += 1
    array_content = content[start:i-1]

    # Parse individual plant objects
    plants = []
    obj_depth = 0
    obj_start = None

    for idx, ch in enumerate(array_content):
        if ch == '{':
            if obj_depth == 0:
                obj_start = idx
            obj_depth += 1
        elif ch == '}':
            obj_depth -= 1
            if obj_depth == 0 and obj_start is not None:
                obj_str = array_content[obj_start:idx+1]
                plant = parse_ts_object(obj_str)
                if plant and 'id' in plant:
                    plants.append(plant)
                obj_start = None

    return plants


def parse_ts_object(obj_str: str) -> dict:
    """Parse a TypeScript object literal into a Python dict."""
    result = {}

    # Extract simple key: 'value' or key: "value" pairs
    for m in re.finditer(r"(\w+):\s*'([^']*(?:\\.[^']*)*)'", obj_str):
        key, val = m.group(1), m.group(2)
        # Unescape
        val = val.replace("\\'", "'").replace('\\u00B0', '\u00B0')
        result[key] = val

    for m in re.finditer(r'(\w+):\s*"([^"]*(?:\\.[^"]*)*)"', obj_str):
        key, val = m.group(1), m.group(2)
        val = val.replace('\\"', '"').replace('\\u00B0', '\u00B0')
        result[key] = val

    # Extract boolean values
    for m in re.finditer(r'(\w+):\s*(true|false)', obj_str):
        result[m.group(1)] = m.group(2) == 'true'

    # Extract number values (but not inside arrays/strings)
    for m in re.finditer(r'(\w+):\s*(-?\d+(?:\.\d+)?)\s*[,}\n]', obj_str):
        key = m.group(1)
        val_str = m.group(2)
        if key not in result:
            result[key] = float(val_str) if '.' in val_str else int(val_str)

    # Extract string arrays: key: ['a', 'b', 'c']
    for m in re.finditer(r"(\w+):\s*\[([^\]]*)\]", obj_str):
        key = m.group(1)
        arr_content = m.group(2).strip()
        if arr_content:
            items = re.findall(r"'([^']*)'", arr_content)
            if items:
                result[key] = items

    # Extract nested care object
    care_match = re.search(r'care:\s*\{', obj_str)
    if care_match:
        start = care_match.end()
        depth = 1
        i = start
        while i < len(obj_str) and depth > 0:
            if obj_str[i] == '{':
                depth += 1
            elif obj_str[i] == '}':
                depth -= 1
            i += 1
        care_str = '{' + obj_str[start:i-1] + '}'
        result['care'] = parse_ts_object(care_str)

    return result


def plant_to_sql_statements(plant: dict) -> list[tuple[str, list]]:
    """Convert parsed plant dict to SQL INSERT statements."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    care = plant.get('care', {})

    statements = []

    # 1. INSERT into plants
    statements.append((
        """INSERT OR REPLACE INTO plants
           (plant_id, scientific, family, genus, category, indoor, edible,
            has_phases, preset, image_url, description, wikidata_id, sources, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            plant['id'],
            plant.get('scientific', ''),
            plant.get('family', ''),
            plant.get('scientific', '').split()[0] if plant.get('scientific') else '',  # genus
            plant.get('plant_type', 'decorative'),
            1,  # indoor
            0,  # edible
            0,  # has_phases
            plant.get('preset', 'Standard'),
            plant.get('image_url', ''),
            '',  # description — will be filled by Wikipedia later
            '',  # wikidata_id
            json.dumps(['popular-plants.ts']),
            now,
        ]
    ))

    # 2. INSERT common_name (English)
    common_name = plant.get('common_name', '')
    if common_name:
        statements.append((
            "INSERT OR REPLACE INTO common_names (plant_id, lang, name, is_primary) VALUES (?, ?, ?, ?)",
            [plant['id'], 'en', common_name, 1]
        ))

    # 3. INSERT care data
    care_params = [
        plant['id'],
        care.get('watering', ''),
        care.get('watering_winter', ''),
        '',  # water_demand
        care.get('start_pct', 0),
        care.get('stop_pct', 0),
        care.get('light', ''),
        care.get('light_also_ok', ''),
        care.get('ppfd_min', 0),
        care.get('ppfd_max', 0),
        care.get('dli_min', 0.0),
        care.get('dli_max', 0.0),
        0,  # temp_min_c — parse from string later
        0,  # temp_max_c
        care.get('humidity', ''),
        0,  # humidity_min_pct
        care.get('humidity_action', ''),
        care.get('soil', ''),
        0.0,  # soil_ph_min
        0.0,  # soil_ph_max
        care.get('repot', ''),
        care.get('fertilizer', ''),
        '',  # fertilizer_freq
        care.get('fertilizer_season', ''),
        0,  # height_min_cm
        0,  # height_max_cm
        '',  # lifecycle
        '',  # difficulty
        '',  # growth_rate
        '',  # watering_guide
        '',  # light_guide
        care.get('tips', ''),
        1 if plant.get('poisonous_to_pets') else 0,
        1 if plant.get('poisonous_to_humans') else 0,
        plant.get('toxicity_note', ''),
        json.dumps(care.get('common_problems', [])),
        json.dumps(care.get('common_pests', [])),
    ]

    # Parse temperature range from string like "18-29°C (65-85°F)"
    temp_str = care.get('temperature', '')
    temp_match = re.search(r'(\d+)-(\d+)', temp_str)
    if temp_match:
        care_params[12] = int(temp_match.group(1))  # temp_min_c
        care_params[13] = int(temp_match.group(2))  # temp_max_c

    # Parse humidity percentage
    hum_str = care.get('humidity', '')
    hum_match = re.search(r'(\d+)-(\d+)%', hum_str)
    if hum_match:
        care_params[15] = int(hum_match.group(1))  # humidity_min_pct

    statements.append((
        """INSERT OR REPLACE INTO care
           (plant_id, water_frequency, water_winter, water_demand,
            start_pct, stop_pct, light_preferred, light_also_ok,
            ppfd_min, ppfd_max, dli_min, dli_max,
            temp_min_c, temp_max_c, humidity_level, humidity_min_pct, humidity_action,
            soil_types, soil_ph_min, soil_ph_max, repot_frequency,
            fertilizer_type, fertilizer_freq, fertilizer_season,
            height_min_cm, height_max_cm, lifecycle, difficulty, growth_rate,
            watering_guide, light_guide, tips,
            toxic_to_pets, toxic_to_humans, toxicity_note,
            common_problems, common_pests)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        care_params
    ))

    # 4. INSERT tags
    tags = []
    if plant.get('category'):
        tags.append(plant['category'])
    if plant.get('plant_type') == 'greens':
        tags.append('edible')
    if plant.get('plant_type') == 'fruiting':
        tags.append('fruiting')
    if not plant.get('poisonous_to_pets') and not plant.get('poisonous_to_humans'):
        tags.append('pet-safe')

    for tag in tags:
        statements.append((
            "INSERT OR REPLACE INTO plant_tags (plant_id, tag) VALUES (?, ?)",
            [plant['id'], tag]
        ))

    return statements


def seed():
    """Main seed function."""
    print(f"Reading {POPULAR_PLANTS_TS}...")
    plants = parse_popular_plants_ts(POPULAR_PLANTS_TS)
    print(f"Parsed {len(plants)} plants from popular-plants.ts")

    if not plants:
        print("ERROR: No plants parsed!", file=sys.stderr)
        sys.exit(1)

    # Collect all SQL statements
    all_statements = []
    for plant in plants:
        all_statements.extend(plant_to_sql_statements(plant))

    print(f"Executing {len(all_statements)} SQL statements...")

    # Turso pipeline has a limit — batch in chunks of 50
    BATCH_SIZE = 50
    for i in range(0, len(all_statements), BATCH_SIZE):
        chunk = all_statements[i:i+BATCH_SIZE]
        turso_batch(chunk)
        print(f"  Batch {i//BATCH_SIZE + 1}: {len(chunk)} statements OK")

    # Verify
    rows = turso_query("SELECT COUNT(*) as cnt FROM plants")
    names = turso_query("SELECT COUNT(*) as cnt FROM common_names")
    care_count = turso_query("SELECT COUNT(*) as cnt FROM care")
    tags = turso_query("SELECT COUNT(*) as cnt FROM plant_tags")

    print(f"\nSeed complete!")
    print(f"  Plants:       {rows[0]['cnt']}")
    print(f"  Common names: {names[0]['cnt']}")
    print(f"  Care records: {care_count[0]['cnt']}")
    print(f"  Tags:         {tags[0]['cnt']}")

    # Show a few examples
    examples = turso_query("SELECT plant_id, scientific, preset FROM plants LIMIT 5")
    print(f"\nSample plants:")
    for ex in examples:
        print(f"  {ex['plant_id']}: {ex['scientific']} ({ex['preset']})")


if __name__ == '__main__':
    seed()
