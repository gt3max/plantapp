import 'package:plantapp/constants/api.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/api_client.dart';

/// Plant API service — library, save, delete, identify.
class PlantService {
  PlantService._();
  static final instance = PlantService._();

  final _api = ApiClient.instance;

  /// Get user's plant library (all plants including device plants)
  Future<List<PlantEntry>> getLibrary() async {
    final data = await _api.get<Map<String, dynamic>>(PlantEndpoints.library);
    final plants = (data['plants'] as List<dynamic>?) ?? [];
    return plants
        .map((p) => PlantEntry.fromJson(p as Map<String, dynamic>))
        .toList();
  }

  /// Get only user-collection plants (no device plants)
  Future<List<PlantEntry>> getMyPlants() async {
    final all = await getLibrary();
    return all
        .where((p) =>
            p.deviceId == 'user-collection' &&
            p.archived != true &&
            p.deleted != true)
        .toList();
  }

  /// Get all library plants (including device plants, for admin view)
  Future<List<PlantEntry>> getAllPlants() async {
    final all = await getLibrary();
    return all.where((p) => p.deleted != true).toList();
  }

  /// Identify plant from base64 image
  Future<List<IdentifyResult>> identify(String base64Image) async {
    final data = await _api.post<Map<String, dynamic>>(
      PlantEndpoints.identify,
      {'image': base64Image},
    );
    final results = (data['results'] as List<dynamic>?) ?? [];
    return results
        .map((r) => IdentifyResult.fromJson(r as Map<String, dynamic>))
        .where((r) => r.score >= 1) // Filter low confidence
        .toList();
  }

  /// Save plant to user collection
  Future<void> savePlant(SavePlantInput input) async {
    await _api.post<Map<String, dynamic>>(
      PlantEndpoints.save,
      input.toJson(),
    );
  }

  /// Delete plant from user collection
  Future<void> deletePlant(String plantId, {String deviceId = 'user-collection'}) async {
    await _api.delete<Map<String, dynamic>>(
      '/plants/$deviceId?plant_id=${Uri.encodeComponent(plantId)}',
    );
  }
}
