import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/app/router.dart';
import 'package:plantapp/stores/auth_store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: PlantApp()));
}

class PlantApp extends ConsumerStatefulWidget {
  const PlantApp({super.key});

  @override
  ConsumerState<PlantApp> createState() => _PlantAppState();
}

class _PlantAppState extends ConsumerState<PlantApp> {
  @override
  void initState() {
    super.initState();
    // Initialize auth (load tokens from secure storage)
    Future.microtask(() {
      ref.read(authProvider.notifier).initialize();
    });
  }

  @override
  Widget build(BuildContext context) {
    final router = buildRouter(ref);

    return MaterialApp.router(
      title: 'PlantApp',
      theme: buildAppTheme(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
