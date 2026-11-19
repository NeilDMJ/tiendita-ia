import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { AvisoConexion } from '@/components/aviso-conexion';
import { colores, tipografia } from '@/theme';

export default function RootLayout() {
  const [clienteQuery] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1 }, mutations: { retry: 0 } } }),
  );

  return (
    <QueryClientProvider client={clienteQuery}>
      <SafeAreaProvider>
        <SafeAreaView edges={['top']} style={{ backgroundColor: colores.fondo }}>
          <AvisoConexion />
        </SafeAreaView>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerShadowVisible: false, // flat: sin sombra en encabezados
            headerStyle: { backgroundColor: colores.fondo },
            headerTintColor: colores.texto,
            headerTitleStyle: { fontSize: tipografia.etiqueta.fontSize, fontWeight: '700' },
            headerBackButtonDisplayMode: 'minimal',
            contentStyle: { backgroundColor: colores.fondo },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
