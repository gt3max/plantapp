"""
Data models for plant records.
PlantRecord = canonical internal format for all plant data.
"""
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class CareData:
    # ── Water ──
    water_frequency: str = ''
    water_winter: str = ''
    water_demand: str = ''          # low/medium/high
    watering_method: str = ''       # "Water over soil at base, avoid wetting leaves"
    watering_avoid: str = ''        # "#1 mistake: overwatering kills roots"
    watering_guide: str = ''
    start_pct: int = 0              # soil moisture sensor start %
    stop_pct: int = 0               # soil moisture sensor stop %

    # ── Light ──
    light_preferred: str = ''
    light_also_ok: str = ''
    ppfd_min: int = 0
    ppfd_max: int = 0
    dli_min: float = 0.0
    dli_max: float = 0.0
    light_guide: str = ''

    # ── Temperature ──
    temp_min_c: int = 0             # survival minimum
    temp_max_c: int = 0             # survival maximum
    temp_opt_low_c: int = 0         # ideal range low
    temp_opt_high_c: int = 0        # ideal range high
    temp_winter_low_c: int = 0      # winter regime low
    temp_winter_high_c: int = 0     # winter regime high
    temp_warning: str = ''          # "Below 10°C kills basil"

    # ── Humidity ──
    humidity_level: str = ''
    humidity_min_pct: int = 0
    humidity_action: str = ''

    # ── Soil & Repotting ──
    soil_types: str = ''
    soil_ph_min: float = 0.0
    soil_ph_max: float = 0.0
    pot_type: str = ''              # "Terracotta — lets soil breathe"
    pot_size_note: str = ''         # "Prefers snug pot"
    repot_frequency: str = ''
    repot_signs: str = ''           # "Roots growing out of drainage holes"

    # ── Fertilizing ──
    fertilizer_type: str = ''
    fertilizer_freq: str = ''
    fertilizer_season: str = ''
    fertilizer_npk: str = ''        # "10-10-10 or 2-7-7"
    fertilizer_warning: str = ''    # "Over-fertilizing causes salt buildup"

    # ── Size ──
    height_min_cm: int = 0
    height_max_cm: int = 0
    height_indoor_max_cm: int = 0
    spread_max_cm: int = 0

    # ── Lifecycle & Difficulty ──
    lifecycle: str = ''             # perennial/annual/biennial
    difficulty: str = ''            # easy/moderate/hard
    difficulty_note: str = ''       # "Tolerates neglect. #1 killer: overwatering"
    growth_rate: str = ''           # slow/moderate/fast

    # ── Toxicity ──
    toxic_to_pets: bool = False
    toxic_to_humans: bool = False
    toxicity_note: str = ''
    toxic_parts: str = ''           # "All parts (leaves, stems, sap)"
    toxicity_severity: str = ''     # mild/moderate/severe
    toxicity_symptoms: str = ''     # "Vomiting, lethargy, diarrhea"
    toxicity_first_aid: str = ''    # "Rinse mouth, call vet if symptoms persist"

    # ── Used for ──
    used_for: list[str] = field(default_factory=list)        # ["Decorative", "Aromatic"]
    used_for_details: str = ''

    # ── Harvest (edible only) ──
    edible_parts: str = ''          # "Leaves, flowers, seeds"
    harvest_info: str = ''          # "Harvest from top, cutting above leaf pair"

    # ── Pruning ──
    pruning_info: str = ''          # Dedicated pruning field (not buried in tips)

    # ── Propagation ──
    propagation_methods: list[str] = field(default_factory=list)  # ["Seeds", "Stem cuttings"]
    propagation_detail: str = ''    # Step-by-step instructions
    germination_days: int = 0
    germination_temp_c: str = ''    # "20-25°C"

    # ── Companions ──
    good_companions: list[str] = field(default_factory=list)
    bad_companions: list[str] = field(default_factory=list)
    companion_note: str = ''        # "Basil repels aphids from tomatoes"

    # ── Problems & Pests (for AI Doctor prep) ──
    common_problems: list[str] = field(default_factory=list)
    common_pests: list[str] = field(default_factory=list)

    # ── Tips / Guides ──
    tips: str = ''

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if isinstance(v, list):
                d[k] = json.dumps(v) if v else None
            elif isinstance(v, bool):
                d[k] = 1 if v else 0
            elif v:
                d[k] = v
            else:
                d[k] = None
        return d


@dataclass
class PlantRecord:
    plant_id: str                   # e.g. 'monstera_deliciosa'
    scientific: str                 # 'Monstera deliciosa'
    family: str                     # 'Araceae'
    genus: str = ''
    category: str = 'decorative'    # decorative/greens/fruiting
    indoor: bool = True
    edible: bool = False
    has_phases: bool = False
    preset: str = 'Standard'
    image_url: str = ''
    description: str = ''
    wikidata_id: str = ''
    origin: str = ''                # "South Africa, Mozambique"
    order_name: str = ''            # Taxonomic order (Saxifragales, Lamiales, etc.)
    synonyms: list[str] = field(default_factory=list)  # Scientific name synonyms
    sources: list[str] = field(default_factory=list)
    updated_at: str = ''

    # Common names: {lang: [names]}
    common_names: dict[str, list[str]] = field(default_factory=dict)

    # Tags: ['indoor', 'tropical', 'pet-safe', ...]
    tags: list[str] = field(default_factory=list)

    # Care data
    care: CareData = field(default_factory=CareData)

    # External IDs: {source: id}
    external_ids: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to flat dict for JSON serialization."""
        return {
            'plant_id': self.plant_id,
            'scientific': self.scientific,
            'family': self.family,
            'genus': self.genus,
            'category': self.category,
            'indoor': self.indoor,
            'edible': self.edible,
            'has_phases': self.has_phases,
            'preset': self.preset,
            'image_url': self.image_url,
            'description': self.description,
            'wikidata_id': self.wikidata_id,
            'origin': self.origin,
            'order_name': self.order_name,
            'synonyms': self.synonyms,
            'sources': self.sources,
            'updated_at': self.updated_at,
            'common_names': self.common_names,
            'tags': self.tags,
            'care': self.care.to_dict(),
            'external_ids': self.external_ids,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'PlantRecord':
        """Restore from JSON dict."""
        care_dict = d.get('care', {})
        care = CareData()
        for k, v in care_dict.items():
            if hasattr(care, k):
                field_type = type(getattr(care, k))
                if field_type == list and isinstance(v, str):
                    setattr(care, k, json.loads(v))
                elif field_type == bool:
                    setattr(care, k, bool(v))
                elif v is not None:
                    setattr(care, k, v)

        rec = cls(
            plant_id=d['plant_id'],
            scientific=d['scientific'],
            family=d['family'],
        )
        for k in ('genus', 'category', 'indoor', 'edible', 'has_phases',
                   'preset', 'image_url', 'description', 'wikidata_id',
                   'origin', 'order_name', 'synonyms',
                   'sources', 'updated_at', 'common_names', 'tags', 'external_ids'):
            if k in d and d[k] is not None:
                setattr(rec, k, d[k])
        rec.care = care
        return rec
