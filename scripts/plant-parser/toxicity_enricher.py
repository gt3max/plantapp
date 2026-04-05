"""
toxicity_enricher.py — Smart toxicity data enrichment.

Parses existing toxicity_note and toxicity_symptoms to extract:
- toxic_parts (leaves, sap, fruit, seeds, all parts, etc.)
- toxicity_severity (Mild / Moderate / Severe)
- toxicity_first_aid (based on toxin type)
- Detailed breakdown by animal (cats, dogs, horses, humans)

Also applies family-based rules for unverified plants.

Usage:
    python3 toxicity_enricher.py              # enrich all plants with existing data
    python3 toxicity_enricher.py --plant X    # enrich one plant
    python3 toxicity_enricher.py --stats      # show coverage stats
"""
import re
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turso_sync import turso_query, turso_batch

# ── Toxic parts extraction keywords ──
PART_KEYWORDS = {
    'all parts': 'All parts',
    'entire plant': 'All parts',
    'whole plant': 'All parts',
    'leaves': 'Leaves',
    'leaf': 'Leaves',
    'foliage': 'Leaves/Foliage',
    'stems': 'Stems',
    'stem': 'Stems',
    'sap': 'Sap/Latex',
    'latex': 'Sap/Latex',
    'milky': 'Sap/Latex',
    'bark': 'Bark',
    'roots': 'Roots',
    'root': 'Roots',
    'rhizome': 'Roots/Rhizome',
    'bulb': 'Bulb',
    'fruit': 'Fruit',
    'berry': 'Berries',
    'berries': 'Berries',
    'seed': 'Seeds',
    'seeds': 'Seeds',
    'flower': 'Flowers',
    'flowers': 'Flowers',
    'pollen': 'Pollen',
    'tuber': 'Tuber',
}

# ── Severity keywords ──
SEVERE_WORDS = ['death', 'fatal', 'kidney failure', 'liver failure', 'cardiac',
                'seizure', 'collapse', 'coma', 'respiratory failure', 'heart']
MODERATE_WORDS = ['vomiting', 'diarrhea', 'tremor', 'difficulty breathing',
                  'depression', 'anorexia', 'drooling', 'hypersalivation',
                  'swelling', 'pain', 'abdominal']
MILD_WORDS = ['irritation', 'dermatitis', 'rash', 'mild', 'discomfort',
              'nausea', 'salivation']

# ── Toxin types → first aid ──
TOXIN_FIRST_AID = {
    'calcium oxalate': 'Rinse mouth with water. Give water or milk to drink. If swelling of mouth/throat occurs or difficulty breathing, seek emergency veterinary care immediately.',
    'oxalate': 'Rinse mouth with water. Give water or milk to drink. If swelling persists, call vet.',
    'saponin': 'Monitor for vomiting and diarrhea. Provide fresh water. Call vet if symptoms are severe or persist more than 24 hours.',
    'cardiac glycoside': 'EMERGENCY — seek immediate veterinary care. Cardiac glycosides can cause fatal heart rhythm changes. Do NOT induce vomiting without vet guidance.',
    'solanine': 'Remove plant material from mouth. Monitor for vomiting and neurological symptoms. Call vet if ingested in significant quantity.',
    'general': 'Remove any remaining plant material from mouth. Rinse with water. Monitor for symptoms (vomiting, drooling, lethargy). Call poison control or vet if symptoms appear.',
}

