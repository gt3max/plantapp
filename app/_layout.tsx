import { useEffect } from 'react';
import { Platform } from 'react-native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useAuthStore } from '../src/stores/auth-store';

export { ErrorBoundary } from 'expo-router';

SplashScreen.preventAutoHideAsync();

// Notifications only on native (crashes SSR/web due to localStorage)
if (Platform.OS !== 'web') {
  const { configureNotifications } = require('../src/lib/reminders');
  configureNotifications();
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, // 1 min (cloud polling is 60s)
      retry: 2,
    },
  },
});

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!isAuthenticated && !inAuthGroup) {
      router.replace('/(auth)/sign-in');
    } else if (isAuthenticated && inAuthGroup) {
      router.replace('/(tabs)');
    }
  }, [isAuthenticated, isLoading, segments]);

  return <>{children}</>;
}

export default function RootLayout() {
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    initialize().finally(() => {
      SplashScreen.hideAsync();
    });

    // Request notification permissions and reschedule existing reminders (native only)
    if (Platform.OS !== 'web') {
      const { requestNotificationPermissions, rescheduleAll } = require('../src/lib/reminders');
      requestNotificationPermissions().then((granted: boolean) => {
        if (granted) {
          rescheduleAll().catch(() => {
            // non-critical — reminders will be rescheduled next launch
          });
        }
      });
    }
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <AuthGuard>
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(auth)" />
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="plant/[id]" options={{ headerShown: true, title: 'Plant' }} />
            <Stack.Screen name="device/[id]" options={{ headerShown: true, title: 'Device' }} />
            <Stack.Screen
              name="settings"
              options={{ presentation: 'modal', headerShown: true, title: 'Settings' }}
            />
          </Stack>
          <StatusBar style="auto" />
        </AuthGuard>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
