import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../src/components/ui/Button';
import { Card } from '../../src/components/ui/Card';
import { Badge } from '../../src/components/ui/Badge';
import { ProgressBar } from '../../src/components/ui/ProgressBar';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { useIdentifyPlant } from '../../src/features/plants/api/identify-api';
import { usePlantsWithDevices } from '../../src/features/plants/api/plants-api';
import { pickImageFromCamera, pickImageFromGallery } from '../../src/lib/image-utils';
import type { PickedImage } from '../../src/lib/image-utils';
import type { IdentifyResult, PlantWithDevice } from '../../src/types/plant';

type ScreenState = 'idle' | 'loading' | 'results' | 'error';

// --- Result Card ---
function ResultCard({
  result,
  expanded,
  onToggle,
  onSave,
}: {
  result: IdentifyResult;
  expanded: boolean;
  onToggle: () => void;
  onSave: () => void;
}) {
  const imageUrl = result.images[0];

  return (
    <TouchableOpacity activeOpacity={0.7} onPress={onToggle}>
      <Card style={styles.resultCard}>
        <View style={styles.resultRow}>
          {imageUrl ? (
            <Image source={{ uri: imageUrl }} style={styles.resultImage} />
          ) : (
            <View style={[styles.resultImage, styles.imagePlaceholder]}>
              <Ionicons name="leaf" size={24} color={Colors.accent} />
            </View>
          )}
          <View style={styles.resultInfo}>
            <Text style={styles.resultScientific}>{result.scientific}</Text>
            {result.commonNames[0] && (
              <Text style={styles.resultCommon}>{result.commonNames[0]}</Text>
            )}
            <Text style={styles.resultFamily}>{result.family}</Text>
          </View>
          <View style={styles.scoreBadge}>
            <Text style={styles.scoreText}>{Math.round(result.score)}%</Text>
          </View>
        </View>

        <View style={styles.badgeRow}>
          <Badge text={result.care.watering} variant="info" size="sm" />
          <Badge text={result.care.light} variant="neutral" size="sm" />
          {result.toxicity?.poisonous_to_pets && (
            <Badge text="Toxic" variant="error" size="sm" />
          )}
          <Badge text={result.care.preset} variant="success" size="sm" />
        </View>

        {expanded && (
          <View style={styles.expandedSection}>
            <Text style={styles.expandedLabel}>Temperature</Text>
            <Text style={styles.expandedValue}>{result.care.temperature}</Text>
            <Text style={styles.expandedLabel}>Humidity</Text>
            <Text style={styles.expandedValue}>{result.care.humidity}</Text>
            {result.care.tips ? (
              <>
                <Text style={styles.expandedLabel}>Tips</Text>
                <Text style={styles.expandedValue}>{result.care.tips}</Text>
              </>
            ) : null}
            <Button
              title="Save to My Plants"
              onPress={onSave}
              variant="primary"
              style={styles.saveBtn}
              icon={<Ionicons name="add-circle-outline" size={18} color="#fff" />}
            />
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );
}

// --- My Plant Card ---
function MyPlantCard({ plant }: { plant: PlantWithDevice }) {
  const router = useRouter();
  const name = plant.common_name || plant.scientific || 'Unknown plant';
  const moisture = plant.moisture_pct;
  const hasDevice = plant.active && plant.device_id;

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => router.push(`/plant/${plant.plant_id}`)}
    >
      <Card style={styles.plantCard}>
        <View style={styles.plantRow}>
          {plant.image_url ? (
            <Image source={{ uri: plant.image_url }} style={styles.plantImage} />
          ) : (
            <View style={[styles.plantImage, styles.imagePlaceholder]}>
              <Ionicons name="leaf" size={20} color={Colors.accent} />
            </View>
          )}
          <View style={styles.plantInfo}>
            <Text style={styles.plantName}>{name}</Text>
            {plant.scientific && plant.common_name && (
              <Text style={styles.plantScientific}>{plant.scientific}</Text>
            )}
            {hasDevice && moisture != null ? (
              <View style={styles.moistureRow}>
                <Ionicons name="water" size={12} color={Colors.moisture} />
                <Text style={styles.moistureText}>{moisture}%</Text>
                <View style={styles.moistureBar}>
                  <ProgressBar value={moisture} color={Colors.moisture} />
                </View>
              </View>
            ) : !hasDevice ? (
              <Text style={styles.noDeviceText}>No device attached</Text>
            ) : null}
          </View>
          {plant.preset && (
            <Badge text={plant.preset} variant="success" size="sm" />
          )}
        </View>
        {hasDevice && (
          <View style={styles.deviceRow}>
            <Ionicons name="hardware-chip-outline" size={11} color={Colors.textSecondary} />
            <Text style={styles.deviceText}>{plant.device_id}</Text>
            <View style={[styles.onlineDot, { backgroundColor: plant.device_online ? Colors.online : Colors.offline }]} />
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );
}

// --- Main Screen ---
export default function IdentifyScreen() {
  const [screenState, setScreenState] = useState<ScreenState>('idle');
  const [pickedImage, setPickedImage] = useState<PickedImage | null>(null);
  const [results, setResults] = useState<IdentifyResult[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const identifyMutation = useIdentifyPlant();

  const { plants, isRefetching, refetch } = usePlantsWithDevices();
  const activePlants = plants.filter((p) => p.active);
  const libraryPlants = plants.filter((p) => !p.active);

  const handleIdentify = useCallback(async (source: 'camera' | 'gallery') => {
    const image = source === 'camera'
      ? await pickImageFromCamera()
      : await pickImageFromGallery();
    if (!image) return;

    setPickedImage(image);
    setScreenState('loading');
    setErrorMsg('');

    identifyMutation.mutate(image.base64, {
      onSuccess: (data) => {
        if (data.results && data.results.length > 0) {
          setResults(data.results);
          setExpandedId(data.results[0].id);
          setScreenState('results');
        } else {
          setErrorMsg('No plants identified. Try a clearer photo.');
          setScreenState('error');
        }
      },
      onError: (err) => {
        setErrorMsg(err instanceof Error ? err.message : 'Identification failed');
        setScreenState('error');
      },
    });
  }, [identifyMutation]);

  const handleSave = useCallback((_result: IdentifyResult) => {
    // Placeholder — will be wired in Step 8
    Alert.alert(
      'Coming Soon',
      'Save flow will be connected in the next update. Connect a Polivalka device to save plants.',
    );
  }, []);

  const reset = () => {
    setScreenState('idle');
    setPickedImage(null);
    setResults([]);
    setExpandedId(null);
    setErrorMsg('');
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
      >
        {/* === IDENTIFY SECTION === */}
        {screenState === 'idle' && (
          <View style={styles.identifySection}>
            <View style={styles.identifyIcon}>
              <Ionicons name="leaf" size={48} color={Colors.accent} />
            </View>
            <Text style={styles.identifyTitle}>Identify Your Plant</Text>
            <Text style={styles.identifySubtitle}>Take a photo or choose from gallery</Text>
            <Button
              title="Take Photo"
              onPress={() => handleIdentify('camera')}
              variant="primary"
              size="lg"
              style={styles.identifyBtn}
              icon={<Ionicons name="camera-outline" size={20} color="#fff" />}
            />
            <View style={styles.secondaryBtns}>
              <Button
                title="Gallery"
                onPress={() => handleIdentify('gallery')}
                variant="outline"
                style={styles.halfBtn}
                icon={<Ionicons name="image-outline" size={16} color={Colors.primary} />}
              />
            </View>
          </View>
        )}

        {screenState === 'loading' && (
          <View style={styles.centerSection}>
            {pickedImage && (
              <Image source={{ uri: pickedImage.uri }} style={styles.previewImage} />
            )}
            <ActivityIndicator size="large" color={Colors.primary} style={{ marginTop: Spacing.xl }} />
            <Text style={styles.statusText}>Identifying plant...</Text>
          </View>
        )}

        {screenState === 'results' && (
          <View>
            <View style={styles.resultsHeader}>
              {pickedImage && (
                <Image source={{ uri: pickedImage.uri }} style={styles.thumbImage} />
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.resultsTitle}>
                  {results.length} match{results.length !== 1 ? 'es' : ''} found
                </Text>
                <TouchableOpacity onPress={reset}>
                  <Text style={styles.tryAgainText}>Try Again</Text>
                </TouchableOpacity>
              </View>
            </View>
            {results.map((r) => (
              <ResultCard
                key={r.id}
                result={r}
                expanded={expandedId === r.id}
                onToggle={() => setExpandedId(expandedId === r.id ? null : r.id)}
                onSave={() => handleSave(r)}
              />
            ))}
          </View>
        )}

        {screenState === 'error' && (
          <View style={styles.centerSection}>
            {pickedImage && (
              <Image source={{ uri: pickedImage.uri }} style={styles.previewImage} />
            )}
            <Ionicons name="alert-circle-outline" size={48} color={Colors.error} style={{ marginTop: Spacing.xl }} />
            <Text style={[styles.statusText, { color: Colors.error }]}>{errorMsg}</Text>
            <Button title="Try Again" onPress={reset} variant="outline" style={{ marginTop: Spacing.lg }} />
          </View>
        )}

        {/* === MY PLANTS SECTION (only in idle state) === */}
        {screenState === 'idle' && (
          <>
            {activePlants.length > 0 && (
              <>
                <Text style={styles.sectionTitle}>My Plants ({activePlants.length})</Text>
                {activePlants.map((plant) => (
                  <MyPlantCard key={plant.plant_id} plant={plant} />
                ))}
              </>
            )}

            {libraryPlants.length > 0 && (
              <>
                <Text style={[styles.sectionTitle, { marginTop: Spacing.xl }]}>
                  Archive ({libraryPlants.length})
                </Text>
                {libraryPlants.map((plant) => (
                  <MyPlantCard key={plant.plant_id} plant={plant} />
                ))}
              </>
            )}

            {activePlants.length === 0 && libraryPlants.length === 0 && (
              <Card style={styles.emptyCard}>
                <Ionicons name="leaf-outline" size={40} color={Colors.accent} />
                <Text style={styles.emptyTitle}>No plants yet</Text>
                <Text style={styles.emptyText}>Identify a plant by photo to get started</Text>
              </Card>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg, paddingBottom: 40 },

  // Identify
  identifySection: { alignItems: 'center', paddingVertical: Spacing.xxl },
  identifyIcon: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center',
    marginBottom: Spacing.lg,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 8, elevation: 3,
  },
  identifyTitle: { fontSize: FontSize.xxl, fontWeight: '700', color: Colors.text, marginBottom: Spacing.sm },
  identifySubtitle: { fontSize: FontSize.md, color: Colors.textSecondary, marginBottom: Spacing.xxl },
  identifyBtn: { width: '100%', marginBottom: Spacing.md },
  secondaryBtns: { flexDirection: 'row', gap: Spacing.md, width: '100%' },
  halfBtn: { flex: 1 },

  // Loading / Error
  centerSection: { alignItems: 'center', paddingVertical: Spacing.xxl },
  previewImage: { width: 200, height: 200, borderRadius: BorderRadius.lg },
  statusText: { fontSize: FontSize.md, color: Colors.textSecondary, marginTop: Spacing.md, textAlign: 'center' },

  // Results
  resultsHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.lg },
  thumbImage: { width: 60, height: 60, borderRadius: BorderRadius.md, marginRight: Spacing.md },
  resultsTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text },
  tryAgainText: { fontSize: FontSize.sm, color: Colors.primary, marginTop: 2 },

  resultCard: { marginBottom: Spacing.md },
  resultRow: { flexDirection: 'row', alignItems: 'center' },
  resultImage: { width: 56, height: 56, borderRadius: BorderRadius.md, marginRight: Spacing.md },
  imagePlaceholder: { backgroundColor: Colors.background, alignItems: 'center', justifyContent: 'center' },
  resultInfo: { flex: 1 },
  resultScientific: { fontSize: FontSize.md, fontWeight: '600', color: Colors.text, fontStyle: 'italic' },
  resultCommon: { fontSize: FontSize.sm, color: Colors.textSecondary },
  resultFamily: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  scoreBadge: { backgroundColor: Colors.accent, borderRadius: BorderRadius.sm, paddingHorizontal: Spacing.sm, paddingVertical: 2 },
  scoreText: { fontSize: FontSize.sm, fontWeight: '700', color: '#fff' },

  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: Spacing.sm },

  expandedSection: { marginTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: Spacing.md },
  expandedLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, fontWeight: '600', marginTop: Spacing.sm },
  expandedValue: { fontSize: FontSize.sm, color: Colors.text },
  saveBtn: { marginTop: Spacing.lg },

  // My Plants
  sectionTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.md, marginTop: Spacing.lg },
  plantCard: { marginBottom: Spacing.sm },
  plantRow: { flexDirection: 'row', alignItems: 'center' },
  plantImage: { width: 44, height: 44, borderRadius: BorderRadius.md, marginRight: Spacing.md },
  plantInfo: { flex: 1 },
  plantName: { fontSize: FontSize.md, fontWeight: '600', color: Colors.text },
  plantScientific: { fontSize: FontSize.xs, color: Colors.textSecondary, fontStyle: 'italic' },
  moistureRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 3 },
  moistureText: { fontSize: FontSize.xs, color: Colors.text, fontWeight: '500', width: 28 },
  moistureBar: { flex: 1, maxWidth: 100 },
  noDeviceText: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  deviceRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: Spacing.xs },
  deviceText: { fontSize: FontSize.xs, color: Colors.textSecondary },
  onlineDot: { width: 6, height: 6, borderRadius: 3 },

  // Empty
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl, marginTop: Spacing.lg },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md, marginBottom: Spacing.sm },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },
});
