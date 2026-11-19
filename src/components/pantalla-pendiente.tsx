import { StyleSheet, Text, View } from 'react-native';

import { colores, espacio, tipografia } from '@/theme';

/** Marcador temporal de pantallas aún no implementadas (Fase 0). */
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
  contenedor: { flex: 1, backgroundColor: colores.fondo, padding: espacio.l, gap: espacio.s },
  titulo: { ...tipografia.titulo, color: colores.texto },
  texto: { ...tipografia.cuerpo, color: colores.textoSecundario },
});
