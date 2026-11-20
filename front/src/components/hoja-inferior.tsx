import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useRef, type ComponentRef, type ReactNode } from 'react';
import {
  AccessibilityInfo,

  KeyboardAvoidingView,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type DimensionValue,
} from 'react-native';
import Animated, { Easing, FadeIn, SlideInDown, useReducedMotion } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { NombreIcono } from '@/constants';
import { bordes, color, elevacion, espacio, iconos, medidas, motion, scrim, shape, tactil, type } from '@/theme';

import { Boton } from './boton';
import { nodoAccesible } from '@/utils/nodo-accesible';

export interface HojaInferiorProps {
  visible: boolean;
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  /** Contenido fijo al pie (p. ej. botón principal). */
  pie?: ReactNode;
  /** Oculta el botón Cerrar (obliga a elegir). */
  sinCerrar?: boolean;
  /** `modal` (default, con velo) o `estandar` (sin velo, convive con la pantalla: tutor de pagos). */
  tipo?: 'modal' | 'estandar';
  /** Fracción 0–1 del alto de la pantalla. Default 0.9. */
  altoMaximo?: number;
  /**
   * El hijo maneja su propio scroll (p. ej. una `FlatList` de chat): sin `ScrollView` envolvente
   * (evita lista virtual dentro de otra) y la hoja toma el alto completo de `altoMaximo`.
   */
  sinScroll?: boolean;
  /** Icono decorativo junto al título (p. ej. `cash-register` en "Pregúntale a Caja"). */
  icono?: NombreIcono;
}

/** Distancia de arrastre hacia abajo del asa que cierra la hoja. */
const ARRASTRE_CIERRE = 64;
const [x1, y1, x2, y2] = motion.easing.emphasizedDecelerate;
const ENTRADA = SlideInDown.duration(motion.duration.medium4).easing(Easing.bezier(x1, y1, x2, y2));
const VELO = FadeIn.duration(motion.duration.medium2);

/**
 * M3 Bottom sheet (00-sistema §9.11): `surfaceContainerLow`, esquinas superiores 28, nivel 1,
 * velo negro 32 % (modal). Asa de arrastre para cerrar + botón "Cerrar" visible (EXC-7).
 * Movimiento reducido: aparece sin deslizar.
 */
export function HojaInferior({
  visible,
  titulo,
  onCerrar,
  children,
  pie,
  sinCerrar,
  tipo = 'modal',
  altoMaximo = 0.9,
  sinScroll = false,
  icono,
}: HojaInferiorProps) {
  const reducido = useReducedMotion();
  const refTitulo = useRef<ComponentRef<typeof Text>>(null);
  // Arrastre del asa hacia abajo = cerrar (opcional; el botón "Cerrar" siempre está visible).
  const inicioArrastre = useRef<number | null>(null);

  useEffect(() => {
    if (!visible || tipo !== 'modal') return;
    const t = setTimeout(() => {
      const nodo = refTitulo.current ? nodoAccesible(refTitulo.current) : null;
      if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
    }, motion.duration.medium4);
    return () => clearTimeout(t);
  }, [visible, tipo]);

  if (!visible && tipo === 'estandar') return null;

  const alto: DimensionValue = `${Math.round(Math.min(1, Math.max(0.2, altoMaximo)) * 100)}%`;

  const hoja = (
    <Animated.View
      entering={reducido ? undefined : ENTRADA}
      style={[estilos.hoja, elevacion.level1, sinScroll ? { height: alto } : { maxHeight: alto }]}
      accessibilityViewIsModal={tipo === 'modal'}
    >
      <SafeAreaView edges={tipo === 'modal' ? ['bottom'] : []} style={[estilos.interior, sinScroll && estilos.flex]}>
        <View
          onTouchStart={(e) => {
            inicioArrastre.current = e.nativeEvent.pageY;
          }}
          onTouchEnd={(e) => {
            const inicio = inicioArrastre.current;
            inicioArrastre.current = null;
            if (!sinCerrar && inicio !== null && e.nativeEvent.pageY - inicio > ARRASTRE_CIERRE) onCerrar();
          }}
          style={estilos.zonaAsa}
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
        >
          <View style={estilos.asa} />
        </View>
        <View style={estilos.cabecera}>
          {icono ? (
            <MaterialCommunityIcons
              name={icono}
              size={iconos.linea}
              color={color.onSurfaceVariant}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          ) : null}
          <Text ref={refTitulo} style={estilos.titulo} accessibilityRole="header">
            {titulo}
          </Text>
          {sinCerrar ? null : (
            <Boton texto="Cerrar" icono="close" variante="text" anchoCompleto={false} onPress={onCerrar} />
          )}
        </View>
        {sinScroll ? (
          <View style={estilos.flex}>{children}</View>
        ) : (
          <ScrollView style={estilos.cuerpo} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
            {children}
          </ScrollView>
        )}
        {pie ? <View style={estilos.pie}>{pie}</View> : null}
      </SafeAreaView>
    </Animated.View>
  );

  if (tipo === 'estandar') return <View style={estilos.estandar}>{hoja}</View>;

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onCerrar} statusBarTranslucent>
      {/* Android con edge-to-edge (Expo SDK 58): la ventana ya no se redimensiona con el teclado,
          así que `padding` en ambas plataformas (docs.expo.dev/guides/keyboard-handling). */}
      <KeyboardAvoidingView behavior="padding" style={estilos.raiz}>
        <Animated.View entering={reducido ? undefined : VELO} style={[StyleSheet.absoluteFill, estilos.velo]}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={sinCerrar ? undefined : onCerrar}
            accessible={false}
            importantForAccessibility="no"
          />
        </Animated.View>
        {hoja}
      </KeyboardAvoidingView>
    </Modal>
  );
}

const estilos = StyleSheet.create({
  raiz: { flex: 1, justifyContent: 'flex-end', alignItems: 'center' },
  velo: { backgroundColor: scrim },
  estandar: { alignItems: 'center' },
  hoja: {
    width: '100%',
    maxWidth: medidas.hojaAnchoMaximo,
    backgroundColor: color.surfaceContainerLow,
    borderTopLeftRadius: shape.extraLarge,
    borderTopRightRadius: shape.extraLarge,
  },
  interior: { flexShrink: 1 },
  flex: { flex: 1 },
  zonaAsa: { height: tactil.minimo, alignItems: 'center', justifyContent: 'center' },
  asa: {
    width: medidas.asaAncho,
    height: medidas.asaAlto,
    borderRadius: shape.full,
    backgroundColor: color.onSurfaceVariant,
  },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingLeft: espacio.l,
    paddingRight: espacio.s,
    marginTop: -espacio.s,
  },
  titulo: { ...type.titleLarge, color: color.onSurface, flex: 1 },
  cuerpo: { flexGrow: 0, flexShrink: 1 },
  contenido: { paddingHorizontal: espacio.l, paddingVertical: espacio.l, gap: espacio.l },
  pie: {
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    gap: tactil.separacion,
    borderTopWidth: bordes.fino,
    borderTopColor: color.outlineVariant,
  },
});
