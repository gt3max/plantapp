import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/constants/popular_plants.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';
import 'package:plantapp/services/library_service.dart';
import 'package:plantapp/services/geolocation_service.dart';
import 'package:plantapp/stores/settings_store.dart';
import 'package:plantapp/widgets/plant_indicators.dart';

// Section accent colors (matching RN)
const _sectionAccent = {
  'water': Color(0xFF3B82F6),
  'soil': Color(0xFF92400E),
  'fertilizing': Color(0xFF16A34A),
  'light': Color(0xFFF59E0B),
  'humidity': Color(0xFF0EA5E9),
  'temperature': Color(0xFFEF4444),
  'outdoor': Color(0xFF22C55E),
  'toxicity': Color(0xFFEF4444),
  'pruning': Color(0xFF6B7280),
  'harvest': Color(0xFFF97316),
  'propagation': Color(0xFF8B5CF6),
  'difficulty': Color(0xFFF59E0B),
  'size': Color(0xFF7C3AED),
  'lifecycle': Color(0xFF8B5CF6),
  'used_for': Color(0xFF10B981),
  'taxonomy': Color(0xFF6B7280),
  'companions': Color(0xFF10B981),
};

// Group/tab definitions
const _groupDefs = [
  ('care', 'Care'),
  ('environment', 'Environment'),
  ('safety', 'Toxicity'),
  ('growing', 'Growing'),
  ('about', 'About'),
  ('companions', 'Companions'),
];

// Month names
const _months = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

// Preset care data (matches RN presets.ts)
const _presetCare = {
  'Succulents': _PresetCare(
    watering: 'Every 2-3 weeks',
    light: 'Bright direct or indirect light',
    temperature: '18-27°C',
    humidity: 'Low (30-40%)',
    soil: 'Well-draining cactus/succulent mix',
    repot: 'Every 2-3 years',
    fertilizer: 'Once in spring and summer',
    fertilizerSeason: 'Spring-Summer only',
    tips: 'Let soil dry completely between waterings.',
  ),
  'Standard': _PresetCare(
    watering: 'Every 7-10 days',
    light: 'Bright indirect light',
    temperature: '18-24°C',
    humidity: 'Average (40-60%)',
    soil: 'Standard potting mix with perlite',
    repot: 'Every 1-2 years',
    fertilizer: 'Monthly during growing season',
    fertilizerSeason: 'Spring-Summer',
    tips: 'Water when top inch of soil is dry.',
  ),
  'Tropical': _PresetCare(
    watering: 'Every 5-7 days',
    light: 'Bright indirect, no direct sun',
    temperature: '20-28°C',
    humidity: 'High (60-80%)',
    soil: 'Rich, well-draining tropical mix',
    repot: 'Every 1-2 years',
    fertilizer: 'Every 2 weeks during growing season',
    fertilizerSeason: 'Spring-Autumn',
    tips: 'Keep soil consistently moist but not soggy.',
  ),
  'Herbs': _PresetCare(
    watering: 'Every 2-3 days',
    light: 'Full sun (6+ hours)',
    temperature: '15-25°C',
    humidity: 'Average (40-60%)',
    soil: 'Light, well-draining herb mix',
    repot: 'When root-bound',
    fertilizer: 'Every 2 weeks',
    fertilizerSeason: 'All growing season',
    tips: 'Harvest regularly to promote bushier growth.',
  ),
};

class _PresetCare {
  final String watering;
  final String light;
  final String temperature;
  final String humidity;
  final String soil;
  final String repot;
  final String fertilizer;
  final String fertilizerSeason;
  final String tips;

  const _PresetCare({
    required this.watering,
    required this.light,
    required this.temperature,
    required this.humidity,
    required this.soil,
    required this.repot,
    required this.fertilizer,
    required this.fertilizerSeason,
    required this.tips,
  });
}

class PlantDetailScreen extends ConsumerStatefulWidget {
  const PlantDetailScreen({super.key, required this.plantId});
  final String plantId;

  @override
  ConsumerState<PlantDetailScreen> createState() => _PlantDetailScreenState();
}

class _PlantDetailScreenState extends ConsumerState<PlantDetailScreen> {
  final _plantService = PlantService.instance;
  final _libraryService = LibraryService.instance;
  final _geoService = GeolocationService.instance;
  final _scrollController = ScrollController();

  // Data — 3 sources (priority: user > Turso DB > popular_plants constant)
  PlantEntry? _userPlant;
  Map<String, dynamic>? _dbDetail;
  PopularPlant? _lib; // rich hardcoded data for 6 prototype plants
  LocationData? _locationData;
  bool _isLoading = true;

  // UI
  String _activeGroup = 'care';
  bool _descExpanded = false;
  bool _isSaving = false;
  bool _isSaved = false;

  // Section keys for scroll tracking
  final _sectionKeys = <String, GlobalKey>{};

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadPlant();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  GlobalKey _keyFor(String section) {
    return _sectionKeys.putIfAbsent(section, () => GlobalKey());
  }

  Future<void> _loadPlant() async {
    setState(() => _isLoading = true);
    try {
      // Source 3: Popular plants constant (instant, no network)
      final lib = getPopularPlant(widget.plantId);
      if (lib != null && mounted) setState(() => _lib = lib);

      // Source 1: User's plant collection
      final plants = await _plantService.getMyPlants();
      final userPlant = plants.where((p) => p.plantId == widget.plantId).firstOrNull;
      if (userPlant != null) {
        if (mounted) setState(() => _userPlant = userPlant);
      }

      // Source 2: Turso DB detail
      try {
        final detail = await _libraryService.getDetail(widget.plantId);
        if (mounted) setState(() => _dbDetail = detail);
      } catch (_) {
        final scientific = _userPlant?.scientific ?? lib?.scientific;
        if (scientific != null && scientific.isNotEmpty) {
          try {
            final results = await _libraryService.search(scientific);
            if (results.isNotEmpty) {
              final detail = await _libraryService.getDetail(results.first.id.toString());
              if (mounted) setState(() => _dbDetail = detail);
            }
          } catch (_) {}
        }
      }

      // Load location (non-blocking)
      _geoService.getLocationData().then((data) {
        if (mounted) setState(() => _locationData = data);
      });
    } catch (e) {
      // Silent — show what we have
    }
    if (mounted) setState(() => _isLoading = false);
  }

