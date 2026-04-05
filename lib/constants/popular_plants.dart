// Popular plants for Library — 6 prototype cards with rich content
// Ported 1:1 from React Native src/constants/popular-plants.ts

class PopularPlant {
  final String id;
  final String scientific;
  final String commonName;
  final String family;
  final String preset;
  final String plantType; // decorative / greens / fruiting
  final String imageUrl;
  final String description;
  final String difficulty;
  final String difficultyNote;
  final String growthRate;
  final String lifecycle;
  final String lifecycleYears;
  final int heightMinCm;
  final int heightMaxCm;
  final int heightIndoorMaxCm;
  final int spreadMaxCm;
  final List<String> usedFor;
  final String usedForDetails;
  final int tempMinC;
  final int tempOptLowC;
  final int tempOptHighC;
  final int tempMaxC;
  final int tempWinterLowC;
  final int tempWinterHighC;
  final String tempWarning;
  final int wateringFreqSummerDays;
  final int wateringFreqWinterDays;
  final String wateringDemand;
  final String wateringSoilHint;
  final String wateringWarning;
  final String wateringMethod;
  final String wateringAvoid;
  final bool edible;
  final String edibleParts;
  final String harvestInfo;
  final bool poisonousToPets;
  final bool poisonousToHumans;
  final String toxicityNote;
  final String toxicParts;
  final String toxicitySeverity;
  final String toxicitySymptoms;
  final String toxicityFirstAid;
  final List<String> soilTypes;
  final String potType;
  final String potSizeNote;
  final String repotSigns;
  final List<String> fertilizerTypes;
  final String fertilizerNpk;
  final String fertilizerWarning;
  final String genus;
  final String order;
  final String origin;
  final List<String> synonyms;
  final List<String> goodCompanions;
  final List<String> badCompanions;
  final String companionNote;
  final String pruningInfo;
  final List<String> propagationMethods;
  final String propagationDetail;
  final int germinationDays;
  final String germinationTempC;
  final String category;
  // Care overrides (per-species, merged with preset defaults)
  final PopularPlantCare care;

  const PopularPlant({
    required this.id,
    required this.scientific,
    required this.commonName,
    required this.family,
    required this.preset,
    required this.plantType,
    required this.imageUrl,
    required this.description,
    required this.difficulty,
    this.difficultyNote = '',
    this.growthRate = '',
    this.lifecycle = '',
    this.lifecycleYears = '',
    this.heightMinCm = 0,
    this.heightMaxCm = 0,
    this.heightIndoorMaxCm = 0,
    this.spreadMaxCm = 0,
    this.usedFor = const [],
    this.usedForDetails = '',
    this.tempMinC = 5,
    this.tempOptLowC = 15,
    this.tempOptHighC = 25,
    this.tempMaxC = 35,
    this.tempWinterLowC = 12,
    this.tempWinterHighC = 22,
    this.tempWarning = '',
    this.wateringFreqSummerDays = 7,
    this.wateringFreqWinterDays = 14,
    this.wateringDemand = '',
    this.wateringSoilHint = '',
    this.wateringWarning = '',
    this.wateringMethod = '',
    this.wateringAvoid = '',
    this.edible = false,
    this.edibleParts = '',
    this.harvestInfo = '',
    required this.poisonousToPets,
    required this.poisonousToHumans,
    required this.toxicityNote,
    this.toxicParts = '',
    this.toxicitySeverity = '',
    this.toxicitySymptoms = '',
    this.toxicityFirstAid = '',
    this.soilTypes = const [],
    this.potType = '',
    this.potSizeNote = '',
    this.repotSigns = '',
    this.fertilizerTypes = const [],
    this.fertilizerNpk = '',
    this.fertilizerWarning = '',
    this.genus = '',
    this.order = '',
    this.origin = '',
    this.synonyms = const [],
    this.goodCompanions = const [],
    this.badCompanions = const [],
    this.companionNote = '',
    this.pruningInfo = '',
    this.propagationMethods = const [],
    this.propagationDetail = '',
    this.germinationDays = 0,
    this.germinationTempC = '',
    this.category = '',
    required this.care,
  });
}

class PopularPlantCare {
  final String watering;
  final String wateringWinter;
  final String light;
  final String lightAlsoOk;
  final int ppfdMin;
  final int ppfdMax;
  final int dliMin;
  final int dliMax;
  final String temperature;
  final String humidity;
  final String humidityAction;
  final String soil;
  final String repot;
  final String fertilizer;
  final String fertilizerSeason;
  final String tips;
  final List<String> commonProblems;
  final List<String> commonPests;

  const PopularPlantCare({
    this.watering = '',
    this.wateringWinter = '',
    this.light = '',
    this.lightAlsoOk = '',
    this.ppfdMin = 0,
    this.ppfdMax = 0,
    this.dliMin = 0,
    this.dliMax = 0,
    this.temperature = '',
    this.humidity = '',
    this.humidityAction = '',
    this.soil = '',
    this.repot = '',
    this.fertilizer = '',
    this.fertilizerSeason = '',
    this.tips = '',
    this.commonProblems = const [],
    this.commonPests = const [],
  });
}

/// Lookup by plant ID
PopularPlant? getPopularPlant(String id) {
  final idx = popularPlants.indexWhere((p) => p.id == id);
  return idx >= 0 ? popularPlants[idx] : null;
}

