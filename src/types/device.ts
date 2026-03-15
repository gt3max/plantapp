export type OperatingMode = 'manual' | 'timer' | 'sensor';

export type SensorState =
  | 'DISABLED'
  | 'LAUNCH'
  | 'ACTIVE'
  | 'STANDBY'
  | 'WATERING'
  | 'PULSE'
  | 'SETTLE'
  | 'CHECK'
  | 'COOLDOWN'
  | 'EMERGENCY'
  | 'ERROR'
  | 'UNKNOWN';

export type DisplayState = 'Standby' | 'Watering' | 'Emergency';

export interface DeviceWarning {
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface AttachedPlant {
  name: string;
  scientific_name?: string;
  preset?: string;
  start_pct?: number;
  stop_pct?: number;
  description?: string;
  care?: string;
}

export interface Device {
  device_id: string;
  name: string;
  location?: string;
  room?: string;
  online: boolean;
  battery_pct: number | null;
  battery_charging: boolean;
  moisture_pct: number | null;
  moisture_adc?: number;
  secondary_moisture_adc?: number;
  mode: OperatingMode;
  state: SensorState;
  firmware_version?: string;
  clean_restarts?: number;
  unexpected_restarts?: number;
  last_watering?: string;
  last_update?: string;
  pump_running?: boolean;
  pump_speed?: number;
  warnings: DeviceWarning[];
  plant?: AttachedPlant;
  // Sensor mode
  sensor_start_pct?: number;
  sensor_stop_pct?: number;
  daily_water_ml?: number;
  watering_count_today?: number;
  // Timer mode
  next_watering?: string;
  schedule_count?: number;
}

export interface DeviceStatus {
  state: SensorState;
  mode: OperatingMode;
  moisture_pct: number | null;
  moisture_adc: number;
  secondary_moisture_adc?: number;
  battery_pct: number | null;
  battery_charging: boolean;
  pump_running: boolean;
  pump_speed: number;
  wifi_connected: boolean;
  firmware_version: string;
  uptime: number;
  warnings: DeviceWarning[];
}
