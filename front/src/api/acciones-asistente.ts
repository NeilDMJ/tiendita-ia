/**
 * Propuestas del asistente → datos validados y llamadas de negocio.
 * Regla de oro (02-asistente §3): nada se ejecuta aquí sin que el tendero haya tocado Confirmar.
 */
import type { Href } from 'expo-router';
import { z } from 'zod';

import { pedir, USAR_MOCKS } from './cliente';
import {
  DatosAbrirPantalla,
  DatosAprobarPromo,
  DatosConfirmarAlta,
  DatosConfirmarVenta,
  DatosModificarItem,
  type AccionAsistente,
  type PantallaDestino,
  type SolicitudVenta,
} from './esquemas';
import { mockAprobarPromocion } from './mocks/asistente';

export type DatosAccion =
  | { tipo: 'confirmar_venta'; datos: DatosConfirmarVenta }
  | { tipo: 'confirmar_alta'; datos: DatosConfirmarAlta }
  | { tipo: 'aprobar_promo'; datos: DatosAprobarPromo }
  | { tipo: 'abrir_pantalla'; datos: DatosAbrirPantalla }
  | { tipo: 'modificar_item'; datos: DatosModificarItem };

/** Valida `datos` según el tipo. `null` = la propuesta no se puede leer (tarjeta "No pudimos leer esta propuesta"). */
export function parsearDatosAccion(accion: AccionAsistente): DatosAccion | null {
  switch (accion.tipo) {
    case 'confirmar_venta': {
      const r = DatosConfirmarVenta.safeParse(accion.datos);
      return r.success ? { tipo: accion.tipo, datos: r.data } : null;
    }
    case 'confirmar_alta': {
      const r = DatosConfirmarAlta.safeParse(accion.datos);
      return r.success ? { tipo: accion.tipo, datos: r.data } : null;
    }
    case 'aprobar_promo': {
      const r = DatosAprobarPromo.safeParse(accion.datos);
      return r.success ? { tipo: accion.tipo, datos: r.data } : null;
    }
    case 'abrir_pantalla': {
      const r = DatosAbrirPantalla.safeParse(accion.datos);
      return r.success ? { tipo: accion.tipo, datos: r.data } : null;
    }
    case 'modificar_item': {
      const r = DatosModificarItem.safeParse(accion.datos);
      return r.success ? { tipo: accion.tipo, datos: r.data } : null;
    }
  }
}

/** Una venta del chat se puede cobrar directo solo si todos sus productos tienen precio y están en el catálogo. */
export function ventaCompleta(datos: DatosConfirmarVenta) {
  return datos.items.every((i) => i.precio_unitario !== null && i.sku !== null);
}

export function totalVenta(datos: DatosConfirmarVenta) {
  return datos.items.reduce((s, i) => s + i.cantidad * (i.precio_unitario ?? 0), 0);
}

/** `id_local = 'chat-' + accion.id`: confirmar dos veces la misma tarjeta nunca duplica la venta. */
export function solicitudDesdeChat(idAccion: string, datos: DatosConfirmarVenta): SolicitudVenta {
  return {
    id_local: `chat-${idAccion}`,
    imagen_id: null,
    metodo_pago: datos.metodo_pago ?? 'efectivo',
    recibido: null,
    items: datos.items.map((i) => ({
      sku: i.sku,
      nombre: i.nombre,
      cantidad: i.cantidad,
      precio_unitario: i.precio_unitario ?? 0,
      corregido: false,
    })),
  };
}

/** POST /promociones/{id}/aprobar (Fase 6). Con mocks es una SIMULACIÓN: no se publica nada. */
export async function aprobarPromocion(promoId: string): Promise<void> {
  if (USAR_MOCKS) return mockAprobarPromocion(promoId);
  await pedir(`/promociones/${encodeURIComponent(promoId)}/aprobar`, z.unknown(), { method: 'POST' });
}

/** Destinos que ya existen en la app. `null` = pantalla de una fase futura (botón con "Disponible pronto"). */
export const RUTAS_DESTINO: Record<PantallaDestino, Href | null> = {
  cobrar: '/cobrar',
  camara_cobro: '/camara?modo=cobro',
  camara_alta: '/camara?modo=alta',
  camara_ticket: '/camara?modo=ticket',
  inventario: '/inventario',
  historial: '/historial',
  pago: null,
  promociones: null,
};
