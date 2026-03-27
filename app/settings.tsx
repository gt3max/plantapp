import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Linking,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuthStore } from '../src/stores/auth-store';
import { useSettingsStore } from '../src/stores/settings-store';
import { Colors, Spacing, FontSize, BorderRadius } from '../src/constants/colors';
import Constants from 'expo-constants';

// ─── Row Components ──────────────────────────────────────────────────

function SettingsRow({ icon, label, onPress, color, right }: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress?: () => void;
  color?: string;
  right?: React.ReactNode;
}) {
  const content = (
    <View style={styles.row}>
      <Ionicons name={icon} size={22} color={color ?? Colors.text} />
      <Text style={[styles.rowLabel, color ? { color } : undefined]}>{label}</Text>
      {right ?? <Ionicons name="chevron-forward" size={18} color={Colors.textSecondary} />}
    </View>
  );

  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.6}>
        {content}
      </TouchableOpacity>
    );
  }
  return content;
}

function SettingsToggle({ icon, label, value, onValueChange }: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: boolean;
  onValueChange: (val: boolean) => void;
}) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={22} color={Colors.text} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: '#D1D5DB', true: Colors.accentLight }}
        thumbColor={value ? Colors.primary : '#f4f3f4'}
      />
    </View>
  );
}

function SettingsSegment({ icon, label, options, value, onChange }: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  options: { key: string; label: string }[];
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={22} color={Colors.text} />
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.segmentContainer}>
        {options.map((opt) => (
          <TouchableOpacity
            key={opt.key}
            onPress={() => onChange(opt.key)}
            style={[styles.segmentBtn, value === opt.key && styles.segmentBtnActive]}
          >
            <Text style={[styles.segmentText, value === opt.key && styles.segmentTextActive]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

// ─── Screen ──────────────────────────────────────────────────────────

export default function SettingsScreen() {
  const { userEmail, logout } = useAuthStore();
  const router = useRouter();
  const {
    temperatureUnit,
    lengthUnit,
    notificationsEnabled,
    isLoaded,
    load,
    setTemperatureUnit,
    setLengthUnit,
    setNotificationsEnabled,
  } = useSettingsStore();

  useEffect(() => {
    if (!isLoaded) load();
  }, [isLoaded, load]);

  const handleLogout = () => {
    Alert.alert(
      'Log Out',
      'Are you sure you want to log out?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Log Out', style: 'destructive', onPress: logout },
      ],
    );
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account, all saved plants, and device data. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            Alert.alert(
              'Confirm Deletion',
              `Type your email to confirm:\n${userEmail}`,
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Delete Forever',
                  style: 'destructive',
                  onPress: () => {
                    // TODO: call DELETE /auth/account endpoint when implemented
                    Alert.alert('Not Available', 'Account deletion will be available in a future update. Contact support for manual deletion.');
                  },
                },
              ],
            );
          },
        },
      ],
    );
  };

  const appVersion = Constants.expoConfig?.version ?? '1.0.0';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scroll}>
      {/* Profile */}
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(userEmail?.[0] ?? '?').toUpperCase()}
          </Text>
        </View>
        <Text style={styles.email}>{userEmail}</Text>
        <Text style={styles.plan}>Free Plan</Text>
      </View>

      {/* Preferences */}
      <Text style={styles.sectionHeader}>Preferences</Text>
      <View style={styles.section}>
        <SettingsToggle
          icon="notifications-outline"
          label="Watering Reminders"
          value={notificationsEnabled}
          onValueChange={setNotificationsEnabled}
        />
        <SettingsSegment
          icon="thermometer-outline"
          label="Temperature"
          options={[{ key: 'celsius', label: '°C' }, { key: 'fahrenheit', label: '°F' }]}
          value={temperatureUnit}
          onChange={(k) => setTemperatureUnit(k as 'celsius' | 'fahrenheit')}
        />
        <SettingsSegment
          icon="resize-outline"
          label="Length"
          options={[{ key: 'cm', label: 'cm' }, { key: 'in', label: 'in' }]}
          value={lengthUnit}
          onChange={(k) => setLengthUnit(k as 'cm' | 'in')}
        />
      </View>

      {/* Subscription */}
      <Text style={styles.sectionHeader}>Subscription</Text>
      <View style={styles.section}>
        <SettingsRow
          icon="card-outline"
          label="Manage Subscription"
          onPress={() => {
            Alert.alert('Coming Soon', 'Premium subscriptions will be available when PlantApp launches on the App Store.');
          }}
          right={<Text style={styles.planBadge}>Free</Text>}
        />
      </View>

      {/* About */}
      <Text style={styles.sectionHeader}>About</Text>
      <View style={styles.section}>
        <SettingsRow
          icon="information-circle-outline"
          label="About PlantApp"
          right={<Text style={styles.versionText}>v{appVersion}</Text>}
        />
        <SettingsRow
          icon="document-text-outline"
          label="Privacy Policy"
          onPress={() => {
            Linking.openURL('https://plantapp.pro/privacy').catch(() => {});
          }}
        />
        <SettingsRow
          icon="mail-outline"
          label="Contact Support"
          onPress={() => {
            Linking.openURL('mailto:support@plantapp.pro').catch(() => {});
          }}
        />
      </View>

      {/* Account */}
      <Text style={styles.sectionHeader}>Account</Text>
      <View style={styles.section}>
        <SettingsRow
          icon="log-out-outline"
          label="Log Out"
          onPress={handleLogout}
          color={Colors.error}
        />
        <SettingsRow
          icon="trash-outline"
          label="Delete Account"
          onPress={handleDeleteAccount}
          color={Colors.error}
        />
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>PlantApp v{appVersion}</Text>
        <Text style={styles.footerText}>Made with care for your plants</Text>
      </View>
    </ScrollView>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg, paddingBottom: 60 },

  // Profile
  profileCard: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
    marginBottom: Spacing.md,
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
  avatarText: { fontSize: FontSize.xxl, fontWeight: '700', color: '#fff' },
  email: { fontSize: FontSize.md, color: Colors.text, fontWeight: '600' },
  plan: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: 2 },

  // Section
  sectionHeader: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: Spacing.sm,
    marginLeft: Spacing.xs,
  },
  section: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    marginBottom: Spacing.lg,
    overflow: 'hidden',
  },

  // Row
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
    minHeight: 52,
  },
  rowLabel: {
    flex: 1,
    fontSize: FontSize.md,
    color: Colors.text,
    marginLeft: Spacing.md,
  },

  // Segment control
  segmentContainer: {
    flexDirection: 'row',
    backgroundColor: '#F3F4F6',
    borderRadius: BorderRadius.sm,
    padding: 2,
  },
  segmentBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm - 1,
  },
  segmentBtnActive: {
    backgroundColor: Colors.surface,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 2,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  segmentText: { fontSize: FontSize.sm, color: Colors.textSecondary, fontWeight: '600' },
  segmentTextActive: { color: Colors.text },

  // Badges
  planBadge: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.primary,
    backgroundColor: '#DCFCE7',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
    overflow: 'hidden',
  },
  versionText: { fontSize: FontSize.sm, color: Colors.textSecondary },

  // Footer
  footer: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
  },
  footerText: { fontSize: FontSize.xs, color: Colors.textSecondary, marginBottom: 2 },
});
