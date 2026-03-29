import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Modal,
  LayoutChangeEvent,
  NativeSyntheticEvent,
  NativeScrollEvent,
  Animated,
  Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { ProgressBar } from '../../src/components/ui/ProgressBar';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { POPULAR_PLANTS } from '../../src/constants/popular-plants';
import { PRESET_CARE } from '../../src/constants/presets';
import { usePlantsWithDevices } from '../../src/features/plants/api/plants-api';
import { usePlantDBDetail } from '../../src/features/plants/api/plant-db-api';
import { dbCareToPresetCare, getCommonName } from '../../src/lib/plant-db-adapter';
import { useLocationData, getOutdoorMonths, formatMonthRange, getSeasonCoefficients } from '../../src/lib/geolocation';
import { LightMeterModal } from '../../src/components/LightMeterModal';
import { useSavePlant } from '../../src/features/plants/api/identify-api';
import { addJournalEntry } from '../../src/lib/plant-journal';
import * as ImagePicker from 'expo-image-picker';
import type { PresetCare } from '../../src/constants/presets';

// ─── PlantVM ─────────────────────────────────────────────────────────

interface PlantVM {
  scientific: string;
  common_name: string;
  family: string;
  genus: string;
  order: string;
  origin: string;
  synonyms: string[];
  good_companions: string[];
  bad_companions: string[];
  companion_note: string;
  pruning_info: string;
  propagation_methods: string[];
  propagation_detail: string;
  germination_days: number;
  germination_temp_c: string;
  preset: string;
  plant_type: 'decorative' | 'greens' | 'fruiting';
  image_url?: string;
  description: string;
  difficulty: string;
  difficulty_note: string;
  growth_rate: string;
  lifecycle: string;
  lifecycle_years: string;
  height_min_cm: number;
  height_max_cm: number;
  height_indoor_max_cm: number;
  spread_max_cm: number;
  used_for: string[];
  used_for_details: string;
  watering_freq_summer_days: number;
  watering_freq_winter_days: number;
  watering_demand: string;
  watering_soil_hint: string;
  watering_warning: string;
  watering_method: string;
  watering_avoid: string;
  temp_min_c: number;
  temp_opt_low_c: number;
  temp_opt_high_c: number;
  temp_max_c: number;
  temp_winter_low_c: number;
  temp_winter_high_c: number;
  temp_warning: string;
  edible: boolean;
  edible_parts: string;
  poisonous_to_pets: boolean;
  poisonous_to_humans: boolean;
  toxicity_note: string;
  toxic_parts: string;
  toxicity_severity: string;
  toxicity_symptoms: string;
  toxicity_first_aid: string;
  soil_types: string[];
  pot_type: string;
  pot_size_note: string;
  repot_signs: string;
  fertilizer_types: string[];
  fertilizer_npk: string;
  fertilizer_warning: string;
  harvest_info: string;
  care: PresetCare;
  hasDevice: boolean;
  device_id?: string;
  device_online?: boolean;
  moisture_pct?: number | null;
  battery_pct?: number | null;
  battery_charging?: boolean;
  device_mode?: string;
  start_pct: number;
  stop_pct: number;
  soil_ph_min?: number;
  soil_ph_max?: number;
  isInCollection: boolean;
}

function usePlantVM(id: string | undefined): PlantVM | null {
  const { plants } = usePlantsWithDevices();
  const { data: dbEntry } = usePlantDBDetail(id);

  return useMemo(() => {
    if (!id) return null;

    const userPlant = plants.find((p) => p.plant_id === id);
    if (userPlant) {
      const presetCare = PRESET_CARE[userPlant.preset ?? 'Standard'] ?? PRESET_CARE.Standard;
      const care = dbEntry?.care ? dbCareToPresetCare(dbEntry.care, presetCare) : presetCare;
      const lib = POPULAR_PLANTS.find((p) => p.id === id);
      return {
        scientific: userPlant.scientific ?? '',
        common_name: userPlant.common_name ?? '',
        family: userPlant.family ?? '',
        genus: lib?.genus ?? '',
        order: lib?.order ?? '',
        origin: lib?.origin ?? '',
        synonyms: lib?.synonyms ?? [],
        good_companions: lib?.good_companions ?? [],
        bad_companions: lib?.bad_companions ?? [],
        companion_note: lib?.companion_note ?? '',
        pruning_info: lib?.pruning_info ?? '',
        propagation_methods: lib?.propagation_methods ?? [],
        propagation_detail: lib?.propagation_detail ?? '',
        germination_days: lib?.germination_days ?? 0,
        germination_temp_c: lib?.germination_temp_c ?? '',
        preset: userPlant.preset ?? 'Standard',
        plant_type: (lib?.plant_type ?? 'decorative') as 'decorative' | 'greens' | 'fruiting',
        image_url: userPlant.image_url,
        description: dbEntry?.description ?? lib?.description ?? '',
        difficulty: dbEntry?.care?.difficulty ?? lib?.difficulty ?? '',
        difficulty_note: lib?.difficulty_note ?? '',
        growth_rate: dbEntry?.care?.growth_rate ?? lib?.growth_rate ?? '',
        lifecycle: dbEntry?.care?.lifecycle ?? lib?.lifecycle ?? '',
        height_min_cm: lib?.height_min_cm ?? 0,
        height_max_cm: dbEntry?.care?.height_max_cm ?? lib?.height_max_cm ?? 0,
        height_indoor_max_cm: lib?.height_indoor_max_cm ?? 0,
        spread_max_cm: lib?.spread_max_cm ?? 0,
        edible: !!(dbEntry?.edible ?? lib?.edible),
        edible_parts: lib?.edible_parts ?? '',
        poisonous_to_pets: userPlant.poisonous_to_pets ?? false,
        poisonous_to_humans: userPlant.poisonous_to_humans ?? false,
        toxicity_note: userPlant.toxicity_note ?? '',
        toxic_parts: lib?.toxic_parts ?? '',
        toxicity_severity: lib?.toxicity_severity ?? '',
        toxicity_symptoms: lib?.toxicity_symptoms ?? '',
        toxicity_first_aid: lib?.toxicity_first_aid ?? '',
        soil_types: lib?.soil_types ?? [],
        pot_type: lib?.pot_type ?? '',
        pot_size_note: lib?.pot_size_note ?? '',
        repot_signs: lib?.repot_signs ?? '',
        fertilizer_types: lib?.fertilizer_types ?? [],
        fertilizer_npk: lib?.fertilizer_npk ?? '',
        fertilizer_warning: lib?.fertilizer_warning ?? '',
        harvest_info: lib?.harvest_info ?? '',
        lifecycle_years: lib?.lifecycle_years ?? '',
        used_for: lib?.used_for ?? [],
        used_for_details: lib?.used_for_details ?? '',
        watering_freq_summer_days: lib?.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib?.watering_freq_winter_days ?? 14,
        watering_demand: lib?.watering_demand ?? '',
        watering_soil_hint: lib?.watering_soil_hint ?? '',
        watering_warning: lib?.watering_warning ?? '',
        watering_method: lib?.watering_method ?? '',
        watering_avoid: lib?.watering_avoid ?? '',
        temp_min_c: lib?.temp_min_c ?? 5,
        temp_opt_low_c: lib?.temp_opt_low_c ?? 15,
        temp_opt_high_c: lib?.temp_opt_high_c ?? 25,
        temp_max_c: lib?.temp_max_c ?? 35,
        temp_winter_low_c: lib?.temp_winter_low_c ?? lib?.temp_opt_low_c ?? 12,
        temp_winter_high_c: lib?.temp_winter_high_c ?? lib?.temp_opt_high_c ?? 22,
        temp_warning: lib?.temp_warning ?? '',
        care,
        isInCollection: true,
        hasDevice: userPlant.active && !!userPlant.device_id,
        device_id: userPlant.device_id,
        device_online: userPlant.device_online,
        moisture_pct: userPlant.moisture_pct,
        battery_pct: userPlant.battery_pct,
        battery_charging: userPlant.battery_charging,
        device_mode: userPlant.device_mode,
        start_pct: userPlant.start_pct ?? care.start_pct,
        stop_pct: userPlant.stop_pct ?? care.stop_pct,
        soil_ph_min: dbEntry?.care?.soil_ph_min,
        soil_ph_max: dbEntry?.care?.soil_ph_max,
      };
    }

    if (dbEntry) {
      const presetCare = PRESET_CARE[dbEntry.preset] ?? PRESET_CARE.Standard;
      const care = dbCareToPresetCare(dbEntry.care, presetCare);
      const category = dbEntry.category as 'decorative' | 'greens' | 'fruiting';
      const lib = POPULAR_PLANTS.find((p) => p.id === id);
      return {
        scientific: dbEntry.scientific,
        common_name: getCommonName(dbEntry),
        family: dbEntry.family,
        genus: lib?.genus ?? dbEntry.genus ?? '',
        order: lib?.order ?? '',
        origin: lib?.origin ?? '',
        synonyms: lib?.synonyms ?? [],
        good_companions: lib?.good_companions ?? [],
        bad_companions: lib?.bad_companions ?? [],
        companion_note: lib?.companion_note ?? '',
        pruning_info: lib?.pruning_info ?? '',
        propagation_methods: lib?.propagation_methods ?? [],
        propagation_detail: lib?.propagation_detail ?? '',
        germination_days: lib?.germination_days ?? 0,
        germination_temp_c: lib?.germination_temp_c ?? '',
        preset: dbEntry.preset,
        plant_type: category === 'greens' || category === 'fruiting' ? category : 'decorative',
        image_url: dbEntry.image_url,
        description: dbEntry.description ?? '',
        difficulty: dbEntry.care?.difficulty ?? '',
        difficulty_note: lib?.difficulty_note ?? '',
        growth_rate: dbEntry.care?.growth_rate ?? '',
        lifecycle: dbEntry.care?.lifecycle ?? '',
        height_min_cm: lib?.height_min_cm ?? 0,
        height_max_cm: dbEntry.care?.height_max_cm ?? lib?.height_max_cm ?? 0,
        height_indoor_max_cm: lib?.height_indoor_max_cm ?? 0,
        spread_max_cm: lib?.spread_max_cm ?? 0,
        edible: !!dbEntry.edible,
        edible_parts: lib?.edible_parts ?? '',
        poisonous_to_pets: !!dbEntry.care?.toxic_to_pets,
        poisonous_to_humans: !!dbEntry.care?.toxic_to_humans,
        toxicity_note: dbEntry.care?.toxicity_note ?? '',
        toxic_parts: lib?.toxic_parts ?? '',
        toxicity_severity: lib?.toxicity_severity ?? '',
        toxicity_symptoms: lib?.toxicity_symptoms ?? '',
        toxicity_first_aid: lib?.toxicity_first_aid ?? '',
        soil_types: lib?.soil_types ?? [],
        pot_type: lib?.pot_type ?? '',
        pot_size_note: lib?.pot_size_note ?? '',
        repot_signs: lib?.repot_signs ?? '',
        fertilizer_types: lib?.fertilizer_types ?? [],
        fertilizer_npk: lib?.fertilizer_npk ?? '',
        fertilizer_warning: lib?.fertilizer_warning ?? '',
        harvest_info: lib?.harvest_info ?? '',
        lifecycle_years: lib?.lifecycle_years ?? '',
        used_for: lib?.used_for ?? [],
        used_for_details: lib?.used_for_details ?? '',
        watering_freq_summer_days: lib?.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib?.watering_freq_winter_days ?? 14,
        watering_demand: lib?.watering_demand ?? '',
        watering_soil_hint: lib?.watering_soil_hint ?? '',
        watering_warning: lib?.watering_warning ?? '',
        watering_method: lib?.watering_method ?? '',
        watering_avoid: lib?.watering_avoid ?? '',
        temp_min_c: lib?.temp_min_c ?? 5,
        temp_opt_low_c: lib?.temp_opt_low_c ?? 15,
        temp_opt_high_c: lib?.temp_opt_high_c ?? 25,
        temp_max_c: lib?.temp_max_c ?? 35,
        temp_winter_low_c: lib?.temp_winter_low_c ?? lib?.temp_opt_low_c ?? 12,
        temp_winter_high_c: lib?.temp_winter_high_c ?? lib?.temp_opt_high_c ?? 22,
        temp_warning: lib?.temp_warning ?? '',
        care,
        isInCollection: false,
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
        soil_ph_min: dbEntry.care?.soil_ph_min,
        soil_ph_max: dbEntry.care?.soil_ph_max,
      };
    }

    const lib = POPULAR_PLANTS.find((p) => p.id === id);
    if (lib) {
      const presetCare = PRESET_CARE[lib.preset] ?? PRESET_CARE.Standard;
      const care = lib.care ? { ...presetCare, ...lib.care } : presetCare;
      return {
        scientific: lib.scientific,
        common_name: lib.common_name,
        family: lib.family,
        genus: lib.genus ?? '',
        order: lib.order ?? '',
        origin: lib.origin ?? '',
        synonyms: lib.synonyms ?? [],
        good_companions: lib.good_companions ?? [],
        bad_companions: lib.bad_companions ?? [],
        companion_note: lib.companion_note ?? '',
        pruning_info: lib.pruning_info ?? '',
        propagation_methods: lib.propagation_methods ?? [],
        propagation_detail: lib.propagation_detail ?? '',
        germination_days: lib.germination_days ?? 0,
        germination_temp_c: lib.germination_temp_c ?? '',
        preset: lib.preset,
        plant_type: lib.plant_type,
        image_url: lib.image_url,
        description: lib.description ?? '',
        difficulty: lib.difficulty ?? '',
        difficulty_note: lib.difficulty_note ?? '',
        growth_rate: lib.growth_rate ?? '',
        lifecycle: lib.lifecycle ?? '',
        height_min_cm: lib.height_min_cm ?? 0,
        height_max_cm: lib.height_max_cm ?? 0,
        height_indoor_max_cm: lib.height_indoor_max_cm ?? 0,
        spread_max_cm: lib.spread_max_cm ?? 0,
        edible: !!lib.edible,
        edible_parts: lib.edible_parts ?? '',
        poisonous_to_pets: lib.poisonous_to_pets,
        poisonous_to_humans: lib.poisonous_to_humans,
        toxicity_note: lib.toxicity_note,
        toxic_parts: lib.toxic_parts ?? '',
        toxicity_severity: lib.toxicity_severity ?? '',
        toxicity_symptoms: lib.toxicity_symptoms ?? '',
        toxicity_first_aid: lib.toxicity_first_aid ?? '',
        soil_types: lib.soil_types ?? [],
        pot_type: lib.pot_type ?? '',
        pot_size_note: lib.pot_size_note ?? '',
        repot_signs: lib.repot_signs ?? '',
        fertilizer_types: lib.fertilizer_types ?? [],
        fertilizer_npk: lib.fertilizer_npk ?? '',
        fertilizer_warning: lib.fertilizer_warning ?? '',
        harvest_info: lib.harvest_info ?? '',
        lifecycle_years: lib.lifecycle_years ?? '',
        used_for: lib.used_for ?? [],
        used_for_details: lib.used_for_details ?? '',
        watering_freq_summer_days: lib.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib.watering_freq_winter_days ?? 14,
        watering_demand: lib.watering_demand ?? '',
        watering_soil_hint: lib.watering_soil_hint ?? '',
        watering_warning: lib.watering_warning ?? '',
        watering_method: lib.watering_method ?? '',
        watering_avoid: lib.watering_avoid ?? '',
        temp_min_c: lib.temp_min_c ?? 5,
        temp_opt_low_c: lib.temp_opt_low_c ?? 15,
        temp_opt_high_c: lib.temp_opt_high_c ?? 25,
        temp_max_c: lib.temp_max_c ?? 35,
        temp_winter_low_c: lib.temp_winter_low_c ?? lib.temp_opt_low_c ?? 12,
        temp_winter_high_c: lib.temp_winter_high_c ?? lib.temp_opt_high_c ?? 22,
        temp_warning: lib.temp_warning ?? '',
        care,
        isInCollection: false,
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
      };
    }

    return null;
  }, [id, plants, dbEntry]);
}

