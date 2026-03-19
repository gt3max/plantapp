import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../lib/api-client';
import { PLANT_ENDPOINTS } from '../../../constants/api';
import { useDevices } from '../../devices/api/devices-api';
import type { PlantEntry, PlantWithDevice } from '../../../types/plant';

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

/** Plants enriched with live device data (moisture, battery, online status) */
export function usePlantsWithDevices(): {
  plants: PlantWithDevice[];
  isLoading: boolean;
  isRefetching: boolean;
  refetch: () => void;
} {
  const { data: plantEntries, isLoading: plantsLoading, isRefetching: plantsRefetching, refetch: refetchPlants } = usePlantLibrary();
  const { data: devices, isLoading: devicesLoading, isRefetching: devicesRefetching, refetch: refetchDevices } = useDevices();

  // Build device lookup by device_id
  const deviceMap = new Map((devices ?? []).map((d) => [d.device_id, d]));

  // Enrich plants with live device data
  const plants: PlantWithDevice[] = (plantEntries ?? [])
    .filter((p) => !p.archived && !p.deleted)
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
        // User-collection plants: always need plant_id
        path = `/plants/user-collection?plant_id=${encodeURIComponent(plantId)}`;
      } else if (active) {
        // Active plant on device: delete without plant_id so Lambda removes the active plant
        path = `/plants/${deviceId}`;
      } else {
        // Archived/library plant on device: specify plant_id to target it in plant_library
        path = `/plants/${deviceId}?plant_id=${encodeURIComponent(plantId)}`;
      }
      return api.delete(path);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plant-library'] });
    },
  });
}
