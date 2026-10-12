import 'dart:async';
import 'package:flutter/material.dart';
import '../widgets/app_drawer.dart';
import '../widgets/theme_toggle_button.dart';
import '../widgets/image_viewer.dart';
import '../widgets/svg_to_png_dialog.dart';
import '../widgets/image_edit_menu.dart';
import '../services/intent_service.dart';
import '../services/file_service.dart';
import '../services/cache_service.dart';
import '../utils/constants.dart';
import 'image_view_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _currentImagePath;
  String _currentImageName = 'No image selected';
  bool _isLoading = false;
  StreamSubscription<String>? _intentSub;

  @override
  void initState() {
    super.initState();

    // File that launched the app (cold start) - may have arrived before this screen existed.
    final pending = IntentService.instance.takePending();
    if (pending != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _loadImage(pending);
      });
    }

    // Files opened while the app is already running ("Open with" on a warm app).
    _intentSub = IntentService.instance.onFile.listen((path) {
      if (mounted) _loadImage(path);
    });
  }

  @override
  void dispose() {
    _intentSub?.cancel();
    super.dispose();
  }

  Future<void> _loadImage(String imagePath) async {
    if (!await FileService.instance.fileExists(imagePath)) {
      if (mounted) {
        _showErrorSnackBar('File not found or cannot be accessed');
      }
      return;
    }
    if (!mounted) return;

    setState(() {
      _isLoading = true;
    });

    try {
      // Add to cache if enabled
      await CacheService.instance.addToCache(imagePath);
      if (!mounted) return;

      setState(() {
        _currentImagePath = imagePath;
        _currentImageName = FileService.instance.getFileName(imagePath);
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      _showErrorSnackBar('Error loading image: ${e.toString()}');
    }
  }

  Future<void> _pickImage() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final imagePath = await FileService.instance.pickImageFile();

      if (imagePath != null) {
        await _loadImage(imagePath);
      } else if (mounted) {
        setState(() {
          _isLoading = false;
        });
        _showErrorSnackBar('No image selected or permission denied');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      _showErrorSnackBar('Error selecting image: ${e.toString()}');
    }
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
        action: SnackBarAction(
          label: 'Dismiss',
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }

  void _onRenamed(String newPath) {
    setState(() {
      _currentImagePath = newPath;
      _currentImageName = FileService.instance.getFileName(newPath);
    });
  }

  void _navigateToFullScreen() {
    if (_currentImagePath != null) {
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => ImageViewScreen(
            imagePath: _currentImagePath!,
            imageName: _currentImageName,
            onRenamed: _onRenamed,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _currentImageName,
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
        leading: Builder(
          builder: (context) => IconButton(
            icon: const Icon(Icons.menu),
            onPressed: () => Scaffold.of(context).openDrawer(),
          ),
        ),
        actions: [
          if (_currentImagePath != null &&
              FileService.instance.isSvgFile(_currentImagePath!))
            IconButton(
              icon: const Icon(Icons.transform),
              tooltip: 'Convert to PNG',
              onPressed: () => showSvgToPngDialog(context, _currentImagePath!),
            ),
          if (_currentImagePath != null)
            ImageEditMenu(
              key: ValueKey(_currentImagePath),
              imagePath: _currentImagePath!,
              onRenamed: _onRenamed,
            ),
          const ThemeToggleButton(),
          const SizedBox(width: 8),
        ],
        elevation: Theme.of(context).appBarTheme.elevation,
      ),
      drawer: AppDrawer(onOpenImage: _pickImage),
      body: _isLoading
          ? const Center(
        child: CircularProgressIndicator(),
      )
          : _currentImagePath == null
          ? _buildEmptyState()
          : _buildImageView(),
      floatingActionButton: AnimatedScale(
        scale: _isLoading ? 0.8 : 1.0,
        duration: const Duration(milliseconds: 200),
        child: FloatingActionButton(
          onPressed: _isLoading ? null : _pickImage,
          tooltip: 'Open Image',
          child: _isLoading
              ? const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
            ),
          )
              : const Icon(Icons.add),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TweenAnimationBuilder(
            tween: Tween<double>(begin: 0, end: 1),
            duration: const Duration(milliseconds: 800),
            builder: (context, double value, child) {
              return Transform.scale(
                scale: value,
                child: Opacity(
                  opacity: value,
                  child: Icon(
                    Icons.image_outlined,
                    size: 120,
                    color: Theme.of(context).colorScheme.primary.withOpacity(0.4),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 24),
          TweenAnimationBuilder(
            tween: Tween<double>(begin: 0, end: 1),
            duration: const Duration(milliseconds: 1000),
            builder: (context, double value, child) {
              return Opacity(
                opacity: value,
                child: Text(
                  'No image selected',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.8),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 12),
          TweenAnimationBuilder(
            tween: Tween<double>(begin: 0, end: 1),
            duration: const Duration(milliseconds: 1200),
            builder: (context, double value, child) {
              return Opacity(
                opacity: value,
                child: Text(
                  'Tap the + button to open an image',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 32),
          TweenAnimationBuilder(
            tween: Tween<double>(begin: 0, end: 1),
            duration: const Duration(milliseconds: 1400),
            builder: (context, double value, child) {
              return Transform.translate(
                offset: Offset(0, 20 * (1 - value)),
                child: Opacity(
                  opacity: value,
                  child: FilledButton.icon(
                    onPressed: _pickImage,
                    icon: const Icon(Icons.folder_open),
                    label: const Text('Browse Images'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildImageView() {
    return GestureDetector(
      onTap: _navigateToFullScreen,
      child: Container(
        width: double.infinity,
        height: double.infinity,
        padding: const EdgeInsets.all(AppConstants.defaultPadding),
        child: Hero(
          tag: 'image_${_currentImagePath.hashCode}',
          child: ImageViewer(
            imagePath: _currentImagePath!,
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}