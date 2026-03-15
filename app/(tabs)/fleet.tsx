import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useDevices } from '../../src/features/devices/api/devices-api';
import { DeviceCard } from '../../src/features/devices/components/DeviceCard';
import { Card } from '../../src/components/ui/Card';
import { Colors, Spacing, FontSize } from '../../src/constants/colors';

export default function FleetScreen() {
  const { data: devices, isLoading, isError, error, refetch, isRefetching } = useDevices();

  const online = devices?.filter((d) => d.online).length ?? 0;
  const warnings = devices?.filter((d) => d.warnings.length > 0).length ?? 0;
  const watering = devices?.filter(
    (d) => d.pump_running || d.state === 'PULSE' || d.state === 'WATERING',
  ).length ?? 0;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor={Colors.primary}
          />
        }
      >
        {/* Stats row */}
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: Colors.online }]}>{online}</Text>
            <Text style={styles.statLabel}>Online</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: warnings > 0 ? Colors.warning : Colors.primary }]}>
              {warnings}
            </Text>
            <Text style={styles.statLabel}>Warnings</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: watering > 0 ? Colors.moisture : Colors.primary }]}>
              {watering}
            </Text>
            <Text style={styles.statLabel}>Watering</Text>
          </View>
        </View>

        {/* Loading */}
        {isLoading && (
          <View style={styles.center}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.loadingText}>Loading devices...</Text>
          </View>
        )}

        {/* Error */}
        {isError && (
          <Card variant="critical">
            <Text style={styles.errorText}>
              Failed to load devices: {(error as Error)?.message || 'Unknown error'}
            </Text>
          </Card>
        )}

        {/* Empty state */}
        {!isLoading && devices && devices.length === 0 && (
          <Card style={styles.emptyCard}>
            <Text style={styles.emptyEmoji}>🌱</Text>
            <Text style={styles.emptyTitle}>No devices yet</Text>
            <Text style={styles.emptyText}>
              Your Polivalka devices will appear here after they connect to your account.
            </Text>
          </Card>
        )}

        {/* Device list */}
        {devices?.map((device) => (
          <DeviceCard key={device.device_id} device={device} />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: Spacing.lg,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  statItem: { alignItems: 'center' },
  statValue: { fontSize: FontSize.xxl, fontWeight: '700' },
  statLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  center: { alignItems: 'center', paddingVertical: Spacing.xxxl },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: FontSize.md },
  errorText: { color: Colors.error, fontSize: FontSize.md },
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl },
  emptyEmoji: { fontSize: 48, marginBottom: Spacing.lg },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.sm },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },
});
