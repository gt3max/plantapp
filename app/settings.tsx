import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../src/stores/auth-store';
import { Colors, Spacing, FontSize, BorderRadius } from '../src/constants/colors';

interface SettingsRowProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
  color?: string;
}

function SettingsRow({ icon, label, onPress, color }: SettingsRowProps) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress} activeOpacity={0.6}>
      <Ionicons name={icon} size={22} color={color || Colors.text} />
      <Text style={[styles.rowLabel, color ? { color } : undefined]}>{label}</Text>
      <Ionicons name="chevron-forward" size={18} color={Colors.textSecondary} />
    </TouchableOpacity>
  );
}

export default function SettingsScreen() {
  const { userEmail, logout } = useAuthStore();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scroll}>
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(userEmail?.[0] || '?').toUpperCase()}
          </Text>
        </View>
        <Text style={styles.email}>{userEmail}</Text>
      </View>

      <View style={styles.section}>
        <SettingsRow icon="person-outline" label="Edit Profile" onPress={() => {}} />
        <SettingsRow icon="notifications-outline" label="Notifications" onPress={() => {}} />
        <SettingsRow icon="card-outline" label="Manage Subscription" onPress={() => {}} />
        <SettingsRow icon="globe-outline" label="Units (Metric)" onPress={() => {}} />
      </View>

      <View style={styles.section}>
        <SettingsRow icon="information-circle-outline" label="About PlantApp" onPress={() => {}} />
        <SettingsRow icon="document-text-outline" label="Privacy Policy" onPress={() => {}} />
      </View>

      <View style={styles.section}>
        <SettingsRow
          icon="log-out-outline"
          label="Log Out"
          onPress={logout}
          color={Colors.error}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg },
  profileCard: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
    marginBottom: Spacing.lg,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  avatarText: {
    fontSize: FontSize.xxl,
    fontWeight: '700',
    color: '#fff',
  },
  email: {
    fontSize: FontSize.md,
    color: Colors.textSecondary,
  },
  section: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    marginBottom: Spacing.lg,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  rowLabel: {
    flex: 1,
    fontSize: FontSize.md,
    color: Colors.text,
    marginLeft: Spacing.md,
  },
});
