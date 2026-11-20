import { useQuery } from '@tanstack/react-query';

import type { ItemVenta, MetodoPago } from '@/api/esquemas';
import { ventasDeHoy } from '@/api/negocio';
import { leerCola, PREFIJO_LOCAL } from '@/estado/cola-ventas';

export type ResumenVenta = {
  id: string;
  folio: string;
  creadaEn: string;
  productos: number;
  metodo: MetodoPago;
  total: number;
  /** Guardada en el teléfono, pendiente de enviar. */
  pendiente: boolean;
  items: ItemVenta[];
};

/** Ventas de hoy del servidor + las que esperan en la cola local (primero las más nuevas). */
export function useVentasHoy() {
  const remotas = useQuery({ queryKey: ['ventas', 'hoy'], queryFn: ventasDeHoy });
  const locales = useQuery({ queryKey: ['ventas', 'pendientes'], queryFn: leerCola });

  const lista: ResumenVenta[] = [
    ...(locales.data ?? []).map((v) => ({
      id: `${PREFIJO_LOCAL}${v.solicitud.id_local}`,
      folio: v.folioLocal,
      creadaEn: v.creada_en,
      productos: v.solicitud.items.length,
      metodo: v.solicitud.metodo_pago,
      total: v.total,
      pendiente: true,
      items: v.solicitud.items,
    })),
    ...(remotas.data ?? []).map((v) => ({
      id: v.venta_id,
      folio: v.folio,
      creadaEn: v.creada_en,
      productos: v.items.length,
      metodo: v.metodo_pago,
      total: v.total,
      pendiente: false,
      items: v.items,
    })),
  ].sort((a, b) => b.creadaEn.localeCompare(a.creadaEn));

  return {
    lista,
    cargando: remotas.isPending,
    error: remotas.isError && (locales.data ?? []).length === 0 ? remotas.error : null,
    errorParcial: remotas.isError,
    reintentar: () => {
      remotas.refetch();
      locales.refetch();
    },
  };
}
