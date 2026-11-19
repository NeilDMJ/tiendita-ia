import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQueryClient } from '@tanstack/react-query';
import { router, usePreventRemove } from 'expo-router';
import { useEffect, useRef, useState, type ComponentRef } from 'react';
import {
  AccessibilityInfo,
  findNodeHandle,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { esErrorApi } from '@/api/cliente';
import { ConflictoExistencia, type MetodoPago, type SolicitudVenta } from '@/api/esquemas';
import { registrarVenta } from '@/api/negocio';
import { Aviso } from '@/components/aviso';
import { BarraPasos } from '@/components/barra-pasos';
import { Boton } from '@/components/boton';
import { Encabezado } from '@/components/encabezado';
import { FilaProducto } from '@/components/fila-producto';
import { HojaInferior } from '@/components/hoja-inferior';
import { DESHACER_MS } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { encolarVenta, PREFIJO_LOCAL } from '@/estado/cola-ventas';
import { useAccesibilidad } from '@/hooks/use-accesibilidad';
import { useConexion } from '@/hooks/use-conexion';
import { bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';
import {
  aItemVenta,
  calcularTotal,
  desdeProducto,
  nivelDeItem,
  plural,
  textoFalta,
  type ItemEditable,
} from '@/utils/carrito';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';
import { crearIdLocal } from '@/utils/id';

import { FotoDetecciones } from './revision/foto-detecciones';
import { HojaCobro, type ErrorCobro } from './revision/hoja-cobro';
import { HojaEditarProducto, type CambiosProducto } from './revision/hoja-editar-producto';

type Editor = { modo: 'editar'; clave: string } | { modo: 'agregar'; id: string } | null;
type Deshacer = { item: ItemEditable; indice: number } | null;

const PASOS = ['Foto', 'Revisar', 'Listo'];
const ESPERA_ANUNCIO_TOTAL_MS = 600;

const ORDEN_AYUDA = { falta: 0, baja: 1 } as const;

/** Se llama solo al registrar (evento), nunca durante el render. */
function segundosDesde(inicio: number | null): number | undefined {
  return inicio ? Math.round((Date.now() - inicio) / 1000) : undefined;
}

/** Revisa la venta: lista densa editable antes de cobrar. Lo de la IA nunca se guarda sin pasar por aquí. */
export function PantallaRevisionCobro({ abrirAgregar }: { abrirAgregar?: boolean }) {
  const {
    carrito,
    cargado,
    actualizarItem,
    quitarItem,
    restaurarItem,
    agregarItem,
    vaciar,
    setUltimaVenta,
  } = useCarrito();
  const conectado = useConexion();
  const sinConexion = conectado === false;
  const { lectorActivo, reducirMovimiento } = useAccesibilidad();
  const clienteQuery = useQueryClient();

  const [editor, setEditor] = useState<Editor>(abrirAgregar ? { modo: 'agregar', id: crearIdLocal() } : null);
  const [deshacer, setDeshacer] = useState<Deshacer>(null);
  const [verFoto, setVerFoto] = useState(false);
  const [confirmarBorrar, setConfirmarBorrar] = useState(false);
  const [salida, setSalida] = useState<{ repetir: () => void } | null>(null);
  const [saliendo, setSaliendo] = useState(false);
  const [hojaCobro, setHojaCobro] = useState(false);
  const [registrando, setRegistrando] = useState(false);
  const [errorCobro, setErrorCobro] = useState<ErrorCobro | null>(null);
  const [errorExistencia, setErrorExistencia] = useState(false);

  const idLocal = useRef(crearIdLocal());
  const scroll = useRef<ComponentRef<typeof ScrollView>>(null);
  const yAyuda = useRef(0);
  const yFilas = useRef<Record<string, number>>({});
  const refsFilas = useRef<Record<string, ComponentRef<typeof View> | null>>({});

  const items = carrito.items;
  const { total, sinPrecio } = calcularTotal(items);
  const textoTotal = `Total ${montoParaLector(total)}${sinPrecio > 0 ? `, más ${plural(sinPrecio, 'producto', 'productos')} sin precio` : ''}`;
  const [totalAnunciado, setTotalAnunciado] = useState(textoTotal);
  const conNivel = items.map((item) => ({ item, nivel: nivelDeItem(item) }));
  const ayuda = conNivel
    .filter((x) => x.nivel === 'falta' || x.nivel === 'baja')
    .sort((a, b) => ORDEN_AYUDA[a.nivel as 'falta' | 'baja'] - ORDEN_AYUDA[b.nivel as 'falta' | 'baja']);
  const listos = conNivel.filter((x) => x.nivel === 'alta' || x.nivel === 'manual');
  const faltan = conNivel.filter((x) => x.nivel === 'falta');
  const hayCajas = items.some((i) => i.caja);

  // ---------- salir sin cobrar ----------
  const desactivarProteccion = usePreventRemove(items.length > 0 && !saliendo, ({ repeat }) => {
    setSalida({ repetir: repeat });
  });

  function salirA(ruta: '/asistente' | `/venta/${string}`) {
    setSaliendo(true);
    desactivarProteccion();
    if (ruta === '/asistente') router.navigate(ruta);
    else router.replace(ruta);
  }

  // ---------- total anunciado con espera (no en cada toque) ----------
  useEffect(() => {
    const t = setTimeout(() => setTotalAnunciado(textoTotal), ESPERA_ANUNCIO_TOTAL_MS);
    return () => clearTimeout(t);
  }, [textoTotal]);

  // ---------- deshacer: 10 s, sin límite con lector de pantalla ----------
  useEffect(() => {
    if (!deshacer || lectorActivo) return;
    const t = setTimeout(() => setDeshacer(null), DESHACER_MS);
    return () => clearTimeout(t);
  }, [deshacer, lectorActivo]);

  function anunciar(texto: string) {
    AccessibilityInfo.announceForAccessibility(texto);
  }

  function quitar(clave: string) {
    const r = quitarItem(clave);
    if (!r) return;
    setDeshacer(r);
    anunciar(`Quitaste ${r.item.nombre}. Botón Deshacer disponible.`);
  }

  function cambiarCantidad(item: ItemEditable, n: number) {
    setDeshacer(null);
    const resuelto = item.problema && item.stockDisponible !== undefined && n <= item.stockDisponible;
    actualizarItem(item.clave, { cantidad: n, ...(resuelto ? { problema: undefined } : {}) });
  }

  function estaBien(item: ItemEditable) {
    setDeshacer(null);
    actualizarItem(item.clave, { revisadoPorUsuario: true });
    anunciar(`${item.nombre} pasó a Listos`);
  }

  function guardarEdicion(cambios: CambiosProducto) {
    setDeshacer(null);
    if (editor?.modo === 'editar') {
      const antes = items.find((i) => i.clave === editor.clave);
      actualizarItem(editor.clave, { ...cambios, revisadoPorUsuario: true, problema: undefined });
      if (antes && nivelDeItem(antes) !== 'alta' && nivelDeItem(antes) !== 'manual') {
        anunciar(`${cambios.nombre} pasó a Listos`);
      }
    } else {
      const nuevo: ItemEditable = {
        ...desdeProducto({
          sku: cambios.sku ?? '',
          nombre: cambios.nombre,
          precio_unitario: cambios.precio_unitario ?? 0,
          existencia: cambios.stockDisponible ?? 0,
        }),
        sku: cambios.sku,
        stockDisponible: cambios.stockDisponible,
        cantidad: cambios.cantidad,
        libre: cambios.libre,
      };
      agregarItem(nuevo);
      anunciar(`Agregaste ${cambios.nombre}`);
    }
    setEditor(null);
  }

  function irAlPrimerProblema() {
    const primero = faltan[0]?.item;
    if (!primero) return;
    const y = yAyuda.current + (yFilas.current[primero.clave] ?? 0);
    scroll.current?.scrollTo({ y: Math.max(0, y - espacio.l), animated: !reducirMovimiento });
    const ref = refsFilas.current[primero.clave];
    const nodo = ref ? findNodeHandle(ref) : null;
    if (nodo) setTimeout(() => AccessibilityInfo.setAccessibilityFocus(nodo), 300);
  }

  // ---------- registrar venta ----------
  function armarSolicitud(metodo: MetodoPago, recibido: number | null): SolicitudVenta {
    return {
      id_local: idLocal.current,
      imagen_id: carrito.imagenId,
      metodo_pago: metodo,
      recibido,
      items: items.map(aItemVenta),
      duracion_seg: segundosDesde(carrito.inicio),
    };
  }

  async function guardarEnTelefono(solicitud: SolicitudVenta) {
    const pendiente = await encolarVenta(solicitud, total);
    const id = `${PREFIJO_LOCAL}${solicitud.id_local}`;
    setUltimaVenta({
      id,
      solicitud,
      total,
      respuesta: null,
      folioLocal: pendiente.folioLocal,
      creadaEn: pendiente.creada_en,
    });
    await clienteQuery.invalidateQueries({ queryKey: ['ventas'] });
    setHojaCobro(false);
    salirA(`/venta/${id}`);
    vaciar();
  }

  async function registrar(metodo: MetodoPago, recibido: number | null) {
    if (registrando) return;
    const solicitud = armarSolicitud(metodo, recibido);
    setErrorCobro(null);
    setRegistrando(true);
    try {
      if (sinConexion) {
        await guardarEnTelefono(solicitud);
        return;
      }
      const r = await registrarVenta(solicitud);
      setUltimaVenta({ id: r.venta_id, solicitud, total: r.total, respuesta: r, creadaEn: r.creada_en });
      await Promise.all([
        clienteQuery.invalidateQueries({ queryKey: ['ventas'] }),
        clienteQuery.invalidateQueries({ queryKey: ['kpis'] }),
        clienteQuery.invalidateQueries({ queryKey: ['inventario'] }),
        clienteQuery.invalidateQueries({ queryKey: ['productos'] }),
      ]);
      setHojaCobro(false);
      salirA(`/venta/${r.venta_id}`);
      vaciar();
    } catch (e) {
      if (esErrorApi(e) && e.tipo === 'sin_conexion') {
        await guardarEnTelefono(solicitud);
      } else if (esErrorApi(e) && e.tipo === 'sin_existencia') {
        const conflicto = ConflictoExistencia.safeParse(e.detalle);
        if (conflicto.success) {
          const afectado = items.find((i) => i.sku === conflicto.data.sku);
          if (afectado) {
            actualizarItem(afectado.clave, {
              stockDisponible: conflicto.data.existencia,
              problema: `Solo hay ${conflicto.data.existencia} en existencia. Ajusta la cantidad.`,
            });
          }
        }
        setHojaCobro(false);
        setErrorExistencia(true);
      } else if (esErrorApi(e) && e.tipo === 'datos_faltantes') {
        setErrorCobro('datos_faltantes');
      } else {
        setErrorCobro('servidor');
      }
    } finally {
      setRegistrando(false);
    }
  }

  const itemEditando = editor?.modo === 'editar' ? items.find((i) => i.clave === editor.clave) : undefined;
  const nombreBorrar = plural(items.length, 'producto', 'productos');

  function renderFila(item: ItemEditable, nivel: ReturnType<typeof nivelDeItem>, enAyuda: boolean) {
    return (
      <FilaProducto
        key={item.clave}
        nombre={item.nombre}
        precioUnitario={item.precio_unitario}
        cantidad={item.cantidad}
        nivel={nivel}
        textoFalta={textoFalta(item)}
        problema={item.problema}
        maximo={item.stockDisponible}
        numero={hayCajas ? item.numero : undefined}
        onCambiarCantidad={(n) => cambiarCantidad(item, n)}
        onQuitar={() => quitar(item.clave)}
        onEditar={() => setEditor({ modo: 'editar', clave: item.clave })}
        onEstaBien={nivel === 'baja' ? () => estaBien(item) : undefined}
        onLayout={enAyuda ? (e) => (yFilas.current[item.clave] = e.nativeEvent.layout.y) : undefined}
        refTexto={(r) => {
          refsFilas.current[item.clave] = r;
        }}
      />
    );
  }

  return (
    <SafeAreaView edges={['bottom']} style={estilos.pantalla}>
      <Encabezado
        titulo="Revisa la venta"
        onAtras={() => (router.canGoBack() ? router.back() : router.replace('/cobrar'))}
        accionDerecha={{
          texto: 'Caja',
          icono: 'cash-register',
          onPress: () => salirA('/asistente'),
          accessibilityHint: sinConexion
            ? 'Necesita internet'
            : 'Pregúntale a Caja. Tu venta queda guardada como borrador.',
          deshabilitado: sinConexion,
        }}
      />
      <BarraPasos pasos={PASOS} actual={1} />

      <ScrollView ref={scroll} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
        {!cargado ? null : items.length === 0 ? (
          <View style={estilos.vacio}>
            <MaterialCommunityIcons name="cart-outline" size={iconos.grande} color={colores.texto} />
            <Text style={estilos.subtitulo}>No hay productos en esta venta</Text>
            <Boton
              texto="Tomar otra foto"
              icono="camera"
              variante="secundario"
              onPress={() => router.replace('/camara?modo=cobro')}
            />
          </View>
        ) : (
          <>
            <View style={estilos.margen}>
              <Text style={estilos.cuerpo}>
                {carrito.imagenId
                  ? `Encontramos ${plural(items.length, 'producto', 'productos')}.`
                  : `Esta venta tiene ${plural(items.length, 'producto', 'productos')}.`}
              </Text>
              {carrito.imagenUri ? (
                <Boton
                  texto={verFoto ? 'Ocultar foto' : 'Ver foto'}
                  icono="image"
                  variante="texto"
                  anchoCompleto={false}
                  onPress={() => setVerFoto((v) => !v)}
                />
              ) : null}
              {verFoto && carrito.imagenUri ? (
                <FotoDetecciones uri={carrito.imagenUri} items={items} />
              ) : null}
            </View>

            {errorExistencia ? (
              <Aviso
                style={estilos.margen}
                tipo="error"
                titulo="No hay suficiente en existencia"
                mensaje="Ajusta la cantidad del producto marcado y vuelve a cobrar."
                accion={{ texto: 'Ir al producto', onPress: irAlPrimerProblema }}
                onCerrar={() => setErrorExistencia(false)}
                enfocar
              />
            ) : faltan.length > 0 ? (
              <Aviso
                style={estilos.margen}
                tipo="error"
                titulo={`${plural(faltan.length, 'producto necesita', 'productos necesitan')} tu ayuda`}
                accion={{ texto: 'Ir al producto', icono: 'arrow-down', onPress: irAlPrimerProblema }}
              />
            ) : ayuda.length === 0 ? (
              <Aviso
                style={estilos.margen}
                tipo="exito"
                titulo="Todo listo."
                mensaje="Revisa las cantidades y cobra."
              />
            ) : null}

            {ayuda.length > 0 ? (
              <View onLayout={(e) => (yAyuda.current = e.nativeEvent.layout.y)} style={estilos.seccion}>
                <Text style={[estilos.subtitulo, estilos.margen]} accessibilityRole="header">
                  Necesitan tu ayuda ({ayuda.length})
                </Text>
                <View style={estilos.listaAyuda}>{ayuda.map(({ item, nivel }) => renderFila(item, nivel, true))}</View>
              </View>
            ) : null}

            {listos.length > 0 ? (
              <View style={estilos.seccion}>
                <Text style={[estilos.subtitulo, estilos.margen]} accessibilityRole="header">
                  Listos ({listos.length})
                </Text>
                <View>{listos.map(({ item, nivel }) => renderFila(item, nivel, false))}</View>
              </View>
            ) : null}
          </>
        )}

        <View style={[estilos.margen, estilos.accionesLista]}>
          {items.length > 0 ? (
            <Boton
              texto="Agregar otro producto"
              icono="plus"
              variante="secundario"
              onPress={() => setEditor({ modo: 'agregar', id: crearIdLocal() })}
            />
          ) : null}
          <Boton
            texto="¿Dudas? Pregúntale a Caja"
            icono="cash-register"
            variante="texto"
            deshabilitado={sinConexion}
            motivoDeshabilitado="Necesita internet"
            accessibilityHint="Abre el asistente. Tu venta queda guardada como borrador."
            onPress={() => salirA('/asistente')}
          />
          {items.length > 0 ? (
            <Boton
              texto="Empezar de nuevo"
              icono="delete-outline"
              variante="peligro"
              onPress={() => setConfirmarBorrar(true)}
            />
          ) : null}
        </View>
      </ScrollView>

      {/* ---------- Barra fija inferior ---------- */}
      <View style={estilos.barra}>
        {deshacer ? (
          <View style={estilos.franjaDeshacer} accessibilityLiveRegion="polite">
            <MaterialCommunityIcons name="undo" size={iconos.linea} color={colores.texto} />
            <Text style={estilos.textoDeshacer}>Quitaste “{deshacer.item.nombre}”.</Text>
            <Boton
              texto="Deshacer"
              variante="secundario"
              anchoCompleto={false}
              onPress={() => {
                restaurarItem(deshacer.item, deshacer.indice);
                anunciar(`${deshacer.item.nombre} regresó a la venta`);
                setDeshacer(null);
              }}
            />
          </View>
        ) : null}
        <View
          style={estilos.filaTotal}
          accessible
          accessibilityLabel={totalAnunciado}
          accessibilityLiveRegion="polite"
        >
          <Text style={estilos.etiqueta}>Total ({plural(items.length, 'producto', 'productos')})</Text>
          <Text style={estilos.total}>{formatoMoneda(total)}</Text>
        </View>
        {sinPrecio > 0 ? (
          <View style={estilos.filaSinPrecio}>
            <MaterialCommunityIcons name="alert-circle" size={iconos.linea} color={colores.peligro} />
            <Text style={estilos.textoSinPrecio}>+ {plural(sinPrecio, 'producto', 'productos')} sin precio</Text>
          </View>
        ) : null}
        {items.length === 0 ? (
          <Boton
            texto="Agregar producto"
            icono="plus"
            tamano="principal"
            onPress={() => setEditor({ modo: 'agregar', id: crearIdLocal() })}
          />
        ) : faltan.length > 0 ? (
          <Boton
            texto={`Corrige ${plural(faltan.length, 'producto', 'productos')} para cobrar`}
            icono="arrow-up"
            variante="secundario"
            tamano="principal"
            accessibilityHint="Te lleva al primer producto con problema"
            onPress={irAlPrimerProblema}
          />
        ) : (
          <Boton
            texto={`Cobrar ${formatoMoneda(total)}`}
            icono="cash-register"
            tamano="principal"
            onPress={() => {
              setErrorCobro(null);
              setHojaCobro(true);
            }}
          />
        )}
      </View>

      {/* ---------- Hojas ---------- */}
      {editor ? (
        <HojaEditarProducto
          key={editor.modo === 'editar' ? editor.clave : editor.id}
          visible
          item={itemEditando}
          onCerrar={() => setEditor(null)}
          onGuardar={guardarEdicion}
          onQuitar={
            itemEditando
              ? () => {
                  setEditor(null);
                  quitar(itemEditando.clave);
                }
              : undefined
          }
        />
      ) : null}

      <HojaCobro
        visible={hojaCobro}
        total={total}
        cargando={registrando}
        error={errorCobro}
        onCerrar={() => setHojaCobro(false)}
        onRegistrar={registrar}
        onGuardarDespues={(metodo, recibido) => guardarEnTelefono(armarSolicitud(metodo, recibido))}
        onIrAlProducto={() => {
          setHojaCobro(false);
          irAlPrimerProblema();
        }}
      />

      <HojaInferior
        visible={confirmarBorrar}
        titulo={`¿Borrar los ${nombreBorrar}?`}
        onCerrar={() => setConfirmarBorrar(false)}
        pie={
          <>
            <Boton texto="No, regresar" onPress={() => setConfirmarBorrar(false)} />
            <Boton
              texto="Sí, borrar"
              icono="trash-can-outline"
              variante="peligroLleno"
              onPress={() => {
                vaciar();
                setDeshacer(null);
                setConfirmarBorrar(false);
                anunciar('Se borraron los productos de la venta');
              }}
            />
          </>
        }
      >
        <Text style={estilos.cuerpo}>Se quitarán todos los productos de esta venta.</Text>
      </HojaInferior>

      <HojaInferior
        visible={salida !== null}
        titulo="¿Salir sin cobrar?"
        onCerrar={() => setSalida(null)}
        pie={
          <>
            <Boton texto="Seguir revisando" onPress={() => setSalida(null)} />
            <Boton
              texto="Salir y guardar borrador"
              variante="secundario"
              onPress={() => {
                const s = salida;
                setSalida(null);
                setSaliendo(true);
                s?.repetir();
              }}
            />
            <Boton
              texto="Descartar venta"
              icono="trash-can-outline"
              variante="peligro"
              onPress={() => {
                const s = salida;
                setSalida(null);
                setSaliendo(true);
                vaciar();
                s?.repetir();
              }}
            />
          </>
        }
      >
        <Text style={estilos.cuerpo}>Guardamos esta venta como borrador para que la termines después.</Text>
      </HojaInferior>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { paddingTop: espacio.s, paddingBottom: espacio.xl, gap: espacio.l },
  margen: { marginHorizontal: espacio.l },
  seccion: { gap: espacio.s },
  listaAyuda: { marginHorizontal: espacio.s },
  vacio: { alignItems: 'center', gap: espacio.m, padding: espacio.xl },
  cuerpo: { ...tipografia.cuerpoGrande, color: colores.texto },
  subtitulo: { ...tipografia.subtitulo, color: colores.texto },
  etiqueta: { ...tipografia.etiqueta, color: colores.texto, flex: 1 },
  accionesLista: { gap: tactil.separacion },
  barra: {
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    gap: espacio.s,
    backgroundColor: colores.superficie,
    borderTopWidth: bordes.grueso,
    borderTopColor: colores.texto,
  },
  franjaDeshacer: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: espacio.s,
    paddingBottom: espacio.s,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.borde,
    borderRadius: radios.recto,
  },
  textoDeshacer: { ...tipografia.cuerpo, color: colores.texto, flex: 1 },
  filaTotal: { flexDirection: 'row', alignItems: 'center', gap: espacio.m },
  total: { ...tipografia.montoGrande, color: colores.texto, fontVariant: ['tabular-nums'] },
  filaSinPrecio: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoSinPrecio: { ...tipografia.etiqueta, color: colores.peligro },
});
