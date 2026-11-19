import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router/tabs';
import { StyleSheet, View, type ColorValue } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, colores, espacio, iconos, medidas, tactil, tipografia } from '@/theme';

/**
 * Icono de pestaña: relleno cuando está activa + barra superior 2px.
 * Así la pestaña activa no se distingue solo por color.
 */
function icono(inactivo: NombreIcono, activo: NombreIcono) {
  function IconoPestana({ color, focused }: { color: ColorValue; focused: boolean }) {
    return (
      <View style={estilos.contenedorIcono}>
        <View style={[estilos.barraActiva, focused && estilos.barraActivaVisible]} />
        <MaterialCommunityIcons
          name={focused ? activo : inactivo}
          size={iconos.pestana}
          color={typeof color === 'string' ? color : undefined}
        />
      </View>
    );
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
        headerTitleStyle: { ...tipografia.subtitulo, color: colores.texto },
        tabBarActiveTintColor: colores.acento,
        tabBarInactiveTintColor: colores.textoSecundario,
        tabBarLabelStyle: { fontSize: tipografia.etiqueta.fontSize, fontWeight: '700' },
        tabBarAllowFontScaling: true,
        tabBarIconStyle: estilos.areaIcono,
        tabBarStyle: {
          backgroundColor: colores.fondo,
          borderTopWidth: bordes.grueso,
          borderTopColor: colores.texto,
          elevation: 0, // flat
          shadowOpacity: 0, // flat
          minHeight: medidas.barraPestanas,
        },
        tabBarItemStyle: { minHeight: tactil.principal },
        sceneStyle: { backgroundColor: colores.fondo },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: icono('home-outline', 'home') }} />
      <Tabs.Screen name="cobrar" options={{ title: 'Cobrar', tabBarIcon: icono('cash-register', 'cash-register') }} />
      <Tabs.Screen
        name="inventario"
        options={{ title: 'Inventario', tabBarIcon: icono('package-variant-closed', 'package-variant') }}
      />
      <Tabs.Screen name="asistente" options={{ title: 'Asistente', tabBarIcon: icono('chat-outline', 'chat') }} />
    </Tabs>
  );
}

const estilos = StyleSheet.create({
  areaIcono: { minHeight: iconos.pestana + bordes.grueso + espacio.xs, minWidth: iconos.pestana + espacio.l },
  contenedorIcono: { alignItems: 'center', gap: espacio.xs },
  barraActiva: { height: bordes.grueso, width: iconos.pestana + espacio.l, backgroundColor: 'transparent' },
  barraActivaVisible: { backgroundColor: colores.acento },
});
