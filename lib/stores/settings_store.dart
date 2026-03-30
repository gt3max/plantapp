import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Settings state
class SettingsState {
  final String temperatureUnit; // 'celsius' | 'fahrenheit'
  final String lengthUnit; // 'cm' | 'in'
  final bool notificationsEnabled;
  final bool isLoaded;

  const SettingsState({
    this.temperatureUnit = 'celsius',
    this.lengthUnit = 'cm',
    this.notificationsEnabled = true,
    this.isLoaded = false,
  });

  SettingsState copyWith({
    String? temperatureUnit,
    String? lengthUnit,
    bool? notificationsEnabled,
    bool? isLoaded,
  }) =>
      SettingsState(
        temperatureUnit: temperatureUnit ?? this.temperatureUnit,
        lengthUnit: lengthUnit ?? this.lengthUnit,
        notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
        isLoaded: isLoaded ?? this.isLoaded,
      );
}

class SettingsNotifier extends StateNotifier<SettingsState> {
  SettingsNotifier() : super(const SettingsState());

  static const _tempKey = 'temperatureUnit';
  static const _lengthKey = 'lengthUnit';
  static const _notifKey = 'notificationsEnabled';

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    state = SettingsState(
      temperatureUnit: prefs.getString(_tempKey) ?? 'celsius',
      lengthUnit: prefs.getString(_lengthKey) ?? 'cm',
      notificationsEnabled: prefs.getBool(_notifKey) ?? true,
      isLoaded: true,
    );
  }

  Future<void> setTemperatureUnit(String unit) async {
    state = state.copyWith(temperatureUnit: unit);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tempKey, unit);
  }

  Future<void> setLengthUnit(String unit) async {
    state = state.copyWith(lengthUnit: unit);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lengthKey, unit);
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    state = state.copyWith(notificationsEnabled: enabled);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_notifKey, enabled);
  }
}

final settingsProvider =
    StateNotifierProvider<SettingsNotifier, SettingsState>((ref) {
  return SettingsNotifier();
});
