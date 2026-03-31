// Plant models — matches React Native src/types/plant.ts

class PlantEntry {
  final String plantId;
  final String? scientific;
  final String? commonName;
  final String? family;
  final String? imageUrl;
  final String? preset;
  final int? startPct;
  final int? stopPct;
  final bool? poisonousToPets;
  final bool? poisonousToHumans;
  final String? toxicityNote;
  final bool active;
  final String deviceId;
  final bool? archived;
  final bool? deleted;

  const PlantEntry({
    required this.plantId,
    this.scientific,
    this.commonName,
    this.family,
    this.imageUrl,
    this.preset,
    this.startPct,
    this.stopPct,
    this.poisonousToPets,
    this.poisonousToHumans,
    this.toxicityNote,
    this.active = false,
    this.deviceId = 'user-collection',
    this.archived,
    this.deleted,
  });

  factory PlantEntry.fromJson(Map<String, dynamic> json) => PlantEntry(
        plantId: json['plant_id'] as String? ?? '',
        scientific: json['scientific'] as String?,
        commonName: json['common_name'] as String?,
        family: json['family'] as String?,
        imageUrl: json['image_url'] as String?,
        preset: json['preset'] as String?,
        startPct: json['start_pct'] as int?,
        stopPct: json['stop_pct'] as int?,
        poisonousToPets: json['poisonous_to_pets'] as bool?,
        poisonousToHumans: json['poisonous_to_humans'] as bool?,
        toxicityNote: json['toxicity_note'] as String?,
        active: json['active'] as bool? ?? false,
        deviceId: json['device_id'] as String? ?? 'user-collection',
        archived: json['archived'] as bool?,
        deleted: json['deleted'] as bool?,
      );

  String get displayName => commonName ?? scientific ?? 'Unknown plant';
}

class IdentifyResult {
  final String id;
  final String scientific;
  final List<String> commonNames;
  final String family;
  final String genus;
  final double score;
  final List<String> images;
  final IdentifyCareSummary care;
  final ToxicityInfo? toxicity;
  final Map<String, dynamic>? enrichment;

  const IdentifyResult({
    required this.id,
    required this.scientific,
    required this.commonNames,
    required this.family,
    required this.genus,
    required this.score,
    required this.images,
    required this.care,
    this.toxicity,
    this.enrichment,
  });

  factory IdentifyResult.fromJson(Map<String, dynamic> json) => IdentifyResult(
        id: json['id'] as String? ?? '',
        scientific: json['scientific'] as String? ?? '',
        commonNames: (json['commonNames'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        family: json['family'] as String? ?? '',
        genus: json['genus'] as String? ?? '',
        score: (json['score'] as num?)?.toDouble() ?? 0,
        images: (json['images'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        care: IdentifyCareSummary.fromJson(
            json['care'] as Map<String, dynamic>? ?? {}),
        toxicity: json['toxicity'] != null
            ? ToxicityInfo.fromJson(json['toxicity'] as Map<String, dynamic>)
            : null,
        enrichment: json['enrichment'] as Map<String, dynamic>?,
      );
}

class IdentifyCareSummary {
  final String preset;
  final int startPct;
  final int stopPct;
  final String watering;
  final String light;
  final String temperature;
  final String humidity;
  final String tips;

  const IdentifyCareSummary({
    required this.preset,
    required this.startPct,
    required this.stopPct,
    required this.watering,
    required this.light,
    required this.temperature,
    required this.humidity,
    required this.tips,
  });

  factory IdentifyCareSummary.fromJson(Map<String, dynamic> json) =>
      IdentifyCareSummary(
        preset: json['preset'] as String? ?? 'Standard',
        startPct: json['start_pct'] as int? ?? 35,
        stopPct: json['stop_pct'] as int? ?? 55,
        watering: json['watering'] as String? ?? '',
        light: json['light'] as String? ?? '',
        temperature: json['temperature'] as String? ?? '',
        humidity: json['humidity'] as String? ?? '',
        tips: json['tips'] as String? ?? '',
      );
}

class ToxicityInfo {
  final bool poisonousToPets;
  final bool poisonousToHumans;
  final String toxicityNote;

  const ToxicityInfo({
    required this.poisonousToPets,
    required this.poisonousToHumans,
    required this.toxicityNote,
  });

  factory ToxicityInfo.fromJson(Map<String, dynamic> json) => ToxicityInfo(
        poisonousToPets: json['poisonous_to_pets'] as bool? ?? false,
        poisonousToHumans: json['poisonous_to_humans'] as bool? ?? false,
        toxicityNote: json['toxicity_note'] as String? ?? '',
      );
}

class SavePlantInput {
  final String? deviceId;
  final Map<String, dynamic> plant;
  final int? wateringFreqDays;

  const SavePlantInput({
    this.deviceId,
    required this.plant,
    this.wateringFreqDays,
  });

  Map<String, dynamic> toJson() => {
        if (deviceId != null) 'device_id': deviceId,
        'plant': plant,
      };
}
