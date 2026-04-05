import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/constants/popular_plants.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';
import 'package:plantapp/services/library_service.dart';
import 'package:plantapp/services/geolocation_service.dart';
import 'package:plantapp/stores/settings_store.dart';
import 'package:image_picker/image_picker.dart';
import 'package:plantapp/services/journal_service.dart';
import 'package:plantapp/widgets/light_meter_modal.dart';
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
  ('about', 'Details'),
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
    startPct: 15,
    stopPct: 25,
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
    startPct: 35,
    stopPct: 55,
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
    startPct: 55,
    stopPct: 75,
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
    startPct: 30,
    stopPct: 45,
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
  final int startPct;
  final int stopPct;
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
    required this.startPct,
    required this.stopPct,
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

  // Photo carousel
  List<String> _photoUrls = [];
  int _currentPhotoIndex = 0;
  final _pageController = PageController();

  // UI
  String _activeGroup = 'care';
  bool _descExpanded = false;
  bool _isSaving = false;
  bool _isSaved = false;
  bool _isAutoScrolling = false;

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
    _pageController.dispose();
    super.dispose();
  }

  void _loadPhotos() {
    final detail = _dbDetail;
    if (detail == null) return;

    // Images can be at top level or inside care
    final images = (detail['images'] as List<dynamic>?) ?? [];
    final urls = images.map((i) => i.toString()).where((u) => u.isNotEmpty).toList();

    // Always include main image first if not already in list
    final mainUrl = _imageUrl;
    if (mainUrl != null && mainUrl.isNotEmpty) {
      if (!urls.any((u) => u.contains(mainUrl.split('/').last))) {
        urls.insert(0, mainUrl);
      }
    }
    if (urls.isEmpty && mainUrl != null) {
      urls.add(mainUrl);
    }
    if (urls.length > 1) {
      setState(() => _photoUrls = urls);
    }
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
    if (mounted) {
      setState(() {
        _isLoading = false;
        // Load carousel photos from detail response
        if (_dbDetail != null) {
          final images = (_dbDetail!['images'] as List<dynamic>?) ?? [];
          final urls = images.map((i) => i.toString()).where((u) => u.isNotEmpty).toList();
          final mainUrl = _imageUrl;
          if (mainUrl != null && mainUrl.isNotEmpty && !urls.contains(mainUrl)) {
            urls.insert(0, mainUrl);
          }
          if (urls.length > 1) {
            _photoUrls = urls;
          }
        }
      });
    }
  }

  // ─── Derived data ────────────────────────────────────────────

  String get _title {
    if (_userPlant != null) return _userPlant!.displayName;
    // Prefer our curated common name from PopularPlant
    if (_lib != null) return _lib!.commonName;
    final db = _dbDetail;
    if (db != null) {
      // Use primary common name from DB
      final primaryName = db['primary_common_name'] as String?;
      if (primaryName != null && primaryName.isNotEmpty) return primaryName;
      final names = db['common_names'] as Map<String, dynamic>?;
      final enNames = (names?['en'] as List<dynamic>?);
      if (enNames != null && enNames.isNotEmpty) return enNames.first as String;
      return (db['scientific'] as String?) ?? 'Plant';
    }
    return 'Plant';
  }

  String get _scientific {
    return _userPlant?.scientific ?? (_dbDetail?['scientific'] as String?) ?? _lib?.scientific ?? '';
  }

  String? get _imageUrl {
    return _userPlant?.imageUrl ?? (_dbDetail?['image_url'] as String?) ?? _lib?.imageUrl;
  }

  String? get _description {
    final desc = (_dbDetail?['description'] as String?)?.isNotEmpty == true
        ? _dbDetail!['description'] as String
        : _lib?.description;
    if (desc == null || desc.isEmpty) return null;
    // Append common names (aliases) at the end if available
    final aliases = _otherCommonNames;
    if (aliases.isNotEmpty) {
      return '$desc Also known as: ${aliases.join(", ")}.';
    }
    return desc;
  }

  List<String> get _otherCommonNames {
    // Collect common names that differ from the title
    final title = _title.toLowerCase();
    final names = <String>{};
    // From DB common_names
    final dbNames = _dbDetail?['common_names'] as Map<String, dynamic>?;
    final enNames = (dbNames?['en'] as List<dynamic>?) ?? [];
    for (final n in enNames) {
      final name = n.toString();
      if (name.toLowerCase() != title && name.isNotEmpty) names.add(name);
    }
    // From PopularPlant synonyms are not stored separately, but Turso has common_names table
    // Limit to 3 aliases
    return names.take(3).toList();
  }

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

  // Map section → group for scroll tracking
  static const _sectionToGroup = {
    'water': 'care', 'soil': 'care', 'fertilizing': 'care',
    'light': 'environment', 'humidity': 'environment', 'temperature': 'environment', 'outdoor': 'environment',
    'toxicity': 'safety',
    'pruning': 'growing', 'harvest': 'growing', 'propagation': 'growing',
    'size': 'about', 'lifecycle': 'about', 'used_for': 'about',
    'companions': 'companions',
  };

  void _onScroll() {
    if (_isAutoScrolling) return;

    // Find topmost visible section
    String currentSection = 'water';
    for (final entry in _sectionKeys.entries) {
      final ctx = entry.value.currentContext;
      if (ctx != null) {
        final box = ctx.findRenderObject() as RenderBox?;
        if (box != null && box.attached) {
          final pos = box.localToGlobal(Offset.zero);
          if (pos.dy < 160) {
            currentSection = entry.key;
          }
        }
      }
    }

    final group = _sectionToGroup[currentSection] ?? 'care';
    if (group != _activeGroup) {
      setState(() => _activeGroup = group);
    }
  }

  void _scrollToGroup(String groupKey) {
    const firstSection = {
      'care': 'water',
      'environment': 'light',
      'safety': 'toxicity',
      'growing': 'pruning',
      'about': 'size',
      'companions': 'companions',
    };

    final section = firstSection[groupKey];
    if (section == null) return;
    final key = _sectionKeys[section];
    final ctx = key?.currentContext;
    if (ctx == null) return;

    // Calculate absolute scroll position of the target section
    final box = ctx.findRenderObject() as RenderBox?;
    if (box == null || !box.attached) return;

    // Get the section's position relative to the viewport
    final viewportPos = box.localToGlobal(Offset.zero);
    // Scroll so the GROUP HEADER is fully visible below sticky nav
    // The group header is ABOVE the first section card (added via _groupHeader widget)
    // Need extra offset for: group header height (~30px) + spacing (~16px)
    final navHeight = MediaQuery.of(context).padding.top + 48 + 56;
    final targetOffset = _scrollController.offset + viewportPos.dy - navHeight;

    setState(() {
      _activeGroup = groupKey;
      _isAutoScrolling = true;
    });

    _scrollController.animateTo(
      targetOffset.clamp(0, _scrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    ).then((_) {
      Future.delayed(const Duration(milliseconds: 400), () {
        if (mounted) setState(() => _isAutoScrolling = false);
      });
    });
  }

  // ─── Journal photo (matches RN handleTakePhoto) ──────────────

  final _imagePicker = ImagePicker();

  Future<void> _takePhotoForJournal() async {
    final picked = await _imagePicker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (picked == null) return;

    final plantId = widget.plantId;
    try {
      await JournalService.instance.addEntry(plantId: plantId, sourceUri: picked.path);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Photo added. Check your Journal.')),
        );
      }
    } catch (e) {
      debugPrint('[Journal] Error: $e');
    }
  }

  // ─── Save to collection ──────────────────────────────────────

  Future<void> _addToCollection() async {
    setState(() => _isSaving = true);
    try {
      final care = _care;
      await _plantService.savePlant(SavePlantInput(
        deviceId: 'user-collection',
        plant: {
          'scientific': _scientific,
          'common_name': _title,
          'family': _lib?.family ?? _dbDetail?['family'] as String? ?? '',
          'preset': _preset,
          'start_pct': _userPlant?.startPct ?? care.startPct,
          'stop_pct': _userPlant?.stopPct ?? care.stopPct,
          'image_url': _imageUrl,
          'poisonous_to_pets': _lib?.poisonousToPets ?? false,
          'poisonous_to_humans': _lib?.poisonousToHumans ?? false,
          'toxicity_note': _lib?.toxicityNote ?? '',
        },
        wateringFreqDays: _lib?.wateringFreqSummerDays,
      ));
      if (mounted) {
        setState(() {
          _isSaving = false;
          _isSaved = true;
        });
        // Reload to update _isInCollection (matches RN queryClient.invalidateQueries)
        _loadPlant();
      }
    } catch (e) {
      debugPrint('[AddToCollection] ERROR: $e');
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save: $e')),
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
                backgroundColor: AppColors.background,
                foregroundColor: AppColors.text,
                leading: IconButton(
                  icon: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.4),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
                  ),
                  onPressed: () => Navigator.pop(context),
                ),
                flexibleSpace: FlexibleSpaceBar(
                  background: _photoUrls.length > 1
                      ? _buildPhotoCarousel()
                      : Stack(
                          fit: StackFit.expand,
                          children: [
                            if (_imageUrl != null)
                              CachedNetworkImage(
                                imageUrl: _imageUrl!,
                                fit: BoxFit.cover,
                                placeholder: (_, __) => _heroPlaceholder(),
                                errorWidget: (_, __, ___) => _heroPlaceholder(),
                              )
                            else
                              _heroPlaceholder(),
                            if (_imageUrl != null)
                              Positioned.fill(
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    onTap: () => _openFullScreenImage(context),
                                  ),
                                ),
                              ),
                          ],
                        ),
                ),
              ),

              // ═══ NAME + DESCRIPTION ═══
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, AppSpacing.sm),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _title,
                              style: TextStyle(
                                fontSize: AppFontSize.xxl,
                                fontWeight: FontWeight.w700,
                                color: AppColors.text,
                              ),
                            ),
                          ),
                          if (_isInCollection)
                            GestureDetector(
                              onTap: _takePhotoForJournal,
                              child: Padding(
                                padding: const EdgeInsets.only(left: AppSpacing.sm),
                                child: Icon(Icons.camera_alt_outlined, size: 20, color: AppColors.primary),
                              ),
                            ),
                        ],
                      ),
                      if (_scientific.isNotEmpty && _scientific != _title)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            _scientific,
                            style: TextStyle(
                              fontSize: AppFontSize.lg,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),

              // ═══ DESCRIPTION (green bubble like RN) ═══
              if (_description != null && _description!.isNotEmpty)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                    child: GestureDetector(
                      onTap: () => setState(() => _descExpanded = !_descExpanded),
                      child: Container(
                        margin: const EdgeInsets.only(bottom: AppSpacing.md),
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(AppBorderRadius.lg),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _description!,
                              maxLines: _descExpanded ? null : 3,
                              overflow: _descExpanded ? null : TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: AppFontSize.md,
                                color: Color(0xFF1B5E20),
                                height: 1.4,
                              ),
                            ),
                            // Difficulty + Taxonomy inside expandable area
                            if (_descExpanded) ...[
                              const Divider(height: AppSpacing.xl),
                              // ── Difficulty (full, with note) ──
                              Text('Difficulty', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w700, color: const Color(0xFF1B5E20))),
                              const SizedBox(height: AppSpacing.xs),
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
                              if (_lib?.difficultyNote.isNotEmpty == true) ...[
                                const SizedBox(height: AppSpacing.xs),
                                Text(_lib!.difficultyNote, style: TextStyle(fontSize: AppFontSize.sm, color: const Color(0xFF2E7D32), height: 1.4)),
                              ],
                              // ── Taxonomy (full, with all fields) ──
                              const Divider(height: AppSpacing.xl),
                              Text('Taxonomy', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w700, color: const Color(0xFF1B5E20))),
                              const SizedBox(height: AppSpacing.xs),
                              _InfoRow(
                                icon: Icons.science_outlined,
                                text: _scientific,
                                iconColor: const Color(0xFF2E7D32),
                                sub: [
                                  _lib?.genus ?? _dbStr('genus'),
                                  _lib?.family ?? (_dbDetail?['family'] as String? ?? ''),
                                  _lib?.order ?? _dbStr('order'),
                                ].where((s) => s.isNotEmpty).join(' \u00B7 '),
                              ),
                              if ((_lib?.origin ?? _dbStr('origin')).isNotEmpty)
                                _InfoRow(
                                  icon: Icons.public_outlined,
                                  text: _lib?.origin ?? _dbStr('origin'),
                                  iconColor: const Color(0xFF2E7D32),
                                  sub: 'Origin',
                                ),
                              if ((_lib?.synonyms ?? []).isNotEmpty) ...[
                                const SizedBox(height: AppSpacing.xs),
                                Text('Also known as: ${_lib!.synonyms.join(', ')}',
                                  style: TextStyle(fontSize: AppFontSize.xs, color: const Color(0xFF2E7D32), fontStyle: FontStyle.italic)),
                              ],
                            ],
                            if (_description!.length > 120 || !_descExpanded)
                              Align(
                                alignment: Alignment.centerRight,
                                child: Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Icon(
                                    _descExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                                    size: 22,
                                    color: AppColors.primary,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
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
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Column(
                    children: [
                    // ══════ GROUP: Care ══════
                    _groupHeader('Care'),

                    // ── 1. Water (RN: InfoRow freq+demand, soil hint, winter freq, warning) ──
                    _buildSection('water', 'Water', [
                      _InfoRow(
                        icon: Icons.water_drop_outlined,
                        text: 'Every ~$_currentWateringDays days in ${_months[DateTime.now().month - 1]}',
                        sub: (_lib?.wateringDemand.isNotEmpty == true ? '${_lib!.wateringDemand} demand'
                            : _dbCareStr('watering_demand').isNotEmpty ? '${_dbCareStr('watering_demand')} demand' : null),
                      ),
                      if (_lib?.wateringSoilHint.isNotEmpty == true)
                        _InfoRow(icon: Icons.touch_app_outlined, text: _lib!.wateringSoilHint, sub: 'When to water'),
                      if ((_lib?.wateringFreqWinterDays ?? 0) > 0)
                        _InfoRow(icon: Icons.ac_unit_outlined, text: 'Every ~${_lib!.wateringFreqWinterDays} days in winter', sub: 'Winter schedule'),
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

                    const SizedBox(height: AppSpacing.lg),
                    // ══════ GROUP: Environment ══════
                    _groupHeader('Environment'),

                    // ── 4. Light (RN: LightLevelIndicator + InfoRow preferred + Measure button) ──
                    _buildSection('light', 'Light', [
                      LightLevelIndicator(lightText: _dbCareStr('light').isNotEmpty ? _dbCareStr('light') : _lib?.care.light ?? care.light),
                      _InfoRow(
                        icon: Icons.wb_sunny_outlined,
                        text: _dbCareStr('light').isNotEmpty ? _dbCareStr('light') : _lib?.care.light ?? care.light,
                        sub: 'Preferred',
                      ),
                    ], guideLabel: 'Understanding light', action: _buildMeasureButton()),

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

                    const SizedBox(height: AppSpacing.lg),
                    // ══════ GROUP: Toxicity ══════
                    _groupHeader('Toxicity'),

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

                    const SizedBox(height: AppSpacing.lg),
                    // ══════ GROUP: Growing ══════
                    _groupHeader('Growing'),

                    // ── 9. Pruning (expandable with icon, NO guide) ──
                    _buildSection('pruning', 'Pruning', [
                      _ExpandableText(
                        text: _lib?.pruningInfo.isNotEmpty == true ? _lib!.pruningInfo
                            : _dbStr('pruning_info').isNotEmpty ? _dbStr('pruning_info')
                            : 'Remove dead or damaged leaves. Prune to shape as needed.',
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

                    const SizedBox(height: AppSpacing.lg),
                    // ══════ GROUP: About ══════
                    _groupHeader('About'),

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

                    // ── 15. Used for (RN: chips with individual green coloring) ──
                    _buildSection('used_for', 'Used for', [
                      () {
                        final tags = _lib?.usedFor ?? _dbList('used_for');
                        if (tags.isNotEmpty) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                            child: Wrap(
                              spacing: AppSpacing.xs,
                              runSpacing: AppSpacing.xs,
                              children: tags.map((tag) {
                                final isEdible = tag.contains('Edible') || tag.contains('Fruiting');
                                return Container(
                                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: isEdible ? const Color(0xFFDCFCE7) : const Color(0xFFF3F4F6),
                                    borderRadius: AppBorderRadius.smAll,
                                  ),
                                  child: Text(tag, style: TextStyle(fontSize: AppFontSize.xs, fontWeight: FontWeight.w600, color: isEdible ? const Color(0xFF166534) : AppColors.text)),
                                );
                              }).toList(),
                            ),
                          );
                        }
                        final fallbackTag = _plantType == 'greens' ? 'Edible greens' : _plantType == 'fruiting' ? 'Fruiting' : 'Decorative';
                        final isEdible = _plantType != 'decorative';
                        return _ChipRow(chips: [fallbackTag], green: isEdible);
                      }(),
                      if (_lib?.edibleParts.isNotEmpty == true)
                        _InfoRow(icon: Icons.restaurant_outlined, text: _lib!.edibleParts, sub: 'Edible parts', iconColor: AppColors.success),
                    ], guideLabel: 'Uses & benefits'),

                    const SizedBox(height: AppSpacing.lg),
                    // ══════ GROUP: Companions ══════
                    _groupHeader('Companions'),

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
                          ],
                        );
                      }(),
                    ], guideLabel: ((_lib?.goodCompanions ?? []).isNotEmpty || (_lib?.badCompanions ?? []).isNotEmpty) ? 'Plant companions' : null),

                    // Bottom padding so floating "Add to My Plants" button doesn't overlap content
                    SizedBox(height: _isInCollection ? 24 : 120),
                  ],
                  ),
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
    // Water demand (from lib or parse care text)
    final waterLabel = _lib?.wateringDemand.isNotEmpty == true
        ? _lib!.wateringDemand
        : care.watering.contains('2-3 week') ? 'Low'
        : care.watering.contains('7-10') || care.watering.contains('7 day') ? 'Medium'
        : 'High';

    // Light
    final lightText = _lib?.care.light ?? care.light;
    final lightLabel = lightText.contains('Full') ? 'Full sun'
        : lightText.contains('indirect') ? 'Indirect'
        : 'Part sun';

    // Difficulty
    final diff = _lib?.difficulty ?? 'Medium';
    final diffStars = diff.toLowerCase().contains('adv') ? 3 : diff.toLowerCase().contains('med') ? 2 : 1;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // 1. Water
        _RoundBadge(icon: Icons.water_drop, label: waterLabel, bgColor: const Color(0xFFEBF5FF), iconColor: const Color(0xFF3B82F6)),
        const SizedBox(width: AppSpacing.md),
        // 2. Light
        _RoundBadge(icon: lightText.contains('Full') ? Icons.wb_sunny : Icons.wb_sunny_outlined, label: lightLabel, bgColor: const Color(0xFFFFF8E1), iconColor: const Color(0xFFF59E0B)),
        const SizedBox(width: AppSpacing.md),
        // 3. Difficulty
        if (diff.isNotEmpty) ...[
          _RoundBadge(icon: Icons.star, label: diff, bgColor: diffStars == 1 ? const Color(0xFFDCFCE7) : diffStars == 2 ? const Color(0xFFFEF3C7) : const Color(0xFFFEE2E2), iconColor: diffStars == 1 ? AppColors.success : diffStars == 2 ? const Color(0xFFF59E0B) : AppColors.error),
          const SizedBox(width: AppSpacing.md),
        ],
        // 4. Toxicity (only if toxic)
        if (_isToxic)
          _RoundBadge(icon: Icons.warning_amber, label: 'Toxic', bgColor: const Color(0xFFFEE2E2), iconColor: AppColors.error),
      ],
    );
  }

  Widget _groupHeader(String label) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm, top: AppSpacing.xs),
        child: Text(
          label.toUpperCase(),
          style: TextStyle(
            fontSize: AppFontSize.xs,
            fontWeight: FontWeight.w700,
            color: AppColors.textSecondary,
            letterSpacing: 1.2,
          ),
        ),
      ),
    );
  }

  // ─── Light Meter button (matches RN: compact inline button) ──

  Widget _buildMeasureButton() {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => LightMeterModal(
            plantName: _title,
            ppfdMin: _lib?.care.ppfdMin ?? 100,
            ppfdMax: _lib?.care.ppfdMax ?? 500,
            dliMin: _lib?.care.dliMin ?? 4,
            dliMax: _lib?.care.dliMax ?? 20,
          ),
        ));
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: AppColors.primary,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.flashlight_on, size: 16, color: Colors.white),
            const SizedBox(width: 4),
            Text('Measure', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: Colors.white)),
          ],
        ),
      ),
    );
  }

  // ─── Section builder ─────────────────────────────────────────

  Widget _buildSection(String key, String title, List<Widget> children, {String? guideLabel, Widget? action}) {
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
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: AppFontSize.md,
                    fontWeight: FontWeight.w700,
                    color: AppColors.text,
                  ),
                ),
              ),
              if (action != null) action,
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ...children,
          if (guideLabel != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Center(
              child: GestureDetector(
                onTap: () => _showGuide(title, key),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
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
            ),
          ],
        ],
      ),
    );
  }

  // RN-exact guide titles
  static const _guideTitles = {
    'water': 'Watering guide',
    'light': 'Understanding light',
    'humidity': 'Managing humidity',
    'temperature': 'Temperature & climate',
    'outdoor': 'Indoor & outdoor',
    'toxicity': 'Toxicity details',
    'used_for': 'Uses & benefits',
    'soil': 'Repotting guide',
    'fertilizing': 'Fertilizing guide',
    'size': 'Growth & dimensions',
    'propagation': 'Germination & propagation',
    'harvest': 'Harvesting guide',
    'lifecycle': 'Lifecycle',
    'companions': 'Plant companions',
  };

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
        builder: (ctx, scrollController) => Column(
          children: [
            // ─── Header: title left, X right (RN: modalHeader) ───
            Container(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.xl, AppSpacing.lg, AppSpacing.md),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.border)),
              ),
              child: Row(
                children: [
                  const SizedBox(width: 24), // balance for X button
                  Expanded(
                    child: Text(
                      _guideTitles[sectionKey] ?? '$title guide',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: AppFontSize.lg, fontWeight: FontWeight.w700, color: AppColors.text),
                    ),
                  ),
                  GestureDetector(
                    onTap: () => Navigator.pop(ctx),
                    child: Icon(Icons.close, size: 24, color: AppColors.text),
                  ),
                ],
              ),
            ),
            // ─── Content ───
            Expanded(
              child: ListView(
                controller: scrollController,
                padding: const EdgeInsets.all(AppSpacing.lg),
                children: [
                  Text(_title, style: TextStyle(fontSize: AppFontSize.md, color: AppColors.textSecondary)),
                  const SizedBox(height: AppSpacing.lg),
                  ..._guideContent(sectionKey, care),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _guideContent(String key, _PresetCare care) {
    final p = _lib;
    final c = p?.care;
    switch (key) {
      // ═══ WATERING GUIDE (RN 1:1) ═══
      case 'water':
        return [
          _guideSectionTitle('Watering frequency'),
          _WateringChart(
            baseDays: _lib?.wateringFreqSummerDays ?? _presetWateringDays,
            currentMonth: DateTime.now().month - 1,
            latitude: _locationData?.latitude,
          ),
          _guideSection('How to water $_title', p?.wateringMethod ?? c?.watering ?? care.watering),
          if (p?.wateringAvoid.isNotEmpty == true) ...[
            _guideSectionTitle('What to avoid'),
            InfoBox(text: p!.wateringAvoid, variant: 'warning'),
          ],
          _guideSectionTitle('Drainage'),
          InfoBox(text: 'Make sure your pot has drainage holes at the bottom. Without drainage, water collects and roots rot. If your pot has no holes, use it as a cachepot \u2014 place a smaller pot with holes inside.', variant: 'info'),
          // Watering methods
          _guideSectionTitle('Watering methods'),
          _guideMethod('Water over soil', 'Slowly pour water over the soil surface until it runs out of drainage holes. Let it drain completely. Discard excess from the saucer.', (p?.wateringMethod ?? '').contains('soil')),
          _guideMethod('Bottom watering', 'Place the pot in a tray of water for 15\u201320 minutes. The soil absorbs water from below through the drainage holes. Remove and let drain.', (p?.wateringMethod ?? '').toLowerCase().contains('bottom')),
          _guideMethod('Water bath / soak', 'Submerge the entire pot in water for 10\u201315 minutes, then drain. Best for bark-based substrates (orchids) and very dry soil that repels water from the top.', (p?.wateringMethod ?? '').toLowerCase().contains('soak') || (p?.wateringMethod ?? '').toLowerCase().contains('bark')),
        ];
      // ═══ LIGHT GUIDE (RN 1:1) ═══
      case 'light':
        final lightText = c?.light ?? care.light;
        return [
          _guideSection('How to light $_title',
            lightText.contains('Full') || lightText.contains('Bright')
              ? 'South-facing window, 6+ hours direct sun.'
              : lightText.contains('indirect')
                ? 'East or west window. No direct sun.'
                : 'North-facing window or away from direct light.'),
          // Light levels
          _guideSectionTitle('Light levels'),
          _guideMethod('Full sun (6+ hours direct)', 'Aloes, Succulents, Cacti, Herbs. Place in south-facing window.', lightText.contains('Full') || lightText.contains('direct')),
          _guideMethod('Part sun / bright indirect (2\u20134 hours)', 'Monstera, Orchids, Calathea. East or west window, or sheer curtain on south.', lightText.contains('indirect') || lightText.contains('Bright')),
          _guideMethod('Shade (no direct sun)', 'ZZ Plant, Pothos, Snake Plant. North-facing window or interior of room.', lightText.contains('Low') || lightText.contains('shade')),
          // Warnings
          _guideSectionTitle('Warnings'),
          if (lightText.contains('Full') || lightText.contains('Bright')) ...[
            InfoBox(text: 'Without enough light, $_title will stretch, lose color, and weaken.', variant: 'warning'),
            InfoBox(text: 'In northern regions Oct\u2013Mar, $_title may need a grow light (full-spectrum LED, 12\u201314h daily).', variant: 'warning'),
          ] else if (lightText.contains('indirect')) ...[
            InfoBox(text: 'Direct sun burns the leaves of $_title. Keep away from unfiltered south-facing windows.', variant: 'warning'),
          ] else ...[
            InfoBox(text: '$_title tolerates low light, but growth will slow significantly in very dark spots.', variant: 'info'),
          ],
          _guideSectionTitle('Signs of incorrect lighting'),
          _guideSection('Not enough light', '\u2022 Leaves turn yellow and fall off\n\u2022 New leaves smaller than older ones\n\u2022 Plant stretches towards light\n\u2022 Slow, weak growth\n\u2022 Leaves far apart on stem'),
          _guideSection('Too much light', '\u2022 Leaves drooping\n\u2022 Leaf edges dry up\n\u2022 Color fading\n\u2022 Flowers shrivel and die'),
          if ((c?.ppfdMin ?? 0) > 0) ...[
            _guideSectionTitle('Light intensity'),
            _InfoRow(icon: Icons.wb_sunny_outlined, text: '${c!.ppfdMin}\u2013${c.ppfdMax} PPFD', sub: 'Photosynthetic Photon Flux Density'),
            _InfoRow(icon: Icons.timer_outlined, text: '${c.dliMin}\u2013${c.dliMax} DLI', sub: 'Daily Light Integral'),
            InfoBox(text: 'PPFD measures how much usable light reaches the plant per second. DLI is the total light received per day. These values help when choosing a grow light \u2014 match its output to the plant\u2019s needs.', variant: 'info'),
          ],
        ];
      // ═══ HUMIDITY GUIDE (RN 1:1) ═══
      case 'humidity':
        final humText = (c?.humidity ?? care.humidity).toLowerCase();
        return [
          _guideSection('Humidity for $_title', c?.humidity ?? care.humidity),
          if (c?.humidityAction.isNotEmpty == true)
            _guideSection('', c!.humidityAction),
          _guideSectionTitle('Warnings'),
          if (humText.contains('high') || humText.contains('60') || humText.contains('70') || humText.contains('80')) ...[
            InfoBox(text: '$_title needs high humidity. In dry apartments (especially with central heating in winter), leaf tips will turn brown and crispy.', variant: 'warning'),
            InfoBox(text: 'Low humidity also attracts spider mites \u2014 the #1 indoor pest for tropical plants.', variant: 'warning'),
          ] else if (humText.contains('low') || humText.contains('dry')) ...[
            InfoBox(text: '$_title prefers dry air. High humidity causes fungal issues and root rot. Do not mist this plant.', variant: 'warning'),
            InfoBox(text: 'Avoid placing in bathrooms or near humidifiers.', variant: 'warning'),
          ] else ...[
            InfoBox(text: '$_title does fine in average room humidity (40\u201360%). No special measures needed in most homes.', variant: 'info'),
          ],
          _guideSectionTitle('How to increase humidity'),
          _guideSection('', '\u2022 Group plants together \u2014 they create a shared humid microclimate\n\u2022 Place pot on a tray with pebbles and water (not touching pot bottom)\n\u2022 Mist leaves in the morning (not evening \u2014 fungal risk)\n\u2022 Use a humidifier in the room'),
          _guideSectionTitle('How to decrease humidity'),
          _guideSection('', '\u2022 Improve air circulation \u2014 open a window, use a small fan\n\u2022 Reduce misting\n\u2022 Move plant to a drier room\n\u2022 Avoid overcrowding plants'),
        ];
      // ═══ TEMPERATURE GUIDE (RN 1:1) ═══
      case 'temperature':
        return [
          _guideSection('Indoor temperature for $_title',
            _preset == 'Tropical'
              ? '$_title is a tropical plant. It thrives at typical room temperature (${_fmtTemp(18)}\u2013${_fmtTemp(27)}) all year. No special temperature adjustments needed indoors.'
              : _preset == 'Succulents'
                ? '$_title comes from an arid climate. Normal room temperature works year-round. A slight winter cool-down (${_fmtTemp(10)}\u2013${_fmtTemp(15)}) can encourage blooming, but is not required to keep the plant alive.'
                : _preset == 'Herbs'
                  ? '$_title prefers moderate temperatures. Some herbs from temperate climates benefit from cooler winters. Avoid hot radiators and cold drafts equally.'
                  : '$_title is a temperate plant. It may need a cooler winter period (dormancy) to stay healthy long-term. Without winter cool-down, it can weaken and become susceptible to pests.'),
          _guideSectionTitle('Summer (optimal)'),
          TempRangeBar(optLow: p?.tempOptLowC ?? 15, optHigh: p?.tempOptHighC ?? 25, color: const Color(0xFFEF4444), formatT: _fmtTemp),
          if ((p?.tempWinterLowC ?? 0) > 0) ...[
            _guideSectionTitle('Winter (optimal)'),
            TempRangeBar(optLow: p!.tempWinterLowC, optHigh: p.tempWinterHighC, color: const Color(0xFF6B7280), formatT: _fmtTemp),
          ],
          if (p?.tempWarning.isNotEmpty == true) ...[
            _guideSectionTitle('Warnings'),
            InfoBox(text: p!.tempWarning, variant: 'warning'),
          ],
          _guideSectionTitle('Current conditions'),
          if (_locationData?.hasData == true) ...[
            () {
              final currentTemp = _locationData!.monthlyAvgTemps[DateTime.now().month - 1];
              final optLow = p?.tempOptLowC ?? 15;
              final optHigh = p?.tempOptHighC ?? 25;
              final minC = p?.tempMinC ?? 5;
              final inOptimal = currentTemp >= optLow && currentTemp <= optHigh;
              final canSurvive = currentTemp >= minC;
              return InfoBox(
                text: 'It\'s ${_fmtTemp(currentTemp.round())} outside right now. ${inOptimal ? 'This is within the optimal range for this plant.' : canSurvive ? 'The plant can survive at this temperature, but it\'s outside the optimal range.' : 'Too cold \u2014 keep this plant indoors.'}',
                variant: inOptimal ? 'success' : 'warning',
              );
            }(),
          ] else
            InfoBox(text: 'Enable location services to see current outdoor temperature in your area and whether it\'s safe to place this plant outside.', variant: 'info'),
          _guideSectionTitle('Common indoor problems'),
          _guideSection('', '\u2022 Cold drafts from windows \u2014 move plant away from drafty spots in winter\n\u2022 Hot radiators \u2014 dry out the air and overheat roots on the side closest to heat\n\u2022 Air conditioning \u2014 sudden cold blasts stress tropical plants\n\u2022 Temperature swings day/night \u2014 most plants prefer stable temperature'),
        ];
      // ═══ OUTDOOR GUIDE (RN 1:1) ═══
      case 'outdoor':
        final tempMin = p?.tempMinC ?? 5;
        return [
          _guideSection('$_title outdoors',
            tempMin <= 0
              ? '$_title tolerates light frost and can stay outdoors longer than most houseplants. Still, potted plants are more vulnerable than those in the ground.'
              : tempMin <= 5
                ? '$_title can go outdoors in warm months but must come inside before temperatures drop below ${_fmtTemp(tempMin)}.'
                : '$_title is sensitive to cold. Only put outdoors when nighttime temperatures are consistently above ${_fmtTemp(tempMin + 5)}.'),
          _guideSectionTitle('Outdoor months (potted)'),
          if (_locationData?.hasData == true) ...[
            _guideSection('', 'These are the months $_title can be outdoors in your area. The rest of the year the temperature is too cold.'),
            () {
              final outdoor = GeolocationService.getOutdoorMonths(tempMin.toDouble(), _locationData!.monthlyAvgTemps);
              return _MonthBar(activeMonths: outdoor.potted, color: const Color(0xFF22C55E));
            }(),
            _guideSectionTitle('Outdoor months (in ground)'),
            () {
              final outdoor = GeolocationService.getOutdoorMonths(tempMin.toDouble(), _locationData!.monthlyAvgTemps);
              return _MonthBar(activeMonths: outdoor.inGround, color: const Color(0xFF16A34A));
            }(),
          ] else
            _guideSection('', 'Enable location to see which months are safe for outdoor placement in your area.'),
          _guideSectionTitle('Frost tolerance'),
          _InfoRow(icon: Icons.thermostat_outlined, text: _fmtTemp(tempMin), sub: 'Lowest temp to survive when potted'),
          InfoBox(text: 'This is the temperature the plant can endure \u2014 not the temperature it prefers. At this point the plant suffers: leaves may drop, growth stops, scarring occurs. It should survive and recover once moved to warmth.', variant: 'info'),
          _guideSectionTitle('Potted vs in ground'),
          _guideSection('', 'A plant in the ground has soil insulation protecting its roots. A potted plant has exposed sides \u2014 the pot freezes through much faster. This means potted plants need to come inside earlier in autumn and go out later in spring.'),
          _guideSectionTitle('Frost tolerance zones'),
          _guideSection('', 'A frost tolerance zone is based on the average lowest winter temperature in your area. It determines which plants can survive outdoors year-round.'),
          _guideSection('', 'Zones range from 1a (coldest, below -51\u00b0C) to 13b (warmest, above 21\u00b0C). Each zone spans about 5\u00b0C.'),
          _guideSection('', 'Important: these zones assume the plant is in the ground. Potted plants are 1\u20132 zones less hardy because roots are exposed to cold from all sides.'),
          if (_locationData?.hasData == true && _locationData!.cityName.isNotEmpty) ...[
            InfoBox(text: 'Your zone: ${_locationData!.hardinessZone}. Current outdoor temperature: ${_fmtTemp(_locationData!.monthlyAvgTemps[DateTime.now().month - 1].round())}.', variant: 'success'),
          ] else
            InfoBox(text: 'Enable location services and we will determine your frost tolerance zone automatically.', variant: 'info'),
        ];
      // ═══ TOXICITY GUIDE (RN 1:1) ═══
      case 'toxicity':
        return [
          _guideSection('Toxicity of $_title', ''),
          _InfoRow(icon: Icons.warning_amber_outlined, text: p?.toxicitySeverity.isNotEmpty == true ? '${p!.toxicitySeverity} toxicity' : 'Toxic', iconColor: AppColors.error),
          _ChipRow(chips: [
            if (p?.poisonousToHumans == true) 'Humans',
            if (p?.poisonousToPets == true) ...'Cats,Dogs'.split(','),
          ]),
          if (p?.toxicParts.isNotEmpty == true) ...[
            _guideSectionTitle('Toxic parts'),
            _guideSection('', p!.toxicParts),
          ],
          if (p?.edible == true && p?.edibleParts.isNotEmpty == true) ...[
            _guideSectionTitle('Edible parts'),
            _InfoRow(icon: Icons.restaurant_outlined, text: p!.edibleParts, iconColor: AppColors.success),
          ],
          if (p?.toxicitySymptoms.isNotEmpty == true) ...[
            _guideSectionTitle('Symptoms by exposure'),
            ...p!.toxicitySymptoms.split('\n').where((l) => l.isNotEmpty).map((line) {
              final parts = line.split(': ');
              if (parts.length >= 2) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(parts[0], style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
                    Text(parts.sublist(1).join(': '), style: TextStyle(fontSize: AppFontSize.sm, color: AppColors.textSecondary, height: 1.4)),
                  ]),
                );
              }
              return _guideSection('', line);
            }),
          ],
          if (p?.toxicityFirstAid.isNotEmpty == true) ...[
            _guideSectionTitle('What to do'),
            ...p!.toxicityFirstAid.split('\n').where((l) => l.isNotEmpty).map((line) {
              final parts = line.split(': ');
              if (parts.length >= 2) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(parts[0], style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
                    Text(parts.sublist(1).join(': '), style: TextStyle(fontSize: AppFontSize.sm, color: AppColors.textSecondary, height: 1.4)),
                  ]),
                );
              }
              return _guideSection('', line);
            }),
          ],
          if (p?.toxicityNote.isNotEmpty == true)
            InfoBox(text: p!.toxicityNote, variant: 'warning'),
          _guideSectionTitle('Disclaimer'),
          InfoBox(text: 'Toxicity information is compiled from multiple botanical sources and may not be exhaustive. Individual reactions vary \u2014 allergies and sensitivities are not covered here. If you or your pet ingested any plant material and feel unwell, contact a medical professional or poison control center immediately. This is not medical advice.', variant: 'info'),
        ];
      // ═══ SOIL / REPOTTING GUIDE (RN 1:1) ═══
      case 'soil':
        return [
          _guideSection('Repotting $_title', ''),
          _InfoRow(icon: Icons.swap_vert, text: c?.repot ?? care.repot, sub: 'Frequency'),
          if (p?.repotSigns.isNotEmpty == true) ...[
            Text('Signs it\'s time:', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
            _guideSection('', p!.repotSigns),
          ],
          _guideSectionTitle('Pot'),
          if (p?.potType.isNotEmpty == true)
            _InfoRow(icon: Icons.inventory_2_outlined, text: p!.potType),
          if (p?.potSizeNote.isNotEmpty == true)
            _guideSection('', p!.potSizeNote),
          InfoBox(text: 'Always use a pot with drainage holes. No drainage = standing water = root rot. If you love a decorative pot without holes, use it as a cachepot \u2014 place a smaller pot with holes inside.', variant: 'warning'),
          // Repotting steps
          _guideSectionTitle('How to repot (step by step)'),
          _guideSection('', '1. Water the plant the day before repotting\n2. Choose a pot 2\u20134 cm wider than the current one\n3. Add drainage material (expanded clay, gravel) to the bottom\n4. Fill 1/3 with fresh soil\n5. Carefully remove the plant \u2014 squeeze the pot or use a knife along the edges\n6. Inspect roots \u2014 trim any dead (brown, mushy) roots with clean scissors\n7. Place plant in the new pot at the same depth as before\n8. Fill with soil around the root ball, press gently\n9. Water thoroughly and let drain'),
          _guideSectionTitle('Soil for $_title'),
          _guideSection('', c?.soil ?? care.soil),
          if (p?.soilTypes.isNotEmpty == true) ...[
            _guideSectionTitle('Recommended soil types'),
            _ChipRow(chips: p!.soilTypes),
          ],
          // pH section (from RN)
          // TODO: PHBar visual component when soil_ph data available
          _guideSectionTitle('Soil acidity (pH)'),
          InfoBox(text: 'pH below 7 is acidic (peat, pine bark). pH above 7 is alkaline (limestone, chalk). Most houseplants prefer slightly acidic to neutral (5.5\u20137.0). Test with a simple pH kit from any garden store.', variant: 'info'),
          _guideSectionTitle('Cleaning'),
          _guideSection('', 'Wipe leaves with a damp cloth regularly. Dust blocks light absorption and slows photosynthesis. For fuzzy-leaved plants, use a soft brush instead.'),
        ];
      // ═══ FERTILIZING GUIDE (RN 1:1) ═══
      case 'fertilizing':
        return [
          _guideSection('Fertilizing $_title', ''),
          _InfoRow(icon: Icons.eco_outlined, text: c?.fertilizer ?? care.fertilizer, sub: c?.fertilizerSeason ?? care.fertilizerSeason),
          if (p?.fertilizerTypes.isNotEmpty == true) ...[
            _guideSectionTitle('Recommended fertilizers'),
            _ChipRow(chips: p!.fertilizerTypes),
          ],
          if (p?.fertilizerNpk.isNotEmpty == true) ...[
            _guideSectionTitle('NPK ratio'),
            _InfoRow(icon: Icons.science_outlined, text: p!.fertilizerNpk, sub: 'Nitrogen \u2013 Phosphorus \u2013 Potassium'),
            InfoBox(text: 'NPK is the three numbers on every fertilizer bottle. N (nitrogen) = leaf growth. P (phosphorus) = roots and flowers. K (potassium) = overall health and fruit. Match the ratio to what your plant needs most.', variant: 'info'),
          ],
          if (p?.fertilizerWarning.isNotEmpty == true) ...[
            _guideSectionTitle('Warnings'),
            InfoBox(text: p!.fertilizerWarning, variant: 'warning'),
          ],
          _guideSectionTitle('When NOT to fertilize'),
          _guideSection('', '\u2022 Winter \u2014 plant is dormant, nutrients accumulate and burn roots\n\u2022 Right after repotting \u2014 fresh soil has nutrients for 2\u20134 weeks\n\u2022 Sick or stressed plant \u2014 fix the problem first, then feed\n\u2022 Dry soil \u2014 always water before fertilizing to avoid root burn'),
          _guideSectionTitle('Signs of over-fertilizing'),
          _guideSection('', '\u2022 White crust on soil surface (salt buildup)\n\u2022 Brown, crispy leaf tips and edges\n\u2022 Wilting despite moist soil\n\u2022 Slow growth or dropping leaves'),
          _guideSectionTitle('Signs of under-fertilizing'),
          _guideSection('', '\u2022 Pale or yellow leaves (especially older ones)\n\u2022 Slow or stunted growth\n\u2022 Small new leaves\n\u2022 No flowers on a flowering plant'),
        ];
      // ═══ SIZE GUIDE (RN 1:1) ═══
      case 'size':
        return [
          _guideSection('$_title dimensions', ''),
          _InfoRow(icon: Icons.height_outlined, text: '${p?.heightMinCm ?? 0} \u2013 ${p?.heightMaxCm ?? 0} cm', sub: 'Height (mature plant, in ground)'),
          if ((p?.spreadMaxCm ?? 0) > 0)
            _InfoRow(icon: Icons.swap_horiz_outlined, text: 'Up to ${p!.spreadMaxCm} cm', sub: 'Crown diameter'),
          _InfoRow(icon: Icons.trending_up_outlined, text: p?.growthRate ?? 'Not specified', sub: 'Growth rate'),
          InfoBox(text: 'These dimensions are for a full grown plant in ideal conditions (in ground, outdoors). Indoor plants in pots will be significantly smaller.', variant: 'info'),
          if ((p?.heightIndoorMaxCm ?? 0) > 0) ...[
            _guideSectionTitle('In a pot'),
            _InfoRow(icon: Icons.inventory_2_outlined, text: 'Up to ${p!.heightIndoorMaxCm} cm', sub: 'Realistic height in a pot'),
            _guideSection('', 'A pot limits root space, which limits the plant\u2019s overall size. The bigger the pot \u2014 the bigger the plant can grow. But too big a pot holds excess moisture and causes root rot.'),
          ],
          _guideSectionTitle('Recommended pot size'),
          _guideSection('',
            _preset == 'Succulents' ? 'Start with a pot 2\u20133 cm wider than the root ball. Succulents prefer snug pots \u2014 too much soil stays wet and causes rot.'
              : _preset == 'Tropical' ? 'Start with a pot 3\u20135 cm wider than the root ball. Tropical plants grow faster and need room, but not too much at once.'
              : _preset == 'Herbs' ? 'For herbs, a pot 15\u201320 cm in diameter works for most. Deeper pots for plants with long roots (rosemary), shallower for bushy herbs (basil).'
              : 'Start with a pot 2\u20134 cm wider than the root ball. Upsize gradually \u2014 one size at a time.'),
          _guideSectionTitle('If your plant is not growing'),
          _guideSection('', '\u2022 Not enough light \u2014 the #1 reason for stunted growth indoors\n\u2022 Pot too small \u2014 roots have nowhere to go\n\u2022 Wrong soil \u2014 compacted soil chokes roots\n\u2022 Not enough nutrients \u2014 time to fertilize\n\u2022 Dormancy \u2014 normal in winter, growth resumes in spring\n\u2022 Root rot \u2014 check roots if plant is wilting despite watering'),
        ];
      // ═══ PROPAGATION GUIDE (RN 1:1) ═══
      case 'propagation':
        return [
          _guideSection('How to propagate $_title', ''),
          if (p?.propagationMethods.isNotEmpty == true) ...[
            Text('Methods', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
            _ChipRow(chips: p!.propagationMethods),
          ],
          if (p?.propagationDetail.isNotEmpty == true)
            _guideSection('', p!.propagationDetail),
          if ((p?.germinationDays ?? 0) > 0) ...[
            _guideSectionTitle('From seed (germination)'),
            _InfoRow(icon: Icons.timer_outlined, text: '~${p!.germinationDays} days', sub: 'Time to germinate'),
            if (p.germinationTempC.isNotEmpty)
              _InfoRow(icon: Icons.thermostat_outlined, text: p.germinationTempC, sub: 'Optimal temperature'),
          ],
          _guideSectionTitle('General tips'),
          _guideSection('', '\u2022 Always use clean, sharp tools when taking cuttings\n\u2022 Spring and early summer are the best time to propagate\n\u2022 Keep soil moist but not soggy for new cuttings\n\u2022 Bright indirect light \u2014 no direct sun on fresh cuttings\n\u2022 Be patient \u2014 rooting can take weeks'),
        ];
      // ═══ HARVEST GUIDE (RN 1:1) ═══
      case 'harvest':
        return [
          if (p?.edibleParts.isNotEmpty == true) ...[
            _guideSectionTitle('Edible parts'),
            _InfoRow(icon: Icons.restaurant_outlined, text: p!.edibleParts, iconColor: AppColors.success),
          ],
          if (p?.harvestInfo.isNotEmpty == true)
            _guideSection('How to harvest', p!.harvestInfo),
          if (_plantType == 'fruiting') ...[
            _guideSectionTitle('Fruit stages'),
            _guideSection('', '\u2022 Flowering \u2014 pollination needed (shake stems indoors)\n\u2022 Fruit set \u2014 small green fruits appear after pollination\n\u2022 Growing \u2014 fruit enlarges, needs consistent watering\n\u2022 Ripening \u2014 color changes, fruit softens slightly\n\u2022 Harvest \u2014 pick when fully colored and gives slightly to gentle pressure'),
            InfoBox(text: 'Do not pick too early. Unripe fruit lacks flavor and may contain higher levels of toxins (e.g. solanine in green tomatoes).', variant: 'warning'),
          ] else if (_plantType == 'greens') ...[
            _guideSectionTitle('Harvesting tips'),
            _guideSection('', '\u2022 Always harvest from the top \u2014 cut above a leaf pair\n\u2022 Never take more than one-third of the plant at once\n\u2022 Regular harvesting stimulates bushier growth\n\u2022 Harvest in the morning \u2014 oils and flavor are strongest\n\u2022 Pinch off flower buds immediately \u2014 flowering ends leaf production'),
          ],
          if (_isToxic && p?.edible == true)
            InfoBox(text: 'Some parts of $_title are toxic while others are edible. Always know which parts are safe before consuming.', variant: 'warning'),
        ];
      // ═══ LIFECYCLE GUIDE (RN 1:1) ═══
      case 'lifecycle':
        return [
          _guideSection('About $_title', ''),
          _InfoRow(icon: Icons.loop_outlined, text: (p?.lifecycle ?? 'perennial') == 'perennial' ? 'Perennial' : 'Annual', sub: p?.lifecycleYears.isNotEmpty == true ? 'Lives ${p!.lifecycleYears} years' : null),
          if (p?.growthRate.isNotEmpty == true)
            _InfoRow(icon: Icons.trending_up_outlined, text: p!.growthRate, sub: 'Growth rate'),
          _guideSectionTitle('What does this mean?'),
          _guideSection('', (p?.lifecycle ?? 'perennial') == 'perennial'
            ? 'Perennial plants live for more than two years. They grow actively in spring and summer, then slow down or go dormant in winter. During dormancy, reduce watering and stop fertilizing \u2014 the plant is resting, not dying. Most houseplants are perennials.'
            : (p?.lifecycle ?? 'perennial') == 'annual'
              ? 'Annual plants complete their entire lifecycle in one growing season \u2014 from seed to flower to seed again. After producing seeds, the plant naturally dies. This is normal. To continue growing, start new plants from seed or buy new seedlings each season.'
              : 'Biennial plants take two years to complete their lifecycle. In the first year they grow leaves and roots, in the second year they flower, produce seeds, and die. Some plants grown as annuals in cold climates are actually perennials in warmer regions.'),
          _guideSectionTitle('Types of plant lifecycles'),
          Text('Annual', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
          _guideSection('', 'One growing season. Examples: basil, tomato, lettuce, sunflower. Plant \u2192 grow \u2192 harvest \u2192 done.'),
          Text('Perennial', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
          _guideSection('', 'Lives for years. Examples: monstera, jade plant, orchid, rosemary. Goes dormant in winter, comes back in spring.'),
          Text('Biennial', style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
          _guideSection('', 'Two-year cycle. Examples: parsley, carrot, foxglove. Leaves first year, flowers second year, then dies.'),
          _guideSectionTitle('Seasonal care tips'),
          _guideSection('', '\u2022 Spring: active growth starts \u2014 increase watering, start fertilizing\n\u2022 Summer: peak growth \u2014 regular watering and feeding\n\u2022 Autumn: growth slows \u2014 reduce watering gradually\n\u2022 Winter: dormancy \u2014 minimal water, no fertilizer, cooler spot if possible'),
          if (p?.growthRate.isNotEmpty == true) ...[
            _guideSectionTitle('Growth rate'),
            _guideSection('', p!.growthRate == 'Fast' || p.growthRate == 'fast'
              ? '$_title is a fast grower. Expect visible changes weekly during the growing season. May need more frequent repotting and pruning.'
              : p.growthRate == 'Slow' || p.growthRate == 'slow'
                ? '$_title grows slowly. Don\'t worry if you don\'t see changes for weeks \u2014 this is normal. Slow growers are often more tolerant of neglect.'
                : '$_title has a moderate growth rate. With proper care, you\'ll see steady progress during the growing season.'),
          ],
        ];
      // ═══ USED FOR GUIDE (RN 1:1) ═══
      case 'used_for':
        final tags = p?.usedFor ?? [];
        return [
          _guideSectionTitle('What is $_title used for'),
          if (tags.isNotEmpty)
            _ChipRow(chips: tags, green: tags.any((t) => t.contains('Edible') || t.contains('Fruiting'))),
          if (p?.usedForDetails.isNotEmpty == true)
            _guideSection('', p!.usedForDetails),
          if (p?.edibleParts.isNotEmpty == true) ...[
            _guideSectionTitle('Edible parts'),
            _InfoRow(icon: Icons.restaurant_outlined, text: p!.edibleParts, iconColor: AppColors.success),
          ],
          if (p?.harvestInfo.isNotEmpty == true) ...[
            _guideSectionTitle('Harvest'),
            _guideSection('', p!.harvestInfo),
          ],
          if (tags.contains('Air purifier')) ...[
            _guideSectionTitle('Air purification'),
            InfoBox(text: 'According to the NASA Clean Air Study, certain houseplants can remove common indoor pollutants like formaldehyde, benzene, and trichloroethylene. For noticeable effect, aim for 2\u20133 large plants per average room.', variant: 'info'),
          ],
          if (tags.contains('Attracts pollinators')) ...[
            _guideSectionTitle('Pollinators'),
            InfoBox(text: 'This plant attracts bees and butterflies. Great for balconies and gardens where you want to support local pollinator populations.', variant: 'info'),
          ],
        ];
      // ═══ COMPANION GUIDE (RN 1:1) ═══
      case 'companions':
        return [
          _guideSection('Why companion planting matters', 'Some plants grow better together \u2014 they share nutrients, repel each other\u2019s pests, or create beneficial shade. Others compete for the same resources or release chemicals that inhibit their neighbors.'),
          if ((p?.goodCompanions ?? []).isNotEmpty) ...[
            _guideSectionTitle('Good neighbors for $_title'),
            _ChipRow(chips: p!.goodCompanions, green: true),
            _guideSection('', p.companionNote.isNotEmpty ? p.companionNote : 'These plants share similar soil and watering requirements, making them ideal pot or garden neighbors. They can be planted in the same bed or grouped together indoors.'),
          ],
          if ((p?.badCompanions ?? []).isNotEmpty) ...[
            _guideSectionTitle('Keep apart from $_title'),
            _ChipRow(chips: p!.badCompanions, red: true),
            _guideSection('', 'These plants compete for resources, have incompatible soil/water needs, or may inhibit each other\u2019s growth. Keep them in separate containers or different areas.'),
          ],
          _guideSectionTitle('Soil sharing tips'),
          _guideSection('', '\u2022 Plants with similar pH and drainage needs can share soil\n\u2022 After harvesting herbs, their soil is often nutrient-depleted \u2014 refresh before reusing\n\u2022 Rotate crops in the same pot: follow a heavy feeder (tomato) with a light feeder (herbs)\n\u2022 Never reuse soil from a diseased plant'),
          _guideSectionTitle('Grouping indoors'),
          _guideSection('', '\u2022 Group plants with similar humidity needs \u2014 they create a shared microclimate\n\u2022 Tall plants can provide shade for low-light neighbors\n\u2022 Keep pest-prone plants away from healthy ones\n\u2022 Fragrant herbs (rosemary, lavender) can deter pests from nearby plants'),
        ];
      default:
        return [
          _guideSection('Information', 'Detailed guide coming soon.'),
        ];
    }
  }

  Widget _guideSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.lg, bottom: AppSpacing.xs),
      child: Text(title, style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w700, color: AppColors.text)),
    );
  }

  Widget _guideMethod(String title, String description, bool isRecommended) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: isRecommended ? const Color(0xFFDCFCE7) : const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(AppBorderRadius.md),
        border: Border.all(color: isRecommended ? AppColors.success : AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(title, style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text)),
            if (isRecommended) ...[
              const SizedBox(width: AppSpacing.sm),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: AppColors.success, borderRadius: BorderRadius.circular(4)),
                child: const Text('Recommended', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.white)),
              ),
            ],
          ]),
          const SizedBox(height: 4),
          Text(description, style: TextStyle(fontSize: AppFontSize.sm, color: AppColors.textSecondary, height: 1.4)),
        ],
      ),
    );
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

  Widget _buildPhotoCarousel() {
    return Stack(
      fit: StackFit.expand,
      children: [
        PageView.builder(
          controller: _pageController,
          itemCount: _photoUrls.length,
          onPageChanged: (i) => setState(() => _currentPhotoIndex = i),
          itemBuilder: (context, index) {
            return GestureDetector(
              onTap: () => _openFullScreenImage(context, photoIndex: index),
              child: Image.network(
                _photoUrls[index],
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => _heroPlaceholder(),
                loadingBuilder: (_, child, progress) {
                  if (progress == null) return child;
                  return _heroPlaceholder();
                },
              ),
            );
          },
        ),
        // Dot indicators
        Positioned(
          bottom: 12,
          left: 0,
          right: 0,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(_photoUrls.length, (i) {
              return Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: i == _currentPhotoIndex
                      ? Colors.white
                      : Colors.white.withValues(alpha: 0.4),
                ),
              );
            }),
          ),
        ),
      ],
    );
  }

  void _openFullScreenImage(BuildContext context, {int photoIndex = 0}) {
    final urls = _photoUrls.isNotEmpty ? _photoUrls : (_imageUrl != null ? [_imageUrl!] : <String>[]);
    if (urls.isEmpty) return;

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _FullScreenGallery(urls: urls, initialIndex: photoIndex),
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

// ─── Month bar (outdoor months visualization, matches RN MonthBar) ──

class _MonthBar extends StatelessWidget {
  final List<String> activeMonths;
  final Color color;
  const _MonthBar({required this.activeMonths, required this.color});

  static const _monthLabels = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
  static const _monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        children: List.generate(12, (i) {
          final active = activeMonths.contains(_monthNames[i]);
          return Expanded(
            child: Column(
              children: [
                Container(
                  width: 12, height: 12,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: active ? color : const Color(0xFFD1D5DB),
                  ),
                ),
                const SizedBox(height: 3),
                Text(_monthLabels[i], style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              ],
            ),
          );
        }),
      ),
    );
  }
}

