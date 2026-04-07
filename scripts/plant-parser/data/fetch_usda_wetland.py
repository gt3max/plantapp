#!/usr/bin/env python3
"""
Fetch wetland indicator status for all USDA PLANTS with characteristics data.
Adds wetland columns to the existing usda_plant_characteristics.csv.

API: https://plantsservices.sc.egov.usda.gov/api/PlantWetland/{id}
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


def fetch_wetland(plant_id):
    """Fetch wetland indicator status for a plant."""
    resp = requests.get(f"{BASE_URL}/PlantWetland/{plant_id}",
                        headers={"Accept": "application/json"}, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def main():
    # Load existing progress data
    progress_file = os.path.join(DATA_DIR, "usda_characteristics_progress.json")
    with open(progress_file, "r") as f:
        plants = json.load(f)
    print(f"Loaded {len(plants)} plants from progress file")

    # Wetland progress
    wetland_file = os.path.join(DATA_DIR, "usda_wetland_progress.json")
    wetland_data = {}
    if os.path.exists(wetland_file):
        with open(wetland_file, "r") as f:
            wetland_data = json.load(f)
        print(f"  Resuming: {len(wetland_data)} plants already fetched")

    plant_ids = [(p["usda_id"], p["symbol"]) for p in plants]
    remaining = [(pid, sym) for pid, sym in plant_ids if str(pid) not in wetland_data]
    print(f"  Fetching wetland data for {len(remaining)} plants...")

    batch_size = 10
    count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i:i + batch_size]
            futures = {}
            for pid, sym in batch:
                futures[executor.submit(fetch_wetland, pid)] = (pid, sym)

            for future in as_completed(futures):
                pid, sym = futures[future]
                try:
                    result = future.result()
                    designations = []
                    if result:
                        for item in result:
                            for wd in item.get("WetlandDesignations", []):
                                designations.append({
                                    "region": wd.get("Region", ""),
                                    "subregion": wd.get("SubRegion"),
                                    "code": wd.get("WetlandCode", ""),
                                    "parent": wd.get("ParentRegion"),
                                })
                    wetland_data[str(pid)] = designations
                    count += 1
                    if count % 50 == 0:
                        print(f"  Progress: {count + len(wetland_data) - len(remaining)}/{len(plant_ids)} ({count})")
                except Exception as e:
                    print(f"  ERROR: {sym} ({pid}): {e}")
                    wetland_data[str(pid)] = []

            if count % 100 == 0 and count > 0:
                with open(wetland_file, "w") as f:
                    json.dump(wetland_data, f)

            time.sleep(0.2)

    # Save final
    with open(wetland_file, "w") as f:
        json.dump(wetland_data, f)

    # Now merge wetland data into the CSV
    # For simplicity, pick the most common/general wetland indicator
    # USDA codes: OBL (obligate wetland), FACW (facultative wetland), FAC (facultative),
    #             FACU (facultative upland), UPL (upland), NI (no indicator)
    wetland_with_data = sum(1 for v in wetland_data.values() if v)
    print(f"\n  Plants with wetland designations: {wetland_with_data}/{len(wetland_data)}")

    # Add wetland columns to each plant
    for plant in plants:
        pid = str(plant["usda_id"])
        designations = wetland_data.get(pid, [])

        # Get unique codes across all regions (top-level only)
        top_codes = [d["code"] for d in designations if not d.get("parent")]
        if top_codes:
            # Most common code
            from collections import Counter
            code_counts = Counter(top_codes)
            plant["wetland_indicator_most_common"] = code_counts.most_common(1)[0][0]
            plant["wetland_indicator_all"] = ", ".join(sorted(set(top_codes)))

        # Per-region codes
        for d in designations:
            if not d.get("parent"):
                col = f"wetland_{d['region'].lower().replace(' ', '_').replace(',', '')}"
                plant[col] = d["code"]

    # Rebuild CSV with wetland columns
    all_columns = set()
    for r in plants:
        all_columns.update(r.keys())

    fixed_cols = ["usda_id", "symbol", "scientific_name", "common_name", "family"]
    wetland_special = ["wetland_indicator_most_common", "wetland_indicator_all"]
    wetland_region_cols = sorted([c for c in all_columns if c.startswith("wetland_") and c not in wetland_special])
    char_cols = sorted([c for c in all_columns if c not in fixed_cols and not c.startswith("wetland_")])

    # Key characteristics first
    KEY_CHARS = ["drought_tolerance", "moisture_use", "shade_tolerance", "salinity_tolerance",
                 "anaerobic_tolerance", "fire_tolerance", "ph_minimum", "ph_maximum",
                 "precipitation_minimum", "precipitation_maximum", "temperature_minimum_degf",
                 "frost_free_days_minimum", "toxicity"]
    key_cols = [c for c in KEY_CHARS if c in char_cols]
    for kc in key_cols:
        char_cols.remove(kc)

    ordered_cols = fixed_cols + key_cols + char_cols + wetland_special + wetland_region_cols

    csv_file = os.path.join(DATA_DIR, "usda_plant_characteristics.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_cols, extrasaction="ignore")
        writer.writeheader()
        for r in plants:
            writer.writerow(r)

    print(f"\n  Updated CSV: {csv_file}")
    print(f"  Total plants: {len(plants)}")
    print(f"  Total columns: {len(ordered_cols)}")
    print(f"  Wetland region columns: {wetland_region_cols}")

    # Stats
    drought_count = sum(1 for r in plants if r.get("drought_tolerance"))
    moisture_count = sum(1 for r in plants if r.get("moisture_use"))
    wetland_count = sum(1 for r in plants if r.get("wetland_indicator_most_common"))
    print(f"\n  Plants with drought_tolerance: {drought_count}")
    print(f"  Plants with moisture_use: {moisture_count}")
    print(f"  Plants with wetland_indicator: {wetland_count}")


if __name__ == "__main__":
    main()
