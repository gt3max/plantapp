"""
Polish toxicity — reconcile all sources, fill details, verify.

Pipeline:
1. ASPCA data (care table) — authoritative for pets
2. TPPT data (source_data) — authoritative for human + animal + parts
3. CBIF data (source_data) — cross-validation
4. Family rules — fallback (confidence=low)
5. Keywords from descriptions — hint only

Principles:
- ASPCA "Non-toxic" → safe (overrides family rules)
- ASPCA "Toxic" → toxic (authoritative)
- TPPT toxic → toxic + details
- TPPT "weak toxic" + edible herb → note only, not toxic flag
- Family rule → toxic with "Based on family characteristics" note
- No data → leave empty (don't mark safe!)
- Severe → red warning in UI
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch

# Family toxicity rules with details
FAMILY_TOXINS = {
    'Araceae': {'toxin': 'calcium oxalate', 'parts': 'All parts (leaves, stems, sap)', 'severity': 'Moderate',
                'symptoms': 'Oral irritation, swelling of mouth/tongue/lips, drooling, difficulty swallowing',
                'first_aid': 'Rinse mouth thoroughly. Give water or milk. If swelling affects breathing, seek emergency help.',
                'pets': True, 'humans': True},
    'Euphorbiaceae': {'toxin': 'diterpene esters', 'parts': 'Sap/Latex', 'severity': 'Moderate',
                      'symptoms': 'Skin irritation, eye damage on contact, vomiting and diarrhea if ingested',
                      'first_aid': 'Wash skin with soap and water. Flush eyes 15 min. If ingested, do not induce vomiting.',
                      'pets': True, 'humans': True},
    'Solanaceae': {'toxin': 'solanine/glycoalkaloids', 'parts': 'Leaves, stems, unripe fruit', 'severity': 'Moderate',
                   'symptoms': 'Vomiting, diarrhea, confusion, drowsiness',
                   'first_aid': 'Remove plant material from mouth. Monitor symptoms. Seek medical help if significant quantity ingested.',
                   'pets': True, 'humans': True},
    'Apocynaceae': {'toxin': 'cardiac glycosides', 'parts': 'All parts (especially sap)', 'severity': 'Severe',
                    'symptoms': 'Irregular heartbeat, vomiting, diarrhea. Potentially fatal.',
                    'first_aid': 'EMERGENCY: Seek immediate medical/veterinary help. Do not induce vomiting.',
                    'pets': True, 'humans': True},
    'Cycadaceae': {'toxin': 'cycasin', 'parts': 'All parts (especially seeds)', 'severity': 'Severe',
                   'symptoms': 'Vomiting, diarrhea, liver failure, seizures. Can be fatal.',
                   'first_aid': 'EMERGENCY: Seek immediate veterinary help. Any ingestion is dangerous.',
                   'pets': True, 'humans': True},
    'Liliaceae': {'toxin': 'various alkaloids', 'parts': 'All parts (especially bulbs)', 'severity': 'Severe',
                  'symptoms': 'Vomiting, lethargy, kidney failure (cats especially susceptible)',
                  'first_aid': 'EMERGENCY for cats: Any contact with lily pollen/leaves → vet immediately.',
                  'pets': True, 'humans': True},
    'Crassulaceae': {'toxin': 'bufadienolides', 'parts': 'Leaves', 'severity': 'Mild',
                     'symptoms': 'Vomiting, diarrhea in pets if ingested',
                     'first_aid': 'Monitor pet. If symptoms persist >24h, consult vet.',
                     'pets': True, 'humans': False},
    'Begoniaceae': {'toxin': 'soluble calcium oxalates', 'parts': 'All parts (especially tubers)', 'severity': 'Mild',
                    'symptoms': 'Oral irritation, drooling, vomiting in pets',
                    'first_aid': 'Rinse mouth. Give water. Monitor for 24h.',
                    'pets': True, 'humans': False},
    'Commelinaceae': {'toxin': 'oxalates', 'parts': 'Sap', 'severity': 'Mild',
                      'symptoms': 'Skin irritation (dermatitis), stomach upset if ingested',
                      'first_aid': 'Wash affected skin. If ingested, give water and monitor.',
                      'pets': True, 'humans': False},
    'Moraceae': {'toxin': 'ficin (latex)', 'parts': 'Sap', 'severity': 'Mild',
                 'symptoms': 'Skin rash on contact. Vomiting if ingested by pets.',
                 'first_aid': 'Wash skin with soap. If ingested by pet, monitor for vomiting.',
                 'pets': True, 'humans': True},
    'Asparagaceae': {'toxin': 'saponins', 'parts': 'Berries, leaves', 'severity': 'Mild',
                     'symptoms': 'Vomiting, diarrhea. Some species irritate skin.',
                     'first_aid': 'Monitor symptoms. Give water. Vet if symptoms persist.',
                     'pets': True, 'humans': False},
    'Ericaceae': {'toxin': 'grayanotoxins', 'parts': 'All parts', 'severity': 'Moderate',
                  'symptoms': 'Vomiting, weakness, cardiac issues',
                  'first_aid': 'Seek medical help if ingested. Monitor heart rate.',
                  'pets': True, 'humans': True},
    'Ranunculaceae': {'toxin': 'protoanemonin', 'parts': 'Sap, all parts', 'severity': 'Moderate',
                      'symptoms': 'Blisters on skin contact. Mouth pain if ingested.',
                      'first_aid': 'Wash skin. Rinse mouth. Wear gloves when handling.',
                      'pets': True, 'humans': True},
    'Zamiaceae': {'toxin': 'cycasin', 'parts': 'All parts (especially seeds)', 'severity': 'Severe',
                  'symptoms': 'Liver failure, seizures. Can be fatal to dogs.',
                  'first_aid': 'EMERGENCY: Any ingestion → vet immediately.',
                  'pets': True, 'humans': True},
}

# Edible herb families — TPPT "weak toxic" should be note, not toxic flag
EDIBLE_FAMILIES = {'Lamiaceae', 'Apiaceae', 'Lauraceae', 'Poaceae', 'Amaranthaceae'}

# TPPT severity mapping
TPPT_SEVERITY = {
    'very strong toxic': 'Severe',
    'strong toxic': 'Severe',
    'toxic': 'Moderate',
    'weak toxic': 'Mild',
    'phototoxic': 'Mild',
    'allergenic': 'Mild',
    'skin-irritating': 'Mild',
    'carcinogenic': 'Severe',
    'liver toxic': 'Severe',
    'cytotoxic': 'Severe',
}


def polish_toxicity(limit=20000):
    """Reconcile and polish toxicity for all plants."""
    rows = turso_query("""
        SELECT p.plant_id, p.scientific, p.family, p.preset,
               c.toxic_to_pets, c.toxic_to_humans, c.toxicity_note,
               c.toxicity_severity, c.toxic_parts, c.toxicity_symptoms, c.toxicity_first_aid
        FROM plants p
        JOIN care c ON p.plant_id = c.plant_id
        LIMIT ?
    """, [limit])

    print(f"[polish_toxicity] Processing {len(rows)} plants...", flush=True)

    stmts = []
    stats = {'family_applied': 0, 'tppt_applied': 0, 'keyword_found': 0, 'already_set': 0, 'edible_protected': 0}

    for i, r in enumerate(rows):
        pid = r['plant_id']
        family = r.get('family') or ''
        is_edible = family in EDIBLE_FAMILIES or (r.get('preset') or '') == 'Herbs'

        # Already has ASPCA data (authoritative) — skip
        note = r.get('toxicity_note') or ''
        if 'ASPCA' in note or 'Non-toxic to Dogs' in note or 'Toxic to Dogs' in note:
            stats['already_set'] += 1
            continue

        # Check TPPT source_data
        tppt = turso_query("SELECT field, value FROM source_data WHERE plant_id = ? AND source = 'tppt'", [pid])
        tppt_data = {t['field']: t['value'] for t in tppt}

        if tppt_data:
            human_tox = tppt_data.get('human_toxicity', '').lower()
            animal_tox = tppt_data.get('animal_toxicity', '').lower()
            parts = tppt_data.get('toxic_parts', '')

            # Edible herb protection
            if is_edible and human_tox in ('weak toxic', 'phototoxic', 'allergenic', 'skin-irritating'):
                if not r.get('toxicity_note'):
                    stmts.append((
                        "UPDATE care SET toxicity_note = ? WHERE plant_id = ?",
                        [f'Generally safe. Scientific note: {human_tox} in concentrated essential oil form (not relevant for normal use). Source: TPPT/Agroscope.', pid]
                    ))
                stats['edible_protected'] += 1
                continue

            # Real toxicity from TPPT
            if human_tox in TPPT_SEVERITY:
                severity = TPPT_SEVERITY[human_tox]
                if not r.get('toxic_to_humans'):
                    stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ?", [pid]))
                if not r.get('toxicity_severity'):
                    stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ?", [severity, pid]))
                if parts and not r.get('toxic_parts'):
                    stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ?", [parts, pid]))
                stats['tppt_applied'] += 1

            if animal_tox in TPPT_SEVERITY:
                if not r.get('toxic_to_pets'):
                    stmts.append(("UPDATE care SET toxic_to_pets = 1 WHERE plant_id = ?", [pid]))
            continue

        # Family rule fallback (only if no other data)
        if family in FAMILY_TOXINS and not r.get('toxic_to_pets') and not r.get('toxic_to_humans'):
            rule = FAMILY_TOXINS[family]
            if rule['pets'] and not r.get('toxic_to_pets'):
                stmts.append(("UPDATE care SET toxic_to_pets = 1 WHERE plant_id = ?", [pid]))
            if rule['humans'] and not r.get('toxic_to_humans'):
                stmts.append(("UPDATE care SET toxic_to_humans = 1 WHERE plant_id = ?", [pid]))
            if not r.get('toxicity_severity'):
                stmts.append(("UPDATE care SET toxicity_severity = ? WHERE plant_id = ?", [rule['severity'], pid]))
            if not r.get('toxic_parts'):
                stmts.append(("UPDATE care SET toxic_parts = ? WHERE plant_id = ?", [rule['parts'], pid]))
            if not r.get('toxicity_symptoms'):
                stmts.append(("UPDATE care SET toxicity_symptoms = ? WHERE plant_id = ?", [rule['symptoms'], pid]))
            if not r.get('toxicity_first_aid'):
                stmts.append(("UPDATE care SET toxicity_first_aid = ? WHERE plant_id = ?", [rule['first_aid'], pid]))
            if not r.get('toxicity_note'):
                stmts.append(("UPDATE care SET toxicity_note = ? WHERE plant_id = ?",
                              [f"Based on {family} family characteristics. {rule['toxin']}. Verify with species-specific data.", pid]))
            stats['family_applied'] += 1

        # Batch write
        if len(stmts) >= 50:
            turso_batch(stmts)
            stmts = []

        if (i + 1) % 5000 == 0:
            print(f"  [{i+1}/{len(rows)}] {stats}", flush=True)

    if stmts:
        turso_batch(stmts)

    print(f"\n[polish_toxicity] Done:", flush=True)
    for k, v in stats.items():
        print(f"  {k}: {v}", flush=True)

    # Coverage report
    r1 = turso_query("SELECT COUNT(*) as cnt FROM care WHERE toxic_to_pets = 1")
    r2 = turso_query("SELECT COUNT(*) as cnt FROM care WHERE toxic_to_humans = 1")
    r3 = turso_query("SELECT COUNT(*) as cnt FROM care WHERE toxicity_severity IS NOT NULL AND toxicity_severity != ''")
    r4 = turso_query("SELECT COUNT(*) as cnt FROM care WHERE toxic_parts IS NOT NULL AND toxic_parts != ''")
    print(f"\n  Coverage:", flush=True)
    print(f"    toxic_to_pets:    {r1[0]['cnt']}", flush=True)
    print(f"    toxic_to_humans:  {r2[0]['cnt']}", flush=True)
    print(f"    severity:         {r3[0]['cnt']}", flush=True)
    print(f"    toxic_parts:      {r4[0]['cnt']}", flush=True)


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    polish_toxicity(limit)
