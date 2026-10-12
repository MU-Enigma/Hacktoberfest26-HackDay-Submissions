import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:vector_graphics/vector_graphics.dart' show vg;

class SvgConverterService {
  static final SvgConverterService instance = SvgConverterService._();
  SvgConverterService._();

  /// GPU texture limits make anything much larger than this unreliable.
  static const int maxDimension = 8192;
  static const double _fallbackSize = 512;

  /// Intrinsic size of the SVG (from width/height or viewBox).
  Future<Size> getSvgSize(String svgPath) async {
    final svg = await File(svgPath).readAsString();
    final info = await vg.loadPicture(SvgStringLoader(svg), null);
    try {
      return _sanitize(info.size);
    } finally {
      info.picture.dispose();
    }
  }

  /// Rasterises the SVG at [scale]x its intrinsic size. [background] null = transparent.
  Future<Uint8List> toPngBytes(
      String svgPath, {
        double scale = 1,
        Color? background,
      }) async {
    final svg = await File(svgPath).readAsString();
    final info = await vg.loadPicture(SvgStringLoader(svg), null);
    try {
      final size = _sanitize(info.size);
      final w = (size.width * scale).round().clamp(1, maxDimension);
      final h = (size.height * scale).round().clamp(1, maxDimension);

      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);
      if (background != null) {
        canvas.drawRect(
          Rect.fromLTWH(0, 0, w.toDouble(), h.toDouble()),
          Paint()..color = background,
        );
      }
      // Scale each axis independently so the clamp above can't leave a margin.
      canvas.scale(w / size.width, h / size.height);
      canvas.drawPicture(info.picture);

      final picture = recorder.endRecording();
      final image = await picture.toImage(w, h);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      picture.dispose();
      if (data == null) throw StateError('PNG encoding returned no data');
      return data.buffer.asUint8List();
    } finally {
      info.picture.dispose();
    }
  }

  /// Asks the user where to save and writes the PNG. Returns the saved path/URI, or null if cancelled.
  Future<String?> savePng(Uint8List bytes, String suggestedName) async {
    final mobile = Platform.isAndroid || Platform.isIOS;
    final out = await FilePicker.platform.saveFile(
      dialogTitle: 'Save PNG',
      fileName: suggestedName,
      type: FileType.custom,
      allowedExtensions: const ['png'],
      bytes: mobile ? bytes : null, // mobile pickers write the bytes themselves
    );
    if (out == null) return null;
    if (mobile) return out;

    // Desktop: the dialog only returns a path, we write the file.
    final path = out.toLowerCase().endsWith('.png') ? out : '$out.png';
    await File(path).writeAsBytes(bytes, flush: true);
    return path;
  }

  Size _sanitize(Size s) {
    if (!s.width.isFinite || !s.height.isFinite || s.width <= 0 || s.height <= 0) {
      return const Size(_fallbackSize, _fallbackSize);
    }
    return s;
  }
}
