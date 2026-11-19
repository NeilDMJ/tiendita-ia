import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { useConexion } from '@/hooks/use-conexion';
import { bordes, colores, espacio, tipografia } from '@/theme';

/** Franja fija cuando no hay internet (Nielsen #1 y #9). Icono + texto, no solo color. */
export function AvisoConexion() {
  const conectado = useConexion();
  if (conectado !== false) return null;
  return (
    <View style={estilos.franja} accessibilityRole="alert" accessibilityLiveRegion="polite">
      <MaterialCommunityIcons name="wifi-off" size={24} color={colores.peligro} />
      <Text style={estilos.texto}>
        Sin conexión. Lo que registres se guarda y se enviará al reconectarte.
      </Text>
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
    backgroundColor: colores.fondo,
    borderBottomWidth: bordes.grueso,
    borderBottomColor: colores.peligro,
  },
  texto: { ...tipografia.cuerpo, color: colores.texto, flex: 1 },
});
