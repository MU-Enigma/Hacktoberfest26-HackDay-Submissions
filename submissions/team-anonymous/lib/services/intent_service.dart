import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import '../utils/constants.dart';

/// Single owner of the "app was asked to open a file" flow.
///
/// - Android cold start: pulls the path once via `getSharedData`.
/// - Android warm start: Kotlin pushes `onNewFile` from `onNewIntent`.
/// - Windows/desktop: file path arrives as a command-line argument ("Open with").
///
/// Only this class may call `getSharedData`: the native side clears the value after
/// the first read, so a second caller would always get null.
class IntentService {
  static final IntentService instance = IntentService._();
  IntentService._();

  static const MethodChannel _channel = MethodChannel('app.channel.shared.data');

  final StreamController<String> _controller = StreamController<String>.broadcast();
  String? _pending;

  /// Paths opened while the app is running.
  Stream<String> get onFile => _controller.stream;

  /// A path that arrived before any screen was listening. Returns it once.
  String? takePending() {
    final p = _pending;
    _pending = null;
    return p;
  }

  Future<void> init(List<String> args) async {
    if (Platform.isAndroid) {
      _channel.setMethodCallHandler((call) async {
        if (call.method == 'onNewFile') {
          _deliver(call.arguments as String?);
        }
        return null;
      });
      try {
        _deliver(await _channel.invokeMethod<String>('getSharedData'));
      } catch (e) {
        debugPrint('Error reading launch intent: $e');
      }
    } else {
      for (final arg in args) {
        final ext = arg.split('.').last.toLowerCase();
        if (AppConstants.supportedExtensions.contains(ext) && File(arg).existsSync()) {
          _deliver(arg);
          break;
        }
      }
    }
  }

  void _deliver(String? path) {
    if (path == null || path.isEmpty) return;
    if (_controller.hasListener) {
      _controller.add(path);
    } else {
      _pending = path;
    }
  }
}
