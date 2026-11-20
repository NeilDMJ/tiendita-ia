/**
 * Cola de ventas registradas sin conexión. Se envían solas al reconectarse
 * (ver `use-sincronizar-cola.ts`). `id_local` evita duplicados en el reintento.
 */
import type { SolicitudVenta } from '@/api/esquemas';

import { guardarJson, leerJson } from './almacen';

const CLAVE_COLA = 'cola-ventas';
const CLAVE_SINCRONIZADAS = 'ventas-sincronizadas';

export type VentaPendiente = {
  solicitud: SolicitudVenta;
  total: number;
  creada_en: string;
  folioLocal: string;
};

export const PREFIJO_LOCAL = 'local-';

export function leerCola() {
  return leerJson<VentaPendiente[]>(CLAVE_COLA, []);
}

export async function encolarVenta(solicitud: SolicitudVenta, total: number): Promise<VentaPendiente> {
  const cola = await leerCola();
  const existente = cola.find((v) => v.solicitud.id_local === solicitud.id_local);
  if (existente) return existente;
  const pendiente: VentaPendiente = {
    solicitud,
    total,
    creada_en: new Date().toISOString(),
    folioLocal: `Pendiente-${cola.length + 1}`,
  };
  await guardarJson(CLAVE_COLA, [pendiente, ...cola]);
  return pendiente;
}

export async function marcarEnviada(idLocal: string, ventaId: string) {
  const cola = await leerCola();
  await guardarJson(
    CLAVE_COLA,
    cola.filter((v) => v.solicitud.id_local !== idLocal),
  );
  const mapa = await leerJson<Record<string, string>>(CLAVE_SINCRONIZADAS, {});
  mapa[idLocal] = ventaId;
  await guardarJson(CLAVE_SINCRONIZADAS, mapa);
}

/** Si una venta local ya se envió, devuelve su id real. */
export async function idEnviado(idLocal: string): Promise<string | null> {
  const mapa = await leerJson<Record<string, string>>(CLAVE_SINCRONIZADAS, {});
  return mapa[idLocal] ?? null;
}