// ─── Section & Group definitions ─────────────────────────────────────

type SectionKey =
  | 'water' | 'light' | 'humidity' | 'temperature' | 'outdoor' | 'toxicity'
  | 'lifecycle' | 'used_for' | 'soil' | 'fertilizing' | 'pruning'
  | 'harvest' | 'propagation' | 'difficulty' | 'size' | 'taxonomy' | 'companions';

type GroupKey = 'care' | 'environment' | 'safety' | 'growing' | 'about' | 'companions';

interface SectionDef {
  key: SectionKey;
  label: string;
}

interface GroupDef {
  key: GroupKey;
  label: string;
  sections: SectionDef[];
}

function getGroups(plant: PlantVM): GroupDef[] {
  const growingSections: SectionDef[] = [
    { key: 'pruning', label: 'Pruning' },
  ];
  if (plant.plant_type === 'greens' || plant.plant_type === 'fruiting') {
    growingSections.push({ key: 'harvest', label: 'Harvest' });
  }
  growingSections.push({ key: 'propagation', label: 'Propagation' });

  return [
    {
      key: 'care', label: 'Care',
      sections: [
        { key: 'water', label: 'Water' },
        { key: 'soil', label: 'Soil' },
        { key: 'fertilizing', label: 'Fertilizing' },
      ],
    },
    {
      key: 'environment', label: 'Environment',
      sections: [
        { key: 'light', label: 'Light' },
        { key: 'humidity', label: 'Air Humidity' },
        { key: 'temperature', label: 'Air Temperature' },
        { key: 'outdoor', label: 'Outdoor' },
      ],
    },
    {
      key: 'safety', label: 'Toxicity',
      sections: [
        { key: 'toxicity', label: 'Toxicity' },
      ],
    },
    {
      key: 'growing', label: 'Growing',
      sections: growingSections,
    },
    {
      key: 'about', label: 'About',
      sections: [
        { key: 'difficulty', label: 'Difficulty' },
        { key: 'size', label: 'Size' },
        { key: 'lifecycle', label: 'Lifecycle' },
        { key: 'used_for', label: 'Used for' },
        { key: 'taxonomy', label: 'Taxonomy' },
      ],
    },
    {
      key: 'companions', label: 'Companions',
      sections: [
        { key: 'companions', label: 'Companions' },
      ],
    },
  ];
}

// Flat list of all sections for scroll tracking (preserves layout order)
function getSections(plant: PlantVM): SectionDef[] {
  const groups = getGroups(plant);
  const sections: SectionDef[] = [];
  for (const g of groups) {
    sections.push(...g.sections);
  }
  return sections;
}

