import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const KEYS = {
  accessToken: 'access_token',
  refreshToken: 'refresh_token',
  tokenExpires: 'token_expires',
  userEmail: 'user_email',
} as const;

// Web fallback: expo-secure-store not available on web
const storage = {
  get: async (key: string): Promise<string | null> => {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return SecureStore.getItemAsync(key);
  },
  set: async (key: string, value: string): Promise<void> => {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
      return;
    }
    await SecureStore.setItemAsync(key, value);
  },
  delete: async (key: string): Promise<void> => {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
      return;
    }
    await SecureStore.deleteItemAsync(key);
  },
};

export const tokenService = {
  getAccessToken: () => storage.get(KEYS.accessToken),
  getRefreshToken: () => storage.get(KEYS.refreshToken),
  getUserEmail: () => storage.get(KEYS.userEmail),

  getTokenExpires: async (): Promise<number> => {
    const val = await storage.get(KEYS.tokenExpires);
    return val ? parseInt(val, 10) : 0;
  },

  saveTokens: async (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
    email: string,
  ): Promise<void> => {
    const expiresAt = Date.now() + expiresIn * 1000;
    await Promise.all([
      storage.set(KEYS.accessToken, accessToken),
      storage.set(KEYS.refreshToken, refreshToken),
      storage.set(KEYS.tokenExpires, expiresAt.toString()),
      storage.set(KEYS.userEmail, email),
    ]);
  },

  updateAccessToken: async (
    accessToken: string,
    expiresIn: number,
  ): Promise<void> => {
    const expiresAt = Date.now() + expiresIn * 1000;
    await Promise.all([
      storage.set(KEYS.accessToken, accessToken),
      storage.set(KEYS.tokenExpires, expiresAt.toString()),
    ]);
  },

  clearAll: async (): Promise<void> => {
    await Promise.all(
      Object.values(KEYS).map((key) => storage.delete(key)),
    );
  },

  isTokenExpired: async (): Promise<boolean> => {
    const expires = await tokenService.getTokenExpires();
    // 5 min buffer (same as web api-adapter.js)
    return Date.now() > expires - 5 * 60 * 1000;
  },
};
