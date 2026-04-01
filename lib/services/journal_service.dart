import 'dart:convert';
import 'dart:io';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Plant Journal — photo diary stored locally on device.
/// Premium feature.
class JournalService {
  JournalService._();
  static final instance = JournalService._();

  static const _storageKey = 'plantapp:journal';
  static const _photoMaxWidth = 1024;
  static const _photoQuality = 70;
  static const _thumbMaxWidth = 300;
  static const _thumbQuality = 50;

  String? _journalDir;

  Future<String> _getDir() async {
    if (_journalDir != null) return _journalDir!;
    final appDir = await getApplicationDocumentsDirectory();
    _journalDir = '${appDir.path}/journal';
    final dir = Directory(_journalDir!);
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    return _journalDir!;
  }

  String _generateId() {
    final ts = DateTime.now().millisecondsSinceEpoch;
    final rand = (DateTime.now().microsecond % 1000000).toRadixString(36);
    return 'j_${ts}_$rand';
  }

  /// Add a photo to the journal. Compresses and creates thumbnail.
  Future<JournalEntry> addEntry({
    required String plantId,
    required String sourceUri,
    String note = '',
  }) async {
    final dir = await _getDir();
    final id = _generateId();

    // Read source image
    final sourceFile = File(sourceUri);
    final bytes = await sourceFile.readAsBytes();
    final original = img.decodeImage(bytes);
    if (original == null) throw Exception('Failed to decode image');

    // Compress full-size
    final resized = img.copyResize(original, width: _photoMaxWidth);
    final photoPath = '$dir/$id.jpg';
    File(photoPath).writeAsBytesSync(img.encodeJpg(resized, quality: _photoQuality));

    // Create thumbnail
    final thumb = img.copyResize(original, width: _thumbMaxWidth);
    final thumbPath = '$dir/${id}_thumb.jpg';
    File(thumbPath).writeAsBytesSync(img.encodeJpg(thumb, quality: _thumbQuality));

    final entry = JournalEntry(
      id: id,
      plantId: plantId,
      uri: photoPath,
      thumbnailUri: thumbPath,
      date: DateTime.now().toIso8601String(),
      note: note,
      createdAt: DateTime.now().millisecondsSinceEpoch,
    );

    final entries = await _loadEntries();
    entries.insert(0, entry); // newest first
    await _saveEntries(entries);

    return entry;
  }

  /// Get all journal entries, newest first. Optionally filter by plantId.
  Future<List<JournalEntry>> getEntries({String? plantId}) async {
    final entries = await _loadEntries();
    if (plantId != null) {
      return entries.where((e) => e.plantId == plantId).toList();
    }
    return entries;
  }

  /// Delete a journal entry and its files.
  Future<void> deleteEntry(String entryId) async {
    final entries = await _loadEntries();
    final entry = entries.where((e) => e.id == entryId).firstOrNull;
    if (entry != null) {
      // Delete files
      final photoFile = File(entry.uri);
      if (photoFile.existsSync()) photoFile.deleteSync();
      final thumbFile = File(entry.thumbnailUri);
      if (thumbFile.existsSync()) thumbFile.deleteSync();

      entries.removeWhere((e) => e.id == entryId);
      await _saveEntries(entries);
    }
  }

  /// Get entries grouped by month for grid display.
  Future<Map<String, List<JournalEntry>>> getEntriesByMonth({String? plantId}) async {
    final entries = await getEntries(plantId: plantId);
    final grouped = <String, List<JournalEntry>>{};
    for (final entry in entries) {
      final date = DateTime.parse(entry.date);
      final key = '${date.year}-${date.month.toString().padLeft(2, '0')}';
      grouped.putIfAbsent(key, () => []).add(entry);
    }
    return grouped;
  }

  /// Update note on an existing entry.
  Future<void> updateNote(String entryId, String note) async {
    final entries = await _loadEntries();
    final idx = entries.indexWhere((e) => e.id == entryId);
    if (idx >= 0) {
      entries[idx] = JournalEntry(
        id: entries[idx].id,
        plantId: entries[idx].plantId,
        uri: entries[idx].uri,
        thumbnailUri: entries[idx].thumbnailUri,
        date: entries[idx].date,
        note: note,
        createdAt: entries[idx].createdAt,
      );
      await _saveEntries(entries);
    }
  }

  /// Delete all journal entries for a specific plant.
  Future<void> deleteAllForPlant(String plantId) async {
    final entries = await _loadEntries();
    final toDelete = entries.where((e) => e.plantId == plantId).toList();
    for (final entry in toDelete) {
      final photoFile = File(entry.uri);
      if (photoFile.existsSync()) photoFile.deleteSync();
      final thumbFile = File(entry.thumbnailUri);
      if (thumbFile.existsSync()) thumbFile.deleteSync();
    }
    entries.removeWhere((e) => e.plantId == plantId);
    await _saveEntries(entries);
  }

  /// Get count of journal entries per plant.
  Future<Map<String, int>> getCounts() async {
    final entries = await _loadEntries();
    final counts = <String, int>{};
    for (final entry in entries) {
      counts[entry.plantId] = (counts[entry.plantId] ?? 0) + 1;
    }
    return counts;
  }

  // ─── Internal ────────────────────────────────────────────────

  Future<List<JournalEntry>> _loadEntries() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);
    if (raw == null) return [];
    final data = json.decode(raw) as Map<String, dynamic>;
    final list = (data['entries'] as List<dynamic>?) ?? [];
    return list.map((e) => JournalEntry.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> _saveEntries(List<JournalEntry> entries) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _storageKey,
      json.encode({'entries': entries.map((e) => e.toJson()).toList()}),
    );
  }
}

/// A journal photo entry.
class JournalEntry {
  final String id;
  final String plantId;
  final String uri;
  final String thumbnailUri;
  final String date;
  final String note;
  final int createdAt;

  const JournalEntry({
    required this.id,
    required this.plantId,
    required this.uri,
    required this.thumbnailUri,
    required this.date,
    required this.note,
    required this.createdAt,
  });

  factory JournalEntry.fromJson(Map<String, dynamic> json) => JournalEntry(
        id: json['id'] as String? ?? '',
        plantId: json['plantId'] as String? ?? '',
        uri: json['uri'] as String? ?? '',
        thumbnailUri: json['thumbnailUri'] as String? ?? '',
        date: json['date'] as String? ?? '',
        note: json['note'] as String? ?? '',
        createdAt: json['createdAt'] as int? ?? 0,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'plantId': plantId,
        'uri': uri,
        'thumbnailUri': thumbnailUri,
        'date': date,
        'note': note,
        'createdAt': createdAt,
      };
}
