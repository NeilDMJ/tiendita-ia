/**
 * Conversación del asistente guardada en el teléfono (02-asistente §2.8 y §4.1).
 * - Pestaña: `asistente-chat-v1`, últimos 100 mensajes.
 * - Hoja "Pregúntale a Caja": `chat-caja-borrador`, ligada a la venta en curso (`sesion`); se borra al cobrar o descartar.
 * Al servidor solo se manda un historial resumido (12 turnos, sin tarjetas).
 */
import type { TipoError } from '@/api/cliente';
import type { AccionAsistente, RolAsistente, TurnoHistorial } from '@/api/esquemas';
import type { EstadoTarjeta } from '@/components/tarjeta-accion';
import { CHAT } from '@/constants';

import { guardarJson, leerJsonConError } from './almacen';

export const CLAVE_CHAT_PESTANA = 'asistente-chat-v1';
export const CLAVE_CHAT_CAJA = 'chat-caja-borrador';

export type EstadoEnvio = 'enviando' | 'enviado' | 'en_espera' | 'fallido';

export type AccionChat = AccionAsistente & {
  estado: EstadoTarjeta;
  /** Texto de `hecha` ("Venta registrada · Folio V-0043"). */
  resultado?: string;
  /** Motivo de `caducada`. */
  motivo?: string;
  /** Mensaje humano de `error`. */
  error?: string;
  /** `datos` no pasó zod: "No pudimos leer esta propuesta". */
  ilegible?: boolean;
  /** Para [Ver comprobante]. */
  idVenta?: string;
  /** modificar_item que excede existencia: clave de la fila para "Revisar y editar". */
  claveFila?: string;
};

export type MensajeTendero = {
  id: string;
  autor: 'tendero';
  texto: string;
  creado_en: string;
  estado: EstadoEnvio;
  error?: TipoError;
};

export type MensajeDelAsistente = {
  id: string;
  autor: 'asistente';
  rol: RolAsistente;
  texto: string;
  creado_en: string;
  no_resuelto?: boolean;
  sugerencias?: string[];
  acciones?: AccionChat[];
};

export type MensajeChat = MensajeTendero | MensajeDelAsistente;

type Guardado = { sesion: string | null; mensajes: MensajeChat[] };

export const MOTIVO_CADUCA_TIEMPO = 'Pasó mucho tiempo.';
export const MOTIVO_CADUCA_NUEVA = 'Hay una más nueva abajo.';

/** Mensaje humano de una burbuja `fallido`. */
export function motivoFallo(error: TipoError | undefined): string {
  if (error === 'sin_conexion') return 'No se envió: sin conexión.';
  if (error === 'tiempo_agotado') return 'Tardó mucho en contestar.';
  if (error === 'cancelado') return 'Detuviste la respuesta.';
  return 'No pudimos traer la respuesta. Intenta de nuevo.';
}

export function recortar(mensajes: MensajeChat[]): MensajeChat[] {
  return mensajes.length > CHAT.maxMensajes ? mensajes.slice(-CHAT.maxMensajes) : mensajes;
}

function vencida(accion: AccionChat, creadoEn: string, ahora: number) {
  if (accion.vence_en) {
    const limite = Date.parse(accion.vence_en);
    if (!Number.isNaN(limite) && limite < ahora) return true;
  }
  return ahora - Date.parse(creadoEn) > CHAT.caducidadMs;
}

/** Tarjetas `pendiente` con más de 30 min (o `vence_en` pasado) → `caducada`. */
export function caducarVencidas(mensajes: MensajeChat[], ahora = Date.now()): MensajeChat[] {
  let cambio = false;
  const nuevos = mensajes.map((m) => {
    if (m.autor !== 'asistente' || !m.acciones) return m;
    let tocado = false;
    const acciones = m.acciones.map((a) => {
      if (a.estado !== 'pendiente' || a.tipo === 'abrir_pantalla' || !vencida(a, m.creado_en, ahora)) return a;
      tocado = true;
      return { ...a, estado: 'caducada' as const, motivo: MOTIVO_CADUCA_TIEMPO };
    });
    if (!tocado) return m;
    cambio = true;
    return { ...m, acciones };
  });
  return cambio ? nuevos : mensajes;
}

/** Al abrir: caducidad + lo que quedó a medias cuando se cerró la app. */
function prepararAlCargar(mensajes: MensajeChat[]): MensajeChat[] {
  return caducarVencidas(
    mensajes.map((m): MensajeChat => {
      if (m.autor === 'tendero') return m.estado === 'enviando' ? { ...m, estado: 'fallido', error: 'servidor' } : m;
      if (!m.acciones) return m;
      return {
        ...m,
        acciones: m.acciones.map((a) =>
          a.estado === 'confirmando'
            ? {
                ...a,
                estado: 'error' as const,
                // id_local = 'chat-' + id: reintentar nunca cobra dos veces
                error: 'No supimos si se completó. Reintenta: no se cobra dos veces.',
              }
            : a,
        ),
      };
    }),
  );
}

export async function leerChat(clave: string, sesion: string | null): Promise<{ mensajes: MensajeChat[]; error: boolean }> {
  const { valor, error } = await leerJsonConError<Guardado>(clave);
  if (error) return { mensajes: [], error: true };
  if (!valor) return { mensajes: [], error: false };
  if (!Array.isArray(valor.mensajes)) return { mensajes: [], error: true };
  if ((valor.sesion ?? null) !== sesion) return { mensajes: [], error: false };
  return { mensajes: prepararAlCargar(recortar(valor.mensajes)), error: false };
}

export function guardarChat(clave: string, sesion: string | null, mensajes: MensajeChat[]) {
  const guardado: Guardado = { sesion, mensajes: recortar(mensajes) };
  return guardarJson(clave, guardado);
}

/** Se llama al cobrar, descartar o empezar otra venta. */
export function borrarChatCaja() {
  return guardarJson(CLAVE_CHAT_CAJA, null);
}

/** Últimos 12 turnos ANTES de `hastaId` (texto solo; sin tarjetas ni mensajes fallidos). */
export function historialParaServidor(mensajes: MensajeChat[], hastaId: string): TurnoHistorial[] {
  const corte = mensajes.findIndex((m) => m.id === hastaId);
  const previos = corte >= 0 ? mensajes.slice(0, corte) : mensajes;
  return previos
    .filter((m) => m.autor === 'asistente' || m.estado === 'enviado')
    .slice(-CHAT.maxHistorial)
    .map((m) =>
      m.autor === 'asistente'
        ? { autor: 'asistente' as const, rol: m.rol, texto: m.texto.slice(0, 2000) }
        : { autor: 'tendero' as const, texto: m.texto.slice(0, 2000) },
    );
}
