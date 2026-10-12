import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:path_provider/path_provider.dart';
import '../models/cached_image.dart';
import '../utils/constants.dart';

class CacheService extends ChangeNotifier {
  static final CacheService _instance = CacheService._internal();
  static CacheService get instance => _instance;

  CacheService._internal();

  late SharedPreferences _prefs;
  late Directory _cacheDir;
  bool _cacheEnabled = true;
  List<CachedImage> _cachedImages = [];

  bool get cacheEnabled => _cacheEnabled;
  List<CachedImage> get cachedImages => List.unmodifiable(_cachedImages);
  int get cacheSize => _cachedImages.length;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    // Support dir, not the cache dir: Android may purge cache dirs at any time, which
    // silently emptied this cache. Our own folder inside it is only cleared by us.
    final base = await getApplicationSupportDirectory();
    _cacheDir = await Directory('${base.path}/image_cache').create(recursive: true);

    _cacheEnabled = _prefs.getBool(AppConstants.cacheEnabledKey) ?? true;
    await _loadCacheIndex();
  }

  Future<void> _loadCacheIndex() async {
    final cacheData = _prefs.getString(AppConstants.cacheKey);
    if (cacheData != null) {
      try {
        final List<dynamic> decoded = jsonDecode(cacheData);
        final all = decoded.map((item) => CachedImage.fromJson(item)).toList();
        _cachedImages =
            all.where((image) => File(image.cachePath).existsSync()).toList();
        if (_cachedImages.length != all.length) {
          await _saveCacheIndex(); // drop entries whose files are gone
        }
      } catch (e) {
        debugPrint('Error loading cache index: $e');
        _cachedImages = [];
      }
    }
  }

  Future<void> _saveCacheIndex() async {
    try {
      final encoded = jsonEncode(_cachedImages.map((e) => e.toJson()).toList());
      await _prefs.setString(AppConstants.cacheKey, encoded);
    } catch (e) {
      debugPrint('Error saving cache index: $e');
    }
  }

  Future<void> setCacheEnabled(bool enabled) async {
    _cacheEnabled = enabled;
    await _prefs.setBool(AppConstants.cacheEnabledKey, enabled);
    notifyListeners();

    if (!enabled) {
      await clearCache();
    }
  }

  Future<CachedImage?> getCachedImage(String filePath) async {
    if (!_cacheEnabled) return null;

    for (final image in _cachedImages) {
      if (image.originalPath == filePath) return image;
    }
    return null;
  }

  Future<void> addToCache(String filePath) async {
    if (!_cacheEnabled) return;

    try {
      final file = File(filePath);
      if (!file.existsSync()) return;

      // Check if already cached
      final existingIndex = _cachedImages.indexWhere(
            (image) => image.originalPath == filePath,
      );

      if (existingIndex != -1) {
        // Update access time and move to front; refresh the copy if the source changed
        var existing = _cachedImages[existingIndex];
        final length = await file.length();
        final cacheFile = File(existing.cachePath);
        if (!cacheFile.existsSync() || await cacheFile.length() != length) {
          await file.copy(existing.cachePath);
          existing = existing.copyWith(fileSize: length);
        }
        _cachedImages.removeAt(existingIndex);
        _cachedImages.insert(0, existing.copyWith(lastAccessed: DateTime.now()));
      } else {
        // Add new cached image
        final fileName = '${DateTime.now().millisecondsSinceEpoch}_${file.uri.pathSegments.last}';
        final cachePath = '${_cacheDir.path}/$fileName';

        await file.copy(cachePath);

        final cachedImage = CachedImage(
          originalPath: filePath,
          cachePath: cachePath,
          fileName: file.uri.pathSegments.last,
          fileSize: await file.length(),
          lastAccessed: DateTime.now(),
        );

        _cachedImages.insert(0, cachedImage);

        // Maintain cache size limit
        if (_cachedImages.length > AppConstants.maxCacheSize) {
          final toRemove = _cachedImages.sublist(AppConstants.maxCacheSize);
          _cachedImages = _cachedImages.sublist(0, AppConstants.maxCacheSize);

          // Delete excess cached files
          for (final image in toRemove) {
            try {
              await File(image.cachePath).delete();
            } catch (e) {
              debugPrint('Error deleting cached file: $e');
            }
          }
        }
      }

      await _saveCacheIndex();
      notifyListeners();
    } catch (e) {
      debugPrint('Error adding to cache: $e');
    }
  }

  /// Keeps the cache entry pointing at a file that was just renamed.
  Future<void> renameOriginal(String oldPath, String newPath) async {
    final i = _cachedImages.indexWhere((e) => e.originalPath == oldPath);
    if (i == -1) return;

    final entry = _cachedImages.removeAt(i);
    // A stale entry for the new name (an older file that used to live there) would be a duplicate.
    final clash = _cachedImages.indexWhere((e) => e.originalPath == newPath);
    if (clash != -1) {
      final stale = _cachedImages.removeAt(clash);
      try {
        await File(stale.cachePath).delete();
      } catch (e) {
        debugPrint('Error deleting cached file: $e');
      }
    }
    _cachedImages.insert(
      0,
      entry.copyWith(originalPath: newPath, fileName: File(newPath).uri.pathSegments.last),
    );
    await _saveCacheIndex();
    notifyListeners();
  }

  Future<void> removeFromCache(String filePath) async {
    final index = _cachedImages.indexWhere(
          (image) => image.originalPath == filePath,
    );

    if (index != -1) {
      final cachedImage = _cachedImages.removeAt(index);
      try {
        await File(cachedImage.cachePath).delete();
      } catch (e) {
        debugPrint('Error deleting cached file: $e');
      }

      await _saveCacheIndex();
      notifyListeners();
    }
  }

  Future<void> clearCache() async {
    for (final image in _cachedImages) {
      try {
        await File(image.cachePath).delete();
      } catch (e) {
        debugPrint('Error deleting cached file: $e');
      }
    }

    _cachedImages.clear();
    await _prefs.remove(AppConstants.cacheKey);
    notifyListeners();
  }

  String getCacheSizeString() {
    double totalSize = 0;
    for (final image in _cachedImages) {
      totalSize += image.fileSize;
    }

    if (totalSize < 1024) {
      return '${totalSize.toStringAsFixed(1)} B';
    } else if (totalSize < 1024 * 1024) {
      return '${(totalSize / 1024).toStringAsFixed(1)} KB';
    } else {
      return '${(totalSize / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
  }
}