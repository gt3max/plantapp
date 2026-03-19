import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../src/components/ui/Card';
import { Badge } from '../../src/components/ui/Badge';
import { Colors, Spacing, FontSize, BorderRadius } from '../../src/constants/colors';
import { POPULAR_PLANTS } from '../../src/constants/popular-plants';
import { usePlantDBSearch, usePlantDBStats } from '../../src/features/plants/api/plant-db-api';
import type { PopularPlant } from '../../src/constants/popular-plants';
import type { PlantDBSearchResult } from '../../src/types/plant-db';

// --- Plant List Item (popular plants with rich data) ---
function PlantListItem({ plant }: { plant: PopularPlant }) {
  const router = useRouter();
  const diffVariant = plant.difficulty === 'Advanced' ? 'error'
    : plant.difficulty === 'Medium' ? 'warning' : 'success';

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => router.push(`/plant/${plant.id}`)}
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
            <Text style={styles.plantName}>{plant.common_name}</Text>
            <Text style={styles.plantScientific}>{plant.scientific}</Text>
            <Text style={styles.plantDesc} numberOfLines={2}>{plant.description}</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color={Colors.textSecondary} />
        </View>
        <View style={styles.badgeRow}>
          {plant.difficulty ? (
            <Badge text={plant.difficulty} variant={diffVariant} size="sm" />
          ) : null}
          {plant.edible && (
            <Badge text="Edible" variant="success" size="sm" />
          )}
          {plant.poisonous_to_pets ? (
            <Badge text="Toxic to pets" variant="error" size="sm" />
          ) : (
            <Badge text="Pet safe" variant="success" size="sm" />
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}

// --- DB Search Result Item ---
function DBSearchItem({ result }: { result: PlantDBSearchResult }) {
  const router = useRouter();

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => router.push(`/plant/${result.plant_id}`)}
    >
      <Card style={styles.plantCard}>
        <View style={styles.plantRow}>
          {result.image_url ? (
            <Image source={{ uri: result.image_url }} style={styles.plantImage} />
          ) : (
            <View style={[styles.plantImage, styles.imagePlaceholder]}>
              <Ionicons name="leaf" size={24} color={Colors.accent} />
            </View>
          )}
          <View style={styles.plantInfo}>
            <Text style={styles.plantName}>{result.common_name || result.scientific}</Text>
            {result.common_name ? (
              <Text style={styles.plantScientific}>{result.scientific}</Text>
            ) : null}
            <Text style={styles.plantFamily}>{result.family}</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color={Colors.textSecondary} />
        </View>
        <View style={styles.badgeRow}>
          {result.toxic_to_pets ? (
            <Badge text="Toxic to pets" variant="error" size="sm" />
          ) : (
            <Badge text="Pet safe" variant="success" size="sm" />
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}

// --- Main Screen ---
export default function LibraryScreen() {
  const [search, setSearch] = useState('');

  // Turso DB search (fires when search >= 2 chars)
  const { data: dbResults, isLoading: dbLoading } = usePlantDBSearch(search.trim());
  const { data: dbStats } = usePlantDBStats();
  const isSearching = search.trim().length >= 2;

  // Local search through popular plants when not hitting DB
  const filteredPlants = useMemo(() => {
    if (isSearching) return [];
    const q = search.trim().toLowerCase();
    if (!q) return POPULAR_PLANTS;
    return POPULAR_PLANTS.filter((p) =>
      p.common_name.toLowerCase().includes(q) ||
      p.scientific.toLowerCase().includes(q) ||
      p.family.toLowerCase().includes(q)
    );
  }, [search, isSearching]);

  const totalPlants = dbStats?.total_plants ?? POPULAR_PLANTS.length;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Search */}
        <View style={styles.searchBar}>
          <Ionicons name="search" size={18} color={Colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder={`Search ${totalPlants.toLocaleString()} plants...`}
            placeholderTextColor={Colors.textSecondary}
            value={search}
            onChangeText={setSearch}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {search.length > 0 && (
            <TouchableOpacity onPress={() => setSearch('')}>
              <Ionicons name="close-circle" size={18} color={Colors.textSecondary} />
            </TouchableOpacity>
          )}
        </View>

        {/* Turso search results */}
        {isSearching ? (
          <>
            {dbLoading ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator size="small" color={Colors.primary} />
                <Text style={styles.loadingText}>Searching...</Text>
              </View>
            ) : dbResults && dbResults.results.length > 0 ? (
              <>
                <Text style={styles.sectionTitle}>
                  Results ({dbResults.count})
                </Text>
                {dbResults.results.map((r) => (
                  <DBSearchItem key={r.plant_id} result={r} />
                ))}
              </>
            ) : (
              <Card style={styles.emptyCard}>
                <Ionicons name="search-outline" size={40} color={Colors.textSecondary} />
                <Text style={styles.emptyTitle}>No plants found</Text>
                <Text style={styles.emptyText}>Try a different search term</Text>
              </Card>
            )}
          </>
        ) : (
          <>
            {/* Plants list — no categories, just the list */}
            <Text style={styles.sectionTitle}>
              Plants ({filteredPlants.length})
            </Text>

            {filteredPlants.length === 0 ? (
              <Card style={styles.emptyCard}>
                <Ionicons name="search-outline" size={40} color={Colors.textSecondary} />
                <Text style={styles.emptyTitle}>No plants found</Text>
                <Text style={styles.emptyText}>Try a different search term</Text>
              </Card>
            ) : (
              filteredPlants.map((plant) => (
                <PlantListItem key={plant.id} plant={plant} />
              ))
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

  // Search
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    marginBottom: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  searchInput: {
    flex: 1,
    fontSize: FontSize.md,
    color: Colors.text,
    marginLeft: Spacing.sm,
    paddingVertical: 4,
  },

  // Section
  sectionTitle: {
    fontSize: FontSize.lg,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.md,
  },

  // Plant card
  plantCard: { marginBottom: Spacing.sm },
  plantRow: { flexDirection: 'row', alignItems: 'center' },
  plantImage: {
    width: 64,
    height: 64,
    borderRadius: BorderRadius.lg,
    marginRight: Spacing.md,
  },
  imagePlaceholder: {
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  plantInfo: { flex: 1 },
  plantName: {
    fontSize: FontSize.md,
    fontWeight: '700',
    color: Colors.text,
  },
  plantScientific: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    fontStyle: 'italic',
  },
  plantDesc: {
    fontSize: FontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 16,
    marginTop: 2,
  },
  plantFamily: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: Spacing.sm },

  // Empty
  emptyCard: { alignItems: 'center', paddingVertical: Spacing.xxxl },
  emptyTitle: {
    fontSize: FontSize.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
    marginBottom: Spacing.sm,
  },
  emptyText: { fontSize: FontSize.md, color: Colors.textSecondary, textAlign: 'center' },

  // Loading
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.xxl,
  },
  loadingText: { fontSize: FontSize.md, color: Colors.textSecondary },
});
