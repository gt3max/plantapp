// Adapter: PlantDBEntry → PresetCare (for Plant Detail screen)
import type { PresetCare } from '../constants/presets';
import type { PlantDBCare, PlantDBEntry } from '../types/plant-db';

/**
 * Convert Turso plant DB care data to PresetCare format.
 * Falls back to preset defaults for missing fields.
 */
export function dbCareToPresetCare(care: PlantDBCare, presetDefaults: PresetCare): PresetCare {
  return {
    name: presetDefaults.name,
    start_pct: care.start_pct || presetDefaults.start_pct,
    stop_pct: care.stop_pct || presetDefaults.stop_pct,
    watering: care.water_frequency || presetDefaults.watering,
    watering_winter: care.water_winter || presetDefaults.watering_winter,
    light: care.light_preferred || presetDefaults.light,
    light_also_ok: care.light_also_ok || presetDefaults.light_also_ok,
    ppfd_min: care.ppfd_min || presetDefaults.ppfd_min,
    ppfd_max: care.ppfd_max || presetDefaults.ppfd_max,
    dli_min: care.dli_min || presetDefaults.dli_min,
    dli_max: care.dli_max || presetDefaults.dli_max,
    temperature: care.temp_min_c && care.temp_max_c
      ? `${care.temp_min_c}-${care.temp_max_c}\u00B0C`
      : presetDefaults.temperature,
    humidity: care.humidity_level || presetDefaults.humidity,
    humidity_action: care.humidity_action || presetDefaults.humidity_action,
    soil: care.soil_types || presetDefaults.soil,
    repot: care.repot_frequency || presetDefaults.repot,
    fertilizer: care.fertilizer_type || presetDefaults.fertilizer,
    fertilizer_season: care.fertilizer_season || presetDefaults.fertilizer_season,
    tips: care.tips || presetDefaults.tips,
    common_problems: care.common_problems?.length ? care.common_problems : presetDefaults.common_problems,
    common_pests: care.common_pests?.length ? care.common_pests : presetDefaults.common_pests,
  };
}

/**
 * Extract common name from DB entry (English primary).
 */
export function getCommonName(entry: PlantDBEntry): string {
  const en = entry.common_names?.en;
  return en?.[0] ?? entry.scientific;
}
