import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../services/file_service.dart';
import '../services/image_edit_service.dart';
import '../services/svg_converter_service.dart';

class _Aspect {
  final String label;
  final double? ratio; // width / height, null = free
  final bool original;
  const _Aspect(this.label, this.ratio, {this.original = false});
}

const _aspects = [
  _Aspect('Free', null),
  _Aspect('Original', null, original: true),
  _Aspect('1:1', 1),
  _Aspect('4:3', 4 / 3),
  _Aspect('3:4', 3 / 4),
  _Aspect('16:9', 16 / 9),
  _Aspect('9:16', 9 / 16),
];

/// Crops a raster image and saves the result as a new PNG.
class CropScreen extends StatefulWidget {
  final String imagePath;
  const CropScreen({super.key, required this.imagePath});

  @override
  State<CropScreen> createState() => _CropScreenState();
}

class _CropScreenState extends State<CropScreen> {
  static const double _pad = 24;
  static const double _touchSlop = 32;

  ui.Image? _image;
  String? _error;
  bool _busy = false;

  /// Crop rectangle in image pixels.
  Rect _crop = Rect.zero;
  _Aspect _aspect = _aspects.first;

  // Layout of the image on screen (set while building).
  Rect _imageRect = Rect.zero;
  double _scale = 1;

