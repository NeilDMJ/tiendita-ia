import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, medidas, shape, type } from '@/theme';
import type { NivelConfianza } from '@/utils/carrito';

export interface IndicadorConfianzaProps {
  nivel: NivelConfianza;
  /** 'Falta precio' | 'Elige producto' */
  textoFalta?: string;
}

type Apariencia = { icono: NombreIcono; colorIcono: string; colorTexto: string; fondo: string; borde?: string; texto: string };

/** 00-sistema §9.6 — contrastes: texto ≥ 7.24:1, icono "Detectado" 6.13:1. */
const NIVELES: Record<NivelConfianza, Apariencia> = {
  alta: {
    icono: 'check-circle',
    colorIcono: color.success,
    colorTexto: color.onSurfaceVariant,
    fondo: 'transparent',
    borde: color.outlineVariant,
    texto: 'Detectado',
  },
  baja: {
    icono: 'help-circle',
    colorIcono: color.onTertiaryContainer,
    colorTexto: color.onTertiaryContainer,
    fondo: color.tertiaryContainer,
    texto: 'Revisa',
  },
  falta: {
    icono: 'alert-circle',
    colorIcono: color.onErrorContainer,
    colorTexto: color.onErrorContainer,
    fondo: color.errorContainer,
    texto: 'Falta precio',
  },
  manual: {
    icono: 'pencil',
    colorIcono: color.onSurfaceVariant,
    colorTexto: color.onSurfaceVariant,
    fondo: 'transparent',
    borde: color.outlineVariant,
    texto: 'Tú lo pusiste',
  },
};

/**
 * Assist chip presentacional (no tocable) del estado de lo detectado.
 * Nunca muestra porcentaje ni la palabra "confianza".
 * No es elemento separado para el lector: su texto va en el label de la fila.
 */
export function IndicadorConfianza({ nivel, textoFalta }: IndicadorConfianzaProps) {
  const n = NIVELES[nivel];
  const texto = nivel === 'falta' && textoFalta ? textoFalta : n.texto;
  return (
    <View
      style={[
        estilos.chip,
        { backgroundColor: n.fondo },
        n.borde ? { borderWidth: bordes.fino, borderColor: n.borde } : null,
      ]}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      <MaterialCommunityIcons name={n.icono} size={iconos.chico} color={n.colorIcono} />
      <Text style={[estilos.texto, { color: n.colorTexto }]}>{texto}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: espacio.s,
    minHeight: medidas.chip,
    paddingHorizontal: espacio.s,
    borderRadius: shape.small,
  },
  texto: { ...type.labelLarge },
});
