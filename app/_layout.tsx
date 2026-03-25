import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useAuthStore } from '../src/stores/auth-store';
import {
  configureNotifications,
  requestNotificationPermissions,
  rescheduleAll,
} from '../src/lib/reminders';

export { ErrorBoundary } from 'expo-router';

SplashScreen.preventAutoHideAsync();

// Configure notification handler at module level (before any scheduling)
configureNotifications();

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

    // Request notification permissions and reschedule existing reminders
    requestNotificationPermissions().then((granted) => {
      if (granted) {
        rescheduleAll().catch(() => {
          // non-critical — reminders will be rescheduled next launch
        });
      }
    });
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
