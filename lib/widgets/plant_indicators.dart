// Visual indicator components for plant detail cards
// 1:1 port from React Native app/plant/[id].tsx

import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

// ─── TempRangeBar ────────────────────────────────────────────
// Fixed scale 0-30°C (like Planta). Shows optimal range as colored bar.

class TempRangeBar extends StatelessWidget {
  const TempRangeBar({
    super.key,
    required this.optLow,
    required this.optHigh,
    this.color,
    this.label,
    required this.formatT,
  });

  final int optLow;
  final int optHigh;
  final Color? color;
  final String? label;
  final String Function(int) formatT;

  @override
  Widget build(BuildContext context) {
    const scaleMin = 0;
    const scaleMax = 30;
    const range = scaleMax - scaleMin;
    final leftPct = ((optLow - scaleMin) / range).clamp(0.0, 1.0);
    final widthPct = ((optHigh - optLow) / range).clamp(0.0, 1.0 - leftPct);
    final barColor = color ?? AppColors.success;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Column(
        children: [
          SizedBox(
            height: 28,
            child: Stack(
              children: [
                // Track
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppColors.border,
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                ),
                // Optimal range
                Positioned(
                  left: leftPct * (MediaQuery.of(context).size.width - 2 * AppSpacing.lg - 2 * AppSpacing.lg),
                  width: widthPct * (MediaQuery.of(context).size.width - 2 * AppSpacing.lg - 2 * AppSpacing.lg),
                  top: 0,
                  bottom: 0,
                  child: Container(
                    decoration: BoxDecoration(
                      color: barColor,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      label ?? '${formatT(optLow)} \u2013 ${formatT(optHigh)}',
                      style: const TextStyle(
                        fontSize: AppFontSize.xs,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(formatT(scaleMin), style: _labelStyle),
              Text(formatT(15), style: _labelStyle),
              Text(formatT(scaleMax), style: _labelStyle),
            ],
          ),
        ],
      ),
    );
  }
}

// ─── HumidityBar ─────────────────────────────────────────────
// Parses humidity text → %, shows as colored fill bar.

class HumidityBar extends StatelessWidget {
  const HumidityBar({super.key, required this.level});
  final String level;

  @override
  Widget build(BuildContext context) {
    final lower = level.toLowerCase();
    double pct = 50;
    String label = 'Medium';
    Color barColor = AppColors.info;

    if (lower.contains('high') || lower.contains('70') || lower.contains('80') || lower.contains('tropical')) {
      pct = 80; label = 'High'; barColor = const Color(0xFF0EA5E9);
    } else if (lower.contains('low') || lower.contains('dry') || lower.contains('20') || lower.contains('30')) {
      pct = 25; label = 'Low'; barColor = const Color(0xFFF59E0B);
    } else if (lower.contains('moderate') || lower.contains('average') || lower.contains('40') || lower.contains('50') || lower.contains('60')) {
      pct = 55; label = 'Medium'; barColor = const Color(0xFF22C55E);
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Column(
        children: [
          SizedBox(
            height: 14,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(7),
              child: Stack(
                children: [
                  Container(color: AppColors.border),
                  FractionallySizedBox(
                    widthFactor: pct / 100,
                    child: Container(
                      decoration: BoxDecoration(
                        color: barColor,
                        borderRadius: BorderRadius.circular(7),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Dry', style: _labelStyle),
              Text('$label ~${pct.toInt()}%', style: TextStyle(fontSize: AppFontSize.xs, fontWeight: FontWeight.w600, color: barColor)),
              Text('Humid', style: _labelStyle),
            ],
          ),
        ],
      ),
    );
  }
}

// ─── LightLevelIndicator ─────────────────────────────────────
// 3 circles (Low/Medium/High), active one highlighted.

class LightLevelIndicator extends StatelessWidget {
  const LightLevelIndicator({super.key, required this.lightText});
  final String lightText;

  @override
  Widget build(BuildContext context) {
    final lower = lightText.toLowerCase();
    int activeLevel = 1; // 0=shade, 1=partial, 2=full sun
    if (lower.contains('full') || lower.contains('direct') || lower.contains('8+')) {
      activeLevel = 2;
    } else if (lower.contains('indirect') || lower.contains('part') || lower.contains('medium')) {
      activeLevel = 1;
    } else if (lower.contains('low') || lower.contains('shade') || lower.contains('dark')) {
      activeLevel = 0;
    }

    const levels = [
      (icon: Icons.cloud_outlined, label: 'Low', color: Color(0xFF94A3B8)),
      (icon: Icons.wb_cloudy_outlined, label: 'Medium', color: Color(0xFFF59E0B)),
      (icon: Icons.wb_sunny, label: 'High', color: Color(0xFFEF8C17)),
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: List.generate(3, (i) {
          final isActive = i == activeLevel;
          final lvl = levels[i];
          return Column(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isActive ? lvl.color.withValues(alpha: 0.12) : const Color(0xFFF3F4F6),
                  border: Border.all(
                    color: isActive ? lvl.color : const Color(0xFFE5E7EB),
                    width: isActive ? 2 : 1,
                  ),
                ),
                child: Icon(lvl.icon, size: 20, color: isActive ? lvl.color : const Color(0xFFD1D5DB)),
              ),
              const SizedBox(height: 4),
              Text(
                lvl.label,
                style: TextStyle(
                  fontSize: AppFontSize.xs,
                  fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
                  color: isActive ? lvl.color : AppColors.textSecondary,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}

// ─── DifficultyStars ─────────────────────────────────────────
// 3 stars, filled up to count.

class DifficultyStars extends StatelessWidget {
  const DifficultyStars({super.key, required this.count, required this.color, this.size = 22});
  final int count;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) => Icon(
        Icons.star,
        size: size,
        color: i < count ? color : color.withValues(alpha: 0.2),
      )),
    );
  }
}

// ─── InfoBox ─────────────────────────────────────────────────
// 3 variants: info (blue), warning (yellow), success (green)

class InfoBox extends StatelessWidget {
  const InfoBox({super.key, required this.text, this.variant = 'info'});
  final String text;
  final String variant;

  @override
  Widget build(BuildContext context) {
    Color bgColor;
    Color iconColor;
    IconData icon;

    switch (variant) {
      case 'warning':
        bgColor = const Color(0xFFFFF8E1);
        iconColor = const Color(0xFFF59E0B);
        icon = Icons.warning_amber_outlined;
      case 'success':
        bgColor = const Color(0xFFDCFCE7);
        iconColor = AppColors.success;
        icon = Icons.check_circle_outline;
      default:
        bgColor = const Color(0xFFEBF5FF);
        iconColor = AppColors.info;
        icon = Icons.info_outline;
    }

    return Container(
      margin: const EdgeInsets.only(top: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(AppBorderRadius.md),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: iconColor),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              text,
              style: TextStyle(fontSize: AppFontSize.sm, color: AppColors.text, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Shared ──────────────────────────────────────────────────

final _labelStyle = TextStyle(fontSize: AppFontSize.xs, color: AppColors.textSecondary);
