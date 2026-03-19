import React, { useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../src/components/ui/Card';
import { Badge } from '../../src/components/ui/Badge';
import { ProgressBar } from '../../src/components/ui/ProgressBar';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { POPULAR_PLANTS } from '../../src/constants/popular-plants';
import { PRESET_CARE } from '../../src/constants/presets';
import { usePlantsWithDevices } from '../../src/features/plants/api/plants-api';
import { usePlantDBDetail } from '../../src/features/plants/api/plant-db-api';
import { dbCareToPresetCare, getCommonName } from '../../src/lib/plant-db-adapter';
import type { PresetCare } from '../../src/constants/presets';

// ─── Build plant view model from either source ───────────────────────

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
  height_max_cm: number;
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

    // Priority 1: User's own plant (from DynamoDB library)
    const userPlant = plants.find((p) => p.plant_id === id);
    if (userPlant) {
      const presetCare = PRESET_CARE[userPlant.preset ?? 'Standard'] ?? PRESET_CARE.Standard;
      const care = dbEntry?.care
        ? dbCareToPresetCare(dbEntry.care, presetCare)
        : presetCare;
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

    // Priority 2: Turso DB (per-species encyclopedia)
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
        care,
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
        soil_ph_min: dbEntry.care?.soil_ph_min,
        soil_ph_max: dbEntry.care?.soil_ph_max,
      };
    }

    // Priority 3: Hardcoded popular plants (offline fallback)
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
        care,
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
      };
    }

    return null;
  }, [id, plants, dbEntry]);
}