# ── Family-based toxin info ──
FAMILY_TOXINS = {
    'Araceae': {'toxin': 'calcium oxalate', 'parts': 'All parts (leaves, stems, sap)',
                'symptoms': 'Oral irritation, pain and swelling of mouth, tongue and lips, excessive drooling, difficulty swallowing'},
    'Euphorbiaceae': {'toxin': 'diterpene esters', 'parts': 'Sap/Latex',
                      'symptoms': 'Skin irritation, eye damage on contact, vomiting and diarrhea if ingested'},
    'Liliaceae': {'toxin': 'various alkaloids', 'parts': 'All parts (especially bulbs)',
                  'symptoms': 'Vomiting, lethargy, kidney failure (cats especially susceptible)'},
    'Solanaceae': {'toxin': 'solanine/glycoalkaloids', 'parts': 'Leaves, stems, unripe fruit',
                   'symptoms': 'Vomiting, diarrhea, confusion, drowsiness'},
    'Apocynaceae': {'toxin': 'cardiac glycosides', 'parts': 'All parts (especially sap)',
                    'symptoms': 'Irregular heartbeat, vomiting, diarrhea. Potentially fatal.'},
    'Cycadaceae': {'toxin': 'cycasin', 'parts': 'All parts (especially seeds)',
                   'symptoms': 'Vomiting, diarrhea, liver failure, seizures. Can be fatal.'},
}


def extract_toxic_parts(text):
    """Extract which parts of the plant are toxic from text."""
    if not text:
        return ''
    text_lower = text.lower()
    parts = set()
    for keyword, part_name in PART_KEYWORDS.items():
        if keyword in text_lower:
            parts.add(part_name)
    # If "all parts" found, just return that
    if 'All parts' in parts:
        return 'All parts'
    return ', '.join(sorted(parts)) if parts else ''


def determine_severity(symptoms_text, note_text=''):
    """Determine toxicity severity from symptoms text."""
    text = f"{symptoms_text or ''} {note_text or ''}".lower()
    if not text.strip():
        return ''

    if any(w in text for w in SEVERE_WORDS):
        return 'Severe'
    if any(w in text for w in MODERATE_WORDS):
        return 'Moderate'
    if any(w in text for w in MILD_WORDS):
        return 'Mild'
    return 'Moderate'  # Default if toxic but can't determine


def determine_first_aid(symptoms_text, note_text='', family=''):
    """Generate first aid advice based on toxin type."""
    text = f"{symptoms_text or ''} {note_text or ''}".lower()

    for toxin, advice in TOXIN_FIRST_AID.items():
        if toxin in text:
            return advice

    # Check family-based toxin
    if family in FAMILY_TOXINS:
        toxin = FAMILY_TOXINS[family]['toxin']
        for t, advice in TOXIN_FIRST_AID.items():
            if t in toxin:
                return advice

    return TOXIN_FIRST_AID['general']


def enrich_plant(plant_id, force=False):
    """Enrich toxicity data for a single plant."""
    r = turso_query('''SELECT c.toxic_to_pets, c.toxic_to_humans, c.toxicity_note,
        c.toxicity_symptoms, c.toxicity_severity, c.toxic_parts, c.toxicity_first_aid,
        p.family
        FROM care c JOIN plants p ON c.plant_id = p.plant_id
        WHERE c.plant_id = ?''', [plant_id])

    if not r:
        return False

    c = r[0]
    is_toxic = bool(c.get('toxic_to_pets')) or bool(c.get('toxic_to_humans'))
    note = c.get('toxicity_note') or ''
    symptoms = c.get('toxicity_symptoms') or ''
    family = c.get('family') or ''
    current_parts = c.get('toxic_parts') or ''
    current_severity = c.get('toxicity_severity') or ''
    current_first_aid = c.get('toxicity_first_aid') or ''

    if not is_toxic and family not in FAMILY_TOXINS:
        return False  # Not toxic and not in toxic family — skip

    updates = {}

    # Extract toxic parts
    if not current_parts or force:
        parts = extract_toxic_parts(f"{note} {symptoms}")
        if not parts and family in FAMILY_TOXINS:
            parts = FAMILY_TOXINS[family]['parts']
        if parts:
            updates['toxic_parts'] = parts

    # Determine severity
    if not current_severity or force:
        severity = determine_severity(symptoms, note)
        if not severity and family in FAMILY_TOXINS:
            # Derive from family
            fam_symptoms = FAMILY_TOXINS[family]['symptoms']
            severity = determine_severity(fam_symptoms)
        if severity:
            updates['toxicity_severity'] = severity

    # Generate first aid
    if not current_first_aid or force:
        first_aid = determine_first_aid(symptoms, note, family)
        if first_aid:
            updates['toxicity_first_aid'] = first_aid

    # If plant is in toxic family but marked safe — add note
    if not is_toxic and family in FAMILY_TOXINS and 'Caution' not in note:
        fam_info = FAMILY_TOXINS[family]
        updates['toxicity_note'] = f"Caution: {family} family. Toxic compound: {fam_info['toxin']}. {fam_info['symptoms']}"
        updates['toxic_parts'] = fam_info['parts']
        updates['toxicity_severity'] = determine_severity(fam_info['symptoms'])
        updates['toxicity_first_aid'] = determine_first_aid('', '', family)

    if updates:
        stmts = []
        for field, value in updates.items():
            stmts.append((
                f"UPDATE care SET {field} = CASE WHEN {field} IS NULL OR {field} = '' THEN ? ELSE {field} END WHERE plant_id = ?",
                [value, plant_id]
            ))
        turso_batch(stmts)
        return True

    return False


