// Legacy theme file — kept for compatibility
// New code should import from src/constants/colors.ts
const tintColorLight = '#2D6A4F';
const tintColorDark = '#52B788';

export default {
  light: {
    text: '#1A1A1A',
    background: '#F5FFF5',
    tint: tintColorLight,
    tabIconDefault: '#9CA3AF',
    tabIconSelected: tintColorLight,
  },
  dark: {
    text: '#F5F5F5',
    background: '#121212',
    tint: tintColorDark,
    tabIconDefault: '#9CA3AF',
    tabIconSelected: tintColorDark,
  },
};
