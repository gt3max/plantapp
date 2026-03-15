// Plant library entry (from GET /plants/library)
export interface PlantEntry {
  plant_id: string;
  scientific?: string;
  common_name?: string;
  family?: string;
  image_url?: string;
  preset?: string;
  start_pct?: number;
  stop_pct?: number;
  poisonous_to_pets?: boolean;
  poisonous_to_humans?: boolean;
  toxicity_note?: string;
  started_at?: string;
  ended_at?: string;
  created_at?: string;
  saved_at?: number;
  archived?: boolean;
  deleted?: boolean;
  active: boolean;       // true = currently on device, false = in library
  device_id: string;
  device_location?: string;
  device_room?: string;
}

// Enriched plant for UI (plant + live device data)
export interface PlantWithDevice extends PlantEntry {
  moisture_pct?: number | null;
  battery_pct?: number | null;
  battery_charging?: boolean;
  device_online?: boolean;
  device_mode?: string;
}

// --- Identify API types (match backend POST /plants/identify response) ---

export interface IdentifyResult {
  id: string;
  scientific: string;
  commonNames: string[];
  family: string;
  genus: string;
  score: number;              // 0-100
  images: string[];           // PlantNet reference photo URLs
  care: IdentifyCareSummary;
  toxicity: ToxicityInfo | null;
}

export interface IdentifyCareSummary {
  preset: string;             // 'Succulents' | 'Standard' | 'Tropical' | 'Herbs'
  start_pct: number;
  stop_pct: number;
  watering: string;
  light: string;
  temperature: string;
  humidity: string;
  tips: string;
}

export interface ToxicityInfo {
  poisonous_to_pets: boolean;
  poisonous_to_humans: boolean;
  toxicity_note: string;
}

export interface IdentifyResponse {
  success: boolean;
  results: IdentifyResult[];
  source: string;
}

// --- Save API types (match backend POST /plants/save) ---

export interface SavePlantInput {
  device_id: string;
  plant: {
    scientific: string;
    common_name: string;
    family?: string;
    preset?: string;
    start_pct?: number;
    stop_pct?: number;
    image_url?: string;
    poisonous_to_pets?: boolean;
    poisonous_to_humans?: boolean;
    toxicity_note?: string;
  };
}
