import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { bordes, color, elevacion, espacio, iconos, shape, type } from '@/theme';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import type { ResumenInventario } from './tipos';

export interface ResumenInventarioCardProps {
  resumen: ResumenInventario;
}

/**
 * Card elevated M3 (level1) con el resumen del inventario.
 * Muestra métricas clave: total de productos, piezas, valor estimado y alertas.
 * Patrón idéntico al CorteCaja de Inicio (consistencia M3, Nielsen #4).
 */
export function ResumenInventarioCard({ resumen }: ResumenInventarioCardProps) {
  const {
    totalProductos,
    totalPiezas,
    productosConStockBajo,
    productosAgotados,
    productosPorCaducar,
    productosCaducados,
    valorEstimado,
  } = resumen;

  const alertas = productosConStockBajo + productosAgotados + productosPorCaducar + productosCaducados;

  return (
    <View
      style={[estilos.card, elevacion.level1]}
      accessible
      accessibilityRole="summary"
      accessibilityLabel={`Inventario: ${totalProductos} productos, ${totalPiezas} piezas, valor estimado ${montoParaLector(valorEstimado)}, ${alertas} alertas activas`}
    >
      <View style={estilos.cabecera}>
        <View style={estilos.filaIcono}>
          <MaterialCommunityIcons
            name="package-variant"
            size={iconos.linea}
            color={color.primary}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.subtitulo}>Tu inventario</Text>
        </View>
        <Text style={estilos.contador}>
          {totalProductos} {totalProductos === 1 ? 'producto' : 'productos'}
        </Text>
      </View>

      {/* Métricas principales */}
      <View style={estilos.grillaMetricas}>
        <View style={estilos.columnaMetrica}>
          <Text style={estilos.etiquetaMetrica}>Piezas totales</Text>
          <Text style={estilos.valorMetrica}>{totalPiezas}</Text>
        </View>
        <View style={estilos.columnaMetrica}>
          <Text style={estilos.etiquetaMetrica}>Valor estimado</Text>
          <Text style={estilos.valorMetrica} accessibilityLabel={montoParaLector(valorEstimado)}>
            {formatoMoneda(valorEstimado)}
          </Text>
        </View>
      </View>

      {alertas > 0 ? (
        <>
          <View style={estilos.divisor} />

          {/* Alertas de inventario */}
          <View style={estilos.grillaAlertas}>
            {productosAgotados > 0 ? (
              <View style={estilos.filaAlerta}>
                <MaterialCommunityIcons
                  name="close-circle"
                  size={iconos.chico}
                  color={color.error}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.textoAlertaRojo}>
                  {productosAgotados} {productosAgotados === 1 ? 'agotado' : 'agotados'}
                </Text>
              </View>
            ) : null}
            {productosConStockBajo > 0 ? (
              <View style={estilos.filaAlerta}>
                <MaterialCommunityIcons
                  name="alert-circle"
                  size={iconos.chico}
                  color={color.warning}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.textoAlertaAviso}>
                  {productosConStockBajo} con poco stock
                </Text>
              </View>
            ) : null}
            {productosCaducados > 0 ? (
              <View style={estilos.filaAlerta}>
                <MaterialCommunityIcons
                  name="calendar-alert"
                  size={iconos.chico}
                  color={color.error}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.textoAlertaRojo}>
                  {productosCaducados} {productosCaducados === 1 ? 'caducado' : 'caducados'}
                </Text>
              </View>
            ) : null}
            {productosPorCaducar > 0 ? (
              <View style={estilos.filaAlerta}>
                <MaterialCommunityIcons
                  name="calendar-clock"
                  size={iconos.chico}
                  color={color.warning}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.textoAlertaAviso}>
                  {productosPorCaducar} por caducar esta semana
                </Text>
              </View>
            ) : null}
          </View>
        </>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  card: {
    backgroundColor: color.surfaceContainerLow,
    borderRadius: shape.large,
    padding: espacio.l,
    gap: espacio.m,
  },
  cabecera: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: espacio.xs,
  },
  filaIcono: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  subtitulo: {
    ...type.titleMedium,
    color: color.onSurface,
  },
  contador: {
    ...type.labelLarge,
    color: color.onSurfaceVariant,
  },
  grillaMetricas: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: espacio.m,
  },
  columnaMetrica: {
    flex: 1,
    gap: espacio.xs,
  },
  etiquetaMetrica: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  valorMetrica: {
    ...type.headlineSmall,
    color: color.onSurface,
    fontVariant: ['tabular-nums'],
  },
  divisor: {
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
  },
  grillaAlertas: {
    gap: espacio.s,
  },
  filaAlerta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  textoAlertaRojo: {
    ...type.bodyLarge,
    color: color.error,
  },
  textoAlertaAviso: {
    ...type.bodyLarge,
    color: color.warning,
  },
});
