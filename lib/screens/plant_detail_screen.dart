import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/constants/popular_plants.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';
import 'package:plantapp/services/library_service.dart';
import 'package:plantapp/services/geolocation_service.dart';
import 'package:plantapp/stores/settings_store.dart';

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

                    // ── 1. Water ──
                    _buildSection('water', 'Water', [
                      _InfoRow(
                        icon: Icons.water_drop_outlined,
                        text: _dbCareStr('watering').isNotEmpty
                            ? _dbCareStr('watering')
                            : _lib?.care.watering.isNotEmpty == true
                                ? _lib!.care.watering
                                : (_locationData?.hasData == true
                                    ? 'Every ~${GeolocationService.getSeasonalWateringDays(_presetWateringDays, _locationData!.latitude)} days in ${_months[DateTime.now().month - 1]}'
                                    : care.watering),
                        sub: (_dbCareStr('watering_demand').isNotEmpty
                            ? '${_dbCareStr('watering_demand')} demand'
                            : _lib?.wateringDemand.isNotEmpty == true
                                ? '${_lib!.wateringDemand} demand'
                                : null),
                      ),
                      if (_lib?.care.wateringWinter.isNotEmpty == true)
                        _InfoRow(icon: Icons.ac_unit_outlined, text: _lib!.care.wateringWinter, sub: 'Winter'),
                      if (_lib?.wateringMethod.isNotEmpty == true)
                        _InfoRow(icon: Icons.opacity_outlined, text: _lib!.wateringMethod, sub: 'Method'),
                      if (_lib?.wateringAvoid.isNotEmpty == true)
                        _InfoRow(icon: Icons.warning_amber_outlined, text: _lib!.wateringAvoid, iconColor: AppColors.error),
                      if (_locationData?.cityName.isNotEmpty == true)
                        _InfoRow(icon: Icons.location_on_outlined, text: 'Adjusted for ${_locationData!.cityName}'),
                      if (_dbStr('tips').isNotEmpty)
                        _InfoRow(icon: Icons.tips_and_updates_outlined, text: _dbStr('tips'))
                      else if (_lib?.care.tips.isNotEmpty == true)
                        _InfoRow(icon: Icons.tips_and_updates_outlined, text: _lib!.care.tips)
                      else
                        _InfoRow(icon: Icons.tips_and_updates_outlined, text: care.tips),
                    ], guideLabel: 'Watering guide'),

                    // ── 2. Soil ──
                    _buildSection('soil', 'Soil', [
                      _InfoRow(
                        icon: Icons.layers_outlined,
                        text: _dbCareStr('soil').isNotEmpty
                            ? _dbCareStr('soil')
                            : _lib?.care.soil.isNotEmpty == true ? _lib!.care.soil : care.soil,
                      ),
                      if (_lib?.soilTypes.isNotEmpty == true)
                        _ChipRow(chips: _lib!.soilTypes),
                      if (_lib?.potType.isNotEmpty == true)
                        _InfoRow(icon: Icons.inventory_2_outlined, text: _lib!.potType, sub: 'Pot'),
                      if (_lib?.potSizeNote.isNotEmpty == true)
                        _InfoRow(icon: Icons.straighten_outlined, text: _lib!.potSizeNote),
                      _InfoRow(
                        icon: Icons.swap_vert,
                        text: 'Repot: ${_dbCareStr('repot').isNotEmpty ? _dbCareStr('repot') : _lib?.care.repot.isNotEmpty == true ? _lib!.care.repot : care.repot}',
                        sub: 'Repotting',
                      ),
                      if (_lib?.repotSigns.isNotEmpty == true)
                        _InfoRow(icon: Icons.info_outline, text: _lib!.repotSigns, sub: 'Signs to repot'),
                    ], guideLabel: 'Repotting guide'),

                    // ── 3. Fertilizing ──
                    _buildSection('fertilizing', 'Fertilizing', [
                      _InfoRow(
                        icon: Icons.eco_outlined,
                        text: _dbCareStr('fertilizer').isNotEmpty
                            ? _dbCareStr('fertilizer')
                            : _lib?.care.fertilizer.isNotEmpty == true ? _lib!.care.fertilizer : care.fertilizer,
                        sub: _lib?.care.fertilizerSeason.isNotEmpty == true ? _lib!.care.fertilizerSeason : care.fertilizerSeason,
                      ),
                      if (_lib?.fertilizerTypes.isNotEmpty == true)
                        _ChipRow(chips: _lib!.fertilizerTypes),
                      if (_lib?.fertilizerNpk.isNotEmpty == true)
                        _InfoRow(icon: Icons.science_outlined, text: 'NPK: ${_lib!.fertilizerNpk}'),
                      if (_lib?.fertilizerWarning.isNotEmpty == true)
                        _InfoRow(icon: Icons.warning_amber_outlined, text: _lib!.fertilizerWarning, iconColor: AppColors.error),
                    ], guideLabel: 'Fertilizing guide'),

                    // ══════ GROUP: Environment ══════

                    // ── 4. Light ──
                    _buildSection('light', 'Light', [
                      _InfoRow(
                        icon: Icons.wb_sunny_outlined,
                        text: _dbCareStr('light').isNotEmpty
                            ? _dbCareStr('light')
                            : _lib?.care.light.isNotEmpty == true ? _lib!.care.light : care.light,
                        sub: 'Preferred',
                      ),
                      if (_lib?.care.lightAlsoOk.isNotEmpty == true)
                        _InfoRow(icon: Icons.wb_sunny_outlined, text: _lib!.care.lightAlsoOk, sub: 'Also OK'),
                      if ((_lib?.care.ppfdMin ?? 0) > 0)
                        _InfoRow(icon: Icons.flash_on_outlined, text: 'PPFD: ${_lib!.care.ppfdMin}-${_lib!.care.ppfdMax} \u00B5mol/m\u00B2/s  |  DLI: ${_lib!.care.dliMin}-${_lib!.care.dliMax} mol/m\u00B2/day', sub: 'Advanced'),
                    ], guideLabel: 'Understanding light'),

                    // ── 5. Humidity ──
                    _buildSection('humidity', 'Air Humidity', [
                      _InfoRow(
                        icon: Icons.water_drop_outlined,
                        text: _dbCareStr('humidity').isNotEmpty
                            ? _dbCareStr('humidity')
                            : _lib?.care.humidity.isNotEmpty == true ? _lib!.care.humidity : care.humidity,
                      ),
                      if (_lib?.care.humidityAction.isNotEmpty == true)
                        _InfoRow(icon: Icons.tips_and_updates_outlined, text: _lib!.care.humidityAction),
                    ], guideLabel: 'Managing humidity'),

                    // ── 6. Temperature ──
                    _buildSection('temperature', 'Air Temperature', [
                      _InfoRow(
                        icon: Icons.thermostat_outlined,
                        text: _lib?.care.temperature.isNotEmpty == true ? _lib!.care.temperature : care.temperature,
                        sub: 'Ideal range',
                      ),
                      () {
                        final minC = _dbInt('temp_min_c') > 0 ? _dbInt('temp_min_c') : _lib?.tempMinC ?? 5;
                        final maxC = _dbInt('temp_max_c') > 0 ? _dbInt('temp_max_c') : _lib?.tempMaxC ?? 35;
                        return _InfoRow(
                          icon: Icons.thermostat_auto_outlined,
                          text: 'Min ${_fmtTemp(minC)} / Max ${_fmtTemp(maxC)}',
                          sub: 'Survival limits',
                        );
                      }(),
                      if (_lib?.tempWarning.isNotEmpty == true)
                        _InfoRow(icon: Icons.warning_amber_outlined, text: _lib!.tempWarning, iconColor: AppColors.error),
                    ], guideLabel: 'Temperature & climate'),

                    // ── 7. Outdoor ──
                    _buildSection('outdoor', 'Outdoor', [
                      if (_locationData?.hasData == true) ...[
                        () {
                          final frostLimit = _dbInt('temp_min_c') > 0 ? _dbInt('temp_min_c') : 5;
                          final outdoor = GeolocationService.getOutdoorMonths(frostLimit.toDouble(), _locationData!.monthlyAvgTemps);
                          final pottedRange = GeolocationService.formatMonthRange(outdoor.potted);
                          return _InfoRow(
                            icon: Icons.park_outlined,
                            text: pottedRange == 'Not recommended'
                                ? 'Not recommended for outdoor'
                                : pottedRange == 'Year-round'
                                    ? 'Can stay outside year-round'
                                    : '$pottedRange — safe to keep outside',
                            sub: _locationData!.cityName.isNotEmpty
                                ? 'Based on climate in ${_locationData!.cityName}'
                                : null,
                          );
                        }(),
                      ] else
                        _InfoRow(
                          icon: Icons.location_on_outlined,
                          text: 'Enable location to see outdoor months',
                          sub: 'Based on your local climate',
                        ),
                    ], guideLabel: 'Indoor & outdoor'),

                    // ══════ GROUP: Toxicity ══════

                    // ── 8. Toxicity ──
                    _buildSection('toxicity', 'Toxicity', [
                      if (_isToxic) ...[
                        _InfoRow(
                          icon: Icons.warning_amber_outlined,
                          text: 'Toxic${_dbStr('toxicity_severity').isNotEmpty ? ' (${_dbStr('toxicity_severity')})' : _lib?.toxicitySeverity.isNotEmpty == true ? ' (${_lib!.toxicitySeverity})' : ''}',
                          iconColor: AppColors.error,
                        ),
                        _ChipRow(chips: [
                          if (_userPlant?.poisonousToHumans == true || _dbCare['toxic_to_humans'] == true || _dbCare['toxic_to_humans'] == 1 || _lib?.poisonousToHumans == true) 'Humans',
                          if (_userPlant?.poisonousToPets == true || _dbCare['toxic_to_pets'] == true || _dbCare['toxic_to_pets'] == 1 || _lib?.poisonousToPets == true) 'Animals',
                        ]),
                        if (_lib?.toxicParts.isNotEmpty == true)
                          _InfoRow(icon: Icons.dangerous_outlined, text: _lib!.toxicParts, sub: 'Toxic parts'),
                        if ((_dbStr('toxicity_note').isNotEmpty || _lib?.toxicityNote.isNotEmpty == true))
                          _InfoRow(icon: Icons.info_outline, text: _dbStr('toxicity_note').isNotEmpty ? _dbStr('toxicity_note') : _lib!.toxicityNote),
                        if (_lib?.toxicitySymptoms.isNotEmpty == true)
                          _InfoRow(icon: Icons.medical_services_outlined, text: _lib!.toxicitySymptoms, sub: 'Symptoms'),
                        if (_lib?.toxicityFirstAid.isNotEmpty == true)
                          _InfoRow(icon: Icons.health_and_safety_outlined, text: _lib!.toxicityFirstAid, sub: 'First aid'),
                      ] else ...[
                        _InfoRow(
                          icon: Icons.check_circle_outline,
                          text: _lib?.toxicityNote.isNotEmpty == true ? _lib!.toxicityNote : 'Non-toxic to humans and pets',
                          iconColor: AppColors.success,
                        ),
                      ],
                    ], guideLabel: _isToxic ? 'Toxicity details' : null),

                    // ══════ GROUP: Growing ══════

                    // ── 9. Pruning ──
                    _buildSection('pruning', 'Pruning', [
                      _InfoRow(
                        icon: Icons.content_cut_outlined,
                        text: _dbStr('pruning_info').isNotEmpty
                            ? _dbStr('pruning_info')
                            : _lib?.pruningInfo.isNotEmpty == true
                                ? _lib!.pruningInfo
                                : 'Remove dead or damaged leaves. Prune to shape as needed.',
                      ),
                    ]),

                    // ── 10. Propagation ──
                    _buildSection('propagation', 'Propagation', [
                      if (_dbList('propagation_methods').isNotEmpty)
                        _ChipRow(chips: _dbList('propagation_methods'))
                      else if (_lib?.propagationMethods.isNotEmpty == true)
                        _ChipRow(chips: _lib!.propagationMethods)
                      else
                        _InfoRow(icon: Icons.call_split_outlined, text: 'Stem cuttings, division', sub: 'Common methods'),
                      if (_lib?.propagationDetail.isNotEmpty == true)
                        _InfoRow(icon: Icons.info_outline, text: _lib!.propagationDetail),
                      if ((_lib?.germinationDays ?? 0) > 0)
                        _InfoRow(icon: Icons.timer_outlined, text: 'Germination: ${_lib!.germinationDays} days at ${_lib!.germinationTempC}'),
                    ]),

                    // ══════ GROUP: About ══════

                    // ── 11. Difficulty ──
                    _buildSection('difficulty', 'Difficulty', [
                      () {
                        final diff = _dbStr('difficulty').isNotEmpty ? _dbStr('difficulty') : _lib?.difficulty ?? 'Medium';
                        final stars = diff.toLowerCase().contains('adv') ? 3 : diff.toLowerCase().contains('med') ? 2 : 1;
                        final color = stars == 3 ? AppColors.error : stars == 2 ? const Color(0xFFF59E0B) : AppColors.success;
                        return Row(
                          children: [
                            ...List.generate(stars, (_) => Icon(Icons.star, size: 20, color: color)),
                            ...List.generate(3 - stars, (_) => Icon(Icons.star_border, size: 20, color: AppColors.border)),
                            const SizedBox(width: AppSpacing.sm),
                            Text(diff, style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w600, color: color)),
                          ],
                        );
                      }(),
                      if (_lib?.difficultyNote.isNotEmpty == true)
                        _InfoRow(icon: Icons.info_outline, text: _lib!.difficultyNote),
                    ]),

                    // ── 12. Size ──
                    _buildSection('size', 'Size', [
                      () {
                        final hMin = _dbInt('height_min_cm') > 0 ? _dbInt('height_min_cm') : _lib?.heightMinCm ?? 0;
                        final hMax = _dbInt('height_max_cm') > 0 ? _dbInt('height_max_cm') : _lib?.heightMaxCm ?? 0;
                        final hIndoor = _lib?.heightIndoorMaxCm ?? 0;
                        return _InfoRow(
                          icon: Icons.height_outlined,
                          text: hMax > 0
                              ? '${hMin > 0 ? '$hMin \u2013 ' : ''}$hMax cm${hIndoor > 0 ? ' (indoors up to $hIndoor cm)' : ''}'
                              : 'Not specified',
                          sub: 'Height (mature)',
                        );
                      }(),
                      () {
                        final spread = _dbInt('spread_max_cm') > 0 ? _dbInt('spread_max_cm') : _lib?.spreadMaxCm ?? 0;
                        if (spread > 0) return _InfoRow(icon: Icons.swap_horiz_outlined, text: 'Up to $spread cm', sub: 'Spread');
                        return const SizedBox.shrink();
                      }(),
                      if (_lib?.growthRate.isNotEmpty == true)
                        _InfoRow(icon: Icons.trending_up_outlined, text: '${_lib!.growthRate} growth rate'),
                    ]),

                    // ── 13. Lifecycle ──
                    _buildSection('lifecycle', 'Lifecycle', [
                      () {
                        final lc = _dbStr('lifecycle').isNotEmpty ? _dbStr('lifecycle') : _lib?.lifecycle ?? 'perennial';
                        final years = _lib?.lifecycleYears ?? '';
                        final label = lc == 'perennial' ? 'Perennial' : lc == 'annual' ? 'Annual' : lc;
                        final sub = years.isNotEmpty
                            ? (lc == 'perennial' ? 'Lives $years years' : years)
                            : (lc == 'perennial' ? 'Lives for multiple years' : 'One growing season');
                        return _InfoRow(icon: Icons.loop_outlined, text: label, sub: sub);
                      }(),
                    ]),

                    // ── 14. Used for ──
                    _buildSection('used_for', 'Used for', [
                      if (_dbList('used_for').isNotEmpty)
                        _ChipRow(chips: _dbList('used_for'))
                      else if (_lib?.usedFor.isNotEmpty == true)
                        _ChipRow(chips: _lib!.usedFor)
                      else
                        _InfoRow(icon: Icons.local_florist_outlined, text: 'Decorative'),
                      if (_lib?.usedForDetails.isNotEmpty == true)
                        _InfoRow(icon: Icons.info_outline, text: _lib!.usedForDetails),
                      if (_lib?.edible == true && _lib?.edibleParts.isNotEmpty == true)
                        _InfoRow(icon: Icons.restaurant_outlined, text: _lib!.edibleParts, sub: 'Edible parts'),
                      if (_lib?.harvestInfo.isNotEmpty == true)
                        _InfoRow(icon: Icons.agriculture_outlined, text: _lib!.harvestInfo, sub: 'Harvest'),
                    ]),

                    // ── 15. Taxonomy ──
                    _buildSection('taxonomy', 'Taxonomy', [
                      _InfoRow(
                        icon: Icons.science_outlined,
                        text: _scientific,
                        sub: [
                          _dbStr('genus').isNotEmpty ? _dbStr('genus') : _lib?.genus ?? '',
                          (_dbDetail?['family'] as String? ?? '').isNotEmpty ? _dbDetail!['family'] as String : _lib?.family ?? '',
                          _dbStr('order').isNotEmpty ? _dbStr('order') : _lib?.order ?? '',
                        ].where((s) => s.isNotEmpty).join(' \u00B7 '),
                      ),
                      if (_dbStr('origin').isNotEmpty)
                        _InfoRow(icon: Icons.public_outlined, text: _dbStr('origin'), sub: 'Origin')
                      else if (_lib?.origin.isNotEmpty == true)
                        _InfoRow(icon: Icons.public_outlined, text: _lib!.origin, sub: 'Origin'),
                      if (_lib?.synonyms.isNotEmpty == true)
                        _InfoRow(icon: Icons.label_outlined, text: _lib!.synonyms.join(', '), sub: 'Synonyms'),
                    ]),

                    // ══════ GROUP: Companions ══════

                    // ── 16. Companions ──
                    _buildSection('companions', 'Companions', [
                      () {
                        final good = _dbList('good_companions').isNotEmpty ? _dbList('good_companions') : _lib?.goodCompanions ?? [];
                        final bad = _dbList('bad_companions').isNotEmpty ? _dbList('bad_companions') : _lib?.badCompanions ?? [];
                        final note = _lib?.companionNote ?? '';
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (good.isNotEmpty) ...[
                              Padding(
                                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                                child: Text('Good neighbors', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
                              ),
                              _ChipRow(chips: good, green: true),
                            ],
                            if (bad.isNotEmpty) ...[
                              const SizedBox(height: AppSpacing.sm),
                              Padding(
                                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                                child: Text('Keep apart', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
                              ),
                              _ChipRow(chips: bad, red: true),
                            ],
                            if (note.isNotEmpty) ...[
                              const SizedBox(height: AppSpacing.sm),
                              _InfoRow(icon: Icons.info_outline, text: note),
                            ],
                            if (good.isEmpty && bad.isEmpty)
                              _InfoRow(icon: Icons.group_outlined, text: 'Companion data coming soon'),
                          ],
                        );
                      }(),
                    ]),

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
    switch (key) {
      case 'water':
        return [
          _guideSection('Watering frequency', care.watering),
          _guideSection('Tips', care.tips),
          _guideSection('Drainage', 'Make sure your pot has drainage holes. Without drainage, water collects and roots rot.'),
        ];
      case 'soil':
        return [
          _guideSection('Recommended soil', care.soil),
          _guideSection('Repotting', care.repot),
          _guideSection('Signs to repot', 'Roots growing out of drainage holes, soil drying out very quickly, plant becoming top-heavy.'),
        ];
      case 'fertilizing':
        return [
          _guideSection('Fertilizer', care.fertilizer),
          _guideSection('Season', care.fertilizerSeason),
          _guideSection('Warning', 'Never fertilize a dry plant. Water first, then fertilize. Over-fertilizing burns roots.'),
        ];
      case 'light':
        return [
          _guideSection('Preferred light', care.light),
          _guideSection('Signs of too little light', 'Leaves turn yellow, plant stretches towards light, slow weak growth, leaves far apart on stem.'),
          _guideSection('Signs of too much light', 'Leaves drooping, leaf edges dry up, color fading, flowers shrivel.'),
        ];
      case 'humidity':
        return [
          _guideSection('Preferred humidity', care.humidity),
          _guideSection('How to increase', 'Group plants together, use a pebble tray with water, mist leaves in the morning, use a humidifier.'),
        ];
      case 'temperature':
        return [
          _guideSection('Ideal range', care.temperature),
          _guideSection('Avoid', 'Keep away from cold drafts, radiators, and air conditioning vents. Sudden temperature changes stress plants.'),
        ];
      case 'outdoor':
        return [
          _guideSection('Outdoor placement', 'Check local temperatures before moving plants outside. Acclimatize gradually over 1-2 weeks.'),
          _guideSection('Bring inside when', 'Night temperatures drop below the plant\'s minimum tolerance. Usually before first frost.'),
        ];
      case 'toxicity':
        return [
          _guideSection('Safety', _isToxic ? 'This plant is toxic. Keep away from children and pets.' : 'This plant is non-toxic and safe around children and pets.'),
          if (_isToxic)
            _guideSection('First aid', 'If ingested, contact poison control immediately. Rinse mouth with water. Do not induce vomiting.'),
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
