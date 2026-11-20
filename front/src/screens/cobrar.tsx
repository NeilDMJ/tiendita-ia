import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState, type ComponentRef } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { Dialogo } from '@/components/dialogo';
import { FabExtendido, RESERVA_FAB } from '@/components/fab-extendido';
import { FilaVenta } from '@/components/fila-venta';
import { Snackbar } from '@/components/snackbar';
import { Tocable } from '@/components/tocable';
import type { NombreIcono } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { useConexion } from '@/hooks/use-conexion';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { bordes, color, espacio, iconos, medidas, shape, tactil, type } from '@/theme';
import { calcularTotal, plural } from '@/utils/carrito';
import { crearIdLocal } from '@/utils/id';
import { formatoMoneda } from '@/utils/formato-moneda';

const MAX_VENTAS = 5;

const SNACKBAR_VENTA_MS = 8_000;

/** Card outlined M3 tocable completa (atajo de cobro). */
function TarjetaAtajo({
  icono,
  titulo,
  detalle,
  onPress,
}: {
  icono: NombreIcono;
  titulo: string;
  detalle: string;
  onPress: () => void;
}) {
  return (
    <Tocable
      onPress={onPress}
      colorContenido={color.onSurface}
      radio={shape.medium}
      accessibilityRole="button"
      accessibilityLabel={`${titulo}. ${detalle}`}
      style={estilos.atajo}
    >
      <MaterialCommunityIcons
        name={icono}
        size={iconos.linea}
        color={color.onSurfaceVariant}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={estilos.atajoTitulo}>{titulo}</Text>
      <Text style={estilos.atajoDetalle}>{detalle}</Text>
    </Tocable>
  );
}

const PASOS_GUIA = ['Pon los productos en el mostrador', 'Toca "Cobrar con foto"', 'Revisa y cobra'];

