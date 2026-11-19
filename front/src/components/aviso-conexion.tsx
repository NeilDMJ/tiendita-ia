import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { useConexion } from '@/hooks/use-conexion';
import { bordes, colores, espacio, iconos, tipografia } from '@/theme';

/**
 * Franja fija cuando no hay internet (Nielsen #1 y #9). Icono + texto, no solo color.
 * Tipo `sinConexion`: borde `texto` y fondo `superficie` (no es un error del usuario).
 */
export function AvisoConexion() {
  const conectado = useConexion();
  if (conectado !== false) return null;
  return (
    <View style={estilos.franja} accessibilityRole="alert" accessibilityLiveRegion="polite">
      <MaterialCommunityIcons
        name="wifi-off"
        size={iconos.linea}
        color={colores.texto}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={estilos.texto}>Sin conexión: lo que registres se guarda y se enviará al reconectarte.</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  franja: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    backgroundColor: colores.superficie,
    borderBottomWidth: bordes.grueso,
    borderBottomColor: colores.texto,
  },
  texto: { ...tipografia.cuerpo, color: colores.texto, flex: 1 },
});