// ─── Screen ──────────────────────────────────────────────────────────

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);
  const plant = usePlantVM(id);

  // Section refs for badge tapping
  const [toxicityY, setToxicityY] = useState(0);
  const [harvestY, setHarvestY] = useState(0);

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

  // Difficulty color
  const difficultyVariant = plant.difficulty === 'Advanced' ? 'error'
    : plant.difficulty === 'Medium' ? 'warning' : 'success';

  // Water demand level from care
  const waterLevel = care.watering.toLowerCase().includes('2-3 week') ? 'Low'
    : care.watering.toLowerCase().includes('7-10') ? 'Medium'
    : 'High';

  const scrollToSection = (y: number) => {
    scrollRef.current?.scrollTo({ y, animated: true });
  };

  return (
    <>
      <Stack.Screen options={{ title }} />
      <ScrollView ref={scrollRef} style={styles.container} contentContainerStyle={styles.scroll}>

        {/* ═══ HERO IMAGE ═══ */}
        {plant.image_url ? (
          <Image source={{ uri: plant.image_url }} style={styles.heroImage} />
        ) : (
          <View style={[styles.heroImage, styles.heroPlaceholder]}>
            <Ionicons name="leaf" size={64} color={Colors.accent} />
          </View>
        )}

        {/* ═══ NAME SECTION ═══ */}
        <View style={styles.nameSection}>
          <Text style={styles.commonNameBig}>{plant.common_name || plant.scientific}</Text>
          {plant.common_name ? (
            <Text style={styles.scientificName}>{plant.scientific}</Text>
          ) : null}
          <Text style={styles.familyLine}>
            {plant.family} {'\u00B7'} {plant.preset}
          </Text>
        </View>

        {/* ═══ BADGES ROW (tappable) ═══ */}
        <View style={styles.tagRow}>
          {plant.difficulty ? (
            <Badge text={plant.difficulty} variant={difficultyVariant} size="md" />
          ) : null}
          {isToxic ? (
            <TouchableOpacity onPress={() => scrollToSection(toxicityY)}>
              <Badge text="Toxic" variant="error" size="md" />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity onPress={() => scrollToSection(toxicityY)}>
              <Badge text="Pet Safe" variant="success" size="md" />
            </TouchableOpacity>
          )}
          {plant.edible && (
            <TouchableOpacity onPress={() => scrollToSection(harvestY)}>
              <Badge text={plant.edible_parts ? `Edible: ${plant.edible_parts}` : 'Edible'} variant="success" size="md" />
            </TouchableOpacity>
          )}
          <Badge text={`Water: ${waterLevel}`} variant="info" size="md" />
          {plant.lifecycle ? (
            <Badge text={plant.lifecycle} variant="neutral" size="md" />
          ) : null}
        </View>

        {/* ═══ DESCRIPTION (no card wrapper, clean text) ═══ */}
        {plant.description ? (
          <View style={styles.descriptionSection}>
            <Text style={styles.descriptionText}>{plant.description}</Text>
            {plant.difficulty_note ? (
              <Text style={styles.difficultyNote}>{plant.difficulty_note}</Text>
            ) : null}
            <View style={styles.detailGrid}>
              {plant.difficulty ? (
                <DetailCell label="Difficulty" value={plant.difficulty} />
              ) : null}
              {plant.growth_rate ? (
                <DetailCell label="Growth" value={plant.growth_rate} />
              ) : null}
              {plant.height_max_cm > 0 ? (
                <DetailCell label="Height" value={`up to ${plant.height_max_cm} cm`} />
              ) : null}
              {plant.lifecycle ? (
                <DetailCell label="Lifecycle" value={plant.lifecycle} />
              ) : null}
            </View>
          </View>
        ) : null}

        {/* ═══ LEVEL 1: #2 CARE ═══ */}
        <CareCard
          icon="water"
          iconBg="#EBF5FF"
          iconColor={Colors.moisture}
          title="Care"
          subtitle={care.watering}
        >
          {/* Water */}
          <Text style={styles.careSection}>Water</Text>
          <ActionHint
            text={
              plant.hasDevice
                ? 'Polivalka waters automatically based on sensor data'
                : 'Water when top layer of soil feels dry to the touch'
            }
          />
          <View style={styles.detailGrid}>
            <DetailCell label="Summer" value={care.watering} />
            <DetailCell label="Winter" value={care.watering_winter} />
          </View>

          {/* Light */}
          <Text style={styles.careSection}>Light</Text>
          <View style={styles.detailGrid}>
            <DetailCell label="Preferred" value={care.light} />
            <DetailCell label="Also OK" value={care.light_also_ok} />
          </View>

          {/* Soil & Pot */}
          <Text style={styles.careSection}>Soil & Pot</Text>
          <View style={styles.detailGrid}>
            <DetailCell label="Soil" value={care.soil} />
            <DetailCell label="Repot" value={care.repot} />
          </View>

          {/* Fertilizer */}
          <Text style={styles.careSection}>Fertilizer</Text>
          <View style={styles.detailGrid}>
            <DetailCell label="Type" value={care.fertilizer} />
            <DetailCell label="Season" value={care.fertilizer_season} />
          </View>

          {/* Warnings from tips */}
          {care.tips ? (
            <ActionHint text={care.tips} color={Colors.warning} />
          ) : null}

          {/* Live moisture from device */}
          {plant.hasDevice && plant.moisture_pct != null && (
            <View style={styles.liveData}>
              <View style={styles.liveHeader}>
                <View style={styles.liveDot} />
                <Text style={styles.liveLabel}>Live sensor</Text>
                <Text style={styles.liveValue}>{plant.moisture_pct}%</Text>
              </View>
              <ProgressBar value={plant.moisture_pct} color={Colors.moisture} />
            </View>
          )}
        </CareCard>

        {/* ═══ LEVEL 1: #3 TOXICITY / SAFETY ═══ */}
        <View onLayout={(e) => setToxicityY(e.nativeEvent.layout.y)}>
          <CareCard
            icon={isToxic ? 'warning' : 'checkmark-circle'}
            iconBg={isToxic ? '#FEE2E2' : '#DCFCE7'}
            iconColor={isToxic ? Colors.error : Colors.success}
            title={plant.edible ? 'Safety & Edibility' : 'Toxicity'}
            subtitle={
              isToxic && plant.edible
                ? 'Parts toxic, parts edible — read carefully'
                : isToxic
                  ? plant.poisonous_to_pets && plant.poisonous_to_humans
                    ? 'Toxic to pets and humans'
                    : plant.poisonous_to_pets
                      ? 'Toxic to pets'
                      : 'Toxic to humans'
                  : plant.edible
                    ? 'Safe and edible'
                    : 'Non-toxic'
            }
            cardStyle={isToxic ? styles.toxicCard : undefined}
          >
            {/* Edible info first for edible plants */}
            {plant.edible && (
              <View style={styles.safetyRow}>
                <Ionicons name="checkmark-circle" size={16} color={Colors.success} />
                <Text style={[styles.safetyText, { color: Colors.success }]}>
                  {plant.edible_parts ? `Edible parts: ${plant.edible_parts}` : 'Edible'}
                </Text>
              </View>
            )}
            {/* Toxic info */}
            {isToxic && (
              <>
                <View style={styles.safetyRow}>
                  <Ionicons name="warning" size={16} color={Colors.error} />
                  <Text style={[styles.safetyText, { color: Colors.error }]}>
                    {plant.toxicity_note || 'Toxic — keep away from pets and children'}
                  </Text>
                </View>
                <ActionHint
                  text="Wash hands after handling. Keep away from pets and children."
                  color={Colors.error}
                />
              </>
            )}
            {!isToxic && !plant.edible && (
              <ActionHint
                text="Safe for pets and children. No special precautions needed."
                color={Colors.success}
              />
            )}
          </CareCard>
        </View>

        {/* ═══ LEVEL 1: #4 HARVEST (greens + fruiting only) ═══ */}
        {(plant.plant_type === 'greens' || plant.plant_type === 'fruiting') && (
          <View onLayout={(e) => setHarvestY(e.nativeEvent.layout.y)}>
            <CareCard
              icon="nutrition-outline"
              iconBg="#E8F5E9"
              iconColor={Colors.success}
              title="Harvest"
              subtitle={plant.plant_type === 'fruiting' ? 'When and how to pick' : 'When and how to harvest'}
            >
              {plant.harvest_info ? (
                <Text style={styles.aboutText}>{plant.harvest_info}</Text>
              ) : (
                <Text style={styles.aboutText}>
                  {plant.plant_type === 'greens'
                    ? 'Harvest outer leaves first, leaving the center to grow. Pick in the morning for best flavor.'
                    : 'Pick fruit when fully colored and slightly soft to touch. Check daily during ripening.'}
                </Text>
              )}
            </CareCard>
          </View>
        )}

        {/* ═══ LIGHT ═══ */}
        <CareCard
          icon="sunny-outline"
          iconBg="#FFF8E1"
          iconColor="#F59E0B"
          title="Light"
          subtitle={care.light}
        >
          <View style={styles.detailGrid}>
            <DetailCell label="Preferred" value={care.light} />
            <DetailCell label="Also OK" value={care.light_also_ok} />
          </View>
          <View style={styles.detailGrid}>
            <DetailCell label="PPFD" value={`${care.ppfd_min}-${care.ppfd_max} µmol/m²/s`} />
            <DetailCell label="DLI" value={`${care.dli_min}-${care.dli_max} mol/m²/day`} />
          </View>
          {plant.plant_type === 'greens' && (
            <ActionHint text="Spectrum: blue + white for leafy growth" />
          )}
          {plant.plant_type === 'fruiting' && (
            <ActionHint text="Spectrum by phase: blue (seedling) → balanced (veg) → red (flowering/fruit)" />
          )}
        </CareCard>

        {/* ═══ ENVIRONMENT ═══ */}
        <CareCard
          icon="thermometer-outline"
          iconBg="#FFF3E0"
          iconColor="#E65100"
          title="Environment"
          subtitle={care.temperature}
        >
          <View style={styles.detailGrid}>
            <DetailCell label="Temperature" value={care.temperature} />
            <DetailCell label="Air Humidity" value={care.humidity} />
          </View>
          {care.humidity_action ? (
            <ActionHint text={care.humidity_action} />
          ) : null}
          {plant.soil_ph_min != null && plant.soil_ph_max != null && plant.soil_ph_min > 0 && (
            <View style={styles.detailGrid}>
              <DetailCell label="Soil pH" value={`${plant.soil_ph_min} - ${plant.soil_ph_max}`} />
            </View>
          )}
        </CareCard>

        {/* ═══ SENSOR SETTINGS (if relevant) ═══ */}
        <CareCard
          icon="speedometer-outline"
          iconBg="#E3F2FD"
          iconColor="#1565C0"
          title="Sensor Settings"
          subtitle={`Start ${plant.start_pct}% / Stop ${plant.stop_pct}%`}
        >
          <View style={styles.detailGrid}>
            <DetailCell label="Start watering" value={`${plant.start_pct}%`} />
            <DetailCell label="Stop watering" value={`${plant.stop_pct}%`} />
          </View>
          <ActionHint text={`Preset: ${plant.preset}. Calibrate for your soil type.`} />
        </CareCard>

        {/* ═══ DEVICE (if attached) ═══ */}
        {plant.hasDevice && (
          <CareCard
            icon="cube-outline"
            iconBg="#E8F5E9"
            iconColor={Colors.primary}
            title={plant.device_id ?? 'Device'}
            subtitle={`${plant.device_online ? 'Online' : 'Offline'}${plant.device_mode ? ` \u00B7 ${plant.device_mode === 'sensor' ? 'Sensor' : plant.device_mode === 'timer' ? 'Timer' : 'Manual'} mode` : ''}`}
            cardStyle={{ marginTop: Spacing.lg }}
          >
            {plant.battery_pct != null && (
              <View style={styles.batteryRow}>
                <Ionicons
                  name={plant.battery_charging ? 'battery-charging' : 'battery-half'}
                  size={18}
                  color={Colors.battery}
                />
                <Text style={styles.batteryText}>Battery {plant.battery_pct}%</Text>
                {plant.battery_charging && (
                  <Text style={styles.chargingText}>Charging</Text>
                )}
              </View>
            )}
            <TouchableOpacity
              style={styles.viewDeviceBtn}
              onPress={() => router.push(`/device/${plant.device_id}`)}
            >
              <Text style={styles.viewDeviceBtnText}>View Device</Text>
              <Ionicons name="arrow-forward" size={14} color={Colors.primary} />
            </TouchableOpacity>
          </CareCard>
        )}
      </ScrollView>
    </>
  );
}

