/**
 * Puente entre la revisión del cobro y "Pregúntale a Caja" (02-asistente §4).
 * La propuesta `modificar_item` se valida contra el carrito ACTUAL antes de aplicarse.
 */
import type { ContextoAsistente, DatosModificarItem, ItemContexto } from '@/api/esquemas';
import type { DatosCarrito } from '@/estado/carrito';

import { calcularTotal, nivelDeItem, type ItemEditable } from './carrito';

const MAX_ITEMS_CONTEXTO = 50;

/** Se arma en el momento de CADA envío (siempre la versión actual de la revisión). */
export function aContextoCobro(carrito: DatosCarrito): ContextoAsistente {
  const items: ItemContexto[] = carrito.items.slice(0, MAX_ITEMS_CONTEXTO).map((item, indice) => ({
    indice,
    clave: item.clave,
    numero_en_foto: item.numero ?? null,
    sku: item.sku,
    nombre: item.nombre,
    cantidad: Math.max(1, item.cantidad),
    precio_unitario: item.precio_unitario,
    existencia: item.stockDisponible ?? null,
    nivel: nivelDeItem(item),
    confianza: Math.min(1, Math.max(0, item.confianza)),
  }));
  return {
    pantalla: 'revision_cobro',
    imagen_id: carrito.imagenId,
    total: calcularTotal(carrito.items).total,
    items,
  };
}

export type ResultadoValidacion =
  | { ok: true; item: ItemEditable }
  /** La fila ya no coincide → tarjeta caducada. */
  | { ok: false; tipo: 'cambio'; mensaje: string }
  /** Cantidad mayor que la existencia → tarjeta en error con "Revisar y editar". */
  | { ok: false; tipo: 'existencia'; mensaje: string; clave: string }
  /** Cambia el producto pero no dice nombre/precio → solo "Revisar y editar". */
  | { ok: false; tipo: 'incompleta'; mensaje: string; clave: string };

export const MOTIVO_VENTA_CAMBIO = 'La venta cambió desde que Caja lo propuso. Pregúntale otra vez.';

export function validarModificacion(items: ItemEditable[], datos: DatosModificarItem): ResultadoValidacion {
  const item = items[datos.indice];
  if (!item || item.clave !== datos.clave || item.nombre !== datos.nombre_actual) {
    return { ok: false, tipo: 'cambio', mensaje: MOTIVO_VENTA_CAMBIO };
  }
  const { cambios } = datos;
  if (cambios.sku !== undefined && (cambios.nombre === undefined || cambios.precio_unitario === undefined)) {
    return { ok: false, tipo: 'incompleta', mensaje: 'Faltan datos para cambiar el producto.', clave: item.clave };
  }
  const cantidad = cambios.cantidad ?? item.cantidad;
  // Si cambia de producto, la existencia conocida ya no aplica.
  const tope = cambios.sku !== undefined && cambios.sku !== item.sku ? undefined : item.stockDisponible;
  if (cantidad < 1 || (tope !== undefined && cantidad > tope)) {
    return {
      ok: false,
      tipo: 'existencia',
      mensaje: `Solo hay ${tope ?? 0} en existencia.`,
      clave: item.clave,
    };
  }
  if (cambios.precio_unitario !== undefined && cambios.precio_unitario < 0) {
    return { ok: false, tipo: 'incompleta', mensaje: 'El precio propuesto no es válido.', clave: item.clave };
  }
  return { ok: true, item };
}

/** Cambios para `actualizarItem` (la fila queda como "Tú lo pusiste": el tendero la confirmó). */
export function aplicarModificacion(item: ItemEditable, datos: DatosModificarItem): Partial<ItemEditable> {
  const { cambios } = datos;
  const cambiaProducto = cambios.sku !== undefined && cambios.sku !== item.sku;
  return {
    ...(cambios.sku !== undefined ? { sku: cambios.sku } : {}),
    ...(cambios.nombre !== undefined ? { nombre: cambios.nombre } : {}),
    ...(cambios.precio_unitario !== undefined ? { precio_unitario: cambios.precio_unitario } : {}),
    ...(cambios.cantidad !== undefined ? { cantidad: cambios.cantidad } : {}),
    ...(cambiaProducto ? { stockDisponible: undefined, libre: false } : {}),
    revisadoPorUsuario: true,
    problema: undefined,
  };
}

/** Copia de los campos que `aplicarModificacion` puede tocar, para Deshacer. */
export function copiaParaDeshacer(item: ItemEditable): Partial<ItemEditable> {
  return {
    sku: item.sku,
    nombre: item.nombre,
    precio_unitario: item.precio_unitario,
    cantidad: item.cantidad,
    stockDisponible: item.stockDisponible,
    libre: item.libre,
    revisadoPorUsuario: item.revisadoPorUsuario,
    problema: item.problema,
  };
}
