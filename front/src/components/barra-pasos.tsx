import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { color, espacio, iconos, medidas, pesoActivo, shape, type } from '@/theme';

export interface BarraPasosProps {
  pasos: string[];
  /** Índice 0-based. */
  actual: number;
  mostrarNombres?: boolean;
}

/**
 * M3 Linear progress determinado + "Paso X de N · Nombre" (Nielsen #1).
 * EXC-5: 8 dp de alto. Indicador `primary`, pista `secondaryContainer` (5.00:1), stop indicator al final.
 */
export function BarraPasos({ pasos, actual, mostrarNombres = true }: BarraPasosProps) {
  const total = pasos.length;
  const progreso = Math.min(1, Math.max(0, (actual + 1) / total));
  const completo = progreso >= 1;
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
      <View style={estilos.progreso}>
        <View style={[estilos.indicador, { flexGrow: progreso }]} />
        {completo ? null : (
          <View style={[estilos.pista, { flexGrow: 1 - progreso }]}>
            <View style={estilos.parada} />
          </View>
        )}
      </View>
      {mostrarNombres ? (
        <View style={estilos.nombres}>
          {pasos.map((paso, i) => (
            <View key={paso} style={estilos.nombre}>
              <MaterialCommunityIcons
                name={i < actual ? 'check-circle' : i === actual ? 'circle-slice-8' : 'circle-outline'}
                size={iconos.chico}
                color={i <= actual ? color.primary : color.onSurfaceVariant}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={[estilos.textoNombre, i === actual && estilos.textoActual]}>{paso}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { paddingHorizontal: espacio.l, paddingVertical: espacio.s, gap: espacio.s },
  titulo: { ...type.titleSmall, color: color.onSurface },
  progreso: { flexDirection: 'row', gap: espacio.xs, height: medidas.progresoAlto },
  indicador: { flexBasis: 0, borderRadius: shape.full, backgroundColor: color.primary },
  pista: {
    flexBasis: 0,
    borderRadius: shape.full,
    backgroundColor: color.secondaryContainer,
    alignItems: 'flex-end',
    justifyContent: 'center',
    paddingRight: (medidas.progresoAlto - medidas.progresoParada) / 2,
  },
  parada: {
    width: medidas.progresoParada,
    height: medidas.progresoParada,
    borderRadius: shape.full,
    backgroundColor: color.primary,
  },
  nombres: { flexDirection: 'row', gap: espacio.xs },
  nombre: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoNombre: { ...type.labelLarge, color: color.onSurfaceVariant, flexShrink: 1 },
  textoActual: { color: color.onSurface, fontWeight: pesoActivo },
});
