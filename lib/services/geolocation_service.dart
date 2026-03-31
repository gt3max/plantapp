import 'dart:convert';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';
import 'package:http/http.dart' as http;

/// Geolocation service — GPS, weather, outdoor months, seasonal coefficients.
class GeolocationService {
  GeolocationService._();
  static final instance = GeolocationService._();

  LocationData? _cache;
  DateTime? _cacheTime;
  static const _cacheDuration = Duration(hours: 1);

  // Northern hemisphere: Jan=winter(3.0) → Jun-Aug=summer(1.0) → Dec=winter(2.8)
  static const _seasonCoeffsNorth = [3.0, 2.8, 2.1, 1.6, 1.2, 1.0, 1.0, 1.0, 1.2, 1.6, 2.1, 2.8];

  /// Get season coefficients adjusted for hemisphere.
  /// Southern hemisphere (lat < 0) shifts by 6 months.
  static List<double> getSeasonCoefficients(double? latitude) {
    if (latitude != null && latitude < 0) {
      return [..._seasonCoeffsNorth.sublist(6), ..._seasonCoeffsNorth.sublist(0, 6)];
    }
    return List.of(_seasonCoeffsNorth);
  }

  /// Get adjusted watering days for current month.
  static int getSeasonalWateringDays(int baseDays, double? latitude) {
    final month = DateTime.now().month - 1; // 0-indexed
    final coeffs = getSeasonCoefficients(latitude);
    return (baseDays * coeffs[month]).round();
  }

  /// Cached latitude (for reminders etc.)
  double? get cachedLatitude => _cache?.latitude;

  /// Load location data (with 1h cache).
  Future<LocationData> getLocationData() async {
    // Check cache
    if (_cache != null && _cacheTime != null &&
        DateTime.now().difference(_cacheTime!) < _cacheDuration) {
      return _cache!;
    }

    try {
      // Check permission
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return LocationData.error('Location permission denied');
      }

      // Get position
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.low,
      );
      final lat = position.latitude;
      final lon = position.longitude;

      // Fetch all in parallel
      final results = await Future.wait([
        _fetchCurrentWeather(lat, lon),
        _fetchMonthlyAverages(lat, lon),
        _reverseGeocode(lat, lon),
      ]);

      final currentTemp = results[0] as double;
      final monthlyTemps = results[1] as List<double>;
      final cityName = results[2] as String;

      final minWinterTemp = monthlyTemps.reduce((a, b) => a < b ? a : b);
      final hardinessZone = _getHardinessZone(minWinterTemp);

      final data = LocationData(
        latitude: lat,
        longitude: lon,
        cityName: cityName,
        currentTemp: currentTemp,
        monthlyAvgTemps: monthlyTemps,
        hardinessZone: hardinessZone,
      );

