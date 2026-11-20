import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, type StyleProp, type ViewStyle } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export interface ChipSugerenciaProps {
  texto: string;
  onPress: () => void;
  icono?: NombreIcono;
  /** Ocupa el ancho disponible (chips apilados del estado vacío). */
  anchoCompleto?: boolean;
  accessibilityHint?: string;
  style?: StyleProp<ViewStyle>;
}

/**
 * M3 Suggestion chip (02-asistente §7) con alto 48 (EXC-2) y borde `outline` (EXC-10).
 * Es una ACCIÓN (`button`), no un filtro: por eso no reutiliza `ChipFiltro` (checkbox).
 */
export function ChipSugerencia({ texto, onPress, icono, anchoCompleto, accessibilityHint, style }: ChipSugerenciaProps) {
  return (
    <Tocable
      onPress={onPress}
      colorContenido={color.onSurfaceVariant}
      radio={shape.full}
      accessibilityRole="button"
      accessibilityLabel={texto}
      accessibilityHint={accessibilityHint}
      style={[estilos.chip, icono && estilos.conIcono, anchoCompleto ? estilos.ancho : estilos.ajustado, style]}
    >
      {icono ? (
        <MaterialCommunityIcons
          name={icono}
          size={iconos.chico}
          color={color.primary}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      ) : null}
      <Text style={estilos.texto}>{texto}</Text>
    </Tocable>
  );
}

const estilos = StyleSheet.create({
  chip: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.xs,
    borderRadius: shape.full,
    borderWidth: bordes.fino,
    borderColor: color.outline,
    backgroundColor: 'transparent',
  },
  conIcono: { paddingLeft: espacio.m },
  ancho: { alignSelf: 'stretch' },
  ajustado: { alignSelf: 'flex-start' },
  texto: { ...type.labelLarge, color: color.onSurfaceVariant, flexShrink: 1 },
});
