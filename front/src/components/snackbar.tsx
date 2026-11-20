import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { AccessibilityInfo, StyleSheet, Text, View } from 'react-native';
import Animated, { Easing, FadeOut, SlideInDown, useReducedMotion } from 'react-native-reanimated';

import type { NombreIcono } from '@/constants';
import { useAccesibilidad } from '@/hooks/use-accesibilidad';
import { color, elevacion, espacio, iconos, motion, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export interface SnackbarProps {
  visible: boolean;
  /** 'Quitaste "Galletas".' */
  mensaje: string;
  icono?: NombreIcono;
  /** 'Deshacer' */
  accion?: { texto: string; onPress: () => void };
  /** Default 10 000 ms; `null` = hasta que se cierre (también sin límite con lector de pantalla, WCAG 2.2.1). */
  duracionMs?: number | null;
  onCerrar: () => void;
  /** Alto de la barra fija que debe librar (el snackbar queda 8 dp encima). */
  separacionInferior: number;
  /**
   * Texto que el lector anuncia al aparecer (iOS y Android). Si se pasa, se desactiva la live region
   * para no anunciar dos veces. La pantalla NO debe anunciar el mismo evento por su cuenta.
   */
  anuncio?: string;
}

const [x1, y1, x2, y2] = motion.easing.emphasizedDecelerate;
const ENTRADA = SlideInDown.duration(motion.duration.medium2).easing(Easing.bezier(x1, y1, x2, y2));
const SALIDA = FadeOut.duration(motion.duration.short4);

/**
 * M3 Snackbar (00-sistema §9.5): confirmaciones breves y "Deshacer".
 * Nunca para errores con acción obligatoria; nunca tapa el botón principal.
 * Se coloca con posición absoluta dentro del contenedor de la pantalla.
 */
export function Snackbar({
  visible,
  mensaje,
  icono,
  accion,
  duracionMs = 10_000,
  onCerrar,
  separacionInferior,
  anuncio,
}: SnackbarProps) {
  const { lectorActivo } = useAccesibilidad();
  const reducido = useReducedMotion();

  const cerrar = useRef(onCerrar);
  useEffect(() => {
    cerrar.current = onCerrar;
  }, [onCerrar]);

  useEffect(() => {
    if (!visible || duracionMs === null || lectorActivo) return;
    const t = setTimeout(() => cerrar.current(), duracionMs);
    return () => clearTimeout(t);
  }, [visible, duracionMs, lectorActivo, mensaje]);

  useEffect(() => {
    if (visible && anuncio) AccessibilityInfo.announceForAccessibility(anuncio);
  }, [visible, anuncio]);

  if (!visible) return null;

  return (
    <Animated.View
      entering={reducido ? undefined : ENTRADA}
      exiting={reducido ? undefined : SALIDA}
      style={[estilos.posicion, { bottom: separacionInferior + espacio.s }]}
      pointerEvents="box-none"
    >
      {/* Un solo mecanismo de anuncio: `anuncio` (iOS y Android) o, si no se pasa, live region (Android). */}
      <View
        style={[estilos.contenedor, elevacion.level3]}
        accessibilityLiveRegion={anuncio ? 'none' : 'polite'}
      >
        {icono ? (
          <MaterialCommunityIcons
            name={icono}
            size={iconos.linea}
            color={color.inverseOnSurface}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        ) : null}
        <Text style={estilos.texto}>{mensaje}</Text>
        <View style={estilos.acciones}>
          {accion ? (
            <Tocable
              onPress={accion.onPress}
              colorContenido={color.inversePrimary}
              radio={shape.full}
              colorAnillo={color.inverseOnSurface}
              accessibilityRole="button"
              accessibilityLabel={accion.texto}
              style={estilos.accion}
            >
              <Text style={estilos.textoAccion}>{accion.texto}</Text>
            </Tocable>
          ) : null}
          <Tocable
            onPress={onCerrar}
            colorContenido={color.inverseOnSurface}
            radio={shape.full}
            colorAnillo={color.inverseOnSurface}
            accessibilityRole="button"
            accessibilityLabel="Cerrar aviso"
            style={estilos.cerrar}
          >
            <MaterialCommunityIcons
              name="close"
              size={iconos.linea}
              color={color.inverseOnSurface}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </Tocable>
        </View>
      </View>
    </Animated.View>
  );
}

const estilos = StyleSheet.create({
  posicion: { position: 'absolute', left: espacio.l, right: espacio.l },
  contenedor: {
    minHeight: tactil.minimo,
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: tactil.separacion,
    paddingLeft: espacio.l,
    paddingRight: espacio.xs,
    paddingVertical: espacio.xs,
    borderRadius: shape.extraSmall,
    backgroundColor: color.inverseSurface,
  },
  texto: { ...type.bodyMedium, color: color.inverseOnSurface, flexGrow: 1, flexShrink: 1, flexBasis: 160 },
  acciones: { flexDirection: 'row', alignItems: 'center', marginLeft: 'auto', gap: tactil.separacion },
  accion: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    paddingHorizontal: espacio.m,
    borderRadius: shape.full,
    justifyContent: 'center',
  },
  textoAccion: { ...type.labelLarge, color: color.inversePrimary },
  cerrar: {
    width: tactil.minimo,
    height: tactil.minimo,
    borderRadius: shape.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