      _cache = data;
      _cacheTime = DateTime.now();
      return data;
    } catch (e) {
      return LocationData.error(e.toString());
    }
  }

  // ─── Outdoor months ──────────────────────────────────────────

  /// Calculate outdoor months based on frost limit and monthly temps.
  static OutdoorMonths getOutdoorMonths(double frostLimitC, List<double> monthlyAvgTemps) {
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    final potted = <String>[];
    final inGround = <String>[];

    for (var i = 0; i < 12 && i < monthlyAvgTemps.length; i++) {
      final temp = monthlyAvgTemps[i];
      if (temp > frostLimitC + 5) potted.add(monthNames[i]);
      if (temp > frostLimitC + 2) inGround.add(monthNames[i]);
    }

    return OutdoorMonths(potted: potted, inGround: inGround);
  }

  /// Format month list into range: "May – September" or "Year-round".
  static String formatMonthRange(List<String> months) {
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    const monthShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    if (months.isEmpty) return 'Not recommended';
    if (months.length == 12) return 'Year-round';
    if (months.length == 1) return months.first;

    // Check if consecutive
    final indices = months.map((m) => monthNames.indexOf(m)).toList();
    var consecutive = true;
    for (var i = 1; i < indices.length; i++) {
      if (indices[i] != indices[i - 1] + 1) {
        consecutive = false;
        break;
      }
    }

    if (consecutive) {
      return '${months.first} – ${months.last}';
    }

    return months.map((m) => monthShort[monthNames.indexOf(m)]).join(', ');
  }

  // ─── API calls ───────────────────────────────────────────────

  Future<double> _fetchCurrentWeather(double lat, double lon) async {
    final url = 'https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m';
    final response = await http.get(Uri.parse(url));
    if (response.statusCode != 200) throw Exception('Weather API error: ${response.statusCode}');
    final data = json.decode(response.body) as Map<String, dynamic>;
    return (data['current']?['temperature_2m'] as num?)?.toDouble() ?? 0;
  }

  Future<List<double>> _fetchMonthlyAverages(double lat, double lon) async {
    final url = 'https://archive-api.open-meteo.com/v1/archive'
        '?latitude=$lat&longitude=$lon'
        '&start_date=2024-01-01&end_date=2024-12-31'
        '&daily=temperature_2m_mean&timezone=auto';
    final response = await http.get(Uri.parse(url));
    if (response.statusCode != 200) throw Exception('Archive API error: ${response.statusCode}');
    final data = json.decode(response.body) as Map<String, dynamic>;
    final dailyTemps = (data['daily']?['temperature_2m_mean'] as List<dynamic>?)
        ?.map((t) => (t as num?)?.toDouble())
        .toList() ?? [];

    // Aggregate daily → monthly averages
    const daysPerMonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    final monthlyAvgs = <double>[];
    var dayIndex = 0;
    for (var m = 0; m < 12; m++) {
      final chunk = dailyTemps
          .skip(dayIndex)
          .take(daysPerMonth[m])
          .where((t) => t != null)
          .cast<double>()
          .toList();
      if (chunk.isNotEmpty) {
        monthlyAvgs.add(
            (chunk.reduce((a, b) => a + b) / chunk.length * 10).round() / 10);
      } else {
        monthlyAvgs.add(0);
      }
      dayIndex += daysPerMonth[m];
    }

    return monthlyAvgs;
  }

  Future<String> _reverseGeocode(double lat, double lon) async {
    try {
      final placemarks = await placemarkFromCoordinates(lat, lon);
      if (placemarks.isNotEmpty) {
        return placemarks.first.locality ?? placemarks.first.administrativeArea ?? '';
      }
    } catch (_) {}
    return '';
  }

  // ─── Hardiness zone ──────────────────────────────────────────

  static String _getHardinessZone(double minWinterTemp) {
    const zones = [
      (-51.1, '1a'), (-48.3, '1b'), (-45.6, '2a'), (-42.8, '2b'),
      (-40.0, '3a'), (-37.2, '3b'), (-34.4, '4a'), (-31.7, '4b'),
      (-28.9, '5a'), (-26.1, '5b'), (-23.3, '6a'), (-20.6, '6b'),
      (-17.8, '7a'), (-15.0, '7b'), (-12.2, '8a'), (-9.4, '8b'),
      (-6.7, '9a'), (-3.9, '9b'), (-1.1, '10a'), (1.7, '10b'),
      (4.4, '11a'), (7.2, '11b'), (10.0, '12a'), (12.8, '12b'),
      (15.6, '13a'), (18.3, '13b'),
    ];
    var zone = '1a';
    for (final entry in zones) {
      if (minWinterTemp >= entry.$1) zone = entry.$2;
    }
    return zone;
  }
}

// ─── Data classes ────────────────────────────────────────────────

class LocationData {
  final double latitude;
  final double longitude;
  final String cityName;
  final double currentTemp;
  final List<double> monthlyAvgTemps;
  final String hardinessZone;
  final bool isLoading;
  final String? errorMsg;

  const LocationData({
    required this.latitude,
    required this.longitude,
    required this.cityName,
    required this.currentTemp,
    required this.monthlyAvgTemps,
    required this.hardinessZone,
    this.isLoading = false,
    this.errorMsg,
  });

  factory LocationData.error(String message) => LocationData(
        latitude: 0,
        longitude: 0,
        cityName: '',
        currentTemp: 0,
        monthlyAvgTemps: [],
        hardinessZone: '',
        errorMsg: message,
      );

  bool get hasData => monthlyAvgTemps.length == 12;
}

class OutdoorMonths {
  final List<String> potted;
  final List<String> inGround;

  const OutdoorMonths({required this.potted, required this.inGround});
}
