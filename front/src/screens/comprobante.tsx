import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { esPagoDigital, type Existencia, type ItemVenta, type MetodoPago } from '@/api/esquemas';
import { detalleVenta } from '@/api/negocio';
import { Aviso } from '@/components/aviso';
import { BarraPasos } from '@/components/barra-pasos';
import { Boton } from '@/components/boton';
import { Encabezado } from '@/components/encabezado';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { FilaProducto } from '@/components/fila-producto';
import { METODOS_PAGO, SEGUNDOS_VENTA_MANUAL } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { idEnviado, leerCola, PREFIJO_LOCAL } from '@/estado/cola-ventas';
import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';
import { duracionLegible, fechaCompleta } from '@/utils/fecha';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

type Comprobante = {
  folio: string;
  creadaEn: string;
  total: number;
  metodo: MetodoPago;
  recibido: number | null;
  items: ItemVenta[];
  pendiente: boolean;
  existencias: Existencia[] | null;
  duracionSeg?: number;
};

/** Datos del comprobante: última venta en memoria, cola local o servidor. */
type EstadoComprobante = {
  datos: Comprobante | null;
  cargando: boolean;
  error: boolean;
  reintentar: () => void;
};

function useComprobante(id: string): EstadoComprobante {
  const { ultimaVenta } = useCarrito();
  const esLocal = id.startsWith(PREFIJO_LOCAL);
  const enMemoria = ultimaVenta?.id === id ? ultimaVenta : null;

  const local = useQuery({
    queryKey: ['ventas', 'pendientes'],
    queryFn: leerCola,
    enabled: esLocal && !enMemoria,
  });
  const remota = useQuery({
    queryKey: ['ventas', 'detalle', id],
    queryFn: () => detalleVenta(id),
    enabled: !esLocal && !enMemoria,
  });

  // Si la venta local ya se envió, abrir la real.
  useEffect(() => {
    if (!esLocal || enMemoria || !local.data) return;
    const idLocal = id.slice(PREFIJO_LOCAL.length);
    if (local.data.some((v) => v.solicitud.id_local === idLocal)) return;
    idEnviado(idLocal).then((real) => {
      if (real) router.replace(`/venta/${real}?origen=historial`);
    });
  }, [esLocal, enMemoria, local.data, id]);

  if (enMemoria) {
    const c: Comprobante = {
      folio: enMemoria.respuesta?.folio ?? enMemoria.folioLocal ?? 'Pendiente',
      creadaEn: enMemoria.creadaEn,
      total: enMemoria.total,
      metodo: enMemoria.solicitud.metodo_pago,
      recibido: enMemoria.solicitud.recibido,
      items: enMemoria.solicitud.items,
      pendiente: enMemoria.respuesta === null,
      existencias: enMemoria.respuesta?.existencias ?? null,
      duracionSeg: enMemoria.solicitud.duracion_seg,
    };
    return { datos: c, cargando: false, error: false, reintentar: () => undefined };
  }

  if (esLocal) {
    const v = local.data?.find((x) => `${PREFIJO_LOCAL}${x.solicitud.id_local}` === id);
    return {
      datos: v
        ? {
            folio: v.folioLocal,
            creadaEn: v.creada_en,
            total: v.total,
            metodo: v.solicitud.metodo_pago,
            recibido: v.solicitud.recibido,
            items: v.solicitud.items,
            pendiente: true,
            existencias: null,
          }
        : null,
      cargando: local.isPending,
      error: !local.isPending && !v,
      reintentar: () => local.refetch(),
    };
  }

  const r = remota.data;
  return {
    datos: r
      ? {
          folio: r.folio,
          creadaEn: r.creada_en,
          total: r.total,
          metodo: r.metodo_pago,
          recibido: r.recibido,
          items: r.items,
          pendiente: false,
          existencias: null,
        }
      : null,
    cargando: remota.isPending,
    error: remota.isError,
    reintentar: () => remota.refetch(),
  };
}

