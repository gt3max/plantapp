import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../lib/api-client';
import { PLANT_ENDPOINTS } from '../../../constants/api';
import type { IdentifyResponse, SavePlantInput } from '../../../types/plant';

// POST /plants/identify — send base64 image, get top matches
async function identifyPlant(image: string): Promise<IdentifyResponse> {
  return api.post<IdentifyResponse>(
    PLANT_ENDPOINTS.identify,
    { image } as Record<string, unknown>,
  );
}

export function useIdentifyPlant() {
  return useMutation({
    mutationFn: identifyPlant,
  });
}

// POST /plants/save — save identified plant to device
async function savePlant(input: SavePlantInput): Promise<{ success: boolean; message: string }> {
  return api.post<{ success: boolean; message: string }>(
    PLANT_ENDPOINTS.save,
    input as unknown as Record<string, unknown>,
  );
}

export function useSavePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: savePlant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plant-library'] });
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
}
