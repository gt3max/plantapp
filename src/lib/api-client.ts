import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_BASE, AUTH_ENDPOINTS } from '../constants/api';
import { tokenService } from './token-service';
import type { RefreshResponse } from '../types/auth';

// Axios instance for all API calls
export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Queue for requests waiting on token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: Error) => void;
}> = [];

function processQueue(error: Error | null, token: string | null) {
  failedQueue.forEach((p) => {
    if (error) {
      p.reject(error);
    } else {
      p.resolve(token!);
    }
  });
  failedQueue = [];
}

// Request interceptor: attach JWT
apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  // Skip auth header for public auth endpoints
  const url = config.url || '';
  if (url.startsWith('/auth/') && !url.includes('/logout')) {
    return config;
  }

  const token = await tokenService.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 → refresh → retry
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Skip refresh for auth endpoints
    const url = originalRequest.url || '';
    if (url.startsWith('/auth/')) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until refresh completes
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        originalRequest._retry = true;
        return apiClient(originalRequest);
      });
    }

    isRefreshing = true;
    originalRequest._retry = true;

    try {
      const refreshToken = await tokenService.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token');
      }

      const { data } = await axios.post<RefreshResponse>(
        `${API_BASE}${AUTH_ENDPOINTS.refresh}`,
        { refresh_token: refreshToken },
      );

      await tokenService.updateAccessToken(data.access_token, data.expires_in);
      processQueue(null, data.access_token);

      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as Error, null);
      await tokenService.clearAll();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// Convenience helpers (like web API.get / API.post)
export const api = {
  get: <T>(path: string) => apiClient.get<T>(path).then((r) => r.data),
  post: <T>(path: string, data?: Record<string, unknown>) =>
    apiClient.post<T>(path, data).then((r) => r.data),
  put: <T>(path: string, data?: Record<string, unknown>) =>
    apiClient.put<T>(path, data).then((r) => r.data),
  delete: <T>(path: string) => apiClient.delete<T>(path).then((r) => r.data),
};
