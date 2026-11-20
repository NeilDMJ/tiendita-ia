import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useState, type ComponentRef, type Ref } from 'react';
import {
  AccessibilityInfo,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, pesoActivo, shape, tactil, type } from '@/theme';
import { leerMonto } from '@/utils/formato-moneda';

export interface CampoProps {
  etiqueta: string;
  valor: string;
  onCambiar: (v: string) => void;
  tipo?: 'texto' | 'moneda' | 'entero';
  prefijo?: string;
  sufijo?: string;
  /** Solo ejemplo; nunca reemplaza la etiqueta. */
  placeholder?: string;
  ayuda?: string;
  error?: string | null;
  obligatorio?: boolean;
  deshabilitado?: boolean;
  autoFocus?: boolean;
  onBlur?: () => void;
  icono?: NombreIcono;
  /** Icono del texto de ayuda (default `information`). */
  iconoAyuda?: NombreIcono;
  /** Varias líneas: crece hasta `maxLineas` y luego hace scroll. */
  multilinea?: boolean;
  /** Default 5. */
  maxLineas?: number;
  maxLength?: number;
  /**
   * EXC-11: oculta la etiqueta visible (solo compositor de chat). La etiqueta sigue siendo el label
   * accesible y el `placeholder` + el botón "Enviar" dejan claro el propósito.
   */
  etiquetaOculta?: boolean;
  /** No pinta ayuda/error debajo (el contenedor los muestra en otro lugar); el borde sí cambia. */
  ocultarMensajes?: boolean;
  onFocus?: () => void;
  ref?: Ref<ComponentRef<typeof TextInput>>;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

/**
 * M3 Text field OUTLINED (00-sistema §9.2) con EXC-3: etiqueta fija arriba a 16 sp
 * (no flota ni se encoge). Ayuda y error en línea con icono + texto.
 */
export function Campo({
  etiqueta,
  valor,
  onCambiar,
  tipo = 'texto',
  prefijo,
  sufijo,
  placeholder,
  ayuda,
  error,
  obligatorio,
  deshabilitado,
  autoFocus,
  onBlur,
  icono,
  iconoAyuda = 'information',
  multilinea = false,
  maxLineas = 5,
  maxLength,
  etiquetaOculta = false,
  ocultarMensajes = false,
  onFocus,
  ref,
  testID,
  style,
}: CampoProps) {
  const [enfocado, setEnfocado] = useState(false);

  useEffect(() => {
    if (error && Platform.OS === 'ios') AccessibilityInfo.announceForAccessibility(error);
  }, [error]);

  const teclado = tipo === 'moneda' ? 'decimal-pad' : tipo === 'entero' ? 'number-pad' : 'default';
  const modoEntrada = tipo === 'moneda' ? 'decimal' : tipo === 'entero' ? 'numeric' : 'text';

  function alSalir() {
    setEnfocado(false);
    if (tipo === 'moneda') {
      const n = leerMonto(valor);
      if (n !== null) onCambiar(n.toFixed(2));
    }
    onBlur?.();
  }

  const colorBorde = deshabilitado
    ? color.outlineVariant
    : error
      ? color.error
      : enfocado
        ? color.primary
        : color.outline;
  const grosor = (error || enfocado) && !deshabilitado ? bordes.grueso : bordes.fino;
  const colorEtiqueta = deshabilitado ? color.onSurfaceVariant : error ? color.error : enfocado ? color.primary : color.onSurface;

  return (
    <View style={[estilos.contenedor, style]}>
      {etiquetaOculta ? null : (
        <View style={estilos.filaEtiqueta}>
          <Text style={[estilos.etiqueta, { color: colorEtiqueta }, enfocado && estilos.etiquetaActiva]}>
            {etiqueta}
          </Text>
          {obligatorio ? <Text style={estilos.obligatorio}>* Obligatorio</Text> : null}
        </View>
      )}
      <View
        style={[
          estilos.caja,
          {
            borderColor: colorBorde,
            borderWidth: grosor,
            // compensa el borde para que el contenido no se mueva al enfocar
            paddingHorizontal: espacio.l - (grosor - bordes.fino),
            backgroundColor: deshabilitado ? color.surfaceContainerHighest : color.surfaceContainerLowest,
          },
        ]}
      >
        {prefijo ? <Text style={estilos.afijo}>{prefijo}</Text> : null}
        <TextInput
          ref={ref}
          testID={testID}
          value={valor}
          onChangeText={onCambiar}
          placeholder={placeholder}
          placeholderTextColor={color.onSurfaceVariant}
          keyboardType={teclado}
          inputMode={modoEntrada}
          editable={!deshabilitado}
          autoFocus={autoFocus}
          onFocus={() => {
            setEnfocado(true);
            onFocus?.();
          }}
          multiline={multilinea}
          maxLength={maxLength}
          submitBehavior={multilinea ? 'newline' : undefined}
          textAlignVertical={multilinea ? 'top' : undefined}
          onBlur={alSalir}
          allowFontScaling
          accessibilityLabel={etiqueta + (obligatorio ? ', obligatorio' : '')}
          accessibilityHint={error ?? ayuda}
          accessibilityState={{ disabled: deshabilitado }}
          style={[
            estilos.entrada,
            multilinea && {
              maxHeight: type.bodyLargePlus.lineHeight * maxLineas + espacio.m * 2,
              paddingTop: espacio.m,
              paddingBottom: espacio.m,
            },
            deshabilitado && estilos.entradaDeshabilitada,
          ]}
        />
        {sufijo ? <Text style={estilos.afijo}>{sufijo}</Text> : null}
        {icono ? (
          <MaterialCommunityIcons
            name={icono}
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        ) : null}
      </View>
      {ocultarMensajes ? null : error ? (
        <View style={estilos.mensaje} accessibilityLiveRegion="polite">
          <MaterialCommunityIcons
            name="alert-circle"
            size={iconos.linea}
            color={color.error}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.error}>{error}</Text>
        </View>
      ) : ayuda ? (
        <View style={estilos.mensaje}>
          <MaterialCommunityIcons
            name={iconoAyuda}
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.ayuda}>{ayuda}</Text>
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { gap: espacio.xs },
  filaEtiqueta: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: espacio.s },
  etiqueta: { ...type.titleSmall },
  etiquetaActiva: { ...pesoActivo },
  obligatorio: { ...type.bodyLarge, color: color.onSurfaceVariant },
  caja: {
    minHeight: tactil.principal,
    borderRadius: shape.medium,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  afijo: { ...type.bodyLargePlus, color: color.onSurfaceVariant },
  entrada: {
    ...type.bodyLargePlus,
    color: color.onSurface,
    flex: 1,
    minHeight: tactil.principal - bordes.grueso * 2,
    paddingVertical: espacio.s,
  },
  entradaDeshabilitada: { color: color.onSurfaceVariant },
  mensaje: { flexDirection: 'row', gap: espacio.xs, alignItems: 'flex-start' },
  error: { ...type.labelLarge, color: color.error, flex: 1 },
  ayuda: { ...type.bodySmall, color: color.onSurfaceVariant, flex: 1 },
});
