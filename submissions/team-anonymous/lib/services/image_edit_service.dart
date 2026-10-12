import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';

class ImageEditService {
  static final ImageEditService instance = ImageEditService._();
  ImageEditService._();

  /// Decodes a raster image (first frame for animated formats).
  /// The caller owns the returned image and must dispose it.
  Future<ui.Image> decode(String path) async {
    final bytes = await File(path).readAsBytes();
    final codec = await ui.instantiateImageCodec(bytes);
    try {
      final frame = await codec.getNextFrame();
      return frame.image;
    } finally {
      codec.dispose();
    }
  }

  /// Crops [region] (in image pixels) out of [image] and encodes it as PNG.
  Future<Uint8List> cropToPng(ui.Image image, Rect region) async {
    final bounds = Rect.fromLTWH(0, 0, image.width.toDouble(), image.height.toDouble());
    final src = Rect.fromLTRB(
      region.left.floorToDouble(),
      region.top.floorToDouble(),
      region.right.ceilToDouble(),
      region.bottom.ceilToDouble(),
    ).intersect(bounds);
    final w = src.width.round();
    final h = src.height.round();
    if (w < 1 || h < 1) throw StateError('Crop area is empty');

    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    canvas.drawImageRect(image, src, Rect.fromLTWH(0, 0, w.toDouble(), h.toDouble()), Paint());
    final picture = recorder.endRecording();
    final out = await picture.toImage(w, h);
    try {
      final data = await out.toByteData(format: ui.ImageByteFormat.png);
      if (data == null) throw StateError('PNG encoding returned no data');
      return data.buffer.asUint8List();
    } finally {
      out.dispose();
      picture.dispose();
    }
  }
}
