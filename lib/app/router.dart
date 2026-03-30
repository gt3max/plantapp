import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/screens/auth/sign_in_screen.dart';
import 'package:plantapp/screens/auth/register_screen.dart';
import 'package:plantapp/screens/tabs/plants_screen.dart';
import 'package:plantapp/screens/tabs/library_screen.dart';
import 'package:plantapp/screens/tabs/doctor_screen.dart';
import 'package:plantapp/screens/tabs/fleet_screen.dart';
import 'package:plantapp/screens/settings_screen.dart';
import 'package:plantapp/stores/auth_store.dart';

/// App router with auth guard and bottom tab navigation.
GoRouter buildRouter(WidgetRef ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final isAuth = authState.status == AuthStatus.authenticated;
      final isLoading = authState.status == AuthStatus.loading;
      final isAuthRoute = state.matchedLocation == '/sign-in' ||
          state.matchedLocation == '/register';

      // Still loading — don't redirect
      if (isLoading) return null;

      // Not authenticated and not on auth route → go to sign-in
      if (!isAuth && !isAuthRoute) return '/sign-in';

      // Authenticated but on auth route → go to home
      if (isAuth && isAuthRoute) return '/';

      return null;
    },
    routes: [
      // Auth routes
      GoRoute(
        path: '/sign-in',
        builder: (context, state) => const SignInScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),

      // Main app with bottom tabs
      ShellRoute(
        builder: (context, state, child) => _MainShell(child: child),
        routes: [
          GoRoute(
            path: '/',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: PlantsScreen(),
            ),
          ),
          GoRoute(
            path: '/library',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: LibraryScreen(),
            ),
          ),
          GoRoute(
            path: '/doctor',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: DoctorScreen(),
            ),
          ),
          GoRoute(
            path: '/fleet',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: FleetScreen(),
            ),
          ),
        ],
      ),

      // Settings (pushed on top, not in tabs)
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
    ],
  );
}

/// Main shell with bottom navigation bar
class _MainShell extends StatelessWidget {
  const _MainShell({required this.child});
  final Widget child;

  static const _tabs = [
    ('/', 'Plants', Icons.eco_outlined),
    ('/library', 'Library', Icons.local_library_outlined),
    ('/doctor', 'AI Doctor', Icons.medical_services_outlined),
    ('/fleet', 'Fleet', Icons.devices_outlined),
  ];

  @override
  Widget build(BuildContext context) {
    // Determine current tab index from location
    final location = GoRouterState.of(context).matchedLocation;
    int currentIndex = _tabs.indexWhere((t) => t.$1 == location);
    if (currentIndex < 0) currentIndex = 0;

    return Scaffold(
      appBar: AppBar(
        title: Text(_tabs[currentIndex].$2),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            color: AppColors.primary,
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: currentIndex,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: AppColors.tabIconDefault,
        onTap: (index) => context.go(_tabs[index].$1),
        items: _tabs
            .map((t) => BottomNavigationBarItem(
                  icon: Icon(t.$3),
                  label: t.$2,
                ))
            .toList(),
      ),
    );
  }
}
