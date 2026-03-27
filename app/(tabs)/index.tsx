import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Modal,
  Dimensions,
} from 'react-native';
import { ScrollView } from 'react-native-gesture-handler';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../src/components/ui/Button';
import { Card } from '../../src/components/ui/Card';
import { Badge } from '../../src/components/ui/Badge';
import { ProgressBar } from '../../src/components/ui/ProgressBar';
import { SwipeableRow } from '../../src/components/ui/SwipeableRow';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { useIdentifyPlant, useSavePlant } from '../../src/features/plants/api/identify-api';
import { usePlantsWithDevices, useDeletePlant } from '../../src/features/plants/api/plants-api';
import { pickImageFromCamera, pickImageFromGallery } from '../../src/lib/image-utils';
import type { PickedImage } from '../../src/lib/image-utils';
import type { IdentifyResult, PlantWithDevice } from '../../src/types/plant';
import { getJournalEntries, deleteJournalEntry, type JournalEntry } from '../../src/lib/plant-journal';

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
          <View style={styles.scoreCol}>
            <View style={styles.scoreBadge}>
              <Text style={styles.scoreText}>{Math.round(result.score)}%</Text>
            </View>
            {result.serpapi_verification?.verified && (
              <Ionicons name="checkmark-circle" size={14} color={Colors.success} style={{ marginTop: 2 }} />
            )}
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
            {result.enrichment?.growth_rate ? (
              <>
                <Text style={styles.expandedLabel}>Growth rate</Text>
                <Text style={styles.expandedValue}>{result.enrichment.growth_rate}</Text>
              </>
            ) : null}
            {result.enrichment?.care_level ? (
              <>
                <Text style={styles.expandedLabel}>Difficulty</Text>
                <Text style={styles.expandedValue}>{result.enrichment.care_level}</Text>
              </>
            ) : null}
            {result.enrichment?.pest_susceptibility && result.enrichment.pest_susceptibility.length > 0 ? (
              <>
                <Text style={styles.expandedLabel}>Common pests</Text>
                <Text style={styles.expandedValue}>{result.enrichment.pest_susceptibility.join(', ')}</Text>
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

// --- My Plant Card (cleaned up) ---
function MyPlantCard({ plant }: { plant: PlantWithDevice }) {
  const router = useRouter();
  const name = plant.common_name || plant.scientific || 'Unknown plant';
  const moisture = plant.moisture_pct;
  const hasDevice = plant.active && plant.device_id && plant.device_id !== 'user-collection';

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
              <Ionicons name="leaf" size={24} color={Colors.accent} />
            </View>
          )}
          <View style={styles.plantInfo}>
            <Text style={styles.plantName}>{name}</Text>
            {plant.scientific && plant.common_name && (
              <Text style={styles.plantScientific}>{plant.scientific}</Text>
            )}
            {hasDevice && moisture != null && (
              <View style={styles.moistureRow}>
                <Ionicons name="water" size={13} color={Colors.moisture} />
                <Text style={styles.moistureText}>{moisture}%</Text>
                <View style={styles.moistureBar}>
                  <ProgressBar value={moisture} color={Colors.moisture} />
                </View>
              </View>
            )}
          </View>
        </View>
        {hasDevice && (
          <View style={styles.deviceRow}>
            <Ionicons name="hardware-chip-outline" size={12} color={Colors.textSecondary} />
            <Text style={styles.deviceText}>{plant.device_id}</Text>
            <View style={[styles.onlineDot, { backgroundColor: plant.device_online ? Colors.online : Colors.offline }]} />
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );
}

// --- Main Screen ---
export default function MyPlantsScreen() {
  const [screenState, setScreenState] = useState<ScreenState>('idle');
  const [pickedImage, setPickedImage] = useState<PickedImage | null>(null);
  const [results, setResults] = useState<IdentifyResult[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'plants' | 'journal'>('plants');
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);
  const [journalLoading, setJournalLoading] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  const identifyMutation = useIdentifyPlant();
  const saveMutation = useSavePlant();
  const deleteMutation = useDeletePlant();

  const { plants, isRefetching, refetch } = usePlantsWithDevices();
  // My Plants = active on device OR saved to collection (no device)
  const myPlants = plants.filter((p) => p.active || p.device_id === 'user-collection');
  const archivedPlants = plants.filter((p) => !p.active && p.device_id !== 'user-collection');

  const reset = useCallback(() => {
    setScreenState('idle');
    setPickedImage(null);
    setResults([]);
    setExpandedId(null);
    setErrorMsg('');
  }, []);

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
        // Filter out low-confidence results (< 1%)
        const filtered = (data.results ?? []).filter((r) => r.score >= 1);
        if (filtered.length > 0) {
          setResults(filtered);
          setExpandedId(filtered[0].id);
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

  const handleSave = useCallback((result: IdentifyResult) => {
    // Default watering frequency (summer days) based on preset
    const presetWateringDays: Record<string, number> = {
      Succulents: 10,
      Standard: 7,
      Tropical: 5,
      Herbs: 2,
    };
    const wateringFreqDays = presetWateringDays[result.care.preset] ?? 7;

    saveMutation.mutate(
      {
        input: {
          plant: {
            scientific: result.scientific,
            common_name: result.commonNames[0] ?? result.scientific,
            family: result.family,
            preset: result.care.preset,
            start_pct: result.care.start_pct,
            stop_pct: result.care.stop_pct,
            image_url: result.images?.[0] || '',
            poisonous_to_pets: result.toxicity?.poisonous_to_pets,
            poisonous_to_humans: result.toxicity?.poisonous_to_humans,
            toxicity_note: result.toxicity?.toxicity_note,
          },
        },
        wateringFreqDays,
      },
      {
        onSuccess: () => {
          Alert.alert('Saved!', `${result.commonNames[0] ?? result.scientific} added to My Plants.`);
          reset();
        },
        onError: (err) => {
          Alert.alert('Error', err instanceof Error ? err.message : 'Failed to save plant.');
        },
      },
    );
  }, [saveMutation, reset]);

  const handleDelete = useCallback((plant: PlantWithDevice) => {
    const name = plant.common_name || plant.scientific || 'this plant';
    const deviceId = plant.device_id || 'user-collection';

    Alert.alert(
      'Delete plant?',
      `Remove ${name} from your collection?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            console.log('[DELETE]', { deviceId, plantId: plant.plant_id, active: plant.active });
            deleteMutation.mutate(
              { deviceId, plantId: plant.plant_id, active: plant.active },
              {
                onError: (err) => {
                  Alert.alert('Error', err instanceof Error ? err.message : 'Failed to delete plant.');
                },
              },
            );
          },
        },
      ],
    );
  }, [deleteMutation]);

  // Load journal entries when journal tab is active
  const loadJournal = useCallback(async () => {
    setJournalLoading(true);
    try {
      const entries = await getJournalEntries();
      setJournalEntries(entries);
    } catch {
      // silently fail — journal is non-critical
    } finally {
      setJournalLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'journal') {
      loadJournal();
    }
  }, [activeTab, loadJournal]);

  // Build a plantId→name map for journal display
  const plantNameMap = useCallback((): Record<string, string> => {
    const map: Record<string, string> = {};
    for (const p of plants) {
      map[p.plant_id] = p.common_name || p.scientific || 'Unknown';
    }
    return map;
  }, [plants]);

  // Group journal entries by month/year
  const groupedJournal = useCallback((): Array<{ label: string; entries: JournalEntry[] }> => {
    const groups: Map<string, JournalEntry[]> = new Map();
    for (const entry of journalEntries) {
      const d = new Date(entry.date);
      const key = `${d.getFullYear()}-${String(d.getMonth()).padStart(2, '0')}`;
      const label = d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(entry);
    }
    return Array.from(groups.entries()).map(([, entries]) => {
      const d = new Date(entries[0].date);
      return {
        label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
        entries,
      };
    });
  }, [journalEntries]);

  const handleDeleteJournalEntry = useCallback((entry: JournalEntry) => {
    const names = plantNameMap();
    Alert.alert(
      'Delete photo?',
      `Remove this photo of ${names[entry.plantId] ?? 'Unknown'}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            await deleteJournalEntry(entry.id);
            setSelectedEntry(null);
            loadJournal();
          },
        },
      ],
    );
  }, [plantNameMap, loadJournal]);

  const screenWidth = Dimensions.get('window').width;
  const thumbSize = (screenWidth - Spacing.lg * 2 - Spacing.sm * 2) / 3;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
      >
        {/* === TAB SWITCHER (only in idle) === */}
        {screenState === 'idle' && (
          <View style={styles.tabSwitcher}>
            <TouchableOpacity
              onPress={() => setActiveTab('plants')}
              style={[styles.tabBtn, activeTab === 'plants' && styles.tabBtnActive]}
            >
              <Text style={[styles.tabBtnText, activeTab === 'plants' && styles.tabBtnTextActive]}>My Plants</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => setActiveTab('journal')}
              style={[styles.tabBtn, activeTab === 'journal' && styles.tabBtnActive]}
            >
              <Text style={[styles.tabBtnText, activeTab === 'journal' && styles.tabBtnTextActive]}>Journal</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Identify buttons moved below plant list */}

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

        {/* === MY PLANTS SECTION (only in idle state + plants tab) === */}
        {screenState === 'idle' && activeTab === 'plants' && (
          <>
            {myPlants.length > 0 && (
              <>
                <Text style={styles.sectionTitle}>My Plants ({myPlants.length})</Text>
                {myPlants.map((plant) => (
                  <SwipeableRow key={plant.plant_id} onDelete={() => handleDelete(plant)}>
                    <MyPlantCard plant={plant} />
                  </SwipeableRow>
                ))}
              </>
            )}

            {archivedPlants.length > 0 && (
              <>
                <Text style={[styles.sectionTitle, { marginTop: Spacing.xl }]}>
                  Archive ({archivedPlants.length})
                </Text>
                {archivedPlants.map((plant) => (
                  <SwipeableRow key={plant.plant_id} onDelete={() => handleDelete(plant)}>
                    <MyPlantCard plant={plant} />
                  </SwipeableRow>
                ))}
              </>
            )}

            {myPlants.length === 0 && archivedPlants.length === 0 && (
              <Card style={styles.emptyCard}>
                <Ionicons name="leaf-outline" size={40} color={Colors.accent} />
                <Text style={styles.emptyTitle}>No plants yet</Text>
                <Text style={styles.emptyText}>Identify a plant by photo to get started</Text>
              </Card>
            )}

            {/* === IDENTIFY BUTTONS (below plant list) === */}
            <View style={styles.identifyColumn}>
              <Button
                title="Identify plant"
                onPress={() => handleIdentify('camera')}
                variant="primary"
                style={styles.identifyBtnFull}
                icon={<Ionicons name="camera-outline" size={18} color="#fff" />}
              />
              <Button
                title="Choose from gallery"
                onPress={() => handleIdentify('gallery')}
                variant="outline"
                style={styles.identifyBtnFull}
                icon={<Ionicons name="image-outline" size={18} color={Colors.primary} />}
              />
            </View>
          </>
        )}

        {/* === JOURNAL TAB (only in idle state + journal tab) === */}
        {screenState === 'idle' && activeTab === 'journal' && (
          <>
            {journalLoading && (
              <View style={styles.centerSection}>
                <ActivityIndicator size="large" color={Colors.primary} />
              </View>
            )}

            {!journalLoading && journalEntries.length === 0 && (
              <Card style={styles.emptyCard}>
                <Ionicons name="images-outline" size={40} color={Colors.accent} />
                <Text style={styles.emptyTitle}>No photos yet</Text>
                <Text style={styles.emptyText}>
                  Open a plant and tap Add Photo to start your journal.
                </Text>
              </Card>
            )}

            {!journalLoading && journalEntries.length > 0 && (
              <>
                {groupedJournal().map((group) => (
                  <View key={group.label}>
                    <Text style={styles.sectionTitle}>{group.label}</Text>
                    <View style={styles.journalGrid}>
                      {group.entries.map((entry) => {
                        const names = plantNameMap();
                        return (
                          <TouchableOpacity
                            key={entry.id}
                            activeOpacity={0.8}
                            onPress={() => setSelectedEntry(entry)}
                            style={[styles.journalThumb, { width: thumbSize, height: thumbSize }]}
                          >
                            <Image source={{ uri: entry.thumbnailUri }} style={styles.journalThumbImage} />
                            <View style={styles.journalThumbBadge}>
                              <Text style={styles.journalThumbName} numberOfLines={1}>
                                {names[entry.plantId] ?? 'Unknown'}
                              </Text>
                            </View>
                            <View style={styles.journalThumbDate}>
                              <Text style={styles.journalThumbDateText}>
                                {new Date(entry.date).getDate()}
                              </Text>
                            </View>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  </View>
                ))}
              </>
            )}
          </>
        )}

        {/* === JOURNAL PHOTO VIEWER MODAL === */}
        <Modal
          visible={selectedEntry !== null}
          transparent
          animationType="fade"
          onRequestClose={() => setSelectedEntry(null)}
        >
          {selectedEntry && (
            <View style={styles.modalOverlay}>
              <View style={styles.modalContent}>
                <Image source={{ uri: selectedEntry.uri }} style={styles.modalImage} />
                <Text style={styles.modalPlantName}>
                  {plantNameMap()[selectedEntry.plantId] ?? 'Unknown'}
                </Text>
                <Text style={styles.modalDate}>
                  {new Date(selectedEntry.date).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </Text>
                {selectedEntry.note ? (
                  <Text style={styles.modalNote}>{selectedEntry.note}</Text>
                ) : null}
                <View style={styles.modalActions}>
                  <TouchableOpacity
                    onPress={() => handleDeleteJournalEntry(selectedEntry)}
                    style={styles.modalDeleteBtn}
                  >
                    <Ionicons name="trash-outline" size={18} color={Colors.error} />
                    <Text style={styles.modalDeleteText}>Delete</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => setSelectedEntry(null)}
                    style={styles.modalCloseBtn}
                  >
                    <Text style={styles.modalCloseText}>Close</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          )}
        </Modal>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.lg, paddingBottom: 40 },

  // Identify buttons (stacked vertically, below plant list)
  identifyColumn: {
    marginTop: Spacing.xl,
    gap: Spacing.md,
  },
  identifyBtnFull: { width: '100%' },

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
  scoreCol: { alignItems: 'center' },
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
  plantImage: { width: 56, height: 56, borderRadius: BorderRadius.md, marginRight: Spacing.md },
  plantInfo: { flex: 1 },
  plantName: { fontSize: FontSize.md, fontWeight: '600', color: Colors.text },
  plantScientific: { fontSize: FontSize.xs, color: Colors.textSecondary, fontStyle: 'italic' },
  moistureRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 3 },
  moistureText: { fontSize: FontSize.xs, color: Colors.text, fontWeight: '500', width: 28 },
  moistureBar: { flex: 1, maxWidth: 100 },
  deviceRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: Spacing.xs },
  deviceText: { fontSize: FontSize.xs, color: Colors.textSecondary },
  onlineDot: { width: 6, height: 6, borderRadius: 3 },

  // Empty
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl, marginTop: Spacing.lg },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md, marginBottom: Spacing.sm },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },

  // Tab switcher (segment control)
  tabSwitcher: {
    flexDirection: 'row',
    backgroundColor: '#F3F4F6',
    borderRadius: BorderRadius.sm,
    padding: 2,
    marginBottom: Spacing.lg,
  },
  tabBtn: {
    flex: 1,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.sm - 1,
    alignItems: 'center',
  },
  tabBtnActive: {
    backgroundColor: Colors.surface,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 2,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  tabBtnText: { fontSize: FontSize.sm, color: Colors.textSecondary, fontWeight: '600' },
  tabBtnTextActive: { color: Colors.text },

  // Journal grid
  journalGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  journalThumb: {
    borderRadius: BorderRadius.md,
    overflow: 'hidden',
    position: 'relative',
  },
  journalThumbImage: {
    width: '100%',
    height: '100%',
  },
  journalThumbBadge: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingHorizontal: Spacing.xs,
    paddingVertical: 2,
  },
  journalThumbName: {
    fontSize: FontSize.xs,
    color: '#fff',
    fontWeight: '600',
  },
  journalThumbDate: {
    position: 'absolute',
    top: Spacing.xs,
    right: Spacing.xs,
    backgroundColor: 'rgba(0,0,0,0.45)',
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.xs,
    paddingVertical: 1,
  },
  journalThumbDateText: {
    fontSize: FontSize.xs,
    color: '#fff',
    fontWeight: '600',
  },

  // Journal modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.lg,
  },
  modalContent: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    overflow: 'hidden',
    width: '100%',
    maxWidth: 400,
  },
  modalImage: {
    width: '100%',
    aspectRatio: 1,
  },
  modalPlantName: {
    fontSize: FontSize.lg,
    fontWeight: '600',
    color: Colors.text,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },
  modalDate: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.xs,
  },
  modalNote: {
    fontSize: FontSize.md,
    color: Colors.text,
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.sm,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.lg,
    marginTop: Spacing.sm,
  },
  modalDeleteBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  modalDeleteText: {
    fontSize: FontSize.sm,
    color: Colors.error,
    fontWeight: '600',
  },
  modalCloseBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.sm,
  },
  modalCloseText: {
    fontSize: FontSize.sm,
    color: '#fff',
    fontWeight: '600',
  },
});
