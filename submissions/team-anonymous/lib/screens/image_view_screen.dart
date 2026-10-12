import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:photo_view/photo_view.dart';
import '../widgets/image_viewer.dart';
import '../widgets/svg_to_png_dialog.dart';
import '../widgets/image_edit_menu.dart';
import '../services/file_service.dart';
import '../utils/constants.dart';

class ImageViewScreen extends StatefulWidget {
  final String imagePath;
  final String imageName;

  /// Called after the user renames the file here, so the screen that opened us can follow.
  /// When null, Rename is not offered (e.g. cached copies).
  final ValueChanged<String>? onRenamed;

  const ImageViewScreen({
    super.key,
    required this.imagePath,
    required this.imageName,
    this.onRenamed,
  });

  @override
  State<ImageViewScreen> createState() => _ImageViewScreenState();
}

class _ImageViewScreenState extends State<ImageViewScreen> {
  late String _path = widget.imagePath;
  late String _name = widget.imageName;
  bool _showAppBar = true;
  PhotoViewController? _photoViewController;

  @override
  void initState() {
    super.initState();
    _photoViewController = PhotoViewController();

    // Hide system UI for immersive experience
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  }

  @override
  void dispose() {
    _photoViewController?.dispose();
    // Restore system UI
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    super.dispose();
  }

  void _handleRenamed(String newPath) {
    setState(() {
      _path = newPath;
      _name = FileService.instance.getFileName(newPath);
    });
    widget.onRenamed?.call(newPath);
  }

  void _toggleAppBar() {
    setState(() {
      _showAppBar = !_showAppBar;
    });
  }

  void _showImageInfo() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _buildImageInfoSheet(),
    );
  }

  Widget _buildImageInfoSheet() {
    return DraggableScrollableSheet(
      initialChildSize: 0.5,
      minChildSize: 0.3,
      maxChildSize: 0.8,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          padding: const EdgeInsets.all(AppConstants.defaultPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              Text(
                'Image Information',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 16),

              Expanded(
                child: ListView(
                  controller: scrollController,
                  children: [
                    _buildInfoTile('Name', _name),
                    _buildInfoTile('Path', _path),
                    _buildInfoTile('Format', FileService.instance.getFileExtension(_path).toUpperCase()),
                    _buildInfoTile('Type', FileService.instance.isSvgFile(_path) ? 'Vector (SVG)' : 'Raster Image'),

                    FutureBuilder<int>(
                      future: FileService.instance.getFileSize(_path),
                      builder: (context, snapshot) {
                        if (snapshot.hasData) {
                          return _buildInfoTile('Size', FileService.instance.formatFileSize(snapshot.data!));
                        }
                        return _buildInfoTile('Size', 'Loading...');
                      },
                    ),

                    FutureBuilder<DateTime?>(
                      future: FileService.instance.getFileModificationDate(_path),
                      builder: (context, snapshot) {
                        if (snapshot.hasData && snapshot.data != null) {
                          final date = snapshot.data!;
                          final formatted = '${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
                          return _buildInfoTile('Modified', formatted);
                        }
                        return _buildInfoTile('Modified', 'Unknown');
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildInfoTile(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: _showAppBar
          ? AppBar(
        backgroundColor: Colors.black.withOpacity(0.5),
        elevation: 0,
        title: Text(
          _name,
          style: const TextStyle(color: Colors.white),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline, color: Colors.white),
            onPressed: _showImageInfo,
          ),
          if (FileService.instance.isSvgFile(_path))
            IconButton(
              icon: const Icon(Icons.transform, color: Colors.white),
              tooltip: 'Convert to PNG',
              onPressed: () => showSvgToPngDialog(context, _path),
            ),
          ImageEditMenu(
            key: ValueKey(_path),
            imagePath: _path,
            onRenamed: widget.onRenamed == null ? null : _handleRenamed,
            iconColor: Colors.white,
          ),
          const SizedBox(width: 8),
        ],
      )
          : null,
      body: GestureDetector(
        onTap: _toggleAppBar,
        child: Container(
          color: Colors.black,
          child: FileService.instance.isSvgFile(_path)
              ? PhotoView.customChild(
            controller: _photoViewController,
            backgroundDecoration: const BoxDecoration(color: Colors.black),
            minScale: PhotoViewComputedScale.contained,
            maxScale: PhotoViewComputedScale.covered * 4,
            child: Hero(
              tag: 'image_${_path.hashCode}',
              child: ImageViewer(
                imagePath: _path,
                fit: BoxFit.contain,
              ),
            ),
          )
              : PhotoView(
            controller: _photoViewController,
            imageProvider: FileImage(
              File(_path),
            ),
            backgroundDecoration: const BoxDecoration(color: Colors.black),
            minScale: PhotoViewComputedScale.contained,
            maxScale: PhotoViewComputedScale.covered * 4,
            heroAttributes: PhotoViewHeroAttributes(
              tag: 'image_${_path.hashCode}',
            ),
          ),
        ),
      ),
    );
  }
}