import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/constants/popular_plants.dart';
import 'package:plantapp/services/library_service.dart';

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  final _libraryService = LibraryService.instance;
  final _searchController = TextEditingController();
  Timer? _debounce;

  List<LibraryPlant> _results = [];
  bool _isSearching = false;
  bool _hasSearched = false;

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    _debounce?.cancel();
    if (query.length < 2) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _isSearching = false;
      });
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 400), () {
      _search(query);
    });
  }

  Future<void> _search(String query) async {
    setState(() => _isSearching = true);
    try {
      final results = await _libraryService.search(query);
      if (mounted) {
        setState(() {
          _results = results;
          _hasSearched = true;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Search failed')),
        );
      }
    }
    if (mounted) setState(() => _isSearching = false);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Search bar
        Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: TextField(
            controller: _searchController,
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: 'Search plants...',
              hintStyle: TextStyle(
                color: AppColors.textSecondary,
                fontSize: AppFontSize.md,
              ),
              prefixIcon:
                  Icon(Icons.search, color: AppColors.textSecondary),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: Icon(Icons.clear,
                          color: AppColors.textSecondary, size: 20),
                      onPressed: () {
                        _searchController.clear();
                        _onSearchChanged('');
                      },
                    )
                  : null,
              filled: true,
              fillColor: AppColors.surface,
              border: OutlineInputBorder(
                borderRadius: AppBorderRadius.lgAll,
                borderSide: BorderSide(color: AppColors.border),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: AppBorderRadius.lgAll,
                borderSide: BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: AppBorderRadius.lgAll,
                borderSide: BorderSide(color: AppColors.primary),
              ),
              contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg, vertical: AppSpacing.md),
            ),
          ),
        ),

        // Content
        Expanded(
          child: _isSearching
              ? const Center(child: CircularProgressIndicator())
              : _hasSearched
                  ? _buildResults()
                  : _buildWelcome(),
        ),
      ],
    );
  }

  Widget _buildWelcome() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.md),
          child: Text(
            'Popular Plants',
            style: TextStyle(
              fontSize: AppFontSize.lg,
              fontWeight: FontWeight.w700,
              color: AppColors.text,
            ),
          ),
        ),
        ...popularPlants.map((p) => _PopularCard(
              plant: p,
              onTap: () => context.push('/plant/${p.id}'),
            )),
      ],
    );
  }

  Widget _buildResults() {
    if (_results.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'No plants found',
              style: TextStyle(
                fontSize: AppFontSize.lg,
                fontWeight: FontWeight.w600,
                color: AppColors.text,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Try a different search term',
              style: TextStyle(
                fontSize: AppFontSize.sm,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      itemCount: _results.length,
      itemBuilder: (context, index) {
        final plant = _results[index];
        return _LibraryCard(
          plant: plant,
          onTap: () => context.push('/plant/${plant.detailId}'),
        );
      },
    );
  }
}

// ─── Library card ────────────────────────────────────────────

class _LibraryCard extends StatelessWidget {
  const _LibraryCard({required this.plant, required this.onTap});
  final LibraryPlant plant;
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
            // Image
            ClipRRect(
              borderRadius: AppBorderRadius.mdAll,
              child: plant.imageUrl != null && plant.imageUrl!.isNotEmpty
                  ? Image.network(
                      plant.imageUrl!,
                      width: 56,
                      height: 56,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _placeholder(),
                    )
                  : _placeholder(),
            ),
            const SizedBox(width: AppSpacing.md),

            // Info
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
                  if (plant.scientific != plant.commonName &&
                      plant.commonName != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      plant.scientific,
                      style: TextStyle(
                        fontSize: AppFontSize.xs,
                        fontStyle: FontStyle.italic,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  if (plant.family != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      plant.family!,
                      style: TextStyle(
                        fontSize: AppFontSize.xs,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Badges
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (plant.careLevel != null)
                  _SmallBadge(
                    label: plant.careLevel!,
                    color: _careLevelColor(plant.careLevel!),
                  ),
                if (plant.indoor == true) ...[
                  const SizedBox(height: 4),
                  _SmallBadge(
                    label: 'Indoor',
                    color: const Color(0xFFDBEAFE),
                  ),
                ],
              ],
            ),

            const SizedBox(width: AppSpacing.sm),
            Icon(Icons.chevron_right,
                color: AppColors.textSecondary, size: 20),
          ],
        ),
      ),
    );
  }

  Color _careLevelColor(String level) {
    switch (level.toLowerCase()) {
      case 'easy':
        return const Color(0xFFDCFCE7);
      case 'medium':
      case 'moderate':
        return const Color(0xFFFEF3C7);
      case 'hard':
      case 'difficult':
        return const Color(0xFFFEE2E2);
      default:
        return const Color(0xFFF3F4F6);
    }
  }

  Widget _placeholder() => Container(
        width: 56,
        height: 56,
        color: AppColors.background,
        child: Icon(Icons.eco, color: AppColors.accent, size: 28),
      );
}

// ─── Card for popular plants (from hardcoded data) ──────────

class _PopularCard extends StatelessWidget {
  const _PopularCard({required this.plant, required this.onTap});
  final PopularPlant plant;
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
            ClipRRect(
              borderRadius: AppBorderRadius.mdAll,
              child: Image.network(
                plant.imageUrl,
                width: 56,
                height: 56,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  width: 56, height: 56,
                  color: AppColors.background,
                  child: Icon(Icons.eco, color: AppColors.accent, size: 28),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plant.commonName,
                    style: TextStyle(
                      fontSize: AppFontSize.md,
                      fontWeight: FontWeight.w600,
                      color: AppColors.text,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    plant.scientific,
                    style: TextStyle(
                      fontSize: AppFontSize.xs,
                      fontStyle: FontStyle.italic,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    plant.family,
                    style: TextStyle(
                      fontSize: AppFontSize.xs,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _SmallBadge(
                  label: plant.difficulty,
                  color: plant.difficulty == 'Easy'
                      ? const Color(0xFFDCFCE7)
                      : plant.difficulty == 'Medium'
                          ? const Color(0xFFFEF3C7)
                          : const Color(0xFFFEE2E2),
                ),
                const SizedBox(height: 4),
                _SmallBadge(
                  label: plant.wateringDemand.isNotEmpty ? plant.wateringDemand : 'Medium',
                  color: const Color(0xFFDBEAFE),
                ),
              ],
            ),
            const SizedBox(width: AppSpacing.sm),
            Icon(Icons.chevron_right, color: AppColors.textSecondary, size: 20),
          ],
        ),
      ),
    );
  }
}

class _SmallBadge extends StatelessWidget {
  const _SmallBadge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: 2),
      decoration: BoxDecoration(
        color: color,
        borderRadius: AppBorderRadius.smAll,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: AppFontSize.xs,
          fontWeight: FontWeight.w600,
          color: AppColors.text,
        ),
      ),
    );
  }
}
