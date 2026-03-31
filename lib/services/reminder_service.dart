import 'dart:convert';
import 'dart:io';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:plantapp/services/geolocation_service.dart';

/// Watering reminder service — local notifications with seasonal adjustment.
class ReminderService {
  ReminderService._();
  static final instance = ReminderService._();

  final _plugin = FlutterLocalNotificationsPlugin();
  static const _storageKey = 'plantapp:watering_reminders';
  bool _initialized = false;

  /// Initialize notification plugin (call once at app startup).
  Future<void> initialize() async {
    if (_initialized) return;

    tz_data.initializeTimeZones();

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: false,
      requestSoundPermission: true,
    );

    await _plugin.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
    );

    // Android notification channel
    if (Platform.isAndroid) {
      await _plugin
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(const AndroidNotificationChannel(
            'watering',
            'Watering Reminders',
            description: 'Reminders to water your plants',
            importance: Importance.high,
          ));
    }

    _initialized = true;
  }

  /// Request notification permissions. Returns true if granted.
  Future<bool> requestPermissions() async {
    if (Platform.isIOS) {
      final result = await _plugin
          .resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>()
          ?.requestPermissions(alert: true, badge: false, sound: true);
      return result ?? false;
    }
    return true; // Android grants by default
  }

  /// Schedule a watering reminder for a plant.
  Future<void> scheduleWateringReminder({
    required String plantId,
    required String plantName,
    required int baseDays,
  }) async {
    await cancelReminder(plantId);

    final latitude = GeolocationService.instance.cachedLatitude;
    final days = GeolocationService.getSeasonalWateringDays(baseDays, latitude);
    final notifId = plantId.hashCode.abs() % 100000;

    await _plugin.zonedSchedule(
      notifId,
      'Time to water $plantName',
      'It\'s been ~$days days since last watering',
      _tzNow().add(Duration(days: days)),
      NotificationDetails(
        android: const AndroidNotificationDetails(
          'watering',
          'Watering Reminders',
          channelDescription: 'Reminders to water your plants',
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: const DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
      payload: plantId,
    );

    // Save record
    final store = await _loadStore();
    store[plantId] = {
      'notifId': notifId,
      'plantId': plantId,
      'plantName': plantName,
      'baseDays': baseDays,
      'latitude': latitude,
      'scheduledAt': DateTime.now().toIso8601String(),
    };
    await _saveStore(store);
  }

  /// Cancel a scheduled reminder for a plant.
  Future<void> cancelReminder(String plantId) async {
    final store = await _loadStore();
    final record = store[plantId];
    if (record != null) {
      final notifId = record['notifId'] as int?;
      if (notifId != null) {
        await _plugin.cancel(notifId);
      }
      store.remove(plantId);
      await _saveStore(store);
    }
  }

  /// Reschedule all stored reminders (after app restart or season change).
  Future<void> rescheduleAll() async {
    final store = await _loadStore();
    final currentLatitude = GeolocationService.instance.cachedLatitude;

    for (final entry in store.entries.toList()) {
      final record = entry.value;
      final plantId = record['plantId'] as String? ?? entry.key;
      final plantName = record['plantName'] as String? ?? 'Plant';
      final baseDays = record['baseDays'] as int? ?? 7;

      // Cancel old
      final oldNotifId = record['notifId'] as int?;
      if (oldNotifId != null) {
        await _plugin.cancel(oldNotifId);
      }

      // Reschedule with current season
      final lat = (record['latitude'] as num?)?.toDouble() ?? currentLatitude;
      final days = GeolocationService.getSeasonalWateringDays(baseDays, lat);
      final notifId = plantId.hashCode.abs() % 100000;

      await _plugin.zonedSchedule(
        notifId,
        'Time to water $plantName',
        'It\'s been ~$days days since last watering',
        _tzNow().add(Duration(days: days)),
        NotificationDetails(
          android: const AndroidNotificationDetails(
            'watering',
            'Watering Reminders',
            channelDescription: 'Reminders to water your plants',
            importance: Importance.high,
            priority: Priority.high,
          ),
          iOS: const DarwinNotificationDetails(),
        ),
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
        payload: plantId,
      );

      store[plantId] = {
        ...record,
        'notifId': notifId,
        'latitude': lat,
        'scheduledAt': DateTime.now().toIso8601String(),
      };
    }
    await _saveStore(store);
  }

  /// Get all stored reminder records.
  Future<Map<String, dynamic>> getReminders() async => _loadStore();

  // ─── Internal ────────────────────────────────────────────────

  tz.TZDateTime _tzNow() => tz.TZDateTime.now(tz.local);

  Future<Map<String, Map<String, dynamic>>> _loadStore() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);
    if (raw == null) return {};
    final decoded = json.decode(raw) as Map<String, dynamic>;
    return decoded.map((k, v) => MapEntry(k, v as Map<String, dynamic>));
  }

  Future<void> _saveStore(Map<String, Map<String, dynamic>> store) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_storageKey, json.encode(store));
  }
}
