import type { Producto } from '@/api/esquemas';

/** Filtros activos del listado de inventario. */
export type FiltroInventario = 'todos' | 'poco' | 'agotado' | 'por-caducar';

/** Producto enriquecido con señales visuales de estado calculadas. */
export interface ProductoInventario extends Producto {
  /** Existencia ≤ EXISTENCIA_BAJA y > 0. */
  stockBajo: boolean;
  /** Existencia ≤ 0. */
  agotado: boolean;
  /** Caduca dentro de los próximos 7 días (y no ha caducado aún). */
  porCaducar: boolean;
  /** Ya caducó (fecha en el pasado). */
  caducado: boolean;
  /** Días restantes para caducar; null si no tiene fecha de caducidad. */
  diasParaCaducar: number | null;
}

/** Resumen del inventario para la tarjeta superior. */
export interface ResumenInventario {
  totalProductos: number;
  totalPiezas: number;
  productosConStockBajo: number;
  productosAgotados: number;
  productosPorCaducar: number;
  productosCaducados: number;
  valorEstimado: number;
}
