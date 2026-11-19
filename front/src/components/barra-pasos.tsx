import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { bordes, colores, espacio, iconos, medidas, tipografia } from '@/theme';

export interface BarraPasosProps {
  pasos: string[];
  /** Índice 0-based. */
  actual: number;
  mostrarNombres?: boolean;
}

/** "Paso X de N · Nombre" + segmentos planos (Nielsen #1). */
export function BarraPasos({ pasos, actual, mostrarNombres = true }: BarraPasosProps) {
  const total = pasos.length;
  return (
    <View
      style={estilos.contenedor}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={`Paso ${actual + 1} de ${total}, ${pasos[actual]}`}
      accessibilityValue={{ min: 1, max: total, now: actual + 1 }}
    >
      <Text style={estilos.titulo}>
        Paso {actual + 1} de {total} · {pasos[actual]}
      </Text>
      <View style={estilos.segmentos}>
        {pasos.map((paso, i) => (
          <View
            key={paso}
            style={[
              estilos.segmento,
              i < actual && estilos.completado,
              i === actual && estilos.actual,
              i > actual && estilos.pendiente,
            ]}
          />
        ))}
      </View>
      {mostrarNombres ? (
        <View style={estilos.segmentos}>
          {pasos.map((paso, i) => (
            <View key={paso} style={estilos.nombre}>
              {i < actual ? <MaterialCommunityIcons name="check" size={iconos.chico} color={colores.texto} /> : null}
              <Text style={[estilos.textoNombre, i === actual && estilos.textoActual]}>{paso}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { paddingHorizontal: espacio.l, paddingVertical: espacio.s, gap: espacio.xs },
  titulo: { ...tipografia.etiqueta, color: colores.texto },
  segmentos: { flexDirection: 'row', gap: espacio.xs },
  segmento: { flex: 1, height: medidas.segmentoPasos },
  completado: { backgroundColor: colores.texto },
  actual: { backgroundColor: colores.acento },
  pendiente: { backgroundColor: colores.fondo, borderWidth: bordes.fino, borderColor: colores.borde },
  nombre: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoNombre: { ...tipografia.cuerpo, color: colores.textoSecundario, flexShrink: 1 },
  textoActual: { color: colores.texto, fontWeight: '700' },
});
