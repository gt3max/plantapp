// Plant DB types — Turso encyclopedia responses

export interface PlantDBCare {
  plant_id: string;
  water_frequency: string;
  water_winter: string;
  water_demand: string;
  start_pct: number;
  stop_pct: number;
  light_preferred: string;
  light_also_ok: string;
  ppfd_min: number;
  ppfd_max: number;
  dli_min: number;
  dli_max: number;
  temp_min_c: number;
  temp_max_c: number;
  humidity_level: string;
  humidity_min_pct: number;
  humidity_action: string;
  soil_types: string;
  soil_ph_min: number;
  soil_ph_max: number;
  repot_frequency: string;
  fertilizer_type: string;
  fertilizer_freq: string;
  fertilizer_season: string;
  height_min_cm: number;
  height_max_cm: number;
  lifecycle: string;
  difficulty: string;
  growth_rate: string;
  watering_guide: string;
  light_guide: string;
  tips: string;
  toxic_to_pets: number;
  toxic_to_humans: number;
  toxicity_note: string;
  common_problems: string[];
  common_pests: string[];
}

export interface PlantDBEntry {
  plant_id: string;
  scientific: string;
  family: string;
  genus: string;
  category: string;
  indoor: number;
  edible: number;
  has_phases: number;
  preset: string;
  image_url: string;
  description: string;
  wikidata_id: string;
  sources: string[];
  updated_at: string;
  care: PlantDBCare;
  common_names: Record<string, string[]>;
  tags: string[];
}

export interface PlantDBSearchResult {
  plant_id: string;
  scientific: string;
  family: string;
  preset: string;
  image_url: string;
  category: string;
  water_frequency: string;
  light_preferred: string;
  toxic_to_pets: number;
  toxic_to_humans: number;
  toxicity_note: string;
  common_name: string;
}

export interface PlantDBSearchResponse {
  results: PlantDBSearchResult[];
  count: number;
  query: string;
}

export interface PlantDBStats {
  total_plants: number;
  total_families: number;
  last_updated: string;
}
