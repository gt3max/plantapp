import { useState, useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import * as Location from 'expo-location';

// ─── Types ───────────────────────────────────────────────────────────

interface MonthlyTemps {
  /** 12 monthly average temperatures in °C, index 0 = January */
  temps: number[];
}

interface LocationData {
  latitude: number;
  longitude: number;
  currentTemp: number;
  monthlyAvgTemps: number[];
  hardinessZone: string;
  isLoading: boolean;
  error: string | null;
}

interface OutdoorMonths {
  potted: string[];
  inGround: string[];
}

// ─── Constants ───────────────────────────────────────────────────────

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const MONTH_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

const CACHE_DURATION_MS = 60 * 60 * 1000; // 1 hour

// ─── USDA Hardiness Zone lookup ──────────────────────────────────────

const HARDINESS_ZONES: { min: number; zone: string }[] = [
  { min: -51.1, zone: '1a' }, { min: -48.3, zone: '1b' },
  { min: -45.6, zone: '2a' }, { min: -42.8, zone: '2b' },
  { min: -40.0, zone: '3a' }, { min: -37.2, zone: '3b' },
  { min: -34.4, zone: '4a' }, { min: -31.7, zone: '4b' },
  { min: -28.9, zone: '5a' }, { min: -26.1, zone: '5b' },
  { min: -23.3, zone: '6a' }, { min: -20.6, zone: '6b' },
  { min: -17.8, zone: '7a' }, { min: -15.0, zone: '7b' },
  { min: -12.2, zone: '8a' }, { min: -9.4, zone: '8b' },
  { min: -6.7, zone: '9a' }, { min: -3.9, zone: '9b' },
  { min: -1.1, zone: '10a' }, { min: 1.7, zone: '10b' },
  { min: 4.4, zone: '11a' }, { min: 7.2, zone: '11b' },
  { min: 10.0, zone: '12a' }, { min: 12.8, zone: '12b' },
  { min: 15.6, zone: '13a' }, { min: 18.3, zone: '13b' },
];

function getHardinessZone(minWinterTemp: number): string {
  let zone = '1a';
  for (const entry of HARDINESS_ZONES) {
    if (minWinterTemp >= entry.min) {
      zone = entry.zone;
    }
  }
  return zone;
}

// ─── Outdoor months calculation ──────────────────────────────────────

export function getOutdoorMonths(
  frostLimitC: number,
  monthlyAvgTemps: number[],
): OutdoorMonths {
  const potted: string[] = [];
  const inGround: string[] = [];

  for (let i = 0; i < 12; i++) {
    const temp = monthlyAvgTemps[i];
    if (temp === undefined) continue;

    if (temp > frostLimitC + 5) {
      potted.push(MONTH_NAMES[i]);
    }
    if (temp > frostLimitC + 2) {
      inGround.push(MONTH_NAMES[i]);
    }
  }

  return { potted, inGround };
}

/** Format month list into range string: "May – September" or "May – Jul, Sep" */
export function formatMonthRange(months: string[]): string {
  if (months.length === 0) return 'Not recommended';
  if (months.length === 12) return 'Year-round';
  if (months.length === 1) return months[0];

  // Check if consecutive
  const indices = months.map((m) => MONTH_NAMES.indexOf(m));
  let consecutive = true;
  for (let i = 1; i < indices.length; i++) {
    if (indices[i] !== indices[i - 1] + 1) {
      consecutive = false;
      break;
    }
  }

  if (consecutive) {
    return `${months[0]} \u2013 ${months[months.length - 1]}`;
  }

  // Non-consecutive: use short names
  return months.map((m) => MONTH_SHORT[MONTH_NAMES.indexOf(m)]).join(', ');
}

// ─── Cache ───────────────────────────────────────────────────────────

interface CachedData {
  latitude: number;
  longitude: number;
  currentTemp: number;
  monthlyAvgTemps: number[];
  minWinterTemp: number;
  hardinessZone: string;
  timestamp: number;
}

let cachedData: CachedData | null = null;

// ─── API calls ───────────────────────────────────────────────────────

interface CurrentWeatherResponse {
  current: {
    temperature_2m: number;
  };
}

interface MonthlyArchiveResponse {
  monthly: {
    temperature_2m_mean: number[];
  };
}

async function fetchCurrentWeather(lat: number, lon: number): Promise<number> {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Weather API error: ${response.status}`);
  const data = (await response.json()) as CurrentWeatherResponse;
  return data.current.temperature_2m;
}

async function fetchMonthlyAverages(lat: number, lon: number): Promise<MonthlyTemps> {
  const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=2024-01-01&end_date=2024-12-31&monthly=temperature_2m_mean&timezone=auto`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Archive API error: ${response.status}`);
  const data = (await response.json()) as MonthlyArchiveResponse;
  return { temps: data.monthly.temperature_2m_mean };
}

// ─── Hook ────────────────────────────────────────────────────────────

const DEFAULT_STATE: LocationData = {
  latitude: 0,
  longitude: 0,
  currentTemp: 0,
  monthlyAvgTemps: [],
  hardinessZone: '',
  isLoading: true,
  error: null,
};

export function useLocationData(): LocationData {
  const [state, setState] = useState<LocationData>(DEFAULT_STATE);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (Platform.OS === 'web') {
      setState({
        ...DEFAULT_STATE,
        isLoading: false,
        error: 'Location not available on web',
      });
      return;
    }

    if (fetchedRef.current) return;

    // Check cache first
    if (cachedData && Date.now() - cachedData.timestamp < CACHE_DURATION_MS) {
      setState({
        latitude: cachedData.latitude,
        longitude: cachedData.longitude,
        currentTemp: cachedData.currentTemp,
        monthlyAvgTemps: cachedData.monthlyAvgTemps,
        hardinessZone: cachedData.hardinessZone,
        isLoading: false,
        error: null,
      });
      fetchedRef.current = true;
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          if (!cancelled) {
            setState({
              ...DEFAULT_STATE,
              isLoading: false,
              error: 'Location permission denied',
            });
          }
          return;
        }

        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Low,
        });
        const { latitude, longitude } = location.coords;

        const [currentTemp, monthly] = await Promise.all([
          fetchCurrentWeather(latitude, longitude),
          fetchMonthlyAverages(latitude, longitude),
        ]);

        const minWinterTemp = Math.min(...monthly.temps);
        const hardinessZone = getHardinessZone(minWinterTemp);

        const newData: CachedData = {
          latitude,
          longitude,
          currentTemp,
          monthlyAvgTemps: monthly.temps,
          minWinterTemp,
          hardinessZone,
          timestamp: Date.now(),
        };
        cachedData = newData;

        if (!cancelled) {
          setState({
            latitude,
            longitude,
            currentTemp,
            monthlyAvgTemps: monthly.temps,
            hardinessZone,
            isLoading: false,
            error: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            ...DEFAULT_STATE,
            isLoading: false,
            error: err instanceof Error ? err.message : 'Failed to get location data',
          });
        }
      }
    }

    fetchedRef.current = true;
    load();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
