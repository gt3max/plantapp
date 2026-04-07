"""
Batch verify ALL photos via iNaturalist CV.
Checks first photo of each plant against expected scientific name.
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

from turso_sync import turso_query

TOKEN = os.environ.get('INATURALIST_API_TOKEN', '')

SYNONYMS = {
    'dracaena trifasciata': ['sansevieria trifasciata'],
    'salvia rosmarinus': ['rosmarinus officinalis'],
    'schefflera arboricola': ['heptapleurum arboricola'],
    'streptocarpus ionanthus': ['saintpaulia ionantha'],
    'haworthiopsis attenuata': ['haworthia attenuata', 'haworthia fasciata'],
    'calathea orbifolia': ['goeppertia orbifolia'],
    'epipremnum aureum': ['pothos aureus', 'scindapsus aureus'],
}


def verify_photo(image_url, expected_scientific):
    try:
        urllib.request.urlretrieve(image_url, '/tmp/verify_photo.jpg')
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            'https://api.inaturalist.org/v1/computervision/score_image',
            '-F', 'image=@/tmp/verify_photo.jpg',
            '-H', f'Authorization: Bearer {TOKEN}',
        ], capture_output=True, text=True, timeout=30)

        data = json.loads(result.stdout)
        if 'results' not in data:
            return 'error', data.get('error', 'unknown'), 0

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
            if (exp == canon or exp in syns) and (got == canon or got in syns):
                return 'synonym', top_name, score

        return 'mismatch', top_name, score
    except Exception as e:
        return 'error', str(e)[:50], 0


def main():
    photos = turso_query("""
        SELECT pi.plant_id, pi.image_url, p.scientific
        FROM plant_images pi
        JOIN plants p ON pi.plant_id = p.plant_id
        GROUP BY pi.plant_id
        ORDER BY
            CASE WHEN pi.image_url LIKE '%doqqrf8z7%' THEN 0 ELSE 1 END,
            pi.plant_id
    """)

    print(f"Verifying {len(photos)} plants (1st photo each)...", flush=True)

    stats = {'match': 0, 'genus': 0, 'synonym': 0, 'mismatch': 0, 'unknown': 0, 'error': 0}
    mismatches = []

    for i, p in enumerate(photos):
        result, top_name, score = verify_photo(p['image_url'], p['scientific'])
        stats[result] += 1

        if result == 'mismatch':
            mismatches.append((p['plant_id'], p['scientific'], top_name, score))
            acct = '2' if 'doqqrf8z7' in p['image_url'] else '1'
            print(f"  [{i+1}] acct{acct} {p['plant_id']:35s} | MISMATCH: {p['scientific']} → {top_name} ({score:.1f})", flush=True)

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(photos)}] match={stats['match']} genus={stats['genus']} mismatch={stats['mismatch']} err={stats['error']}", flush=True)

        time.sleep(1)

    print(f"\n=== RESULTS ===", flush=True)
    total = sum(stats.values())
    ok = stats['match'] + stats['genus'] + stats['synonym']
    print(f"  match: {stats['match']}", flush=True)
    print(f"  genus: {stats['genus']}", flush=True)
    print(f"  synonym: {stats['synonym']}", flush=True)
    print(f"  mismatch: {stats['mismatch']}", flush=True)
    print(f"  unknown: {stats['unknown']}", flush=True)
    print(f"  error: {stats['error']}", flush=True)
    print(f"  Accuracy: {ok}/{total} ({ok * 100 // max(total, 1)}%)", flush=True)

    if mismatches:
        print(f"\nMISMATCHES ({len(mismatches)}):", flush=True)
        for pid, exp, got, sc in mismatches:
            print(f"  {pid:35s} | {exp:30s} → {got} ({sc:.1f})", flush=True)


if __name__ == '__main__':
    main()
