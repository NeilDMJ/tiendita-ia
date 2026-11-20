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

/** 02-asistente §5.2. `modificar_item` solo llega con contexto `revision_cobro`. */
export const TipoAccion = z.enum([
  'confirmar_venta',
  'confirmar_alta',
  'aprobar_promo',
  'abrir_pantalla',
  'modificar_item',
]);
export type TipoAccion = z.infer<typeof TipoAccion>;

export const AccionAsistente = z.object({
  id: z.string(),
  tipo: TipoAccion,
  /** Texto del botón/tarjeta, en lenguaje de tienda. */
  titulo: z.string(),
  /** Se valida POR TIPO al mostrar (`parsearDatosAccion`): una acción mal formada no tira toda la respuesta. */
  datos: z.unknown(),
  vence_en: z.string().optional(),
});
export type AccionAsistente = z.infer<typeof AccionAsistente>;

export const MensajeAsistente = z.object({
  rol: RolAsistente,
  texto: z.string(),
  acciones: z.array(AccionAsistente).max(3).optional(),
  no_resuelto: z.boolean().optional(),
  /** Chips de seguimiento (máx. 3). */
  sugerencias: z.array(z.string().max(60)).max(3).optional(),
});
export type MensajeAsistente = z.infer<typeof MensajeAsistente>;

// ---------- Asistente: solicitud (02-asistente §5.1) ----------
export const PantallaAsistente = z.enum(['asistente', 'revision_cobro', 'inicio', 'inventario', 'pago']);
export type PantallaAsistente = z.infer<typeof PantallaAsistente>;

/** = `nivelDeItem()` del front. */
export const NivelItem = z.enum(['alta', 'baja', 'falta', 'manual']);
export type NivelItem = z.infer<typeof NivelItem>;

export const ItemContexto = z.object({
  /** Posición en `carrito.items` (orden del servidor, no el visual). */
  indice: z.number().int().nonnegative(),
  /** id local estable de la fila */
  clave: z.string(),
  /** Número que ve el tendero en la fila ("el producto 1"). */
  numero_en_foto: z.number().int().positive().nullable(),
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_unitario: z.number().nonnegative().nullable(),
  existencia: z.number().int().nullable(),
  nivel: NivelItem,
  /** Solo para el back; nunca se muestra. */
  confianza: z.number().min(0).max(1),
});
export type ItemContexto = z.infer<typeof ItemContexto>;

export const ContextoAsistente = z.discriminatedUnion('pantalla', [
  z.object({ pantalla: z.literal('asistente') }),
  z.object({ pantalla: z.literal('inicio') }),
  z.object({ pantalla: z.literal('inventario') }),
  z.object({ pantalla: z.literal('pago') }),
  z.object({
    pantalla: z.literal('revision_cobro'),
    imagen_id: z.string().nullable(),
    total: z.number().nonnegative(),
    items: z.array(ItemContexto).max(50),
  }),
]);
export type ContextoAsistente = z.infer<typeof ContextoAsistente>;

export const TurnoHistorial = z.object({
  autor: z.enum(['tendero', 'asistente']),
  /** Solo si autor = asistente. */
  rol: RolAsistente.optional(),
  texto: z.string().max(2000),
});
export type TurnoHistorial = z.infer<typeof TurnoHistorial>;

// POST /asistente/mensaje
export const SolicitudAsistente = z.object({
  /** id del teléfono: un Reintentar no duplica la respuesta. */
  id_mensaje: z.string(),
  texto: z.string().trim().min(1).max(500),
  /** Últimos 12 turnos, sin tarjetas. */
  historial: z.array(TurnoHistorial).max(12),
  /** Ausente = { pantalla: 'asistente' }. */
  contexto: ContextoAsistente.optional(),
});
export type SolicitudAsistente = z.infer<typeof SolicitudAsistente>;

// ---------- Asistente: `datos` por tipo de acción (02-asistente §5.3) ----------
export const ItemPropuesto = z.object({
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  /** null → la tarjeta obliga a "Revisar y editar". */
  precio_unitario: z.number().nonnegative().nullable(),
});
export type ItemPropuesto = z.infer<typeof ItemPropuesto>;

export const DatosConfirmarAlta = z.object({
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_venta: z.number().nonnegative().nullable(),
  /** 'AAAA-MM-DD' */
  caducidad: z.string().nullable(),
});
export type DatosConfirmarAlta = z.infer<typeof DatosConfirmarAlta>;

export const DatosAprobarPromo = z.object({
  promo_id: z.string(),
  producto: z.string(),
  copy: z.string().max(280),
  precio_promo: z.number().nonnegative(),
  /** 'AAAA-MM-DD' */
  vigente_hasta: z.string(),
  video_url: z.string().nullable(),
  /** true → chip "Simulación" obligatorio */
  simulacion: z.boolean(),
});
export type DatosAprobarPromo = z.infer<typeof DatosAprobarPromo>;

export const PantallaDestino = z.enum([
  'cobrar',
  'camara_cobro',
  'camara_alta',
  'camara_ticket',
  'inventario',
  'historial',
  'pago',
  'promociones',
]);
export type PantallaDestino = z.infer<typeof PantallaDestino>;

