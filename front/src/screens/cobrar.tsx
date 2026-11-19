import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { FilaVenta } from '@/components/fila-venta';
import { HojaInferior } from '@/components/hoja-inferior';
import type { NombreIcono } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { useConexion } from '@/hooks/use-conexion';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { bordes, colores, espacio, iconos, medidas, radios, tactil, tipografia } from '@/theme';
import { calcularTotal, plural } from '@/utils/carrito';
import { crearIdLocal } from '@/utils/id';
import { formatoMoneda } from '@/utils/formato-moneda';

const MAX_VENTAS = 5;

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
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${titulo}. ${detalle}`}
      style={({ pressed }) => [estilos.atajo, pressed && estilos.presionado]}
    >
      <MaterialCommunityIcons name={icono} size={iconos.camara} color={colores.texto} />
      <Text style={estilos.atajoTitulo}>{titulo}</Text>
      <Text style={estilos.atajoDetalle}>{detalle}</Text>
    </Pressable>
  );
}

/** Pestaña Cobrar: 1 acción dominante (foto) + atajos + ventas de hoy. */
export function PantallaCobrar() {
  const { carrito, cargado, vaciar, cargarItems } = useCarrito();
  const conectado = useConexion();
  const sinConexion = conectado === false;
  const ventas = useVentasHoy();
  const [confirmarDescarte, setConfirmarDescarte] = useState(false);

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
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      {borrador ? (
        <View style={estilos.borrador}>
          <View style={estilos.filaIcono}>
            <MaterialCommunityIcons name="information" size={iconos.linea} color={colores.texto} />
            <Text style={estilos.subtitulo}>Venta sin terminar</Text>
          </View>
          <Text style={estilos.cuerpo}>
            Tienes una venta de {formatoMoneda(totalBorrador)} sin cobrar (
            {plural(carrito.items.length, 'producto', 'productos')}).
          </Text>
          <Boton texto="Continuar venta" onPress={() => router.push('/revision/cobro')} />
          <Boton texto="Descartar" variante="peligro" icono="trash-can-outline" onPress={() => setConfirmarDescarte(true)} />
        </View>
      ) : null}

      {sinConexion ? <View style={estilos.atajoSolo}>{tarjetaBuscar}</View> : null}

      <View style={estilos.principal}>
        <MaterialCommunityIcons name="camera" size={iconos.grande} color={colores.acento} />
        <Text style={estilos.titulo}>Cobrar con foto</Text>
        <Text style={estilos.secundario}>Pon los productos en el mostrador y tómales una foto.</Text>
        {sinConexion ? (
          <Text style={estilos.secundario}>
            Sin internet la foto no se puede revisar. Puedes cobrar buscando el producto.
          </Text>
        ) : null}
        <Boton texto="Abrir cámara" icono="camera" tamano="principal" onPress={abrirCamara} />
      </View>

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
          variante="texto"
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

      <HojaInferior
        visible={confirmarDescarte}
        titulo="¿Descartar la venta sin terminar?"
        onCerrar={() => setConfirmarDescarte(false)}
        pie={
          <>
            <Boton texto="No, regresar" onPress={() => setConfirmarDescarte(false)} />
            <Boton
              texto="Sí, descartar"
              variante="peligroLleno"
              icono="trash-can-outline"
              onPress={() => {
                vaciar();
                setConfirmarDescarte(false);
              }}
            />
          </>
        }
      >
        <Text style={estilos.cuerpo}>
          Se borrarán {plural(carrito.items.length, 'producto', 'productos')} por{' '}
          {formatoMoneda(totalBorrador)}. Esto no se puede deshacer.
        </Text>
      </HojaInferior>
    </ScrollView>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.l, gap: espacio.xl },
  flex: { flex: 1 },
  presionado: { backgroundColor: colores.superficie },
  borrador: {
    borderWidth: bordes.grueso,
    borderColor: colores.texto,
    borderRadius: radios.medio,
    padding: espacio.l,
    gap: espacio.m,
  },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  principal: {
    borderWidth: bordes.grueso,
    borderColor: colores.acento,
    borderRadius: radios.medio,
    padding: espacio.l,
    gap: espacio.m,
    alignItems: 'center',
  },
  titulo: { ...tipografia.titulo, color: colores.texto, textAlign: 'center' },
  subtitulo: { ...tipografia.subtitulo, color: colores.texto },
  cuerpo: { ...tipografia.cuerpoGrande, color: colores.texto },
  secundario: { ...tipografia.cuerpo, color: colores.textoSecundario, textAlign: 'center' },
  atajos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.l },
  atajoSolo: { flexDirection: 'row' },
  atajo: {
    flexGrow: 1,
    flexBasis: medidas.tarjetaAtajoAncho,
    minHeight: medidas.tarjetaAtajoAlto,
    borderWidth: bordes.fino,
    borderColor: colores.borde,
    borderRadius: radios.medio,
    padding: espacio.m,
    gap: espacio.xs,
  },
  atajoTitulo: { ...tipografia.etiqueta, color: colores.texto },
  atajoDetalle: { ...tipografia.cuerpo, color: colores.textoSecundario },
  cabeceraVentas: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginBottom: -espacio.m },
  lista: { marginHorizontal: -espacio.l, borderTopWidth: bordes.fino, borderTopColor: colores.divisor },
  esqueleto: {
    height: tactil.principal,
    backgroundColor: colores.superficie,
    borderRadius: radios.chico,
    marginBottom: espacio.s,
  },
});
