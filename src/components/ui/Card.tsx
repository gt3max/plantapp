import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Colors, Spacing, BorderRadius } from '../../constants/colors';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  variant?: 'default' | 'warning' | 'critical' | 'accent';
}

export function Card({ children, style, variant = 'default' }: CardProps) {
  return (
    <View style={[styles.card, variantStyles[variant], style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
});

const variantStyles: Record<string, ViewStyle> = {
  default: {},
  warning: { borderLeftWidth: 3, borderLeftColor: Colors.warning },
  critical: { borderLeftWidth: 3, borderLeftColor: Colors.error },
  accent: { borderLeftWidth: 3, borderLeftColor: Colors.accent },
};
