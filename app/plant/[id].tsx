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
import type { PresetCare } from '../../src/constants/presets';

// ─── PlantVM ─────────────────────────────────────────────────────────

interface PlantVM {
  scientific: string;
  common_name: string;
  family: string;
  preset: string;
  plant_type: 'decorative' | 'greens' | 'fruiting';
  image_url?: string;
  description: string;
  difficulty: string;
  difficulty_note: string;
  growth_rate: string;
  lifecycle: string;
  lifecycle_years: string;
  height_max_cm: number;
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
        preset: userPlant.preset ?? 'Standard',
        plant_type: (lib?.plant_type ?? 'decorative') as 'decorative' | 'greens' | 'fruiting',
        image_url: userPlant.image_url,
        description: dbEntry?.description ?? lib?.description ?? '',
        difficulty: dbEntry?.care?.difficulty ?? lib?.difficulty ?? '',
        difficulty_note: lib?.difficulty_note ?? '',
        growth_rate: dbEntry?.care?.growth_rate ?? lib?.growth_rate ?? '',
        lifecycle: dbEntry?.care?.lifecycle ?? lib?.lifecycle ?? '',
        height_max_cm: dbEntry?.care?.height_max_cm ?? lib?.height_max_cm ?? 0,
        edible: !!(dbEntry?.edible ?? lib?.edible),
        edible_parts: lib?.edible_parts ?? '',
        poisonous_to_pets: userPlant.poisonous_to_pets ?? false,
        poisonous_to_humans: userPlant.poisonous_to_humans ?? false,
        toxicity_note: userPlant.toxicity_note ?? '',
        toxic_parts: lib?.toxic_parts ?? '',
        toxicity_severity: lib?.toxicity_severity ?? '',
        toxicity_symptoms: lib?.toxicity_symptoms ?? '',
        toxicity_first_aid: lib?.toxicity_first_aid ?? '',
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
        preset: dbEntry.preset,
        plant_type: category === 'greens' || category === 'fruiting' ? category : 'decorative',
        image_url: dbEntry.image_url,
        description: dbEntry.description ?? '',
        difficulty: dbEntry.care?.difficulty ?? '',
        difficulty_note: lib?.difficulty_note ?? '',
        growth_rate: dbEntry.care?.growth_rate ?? '',
        lifecycle: dbEntry.care?.lifecycle ?? '',
        height_max_cm: dbEntry.care?.height_max_cm ?? 0,
        edible: !!dbEntry.edible,
        edible_parts: lib?.edible_parts ?? '',
        poisonous_to_pets: !!dbEntry.care?.toxic_to_pets,
        poisonous_to_humans: !!dbEntry.care?.toxic_to_humans,
        toxicity_note: dbEntry.care?.toxicity_note ?? '',
        toxic_parts: lib?.toxic_parts ?? '',
        toxicity_severity: lib?.toxicity_severity ?? '',
        toxicity_symptoms: lib?.toxicity_symptoms ?? '',
        toxicity_first_aid: lib?.toxicity_first_aid ?? '',
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
        preset: lib.preset,
        plant_type: lib.plant_type,
        image_url: lib.image_url,
        description: lib.description ?? '',
        difficulty: lib.difficulty ?? '',
        difficulty_note: lib.difficulty_note ?? '',
        growth_rate: lib.growth_rate ?? '',
        lifecycle: lib.lifecycle ?? '',
        height_max_cm: lib.height_max_cm ?? 0,
        edible: !!lib.edible,
        edible_parts: lib.edible_parts ?? '',
        poisonous_to_pets: lib.poisonous_to_pets,
        poisonous_to_humans: lib.poisonous_to_humans,
        toxicity_note: lib.toxicity_note,
        toxic_parts: lib.toxic_parts ?? '',
        toxicity_severity: lib.toxicity_severity ?? '',
        toxicity_symptoms: lib.toxicity_symptoms ?? '',
        toxicity_first_aid: lib.toxicity_first_aid ?? '',
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
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
      };
    }

    return null;
  }, [id, plants, dbEntry]);
}

// ─── Section definitions ─────────────────────────────────────────────

type SectionKey =
  | 'water' | 'light' | 'humidity' | 'temperature' | 'outdoor' | 'toxicity'
  | 'lifecycle' | 'used_for' | 'soil' | 'fertilizing'
  | 'difficulty' | 'size' | 'taxonomy' | 'companions';

interface SectionDef {
  key: SectionKey;
  label: string;
}

