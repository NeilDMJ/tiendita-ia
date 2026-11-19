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
import { bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';
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
  ref?: Ref<ComponentRef<typeof TextInput>>;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

/** Campo con etiqueta visible, ayuda y error en línea (icono + texto). */
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
    ? colores.divisor
    : error
      ? colores.peligro
      : enfocado
        ? colores.acento
        : colores.borde;
  const grosor = error || enfocado ? bordes.grueso : bordes.fino;

  return (
    <View style={[estilos.contenedor, style]}>
      <View style={estilos.filaEtiqueta}>
        <Text style={estilos.etiqueta}>{etiqueta}</Text>
        {obligatorio ? <Text style={estilos.obligatorio}>* Obligatorio</Text> : null}
      </View>
      <View
        style={[
          estilos.caja,
          {
            borderColor: colorBorde,
            borderWidth: grosor,
            // compensa el borde para que el contenido no se mueva al enfocar
            paddingHorizontal: espacio.m - (grosor - bordes.fino),
            backgroundColor: deshabilitado ? colores.deshabilitadoFondo : colores.fondo,
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
          placeholderTextColor={colores.textoSecundario}
          keyboardType={teclado}
          inputMode={modoEntrada}
          editable={!deshabilitado}
          autoFocus={autoFocus}
          onFocus={() => setEnfocado(true)}
          onBlur={alSalir}
          allowFontScaling
          accessibilityLabel={etiqueta + (obligatorio ? ', obligatorio' : '')}
          accessibilityHint={error ?? ayuda}
          accessibilityState={{ disabled: deshabilitado }}
          style={[estilos.entrada, deshabilitado && estilos.entradaDeshabilitada]}
        />
        {sufijo ? <Text style={estilos.afijo}>{sufijo}</Text> : null}
        {icono ? (
          <MaterialCommunityIcons
            name={icono}
            size={iconos.linea}
            color={colores.textoSecundario}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        ) : null}
      </View>
      {error ? (
        <View style={estilos.mensaje} accessibilityLiveRegion="polite">
          <MaterialCommunityIcons
            name="alert-circle"
            size={iconos.linea}
            color={colores.peligro}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.error}>{error}</Text>
        </View>
      ) : ayuda ? (
        <View style={estilos.mensaje}>
          <MaterialCommunityIcons
            name="information"
            size={iconos.linea}
            color={colores.textoSecundario}
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
  etiqueta: { ...tipografia.etiqueta, color: colores.texto },
  obligatorio: { ...tipografia.cuerpo, color: colores.textoSecundario },
  caja: {
    minHeight: tactil.minimo,
    borderRadius: radios.medio,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  afijo: { ...tipografia.cuerpoGrande, color: colores.texto },
  entrada: {
    ...tipografia.cuerpoGrande,
    color: colores.texto,
    flex: 1,
    minHeight: tactil.minimo - bordes.grueso * 2,
    paddingVertical: espacio.s,
  },
  entradaDeshabilitada: { color: colores.deshabilitadoTexto },
  mensaje: { flexDirection: 'row', gap: espacio.xs, alignItems: 'flex-start' },
  error: { ...tipografia.etiqueta, color: colores.peligro, flex: 1 },
  ayuda: { ...tipografia.cuerpo, color: colores.textoSecundario, flex: 1 },
});