// ─── Reusable components ─────────────────────────────────────────────

function CareCard({
  icon,
  iconBg,
  iconColor,
  title,
  subtitle,
  children,
  cardStyle,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  iconBg: string;
  iconColor: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  cardStyle?: ViewStyle;
}) {
  return (
    <Card style={StyleSheet.flatten([styles.careCard, cardStyle])}>
      <View style={styles.careIconRow}>
        <View style={[styles.careIconCircle, { backgroundColor: iconBg }]}>
          <Ionicons name={icon} size={22} color={iconColor} />
        </View>
        <View style={styles.careHeaderText}>
          <Text style={styles.careTitle}>{title}</Text>
          <Text style={styles.careSubtitle}>{subtitle}</Text>
        </View>
      </View>
      {children}
    </Card>
  );
}

function ActionHint({ text, color }: { text: string; color?: string }) {
  const c = color ?? Colors.primary;
  return (
    <View style={[styles.actionRow, { backgroundColor: `${c}10` }]}>
      <Ionicons name="arrow-forward-circle" size={16} color={c} />
      <Text style={[styles.actionText, { color: c }]}>{text}</Text>
    </View>
  );
}

function DetailCell({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailCell}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}


// ─── Styles ──────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingBottom: 40 },

  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  notFoundText: { fontSize: FontSize.lg, color: Colors.textSecondary, marginTop: Spacing.md },
  backLink: { fontSize: FontSize.md, color: Colors.primary, marginTop: Spacing.lg },

  // Hero
  heroImage: { width: '100%', height: 280 },
  heroPlaceholder: { backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center' },
  nameSection: { padding: Spacing.lg, paddingBottom: Spacing.sm },
  commonNameBig: { fontSize: FontSize.xxl, fontWeight: '700', color: Colors.text },
  scientificName: { fontSize: FontSize.md, color: Colors.textSecondary, fontStyle: 'italic', marginTop: 2 },
  familyLine: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: Spacing.xs },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, paddingHorizontal: Spacing.lg, marginBottom: Spacing.xl },

  // Description (replaces About card)
  descriptionSection: { paddingHorizontal: Spacing.lg, marginBottom: Spacing.lg },
  descriptionText: { fontSize: FontSize.md, color: Colors.text, lineHeight: 22 },
  difficultyNote: { fontSize: FontSize.sm, color: Colors.textSecondary, lineHeight: 20, marginTop: Spacing.sm, fontStyle: 'italic' },
  aboutText: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20, marginBottom: Spacing.sm },

  // Care section headers
  careSection: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.textSecondary, marginTop: Spacing.lg, marginBottom: Spacing.xs },

  // Care cards
  careCard: { marginHorizontal: Spacing.lg, marginBottom: Spacing.md },
  toxicCard: { borderLeftWidth: 3, borderLeftColor: Colors.error },
  careIconRow: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.md },
  careIconCircle: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: Spacing.md },
  careHeaderText: { flex: 1 },
  careTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },
  careSubtitle: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: 1 },

  // Safety rows
  safetyRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm, marginTop: Spacing.sm },
  safetyText: { flex: 1, fontSize: FontSize.sm, lineHeight: 20 },

  // Action hints
  actionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm, borderRadius: BorderRadius.md, padding: Spacing.md, marginTop: Spacing.sm },
  actionText: { flex: 1, fontSize: FontSize.sm, lineHeight: 20 },

  // Detail grid
  detailGrid: { flexDirection: 'row', gap: Spacing.lg, marginTop: Spacing.sm },
  detailCell: { flex: 1 },
  detailLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, fontWeight: '600' },
  detailValue: { fontSize: FontSize.md, color: Colors.text, marginTop: 1 },

  // Live data
  liveData: { marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  liveHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.sm },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.success },
  liveLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, flex: 1 },
  liveValue: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },

  // Toxicity
  toxDetail: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20, marginBottom: Spacing.xs },

  // Device
  batteryRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.sm, paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border },
  batteryText: { fontSize: FontSize.sm, color: Colors.text },
  chargingText: { fontSize: FontSize.xs, color: Colors.success },
  viewDeviceBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs, marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  viewDeviceBtnText: { fontSize: FontSize.md, color: Colors.primary, fontWeight: '600' },
});
