import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentRef, Ref } from 'react';
import { ActivityIndicator, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, color, elevacion, espacio, iconos, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export type VarianteM3 =
  | 'filled'
  | 'tonal'
  | 'outlined'
  | 'text'
  | 'elevated'
  | 'outlinedError'
  | 'filledError'
  /** Botón text en color `error` (acción destructiva secundaria: "Descartar venta", "Empezar de nuevo"). */
  | 'textError';

export type VarianteBoton = VarianteM3;

export interface BotonProps {
  texto: string;
  onPress: () => void;
  variante?: VarianteBoton;
  icono?: NombreIcono;
  tamano?: 'normal' | 'principal';
  deshabilitado?: boolean;
  /** Se lee como hint: el usuario sabe por qué no puede continuar. */
  motivoDeshabilitado?: string;
  cargando?: boolean;
  textoCargando?: string;
  anchoCompleto?: boolean;
  accessibilityHint?: string;
  testID?: string;
  style?: StyleProp<ViewStyle>;
  /** Para devolver el foco del lector a este botón (p. ej. al cerrar un diálogo). */
  ref?: Ref<ComponentRef<typeof View>>;
}

type Apariencia = { contenedor: string; contenido: string; borde?: string; nivel: 0 | 1 };

const VARIANTES: Record<VarianteM3, Apariencia> = {
  filled: { contenedor: color.primary, contenido: color.onPrimary, nivel: 0 },
  tonal: { contenedor: color.secondaryContainer, contenido: color.onSecondaryContainer, nivel: 0 },
  outlined: { contenedor: 'transparent', contenido: color.primary, borde: color.outline, nivel: 0 },
  text: { contenedor: 'transparent', contenido: color.primary, nivel: 0 },
  elevated: { contenedor: color.surfaceContainerLow, contenido: color.primary, nivel: 1 },
  outlinedError: { contenedor: 'transparent', contenido: color.error, borde: color.error, nivel: 0 },
  filledError: { contenedor: color.error, contenido: color.onError, nivel: 0 },
  textError: { contenedor: 'transparent', contenido: color.error, nivel: 0 },
};

/** M3 Buttons (00-sistema §9.1). Alto 48 / 56 (EXC-2), forma píldora, capa de estado 10 %. */
export function Boton({
  texto,
  onPress,
  variante = 'filled',
  icono,
  tamano = 'normal',
  deshabilitado = false,
  motivoDeshabilitado,
  cargando = false,
  textoCargando,
  anchoCompleto = true,
  accessibilityHint,
  testID,
  style,
  ref,
}: BotonProps) {
  const nombre = variante;
  const v = VARIANTES[nombre];
  const inactivo = deshabilitado || cargando;
  const conBorde = v.borde !== undefined;
  const transparente = v.contenedor === 'transparent';
  // EXC-4: deshabilitado legible (onSurfaceVariant sobre surfaceContainerHighest, 7.24:1)
  const colorContenido = deshabilitado ? color.onSurfaceVariant : v.contenido;
  const fondo = deshabilitado ? (transparente ? 'transparent' : color.surfaceContainerHighest) : v.contenedor;
  const borde = deshabilitado ? color.outlineVariant : v.borde;
  const etiqueta = cargando && textoCargando ? textoCargando : texto;

  return (
    <Tocable
      ref={ref}
      testID={testID}
      onPress={inactivo ? undefined : onPress}
      colorContenido={colorContenido}
      radio={shape.full}
      sinCapa={inactivo}
      accessibilityRole="button"
      accessibilityLabel={etiqueta}
      accessibilityHint={deshabilitado ? motivoDeshabilitado : accessibilityHint}
      accessibilityState={{ disabled: deshabilitado, busy: cargando }}
      style={({ hover, enfocado }) => [
        estilos.base,
        tamano === 'principal' && estilos.principal,
        anchoCompleto ? estilos.anchoCompleto : estilos.anchoAjustado,
        icono || cargando ? estilos.conIcono : null,
        nombre === 'text' || nombre === 'textError' ? estilos.textoSolo : null,
        { backgroundColor: fondo },
        conBorde ? { borderWidth: bordes.fino, borderColor: borde } : null,
        !deshabilitado && v.nivel === 1 ? (hover ? elevacion.level2 : elevacion.level1) : null,
        !deshabilitado && nombre === 'tonal' && hover ? elevacion.level1 : null,
        !deshabilitado && nombre === 'filled' && (hover || enfocado) ? elevacion.level1 : null,
        style,
      ]}
    >
      <View style={estilos.contenido}>
        {cargando ? (
          <ActivityIndicator color={colorContenido} />
        ) : icono ? (
          <MaterialCommunityIcons
            name={icono}
            size={iconos.linea}
            color={colorContenido}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        ) : null}
        <Text style={[estilos.texto, { color: colorContenido }]}>{etiqueta}</Text>
      </View>
    </Tocable>
  );
}

const estilos = StyleSheet.create({
  base: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    paddingHorizontal: espacio.xl,
    paddingVertical: espacio.s,
    borderRadius: shape.full,
    justifyContent: 'center',
  },
  principal: { minHeight: tactil.principal },
  conIcono: { paddingLeft: espacio.l },
  textoSolo: { paddingHorizontal: espacio.m },
  anchoCompleto: { alignSelf: 'stretch' },
  anchoAjustado: { alignSelf: 'flex-start' },
  contenido: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: espacio.s },
  texto: { ...type.labelLarge, textAlign: 'center', flexShrink: 1 },
});
