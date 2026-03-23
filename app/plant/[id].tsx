import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
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
  watering_freq_summer_days: number;
  watering_freq_winter_days: number;
  watering_demand: string;
  watering_soil_hint: string;
  watering_warning: string;
  watering_method: string;
  watering_avoid: string;
  edible: boolean;
  edible_parts: string;
  poisonous_to_pets: boolean;
  poisonous_to_humans: boolean;
  toxicity_note: string;
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
        harvest_info: lib?.harvest_info ?? '',
        lifecycle_years: lib?.lifecycle_years ?? '',
        used_for: lib?.used_for ?? [],
        watering_freq_summer_days: lib?.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib?.watering_freq_winter_days ?? 14,
        watering_demand: lib?.watering_demand ?? '',
        watering_soil_hint: lib?.watering_soil_hint ?? '',
        watering_warning: lib?.watering_warning ?? '',
        watering_method: lib?.watering_method ?? '',
        watering_avoid: lib?.watering_avoid ?? '',
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
        harvest_info: lib?.harvest_info ?? '',
        lifecycle_years: lib?.lifecycle_years ?? '',
        used_for: lib?.used_for ?? [],
        watering_freq_summer_days: lib?.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib?.watering_freq_winter_days ?? 14,
        watering_demand: lib?.watering_demand ?? '',
        watering_soil_hint: lib?.watering_soil_hint ?? '',
        watering_warning: lib?.watering_warning ?? '',
        watering_method: lib?.watering_method ?? '',
        watering_avoid: lib?.watering_avoid ?? '',
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
        harvest_info: lib.harvest_info ?? '',
        lifecycle_years: lib.lifecycle_years ?? '',
        used_for: lib.used_for ?? [],
        watering_freq_summer_days: lib.watering_freq_summer_days ?? 7,
        watering_freq_winter_days: lib.watering_freq_winter_days ?? 14,
        watering_demand: lib.watering_demand ?? '',
        watering_soil_hint: lib.watering_soil_hint ?? '',
        watering_warning: lib.watering_warning ?? '',
        watering_method: lib.watering_method ?? '',
        watering_avoid: lib.watering_avoid ?? '',
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
  | 'water' | 'light' | 'humidity' | 'temperature' | 'toxicity'
  | 'lifecycle' | 'used_for' | 'soil' | 'fertilizing'
  | 'difficulty' | 'size' | 'taxonomy';

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
    { key: 'toxicity', label: 'Toxicity' },
    { key: 'lifecycle', label: 'Lifecycle' },
    { key: 'used_for', label: 'Used for' },
    { key: 'soil', label: 'Soil' },
    { key: 'fertilizing', label: 'Fertilizing' },
    { key: 'difficulty', label: 'Difficulty' },
    { key: 'size', label: 'Size' },
    { key: 'taxonomy', label: 'Taxonomy' },
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
  const seasonCoeff = [2.0, 1.8, 1.5, 1.2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.5, 1.8][monthIndex];
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
            <InfoRow icon="water-outline" text={`~${currentWateringDays} days in ${currentMonth}`} sub={plant.watering_demand ? `${plant.watering_soil_hint} \u2022 ${plant.watering_demand} demand` : care.watering} />
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
            <TouchableOpacity onPress={() => setShowWateringGuide(!showWateringGuide)} style={styles.guideBtn}>
              <Text style={styles.guideBtnText}>Watering guide</Text>
              <Ionicons name={showWateringGuide ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.primary} />
            </TouchableOpacity>
            {showWateringGuide && (
              <View style={styles.guideContent}>
                <Text style={styles.guideSectionTitle}>Recommended method</Text>
                <Text style={styles.bodyText}>{plant.watering_method || care.watering}</Text>
                {plant.watering_avoid ? (
                  <>
                    <Text style={styles.guideSectionTitle}>What to avoid</Text>
                    <InfoBox text={plant.watering_avoid} variant="warning" />
                  </>
                ) : null}
                <InfoBox text="Make sure your pot has drainage holes. Without drainage, water collects at the bottom and roots rot." variant="info" />
              </View>
            )}
          </View>

          {/* ── 2. Light ── */}
          <View onLayout={(e) => onSectionLayout('light', e)} style={styles.sectionCard}>
            <SectionTitle text="Light" />
            <InfoRow icon="sunny-outline" text={care.light} sub="Preferred" />
            <InfoRow icon="partly-sunny-outline" text={care.light_also_ok} sub="Also tolerates" />
            {care.light.includes('Full') || care.light.includes('Bright') ? (
              <InfoBox text="Without enough light this plant will stretch, lose color, and eventually die. In northern regions (Oct\u2013Mar), consider a grow light." variant="warning" />
            ) : care.light.includes('indirect') ? (
              <InfoBox text="Avoid direct sun \u2014 leaves can burn. A spot near a window with filtered light works best." variant="info" />
            ) : (
              <InfoBox text="Low-light tolerant, but growth will slow significantly in very dark spots." variant="info" />
            )}
          </View>

          {/* ── 3. Air Humidity ── */}
          <View onLayout={(e) => onSectionLayout('humidity', e)} style={styles.sectionCard}>
            <SectionTitle text="Air Humidity" />
            <InfoRow icon="cloud-outline" text={care.humidity} sub="Air humidity level" />
            {care.humidity_action ? (
              <InfoBox text={care.humidity_action} variant="info" />
            ) : null}
          </View>

          {/* ── 4. Air Temperature ── */}
          <View onLayout={(e) => onSectionLayout('temperature', e)} style={styles.sectionCard}>
            <SectionTitle text="Air Temperature" />
            <InfoRow icon="thermometer-outline" text={care.temperature} sub="Recommended range" />
          </View>

          {/* ── 5. Toxicity ── */}
          <View onLayout={(e) => onSectionLayout('toxicity', e)} style={styles.sectionCard}>
            <SectionTitle text="Toxicity" />
            {isToxic ? (
              <>
                <InfoRow icon="alert-circle" text="Toxic" iconColor={Colors.error} />
                <Text style={styles.bodyText}>Toxic to:</Text>
                <View style={styles.chipRow}>
                  {plant.poisonous_to_humans && <View style={styles.chip}><Text style={styles.chipText}>Humans</Text></View>}
                  {plant.poisonous_to_pets && <View style={styles.chip}><Text style={styles.chipText}>Animals</Text></View>}
                </View>
                {plant.edible && plant.edible_parts ? (
                  <InfoRow icon="nutrition-outline" text={plant.edible_parts} sub="Edible parts" iconColor={Colors.success} />
                ) : null}
                {plant.toxicity_note ? (
                  <InfoBox text={plant.toxicity_note} variant="warning" />
                ) : (
                  <InfoBox text="Toxic according to different sources, use this information at your own risk." variant="warning" />
                )}
              </>
            ) : (
              <>
                <InfoRow icon="checkmark-circle" text="Not toxic" iconColor={Colors.success} />
                <InfoBox text="This plant is considered non-toxic to humans and pets." variant="success" />
              </>
            )}
          </View>

          {/* ── 6. Lifecycle ── */}
          <View onLayout={(e) => onSectionLayout('lifecycle', e)} style={styles.sectionCard}>
            <SectionTitle text="Lifecycle" />
            <InfoRow icon="sync-outline" text={plant.lifecycle === 'perennial' ? 'Perennial' : plant.lifecycle === 'annual' ? 'Annual' : plant.lifecycle || 'Unknown'} sub={plant.lifecycle_years ? (plant.lifecycle === 'perennial' ? `Lives ${plant.lifecycle_years} years` : `${plant.lifecycle_years}`) : (plant.lifecycle === 'perennial' ? 'Lives for multiple years' : 'One growing season')} />
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
          </View>

          {/* ── 8. Soil ── */}
          <View onLayout={(e) => onSectionLayout('soil', e)} style={styles.sectionCard}>
            <SectionTitle text="Soil" />
            <InfoRow icon="layers-outline" text={care.soil} sub="Soil mix" />
            {plant.soil_ph_min != null && plant.soil_ph_min > 0 && (
              <InfoRow icon="flask-outline" text={`pH ${plant.soil_ph_min} \u2013 ${plant.soil_ph_max}`} sub="Soil acidity" />
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
              <InfoBox text="Forgiving plant \u2014 tolerates irregular watering, adapts to various light conditions. Great for beginners." variant="success" />
            ) : plant.difficulty === 'Advanced' ? (
              <InfoBox text="Needs precise humidity, consistent watering schedule, and specific light conditions. Not forgiving of mistakes." variant="warning" />
            ) : (
              <InfoBox text="Needs some attention \u2014 regular watering and decent light, but recovers from occasional neglect." variant="info" />
            )}
          </View>

          {/* ── 11. Size ── */}
          <View onLayout={(e) => onSectionLayout('size', e)} style={styles.sectionCard}>
            <SectionTitle text="Size" />
            <InfoRow icon="arrow-up-outline" text={plant.height_max_cm > 0 ? `Up to ${plant.height_max_cm} cm (${Math.round(plant.height_max_cm / 2.54)}\u2033)` : 'Not specified'} sub="Max height (full grown)" />
            <InfoRow icon="trending-up-outline" text={plant.growth_rate || 'Not specified'} sub="Growth rate" />
            {plant.height_max_cm > 100 ? (
              <InfoBox text={`In a pot, expect much less than ${plant.height_max_cm} cm. Pot size limits root growth which limits height.`} variant="info" />
            ) : plant.height_max_cm > 0 ? (
              <InfoBox text="Pot size directly affects final size. Bigger pot = bigger plant. Repot when roots circle the bottom." variant="info" />
            ) : null}
          </View>

          {/* ── 12. Taxonomy ── */}
          <View onLayout={(e) => onSectionLayout('taxonomy', e)} style={styles.sectionCard}>
            <SectionTitle text="Taxonomy" />
            <InfoRow icon="document-text-outline" text={plant.scientific} sub="Scientific name" />
            <InfoRow icon="git-branch-outline" text={plant.family} sub="Family" />
            {plant.common_name ? (
              <InfoRow icon="globe-outline" text={plant.common_name} sub="Common name" />
            ) : null}
          </View>

        </View>
      </ScrollView>
    </>
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
  guideBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs, paddingVertical: Spacing.sm, marginTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border },
  guideBtnText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.primary },
  guideContent: { marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  guideSectionTitle: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.text, marginBottom: Spacing.sm, marginTop: Spacing.sm },

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
