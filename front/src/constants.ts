import type { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';

import type { RolAsistente } from '@/api/esquemas';

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

/** Nombres de oficio por rol del asistente. */
export const ROLES: Record<RolAsistente, { nombre: string; icono: NombreIcono }> = {
  caja: { nombre: 'Caja', icono: 'cash-register' },
  bodega: { nombre: 'Bodega', icono: 'package-variant-closed' },
  cuentas: { nombre: 'Cuentas', icono: 'calculator-variant' },
  promociones: { nombre: 'Promociones', icono: 'bullhorn-outline' },
  tutor: { nombre: 'Ayuda de pagos', icono: 'school-outline' },
  general: { nombre: 'Asistente', icono: 'chat-outline' },
};
