import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Colors, Spacing, FontSize, BorderRadius } from '../../../constants/colors';
import { mapStateToDisplay, timeAgo, formatBattery } from '../../../lib/utils';
import type { Device } from '../../../types/device';

interface DeviceCardProps {
  device: Device;
}

const modeIcons: Record<string, string> = {
  manual: 'hand-left-outline',
  timer: 'timer-outline',
  sensor: 'water-outline',
};

const modeLabels: Record<string, string> = {
  manual: 'Manual',
  timer: 'Timer',
  sensor: 'Sensor',
};

export function DeviceCard({ device }: DeviceCardProps) {
  const router = useRouter();
  const display = mapStateToDisplay(device.state, device.pump_running);
  const hasWarnings = device.warnings.length > 0;
  const isCritical =
    (device.battery_pct !== null && device.battery_pct < 10) ||
    (device.moisture_pct !== null && device.moisture_pct < 15);

  const variant = isCritical ? 'critical' : hasWarnings ? 'warning' : 'default';
  const customName = device.name !== device.device_id ? device.name : null;

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => router.push(`/device/${device.device_id}`)}
    >
      <Card variant={variant} style={!device.online ? { ...styles.card, ...styles.offline } : styles.card}>
        {/* Header: device ID + status */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={styles.deviceId}>{device.device_id}</Text>
            <Text style={styles.location}>
              {device.location || 'Home'} / {device.room || 'Room'}
              {customName ? ` / ${customName}` : ''}
            </Text>
          </View>
          <Badge
            text={device.online ? 'Online' : 'Offline'}
            variant={device.online ? 'success' : 'neutral'}
          />
        </View>

        {/* Metrics row */}
        <View style={styles.metrics}>
          {/* Moisture */}
          <View style={styles.metric}>
            <Ionicons name="water" size={14} color={Colors.moisture} />
            <Text style={styles.metricValue}>
              {device.moisture_pct !== null ? `${device.moisture_pct}%` : '--'}
            </Text>
          </View>

          {/* Battery */}
          <View style={styles.metric}>
            <Ionicons
              name={device.battery_charging ? 'flash' : 'battery-half'}
              size={14}
              color={Colors.battery}
            />
            <Text style={styles.metricValue}>
              {formatBattery(device.battery_pct, device.battery_charging)}
            </Text>
          </View>

          {/* Mode */}
          <View style={styles.metric}>
            <Ionicons
              name={(modeIcons[device.mode] || 'help-outline') as keyof typeof Ionicons.glyphMap}
              size={14}
              color={Colors.primary}
            />
            <Text style={styles.metricValue}>
              {modeLabels[device.mode] || device.mode}
            </Text>
          </View>

          {/* State */}
          <View style={styles.metric}>
            <Text style={[styles.metricValue, { color: display.color }]}>
              {display.emoji} {display.text}
            </Text>
          </View>
        </View>

        {/* Last watering */}
        <Text style={styles.lastWatering}>
          Last water: {timeAgo(device.last_watering)}
        </Text>

        {/* Warnings */}
        {hasWarnings && (
          <View style={styles.warnings}>
            {device.warnings.slice(0, 2).map((w, i) => (
              <Text key={i} style={styles.warningText}>
                {w.message}
              </Text>
            ))}
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: Spacing.md },
  offline: { opacity: 0.6 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.md,
  },
  headerLeft: { flex: 1, marginRight: Spacing.sm },
  deviceId: {
    fontSize: FontSize.md,
    fontWeight: '600',
    color: Colors.text,
  },
  location: {
    fontSize: FontSize.xs,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.md,
    marginBottom: Spacing.sm,
  },
  metric: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metricValue: {
    fontSize: FontSize.sm,
    color: Colors.text,
  },
  lastWatering: {
    fontSize: FontSize.xs,
    color: Colors.textSecondary,
  },
  warnings: {
    marginTop: Spacing.sm,
    backgroundColor: '#fff3cd',
    borderRadius: BorderRadius.sm,
    padding: Spacing.sm,
  },
  warningText: {
    fontSize: FontSize.xs,
    color: '#92400e',
  },
});
