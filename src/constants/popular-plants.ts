// Popular plants for Library MVP — 5 prototype cards with rich content
// Care data: per-species overrides take priority over preset defaults
import type { PresetCare } from './presets';

export interface PopularPlant {
  id: string;
  scientific: string;
  common_name: string;
  family: string;
  preset: 'Succulents' | 'Standard' | 'Tropical' | 'Herbs';
  plant_type: 'decorative' | 'greens' | 'fruiting';  // determines card type
  image_url: string;          // Wikipedia CC thumbnail
  description: string;        // actionable — why would I want this plant?
  difficulty: string;         // Easy/Medium/Advanced WITH reason
  difficulty_note?: string;   // extra context on difficulty (shown as action hint)
  growth_rate: string;        // Slow / Medium / Fast
  lifecycle?: string;         // annual / perennial
  lifecycle_years?: string;   // e.g. "2+" or "10-20" or "1 season"
  height_min_cm?: number;     // min height (mature)
  height_max_cm?: number;     // max height (in ground, full grown)
  height_indoor_max_cm?: number; // realistic max in a pot
  spread_max_cm?: number;     // width/spread (full grown)
  used_for?: string[];        // e.g. ['Decorative', 'Air purifier', 'Aromatic']
  used_for_details?: string;  // expanded info for Used for guide
  temp_min_c?: number;        // absolute minimum (plant dies below)
  temp_opt_low_c?: number;    // optimal range low
  temp_opt_high_c?: number;   // optimal range high
  temp_max_c?: number;        // absolute maximum
  temp_winter_low_c?: number; // winter optimal low (if different)
  temp_winter_high_c?: number;// winter optimal high
  temp_warning?: string;      // specific warning
  watering_freq_summer_days?: number;  // base interval in days (summer)
  watering_freq_winter_days?: number;  // base interval in days (winter)
  watering_demand?: string;   // 'Low' | 'Medium' | 'High' | 'Very high'
  watering_soil_hint?: string; // e.g. 'Let soil dry completely' or 'Keep soil moist'
  watering_warning?: string;  // e.g. 'Sensitive to lime in water'
  watering_method?: string;   // recommended method for this plant
  watering_avoid?: string;    // what NOT to do
  edible: boolean;            // true for herbs, veggies, fruit
  edible_parts?: string;      // what parts are edible (for edible plants)
  harvest_info?: string;      // when/how to harvest (for edible/fruiting)
  poisonous_to_pets: boolean;
  poisonous_to_humans: boolean;
  toxicity_note: string;
  toxic_parts?: string;       // which parts are toxic: 'All parts' / 'Leaves, sap' / etc
  toxicity_severity?: string; // 'Mild' / 'Moderate' / 'Severe'
  toxicity_symptoms?: string; // symptoms if ingested/contacted
  toxicity_first_aid?: string; // what to do
  soil_types?: string[];      // e.g. ['Cactus & succulent mix', 'Perlite']
  pot_type?: string;          // e.g. 'Terracotta' / 'Plastic' / 'Clear (orchids)'
  pot_size_note?: string;     // pot size advice
  repot_signs?: string;       // when to know it's time to repot
  fertilizer_types?: string[];  // e.g. ['Balanced NPK', 'Succulent fertilizer']
  fertilizer_npk?: string;      // e.g. '10-10-10' or '20-20-20'
  fertilizer_warning?: string;  // what to avoid
  category: string;           // for grouping in UI (tropical/succulents/foliage/herbs/flowering/fruiting)
  care?: Partial<PresetCare>; // per-species care overrides (merged with preset defaults)
}

export interface PlantCategory {
  key: string;
  label: string;
  icon: string;               // emoji
  count: number;
}

export const CATEGORIES: PlantCategory[] = [
  { key: 'tropical', label: 'Tropical', icon: '🌴', count: 0 },
  { key: 'succulents', label: 'Succulents', icon: '🌵', count: 0 },
  { key: 'foliage', label: 'Foliage', icon: '🌿', count: 0 },
  { key: 'herbs', label: 'Herbs', icon: '🌱', count: 0 },
  { key: 'flowering', label: 'Flowering', icon: '🌸', count: 0 },
  { key: 'fruiting', label: 'Fruiting', icon: '🍅', count: 0 },
];

