import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';

import { color, espacio, gradienteMarca, iconos, shape, type } from '@/theme';

export interface MarcaProps {
  /** Solo el icono con degradado (cabeceras compactas). Por defecto lleva el nombre al lado. */
  soloIcono?: boolean;
}

const LADO = 48; // EXC-2: mismo mínimo táctil, aunque la marca no sea tocable

/**
 * Logotipo de Tendero IA: icono de tienda blanco sobre el degradado de marca (azul → violeta).
 * Es uno de los dos únicos sitios donde se permite el degradado (identidad: logo + palabra clave).
 * Blanco sobre #1D4ED8 y sobre #5B3FD6 supera 6:1.
 */
export function Marca({ soloIcono = false }: MarcaProps) {
  return (
    <View
      style={estilos.fila}
      accessible
      accessibilityRole="image"
      accessibilityLabel="Tendero IA"
    >
      <LinearGradient
        colors={[...gradienteMarca.colores]}
        start={gradienteMarca.inicio}
        end={gradienteMarca.fin}
        style={estilos.icono}
      >
        <MaterialCommunityIcons
          name="storefront-outline"
          size={iconos.linea}
          color={color.onPrimary}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      </LinearGradient>
      {soloIcono ? null : <Text style={estilos.nombre}>Tendero IA</Text>}
    </View>
  );
}

const estilos = StyleSheet.create({
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.m },
  icono: {
    width: LADO,
    height: LADO,
    borderRadius: shape.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nombre: { ...type.headlineSmall, color: color.onSurface },
});