/** Pestaña Cobrar (01-cobrar §2.1): card guía + atajos + ventas de hoy; la acción dominante es el Extended FAB. */
export function PantallaCobrar() {
  const { carrito, cargado, vaciar, cargarItems, ultimaVenta } = useCarrito();
  const conectado = useConexion();
  const sinConexion = conectado === false;
  const ventas = useVentasHoy();
  const [confirmarDescarte, setConfirmarDescarte] = useState(false);
  const refDescartar = useRef<ComponentRef<typeof View>>(null);
  // Snackbar "Venta registrada" al volver del comprobante (solo una vez por venta).
  const ventaAvisada = useRef<string | null>(null);
  const [ventaReciente, setVentaReciente] = useState<{ id: string; total: number; pendiente: boolean } | null>(null);
  useFocusEffect(
    useCallback(() => {
      if (!ultimaVenta || ventaAvisada.current === ultimaVenta.id) return;
      ventaAvisada.current = ultimaVenta.id;
      setVentaReciente({ id: ultimaVenta.id, total: ultimaVenta.total, pendiente: ultimaVenta.respuesta === null });
    }, [ultimaVenta]),
  );

  const borrador = cargado && carrito.items.length > 0;
  const { total: totalBorrador } = calcularTotal(carrito.items);
  const ultima = ventas.lista[0];

  const abrirCamara = () => router.push('/camara?modo=cobro');
  const buscarProducto = () => router.push('/revision/cobro?agregar=1');
  const repetirUltima = () => {
    if (!ultima) return;
    cargarItems(
      ultima.items.map((i) => ({
        clave: crearIdLocal(),
        sku: i.sku,
        nombre: i.nombre,
        cantidad: i.cantidad,
        precio_unitario: i.precio_unitario,
        confianza: 1,
        origen: 'manual' as const,
        revisadoPorUsuario: true,
        libre: i.libre,
      })),
    );
    router.push('/revision/cobro');
  };

  const tarjetaBuscar = (
    <TarjetaAtajo
      icono="magnify"
      titulo="Buscar producto"
      detalle="Cobrar sin foto"
      onPress={buscarProducto}
    />
  );

  return (
    <View style={estilos.pantalla}>
      <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
        {borrador ? (
          <Aviso
            tipo="info"
            titulo="Venta sin terminar"
            mensaje={`Tienes una venta de ${formatoMoneda(totalBorrador)} sin cobrar (${plural(carrito.items.length, 'producto', 'productos')}).`}
            // el Extended FAB es la única acción filled de la vista
            accion={{ texto: 'Continuar venta', variante: 'tonal', onPress: () => router.push('/revision/cobro') }}
            accionSecundaria={{
              texto: 'Descartar',
              icono: 'trash-can-outline',
              onPress: () => setConfirmarDescarte(true),
            }}
            refAccionSecundaria={refDescartar}
          />
        ) : null}

        {sinConexion ? (
          <>
            <Aviso
              tipo="info"
              titulo="Sin internet la foto no se puede revisar."
              mensaje="Puedes cobrar buscando el producto."
            />
            <View style={estilos.atajoSolo}>{tarjetaBuscar}</View>
          </>
        ) : (
          <View style={estilos.guia}>
            <View style={estilos.filaIcono}>
              <MaterialCommunityIcons
                name="camera"
                size={iconos.linea}
                color={color.onSurface}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.subtitulo} accessibilityRole="header">
                Cobra en 3 pasos
              </Text>
            </View>
            {PASOS_GUIA.map((paso, i) => (
              <View key={paso} style={estilos.pasoGuia}>
                <Text style={estilos.numeroPaso}>{i + 1}</Text>
                <Text style={estilos.textoPaso}>{paso}</Text>
              </View>
            ))}
          </View>
        )}

        <Text style={estilos.subtitulo} accessibilityRole="header">
          Otras formas de cobrar
        </Text>
        <View style={estilos.atajos}>
          {sinConexion ? null : tarjetaBuscar}
          {ultima ? (
            <TarjetaAtajo
              icono="replay"
              titulo="Repetir última venta"
              detalle={formatoMoneda(ultima.total)}
              onPress={repetirUltima}
            />
          ) : null}
        </View>

        <View style={estilos.cabeceraVentas}>
          <Text style={[estilos.subtitulo, estilos.flex]} accessibilityRole="header">
            Ventas de hoy
          </Text>
          <Boton
            texto="Ver todas"
            icono="arrow-right"
            variante="text"
            anchoCompleto={false}
            onPress={() => router.push('/historial')}
          />
        </View>

        {ventas.cargando ? (
          <View accessibilityLiveRegion="polite" accessibilityLabel="Cargando ventas de hoy" accessible>
            {[0, 1, 2].map((i) => (
              <View key={i} style={estilos.esqueleto} />
            ))}
          </View>
        ) : ventas.error && !sinConexion ? (
          <Aviso
            tipo="error"
            titulo="No pudimos traer tus ventas de hoy."
            accion={{ texto: 'Reintentar', icono: 'refresh', onPress: ventas.reintentar }}
          />
        ) : ventas.lista.length === 0 ? (
          <Aviso tipo="info" titulo="Todavía no hay ventas hoy." mensaje="Tu primera venta aparecerá aquí." />
        ) : (
          <View style={estilos.lista}>
            {ventas.lista.slice(0, MAX_VENTAS).map((v) => (
              <FilaVenta key={v.id} venta={v} onPress={() => router.push(`/venta/${v.id}?origen=historial`)} />
            ))}
          </View>
        )}
      </ScrollView>

      <Snackbar
        visible={ventaReciente !== null}
        mensaje={
          ventaReciente
            ? `Venta de ${formatoMoneda(ventaReciente.total)} ${ventaReciente.pendiente ? 'guardada en tu teléfono' : 'registrada'}`
            : ''
        }
        icono={ventaReciente?.pendiente ? 'cloud-upload' : 'check-circle'}
        anuncio={
          ventaReciente
            ? `Venta de ${formatoMoneda(ventaReciente.total)} ${ventaReciente.pendiente ? 'guardada en tu teléfono' : 'registrada'}. Botón Ver disponible.`
            : undefined
        }
        accion={
          ventaReciente
            ? {
                texto: 'Ver',
                onPress: () => {
                  const id = ventaReciente.id;
                  setVentaReciente(null);
                  router.push(`/venta/${id}?origen=historial`);
                },
              }
            : undefined
        }
        duracionMs={SNACKBAR_VENTA_MS}
        onCerrar={() => setVentaReciente(null)}
        separacionInferior={espacio.l + tactil.principal}
      />

      <FabExtendido
        texto="Cobrar con foto"
        icono="camera"
        onPress={abrirCamara}
        accessibilityHint="Abre la cámara para cobrar los productos del mostrador"
      />

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
    </View>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: color.surface },
  contenido: { padding: espacio.l, paddingBottom: RESERVA_FAB + espacio.l, gap: espacio.xl },
  flex: { flex: 1 },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  // card filled de guía (sin botón: el botón es el FAB)
  guia: {
    backgroundColor: color.surfaceContainerHighest,
    borderRadius: shape.medium,
    padding: espacio.l,
    gap: espacio.s,
  },
  pasoGuia: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.m },
  numeroPaso: { ...type.titleSmall, color: color.onSurface, minWidth: espacio.l, textAlign: 'center' },
  textoPaso: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
  subtitulo: { ...type.titleMedium, color: color.onSurface },
  atajos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.l },
  atajoSolo: { flexDirection: 'row' },
  // card outlined tocable
  atajo: {
    flexGrow: 1,
    flexBasis: medidas.tarjetaAtajoAncho,
    minHeight: medidas.tarjetaAtajoAlto,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
    borderRadius: shape.medium,
    backgroundColor: color.surface,
    padding: espacio.l,
    gap: espacio.xs,
  },
  atajoTitulo: { ...type.titleSmall, color: color.onSurface },
  atajoDetalle: { ...type.bodyLarge, color: color.onSurfaceVariant },
  cabeceraVentas: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginBottom: -espacio.m },
  lista: { marginHorizontal: -espacio.l },
  esqueleto: {
    height: medidas.filaVenta - espacio.s,
    backgroundColor: color.surfaceDim,
    borderRadius: shape.small,
    marginBottom: espacio.s,
  },
});
