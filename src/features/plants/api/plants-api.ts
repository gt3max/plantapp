import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '../../../lib/api-client';
import { PLANT_ENDPOINTS } from '../../../constants/api';
import { useDevices } from '../../devices/api/devices-api';
import type { PlantEntry, PlantWithDevice } from '../../../types/plant';

// Local deleted plant IDs (fallback when backend delete doesn't stick)
const DELETED_IDS_KEY = 'plantapp:deleted_plant_ids';

async function getLocalDeletedIds(): Promise<Set<string>> {
  const raw = await AsyncStorage.getItem(DELETED_IDS_KEY);
  return new Set(raw ? JSON.parse(raw) as string[] : []);
}

async function addLocalDeletedId(plantId: string): Promise<void> {
  const ids = await getLocalDeletedIds();
  ids.add(plantId);
  await AsyncStorage.setItem(DELETED_IDS_KEY, JSON.stringify([...ids]));
}

interface PlantLibraryResponse {
  success: boolean;
  plants: PlantEntry[];
}

async function fetchPlantLibrary(): Promise<PlantEntry[]> {
  const res = await api.get<PlantLibraryResponse>(PLANT_ENDPOINTS.library);
  return res.plants ?? [];
}

export function usePlantLibrary() {
  return useQuery({
    queryKey: ['plant-library'],
    queryFn: fetchPlantLibrary,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

/** Local deleted IDs query — keeps them in React Query cache */
function useLocalDeletedIds() {
  return useQuery({
    queryKey: ['local-deleted-ids'],
    queryFn: async () => getLocalDeletedIds(),
    staleTime: Infinity,
  });
}

/** Plants enriched with live device data (moisture, battery, online status) */
export function usePlantsWithDevices(): {
  plants: PlantWithDevice[];
  isLoading: boolean;
  isRefetching: boolean;
  refetch: () => void;
} {
  const { data: plantEntries, isLoading: plantsLoading, isRefetching: plantsRefetching, refetch: refetchPlants } = usePlantLibrary();
  const { data: devices, isLoading: devicesLoading, isRefetching: devicesRefetching, refetch: refetchDevices } = useDevices();
  const { data: localDeletedIds } = useLocalDeletedIds();

  // Build device lookup by device_id
  const deviceMap = new Map((devices ?? []).map((d) => [d.device_id, d]));

  // Enrich plants with live device data, filter out deleted (backend + local)
  const plants: PlantWithDevice[] = (plantEntries ?? [])
    .filter((p) => !p.archived && !p.deleted && !localDeletedIds?.has(p.plant_id))
    .map((plant) => {
      const device = plant.active ? deviceMap.get(plant.device_id) : undefined;
      return {
        ...plant,
        moisture_pct: device?.moisture_pct,
        battery_pct: device?.battery_pct,
        battery_charging: device?.battery_charging,
        device_online: device?.online,
        device_mode: device?.mode,
      };
    });

  return {
    plants,
    isLoading: plantsLoading || devicesLoading,
    isRefetching: plantsRefetching || devicesRefetching,
    refetch: () => { refetchPlants(); refetchDevices(); },
  };
}

/** Delete a plant (soft-delete). Supports device plants, user-collection plants, and active plants. */
export function useDeletePlant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ deviceId, plantId, active }: { deviceId: string; plantId: string; active?: boolean }) => {
      let path: string;
      if (deviceId === 'user-collection') {
        path = `/plants/user-collection?plant_id=${encodeURIComponent(plantId)}`;
      } else if (active) {
        path = `/plants/${deviceId}`;
      } else {
        path = `/plants/${deviceId}?plant_id=${encodeURIComponent(plantId)}`;
      }
      console.log('[DELETE] path:', path, 'deviceId:', deviceId, 'plantId:', plantId, 'active:', active);
      try {
        const result = await api.delete(path);
        console.log('[DELETE] response:', JSON.stringify(result));
        return result;
      } catch (err: unknown) {
        console.log('[DELETE] error:', err);
        // 404 = already gone, treat as success
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { status?: number; data?: unknown } };
          console.log('[DELETE] error status:', axiosErr.response?.status, 'data:', JSON.stringify(axiosErr.response?.data));
          if (axiosErr.response?.status === 404) return { success: true };
        }
        throw err;
      }
    },
    onMutate: async ({ plantId }) => {
      // Save locally so plant stays deleted even if backend doesn't persist
      await addLocalDeletedId(plantId);
      // Optimistic: remove plant from cache immediately
      await queryClient.cancelQueries({ queryKey: ['plant-library'] });
      await queryClient.cancelQueries({ queryKey: ['local-deleted-ids'] });
      const prev = queryClient.getQueryData<PlantEntry[]>(['plant-library']);
      if (prev) {
        queryClient.setQueryData(['plant-library'], prev.filter((p) => p.plant_id !== plantId));
      }
      queryClient.invalidateQueries({ queryKey: ['local-deleted-ids'] });
      return { prev };
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['plant-library'] });
      queryClient.invalidateQueries({ queryKey: ['local-deleted-ids'] });
    },
  });
}
