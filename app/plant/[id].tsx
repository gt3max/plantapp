import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
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
import type { PresetCare } from '../../src/constants/presets';

// ─── Build plant view model from either source ───────────────────────

interface PlantVM {
  scientific: string;
  common_name: string;
  family: string;
  preset: string;
  plant_type: 'decorative' | 'greens' | 'fruiting';
  image_url?: string;
  poisonous_to_pets: boolean;
  poisonous_to_humans: boolean;
  toxicity_note: string;
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
}

function usePlantVM(id: string | undefined): PlantVM | null {
  const { plants } = usePlantsWithDevices();

  return useMemo(() => {
    if (!id) return null;

    const userPlant = plants.find((p) => p.plant_id === id);
    if (userPlant) {
      const care = PRESET_CARE[userPlant.preset ?? 'Standard'] ?? PRESET_CARE.Standard;
      return {
        scientific: userPlant.scientific ?? '',
        common_name: userPlant.common_name ?? '',
        family: userPlant.family ?? '',
        preset: userPlant.preset ?? 'Standard',
        plant_type: 'decorative' as const,
        image_url: userPlant.image_url,
        poisonous_to_pets: userPlant.poisonous_to_pets ?? false,
        poisonous_to_humans: userPlant.poisonous_to_humans ?? false,
        toxicity_note: userPlant.toxicity_note ?? '',
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
      };
    }

    const lib = POPULAR_PLANTS.find((p) => p.id === id);
    if (lib) {
      const care = PRESET_CARE[lib.preset] ?? PRESET_CARE.Standard;
      return {
        scientific: lib.scientific,
        common_name: lib.common_name,
        family: lib.family,
        preset: lib.preset,
        plant_type: lib.plant_type,
        image_url: lib.image_url,
        poisonous_to_pets: lib.poisonous_to_pets,
        poisonous_to_humans: lib.poisonous_to_humans,
        toxicity_note: lib.toxicity_note,
        care,
        hasDevice: false,
        start_pct: care.start_pct,
        stop_pct: care.stop_pct,
      };
    }

    return null;
  }, [id, plants]);
}

