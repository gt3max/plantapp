#!/usr/bin/env python3
"""
Backup plant database from Turso to JSON files (grouped by family).
This is the "ГЛАВНЫЙ СЕЙФ" — JSON in git = permanent backup.

Usage: python3 backup.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from turso_sync import turso_query
from config import DATA_DIR, SCHEMA_VERSION


def backup():
    """Dump all plant data from Turso to JSON files by family."""
    print("Backing up Turso → JSON...")

    # Fetch all plants
    plants = turso_query("SELECT * FROM plants ORDER BY scientific")
    if not plants:
        print("No plants in database. Nothing to backup.")
        return

    # Fetch all care data
    care_rows = turso_query("SELECT * FROM care")
    care_map = {r['plant_id']: r for r in care_rows}

    # Fetch common names
    names_rows = turso_query("SELECT * FROM common_names ORDER BY plant_id, lang, name")
    names_map = defaultdict(lambda: defaultdict(list))
    for n in names_rows:
        names_map[n['plant_id']][n['lang']].append(n['name'])

    # Fetch tags
    tags_rows = turso_query("SELECT * FROM plant_tags ORDER BY plant_id, tag")
    tags_map = defaultdict(list)
    for t in tags_rows:
        tags_map[t['plant_id']].append(t['tag'])

    # Fetch external_ids
    ext_rows = turso_query("SELECT * FROM external_ids")
    ext_map = defaultdict(dict)
    for e in ext_rows:
        ext_map[e['plant_id']][e['source']] = e['external_id']

    # Group by family
    families = defaultdict(list)
    for plant in plants:
        pid = plant['plant_id']

        # Parse sources JSON
        sources = plant.get('sources')
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except (json.JSONDecodeError, TypeError):
                sources = []

        # Build care dict
        care = care_map.get(pid, {})
        # Parse JSON arrays in care
        for field in ('common_problems', 'common_pests'):
            if field in care and isinstance(care[field], str):
                try:
                    care[field] = json.loads(care[field])
                except (json.JSONDecodeError, TypeError):
                    care[field] = []

        record = {
            **plant,
            'sources': sources,
            'care': care,
            'common_names': dict(names_map.get(pid, {})),
            'tags': tags_map.get(pid, []),
            'external_ids': ext_map.get(pid, {}),
        }

        families[plant['family']].append(record)

    # Create output directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write family files
    total = 0
    for family, records in sorted(families.items()):
        filepath = DATA_DIR / f"{family}.json"
        # Sort records by scientific name
        records.sort(key=lambda r: r.get('scientific', ''))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        total += len(records)
        print(f"  {family}.json: {len(records)} plants")

    # Write metadata
    metadata = {
        'total_plants': total,
        'total_families': len(families),
        'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'families': sorted(families.keys()),
    }
    with open(DATA_DIR / '_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Write schema version
    with open(DATA_DIR / '_schema_version.json', 'w', encoding='utf-8') as f:
        json.dump({'version': SCHEMA_VERSION, 'created': metadata['last_updated']}, f, indent=2)

    print(f"\nBackup complete: {total} plants in {len(families)} families")
    print(f"Output: {DATA_DIR}/")


if __name__ == '__main__':
    backup()
