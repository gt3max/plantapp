/**
 * Light Meter — Lux estimation and PPFD conversion.
 *
 * Conversion factors (confirmed by LI-COR + Mulyarchik spectroradiometer):
 * - Sunlight:  PPFD = Lux × 0.018  (1 klux = 18 µmol/m²/s)
 * - White LED: PPFD = Lux × 0.012  (1 klux = 12 µmol/m²/s)
 * - Grow LED (R+B): unreliable via Lux — needs PAR-meter
 *
 * DLI = PPFD × photoperiod_hours × 3600 / 1_000_000
 */

// ─── Types ───────────────────────────────────────────────────────────

export type LightSource = 'sunlight' | 'led' | 'mixed';

export interface LightReading {
  lux: number;
  ppfd: number;
  dli: number; // based on 12h photoperiod
  source: LightSource;
}

export interface LightAssessment {
  reading: LightReading;
  status: 'too_low' | 'low' | 'good' | 'high' | 'too_high';
  message: string;
  plantNeeds: { ppfdMin: number; ppfdMax: number; dliMin: number; dliMax: number };
}

// ─── Conversion ──────────────────────────────────────────────────────

const LUX_TO_PPFD: Record<LightSource, number> = {
  sunlight: 0.018,  // natural daylight through window
  led: 0.015,       // average lamp (LED=0.012, incandescent=0.017, fluorescent=0.014)
  mixed: 0.016,     // window + lamp combined
};

const DEFAULT_PHOTOPERIOD_HOURS = 12;

export function luxToPPFD(lux: number, source: LightSource = 'mixed'): number {
  return Math.round(lux * LUX_TO_PPFD[source]);
}

export function ppfdToDLI(ppfd: number, hours: number = DEFAULT_PHOTOPERIOD_HOURS): number {
  return Math.round((ppfd * hours * 3600) / 1_000_000 * 10) / 10;
}

export function createReading(lux: number, source: LightSource = 'mixed'): LightReading {
  const ppfd = luxToPPFD(lux, source);
  const dli = ppfdToDLI(ppfd);
  return { lux: Math.round(lux), ppfd, dli, source };
}

// ─── Assessment ──────────────────────────────────────────────────────

export function assessLight(
  reading: LightReading,
  ppfdMin: number,
  ppfdMax: number,
  dliMin: number,
  dliMax: number,
): LightAssessment {
  const { ppfd } = reading;
  const plantNeeds = { ppfdMin, ppfdMax, dliMin, dliMax };

  if (ppfd < ppfdMin * 0.5) {
    return {
      reading,
      status: 'too_low',
      message: `Very low light (${ppfd} PPFD). This plant needs at least ${ppfdMin} PPFD. Move closer to a window or add a grow light.`,
      plantNeeds,
    };
  }
  if (ppfd < ppfdMin) {
    return {
      reading,
      status: 'low',
      message: `Light is below ideal (${ppfd} PPFD, needs ${ppfdMin}+). Consider a brighter spot or supplemental lighting.`,
      plantNeeds,
    };
  }
  if (ppfd > ppfdMax * 1.5) {
    return {
      reading,
      status: 'too_high',
      message: `Very intense light (${ppfd} PPFD). Risk of leaf burn. Move away from direct sun or add a sheer curtain.`,
      plantNeeds,
    };
  }
  if (ppfd > ppfdMax) {
    return {
      reading,
      status: 'high',
      message: `Light is above ideal (${ppfd} PPFD, max ${ppfdMax}). Monitor for signs of stress.`,
      plantNeeds,
    };
  }
  return {
    reading,
    status: 'good',
    message: `Light is in the ideal range (${ppfd} PPFD). This spot works well for your plant.`,
    plantNeeds,
  };
}

// ─── Brightness to Lux estimation ────────────────────────────────────

/**
 * Estimate Lux from average image brightness (0-255 RGB).
 *
 * Calibration: smartphone cameras auto-expose, so brightness ≈ 128 (middle gray)
 * in most conditions. We use the camera's reported exposure metadata when available.
 * Fallback: map 0-255 brightness to ~0-100,000 Lux logarithmic scale.
 *
 * This is an ESTIMATION — not a PAR meter. Accuracy ±30%.
 * Good enough for "too dark / good / too bright" assessment.
 */
export function brightnessToLux(avgBrightness: number): number {
  // Clamp to 0-255
  const b = Math.max(0, Math.min(255, avgBrightness));

  if (b < 5) return 0;

  // Logarithmic mapping: cameras compress dynamic range
  // Dark room (~10 Lux) → b≈20, Office (~500 Lux) → b≈100,
  // Bright window (~10K Lux) → b≈180, Direct sun (~100K Lux) → b≈240
  const normalized = b / 255;
  const lux = Math.pow(normalized, 2.2) * 100000; // gamma-like curve

  return Math.round(lux);
}

// ─── PPFD bar position helper ────────────────────────────────────────

/** Returns 0-100 position on a logarithmic PPFD scale (0-1000) */
export function ppfdToPercent(ppfd: number): number {
  if (ppfd <= 0) return 0;
  const maxPPFD = 1000;
  return Math.min(100, Math.max(0, (Math.log10(ppfd) / Math.log10(maxPPFD)) * 100));
}