// ─── Screen ──────────────────────────────────────────────────────────

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const plant = usePlantVM(id);
  const saveMutation = useSavePlant();

  const handleAddToCollection = useCallback(() => {
    if (!plant) return;
    saveMutation.mutate(
      {
        input: {
          device_id: 'user-collection',
          plant: {
            scientific: plant.scientific,
            common_name: plant.common_name,
            family: plant.family,
            preset: plant.preset,
            start_pct: plant.start_pct,
            stop_pct: plant.stop_pct,
            image_url: plant.image_url,
            poisonous_to_pets: plant.poisonous_to_pets,
            poisonous_to_humans: plant.poisonous_to_humans,
            toxicity_note: plant.toxicity_note,
          },
        },
        wateringFreqDays: plant.watering_freq_summer_days,
      },
      {
        onError: (err) => {
          Alert.alert('Error', err instanceof Error ? err.message : 'Failed to save plant');
        },
      },
    );
  }, [plant, saveMutation]);

  const handleAddPhoto = useCallback(async () => {
    if (!plant || !id) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });
    if (result.canceled || !result.assets[0]) return;
    await addJournalEntry(id, result.assets[0].uri);
    Alert.alert('Photo added', 'Check your Journal for this plant.');
  }, [plant, id]);

  const handleTakePhoto = useCallback(async () => {
    if (!plant || !id) return;
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return;
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.8,
    });
    if (result.canceled || !result.assets[0]) return;
    await addJournalEntry(id, result.assets[0].uri);
    Alert.alert('Photo added', 'Check your Journal for this plant.');
  }, [plant, id]);

  const mainScrollRef = useRef<ScrollView>(null);
  const tabScrollRef = useRef<ScrollView>(null);
  const sectionYs = useRef<Record<string, number>>({});
  const containerY = useRef(0);
  const stickyNavHeight = useRef(0);
  const tabXs = useRef<Record<string, number>>({});
  const [activeGroup, setActiveGroup] = useState<GroupKey>('care');
  const [showWateringGuide, setShowWateringGuide] = useState(false);
  const [showLightGuide, setShowLightGuide] = useState(false);
  const [showHumidityGuide, setShowHumidityGuide] = useState(false);
  const [showTempGuide, setShowTempGuide] = useState(false);
  const [showOutdoorGuide, setShowOutdoorGuide] = useState(false);
  const [showToxicityGuide, setShowToxicityGuide] = useState(false);
  const [showUsedForGuide, setShowUsedForGuide] = useState(false);
  const [showSoilGuide, setShowSoilGuide] = useState(false);
  const [showFertGuide, setShowFertGuide] = useState(false);
  const [showSizeGuide, setShowSizeGuide] = useState(false);
  const [showPropGuide, setShowPropGuide] = useState(false);
  const [showHarvestGuide, setShowHarvestGuide] = useState(false);
  const [showCompanionGuide, setShowCompanionGuide] = useState(false);
  const [showLightMeter, setShowLightMeter] = useState(false);
  const isAutoScrolling = useRef(false);

  const onContainerLayout = useCallback((e: LayoutChangeEvent) => {
    containerY.current = e.nativeEvent.layout.y;
  }, []);

  const onStickyNavLayout = useCallback((e: LayoutChangeEvent) => {
    stickyNavHeight.current = e.nativeEvent.layout.height;
  }, []);

  const onSectionLayout = useCallback((key: string, e: LayoutChangeEvent) => {
    // y relative to sectionsContainer; absolute = containerY + local y
    sectionYs.current[key] = e.nativeEvent.layout.y;
  }, []);

  const onTabLayout = useCallback((key: string, e: LayoutChangeEvent) => {
    tabXs.current[key] = e.nativeEvent.layout.x;
  }, []);

  const scrollTabBarTo = useCallback((key: GroupKey) => {
    const x = tabXs.current[key];
    if (x != null && tabScrollRef.current) {
      tabScrollRef.current.scrollTo({ x: Math.max(0, x - 40), animated: true });
    }
  }, []);

  const getAbsoluteY = useCallback((key: string): number | undefined => {
    const localY = sectionYs.current[key];
    if (localY == null) return undefined;
    return containerY.current + localY;
  }, []);

  const scrollToGroup = useCallback((groupKey: GroupKey) => {
    if (!plant) return;
    const groups = getGroups(plant);
    const group = groups.find((g) => g.key === groupKey);
    if (!group || group.sections.length === 0) return;
    // Scroll to first section of the group
    const firstSectionKey = group.sections[0].key;
    const absY = getAbsoluteY(firstSectionKey);
    if (absY != null && mainScrollRef.current) {
      isAutoScrolling.current = true;
      activeGroupRef.current = groupKey;
      setActiveGroup(groupKey);
      scrollTabBarTo(groupKey);
      const navH = stickyNavHeight.current || 120;
      mainScrollRef.current.scrollTo({ y: absY - navH, animated: true });
      setTimeout(() => { isAutoScrolling.current = false; }, 600);
    }
  }, [plant, scrollTabBarTo, getAbsoluteY]);

  // Keep scrollToSection for internal use (guide buttons etc)
  const scrollToSection = useCallback((key: SectionKey) => {
    const absY = getAbsoluteY(key);
    if (absY != null && mainScrollRef.current) {
      isAutoScrolling.current = true;
      const navH = stickyNavHeight.current || 120;
      mainScrollRef.current.scrollTo({ y: absY - navH, animated: true });
      setTimeout(() => { isAutoScrolling.current = false; }, 600);
    }
  }, [getAbsoluteY]);

  const activeGroupRef = useRef<GroupKey>('care');

  // Map section key → group key for scroll tracking
  const sectionToGroup = useMemo((): Record<string, GroupKey> => {
    if (!plant) return {};
    const map: Record<string, GroupKey> = {};
    for (const g of getGroups(plant)) {
      for (const s of g.sections) {
        map[s.key] = g.key;
      }
    }
    return map;
  }, [plant]);

  const onMainScroll = useCallback((e: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isAutoScrolling.current || !plant) return;
    const navH = stickyNavHeight.current || 120;
    const scrollY = e.nativeEvent.contentOffset.y + navH + 20;
    const sections = getSections(plant);
    let currentSection = sections[0]?.key ?? 'water';
    for (const sec of sections) {
      const absY = getAbsoluteY(sec.key);
      if (absY != null && scrollY >= absY) {
        currentSection = sec.key;
      }
    }
    const currentGroup = sectionToGroup[currentSection] ?? 'care';
    if (currentGroup !== activeGroupRef.current) {
      activeGroupRef.current = currentGroup;
      setActiveGroup(currentGroup);
      scrollTabBarTo(currentGroup);
    }
  }, [plant, scrollTabBarTo, getAbsoluteY]);

  if (!plant) {
    return (
      <View style={styles.centered}>
        <Stack.Screen options={{ title: 'Plant' }} />
        <Ionicons name="leaf-outline" size={48} color={Colors.textSecondary} />
        <Text style={styles.notFoundText}>Plant not found</Text>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backLink}>Go back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const title = plant.common_name || plant.scientific;
  const isToxic = plant.poisonous_to_pets || plant.poisonous_to_humans;
  const { care } = plant;
  const sections = getSections(plant);

  // Location & outdoor data
  const locationData = useLocationData();
  const outdoorMonths = locationData.monthlyAvgTemps.length === 12
    ? getOutdoorMonths(plant.temp_min_c, locationData.monthlyAvgTemps)
    : null;
  const pottedRange = outdoorMonths ? formatMonthRange(outdoorMonths.potted) : null;
  const inGroundRange = outdoorMonths ? formatMonthRange(outdoorMonths.inGround) : null;

  // Water demand level
  const waterDrops = care.watering.toLowerCase().includes('2-3 week') ? 1
    : care.watering.toLowerCase().includes('7-10') || care.watering.toLowerCase().includes('every 7') ? 2 : 3;
  const waterLabel = waterDrops === 1 ? 'Low' : waterDrops === 2 ? 'Medium' : 'High';

  // Light level
  const lightIcon: keyof typeof Ionicons.glyphMap =
    care.light.includes('Full') ? 'sunny' : care.light.includes('indirect') ? 'partly-sunny' : 'cloudy';
  const lightLabel = care.light.includes('Full') ? 'Full sun' : care.light.includes('indirect') ? 'Indirect' : 'Part sun';

  // Difficulty
  const diffColor = plant.difficulty === 'Advanced' ? Colors.error
    : plant.difficulty === 'Medium' ? '#F59E0B' : Colors.success;
  const diffBg = plant.difficulty === 'Advanced' ? '#FEE2E2'
    : plant.difficulty === 'Medium' ? '#FFF8E1' : '#DCFCE7';
  const diffStars = plant.difficulty === 'Advanced' ? 3 : plant.difficulty === 'Medium' ? 2 : 1;

  // Watering frequency for current month
  const now = new Date();
  const monthIndex = now.getMonth(); // 0-11
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const currentMonth = monthNames[monthIndex];
  // Jan=3.0 (deep dormancy) → Jun-Aug=1.0 (active growth) → Dec=2.8
  const seasonCoeffs = getSeasonCoefficients(locationData.latitude || null);
  const seasonCoeff = seasonCoeffs[monthIndex];
  const baseDays = plant.watering_freq_summer_days || 7;
  const currentWateringDays = Math.round(baseDays * seasonCoeff);

  // stickyHeaderIndices: hero=0, name=1, desc(optional)=2, stickyNav is next
  // We always render desc wrapper (even if empty) to keep indices stable
  const stickyIndex = 3; // hero(0), name(1), desc(2), stickyNav(3)

  return (
    <>
      <Stack.Screen options={{ title }} />
      <ScrollView
        ref={mainScrollRef}
        style={styles.container}
        contentContainerStyle={styles.scroll}
        onScroll={onMainScroll}
        scrollEventThrottle={64}
        stickyHeaderIndices={[stickyIndex]}
      >

        {/* ═══ CHILD 0: HERO ═══ */}
        {plant.image_url ? (
          <Image source={{ uri: plant.image_url }} style={styles.hero} />
        ) : (
          <View style={[styles.hero, styles.heroPlaceholder]}>
            <Ionicons name="leaf" size={64} color={Colors.accent} />
          </View>
        )}

        {/* ═══ CHILD 1: NAME ═══ */}
        <View style={styles.nameBlock}>
          <View style={styles.nameRow}>
            <Text style={[styles.name, { flex: 1 }]}>{plant.common_name || plant.scientific}</Text>
            {plant.isInCollection && (
              <TouchableOpacity onPress={handleTakePhoto} style={styles.addPhotoBtn} activeOpacity={0.7}>
                <Ionicons name="camera-outline" size={20} color={Colors.primary} />
              </TouchableOpacity>
            )}
          </View>
          {plant.common_name ? (
            <Text style={styles.scientific}>{plant.scientific}</Text>
          ) : null}
        </View>

        {/* ═══ CHILD 2: DESCRIPTION (always rendered for stable index) ═══ */}
        <View>
          {plant.description ? (
            <View style={styles.descBubble}>
              <ExpandableText text={plant.description} maxLines={3} />
            </View>
          ) : null}
        </View>

        {/* ═══ CHILD 3: STICKY NAV (badges + tabs) ═══ */}
        <View style={styles.stickyNav} onLayout={onStickyNavLayout}>
          <View style={styles.badgeRow}>
            <RoundBadge
              icon="water"
              label={waterLabel}
              bg="#EBF5FF"
              color={Colors.moisture}
              extraContent={<WaterDrops count={waterDrops} />}
            />
            <RoundBadge
              icon={lightIcon}
              label={lightLabel}
              bg="#FFF8E1"
              color="#F59E0B"
            />
            {plant.difficulty ? (
              <RoundBadge
                icon="star"
                label={plant.difficulty}
                bg={diffBg}
                color={diffColor}
                extraContent={<DifficultyStars count={diffStars} color={diffColor} />}
              />
            ) : null}
            {isToxic && (
              <RoundBadge
                icon={plant.poisonous_to_humans ? 'skull-outline' : 'warning-outline'}
                label="Toxic"
                bg="#FEE2E2"
                color={Colors.error}
              />
            )}
          </View>

          <ScrollView
            ref={tabScrollRef}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.tabBar}
          >
            {getGroups(plant).map((group) => (
              <TouchableOpacity
                key={group.key}
                activeOpacity={0.7}
                onPress={() => scrollToGroup(group.key)}
                onLayout={(e) => onTabLayout(group.key, e)}
                style={[styles.tab, activeGroup === group.key && styles.tabActive]}
              >
                <Text style={[styles.tabText, activeGroup === group.key && styles.tabTextActive]}>
                  {group.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* ═══ CHILD 4: ALL SECTIONS (long feed) ═══ */}
        <View style={styles.sectionsContainer} onLayout={onContainerLayout}>

          {/* ═══ GROUP: Care ═══ */}

          {/* ── 1. Water ── */}
          <View onLayout={(e) => onSectionLayout('water', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.water }]}>
            <SectionTitle text="Water" />
            <InfoRow icon="water-outline" text={`Every ~${currentWateringDays} days in ${currentMonth}`} sub={plant.watering_demand ? `${plant.watering_demand} demand` : undefined} />
            {plant.watering_warning ? (
              <InfoBox text={plant.watering_warning} variant="warning" />
            ) : null}
            {plant.hasDevice && plant.moisture_pct != null && (
              <View style={styles.liveBlock}>
                <View style={styles.liveHeader}>
                  <View style={styles.liveDot} />
                  <Text style={styles.liveLabel}>Soil Moisture</Text>
                  <Text style={styles.liveValue}>{plant.moisture_pct}%</Text>
                </View>
                <ProgressBar value={plant.moisture_pct} color={Colors.moisture} />
              </View>
            )}
            <TouchableOpacity onPress={() => setShowWateringGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Watering guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 2. Soil ── */}
          <View onLayout={(e) => onSectionLayout('soil', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.soil }]}>
            <SectionTitle text="Soil" />
            {plant.soil_types.length > 0 && (
              <View style={styles.chipRow}>
                {plant.soil_types.map((t) => (
                  <View key={t} style={styles.chip}><Text style={styles.chipText}>{t}</Text></View>
                ))}
              </View>
            )}
            {plant.soil_ph_min != null && plant.soil_ph_min > 0 && plant.soil_ph_max != null && (
              <PHBar min={plant.soil_ph_min} max={plant.soil_ph_max} />
            )}
            <InfoRow icon="swap-vertical-outline" text={`Repot: ${care.repot}`} sub="Repotting" />
            <TouchableOpacity onPress={() => setShowSoilGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Soil & repotting guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 3. Fertilizing ── */}
          <View onLayout={(e) => onSectionLayout('fertilizing', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.fertilizing }]}>
            <SectionTitle text="Fertilizing" />
            <InfoRow icon="leaf-outline" text={care.fertilizer} sub={care.fertilizer_season} />
            <TouchableOpacity onPress={() => setShowFertGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>When and how to feed</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ═══ GROUP: Environment ═══ */}

          {/* ── 5. Light ── */}
          <View onLayout={(e) => onSectionLayout('light', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.light }]}>
            <SectionTitle text="Light" />
            <InfoRow icon="sunny-outline" text={care.light} sub="Preferred" />
            <View style={{ flexDirection: 'row', gap: Spacing.sm, marginTop: Spacing.xs }}>
              <TouchableOpacity onPress={() => setShowLightMeter(true)} style={[styles.measureLightBtn, { flex: 1 }]}>
                <Ionicons name="flashlight-outline" size={16} color="#fff" />
                <Text style={[styles.measureLightText, { fontSize: FontSize.xs }]}>Measure</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setShowLightGuide(true)} style={[styles.guideBtn, { flex: 1, marginTop: 0, borderTopWidth: 0 }]}>
                <Text style={styles.guideBtnText}>Learn more</Text>
                <Ionicons name="chevron-forward" size={14} color={Colors.primary} />
              </TouchableOpacity>
            </View>
          </View>

          {/* ── 6. Air Humidity ── */}
          <View onLayout={(e) => onSectionLayout('humidity', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.humidity }]}>
            <SectionTitle text="Air Humidity" />
            <HumidityBar level={care.humidity} />
            <TouchableOpacity onPress={() => setShowHumidityGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Managing humidity</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 7. Air Temperature ── */}
          <View onLayout={(e) => onSectionLayout('temperature', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.temperature }]}>
            <SectionTitle text="Air Temperature" />
            <Text style={[styles.bodyText, { fontWeight: '600', marginBottom: Spacing.xs }]}>Ideal range</Text>
            <TempRangeBar optLow={plant.temp_opt_low_c} optHigh={plant.temp_opt_high_c} />
            <InfoRow icon="thermometer-outline" text={`Min ${plant.temp_min_c}°C / Max ${plant.temp_max_c}°C`} sub="Survival limits" />
            <TouchableOpacity onPress={() => setShowTempGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Temperature details</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 8. Outdoor ── */}
          <View onLayout={(e) => onSectionLayout('outdoor', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.outdoor }]}>
            <SectionTitle text="Outdoor" />
            {locationData.isLoading ? (
              <InfoRow icon="location-outline" text="Checking your location..." sub="" />
            ) : locationData.error ? (
              <InfoRow icon="leaf-outline" text="Enable location to see outdoor months" sub="" />
            ) : (
              <InfoRow icon="leaf-outline" text={pottedRange === 'Not recommended' ? 'Not recommended for outdoor' : pottedRange === 'Year-round' ? 'Can stay outside year-round' : `${pottedRange} — safe to keep outside`} sub="" />
            )}
            <TouchableOpacity onPress={() => setShowOutdoorGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Can I put it outside?</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ═══ GROUP: Safety ═══ */}

          {/* ── 9. Toxicity ── */}
          <View onLayout={(e) => onSectionLayout('toxicity', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.toxicity }]}>
            <SectionTitle text="Toxicity" />
            {isToxic ? (
              <>
                <InfoRow icon="alert-circle" text={`Toxic${plant.toxicity_severity ? ` (${plant.toxicity_severity})` : ''}`} iconColor={Colors.error} />
                <View style={styles.chipRow}>
                  {plant.poisonous_to_humans && <View style={styles.chip}><Text style={styles.chipText}>Humans</Text></View>}
                  {plant.poisonous_to_pets && <View style={styles.chip}><Text style={styles.chipText}>Animals</Text></View>}
                </View>
                <TouchableOpacity onPress={() => setShowToxicityGuide(true)} style={styles.guideBtn}>
                  <Text style={styles.guideBtnText}>Toxicity details</Text>
                  <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
                </TouchableOpacity>
              </>
            ) : (
              <InfoRow icon="checkmark-circle" text="Non-toxic to humans and pets" iconColor={Colors.success} />
            )}
          </View>

          {/* ═══ GROUP: Growing ═══ */}

          {/* ── Pruning ── */}
          <View onLayout={(e) => onSectionLayout('pruning', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.pruning }]}>
            <SectionTitle text="Pruning" />
            {plant.pruning_info ? (
              <Text style={styles.bodyText} numberOfLines={3}>{plant.pruning_info}</Text>
            ) : (
              <Text style={styles.bodyText}>Remove dead or damaged leaves. Prune to shape as needed.</Text>
            )}
          </View>

          {/* ── Harvest (edible only) ── */}
          {(plant.plant_type === 'greens' || plant.plant_type === 'fruiting') && (
            <View onLayout={(e) => onSectionLayout('harvest', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.harvest }]}>
              <SectionTitle text="Harvest" />
              {plant.edible_parts ? (
                <InfoRow icon="nutrition-outline" text={plant.edible_parts} sub="Edible parts" iconColor={Colors.success} />
              ) : null}
              <TouchableOpacity onPress={() => setShowHarvestGuide(true)} style={styles.guideBtn}>
                <Text style={styles.guideBtnText}>Harvesting guide</Text>
                <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
              </TouchableOpacity>
            </View>
          )}

          {/* ── 11. Propagation ── */}
          <View onLayout={(e) => onSectionLayout('propagation', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.propagation }]}>
            <SectionTitle text="Propagation" />
            {plant.propagation_methods.length > 0 && (
              <View style={styles.chipRow}>
                {plant.propagation_methods.map((m) => (
                  <View key={m} style={styles.chip}><Text style={styles.chipText}>{m}</Text></View>
                ))}
              </View>
            )}
            <TouchableOpacity onPress={() => setShowPropGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>How to grow a new one</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ═══ GROUP: About ═══ */}

          {/* ── 12. Difficulty ── */}
          <View onLayout={(e) => onSectionLayout('difficulty', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.difficulty }]}>
            <SectionTitle text="Difficulty" />
            {plant.difficulty ? (
              <>
                <View style={styles.difficultyRow}>
                  <DifficultyStars count={diffStars} color={diffColor} size={22} />
                  <Text style={[styles.difficultyLabel, { color: diffColor }]}>{plant.difficulty}</Text>
                </View>
                {plant.difficulty_note ? (
                  <InfoBox text={plant.difficulty_note} variant="info" />
                ) : null}
              </>
            ) : (
              <Text style={[styles.bodyText, { color: Colors.textSecondary }]}>No data available yet</Text>
            )}
          </View>

          {/* ── 13. Size ── */}
          <View onLayout={(e) => onSectionLayout('size', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.size }]}>
            <SectionTitle text="Size" />
            <InfoRow icon="arrow-up-outline" text={plant.height_max_cm > 0 ? `${plant.height_min_cm || '?'} – ${plant.height_max_cm} cm` : 'Not specified'} sub="Height (mature)" />
            {plant.spread_max_cm > 0 && (
              <InfoRow icon="swap-horizontal-outline" text={`Up to ${plant.spread_max_cm} cm`} sub="Spread" />
            )}
            <TouchableOpacity onPress={() => setShowSizeGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>How big will it get?</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 14. Lifecycle ── */}
          <View onLayout={(e) => onSectionLayout('lifecycle', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.lifecycle }]}>
            <SectionTitle text="Lifecycle" />
            <InfoRow icon="sync-outline" text={plant.lifecycle === 'perennial' ? 'Perennial' : plant.lifecycle === 'annual' ? 'Annual' : plant.lifecycle || 'Unknown'} sub={plant.lifecycle_years ? (plant.lifecycle === 'perennial' ? `Lives ${plant.lifecycle_years} years` : `${plant.lifecycle_years}`) : (plant.lifecycle === 'perennial' ? 'Lives for multiple years' : 'One growing season')} />
            <InfoRow icon="leaf-outline" text={plant.lifecycle === 'perennial' ? 'Evergreen' : 'Seasonal'} sub="Foliage type" />
          </View>

          {/* ── 15. Used for ── */}
          <View onLayout={(e) => onSectionLayout('used_for', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.used_for }]}>
            <SectionTitle text="Used for" />
            <View style={styles.chipRow}>
              {plant.used_for.length > 0 ? (
                plant.used_for.map((tag) => (
                  <View key={tag} style={tag === 'Edible' || tag === 'Edible greens' || tag === 'Fruiting' ? [styles.chip, styles.chipGreen] : styles.chip}>
                    <Text style={tag === 'Edible' || tag === 'Edible greens' || tag === 'Fruiting' ? styles.chipTextGreen : styles.chipText}>{tag}</Text>
                  </View>
                ))
              ) : (
                <>
                  {plant.plant_type === 'decorative' && <View style={styles.chip}><Text style={styles.chipText}>Decorative</Text></View>}
                  {plant.plant_type === 'greens' && <View style={[styles.chip, styles.chipGreen]}><Text style={styles.chipTextGreen}>Edible greens</Text></View>}
                  {plant.plant_type === 'fruiting' && <View style={[styles.chip, styles.chipGreen]}><Text style={styles.chipTextGreen}>Fruiting</Text></View>}
                </>
              )}
            </View>
            {plant.edible_parts ? (
              <InfoRow icon="nutrition-outline" text={plant.edible_parts} sub="Edible parts" iconColor={Colors.success} />
            ) : null}
            <TouchableOpacity onPress={() => setShowUsedForGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Learn more</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 16. Taxonomy ── */}
          <View onLayout={(e) => onSectionLayout('taxonomy', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.taxonomy }]}>
            <SectionTitle text="Taxonomy" />
            <InfoRow icon="document-text-outline" text={plant.scientific} sub={[plant.genus, plant.family, plant.order].filter(Boolean).join(' · ')} />
            {plant.origin ? <InfoRow icon="earth-outline" text={plant.origin} sub="Origin" /> : null}
          </View>

          {/* ═══ GROUP: Companions ═══ */}

          {/* ── 17. Companions ── */}
          <View onLayout={(e) => onSectionLayout('companions', e)} style={[styles.sectionCard, styles.sectionCardAccent, { borderLeftColor: SECTION_ACCENT.companions }]}>
            <SectionTitle text="Companions" />
            {plant.good_companions.length > 0 && (
              <>
                <Text style={[styles.bodyText, { fontWeight: '600', marginBottom: Spacing.xs }]}>Good neighbors</Text>
                <View style={styles.chipRow}>
                  {plant.good_companions.map((c) => (
                    <View key={c} style={[styles.chip, styles.chipGreen]}><Text style={styles.chipTextGreen}>{c}</Text></View>
                  ))}
                </View>
              </>
            )}
            {plant.bad_companions.length > 0 && (
              <>
                <Text style={[styles.bodyText, { fontWeight: '600', marginBottom: Spacing.xs }]}>Keep apart</Text>
                <View style={styles.chipRow}>
                  {plant.bad_companions.map((c) => (
                    <View key={c} style={[styles.chip, { backgroundColor: '#FEE2E2' }]}><Text style={[styles.chipText, { color: Colors.error }]}>{c}</Text></View>
                  ))}
                </View>
              </>
            )}
            {(plant.good_companions.length > 0 || plant.bad_companions.length > 0) && (
              <TouchableOpacity onPress={() => setShowCompanionGuide(true)} style={styles.guideBtn}>
                <Text style={styles.guideBtnText}>Why these combinations?</Text>
                <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
              </TouchableOpacity>
            )}
          </View>

        </View>
      </ScrollView>

      {/* ═══ ADD TO MY PLANTS (floating button, only when not in collection) ═══ */}
      {!plant.isInCollection && (
        <View style={styles.addToCollectionBar}>
          <TouchableOpacity
            onPress={handleAddToCollection}
            style={styles.addToCollectionBtn}
            disabled={saveMutation.isPending}
            activeOpacity={0.8}
          >
            <Ionicons name="add-circle-outline" size={20} color="#fff" />
            <Text style={styles.addToCollectionText}>
              {saveMutation.isPending ? 'Saving...' : 'Add to My Plants'}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ═══ WATERING GUIDE MODAL ═══ */}
      <Modal visible={showWateringGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Watering guide</Text>
            <TouchableOpacity onPress={() => setShowWateringGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.modalPlantName}>{title}</Text>

            <Text style={styles.guideSectionTitle}>Watering frequency</Text>
            <WateringChart baseDays={baseDays} currentMonth={monthIndex} latitude={locationData.latitude || null} />

            <Text style={styles.guideSectionTitle}>How to water {title}</Text>
            <Text style={styles.bodyText}>{plant.watering_method || care.watering}</Text>

            {plant.watering_avoid ? (
              <>
                <Text style={styles.guideSectionTitle}>What to avoid</Text>
                <InfoBox text={plant.watering_avoid} variant="warning" />
              </>
            ) : null}

            <Text style={styles.guideSectionTitle}>Drainage</Text>
            <InfoBox text="Make sure your pot has drainage holes at the bottom. Without drainage, water collects and roots rot. If your pot has no holes, use it as a cachepot — place a smaller pot with holes inside." variant="info" />

            <WateringMethodsAccordion recommendedMethod={plant.watering_method} />
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ LIGHT GUIDE MODAL ═══ */}
      <Modal visible={showLightGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Light guide</Text>
            <TouchableOpacity onPress={() => setShowLightGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>How to light {title}</Text>
            <Text style={styles.bodyText}>{care.light.includes('Full') || care.light.includes('Bright')
              ? `South-facing window, 6+ hours direct sun.`
              : care.light.includes('indirect')
              ? `East or west window. No direct sun.`
              : `North-facing window or away from direct light.`
            }</Text>

            <LightLevelsAccordion recommendedLight={care.light} alsoSuitable={care.light_also_ok} />

            <Text style={styles.guideSectionTitle}>Warnings</Text>
            {care.light.includes('Full') || care.light.includes('Bright') ? (
              <>
                <InfoBox text={`Without enough light, ${title} will stretch, lose color, and weaken.`} variant="warning" />
                <InfoBox text={`In northern regions Oct–Mar, ${title} may need a grow light (full-spectrum LED, 12–14h daily).`} variant="warning" />
              </>
            ) : care.light.includes('indirect') ? (
              <InfoBox text={`Direct sun burns the leaves of ${title}. Keep away from unfiltered south-facing windows.`} variant="warning" />
            ) : (
              <InfoBox text={`${title} tolerates low light, but growth will slow significantly in very dark spots.`} variant="info" />
            )}

            <Text style={styles.guideSectionTitle}>Signs of incorrect lighting</Text>
            <Text style={[styles.bodyText, { fontWeight: '600', marginTop: Spacing.sm }]}>Not enough light</Text>
            <Text style={styles.bodyText}>{'• Leaves turn yellow and fall off\n• New leaves smaller than older ones\n• Plant stretches towards light\n• Slow, weak growth\n• Leaves far apart on stem'}</Text>
            <Text style={[styles.bodyText, { fontWeight: '600', marginTop: Spacing.sm }]}>Too much light</Text>
            <Text style={styles.bodyText}>{'• Leaves drooping\n• Leaf edges dry up\n• Color fading\n• Flowers shrivel and die'}</Text>

            {care.ppfd_min > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Light intensity</Text>
                <InfoRow icon="sunny-outline" text={`${care.ppfd_min}–${care.ppfd_max} PPFD`} sub="Photosynthetic Photon Flux Density" />
                <InfoRow icon="time-outline" text={`${care.dli_min}–${care.dli_max} DLI`} sub="Daily Light Integral" />
                <InfoBox text="PPFD measures how much usable light reaches the plant per second. DLI is the total light received per day. These values help when choosing a grow light — match its output to the plant's needs." variant="info" />
              </>
            )}
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ HUMIDITY GUIDE MODAL ═══ */}
      <Modal visible={showHumidityGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Humidity guide</Text>
            <TouchableOpacity onPress={() => setShowHumidityGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Humidity for {title}</Text>
            <InfoRow icon="cloud-outline" text={care.humidity} sub="Recommended level" />
            {care.humidity_action ? (
              <Text style={styles.bodyText}>{care.humidity_action}</Text>
            ) : null}

            <Text style={styles.guideSectionTitle}>Warnings</Text>
            {care.humidity.toLowerCase().includes('high') || care.humidity.toLowerCase().includes('60') || care.humidity.toLowerCase().includes('70') || care.humidity.toLowerCase().includes('80') ? (
              <>
                <InfoBox text={`${title} needs high humidity. In dry apartments (especially with central heating in winter), leaf tips will turn brown and crispy.`} variant="warning" />
                <InfoBox text="Low humidity also attracts spider mites — the #1 indoor pest for tropical plants." variant="warning" />
              </>
            ) : care.humidity.toLowerCase().includes('low') || care.humidity.toLowerCase().includes('dry') ? (
              <>
                <InfoBox text={`${title} prefers dry air. High humidity causes fungal issues and root rot. Do not mist this plant.`} variant="warning" />
                <InfoBox text="Avoid placing in bathrooms or near humidifiers." variant="warning" />
              </>
            ) : (
              <InfoBox text={`${title} does fine in average room humidity (40–60%). No special measures needed in most homes.`} variant="info" />
            )}

            <HumidityMethodsAccordion />
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ TEMPERATURE GUIDE MODAL ═══ */}
      <Modal visible={showTempGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Temperature guide</Text>
            <TouchableOpacity onPress={() => setShowTempGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Indoor temperature for {title}</Text>
            <Text style={styles.bodyText}>
              {plant.preset === 'Tropical'
                ? `${title} is a tropical plant. It thrives at typical room temperature (18–27°C) all year. No special temperature adjustments needed indoors.`
                : plant.preset === 'Succulents'
                ? `${title} comes from an arid climate. Normal room temperature works year-round. A slight winter cool-down (10–15°C) can encourage blooming, but is not required to keep the plant alive.`
                : plant.preset === 'Herbs'
                ? `${title} prefers moderate temperatures. Some herbs from temperate climates benefit from cooler winters. Avoid hot radiators and cold drafts equally.`
                : `${title} is a temperate plant. It may need a cooler winter period (dormancy) to stay healthy long-term. Without winter cool-down, it can weaken and become susceptible to pests.`
              }
            </Text>

            <Text style={[styles.bodyText, { fontWeight: '600', marginTop: Spacing.md }]}>Summer (optimal)</Text>
            <TempRangeBar optLow={plant.temp_opt_low_c} optHigh={plant.temp_opt_high_c} color="#EF4444" />

            {plant.temp_winter_low_c > 0 && (
              <>
                <Text style={[styles.bodyText, { fontWeight: '600', marginTop: Spacing.md }]}>Winter (optimal)</Text>
                <TempRangeBar optLow={plant.temp_winter_low_c} optHigh={plant.temp_winter_high_c} color="#6B7280" />
              </>
            )}

            {plant.temp_warning ? (
              <>
                <Text style={styles.guideSectionTitle}>Warnings</Text>
                <InfoBox text={plant.temp_warning} variant="warning" />
              </>
            ) : null}

            <Text style={styles.guideSectionTitle}>Current conditions</Text>
            {locationData.isLoading ? (
              <InfoBox text="Getting your location..." variant="info" />
            ) : locationData.error ? (
              <InfoBox text="Enable location services to see current outdoor temperature in your area and whether it's safe to place this plant outside." variant="info" />
            ) : (
              <InfoBox
                text={`It's ${Math.round(locationData.currentTemp)}°C outside right now. ${
                  locationData.currentTemp >= plant.temp_opt_low_c && locationData.currentTemp <= plant.temp_opt_high_c
                    ? 'This is within the optimal range for this plant.'
                    : locationData.currentTemp >= plant.temp_min_c
                      ? 'The plant can survive at this temperature, but it\'s outside the optimal range.'
                      : 'Too cold — keep this plant indoors.'
                }`}
                variant={
                  locationData.currentTemp >= plant.temp_opt_low_c && locationData.currentTemp <= plant.temp_opt_high_c
                    ? 'success'
                    : locationData.currentTemp >= plant.temp_min_c
                      ? 'warning'
                      : 'warning'
                }
              />
            )}

            <Text style={styles.guideSectionTitle}>Common indoor problems</Text>
            <Text style={styles.bodyText}>{'• Cold drafts from windows — move plant away from drafty spots in winter\n• Hot radiators — dry out the air and overheat roots on the side closest to heat\n• Air conditioning — sudden cold blasts stress tropical plants\n• Temperature swings day/night — most plants prefer stable temperature'}</Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ OUTDOOR GUIDE MODAL ═══ */}
      <Modal visible={showOutdoorGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Outdoor guide</Text>
            <TouchableOpacity onPress={() => setShowOutdoorGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>{title} outdoors</Text>
            <Text style={styles.bodyText}>
              {plant.temp_min_c <= 0
                ? `${title} tolerates light frost and can stay outdoors longer than most houseplants. Still, potted plants are more vulnerable than those in the ground.`
                : plant.temp_min_c <= 5
                ? `${title} can go outdoors in warm months but must come inside before temperatures drop below ${plant.temp_min_c}°C.`
                : `${title} is sensitive to cold. Only put outdoors when nighttime temperatures are consistently above ${plant.temp_min_c + 5}°C.`
              }
            </Text>

            <Text style={styles.guideSectionTitle}>Indoor months</Text>
            <MonthBar activeMonths={['January','February','March','April','May','June','July','August','September','October','November','December']} label="" color="#22C55E" />

            <Text style={styles.guideSectionTitle}>Outdoor months (potted)</Text>
            {locationData.isLoading ? (
              <InfoRow icon="location-outline" text="Getting your location..." sub="" />
            ) : locationData.error ? (
              <>
                <Text style={styles.bodyText}>Enable location to see which months are safe for outdoor placement in your area.</Text>
              </>
            ) : (
              <>
                <Text style={styles.bodyText}>These are the months {title} can be outdoor in your area. The rest of the year the temperature is too cold.</Text>
                <MonthBar activeMonths={outdoorMonths?.potted ?? []} label="" color="#22C55E" />

                <Text style={styles.guideSectionTitle}>Outdoor months (in ground)</Text>
                <MonthBar activeMonths={outdoorMonths?.inGround ?? []} label="" color="#16A34A" />
              </>
            )}

            <Text style={styles.guideSectionTitle}>Frost tolerance</Text>
            <InfoRow icon="thermometer-outline" text={`${plant.temp_min_c}°C (${Math.round(plant.temp_min_c * 9 / 5 + 32)}°F)`} sub="Lowest temp to survive when potted" />
            <InfoBox text="This is the temperature the plant can endure — not the temperature it prefers. At this point the plant suffers: leaves may drop, growth stops, scarring occurs. It should survive and recover once moved to warmth." variant="info" />

            <Text style={styles.guideSectionTitle}>Potted vs in ground</Text>
            <Text style={styles.bodyText}>
              A plant in the ground has soil insulation protecting its roots. A potted plant has exposed sides — the pot freezes through much faster. This means potted plants need to come inside earlier in autumn and go out later in spring.
            </Text>

            <Text style={styles.guideSectionTitle}>Frost tolerance zones</Text>
            <Text style={styles.bodyText}>
              A frost tolerance zone is based on the average lowest winter temperature in your area. It determines which plants can survive outdoors year-round.
            </Text>
            <Text style={styles.bodyText}>
              Zones range from 1a (coldest, below -51°C) to 13b (warmest, above 21°C). Each zone spans about 5°C.
            </Text>
            <Text style={styles.bodyText}>
              Important: these zones assume the plant is in the ground. Potted plants are 1–2 zones less hardy because roots are exposed to cold from all sides.
            </Text>
            {locationData.error ? (
              <InfoBox text="Enable location services and we will determine your frost tolerance zone automatically." variant="info" />
            ) : !locationData.isLoading ? (
              <InfoBox text={`Your zone: ${locationData.hardinessZone}. Current outdoor temperature: ${Math.round(locationData.currentTemp)}°C.`} variant="success" />
            ) : null}
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ TOXICITY GUIDE MODAL ═══ */}
      <Modal visible={showToxicityGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Toxicity details</Text>
            <TouchableOpacity onPress={() => setShowToxicityGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Toxicity of {title}</Text>

            <InfoRow icon="alert-circle" text={plant.toxicity_severity ? `${plant.toxicity_severity} toxicity` : 'Toxic'} iconColor={Colors.error} />

            <View style={styles.chipRow}>
              {plant.poisonous_to_humans && <View style={styles.chip}><Text style={styles.chipText}>Humans</Text></View>}
              {plant.poisonous_to_pets && <View style={styles.chip}><Text style={styles.chipText}>Cats</Text></View>}
              {plant.poisonous_to_pets && <View style={styles.chip}><Text style={styles.chipText}>Dogs</Text></View>}
            </View>

            {plant.toxic_parts ? (
              <>
                <Text style={styles.guideSectionTitle}>Toxic parts</Text>
                <Text style={styles.bodyText}>{plant.toxic_parts}</Text>
              </>
            ) : null}

            {plant.edible && plant.edible_parts ? (
              <>
                <Text style={styles.guideSectionTitle}>Edible parts</Text>
                <InfoRow icon="nutrition-outline" text={plant.edible_parts} iconColor={Colors.success} />
              </>
            ) : null}

            {plant.toxicity_symptoms ? (
              <>
                <Text style={styles.guideSectionTitle}>Symptoms by exposure</Text>
                {plant.toxicity_symptoms.split('\n').filter(Boolean).map((line, i) => {
                  const [cat, ...rest] = line.split(': ');
                  return (
                    <View key={i} style={{ marginBottom: Spacing.sm }}>
                      <Text style={[styles.bodyText, { fontWeight: '600' }]}>{cat}</Text>
                      <Text style={styles.bodyText}>{rest.join(': ')}</Text>
                    </View>
                  );
                })}
              </>
            ) : null}

            {plant.toxicity_first_aid ? (
              <>
                <Text style={styles.guideSectionTitle}>What to do</Text>
                {plant.toxicity_first_aid.split('\n').filter(Boolean).map((line, i) => {
                  const [cat, ...rest] = line.split(': ');
                  return (
                    <View key={i} style={{ marginBottom: Spacing.sm }}>
                      <Text style={[styles.bodyText, { fontWeight: '600' }]}>{cat}</Text>
                      <Text style={styles.bodyText}>{rest.join(': ')}</Text>
                    </View>
                  );
                })}
              </>
            ) : null}

            {plant.toxicity_note ? (
              <InfoBox text={plant.toxicity_note} variant="warning" />
            ) : null}

            <Text style={styles.guideSectionTitle}>Disclaimer</Text>
            <InfoBox text="Toxicity information is compiled from multiple botanical sources and may not be exhaustive. Individual reactions vary — allergies and sensitivities are not covered here. If you or your pet ingested any plant material and feel unwell, contact a medical professional or poison control center immediately. This is not medical advice." variant="info" />
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ USED FOR GUIDE MODAL ═══ */}
      <Modal visible={showUsedForGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>About {title}</Text>
            <TouchableOpacity onPress={() => setShowUsedForGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>What is {title} used for</Text>
            <View style={styles.chipRow}>
              {plant.used_for.map((tag) => (
                <View key={tag} style={tag === 'Edible' || tag === 'Edible greens' || tag === 'Fruiting' ? [styles.chip, styles.chipGreen] : styles.chip}>
                  <Text style={tag === 'Edible' || tag === 'Edible greens' || tag === 'Fruiting' ? styles.chipTextGreen : styles.chipText}>{tag}</Text>
                </View>
              ))}
            </View>

            {plant.used_for_details ? (
              <Text style={styles.bodyText}>{plant.used_for_details}</Text>
            ) : null}

            {plant.edible_parts ? (
              <>
                <Text style={styles.guideSectionTitle}>Edible parts</Text>
                <InfoRow icon="nutrition-outline" text={plant.edible_parts} iconColor={Colors.success} />
              </>
            ) : null}

            {plant.harvest_info ? (
              <>
                <Text style={styles.guideSectionTitle}>Harvest</Text>
                <Text style={styles.bodyText}>{plant.harvest_info}</Text>
              </>
            ) : null}

            {plant.used_for.includes('Air purifier') && (
              <>
                <Text style={styles.guideSectionTitle}>Air purification</Text>
                <InfoBox text="According to the NASA Clean Air Study, certain houseplants can remove common indoor pollutants like formaldehyde, benzene, and trichloroethylene. For noticeable effect, aim for 2-3 large plants per average room." variant="info" />
              </>
            )}

            {plant.used_for.includes('Attracts pollinators') && (
              <>
                <Text style={styles.guideSectionTitle}>Pollinators</Text>
                <InfoBox text="This plant attracts bees and butterflies. Great for balconies and gardens where you want to support local pollinator populations." variant="info" />
              </>
            )}
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ REPOTTING GUIDE MODAL ═══ */}
      <Modal visible={showSoilGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Repotting guide</Text>
            <TouchableOpacity onPress={() => setShowSoilGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Repotting {title}</Text>
            <InfoRow icon="swap-vertical-outline" text={care.repot} sub="Frequency" />
            {plant.repot_signs ? (
              <>
                <Text style={[styles.bodyText, { fontWeight: '600' }]}>Signs it's time:</Text>
                <Text style={styles.bodyText}>{plant.repot_signs}</Text>
              </>
            ) : null}

            <Text style={styles.guideSectionTitle}>Pot</Text>
            {plant.pot_type ? (
              <InfoRow icon="cube-outline" text={plant.pot_type} />
            ) : null}
            {plant.pot_size_note ? (
              <Text style={styles.bodyText}>{plant.pot_size_note}</Text>
            ) : null}
            <InfoBox text="Always use a pot with drainage holes. No drainage = standing water = root rot. If you love a decorative pot without holes, use it as a cachepot — place a smaller pot with holes inside." variant="warning" />

            <RepottingAccordion />

            <Text style={styles.guideSectionTitle}>Soil for {title}</Text>
            <Text style={styles.bodyText}>{care.soil}</Text>

            {plant.soil_types.length > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Recommended soil types</Text>
                <View style={styles.chipRow}>
                  {plant.soil_types.map((t) => (
                    <View key={t} style={styles.chip}><Text style={styles.chipText}>{t}</Text></View>
                  ))}
                </View>
              </>
            )}

            {plant.soil_ph_min != null && plant.soil_ph_min > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Soil acidity (pH)</Text>
                <InfoRow icon="flask-outline" text={`pH ${plant.soil_ph_min} – ${plant.soil_ph_max}`} sub="Optimal range" />
                <InfoBox text="pH below 7 is acidic (peat, pine bark). pH above 7 is alkaline (limestone, chalk). Most houseplants prefer slightly acidic to neutral (5.5–7.0). Test with a simple pH kit from any garden store." variant="info" />
              </>
            )}

            <Text style={styles.guideSectionTitle}>Cleaning</Text>
            <Text style={styles.bodyText}>Wipe leaves with a damp cloth regularly. Dust blocks light absorption and slows photosynthesis. For fuzzy-leaved plants, use a soft brush instead.</Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ FERTILIZING GUIDE MODAL ═══ */}
      <Modal visible={showFertGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Fertilizing guide</Text>
            <TouchableOpacity onPress={() => setShowFertGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Fertilizing {title}</Text>
            <InfoRow icon="leaf-outline" text={care.fertilizer} sub={care.fertilizer_season} />

            {plant.fertilizer_types.length > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Recommended fertilizers</Text>
                <View style={styles.chipRow}>
                  {plant.fertilizer_types.map((t) => (
                    <View key={t} style={styles.chip}><Text style={styles.chipText}>{t}</Text></View>
                  ))}
                </View>
              </>
            )}

            {plant.fertilizer_npk ? (
              <>
                <Text style={styles.guideSectionTitle}>NPK ratio</Text>
                <InfoRow icon="flask-outline" text={plant.fertilizer_npk} sub="Nitrogen – Phosphorus – Potassium" />
                <InfoBox text="NPK is the three numbers on every fertilizer bottle. N (nitrogen) = leaf growth. P (phosphorus) = roots and flowers. K (potassium) = overall health and fruit. Match the ratio to what your plant needs most." variant="info" />
              </>
            ) : null}

            {plant.fertilizer_warning ? (
              <>
                <Text style={styles.guideSectionTitle}>Warnings</Text>
                <InfoBox text={plant.fertilizer_warning} variant="warning" />
              </>
            ) : null}

            <Text style={styles.guideSectionTitle}>When NOT to fertilize</Text>
            <Text style={styles.bodyText}>{'• Winter — plant is dormant, nutrients accumulate and burn roots\n• Right after repotting — fresh soil has nutrients for 2-4 weeks\n• Sick or stressed plant — fix the problem first, then feed\n• Dry soil — always water before fertilizing to avoid root burn'}</Text>

            <Text style={styles.guideSectionTitle}>Signs of over-fertilizing</Text>
            <Text style={styles.bodyText}>{'• White crust on soil surface (salt buildup)\n• Brown, crispy leaf tips and edges\n• Wilting despite moist soil\n• Slow growth or dropping leaves'}</Text>

            <Text style={styles.guideSectionTitle}>Signs of under-fertilizing</Text>
            <Text style={styles.bodyText}>{'• Pale or yellow leaves (especially older ones)\n• Slow or stunted growth\n• Small new leaves\n• No flowers on a flowering plant'}</Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ SIZE GUIDE MODAL ═══ */}
      <Modal visible={showSizeGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Growth & dimensions</Text>
            <TouchableOpacity onPress={() => setShowSizeGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>{title} dimensions</Text>
            <InfoRow icon="arrow-up-outline" text={plant.height_max_cm > 0 ? `${plant.height_min_cm || '?'} – ${plant.height_max_cm} cm` : 'Not specified'} sub="Height (mature plant, in ground)" />
            {plant.spread_max_cm > 0 && (
              <InfoRow icon="swap-horizontal-outline" text={`Up to ${plant.spread_max_cm} cm`} sub="Crown diameter" />
            )}
            <InfoRow icon="trending-up-outline" text={plant.growth_rate || 'Not specified'} sub="Growth rate" />
            <InfoBox text="These dimensions are for a full grown plant in ideal conditions (in ground, outdoors). Indoor plants in pots will be significantly smaller." variant="info" />

            <Text style={styles.guideSectionTitle}>In a pot</Text>
            {plant.height_indoor_max_cm > 0 && (
              <InfoRow icon="cube-outline" text={`Up to ${plant.height_indoor_max_cm} cm`} sub="Realistic height in a pot (plant only, without pot)" />
            )}
            <Text style={styles.bodyText}>
              {`A pot limits root space, which limits the plant's overall size. This is the main reason indoor plants stay smaller than outdoor ones. The bigger the pot — the bigger the plant can grow. But too big a pot holds excess moisture and causes root rot.`}
            </Text>

            <Text style={styles.guideSectionTitle}>Recommended pot size</Text>
            <Text style={styles.bodyText}>
              {plant.preset === 'Succulents'
                ? 'Start with a pot 2-3 cm wider than the root ball. Succulents prefer snug pots — too much soil stays wet and causes rot.'
                : plant.preset === 'Tropical'
                ? 'Start with a pot 3-5 cm wider than the root ball. Tropical plants grow faster and need room, but not too much at once.'
                : plant.preset === 'Herbs'
                ? 'For herbs, a pot 15-20 cm in diameter works for most. Deeper pots for plants with long roots (rosemary), shallower for bushy herbs (basil).'
                : 'Start with a pot 2-4 cm wider than the root ball. Upsize gradually — one size at a time.'
              }
            </Text>

            <Text style={styles.guideSectionTitle}>If your plant is not growing</Text>
            <Text style={styles.bodyText}>{'• Not enough light — the #1 reason for stunted growth indoors\n• Pot too small — roots have nowhere to go\n• Wrong soil — compacted soil chokes roots\n• Not enough nutrients — time to fertilize\n• Dormancy — normal in winter, growth resumes in spring\n• Root rot — check roots if plant is wilting despite watering'}</Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ PROPAGATION GUIDE MODAL ═══ */}
      <Modal visible={showPropGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Germination & Propagation</Text>
            <TouchableOpacity onPress={() => setShowPropGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>How to propagate {title}</Text>

            {plant.propagation_methods.length > 0 && (
              <>
                <Text style={[styles.bodyText, { fontWeight: '600' }]}>Methods</Text>
                <View style={styles.chipRow}>
                  {plant.propagation_methods.map((m) => (
                    <View key={m} style={styles.chip}><Text style={styles.chipText}>{m}</Text></View>
                  ))}
                </View>
              </>
            )}

            {plant.propagation_detail ? (
              <Text style={styles.bodyText}>{plant.propagation_detail}</Text>
            ) : null}

            {plant.germination_days > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>From seed (germination)</Text>
                <InfoRow icon="time-outline" text={`~${plant.germination_days} days`} sub="Time to germinate" />
                {plant.germination_temp_c ? (
                  <InfoRow icon="thermometer-outline" text={plant.germination_temp_c} sub="Optimal temperature" />
                ) : null}
              </>
            )}

            <Text style={styles.guideSectionTitle}>General tips</Text>
            <Text style={styles.bodyText}>{'• Always use clean, sharp tools when taking cuttings\n• Spring and early summer are the best time to propagate\n• Keep soil moist but not soggy for new cuttings\n• Bright indirect light — no direct sun on fresh cuttings\n• Be patient — rooting can take weeks'}</Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ HARVEST GUIDE MODAL ═══ */}
      <Modal visible={showHarvestGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Harvesting {title}</Text>
            <TouchableOpacity onPress={() => setShowHarvestGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            {plant.edible_parts ? (
              <>
                <Text style={styles.guideSectionTitle}>Edible parts</Text>
                <InfoRow icon="nutrition-outline" text={plant.edible_parts} iconColor={Colors.success} />
              </>
            ) : null}

            {plant.harvest_info ? (
              <>
                <Text style={styles.guideSectionTitle}>How to harvest</Text>
                <Text style={styles.bodyText}>{plant.harvest_info}</Text>
              </>
            ) : null}

            {plant.plant_type === 'fruiting' ? (
              <>
                <Text style={styles.guideSectionTitle}>Fruit stages</Text>
                <Text style={styles.bodyText}>{'• Flowering — pollination needed (shake stems indoors)\n• Fruit set — small green fruits appear after pollination\n• Growing — fruit enlarges, needs consistent watering\n• Ripening — color changes, fruit softens slightly\n• Harvest — pick when fully colored and gives slightly to gentle pressure'}</Text>
                <InfoBox text="Do not pick too early. Unripe fruit lacks flavor and may contain higher levels of toxins (e.g. solanine in green tomatoes)." variant="warning" />
              </>
            ) : plant.plant_type === 'greens' ? (
              <>
                <Text style={styles.guideSectionTitle}>Harvesting tips</Text>
                <Text style={styles.bodyText}>{'• Always harvest from the top — cut above a leaf pair\n• Never take more than one-third of the plant at once\n• Regular harvesting stimulates bushier growth\n• Harvest in the morning — oils and flavor are strongest\n• Pinch off flower buds immediately — flowering ends leaf production'}</Text>
              </>
            ) : null}

            {isToxic && plant.edible ? (
              <InfoBox text={`Some parts of ${title} are toxic while others are edible. Always know which parts are safe before consuming.`} variant="warning" />
            ) : null}
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ COMPANION GUIDE MODAL ═══ */}
      <Modal visible={showCompanionGuide} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Plant companions</Text>
            <TouchableOpacity onPress={() => setShowCompanionGuide(false)} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalScroll}>
            <Text style={styles.guideSectionTitle}>Why companion planting matters</Text>
            <Text style={styles.bodyText}>
              Some plants grow better together — they share nutrients, repel each other's pests, or create beneficial shade. Others compete for the same resources or release chemicals that inhibit their neighbors.
            </Text>

            {plant.good_companions.length > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Good neighbors for {title}</Text>
                <View style={styles.chipRow}>
                  {plant.good_companions.map((c) => (
                    <View key={c} style={[styles.chip, styles.chipGreen]}><Text style={styles.chipTextGreen}>{c}</Text></View>
                  ))}
                </View>
                {plant.companion_note ? (
                  <Text style={styles.bodyText}>{plant.companion_note}</Text>
                ) : (
                  <Text style={styles.bodyText}>
                    These plants share similar soil and watering requirements, making them ideal pot or garden neighbors. They can be planted in the same bed or grouped together indoors.
                  </Text>
                )}
              </>
            )}

            {plant.bad_companions.length > 0 && (
              <>
                <Text style={styles.guideSectionTitle}>Keep apart from {title}</Text>
                <View style={styles.chipRow}>
                  {plant.bad_companions.map((c) => (
                    <View key={c} style={[styles.chip, { backgroundColor: '#FEE2E2' }]}><Text style={[styles.chipText, { color: Colors.error }]}>{c}</Text></View>
                  ))}
                </View>
                <Text style={styles.bodyText}>
                  These plants compete for resources, have incompatible soil/water needs, or may inhibit each other's growth. Keep them in separate containers or different areas.
                </Text>
              </>
            )}

            <Text style={styles.guideSectionTitle}>Soil sharing tips</Text>
            <Text style={styles.bodyText}>
              {'• Plants with similar pH and drainage needs can share soil\n• After harvesting herbs, their soil is often nutrient-depleted — refresh before reusing\n• Rotate crops in the same pot: follow a heavy feeder (tomato) with a light feeder (herbs)\n• Never reuse soil from a diseased plant'}
            </Text>

            <Text style={styles.guideSectionTitle}>Grouping indoors</Text>
            <Text style={styles.bodyText}>
              {'• Group plants with similar humidity needs — they create a shared microclimate\n• Tall plants can provide shade for low-light neighbors\n• Keep pest-prone plants away from healthy ones\n• Fragrant herbs (rosemary, lavender) can deter pests from nearby plants'}
            </Text>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ LIGHT METER ═══ */}
      <LightMeterModal
        visible={showLightMeter}
        onClose={() => setShowLightMeter(false)}
        plantName={title}
        ppfdMin={care.ppfd_min}
        ppfdMax={care.ppfd_max}
        dliMin={care.dli_min}
        dliMax={care.dli_max}
      />
    </>
  );
}

// ─── Repotting accordion ─────────────────────────────────────────────

function RepottingAccordion() {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={{ marginTop: Spacing.sm }}>
      <View style={styles.accordionItem}>
        <TouchableOpacity
          onPress={() => setExpanded(!expanded)}
          style={styles.accordionHeader}
        >
          <Text style={styles.accordionTitle}>How to repot (step by step)</Text>
          <Ionicons name={expanded ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.textSecondary} />
        </TouchableOpacity>
        {expanded && (
          <View style={styles.accordionBody}>
            {[
              'Water the plant a day before repotting — moist soil holds together better.',
              'Choose a new pot 2-3 cm larger in diameter. Too big = too much wet soil = root rot.',
              'Place drainage material at the bottom (clay shards, pebbles, or LECA).',
              'Fill the bottom with fresh soil mix appropriate for your plant.',
              'Gently remove the plant from the old pot. Loosen the root ball with your fingers.',
              'Trim any dead, mushy, or circling roots with clean scissors.',
              'Place the plant in the new pot at the same depth as before.',
              'Fill around the roots with fresh soil, pressing gently to remove air pockets.',
              'Water thoroughly and let drain. Do not fertilize for 2-4 weeks — fresh soil has nutrients.',
            ].map((step, i) => (
              <View key={i} style={styles.stepRow}>
                <Text style={styles.stepNumber}>{i + 1}.</Text>
                <Text style={styles.stepText}>{step}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}

// ─── Temperature range bar ───────────────────────────────────────────

function TempRangeBar({ optLow, optHigh, color, label }: {
  optLow: number; optHigh: number; color?: string; label?: string;
}) {
  // Fixed scale 0-30°C like Planta
  const scaleMin = 0;
  const scaleMax = 30;
  const range = scaleMax - scaleMin;
  const leftPct = Math.max(0, ((optLow - scaleMin) / range) * 100);
  const widthPct = Math.min(100 - leftPct, ((optHigh - optLow) / range) * 100);
  const barColor = color ?? Colors.success;

  return (
    <View style={styles.tempBarContainer}>
      <View style={styles.tempBarTrack}>
        <View style={[styles.tempBarOptimal, { left: `${leftPct}%`, width: `${widthPct}%`, backgroundColor: barColor }]}>
          <Text style={styles.tempBarInnerLabel}>{label ?? `${optLow}°C – ${optHigh}°C`}</Text>
        </View>
      </View>
      <View style={styles.tempBarLabels}>
        <Text style={styles.tempBarLabel}>{scaleMin}°C</Text>
        <Text style={styles.tempBarLabel}>15°C</Text>
        <Text style={styles.tempBarLabel}>{scaleMax}°C</Text>
      </View>
    </View>
  );
}


// ─── Light levels accordion ──────────────────────────────────────────

const LIGHT_LEVELS = [
  {
    title: 'Full sun',
    description: 'At least 6 hours of direct sunlight daily. South-facing window with no barriers (curtains, buildings, trees). Plants: Aloes, Succulents, Cacti, Herbs.',
    also: 'Bright light, direct light',
  },
  {
    title: 'Part sun, part shade',
    description: '2–4 hours of direct light per day. West or east-facing window, or further from a sunny window. Plants: Monstera, Orchids, Calathea.',
    also: 'Dappled sunlight, medium light, filtered sunlight, bright indirect light',
  },
  {
    title: 'Shade',
    description: 'No direct sunlight. North-facing window or far from windows. Plants: ZZ-plant, Pothos, Snake Plant.',
    also: 'Low light',
  },
];


function LightLevelsAccordion({ recommendedLight, alsoSuitable }: { recommendedLight?: string; alsoSuitable?: string }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const matchesLight = (title: string, text: string): boolean => {
    const lower = text.toLowerCase();
    if (title === 'Full sun' && (lower.includes('full') || lower.includes('direct'))) return true;
    if (title === 'Part sun, part shade' && (lower.includes('indirect') || lower.includes('part'))) return true;
    if (title === 'Shade' && (lower.includes('low') || lower.includes('shade'))) return true;
    return false;
  };

  const getLabel = (title: string): string => {
    if (recommendedLight && matchesLight(title, recommendedLight)) return ' (Recommended)';
    if (alsoSuitable && matchesLight(title, alsoSuitable)) return ' (Also suitable)';
    return '';
  };

  return (
    <View style={{ marginTop: Spacing.lg }}>
      <Text style={styles.guideSectionTitle}>Light levels</Text>
      {LIGHT_LEVELS.map((level) => {
        const label = getLabel(level.title);
        return (
          <View key={level.title} style={styles.accordionItem}>
            <TouchableOpacity
              onPress={() => setExpanded(expanded === level.title ? null : level.title)}
              style={styles.accordionHeader}
            >
              <Text style={styles.accordionTitle}>{level.title}{label}</Text>
              <Ionicons name={expanded === level.title ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.textSecondary} />
            </TouchableOpacity>
            {expanded === level.title && (
              <View style={styles.accordionBody}>
                <Text style={styles.bodyText}>{level.description}</Text>
                <Text style={[styles.bodyText, { fontStyle: 'italic', color: Colors.textSecondary }]}>Also described as: {level.also}</Text>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

// ─── Humidity methods accordion ──────────────────────────────────────

const HUMIDITY_METHODS = [
  {
    title: 'How to increase humidity',
    steps: [
      'Group plants together — they create a microclimate with higher humidity.',
      'Place a tray with pebbles and water under the pot. Water evaporates and humidifies the air around the plant.',
      'Use a room humidifier nearby, especially in winter with central heating.',
      'Move the plant to a naturally humid room (kitchen, bathroom with window).',
    ],
  },
  {
    title: 'How to decrease humidity',
    steps: [
      'Improve air circulation — open windows, use a fan.',
      'Move the plant away from bathrooms and kitchens.',
      'Use a dehumidifier if the room is consistently above 70%.',
      'Avoid overwatering — wet soil adds moisture to the air.',
      'Use terracotta pots — they absorb excess moisture.',
    ],
  },
  {
    title: 'About misting',
    steps: [
      'Misting raises humidity for minutes, not hours. It helps tropical plants but is not a substitute for a humidifier.',
      'Never mist succulents, cacti, or plants with fuzzy leaves — water sits on leaves and causes rot or fungal spots.',
      'If you mist, do it in the morning so leaves dry before evening.',
    ],
  },
];

function HumidityMethodsAccordion() {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <View style={{ marginTop: Spacing.lg }}>
      <Text style={styles.guideSectionTitle}>Managing humidity</Text>
      {HUMIDITY_METHODS.map((method) => (
        <View key={method.title} style={styles.accordionItem}>
          <TouchableOpacity
            onPress={() => setExpanded(expanded === method.title ? null : method.title)}
            style={styles.accordionHeader}
          >
            <Text style={styles.accordionTitle}>{method.title}</Text>
            <Ionicons name={expanded === method.title ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.textSecondary} />
          </TouchableOpacity>
          {expanded === method.title && (
            <View style={styles.accordionBody}>
              {method.steps.map((step, i) => (
                <View key={i} style={styles.stepRow}>
                  <Text style={styles.stepNumber}>{i + 1}.</Text>
                  <Text style={styles.stepText}>{step}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      ))}
    </View>
  );
}

// ─── Watering frequency chart ────────────────────────────────────────

const MONTH_LABELS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

function WateringChart({ baseDays, currentMonth, latitude }: { baseDays: number; currentMonth: number; latitude: number | null }) {
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);

  const coeffs = getSeasonCoefficients(latitude);
  const daysPerMonth = coeffs.map((c) => Math.round(baseDays * c));
  const maxDays = Math.max(...daysPerMonth);

  const activeMonth = selectedMonth ?? currentMonth;
  const activeDays = daysPerMonth[activeMonth];
  const activeLabel = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][activeMonth];

  // Bar height: invert — more frequent (fewer days) = taller bar
  // So bar represents "water need", not "days between"
  const maxBarHeight = 80;

  return (
    <View>
      <Text style={styles.chartLabel}>
        {activeLabel}: every ~{activeDays} {activeDays === 1 ? 'day' : 'days'}
      </Text>
      <View style={styles.chartContainer}>
        {daysPerMonth.map((days, i) => {
          const barHeight = Math.max(8, maxBarHeight * (1 - (days - baseDays) / (maxDays - baseDays + 1)));
          const isCurrent = i === currentMonth;
          const isSelected = i === activeMonth;
          return (
            <TouchableOpacity
              key={i}
              onPress={() => setSelectedMonth(i === currentMonth ? null : i)}
              style={styles.chartBarCol}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.chartBar,
                  {
                    height: barHeight,
                    backgroundColor: isSelected ? Colors.primary : isCurrent ? Colors.moisture : '#D1D5DB',
                  },
                ]}
              />
              <Text style={[styles.chartMonthLabel, isCurrent && styles.chartMonthLabelActive]}>
                {MONTH_LABELS[i]}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

// ─── Watering methods accordion ──────────────────────────────────────

const WATERING_METHODS = [
  {
    title: 'Water over the soil',
    steps: [
      'Pour water over the soil using a watering can or place the pot directly under a tap.',
      'Continue adding water until it starts to run out from the drainage holes.',
      'If you have a tray under the pot, make sure you remove all collected water afterwards — never let your plant sit in water.',
      'If you watered under a tap, make sure water has stopped running out from the bottom before putting it back.',
    ],
    note: null,
  },
  {
    title: 'Bottom watering',
    steps: [
      'Fill the plant tray with water.',
      'Make sure the soil is in contact with the water on the tray.',
      'Wait for about 10 minutes.',
      'Feel the soil to see if it absorbed enough water — if moist throughout, remove excess water from the tray.',
      "If it's still dry — add more water to the tray.",
      'Wait 20 more minutes before removing the excess.',
    ],
    note: 'Bottom watering will not wash away salts and other minerals from the soil, so make sure to also give water over the soil every now and then.',
  },
  {
    title: 'Water bath',
    steps: [
      'Fill a bucket or any other vessel with lukewarm water.',
      'Lower the whole pot down in the water, stop where the stem of the plant starts. Make sure all of the soil is under water.',
      'The water will now start to bubble — wait until it stopped.',
      'Lift the pot up and let the excess drain off.',
      'Put your plant back in the cachepot or on the tray.',
      "After 1 hour, check that your plant isn't standing in water — if it is, it might get overwatered and rot.",
    ],
    note: null,
  },
];

function WateringMethodsAccordion({ recommendedMethod }: { recommendedMethod?: string }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const isRecommended = (title: string): boolean => {
    if (!recommendedMethod) return false;
    const lower = recommendedMethod.toLowerCase();
    if (title === 'Water over the soil' && (lower.includes('over') || lower.includes('base') || lower.includes('pour') || lower.includes('watering can'))) return true;
    if (title === 'Bottom watering' && (lower.includes('bottom') || lower.includes('tray'))) return true;
    if (title === 'Water bath' && (lower.includes('bath') || lower.includes('soak') || lower.includes('submerge'))) return true;
    return false;
  };

  return (
    <View style={{ marginTop: Spacing.lg }}>
      <Text style={styles.guideSectionTitle}>Watering methods</Text>
      {WATERING_METHODS.map((method) => {
        const recommended = isRecommended(method.title);
        return (
        <View key={method.title} style={styles.accordionItem}>
          <TouchableOpacity
            onPress={() => setExpanded(expanded === method.title ? null : method.title)}
            style={styles.accordionHeader}
          >
            <Text style={styles.accordionTitle}>{method.title}{recommended ? ' (Recommended)' : ''}</Text>
            <Ionicons name={expanded === method.title ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.textSecondary} />
          </TouchableOpacity>
          {expanded === method.title && (
            <View style={styles.accordionBody}>
              {method.steps.map((step, i) => (
                <View key={i} style={styles.stepRow}>
                  <Text style={styles.stepNumber}>{i + 1}.</Text>
                  <Text style={styles.stepText}>{step}</Text>
                </View>
              ))}
              {method.note && (
                <InfoBox text={method.note} variant="info" />
              )}
            </View>
          )}
        </View>
        );
      })}
    </View>
  );
}

// ─── Reusable components ─────────────────────────────────────────────

function WaterDrops({ count }: { count: number }) {
  const c = Colors.moisture;
  if (count === 1) {
    return <Ionicons name="water" size={22} color={c} />;
  }
  if (count === 2) {
    return (
      <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
        <Ionicons name="water" size={18} color={c} style={{ marginRight: -4, opacity: 0.7 }} />
        <Ionicons name="water" size={22} color={c} />
      </View>
    );
  }
  return (
    <View style={{ alignItems: 'center' }}>
      <Ionicons name="water" size={16} color={c} style={{ marginBottom: -5 }} />
      <View style={{ flexDirection: 'row' }}>
        <Ionicons name="water" size={16} color={c} style={{ marginRight: -3, opacity: 0.7 }} />
        <Ionicons name="water" size={16} color={c} />
      </View>
    </View>
  );
}

function RulerIcon({ color }: { color: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: 24, width: 20 }}>
      {/* Vertical bar */}
      <View style={{ width: 2.5, height: 24, backgroundColor: color, borderRadius: 1 }} />
      {/* Horizontal base */}
      <View style={{ position: 'absolute', bottom: 0, left: 0, width: 14, height: 2.5, backgroundColor: color, borderRadius: 1 }} />
      {/* Ticks */}
      <View style={{ marginLeft: 1, justifyContent: 'space-between', height: 24, paddingVertical: 2 }}>
        <View style={{ height: 1.5, width: 10, backgroundColor: color, borderRadius: 1 }} />
        <View style={{ height: 1.5, width: 6, backgroundColor: color, borderRadius: 1, opacity: 0.6 }} />
        <View style={{ height: 1.5, width: 10, backgroundColor: color, borderRadius: 1 }} />
        <View style={{ height: 1.5, width: 6, backgroundColor: color, borderRadius: 1, opacity: 0.6 }} />
        <View style={{ height: 1.5, width: 10, backgroundColor: color, borderRadius: 1 }} />
      </View>
    </View>
  );
}

function DifficultyStars({ count, color, size = 14 }: { count: number; color: string; size?: number }) {
  return (
    <View style={styles.starsRow}>
      {Array.from({ length: 3 }).map((_, i) => (
        <Ionicons key={i} name="star" size={size} color={i < count ? color : `${color}30`} />
      ))}
    </View>
  );
}

function RoundBadge({ icon, label, bg, color, onPress, extraContent }: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  bg: string;
  color: string;
  onPress?: () => void;
  extraContent?: React.ReactNode;
}) {
  const content = (
    <View style={styles.badge}>
      <View style={[styles.badgeCircle, { backgroundColor: bg, shadowColor: color, shadowOpacity: 0.15, shadowRadius: 4, shadowOffset: { width: 0, height: 2 }, elevation: 3 }]}>
        {extraContent ?? <Ionicons name={icon} size={22} color={color} />}
      </View>
      <Text style={[styles.badgeLabel, { color }]} numberOfLines={1}>{label}</Text>
    </View>
  );
  if (onPress) {
    return <TouchableOpacity activeOpacity={0.7} onPress={onPress}>{content}</TouchableOpacity>;
  }
  return content;
}

const SECTION_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  Water: 'water-outline',
  Light: 'sunny-outline',
  'Air Humidity': 'cloud-outline',
  'Air Temperature': 'thermometer-outline',
  Outdoor: 'leaf-outline',
  Toxicity: 'alert-circle-outline',
  Lifecycle: 'sync-outline',
  'Used for': 'bookmark-outline',
  Soil: 'layers-outline',
  Fertilizing: 'flask-outline',
  Pruning: 'cut-outline',
  Harvest: 'nutrition-outline',
  Propagation: 'git-branch-outline',
  Difficulty: 'speedometer-outline',
  Size: 'resize-outline',
  Taxonomy: 'document-text-outline',
  Companions: 'people-outline',
};

function SectionTitle({ text }: { text: string }) {
  const icon = SECTION_ICONS[text];
  return (
    <View style={styles.sectionTitleRow}>
      {icon && <Ionicons name={icon} size={18} color={Colors.primary} />}
      <Text style={styles.sectionTitle}>{text}</Text>
    </View>
  );
}

function SectionDivider() {
  return <View style={styles.divider} />;
}

function FreqCircle({ number, label }: { number: string; label: string }) {
  return (
    <View style={styles.freqRow}>
      <View style={styles.freqCircle}>
        <Text style={styles.freqNumber}>{number}</Text>
      </View>
      <Text style={styles.freqLabel}>{label}</Text>
    </View>
  );
}

function InfoRow({ icon, text, sub, iconColor }: {
  icon: keyof typeof Ionicons.glyphMap;
  text: string;
  sub?: string;
  iconColor?: string;
}) {
  return (
    <View style={styles.infoRow}>
      <View style={[styles.infoIcon, { backgroundColor: iconColor ? `${iconColor}15` : '#F0F0F0' }]}>
        <Ionicons name={icon} size={18} color={iconColor ?? Colors.textSecondary} />
      </View>
      <View style={styles.infoText}>
        <Text style={styles.infoMain}>{text}</Text>
        {sub ? <Text style={styles.infoSub}>{sub}</Text> : null}
      </View>
    </View>
  );
}

function InfoBox({ text, variant }: { text: string; variant: 'info' | 'warning' | 'success' }) {
  const bg = variant === 'warning' ? '#FFF8E1' : variant === 'success' ? '#DCFCE7' : '#EBF5FF';
  const color = variant === 'warning' ? '#92400E' : variant === 'success' ? '#166534' : '#1E40AF';
  const iconName: keyof typeof Ionicons.glyphMap = variant === 'warning' ? 'alert-circle' : variant === 'success' ? 'checkmark-circle' : 'information-circle';
  const iconColor = variant === 'warning' ? '#D97706' : variant === 'success' ? '#16A34A' : '#2563EB';
  return (
    <View style={[styles.infoBox, { backgroundColor: bg }]}>
      <View style={styles.infoBoxRow}>
        <Ionicons name={iconName} size={16} color={iconColor} style={styles.infoBoxIcon} />
        <Text style={[styles.infoBoxText, { color }]}>{text}</Text>
      </View>
    </View>
  );
}

// ─── Expandable description ──────────────────────────────────────────

function ExpandableText({ text, maxLines = 3 }: { text: string; maxLines?: number }) {
  const [expanded, setExpanded] = useState(false);
  const [needsTruncation, setNeedsTruncation] = useState(false);

  return (
    <View>
      <Text
        style={styles.descText}
        numberOfLines={expanded ? undefined : maxLines}
        onTextLayout={(e) => {
          if (e.nativeEvent.lines.length > maxLines) {
            setNeedsTruncation(true);
          }
        }}
      >
        {text}
      </Text>
      {needsTruncation && (
        <TouchableOpacity onPress={() => setExpanded(!expanded)} style={styles.readMoreBtn}>
          <Text style={styles.readMoreText}>{expanded ? 'Show less' : 'Read more'}</Text>
          <Ionicons name={expanded ? 'chevron-up' : 'chevron-down'} size={14} color={Colors.primary} />
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─── Humidity level bar ──────────────────────────────────────────────

function HumidityBar({ level }: { level: string }) {
  // Determine humidity level from text
  const lower = level.toLowerCase();
  let pct = 50;
  let label = 'Medium';
  let barColor: string = Colors.info;
  if (lower.includes('high') || lower.includes('70') || lower.includes('80') || lower.includes('tropical')) {
    pct = 80; label = 'High'; barColor = '#0EA5E9';
  } else if (lower.includes('low') || lower.includes('dry') || lower.includes('20') || lower.includes('30')) {
    pct = 25; label = 'Low'; barColor = '#F59E0B';
  } else if (lower.includes('moderate') || lower.includes('average') || lower.includes('40') || lower.includes('50') || lower.includes('60')) {
    pct = 55; label = 'Medium'; barColor = '#22C55E';
  }

  return (
    <View style={styles.humBarContainer}>
      <View style={styles.humBarTrack}>
        <View style={[styles.humBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
      </View>
      <View style={styles.humBarLabels}>
        <Text style={styles.humBarLabel}>Dry</Text>
        <Text style={[styles.humBarValue, { color: barColor }]}>{label} ~{pct}%</Text>
        <Text style={styles.humBarLabel}>Humid</Text>
      </View>
    </View>
  );
}

// ─── Light level indicator ───────────────────────────────────────────

function LightLevelIndicator({ lightText }: { lightText: string }) {
  const lower = lightText.toLowerCase();
  let activeLevel = 1; // 0=shade, 1=partial, 2=full sun
  if (lower.includes('full') || lower.includes('direct') || lower.includes('bright')) {
    activeLevel = 2;
  } else if (lower.includes('indirect') || lower.includes('part') || lower.includes('medium')) {
    activeLevel = 1;
  } else {
    activeLevel = 0;
  }

  const levels = [
    { icon: 'cloudy' as keyof typeof Ionicons.glyphMap, label: 'Low', color: '#94A3B8' },
    { icon: 'partly-sunny' as keyof typeof Ionicons.glyphMap, label: 'Medium', color: '#F59E0B' },
    { icon: 'sunny' as keyof typeof Ionicons.glyphMap, label: 'High', color: '#EF8C17' },
  ];

  return (
    <View style={styles.lightLevelRow}>
      {levels.map((lvl, i) => {
        const isActive = i === activeLevel;
        return (
          <View key={lvl.label} style={styles.lightLevelItem}>
            <View style={[
              styles.lightLevelCircle,
              { backgroundColor: isActive ? `${lvl.color}20` : '#F3F4F6', borderColor: isActive ? lvl.color : '#E5E7EB' },
            ]}>
              <Ionicons name={lvl.icon} size={18} color={isActive ? lvl.color : '#D1D5DB'} />
            </View>
            <Text style={[styles.lightLevelLabel, isActive && { color: lvl.color, fontWeight: '700' }]}>{lvl.label}</Text>
          </View>
        );
      })}
      <View style={styles.lightLevelConnector} />
    </View>
  );
}

// ─── Soil pH bar ─────────────────────────────────────────────────────

function PHBar({ min, max }: { min: number; max: number }) {
  // pH scale 3-10
  const scaleMin = 3;
  const scaleMax = 10;
  const range = scaleMax - scaleMin;
  const leftPct = ((min - scaleMin) / range) * 100;
  const widthPct = ((max - min) / range) * 100;

  return (
    <View style={styles.phBarContainer}>
      <View style={styles.phBarTrack}>
        <View style={[styles.phBarFill, { left: `${leftPct}%`, width: `${widthPct}%` }]}>
          <Text style={styles.phBarValue}>{min} – {max}</Text>
        </View>
      </View>
      <View style={styles.phBarLabels}>
        <Text style={styles.phBarLabel}>Acidic</Text>
        <Text style={[styles.phBarLabel, { textAlign: 'center' }]}>Neutral</Text>
        <Text style={[styles.phBarLabel, { textAlign: 'right' }]}>Alkaline</Text>
      </View>
    </View>
  );
}

// ─── Month bar (outdoor months visualization) ───────────────────────

const MONTH_SHORT_LABELS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
const MONTH_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function MonthBar({ activeMonths, label, color }: { activeMonths: string[]; label: string; color?: string }) {
  const barColor = color ?? Colors.success;
  const activeSet = new Set(activeMonths);

  // Find first and last active index for the label
  const activeIndices = MONTH_FULL.map((m, i) => activeSet.has(m) ? i : -1).filter((i) => i >= 0);
  const firstActive = activeIndices[0] ?? -1;
  const lastActive = activeIndices[activeIndices.length - 1] ?? -1;

  const rangeText = activeMonths.length === 0
    ? 'Not recommended'
    : activeMonths.length === 12
    ? 'Full year'
    : `${MONTH_FULL[firstActive]?.slice(0, 3)} \u2013 ${MONTH_FULL[lastActive]?.slice(0, 3)}`;

  return (
    <View style={styles.monthBarContainer}>
      <Text style={styles.monthBarLabel}>{label}</Text>
      <View style={styles.monthBarRow}>
        {MONTH_FULL.map((month, i) => {
          const isActive = activeSet.has(month);
          // Check if neighbors are active for connected bar effect
          const prevActive = i > 0 && activeSet.has(MONTH_FULL[i - 1]);
          const nextActive = i < 11 && activeSet.has(MONTH_FULL[i + 1]);
          return (
            <View key={month} style={styles.monthBarCol}>
              <View style={[
                styles.monthBarDot,
                isActive && {
                  backgroundColor: barColor,
                  borderRadius: 4,
                  flex: 1,
                  marginHorizontal: 0,
                  borderTopLeftRadius: !prevActive ? 8 : 2,
                  borderBottomLeftRadius: !prevActive ? 8 : 2,
                  borderTopRightRadius: !nextActive ? 8 : 2,
                  borderBottomRightRadius: !nextActive ? 8 : 2,
                },
              ]} />
              <Text style={[styles.monthBarMonthLabel, isActive && { color: barColor, fontWeight: '700' }]}>
                {MONTH_SHORT_LABELS[i]}
              </Text>
            </View>
          );
        })}
      </View>
      {activeMonths.length > 0 && (
        <Text style={[styles.monthBarRangeText, { color: barColor }]}>{rangeText}</Text>
      )}
    </View>
  );
}

// ─── Section accent colors ───────────────────────────────────────────

const SECTION_ACCENT: Record<string, string> = {
  water: '#3B82F6',
  light: '#F59E0B',
  humidity: '#0EA5E9',
  temperature: '#EF4444',
  outdoor: '#22C55E',
  toxicity: '#EF4444',
  lifecycle: '#8B5CF6',
  used_for: '#10B981',
  soil: '#92400E',
  fertilizing: '#16A34A',
  pruning: '#6B7280',
  harvest: '#F97316',
  propagation: '#8B5CF6',
  difficulty: '#F59E0B',
  size: '#7C3AED',
  taxonomy: '#6B7280',
  companions: '#10B981',
};

// ─── Styles ──────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingBottom: 100 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  notFoundText: { fontSize: FontSize.lg, color: Colors.textSecondary, marginTop: Spacing.md },
  backLink: { fontSize: FontSize.md, color: Colors.primary, marginTop: Spacing.lg },

  // Hero
  hero: { width: '100%', height: 300 },
  heroPlaceholder: { backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center' },

  // Name
  nameBlock: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.lg, paddingBottom: Spacing.sm },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  name: { fontSize: 26, fontWeight: '700', color: Colors.text },
  addPhotoBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#EBF5FF', alignItems: 'center', justifyContent: 'center' },
  scientific: { fontSize: FontSize.md, color: Colors.textSecondary, fontStyle: 'italic', marginTop: 2 },

  // Description bubble
  descBubble: { marginHorizontal: Spacing.lg, marginBottom: Spacing.md, backgroundColor: '#E8F5E9', borderRadius: BorderRadius.lg, padding: Spacing.md },
  descText: { fontSize: FontSize.sm, color: '#1B5E20', lineHeight: 20 },

  // Sticky nav wrapper
  stickyNav: { backgroundColor: Colors.background, paddingTop: Spacing.sm, paddingBottom: Spacing.xs },

  // Round badges
  badgeRow: { flexDirection: 'row', paddingHorizontal: Spacing.lg, gap: Spacing.md, marginBottom: Spacing.sm, justifyContent: 'center' },
  badge: { alignItems: 'center', width: 62 },
  badgeCircle: { width: 50, height: 50, borderRadius: 25, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  badgeLabel: { fontSize: 11, fontWeight: '700', textAlign: 'center' },
  dropsRow: { flexDirection: 'row', gap: 1 },
  starsRow: { flexDirection: 'row', gap: 1 },

  // Tab bar
  tabBar: { paddingHorizontal: Spacing.lg, gap: Spacing.xs, paddingVertical: Spacing.sm },
  tab: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, borderRadius: BorderRadius.lg, borderWidth: 1, borderColor: Colors.border, backgroundColor: Colors.surface },
  tabActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  tabText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textSecondary },
  tabTextActive: { color: '#fff' },

  // Sections container
  sectionsContainer: { paddingHorizontal: Spacing.md, paddingTop: Spacing.sm, gap: Spacing.md },

  // Section card
  sectionCard: { backgroundColor: Colors.surface, borderRadius: BorderRadius.lg, padding: Spacing.lg, borderWidth: 1, borderColor: Colors.border },
  sectionCardAccent: { borderLeftWidth: 3 },

  // Watering guide button & content
  // Temperature range bar
  tempBarContainer: { marginBottom: Spacing.md },
  tempBarTrack: { height: 24, backgroundColor: '#E5E7EB', borderRadius: 12, overflow: 'visible' as const },
  tempBarOptimal: { position: 'absolute' as const, height: 24, backgroundColor: Colors.success, borderRadius: 12, justifyContent: 'center' as const, alignItems: 'center' as const },
  tempBarInnerLabel: { fontSize: 10, fontWeight: '700' as const, color: '#fff' },
  tempBarLabels: { flexDirection: 'row' as const, justifyContent: 'space-between' as const, marginTop: 4 },
  tempBarLabel: { fontSize: 10, color: Colors.textSecondary },

  measureLightBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, backgroundColor: Colors.primary, borderRadius: BorderRadius.md, paddingVertical: Spacing.sm, marginTop: Spacing.md },
  measureLightText: { fontSize: FontSize.sm, fontWeight: '600', color: '#fff' },
  guideBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs, paddingVertical: Spacing.sm, marginTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border },
  guideBtnText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.primary },
  guideSectionTitle: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.text, marginBottom: Spacing.sm, marginTop: Spacing.md },

  // Modal
  modalContainer: { flex: 1, backgroundColor: Colors.background },
  modalHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.xl, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  modalTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },
  modalScroll: { padding: Spacing.lg, paddingBottom: 60 },
  modalPlantName: { fontSize: FontSize.md, color: Colors.textSecondary, fontStyle: 'italic', marginBottom: Spacing.lg },

  // Accordion
  accordionItem: { borderWidth: 1, borderColor: Colors.border, borderRadius: BorderRadius.md, marginBottom: Spacing.sm, overflow: 'hidden' },
  accordionItemRecommended: { borderColor: Colors.primary, borderWidth: 1.5 },
  accordionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: Spacing.md, backgroundColor: Colors.surface },
  accordionTitle: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.text },
  accordionBody: { padding: Spacing.md, paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border },
  stepRow: { flexDirection: 'row', marginBottom: Spacing.sm, gap: Spacing.sm },
  stepNumber: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.primary, width: 20 },
  stepText: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20, flex: 1 },

  // Watering chart
  chartContainer: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 100, paddingTop: Spacing.sm },
  chartBarCol: { alignItems: 'center', flex: 1 },
  chartBar: { width: 16, borderRadius: 4, minHeight: 8 },
  chartMonthLabel: { fontSize: 10, color: Colors.textSecondary, marginTop: 4, fontWeight: '500' },
  chartMonthLabelActive: { color: Colors.primary, fontWeight: '700' },
  chartLabel: { fontSize: FontSize.sm, color: Colors.text, fontWeight: '600', textAlign: 'center', marginBottom: Spacing.sm },

  // Section title
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.md },
  sectionTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },

  // Divider
  divider: { height: 1, backgroundColor: Colors.border, marginVertical: Spacing.lg },

  // Difficulty row
  difficultyRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.md },
  difficultyLabel: { fontSize: FontSize.md, fontWeight: '700' },

  // Frequency circle
  freqRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, marginBottom: Spacing.md },
  freqCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: Colors.primary, alignItems: 'center', justifyContent: 'center' },
  freqNumber: { fontSize: FontSize.lg, fontWeight: '700', color: '#fff' },
  freqLabel: { flex: 1, fontSize: FontSize.sm, color: Colors.text, lineHeight: 20 },

  // Info row
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, marginBottom: Spacing.md },
  infoIcon: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  infoText: { flex: 1 },
  infoMain: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20 },
  infoSub: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 1 },

  // Info box
  infoBox: { borderRadius: BorderRadius.md, padding: Spacing.md, marginBottom: Spacing.md },
  infoBoxRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  infoBoxIcon: { marginTop: 2 },
  infoBoxText: { fontSize: FontSize.sm, lineHeight: 20, flex: 1 },

  // Body text
  bodyText: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20, marginBottom: Spacing.md },

  // Chips
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, marginBottom: Spacing.md },
  chip: { backgroundColor: '#E5E7EB', borderRadius: 16, paddingHorizontal: Spacing.md, paddingVertical: 6 },
  chipText: { fontSize: FontSize.sm, color: Colors.text, fontWeight: '600' },
  chipGreen: { backgroundColor: '#DCFCE7' },
  chipTextGreen: { fontSize: FontSize.sm, color: '#166534', fontWeight: '600' },

  // Live sensor
  liveBlock: { marginVertical: Spacing.md, padding: Spacing.md, backgroundColor: Colors.surface, borderRadius: BorderRadius.md, borderWidth: 1, borderColor: Colors.border },
  liveHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.sm },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.success },
  liveLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, flex: 1 },
  liveValue: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },

  // Add to collection floating bar
  addToCollectionBar: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: Spacing.md, paddingBottom: Spacing.xxl, backgroundColor: Colors.background },
  addToCollectionBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, backgroundColor: Colors.primary, borderRadius: BorderRadius.lg, paddingVertical: Spacing.md, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 8, shadowOffset: { width: 0, height: -2 }, elevation: 5 },
  addToCollectionText: { fontSize: FontSize.md, fontWeight: '700', color: '#fff' },

  // Expandable text
  readMoreBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  readMoreText: { fontSize: FontSize.xs, fontWeight: '600', color: Colors.primary },

  // Humidity bar
  humBarContainer: { marginBottom: Spacing.md },
  humBarTrack: { height: 10, backgroundColor: '#E5E7EB', borderRadius: 5, overflow: 'hidden' },
  humBarFill: { height: 10, borderRadius: 5 },
  humBarLabels: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 },
  humBarLabel: { fontSize: 10, color: Colors.textSecondary },
  humBarValue: { fontSize: 11, fontWeight: '700' },

  // Light level indicator
  lightLevelRow: { flexDirection: 'row', justifyContent: 'center', gap: Spacing.xl, marginBottom: Spacing.md, position: 'relative' },
  lightLevelItem: { alignItems: 'center', zIndex: 1 },
  lightLevelCircle: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', borderWidth: 2 },
  lightLevelLabel: { fontSize: 10, color: Colors.textSecondary, marginTop: 4, fontWeight: '500' },
  lightLevelConnector: { position: 'absolute', top: 19, left: '20%', right: '20%', height: 2, backgroundColor: '#E5E7EB', zIndex: 0 },

  // Month bar (outdoor months)
  monthBarContainer: { marginBottom: Spacing.md },
  monthBarLabel: { fontSize: FontSize.xs, fontWeight: '600', color: Colors.textSecondary, marginBottom: Spacing.xs },
  monthBarRow: { flexDirection: 'row', height: 16, gap: 2 },
  monthBarCol: { flex: 1, alignItems: 'center' },
  monthBarDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#D1D5DB' },
  monthBarMonthLabel: { fontSize: 8, color: Colors.textSecondary, marginTop: 2 },
  monthBarRangeText: { fontSize: FontSize.xs, fontWeight: '700', textAlign: 'center', marginTop: 4 },

  // pH bar
  phBarContainer: { marginBottom: Spacing.md },
  phBarTrack: { height: 16, borderRadius: 8, overflow: 'visible', backgroundColor: '#E5E7EB' },
  phBarFill: { position: 'absolute', height: 16, borderRadius: 8, backgroundColor: '#22C55E', justifyContent: 'center', alignItems: 'center' },
  phBarValue: { fontSize: 10, fontWeight: '700', color: '#fff' },
  phBarLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  phBarLabel: { fontSize: 10, color: Colors.textSecondary, flex: 1 },
});
