/// Light Meter — Lux estimation and PPFD conversion.
/// Ported 1:1 from src/lib/light-meter.ts
///
/// Conversion factors (confirmed by LI-COR + Mulyarchik spectroradiometer):
/// - Sunlight:  PPFD = Lux × 0.018  (1 klux = 18 µmol/m²/s)
/// - White LED: PPFD = Lux × 0.012  (1 klux = 12 µmol/m²/s)
/// - Grow LED (R+B): unreliable via Lux — needs PAR-meter
///
/// DLI = PPFD × photoperiod_hours × 3600 / 1_000_000

import 'dart:math';

enum LightSource { sunlight, led, mixed }

class LightReading {
  final int lux;
  final int ppfd;
  final double dli;
  final LightSource source;

  const LightReading({
    required this.lux,
    required this.ppfd,
    required this.dli,
    required this.source,
  });
}

enum LightStatus { tooLow, low, good, high, tooHigh }

class LightAssessment {
  final LightReading reading;
  final LightStatus status;
  final String message;
  final int ppfdMin;
  final int ppfdMax;
  final int dliMin;
  final int dliMax;

  const LightAssessment({
    required this.reading,
    required this.status,
    required this.message,
    required this.ppfdMin,
    required this.ppfdMax,
    required this.dliMin,
    required this.dliMax,
  });
}

// ─── Conversion ──────────────────────────────────────────────────────

const _luxToPpfd = <LightSource, double>{
  LightSource.sunlight: 0.0185,
  LightSource.led: 0.015,
  LightSource.mixed: 0.017,
};

const _defaultPhotoperiodHours = 12;

int luxToPPFD(double lux, [LightSource source = LightSource.mixed]) {
  return (lux * _luxToPpfd[source]!).round();
}

double ppfdToDLI(int ppfd, [int hours = _defaultPhotoperiodHours]) {
  return ((ppfd * hours * 3600) / 1000000 * 10).roundToDouble() / 10;
}

LightReading createReading(double lux, [LightSource source = LightSource.mixed]) {
  final ppfd = luxToPPFD(lux, source);
  final dli = ppfdToDLI(ppfd);
  return LightReading(lux: lux.round(), ppfd: ppfd, dli: dli, source: source);
}

// ─── Assessment ──────────────────────────────────────────────────────

LightAssessment assessLight(
  LightReading reading, {
  required int ppfdMin,
  required int ppfdMax,
  required int dliMin,
  required int dliMax,
}) {
  final ppfd = reading.ppfd;

  if (ppfd < ppfdMin * 0.5) {
    return LightAssessment(
      reading: reading,
      status: LightStatus.tooLow,
      message: 'Very low light ($ppfd PPFD). This plant needs at least $ppfdMin PPFD. Move closer to a window or add a grow light.',
      ppfdMin: ppfdMin, ppfdMax: ppfdMax, dliMin: dliMin, dliMax: dliMax,
    );
  }
  if (ppfd < ppfdMin) {
    return LightAssessment(
      reading: reading,
      status: LightStatus.low,
      message: 'Light is below ideal ($ppfd PPFD, needs $ppfdMin+). Consider a brighter spot or supplemental lighting.',
      ppfdMin: ppfdMin, ppfdMax: ppfdMax, dliMin: dliMin, dliMax: dliMax,
    );
  }
  if (ppfd > ppfdMax * 1.5) {
    return LightAssessment(
      reading: reading,
      status: LightStatus.tooHigh,
      message: 'Very intense light ($ppfd PPFD). Risk of leaf burn. Move away from direct sun or add a sheer curtain.',
      ppfdMin: ppfdMin, ppfdMax: ppfdMax, dliMin: dliMin, dliMax: dliMax,
    );
  }
  if (ppfd > ppfdMax) {
    return LightAssessment(
      reading: reading,
      status: LightStatus.high,
      message: 'Light is above ideal ($ppfd PPFD, max $ppfdMax). Monitor for signs of stress.',
      ppfdMin: ppfdMin, ppfdMax: ppfdMax, dliMin: dliMin, dliMax: dliMax,
    );
  }
  return LightAssessment(
    reading: reading,
    status: LightStatus.good,
    message: 'Light is in the ideal range ($ppfd PPFD). This spot works well for your plant.',
    ppfdMin: ppfdMin, ppfdMax: ppfdMax, dliMin: dliMin, dliMax: dliMax,
  );
}

// ─── Brightness to Lux estimation ────────────────────────────────────

/// Estimate Lux from average image brightness (0-255 RGB).
/// ESTIMATION — not a PAR meter. Accuracy ±30%.
double brightnessToLux(double avgBrightness) {
  final b = avgBrightness.clamp(0.0, 255.0);
  if (b < 5) return 0;
  final normalized = b / 255;
  return (pow(normalized, 2.2) * 100000).roundToDouble();
}

/// Returns 0-100 position on a logarithmic PPFD scale (0-1000)
double ppfdToPercent(int ppfd) {
  if (ppfd <= 0) return 0;
  const maxPPFD = 1000;
  return (log(ppfd) / ln10 / (log(maxPPFD) / ln10) * 100).clamp(0.0, 100.0);
}

/// Calculate Lux from EXIF data (EV-based, ISO 2720 standard)
double? luxFromExif({
  required double? exposureTime,
  required double? iso,
  double? fNumber,
}) {
  if (exposureTime == null || iso == null || exposureTime <= 0 || iso <= 0) return null;
  final f = fNumber ?? 1.8;
  final ev = (log(f * f / exposureTime) / ln2) - (log(iso / 100) / ln2);
  final lux = pow(2, ev) * 2.5;
  return lux.toDouble().clamp(0, 150000);
}
