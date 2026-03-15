import { create } from 'zustand';
import { tokenService } from '../lib/token-service';
import { api } from '../lib/api-client';
import { AUTH_ENDPOINTS } from '../constants/api';
import type { AuthResponse, LoginRequest, RegisterRequest, VerifyRequest } from '../types/auth';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  userEmail: string | null;
  error: string | null;
  pendingEmail: string | null; // email waiting for verification

  // Actions
  initialize: () => Promise<void>;
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  verify: (req: VerifyRequest) => Promise<void>;
  resendCode: () => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  isLoading: true,
  userEmail: null,
  error: null,
  pendingEmail: null,

  initialize: async () => {
    try {
      const [token, expired, email] = await Promise.all([
        tokenService.getAccessToken(),
        tokenService.isTokenExpired(),
        tokenService.getUserEmail(),
      ]);

      if (token && !expired) {
        set({ isAuthenticated: true, userEmail: email, isLoading: false });
      } else if (token && expired) {
        // Try refresh
        const refreshToken = await tokenService.getRefreshToken();
        if (refreshToken) {
          try {
            const data = await api.post<{ access_token: string; expires_in: number }>(
              AUTH_ENDPOINTS.refresh,
              { refresh_token: refreshToken } as unknown as Record<string, unknown>,
            );
            await tokenService.updateAccessToken(data.access_token, data.expires_in);
            set({ isAuthenticated: true, userEmail: email, isLoading: false });
          } catch {
            await tokenService.clearAll();
            set({ isAuthenticated: false, isLoading: false });
          }
        } else {
          await tokenService.clearAll();
          set({ isAuthenticated: false, isLoading: false });
        }
      } else {
        set({ isAuthenticated: false, isLoading: false });
      }
    } catch {
      set({ isAuthenticated: false, isLoading: false });
    }
  },

  login: async (req: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<AuthResponse>(AUTH_ENDPOINTS.login, req as unknown as Record<string, unknown>);
      await tokenService.saveTokens(
        data.access_token,
        data.refresh_token,
        data.expires_in,
        data.email,
      );
      set({ isAuthenticated: true, userEmail: data.email, isLoading: false });
    } catch (err: unknown) {
      const message = extractErrorMessage(err, 'Login failed');
      // Check if email needs verification
      if (message.toLowerCase().includes('not verified') || message.toLowerCase().includes('verify')) {
        set({ pendingEmail: req.email, error: message, isLoading: false });
      } else {
        set({ error: message, isLoading: false });
      }
    }
  },

  register: async (req: RegisterRequest) => {
    set({ isLoading: true, error: null });
    try {
      await api.post(AUTH_ENDPOINTS.register, req as unknown as Record<string, unknown>);
      set({ pendingEmail: req.email, isLoading: false });
    } catch (err: unknown) {
      set({ error: extractErrorMessage(err, 'Registration failed'), isLoading: false });
    }
  },

  verify: async (req: VerifyRequest) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<AuthResponse>(AUTH_ENDPOINTS.verify, req as unknown as Record<string, unknown>);
      await tokenService.saveTokens(
        data.access_token,
        data.refresh_token,
        data.expires_in,
        data.email,
      );
      set({
        isAuthenticated: true,
        userEmail: data.email,
        pendingEmail: null,
        isLoading: false,
      });
    } catch (err: unknown) {
      set({ error: extractErrorMessage(err, 'Verification failed'), isLoading: false });
    }
  },

  resendCode: async () => {
    const email = get().pendingEmail;
    if (!email) return;
    set({ error: null });
    try {
      await api.post(AUTH_ENDPOINTS.resendCode, { email } as unknown as Record<string, unknown>);
    } catch (err: unknown) {
      set({ error: extractErrorMessage(err, 'Failed to resend code') });
    }
  },

  logout: async () => {
    try {
      await api.post(AUTH_ENDPOINTS.logout);
    } catch {
      // Ignore logout API errors
    }
    await tokenService.clearAll();
    set({ isAuthenticated: false, userEmail: null, pendingEmail: null });
  },

  clearError: () => set({ error: null }),
}));

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const axiosErr = err as { response?: { data?: { error?: string; message?: string } } };
    return axiosErr.response?.data?.error || axiosErr.response?.data?.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
