import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import type { NombreIcono } from '@/constants';
import { anilloFoco, bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';

export type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'peligroLleno' | 'texto';

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
}

const VARIANTES: Record<VarianteBoton, { fondo: string; presionado: string; borde: string; texto: string }> = {
  primario: { fondo: colores.acento, presionado: colores.acentoPresionado, borde: colores.acento, texto: colores.sobreAcento },
  secundario: { fondo: colores.fondo, presionado: colores.superficie, borde: colores.texto, texto: colores.texto },
  peligro: { fondo: colores.fondo, presionado: colores.superficie, borde: colores.peligro, texto: colores.peligro },
  peligroLleno: {
    fondo: colores.peligro,
    presionado: colores.peligroPresionado,
    borde: colores.peligro,
    texto: colores.sobrePeligro,
  },
  texto: { fondo: 'transparent', presionado: colores.superficie, borde: 'transparent', texto: colores.acento },
};

/** Botón plano: presionado = cambio de fondo (sin opacidad, escala ni ripple). */
export function Boton({
  texto,
  onPress,
  variante = 'primario',
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
}: BotonProps) {
  const [enfocado, setEnfocado] = useState(false);
  const v = VARIANTES[variante];
  const inactivo = deshabilitado || cargando;
  const colorTexto = deshabilitado ? colores.deshabilitadoTexto : v.texto;

  return (
    <Pressable
      testID={testID}
      onPress={inactivo ? undefined : onPress}
      onFocus={() => setEnfocado(true)}
      onBlur={() => setEnfocado(false)}
      accessibilityRole="button"
      accessibilityLabel={cargando && textoCargando ? textoCargando : texto}
      accessibilityHint={deshabilitado ? motivoDeshabilitado : accessibilityHint}
      accessibilityState={{ disabled: deshabilitado, busy: cargando }}
      style={({ pressed }) => [
        estilos.base,
        tamano === 'principal' && estilos.principal,
        anchoCompleto ? estilos.anchoCompleto : estilos.anchoAjustado,
        {
          backgroundColor: deshabilitado ? colores.deshabilitadoFondo : pressed && !inactivo ? v.presionado : v.fondo,
          borderColor: deshabilitado ? colores.deshabilitadoFondo : v.borde,
        },
        enfocado && anilloFoco,
        style,
      ]}
    >
      <View style={estilos.contenido}>
        {cargando ? (
          <ActivityIndicator color={colorTexto} />
        ) : icono ? (
          <MaterialCommunityIcons
            name={icono}
            size={iconos.linea}
            color={colorTexto}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        ) : null}
        <Text style={[estilos.texto, { color: colorTexto }, variante === 'texto' && estilos.subrayado]}>
          {cargando && textoCargando ? textoCargando : texto}
        </Text>
      </View>
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  base: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    borderRadius: radios.medio,
    borderWidth: bordes.grueso,
    justifyContent: 'center',
  },
  principal: { minHeight: tactil.principal },
  anchoCompleto: { alignSelf: 'stretch' },
  anchoAjustado: { alignSelf: 'flex-start' },
  contenido: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: espacio.s },
  texto: { ...tipografia.etiqueta, textAlign: 'center', flexShrink: 1 },
  subrayado: { textDecorationLine: 'underline' },
});
