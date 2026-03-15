import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useLocalSearchParams, Stack } from 'expo-router';
import { Colors, Spacing, FontSize } from '../../src/constants/colors';

export default function DeviceDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  return (
    <View style={styles.container}>
      <Stack.Screen options={{ title: id || 'Device' }} />
      <Text style={styles.title}>Device Detail</Text>
      <Text style={styles.subtitle}>{id}</Text>
      <Text style={styles.placeholder}>Full device controls coming in Stage 5</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xl,
  },
  title: { fontSize: FontSize.xl, fontWeight: '700', color: Colors.text },
  subtitle: { fontSize: FontSize.md, color: Colors.textSecondary, marginTop: Spacing.sm },
  placeholder: { fontSize: FontSize.md, color: Colors.textSecondary, marginTop: Spacing.xl },
});
