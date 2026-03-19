"""
Data models for plant records.
PlantRecord = canonical internal format for all plant data.
"""
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class CareData:
    water_frequency: str = ''
    water_winter: str = ''
    water_demand: str = ''          # low/medium/high
    start_pct: int = 0
    stop_pct: int = 0
    light_preferred: str = ''
    light_also_ok: str = ''
    ppfd_min: int = 0
    ppfd_max: int = 0
    dli_min: float = 0.0
    dli_max: float = 0.0
    temp_min_c: int = 0
    temp_max_c: int = 0
    humidity_level: str = ''
    humidity_min_pct: int = 0
    humidity_action: str = ''
    soil_types: str = ''
    soil_ph_min: float = 0.0
    soil_ph_max: float = 0.0
    repot_frequency: str = ''
    fertilizer_type: str = ''
    fertilizer_freq: str = ''
    fertilizer_season: str = ''
    height_min_cm: int = 0
    height_max_cm: int = 0
    lifecycle: str = ''             # perennial/annual/biennial
    difficulty: str = ''            # easy/moderate/hard
    growth_rate: str = ''           # slow/moderate/fast
    watering_guide: str = ''
    light_guide: str = ''
    tips: str = ''
    toxic_to_pets: bool = False
    toxic_to_humans: bool = False
    toxicity_note: str = ''
    common_problems: list[str] = field(default_factory=list)
    common_pests: list[str] = field(default_factory=list)

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
                   'sources', 'updated_at', 'common_names', 'tags', 'external_ids'):
            if k in d and d[k] is not None:
                setattr(rec, k, d[k])
        rec.care = care
        return rec
