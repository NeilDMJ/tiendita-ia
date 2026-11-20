import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { AvisoConexion } from '@/components/aviso-conexion';
import { ProveedorCarrito } from '@/estado/carrito';
import { useAccesibilidad } from '@/hooks/use-accesibilidad';
import { useSincronizarCola } from '@/hooks/use-sincronizar-cola';
import { color, type } from '@/theme';

function SincronizadorCola() {
  useSincronizarCola();
  return null;
}

export default function RootLayout() {
  const [clienteQuery] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1 }, mutations: { retry: 0 } } }),
  );
  const { reducirMovimiento } = useAccesibilidad();

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
              headerTitleStyle: { fontSize: type.titleLarge.fontSize, fontWeight: type.titleLarge.fontWeight },
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
