import type { ItemDetectado, ItemVenta, Producto } from '@/api/esquemas';
import { UMBRAL_CONFIANZA } from '@/constants';

import { crearIdLocal } from './id';

export type NivelConfianza = 'alta' | 'baja' | 'falta' | 'manual';

export type ItemEditable = {
  /** id local estable para listas y deshacer */
  clave: string;
  sku: string | null;
  nombre: string;
  /** ≥ 1 en la UI (si viene 0 se fuerza a 1 y queda como 'baja') */
  cantidad: number;
  precio_unitario: number | null;
  /** original del servidor */
  confianza: number;
  origen: 'foto' | 'manual';
  /** true tras "Está bien" o editar → nivel 'manual' */
  revisadoPorUsuario: boolean;
  stockDisponible?: number;
  /** producto suelto fuera de catálogo */
  libre?: boolean;
  /** número que coincide con el recuadro en la foto */
  numero?: number;
  /** caja de detección [x, y, ancho, alto] normalizada 0–1 (si el back la manda) */
  caja?: [number, number, number, number];
  /** mensaje del servidor (409) para esta fila */
  problema?: string;
};

/** falta > manual > baja > alta */
export function nivelDeItem(item: ItemEditable): NivelConfianza {
  if ((item.sku === null && !item.libre) || item.precio_unitario === null || item.problema) return 'falta';
  if (item.revisadoPorUsuario || item.origen === 'manual') return 'manual';
  if (item.confianza < UMBRAL_CONFIANZA) return 'baja';
  return 'alta';
}

export function textoFalta(item: ItemEditable): string {
  if (item.problema) return 'Ajusta la cantidad';
  if (item.sku === null && !item.libre) return 'Elige producto';
  return 'Falta precio';
}

export function desdeDetectado(item: ItemDetectado, indice: number): ItemEditable {
  return {
    clave: crearIdLocal(),
    sku: item.sku,
    nombre: item.nombre,
    cantidad: Math.max(1, item.cantidad),
    precio_unitario: item.precio_unitario,
    confianza: item.cantidad < 1 ? Math.min(item.confianza, UMBRAL_CONFIANZA - 0.01) : item.confianza,
    origen: 'foto',
    revisadoPorUsuario: false,
    numero: indice + 1,
    caja: item.caja,
  };
}

export function desdeProducto(p: Producto, cantidad = 1): ItemEditable {
  return {
    clave: crearIdLocal(),
    sku: p.sku,
    nombre: p.nombre,
    cantidad,
    precio_unitario: p.precio_unitario,
    confianza: 1,
    origen: 'manual',
    revisadoPorUsuario: true,
    stockDisponible: p.existencia,
  };
}

export function calcularTotal(items: ItemEditable[]) {
  let total = 0;
  let sinPrecio = 0;
  for (const i of items) {
    if (i.precio_unitario === null) sinPrecio += 1;
    else total += i.cantidad * i.precio_unitario;
  }
  return { total, sinPrecio };
}

export function aItemVenta(item: ItemEditable): ItemVenta {
  return {
    sku: item.libre ? null : item.sku,
    nombre: item.nombre,
    cantidad: item.cantidad,
    precio_unitario: item.precio_unitario ?? 0,
    libre: item.libre || undefined,
    corregido: item.origen === 'manual' || item.revisadoPorUsuario,
  };
}

export function plural(n: number, singular: string, pluralTexto: string) {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}
