// API Gateway (AWS Lambda — EU Frankfurt)
export const API_BASE = 'https://p0833p2v29.execute-api.eu-central-1.amazonaws.com';

// Auth endpoints (public)
export const AUTH_ENDPOINTS = {
  login: '/auth/login',
  register: '/auth/register',
  verify: '/auth/verify',
  resendCode: '/auth/resend-code',
  refresh: '/auth/refresh',
  logout: '/auth/logout',
} as const;

// Device endpoints (require JWT + device_id)
export const DEVICE_ENDPOINTS = {
  list: '/devices',
  status: (id: string) => `/device/${id}/status`,
  water: (id: string) => `/device/${id}/water`,
  stop: (id: string) => `/device/${id}/stop`,
  config: (id: string) => `/device/${id}/config`,
  mode: (id: string) => `/device/${id}/mode`,
  pumpSpeed: (id: string) => `/device/${id}/pump/speed`,
  sensorController: (id: string) => `/device/${id}/sensor/controller`,
  sensorPreset: (id: string) => `/device/${id}/sensor/preset`,
  timerController: (id: string) => `/device/${id}/timer/controller`,
  schedules: (id: string) => `/device/${id}/schedules`,
  telemetry: (id: string) => `/device/${id}/telemetry`,
} as const;

// Plant endpoints (require JWT)
export const PLANT_ENDPOINTS = {
  identify: '/plants/identify',
  care: '/plants/care',
  library: '/plants/library',
  save: '/plants/save',
} as const;

// Token refresh buffer (5 minutes before expiry)
export const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000;
