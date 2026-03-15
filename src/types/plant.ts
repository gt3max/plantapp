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
  // Live data from device (if active)
  moisture_pct?: number | null;
  battery_pct?: number | null;
  battery_charging?: boolean;
  device_online?: boolean;
  device_mode?: string;
}

export interface IdentifyResult {
  name: string;
  scientific_name: string;
  confidence: number;
  family?: string;
  description?: string;
  care?: PlantCareInfo;
  photo_url?: string;
}

export interface PlantCareInfo {
  light: string;
  watering: string;
  temperature: string;
  humidity: string;
  soil: string;
  fertilizing: string;
  toxic_to_pets: boolean;
  toxic_to_humans: boolean;
  common_problems: string[];
}
