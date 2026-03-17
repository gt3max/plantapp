import { useQuery } from '@tanstack/react-query';
import { API_BASE, PLANT_DB_ENDPOINTS } from '../../../constants/api';
import type { PlantDBEntry, PlantDBSearchResponse, PlantDBStats } from '../../../types/plant-db';

/**
 * Fetch plant detail from Turso DB (public, no auth needed).
 * Uses plain fetch to bypass auth interceptor.
 */
async function fetchPlantDBDetail(plantId: string): Promise<PlantDBEntry | null> {
  const url = `${API_BASE}${PLANT_DB_ENDPOINTS.detail(plantId)}`;
  const res = await fetch(url);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Plant DB error: ${res.status}`);
  return res.json();
}

/**
 * Search plant DB (public, no auth needed).
 */
async function fetchPlantDBSearch(query: string, limit = 20): Promise<PlantDBSearchResponse> {
  const url = `${API_BASE}${PLANT_DB_ENDPOINTS.search}?q=${encodeURIComponent(query)}&limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Plant DB search error: ${res.status}`);
  return res.json();
}

/**
 * Hook: get single plant from Turso DB by plant_id.
 */
export function usePlantDBDetail(plantId: string | undefined) {
  return useQuery({
    queryKey: ['plant-db', plantId],
    queryFn: () => fetchPlantDBDetail(plantId!),
    enabled: !!plantId,
    staleTime: 5 * 60_000,  // 5 min cache
  });
}

/**
 * Hook: search plant DB by name.
 * Debounce handled by caller (only triggers when query changes).
 */
export function usePlantDBSearch(query: string, limit = 20) {
  return useQuery({
    queryKey: ['plant-db-search', query, limit],
    queryFn: () => fetchPlantDBSearch(query, limit),
    enabled: query.length >= 2,
    staleTime: 60_000,
  });
}

/**
 * Hook: get plant DB stats.
 */
export function usePlantDBStats() {
  return useQuery({
    queryKey: ['plant-db-stats'],
    queryFn: async (): Promise<PlantDBStats> => {
      const res = await fetch(`${API_BASE}${PLANT_DB_ENDPOINTS.stats}`);
      if (!res.ok) throw new Error(`Stats error: ${res.status}`);
      return res.json();
    },
    staleTime: 10 * 60_000,
  });
}
