"""
Batch verify photos via iNaturalist CV.
Checks first photo of each plant against expected scientific name.
Saves results to source_data. Skips already verified.

Usage:
    python3 verify_photos_batch.py              # all unverified
    python3 verify_photos_batch.py --limit 200
    python3 verify_photos_batch.py --retry-errors  # re-check errors
"""
import subprocess
import json
import time
import urllib.request
import os
import sys

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

TOKEN = os.environ.get('INATURALIST_API_TOKEN', '')

SYNONYMS = {
    'dracaena trifasciata': ['sansevieria trifasciata'],
    'salvia rosmarinus': ['rosmarinus officinalis'],
    'schefflera arboricola': ['heptapleurum arboricola'],
    'streptocarpus ionanthus': ['saintpaulia ionantha'],
    'haworthiopsis attenuata': ['haworthia attenuata', 'haworthia fasciata'],
    'calathea orbifolia': ['goeppertia orbifolia'],
    'epipremnum aureum': ['pothos aureus', 'scindapsus aureus'],
    'dypsis lutescens': ['chrysalidocarpus lutescens'],
    'cycas revoluta': [],
    'nephrolepis exaltata': [],
}


def verify_photo(image_url, expected_scientific, retries=2):
    """Verify photo via iNaturalist CV. Retries on error."""
    for attempt in range(retries + 1):
        try:
            urllib.request.urlretrieve(image_url, '/tmp/verify_photo.jpg')
            result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                'https://api.inaturalist.org/v1/computervision/score_image',
                '-F', 'image=@/tmp/verify_photo.jpg',
                '-H', f'Authorization: Bearer {TOKEN}',
            ], capture_output=True, text=True, timeout=30)

            if not result.stdout.strip():
                if attempt < retries:
                    time.sleep(3)
                    continue
                return 'error', 'empty response (auth?)', 0

            data = json.loads(result.stdout)
            if 'results' not in data:
                err = data.get('error', str(data)[:80])
                if attempt < retries:
                    time.sleep(3)
                    continue
                return 'error', err, 0

            results = data['results']
            if not results:
                return 'unknown', '', 0

            top = results[0]
            top_name = top.get('taxon', {}).get('name', '')
            score = top.get('combined_score', 0)

            exp = expected_scientific.lower()
            got = top_name.lower()

            if exp == got:
                return 'match', top_name, score
            if exp.split()[0] == got.split()[0]:
                return 'genus', top_name, score

            for canon, syns in SYNONYMS.items():
                all_names = [canon] + syns
                if exp in all_names and got in all_names:
                    return 'synonym', top_name, score

            return 'mismatch', top_name, score
        except Exception as e:
            if attempt < retries:
                time.sleep(3)
                continue
            return 'error', str(e)[:80], 0

    return 'error', 'max retries', 0


def main():
    limit = None
    retry_errors = '--retry-errors' in sys.argv
    for arg in sys.argv[1:]:
        if arg.startswith('--limit'):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        elif arg.isdigit():
            limit = int(arg)

    # Get already verified plant_ids
    if retry_errors:
        # Re-check only errors
        already = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'photo_verify' AND field = 'result' AND value != 'error'")
        already_set = set(r['plant_id'] for r in already)
        print(f"Retry mode: skipping {len(already_set)} already OK", flush=True)
    else:
        already = turso_query("SELECT DISTINCT plant_id FROM source_data WHERE source = 'photo_verify'")
        already_set = set(r['plant_id'] for r in already)
        print(f"Skipping {len(already_set)} already verified", flush=True)

    # Get first photo per plant (prefer account 2)
    photos = turso_query("""
        SELECT pi.plant_id, pi.image_url, p.scientific
        FROM plant_images pi
        JOIN plants p ON pi.plant_id = p.plant_id
        WHERE pi.image_type != 'flagged'
        AND pi.sort_order = (
            SELECT MIN(pi2.sort_order) FROM plant_images pi2
            WHERE pi2.plant_id = pi.plant_id AND pi2.image_type != 'flagged'
        )
        ORDER BY pi.plant_id
    """)

    # Filter already verified
    candidates = [p for p in photos if p['plant_id'] not in already_set]
    if limit:
        candidates = candidates[:limit]

    print(f"Verifying {len(candidates)} photos (total in DB: {len(photos)}, already done: {len(already_set)})", flush=True)

    if not candidates:
        print("Nothing to verify.", flush=True)
        return

    stats = {'match': 0, 'genus': 0, 'synonym': 0, 'mismatch': 0, 'unknown': 0, 'error': 0}
    stmts = []
    consecutive_errors = 0

    for i, p in enumerate(candidates):
        result, top_name, score = verify_photo(p['image_url'], p['scientific'])
        stats[result] += 1

        # Save result to source_data
        stmts.append((
            "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'photo_verify', 'result', ?, datetime('now'))",
            [p['plant_id'], result]
        ))
        if top_name:
            stmts.append((
                "INSERT OR REPLACE INTO source_data (plant_id, source, field, value, fetched_at) VALUES (?, 'photo_verify', 'cv_top_match', ?, datetime('now'))",
                [p['plant_id'], f"{top_name} ({score:.2f})"]
            ))

        if result == 'mismatch':
            print(f"  [{i+1}] MIS {p['plant_id']:35s} | {p['scientific']} -> {top_name} ({score:.1f})", flush=True)
            consecutive_errors = 0
        elif result == 'error':
            consecutive_errors += 1
            if consecutive_errors >= 5:
                print(f"  [{i+1}] 5 consecutive errors — stopping. Last: {top_name}", flush=True)
                break
        else:
            consecutive_errors = 0

        # Progress every 50
        if (i + 1) % 50 == 0:
            ok = stats['match'] + stats['genus'] + stats['synonym']
            print(f"  [{i+1}/{len(candidates)}] ok={ok} mis={stats['mismatch']} err={stats['error']}", flush=True)

        # Batch write every 100
        if len(stmts) >= 100:
            turso_batch(stmts)
            stmts = []

        time.sleep(1)

    if stmts:
        turso_batch(stmts)

    ok = stats['match'] + stats['genus'] + stats['synonym']
    total = sum(stats.values())
    print(f"\n=== RESULTS ===", flush=True)
    print(f"  match:    {stats['match']}", flush=True)
    print(f"  genus:    {stats['genus']}", flush=True)
    print(f"  synonym:  {stats['synonym']}", flush=True)
    print(f"  mismatch: {stats['mismatch']}", flush=True)
    print(f"  error:    {stats['error']}", flush=True)
    print(f"  Accuracy: {ok}/{total} ({ok * 100 // max(total, 1)}%)", flush=True)


if __name__ == '__main__':
    main()