  // ─── Derived data ────────────────────────────────────────────

  String get _title {
    if (_userPlant != null) return _userPlant!.displayName;
    final db = _dbDetail;
    if (db != null) {
      final names = db['common_names'] as Map<String, dynamic>?;
      final enNames = (names?['en'] as List<dynamic>?);
      if (enNames != null && enNames.isNotEmpty) return enNames.first as String;
      return (db['scientific'] as String?) ?? _lib?.commonName ?? 'Plant';
    }
    return _lib?.commonName ?? 'Plant';
  }

  String get _scientific {
    return _userPlant?.scientific ?? (_dbDetail?['scientific'] as String?) ?? _lib?.scientific ?? '';
  }

  String? get _imageUrl {
    return _userPlant?.imageUrl ?? (_dbDetail?['image_url'] as String?) ?? _lib?.imageUrl;
  }

  String? get _description =>
      (_dbDetail?['description'] as String?)?.isNotEmpty == true
          ? _dbDetail!['description'] as String
          : _lib?.description;

  String get _preset {
    return _userPlant?.preset ?? (_dbDetail?['preset'] as String?) ?? _lib?.preset ?? 'Standard';
  }

  _PresetCare get _care => _presetCare[_preset] ?? _presetCare['Standard']!;

  bool get _isInCollection => _userPlant != null;

  // DB care helpers — Turso field names differ from RN popular-plants
  Map<String, dynamic> get _dbCare =>
      (_dbDetail?['care'] as Map<String, dynamic>?) ?? {};

  // Map friendly names to actual Turso care field names
  String _dbCareStr(String key) {
    const fieldMap = {
      'watering': 'water_frequency',
      'watering_winter': 'water_winter',
      'watering_demand': 'water_demand',
      'light': 'light_preferred',
      'humidity': 'humidity_level',
      'repot': 'repot_frequency',
      'fertilizer': 'fertilizer_type',
      'soil': 'soil_types',
    };
    final dbKey = fieldMap[key] ?? key;
    return _dbCare[dbKey] as String? ?? '';
  }

  String _dbStr(String key) => _dbCare[key] as String? ?? '';
  int _dbInt(String key) => (_dbCare[key] as num?)?.toInt() ?? 0;
  List<String> _dbList(String key) {
    final val = _dbCare[key];
    if (val is List) return val.map((e) => e.toString()).toList();
    if (val is String && val.startsWith('[')) {
      try {
        return val.replaceAll('[', '').replaceAll(']', '').replaceAll('"', '').split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
      } catch (_) {}
    }
    return [];
  }

  int get _presetWateringDays {
    const days = {'Succulents': 10, 'Standard': 7, 'Tropical': 5, 'Herbs': 2};
    return days[_preset] ?? 7;
  }

  /// Current watering days (from lib data or seasonal adjustment)
  int get _currentWateringDays {
    if (_lib != null) {
      return _lib!.wateringFreqSummerDays > 0 ? _lib!.wateringFreqSummerDays : _presetWateringDays;
    }
    if (_locationData?.hasData == true) {
      return GeolocationService.getSeasonalWateringDays(_presetWateringDays, _locationData!.latitude);
    }
    return _presetWateringDays;
  }

  String get _plantType => _lib?.plantType ?? 'decorative';

  bool get _isToxic {
    return (_userPlant?.poisonousToPets == true) ||
        (_userPlant?.poisonousToHumans == true) ||
        (_dbCare['toxic_to_pets'] == true || _dbCare['toxic_to_pets'] == 1) ||
        (_dbCare['toxic_to_humans'] == true || _dbCare['toxic_to_humans'] == 1) ||
        (_lib?.poisonousToPets == true) ||
        (_lib?.poisonousToHumans == true);
  }

  String _fmtTemp(int celsius) {
    final settings = ref.read(settingsProvider);
    if (settings.temperatureUnit == 'fahrenheit') {
      return '${(celsius * 9 / 5 + 32).round()}°F';
    }
    return '$celsius°C';
  }

  // ─── Scroll tracking ────────────────────────────────────────

  void _onScroll() {
    // Track which group is visible
    const groupSections = {
      'care': ['water', 'soil', 'fertilizing'],
      'environment': ['light', 'humidity', 'temperature', 'outdoor'],
      'safety': ['toxicity'],
      'growing': ['pruning', 'propagation'],
      'about': ['difficulty', 'size', 'lifecycle', 'used_for', 'taxonomy'],
      'companions': ['companions'],
    };

    String? currentGroup;
    for (final entry in groupSections.entries) {
      for (final section in entry.value) {
        final key = _sectionKeys[section];
        if (key?.currentContext != null) {
          final box = key!.currentContext!.findRenderObject() as RenderBox?;
          if (box != null && box.attached) {
            final pos = box.localToGlobal(Offset.zero);
            if (pos.dy < 200) {
              currentGroup = entry.key;
            }
          }
        }
      }
    }

    if (currentGroup != null && currentGroup != _activeGroup) {
      setState(() => _activeGroup = currentGroup!);
    }
  }

  void _scrollToGroup(String groupKey) {
    const firstSection = {
      'care': 'water',
      'environment': 'light',
      'safety': 'toxicity',
      'growing': 'pruning',
      'about': 'difficulty',
      'companions': 'companions',
    };

    final section = firstSection[groupKey];
    if (section == null) return;
    final key = _sectionKeys[section];
    if (key?.currentContext != null) {
      setState(() => _activeGroup = groupKey);
      Scrollable.ensureVisible(
        key!.currentContext!,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        alignmentPolicy: ScrollPositionAlignmentPolicy.explicit,
      );
    }
  }

