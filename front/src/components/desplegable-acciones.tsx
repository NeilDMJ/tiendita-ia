import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { color, espacio, iconos, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

export interface DesplegableAccionesProps {
  /** Texto de la cabecera. Default "Acciones rápidas". */
  titulo?: string;
  /** Empieza abierto. Default cerrado: la conversación es lo primero. */
  abiertoInicial?: boolean;
  children: ReactNode;
}

/**
 * Cabecera tocable que muestra u oculta un grupo de acciones (chips de sugerencia).
 * Alto 48 (EXC-2); el estado se anuncia con `expanded` y además cambia el icono (no depende del color).
 */
export function DesplegableAcciones({
  titulo = 'Acciones rápidas',
  abiertoInicial = false,
  children,
}: DesplegableAccionesProps) {
  const [abierto, setAbierto] = useState(abiertoInicial);

  return (
    <View style={estilos.contenedor}>
      <Tocable
        onPress={() => setAbierto((a) => !a)}
        colorContenido={color.onSurface}
        radio={shape.medium}
        accessibilityRole="button"
        accessibilityLabel={titulo}
        accessibilityHint={abierto ? 'Oculta las acciones' : 'Muestra las acciones'}
        accessibilityState={{ expanded: abierto }}
        style={estilos.cabecera}
      >
        <MaterialCommunityIcons
          name="lightning-bolt-outline"
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.titulo}>{titulo}</Text>
        <MaterialCommunityIcons
          name={abierto ? 'chevron-up' : 'chevron-down'}
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      </Tocable>
      {abierto ? <View style={estilos.cuerpo}>{children}</View> : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { gap: espacio.s },
  cabecera: {
    minHeight: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.s,
  },
  titulo: { ...type.titleSmall, color: color.onSurface, flex: 1 },
  cuerpo: { gap: tactil.separacion },
});
