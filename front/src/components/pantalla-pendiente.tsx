import { StyleSheet, Text, View } from 'react-native';

import { color, espacio, type } from '@/theme';

/** Marcador temporal de pantallas aún no implementadas (estado vacío M3). */
export function PantallaPendiente({ titulo, descripcion }: { titulo: string; descripcion: string }) {
  return (
    <View style={estilos.contenedor}>
      <Text style={estilos.titulo} accessibilityRole="header">
        {titulo}
      </Text>
      <Text style={estilos.texto}>{descripcion}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.surface, padding: espacio.l, gap: espacio.s },
  titulo: { ...type.headlineSmall, color: color.onSurface },
  texto: { ...type.bodyLarge, color: color.onSurfaceVariant },
});
