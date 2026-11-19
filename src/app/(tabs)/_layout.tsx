import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router/tabs';
import type { ComponentProps } from 'react';
import type { ColorValue } from 'react-native';

import { bordes, colores, tipografia } from '@/theme';

type NombreIcono = ComponentProps<typeof MaterialCommunityIcons>['name'];

function icono(nombre: NombreIcono) {
  function IconoPestana({ color }: { color: ColorValue }) {
    return <MaterialCommunityIcons name={nombre} size={28} color={typeof color === "string" ? color : undefined} />;
  }
  return IconoPestana;
}

/** Barra inferior fija: máximo 4 destinos, icono + etiqueta siempre (Nielsen #4). */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShadowVisible: false,
        headerStyle: { backgroundColor: colores.fondo, borderBottomWidth: bordes.fino, borderBottomColor: colores.divisor },
        headerTitleStyle: { ...tipografia.etiqueta, fontSize: 20, color: colores.texto },
        tabBarActiveTintColor: colores.acento,
        tabBarInactiveTintColor: colores.textoSecundario,
        tabBarLabelStyle: { fontSize: 14, fontWeight: '700' },
        tabBarStyle: {
          backgroundColor: colores.fondo,
          borderTopWidth: bordes.grueso,
          borderTopColor: colores.texto,
          elevation: 0, // flat
          shadowOpacity: 0, // flat
          minHeight: 64,
        },
        tabBarItemStyle: { minHeight: 56 },
        sceneStyle: { backgroundColor: colores.fondo },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: icono('home-outline') }} />
      <Tabs.Screen name="cobrar" options={{ title: 'Cobrar', tabBarIcon: icono('cash-register') }} />
      <Tabs.Screen name="inventario" options={{ title: 'Inventario', tabBarIcon: icono('package-variant-closed') }} />
      <Tabs.Screen name="asistente" options={{ title: 'Asistente', tabBarIcon: icono('chat-outline') }} />
    </Tabs>
  );
}
