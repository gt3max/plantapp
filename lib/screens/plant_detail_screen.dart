import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';
import 'package:plantapp/services/library_service.dart';
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
  final _scrollController = ScrollController();

  // Data
  PlantEntry? _userPlant;
  Map<String, dynamic>? _dbDetail;
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
      // Try user plant first
      final plants = await _plantService.getMyPlants();
      final userPlant = plants.where((p) => p.plantId == widget.plantId).firstOrNull;
      if (userPlant != null) {
        if (mounted) setState(() => _userPlant = userPlant);
      }

      // Try Turso DB detail
      try {
        final detail = await _libraryService.getDetail(widget.plantId);
        if (mounted) setState(() => _dbDetail = detail);
      } catch (_) {
        // DB detail not available — OK for user-collection plants
      }
    } catch (e) {
      // Silent — show what we have
    }
    if (mounted) setState(() => _isLoading = false);
  }

  // ─── Derived data ────────────────────────────────────────────

  String get _title {
    if (_userPlant != null) return _userPlant!.displayName;
    final db = _dbDetail;
    if (db != null) return (db['common_name'] as String?) ?? (db['scientific_name'] as String?) ?? 'Plant';
    return 'Plant';
  }

  String get _scientific {
    return _userPlant?.scientific ?? (_dbDetail?['scientific_name'] as String?) ?? '';
  }

  String? get _imageUrl {
    return _userPlant?.imageUrl ?? (_dbDetail?['default_image'] as String?);
  }

  String? get _description => _dbDetail?['description'] as String?;

  String get _preset {
    return _userPlant?.preset ?? (_dbDetail?['preset'] as String?) ?? 'Standard';
  }

  _PresetCare get _care => _presetCare[_preset] ?? _presetCare['Standard']!;

  bool get _isInCollection => _userPlant != null;

  bool get _isToxic {
    return (_userPlant?.poisonousToPets == true) ||
        (_userPlant?.poisonousToHumans == true) ||
        (_dbDetail?['care']?['toxic_to_pets'] == true) ||
        (_dbDetail?['care']?['toxic_to_humans'] == true);
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

    if (_userPlant == null && _dbDetail == null) {
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
                    // ── GROUP: Care ──
                    _buildSection('water', 'Water', [
                      _InfoRow(
                        icon: Icons.water_drop_outlined,
                        text: care.watering,
                      ),
                      _InfoRow(
                        icon: Icons.calendar_today_outlined,
                        text: 'Current month: ${_months[DateTime.now().month - 1]}',
                        sub: care.tips,
                      ),
                    ]),
                    _buildSection('soil', 'Soil', [
                      _InfoRow(icon: Icons.layers_outlined, text: care.soil),
                      _InfoRow(
                          icon: Icons.swap_vert, text: 'Repot: ${care.repot}', sub: 'Repotting'),
                    ]),
                    _buildSection('fertilizing', 'Fertilizing', [
                      _InfoRow(icon: Icons.eco_outlined, text: care.fertilizer, sub: care.fertilizerSeason),
                    ]),

                    // ── GROUP: Environment ──
                    _buildSection('light', 'Light', [
                      _InfoRow(icon: Icons.wb_sunny_outlined, text: care.light, sub: 'Preferred'),
                    ]),
                    _buildSection('humidity', 'Air Humidity', [
                      _InfoRow(icon: Icons.water_drop_outlined, text: care.humidity),
                    ]),
                    _buildSection('temperature', 'Air Temperature', [
                      _InfoRow(icon: Icons.thermostat_outlined, text: care.temperature, sub: 'Ideal range'),
                      _InfoRow(icon: Icons.thermostat_auto_outlined, text: 'Min ${_fmtTemp(5)} / Max ${_fmtTemp(35)}', sub: 'Survival limits'),
                    ]),
                    _buildSection('outdoor', 'Outdoor', [
                      _InfoRow(
                        icon: Icons.park_outlined,
                        text: 'Enable location to see outdoor months',
                        sub: 'Based on your local climate',
                      ),
                    ]),

                    // ── GROUP: Safety ──
                    _buildSection('toxicity', 'Toxicity', [
                      if (_isToxic)
                        _InfoRow(
                          icon: Icons.warning_amber_outlined,
                          text: 'Toxic',
                          iconColor: AppColors.error,
                        )
                      else
                        _InfoRow(
                          icon: Icons.check_circle_outline,
                          text: 'Non-toxic to humans and pets',
                          iconColor: AppColors.success,
                        ),
                    ]),

                    // ── GROUP: Growing ──
                    _buildSection('pruning', 'Pruning', [
                      _InfoRow(
                        icon: Icons.content_cut_outlined,
                        text: 'Remove dead or damaged leaves. Prune to shape as needed.',
                      ),
                    ]),
                    _buildSection('propagation', 'Propagation', [
                      _InfoRow(
                        icon: Icons.call_split_outlined,
                        text: 'Stem cuttings, division',
                        sub: 'Common methods',
                      ),
                    ]),

                    // ── GROUP: About ──
                    _buildSection('difficulty', 'Difficulty', [
                      _InfoRow(icon: Icons.speed_outlined, text: _dbDetail?['care']?['difficulty'] as String? ?? 'Medium'),
                    ]),
                    _buildSection('size', 'Size', [
                      _InfoRow(
                        icon: Icons.height_outlined,
                        text: _dbDetail?['care']?['height_max_cm'] != null
                            ? '${_dbDetail!['care']['height_max_cm']} cm'
                            : 'Not specified',
                        sub: 'Height (mature)',
                      ),
                    ]),
                    _buildSection('lifecycle', 'Lifecycle', [
                      _InfoRow(
                        icon: Icons.loop_outlined,
                        text: _dbDetail?['care']?['lifecycle'] as String? ?? 'Perennial',
                        sub: 'Lives for multiple years',
                      ),
                    ]),
                    _buildSection('used_for', 'Used for', [
                      _InfoRow(icon: Icons.local_florist_outlined, text: 'Decorative'),
                    ]),
                    _buildSection('taxonomy', 'Taxonomy', [
                      _InfoRow(
                        icon: Icons.science_outlined,
                        text: _scientific,
                        sub: _dbDetail?['family'] as String?,
                      ),
                    ]),

                    // ── GROUP: Companions ──
                    _buildSection('companions', 'Companions', [
                      _InfoRow(
                        icon: Icons.group_outlined,
                        text: 'Companion data coming soon',
                        sub: 'Check back after database enrichment',
                      ),
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

  Widget _buildSection(String key, String title, List<Widget> children) {
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
