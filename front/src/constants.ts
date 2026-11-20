import type { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';

import type { MetodoPago, RolAsistente } from '@/api/esquemas';

export type NombreIcono = ComponentProps<typeof MaterialCommunityIcons>['name'];

/** Por debajo de este valor la fila se marca "Revisa" (icono + texto, nunca porcentaje). */
export const UMBRAL_CONFIANZA = 0.6;

/** Referencia ESTIMADA de una venta a mano (libreta + calculadora). Reemplazar si se mide en tienda. */
export const SEGUNDOS_VENTA_MANUAL = 180;

/** Existencia a partir de la cual se muestra "Poco". */
export const EXISTENCIA_BAJA = 3;

/** Tiempos del análisis de foto. */
export const TIEMPOS_ANALISIS = {
  limiteMs: 20_000,
  avisoTardandoMs: 8_000,
  reconociendoMs: 1_500,
} as const;

/** Tiempo que se muestra la franja de "Deshacer" (sin límite si hay lector de pantalla). */
export const DESHACER_MS = 10_000;

/** Compresión de fotos antes de subir. */
export const IMAGEN_LADO_MAXIMO = 1280;
export const IMAGEN_CALIDAD = 0.7;

/** Métodos de pago: nombre visible e icono. Los digitales son SIMULACIÓN (no mueven dinero real). */
export const METODOS_PAGO: Record<MetodoPago, { nombre: string; icono: NombreIcono }> = {
  efectivo: { nombre: 'Efectivo', icono: 'cash' },
  transferencia: { nombre: 'Transferencia', icono: 'bank-transfer' },
  qr: { nombre: 'Código QR', icono: 'qrcode' },
  tarjeta: { nombre: 'Tarjeta', icono: 'credit-card-outline' },
};

/** Nombres de oficio por rol del asistente. */
export const ROLES: Record<RolAsistente, { nombre: string; icono: NombreIcono }> = {
  caja: { nombre: 'Caja', icono: 'cash-register' },
  bodega: { nombre: 'Bodega', icono: 'package-variant-closed' },
  cuentas: { nombre: 'Cuentas', icono: 'calculator-variant' },
  promociones: { nombre: 'Promociones', icono: 'bullhorn-outline' },
  tutor: { nombre: 'Ayuda de pagos', icono: 'school-outline' },
  general: { nombre: 'Tu asistente', icono: 'chat-outline' },
  banco: { nombre: 'Guía del banco', icono: 'bank-outline' },
};

/** "Te contestan" del estado vacío del chat (02-asistente §2.4). `general` no aparece. */
export const TE_CONTESTAN: { rol: RolAsistente; texto: string }[] = [
  { rol: 'caja', texto: 'ventas y precios' },
  { rol: 'bodega', texto: 'lo que tienes' },
  { rol: 'cuentas', texto: 'ganancias, gastos' },
  { rol: 'promociones', texto: 'ofertas' },
  { rol: 'tutor', texto: 'cobro digital' },
];

/** Chips "Prueba con:" de la pestaña Asistente (envían el texto de inmediato). */
export const SUGERENCIAS_INICIO: { texto: string; icono: NombreIcono }[] = [
  { texto: '¿Cuánto vendí hoy?', icono: 'trending-up' },
  { texto: '¿Qué se me está acabando?', icono: 'package-down' },
  { texto: 'Registrar una venta', icono: 'cash-register' },
  { texto: '¿Cómo cobro con transferencia?', icono: 'bank-transfer' },
];

/** Chips de la hoja "Pregúntale a Caja" en la revisión del cobro. */
export const SUGERENCIAS_CAJA = ['¿Qué producto no reconoció?', '¿Cuánto cuesta este producto?', '¿Me alcanza el stock?'];

/** Chat del asistente (02-asistente §7). */
export const CHAT = {
  /** Aviso "Está tardando más de lo normal…" */
  avisoTardandoMs: 8_000,
  /** Tarjetas pendientes caducan pasado este tiempo. */
  caducidadMs: 30 * 60 * 1000,
  maxMensajes: 100,
  /** Turnos que se mandan al servidor como historial. */
  maxHistorial: 12,
  maxCaracteres: 500,
  /** El contador aparece desde aquí. */
  avisoCaracteres: 450,
  /** El indicador "Cargando tu conversación…" solo aparece si tarda más de esto. */
  cargaVisibleMs: 300,
} as const;

/** Número de soporte por WhatsApp (de .env; vacío = se oculta el botón). Nunca datos reales en el código. */
export const SOPORTE_WHATSAPP = process.env.EXPO_PUBLIC_SOPORTE_WHATSAPP ?? '';