export const DatosAbrirPantalla = z.object({ pantalla: PantallaDestino });
export type DatosAbrirPantalla = z.infer<typeof DatosAbrirPantalla>;

export const DatosModificarItem = z.object({
  indice: z.number().int().nonnegative(),
  /** Debe coincidir con la fila actual. */
  clave: z.string(),
  /** Segunda verificación + texto "Antes". */
  nombre_actual: z.string(),
  cambios: z
    .object({
      sku: z.string().nullable().optional(),
      nombre: z.string().optional(),
      precio_unitario: z.number().nonnegative().optional(),
      cantidad: z.number().int().positive().optional(),
    })
    .refine((c) => Object.keys(c).length > 0, 'sin cambios'),
});
export type DatosModificarItem = z.infer<typeof DatosModificarItem>;

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
/** Unidad de venta. `pieza` → cantidades enteras; `kg`/`litro` → granel, admite decimales. */
export const UnidadMedida = z.enum(['pieza', 'kg', 'litro']);
export type UnidadMedida = z.infer<typeof UnidadMedida>;

export const Producto = z.object({
  sku: z.string(),
  nombre: z.string(),
  precio_unitario: z.number().nonnegative(), // por unidad (pieza, kg o litro)
  existencia: z.number(), // tope del stepper y aviso "Poco"; decimal si es granel
  unidad: UnidadMedida.optional(), // sin unidad = 'pieza'
});
export type Producto = z.infer<typeof Producto>;

/**
 * Método con el que paga el cliente. Los digitales son SIMULACIÓN en la demo:
 * el back guarda `pago.simulado = true` y la UI muestra la etiqueta "Simulación".
 */
export const MetodoPago = z.enum(['efectivo', 'transferencia', 'qr', 'tarjeta']);
export type MetodoPago = z.infer<typeof MetodoPago>;

export const esPagoDigital = (m: MetodoPago) => m !== 'efectivo';

/** Estado del pago (solo avanza). Efectivo nace `conciliado`; los digitales, `pendiente`. */
export const EstadoPago = z.enum(['pendiente', 'enviado', 'recibido', 'conciliado']);
export type EstadoPago = z.infer<typeof EstadoPago>;

/** `datos` de la acción `confirmar_venta` del asistente (02-asistente §5.3). */
export const DatosConfirmarVenta = z.object({
  items: z.array(ItemPropuesto).min(1).max(50),
  /** default 'efectivo' */
  metodo_pago: MetodoPago.optional(),
});
export type DatosConfirmarVenta = z.infer<typeof DatosConfirmarVenta>;

// POST /inventario/altas (PROPUESTA de 02-asistente §3.1; acordar en Fase 4 con back/)
export const RespuestaAlta = z.object({ sku: z.string(), nombre: z.string(), quedan: z.number() });
export type RespuestaAlta = z.infer<typeof RespuestaAlta>;

export const ItemVenta = z.object({
  sku: z.string().nullable(), // null solo si libre === true
  nombre: z.string(),
  // Entera si el producto es por pieza (lo valida el back con producto.unidad); decimal si es granel.
  cantidad: z.number().positive(),
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
  /** Hora del teléfono en que ocurrió la venta (importa en las que se envían después). */
  ocurrida_en: z.string().optional(),
  /**
   * true = la venta se hizo sin conexión y llega desde la cola. Ya ocurrió, así que el back
   * la registra aunque la existencia quede negativa y genera una alerta (no responde 409).
   */
  fuera_de_linea: z.boolean().optional(),
});
export type SolicitudVenta = z.infer<typeof SolicitudVenta>;

export const Existencia = z.object({
  sku: z.string(),
  nombre: z.string(),
  quedan: z.number(), // puede ser negativa solo tras una venta fuera_de_linea
  bajo: z.boolean(),
});
export type Existencia = z.infer<typeof Existencia>;

export const RespuestaVenta = z.object({
  venta_id: z.string(),
  folio: z.string(),
  total: z.number(),
  creada_en: z.string(),
  estado_pago: EstadoPago.optional(),
  existencias: z.array(Existencia),
});
export type RespuestaVenta = z.infer<typeof RespuestaVenta>;

/** Cuerpo del 409 de POST /ventas (solo ventas en línea). */
export const ConflictoExistencia = z.object({ sku: z.string(), existencia: z.number() });
export type ConflictoExistencia = z.infer<typeof ConflictoExistencia>;

// GET /ventas?dia=hoy  y  GET /ventas/{id}  (PROPUESTA: no está en 01-cobrar §5; acordar con back/)
export const DetalleVenta = z.object({
  venta_id: z.string(),
  folio: z.string(),
  total: z.number(),
  creada_en: z.string(),
  metodo_pago: MetodoPago,
  estado_pago: EstadoPago.optional(),
  recibido: z.number().nullable(),
  items: z.array(ItemVenta),
});
export type DetalleVenta = z.infer<typeof DetalleVenta>;
