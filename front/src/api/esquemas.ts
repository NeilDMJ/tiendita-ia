/**
 * Contrato front ↔ back. Mantener sincronizado con back/.
 * Validar SIEMPRE las respuestas con zod: la IA puede devolver datos incompletos.
 */
/* eslint-disable @typescript-eslint/no-redeclare -- patrón zod: esquema y tipo con el mismo nombre */
import { z } from 'zod';

// ---------- Visión ----------
export const ItemDetectado = z.object({
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().nonnegative(),
  precio_unitario: z.number().nonnegative().nullable(),
  confianza: z.number().min(0).max(1),
  caja: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(),
});
export type ItemDetectado = z.infer<typeof ItemDetectado>;

export const RespuestaPosCheckout = z.object({
  items: z.array(ItemDetectado),
  imagen_id: z.string(),
});
export type RespuestaPosCheckout = z.infer<typeof RespuestaPosCheckout>;

export const RespuestaCatalogScan = z.object({
  items: z.array(ItemDetectado),
  categoria: z.string().optional(),
  caducidad_ocr: z.string().nullable().optional(),
});
export type RespuestaCatalogScan = z.infer<typeof RespuestaCatalogScan>;

export const RespuestaReceiptOcr = z.object({
  fecha: z.string().nullable(),
  proveedor: z.string().nullable(),
  total: z.number().nullable(),
  conceptos: z.array(z.object({ descripcion: z.string(), monto: z.number().nullable() })),
  tipo: z.enum(['gasto', 'compra', 'inversion']).nullable(),
  confianza: z.number().min(0).max(1),
});
export type RespuestaReceiptOcr = z.infer<typeof RespuestaReceiptOcr>;

export type ModoCamara = 'cobro' | 'alta' | 'ticket';

// ---------- Asistente ----------
export const RolAsistente = z.enum(['caja', 'bodega', 'cuentas', 'promociones', 'tutor', 'general', 'banco']);
export type RolAsistente = z.infer<typeof RolAsistente>;

export const AccionAsistente = z.object({
  id: z.string(),
  tipo: z.enum(['confirmar_venta', 'confirmar_alta', 'aprobar_promo', 'abrir_pantalla']),
  titulo: z.string(),
  datos: z.unknown(),
});
export type AccionAsistente = z.infer<typeof AccionAsistente>;

/** Guía paso a paso de una operación bancaria (rol 'banco'). Ver docs/DISENO-agente-bancario.md §2. */
export const PasoGuia = z.object({
  n: z.number().int().positive(),
  texto: z.string(),
  pantalla: z.string().optional(),
});
export type PasoGuia = z.infer<typeof PasoGuia>;

export const MensajeAsistente = z.object({
  rol: RolAsistente,
  texto: z.string(),
  acciones: z.array(AccionAsistente).optional(),
  no_resuelto: z.boolean().optional(),
  // Guía bancaria (todos opcionales: el resto de roles no los usa)
  pasos: z.array(PasoGuia).optional(),
  advertencias: z.array(z.string()).optional(),
  guia_verificada: z.boolean().optional(),
  respuestas_rapidas: z.array(z.string()).optional(),
});
export type MensajeAsistente = z.infer<typeof MensajeAsistente>;

// ---------- Tutor de pagos (estado de pantalla, no capturas) ----------
export type EstadoPantalla = {
  pantalla: string;
  paso: number;
  campos: Record<string, 'vacio' | 'lleno' | 'error'>;
  errores_visibles: string[];
  segundos_inactivo: number;
};
