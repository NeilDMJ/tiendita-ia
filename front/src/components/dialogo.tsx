import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useRef, type ComponentRef, type RefObject } from 'react';
import {
  AccessibilityInfo,

  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import Animated, { Easing, FadeIn, useReducedMotion } from 'react-native-reanimated';

import type { NombreIcono } from '@/constants';
import { color, elevacion, espacio, iconos, medidas, motion, scrim, shape, tactil, type } from '@/theme';

import { Boton, type VarianteBoton } from './boton';
import { nodoAccesible } from '@/utils/nodo-accesible';

export interface DialogoProps {
  visible: boolean;
  titulo: string;
  mensaje?: string;
  icono?: NombreIcono;
  /** En orden visual. La segura en `filled`/`tonal`; la destructiva en `textError`/`filledError`. */
  acciones: { texto: string; onPress: () => void; variante: VarianteBoton; icono?: NombreIcono }[];
  /** Ausente = obliga a elegir (el velo y "atrás" no cierran). */
  onCerrar?: () => void;
  /**
   * Elemento que abrió el diálogo: al cerrarse, el foco del lector vuelve a él (iOS/Android).
   * Si ya no existe (p. ej. se borró la lista), el sistema decide el foco.
   */
  refRetorno?: RefObject<ComponentRef<typeof View> | null>;
}

/** Con letra grande del sistema las acciones se apilan a ancho completo. */
const ESCALA_APILAR = 1.3;
const [x1, y1, x2, y2] = motion.easing.emphasizedDecelerate;
const ENTRADA = FadeIn.duration(motion.duration.medium4).easing(Easing.bezier(x1, y1, x2, y2));

/** M3 Basic dialog (00-sistema §9.12): confirmaciones destructivas. */
export function Dialogo({ visible, titulo, mensaje, icono, acciones, onCerrar, refRetorno }: DialogoProps) {
  const { fontScale } = useWindowDimensions();
  const reducido = useReducedMotion();
  const refTitulo = useRef<ComponentRef<typeof Text>>(null);
  const apilar = acciones.length >= 3 || fontScale >= ESCALA_APILAR;

  // Devuelve el foco al elemento que abrió el diálogo cuando éste se cierra.
  const estabaVisible = useRef(visible);
  useEffect(() => {
    const cerrado = estabaVisible.current && !visible;
    estabaVisible.current = visible;
    if (!cerrado || !refRetorno) return;
    const t = setTimeout(() => {
      const nodo = refRetorno.current ? nodoAccesible(refRetorno.current) : null;
      if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
    }, motion.duration.medium2);
    return () => clearTimeout(t);
  }, [visible, refRetorno]);

  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(() => {
      const nodo = refTitulo.current ? nodoAccesible(refTitulo.current) : null;
      if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
    }, motion.duration.medium2);
    return () => clearTimeout(t);
  }, [visible]);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      statusBarTranslucent
      onRequestClose={onCerrar ?? (() => undefined)}
    >
      <View style={estilos.raiz}>
        <Pressable
          style={[StyleSheet.absoluteFill, estilos.velo]}
          onPress={onCerrar}
          accessible={false}
          importantForAccessibility="no"
        />
        <Animated.View
          entering={reducido ? undefined : ENTRADA}
          style={[estilos.dialogo, elevacion.level3]}
          accessibilityViewIsModal
        >
          <ScrollView style={estilos.scroll} contentContainerStyle={estilos.contenido} bounces={false}>
            {icono ? (
              <MaterialCommunityIcons
                name={icono}
                size={iconos.linea}
                color={color.secondary}
                style={estilos.icono}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
            ) : null}
            <Text
              ref={refTitulo}
              style={[estilos.titulo, icono ? estilos.centrado : null]}
              accessibilityRole="alert"
            >
              {titulo}
            </Text>
            {mensaje ? <Text style={estilos.mensaje}>{mensaje}</Text> : null}
          </ScrollView>
          <View style={[estilos.acciones, apilar ? estilos.apiladas : estilos.enFila]}>
            {acciones.map((a) => (
              <Boton
                key={a.texto}
                texto={a.texto}
                icono={a.icono}
                variante={a.variante}
                anchoCompleto={apilar}
                onPress={a.onPress}
              />
            ))}
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

const estilos = StyleSheet.create({
  raiz: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: espacio.xl },
  velo: { backgroundColor: scrim },
  dialogo: {
    minWidth: medidas.dialogoAnchoMinimo,
    maxWidth: medidas.dialogoAnchoMaximo,
    width: '100%',
    maxHeight: '90%',
    borderRadius: shape.extraLarge,
    backgroundColor: color.surfaceContainerHigh,
    paddingVertical: espacio.xl,
    gap: espacio.xl,
  },
  scroll: { flexGrow: 0, flexShrink: 1 },
  contenido: { paddingHorizontal: espacio.xl, gap: espacio.l },
  icono: { alignSelf: 'center' },
  titulo: { ...type.headlineSmall, color: color.onSurface },
  centrado: { textAlign: 'center' },
  mensaje: { ...type.bodyMedium, color: color.onSurfaceVariant },
  acciones: { paddingHorizontal: espacio.xl, gap: tactil.separacion },
  apiladas: { flexDirection: 'column' },
  enFila: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end' },
});
