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
import { POPULAR_PLANTS, CATEGORIES } from '../../src/constants/popular-plants';
import { usePlantDBSearch, usePlantDBStats } from '../../src/features/plants/api/plant-db-api';
import type { PopularPlant } from '../../src/constants/popular-plants';
import type { PlantDBSearchResult } from '../../src/types/plant-db';

// --- Category Tile ---
function CategoryTile({
  label,
  icon,
  count,
  selected,
  onPress,
}: {
  label: string;
  icon: string;
  count: number;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      style={[styles.categoryTile, selected && styles.categoryTileSelected]}
    >
      <Text style={styles.categoryEmoji}>{icon}</Text>
      <Text style={[styles.categoryLabel, selected && styles.categoryLabelSelected]}>
        {label}
      </Text>
      <Text style={styles.categoryCount}>{count}</Text>
    </TouchableOpacity>
  );
}

// --- Plant List Item ---
function PlantListItem({ plant }: { plant: PopularPlant }) {
  const router = useRouter();

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
              <Ionicons name="leaf" size={20} color={Colors.accent} />
            </View>
          )}
          <View style={styles.plantInfo}>
            <Text style={styles.plantScientific}>{plant.scientific}</Text>
            <Text style={styles.plantCommon}>{plant.common_name}</Text>
            <Text style={styles.plantFamily}>{plant.family}</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color={Colors.textSecondary} />
        </View>
        <View style={styles.badgeRow}>
          <Badge text={plant.preset} variant="success" size="sm" />
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
              <Ionicons name="leaf" size={20} color={Colors.accent} />
            </View>
          )}
          <View style={styles.plantInfo}>
            <Text style={styles.plantScientific}>{result.scientific}</Text>
            <Text style={styles.plantCommon}>{result.common_name}</Text>
            <Text style={styles.plantFamily}>{result.family}</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color={Colors.textSecondary} />
        </View>
        <View style={styles.badgeRow}>
          <Badge text={result.preset} variant="success" size="sm" />
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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Turso DB search (fires when search >= 2 chars)
  const { data: dbResults, isLoading: dbLoading } = usePlantDBSearch(search.trim());
  const { data: dbStats } = usePlantDBStats();
  const isSearching = search.trim().length >= 2;

  const filteredPlants = useMemo(() => {
    // When actively searching, Turso results take over
    if (isSearching) return [];

    let list = POPULAR_PLANTS;

    if (selectedCategory) {
      list = list.filter((p) => p.category === selectedCategory);
    }

    return list;
  }, [selectedCategory, isSearching]);

  const handleCategoryPress = (key: string) => {
    setSelectedCategory(selectedCategory === key ? null : key);
  };

  const totalPlants = dbStats?.total_plants ?? 25;

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
            {/* Categories */}
            <Text style={styles.sectionTitle}>Categories</Text>
            <View style={styles.categoryGrid}>
              {CATEGORIES.map((cat) => (
                <CategoryTile
                  key={cat.key}
                  label={cat.label}
                  icon={cat.icon}
                  count={cat.count}
                  selected={selectedCategory === cat.key}
                  onPress={() => handleCategoryPress(cat.key)}
                />
              ))}
            </View>

            {/* Plants list */}
            <Text style={styles.sectionTitle}>
              {selectedCategory
                ? `${CATEGORIES.find((c) => c.key === selectedCategory)?.label ?? 'Plants'} (${filteredPlants.length})`
                : `Popular Plants (${filteredPlants.length})`}
            </Text>

            {filteredPlants.length === 0 ? (
              <Card style={styles.emptyCard}>
                <Ionicons name="search-outline" size={40} color={Colors.textSecondary} />
                <Text style={styles.emptyTitle}>No plants found</Text>
                <Text style={styles.emptyText}>Try a different search or category</Text>
              </Card>
            ) : (
              filteredPlants.map((plant) => (
                <PlantListItem key={plant.id} plant={plant} />
              ))
            )}
          </>
        )}

        {/* DB info */}
        <Card style={styles.comingSoonCard}>
          <Ionicons name="library-outline" size={32} color={Colors.accent} />
          <Text style={styles.comingSoonTitle}>
            {totalPlants.toLocaleString()} plants in database
          </Text>
          <Text style={styles.comingSoonText}>
            Growing to 100,000+ species with per-plant care data.
          </Text>
        </Card>
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

  // Categories
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    marginBottom: Spacing.xl,
  },
  categoryTile: {
    width: '31%',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    paddingVertical: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  categoryTileSelected: {
    borderColor: Colors.primary,
    backgroundColor: '#E8F5E9',
  },
  categoryEmoji: { fontSize: 28, marginBottom: Spacing.xs },
  categoryLabel: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.text },
  categoryLabelSelected: { color: Colors.primary },
  categoryCount: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },

  // Plant card
  plantCard: { marginBottom: Spacing.sm },
  plantRow: { flexDirection: 'row', alignItems: 'center' },
  plantImage: {
    width: 52,
    height: 52,
    borderRadius: BorderRadius.md,
    marginRight: Spacing.md,
  },
  imagePlaceholder: {
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  plantInfo: { flex: 1 },
  plantScientific: {
    fontSize: FontSize.md,
    fontWeight: '600',
    color: Colors.text,
    fontStyle: 'italic',
  },
  plantCommon: { fontSize: FontSize.sm, color: Colors.textSecondary },
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

  // Coming soon
  comingSoonCard: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
    marginTop: Spacing.lg,
  },
  comingSoonTitle: {
    fontSize: FontSize.md,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
    marginBottom: Spacing.xs,
  },
  comingSoonText: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
});
