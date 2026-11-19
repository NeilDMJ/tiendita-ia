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
  /** [x, y, ancho, alto] normalizada 0–1 respecto a la foto */
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
export const RolAsistente = z.enum(['caja', 'bodega', 'cuentas', 'promociones', 'tutor', 'general']);
export type RolAsistente = z.infer<typeof RolAsistente>;

export const AccionAsistente = z.object({
  id: z.string(),
  tipo: z.enum(['confirmar_venta', 'confirmar_alta', 'aprobar_promo', 'abrir_pantalla']),
  titulo: z.string(),
  datos: z.unknown(),
});
export type AccionAsistente = z.infer<typeof AccionAsistente>;

export const MensajeAsistente = z.object({
  rol: RolAsistente,
  texto: z.string(),
  acciones: z.array(AccionAsistente).optional(),
  no_resuelto: z.boolean().optional(),
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

// ---------- Negocio: catálogo y ventas (propuesta de 01-cobrar §5; acordar con back/) ----------
// GET /productos?q=texto&limite=10   y   GET /productos/mas-vendidos?limite=6
export const Producto = z.object({
  sku: z.string(),
  nombre: z.string(),
  precio_unitario: z.number().nonnegative(),
  existencia: z.number().int(), // tope del stepper y aviso "Poco"
});
export type Producto = z.infer<typeof Producto>;

export const MetodoPago = z.enum(['efectivo', 'digital_simulado']);
export type MetodoPago = z.infer<typeof MetodoPago>;

export const ItemVenta = z.object({
  sku: z.string().nullable(), // null solo si libre === true
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_unitario: z.number().nonnegative(),
  libre: z.boolean().optional(), // producto suelto: no descuenta inventario
  corregido: z.boolean(), // útil para medir/reentrenar la visión
});
export type ItemVenta = z.infer<typeof ItemVenta>;

// POST /ventas
export const SolicitudVenta = z.object({
  id_local: z.string(), // id del teléfono → idempotencia (un reintento nunca duplica)
  imagen_id: z.string().nullable(), // de RespuestaPosCheckout, null si fue sin foto
  metodo_pago: MetodoPago,
  recibido: z.number().nullable(),
  items: z.array(ItemVenta),
  duracion_seg: z.number().optional(), // indicador "Antes vs. ahora"
});
export type SolicitudVenta = z.infer<typeof SolicitudVenta>;

export const Existencia = z.object({
  sku: z.string(),
  nombre: z.string(),
  quedan: z.number().int(),
  bajo: z.boolean(),
});
export type Existencia = z.infer<typeof Existencia>;

export const RespuestaVenta = z.object({
  venta_id: z.string(),
  folio: z.string(),
  total: z.number(),
  creada_en: z.string(),
  existencias: z.array(Existencia),
});
export type RespuestaVenta = z.infer<typeof RespuestaVenta>;

/** Cuerpo del 409 de POST /ventas. */
export const ConflictoExistencia = z.object({ sku: z.string(), existencia: z.number().int() });
export type ConflictoExistencia = z.infer<typeof ConflictoExistencia>;

// GET /ventas?dia=hoy  y  GET /ventas/{id}  (PROPUESTA: no está en 01-cobrar §5; acordar con back/)
export const DetalleVenta = z.object({
  venta_id: z.string(),
  folio: z.string(),
  total: z.number(),
  creada_en: z.string(),
  metodo_pago: MetodoPago,
  recibido: z.number().nullable(),
  items: z.array(ItemVenta),
});
export type DetalleVenta = z.infer<typeof DetalleVenta>;