export function PantallaComprobante({ id, desdeHistorial }: { id: string; desdeHistorial: boolean }) {
  const { datos, cargando, error, reintentar } = useComprobante(id);
  const cerrar = () => (desdeHistorial && router.canGoBack() ? router.back() : router.navigate('/cobrar'));

  useEffect(() => {
    if (!datos || desdeHistorial) return;
    AccessibilityInfo.announceForAccessibility(
      `${datos.pendiente ? 'Venta guardada en tu teléfono' : 'Venta registrada'}. Total ${montoParaLector(datos.total)}. Folio ${datos.folio}.`,
    );
    // solo al llegar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datos?.folio]);

  const titulo = datos?.pendiente ? 'Venta guardada' : desdeHistorial ? 'Venta' : 'Venta registrada';
  const digital = datos ? esPagoDigital(datos.metodo) : false;
  const [desplazado, setDesplazado] = useState(false);

  return (
    <SafeAreaView edges={['bottom']} style={estilos.pantalla}>
      <Encabezado
        titulo={titulo}
        tipoAtras={desdeHistorial ? 'atras' : 'cerrar'}
        onAtras={cerrar}
        desplazado={desplazado}
      />
      {digital ? <EtiquetaSimulacion modo="franja" detalle="este cobro no movió dinero real" /> : null}

      {cargando ? (
        <View style={estilos.centrado} accessibilityLiveRegion="polite">
          <ActivityIndicator size="large" color={color.primary} />
          <Text style={estilos.cuerpo}>Cargando venta…</Text>
        </View>
      ) : error || !datos ? (
        <View style={estilos.contenido}>
          <Aviso
            tipo="error"
            titulo="No encontramos esta venta."
            accion={{ texto: 'Volver a ventas de hoy', onPress: () => router.replace('/historial') }}
            accionSecundaria={{ texto: 'Reintentar', onPress: reintentar }}
            enfocar
          />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={estilos.contenido}
          scrollEventThrottle={16}
          onScroll={(e) => setDesplazado(e.nativeEvent.contentOffset.y > 0)}
        >
          {desdeHistorial ? null : <BarraPasos pasos={['Foto', 'Revisar', 'Listo']} actual={2} />}

          {/* card filled successContainer (o surfaceContainerHigh si quedó en el teléfono) */}
          <View style={[estilos.cabecera, datos.pendiente ? estilos.cabeceraPendiente : estilos.cabeceraExito]}>
            <MaterialCommunityIcons
              name={datos.pendiente ? 'cloud-upload' : 'check-circle'}
              size={iconos.grande}
              color={datos.pendiente ? color.onSurfaceVariant : color.onSuccessContainer}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text
              style={[estilos.titulo, { color: datos.pendiente ? color.onSurface : color.onSuccessContainer }]}
              accessibilityRole="header"
            >
              {datos.pendiente ? 'Venta guardada en tu teléfono' : '¡Venta registrada!'}
            </Text>
            {datos.pendiente ? (
              <Text style={estilos.cuerpo}>
                Se enviará sola cuando vuelva el internet. El inventario se actualizará en ese momento.
              </Text>
            ) : null}
            <Text style={[estilos.cuerpoCabecera, datos.pendiente ? null : estilos.sobreExito]}>
              Folio {datos.folio} · {fechaCompleta(datos.creadaEn)}
            </Text>
            <Text style={[estilos.cuerpoCabecera, datos.pendiente ? null : estilos.sobreExito]}>
              {digital
                ? `${METODOS_PAGO[datos.metodo].nombre} (simulación)`
                : datos.recibido !== null
                  ? `Efectivo · Te dieron ${formatoMoneda(datos.recibido)} · Cambio ${formatoMoneda(datos.recibido - datos.total)}`
                  : 'Efectivo'}
            </Text>
          </View>

          <View>
            {datos.items.map((i, n) => (
              <FilaProducto
                key={`${i.sku ?? i.nombre}-${n}`}
                modo="soloLectura"
                nombre={i.nombre}
                cantidad={i.cantidad}
                precioUnitario={i.precio_unitario}
                nivel="alta"
              />
            ))}
            <View
              style={estilos.filaTotal}
              accessible
              accessibilityLabel={`Total ${montoParaLector(datos.total)}`}
            >
              <Text style={estilos.etiquetaTotal}>Total</Text>
              <Text style={estilos.total}>{formatoMoneda(datos.total)}</Text>
            </View>
          </View>

          {datos.pendiente ? (
            <View style={estilos.bloque}>
              <View style={estilos.filaIcono}>
                <MaterialCommunityIcons
                  name="package-variant"
                  size={iconos.linea}
                  color={color.onSurfaceVariant}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.subtitulo}>Inventario: pendiente</Text>
              </View>
              <Text style={estilos.secundario}>Se descontará cuando la venta se envíe.</Text>
            </View>
          ) : datos.existencias && datos.existencias.length > 0 ? (
            <View style={estilos.bloque}>
              <View style={estilos.filaIcono}>
                <MaterialCommunityIcons
                  name="package-variant"
                  size={iconos.linea}
                  color={color.onSurfaceVariant}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.subtitulo}>Inventario actualizado · Quedan:</Text>
              </View>
              {datos.existencias.map((e) => (
                <View
                  key={e.sku}
                  style={estilos.filaExistencia}
                  accessible
                  accessibilityLabel={`${e.nombre}, quedan ${e.quedan} piezas${e.bajo ? ', poco' : ''}`}
                >
                  <Text style={[estilos.cuerpo, estilos.flex]}>{e.nombre}</Text>
                  <Text style={estilos.etiqueta}>{e.quedan} pz</Text>
                  {e.bajo ? (
                    <View style={estilos.chipPoco}>
                      <MaterialCommunityIcons
                        name="alert-circle"
                        size={iconos.chico}
                        color={color.onErrorContainer}
                        accessibilityElementsHidden
                        importantForAccessibility="no"
                      />
                      <Text style={estilos.textoPoco}>Poco</Text>
                    </View>
                  ) : null}
                </View>
              ))}
            </View>
          ) : null}

          {!desdeHistorial && datos.duracionSeg !== undefined ? (
            <View style={[estilos.bloque, estilos.bloqueSuperficie]}>
              <View style={estilos.filaIcono}>
                <MaterialCommunityIcons
                  name="timer-outline"
                  size={iconos.linea}
                  color={color.onSurface}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <Text style={estilos.subtitulo}>Esta venta: {duracionLegible(datos.duracionSeg)}</Text>
              </View>
              <Text style={estilos.cuerpo}>
                A mano (libreta y calculadora): ~{duracionLegible(SEGUNDOS_VENTA_MANUAL)}
              </Text>
              <Text style={estilos.secundario}>Tiempo a mano estimado.</Text>
              <Text style={estilos.cuerpo}>Sin sumar a mano · Inventario al día</Text>
            </View>
          ) : null}
        </ScrollView>
      )}

      <View style={estilos.barra}>
        {desdeHistorial ? (
          <Boton texto="Volver" icono="arrow-left" tamano="principal" onPress={cerrar} />
        ) : (
          <>
            <Boton
              texto="Nueva venta con foto"
              icono="camera"
              tamano="principal"
              onPress={() => router.replace('/camara?modo=cobro')}
            />
            <View style={estilos.filaBotones}>
              <Boton
                texto="Ver ventas de hoy"
                variante="outlined"
                anchoCompleto={false}
                style={estilos.flex}
                onPress={() => router.replace('/historial')}
              />
              <Boton texto="Ir a Inicio" variante="text" anchoCompleto={false} onPress={() => router.navigate('/')} />
            </View>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: color.surface },
  flex: { flex: 1 },
  centrado: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.m },
  contenido: { padding: espacio.l, gap: espacio.xl },
  cabecera: { gap: espacio.s, alignItems: 'flex-start', borderRadius: shape.medium, padding: espacio.l },
  cabeceraExito: { backgroundColor: color.successContainer },
  cabeceraPendiente: { backgroundColor: color.surfaceContainerHigh },
  titulo: { ...type.headlineSmall },
  subtitulo: { ...type.titleSmall, color: color.onSurface, flexShrink: 1 },
  cuerpo: { ...type.bodyLarge, color: color.onSurface },
  cuerpoCabecera: { ...type.bodyLarge, color: color.onSurface },
  sobreExito: { color: color.onSuccessContainer },
  secundario: { ...type.bodyLarge, color: color.onSurfaceVariant },
  etiqueta: { ...type.labelLarge, color: color.onSurface },
  filaTotal: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: espacio.m },
  etiquetaTotal: { ...type.titleMedium, color: color.onSurface },
  total: { ...type.headlineLarge, color: color.onSurface },
  // card outlined (inventario)
  bloque: {
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
    borderRadius: shape.medium,
    padding: espacio.l,
    gap: espacio.s,
  },
  // card filled ("Antes vs. ahora")
  bloqueSuperficie: { backgroundColor: color.surfaceContainerHighest, borderWidth: 0 },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  filaExistencia: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, flexWrap: 'wrap' },
  chipPoco: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.s,
    borderRadius: shape.small,
    backgroundColor: color.errorContainer,
  },
  textoPoco: { ...type.labelLarge, color: color.onErrorContainer },
  // barra inferior tonal
  barra: {
    padding: espacio.l,
    gap: tactil.separacion,
    backgroundColor: color.surfaceContainer,
    borderTopWidth: bordes.fino,
    borderTopColor: color.outlineVariant,
  },
  filaBotones: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion, alignItems: 'center' },
});
