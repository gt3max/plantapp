#!/usr/bin/env python3
"""
Fetch USDA PLANTS Database characteristics for all plants.
Downloads drought_tolerance, moisture_use, and all other characteristics.
Also fetches wetland indicator status.

API discovered from: https://plants.sc.egov.usda.gov/assets/config.json
Base URL: https://plantsservices.sc.egov.usda.gov/api/
"""

import json
import csv
import time
import sys
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://plantsservices.sc.egov.usda.gov/api"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Characteristics we want (will also save all others)
KEY_CHARACTERISTICS = [
    "Drought Tolerance",
    "Moisture Use",
    "Shade Tolerance",
    "Salinity Tolerance",
    "Anaerobic Tolerance",
    "Fire Tolerance",
    "pH, Minimum",
    "pH, Maximum",
    "Precipitation, Minimum",
    "Precipitation, Maximum",
    "Temperature, Minimum (°F)",
    "Frost Free Days, Minimum",
    "Toxicity",
]

WETLAND_REGIONS = [
    (3, "Alaska"),
    (4, "Arid West"),
    (5, "Atlantic and Gulf Coastal Plain"),
    (2, "Caribbean"),
    (6, "Eastern Mountains and Piedmont"),
    (7, "Great Plains"),
    (1, "Hawaii"),
    (8, "Midwest"),
    (9, "Northcentral and Northeast"),
    (10, "Western Mountains, Valleys, and Coast"),
]


def fetch_all_plants():
    """Fetch list of all plants with characteristics data."""
    print("Fetching plant list from characteristics search...")
    resp = requests.get(f"{BASE_URL}/characteristicSearchResults",
                        headers={"Accept": "application/json"}, timeout=60)
    resp.raise_for_status()
    plants = resp.json()
    print(f"  Found {len(plants)} plants with characteristics data")
    return plants


def fetch_plant_characteristics(plant_id):
    """Fetch all characteristics for a single plant."""
    resp = requests.get(f"{BASE_URL}/PlantCharacteristics/{plant_id}",
                        headers={"Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_plant_wetland(plant_id):
    """Fetch wetland indicator status for a plant."""
    resp = requests.get(f"{BASE_URL}/wetland/profile/{plant_id}",
                        headers={"Accept": "application/json"}, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def fetch_one_plant(plant):
    """Fetch characteristics + wetland for one plant. Returns dict."""
    plant_id = plant["id"]
    symbol = plant["symbol"]

    # Remove HTML tags from scientific name
    sci_name = plant.get("scientificNameWithoutAuthor", "")
    if not sci_name:
        sci_name = plant.get("scientificName", "").replace("<i>", "").replace("</i>", "")

    row = {
        "usda_id": plant_id,
        "symbol": symbol,
        "scientific_name": sci_name,
        "common_name": plant.get("commonName", ""),
        "family": plant.get("familyName", ""),
    }

    try:
        chars = fetch_plant_characteristics(plant_id)
        for c in chars:
            name = c["PlantCharacteristicName"]
            val = c["PlantCharacteristicValue"]
            # Normalize column names
            col = name.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("/", "_").replace("°", "deg")
            row[col] = val
    except Exception as e:
        print(f"  ERROR fetching characteristics for {symbol} ({plant_id}): {e}")

    try:
        wetland = fetch_plant_wetland(plant_id)
        if wetland:
            # wetland data is a list of {RegionName, IndicatorStatus, ...}
            for w in wetland:
                region = w.get("WetlandRegionName", w.get("RegionName", "unknown"))
                status = w.get("WetlandIndicatorStatus", w.get("IndicatorStatus", ""))
                col = f"wetland_{region.lower().replace(' ', '_').replace(',', '')}"
                row[col] = status
    except Exception as e:
        if "404" not in str(e):
            print(f"  ERROR fetching wetland for {symbol} ({plant_id}): {e}")

    return row


def main():
    # Step 1: Get all plants
    plants = fetch_all_plants()

    # Save raw plant list
    raw_file = os.path.join(DATA_DIR, "usda_plants_list_raw.json")
    with open(raw_file, "w") as f:
        json.dump(plants, f)
    print(f"  Saved raw plant list to {raw_file}")

    # Step 2: Check for existing progress
    progress_file = os.path.join(DATA_DIR, "usda_characteristics_progress.json")
    results = []
    done_ids = set()
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            results = json.load(f)
        done_ids = {r["usda_id"] for r in results}
        print(f"  Resuming: {len(done_ids)} plants already fetched")

    remaining = [p for p in plants if p["id"] not in done_ids]
    print(f"  Fetching characteristics for {len(remaining)} plants...")

    # Step 3: Fetch in parallel with rate limiting
    batch_size = 10
    save_every = 50
    count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i:i + batch_size]
            futures = {executor.submit(fetch_one_plant, p): p for p in batch}

            for future in as_completed(futures):
                plant = futures[future]
                try:
                    row = future.result()
                    results.append(row)
                    count += 1
                    if count % 20 == 0:
                        print(f"  Progress: {count + len(done_ids)}/{len(plants)} "
                              f"({(count + len(done_ids)) * 100 // len(plants)}%)")
                except Exception as e:
                    print(f"  FAILED: {plant['symbol']} - {e}")

            # Save progress periodically
            if count % save_every == 0 and count > 0:
                with open(progress_file, "w") as f:
                    json.dump(results, f)

            # Small delay between batches
            time.sleep(0.2)

    # Save final progress
    with open(progress_file, "w") as f:
        json.dump(results, f)
    print(f"\n  Fetched {len(results)} plants total")

    # Step 4: Build CSV
    # Collect all column names
    all_columns = set()
    for r in results:
        all_columns.update(r.keys())

    # Order columns: fixed first, then sorted characteristics, then wetland
    fixed_cols = ["usda_id", "symbol", "scientific_name", "common_name", "family"]
    wetland_cols = sorted([c for c in all_columns if c.startswith("wetland_")])
    char_cols = sorted([c for c in all_columns if c not in fixed_cols and c not in wetland_cols])

    # Put key characteristics first
    key_cols_normalized = []
    for kc in KEY_CHARACTERISTICS:
        col = kc.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("/", "_").replace("°", "deg")
        if col in char_cols:
            key_cols_normalized.append(col)
            char_cols.remove(col)

    ordered_cols = fixed_cols + key_cols_normalized + char_cols + wetland_cols

    csv_file = os.path.join(DATA_DIR, "usda_plant_characteristics.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_cols, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"\n  Saved CSV: {csv_file}")
    print(f"  Total plants: {len(results)}")
    print(f"  Total columns: {len(ordered_cols)}")
    print(f"  Key columns: {key_cols_normalized}")
    print(f"  Wetland columns: {wetland_cols}")

    # Step 5: Quick stats
    drought_count = sum(1 for r in results if r.get("drought_tolerance"))
    moisture_count = sum(1 for r in results if r.get("moisture_use"))
    wetland_count = sum(1 for r in results if any(r.get(wc) for wc in wetland_cols))
    print(f"\n  Plants with drought_tolerance: {drought_count}")
    print(f"  Plants with moisture_use: {moisture_count}")
    print(f"  Plants with wetland data: {wetland_count}")


if __name__ == "__main__":
    main()
