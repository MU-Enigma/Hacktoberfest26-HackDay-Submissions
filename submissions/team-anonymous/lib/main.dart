import 'package:flutter/material.dart';
import 'services/theme_service.dart';
import 'services/cache_service.dart';
import 'services/intent_service.dart';
import 'screens/home_screen.dart';
import 'utils/constants.dart';

void main(List<String> args) async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize services
  await ThemeService.instance.init();
  await CacheService.instance.init();
  // Must be the only reader of the launch intent / command-line file (HomeScreen listens to it).
  await IntentService.instance.init(args);

  runApp(const SVGViewerApp());
}

class SVGViewerApp extends StatefulWidget {
  const SVGViewerApp({super.key});

  @override
  State<SVGViewerApp> createState() => _SVGViewerAppState();
}

class _SVGViewerAppState extends State<SVGViewerApp> {
  @override
  void initState() {
    super.initState();
    ThemeService.instance.addListener(_themeChanged);
  }

  @override
  void dispose() {
    ThemeService.instance.removeListener(_themeChanged);
    super.dispose();
  }

  void _themeChanged() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeService.instance.lightTheme,
      darkTheme: ThemeService.instance.darkTheme,
      themeMode: ThemeService.instance.themeMode,
      home: const HomeScreen(),
    );
  }
}