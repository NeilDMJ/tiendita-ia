import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
  useFonts,
} from '@expo-google-fonts/inter';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { AvisoConexion } from '@/components/aviso-conexion';
import { ProveedorCarrito } from '@/estado/carrito';
import { useAccesibilidad } from '@/hooks/use-accesibilidad';
import { useSincronizarCola } from '@/hooks/use-sincronizar-cola';
import { color, fuente, type } from '@/theme';

function SincronizadorCola() {
  useSincronizarCola();
  return null;
}

export default function RootLayout() {
  const [clienteQuery] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1 }, mutations: { retry: 0 } } }),
  );
  const { reducirMovimiento } = useAccesibilidad();
  const [fuentesListas, errorFuentes] = useFonts({
    [fuente.regular]: Inter_400Regular,
    [fuente.medium]: Inter_500Medium,
    [fuente.semibold]: Inter_600SemiBold,
    [fuente.bold]: Inter_700Bold,
    [fuente.extrabold]: Inter_800ExtraBold,
  });

  // Si Inter no carga (error), la app sigue con la fuente del sistema en vez de quedarse en blanco.
  if (!fuentesListas && !errorFuentes) return null;

  return (
    <QueryClientProvider client={clienteQuery}>
      <ProveedorCarrito>
        <SincronizadorCola />
        <SafeAreaProvider>
          <SafeAreaView edges={['top']} style={{ backgroundColor: color.surface }}>
            <AvisoConexion />
          </SafeAreaView>
          <StatusBar style="dark" />
          <Stack
            screenOptions={{
              headerShadowVisible: false, // M3: la top app bar se separa por tono, no por sombra
              headerStyle: { backgroundColor: color.surface },
              headerTintColor: color.onSurface,
              headerTitleStyle: { fontSize: type.titleLarge.fontSize, fontFamily: type.titleLarge.fontFamily },
              headerBackButtonDisplayMode: 'minimal',
              contentStyle: { backgroundColor: color.surface },
              animation: reducirMovimiento ? 'none' : 'default',
            }}
          >
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen
              name="camara"
              options={{
                headerShown: false,
                animation: reducirMovimiento ? 'none' : 'slide_from_bottom',
                contentStyle: { backgroundColor: color.inverseSurface },
              }}
            />
            <Stack.Screen name="revision/[modo]" options={{ headerShown: false }} />
            <Stack.Screen name="venta/[id]" options={{ headerShown: false }} />
            <Stack.Screen name="historial" options={{ headerShown: false }} />
          </Stack>
        </SafeAreaProvider>
      </ProveedorCarrito>
    </QueryClientProvider>
  );
}
