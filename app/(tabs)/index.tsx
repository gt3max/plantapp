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
import { useAuthStore } from '../../src/stores/auth-store';
import { useDevices } from '../../src/features/devices/api/devices-api';
import { Card } from '../../src/components/ui/Card';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { timeAgo, formatBattery } from '../../src/lib/utils';
import type { Device } from '../../src/types/device';

interface AlertItem {
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  variant: 'warning' | 'critical';
  deviceId: string;
}

function generateAlerts(devices: Device[]): AlertItem[] {
  const alerts: AlertItem[] = [];
  devices.forEach((d) => {
    // Low moisture
    if (d.moisture_pct !== null && d.sensor_start_pct && d.moisture_pct <= d.sensor_start_pct) {
      alerts.push({
        id: `moisture-${d.device_id}`,
        icon: '💧',
        title: `${d.plant?.name || d.name || d.device_id} — moisture ${d.moisture_pct}%`,
        subtitle: 'Needs water soon',
        variant: d.moisture_pct < 15 ? 'critical' : 'warning',
        deviceId: d.device_id,
      });
    }
    // Low battery
    if (d.battery_pct !== null && d.battery_pct < 20) {
      alerts.push({
        id: `battery-${d.device_id}`,
        icon: '🔋',
        title: `${d.device_id} — battery ${d.battery_pct}%`,
        subtitle: 'Consider charging soon',
        variant: d.battery_pct < 10 ? 'critical' : 'warning',
        deviceId: d.device_id,
      });
    }
    // Device warnings
    d.warnings.forEach((w, i) => {
      alerts.push({
        id: `warn-${d.device_id}-${i}`,
        icon: '⚠️',
        title: `${d.device_id}`,
        subtitle: w.message,
        variant: w.severity === 'critical' ? 'critical' : 'warning',
        deviceId: d.device_id,
      });
    });
  });
  return alerts;
}

interface ActivityItem {
  id: string;
  text: string;
}

function generateActivity(devices: Device[]): ActivityItem[] {
  const items: ActivityItem[] = [];
  devices.forEach((d) => {
    if (d.last_watering) {
      const name = d.plant?.name || d.name || d.device_id;
      items.push({
        id: `water-${d.device_id}`,
        text: `${name} watered ${timeAgo(d.last_watering)}`,
      });
    }
  });
  return items.slice(0, 5);
}

export default function HomeScreen() {
  const userEmail = useAuthStore((s) => s.userEmail);
  const name = userEmail?.split('@')[0] || 'there';
  const router = useRouter();
  const { data: devices, refetch, isRefetching } = useDevices();

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  const onlineCount = devices?.filter((d) => d.online).length ?? 0;
  const totalPlants = devices?.filter((d) => d.plant).length ?? 0;
  const totalDevices = devices?.length ?? 0;

  const alerts = devices ? generateAlerts(devices) : [];
  const activity = devices ? generateActivity(devices) : [];

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
      >
        <Text style={styles.greeting}>{greeting}, {name}!</Text>
        <Text style={styles.stats}>
          {totalDevices > 0
            ? `${onlineCount} device${onlineCount !== 1 ? 's' : ''} online · ${totalPlants} plant${totalPlants !== 1 ? 's' : ''}`
            : 'No devices connected'}
        </Text>

        {/* Alerts */}
        {alerts.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Alerts</Text>
            {alerts.map((a) => (
              <TouchableOpacity
                key={a.id}
                activeOpacity={0.7}
                onPress={() => router.push(`/device/${a.deviceId}`)}
              >
                <Card variant={a.variant} style={styles.alertCard}>
                  <Text style={styles.alertIcon}>{a.icon}</Text>
                  <View style={styles.alertContent}>
                    <Text style={styles.alertTitle}>{a.title}</Text>
                    <Text style={styles.alertSubtitle}>{a.subtitle}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={16} color={Colors.textSecondary} />
                </Card>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {alerts.length === 0 && devices && devices.length > 0 && (
          <View style={styles.section}>
            <Card style={styles.happyCard}>
              <Text style={styles.happyEmoji}>🌿</Text>
              <Text style={styles.happyText}>All plants are happy!</Text>
            </Card>
          </View>
        )}

        {/* Recent Activity */}
        {activity.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recent Activity</Text>
            <Card>
              {activity.map((item, i) => (
                <View key={item.id} style={[styles.activityRow, i > 0 && styles.activityBorder]}>
                  <Text style={styles.activityDot}>•</Text>
                  <Text style={styles.activityText}>{item.text}</Text>
                </View>
              ))}
            </Card>
          </View>
        )}

        {/* Empty state */}
        {devices && devices.length === 0 && (
          <Card style={styles.emptyCard}>
            <Text style={styles.emptyEmoji}>🌱</Text>
            <Text style={styles.emptyTitle}>Welcome to PlantApp!</Text>
            <Text style={styles.emptyText}>
              Connect a Polivalka device to start monitoring your plants.
            </Text>
          </Card>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg },
  greeting: { fontSize: FontSize.xxl, fontWeight: '700', color: Colors.text, marginBottom: Spacing.xs },
  stats: { fontSize: FontSize.md, color: Colors.textSecondary, marginBottom: Spacing.xl },
  section: { marginBottom: Spacing.xl },
  sectionTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.md },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
    paddingVertical: Spacing.md,
  },
  alertIcon: { fontSize: 24, marginRight: Spacing.md },
  alertContent: { flex: 1 },
  alertTitle: { fontSize: FontSize.md, fontWeight: '600', color: Colors.text },
  alertSubtitle: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: 2 },
  happyCard: { alignItems: 'center', paddingVertical: Spacing.xl },
  happyEmoji: { fontSize: 36, marginBottom: Spacing.sm },
  happyText: { fontSize: FontSize.md, color: Colors.primary, fontWeight: '500' },
  activityRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.sm },
  activityBorder: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: Colors.border },
  activityDot: { fontSize: FontSize.lg, color: Colors.accent, marginRight: Spacing.sm },
  activityText: { fontSize: FontSize.sm, color: Colors.textSecondary, flex: 1 },
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl },
  emptyEmoji: { fontSize: 48, marginBottom: Spacing.lg },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.sm },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },
});
