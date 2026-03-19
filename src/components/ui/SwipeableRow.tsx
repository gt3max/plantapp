import React, { useRef } from 'react';
import { View, Text, StyleSheet, Animated, TouchableOpacity } from 'react-native';
import { Swipeable } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, FontSize, BorderRadius } from '../../constants/colors';

interface SwipeableRowProps {
  children: React.ReactNode;
  onDelete: () => void;
}

export function SwipeableRow({ children, onDelete }: SwipeableRowProps) {
  const swipeableRef = useRef<Swipeable>(null);

  const renderRightActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    const scale = dragX.interpolate({
      inputRange: [-80, 0],
      outputRange: [1, 0.5],
      extrapolate: 'clamp',
    });

    return (
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => {
          swipeableRef.current?.close();
          onDelete();
        }}
        style={styles.rightAction}
      >
        <Animated.View style={[styles.deleteBtn, { transform: [{ scale }] }]}>
          <Ionicons name="trash-outline" size={22} color="#fff" />
          <Text style={styles.deleteText}>Delete</Text>
        </Animated.View>
      </TouchableOpacity>
    );
  };

  return (
    <Swipeable
      ref={swipeableRef}
      renderRightActions={renderRightActions}
      rightThreshold={80}
      overshootRight={false}
    >
      {children}
    </Swipeable>
  );
}

const styles = StyleSheet.create({
  rightAction: {
    justifyContent: 'center',
    alignItems: 'flex-end',
    marginBottom: Spacing.sm,
  },
  deleteBtn: {
    backgroundColor: Colors.error,
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
    height: '100%',
    borderTopRightRadius: BorderRadius.lg,
    borderBottomRightRadius: BorderRadius.lg,
  },
  deleteText: {
    color: '#fff',
    fontSize: FontSize.xs,
    fontWeight: '600',
    marginTop: 2,
  },
});
