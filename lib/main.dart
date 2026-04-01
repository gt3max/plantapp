import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/app/router.dart';
import 'package:plantapp/stores/auth_store.dart';
import 'package:plantapp/services/reminder_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Prevent crashes from rendering errors — show red error box instead of crash
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return Material(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Something went wrong',
            style: TextStyle(color: Colors.red[300], fontSize: 14),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  };

  runApp(const ProviderScope(child: PlantApp()));
}

class PlantApp extends ConsumerStatefulWidget {
  const PlantApp({super.key});

  @override
  ConsumerState<PlantApp> createState() => _PlantAppState();
}

class _PlantAppState extends ConsumerState<PlantApp> {
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      await ref.read(authProvider.notifier).initialize();
      // Initialize reminders (non-blocking)
      ReminderService.instance.initialize().then((_) {
        ReminderService.instance.rescheduleAll();
      });
    } catch (e) {
      // Auth init failed — will show sign-in screen
    }
    if (mounted) {
      setState(() => _initialized = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return MaterialApp(
        home: Scaffold(
          backgroundColor: AppColors.background,
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.eco, size: 64, color: AppColors.primary),
                const SizedBox(height: 16),
                CircularProgressIndicator(color: AppColors.primary),
              ],
            ),
          ),
        ),
        debugShowCheckedModeBanner: false,
      );
    }

    final router = buildRouter(ref);

    return MaterialApp.router(
      title: 'PlantApp',
      theme: buildAppTheme(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
