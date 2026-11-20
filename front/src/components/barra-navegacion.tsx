import type { BottomTabBarProps } from 'expo-router/tabs';
import { useEffect, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { anilloFoco, color, espacio, estado, iconos, medidas, motion, pesoActivo, shape, type } from '@/theme';

import { Tocable } from './tocable';

const [x1, y1, x2, y2] = motion.easing.standard;
const CURVA = Easing.bezier(x1, y1, x2, y2);

function Destino({
  etiqueta,
  etiquetaLector,
  activo,
  icono,
  badge,
  testID,
  onPress,
  onLongPress,
}: {
  etiqueta: string;
  etiquetaLector: string;
  activo: boolean;
  icono: ReactNode;
  badge?: string | number;
  testID?: string;
  onPress: () => void;
  onLongPress: () => void;
}) {
  const reducido = useReducedMotion();
  const progreso = useSharedValue(activo ? 1 : 0);

  useEffect(() => {
    progreso.value = withTiming(activo ? 1 : 0, {
      duration: reducido ? 0 : motion.duration.medium2,
      easing: CURVA,
    });
  }, [activo, reducido, progreso]);

  // El indicador se expande desde el centro (M3); no se escala nada al presionar.
  const estiloIndicador = useAnimatedStyle(() => ({
    opacity: progreso.value,
    transform: [{ scaleX: 0.5 + progreso.value * 0.5 }],
  }));

  return (
    <Tocable
      testID={testID}
      onPress={onPress}
      onLongPress={onLongPress}
      colorContenido={color.onSurface}
      sinCapa
      conAnilloFoco={false}
      accessibilityRole="tab"
      accessibilityState={{ selected: activo }}
      accessibilityLabel={etiquetaLector}
      style={estilos.destino}
    >
      {({ pressed, enfocado, hover }) => (
        <>
          <View style={[estilos.zonaIcono, enfocado && anilloFoco]}>
            <Animated.View style={[StyleSheet.absoluteFill, estilos.indicador, estiloIndicador]} />
            {/* capa de estado limitada al área del indicador (M3) */}
            {pressed || enfocado || hover ? (
              <View
                pointerEvents="none"
                style={[
                  StyleSheet.absoluteFill,
                  estilos.capa,
                  { backgroundColor: activo ? color.onSecondaryContainer : color.onSurfaceVariant },
                  { opacity: hover && !pressed && !enfocado ? estado.hover : estado.pressed },
                ]}
              />
            ) : null}
            {icono}
            {badge !== undefined ? (
              <View style={estilos.badge}>
                <Text style={estilos.textoBadge}>{badge}</Text>
              </View>
            ) : null}
          </View>
          <Text style={[estilos.etiqueta, activo ? estilos.etiquetaActiva : estilos.etiquetaInactiva]}>
            {etiqueta}
          </Text>
        </>
      )}
    </Tocable>
  );
}

/**
 * M3 Navigation bar (00-sistema §9.14) para `Tabs` de Expo Router.
 * Activo = píldora `secondaryContainer` + icono relleno + etiqueta 700 (no depende del color).
 * Etiquetas siempre visibles; máximo 4 destinos.
 */
export function BarraNavegacion({ state, descriptors, emitter, navigateToTab, insets }: BottomTabBarProps) {
  return (
    <View style={[estilos.barra, { paddingBottom: insets.bottom }]} accessibilityRole="tablist">
      {state.routes.map((route, index) => {
        const activo = index === state.index;
        const { options } = descriptors[route.key];
        const etiqueta = typeof options.title === 'string' ? options.title : route.name;
        const badge = options.tabBarBadge;
        const colorIcono = activo ? color.onSecondaryContainer : color.onSurfaceVariant;
        const etiquetaLector =
          options.tabBarAccessibilityLabel ??
          (badge !== undefined ? `${etiqueta}, ${badge} ${badge === 1 ? 'alerta' : 'alertas'}` : etiqueta);

        return (
          <Destino
            key={route.key}
            etiqueta={etiqueta}
            etiquetaLector={etiquetaLector}
            activo={activo}
            badge={badge}
            testID={options.tabBarButtonTestID}
            icono={options.tabBarIcon?.({ focused: activo, color: colorIcono, size: iconos.linea })}
            onPress={() => {
              const evento = emitter.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
              if (!activo && !evento.defaultPrevented) navigateToTab(route.key);
            }}
            onLongPress={() => emitter.emit({ type: 'tabLongPress', target: route.key })}
          />
        );
      })}
    </View>
  );
}

const estilos = StyleSheet.create({
  barra: {
    flexDirection: 'row',
    backgroundColor: color.surfaceContainer,
    minHeight: medidas.barraNavegacion,
  },
  destino: {
    flex: 1,
    minHeight: medidas.barraNavegacion,
    alignItems: 'center',
    justifyContent: 'center',
    gap: espacio.xs,
    paddingTop: espacio.m,
    paddingBottom: espacio.m,
  },
  zonaIcono: {
    borderRadius: shape.full,
    width: medidas.indicadorNavAncho,
    height: medidas.indicadorNavAlto,
    alignItems: 'center',
    justifyContent: 'center',
  },
  indicador: { borderRadius: shape.full, backgroundColor: color.secondaryContainer },
  capa: { borderRadius: shape.full },
  badge: {
    position: 'absolute',
    top: -espacio.xs,
    right: espacio.xs,
    minWidth: medidas.badge,
    height: medidas.badge,
    paddingHorizontal: espacio.xs,
    borderRadius: shape.full,
    backgroundColor: color.error,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textoBadge: { ...type.labelSmall, color: color.onError },
  etiqueta: { ...type.labelMedium, textAlign: 'center' },
  etiquetaActiva: { color: color.onSurface, fontWeight: pesoActivo },
  etiquetaInactiva: { color: color.onSurfaceVariant },
});
