import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// ---------------------------------------------------------------------------
// Season coefficients (Jan=0 … Dec=11)
// Multiplier for summer-base watering interval → longer in winter, same in summer
// ---------------------------------------------------------------------------
const SEASON_COEFFICIENTS: readonly number[] = [
  3.0, 2.8, 2.1, 1.6, 1.2, 1.0, 1.0, 1.0, 1.2, 1.6, 2.1, 2.8,
] as const;

const STORAGE_KEY = 'plantapp:watering_reminders';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface ReminderRecord {
  notificationId: string;
  plantId: string;
  plantName: string;
  baseDays: number;
  scheduledAt: string; // ISO date when the reminder was scheduled
}

type ReminderStore = Record<string, ReminderRecord>;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------
async function loadStore(): Promise<ReminderStore> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as ReminderStore) : {};
}

async function saveStore(store: ReminderStore): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

/**
 * Returns the adjusted watering interval (in days) for the current month.
 * baseDays is the summer frequency; we multiply by the seasonal coefficient.
 */
function getSeasonalDays(baseDays: number): number {
  const month = new Date().getMonth(); // 0-11
  const coeff = SEASON_COEFFICIENTS[month];
  return Math.round(baseDays * coeff);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Request notification permissions (call once at app startup).
 * Returns true if permissions were granted.
 */
export async function requestNotificationPermissions(): Promise<boolean> {
  const { status: existing } = await Notifications.getPermissionsAsync();
  if (existing === 'granted') return true;

  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}

/**
 * Configure the notification handler (call once at module level in _layout).
 */
export function configureNotifications(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
      priority: Notifications.AndroidNotificationPriority.HIGH,
    }),
  });

  if (Platform.OS === 'android') {
    Notifications.setNotificationChannelAsync('watering', {
      name: 'Watering Reminders',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
    }).catch(() => {
      // non-critical — Android channel creation can fail silently on some devices
    });
  }
}

/**
 * Schedule a local notification for watering a plant.
 *
 * @param plantId   Unique plant identifier
 * @param plantName Display name of the plant
 * @param baseDays  watering_freq_summer_days (summer base interval)
 */
export async function scheduleWateringReminder(
  plantId: string,
  plantName: string,
  baseDays: number,
): Promise<void> {
  // Cancel any existing reminder for this plant first
  await cancelReminder(plantId);

  const days = getSeasonalDays(baseDays);

  const notificationId = await Notifications.scheduleNotificationAsync({
    content: {
      title: `Time to water ${plantName}`,
      body: `It's been ~${days} days since last watering`,
      data: { plantId },
      ...(Platform.OS === 'android' ? { channelId: 'watering' } : {}),
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
      seconds: days * 24 * 60 * 60,
      repeats: false,
    },
  });

  const store = await loadStore();
  store[plantId] = {
    notificationId,
    plantId,
    plantName,
    baseDays,
    scheduledAt: new Date().toISOString(),
  };
  await saveStore(store);
}

/**
 * Cancel a scheduled watering reminder for a specific plant.
 */
export async function cancelReminder(plantId: string): Promise<void> {
  const store = await loadStore();
  const record = store[plantId];
  if (record) {
    await Notifications.cancelScheduledNotificationAsync(record.notificationId);
    delete store[plantId];
    await saveStore(store);
  }
}

/**
 * Reschedule all stored reminders (e.g. after app restart or season change).
 * Cancels existing notifications and creates new ones with recalculated intervals.
 */
export async function rescheduleAll(): Promise<void> {
  const store = await loadStore();
  const entries = Object.values(store);

  // Cancel all existing scheduled notifications for our reminders
  for (const record of entries) {
    await Notifications.cancelScheduledNotificationAsync(record.notificationId).catch(() => {
      // notification may have already fired or been dismissed
    });
  }

  // Re-schedule each with current seasonal coefficient
  const newStore: ReminderStore = {};
  for (const record of entries) {
    const days = getSeasonalDays(record.baseDays);

    const notificationId = await Notifications.scheduleNotificationAsync({
      content: {
        title: `Time to water ${record.plantName}`,
        body: `It's been ~${days} days since last watering`,
        data: { plantId: record.plantId },
        ...(Platform.OS === 'android' ? { channelId: 'watering' } : {}),
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds: days * 24 * 60 * 60,
        repeats: false,
      },
    });

    newStore[record.plantId] = {
      ...record,
      notificationId,
      scheduledAt: new Date().toISOString(),
    };
  }

  await saveStore(newStore);
}
