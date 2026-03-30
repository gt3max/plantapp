import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/models/plant.dart';
import 'package:plantapp/services/plant_service.dart';

class PlantsScreen extends StatefulWidget {
  const PlantsScreen({super.key});

  @override
  State<PlantsScreen> createState() => _PlantsScreenState();
}

class _PlantsScreenState extends State<PlantsScreen> {
  final _plantService = PlantService.instance;

  List<PlantEntry> _plants = [];
  bool _isLoading = true;
  String _activeTab = 'plants'; // 'plants' | 'journal'

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

  @override
  Widget build(BuildContext context) {
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

  Widget _buildPlantsTab() {
    return RefreshIndicator(
      onRefresh: _loadPlants,
      color: AppColors.primary,
      child: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _plants.isEmpty
              ? _buildEmptyState()
              : ListView(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
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
                            onTap: () {
                              // TODO: navigate to plant detail
                            },
                          ),
                        )),

                    const SizedBox(height: AppSpacing.xl),

                    // Identify buttons
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () {
                          // TODO: identify flow
                        },
                        icon: const Icon(Icons.camera_alt_outlined),
                        label: const Text('Identify plant'),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () {
                          // TODO: gallery identify
                        },
                        icon: const Icon(Icons.image_outlined),
                        label: const Text('Choose from gallery'),
                      ),
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
          child: ElevatedButton.icon(
            onPressed: () {
              // TODO: identify flow
            },
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Identify plant'),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: OutlinedButton.icon(
            onPressed: () {
              // TODO: gallery identify
            },
            icon: const Icon(Icons.image_outlined),
            label: const Text('Choose from gallery'),
          ),
        ),
      ],
    );
  }
}

// ─── Sub-widgets ─────────────────────────────────────────────

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
            Icon(Icons.chevron_right, color: AppColors.textSecondary, size: 20),
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
