import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';
import 'package:plantapp/services/reminder_service.dart';

class PlantsScreen extends StatefulWidget {
  const PlantsScreen({super.key});

  @override
  State<PlantsScreen> createState() => _PlantsScreenState();
}

class _PlantsScreenState extends State<PlantsScreen> {
  final _plantService = PlantService.instance;
  final _imagePicker = ImagePicker();

  List<PlantEntry> _plants = [];
  bool _isLoading = true;
  String _activeTab = 'plants'; // 'plants' | 'journal'

  // Identify state
  String _identifyState = 'idle'; // 'idle' | 'loading' | 'results' | 'error'
  String? _previewPath; // Local file path for camera/gallery preview
  List<IdentifyResult> _results = [];
  String? _expandedResultId;
  String? _identifyError;
  String? _savingResultId; // Which result is being saved

  @override
  void initState() {
    super.initState();
    _loadPlants();
  }

  Future<void> _loadPlants() async {
    setState(() => _isLoading = true);
    try {
      final plants = await _plantService.getMyPlants();
      if (mounted) setState(() => _plants = plants);
    } catch (e) {
      // Silent fail — show empty state
    }
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _deletePlant(PlantEntry plant) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete plant?'),
        content: Text('Remove ${plant.displayName} from your collection?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirm != true) return;

    try {
      await _plantService.deletePlant(plant.plantId, deviceId: plant.deviceId);
      _loadPlants();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to delete plant')),
        );
      }
    }
  }

  // ─── Identify flow ───────────────────────────────────────────

  Future<void> _pickAndIdentify(ImageSource source) async {
    try {
      final picked = await _imagePicker.pickImage(
        source: source,
        imageQuality: 70,
        maxWidth: 1024,
        maxHeight: 1024,
      );
      if (picked == null) return;

      setState(() {
        _identifyState = 'loading';
        _previewPath = picked.path;
        _results = [];
        _identifyError = null;
        _expandedResultId = null;
      });

      // Read file and encode to base64
      final bytes = await File(picked.path).readAsBytes();
      final base64Image = base64Encode(bytes);

      // Call identify API
      final results = await _plantService.identify(base64Image);

      if (!mounted) return;

      if (results.isEmpty) {
        setState(() {
          _identifyState = 'error';
          _identifyError = 'No plants identified. Try a clearer photo.';
        });
        return;
      }

      setState(() {
        _identifyState = 'results';
        _results = results;
        _expandedResultId = results.first.id;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _identifyState = 'error';
          _identifyError = e.toString().contains('timeout')
              ? 'Request timed out. Please try again.'
              : 'Failed to identify plant. Please try again.';
        });
      }
    }
  }

  Future<void> _savePlant(IdentifyResult result) async {
    setState(() => _savingResultId = result.id);

    try {
      // Map preset → watering frequency
      const presetDays = {
        'Succulents': 10,
        'Standard': 7,
        'Tropical': 5,
        'Herbs': 2,
      };
      final wateringDays = presetDays[result.care.preset] ?? 7;

      await _plantService.savePlant(SavePlantInput(
        deviceId: 'user-collection',
        plant: {
          'scientific': result.scientific,
          'common_name':
              result.commonNames.isNotEmpty ? result.commonNames.first : null,
          'family': result.family,
          'preset': result.care.preset,
          'start_pct': result.care.startPct,
          'stop_pct': result.care.stopPct,
          'image_url': result.images.isNotEmpty ? result.images.first : null,
          if (result.toxicity != null) ...{
            'poisonous_to_pets': result.toxicity!.poisonousToPets,
            'poisonous_to_humans': result.toxicity!.poisonousToHumans,
            'toxicity_note': result.toxicity!.toxicityNote,
          },
        },
      ));

      if (!mounted) return;

      final name = result.commonNames.isNotEmpty
          ? result.commonNames.first
          : result.scientific;

      // Schedule watering reminder
      try {
        await ReminderService.instance.scheduleWateringReminder(
          plantId: result.scientific,
          plantName: name,
          baseDays: wateringDays,
        );
      } catch (_) {
        // Non-critical — reminder scheduling can fail silently
      }

      // Success — reset and refresh
      setState(() {
        _identifyState = 'idle';
        _previewPath = null;
        _results = [];
        _savingResultId = null;
      });

      _loadPlants();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$name added to My Plants'),
            backgroundColor: AppColors.primary,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _savingResultId = null);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to save plant')),
        );
      }
    }
  }

  void _resetIdentify() {
    setState(() {
      _identifyState = 'idle';
      _previewPath = null;
      _results = [];
      _identifyError = null;
      _expandedResultId = null;
      _savingResultId = null;
    });
  }

  // ─── Build ───────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    // If in identify flow, show that instead of tabs
    if (_identifyState != 'idle') {
      return _buildIdentifyFlow();
    }

    return Column(
      children: [
        // Tab switcher: My Plants | Journal
        Padding(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
          child: Row(
            children: [
              _TabButton(
                label: 'My Plants',
                active: _activeTab == 'plants',
                onTap: () => setState(() => _activeTab = 'plants'),
              ),
              const SizedBox(width: AppSpacing.sm),
              _TabButton(
                label: 'Journal',
                active: _activeTab == 'journal',
                onTap: () => setState(() => _activeTab = 'journal'),
              ),
            ],
          ),
        ),

        // Content
        Expanded(
          child: _activeTab == 'plants'
              ? _buildPlantsTab()
              : _buildJournalTab(),
        ),
      ],
    );
  }

  // ─── Identify flow UI ────────────────────────────────────────

  Widget _buildIdentifyFlow() {
    return Column(
      children: [
        // Header with back button
        Padding(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: _resetIdentify,
              ),
              Text(
                _identifyState == 'loading'
                    ? 'Identifying...'
                    : _identifyState == 'results'
                        ? 'Results'
                        : 'Identify',
                style: TextStyle(
                  fontSize: AppFontSize.lg,
                  fontWeight: FontWeight.w600,
                  color: AppColors.text,
                ),
              ),
            ],
          ),
        ),

        // Preview image
        if (_previewPath != null)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: AppBorderRadius.lgAll,
              border: Border.all(color: AppColors.border),
            ),
            clipBehavior: Clip.antiAlias,
            child: Image.file(
              File(_previewPath!),
              fit: BoxFit.cover,
            ),
          ),

        const SizedBox(height: AppSpacing.lg),

        // Content based on state
        Expanded(
          child: _identifyState == 'loading'
              ? _buildIdentifyLoading()
              : _identifyState == 'error'
                  ? _buildIdentifyError()
                  : _buildIdentifyResults(),
        ),
      ],
    );
  }

  Widget _buildIdentifyLoading() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: AppColors.primary),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Identifying plant...',
            style: TextStyle(
              fontSize: AppFontSize.md,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'This may take up to 30 seconds',
            style: TextStyle(
              fontSize: AppFontSize.sm,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIdentifyError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: AppColors.error),
            const SizedBox(height: AppSpacing.lg),
            Text(
              _identifyError ?? 'Something went wrong',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: AppFontSize.md,
                color: AppColors.text,
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: _resetIdentify,
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: AppSpacing.md),
                ElevatedButton.icon(
                  onPressed: () => _pickAndIdentify(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt_outlined),
                  label: const Text('Try Again'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIdentifyResults() {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      itemCount: _results.length,
      itemBuilder: (context, index) {
        final result = _results[index];
        final isExpanded = _expandedResultId == result.id;

        return _IdentifyResultCard(
          result: result,
          isExpanded: isExpanded,
          isSaving: _savingResultId == result.id,
          onTap: () {
            setState(() {
              _expandedResultId = isExpanded ? null : result.id;
            });
          },
          onSave: () => _savePlant(result),
        );
      },
    );
  }

  // ─── Plants tab ──────────────────────────────────────────────

  Widget _buildPlantsTab() {
    return RefreshIndicator(
      onRefresh: _loadPlants,
      color: AppColors.primary,
      child: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _plants.isEmpty
              ? _buildEmptyState()
              : ListView(
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  children: [
                    ..._plants.map((plant) => Dismissible(
                          key: Key(plant.plantId),
                          direction: DismissDirection.endToStart,
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding:
                                const EdgeInsets.only(right: AppSpacing.xl),
                            color: AppColors.error,
                            child: const Icon(Icons.delete_outline,
                                color: Colors.white),
                          ),
                          confirmDismiss: (_) async {
                            _deletePlant(plant);
                            return false; // Handle manually
                          },
                          child: _PlantCard(
                            plant: plant,
                            onTap: () => context.push('/plant/${plant.plantId}'),
                          ),
                        )),

                    const SizedBox(height: AppSpacing.xl),

                    // Identify buttons
                    _IdentifyButtons(
                      onCamera: () =>
                          _pickAndIdentify(ImageSource.camera),
                      onGallery: () =>
                          _pickAndIdentify(ImageSource.gallery),
                    ),
                    const SizedBox(height: AppSpacing.xxl),
                  ],
                ),
    );
  }

  Widget _buildJournalTab() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.photo_library_outlined,
              size: 48, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'No photos yet',
            style: TextStyle(
                fontSize: AppFontSize.lg, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Open a plant and tap the camera icon\nto start your journal',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: AppFontSize.sm, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return ListView(
      children: [
        const SizedBox(height: 80),
        Icon(Icons.eco_outlined, size: 64, color: AppColors.accent),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'No plants yet',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: AppFontSize.xl,
            fontWeight: FontWeight.w700,
            color: AppColors.text,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Identify a plant by photo to get started',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: AppFontSize.md,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.xxxl),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: _IdentifyButtons(
            onCamera: () => _pickAndIdentify(ImageSource.camera),
            onGallery: () => _pickAndIdentify(ImageSource.gallery),
          ),
        ),
      ],
    );
  }
}