// 5 prototype plants with full, rich data
export const POPULAR_PLANTS: PopularPlant[] = [
  // ── 1. Crassula ovata (Jade Plant) ─────────────────────────────
  {
    id: 'crassula_ovata',
    scientific: 'Crassula ovata',
    common_name: 'Jade Plant',
    family: 'Crassulaceae',
    preset: 'Succulents',
    plant_type: 'decorative',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Crassula_ovata_700.jpg/330px-Crassula_ovata_700.jpg',
    description: 'Succulent, survives 2-3 weeks without water. Grows into a tree-like form over decades (up to 1.5m). Main killer: overwatering — root rot develops fast in wet soil. Stores water in thick leaves. Needs bright light for compact growth.',
    difficulty: 'Easy',
    difficulty_note: 'Tolerates neglect. #1 cause of death: overwatering.',
    growth_rate: 'Slow',
    lifecycle: 'perennial',
    lifecycle_years: '50+',
    height_min_cm: 10,
    height_max_cm: 300,
    height_indoor_max_cm: 100,
    spread_max_cm: 200,
    used_for: ['Decorative'],
    used_for_details: 'Symbol of good luck and prosperity in many cultures — often called Money Plant or Friendship Tree. Grows into an attractive tree-like form over decades. Can be shaped as bonsai.',
    temp_min_c: 4, temp_opt_low_c: 15, temp_opt_high_c: 24, temp_max_c: 35,
    temp_winter_low_c: 12, temp_winter_high_c: 18,
    temp_warning: 'Keep above 4°C. Sensitive to cold drafts — move away from open windows in winter.',
    watering_freq_summer_days: 10,
    watering_freq_winter_days: 30,
    watering_demand: 'Low',
    watering_soil_hint: 'Let soil dry completely',
    watering_method: 'Water over the soil slowly until it drains. Discard excess water from saucer.',
    watering_avoid: 'Never let the pot sit in water. Overwatering causes root rot — the #1 killer of Jade Plants.',
    edible: false,
    poisonous_to_pets: true,
    poisonous_to_humans: false,
    toxicity_note: 'Toxic to cats and dogs if ingested — causes vomiting and lethargy. Keep on a high shelf if you have pets.',
    toxic_parts: 'All parts (leaves, stems, sap)',
    toxicity_severity: 'Mild',
    toxicity_symptoms: 'Ingestion: nausea, vomiting, diarrhea, lethargy (pets: also loss of coordination).\nDermal: generally no reaction, wash hands after handling.\nEye contact: mild irritation if sap gets in eyes.\nInhalation: not applicable.',
    toxicity_first_aid: 'Ingestion: remove plant material from mouth, rinse with water, offer water or milk. Monitor for a few hours — call poison control or vet if symptoms persist.\nDermal: wash skin with soap and water.\nEye contact: flush with clean water for 10–15 minutes.',
    soil_types: ['Cactus & succulent mix', 'Perlite', 'Coarse sand'],
    pot_type: 'Terracotta — lets soil breathe and dry faster',
    pot_size_note: 'Prefers a snug pot — slightly rootbound encourages compact growth.',
    repot_signs: 'Roots growing out of drainage holes, soil dries out within a day, plant becomes top-heavy.',
    fertilizer_types: ['Succulent fertilizer', 'Balanced liquid (diluted to half)'],
    fertilizer_npk: '10-10-10 or 2-7-7',
    fertilizer_warning: 'Over-fertilizing causes salt buildup and root burn. Less is more with succulents.',
    category: 'succulents',
    care: {
      watering: 'Every 2-3 weeks, let soil dry completely between waterings',
      watering_winter: 'Once a month — seriously, put the watering can down',
      light: 'Bright indirect to direct sun (south or west window)',
      light_also_ok: 'Medium light (survives but grows leggy and slow)',
      ppfd_min: 200, ppfd_max: 600, dli_min: 8, dli_max: 20,
      temperature: '15-24\u00B0C (59-75\u00B0F)',
      humidity: 'Low to average (30-50%) — loves dry air',
      humidity_action: 'No misting needed. Normal apartment air is perfect.',
      soil: 'Well-draining succulent mix with coarse sand or perlite. Terracotta pot helps soil dry faster.',
      repot: 'Every 2-3 years. Prefers a snug pot — slightly rootbound encourages compact growth.',
      fertilizer: 'Diluted balanced fertilizer 2-3 times during spring and summer only',
      fertilizer_season: 'Spring-Summer',
      tips: 'Overwatering is the #1 killer. When in doubt, wait another week. Develops a thick woody trunk with age — can become a stunning bonsai-like showpiece over 5-10 years. Prune stems to encourage branching. Leaf or stem cuttings root easily for propagation.',
      common_problems: ['Soft, mushy leaves (overwatering — let it dry out and reduce frequency)', 'Dropping leaves (cold draft or overwatering)', 'Leggy, stretched growth (needs more light — move closer to window)'],
      common_pests: ['Mealybugs (white cottony spots — wipe with rubbing alcohol)', 'Spider mites (tiny webs — increase air circulation)', 'Scale (brown bumps on stems — scrape off manually)'],
    },
  },

  // ── 2. Phalaenopsis amabilis (Moth Orchid) ────────────────────
  {
    id: 'phalaenopsis_amabilis',
    scientific: 'Phalaenopsis amabilis',
    common_name: 'Moth Orchid',
    family: 'Orchidaceae',
    preset: 'Tropical',
    plant_type: 'decorative',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Phalaenopsis_amabilis_Orchi_198.jpg/330px-Phalaenopsis_amabilis_Orchi_198.jpg',
    description: 'Epiphyte — grows on bark, not soil. Blooms 2-3 months, re-blooms with 5°C night temperature drop in autumn. Roots photosynthesize (use clear pot). Water by soaking bark, drain fully. Green roots = hydrated, silver = needs water.',
    difficulty: 'Easy',
    difficulty_note: 'Two rules: no soggy roots, no direct sun. Rest is forgiving.',
    growth_rate: 'Slow',
    lifecycle: 'perennial',
    lifecycle_years: '10-15',
    height_min_cm: 15,
    height_max_cm: 60,
    height_indoor_max_cm: 50,
    spread_max_cm: 30,
    used_for: ['Decorative', 'Flowering'],
    used_for_details: 'Blooms for 2-3 months with minimal care. Available in hundreds of colors. One of the most popular gift plants worldwide. Can re-bloom year after year with proper autumn temperature drop.',
    temp_min_c: 15, temp_opt_low_c: 18, temp_opt_high_c: 27, temp_max_c: 35,
    temp_winter_low_c: 15, temp_winter_high_c: 22,
    temp_warning: 'A 5°C night temperature drop in autumn triggers re-blooming. Never below 15°C.',
    watering_freq_summer_days: 7,
    watering_freq_winter_days: 12,
    watering_demand: 'Medium',
    watering_soil_hint: 'Let bark dry between waterings',
    watering_method: 'Soak the bark for 10-15 minutes, then drain completely. Never leave roots sitting in water.',
    watering_avoid: 'Never pour water into the crown (center of leaves) — causes crown rot. Never use ice cubes — this is a myth.',
    edible: false,
    poisonous_to_pets: false,
    poisonous_to_humans: false,
    toxicity_note: 'Completely non-toxic. Safe around kids and pets.',
    soil_types: ['Orchid bark mix', 'Sphagnum moss', 'Perlite'],
    pot_type: 'Clear plastic pot — roots photosynthesize and you can see root health',
    pot_size_note: 'Orchids like tight pots. Only repot when bark decomposes (every 2-3 years after flowering).',
    repot_signs: 'Bark breaking down and holding too much water, roots rotting, plant wobbling in pot.',
    fertilizer_types: ['Orchid fertilizer (20-20-20)', 'Balanced liquid (half strength)'],
    fertilizer_npk: '20-20-20',
    fertilizer_warning: '"Weekly, weakly" — half the recommended dose. Never fertilize a dry plant, water first.',
    category: 'flowering',
    care: {
      watering: 'Every 7-10 days: soak the bark, let it drain completely. Roots should dry between waterings.',
      watering_winter: 'Every 10-14 days. Less water, same method.',
      light: 'Bright indirect light — east or north-facing window is ideal',
      light_also_ok: 'Can tolerate lower light, but may not re-bloom',
      ppfd_min: 100, ppfd_max: 300, dli_min: 4, dli_max: 12,
      temperature: '18-27\u00B0C (65-80\u00B0F). A 5\u00B0C night-time temperature drop in autumn triggers blooming.',
      humidity: 'Average to high (50-70%)',
      humidity_action: 'Light misting in dry winters helps. Never let water pool in the crown — causes rot.',
      soil: 'Orchid bark mix (bark, sphagnum, perlite). Never use regular potting soil — roots need air!',
      repot: 'Every 2-3 years after flowering, when bark starts decomposing and holds too much water.',
      fertilizer: 'Orchid-specific fertilizer (20-20-20) every 2 weeks spring through fall. "Weekly, weakly" — half strength.',
      fertilizer_season: 'Spring through Fall',
      tips: 'After all flowers drop: cut the spike above the second node from the base — often triggers a second bloom. Green roots = healthy, silver roots = thirsty. Use a clear pot so you can see root health. Ice cube watering is a myth — use room temperature water.',
      common_problems: ['Bud blast / buds falling off (moved the plant or temperature shock — pick a spot and leave it)', 'Wrinkled leaves (roots are dead or dehydrated — check root health)', 'Yellow lower leaf (normal aging, one at a time. Multiple = overwatering)'],
      common_pests: ['Mealybugs (cottony white masses near leaf joints — isolate and treat with alcohol)', 'Scale (brown or tan bumps — scrape off, treat with neem)', 'Thrips (silvery streaks on flowers — remove affected flowers)'],
    },
  },

  // ── 3. Ocimum basilicum (Basil) ───────────────────────────────
  {
    id: 'ocimum_basilicum',
    scientific: 'Ocimum basilicum',
    common_name: 'Basil',
    family: 'Lamiaceae',
    preset: 'Herbs',
    plant_type: 'greens',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Ocimum_basilicum_8zz.jpg/330px-Ocimum_basilicum_8zz.jpg',
    description: 'Annual herb, seed to harvest in 3-4 weeks. Needs 6+ hours direct sun — without it, leggy and flavorless. Pinch flower buds immediately: after flowering, leaves turn bitter. More you harvest from top, bushier it grows. Essential oils concentrate with more sun.',
    difficulty: 'Easy',
    difficulty_note: 'Fast growing. Needs consistent sun and water. Bolts if stressed by heat or drought.',
    growth_rate: 'Fast',
    lifecycle: 'annual',
    lifecycle_years: '1 season',
    height_min_cm: 20,
    height_max_cm: 60,
    height_indoor_max_cm: 40,
    spread_max_cm: 30,
    used_for: ['Edible', 'Aromatic', 'Culinary herb', 'Attracts pollinators'],
    used_for_details: 'Essential kitchen herb — pesto, salads, pasta, pizza. Flowers attract bees and butterflies. Strong aroma repels mosquitoes and flies. Companion plant for tomatoes — improves flavor and repels pests.',
    temp_min_c: 5, temp_opt_low_c: 18, temp_opt_high_c: 27, temp_max_c: 38,
    temp_warning: 'Below 10°C kills basil. Bring indoors at first sign of cold nights.',
    watering_freq_summer_days: 2,
    watering_freq_winter_days: 5,
    watering_demand: 'Very high',
    watering_soil_hint: 'Keep soil moist but not soggy',
    watering_method: 'Water over the soil at the base. Avoid wetting leaves — promotes fungal issues.',
    watering_avoid: 'Do not let soil dry out — basil wilts fast and recovers slowly if caught late. But also no standing water.',
    edible: true,
    edible_parts: 'Leaves, flowers, seeds — all edible',
    harvest_info: 'Harvest from the top, cutting above a leaf pair. First harvest 3-4 weeks from seed. Pick regularly to keep it bushy.',
    poisonous_to_pets: false,
    poisonous_to_humans: false,
    toxicity_note: 'Completely safe. All parts are edible.',
    soil_types: ['Rich potting mix', 'Compost', 'Peat-based mix'],
    pot_type: 'Any pot with drainage holes — plastic or terracotta both work',
    pot_size_note: 'Annual plant — no need to upsize. Start new from seed every 3-4 months.',
    repot_signs: 'Not applicable — basil is annual. Start fresh from seed instead of repotting.',
    fertilizer_types: ['Nitrogen-rich liquid fertilizer', 'All-purpose liquid'],
    fertilizer_npk: '10-5-5 or similar (high nitrogen)',
    fertilizer_warning: 'Over-fertilizing reduces flavor and aroma. Keep it moderate.',
    category: 'herbs',
    care: {
      watering: 'Every 3-5 days, keep soil moist but never soggy. Wilts dramatically when thirsty — water immediately.',
      watering_winter: 'Every 5-7 days. Basil slows down in winter indoors.',
      light: 'Full sun 6+ hours daily — south-facing window is ideal. This is non-negotiable.',
      light_also_ok: 'Bright indirect (survives but leggy, less flavorful. Consider a grow light.)',
      ppfd_min: 300, ppfd_max: 600, dli_min: 12, dli_max: 22,
      temperature: '18-27\u00B0C (65-80\u00B0F). Hates cold — below 10\u00B0C kills it.',
      humidity: 'Average (40-60%)',
      humidity_action: 'Good air circulation is more important than humidity. Stagnant wet air causes fungal issues.',
      soil: 'Rich, well-draining potting mix with compost. pH 6.0-7.0.',
      repot: 'Annual plant — start new from seed every 3-4 months instead of repotting. Multiple sowings = year-round harvest.',
      fertilizer: 'Every 2-3 weeks with nitrogen-rich liquid fertilizer. Over-fertilizing reduces flavor.',
      fertilizer_season: 'Throughout growing season',
      tips: 'The #1 rule: pinch off flower buds the moment you see them. Flowering = end of leaf production (bolting). Harvest from the top, cutting just above a leaf pair — this triggers two new branches. More you harvest, bushier it grows. Seed to first harvest: 3-4 weeks.',
      common_problems: ['Bolting / flowering (too hot, too stressed, or too late in season — pinch flowers immediately)', 'Wilting then yellow leaves (underwatering — basil is dramatic but recovers fast if caught early)', 'Black spots on leaves (fungal — water the soil not the leaves, improve air circulation)'],
      common_pests: ['Aphids (tiny green bugs clustering on new growth — blast with water or use insecticidal soap)', 'Slugs (if growing outdoors — use copper tape or beer traps)', 'Whiteflies (tiny white moths — yellow sticky traps work well)'],
    },
  },

  // ── 4. Salvia rosmarinus (Rosemary) ───────────────────────────
  {
    id: 'rosmarinus_officinalis',
    scientific: 'Salvia rosmarinus',
    common_name: 'Rosemary',
    family: 'Lamiaceae',
    preset: 'Herbs',
    plant_type: 'greens',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Rosemary_in_bloom.JPG/330px-Rosemary_in_bloom.JPG',
    description: 'Evergreen Mediterranean shrub. Thrives in poor, sandy soil — over-fertilizing reduces essential oil content (= less flavor). Needs 6+ hours direct sun. Woody stems are normal. Flowers are edible. One plant provides rosemary for years. Prefers dry air and good ventilation.',
    difficulty: 'Medium',
    difficulty_note: 'Easy outdoors, trickier indoors: overwatering + poor air circulation are the main killers.',
    growth_rate: 'Medium',
    lifecycle: 'perennial',
    lifecycle_years: '10-20',
    height_min_cm: 60,
    height_max_cm: 180,
    height_indoor_max_cm: 50,
    spread_max_cm: 120,
    used_for: ['Edible', 'Aromatic', 'Culinary herb', 'Medicinal', 'Attracts pollinators'],
    used_for_details: 'Versatile culinary herb — roasts, stews, bread, tea. Medicinal: anti-inflammatory, improves memory and concentration (traditional use). Flowers attract bees. Strong scent repels deer and rabbits — good garden border plant.',
    temp_min_c: -5, temp_opt_low_c: 10, temp_opt_high_c: 24, temp_max_c: 35,
    temp_winter_low_c: 5, temp_winter_high_c: 15,
    temp_warning: 'Tolerates light frost outdoors. Indoors, prefers cooler conditions than most herbs.',
    watering_freq_summer_days: 5,
    watering_freq_winter_days: 14,
    watering_demand: 'Low',
    watering_soil_hint: 'Let top inch dry between waterings',
    watering_method: 'Water at the base, let drain. Terracotta pot helps soil dry evenly.',
    watering_avoid: 'Do not overwater — root rot is the #1 indoor killer for rosemary. If in doubt, skip watering.',
    edible: true,
    edible_parts: 'Leaves and flowers — both edible',
    harvest_info: 'Cut sprigs (not individual needles) above a leaf node. Available year-round. Flavor is strongest just before flowering.',
    poisonous_to_pets: false,
    poisonous_to_humans: false,
    toxicity_note: 'Completely safe. Used in cooking, tea, and aromatherapy.',
    soil_types: ['Sandy mix', 'Perlite', 'Well-draining potting soil'],
    pot_type: 'Terracotta — lets soil breathe, prevents root rot',
    pot_size_note: 'Repot every 1-2 years. Does not mind being slightly rootbound.',
    repot_signs: 'Roots circling the bottom, water runs straight through without absorbing, stunted growth.',
    fertilizer_types: ['Light all-purpose fertilizer'],
    fertilizer_npk: '10-10-10 (diluted)',
    fertilizer_warning: 'Too much fertilizer reduces essential oil content = less flavor. Once in spring is enough.',
    category: 'herbs',
    care: {
      watering: 'Every 7-10 days when top inch of soil is dry. Let it dry out between waterings — this is not basil.',
      watering_winter: 'Every 10-14 days. Err on the dry side — root rot is the biggest indoor killer.',
      light: 'Full sun 6+ hours daily (south-facing window). Absolutely needs direct sunlight.',
      light_also_ok: 'Bright indirect (survives a few weeks but gets leggy and loses flavor fast)',
      ppfd_min: 300, ppfd_max: 600, dli_min: 12, dli_max: 22,
      temperature: '10-24\u00B0C (50-75\u00B0F). Tolerates light frost outdoors. Prefers cooler conditions than most herbs.',
      humidity: 'Low to average (30-50%) — actually prefers dry air',
      humidity_action: 'Good air circulation is critical indoors. Open a window nearby when possible. Do not mist.',
      soil: 'Well-draining, sandy, slightly alkaline soil (pH 6.0-7.5). Mix in extra sand or perlite.',
      repot: 'Every 1-2 years. Terracotta pot is ideal — lets soil breathe and dry out evenly.',
      fertilizer: 'Light feeding once in spring. Too much fertilizer reduces essential oil concentration = less flavor.',
      fertilizer_season: 'Spring only',
      tips: 'Harvest by cutting sprigs (not individual leaves) — cut above a leaf node to encourage branching. Woody stems at the base are normal and healthy. If it gets leggy indoors, it needs more direct sun. Prune after flowering to stay bushy. Flowers are edible and attract pollinators.',
      common_problems: ['Crispy brown needle tips (too dry indoors or underwatering — check if roots are healthy first)', 'Powdery mildew (white dusty coating — improve air circulation, reduce crowding)', 'Root rot (overwatering in heavy soil — switch to terracotta pot with sandy mix)'],
      common_pests: ['Spider mites (especially in dry indoor air — increase ventilation, spray with water)', 'Whiteflies (yellow sticky traps near the plant)', 'Powdery mildew (fungal, not a pest — improve air circulation)'],
    },
  },

  // ── 5. Solanum lycopersicum (Cherry Tomato) ───────────────────
  {
    id: 'solanum_lycopersicum',
    scientific: 'Solanum lycopersicum',
    common_name: 'Cherry Tomato',
    family: 'Solanaceae',
    preset: 'Herbs',
    plant_type: 'fruiting',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Cherry_tomatoes_red_and_green_2009_16x9.jpg/330px-Cherry_tomatoes_red_and_green_2009_16x9.jpg',
    description: 'Compact fruiting annual, 60-70 days seed to harvest. Needs 8+ hours direct sun minimum — without it, no fruit. Hand-pollinate indoors (shake flowering stems). Ripe fruit: edible. Leaves/stems/green fruit: toxic (solanine). Bush varieties (Tiny Tim, Micro Tom) best for indoors. One plant yields 100+ fruit.',
    difficulty: 'Medium',
    difficulty_note: 'Demanding on light (8h+) and feeding, but very productive. Bush varieties easier indoors.',
    growth_rate: 'Fast',
    lifecycle: 'annual',
    lifecycle_years: '1 season',
    height_min_cm: 30,
    height_max_cm: 100,
    height_indoor_max_cm: 50,
    spread_max_cm: 40,
    used_for: ['Edible', 'Fruiting', 'Attracts pollinators'],
    used_for_details: 'One plant yields 100+ cherry tomatoes per season. Rich in vitamins A and C. Hand-pollinate indoors by shaking flowering stems. Bush varieties (Tiny Tim, Micro Tom) ideal for windowsill or balcony.',
    temp_min_c: 5, temp_opt_low_c: 18, temp_opt_high_c: 29, temp_max_c: 40,
    temp_warning: 'Below 10°C stops growth. Above 35°C causes blossom drop — no fruit.',
    watering_freq_summer_days: 2,
    watering_freq_winter_days: undefined,
    watering_demand: 'Very high',
    watering_soil_hint: 'Keep soil consistently moist',
    watering_method: 'Deep soak at the base. Consistent watering prevents fruit cracking. Mulch helps retain moisture.',
    watering_avoid: 'Avoid wetting leaves — promotes blight. Inconsistent watering causes blossom end rot and cracking.',
    edible: true,
    edible_parts: 'Ripe fruit only — leaves and stems are toxic',
    harvest_info: 'Pick when fully red and slightly soft to the touch. About 60-70 days from planting to first harvest. One plant can produce 100+ tomatoes.',
    poisonous_to_pets: true,
    poisonous_to_humans: false,
    toxicity_note: 'Ripe fruit is safe. Leaves, stems, and green unripe fruit contain solanine — mildly toxic to pets and small children if eaten in quantity.',
    toxic_parts: 'Leaves, stems, green unripe fruit (contain solanine). Ripe fruit is safe.',
    toxicity_severity: 'Mild to Moderate',
    toxicity_symptoms: 'Ingestion (leaves/green fruit): nausea, vomiting, abdominal pain, diarrhea. Large quantities: headache, dizziness. Pets are more sensitive than humans.\nDermal: sap may cause mild skin irritation in sensitive individuals.\nEye contact: irritation if sap gets in eyes.\nInhalation: not applicable.',
    toxicity_first_aid: 'Ingestion: remove plant material, rinse mouth, drink water. If large amount consumed — call poison control or vet.\nDermal: wash with soap and water.\nEye contact: flush with clean water for 10–15 minutes.',
    soil_types: ['Rich potting mix', 'Compost', 'Peat-based mix'],
    pot_type: 'Any pot with drainage, at least 5 liters for bush varieties',
    pot_size_note: 'Annual — start new each spring. Pot up seedlings once when they outgrow starter pots.',
    repot_signs: 'Seedlings outgrowing starter pots — move to final container. Do not disturb once fruiting.',
    fertilizer_types: ['Tomato fertilizer (high potassium)', 'Balanced + calcium supplement'],
    fertilizer_npk: '5-10-10 or tomato-specific',
    fertilizer_warning: 'Start fertilizing when flowers appear, not before. Calcium supplement prevents blossom end rot.',
    category: 'fruiting',
    care: {
      watering: 'Every 2-3 days in summer, daily in hot weather. Consistent watering prevents cracking. Deep soak, not a sprinkle.',
      watering_winter: 'Not applicable — tomatoes are annual warm-season plants. Start new seeds in spring.',
      light: 'Full sun 8+ hours daily. The single most important factor. South-facing window minimum; balcony or grow light ideal.',
      light_also_ok: 'Bright indirect with supplemental grow light (at least 14 hours total light)',
      ppfd_min: 400, ppfd_max: 800, dli_min: 15, dli_max: 30,
      temperature: '18-29\u00B0C (65-85\u00B0F). Below 10\u00B0C stops growth. Above 35\u00B0C causes blossom drop.',
      humidity: 'Average (40-60%)',
      humidity_action: 'Good air circulation prevents fungal disease. Avoid wetting leaves when watering.',
      soil: 'Rich, well-draining potting mix with compost. pH 6.0-6.8. At least a 5-liter pot for bush varieties.',
      repot: 'Annual plant. Start new from seed each spring. Pot up seedlings once when they outgrow starter pots.',
      fertilizer: 'Weekly with tomato-specific fertilizer (high potassium) once flowering starts. Calcium supplement prevents blossom end rot.',
      fertilizer_season: 'From first flowers through harvest',
      tips: 'Choose determinate (bush) varieties for indoors: Tiny Tim, Red Robin, Micro Tom. Hand-pollinate by gently shaking the plant or tapping flowers when they open. Pinch off suckers (shoots growing between main stem and branches) to focus energy on fruit. Harvest when fully colored — they ripen best on the vine.',
      common_problems: ['Blossom end rot (black spot on bottom of fruit — calcium deficiency from inconsistent watering)', 'Leggy seedlings (not enough light — the #1 indoor problem, get a grow light)', 'Blossom drop / no fruit (too hot, too cold, or not pollinated — shake the plant daily during flowering)'],
      common_pests: ['Aphids (green clusters on stems — blast with water or insecticidal soap)', 'Whiteflies (tiny white moths — yellow sticky traps)', 'Spider mites (in dry indoor air — mist around plant, not on leaves)'],
    },
  },
  // ── 6. Sansevieria trifasciata (Snake Plant) ──────────────────
  {
    id: 'sansevieria_trifasciata',
    scientific: 'Dracaena trifasciata',
    common_name: 'Snake Plant',
    family: 'Asparagaceae',
    preset: 'Succulents',
    plant_type: 'decorative',
    image_url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg/330px-Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg',
    description: 'Nearly indestructible. Tolerates low light, dry air, irregular watering. Purifies air (NASA study). Releases oxygen at night — ideal for bedroom. Grows slowly but lives for decades. The perfect first plant.',
    difficulty: 'Easy',
    difficulty_note: 'The most forgiving houseplant. Survives weeks of neglect. Only real killer: overwatering.',
    growth_rate: 'Slow',
    lifecycle: 'perennial',
    lifecycle_years: '20-25',
    height_min_cm: 20,
    height_max_cm: 120,
    height_indoor_max_cm: 100,
    spread_max_cm: 40,
    used_for: ['Decorative', 'Air purifier'],
    used_for_details: 'One of the top air-purifying plants (NASA Clean Air Study). Removes formaldehyde, benzene, trichloroethylene, xylene from indoor air. Unique feature: releases oxygen at night (most plants only during the day) — ideal for bedrooms. Recommended: 2-3 large plants per room for noticeable air quality improvement.',
    temp_min_c: 4, temp_opt_low_c: 15, temp_opt_high_c: 27, temp_max_c: 38,
    temp_winter_low_c: 12, temp_winter_high_c: 25,
    temp_warning: 'Keep above 10°C. Cold drafts cause permanent scarring on leaves.',
    watering_freq_summer_days: 14,
    watering_freq_winter_days: 30,
    watering_demand: 'Low',
    watering_soil_hint: 'Let soil dry completely',
    watering_warning: 'Sensitive to lime in water — use filtered or rainwater if possible',
    watering_method: 'Water at the base, avoiding the leaf rosette. Let drain fully. Bottom watering works well.',
    watering_avoid: 'Never let pot sit in water. Do not water into the center of the leaf rosette — causes rot.',
    edible: false,
    poisonous_to_pets: true,
    poisonous_to_humans: false,
    toxicity_note: 'Mildly toxic to cats and dogs if chewed — causes nausea, vomiting, diarrhea. Keep away from pets that like to chew leaves.',
    toxic_parts: 'All parts (contains saponins)',
    toxicity_severity: 'Mild',
    toxicity_symptoms: 'Ingestion: nausea, vomiting, diarrhea, drooling (pets). Mouth and throat irritation (humans). Usually self-limiting.\nDermal: sap may cause mild irritation or rash on sensitive skin.\nEye contact: irritation, redness.\nInhalation: not applicable.',
    toxicity_first_aid: 'Ingestion: remove plant material from mouth, rinse with water, offer water. Monitor pets for 24h — contact vet if vomiting persists.\nDermal: wash with soap and water.\nEye contact: flush with clean water for 10–15 minutes.',
    soil_types: ['Cactus & succulent mix', 'Perlite', 'Well-draining potting soil'],
    pot_type: 'Terracotta — helps soil dry evenly, prevents overwatering',
    pot_size_note: 'Likes being rootbound — no rush to repot. Every 2-3 years is fine.',
    repot_signs: 'Pot cracking from root pressure, roots growing out of drainage holes, soil depleted.',
    fertilizer_types: ['All-purpose liquid (diluted)', 'Succulent fertilizer'],
    fertilizer_npk: '10-10-10 (half strength)',
    fertilizer_warning: 'Fertilize only in spring-summer. Never in winter — plant is dormant.',
    category: 'foliage',
    care: {
      watering: 'Every 2-3 weeks, let soil dry completely. Stick your finger 5 cm into soil — if dry, water.',
      watering_winter: 'Once a month or less. In winter this plant barely drinks.',
      light: 'Low to bright indirect light — adapts to almost anything',
      light_also_ok: 'Tolerates shade, but growth slows significantly. No direct harsh sun — burns leaf tips.',
      ppfd_min: 50, ppfd_max: 300, dli_min: 2, dli_max: 12,
      temperature: '15-27\u00B0C (59-80\u00B0F). Keep above 10\u00B0C — cold drafts cause scarring.',
      humidity: 'Low to average (30-50%) — thrives in dry apartment air',
      humidity_action: 'No misting needed. Normal room air is perfect. Avoid humid bathrooms.',
      soil: 'Well-draining succulent/cactus mix with perlite. Must drain fast — standing water kills roots.',
      repot: 'Every 2-3 years. Likes being rootbound — no rush to repot. Terracotta pot helps soil dry evenly.',
      fertilizer: 'Once or twice during spring-summer with diluted all-purpose fertilizer. Less is more.',
      fertilizer_season: 'Spring-Summer only',
      tips: 'Overwatering is the only real threat. When in doubt, skip watering. Leaves store water — wrinkly leaves mean it finally needs a drink. Propagate by leaf cuttings in water or soil. Wipe leaves monthly to remove dust — helps it photosynthesize.',
      common_problems: ['Mushy base / yellow leaves (overwatering — stop immediately, check for root rot, repot in dry soil)', 'Brown crispy leaf tips (underwatering or low humidity — rare, check soil first)', 'Leaves falling over / splitting (physical damage or very overwatered roots)'],
      common_pests: ['Mealybugs (white cottony spots in leaf crevices — wipe with rubbing alcohol)', 'Spider mites (fine webs — wipe leaves with damp cloth)', 'Fungus gnats (tiny flies near soil — let soil dry out more between waterings)'],
    },
  },
];

// Compute category counts
CATEGORIES.forEach((cat) => {
  cat.count = POPULAR_PLANTS.filter((p) => p.category === cat.key).length;
});
