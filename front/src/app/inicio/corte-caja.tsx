import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Boton } from '@/components/boton';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { bordes, color, elevacion, espacio, iconos, shape, type } from '@/theme';
import { plural } from '@/utils/carrito';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import type { CorteCajaProps } from './tipos';

/**
 * Bloque métrico M3 de Corte de caja del día (00-sistema §9.10).
 * Card elevated (level1, surfaceContainerLow) con tipografía grande tabular (32 sp),
 * desglose de métodos y banner de impacto acumulado para la demo.
 */
export function CorteCaja({ metricas, onVerHistorial }: CorteCajaProps) {
  const {
    totalVendido,
    totalVentas,
    ticketPromedio,
    totalEfectivo,
    totalDigital,
    minutosAhorrados,
  } = metricas;

  return (
    <View
      style={[estilos.card, elevacion.level1]}
      accessible
      accessibilityRole="summary"
      accessibilityLabel={`Corte del día: Total vendido ${montoParaLector(totalVendido)}, en ${totalVentas} ${plural(totalVentas, 'venta', 'ventas')}. Promedio ${montoParaLector(ticketPromedio)} por venta.`}
    >
      <View style={estilos.cabecera}>
        <View style={estilos.filaIcono}>
          <MaterialCommunityIcons
            name="cash-register"
            size={iconos.linea}
            color={color.primary}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.subtitulo}>Corte del día</Text>
        </View>
        <Text style={estilos.contadorVentas}>
          {totalVentas} {plural(totalVentas, 'venta registrada', 'ventas registradas')}
        </Text>
      </View>

      {/* Monto grande acumulado */}
      <View style={estilos.bloqueTotal}>
        <Text style={estilos.etiquetaTotal}>Total recaudado hoy</Text>
        <Text style={estilos.montoGrande} accessibilityLabel={montoParaLector(totalVendido)}>
          {formatoMoneda(totalVendido)}
        </Text>
      </View>

      <View style={estilos.divisor} />

      {/* Métricas clave: Promedio y Efectivo */}
      <View style={estilos.grillaMetricas}>
        <View style={estilos.columnaMetrica}>
          <Text style={estilos.etiquetaMetrica}>Ticket promedio</Text>
          <Text style={estilos.valorMetrica} accessibilityLabel={montoParaLector(ticketPromedio)}>
            {formatoMoneda(ticketPromedio)}
          </Text>
        </View>

        <View style={estilos.columnaMetrica}>
          <Text style={estilos.etiquetaMetrica}>En efectivo</Text>
          <Text style={estilos.valorMetrica} accessibilityLabel={montoParaLector(totalEfectivo)}>
            {formatoMoneda(totalEfectivo)}
          </Text>
        </View>
      </View>

      {totalDigital > 0 ? (
        <View style={estilos.filaDigital}>
          <View style={estilos.columnaMetrica}>
            <Text style={estilos.etiquetaMetrica}>Pago digital</Text>
            <Text style={estilos.valorMetrica} accessibilityLabel={montoParaLector(totalDigital)}>
              {formatoMoneda(totalDigital)}
            </Text>
          </View>
          <EtiquetaSimulacion modo="chip" />
        </View>
      ) : null}

      {/* Indicador para la demo: Proceso digital vs. manual */}
      {totalVentas > 0 && minutosAhorrados > 0 ? (
        <View style={estilos.cardAhorro}>
          <View style={estilos.filaIcono}>
            <MaterialCommunityIcons
              name="timer-outline"
              size={iconos.linea}
              color={color.primary}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.tituloAhorro}>
              ~{minutosAhorrados} min ahorrados hoy
            </Text>
          </View>
          <Text style={estilos.detalleAhorro}>
            Frente a libreta y calculadora manual · Sin sumar a mano · Inventario al día
          </Text>
        </View>
      ) : null}

      {/* Botón de texto para ir al historial completo */}
      {totalVentas > 0 ? (
        <Boton
          texto="Ver historial completo de ventas"
          icono="history"
          variante="tonal"
          onPress={onVerHistorial}
          accessibilityHint="Abre la pantalla de historial completo de ventas de hoy"
        />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  card: {
    backgroundColor: color.surfaceContainerLow,
    borderRadius: shape.medium,
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
  contadorVentas: {
    ...type.labelLarge,
    color: color.onSurfaceVariant,
  },
  bloqueTotal: {
    gap: espacio.xs,
  },
  etiquetaTotal: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  montoGrande: {
    ...type.headlineLarge,
    color: color.primary,
  },
  divisor: {
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
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
    ...type.amount,
    color: color.onSurface,
  },
  filaDigital: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: espacio.xs,
  },
  cardAhorro: {
    padding: espacio.m,
    borderRadius: shape.small,
    backgroundColor: color.surfaceContainerHighest,
    gap: espacio.xs,
  },
  tituloAhorro: {
    ...type.titleSmall,
    color: color.onSurface,
  },
  detalleAhorro: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
});
