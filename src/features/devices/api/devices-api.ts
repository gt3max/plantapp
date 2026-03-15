import { useQuery } from '@tanstack/react-query';
import { api } from '../../../lib/api-client';
import { DEVICE_ENDPOINTS } from '../../../constants/api';
import type { Device } from '../../../types/device';

// Normalize: ADC < 100 = sensor disconnected → null
function normalizeSensorData(device: Device): Device {
  if (device.moisture_adc !== undefined && device.moisture_adc < 100) {
    device.moisture_pct = null;
  }
  return device;
}

async function fetchDevices(): Promise<Device[]> {
  const devices = await api.get<Device[]>(DEVICE_ENDPOINTS.list);
  if (!Array.isArray(devices)) return [];
  return devices.map(normalizeSensorData);
}

export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: fetchDevices,
    staleTime: 60_000, // 60s (cloud polling rate)
    refetchInterval: 60_000,
  });
}
