import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SETTINGS_KEY = 'plantapp:settings';

export type TemperatureUnit = 'celsius' | 'fahrenheit';
export type LengthUnit = 'cm' | 'in';

interface SettingsState {
  temperatureUnit: TemperatureUnit;
  lengthUnit: LengthUnit;
  notificationsEnabled: boolean;
  isLoaded: boolean;

  load: () => Promise<void>;
  setTemperatureUnit: (unit: TemperatureUnit) => void;
  setLengthUnit: (unit: LengthUnit) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
}

interface PersistedSettings {
  temperatureUnit: TemperatureUnit;
  lengthUnit: LengthUnit;
  notificationsEnabled: boolean;
}

async function persist(settings: PersistedSettings): Promise<void> {
  await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  temperatureUnit: 'celsius',
  lengthUnit: 'cm',
  notificationsEnabled: true,
  isLoaded: false,

  load: async () => {
    try {
      const raw = await AsyncStorage.getItem(SETTINGS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<PersistedSettings>;
        set({
          temperatureUnit: parsed.temperatureUnit ?? 'celsius',
          lengthUnit: parsed.lengthUnit ?? 'cm',
          notificationsEnabled: parsed.notificationsEnabled ?? true,
          isLoaded: true,
        });
      } else {
        set({ isLoaded: true });
      }
    } catch {
      set({ isLoaded: true });
    }
  },

  setTemperatureUnit: (unit) => {
    set({ temperatureUnit: unit });
    const s = get();
    persist({ temperatureUnit: unit, lengthUnit: s.lengthUnit, notificationsEnabled: s.notificationsEnabled });
  },

  setLengthUnit: (unit) => {
    set({ lengthUnit: unit });
    const s = get();
    persist({ temperatureUnit: s.temperatureUnit, lengthUnit: unit, notificationsEnabled: s.notificationsEnabled });
  },

  setNotificationsEnabled: (enabled) => {
    set({ notificationsEnabled: enabled });
    const s = get();
    persist({ temperatureUnit: s.temperatureUnit, lengthUnit: s.lengthUnit, notificationsEnabled: enabled });
  },
}));
