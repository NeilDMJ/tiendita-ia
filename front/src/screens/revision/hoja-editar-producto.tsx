import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import type { Producto } from '@/api/esquemas';
import { buscarProductos, masVendidos } from '@/api/negocio';
import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { Campo } from '@/components/campo';
import { HojaInferior } from '@/components/hoja-inferior';
import { StepperCantidad } from '@/components/stepper-cantidad';
import { Tocable } from '@/components/tocable';
import { EXISTENCIA_BAJA } from '@/constants';
import { useConexion } from '@/hooks/use-conexion';
import { bordes, color, espacio, iconos, pesoActivo, shape, tactil, type } from '@/theme';
import type { ItemEditable } from '@/utils/carrito';
import { formatoMoneda, leerMonto, montoParaLector } from '@/utils/formato-moneda';

export type CambiosProducto = Pick<
  ItemEditable,
  'sku' | 'nombre' | 'precio_unitario' | 'cantidad' | 'stockDisponible' | 'libre'
>;

export interface HojaEditarProductoProps {
  visible: boolean;
  /** Sin item = "Agregar producto". */
  item?: ItemEditable;
  onCerrar: () => void;
  onGuardar: (cambios: CambiosProducto) => void;
  onQuitar?: () => void;
}

type Seleccion = { sku: string; nombre: string; existencia?: number } | null;

/** List item M3 de 2 líneas con radio (opción del catálogo). */
function FilaSugerencia({ producto, onPress }: { producto: Producto; onPress: () => void }) {
  const poco = producto.existencia <= EXISTENCIA_BAJA;
  return (
    <Tocable
      onPress={onPress}
      colorContenido={color.onSurface}
      accessibilityRole="radio"
      accessibilityState={{ checked: false }}
      accessibilityLabel={`${producto.nombre}, ${montoParaLector(producto.precio_unitario)}, ${producto.existencia} en existencia${poco ? ', poco' : ''}`}
      style={estilos.sugerencia}
    >
      <MaterialCommunityIcons
        name="radiobox-blank"
        size={iconos.linea}
        color={color.outline}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <View style={estilos.flex}>
        <Text style={estilos.nombreSugerencia}>{producto.nombre}</Text>
        <Text style={estilos.secundario}>
          {formatoMoneda(producto.precio_unitario)} · {producto.existencia} en existencia
          {poco ? ' · Poco' : ''}
        </Text>
      </View>
      <View style={estilos.divisor} />
    </Tocable>
  );
}

