import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { color, espacio, iconos, medidas, shape, type } from '@/theme';

export interface EtiquetaSimulacionProps {
  modo?: 'chip' | 'franja';
  /** Texto de la franja. */
  detalle?: string;
}

/**
 * Marca visible de todo lo que no es real (pagos digitales, datos de demo).
 * `chip` = badge en píldora ámbar (EXC-1: 16 sp); `franja` = banner ancho completo. Ámbar suave (8.15:1), nunca se oculta.
 */
export function EtiquetaSimulacion({ modo = 'chip', detalle }: EtiquetaSimulacionProps) {
  const texto = modo === 'franja' ? `Simulación: ${detalle ?? 'esto no mueve dinero real'}` : 'SIMULACIÓN';
  return (
    <View
      style={modo === 'franja' ? estilos.franja : estilos.chip}
      accessible
      accessibilityRole="text"
      accessibilityLabel={`Simulación. ${detalle ?? ''}`}
    >
      <MaterialCommunityIcons
        name="flask-outline"
        size={iconos.chico}
        color={color.onWarningContainer}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={estilos.texto}>{texto}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: espacio.xs,
    minHeight: medidas.chip,
    paddingHorizontal: espacio.s,
    paddingVertical: espacio.xs,
    borderRadius: shape.full,
    backgroundColor: color.warningContainer,
  },
  franja: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    minHeight: medidas.franjaSimulacion,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    backgroundColor: color.warningContainer,
  },
  texto: { ...type.labelMedium, color: color.onWarningContainer, flexShrink: 1 },
});
