import 'package:flutter/material.dart';

/// PlantApp Design System
/// Ported from src/constants/colors.ts (React Native version)

class AppColors {
  AppColors._();

  // Brand
  static const primary = Color(0xFF2D6A4F);
  static const primaryLight = Color(0xFF40916C);
  static const primaryDark = Color(0xFF1B4332);
  static const accent = Color(0xFF52B788);
  static const accentLight = Color(0xFF74C69D);

  // Backgrounds
  static const background = Color(0xFFF5FFF5);
  static const backgroundDark = Color(0xFF121212);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceDark = Color(0xFF1E1E1E);
  static const cardDark = Color(0xFF2A2A2A);

  // Text
  static const text = Color(0xFF1A1A1A);
  static const textSecondary = Color(0xFF6B7280);
  static const textDark = Color(0xFFF5F5F5);
  static const textSecondaryDark = Color(0xFF9CA3AF);

  // Status
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFEF4444);
  static const info = Color(0xFF3B82F6);

  // Specific
  static const online = Color(0xFF22C55E);
  static const offline = Color(0xFF9CA3AF);
  static const battery = Color(0xFFF59E0B);
  static const moisture = Color(0xFF3B82F6);

  // UI
  static const border = Color(0xFFE5E7EB);
  static const borderDark = Color(0xFF374151);
  static const tabBarBackground = Color(0xFFFFFFFF);
  static const tabBarBackgroundDark = Color(0xFF1E1E1E);
  static const tabIconDefault = Color(0xFF9CA3AF);
}

class AppSpacing {
  AppSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
}

class AppFontSize {
  AppFontSize._();

  static const double xs = 12;
  static const double sm = 14;
  static const double md = 16;
  static const double lg = 18;
  static const double xl = 22;
  static const double xxl = 26;
  static const double xxxl = 34;
}

class AppBorderRadius {
  AppBorderRadius._();

  static const double sm = 6;
  static const double md = 10;
  static const double lg = 14;
  static const double xl = 20;
  static const double full = 9999;

  static BorderRadius get smAll => BorderRadius.circular(sm);
  static BorderRadius get mdAll => BorderRadius.circular(md);
  static BorderRadius get lgAll => BorderRadius.circular(lg);
  static BorderRadius get xlAll => BorderRadius.circular(xl);
  static BorderRadius get fullAll => BorderRadius.circular(full);
}

/// App theme configuration
ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      secondary: AppColors.accent,
      surface: AppColors.surface,
      error: AppColors.error,
    ),
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.text,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontSize: AppFontSize.lg,
        fontWeight: FontWeight.w600,
        color: AppColors.text,
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.tabBarBackground,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.tabIconDefault,
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: AppBorderRadius.lgAll,
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: AppBorderRadius.lgAll,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xl,
          vertical: AppSpacing.md,
        ),
        textStyle: const TextStyle(
          fontSize: AppFontSize.md,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary),
        shape: RoundedRectangleBorder(
          borderRadius: AppBorderRadius.lgAll,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xl,
          vertical: AppSpacing.md,
        ),
        textStyle: const TextStyle(
          fontSize: AppFontSize.md,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      border: OutlineInputBorder(
        borderRadius: AppBorderRadius.mdAll,
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppBorderRadius.mdAll,
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppBorderRadius.mdAll,
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
    ),
  );
}
