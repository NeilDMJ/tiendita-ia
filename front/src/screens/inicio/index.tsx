import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useRef, useState, type ComponentRef } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { buscarProductos } from '@/api/negocio';
import { Dialogo } from '@/components/dialogo';
import { Tocable } from '@/components/tocable';
import { EXISTENCIA_BAJA, SEGUNDOS_VENTA_MANUAL } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { useConexion } from '@/hooks/use-conexion';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { color, elevacion, espacio, fuente, iconos, shape, tactil, type } from '@/theme';
import { calcularTotal, plural } from '@/utils/carrito';
import { formatoMoneda } from '@/utils/formato-moneda';

import { AlertasDia } from './alertas-dia';
import { CorteCaja } from './corte-caja';
import type { ProductoAlertaStock, ProductoMasVendido, ResumenMetricasVentas } from './tipos';

const SEGUNDOS_PROMEDIO_DIGITAL = 45;

function obtenerContextoHorario(): { saludo: string; fecha: string } {
  const ahora = new Date();
  const zonaHoraria = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const horaStr = new Intl.DateTimeFormat('es-MX', {
    hour: 'numeric',
    hour12: false,
    timeZone: zonaHoraria,
  }).format(ahora);

  const hora = Number.parseInt(horaStr, 10);
  let saludo = '¡Buenas noches!';
  if (hora >= 5 && hora < 12) {
    saludo = '¡Buenos días!';
  } else if (hora >= 12 && hora < 19) {
    saludo = '¡Buenas tardes!';
  }

  const fechaCruda = new Intl.DateTimeFormat('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: zonaHoraria,
  }).format(ahora);

  const fecha = fechaCruda.charAt(0).toUpperCase() + fechaCruda.slice(1);

  return { saludo, fecha };
}

export function PantallaInicio() {
  const conectado = useConexion();
  const sinConexion = conectado === false;

  const ventas = useVentasHoy();
  const { carrito, cargado: carritoCargado, vaciar } = useCarrito();
  const [confirmarDescarte, setConfirmarDescarte] = useState(false);
  const refDescartar = useRef<ComponentRef<typeof View>>(null);
  const [refrescando, setRefrescando] = useState(false);

  const { saludo, fecha } = obtenerContextoHorario();

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
    .filter((v) => v.metodo === 'digital_simulado')
    .reduce((s, v) => s + v.total, 0);

  const segundosAhorrados = totalVentas * Math.max(0, SEGUNDOS_VENTA_MANUAL - SEGUNDOS_PROMEDIO_DIGITAL);
  const minutosAhorrados = Math.round(segundosAhorrados / 60);

  // Cálculo de productos más vendidos hoy a partir de ventas.lista
  const mapaProductos = new Map<string, ProductoMasVendido>();
  for (const venta of ventas.lista) {
    for (const item of venta.items) {
      const clave = item.sku ?? `libre-${item.nombre.toLowerCase().trim()}`;
      const actual = mapaProductos.get(clave);
      const montoItem = item.cantidad * item.precio_unitario;
      if (actual) {
        actual.cantidad += item.cantidad;
        actual.totalGenerado += montoItem;
      } else {
        mapaProductos.set(clave, {
          clave,
          nombre: item.nombre,
          cantidad: item.cantidad,
          totalGenerado: montoItem,
        });
      }
    }
  }

  const topProductos = Array.from(mapaProductos.values())
    .sort((a, b) => b.cantidad - a.cantidad || b.totalGenerado - a.totalGenerado)
    .slice(0, 4);

  const metricas: ResumenMetricasVentas = {
    totalVendido,
    totalVentas,
    ticketPromedio,
    totalEfectivo,
    totalDigital,
    ventasPendientes,
    minutosAhorrados,
    topProductos,
  };

  const alRefrescar = async () => {
    setRefrescando(true);
    ventas.reintentar();
    await consultaStock.refetch();
    setRefrescando(false);
  };

  const abrirHistorial = () => router.push('/historial');
  const abrirAsistente = () => router.push('/asistente');
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
        {/* 1. Bienvenida según zona horaria */}
        <View style={estilos.cabeceraBienvenida}>
          <View style={estilos.iconoBienvenida}>
            <MaterialCommunityIcons
              name="storefront-outline"
              size={iconos.linea}
              color={color.onPrimaryContainer}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </View>
          <View style={estilos.textosBienvenida}>
            <Text style={estilos.saludoTexto} accessibilityRole="header">
              {saludo}
            </Text>
            <Text style={estilos.subtituloBienvenida}>{fecha}</Text>
          </View>
        </View>

        {/* 2. Botón protagonista de acceso directo a la IA / Chatbot */}
        <Tocable
          onPress={abrirAsistente}
          colorContenido={color.onPrimary}
          radio={shape.large}
          accessibilityRole="button"
          accessibilityLabel="Hablar con el Asistente IA de la tienda"
          accessibilityHint="Abre el chat inteligente para revisar ventas, cuentas e inventario"
          style={[estilos.botonIA, elevacion.level2]}
        >
          <View style={estilos.badgeIconoIA}>
            <MaterialCommunityIcons
              name="chat-outline"
              size={iconos.linea}
              color={color.primary}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </View>
          <View style={estilos.textosBotonIA}>
            <Text style={estilos.tituloBotonIA}>Pregúntale al Asistente IA</Text>
            <Text style={estilos.subtituloBotonIA}>
              Dudas de ventas, inventario o cuentas del día
            </Text>
          </View>
          <MaterialCommunityIcons
            name="chevron-right"
            size={iconos.linea}
            color={color.onPrimary}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        </Tocable>

        {/* 3. Gráficas y Reporte de Ventas */}
        <CorteCaja metricas={metricas} onVerHistorial={abrirHistorial} />

        {/* 4. Centro de Alertas operativas e inventario */}
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
  cabeceraBienvenida: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
  },
  iconoBienvenida: {
    width: tactil.minimo,
    height: tactil.minimo,
    borderRadius: shape.large,
    backgroundColor: color.primaryContainer,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textosBienvenida: {
    flex: 1,
    gap: espacio.xs,
  },
  saludoTexto: {
    ...type.headlineSmall,
    color: color.onSurface,
    fontFamily: fuente.bold,
  },
  subtituloBienvenida: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  botonIA: {
    minHeight: tactil.principal + 16,
    backgroundColor: color.primary,
    borderRadius: shape.large,
    padding: espacio.l,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
  },
  badgeIconoIA: {
    width: tactil.minimo,
    height: tactil.minimo,
    borderRadius: shape.full,
    backgroundColor: color.onPrimary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textosBotonIA: {
    flex: 1,
    gap: espacio.xs,
  },
  tituloBotonIA: {
    ...type.titleMedium,
    color: color.onPrimary,
    fontFamily: fuente.bold,
  },
  subtituloBotonIA: {
    ...type.bodyLarge,
    color: color.primaryContainer,
  },
});