  // Which parts the current drag is moving.
  bool _dragL = false, _dragT = false, _dragR = false, _dragB = false, _dragMove = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _image?.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final img = await ImageEditService.instance.decode(widget.imagePath);
      if (!mounted) {
        img.dispose();
        return;
      }
      setState(() {
        _image = img;
        _crop = Rect.fromLTWH(0, 0, img.width.toDouble(), img.height.toDouble());
      });
    } catch (e) {
      if (mounted) setState(() => _error = 'This image can\'t be opened for cropping.');
    }
  }

  double get _minSide => math.min(16.0, math.min(_image!.width, _image!.height).toDouble());

  double? get _ratio {
    if (_aspect.original) return _image!.width / _image!.height;
    return _aspect.ratio;
  }

  static double _clamp(double v, double lo, double hi) => v < lo ? lo : (v > hi ? hi : v);

  Rect _toScreen(Rect r) => Rect.fromLTRB(
    _imageRect.left + r.left * _scale,
    _imageRect.top + r.top * _scale,
    _imageRect.left + r.right * _scale,
    _imageRect.top + r.bottom * _scale,
  );

  void _onPanStart(DragStartDetails d) {
    final p = d.localPosition;
    final sr = _toScreen(_crop);
    final dl = (p.dx - sr.left).abs(), dr = (p.dx - sr.right).abs();
    final dt = (p.dy - sr.top).abs(), db = (p.dy - sr.bottom).abs();
    final inX = p.dx >= sr.left - _touchSlop && p.dx <= sr.right + _touchSlop;
    final inY = p.dy >= sr.top - _touchSlop && p.dy <= sr.bottom + _touchSlop;

    _dragL = dl < _touchSlop && dl <= dr && inY;
    _dragR = dr < _touchSlop && dr < dl && inY;
    _dragT = dt < _touchSlop && dt <= db && inX;
    _dragB = db < _touchSlop && db < dt && inX;
    _dragMove = !(_dragL || _dragR || _dragT || _dragB) && sr.contains(p);
  }

  void _onPanUpdate(DragUpdateDetails d) {
    final img = _image;
    if (img == null) return;
    final w = img.width.toDouble(), h = img.height.toDouble();
    final dx = d.delta.dx / _scale, dy = d.delta.dy / _scale;
    final r = _crop;
    Rect? next;

    if (_dragMove) {
      final l = _clamp(r.left + dx, 0, w - r.width);
      final t = _clamp(r.top + dy, 0, h - r.height);
      next = Rect.fromLTWH(l, t, r.width, r.height);
    } else if (_dragL || _dragR || _dragT || _dragB) {
      var l = r.left, t = r.top, rt = r.right, b = r.bottom;
      final m = _minSide;
      if (_dragL) l = _clamp(l + dx, 0, rt - m);
      if (_dragR) rt = _clamp(rt + dx, l + m, w);
      if (_dragT) t = _clamp(t + dy, 0, b - m);
      if (_dragB) b = _clamp(b + dy, t + m, h);
      next = Rect.fromLTRB(l, t, rt, b);
      final ratio = _ratio;
      if (ratio != null) next = _applyRatio(next, ratio);
    }

    if (next != null && next != _crop) setState(() => _crop = next!);
  }

  /// Forces [r] to [ratio]; the side being dragged decides which dimension leads and
  /// the opposite side stays put. Returns null if the result would leave the image.
  Rect? _applyRatio(Rect r, double ratio) {
    final img = _image!;
    final horizontalLeads = _dragL || _dragR;
    var w = r.width, h = r.height;
    if (horizontalLeads) {
      h = w / ratio;
    } else {
      w = h * ratio;
    }

    final double l = _dragL ? r.right - w : (_dragR ? r.left : r.center.dx - w / 2);
    final double t = _dragT ? r.bottom - h : (_dragB ? r.top : r.center.dy - h / 2);
    final out = Rect.fromLTWH(l, t, w, h);

    const eps = 0.01;
    if (out.left < -eps ||
        out.top < -eps ||
        out.right > img.width + eps ||
        out.bottom > img.height + eps ||
        w < _minSide ||
        h < _minSide) {
      return null;
    }
    return out;
  }

  void _selectAspect(_Aspect a) {
    setState(() {
      _aspect = a;
      final ratio = _ratio;
      if (ratio == null) return;
      final iw = _image!.width.toDouble(), ih = _image!.height.toDouble();
      // Largest rectangle of this ratio that fits the image, centred on the current crop.
      final w = math.min(iw, ih * ratio);
      final h = w / ratio;
      final left = _clamp(_crop.center.dx - w / 2, 0, iw - w);
      final top = _clamp(_crop.center.dy - h / 2, 0, ih - h);
      _crop = Rect.fromLTWH(left, top, w, h);
    });
  }

  Future<void> _save() async {
    final img = _image;
    if (img == null || _busy) return;
    setState(() => _busy = true);
    final messenger = ScaffoldMessenger.of(context);
    final nav = Navigator.of(context);
    try {
      final bytes = await ImageEditService.instance.cropToPng(img, _crop);
      final base = FileService.instance.getBaseName(widget.imagePath);
      final saved = await SvgConverterService.instance.savePng(bytes, '${base}_cropped.png');
      if (saved == null) {
        if (mounted) setState(() => _busy = false); // cancelled the save dialog
        return;
      }
      nav.pop();
      messenger.showSnackBar(const SnackBar(content: Text('Saved cropped image')));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        messenger.showSnackBar(SnackBar(content: Text('Crop failed: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final img = _image;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('Crop'),
        actions: [
          if (_busy)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.check),
              tooltip: 'Save cropped image',
              onPressed: img == null ? null : _save,
            ),
        ],
      ),
      body: _error != null
          ? Center(child: Text(_error!, style: const TextStyle(color: Colors.white70)))
          : img == null
          ? const Center(child: CircularProgressIndicator())
          : Column(
        children: [
          Expanded(
            child: LayoutBuilder(
              builder: (context, c) {
                final availW = math.max(1.0, c.maxWidth - _pad * 2);
                final availH = math.max(1.0, c.maxHeight - _pad * 2);
                _scale = math.min(availW / img.width, availH / img.height);
                final w = img.width * _scale, h = img.height * _scale;
                _imageRect = Rect.fromLTWH(
                  _pad + (availW - w) / 2,
                  _pad + (availH - h) / 2,
                  w,
                  h,
                );
                return GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onPanStart: _onPanStart,
                  onPanUpdate: _onPanUpdate,
                  child: CustomPaint(
                    size: Size.infinite,
                    painter: _CropPainter(
                      image: img,
                      imageRect: _imageRect,
                      crop: _toScreen(_crop),
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${_crop.width.round()} × ${_crop.height.round()} px',
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 44,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    children: [
                      for (final a in _aspects)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: ChoiceChip(
                            label: Text(a.label),
                            selected: _aspect == a,
                            onSelected: _busy ? null : (_) => _selectAspect(a),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CropPainter extends CustomPainter {
  final ui.Image image;
  final Rect imageRect; // where the image sits on screen
  final Rect crop; // crop box on screen

  _CropPainter({required this.image, required this.imageRect, required this.crop});

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawImageRect(
      image,
      Rect.fromLTWH(0, 0, image.width.toDouble(), image.height.toDouble()),
      imageRect,
      Paint()..filterQuality = FilterQuality.medium,
    );

    // Dim everything outside the crop box.
    final dim = Path()
      ..fillType = PathFillType.evenOdd
      ..addRect(imageRect)
      ..addRect(crop);
    canvas.drawPath(dim, Paint()..color = const Color(0x99000000));

    // Rule-of-thirds grid.
    final grid = Paint()
      ..color = Colors.white38
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    for (var i = 1; i <= 2; i++) {
      final x = crop.left + crop.width * i / 3;
      final y = crop.top + crop.height * i / 3;
      canvas.drawLine(Offset(x, crop.top), Offset(x, crop.bottom), grid);
      canvas.drawLine(Offset(crop.left, y), Offset(crop.right, y), grid);
    }

    canvas.drawRect(
      crop,
      Paint()
        ..color = Colors.white
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke,
    );

    // Corner brackets + edge bars as grab handles.
    final handle = Paint()
      ..color = Colors.white
      ..strokeWidth = 4
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.square;
    final len = math.min(24.0, math.min(crop.width, crop.height) / 3);
    final l = crop.left, t = crop.top, r = crop.right, b = crop.bottom;

    canvas.drawPath(
      Path()
        ..moveTo(l, t + len)..lineTo(l, t)..lineTo(l + len, t)
        ..moveTo(r - len, t)..lineTo(r, t)..lineTo(r, t + len)
        ..moveTo(l, b - len)..lineTo(l, b)..lineTo(l + len, b)
        ..moveTo(r - len, b)..lineTo(r, b)..lineTo(r, b - len),
      handle,
    );

    final bar = len / 2;
    canvas.drawLine(Offset(crop.center.dx - bar, t), Offset(crop.center.dx + bar, t), handle);
    canvas.drawLine(Offset(crop.center.dx - bar, b), Offset(crop.center.dx + bar, b), handle);
    canvas.drawLine(Offset(l, crop.center.dy - bar), Offset(l, crop.center.dy + bar), handle);
    canvas.drawLine(Offset(r, crop.center.dy - bar), Offset(r, crop.center.dy + bar), handle);
  }

  @override
  bool shouldRepaint(_CropPainter old) =>
      old.crop != crop || old.imageRect != imageRect || old.image != image;
}