// ─── Screen ──────────────────────────────────────────────────────────

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [level2Open, setLevel2Open] = useState(false);
  const plant = usePlantVM(id);

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

  return (
    <>
      <Stack.Screen options={{ title }} />
      <ScrollView style={styles.container} contentContainerStyle={styles.scroll}>

        {/* ═══ #1 IDENTIFICATION ═══ (hero + names + tags) */}
        {plant.image_url ? (
          <Image source={{ uri: plant.image_url }} style={styles.heroImage} />
        ) : (
          <View style={[styles.heroImage, styles.heroPlaceholder]}>
            <Ionicons name="leaf" size={64} color={Colors.accent} />
          </View>
        )}

        <View style={styles.nameSection}>
          <Text style={styles.scientificName}>{plant.scientific}</Text>
          {plant.common_name ? (
            <Text style={styles.commonName}>{plant.common_name}</Text>
          ) : null}
          <Text style={styles.familyLine}>
            {plant.family} {'\u00B7'} {plant.preset}
          </Text>
        </View>

        {/* Quick tags (like Planta but better) */}
        <View style={styles.tagRow}>
          <Badge text={care.light.split(',')[0]} variant="neutral" size="md" />
          <Badge text={care.humidity.split(' ')[0]} variant="info" size="md" />
          {isToxic ? (
            <Badge text="Toxic" variant="error" size="md" />
          ) : (
            <Badge text="Pet Safe" variant="success" size="md" />
          )}
          {plant.plant_type === 'greens' && (
            <Badge text="Edible" variant="success" size="md" />
          )}
          {plant.plant_type === 'fruiting' && (
            <Badge text="Fruiting" variant="warning" size="md" />
          )}
        </View>

        {/* ═══ #2 WATERING ═══ */}
        <CareCard
          icon="water"
          iconBg="#EBF5FF"
          iconColor={Colors.moisture}
          title="Watering"
          subtitle={care.watering}
        >
          <ActionHint
            text={
              plant.hasDevice
                ? 'Polivalka waters automatically based on sensor data'
                : 'Water when top layer of soil feels dry to the touch'
            }
          />
          <View style={styles.detailGrid}>
            <DetailCell label="Target moisture" value={`${plant.start_pct}-${plant.stop_pct}%`} />
            <DetailCell label="Winter" value={care.watering_winter} />
          </View>

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

        {/* ═══ #3 LIGHT + PPFD ═══ */}
        <CareCard
          icon="sunny"
          iconBg="#FFF8E1"
          iconColor="#F59E0B"
          title="Light"
          subtitle={care.light}
        >
          <ActionHint
            text={
              care.light.toLowerCase().includes('full sun')
                ? 'Place on a sunny windowsill or balcony (6+ hours direct sun)'
                : care.light.toLowerCase().includes('no direct')
                  ? 'Place near a window with filtered sunlight, avoid direct rays'
                  : 'Keep in a well-lit room with bright indirect light'
            }
          />
          <Text style={styles.alsoOkText}>Also OK: {care.light_also_ok}</Text>

          {/* PPFD / DLI — our unique data, Planta doesn't have this */}
          <View style={styles.ppfdSection}>
            <View style={styles.ppfdHeader}>
              <Ionicons name="flash-outline" size={14} color={Colors.primary} />
              <Text style={styles.ppfdTitle}>Light intensity (PPFD / DLI)</Text>
            </View>
            <View style={styles.detailGrid}>
              <DetailCell
                label="PPFD"
                value={`${care.ppfd_min}-${care.ppfd_max} \u00B5mol/m\u00B2/s`}
              />
              <DetailCell
                label="DLI"
                value={`${care.dli_min}-${care.dli_max} mol/m\u00B2/day`}
              />
            </View>
            <Text style={styles.ppfdHint}>
              Use phone camera light meter to check (coming soon)
            </Text>
          </View>

          {/* Greens: light spectrum info */}
          {plant.plant_type === 'greens' && (
            <View style={styles.spectrumBlock}>
              <Ionicons name="color-wand-outline" size={14} color={Colors.primary} />
              <Text style={styles.spectrumText}>
                Optimal spectrum: blue + white (vegetative growth, leafy mass)
              </Text>
            </View>
          )}

          {/* Fruiting: spectrum changes by phase */}
          {plant.plant_type === 'fruiting' && (
            <View style={styles.spectrumBlock}>
              <Ionicons name="color-wand-outline" size={14} color={Colors.primary} />
              <Text style={styles.spectrumText}>
                Spectrum changes by phase: blue (seedling) → balanced (vegetative) → red (flowering/fruiting)
              </Text>
            </View>
          )}
        </CareCard>

        {/* ═══ #4 TOXICITY ═══ */}
        <CareCard
          icon={isToxic ? 'warning' : 'checkmark-circle'}
          iconBg={isToxic ? '#FEE2E2' : '#DCFCE7'}
          iconColor={isToxic ? Colors.error : Colors.success}
          title="Toxicity"
          subtitle={
            isToxic
              ? plant.poisonous_to_pets && plant.poisonous_to_humans
                ? 'Toxic to pets and humans'
                : plant.poisonous_to_pets
                  ? 'Toxic to pets'
                  : 'Toxic to humans'
              : 'Non-toxic'
          }
          cardStyle={isToxic ? styles.toxicCard : undefined}
        >
          {isToxic ? (
            <>
              {plant.toxicity_note ? (
                <Text style={styles.toxDetail}>{plant.toxicity_note}</Text>
              ) : null}
              <ActionHint
                text="Keep away from pets and children. Wash hands after handling."
                color={Colors.error}
              />
            </>
          ) : (
            <ActionHint
              text="Safe for pets and children. No special precautions needed."
              color={Colors.success}
            />
          )}
        </CareCard>

        {/* ═══ #5 PROBLEMS & PESTS ═══ */}
        <CareCard
          icon="medkit-outline"
          iconBg="#FFF3E0"
          iconColor="#E65100"
          title="Common Problems"
          subtitle={`${care.common_problems.length} issues · ${care.common_pests.length} pests`}
        >
          {care.common_problems.map((p, i) => (
            <View key={i} style={styles.problemRow}>
              <Ionicons name="alert-circle" size={14} color={Colors.warning} />
              <Text style={styles.problemText}>{p}</Text>
            </View>
          ))}

          <Text style={styles.pestSectionTitle}>Common Pests</Text>
          <View style={styles.pestRow}>
            {care.common_pests.map((p, i) => (
              <Badge key={i} text={p} variant="warning" size="sm" />
            ))}
          </View>
        </CareCard>

        {/* ═══ Greens: Harvest block ═══ */}
        {plant.plant_type === 'greens' && (
          <CareCard
            icon="nutrition-outline"
            iconBg="#E8F5E9"
            iconColor={Colors.success}
            title="Harvesting"
            subtitle="Harvest regularly for best flavor"
          >
            <ActionHint text="Pick outer leaves first, leaving the center to grow. Harvest in the morning for best flavor." />
            <View style={styles.spectrumBlock}>
              <Ionicons name="flask-outline" size={14} color={Colors.primary} />
              <Text style={styles.spectrumText}>
                Fertilizer focus: nitrogen (N) for leafy growth
              </Text>
            </View>
          </CareCard>
        )}

        {/* ═══ Fruiting: Harvest + Phases block ═══ */}
        {plant.plant_type === 'fruiting' && (
          <CareCard
            icon="nutrition-outline"
            iconBg="#FFF8E1"
            iconColor="#F59E0B"
            title="Growth Phases"
            subtitle="Care changes by growth phase"
          >
            <Text style={styles.phaseNote}>
              Fruiting plants have distinct phases with different watering, light, and fertilizer needs.
            </Text>
            {['Seedling', 'Vegetative', 'Flowering', 'Fruiting', 'Dormancy'].map((phase, i) => (
              <View key={i} style={styles.phaseRow}>
                <View style={[styles.phaseDot, i <= 3 && { backgroundColor: Colors.accent }]} />
                <Text style={styles.phaseText}>{phase}</Text>
              </View>
            ))}
            <Text style={styles.ppfdHint}>
              Phase-specific care recommendations coming soon
            </Text>
          </CareCard>
        )}

        {/* ═══ LEVEL 2 Toggle ═══ */}
        <TouchableOpacity
          activeOpacity={0.7}
          onPress={() => setLevel2Open(!level2Open)}
          style={styles.level2Toggle}
        >
          <Ionicons
            name={level2Open ? 'chevron-up' : 'chevron-down'}
            size={20}
            color={Colors.primary}
          />
          <Text style={styles.level2ToggleText}>
            {level2Open ? 'Hide Advanced Care' : 'Advanced Care Guide'}
          </Text>
        </TouchableOpacity>

        {/* ═══ LEVEL 2: #6-10 ═══ */}
        {level2Open && (
          <View style={styles.level2Container}>
            {/* #6 Temperature */}
            <Level2Row icon="thermometer-outline" title="Temperature" value={care.temperature}>
              <Text style={styles.l2Action}>
                Avoid cold drafts and sudden temperature changes. Keep away from AC vents.
              </Text>
            </Level2Row>

            {/* #7 Humidity */}
            <Level2Row icon="water-outline" title="Humidity" value={care.humidity}>
              <Text style={styles.l2Action}>{care.humidity_action}</Text>
            </Level2Row>

            {/* #8 Soil & Repotting */}
            <Level2Row icon="layers-outline" title="Soil & Repotting" value={care.soil}>
              <Text style={styles.l2Action}>Repot: {care.repot}. Use a pot with drainage holes.</Text>
            </Level2Row>

            {/* #9 Fertilizing */}
            <Level2Row icon="flask-outline" title="Fertilizing" value={care.fertilizer}>
              <Text style={styles.l2Action}>
                Season: {care.fertilizer_season}. Use balanced liquid fertilizer at half strength. Stop in winter.
              </Text>
            </Level2Row>

            {/* #10 Tips */}
            {care.tips ? (
              <Level2Row icon="bulb-outline" title="Pro Tips" value={care.tips} />
            ) : null}
          </View>
        )}

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
  cardStyle?: object;
}) {
  return (
    <Card style={[styles.careCard, cardStyle]}>
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
    <View style={[styles.actionRow, { backgroundColor: color ? `${c}10` : '#F0FFF4' }]}>
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

function Level2Row({
  icon,
  title,
  value,
  children,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <View style={styles.l2Card}>
      <View style={styles.l2Header}>
        <Ionicons name={icon} size={18} color={Colors.textSecondary} />
        <Text style={styles.l2Title}>{title}</Text>
      </View>
      <Text style={styles.l2Value}>{value}</Text>
      {children}
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

  // #1 Identification
  heroImage: { width: '100%', height: 280 },
  heroPlaceholder: { backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center' },
  nameSection: { padding: Spacing.lg, paddingBottom: Spacing.sm },
  scientificName: { fontSize: FontSize.xxl, fontWeight: '700', color: Colors.text, fontStyle: 'italic' },
  commonName: { fontSize: FontSize.lg, color: Colors.textSecondary, marginTop: 2 },
  familyLine: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: Spacing.xs },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, paddingHorizontal: Spacing.lg, marginBottom: Spacing.xl },

  // Care cards
  careCard: { marginHorizontal: Spacing.lg, marginBottom: Spacing.md },
  toxicCard: { borderLeftWidth: 3, borderLeftColor: Colors.error },
  careIconRow: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.md },
  careIconCircle: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: Spacing.md },
  careHeaderText: { flex: 1 },
  careTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },
  careSubtitle: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: 1 },

  // Action hints
  actionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm, borderRadius: BorderRadius.md, padding: Spacing.md, marginTop: Spacing.sm },
  actionText: { flex: 1, fontSize: FontSize.sm, lineHeight: 18 },

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

  // Light — PPFD
  alsoOkText: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: Spacing.sm },
  ppfdSection: { marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  ppfdHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, marginBottom: Spacing.sm },
  ppfdTitle: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.primary },
  ppfdHint: { fontSize: FontSize.xs, color: Colors.textSecondary, fontStyle: 'italic', marginTop: Spacing.sm },

  // Spectrum (greens/fruiting)
  spectrumBlock: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm, marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  spectrumText: { flex: 1, fontSize: FontSize.sm, color: Colors.primary, lineHeight: 18 },

  // Toxicity
  toxDetail: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 18, marginBottom: Spacing.xs },

  // Problems & Pests
  problemRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.sm },
  problemText: { flex: 1, fontSize: FontSize.sm, color: Colors.text },
  pestSectionTitle: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textSecondary, marginTop: Spacing.lg, marginBottom: Spacing.sm },
  pestRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },

  // Phases (fruiting)
  phaseNote: { fontSize: FontSize.sm, color: Colors.textSecondary, lineHeight: 18, marginBottom: Spacing.md },
  phaseRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: 4 },
  phaseDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: Colors.border },
  phaseText: { fontSize: FontSize.sm, color: Colors.text },

  // Level 2 toggle
  level2Toggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs, paddingVertical: Spacing.lg, marginHorizontal: Spacing.lg, borderTopWidth: 1, borderTopColor: Colors.border, marginTop: Spacing.sm },
  level2ToggleText: { fontSize: FontSize.md, color: Colors.primary, fontWeight: '600' },

  // Level 2 rows
  level2Container: { paddingHorizontal: Spacing.lg },
  l2Card: { paddingVertical: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  l2Header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.xs },
  l2Title: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textSecondary },
  l2Value: { fontSize: FontSize.md, color: Colors.text, lineHeight: 20 },
  l2Action: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: Spacing.xs, lineHeight: 18 },

  // Device
  batteryRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.sm, paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border },
  batteryText: { fontSize: FontSize.sm, color: Colors.text },
  chargingText: { fontSize: FontSize.xs, color: Colors.success },
  viewDeviceBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs, marginTop: Spacing.md, paddingTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border },
  viewDeviceBtnText: { fontSize: FontSize.md, color: Colors.primary, fontWeight: '600' },
});