// ─── Sub-widgets ─────────────────────────────────────────────

class _IdentifyButtons extends StatelessWidget {
  const _IdentifyButtons({required this.onCamera, required this.onGallery});
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: onCamera,
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Identify plant'),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: onGallery,
            icon: const Icon(Icons.image_outlined),
            label: const Text('Choose from gallery'),
          ),
        ),
      ],
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.active,
    required this.onTap,
  });
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          color: active ? AppColors.primary : AppColors.surface,
          borderRadius: AppBorderRadius.lgAll,
          border: Border.all(
              color: active ? AppColors.primary : AppColors.border),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: AppFontSize.sm,
            fontWeight: FontWeight.w600,
            color: active ? Colors.white : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}

class _PlantCard extends StatelessWidget {
  const _PlantCard({required this.plant, required this.onTap});
  final PlantEntry plant;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.md),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: AppBorderRadius.lgAll,
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            // Plant image
            ClipRRect(
              borderRadius: AppBorderRadius.mdAll,
              child: plant.imageUrl != null && plant.imageUrl!.isNotEmpty
                  ? Image.network(
                      plant.imageUrl!,
                      width: 56,
                      height: 56,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _imagePlaceholder(),
                    )
                  : _imagePlaceholder(),
            ),
            const SizedBox(width: AppSpacing.md),

            // Plant info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plant.displayName,
                    style: TextStyle(
                      fontSize: AppFontSize.md,
                      fontWeight: FontWeight.w600,
                      color: AppColors.text,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (plant.scientific != null &&
                      plant.commonName != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      plant.scientific!,
                      style: TextStyle(
                        fontSize: AppFontSize.xs,
                        fontStyle: FontStyle.italic,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),

            // Chevron
            Icon(Icons.chevron_right,
                color: AppColors.textSecondary, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _imagePlaceholder() => Container(
        width: 56,
        height: 56,
        color: AppColors.background,
        child: Icon(Icons.eco, color: AppColors.accent, size: 28),
      );
}

// ─── Identify result card ────────────────────────────────────

class _IdentifyResultCard extends StatelessWidget {
  const _IdentifyResultCard({
    required this.result,
    required this.isExpanded,
    required this.isSaving,
    required this.onTap,
    required this.onSave,
  });
  final IdentifyResult result;
  final bool isExpanded;
  final bool isSaving;
  final VoidCallback onTap;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final commonName = result.commonNames.isNotEmpty ? result.commonNames.first : null;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: AppBorderRadius.lgAll,
          border: Border.all(
            color: isExpanded ? AppColors.primary : AppColors.border,
            width: isExpanded ? 1.5 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Large plant image
            if (result.images.isNotEmpty)
              ClipRRect(
                borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(AppBorderRadius.lg)),
                child: Image.network(
                  result.images.first,
                  width: double.infinity,
                  height: 180,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 180,
                    color: AppColors.background,
                    child: Center(
                        child: Icon(Icons.eco, size: 48, color: AppColors.accent)),
                  ),
                ),
              ),

            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name + score row
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (commonName != null)
                              Text(
                                commonName,
                                style: TextStyle(
                                  fontSize: AppFontSize.lg,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.text,
                                ),
                              ),
                            Text(
                              result.scientific,
                              style: TextStyle(
                                fontSize: commonName != null ? AppFontSize.sm : AppFontSize.lg,
                                fontWeight: commonName != null ? FontWeight.w400 : FontWeight.w700,
                                fontStyle: FontStyle.italic,
                                color: commonName != null ? AppColors.textSecondary : AppColors.text,
                              ),
                            ),
                            if (result.family.isNotEmpty) ...[
                              const SizedBox(height: 2),
                              Text(
                                result.family,
                                style: TextStyle(
                                  fontSize: AppFontSize.xs,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),

                      const SizedBox(width: AppSpacing.sm),

                      // Score badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.sm, vertical: 4),
                        decoration: BoxDecoration(
                          color: result.score >= 50
                              ? const Color(0xFFDCFCE7)
                              : const Color(0xFFFEF3C7),
                          borderRadius: AppBorderRadius.smAll,
                        ),
                        child: Text(
                          '${result.score.round()}%',
                          style: TextStyle(
                            fontSize: AppFontSize.sm,
                            fontWeight: FontWeight.w700,
                            color: result.score >= 50
                                ? const Color(0xFF166534)
                                : const Color(0xFF92400E),
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: AppSpacing.sm),

                  // Badges row
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: AppSpacing.xs,
                    children: [
                      _Badge(
                        label: result.care.watering.isNotEmpty
                            ? result.care.watering
                            : 'Water',
                        color: const Color(0xFFDBEAFE),
                        textColor: const Color(0xFF1E40AF),
                      ),
                      _Badge(
                        label: result.care.light.isNotEmpty
                            ? result.care.light
                            : 'Light',
                        color: const Color(0xFFF3F4F6),
                        textColor: const Color(0xFF374151),
                      ),
                      if (result.toxicity?.poisonousToPets == true)
                        _Badge(
                          label: 'Toxic',
                          color: const Color(0xFFFEE2E2),
                          textColor: const Color(0xFF991B1B),
                        ),
                      _Badge(
                        label: result.care.preset,
                        color: const Color(0xFFDCFCE7),
                        textColor: const Color(0xFF166534),
                      ),
                    ],
                  ),

                  // Expanded details
                  if (isExpanded) ...[
                    const SizedBox(height: AppSpacing.md),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.md),

                    if (result.care.temperature.isNotEmpty)
                      _DetailRow(
                          icon: Icons.thermostat_outlined,
                          label: 'Temperature',
                          value: result.care.temperature),
                    if (result.care.humidity.isNotEmpty)
                      _DetailRow(
                          icon: Icons.water_drop_outlined,
                          label: 'Humidity',
                          value: result.care.humidity),
                    if (result.care.tips.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        result.care.tips,
                        style: TextStyle(
                          fontSize: AppFontSize.sm,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],

                    // Enrichment data
                    if (result.enrichment != null) ...[
                      if (result.enrichment!['care_level'] != null)
                        _DetailRow(
                            icon: Icons.speed_outlined,
                            label: 'Difficulty',
                            value: result.enrichment!['care_level'] as String),
                      if (result.enrichment!['growth_rate'] != null)
                        _DetailRow(
                            icon: Icons.trending_up,
                            label: 'Growth',
                            value: result.enrichment!['growth_rate'] as String),
                    ],

                    const SizedBox(height: AppSpacing.lg),

                    // Save button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: isSaving ? null : onSave,
                        icon: isSaving
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.add),
                        label: Text(isSaving ? 'Saving...' : 'Save to My Plants'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({
    required this.label,
    required this.color,
    required this.textColor,
  });
  final String label;
  final Color color;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 2),
      decoration: BoxDecoration(
        color: color,
        borderRadius: AppBorderRadius.smAll,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: AppFontSize.xs,
          fontWeight: FontWeight.w600,
          color: textColor,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: AppSpacing.sm),
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: AppFontSize.sm,
              fontWeight: FontWeight.w600,
              color: AppColors.text,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: AppFontSize.sm,
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
