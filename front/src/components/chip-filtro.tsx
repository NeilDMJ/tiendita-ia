import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text } from 'react-native';

import { bordes, color, espacio, iconos, pesoActivo, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export interface ChipFiltroProps {
  texto: string;
  seleccionado: boolean;
  /** `radio` cuando los chips son opciones excluyentes dentro de un `radiogroup`. Default `checkbox`. */
  rol?: 'checkbox' | 'radio';
  onPress: () => void;
  accessibilityHint?: string;
}

/**
 * M3 Filter chip con alto 48 (EXC-2). Seleccionado = `secondaryContainer` + check + peso 700
 * (no depende solo del color).
 */
export function ChipFiltro({ texto, seleccionado, onPress, accessibilityHint, rol = 'checkbox' }: ChipFiltroProps) {
  const contenido = seleccionado ? color.onSecondaryContainer : color.onSurfaceVariant;
  return (
    <Tocable
      onPress={onPress}
      colorContenido={contenido}
      radio={shape.small}
      accessibilityRole={rol}
      accessibilityState={{ checked: seleccionado }}
      accessibilityLabel={texto}
      accessibilityHint={accessibilityHint}
      style={[estilos.chip, seleccionado ? estilos.seleccionado : estilos.normal]}
    >
      {seleccionado ? (
        <MaterialCommunityIcons
          name="check"
          size={iconos.chico}
          color={contenido}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      ) : null}
      <Text style={[estilos.texto, { color: contenido }, seleccionado && estilos.textoSeleccionado]}>{texto}</Text>
    </Tocable>
  );
}

const estilos = StyleSheet.create({
  chip: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    borderRadius: shape.small,
  },
  // EXC-10: borde `outline` (no `outlineVariant`) para que el límite del chip tenga ≥ 3:1
  normal: { borderWidth: bordes.fino, borderColor: color.outline, backgroundColor: 'transparent' },
  seleccionado: {
    borderWidth: bordes.fino,
    borderColor: color.secondaryContainer,
    backgroundColor: color.secondaryContainer,
    paddingLeft: espacio.s,
  },
  texto: { ...type.labelLarge },
  textoSeleccionado: { fontWeight: pesoActivo },
});
