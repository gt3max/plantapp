// PlantApp color palette — green theme
export const Colors = {
  // Brand
  primary: '#2D6A4F',
  primaryLight: '#40916C',
  primaryDark: '#1B4332',
  accent: '#52B788',
  accentLight: '#74C69D',

  // Backgrounds
  background: '#F5FFF5',
  backgroundDark: '#121212',
  surface: '#FFFFFF',
  surfaceDark: '#1E1E1E',
  cardDark: '#2A2A2A',

  // Text
  text: '#1A1A1A',
  textSecondary: '#6B7280',
  textDark: '#F5F5F5',
  textSecondaryDark: '#9CA3AF',

  // Status
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // Specific
  online: '#22C55E',
  offline: '#9CA3AF',
  battery: '#F59E0B',
  moisture: '#3B82F6',

  // UI
  border: '#E5E7EB',
  borderDark: '#374151',
  tabBarBackground: '#FFFFFF',
  tabBarBackgroundDark: '#1E1E1E',
  tabIconDefault: '#9CA3AF',
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const FontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 22,
  xxl: 26,
  xxxl: 34,
} as const;

export const BorderRadius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  full: 9999,
} as const;
