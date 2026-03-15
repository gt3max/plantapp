import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { usePlantsWithDevices } from '../../src/features/plants/api/plants-api';
import { Button } from '../../src/components/ui/Button';
import { Card } from '../../src/components/ui/Card';
import { Badge } from '../../src/components/ui/Badge';
import { ProgressBar } from '../../src/components/ui/ProgressBar';
import { Colors, Spacing, FontSize } from '../../src/constants/colors';
import type { PlantWithDevice } from '../../src/types/plant';

function moistureColor(pct: number): string {
  if (pct < 20) return Colors.error;
  if (pct < 40) return Colors.warning;
  return Colors.accent;
}

function PlantCard({ plant }: { plant: PlantWithDevice }) {
  const router = useRouter();
  const name = plant.common_name || plant.scientific || 'Unknown plant';
  const moisture = plant.moisture_pct;
  const hasDevice = plant.active && plant.device_id;

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => {
        if (hasDevice) router.push(`/device/${plant.device_id}`);
      }}
    >
      <Card style={styles.plantCard}>
        {/* Plant info — primary */}
        <View style={styles.plantHeader}>
          <View style={styles.plantIconWrap}>
            <Ionicons name="leaf" size={24} color={Colors.accent} />
          </View>
          <View style={styles.plantInfo}>
            <Text style={styles.plantName}>{name}</Text>
            {plant.scientific && plant.common_name && (
              <Text style={styles.scientificName}>{plant.scientific}</Text>
            )}
            {plant.preset && (
              <Text style={styles.presetLabel}>{plant.preset}</Text>
            )}
          </View>
          {!plant.active && (
            <Badge text="Archived" variant="neutral" size="sm" />
          )}
        </View>

        {/* Moisture bar — live data from attached device */}
        {hasDevice && moisture !== null && moisture !== undefined ? (
          <View style={styles.moistureRow}>
            <Ionicons name="water" size={14} color={moistureColor(moisture)} />
            <Text style={styles.moistureValue}>{moisture}%</Text>
            <View style={styles.moistureBar}>
              <ProgressBar value={moisture} color={moistureColor(moisture)} />
            </View>
            {plant.start_pct != null && plant.stop_pct != null && (
              <Text style={styles.moistureRange}>
                {plant.start_pct}-{plant.stop_pct}%
              </Text>
            )}
          </View>
        ) : !hasDevice ? (
          <Text style={styles.noDevice}>No device attached</Text>
        ) : (
          <Text style={styles.noDevice}>No sensor data</Text>
        )}

        {/* Device badge — secondary (only if attached) */}
        {hasDevice && (
          <View style={styles.deviceBadge}>
            <Ionicons name="hardware-chip-outline" size={12} color={Colors.textSecondary} />
            <Text style={styles.deviceBadgeText}>{plant.device_id}</Text>
            <Badge
              text={plant.device_online ? 'Online' : 'Offline'}
              variant={plant.device_online ? 'success' : 'neutral'}
              size="sm"
            />
            {plant.device_mode && (
              <>
                <Ionicons
                  name={(plant.device_mode === 'sensor' ? 'water-outline' : plant.device_mode === 'timer' ? 'timer-outline' : 'hand-left-outline') as keyof typeof Ionicons.glyphMap}
                  size={12}
                  color={Colors.primary}
                />
                <Text style={styles.deviceBadgeMode}>
                  {plant.device_mode === 'sensor' ? 'Sensor' : plant.device_mode === 'timer' ? 'Timer' : 'Manual'}
                </Text>
              </>
            )}
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );
}

export default function PlantsScreen() {
  const { plants, isRefetching, refetch } = usePlantsWithDevices();

  const activePlants = plants.filter((p) => p.active);
  const libraryPlants = plants.filter((p) => !p.active);

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
      >
        {/* Identify buttons */}
        <View style={styles.identifyRow}>
          <Button
            title="Take Photo"
            onPress={() => {}}
            variant="outline"
            style={styles.identifyBtn}
            icon={<Ionicons name="camera-outline" size={18} color={Colors.primary} />}
          />
          <Button
            title="From Gallery"
            onPress={() => {}}
            variant="outline"
            style={styles.identifyBtn}
            icon={<Ionicons name="image-outline" size={18} color={Colors.primary} />}
          />
        </View>

        {/* Active plants */}
        <Text style={styles.sectionTitle}>
          My Plants ({activePlants.length})
        </Text>

        {activePlants.length === 0 && (
          <Card style={styles.emptyCard}>
            <Text style={styles.emptyEmoji}>🌿</Text>
            <Text style={styles.emptyTitle}>No plants yet</Text>
            <Text style={styles.emptyText}>
              Identify a plant by photo or connect a Polivalka device.
            </Text>
          </Card>
        )}

        {activePlants.map((plant) => (
          <PlantCard key={plant.plant_id} plant={plant} />
        ))}

        {/* Library (archived) */}
        {libraryPlants.length > 0 && (
          <>
            <Text style={[styles.sectionTitle, { marginTop: Spacing.lg }]}>
              Library ({libraryPlants.length})
            </Text>
            {libraryPlants.map((plant) => (
              <PlantCard key={plant.plant_id} plant={plant} />
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg },
  identifyRow: { flexDirection: 'row', gap: Spacing.md, marginBottom: Spacing.xl },
  identifyBtn: { flex: 1 },
  sectionTitle: {
    fontSize: FontSize.lg,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.md,
  },
  plantCard: { marginBottom: Spacing.md },
  plantHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  plantIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.md,
  },
  plantInfo: { flex: 1 },
  plantName: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },
  scientificName: { fontSize: FontSize.sm, color: Colors.textSecondary, fontStyle: 'italic', marginTop: 2 },
  presetLabel: { fontSize: FontSize.xs, color: Colors.primary, marginTop: 2 },
  moistureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: Spacing.sm,
  },
  moistureValue: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.text, width: 32 },
  moistureBar: { flex: 1 },
  moistureRange: { fontSize: FontSize.xs, color: Colors.textSecondary },
  noDevice: { fontSize: FontSize.sm, color: Colors.textSecondary, marginBottom: Spacing.sm },
  deviceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  deviceBadgeText: { fontSize: FontSize.xs, color: Colors.textSecondary },
  deviceBadgeMode: { fontSize: FontSize.xs, color: Colors.primary, fontWeight: '500' },
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl },
  emptyEmoji: { fontSize: 48, marginBottom: Spacing.lg },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.sm },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },
});
