import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router/tabs';
import type { ColorValue } from 'react-native';

import { BarraNavegacion } from '@/components/barra-navegacion';
import type { NombreIcono } from '@/constants';
import { color, iconos, type } from '@/theme';

/** Icono de destino: relleno cuando está activo (una de las 3 señales no cromáticas de M3). */
function icono(inactivo: NombreIcono, activo: NombreIcono) {
  function IconoDestino({ color: tinte, focused }: { color: ColorValue; focused: boolean }) {
    return (
      <MaterialCommunityIcons
        name={focused ? activo : inactivo}
        size={iconos.linea}
        color={typeof tinte === 'string' ? tinte : undefined}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
    );
  }
  return IconoDestino;
}

/** M3 Navigation bar fija: 4 destinos, icono + etiqueta siempre (00-sistema §9.14). */
export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <BarraNavegacion {...props} />}
      screenOptions={{
        headerShadowVisible: false, // separación tonal, no sombra (M3 top app bar)
        headerStyle: { backgroundColor: color.surface },
        headerTitleStyle: { ...type.titleLarge, color: color.onSurface },
        headerTintColor: color.onSurface,
        tabBarAllowFontScaling: true,
        // La barra se oculta con el teclado (chat del asistente: el compositor queda pegado al teclado).
        tabBarHideOnKeyboard: true,
        sceneStyle: { backgroundColor: color.surface },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: icono('home-outline', 'home') }} />
      <Tabs.Screen name="cobrar" options={{ title: 'Cobrar', tabBarIcon: icono('point-of-sale', 'cash-register') }} />
      <Tabs.Screen
        name="inventario"
        options={{ title: 'Inventario', tabBarIcon: icono('package-variant-closed', 'package-variant') }}
      />
      <Tabs.Screen name="asistente" options={{ title: 'Asistente', tabBarIcon: icono('chat-outline', 'chat') }} />
    </Tabs>
  );
}