/** Hoja para corregir o agregar un producto: buscador del catálogo, precio y cantidad. */
export function HojaEditarProducto({ visible, item, onCerrar, onGuardar, onQuitar }: HojaEditarProductoProps) {
  const agregando = !item;
  const conectado = useConexion();
  const [seleccion, setSeleccion] = useState<Seleccion>(
    item?.sku ? { sku: item.sku, nombre: item.nombre, existencia: item.stockDisponible } : null,
  );
  const [libre, setLibre] = useState(item?.libre ?? false);
  const [busqueda, setBusqueda] = useState(item && !item.sku && !item.libre ? item.nombre : '');
  const [consulta, setConsulta] = useState(busqueda);
  const [nombreLibre, setNombreLibre] = useState(item?.libre ? item.nombre : '');
  const [precio, setPrecio] = useState(item?.precio_unitario != null ? item.precio_unitario.toFixed(2) : '');
  const [cantidad, setCantidad] = useState(item?.cantidad ?? 1);
  const [tocado, setTocado] = useState({ producto: false, precio: false, nombre: false });
  const [intentoGuardar, setIntentoGuardar] = useState(false);

  // espera breve para no buscar en cada tecla
  useEffect(() => {
    const t = setTimeout(() => setConsulta(busqueda), 300);
    return () => clearTimeout(t);
  }, [busqueda]);

  const buscando = !seleccion && !libre;
  const sugerencias = useQuery({
    queryKey: ['productos', 'buscar', consulta],
    queryFn: () => buscarProductos(consulta),
    enabled: visible && buscando && consulta.trim().length > 0,
  });
  const populares = useQuery({
    queryKey: ['productos', 'mas-vendidos'],
    queryFn: () => masVendidos(6),
    enabled: visible && buscando && agregando,
  });

  const precioNumero = leerMonto(precio);
  const errorPrecio =
    precio.trim() === '' ? 'Escribe el precio. Ej. 18.50' : precioNumero === null ? 'Escribe solo números. Ej. 18.50' : precioNumero === 0 ? 'El precio no puede ser 0' : null;
  const errorNombre = libre && nombreLibre.trim() === '' ? 'Escribe cómo se llama el producto' : null;
  const faltaProducto = !seleccion && !libre;

  const pendientes: string[] = [];
  if (faltaProducto) pendientes.push('elegir el producto');
  if (errorNombre) pendientes.push('escribir el nombre');
  if (errorPrecio) pendientes.push('poner el precio');
  const motivo = pendientes.length > 0 ? `Falta ${pendientes.join(' y ')}` : undefined;

  function elegir(p: Producto) {
    setSeleccion({ sku: p.sku, nombre: p.nombre, existencia: p.existencia });
    setPrecio(p.precio_unitario.toFixed(2));
    setLibre(false);
    if (cantidad > p.existencia && p.existencia > 0) setCantidad(p.existencia);
  }

  function guardar() {
    setIntentoGuardar(true);
    if (motivo || precioNumero === null) return;
    onGuardar({
      sku: libre ? null : (seleccion?.sku ?? null),
      nombre: libre ? nombreLibre.trim() : (seleccion?.nombre ?? ''),
      precio_unitario: precioNumero,
      cantidad,
      stockDisponible: libre ? undefined : seleccion?.existencia,
      libre: libre || undefined,
    });
  }

  const mostrar = (campo: keyof typeof tocado) => tocado[campo] || intentoGuardar;
  const lista = consulta.trim().length > 0 ? sugerencias : agregando ? populares : null;

  return (
    <HojaInferior
      visible={visible}
      titulo={agregando ? 'Agregar producto' : 'Editar producto'}
      onCerrar={onCerrar}
      pie={
        <>
          {motivo ? (
            <View style={estilos.motivo}>
              <MaterialCommunityIcons
                name="information"
                size={iconos.linea}
                color={color.onSurfaceVariant}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.secundario}>{motivo}.</Text>
            </View>
          ) : null}
          <Boton
            texto={agregando ? 'Agregar a la venta' : 'Guardar cambios'}
            tamano="principal"
            onPress={guardar}
            deshabilitado={Boolean(motivo)}
            motivoDeshabilitado={motivo}
          />
        </>
      }
    >
      {/* Producto */}
      {seleccion && !libre ? (
        <View style={estilos.bloque}>
          <Text style={estilos.etiqueta}>Producto *</Text>
          <View
            style={estilos.elegido}
            accessible
            accessibilityRole="radio"
            accessibilityState={{ checked: true }}
            accessibilityLabel={`${seleccion.nombre}, elegido${seleccion.existencia !== undefined ? `, ${seleccion.existencia} en existencia` : ''}`}
          >
            <MaterialCommunityIcons name="radiobox-marked" size={iconos.linea} color={color.primary} />
            <View style={estilos.flex}>
              <Text style={[estilos.nombreSugerencia, estilos.textoElegido]}>{seleccion.nombre}</Text>
              {seleccion.existencia !== undefined ? (
                <Text style={estilos.secundarioElegido}>{seleccion.existencia} en existencia</Text>
              ) : null}
            </View>
            <Text style={estilos.marcaElegido}>Elegido</Text>
          </View>
          <Boton
            texto="Cambiar producto"
            icono="magnify"
            variante="text"
            anchoCompleto={false}
            onPress={() => {
              setBusqueda(seleccion.nombre.split(' ')[0] ?? '');
              setSeleccion(null);
            }}
          />
        </View>
      ) : libre ? (
        <View style={estilos.bloque}>
          <Campo
            etiqueta="Nombre del producto suelto"
            valor={nombreLibre}
            onCambiar={setNombreLibre}
            obligatorio
            autoFocus
            placeholder="Ej. Dulce de tamarindo"
            ayuda="No se descuenta del inventario."
            error={mostrar('nombre') ? errorNombre : null}
            onBlur={() => setTocado((t) => ({ ...t, nombre: true }))}
          />
          <Boton
            texto="Mejor buscar en mi lista"
            icono="magnify"
            variante="text"
            anchoCompleto={false}
            onPress={() => setLibre(false)}
          />
        </View>
      ) : (
        <View style={estilos.bloque}>
          <Campo
            etiqueta="Producto"
            valor={busqueda}
            onCambiar={setBusqueda}
            obligatorio
            icono="magnify"
            autoFocus
            placeholder="Ej. galletas"
            error={(mostrar('producto') || intentoGuardar) && faltaProducto ? 'Elige un producto de la lista' : null}
            onBlur={() => setTocado((t) => ({ ...t, producto: true }))}
          />
          {agregando && consulta.trim() === '' ? <Text style={estilos.etiqueta}>Más vendidos</Text> : null}
          {lista?.isFetching ? (
            <View style={estilos.filaIcono} accessibilityLiveRegion="polite">
              <ActivityIndicator color={color.primary} />
              <Text style={estilos.cuerpo}>Buscando…</Text>
            </View>
          ) : lista?.isError ? (
            conectado === false ? (
              <Aviso
                tipo="sinConexion"
                titulo="Sin internet solo puedes buscar productos que ya cargaste antes."
                accion={{ texto: 'Cobrar como producto suelto', onPress: () => setLibre(true) }}
              />
            ) : (
              <Aviso
                tipo="error"
                titulo="No pudimos buscar."
                accion={{ texto: 'Reintentar', icono: 'refresh', onPress: () => lista.refetch() }}
              />
            )
          ) : lista?.data && lista.data.length === 0 && consulta.trim() !== '' ? (
            <Text style={estilos.cuerpo}>No encontramos “{consulta}” en tu lista.</Text>
          ) : (
            <View>
              {(lista?.data ?? []).map((p) => (
                <FilaSugerencia key={p.sku} producto={p} onPress={() => elegir(p)} />
              ))}
            </View>
          )}
          <Boton
            texto="No está en mi lista: cobrar como producto suelto"
            variante="text"
            onPress={() => {
              setLibre(true);
              setNombreLibre(busqueda);
            }}
          />
        </View>
      )}

      <Campo
        etiqueta="Precio por pieza"
        valor={precio}
        onCambiar={setPrecio}
        tipo="moneda"
        prefijo="$"
        obligatorio
        autoFocus={Boolean(item?.sku) && item?.precio_unitario == null}
        placeholder="0.00"
        error={mostrar('precio') ? errorPrecio : null}
        onBlur={() => setTocado((t) => ({ ...t, precio: true }))}
      />

      <View style={estilos.bloque}>
        <Text style={estilos.etiqueta}>Cantidad</Text>
        <StepperCantidad
          valor={cantidad}
          onCambiar={setCantidad}
          maximo={libre ? undefined : seleccion?.existencia}
          nombreProducto={libre ? nombreLibre || 'producto' : (seleccion?.nombre ?? 'producto')}
        />
      </View>

      {onQuitar ? (
        <Boton texto="Quitar de la venta" icono="trash-can-outline" variante="outlinedError" onPress={onQuitar} />
      ) : null}
    </HojaInferior>
  );
}

const estilos = StyleSheet.create({
  flex: { flex: 1 },
  bloque: { gap: espacio.s },
  etiqueta: { ...type.titleSmall, color: color.onSurface },
  cuerpo: { ...type.bodyLargePlus, color: color.onSurface },
  secundario: { ...type.bodyLarge, color: color.onSurfaceVariant, flexShrink: 1 },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  motivo: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  // opción elegida: primaryContainer + radio relleno + "Elegido"
  elegido: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    minHeight: tactil.principal,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    borderRadius: shape.medium,
    backgroundColor: color.primaryContainer,
  },
  textoElegido: { color: color.onPrimaryContainer },
  secundarioElegido: { ...type.bodyLarge, color: color.onPrimaryContainer },
  marcaElegido: { ...type.labelLarge, color: color.onPrimaryContainer, ...pesoActivo },
  sugerencia: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.l,
    paddingVertical: espacio.s,
    paddingHorizontal: espacio.s,
  },
  divisor: {
    position: 'absolute',
    left: espacio.s,
    right: 0,
    bottom: 0,
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
  },
  nombreSugerencia: { ...type.titleMedium, color: color.onSurface },
});
