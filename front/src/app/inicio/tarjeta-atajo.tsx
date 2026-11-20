import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text } from 'react-native';

import { Tocable } from '@/components/tocable';
import type { NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, medidas, shape, type } from '@/theme';

export interface TarjetaAtajoProps {
  icono: NombreIcono;
  titulo: string;
  detalle: string;
  onPress: () => void;
  accesibilidadLabel?: string;
  accesibilidadHint?: string;
  destacada?: boolean;
}

/**
 * Card outlined M3 tocable completa (01-cobrar §2.1).
 * Usa Tocable para ripple nativo y capa de estado M3 al 10 %, borde outlineVariant y radio medium (12).
 */
export function TarjetaAtajo({
  icono,
  titulo,
  detalle,
  onPress,
  accesibilidadLabel,
  accesibilidadHint,
  destacada = false,
}: TarjetaAtajoProps) {
  return (
    <Tocable
      onPress={onPress}
      colorContenido={destacada ? color.primary : color.onSurface}
      radio={shape.medium}
      accessibilityRole="button"
      accessibilityLabel={accesibilidadLabel ?? `${titulo}. ${detalle}`}
      accessibilityHint={accesibilidadHint}
      style={[estilos.atajo, destacada ? estilos.atajoDestacado : null]}
    >
      <MaterialCommunityIcons
        name={icono}
        size={iconos.linea}
        color={destacada ? color.primary : color.onSurfaceVariant}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={[estilos.atajoTitulo, destacada ? estilos.tituloDestacado : null]}>{titulo}</Text>
      <Text style={estilos.atajoDetalle}>{detalle}</Text>
    </Tocable>
  );
}

const estilos = StyleSheet.create({
  atajo: {
    flexGrow: 1,
    flexBasis: medidas.tarjetaAtajoAncho,
    minHeight: medidas.tarjetaAtajoAlto,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
    borderRadius: shape.medium,
    backgroundColor: color.surface,
    padding: espacio.l,
    gap: espacio.xs,
  },
  atajoDestacado: {
    borderColor: color.primary,
    backgroundColor: color.surfaceContainerLow,
  },
  atajoTitulo: {
    ...type.titleSmall,
    color: color.onSurface,
  },
  tituloDestacado: {
    color: color.primary,
    fontWeight: '700',
  },
  atajoDetalle: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
});
