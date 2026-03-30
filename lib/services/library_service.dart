import 'package:plantapp/constants/api.dart';
import 'package:plantapp/services/api_client.dart';

/// Plant encyclopedia service — Turso DB search
class LibraryService {
  LibraryService._();
  static final instance = LibraryService._();

  final _api = ApiClient.instance;

  /// Search plants by name (debounce on UI side)
  Future<List<LibraryPlant>> search(String query) async {
    if (query.length < 2) return [];
    final data = await _api.get<Map<String, dynamic>>(
      '${PlantDBEndpoints.search}?q=${Uri.encodeComponent(query)}',
    );
    final plants = (data['plants'] as List<dynamic>?) ?? [];
    return plants
        .map((p) => LibraryPlant.fromJson(p as Map<String, dynamic>))
        .toList();
  }

  /// Get plant detail by ID
  Future<Map<String, dynamic>> getDetail(String id) async {
    return await _api.get<Map<String, dynamic>>(PlantDBEndpoints.detail(id));
  }

  /// Get DB stats (total count)
  Future<int> getPlantCount() async {
    final data =
        await _api.get<Map<String, dynamic>>(PlantDBEndpoints.stats);
    return (data['total_plants'] as int?) ?? 0;
  }
}

/// Turso DB plant entry
class LibraryPlant {
  final int id;
  final String scientific;
  final String? commonName;
  final String? family;
  final String? imageUrl;
  final String? careLevel;
  final String? watering;
  final bool? indoor;

  const LibraryPlant({
    required this.id,
    required this.scientific,
    this.commonName,
    this.family,
    this.imageUrl,
    this.careLevel,
    this.watering,
    this.indoor,
  });

  factory LibraryPlant.fromJson(Map<String, dynamic> json) => LibraryPlant(
        id: json['id'] as int? ?? 0,
        scientific: json['scientific_name'] as String? ?? '',
        commonName: json['common_name'] as String?,
        family: json['family'] as String?,
        imageUrl: json['default_image'] as String?,
        careLevel: json['care_level'] as String?,
        watering: json['watering'] as String?,
        indoor: json['indoor'] as bool?,
      );

  String get displayName => commonName ?? scientific;
}
