import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../lib/api-client';
import { API_BASE, PLANT_ENDPOINTS } from '../../../constants/api';
import type { IdentifyResponse, SavePlantInput } from '../../../types/plant';

// POST /plants/identify — send base64 image, get top matches
// Uses plain fetch with longer timeout (PlantNet can take 30s + Lambda cold start)
async function identifyPlant(image: string): Promise<IdentifyResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 50000); // 50s timeout

  try {
    const res = await fetch(`${API_BASE}${PLANT_ENDPOINTS.identify}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image }),
      signal: controller.signal,
    });

    const data = await res.json();

    if (!res.ok) {
      // Extract error message from Lambda response body
      const errMsg = data?.error || `Identification failed (${res.status})`;
      throw new Error(errMsg);
    }

    return data;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
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