function getSections(_plant: PlantVM): SectionDef[] {
  return [
    { key: 'water', label: 'Water' },
    { key: 'light', label: 'Light' },
    { key: 'humidity', label: 'Air Humidity' },
    { key: 'temperature', label: 'Air Temperature' },
    { key: 'outdoor', label: 'Outdoor' },
    { key: 'toxicity', label: 'Toxicity' },
    { key: 'lifecycle', label: 'Lifecycle' },
    { key: 'used_for', label: 'Used for' },
    { key: 'soil', label: 'Soil' },
    { key: 'fertilizing', label: 'Fertilizing' },
    { key: 'difficulty', label: 'Difficulty' },
    { key: 'size', label: 'Size' },
    { key: 'taxonomy', label: 'Taxonomy' },
    { key: 'companions', label: 'Companions' },
  ];
}

// ─── Screen ──────────────────────────────────────────────────────────

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const plant = usePlantVM(id);

  const mainScrollRef = useRef<ScrollView>(null);
  const tabScrollRef = useRef<ScrollView>(null);
  const sectionYs = useRef<Record<string, number>>({});
  const containerY = useRef(0);
  const stickyNavHeight = useRef(0);
  const tabXs = useRef<Record<string, number>>({});
  const [activeSection, setActiveSection] = useState<SectionKey>('water');
  const [showWateringGuide, setShowWateringGuide] = useState(false);
  const [showLightGuide, setShowLightGuide] = useState(false);
  const [showHumidityGuide, setShowHumidityGuide] = useState(false);
  const [showTempGuide, setShowTempGuide] = useState(false);
  const [showOutdoorGuide, setShowOutdoorGuide] = useState(false);
  const [showToxicityGuide, setShowToxicityGuide] = useState(false);
  const [showUsedForGuide, setShowUsedForGuide] = useState(false);
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

  const scrollTabBarTo = useCallback((key: SectionKey) => {
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

  const scrollToSection = useCallback((key: SectionKey) => {
    const absY = getAbsoluteY(key);
    if (absY != null && mainScrollRef.current) {
      isAutoScrolling.current = true;
      setActiveSection(key);
      scrollTabBarTo(key);
      // Scroll so section appears just below the sticky nav
      mainScrollRef.current.scrollTo({ y: absY - stickyNavHeight.current, animated: true });
      setTimeout(() => { isAutoScrolling.current = false; }, 600);
    }
  }, [scrollTabBarTo, getAbsoluteY]);

  const onMainScroll = useCallback((e: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isAutoScrolling.current || !plant) return;
    // The visible top edge, accounting for sticky nav
    const scrollY = e.nativeEvent.contentOffset.y + stickyNavHeight.current + 20;
    const sections = getSections(plant);
    let current = sections[0]?.key ?? 'water';
    for (const sec of sections) {
      const absY = getAbsoluteY(sec.key);
      if (absY != null && scrollY >= absY) {
        current = sec.key;
      }
    }
    if (current !== activeSection) {
      setActiveSection(current);
      scrollTabBarTo(current);
    }
  }, [plant, activeSection, scrollTabBarTo, getAbsoluteY]);

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
  const seasonCoeff = [3.0, 2.8, 2.1, 1.6, 1.2, 1.0, 1.0, 1.0, 1.2, 1.6, 2.1, 2.8][monthIndex];
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
        scrollEventThrottle={32}
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
          <Text style={styles.name}>{plant.common_name || plant.scientific}</Text>
          {plant.common_name ? (
            <Text style={styles.scientific}>{plant.scientific}</Text>
          ) : null}
        </View>

        {/* ═══ CHILD 2: DESCRIPTION (always rendered for stable index) ═══ */}
        <View>
          {plant.description ? (
            <View style={styles.descBubble}>
              <Text style={styles.descText}>{plant.description}</Text>
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
              onPress={() => scrollToSection('water')}
            />
            <RoundBadge
              icon={lightIcon}
              label={lightLabel}
              bg="#FFF8E1"
              color="#F59E0B"
              onPress={() => scrollToSection('light')}
            />
            {plant.difficulty ? (
              <RoundBadge
                icon="star"
                label={plant.difficulty}
                bg={diffBg}
                color={diffColor}
                extraContent={<DifficultyStars count={diffStars} color={diffColor} />}
                onPress={() => scrollToSection('difficulty')}
              />
            ) : null}
            <RoundBadge
              icon="resize-outline"
              label="Size"
              bg="#F3E8FF"
              color="#7C3AED"
              extraContent={<RulerIcon color="#7C3AED" />}
              onPress={() => scrollToSection('size')}
            />
            {isToxic && (
              <RoundBadge
                icon={plant.poisonous_to_humans ? 'skull-outline' : 'warning-outline'}
                label="Toxic"
                bg="#FEE2E2"
                color={Colors.error}
                onPress={() => scrollToSection('toxicity')}
              />
            )}
          </View>

          <ScrollView
            ref={tabScrollRef}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.tabBar}
          >
            {sections.map((sec) => (
              <TouchableOpacity
                key={sec.key}
                activeOpacity={0.7}
                onPress={() => scrollToSection(sec.key)}
                onLayout={(e) => onTabLayout(sec.key, e)}
                style={[styles.tab, activeSection === sec.key && styles.tabActive]}
              >
                <Text style={[styles.tabText, activeSection === sec.key && styles.tabTextActive]}>
                  {sec.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* ═══ CHILD 4: ALL SECTIONS (long feed) ═══ */}
        <View style={styles.sectionsContainer} onLayout={onContainerLayout}>

          {/* ── 1. Water ── */}
          <View onLayout={(e) => onSectionLayout('water', e)} style={styles.sectionCard}>
            <SectionTitle text="Water" />
            <InfoRow icon="water-outline" text={`Every ~${currentWateringDays} days in ${currentMonth}`} sub={plant.watering_demand ? `${plant.watering_soil_hint} \u2022 ${plant.watering_demand} demand` : care.watering} />
            {plant.watering_warning ? (
              <InfoBox text={plant.watering_warning} variant="warning" />
            ) : waterDrops === 1 ? (
              <InfoBox text="This plant is sensitive to overwatering. Let the soil dry out completely between waterings." variant="warning" />
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

          {/* ── 2. Light ── */}
          <View onLayout={(e) => onSectionLayout('light', e)} style={styles.sectionCard}>
            <SectionTitle text="Light" />
            <InfoRow icon="sunny-outline" text={care.light} sub="Preferred" />
            <InfoRow icon="partly-sunny-outline" text={care.light_also_ok} sub="Also tolerates" />
            {care.light.includes('Full') || care.light.includes('Bright') ? (
              <InfoBox text="Needs strong light. Without it — stretches and weakens." variant="warning" />
            ) : care.light.includes('indirect') ? (
              <InfoBox text="No direct sun — leaves burn." variant="info" />
            ) : (
              <InfoBox text="Low-light tolerant. Growth slows in dark spots." variant="info" />
            )}
            <TouchableOpacity onPress={() => {}} style={styles.measureLightBtn}>
              <Ionicons name="flashlight-outline" size={18} color="#fff" />
              <Text style={styles.measureLightText}>Measure light</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setShowLightGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Light guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 3. Air Humidity ── */}
          <View onLayout={(e) => onSectionLayout('humidity', e)} style={styles.sectionCard}>
            <SectionTitle text="Air Humidity" />
            <InfoRow icon="cloud-outline" text={care.humidity.replace(/\s*\([\d\-–%\s]+\)\s*/g, '')} sub="Air humidity level" />
            {care.humidity_action ? (
              <InfoBox text={care.humidity_action} variant={care.humidity.toLowerCase().includes('low') ? 'warning' : 'info'} />
            ) : null}
            <TouchableOpacity onPress={() => setShowHumidityGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Humidity guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 4. Air Temperature ── */}
          <View onLayout={(e) => onSectionLayout('temperature', e)} style={styles.sectionCard}>
            <SectionTitle text="Air Temperature" />
            <TempRangeBar optLow={plant.temp_opt_low_c} optHigh={plant.temp_opt_high_c} />
            <InfoRow icon="thermometer-outline" text={`Min ${plant.temp_min_c}°C / Max ${plant.temp_max_c}°C`} sub="Survival limits" />
            {plant.temp_warning ? (
              <InfoBox text={plant.temp_warning} variant="warning" />
            ) : null}
            <TouchableOpacity onPress={() => setShowTempGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Temperature guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 5. Outdoor ── */}
          <View onLayout={(e) => onSectionLayout('outdoor', e)} style={styles.sectionCard}>
            <SectionTitle text="Outdoor" />
            <InfoRow icon="home-outline" text="Full year" sub="Can be kept indoors" />
            <InfoRow icon="leaf-outline" text="Depends on your location" sub="Outdoor months (potted)" />
            <InfoRow icon="earth-outline" text="Depends on your location" sub="Outdoor months (in ground)" />
            <View style={{ marginTop: Spacing.sm }}>
              <Text style={[styles.bodyText, { fontWeight: '600' }]}>Frost tolerance</Text>
              <InfoRow icon="thermometer-outline" text={`${plant.temp_min_c}°C (${Math.round(plant.temp_min_c * 9 / 5 + 32)}°F)`} sub="Lowest temp to survive when potted" />
            </View>
            <InfoBox text="Potted plants are more sensitive to cold than plants in the ground — roots in a pot freeze faster." variant="warning" />
            <TouchableOpacity onPress={() => setShowOutdoorGuide(true)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Outdoor guide</Text>
              <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
            </TouchableOpacity>
          </View>

          {/* ── 6. Toxicity ── */}
          <View onLayout={(e) => onSectionLayout('toxicity', e)} style={styles.sectionCard}>
            <SectionTitle text="Toxicity" />
            {isToxic ? (
              <>
                <InfoRow icon="alert-circle" text={`Toxic${plant.toxicity_severity ? ` (${plant.toxicity_severity})` : ''}`} iconColor={Colors.error} />
                <View style={styles.chipRow}>
                  {plant.poisonous_to_humans && <View style={styles.chip}><Text style={styles.chipText}>Humans</Text></View>}
                  {plant.poisonous_to_pets && <View style={styles.chip}><Text style={styles.chipText}>Animals</Text></View>}
                </View>
                {plant.toxic_parts ? (
                  <InfoRow icon="warning-outline" text={plant.toxic_parts} sub="Toxic parts" iconColor={Colors.error} />
                ) : null}
                {plant.edible && plant.edible_parts ? (
                  <InfoRow icon="nutrition-outline" text={plant.edible_parts} sub="Edible parts" iconColor={Colors.success} />
                ) : null}
                {plant.toxicity_note ? (
                  <InfoBox text={plant.toxicity_note} variant="warning" />
                ) : null}
                <TouchableOpacity onPress={() => setShowToxicityGuide(true)} style={styles.guideBtn}>
                  <Text style={styles.guideBtnText}>Toxicity details</Text>
                  <Ionicons name="chevron-forward" size={16} color={Colors.primary} />
                </TouchableOpacity>
              </>
            ) : (
              <>
                <InfoRow icon="checkmark-circle" text="Not toxic" iconColor={Colors.success} />
                <InfoBox text="This plant is considered non-toxic to humans and pets." variant="success" />
              </>
            )}
          </View>

          {/* ── 7. Lifecycle ── */}
          <View onLayout={(e) => onSectionLayout('lifecycle', e)} style={styles.sectionCard}>
            <SectionTitle text="Lifecycle" />
            <InfoRow icon="sync-outline" text={plant.lifecycle === 'perennial' ? 'Perennial' : plant.lifecycle === 'annual' ? 'Annual' : plant.lifecycle || 'Unknown'} sub={plant.lifecycle_years ? (plant.lifecycle === 'perennial' ? `Lives ${plant.lifecycle_years} years` : `${plant.lifecycle_years}`) : (plant.lifecycle === 'perennial' ? 'Lives for multiple years' : 'One growing season')} />
            <InfoRow icon="leaf-outline" text={plant.lifecycle === 'perennial' ? 'Evergreen' : 'Seasonal'} sub="Foliage type" />
            {plant.lifecycle === 'perennial' ? (
              <InfoBox text="Active growth in spring and summer. Slower or dormant in winter — reduce watering and feeding." variant="info" />
            ) : (
              <InfoBox text="Complete lifecycle in one season. Start new plants from seed when this one finishes." variant="info" />
            )}
          </View>

          {/* ── 7. Used for ── */}
          <View onLayout={(e) => onSectionLayout('used_for', e)} style={styles.sectionCard}>
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

          {/* ── 8. Soil ── */}
          <View onLayout={(e) => onSectionLayout('soil', e)} style={styles.sectionCard}>
            <SectionTitle text="Soil" />
            <InfoRow icon="layers-outline" text={care.soil} sub="Soil mix" />
            {plant.soil_ph_min != null && plant.soil_ph_min > 0 && (
              <InfoRow icon="flask-outline" text={`pH ${plant.soil_ph_min} – ${plant.soil_ph_max}`} sub="Soil acidity" />
            )}
            <InfoRow icon="resize-outline" text={care.repot} sub="Repotting" />
            <InfoRow icon="sparkles-outline" text="Wipe leaves with a damp cloth" sub="Removes dust, helps photosynthesis" />
          </View>

          {/* ── 9. Fertilizing ── */}
          <View onLayout={(e) => onSectionLayout('fertilizing', e)} style={styles.sectionCard}>
            <SectionTitle text="Fertilizing" />
            <InfoRow icon="leaf-outline" text={care.fertilizer} sub={care.fertilizer_season} />
          </View>

          {/* ── 10. Difficulty ── */}
          <View onLayout={(e) => onSectionLayout('difficulty', e)} style={styles.sectionCard}>
            <SectionTitle text="Difficulty" />
            <View style={styles.difficultyRow}>
              <DifficultyStars count={diffStars} color={diffColor} size={22} />
              <Text style={[styles.difficultyLabel, { color: diffColor }]}>{plant.difficulty || 'Unknown'}</Text>
            </View>
            {plant.difficulty_note ? (
              <InfoBox text={plant.difficulty_note} variant="info" />
            ) : plant.difficulty === 'Easy' ? (
              <InfoBox text="Forgiving plant — tolerates irregular watering, adapts to various light conditions. Great for beginners." variant="success" />
            ) : plant.difficulty === 'Advanced' ? (
              <InfoBox text="Needs precise humidity, consistent watering schedule, and specific light conditions. Not forgiving of mistakes." variant="warning" />
            ) : (
              <InfoBox text="Needs some attention — regular watering and decent light, but recovers from occasional neglect." variant="info" />
            )}
          </View>

          {/* ── 11. Size ── */}
          <View onLayout={(e) => onSectionLayout('size', e)} style={styles.sectionCard}>
            <SectionTitle text="Size" />
            <InfoRow icon="arrow-up-outline" text={plant.height_max_cm > 0 ? `Up to ${plant.height_max_cm} cm (${Math.round(plant.height_max_cm / 2.54)}″)` : 'Not specified'} sub="Max height (full grown)" />
            <InfoRow icon="trending-up-outline" text={plant.growth_rate || 'Not specified'} sub="Growth rate" />
            {plant.height_max_cm > 100 ? (
              <InfoBox text={`In a pot, expect much less than ${plant.height_max_cm} cm. Pot size limits root growth which limits height.`} variant="info" />
            ) : plant.height_max_cm > 0 ? (
              <InfoBox text="Pot size directly affects final size. Bigger pot = bigger plant. Repot when roots circle the bottom." variant="info" />
            ) : null}
          </View>

          {/* ── 13. Taxonomy ── */}
          <View onLayout={(e) => onSectionLayout('taxonomy', e)} style={styles.sectionCard}>
            <SectionTitle text="Taxonomy" />
            <InfoRow icon="document-text-outline" text={plant.scientific} sub="Scientific name" />
            <InfoRow icon="git-branch-outline" text={plant.family} sub="Family" />
            {plant.common_name ? (
              <InfoRow icon="globe-outline" text={plant.common_name} sub="Common name" />
            ) : null}
          </View>

          {/* ── 14. Companions ── */}
          <View onLayout={(e) => onSectionLayout('companions', e)} style={styles.sectionCard}>
            <SectionTitle text="Companions" />
            <InfoBox text="Companion planting data coming soon — good and bad neighbors, nutrient cycling, pest management." variant="info" />
          </View>

        </View>
      </ScrollView>

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
            <WateringChart baseDays={baseDays} currentMonth={monthIndex} />

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
            <InfoBox text="Enable location services to see current outdoor temperature in your area and whether it's safe to place this plant outside." variant="info" />

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

            <Text style={styles.guideSectionTitle}>Indoor vs Outdoor months</Text>
            <InfoRow icon="home-outline" text="Full year" sub="Indoor — safe year-round" />
            <InfoRow icon="leaf-outline" text="Depends on your location" sub="Outdoor (potted) — enable location for dates" />
            <InfoRow icon="earth-outline" text="Depends on your location" sub="Outdoor (in ground) — enable location for dates" />
            <InfoBox text="Enable location services to see which months are safe for outdoor placement in your area." variant="info" />

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
            <InfoBox text="Enable location services and we will determine your frost tolerance zone automatically." variant="info" />
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
    </>
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

const SEASON_COEFFS = [3.0, 2.8, 2.1, 1.6, 1.2, 1.0, 1.0, 1.0, 1.2, 1.6, 2.1, 2.8];
const MONTH_LABELS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

function WateringChart({ baseDays, currentMonth }: { baseDays: number; currentMonth: number }) {
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);

  const daysPerMonth = SEASON_COEFFS.map((c) => Math.round(baseDays * c));
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
  if (count === 1) {
    return <Ionicons name="water" size={18} color={Colors.moisture} />;
  }
  if (count === 2) {
    return (
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <Ionicons name="water" size={14} color={Colors.moisture} style={{ marginRight: -3 }} />
        <Ionicons name="water" size={14} color={Colors.moisture} />
      </View>
    );
  }
  // 3 drops: pyramid — 1 on top, 2 on bottom, overlapping
  return (
    <View style={{ alignItems: 'center' }}>
      <Ionicons name="water" size={12} color={Colors.moisture} style={{ marginBottom: -4 }} />
      <View style={{ flexDirection: 'row' }}>
        <Ionicons name="water" size={12} color={Colors.moisture} style={{ marginRight: -2 }} />
        <Ionicons name="water" size={12} color={Colors.moisture} />
      </View>
    </View>
  );
}

function RulerIcon({ color }: { color: string }) {
  // Vertical ruler with L-shaped base and tick marks
  const tick = (w: number) => (
    <View style={{ height: 1.5, width: w, backgroundColor: color, marginBottom: 3 }} />
  );
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: 22, width: 18 }}>
      {/* Vertical bar */}
      <View style={{ width: 2, height: 22, backgroundColor: color, marginRight: 1 }} />
      {/* Ticks */}
      <View style={{ justifyContent: 'space-between', height: 22, paddingVertical: 1 }}>
        {tick(8)}
        {tick(5)}
        {tick(8)}
        {tick(5)}
        {tick(8)}
      </View>
    </View>
  );
}

function DifficultyStars({ count, color, size = 12 }: { count: number; color: string; size?: number }) {
  return (
    <View style={styles.starsRow}>
      {Array.from({ length: count }).map((_, i) => (
        <Ionicons key={i} name="star" size={size} color={color} />
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
      <View style={[styles.badgeCircle, { backgroundColor: bg }]}>
        {extraContent ?? <Ionicons name={icon} size={20} color={color} />}
      </View>
      <Text style={[styles.badgeLabel, { color }]} numberOfLines={1}>{label}</Text>
    </View>
  );
  if (onPress) {
    return <TouchableOpacity activeOpacity={0.7} onPress={onPress}>{content}</TouchableOpacity>;
  }
  return content;
}

function SectionTitle({ text }: { text: string }) {
  return <Text style={styles.sectionTitle}>{text}</Text>;
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
  return (
    <View style={[styles.infoBox, { backgroundColor: bg }]}>
      <Text style={[styles.infoBoxText, { color }]}>{text}</Text>
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingBottom: 60 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  notFoundText: { fontSize: FontSize.lg, color: Colors.textSecondary, marginTop: Spacing.md },
  backLink: { fontSize: FontSize.md, color: Colors.primary, marginTop: Spacing.lg },

  // Hero
  hero: { width: '100%', height: 300 },
  heroPlaceholder: { backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center' },

  // Name
  nameBlock: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.lg, paddingBottom: Spacing.sm },
  name: { fontSize: 26, fontWeight: '700', color: Colors.text },
  scientific: { fontSize: FontSize.md, color: Colors.textSecondary, fontStyle: 'italic', marginTop: 2 },

  // Description bubble
  descBubble: { marginHorizontal: Spacing.lg, marginBottom: Spacing.md, backgroundColor: '#E8F5E9', borderRadius: BorderRadius.lg, padding: Spacing.md },
  descText: { fontSize: FontSize.sm, color: '#1B5E20', lineHeight: 20 },

  // Sticky nav wrapper
  stickyNav: { backgroundColor: Colors.background, paddingTop: Spacing.sm, paddingBottom: Spacing.xs },

  // Round badges
  badgeRow: { flexDirection: 'row', paddingHorizontal: Spacing.lg, gap: Spacing.md, marginBottom: Spacing.sm, justifyContent: 'center' },
  badge: { alignItems: 'center', width: 58 },
  badgeCircle: { width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  badgeLabel: { fontSize: 11, fontWeight: '600', textAlign: 'center' },
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
  sectionTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text, marginTop: Spacing.md, marginBottom: Spacing.md },

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
  infoBoxText: { fontSize: FontSize.sm, lineHeight: 20 },

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
});
