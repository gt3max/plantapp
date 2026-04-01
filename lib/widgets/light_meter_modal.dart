/// Light Meter Modal — camera-based light measurement.
/// Ported 1:1 from src/components/LightMeterModal.tsx
import 'dart:math';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/services/light_meter_service.dart';

class LightMeterModal extends StatefulWidget {
  final String plantName;
  final int ppfdMin;
  final int ppfdMax;
  final int dliMin;
  final int dliMax;

  const LightMeterModal({
    super.key,
    required this.plantName,
    required this.ppfdMin,
    required this.ppfdMax,
    required this.dliMin,
    required this.dliMax,
  });

  @override
  State<LightMeterModal> createState() => _LightMeterModalState();
}

class _LightMeterModalState extends State<LightMeterModal> {
  CameraController? _cameraController;
  bool _cameraReady = false;
  bool _measuring = false;
  LightSource _lightSource = LightSource.mixed;
  LightAssessment? _assessment;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() => _errorMessage = 'No camera available');
        return;
      }
      final back = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      _cameraController = CameraController(back, ResolutionPreset.low, enableAudio: false);
      await _cameraController!.initialize();
      if (mounted) setState(() => _cameraReady = true);
    } catch (e) {
      if (mounted) setState(() => _errorMessage = 'Camera error: $e');
    }
  }

  Future<void> _measure() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    setState(() => _measuring = true);

    try {
      // Take 3 photos, use median Lux for stability (same as RN)
      final luxReadings = <double>[];

      for (var i = 0; i < 3; i++) {
        final file = await _cameraController!.takePicture();

        // Try EXIF-based calculation
        // camera package doesn't expose EXIF directly, so use brightness fallback
        // TODO: Add exif package for more accurate readings
        final bytes = await file.readAsBytes();
        final avgBrightness = _estimateBrightness(bytes);
        final lux = brightnessToLux(avgBrightness);
        luxReadings.add(lux);
      }

      double lux;
      if (luxReadings.length == 3) {
        luxReadings.sort();
        lux = luxReadings[1]; // median
      } else {
        lux = luxReadings.reduce((a, b) => a + b) / luxReadings.length;
      }

      final reading = createReading(lux, _lightSource);
      final assessment = assessLight(
        reading,
        ppfdMin: widget.ppfdMin,
        ppfdMax: widget.ppfdMax,
        dliMin: widget.dliMin,
        dliMax: widget.dliMax,
      );
      if (mounted) setState(() => _assessment = assessment);
    } catch (e) {
      debugPrint('[LightMeter] Error: $e');
    }
    if (mounted) setState(() => _measuring = false);
  }

  /// Estimate average brightness from JPEG bytes (quick approximation)
  double _estimateBrightness(List<int> bytes) {
    // Sample every 100th byte from the image data area (skip JPEG header)
    final start = min(1000, bytes.length ~/ 4);
    final end = bytes.length;
    if (end <= start) return 128;

    double sum = 0;
    int count = 0;
    for (var i = start; i < end; i += 100) {
      sum += bytes[i];
      count++;
    }
    return count > 0 ? sum / count : 128;
  }

  void _reset() {
    setState(() {
      _assessment = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Light Meter'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _errorMessage != null
          ? _buildError()
          : !_cameraReady
              ? const Center(child: CircularProgressIndicator())
              : _assessment != null
                  ? _buildResult()
                  : _buildCamera(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.flashlight_on, size: 48, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.lg),
          Text(_errorMessage!, style: TextStyle(color: AppColors.textSecondary, fontSize: AppFontSize.md)),
        ],
      ),
    );
  }

  Widget _buildCamera() {
    return Stack(
      children: [
        // Camera preview
        Positioned.fill(child: CameraPreview(_cameraController!)),

        // Instruction overlay
        Positioned(
          top: AppSpacing.xxl,
          left: 0,
          right: 0,
          child: Column(
            children: [
              Text(
                'Place a white paper where plant sits',
                style: TextStyle(
                  fontSize: AppFontSize.md, fontWeight: FontWeight.w700, color: Colors.white,
                  shadows: [Shadow(blurRadius: 4, color: Colors.black54)],
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                'Point camera at the paper from above (~30 cm)',
                style: TextStyle(
                  fontSize: AppFontSize.sm, color: Colors.white70,
                  shadows: [Shadow(blurRadius: 4, color: Colors.black54)],
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),

        // Light source selector
        Positioned(
          top: 80,
          left: 0,
          right: 0,
          child: Center(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(24),
              ),
              padding: const EdgeInsets.all(4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: LightSource.values.map((src) {
                  final active = _lightSource == src;
                  final icon = src == LightSource.sunlight ? Icons.wb_sunny
                      : src == LightSource.led ? Icons.lightbulb_outline
                      : Icons.contrast;
                  final label = src == LightSource.sunlight ? 'Window'
                      : src == LightSource.led ? 'Lamp'
                      : 'Both';
                  return GestureDetector(
                    onTap: () => setState(() => _lightSource = src),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: active ? AppColors.primary : Colors.transparent,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        children: [
                          Icon(icon, size: 16, color: active ? Colors.white : AppColors.textSecondary),
                          const SizedBox(width: 4),
                          Text(label, style: TextStyle(
                            fontSize: AppFontSize.xs,
                            color: active ? Colors.white : AppColors.textSecondary,
                            fontWeight: active ? FontWeight.w600 : FontWeight.normal,
                          )),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        ),

        // Measure button
        Positioned(
          bottom: 40,
          left: 0,
          right: 0,
          child: Center(
            child: GestureDetector(
              onTap: _measuring ? null : _measure,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl, vertical: AppSpacing.lg),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(32),
                  boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 8, offset: Offset(0, 4))],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: _measuring
                      ? [Text('Measuring...', style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w700, color: Colors.white))]
                      : [
                          const Icon(Icons.flashlight_on, size: 24, color: Colors.white),
                          const SizedBox(width: AppSpacing.sm),
                          Text('Measure', style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w700, color: Colors.white)),
                        ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildResult() {
    final a = _assessment!;
    final reading = a.reading;

    final statusColor = a.status == LightStatus.good ? AppColors.success
        : (a.status == LightStatus.low || a.status == LightStatus.high) ? const Color(0xFFF59E0B)
        : AppColors.error;

    final statusIcon = a.status == LightStatus.good ? Icons.check_circle
        : (a.status == LightStatus.low || a.status == LightStatus.tooLow) ? Icons.arrow_downward
        : Icons.arrow_upward;

    final statusLabel = a.status == LightStatus.good ? 'Ideal'
        : a.status == LightStatus.low ? 'Low'
        : a.status == LightStatus.tooLow ? 'Too dark'
        : a.status == LightStatus.high ? 'Bright'
        : 'Too bright';

    final needsLeft = ppfdToPercent(a.ppfdMin);
    final needsRight = ppfdToPercent(a.ppfdMax);
    final currentPos = ppfdToPercent(reading.ppfd);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: [
          // Big PPFD reading
          Text('${reading.ppfd}', style: TextStyle(fontSize: 56, fontWeight: FontWeight.w800, color: statusColor)),
          Text('PPFD', style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
          const SizedBox(height: AppSpacing.sm),

          // Status badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(statusIcon, size: 20, color: statusColor),
                const SizedBox(width: AppSpacing.sm),
                Text(statusLabel, style: TextStyle(fontSize: AppFontSize.md, fontWeight: FontWeight.w700, color: statusColor)),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),

          // PPFD bar
          Text(
            '${widget.plantName} needs ${a.ppfdMin}–${a.ppfdMax} PPFD',
            style: TextStyle(fontSize: AppFontSize.xs, color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.xs),
          SizedBox(
            height: 20,
            child: LayoutBuilder(builder: (context, constraints) {
              final w = constraints.maxWidth;
              return Stack(
                clipBehavior: Clip.none,
                children: [
                  // Track
                  Positioned(top: 4, left: 0, right: 0, child: Container(height: 12, decoration: BoxDecoration(color: const Color(0xFFE5E7EB), borderRadius: BorderRadius.circular(6)))),
                  // Ideal range
                  Positioned(
                    top: 4, left: w * needsLeft / 100,
                    width: max(4, w * (needsRight - needsLeft) / 100),
                    child: Container(height: 12, decoration: BoxDecoration(color: const Color(0xFFDCFCE7), borderRadius: BorderRadius.circular(6))),
                  ),
                  // Current cursor
                  Positioned(
                    top: 0, left: (w * min(98, currentPos) / 100) - 2,
                    child: Container(width: 4, height: 20, decoration: BoxDecoration(color: statusColor, borderRadius: BorderRadius.circular(2))),
                  ),
                ],
              );
            }),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: ['0', '100', '500', '1000'].map((l) => Text(l, style: TextStyle(fontSize: 9, color: AppColors.textSecondary))).toList(),
          ),
          const SizedBox(height: AppSpacing.lg),

          // Details row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _DetailItem(value: '${reading.lux}', label: 'Lux'),
              _DetailItem(value: '${reading.dli}', label: 'DLI (12h)'),
              _DetailItem(
                value: reading.source == LightSource.sunlight ? 'Window'
                    : reading.source == LightSource.led ? 'Lamp'
                    : 'Both',
                label: 'Source',
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),

          // Assessment message
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.06),
              borderRadius: AppBorderRadius.mdAll,
            ),
            child: Text(
              a.message,
              style: TextStyle(
                fontSize: AppFontSize.sm,
                height: 1.5,
                color: statusColor == AppColors.success ? const Color(0xFF166534)
                    : statusColor == const Color(0xFFF59E0B) ? const Color(0xFF92400E)
                    : const Color(0xFF991B1B),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          // Disclaimer
          Text(
            'Estimated from camera brightness. Accuracy ~30%. For precise measurements use a PAR meter.',
            style: TextStyle(fontSize: 10, color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),

          // Measure again
          TextButton.icon(
            onPressed: _reset,
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Measure again'),
          ),
        ],
      ),
    );
  }
}

class _DetailItem extends StatelessWidget {
  final String value;
  final String label;
  const _DetailItem({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: AppFontSize.lg, fontWeight: FontWeight.w700, color: AppColors.text)),
        Text(label, style: TextStyle(fontSize: AppFontSize.xs, color: AppColors.textSecondary)),
      ],
    );
  }
}