def enrich_all(limit=None):
    """Enrich toxicity for all plants."""
    # Get all plants that have some toxicity data or are in toxic families
    rows = turso_query('''
        SELECT p.plant_id FROM plants p
        JOIN care c ON p.plant_id = c.plant_id
        WHERE c.toxic_to_pets = 1 OR c.toxic_to_humans = 1
           OR p.family IN ('Araceae','Euphorbiaceae','Solanaceae','Liliaceae','Apocynaceae','Cycadaceae')
        ORDER BY p.plant_id
    ''')

    if limit:
        rows = rows[:limit]

    enriched = 0
    for row in rows:
        if enrich_plant(row['plant_id']):
            enriched += 1

    print(f'Enriched toxicity for {enriched} plants')
    return enriched


def show_stats():
    """Show toxicity coverage stats."""
    total = 20257
    fields = [
        ('toxic_to_pets=1', "toxic_to_pets = 1"),
        ('toxic_to_humans=1', "toxic_to_humans = 1"),
        ('toxicity_note filled', "toxicity_note IS NOT NULL AND toxicity_note != ''"),
        ('toxicity_symptoms', "toxicity_symptoms IS NOT NULL AND toxicity_symptoms != ''"),
        ('toxicity_severity', "toxicity_severity IS NOT NULL AND toxicity_severity != ''"),
        ('toxic_parts', "toxic_parts IS NOT NULL AND toxic_parts != ''"),
        ('toxicity_first_aid', "toxicity_first_aid IS NOT NULL AND toxicity_first_aid != ''"),
    ]
    for label, where in fields:
        cnt = turso_query(f"SELECT COUNT(*) as cnt FROM care WHERE {where}")[0]['cnt']
        print(f'  {label:25s}: {cnt:6d} ({cnt*100/total:.1f}%)')


if __name__ == '__main__':
    if '--stats' in sys.argv:
        show_stats()
    elif '--plant' in sys.argv:
        idx = sys.argv.index('--plant')
        pid = sys.argv[idx + 1]
        result = enrich_plant(pid, force=True)
        print(f'{pid}: {"enriched" if result else "no changes"}')
        # Show result
        r = turso_query('SELECT toxic_parts, toxicity_severity, toxicity_first_aid FROM care WHERE plant_id = ?', [pid])
        if r:
            print(f'  parts:     {r[0].get("toxic_parts")}')
            print(f'  severity:  {r[0].get("toxicity_severity")}')
            print(f'  first_aid: {(r[0].get("toxicity_first_aid") or "")[:80]}')
    else:
        enrich_all()
        print('\nAfter enrichment:')
        show_stats()
