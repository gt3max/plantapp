import React, { useCallback, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  Image,
  Platform,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, FontSize, BorderRadius } from '../constants/colors';
import {
  createReading,
  assessLight,
  brightnessToLux,
  ppfdToPercent,
  type LightSource,
  type LightAssessment,
} from '../lib/light-meter';

// ─── Props ───────────────────────────────────────────────────────────

interface LightMeterModalProps {
  visible: boolean;
  onClose: () => void;
  plantName: string;
  ppfdMin: number;
  ppfdMax: number;
  dliMin: number;
  dliMax: number;
}

// ─── Component ───────────────────────────────────────────────────────

export function LightMeterModal({
  visible,
  onClose,
  plantName,
  ppfdMin,
  ppfdMax,
  dliMin,
  dliMax,
}: LightMeterModalProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [lightSource, setLightSource] = useState<LightSource>('mixed');
  const [assessment, setAssessment] = useState<LightAssessment | null>(null);
  const [capturedUri, setCapturedUri] = useState<string | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const handleMeasure = useCallback(async () => {
    if (!cameraRef.current) return;
    setMeasuring(true);
    try {
      // Take 3 photos rapidly and average the Lux readings for stability
      const luxReadings: number[] = [];
      let lastUri: string | null = null;

      for (let i = 0; i < 3; i++) {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.3,
          exif: true,
        });
        if (!photo) continue;
        if (i === 2) lastUri = photo.uri; // keep last photo for display

        const exif = photo.exif;
        if (exif?.ExposureTime && exif?.ISOSpeedRatings) {
          const exposureTime = Number(exif.ExposureTime);
          const iso = Array.isArray(exif.ISOSpeedRatings)
            ? Number(exif.ISOSpeedRatings[0])
            : Number(exif.ISOSpeedRatings);
          const fNumber = Number(exif.FNumber ?? exif.ApertureValue ?? 1.8);

          // EV = log2(F² / ExposureTime) - log2(ISO / 100)
          // Lux = 2^EV × C where C=2.5 (ISO 2720 standard)
          // Equivalent to Lux = (F² × 250) / (t × ISO)
          // Method: point camera at white paper on plant surface (acts as diffuser)
          const ev = Math.log2((fNumber * fNumber) / exposureTime) - Math.log2(iso / 100);
          const lux = Math.pow(2, ev) * 2.5;
          luxReadings.push(Math.max(0, Math.min(150000, lux)));
        }
      }

      setCapturedUri(lastUri);

      let lux: number;
      if (luxReadings.length > 0) {
        // Average of readings, discard outliers if 3 samples
        if (luxReadings.length === 3) {
          luxReadings.sort((a, b) => a - b);
          lux = luxReadings[1]; // median of 3
        } else {
          lux = luxReadings.reduce((a, b) => a + b, 0) / luxReadings.length;
        }
        lux = Math.round(lux);
      } else {
        lux = brightnessToLux(128); // fallback
      }

      const reading = createReading(lux, lightSource);
      const result = assessLight(reading, ppfdMin, ppfdMax, dliMin, dliMax);
      setAssessment(result);
    } catch (err) {
      console.log('[LightMeter] Error:', err);
    }
    setMeasuring(false);
  }, [lightSource, ppfdMin, ppfdMax, dliMin, dliMax]);

  const handleReset = useCallback(() => {
    setAssessment(null);
    setCapturedUri(null);
  }, []);

  const handleClose = useCallback(() => {
    handleReset();
    onClose();
  }, [onClose, handleReset]);

  if (Platform.OS === 'web') {
    return (
      <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.container}>
          <Header onClose={handleClose} />
          <View style={styles.centered}>
            <Ionicons name="flashlight-outline" size={48} color={Colors.textSecondary} />
            <Text style={styles.permText}>Light meter is not available on web</Text>
          </View>
        </View>
      </Modal>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
      <View style={styles.container}>
        <Header onClose={handleClose} />

        {!permission?.granted ? (
          <View style={styles.centered}>
            <Ionicons name="camera-outline" size={48} color={Colors.textSecondary} />
            <Text style={styles.permText}>Camera access needed to measure light</Text>
            <TouchableOpacity onPress={requestPermission} style={styles.permBtn}>
              <Text style={styles.permBtnText}>Allow camera</Text>
            </TouchableOpacity>
          </View>
        ) : assessment ? (
          <ResultView
            assessment={assessment}
            capturedUri={capturedUri}
            plantName={plantName}
            onReset={handleReset}
          />
        ) : (
          <View style={styles.cameraContainer}>
            <CameraView
              ref={cameraRef}
              style={styles.camera}
              facing="back"
            />
            <View style={styles.overlay}>
              <Text style={styles.instruction}>
                Place a white paper where plant sits
              </Text>
              <Text style={styles.subInstruction}>
                Point camera at the paper from above (~30 cm)
              </Text>
            </View>

            <View style={styles.sourceSelector}>
              {(['sunlight', 'led', 'mixed'] as LightSource[]).map((src) => (
                <TouchableOpacity
                  key={src}
                  onPress={() => setLightSource(src)}
                  style={[styles.sourceBtn, lightSource === src && styles.sourceBtnActive]}
                >
                  <Ionicons
                    name={src === 'sunlight' ? 'sunny' : src === 'led' ? 'bulb' : 'contrast'}
                    size={16}
                    color={lightSource === src ? '#fff' : Colors.textSecondary}
                  />
                  <Text style={[styles.sourceBtnText, lightSource === src && styles.sourceBtnTextActive]}>
                    {src === 'sunlight' ? 'Window' : src === 'led' ? 'Lamp' : 'Both'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity
              onPress={handleMeasure}
              style={styles.measureBtn}
              disabled={measuring}
            >
              <View style={styles.measureBtnInner}>
                {measuring ? (
                  <Text style={styles.measureBtnText}>Measuring...</Text>
                ) : (
                  <>
                    <Ionicons name="flashlight" size={24} color="#fff" />
                    <Text style={styles.measureBtnText}>Measure</Text>
                  </>
                )}
              </View>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────

function Header({ onClose }: { onClose: () => void }) {
  return (
    <View style={styles.header}>
      <Text style={styles.headerTitle}>Light Meter</Text>
      <TouchableOpacity onPress={onClose} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
        <Ionicons name="close" size={24} color={Colors.text} />
      </TouchableOpacity>
    </View>
  );
}

function ResultView({
  assessment,
  capturedUri,
  plantName,
  onReset,
}: {
  assessment: LightAssessment;
  capturedUri: string | null;
  plantName: string;
  onReset: () => void;
}) {
  const { reading, status, message, plantNeeds } = assessment;

  const statusColor =
    status === 'good' ? Colors.success
    : status === 'low' || status === 'high' ? '#F59E0B'
    : Colors.error;

  const statusIcon: keyof typeof Ionicons.glyphMap =
    status === 'good' ? 'checkmark-circle'
    : status === 'low' || status === 'too_low' ? 'arrow-down-circle'
    : 'arrow-up-circle';

  const statusLabel =
    status === 'good' ? 'Ideal'
    : status === 'low' ? 'Low'
    : status === 'too_low' ? 'Too dark'
    : status === 'high' ? 'Bright'
    : 'Too bright';

  // Bar positions
  const needsLeft = ppfdToPercent(plantNeeds.ppfdMin);
  const needsRight = ppfdToPercent(plantNeeds.ppfdMax);
  const currentPos = ppfdToPercent(reading.ppfd);

  return (
    <View style={styles.resultContainer}>
      {capturedUri && (
        <Image source={{ uri: capturedUri }} style={styles.capturedImage} />
      )}

      {/* Big PPFD reading */}
      <View style={styles.bigReading}>
        <Text style={[styles.bigNumber, { color: statusColor }]}>{reading.ppfd}</Text>
        <Text style={styles.bigUnit}>PPFD</Text>
      </View>

      {/* Status badge */}
      <View style={[styles.statusBadge, { backgroundColor: `${statusColor}15` }]}>
        <Ionicons name={statusIcon} size={20} color={statusColor} />
        <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
      </View>

      {/* PPFD bar with range and current position */}
      <View style={styles.ppfdBarContainer}>
        <Text style={styles.ppfdBarLabel}>{plantName} needs {plantNeeds.ppfdMin}–{plantNeeds.ppfdMax} PPFD</Text>
        <View style={styles.ppfdBarTrack}>
          <View style={[styles.ppfdBarRange, { left: `${needsLeft}%`, width: `${Math.max(1, needsRight - needsLeft)}%` }]} />
          <View style={[styles.ppfdBarCursor, { left: `${Math.min(98, currentPos)}%`, backgroundColor: statusColor }]} />
        </View>
        <View style={styles.ppfdBarLabels}>
          <Text style={styles.ppfdBarLabelText}>0</Text>
          <Text style={styles.ppfdBarLabelText}>100</Text>
          <Text style={styles.ppfdBarLabelText}>500</Text>
          <Text style={styles.ppfdBarLabelText}>1000</Text>
        </View>
      </View>

      {/* Details */}
      <View style={styles.detailsRow}>
        <View style={styles.detailItem}>
          <Text style={styles.detailValue}>{reading.lux}</Text>
          <Text style={styles.detailLabel}>Lux</Text>
        </View>
        <View style={styles.detailItem}>
          <Text style={styles.detailValue}>{reading.dli}</Text>
          <Text style={styles.detailLabel}>DLI (12h)</Text>
        </View>
        <View style={styles.detailItem}>
          <Text style={styles.detailValue}>{reading.source === 'sunlight' ? 'Window' : reading.source === 'led' ? 'Lamp' : 'Both'}</Text>
          <Text style={styles.detailLabel}>Source</Text>
        </View>
      </View>

      {/* Assessment message */}
      <View style={[styles.messageBox, { backgroundColor: `${statusColor}10` }]}>
        <Text style={[styles.messageText, { color: statusColor === Colors.success ? '#166534' : statusColor === '#F59E0B' ? '#92400E' : '#991B1B' }]}>
          {message}
        </Text>
      </View>

      {/* Disclaimer */}
      <Text style={styles.disclaimer}>
        Estimated from camera brightness. Accuracy ~30%. For precise measurements use a PAR meter.
      </Text>

      <TouchableOpacity onPress={onReset} style={styles.retryBtn}>
        <Ionicons name="refresh" size={18} color={Colors.primary} />
        <Text style={styles.retryBtnText}>Measure again</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.xl, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },

  // Permission
  permText: { fontSize: FontSize.md, color: Colors.textSecondary, marginTop: Spacing.lg, textAlign: 'center' },
  permBtn: { marginTop: Spacing.lg, backgroundColor: Colors.primary, borderRadius: BorderRadius.md, paddingHorizontal: Spacing.xxl, paddingVertical: Spacing.md },
  permBtnText: { fontSize: FontSize.md, fontWeight: '600', color: '#fff' },

  // Camera
  cameraContainer: { flex: 1 },
  camera: { flex: 1 },
  overlay: { position: 'absolute', top: Spacing.xxl, left: 0, right: 0, alignItems: 'center' },
  instruction: { fontSize: FontSize.md, fontWeight: '700', color: '#fff', textShadowColor: 'rgba(0,0,0,0.5)', textShadowRadius: 4, textShadowOffset: { width: 0, height: 1 } },
  subInstruction: { fontSize: FontSize.sm, color: 'rgba(255,255,255,0.8)', marginTop: 4, textShadowColor: 'rgba(0,0,0,0.5)', textShadowRadius: 4, textShadowOffset: { width: 0, height: 1 } },

  // Light source selector
  sourceSelector: { position: 'absolute', top: 80, alignSelf: 'center', flexDirection: 'row', gap: Spacing.sm, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: BorderRadius.full, padding: 4 },
  sourceBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, borderRadius: BorderRadius.full },
  sourceBtnActive: { backgroundColor: Colors.primary },
  sourceBtnText: { fontSize: FontSize.xs, color: Colors.textSecondary },
  sourceBtnTextActive: { color: '#fff', fontWeight: '600' },

  // Measure button
  measureBtn: { position: 'absolute', bottom: 40, alignSelf: 'center' },
  measureBtnInner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: Colors.primary, borderRadius: BorderRadius.full, paddingHorizontal: Spacing.xxl, paddingVertical: Spacing.lg, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 8, shadowOffset: { width: 0, height: 4 }, elevation: 5 },
  measureBtnText: { fontSize: FontSize.md, fontWeight: '700', color: '#fff' },

  // Result
  resultContainer: { flex: 1, padding: Spacing.lg, alignItems: 'center' },
  capturedImage: { width: '100%', height: 150, borderRadius: BorderRadius.lg, marginBottom: Spacing.lg },

  bigReading: { alignItems: 'center', marginBottom: Spacing.sm },
  bigNumber: { fontSize: 56, fontWeight: '800' },
  bigUnit: { fontSize: FontSize.md, fontWeight: '600', color: Colors.textSecondary, marginTop: -4 },

  statusBadge: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, borderRadius: BorderRadius.full, marginBottom: Spacing.lg },
  statusText: { fontSize: FontSize.md, fontWeight: '700' },

  // PPFD bar
  ppfdBarContainer: { width: '100%', marginBottom: Spacing.lg },
  ppfdBarLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, marginBottom: Spacing.xs, textAlign: 'center' },
  ppfdBarTrack: { height: 12, backgroundColor: '#E5E7EB', borderRadius: 6, overflow: 'visible', position: 'relative' },
  ppfdBarRange: { position: 'absolute', height: 12, backgroundColor: '#DCFCE7', borderRadius: 6 },
  ppfdBarCursor: { position: 'absolute', width: 4, height: 20, borderRadius: 2, top: -4 },
  ppfdBarLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  ppfdBarLabelText: { fontSize: 9, color: Colors.textSecondary },

  // Details
  detailsRow: { flexDirection: 'row', gap: Spacing.xxl, marginBottom: Spacing.lg },
  detailItem: { alignItems: 'center' },
  detailValue: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.text },
  detailLabel: { fontSize: FontSize.xs, color: Colors.textSecondary },

  // Message
  messageBox: { width: '100%', borderRadius: BorderRadius.md, padding: Spacing.md, marginBottom: Spacing.md },
  messageText: { fontSize: FontSize.sm, lineHeight: 20 },

  disclaimer: { fontSize: 10, color: Colors.textSecondary, textAlign: 'center', marginBottom: Spacing.lg },

  retryBtn: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.md },
  retryBtnText: { fontSize: FontSize.md, fontWeight: '600', color: Colors.primary },
});
