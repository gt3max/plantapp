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
    // API returns either 'plants' or 'results' depending on endpoint version
    final plants = (data['plants'] as List<dynamic>?) ??
        (data['results'] as List<dynamic>?) ??
        [];
    return plants
        .map((p) => LibraryPlant.fromJson(p as Map<String, dynamic>))
        .toList();
  }

  /// Get plant detail by ID
  Future<Map<String, dynamic>> getDetail(String id) async {
    return await _api.get<Map<String, dynamic>>(PlantDBEndpoints.detail(id));
  }

  /// Fixed list of popular plants for Library home screen
  static const _featuredIds = [
    'monstera_deliciosa', 'epipremnum_aureum', 'dracaena_trifasciata',
    'crassula_ovata', 'spathiphyllum_wallisii', 'ficus_lyrata',
    'ficus_elastica', 'aloe_vera', 'zamioculcas_zamiifolia',
    'chlorophytum_comosum', 'phalaenopsis_amabilis', 'calathea_orbifolia',
    'dracaena_marginata', 'philodendron_hederaceum', 'monstera_adansonii',
    'ocimum_basilicum', 'rosmarinus_officinalis', 'solanum_lycopersicum',
    'nephrolepis_exaltata', 'anthurium_andraeanum', 'strelitzia_nicolai',
    'echeveria_elegans', 'mentha_spicata', 'dieffenbachia_seguine',
    'lavandula_angustifolia', 'dracaena_fragrans', 'dypsis_lutescens',
    'cycas_revoluta',
  ];

  /// Get featured plants for Library home screen (fixed popular list, single API call)
  Future<List<LibraryPlant>> getFeatured({int limit = 30}) async {
    final ids = _featuredIds.take(limit).join(',');
    final data = await _api.get<Map<String, dynamic>>(
      '${PlantDBEndpoints.search}?ids=$ids',
    );
    final plants = (data['plants'] as List<dynamic>?) ??
        (data['results'] as List<dynamic>?) ??
        [];
    // Sort results to match our preferred order
    final idOrder = {for (var i = 0; i < _featuredIds.length; i++) _featuredIds[i]: i};
    final result = plants
        .map((p) => LibraryPlant.fromJson(p as Map<String, dynamic>))
        .toList();
    result.sort((a, b) => (idOrder[a.detailId] ?? 99).compareTo(idOrder[b.detailId] ?? 99));
    return result;
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
  final String? plantIdStr; // Turso uses string IDs like "monstera_deliciosa"
  final String scientific;
  final String? commonName;
  final String? family;
  final String? imageUrl;
  final String? careLevel;
  final String? watering;
  final bool? indoor;

  const LibraryPlant({
    required this.id,
    this.plantIdStr,
    required this.scientific,
    this.commonName,
    this.family,
    this.imageUrl,
    this.careLevel,
    this.watering,
    this.indoor,
  });

  /// Get the ID to use for navigation/detail lookup
  String get detailId => plantIdStr ?? id.toString();

  factory LibraryPlant.fromJson(Map<String, dynamic> json) => LibraryPlant(
        id: json['plant_id'] is int
            ? json['plant_id'] as int
            : 0,
        plantIdStr: json['plant_id'] is String ? json['plant_id'] as String : null,
        scientific: (json['scientific_name'] as String?) ??
            (json['scientific'] as String?) ??
            '',
        commonName: json['common_name'] as String?,
        family: json['family'] as String?,
        imageUrl: (json['default_image'] as String?) ??
            (json['image_url'] as String?),
        careLevel: json['care_level'] as String?,
        watering: (json['watering'] as String?) ??
            (json['water_frequency'] as String?),
        indoor: json['indoor'] is bool
            ? json['indoor'] as bool
            : json['indoor'] == 1,
      );

  String get displayName => commonName ?? scientific;
}
