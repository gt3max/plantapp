// Preset care details — matches backend PRESET_DETAILS
// Used for Plant Detail screen when viewing from Library (no API call needed)
// PPFD ranges from LI-COR literature + Mulyarchik spectroradiometer data

export interface PresetCare {
  name: string;
  start_pct: number;
  stop_pct: number;
  watering: string;
  watering_winter: string;
  light: string;
  light_also_ok: string;
  ppfd_min: number;            // µmol/m²/s
  ppfd_max: number;
  dli_min: number;             // mol/m²/day (Daily Light Integral)
  dli_max: number;
  temperature: string;
  humidity: string;
  humidity_action: string;     // what to DO about humidity
  soil: string;
  repot: string;
  fertilizer: string;
  fertilizer_season: string;
  tips: string;
  common_problems: string[];
  common_pests: string[];
}

export const PRESET_CARE: Record<string, PresetCare> = {
  Succulents: {
    name: 'Succulents',
    start_pct: 15,
    stop_pct: 25,
    watering: 'Every 2-3 weeks',
    watering_winter: 'Once a month',
    light: 'Bright direct or indirect light',
    light_also_ok: 'Part shade (tolerates)',
    ppfd_min: 200,
    ppfd_max: 600,
    dli_min: 8,
    dli_max: 20,
    temperature: '18-27\u00B0C (65-80\u00B0F)',
    humidity: 'Low (30-40%)',
    humidity_action: 'Normal room humidity is fine. No misting needed.',
    soil: 'Well-draining cactus/succulent mix',
    repot: 'Every 2-3 years',
    fertilizer: 'Once in spring and summer',
    fertilizer_season: 'Spring-Summer only',
    tips: 'Let soil dry completely between waterings. Overwatering is the #1 killer.',
    common_problems: ['Root rot (overwatering)', 'Etiolation (stretching)', 'Sunburn'],
    common_pests: ['Mealybugs', 'Scale', 'Fungus gnats'],
  },
  Standard: {
    name: 'Standard',
    start_pct: 35,
    stop_pct: 55,
    watering: 'Every 7-10 days',
    watering_winter: 'Every 2 weeks',
    light: 'Bright indirect light',
    light_also_ok: 'Shade tolerant',
    ppfd_min: 100,
    ppfd_max: 300,
    dli_min: 4,
    dli_max: 12,
    temperature: '18-24\u00B0C (65-75\u00B0F)',
    humidity: 'Average (40-60%)',
    humidity_action: 'Occasional misting helps, especially in dry seasons.',
    soil: 'Standard potting mix with perlite',
    repot: 'Every 1-2 years',
    fertilizer: 'Monthly during growing season',
    fertilizer_season: 'Spring-Summer',
    tips: 'Water when top inch of soil is dry. Most forgiving category.',
    common_problems: ['Yellow leaves (overwatering)', 'Brown tips (dry air)', 'Leggy growth (low light)'],
    common_pests: ['Spider mites', 'Mealybugs', 'Fungus gnats'],
  },
  Tropical: {
    name: 'Tropical',
    start_pct: 55,
    stop_pct: 75,
    watering: 'Every 5-7 days',
    watering_winter: 'Every 10-14 days',
    light: 'Bright indirect light, no direct sun',
    light_also_ok: 'Medium light',
    ppfd_min: 150,
    ppfd_max: 400,
    dli_min: 6,
    dli_max: 14,
    temperature: '21-29\u00B0C (70-85\u00B0F)',
    humidity: 'High (60-80%)',
    humidity_action: 'Mist leaves regularly or use a humidifier nearby.',
    soil: 'Rich, well-draining tropical mix with perlite',
    repot: 'Every 1-2 years in spring',
    fertilizer: 'Monthly during growing season',
    fertilizer_season: 'Spring-Summer',
    tips: 'Keep soil consistently moist but not soggy. Mist leaves or use humidifier.',
    common_problems: ['Brown leaf edges (low humidity)', 'Root rot (soggy soil)', 'Yellow leaves (cold draft)'],
    common_pests: ['Spider mites', 'Thrips', 'Mealybugs'],
  },
  Herbs: {
    name: 'Herbs',
    start_pct: 30,
    stop_pct: 45,
    watering: 'Every 5-7 days',
    watering_winter: 'Every 7-10 days',
    light: 'Full sun (6+ hours)',
    light_also_ok: 'Bright indirect',
    ppfd_min: 300,
    ppfd_max: 600,
    dli_min: 12,
    dli_max: 20,
    temperature: '15-24\u00B0C (60-75\u00B0F)',
    humidity: 'Average (40-50%)',
    humidity_action: 'Good air circulation is more important than humidity for herbs.',
    soil: 'Light potting mix with good drainage',
    repot: 'Yearly or when rootbound',
    fertilizer: 'Every 2-4 weeks during growing season',
    fertilizer_season: 'Spring-Fall',
    tips: 'Herbs like consistent moisture. Harvest regularly to promote growth.',
    common_problems: ['Bolting (too hot)', 'Leggy growth (low light)', 'Wilting (underwatering)'],
    common_pests: ['Aphids', 'Whiteflies', 'Spider mites'],
  },
};