const popularPlants = <PopularPlant>[
  // ── 1. Crassula ovata (Jade Plant) ─────────────────────────────
  PopularPlant(
    id: 'crassula_ovata',
    scientific: 'Crassula ovata',
    commonName: 'Jade Plant',
    family: 'Crassulaceae',
    preset: 'Succulents',
    plantType: 'decorative',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Crassula_ovata_700.jpg/330px-Crassula_ovata_700.jpg',
    description: 'Succulent, survives 2-3 weeks without water. Grows into a tree-like form over decades (up to 1.5m). Main killer: overwatering \u2014 root rot develops fast in wet soil. Stores water in thick leaves. Needs bright light for compact growth.',
    difficulty: 'Easy',
    difficultyNote: 'Tolerates neglect. #1 cause of death: overwatering.',
    growthRate: 'Slow',
    lifecycle: 'perennial',
    lifecycleYears: '50+',
    heightMinCm: 10,
    heightMaxCm: 300,
    heightIndoorMaxCm: 100,
    spreadMaxCm: 200,
    usedFor: ['Decorative'],
    usedForDetails: 'Symbol of good luck and prosperity in many cultures \u2014 often called Money Plant or Friendship Tree. Grows into an attractive tree-like form over decades. Can be shaped as bonsai.',
    tempMinC: 4, tempOptLowC: 15, tempOptHighC: 24, tempMaxC: 35,
    tempWinterLowC: 12, tempWinterHighC: 18,
    tempWarning: 'Keep above 4\u00B0C. Sensitive to cold drafts \u2014 move away from open windows in winter.',
    wateringFreqSummerDays: 10,
    wateringFreqWinterDays: 30,
    wateringDemand: 'Low',
    wateringSoilHint: 'Let soil dry completely',
    wateringMethod: 'Water over the soil slowly until it drains. Discard excess water from saucer.',
    wateringAvoid: 'Never let the pot sit in water. Overwatering causes root rot \u2014 the #1 killer of Jade Plants.',
    poisonousToPets: true,
    poisonousToHumans: false,
    toxicityNote: 'Toxic to cats and dogs if ingested \u2014 causes vomiting and lethargy. Keep on a high shelf if you have pets.',
    toxicParts: 'All parts (leaves, stems, sap)',
    toxicitySeverity: 'Mild',
    toxicitySymptoms: 'Ingestion: nausea, vomiting, diarrhea, lethargy (pets: also loss of coordination).\nDermal: generally no reaction, wash hands after handling.\nEye contact: mild irritation if sap gets in eyes.',
    toxicityFirstAid: 'Ingestion: remove plant material from mouth, rinse with water, offer water or milk. Monitor for a few hours \u2014 call poison control or vet if symptoms persist.\nDermal: wash skin with soap and water.\nEye contact: flush with clean water for 10\u201315 minutes.',
    soilTypes: ['Cactus & succulent mix', 'Perlite', 'Coarse sand'],
    potType: 'Terracotta \u2014 lets soil breathe and dry faster',
    potSizeNote: 'Prefers a snug pot \u2014 slightly rootbound encourages compact growth.',
    repotSigns: 'Roots growing out of drainage holes, soil dries out within a day, plant becomes top-heavy.',
    fertilizerTypes: ['Succulent fertilizer', 'Balanced liquid (diluted to half)'],
    fertilizerNpk: '10-10-10 or 2-7-7',
    fertilizerWarning: 'Over-fertilizing causes salt buildup and root burn. Less is more with succulents.',
    genus: 'Crassula',
    order: 'Saxifragales',
    origin: 'South Africa, Mozambique',
    goodCompanions: ['Other succulents', 'Snake Plant', 'Aloe Vera'],
    badCompanions: ['Tropical plants (different watering needs)'],
    companionNote: 'Group with other drought-tolerant plants. They share similar watering and light needs. Avoid mixing with moisture-loving tropicals \u2014 one will suffer.',
    pruningInfo: 'Prune leggy branches to encourage compact, bushy growth. Cut above a leaf node. Remove dead or yellowing leaves at the base. Can be shaped into a bonsai form with regular pruning over years.',
    propagationMethods: ['Stem cuttings', 'Leaf cuttings'],
    propagationDetail: 'Stem cuttings: cut a 10 cm branch, let dry for 2-3 days, plant in succulent mix. Leaf cuttings: twist off a healthy leaf, let callous for a day, lay on moist soil. Roots in 2-4 weeks.',
    category: 'succulents',
    care: PopularPlantCare(
      watering: 'Every 2-3 weeks, let soil dry completely between waterings',
      wateringWinter: 'Once a month \u2014 seriously, put the watering can down',
      light: 'Bright indirect to direct sun (south or west window)',
      lightAlsoOk: 'Medium light (survives but grows leggy and slow)',
      ppfdMin: 200, ppfdMax: 600, dliMin: 8, dliMax: 20,
      temperature: '15-24\u00B0C (59-75\u00B0F)',
      humidity: 'Low to average (30-50%) \u2014 loves dry air',
      humidityAction: 'No misting needed. Normal apartment air is perfect.',
      soil: 'Well-draining succulent mix with coarse sand or perlite. Terracotta pot helps soil dry faster.',
      repot: 'Every 2-3 years. Prefers a snug pot \u2014 slightly rootbound encourages compact growth.',
      fertilizer: 'Diluted balanced fertilizer 2-3 times during spring and summer only',
      fertilizerSeason: 'Spring-Summer',
      tips: 'Overwatering is the #1 killer. When in doubt, wait another week. Develops a thick woody trunk with age \u2014 can become a stunning bonsai-like showpiece over 5-10 years. Prune stems to encourage branching. Leaf or stem cuttings root easily for propagation.',
      commonProblems: ['Soft, mushy leaves (overwatering \u2014 let it dry out and reduce frequency)', 'Dropping leaves (cold draft or overwatering)', 'Leggy, stretched growth (needs more light \u2014 move closer to window)'],
      commonPests: ['Mealybugs (white cottony spots \u2014 wipe with rubbing alcohol)', 'Spider mites (tiny webs \u2014 increase air circulation)', 'Scale (brown bumps on stems \u2014 scrape off manually)'],
    ),
  ),

  // ── 2. Phalaenopsis amabilis (Moth Orchid) ────────────────────
  PopularPlant(
    id: 'phalaenopsis_amabilis',
    scientific: 'Phalaenopsis amabilis',
    commonName: 'Moth Orchid',
    family: 'Orchidaceae',
    preset: 'Tropical',
    plantType: 'decorative',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Phalaenopsis_amabilis_Orchi_198.jpg/330px-Phalaenopsis_amabilis_Orchi_198.jpg',
    description: 'Epiphyte \u2014 grows on bark, not soil. Blooms 2-3 months, re-blooms with 5\u00B0C night temperature drop in autumn. Roots photosynthesize (use clear pot). Water by soaking bark, drain fully. Green roots = hydrated, silver = needs water.',
    difficulty: 'Easy',
    difficultyNote: 'Two rules: no soggy roots, no direct sun. Rest is forgiving.',
    growthRate: 'Slow',
    lifecycle: 'perennial',
    lifecycleYears: '10-15',
    heightMinCm: 15,
    heightMaxCm: 60,
    heightIndoorMaxCm: 50,
    spreadMaxCm: 30,
    usedFor: ['Decorative', 'Flowering'],
    usedForDetails: 'Blooms for 2-3 months with minimal care. Available in hundreds of colors. One of the most popular gift plants worldwide. Can re-bloom year after year with proper autumn temperature drop.',
    tempMinC: 15, tempOptLowC: 18, tempOptHighC: 27, tempMaxC: 35,
    tempWinterLowC: 15, tempWinterHighC: 22,
    tempWarning: 'A 5\u00B0C night temperature drop in autumn triggers re-blooming. Never below 15\u00B0C.',
    wateringFreqSummerDays: 7,
    wateringFreqWinterDays: 12,
    wateringDemand: 'Medium',
    wateringSoilHint: 'Let bark dry between waterings',
    wateringMethod: 'Soak the bark for 10-15 minutes, then drain completely. Never leave roots sitting in water.',
    wateringAvoid: 'Never pour water into the crown (center of leaves) \u2014 causes crown rot. Never use ice cubes \u2014 this is a myth.',
    poisonousToPets: false,
    poisonousToHumans: false,
    toxicityNote: 'Completely non-toxic. Safe around kids and pets.',
    soilTypes: ['Orchid bark mix', 'Sphagnum moss', 'Perlite'],
    potType: 'Clear plastic pot \u2014 roots photosynthesize and you can see root health',
    potSizeNote: 'Orchids like tight pots. Only repot when bark decomposes (every 2-3 years after flowering).',
    repotSigns: 'Bark breaking down and holding too much water, roots rotting, plant wobbling in pot.',
    fertilizerTypes: ['Orchid fertilizer (20-20-20)', 'Balanced liquid (half strength)'],
    fertilizerNpk: '20-20-20',
    fertilizerWarning: '"Weekly, weakly" \u2014 half the recommended dose. Never fertilize a dry plant, water first.',
    genus: 'Phalaenopsis',
    order: 'Asparagales',
    origin: 'Southeast Asia, Australia',
    goodCompanions: [],
    badCompanions: [],
    companionNote: 'Orchids grow in bark, not soil \u2014 companion planting does not apply in the traditional sense. Can be displayed alongside other plants for decoration.',
    pruningInfo: 'After all flowers drop: cut the spike above the 2nd node from the base \u2014 often triggers a second bloom. Remove dead roots (brown, mushy) when repotting. Cut dead flower spikes at the base if no new growth after 2 months.',
    propagationMethods: ['Division', 'Keiki (baby plant)'],
    propagationDetail: 'Division: when repotting, separate clumps with at least 3 pseudobulbs each. Keiki: baby plants sometimes grow on flower spikes \u2014 let roots reach 5 cm, then cut and pot separately.',
    category: 'flowering',
    care: PopularPlantCare(
      watering: 'Every 7-10 days: soak the bark, let it drain completely. Roots should dry between waterings.',
      wateringWinter: 'Every 10-14 days. Less water, same method.',
      light: 'Bright indirect light \u2014 east or north-facing window is ideal',
      lightAlsoOk: 'Can tolerate lower light, but may not re-bloom',
      ppfdMin: 100, ppfdMax: 300, dliMin: 4, dliMax: 12,
      temperature: '18-27\u00B0C (65-80\u00B0F). A 5\u00B0C night-time temperature drop in autumn triggers blooming.',
      humidity: 'Average to high (50-70%)',
      humidityAction: 'Light misting in dry winters helps. Never let water pool in the crown \u2014 causes rot.',
      soil: 'Orchid bark mix (bark, sphagnum, perlite). Never use regular potting soil \u2014 roots need air!',
      repot: 'Every 2-3 years after flowering, when bark starts decomposing and holds too much water.',
      fertilizer: 'Orchid-specific fertilizer (20-20-20) every 2 weeks spring through fall. "Weekly, weakly" \u2014 half strength.',
      fertilizerSeason: 'Spring through Fall',
      tips: 'After all flowers drop: cut the spike above the second node from the base \u2014 often triggers a second bloom. Green roots = healthy, silver roots = thirsty. Use a clear pot so you can see root health. Ice cube watering is a myth \u2014 use room temperature water.',
      commonProblems: ['Bud blast / buds falling off (moved the plant or temperature shock \u2014 pick a spot and leave it)', 'Wrinkled leaves (roots are dead or dehydrated \u2014 check root health)', 'Yellow lower leaf (normal aging, one at a time. Multiple = overwatering)'],
      commonPests: ['Mealybugs (cottony white masses near leaf joints \u2014 isolate and treat with alcohol)', 'Scale (brown or tan bumps \u2014 scrape off, treat with neem)', 'Thrips (silvery streaks on flowers \u2014 remove affected flowers)'],
    ),
  ),

  // ── 3. Ocimum basilicum (Basil) ───────────────────────────────
  PopularPlant(
    id: 'ocimum_basilicum',
    scientific: 'Ocimum basilicum',
    commonName: 'Basil',
    family: 'Lamiaceae',
    preset: 'Herbs',
    plantType: 'greens',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Ocimum_basilicum_8zz.jpg/330px-Ocimum_basilicum_8zz.jpg',
    description: 'Annual herb, seed to harvest in 3-4 weeks. Needs 6+ hours direct sun \u2014 without it, leggy and flavorless. Pinch flower buds immediately: after flowering, leaves turn bitter. More you harvest from top, bushier it grows. Essential oils concentrate with more sun.',
    difficulty: 'Easy',
    difficultyNote: 'Fast growing. Needs consistent sun and water. Bolts if stressed by heat or drought.',
    growthRate: 'Fast',
    lifecycle: 'annual',
    lifecycleYears: '1 season',
    heightMinCm: 20,
    heightMaxCm: 60,
    heightIndoorMaxCm: 40,
    spreadMaxCm: 30,
    usedFor: ['Edible', 'Aromatic', 'Culinary herb', 'Attracts pollinators'],
    usedForDetails: 'Essential kitchen herb \u2014 pesto, salads, pasta, pizza. Flowers attract bees and butterflies. Strong aroma repels mosquitoes and flies. Companion plant for tomatoes \u2014 improves flavor and repels pests.',
    tempMinC: 5, tempOptLowC: 18, tempOptHighC: 27, tempMaxC: 38,
    tempWarning: 'Below 10\u00B0C kills basil. Bring indoors at first sign of cold nights.',
    wateringFreqSummerDays: 2,
    wateringFreqWinterDays: 5,
    wateringDemand: 'Very high',
    wateringSoilHint: 'Keep soil moist but not soggy',
    wateringMethod: 'Water over the soil at the base. Avoid wetting leaves \u2014 promotes fungal issues.',
    wateringAvoid: 'Do not let soil dry out \u2014 basil wilts fast and recovers slowly if caught late. But also no standing water.',
    edible: true,
    edibleParts: 'Leaves, flowers, seeds \u2014 all edible',
    harvestInfo: 'Harvest from the top, cutting above a leaf pair. First harvest 3-4 weeks from seed. Pick regularly to keep it bushy.',
    poisonousToPets: false,
    poisonousToHumans: false,
    toxicityNote: 'Completely safe. All parts are edible.',
    soilTypes: ['Rich potting mix', 'Compost', 'Peat-based mix'],
    potType: 'Any pot with drainage holes \u2014 plastic or terracotta both work',
    potSizeNote: 'Annual plant \u2014 no need to upsize. Start new from seed every 3-4 months.',
    repotSigns: 'Not applicable \u2014 basil is annual. Start fresh from seed instead of repotting.',
    fertilizerTypes: ['Nitrogen-rich liquid fertilizer', 'All-purpose liquid'],
    fertilizerNpk: '10-5-5 or similar (high nitrogen)',
    fertilizerWarning: 'Over-fertilizing reduces flavor and aroma. Keep it moderate.',
    genus: 'Ocimum',
    order: 'Lamiales',
    origin: 'Central Africa, Southeast Asia',
    goodCompanions: ['Tomato', 'Pepper', 'Parsley', 'Oregano'],
    badCompanions: ['Sage', 'Rue', 'Thyme (competes for nutrients)'],
    companionNote: 'Classic companion to tomatoes \u2014 improves flavor and repels aphids and whiteflies. Plant together in the same bed or neighboring pots. Avoid sage \u2014 they inhibit each other.',
    pruningInfo: 'Pinch off flower buds the moment you see them \u2014 flowering ends leaf production and turns leaves bitter. Harvest from the top, cutting above a leaf pair. This triggers two new branches = bushier plant.',
    propagationMethods: ['Seeds', 'Stem cuttings'],
    propagationDetail: 'Seeds: sow on surface of moist soil, press lightly, do not cover. Keep warm (20-25\u00B0C). Germinates in 5-10 days. Stem cuttings: cut 10 cm stem, remove lower leaves, place in water until roots appear (7-14 days).',
    germinationDays: 7,
    germinationTempC: '20-25\u00B0C',
    category: 'herbs',
    care: PopularPlantCare(
      watering: 'Every 3-5 days, keep soil moist but never soggy. Wilts dramatically when thirsty \u2014 water immediately.',
      wateringWinter: 'Every 5-7 days. Basil slows down in winter indoors.',
      light: 'Full sun 6+ hours daily \u2014 south-facing window is ideal. This is non-negotiable.',
      lightAlsoOk: 'Bright indirect (survives but leggy, less flavorful. Consider a grow light.)',
      ppfdMin: 300, ppfdMax: 600, dliMin: 12, dliMax: 22,
      temperature: '18-27\u00B0C (65-80\u00B0F). Hates cold \u2014 below 10\u00B0C kills it.',
      humidity: 'Average (40-60%)',
      humidityAction: 'Good air circulation is more important than humidity. Stagnant wet air causes fungal issues.',
      soil: 'Rich, well-draining potting mix with compost. pH 6.0-7.0.',
      repot: 'Annual plant \u2014 start new from seed every 3-4 months instead of repotting. Multiple sowings = year-round harvest.',
      fertilizer: 'Every 2-3 weeks with nitrogen-rich liquid fertilizer. Over-fertilizing reduces flavor.',
      fertilizerSeason: 'Throughout growing season',
      tips: 'The #1 rule: pinch off flower buds the moment you see them. Flowering = end of leaf production (bolting). Harvest from the top, cutting just above a leaf pair \u2014 this triggers two new branches. More you harvest, bushier it grows. Seed to first harvest: 3-4 weeks.',
      commonProblems: ['Bolting / flowering (too hot, too stressed, or too late in season \u2014 pinch flowers immediately)', 'Wilting then yellow leaves (underwatering \u2014 basil is dramatic but recovers fast if caught early)', 'Black spots on leaves (fungal \u2014 water the soil not the leaves, improve air circulation)'],
      commonPests: ['Aphids (tiny green bugs clustering on new growth \u2014 blast with water or use insecticidal soap)', 'Slugs (if growing outdoors \u2014 use copper tape or beer traps)', 'Whiteflies (tiny white moths \u2014 yellow sticky traps work well)'],
    ),
  ),

  // ── 4. Salvia rosmarinus (Rosemary) ───────────────────────────
  PopularPlant(
    id: 'rosmarinus_officinalis',
    scientific: 'Salvia rosmarinus',
    commonName: 'Rosemary',
    family: 'Lamiaceae',
    preset: 'Herbs',
    plantType: 'greens',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Rosemary_in_bloom.JPG/330px-Rosemary_in_bloom.JPG',
    description: 'Evergreen Mediterranean shrub. Thrives in poor, sandy soil \u2014 over-fertilizing reduces essential oil content (= less flavor). Needs 6+ hours direct sun. Woody stems are normal. Flowers are edible. One plant provides rosemary for years. Prefers dry air and good ventilation.',
    difficulty: 'Medium',
    difficultyNote: 'Easy outdoors, trickier indoors: overwatering + poor air circulation are the main killers.',
    growthRate: 'Medium',
    lifecycle: 'perennial',
    lifecycleYears: '10-20',
    heightMinCm: 60,
    heightMaxCm: 180,
    heightIndoorMaxCm: 50,
    spreadMaxCm: 120,
    usedFor: ['Edible', 'Aromatic', 'Culinary herb', 'Medicinal', 'Attracts pollinators'],
    usedForDetails: 'Versatile culinary herb \u2014 roasts, stews, bread, tea. Medicinal: anti-inflammatory, improves memory and concentration (traditional use). Flowers attract bees. Strong scent repels deer and rabbits \u2014 good garden border plant.',
    tempMinC: -5, tempOptLowC: 10, tempOptHighC: 24, tempMaxC: 35,
    tempWinterLowC: 5, tempWinterHighC: 15,
    tempWarning: 'Tolerates light frost outdoors. Indoors, prefers cooler conditions than most herbs.',
    wateringFreqSummerDays: 5,
    wateringFreqWinterDays: 14,
    wateringDemand: 'Low',
    wateringSoilHint: 'Let top inch dry between waterings',
    wateringMethod: 'Water at the base, let drain. Terracotta pot helps soil dry evenly.',
    wateringAvoid: 'Do not overwater \u2014 root rot is the #1 indoor killer for rosemary. If in doubt, skip watering.',
    edible: true,
    edibleParts: 'Leaves and flowers \u2014 both edible',
    harvestInfo: 'Cut sprigs (not individual needles) above a leaf node. Available year-round. Flavor is strongest just before flowering.',
    poisonousToPets: false,
    poisonousToHumans: false,
    toxicityNote: 'Completely safe. Used in cooking, tea, and aromatherapy.',
    soilTypes: ['Sandy mix', 'Perlite', 'Well-draining potting soil'],
    potType: 'Terracotta \u2014 lets soil breathe, prevents root rot',
    potSizeNote: 'Repot every 1-2 years. Does not mind being slightly rootbound.',
    repotSigns: 'Roots circling the bottom, water runs straight through without absorbing, stunted growth.',
    fertilizerTypes: ['Light all-purpose fertilizer'],
    fertilizerNpk: '10-10-10 (diluted)',
    fertilizerWarning: 'Too much fertilizer reduces essential oil content = less flavor. Once in spring is enough.',
    genus: 'Salvia',
    order: 'Lamiales',
    origin: 'Mediterranean region',
    synonyms: ['Rosmarinus officinalis'],
    goodCompanions: ['Cabbage', 'Beans', 'Carrots', 'Sage'],
    badCompanions: ['Cucumber', 'Pumpkin', 'Basil (competes)'],
    companionNote: 'Strong scent repels carrot fly, cabbage moths, and bean beetles. Excellent border plant for vegetable gardens. Keep away from cucumbers \u2014 rosemary inhibits their growth.',
    pruningInfo: 'Prune after flowering to maintain bushy shape. Cut back up to one-third of the plant. Never cut into old wood (brown, bare stems) \u2014 it will not regrow from there. Regular light pruning is better than one heavy cut.',
    propagationMethods: ['Stem cuttings', 'Layering'],
    propagationDetail: 'Stem cuttings: take 10-15 cm softwood cuttings in spring/summer, remove lower needles, dip in rooting hormone, plant in sandy mix. Keep moist. Roots in 4-8 weeks. Layering: bend a low branch to touch soil, pin down, cover with soil. Roots in a few months.',
    germinationDays: 21,
    germinationTempC: '15-20\u00B0C',
    category: 'herbs',
    care: PopularPlantCare(
      watering: 'Every 7-10 days when top inch of soil is dry. Let it dry out between waterings \u2014 this is not basil.',
      wateringWinter: 'Every 10-14 days. Err on the dry side \u2014 root rot is the biggest indoor killer.',
      light: 'Full sun 6+ hours daily (south-facing window). Absolutely needs direct sunlight.',
      lightAlsoOk: 'Bright indirect (survives a few weeks but gets leggy and loses flavor fast)',
      ppfdMin: 300, ppfdMax: 600, dliMin: 12, dliMax: 22,
      temperature: '10-24\u00B0C (50-75\u00B0F). Tolerates light frost outdoors. Prefers cooler conditions than most herbs.',
      humidity: 'Low to average (30-50%) \u2014 actually prefers dry air',
      humidityAction: 'Good air circulation is critical indoors. Open a window nearby when possible. Do not mist.',
      soil: 'Well-draining, sandy, slightly alkaline soil (pH 6.0-7.5). Mix in extra sand or perlite.',
      repot: 'Every 1-2 years. Terracotta pot is ideal \u2014 lets soil breathe and dry out evenly.',
      fertilizer: 'Light feeding once in spring. Too much fertilizer reduces essential oil concentration = less flavor.',
      fertilizerSeason: 'Spring only',
      tips: 'Harvest by cutting sprigs (not individual leaves) \u2014 cut above a leaf node to encourage branching. Woody stems at the base are normal and healthy. If it gets leggy indoors, it needs more direct sun. Prune after flowering to stay bushy. Flowers are edible and attract pollinators.',
      commonProblems: ['Crispy brown needle tips (too dry indoors or underwatering \u2014 check if roots are healthy first)', 'Powdery mildew (white dusty coating \u2014 improve air circulation, reduce crowding)', 'Root rot (overwatering in heavy soil \u2014 switch to terracotta pot with sandy mix)'],
      commonPests: ['Spider mites (especially in dry indoor air \u2014 increase ventilation, spray with water)', 'Whiteflies (yellow sticky traps near the plant)', 'Powdery mildew (fungal, not a pest \u2014 improve air circulation)'],
    ),
  ),

  // ── 5. Solanum lycopersicum (Cherry Tomato) ───────────────────
  PopularPlant(
    id: 'solanum_lycopersicum',
    scientific: 'Solanum lycopersicum',
    commonName: 'Cherry Tomato',
    family: 'Solanaceae',
    preset: 'Herbs',
    plantType: 'fruiting',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Cherry_tomatoes_red_and_green_2009_16x9.jpg/330px-Cherry_tomatoes_red_and_green_2009_16x9.jpg',
    description: 'Compact fruiting annual, 60-70 days seed to harvest. Needs 8+ hours direct sun minimum \u2014 without it, no fruit. Hand-pollinate indoors (shake flowering stems). Ripe fruit: edible. Leaves/stems/green fruit: toxic (solanine). Bush varieties (Tiny Tim, Micro Tom) best for indoors. One plant yields 100+ fruit.',
    difficulty: 'Medium',
    difficultyNote: 'Demanding on light (8h+) and feeding, but very productive. Bush varieties easier indoors.',
    growthRate: 'Fast',
    lifecycle: 'annual',
    lifecycleYears: '1 season',
    heightMinCm: 30,
    heightMaxCm: 100,
    heightIndoorMaxCm: 50,
    spreadMaxCm: 40,
    usedFor: ['Edible', 'Fruiting', 'Attracts pollinators'],
    usedForDetails: 'One plant yields 100+ cherry tomatoes per season. Rich in vitamins A and C. Hand-pollinate indoors by shaking flowering stems. Bush varieties (Tiny Tim, Micro Tom) ideal for windowsill or balcony.',
    tempMinC: 5, tempOptLowC: 18, tempOptHighC: 29, tempMaxC: 40,
    tempWarning: 'Below 10\u00B0C stops growth. Above 35\u00B0C causes blossom drop \u2014 no fruit.',
    wateringFreqSummerDays: 2,
    wateringFreqWinterDays: 0,
    wateringDemand: 'Very high',
    wateringSoilHint: 'Keep soil consistently moist',
    wateringMethod: 'Deep soak at the base. Consistent watering prevents fruit cracking. Mulch helps retain moisture.',
    wateringAvoid: 'Avoid wetting leaves \u2014 promotes blight. Inconsistent watering causes blossom end rot and cracking.',
    edible: true,
    edibleParts: 'Ripe fruit only \u2014 leaves and stems are toxic',
    harvestInfo: 'Pick when fully red and slightly soft to the touch. About 60-70 days from planting to first harvest. One plant can produce 100+ tomatoes.',
    poisonousToPets: true,
    poisonousToHumans: false,
    toxicityNote: 'Ripe fruit is safe. Leaves, stems, and green unripe fruit contain solanine \u2014 mildly toxic to pets and small children if eaten in quantity.',
    toxicParts: 'Leaves, stems, green unripe fruit (contain solanine). Ripe fruit is safe.',
    toxicitySeverity: 'Mild to Moderate',
    toxicitySymptoms: 'Ingestion (leaves/green fruit): nausea, vomiting, abdominal pain, diarrhea. Large quantities: headache, dizziness. Pets are more sensitive than humans.\nDermal: sap may cause mild skin irritation in sensitive individuals.',
    toxicityFirstAid: 'Ingestion: remove plant material, rinse mouth, drink water. If large amount consumed \u2014 call poison control or vet.\nDermal: wash with soap and water.\nEye contact: flush with clean water for 10\u201315 minutes.',
    soilTypes: ['Rich potting mix', 'Compost', 'Peat-based mix'],
    potType: 'Any pot with drainage, at least 5 liters for bush varieties',
    potSizeNote: 'Annual \u2014 start new each spring. Pot up seedlings once when they outgrow starter pots.',
    repotSigns: 'Seedlings outgrowing starter pots \u2014 move to final container. Do not disturb once fruiting.',
    fertilizerTypes: ['Tomato fertilizer (high potassium)', 'Balanced + calcium supplement'],
    fertilizerNpk: '5-10-10 or tomato-specific',
    fertilizerWarning: 'Start fertilizing when flowers appear, not before. Calcium supplement prevents blossom end rot.',
    genus: 'Solanum',
    order: 'Solanales',
    origin: 'South America (Peru, Ecuador)',
    goodCompanions: ['Basil', 'Carrot', 'Parsley', 'Marigold'],
    badCompanions: ['Fennel', 'Cabbage', 'Dill (when mature)'],
    companionNote: 'Basil repels aphids and whiteflies from tomatoes. Marigolds kill soil nematodes. Carrots loosen soil for tomato roots. Never plant near fennel \u2014 it inhibits tomato growth.',
    pruningInfo: 'Remove suckers (shoots growing between main stem and branches) to focus energy on fruit production. Pinch growing tip when plant reaches desired height (for determinate/bush varieties). Remove yellow lower leaves for air circulation.',
    propagationMethods: ['Seeds'],
    propagationDetail: 'Seeds: sow indoors 6-8 weeks before last frost. Plant 0.5 cm deep in moist seed starting mix. Keep warm (20-25\u00B0C). Germinates in 5-10 days. Transplant to final pot when seedlings have 2 true leaves.',
    germinationDays: 7,
    germinationTempC: '20-25\u00B0C',
    category: 'fruiting',
    care: PopularPlantCare(
      watering: 'Every 2-3 days in summer, daily in hot weather. Consistent watering prevents cracking. Deep soak, not a sprinkle.',
      wateringWinter: 'Not applicable \u2014 tomatoes are annual warm-season plants. Start new seeds in spring.',
      light: 'Full sun 8+ hours daily. The single most important factor. South-facing window minimum; balcony or grow light ideal.',
      lightAlsoOk: 'Bright indirect with supplemental grow light (at least 14 hours total light)',
      ppfdMin: 400, ppfdMax: 800, dliMin: 15, dliMax: 30,
      temperature: '18-29\u00B0C (65-85\u00B0F). Below 10\u00B0C stops growth. Above 35\u00B0C causes blossom drop.',
      humidity: 'Average (40-60%)',
      humidityAction: 'Good air circulation prevents fungal disease. Avoid wetting leaves when watering.',
      soil: 'Rich, well-draining potting mix with compost. pH 6.0-6.8. At least a 5-liter pot for bush varieties.',
      repot: 'Annual plant. Start new from seed each spring. Pot up seedlings once when they outgrow starter pots.',
      fertilizer: 'Weekly with tomato-specific fertilizer (high potassium) once flowering starts. Calcium supplement prevents blossom end rot.',
      fertilizerSeason: 'From first flowers through harvest',
      tips: 'Choose determinate (bush) varieties for indoors: Tiny Tim, Red Robin, Micro Tom. Hand-pollinate by gently shaking the plant or tapping flowers when they open. Pinch off suckers (shoots growing between main stem and branches) to focus energy on fruit. Harvest when fully colored \u2014 they ripen best on the vine.',
      commonProblems: ['Blossom end rot (black spot on bottom of fruit \u2014 calcium deficiency from inconsistent watering)', 'Leggy seedlings (not enough light \u2014 the #1 indoor problem, get a grow light)', 'Blossom drop / no fruit (too hot, too cold, or not pollinated \u2014 shake the plant daily during flowering)'],
      commonPests: ['Aphids (green clusters on stems \u2014 blast with water or insecticidal soap)', 'Whiteflies (tiny white moths \u2014 yellow sticky traps)', 'Spider mites (in dry indoor air \u2014 mist around plant, not on leaves)'],
    ),
  ),

  // ── 6. Sansevieria trifasciata (Snake Plant) ──────────────────
  PopularPlant(
    id: 'dracaena_trifasciata',
    scientific: 'Dracaena trifasciata',
    commonName: 'Snake Plant',
    family: 'Asparagaceae',
    preset: 'Succulents',
    plantType: 'decorative',
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg/330px-Snake_Plant_%28Sansevieria_trifasciata_%27Laurentii%27%29.jpg',
    description: 'Nearly indestructible. Tolerates low light, dry air, irregular watering. Purifies air (NASA study). Releases oxygen at night \u2014 ideal for bedroom. Grows slowly but lives for decades. The perfect first plant.',
    difficulty: 'Easy',
    difficultyNote: 'The most forgiving houseplant. Survives weeks of neglect. Only real killer: overwatering.',
    growthRate: 'Slow',
    lifecycle: 'perennial',
    lifecycleYears: '20-25',
    heightMinCm: 20,
    heightMaxCm: 120,
    heightIndoorMaxCm: 100,
    spreadMaxCm: 40,
    usedFor: ['Decorative', 'Air purifier'],
    usedForDetails: 'One of the top air-purifying plants (NASA Clean Air Study). Removes formaldehyde, benzene, trichloroethylene, xylene from indoor air. Unique feature: releases oxygen at night (most plants only during the day) \u2014 ideal for bedrooms. Recommended: 2-3 large plants per room for noticeable air quality improvement.',
    tempMinC: 4, tempOptLowC: 15, tempOptHighC: 27, tempMaxC: 38,
    tempWinterLowC: 12, tempWinterHighC: 25,
    tempWarning: 'Keep above 10\u00B0C. Cold drafts cause permanent scarring on leaves.',
    wateringFreqSummerDays: 14,
    wateringFreqWinterDays: 30,
    wateringDemand: 'Low',
    wateringSoilHint: 'Let soil dry completely',
    wateringWarning: 'Sensitive to lime in water \u2014 use filtered or rainwater if possible',
    wateringMethod: 'Water at the base, avoiding the leaf rosette. Let drain fully. Bottom watering works well.',
    wateringAvoid: 'Never let pot sit in water. Do not water into the center of the leaf rosette \u2014 causes rot.',
    poisonousToPets: true,
    poisonousToHumans: false,
    toxicityNote: 'Mildly toxic to cats and dogs if chewed \u2014 causes nausea, vomiting, diarrhea. Keep away from pets that like to chew leaves.',
    toxicParts: 'All parts (contains saponins)',
    toxicitySeverity: 'Mild',
    toxicitySymptoms: 'Ingestion: nausea, vomiting, diarrhea, drooling (pets). Mouth and throat irritation (humans). Usually self-limiting.\nDermal: sap may cause mild irritation or rash on sensitive skin.',
    toxicityFirstAid: 'Ingestion: remove plant material from mouth, rinse with water, offer water. Monitor pets for 24h \u2014 contact vet if vomiting persists.\nDermal: wash with soap and water.\nEye contact: flush with clean water for 10\u201315 minutes.',
    soilTypes: ['Cactus & succulent mix', 'Perlite', 'Well-draining potting soil'],
    potType: 'Terracotta \u2014 helps soil dry evenly, prevents overwatering',
    potSizeNote: 'Likes being rootbound \u2014 no rush to repot. Every 2-3 years is fine.',
    repotSigns: 'Pot cracking from root pressure, roots growing out of drainage holes, soil depleted.',
    fertilizerTypes: ['All-purpose liquid (diluted)', 'Succulent fertilizer'],
    fertilizerNpk: '10-10-10 (half strength)',
    fertilizerWarning: 'Fertilize only in spring-summer. Never in winter \u2014 plant is dormant.',
    genus: 'Dracaena',
    order: 'Asparagales',
    origin: 'West Africa (Nigeria to Congo)',
    synonyms: ['Sansevieria trifasciata'],
    goodCompanions: ['Other succulents', 'Jade Plant', 'ZZ Plant', 'Pothos'],
    badCompanions: ['Tropical plants needing high humidity'],
    companionNote: 'Group with other low-maintenance, drought-tolerant plants. They all tolerate dry air and infrequent watering. Avoid placing next to moisture-loving tropicals like Calathea.',
    pruningInfo: 'Minimal pruning needed. Remove damaged or dead leaves at the base with a clean cut. If a leaf is partially damaged, you can trim the damaged part \u2014 the rest stays healthy. Divide overcrowded clumps when repotting.',
    propagationMethods: ['Division', 'Leaf cuttings', 'Seeds (slow)'],
    propagationDetail: 'Division: separate rhizome clumps when repotting, each piece with at least one leaf. Leaf cuttings: cut a leaf into 10 cm sections, let dry for a day, plant upright in moist soil. New shoots in 4-8 weeks. Note: variegated varieties lose stripes when propagated from cuttings.',
    category: 'foliage',
    care: PopularPlantCare(
      watering: 'Every 2-3 weeks, let soil dry completely. Stick your finger 5 cm into soil \u2014 if dry, water.',
      wateringWinter: 'Once a month or less. In winter this plant barely drinks.',
      light: 'Low to bright indirect light \u2014 adapts to almost anything',
      lightAlsoOk: 'Tolerates shade, but growth slows significantly. No direct harsh sun \u2014 burns leaf tips.',
      ppfdMin: 50, ppfdMax: 300, dliMin: 2, dliMax: 12,
      temperature: '15-27\u00B0C (59-80\u00B0F). Keep above 10\u00B0C \u2014 cold drafts cause scarring.',
      humidity: 'Low to average (30-50%) \u2014 thrives in dry apartment air',
      humidityAction: 'No misting needed. Normal room air is perfect. Avoid humid bathrooms.',
      soil: 'Well-draining succulent/cactus mix with perlite. Must drain fast \u2014 standing water kills roots.',
      repot: 'Every 2-3 years. Likes being rootbound \u2014 no rush to repot. Terracotta pot helps soil dry evenly.',
      fertilizer: 'Once or twice during spring-summer with diluted all-purpose fertilizer. Less is more.',
      fertilizerSeason: 'Spring-Summer only',
      tips: 'Overwatering is the only real threat. When in doubt, skip watering. Leaves store water \u2014 wrinkly leaves mean it finally needs a drink. Propagate by leaf cuttings in water or soil. Wipe leaves monthly to remove dust \u2014 helps it photosynthesize.',
      commonProblems: ['Mushy base / yellow leaves (overwatering \u2014 stop immediately, check for root rot, repot in dry soil)', 'Brown crispy leaf tips (underwatering or low humidity \u2014 rare, check soil first)', 'Leaves falling over / splitting (physical damage or very overwatered roots)'],
      commonPests: ['Mealybugs (white cottony spots in leaf crevices \u2014 wipe with rubbing alcohol)', 'Spider mites (fine webs \u2014 wipe leaves with damp cloth)', 'Fungus gnats (tiny flies near soil \u2014 let soil dry out more between waterings)'],
    ),
  ),
];
