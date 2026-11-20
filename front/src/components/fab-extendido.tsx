import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import { color, elevacion, espacio, iconos, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export interface FabExtendidoProps {
  texto: string;
  icono: NombreIcono;
  onPress: () => void;
  /** 'Abre la cámara para cobrar los productos del mostrador' */
  accessibilityHint?: string;
  /** Distancia al borde inferior del contenedor. Default 16. */
  separacionInferior?: number;
  testID?: string;
}

/** Alto del FAB + su separación: lo que las listas deben reservar abajo para que no tape nada. */
export const RESERVA_FAB = tactil.principal + espacio.xxl;

/**
 * M3 Extended FAB, variante primary (00-sistema §9.15). Esquina inferior derecha.
 * EXC-9: nunca se colapsa a solo icono.
 */
export function FabExtendido({
  texto,
  icono,
  onPress,
  accessibilityHint,
  separacionInferior = espacio.l,
  testID,
}: FabExtendidoProps) {
  return (
    <View style={[estilos.posicion, { bottom: separacionInferior }]} pointerEvents="box-none">
      <Tocable
        testID={testID}
        onPress={onPress}
        colorContenido={color.onPrimary}
        radio={shape.large}
        accessibilityRole="button"
        accessibilityLabel={texto}
        accessibilityHint={accessibilityHint}
        style={({ hover, enfocado }) => [estilos.fab, hover || enfocado ? elevacion.level4 : elevacion.level3]}
      >
        <MaterialCommunityIcons
          name={icono}
          size={iconos.linea}
          color={color.onPrimary}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.texto}>{texto}</Text>
      </Tocable>
    </View>
  );
}

const estilos = StyleSheet.create({
  posicion: { position: 'absolute', right: espacio.l, left: espacio.l, alignItems: 'flex-end' },
  fab: {
    minHeight: tactil.principal,
    minWidth: tactil.principal + espacio.xl,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    paddingLeft: espacio.l,
    paddingRight: espacio.l + espacio.xs,
    paddingVertical: espacio.s,
    borderRadius: shape.large,
    backgroundColor: color.primary,
  },
  texto: { ...type.labelLarge, color: color.onPrimary, flexShrink: 1 },
});