  // ─── Save to collection ──────────────────────────────────────

  Future<void> _addToCollection() async {
    setState(() => _isSaving = true);
    try {
      await _plantService.savePlant(SavePlantInput(
        plant: {
          'scientific': _scientific,
          'common_name': _title,
          'family': _dbDetail?['family'] as String? ?? '',
          'preset': _preset,
          'start_pct': _userPlant?.startPct ?? 35,
          'stop_pct': _userPlant?.stopPct ?? 55,
          'image_url': _imageUrl,
          'poisonous_to_pets': _isToxic,
          'poisonous_to_humans':
              _userPlant?.poisonousToHumans ?? (_dbDetail?['care']?['toxic_to_humans'] == true),
          'toxicity_note': _userPlant?.toxicityNote ?? '',
        },
      ));
      if (mounted) {
        setState(() {
          _isSaving = false;
          _isSaved = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to save plant')),
        );
      }
    }
  }

  // ─── Build ───────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Plant')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_userPlant == null && _dbDetail == null && _lib == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Plant')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.eco_outlined, size: 48, color: AppColors.textSecondary),
              const SizedBox(height: AppSpacing.md),
              Text('Plant not found',
                  style: TextStyle(fontSize: AppFontSize.lg, color: AppColors.textSecondary)),
              const SizedBox(height: AppSpacing.lg),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: Text('Go back', style: TextStyle(color: AppColors.primary)),
              ),
            ],
          ),
        ),
      );
    }

    final care = _care;

    return Scaffold(
      body: Stack(
        children: [
          CustomScrollView(
            controller: _scrollController,
            slivers: [
              // ═══ HERO IMAGE + APP BAR ═══
              SliverAppBar(
                expandedHeight: 300,
                pinned: true,
                title: Text(_title),
                flexibleSpace: FlexibleSpaceBar(
                  background: _imageUrl != null
                      ? Image.network(
                          _imageUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => _heroPlaceholder(),
                        )
                      : _heroPlaceholder(),
                ),
              ),

              // ═══ NAME + DESCRIPTION ═══
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _title,
                        style: TextStyle(
                          fontSize: AppFontSize.xxl,
                          fontWeight: FontWeight.w700,
                          color: AppColors.text,
                        ),
                      ),
                      if (_scientific.isNotEmpty && _scientific != _title)
                        Text(
                          _scientific,
                          style: TextStyle(
                            fontSize: AppFontSize.md,
                            fontStyle: FontStyle.italic,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      if (_description != null && _description!.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.md),
                        GestureDetector(
                          onTap: () => setState(() => _descExpanded = !_descExpanded),
                          child: Text(
                            _description!,
                            maxLines: _descExpanded ? null : 3,
                            overflow: _descExpanded ? null : TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: AppFontSize.sm,
                              color: AppColors.textSecondary,
                              height: 1.5,
                            ),
                          ),
                        ),
                        if (_description!.length > 150)
                          GestureDetector(
                            onTap: () => setState(() => _descExpanded = !_descExpanded),
                            child: Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                _descExpanded ? 'Show less' : 'Read more',
                                style: TextStyle(
                                  fontSize: AppFontSize.sm,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primary,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
              ),

              // ═══ BADGES ═══
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: _buildBadges(care),
                ),
              ),

              // ═══ STICKY TABS ═══
              SliverPersistentHeader(
                pinned: true,
                delegate: _StickyTabDelegate(
                  activeGroup: _activeGroup,
                  onTap: _scrollToGroup,
                ),
              ),

              // ═══ ALL SECTIONS ═══
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    // ══════ GROUP: Care ══════

                    // ── 1. Water (RN: InfoRow freq+demand, warning box, moisture) ──
                    _buildSection('water', 'Water', [
                      _InfoRow(
                        icon: Icons.water_drop_outlined,
                        text: 'Every ~$_currentWateringDays days in ${_months[DateTime.now().month - 1]}',
                        sub: (_lib?.wateringDemand.isNotEmpty == true ? '${_lib!.wateringDemand} demand'
                            : _dbCareStr('watering_demand').isNotEmpty ? '${_dbCareStr('watering_demand')} demand' : null),
                      ),
                      if (_lib?.wateringWarning.isNotEmpty == true)
                        InfoBox(text: _lib!.wateringWarning, variant: 'warning'),
                    ], guideLabel: 'Watering guide'),

                    // ── 2. Soil (RN: chips, pH bar, repot InfoRow) ──
                    _buildSection('soil', 'Soil', [
                      if (_lib?.soilTypes.isNotEmpty == true)
                        _ChipRow(chips: _lib!.soilTypes)
                      else if (_dbCareStr('soil').isNotEmpty)
                        _ChipRow(chips: [_dbCareStr('soil')]),
                      _InfoRow(
                        icon: Icons.swap_vert,
                        text: 'Repot: ${_dbCareStr('repot').isNotEmpty ? _dbCareStr('repot') : _lib?.care.repot.isNotEmpty == true ? _lib!.care.repot : care.repot}',
                        sub: 'Repotting',
                      ),
                    ], guideLabel: 'Repotting guide'),

                    // ── 3. Fertilizing (RN: seasonal logic — active/inactive) ──
                    _buildSection('fertilizing', 'Fertilizing', [
                      () {
                        final fertText = _dbCareStr('fertilizer').isNotEmpty
                            ? _dbCareStr('fertilizer')
                            : _lib?.care.fertilizer.isNotEmpty == true ? _lib!.care.fertilizer : care.fertilizer;
                        final seasonText = (_lib?.care.fertilizerSeason ?? care.fertilizerSeason).toLowerCase();
                        final m = DateTime.now().month - 1;
                        final isSpring = m >= 2 && m <= 4;
                        final isSummer = m >= 5 && m <= 7;
                        bool inSeason = true;
                        if (seasonText.contains('spring') && seasonText.contains('summer')) {
                          inSeason = isSpring || isSummer;
                        } else if (seasonText.contains('spring')) {
                          inSeason = isSpring;
                        }
                        if (seasonText.contains('winter') == false && (m <= 1 || m == 11)) {
                          inSeason = false;
                        }
                        return inSeason
                            ? _InfoRow(icon: Icons.eco_outlined, text: '$fertText \u2014 active season now', sub: _lib?.care.fertilizerSeason ?? care.fertilizerSeason)
                            : _InfoRow(icon: Icons.eco_outlined, text: 'No fertilizing needed in ${_months[m]}', sub: 'Resume in ${_lib?.care.fertilizerSeason ?? care.fertilizerSeason}');
                      }(),
                    ], guideLabel: 'Fertilizing guide'),

                    // ══════ GROUP: Environment ══════

                    // ── 4. Light (RN: LightLevelIndicator + InfoRow preferred) ──
                    _buildSection('light', 'Light', [
                      LightLevelIndicator(lightText: _dbCareStr('light').isNotEmpty ? _dbCareStr('light') : _lib?.care.light ?? care.light),
                      _InfoRow(
                        icon: Icons.wb_sunny_outlined,
                        text: _dbCareStr('light').isNotEmpty ? _dbCareStr('light') : _lib?.care.light ?? care.light,
                        sub: 'Preferred',
                      ),
                    ], guideLabel: 'Understanding light'),

                    // ── 5. Humidity (RN: HumidityBar only) ──
                    _buildSection('humidity', 'Air Humidity', [
                      HumidityBar(level: _dbCareStr('humidity').isNotEmpty ? _dbCareStr('humidity') : _lib?.care.humidity ?? care.humidity),
                    ], guideLabel: 'Managing humidity'),

                    // ── 6. Temperature (RN: TempRangeBar + InfoRow survival) ──
                    _buildSection('temperature', 'Air Temperature', [
                      () {
                        final optLow = _lib?.tempOptLowC ?? (_dbInt('temp_min_c') > 0 ? _dbInt('temp_min_c') : 15);
                        final optHigh = _lib?.tempOptHighC ?? (_dbInt('temp_max_c') > 0 ? _dbInt('temp_max_c') : 25);
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Ideal range', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
                            TempRangeBar(optLow: optLow, optHigh: optHigh, formatT: _fmtTemp),
                          ],
                        );
                      }(),
                      () {
                        final minC = _dbInt('temp_min_c') > 0 ? _dbInt('temp_min_c') : _lib?.tempMinC ?? 5;
                        final maxC = _dbInt('temp_max_c') > 0 ? _dbInt('temp_max_c') : _lib?.tempMaxC ?? 35;
                        return _InfoRow(icon: Icons.thermostat_outlined, text: 'Min ${_fmtTemp(minC)} / Max ${_fmtTemp(maxC)}', sub: 'Survival limits');
                      }(),
                    ], guideLabel: 'Temperature & climate'),

                    // ── 7. Outdoor (RN: InfoRow location status) ──
                    _buildSection('outdoor', 'Outdoor', [
                      if (_locationData?.hasData == true) ...[
                        () {
                          final frostLimit = (_lib?.tempMinC ?? (_dbInt('temp_min_c') > 0 ? _dbInt('temp_min_c') : 5)).toDouble();
                          final outdoor = GeolocationService.getOutdoorMonths(frostLimit, _locationData!.monthlyAvgTemps);
                          final pottedRange = GeolocationService.formatMonthRange(outdoor.potted);
                          return _InfoRow(
                            icon: Icons.park_outlined,
                            text: pottedRange == 'Not recommended' ? 'Not recommended for outdoor'
                                : pottedRange == 'Year-round' ? 'Can stay outside year-round'
                                : '$pottedRange \u2014 safe to keep outside',
                            sub: _locationData!.cityName.isNotEmpty ? 'Based on climate in ${_locationData!.cityName}' : null,
                          );
                        }(),
                      ] else
                        _InfoRow(icon: Icons.location_on_outlined, text: 'Enable location to see outdoor months', sub: 'Based on your local climate'),
                    ], guideLabel: 'Indoor & outdoor'),

                    // ══════ GROUP: Toxicity ══════

                    // ── 8. Toxicity (RN: toxic alert+chips OR non-toxic green) ──
                    _buildSection('toxicity', 'Toxicity', [
                      if (_isToxic) ...[
                        _InfoRow(
                          icon: Icons.warning_amber_outlined,
                          text: 'Toxic${_lib?.toxicitySeverity.isNotEmpty == true ? ' (${_lib!.toxicitySeverity})' : _dbStr('toxicity_severity').isNotEmpty ? ' (${_dbStr('toxicity_severity')})' : ''}',
                          iconColor: AppColors.error,
                        ),
                        _ChipRow(chips: [
                          if (_userPlant?.poisonousToHumans == true || _dbCare['toxic_to_humans'] == true || _dbCare['toxic_to_humans'] == 1 || _lib?.poisonousToHumans == true) 'Humans',
                          if (_userPlant?.poisonousToPets == true || _dbCare['toxic_to_pets'] == true || _dbCare['toxic_to_pets'] == 1 || _lib?.poisonousToPets == true) 'Animals',
                        ]),
                      ] else
                        _InfoRow(icon: Icons.check_circle_outline, text: 'Non-toxic to humans and pets', iconColor: AppColors.success),
                    ], guideLabel: _isToxic ? 'Toxicity details' : null),

                    // ══════ GROUP: Growing ══════

                    // ── 9. Pruning (RN: text 3 lines, NO guide) ──
                    _buildSection('pruning', 'Pruning', [
                      Text(
                        _lib?.pruningInfo.isNotEmpty == true ? _lib!.pruningInfo
                            : _dbStr('pruning_info').isNotEmpty ? _dbStr('pruning_info')
                            : 'Remove dead or damaged leaves. Prune to shape as needed.',
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: AppFontSize.sm, color: AppColors.textSecondary, height: 1.4),
                      ),
                    ]),

                    // ── 10. Harvest (RN: only greens/fruiting, edible parts InfoRow) ──
                    if (_plantType == 'greens' || _plantType == 'fruiting')
                      _buildSection('harvest', 'Harvest', [
                        if (_lib?.edibleParts.isNotEmpty == true)
                          _InfoRow(icon: Icons.restaurant_outlined, text: _lib!.edibleParts, sub: 'Edible parts', iconColor: AppColors.success),
                      ], guideLabel: 'Harvesting guide'),

                    // ── 11. Propagation (RN: method chips) ──
                    _buildSection('propagation', 'Propagation', [
                      if (_lib?.propagationMethods.isNotEmpty == true)
                        _ChipRow(chips: _lib!.propagationMethods)
                      else if (_dbList('propagation_methods').isNotEmpty)
                        _ChipRow(chips: _dbList('propagation_methods'))
                      else
                        _InfoRow(icon: Icons.call_split_outlined, text: 'Stem cuttings, division', sub: 'Common methods'),
                    ], guideLabel: 'Germination & propagation'),

                    // ══════ GROUP: About ══════

                    // ── 12. Difficulty (RN: stars + label + note InfoBox, NO guide) ──
                    _buildSection('difficulty', 'Difficulty', [
                      () {
                        final diff = _lib?.difficulty ?? (_dbStr('difficulty').isNotEmpty ? _dbStr('difficulty') : 'Medium');
                        final stars = diff.toLowerCase().contains('adv') ? 3 : diff.toLowerCase().contains('med') ? 2 : 1;
                        final color = stars == 3 ? AppColors.error : stars == 2 ? const Color(0xFFF59E0B) : AppColors.success;
                        return Row(
                          children: [
                            DifficultyStars(count: stars, color: color),
                            const SizedBox(width: AppSpacing.sm),
                            Text(diff, style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w600, color: color)),
                          ],
                        );
                      }(),
                      if (_lib?.difficultyNote.isNotEmpty == true)
                        InfoBox(text: _lib!.difficultyNote, variant: 'info'),
                    ]),

                    // ── 13. Size (RN: height InfoRow + spread InfoRow) ──
                    _buildSection('size', 'Size', [
                      () {
                        final hMin = _lib?.heightMinCm ?? (_dbInt('height_min_cm') > 0 ? _dbInt('height_min_cm') : 0);
                        final hMax = _lib?.heightMaxCm ?? (_dbInt('height_max_cm') > 0 ? _dbInt('height_max_cm') : 0);
                        return _InfoRow(
                          icon: Icons.height_outlined,
                          text: hMax > 0 ? '${hMin > 0 ? '$hMin \u2013 ' : ''}$hMax cm' : 'Not specified',
                          sub: 'Height (mature)',
                        );
                      }(),
                      if ((_lib?.spreadMaxCm ?? _dbInt('spread_max_cm')) > 0)
                        _InfoRow(icon: Icons.swap_horiz_outlined, text: 'Up to ${_lib?.spreadMaxCm ?? _dbInt('spread_max_cm')} cm', sub: 'Spread'),
                    ], guideLabel: 'Growth & dimensions'),

                    // ── 14. Lifecycle (RN: type+years InfoRow + foliage InfoRow) ──
                    _buildSection('lifecycle', 'Lifecycle', [
                      () {
                        final lc = _lib?.lifecycle ?? (_dbStr('lifecycle').isNotEmpty ? _dbStr('lifecycle') : 'perennial');
                        final years = _lib?.lifecycleYears ?? '';
                        final label = lc == 'perennial' ? 'Perennial' : lc == 'annual' ? 'Annual' : lc;
                        final sub = years.isNotEmpty
                            ? (lc == 'perennial' ? 'Lives $years years' : years)
                            : (lc == 'perennial' ? 'Lives for multiple years' : 'One growing season');
                        return _InfoRow(icon: Icons.loop_outlined, text: label, sub: sub);
                      }(),
                      _InfoRow(
                        icon: Icons.eco_outlined,
                        text: (_lib?.lifecycle ?? 'perennial') == 'perennial' ? 'Evergreen' : 'Seasonal',
                        sub: 'Foliage type',
                      ),
                    ], guideLabel: 'Lifecycle'),

                    // ── 15. Used for (RN: chips + edible parts InfoRow) ──
                    _buildSection('used_for', 'Used for', [
                      () {
                        final tags = _lib?.usedFor ?? _dbList('used_for');
                        if (tags.isNotEmpty) {
                          return _ChipRow(chips: tags, green: tags.any((t) => t.contains('Edible') || t.contains('Fruiting')));
                        }
                        return _ChipRow(chips: [_plantType == 'greens' ? 'Edible greens' : _plantType == 'fruiting' ? 'Fruiting' : 'Decorative']);
                      }(),
                      if (_lib?.edibleParts.isNotEmpty == true)
                        _InfoRow(icon: Icons.restaurant_outlined, text: _lib!.edibleParts, sub: 'Edible parts', iconColor: AppColors.success),
                    ], guideLabel: 'About this plant'),

                    // ── 16. Taxonomy (RN: scientific InfoRow + origin, NO guide) ──
                    _buildSection('taxonomy', 'Taxonomy', [
                      _InfoRow(
                        icon: Icons.science_outlined,
                        text: _scientific,
                        sub: [
                          _lib?.genus ?? _dbStr('genus'),
                          _lib?.family ?? (_dbDetail?['family'] as String? ?? ''),
                          _lib?.order ?? _dbStr('order'),
                        ].where((s) => s.isNotEmpty).join(' \u00B7 '),
                      ),
                      if ((_lib?.origin ?? '').isNotEmpty)
                        _InfoRow(icon: Icons.public_outlined, text: _lib!.origin, sub: 'Origin')
                      else if (_dbStr('origin').isNotEmpty)
                        _InfoRow(icon: Icons.public_outlined, text: _dbStr('origin'), sub: 'Origin'),
                    ]),

                    // ══════ GROUP: Companions ══════

                    // ── 17. Companions (RN: good chips green + bad chips red) ──
                    _buildSection('companions', 'Companions', [
                      () {
                        final good = _lib?.goodCompanions ?? _dbList('good_companions');
                        final bad = _lib?.badCompanions ?? _dbList('bad_companions');
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (good.isNotEmpty) ...[
                              Padding(padding: const EdgeInsets.only(bottom: AppSpacing.xs), child: Text('Good neighbors', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text))),
                              _ChipRow(chips: good, green: true),
                            ],
                            if (bad.isNotEmpty) ...[
                              const SizedBox(height: AppSpacing.sm),
                              Padding(padding: const EdgeInsets.only(bottom: AppSpacing.xs), child: Text('Keep apart', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text))),
                              _ChipRow(chips: bad, red: true),
                            ],
                            if (good.isEmpty && bad.isEmpty)
                              _InfoRow(icon: Icons.group_outlined, text: 'Companion data coming soon'),
                          ],
                        );
                      }(),
                    ], guideLabel: ((_lib?.goodCompanions ?? []).isNotEmpty || (_lib?.badCompanions ?? []).isNotEmpty) ? 'Plant companions' : null),

                    // Bottom padding for floating button
                    const SizedBox(height: 100),
                  ]),
                ),
              ),
            ],
          ),

          // ═══ ADD TO MY PLANTS (floating) ═══
          if (!_isInCollection)
            Positioned(
              left: AppSpacing.lg,
              right: AppSpacing.lg,
              bottom: MediaQuery.of(context).padding.bottom + AppSpacing.lg,
              child: SafeArea(
                child: SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton.icon(
                    onPressed: _isSaving || _isSaved ? null : _addToCollection,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _isSaved ? AppColors.success : null,
                    ),
                    icon: _isSaving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : Icon(_isSaved ? Icons.check_circle : Icons.add_circle_outline),
                    label: Text(_isSaved
                        ? 'Added'
                        : _isSaving
                            ? 'Saving...'
                            : 'Add to My Plants'),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  // ─── Badges ──────────────────────────────────────────────────

  Widget _buildBadges(_PresetCare care) {
    // Water demand
    final waterLabel = care.watering.contains('2-3 week')
        ? 'Low'
        : care.watering.contains('7-10') || care.watering.contains('7 day')
            ? 'Medium'
            : 'High';

    // Light
    final lightLabel = care.light.contains('Full')
        ? 'Full sun'
        : care.light.contains('indirect')
            ? 'Indirect'
            : 'Part sun';

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _RoundBadge(
          icon: Icons.water_drop,
          label: waterLabel,
          bgColor: const Color(0xFFEBF5FF),
          iconColor: const Color(0xFF3B82F6),
        ),
        _RoundBadge(
          icon: care.light.contains('Full') ? Icons.wb_sunny : Icons.wb_sunny_outlined,
          label: lightLabel,
          bgColor: const Color(0xFFFFF8E1),
          iconColor: const Color(0xFFF59E0B),
        ),
        if (_isToxic)
          _RoundBadge(
            icon: Icons.warning_amber,
            label: 'Toxic',
            bgColor: const Color(0xFFFEE2E2),
            iconColor: AppColors.error,
          ),
      ],
    );
  }

  // ─── Section builder ─────────────────────────────────────────

  Widget _buildSection(String key, String title, List<Widget> children, {String? guideLabel}) {
    final accent = _sectionAccent[key] ?? AppColors.border;
    return Container(
      key: _keyFor(key),
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppBorderRadius.lgAll,
        border: Border(
          left: BorderSide(color: accent, width: 3),
          top: BorderSide(color: AppColors.border),
          right: BorderSide(color: AppColors.border),
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: AppFontSize.md,
              fontWeight: FontWeight.w700,
              color: AppColors.text,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          ...children,
          if (guideLabel != null) ...[
            const SizedBox(height: AppSpacing.sm),
            GestureDetector(
              onTap: () => _showGuide(title, key),
              child: Row(
                children: [
                  Text(
                    guideLabel,
                    style: TextStyle(
                      fontSize: AppFontSize.sm,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(Icons.chevron_right, size: 16, color: AppColors.primary),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _showGuide(String title, String sectionKey) {
    final care = _care;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.4,
        expand: false,
        builder: (ctx, scrollController) => Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: ListView(
            controller: scrollController,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: AppSpacing.lg),
                  decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              // Title
              Text(
                '$title guide',
                style: TextStyle(
                  fontSize: AppFontSize.xl,
                  fontWeight: FontWeight.w700,
                  color: AppColors.text,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                _title,
                style: TextStyle(
                  fontSize: AppFontSize.md,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              // Content based on section
              ..._guideContent(sectionKey, care),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _guideContent(String key, _PresetCare care) {
    final lib = _lib;
    switch (key) {
      case 'water':
        return [
          _guideSection('How to water $_title', lib?.wateringMethod ?? care.watering),
          if (lib?.wateringAvoid.isNotEmpty == true)
            _guideSection('What to avoid', lib!.wateringAvoid),
          if (lib?.care.wateringWinter.isNotEmpty == true)
            _guideSection('Winter watering', lib!.care.wateringWinter),
          _guideSection('Drainage', 'Make sure your pot has drainage holes. Without drainage, water collects at the bottom and roots rot.'),
          if (lib?.care.tips.isNotEmpty == true)
            _guideSection('Tips', lib!.care.tips)
          else
            _guideSection('Tips', care.tips),
        ];
      case 'soil':
        return [
          _guideSection('Recommended soil', lib?.care.soil ?? care.soil),
          if (lib?.soilTypes.isNotEmpty == true)
            _guideSection('Soil components', lib!.soilTypes.join(', ')),
          _guideSection('Repotting', lib?.care.repot ?? care.repot),
          if (lib?.repotSigns.isNotEmpty == true)
            _guideSection('Signs to repot', lib!.repotSigns),
          if (lib?.potType.isNotEmpty == true)
            _guideSection('Pot type', lib!.potType),
          if (lib?.potSizeNote.isNotEmpty == true)
            _guideSection('Pot size', lib!.potSizeNote),
        ];
      case 'fertilizing':
        return [
          _guideSection('Schedule', '${lib?.care.fertilizer ?? care.fertilizer}\nSeason: ${lib?.care.fertilizerSeason ?? care.fertilizerSeason}'),
          if (lib?.fertilizerTypes.isNotEmpty == true)
            _guideSection('Recommended fertilizers', lib!.fertilizerTypes.join(', ')),
          if (lib?.fertilizerNpk.isNotEmpty == true)
            _guideSection('NPK ratio', lib!.fertilizerNpk),
          if (lib?.fertilizerWarning.isNotEmpty == true)
            _guideSection('Warning', lib!.fertilizerWarning),
          _guideSection('When NOT to fertilize', 'In winter (plant is dormant), right after repotting, when soil is dry (water first), when plant is stressed or sick.'),
        ];
      case 'light':
        return [
          _guideSection('Preferred light', lib?.care.light ?? care.light),
          if (lib?.care.lightAlsoOk.isNotEmpty == true)
            _guideSection('Also suitable', lib!.care.lightAlsoOk),
          _guideSection('Signs of too little light', 'Leaves turn yellow, plant stretches towards light, slow weak growth, leaves far apart on stem.'),
          _guideSection('Signs of too much light', 'Leaves drooping, leaf edges dry up, color fading, flowers shrivel.'),
          if ((lib?.care.ppfdMin ?? 0) > 0)
            _guideSection('Light intensity', 'PPFD: ${lib!.care.ppfdMin}\u2013${lib.care.ppfdMax} \u00B5mol/m\u00B2/s\nDLI: ${lib.care.dliMin}\u2013${lib.care.dliMax} mol/m\u00B2/day'),
        ];
      case 'humidity':
        return [
          _guideSection('Recommended level', lib?.care.humidity ?? care.humidity),
          if (lib?.care.humidityAction.isNotEmpty == true)
            _guideSection('What to do', lib!.care.humidityAction),
          _guideSection('How to increase humidity', 'Group plants together, use a pebble tray with water, mist leaves in the morning, use a humidifier.'),
          _guideSection('How to decrease humidity', 'Improve air circulation, open a window, use a small fan. Avoid overcrowding plants.'),
        ];
      case 'temperature':
        return [
          _guideSection('Ideal range', lib?.care.temperature ?? care.temperature),
          if (lib?.tempWarning.isNotEmpty == true)
            _guideSection('Warning', lib!.tempWarning),
          _guideSection('Common indoor problems', 'Cold drafts from windows, hot air from radiators, dry air from air conditioning, sudden temperature swings when opening doors in winter.'),
        ];
      case 'outdoor':
        return [
          _guideSection('Moving outdoors', 'Check local temperatures before moving plants outside. Acclimatize gradually over 1\u20132 weeks in a sheltered spot.'),
          _guideSection('Bring inside when', 'Night temperatures drop below the plant\'s minimum tolerance (${_fmtTemp(lib?.tempMinC ?? 5)}). Usually before first frost.'),
        ];
      case 'toxicity':
        return [
          if (lib?.toxicParts.isNotEmpty == true)
            _guideSection('Toxic parts', lib!.toxicParts),
          if (lib?.toxicitySymptoms.isNotEmpty == true)
            _guideSection('Symptoms', lib!.toxicitySymptoms),
          if (lib?.toxicityFirstAid.isNotEmpty == true)
            _guideSection('First aid', lib!.toxicityFirstAid),
          if (lib?.toxicityNote.isNotEmpty == true)
            _guideSection('Note', lib!.toxicityNote),
          _guideSection('Disclaimer', 'This information is for reference only. In case of ingestion, always contact poison control or a veterinarian immediately.'),
        ];
      case 'harvest':
        return [
          if (lib?.edibleParts.isNotEmpty == true)
            _guideSection('Edible parts', lib!.edibleParts),
          if (lib?.harvestInfo.isNotEmpty == true)
            _guideSection('How to harvest', lib!.harvestInfo),
          if (_plantType == 'greens')
            _guideSection('Harvesting tips', 'Harvest from the top, cutting above a leaf pair. Never take more than 1/3 of the plant at once. Morning harvest preserves the most flavor. Pinch off flower buds to extend leaf production.')
          else if (_plantType == 'fruiting')
            _guideSection('Fruit ripeness', 'Pick when fully colored and slightly soft to the touch. Harvest regularly to encourage continued production. Green unripe fruit may contain toxins.'),
        ];
      case 'propagation':
        return [
          if (lib?.propagationMethods.isNotEmpty == true)
            _guideSection('Methods', lib!.propagationMethods.join(', ')),
          if (lib?.propagationDetail.isNotEmpty == true)
            _guideSection('How to propagate', lib!.propagationDetail),
          if ((lib?.germinationDays ?? 0) > 0)
            _guideSection('From seed', 'Germination: ${lib!.germinationDays} days at ${lib.germinationTempC}'),
          _guideSection('General tips', 'Use clean, sharp tools. Best time: spring or early summer. Keep cuttings in moist (not soggy) soil. Bright indirect light. Be patient \u2014 rooting takes weeks.'),
        ];
      case 'size':
        return [
          _guideSection('Dimensions', '${lib?.heightMinCm ?? 0}\u2013${lib?.heightMaxCm ?? 0} cm height (mature, in ground)\n${(lib?.spreadMaxCm ?? 0) > 0 ? 'Spread: up to ${lib!.spreadMaxCm} cm' : ''}'),
          if ((lib?.heightIndoorMaxCm ?? 0) > 0)
            _guideSection('In a pot', 'Realistic indoor height: up to ${lib!.heightIndoorMaxCm} cm. Pot size limits root growth which limits plant size.'),
          if (lib?.growthRate.isNotEmpty == true)
            _guideSection('Growth rate', lib!.growthRate),
        ];
      case 'lifecycle':
        return [
          _guideSection('Type', '${lib?.lifecycle == 'perennial' ? 'Perennial \u2014 lives for multiple years' : 'Annual \u2014 completes lifecycle in one season'}${lib?.lifecycleYears.isNotEmpty == true ? ' (${lib!.lifecycleYears})' : ''}'),
          _guideSection('Seasonal care', 'Spring: active growth begins \u2014 increase watering and start fertilizing.\nSummer: peak growth \u2014 regular watering and feeding.\nAutumn: growth slows \u2014 reduce watering and stop fertilizing.\nWinter: dormancy \u2014 minimal watering, no fertilizer.'),
        ];
      case 'used_for':
        return [
          if (lib?.usedForDetails.isNotEmpty == true)
            _guideSection('About $_title', lib!.usedForDetails),
          if (lib?.edibleParts.isNotEmpty == true)
            _guideSection('Edible parts', lib!.edibleParts),
          if (lib?.harvestInfo.isNotEmpty == true)
            _guideSection('Harvest', lib!.harvestInfo),
        ];
      case 'companions':
        return [
          _guideSection('Why companion planting matters', 'Some plants benefit each other through pest control, pollination, or nutrient sharing. Others compete for resources or inhibit each other\'s growth.'),
          if (lib?.companionNote.isNotEmpty == true)
            _guideSection('About $_title', lib!.companionNote),
          _guideSection('Grouping indoors', 'Group plants with similar humidity needs together. Use tall plants to provide shade for shade-loving neighbors. Keep fragrant herbs near windows. Isolate any plant with pest issues immediately.'),
        ];
      default:
        return [
          _guideSection('Information', 'Detailed guide coming soon.'),
        ];
    }
  }

  Widget _guideSection(String title, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: AppFontSize.md,
              fontWeight: FontWeight.w700,
              color: AppColors.text,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            text,
            style: TextStyle(
              fontSize: AppFontSize.sm,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _heroPlaceholder() => Container(
        color: AppColors.background,
        child: Center(
          child: Icon(Icons.eco, size: 64, color: AppColors.accent),
        ),
      );
}

// ─── Round badge ─────────────────────────────────────────────

class _RoundBadge extends StatelessWidget {
  const _RoundBadge({
    required this.icon,
    required this.label,
    required this.bgColor,
    required this.iconColor,
  });
  final IconData icon;
  final String label;
  final Color bgColor;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: bgColor,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: iconColor, size: 24),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: AppFontSize.xs,
            fontWeight: FontWeight.w600,
            color: AppColors.text,
          ),
        ),
      ],
    );
  }
}

// ─── Sticky tab delegate ─────────────────────────────────────

class _StickyTabDelegate extends SliverPersistentHeaderDelegate {
  _StickyTabDelegate({required this.activeGroup, required this.onTap});
  final String activeGroup;
  final void Function(String) onTap;

  @override
  double get minExtent => 48;
  @override
  double get maxExtent => 48;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: AppColors.background,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
        child: Row(
          children: _groupDefs.map((g) {
            final isActive = g.$1 == activeGroup;
            return Padding(
              padding: const EdgeInsets.only(right: AppSpacing.sm),
              child: GestureDetector(
                onTap: () => onTap(g.$1),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: isActive ? AppColors.primary : Colors.transparent,
                    borderRadius: AppBorderRadius.lgAll,
                    border: Border.all(
                      color: isActive ? AppColors.primary : AppColors.border,
                    ),
                  ),
                  child: Text(
                    g.$2,
                    style: TextStyle(
                      fontSize: AppFontSize.sm,
                      fontWeight: FontWeight.w600,
                      color: isActive ? Colors.white : AppColors.textSecondary,
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _StickyTabDelegate oldDelegate) =>
      activeGroup != oldDelegate.activeGroup;
}

// ─── Info row ────────────────────────────────────────────────

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.text,
    this.sub,
    this.iconColor,
  });
  final IconData icon;
  final String text;
  final String? sub;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: iconColor ?? AppColors.textSecondary),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  text,
                  style: TextStyle(
                    fontSize: AppFontSize.sm,
                    color: AppColors.text,
                  ),
                ),
                if (sub != null)
                  Text(
                    sub!,
                    style: TextStyle(
                      fontSize: AppFontSize.xs,
                      color: AppColors.textSecondary,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChipRow extends StatelessWidget {
  const _ChipRow({required this.chips, this.green = false, this.red = false});
  final List<String> chips;
  final bool green;
  final bool red;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Wrap(
        spacing: AppSpacing.xs,
        runSpacing: AppSpacing.xs,
        children: chips.map((chip) => Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 4),
          decoration: BoxDecoration(
            color: green
                ? const Color(0xFFDCFCE7)
                : red
                    ? const Color(0xFFFEE2E2)
                    : const Color(0xFFF3F4F6),
            borderRadius: AppBorderRadius.smAll,
          ),
          child: Text(
            chip,
            style: TextStyle(
              fontSize: AppFontSize.xs,
              fontWeight: FontWeight.w600,
              color: green
                  ? const Color(0xFF166534)
                  : red
                      ? AppColors.error
                      : AppColors.text,
            ),
          ),
        )).toList(),
      ),
    );
  }
}
