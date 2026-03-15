import type { SensorState, DisplayState } from '../types/device';

/**
 * Map internal state to user-friendly display.
 * Based on polivalka-web common.js mapStateToDisplay()
 */
export function mapStateToDisplay(
  state: SensorState,
  pumpRunning?: boolean,
): { text: DisplayState; emoji: string; color: string } {
  if (
    pumpRunning ||
    state === 'WATERING' ||
    state === 'PULSE' ||
    state === 'SETTLE' ||
    state === 'CHECK'
  ) {
    return { text: 'Watering', emoji: '\u{1F4A7}', color: '#3B82F6' };
  }
  if (state === 'EMERGENCY' || state.includes('ERROR')) {
    return { text: 'Emergency', emoji: '\u{26A0}\u{FE0F}', color: '#EF4444' };
  }
  return { text: 'Standby', emoji: '\u{1F4A4}', color: '#22C55E' };
}

/**
 * Format timestamp to relative "X ago" string.
 * Based on polivalka-web common.js timeAgo()
 */
export function timeAgo(timestamp: string | number | null | undefined): string {
  if (!timestamp) return 'Never';
  const now = Date.now();
  const then = typeof timestamp === 'string' ? new Date(timestamp).getTime() : timestamp;
  const diff = now - then;

  if (diff < 0) return 'Just now';
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

/**
 * Format HH:MM (24h)
 */
export function formatTime(date: Date | number | string): string {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return '--:--';
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false });
}

/**
 * Format battery display
 */
export function formatBattery(percent: number | null, charging: boolean): string {
  if (percent === null && charging) return 'AC';
  if (percent === null) return '--';
  return `${percent}%${charging ? ' \u{26A1}' : ''}`;
}

/**
 * Format moisture percentage
 */
export function formatMoisture(percent: number | null): string {
  if (percent === null || percent === undefined) return '--';
  return `${percent}%`;
}
