#!/usr/bin/env python3
"""
Enrich plant descriptions from Wikipedia REST API.
Fetches summary text for each plant and updates Turso.

Usage: python3 enrich_descriptions.py
"""
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import sys

from turso_sync import turso_query, turso_batch
from config import WIKI_REST_BASE, WIKIPEDIA_DELAY


def fetch_wikipedia_summary(title: str) -> dict:
    """Fetch Wikipedia summary for a given title."""
    # Replace spaces with underscores for URL
    url_title = urllib.parse.quote(title.replace(' ', '_'))
    url = f"{WIKI_REST_BASE}/page/summary/{url_title}"

    req = urllib.request.Request(url, headers={
        'User-Agent': 'PlantApp/1.0 (https://plantapp.pro; contact@plantapp.pro)',
        'Accept': 'application/json',
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise


def enrich():
    """Fetch Wikipedia descriptions for all plants without descriptions."""
    plants = turso_query(
        "SELECT plant_id, scientific, description FROM plants WHERE description IS NULL OR description = ''"
    )

    if not plants:
        print("All plants already have descriptions.")
        return

    print(f"Enriching {len(plants)} plants with Wikipedia descriptions...")

    statements = []
    success = 0
    failed = 0

    for plant in plants:
        scientific = plant['scientific']
        plant_id = plant['plant_id']

        try:
            data = fetch_wikipedia_summary(scientific)
            extract = data.get('extract', '')

            if extract:
                # Truncate to ~500 chars for summary
                if len(extract) > 500:
                    # Cut at last sentence within 500 chars
                    cut = extract[:500].rfind('.')
                    if cut > 200:
                        extract = extract[:cut+1]
                    else:
                        extract = extract[:500] + '...'

                statements.append((
                    "UPDATE plants SET description = ? WHERE plant_id = ?",
                    [extract, plant_id]
                ))
                success += 1
                print(f"  + {scientific}: {len(extract)} chars")
            else:
                failed += 1
                print(f"  - {scientific}: no Wikipedia article")

        except Exception as e:
            failed += 1
            print(f"  ! {scientific}: {e}")

        time.sleep(WIKIPEDIA_DELAY)

    if statements:
        # Batch update
        BATCH_SIZE = 25
        for i in range(0, len(statements), BATCH_SIZE):
            chunk = statements[i:i+BATCH_SIZE]
            turso_batch(chunk)

    print(f"\nDone: {success} enriched, {failed} failed")


if __name__ == '__main__':
    enrich()
