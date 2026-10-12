import 'package:flutter/material.dart';
import '../services/file_service.dart';
import '../services/svg_converter_service.dart';

/// Shows the "Convert to PNG" dialog for an SVG file and saves the result.
Future<void> showSvgToPngDialog(BuildContext context, String svgPath) {
  return showDialog(
    context: context,
    builder: (_) => _SvgToPngDialog(svgPath: svgPath),
  );
}

enum _Bg { transparent, white, black }

class _SvgToPngDialog extends StatefulWidget {
  final String svgPath;
  const _SvgToPngDialog({required this.svgPath});

  @override
  State<_SvgToPngDialog> createState() => _SvgToPngDialogState();
}

class _SvgToPngDialogState extends State<_SvgToPngDialog> {
  static const _scales = [1.0, 2.0, 3.0, 4.0];

  Size? _size;
  double _scale = 2;
  _Bg _bg = _Bg.transparent;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    SvgConverterService.instance
        .getSvgSize(widget.svgPath)
        .then((s) {
      if (mounted) setState(() => _size = s);
    }).catchError((e) {
      if (mounted) setState(() => _error = 'Could not read this SVG');
    });
  }

  Color? get _bgColor => switch (_bg) {
    _Bg.transparent => null,
    _Bg.white => Colors.white,
    _Bg.black => Colors.black,
  };

  String get _outputSizeLabel {
    final s = _size;
    if (s == null) return '…';
    final max = SvgConverterService.maxDimension;
    final w = (s.width * _scale).round().clamp(1, max);
    final h = (s.height * _scale).round().clamp(1, max);
    return '$w × $h px';
  }

  Future<void> _convert() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final messenger = ScaffoldMessenger.of(context);
    final nav = Navigator.of(context);
    try {
      final bytes = await SvgConverterService.instance
          .toPngBytes(widget.svgPath, scale: _scale, background: _bgColor);

      final base = FileService.instance.getFileName(widget.svgPath).replaceAll(RegExp(r'\.svg$', caseSensitive: false), '');
      final saved = await SvgConverterService.instance.savePng(bytes, '$base.png');

      if (saved == null) {
        if (mounted) setState(() => _busy = false); // user cancelled the save dialog
        return;
      }
      nav.pop();
      messenger.showSnackBar(const SnackBar(content: Text('Saved PNG')));
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = 'Conversion failed: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Convert to PNG'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Scale', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final s in _scales)
                ChoiceChip(
                  label: Text('${s.toInt()}x'),
                  selected: _scale == s,
                  onSelected: _busy ? null : (_) => setState(() => _scale = s),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text('Background', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          SegmentedButton<_Bg>(
            segments: const [
              ButtonSegment(value: _Bg.transparent, label: Text('Clear')),
              ButtonSegment(value: _Bg.white, label: Text('White')),
              ButtonSegment(value: _Bg.black, label: Text('Black')),
            ],
            selected: {_bg},
            onSelectionChanged: _busy ? null : (v) => setState(() => _bg = v.first),
          ),
          const SizedBox(height: 16),
          Text('Output: $_outputSizeLabel'),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: (_busy || _size == null) ? null : _convert,
          child: _busy
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Convert'),
        ),
      ],
    );
  }
}