// ─── Watering chart (monthly frequency bars, matches RN WateringChart) ──

class _WateringChart extends StatefulWidget {
  final int baseDays;
  final int currentMonth;
  final double? latitude;
  const _WateringChart({required this.baseDays, required this.currentMonth, this.latitude});

  @override
  State<_WateringChart> createState() => _WateringChartState();
}

class _WateringChartState extends State<_WateringChart> {
  int? _selectedMonth;

  @override
  Widget build(BuildContext context) {
    final coeffs = GeolocationService.getSeasonCoefficients(widget.latitude);
    final daysPerMonth = coeffs.map((c) => (widget.baseDays * c).round()).toList();
    final maxDays = daysPerMonth.reduce((a, b) => a > b ? a : b);
    final minDays = daysPerMonth.reduce((a, b) => a < b ? a : b);

    final activeMonth = _selectedMonth ?? widget.currentMonth;
    final activeDays = daysPerMonth[activeMonth];
    final activeLabel = _months[activeMonth];

    const maxBarHeight = 80.0;
    const labels = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

    return Column(
      children: [
        Text(
          '$activeLabel: every ~$activeDays ${activeDays == 1 ? "day" : "days"}',
          style: TextStyle(fontSize: AppFontSize.sm, fontWeight: FontWeight.w600, color: AppColors.text),
        ),
        const SizedBox(height: AppSpacing.sm),
        SizedBox(
          height: maxBarHeight + 24,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: List.generate(12, (i) {
              final days = daysPerMonth[i];
              final range = maxDays - minDays;
              final barHeight = range > 0
                  ? (maxBarHeight * (1 - (days - minDays) / (range + 1))).clamp(8.0, maxBarHeight)
                  : maxBarHeight * 0.5;
              final isCurrent = i == widget.currentMonth;
              final isSelected = i == activeMonth;
              return Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _selectedMonth = i == widget.currentMonth ? null : i),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Container(
                        height: barHeight,
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        decoration: BoxDecoration(
                          color: isSelected ? AppColors.primary : isCurrent ? const Color(0xFF3B82F6) : const Color(0xFFD1D5DB),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(labels[i], style: TextStyle(
                        fontSize: 10,
                        fontWeight: isCurrent ? FontWeight.w700 : FontWeight.normal,
                        color: isCurrent ? AppColors.primary : AppColors.textSecondary,
                      )),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
      ],
    );
  }
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
          Icon(icon, size: 20, color: iconColor ?? AppColors.textSecondary),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  text,
                  style: TextStyle(
                    fontSize: AppFontSize.md,
                    color: AppColors.text,
                  ),
                ),
                if (sub != null)
                  Text(
                    sub!,
                    style: TextStyle(
                      fontSize: AppFontSize.sm,
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

// ─── Expandable text with icon (for Pruning etc) ────────────

class _ExpandableText extends StatefulWidget {
  const _ExpandableText({required this.text, this.maxLines = 3});
  final String text;
  final int maxLines;

  @override
  State<_ExpandableText> createState() => _ExpandableTextState();
}

class _ExpandableTextState extends State<_ExpandableText> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final needsExpansion = widget.text.length > widget.maxLines * 50;
    return GestureDetector(
      onTap: needsExpansion ? () => setState(() => _expanded = !_expanded) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.text,
            maxLines: _expanded ? null : widget.maxLines,
            overflow: _expanded ? null : TextOverflow.ellipsis,
            style: TextStyle(fontSize: AppFontSize.md, color: AppColors.textSecondary, height: 1.4),
          ),
          if (needsExpansion)
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Icon(
                  _expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                  size: 20,
                  color: AppColors.primary,
                ),
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
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 6),
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
              fontSize: AppFontSize.sm,
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

// ─── Fullscreen photo gallery with swipe ─────────────────────

class _FullScreenGallery extends StatefulWidget {
  const _FullScreenGallery({required this.urls, this.initialIndex = 0});
  final List<String> urls;
  final int initialIndex;

  @override
  State<_FullScreenGallery> createState() => _FullScreenGalleryState();
}

class _FullScreenGalleryState extends State<_FullScreenGallery> {
  late PageController _controller;
  late int _current;

  @override
  void initState() {
    super.initState();
    _current = widget.initialIndex;
    _controller = PageController(initialPage: _current);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: widget.urls.length > 1
            ? Text('${_current + 1} / ${widget.urls.length}',
                style: const TextStyle(color: Colors.white70, fontSize: 14))
            : null,
        centerTitle: true,
      ),
      extendBodyBehindAppBar: true,
      body: Stack(
        children: [
          PageView.builder(
            controller: _controller,
            itemCount: widget.urls.length,
            onPageChanged: (i) => setState(() => _current = i),
            itemBuilder: (context, index) {
              return Center(
                child: Image.network(
                  widget.urls[index],
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const Icon(
                      Icons.broken_image, color: Colors.white54, size: 64),
                  loadingBuilder: (_, child, progress) {
                    if (progress == null) return child;
                    return const Center(
                        child: CircularProgressIndicator(color: Colors.white));
                  },
                ),
              );
            },
          ),
          // Dot indicators
          if (widget.urls.length > 1)
            Positioned(
              bottom: MediaQuery.of(context).padding.bottom + 16,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(widget.urls.length, (i) {
                  return Container(
                    width: 8,
                    height: 8,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: i == _current
                          ? Colors.white
                          : Colors.white.withValues(alpha: 0.4),
                    ),
                  );
                }),
              ),
            ),
        ],
      ),
    );
  }
}
