import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Boton } from '@/components/boton';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { bordes, color, elevacion, espacio, iconos, shape, tactil, type } from '@/theme';
import { plural } from '@/utils/carrito';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import type { CorteCajaProps } from './tipos';

const COLORES_GRAFICA = [
  color.success,
  color.primary,
  color.tertiary,
  color.secondary,
] as const;

export function CorteCaja({ metricas, onVerHistorial }: CorteCajaProps) {
  const {
    totalVendido,
    totalVentas,
    ticketPromedio,
    totalEfectivo,
    totalDigital,
    minutosAhorrados,
    topProductos,
  } = metricas;

  const porcentajeEfectivo = totalVendido > 0 ? Math.round((totalEfectivo / totalVendido) * 100) : 0;
  const porcentajeDigital = totalVendido > 0 ? Math.max(0, 100 - porcentajeEfectivo) : 0;

  const totalPiezasTop = topProductos.reduce((acc, p) => acc + p.cantidad, 0);
  const maxPiezasTop = topProductos.length > 0 ? Math.max(...topProductos.map((p) => p.cantidad), 1) : 1;

  return (
    <View style={estilos.seccion}>
      {/* Tarjeta 1: Reporte y Gráfica de Ingresos */}
      <View
        style={[estilos.card, elevacion.level1]}
        accessible
        accessibilityRole="summary"
        accessibilityLabel={`Reporte del día: Total vendido ${montoParaLector(totalVendido)}, en ${totalVentas} ${plural(totalVentas, 'venta', 'ventas')}.`}
      >
        <View style={estilos.cabeceraCard}>
          <View style={[estilos.iconoCirculo, { backgroundColor: color.successContainer }]}>
            <MaterialCommunityIcons
              name="cash-register"
              size={iconos.linea}
              color={color.onSuccessContainer}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </View>
          <View style={estilos.flex}>
            <Text style={estilos.tituloCard}>Reporte de ventas de hoy</Text>
            <Text style={estilos.subtituloCard}>Resumen de dinero en caja</Text>
          </View>
        </View>

        {/* Monto total único */}
        <View style={estilos.bloqueTotal}>
          <Text style={estilos.etiquetaTotal}>Total vendido</Text>
          <Text style={estilos.montoGrande} accessibilityLabel={montoParaLector(totalVendido)}>
            {formatoMoneda(totalVendido)}
          </Text>
        </View>

        {/* Gráfica 1: Distribución de pagos (Efectivo vs Digital) */}
        <View style={estilos.bloqueGrafica}>
          <Text style={estilos.tituloGrafica}>Distribución por forma de pago</Text>

          <View style={estilos.barraApilada}>
            {totalVendido > 0 ? (
              <>
                {porcentajeEfectivo > 0 ? (
                  <View
                    style={[
                      estilos.segmentoBarra,
                      { flex: porcentajeEfectivo, backgroundColor: color.success },
                    ]}
                  />
                ) : null}
                {porcentajeDigital > 0 ? (
                  <View
                    style={[
                      estilos.segmentoBarra,
                      { flex: porcentajeDigital, backgroundColor: color.primary },
                    ]}
                  />
                ) : null}
              </>
            ) : (
              <View
                style={[
                  estilos.segmentoBarra,
                  { flex: 1, backgroundColor: color.surfaceContainerHighest },
                ]}
              />
            )}
          </View>

          <View style={estilos.grillaMetodos}>
            <View style={estilos.cajaMetodo}>
              <View style={estilos.filaIconoMetodo}>
                <MaterialCommunityIcons
                  name="cash-multiple"
                  size={iconos.linea}
                  color={color.success}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.nombreMetodo}>Efectivo</Text>
              </View>
              <Text style={estilos.valorMetrica}>{formatoMoneda(totalEfectivo)}</Text>
              <Text style={estilos.porcentajeMetodo}>{porcentajeEfectivo}% del total</Text>
            </View>

            <View style={estilos.cajaMetodo}>
              <View style={estilos.filaIconoMetodo}>
                <MaterialCommunityIcons
                  name="credit-card-outline"
                  size={iconos.linea}
                  color={color.primary}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.nombreMetodo}>Digital</Text>
              </View>
              <View style={estilos.filaValorDigital}>
                <Text style={estilos.valorMetrica}>{formatoMoneda(totalDigital)}</Text>
                {totalDigital > 0 ? <EtiquetaSimulacion modo="chip" /> : null}
              </View>
              <Text style={estilos.porcentajeMetodo}>{porcentajeDigital}% del total</Text>
            </View>
          </View>
        </View>

        <View style={estilos.divisor} />

        {/* Indicadores únicos sin duplicar */}
        <View style={estilos.grillaIndicadores}>
          <View style={estilos.tarjetaIndicador}>
            <MaterialCommunityIcons
              name="receipt-text"
              size={iconos.linea}
              color={color.primary}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.etiquetaMetrica}>Ventas hechas</Text>
            <Text style={estilos.valorMetrica}>{totalVentas}</Text>
          </View>

          <View style={estilos.tarjetaIndicador}>
            <MaterialCommunityIcons
              name="cash-register"
              size={iconos.linea}
              color={color.success}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.etiquetaMetrica}>Promedio por venta</Text>
            <Text style={estilos.valorMetrica}>{formatoMoneda(ticketPromedio)}</Text>
          </View>

          <View style={estilos.tarjetaIndicador}>
            <MaterialCommunityIcons
              name="timer-outline"
              size={iconos.linea}
              color={color.tertiary}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.etiquetaMetrica}>Tiempo ahorrado</Text>
            <Text style={estilos.valorMetrica}>~{minutosAhorrados} min</Text>
          </View>
        </View>

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

      {/* Tarjeta 2: Gráfica de Barras de Productos Más Vendidos */}
      <View style={[estilos.card, elevacion.level1]}>
        <View style={estilos.cabeceraCard}>
          <View style={[estilos.iconoCirculo, { backgroundColor: color.primaryContainer }]}>
            <MaterialCommunityIcons
              name="star-outline"
              size={iconos.linea}
              color={color.onPrimaryContainer}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </View>
          <View style={estilos.flex}>
            <Text style={estilos.tituloCard}>Productos más vendidos</Text>
            <Text style={estilos.subtituloCard}>Comparativa de artículos más pedidos</Text>
          </View>
        </View>

        {topProductos.length > 0 ? (
          <View style={estilos.contenedorGraficaBarras}>
            {/* Gráfica de columnas verticales */}
            <View style={estilos.areaColumnas}>
              {topProductos.map((prod, indice) => {
                const alturaColumna = Math.max(24, Math.round((prod.cantidad / maxPiezasTop) * 120));
                const porcentajeParticipacion =
                  totalPiezasTop > 0 ? Math.round((prod.cantidad / totalPiezasTop) * 100) : 0;
                const colorBarra = COLORES_GRAFICA[indice % COLORES_GRAFICA.length];

                return (
                  <View
                    key={prod.clave}
                    style={estilos.columnaItem}
                    accessible
                    accessibilityLabel={`${prod.nombre}: ${prod.cantidad} piezas, representa el ${porcentajeParticipacion} por ciento`}
                  >
                    <Text style={estilos.datoArribaBarra}>{porcentajeParticipacion}%</Text>
                    <View style={estilos.pistaColumna}>
                      <View
                        style={[
                          estilos.rellenoColumna,
                          {
                            height: alturaColumna,
                            backgroundColor: colorBarra,
                          },
                        ]}
                      />
                    </View>
                    <Text style={estilos.etiquetaEjeX} numberOfLines={2}>
                      {prod.nombre}
                    </Text>
                  </View>
                );
              })}
            </View>

            {/* Leyenda limpia con cantidad exacta una sola vez */}
            <View style={estilos.leyendaGrafica}>
              {topProductos.map((prod, indice) => {
                const colorBarra = COLORES_GRAFICA[indice % COLORES_GRAFICA.length];
                return (
                  <View key={prod.clave} style={estilos.filaLeyenda}>
                    <View style={[estilos.puntoLeyenda, { backgroundColor: colorBarra }]} />
                    <Text style={estilos.nombreLeyenda} numberOfLines={1}>
                      {prod.nombre}
                    </Text>
                    <Text style={estilos.cantidadLeyenda}>
                      {plural(prod.cantidad, 'pieza', 'piezas')}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>
        ) : (
          <View style={estilos.estadoVacioTop}>
            <MaterialCommunityIcons
              name="basket-outline"
              size={iconos.linea}
              color={color.onSurfaceVariant}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.textoVacioTop}>
              Aquí aparecerá la gráfica con tus productos más vendidos en cuanto cobres tu primera venta.
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  seccion: {
    gap: espacio.l,
  },
  card: {
    backgroundColor: color.surfaceContainerLow,
    borderRadius: shape.large,
    padding: espacio.l,
    gap: espacio.m,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
  },
  cabeceraCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
  },
  iconoCirculo: {
    width: tactil.minimo,
    height: tactil.minimo,
    borderRadius: shape.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  flex: {
    flex: 1,
  },
  tituloCard: {
    ...type.titleMedium,
    color: color.onSurface,
    fontWeight: '700',
  },
  subtituloCard: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  bloqueTotal: {
    backgroundColor: color.surfaceContainerLowest,
    padding: espacio.m,
    borderRadius: shape.medium,
    gap: espacio.xs,
  },
  etiquetaTotal: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  montoGrande: {
    ...type.headlineLarge,
    color: color.primary,
    fontWeight: '700',
  },
  bloqueGrafica: {
    gap: espacio.s,
  },
  tituloGrafica: {
    ...type.titleSmall,
    color: color.onSurface,
  },
  barraApilada: {
    height: 16,
    borderRadius: shape.full,
    overflow: 'hidden',
    flexDirection: 'row',
    backgroundColor: color.surfaceContainerHighest,
    gap: 2,
  },
  segmentoBarra: {
    height: '100%',
  },
  grillaMetodos: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: espacio.m,
    marginTop: espacio.xs,
  },
  cajaMetodo: {
    flexGrow: 1,
    flexBasis: 130,
    backgroundColor: color.surfaceContainerLowest,
    padding: espacio.m,
    borderRadius: shape.medium,
    gap: espacio.xs,
  },
  filaIconoMetodo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
  },
  nombreMetodo: {
    ...type.labelLarge,
    color: color.onSurface,
  },
  porcentajeMetodo: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  filaValorDigital: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: espacio.xs,
  },
  divisor: {
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
  },
  grillaIndicadores: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: espacio.m,
  },
  tarjetaIndicador: {
    flexGrow: 1,
    flexBasis: 130,
    backgroundColor: color.surfaceContainerLowest,
    padding: espacio.m,
    borderRadius: shape.medium,
    gap: espacio.xs,
  },
  etiquetaMetrica: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  valorMetrica: {
    ...type.amount,
    color: color.onSurface,
    fontWeight: '700',
  },
  contenedorGraficaBarras: {
    gap: espacio.l,
  },
  areaColumnas: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    backgroundColor: color.surfaceContainerLowest,
    borderRadius: shape.medium,
    padding: espacio.m,
    paddingTop: espacio.l,
    gap: espacio.s,
  },
  columnaItem: {
    flex: 1,
    alignItems: 'center',
    gap: espacio.xs,
  },
  datoArribaBarra: {
    ...type.labelLarge,
    color: color.onSurface,
    fontWeight: '700',
  },
  pistaColumna: {
    width: '70%',
    maxWidth: 44,
    height: 120,
    justifyContent: 'flex-end',
    backgroundColor: color.surfaceContainer,
    borderRadius: shape.small,
    overflow: 'hidden',
  },
  rellenoColumna: {
    width: '100%',
    borderRadius: shape.small,
  },
  etiquetaEjeX: {
    ...type.labelLarge,
    color: color.onSurfaceVariant,
    textAlign: 'center',
  },
  leyendaGrafica: {
    gap: espacio.s,
  },
  filaLeyenda: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    backgroundColor: color.surfaceContainerLowest,
    paddingHorizontal: espacio.m,
    paddingVertical: espacio.s,
    borderRadius: shape.small,
  },
  puntoLeyenda: {
    width: 14,
    height: 14,
    borderRadius: shape.full,
  },
  nombreLeyenda: {
    ...type.titleSmall,
    color: color.onSurface,
    flex: 1,
  },
  cantidadLeyenda: {
    ...type.labelLarge,
    color: color.primary,
    fontWeight: '700',
  },
  estadoVacioTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    padding: espacio.m,
    backgroundColor: color.surfaceContainerLowest,
    borderRadius: shape.medium,
  },
  textoVacioTop: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
    flex: 1,
  },
});