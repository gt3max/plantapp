/**
 * Plant Journal — photo diary for user's plants.
 * Photos stored locally on device (expo-file-system).
 * Metadata stored in AsyncStorage.
 * Premium feature.
 */

import * as FileSystem from 'expo-file-system/legacy';
import * as ImageManipulator from 'expo-image-manipulator';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── Types ───────────────────────────────────────────────────────────

export interface JournalEntry {
  id: string;
  plantId: string;
  uri: string;           // file:// path on device
  thumbnailUri: string;  // smaller version for grid display
  date: string;          // ISO date string
  note: string;
  createdAt: number;     // Unix timestamp
}

interface JournalStore {
  entries: JournalEntry[];
}

// ─── Constants ───────────────────────────────────────────────────────

const STORAGE_KEY = 'plantapp:journal';
const JOURNAL_DIR = `${FileSystem.documentDirectory}journal/`;
const PHOTO_MAX_WIDTH = 1024;
const PHOTO_QUALITY = 0.7;
const THUMB_MAX_WIDTH = 300;
const THUMB_QUALITY = 0.5;

// ─── Internal helpers ────────────────────────────────────────────────

async function ensureDir(): Promise<void> {
  const info = await FileSystem.getInfoAsync(JOURNAL_DIR);
  if (!info.exists) {
    await FileSystem.makeDirectoryAsync(JOURNAL_DIR, { intermediates: true });
  }
}

async function loadStore(): Promise<JournalStore> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as JournalStore) : { entries: [] };
}

async function saveStore(store: JournalStore): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function generateId(): string {
  return `j_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Public API ──────────────────────────────────────────────────────

/**
 * Add a new photo to the journal.
 * Compresses the image and creates a thumbnail.
 * Returns the new entry.
 */
export async function addJournalEntry(
  plantId: string,
  sourceUri: string,
  note: string = '',
): Promise<JournalEntry> {
  await ensureDir();

  const id = generateId();

  // Compress full-size photo
  const photo = await ImageManipulator.manipulateAsync(
    sourceUri,
    [{ resize: { width: PHOTO_MAX_WIDTH } }],
    { compress: PHOTO_QUALITY, format: ImageManipulator.SaveFormat.JPEG },
  );
  const photoPath = `${JOURNAL_DIR}${id}.jpg`;
  await FileSystem.moveAsync({ from: photo.uri, to: photoPath });

  // Create thumbnail
  const thumb = await ImageManipulator.manipulateAsync(
    sourceUri,
    [{ resize: { width: THUMB_MAX_WIDTH } }],
    { compress: THUMB_QUALITY, format: ImageManipulator.SaveFormat.JPEG },
  );
  const thumbPath = `${JOURNAL_DIR}${id}_thumb.jpg`;
  await FileSystem.moveAsync({ from: thumb.uri, to: thumbPath });

  const entry: JournalEntry = {
    id,
    plantId,
    uri: photoPath,
    thumbnailUri: thumbPath,
    date: new Date().toISOString(),
    note,
    createdAt: Date.now(),
  };

  const store = await loadStore();
  store.entries.unshift(entry); // newest first
  await saveStore(store);

  return entry;
}

/**
 * Get all journal entries, newest first.
 * Optionally filter by plantId.
 */
export async function getJournalEntries(plantId?: string): Promise<JournalEntry[]> {
  const store = await loadStore();
  if (plantId) {
    return store.entries.filter((e) => e.plantId === plantId);
  }
  return store.entries;
}

/**
 * Update note on an existing entry.
 */
export async function updateJournalNote(entryId: string, note: string): Promise<void> {
  const store = await loadStore();
  const entry = store.entries.find((e) => e.id === entryId);
  if (entry) {
    entry.note = note;
    await saveStore(store);
  }
}

/**
 * Delete a journal entry and its files.
 */
export async function deleteJournalEntry(entryId: string): Promise<void> {
  const store = await loadStore();
  const entry = store.entries.find((e) => e.id === entryId);
  if (entry) {
    // Delete photo files
    await FileSystem.deleteAsync(entry.uri, { idempotent: true });
    await FileSystem.deleteAsync(entry.thumbnailUri, { idempotent: true });
    // Remove from store
    store.entries = store.entries.filter((e) => e.id !== entryId);
    await saveStore(store);
  }
}

/**
 * Delete all journal entries for a specific plant.
 * Called when plant is removed from collection.
 */
export async function deleteAllForPlant(plantId: string): Promise<void> {
  const store = await loadStore();
  const toDelete = store.entries.filter((e) => e.plantId === plantId);
  for (const entry of toDelete) {
    await FileSystem.deleteAsync(entry.uri, { idempotent: true });
    await FileSystem.deleteAsync(entry.thumbnailUri, { idempotent: true });
  }
  store.entries = store.entries.filter((e) => e.plantId !== plantId);
  await saveStore(store);
}

/**
 * Get count of journal entries per plant.
 */
export async function getJournalCounts(): Promise<Record<string, number>> {
  const store = await loadStore();
  const counts: Record<string, number> = {};
  for (const entry of store.entries) {
    counts[entry.plantId] = (counts[entry.plantId] ?? 0) + 1;
  }
  return counts;
}
