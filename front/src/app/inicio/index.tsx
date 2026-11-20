import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useRef, useState, type ComponentRef } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { esPagoDigital } from '@/api/esquemas';
import { buscarProductos } from '@/api/negocio';
import { Dialogo } from '@/components/dialogo';
import { EXISTENCIA_BAJA, SEGUNDOS_VENTA_MANUAL } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { useConexion } from '@/hooks/use-conexion';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { color, espacio, type } from '@/theme';
import { calcularTotal, plural } from '@/utils/carrito';
import { formatoMoneda } from '@/utils/formato-moneda';

import { AlertasDia } from './alertas-dia';
import { AtajosCamara } from './atajos-camara';
import { CorteCaja } from './corte-caja';
import type { ProductoAlertaStock, ResumenMetricasVentas } from './tipos';

const DIAS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

function fechaHoyTexto(): string {
  const d = new Date();
  return `${DIAS[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]}`;
}

const SEGUNDOS_PROMEDIO_DIGITAL = 45;

/**
 * Pantalla de Inicio — App del Tendero (Material Design 3):
 * Centro de operaciones de la jornada que reúne el corte métrico de ventas,
 * el centro de alertas operativas del negocio y atajos a la cámara para mercancía y tickets.
 * Diseñada para no duplicar ni interferir con la pantalla de cobro.
 */
export function PantallaInicio() {
  const conectado = useConexion();
  const sinConexion = conectado === false;

  const ventas = useVentasHoy();
  const { carrito, cargado: carritoCargado, vaciar } = useCarrito();
  const [confirmarDescarte, setConfirmarDescarte] = useState(false);
  const refDescartar = useRef<ComponentRef<typeof View>>(null);
  const [refrescando, setRefrescando] = useState(false);

  // Consulta de catálogo para alertas de stock bajo
  const consultaStock = useQuery({
    queryKey: ['productos', 'alertas-stock'],
    queryFn: () => buscarProductos('', 50),
    enabled: !sinConexion,
  });

  const productosAlerta: ProductoAlertaStock[] = (consultaStock.data ?? [])
    .filter((p) => p.existencia <= EXISTENCIA_BAJA)
    .map((p) => ({
      ...p,
      bajo: p.existencia > 0 && p.existencia <= EXISTENCIA_BAJA,
      agotado: p.existencia <= 0,
    }))
    .sort((a, b) => a.existencia - b.existencia);

  const hayBorrador = carritoCargado && carrito.items.length > 0;
  const { total: totalBorrador } = calcularTotal(carrito.items);
  const ventasPendientes = ventas.lista.filter((v) => v.pendiente).length;

  // Cálculo de métricas del día para el corte
  const totalVendido = ventas.lista.reduce((s, v) => s + v.total, 0);
  const totalVentas = ventas.lista.length;
  const ticketPromedio = totalVentas > 0 ? totalVendido / totalVentas : 0;
  const totalEfectivo = ventas.lista
    .filter((v) => v.metodo === 'efectivo')
    .reduce((s, v) => s + v.total, 0);
  const totalDigital = ventas.lista
    .filter((v) => esPagoDigital(v.metodo))
    .reduce((s, v) => s + v.total, 0);

  const segundosAhorrados = totalVentas * Math.max(0, SEGUNDOS_VENTA_MANUAL - SEGUNDOS_PROMEDIO_DIGITAL);
  const minutosAhorrados = Math.round(segundosAhorrados / 60);

  const metricas: ResumenMetricasVentas = {
    totalVendido,
    totalVentas,
    ticketPromedio,
    totalEfectivo,
    totalDigital,
    ventasPendientes,
    minutosAhorrados,
  };

  const alRefrescar = async () => {
    setRefrescando(true);
    ventas.reintentar();
    await consultaStock.refetch();
    setRefrescando(false);
  };

  const abrirHistorial = () => router.push('/historial');
  const continuarBorrador = () =>
    router.push({ pathname: '/revision/[modo]', params: { modo: 'cobro' } } as any);

  return (
    <SafeAreaView edges={['top']} style={estilos.pantalla}>
      <ScrollView
        style={estilos.scroll}
        contentContainerStyle={estilos.contenido}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={alRefrescar}
            tintColor={color.primary}
            colors={[color.primary]}
          />
        }
      >
        {/* Cabecera del día */}
        <View style={estilos.cabeceraDia}>
          <Text style={estilos.fechaTexto}>{fechaHoyTexto()}</Text>
          <Text style={estilos.saludoTexto} accessibilityRole="header">
            Tiendita y Mostrador
          </Text>
        </View>

        {/* 1. Corte del día / Resumen Financiero */}
        <CorteCaja metricas={metricas} onVerHistorial={abrirHistorial} />

        {/* 2. Centro de Alertas operativas de la tienda */}
        <AlertasDia
          borradorTotal={totalBorrador}
          borradorCantidad={hayBorrador ? carrito.items.length : 0}
          onContinuarBorrador={continuarBorrador}
          onDescartarBorrador={() => setConfirmarDescarte(true)}
          refDescartar={refDescartar}
          ventasPendientes={ventasPendientes}
          onSincronizarCola={ventas.reintentar}
          sinConexion={sinConexion}
          productosAlerta={productosAlerta}
          cargandoStock={consultaStock.isPending}
        />

        {/* 3. Atajos a la cámara y mostrador */}
        <AtajosCamara />
      </ScrollView>

      {/* M3 Basic Dialog para descartar ventas sin perder datos accidentalmente */}
      <Dialogo
        visible={confirmarDescarte}
        icono="trash-can-outline"
        titulo="¿Descartar la venta sin terminar?"
        mensaje={`Se borrarán ${plural(carrito.items.length, 'producto', 'productos')} por ${formatoMoneda(totalBorrador)}. Esto no se puede deshacer.`}
        onCerrar={() => setConfirmarDescarte(false)}
        refRetorno={refDescartar}
        acciones={[
          { texto: 'No, regresar', variante: 'tonal', onPress: () => setConfirmarDescarte(false) },
          {
            texto: 'Sí, descartar',
            variante: 'filledError',
            icono: 'trash-can-outline',
            onPress: () => {
              vaciar();
              setConfirmarDescarte(false);
            },
          },
        ]}
      />
    </SafeAreaView>
  );
}

export default PantallaInicio;

const estilos = StyleSheet.create({
  pantalla: {
    flex: 1,
    backgroundColor: color.surface,
  },
  scroll: {
    flex: 1,
  },
  contenido: {
    padding: espacio.l,
    paddingBottom: espacio.xxl * 2,
    gap: espacio.xl,
  },
  cabeceraDia: {
    gap: espacio.xs,
  },
  fechaTexto: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
    textTransform: 'capitalize',
  },
  saludoTexto: {
    ...type.headlineSmall,
    color: color.onSurface,
  },
});
