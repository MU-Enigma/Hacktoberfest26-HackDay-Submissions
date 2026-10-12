import 'package:flutter/material.dart';
import '../screens/crop_screen.dart';
import '../services/cache_service.dart';
import '../services/file_service.dart';

enum _EditAction { rename, crop }

/// Overflow menu with Rename and Crop. Crop is hidden for SVG (vector files can't be cropped
/// as pixels); Rename is hidden unless the host passes [onRenamed] so it can follow the new path.
class ImageEditMenu extends StatelessWidget {
  final String imagePath;
  final ValueChanged<String>? onRenamed;
  final Color? iconColor;

  const ImageEditMenu({
    super.key,
    required this.imagePath,
    this.onRenamed,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    final canCrop = !FileService.instance.isSvgFile(imagePath);
    final canRename = onRenamed != null;
    if (!canCrop && !canRename) return const SizedBox.shrink();

    return PopupMenuButton<_EditAction>(
      icon: Icon(Icons.more_vert, color: iconColor),
      tooltip: 'Edit',
      onSelected: (action) {
        switch (action) {
          case _EditAction.rename:
            _rename(context);
          case _EditAction.crop:
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => CropScreen(imagePath: imagePath)),
            );
        }
      },
      itemBuilder: (_) => [
        if (canRename)
          const PopupMenuItem(
            value: _EditAction.rename,
            child: _MenuRow(Icons.drive_file_rename_outline, 'Rename'),
          ),
        if (canCrop)
          const PopupMenuItem(
            value: _EditAction.crop,
            child: _MenuRow(Icons.crop, 'Crop'),
          ),
      ],
    );
  }

  Future<void> _rename(BuildContext context) async {
    final newPath = await showDialog<String>(
      context: context,
      builder: (_) => _RenameDialog(path: imagePath),
    );
    if (newPath != null && newPath != imagePath) onRenamed?.call(newPath);
  }
}

class _MenuRow extends StatelessWidget {
  final IconData icon;
  final String label;
  const _MenuRow(this.icon, this.label);

  @override
  Widget build(BuildContext context) => Row(
    children: [Icon(icon, size: 20), const SizedBox(width: 12), Text(label)],
  );
}

class _RenameDialog extends StatefulWidget {
  final String path;
  const _RenameDialog({required this.path});

  @override
  State<_RenameDialog> createState() => _RenameDialogState();
}

class _RenameDialogState extends State<_RenameDialog> {
  late final TextEditingController _controller;
  late final String _ext;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final base = FileService.instance.getBaseName(widget.path);
    final name = FileService.instance.getFileName(widget.path);
    _ext = name.substring(base.length); // includes the dot, or empty
    _controller = TextEditingController(text: base)
      ..selection = TextSelection(baseOffset: 0, extentOffset: base.length);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final newPath = await FileService.instance.renameFile(widget.path, _controller.text);
      if (newPath != widget.path) {
        await CacheService.instance.renameOriginal(widget.path, newPath);
      }
      if (mounted) Navigator.of(context).pop(newPath);
    } on FormatException catch (e) {
      if (mounted) setState(() {
        _busy = false;
        _error = e.message;
      });
    } catch (e) {
      if (mounted) setState(() {
        _busy = false;
        _error = 'Could not rename: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Rename'),
      content: TextField(
        controller: _controller,
        autofocus: true,
        enabled: !_busy,
        textInputAction: TextInputAction.done,
        onSubmitted: (_) => _submit(),
        decoration: InputDecoration(
          suffixText: _ext,
          errorText: _error,
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: const Text('Rename'),
        ),
      ],
    );
  }
}
