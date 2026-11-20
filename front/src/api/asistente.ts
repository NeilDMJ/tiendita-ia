import { z } from 'zod';

import { pedir, pedirJson, USAR_MOCKS, type OpcionesPedido } from './cliente';
import { MensajeAsistente, type EstadoPantalla, type SolicitudAsistente } from './esquemas';
import { esperar } from './mocks';
import { mockRespuestaAsistente } from './mocks/asistente';

/** Tiempo límite de una respuesta del asistente (02-asistente §5.4). */
export const TIEMPO_ASISTENTE_MS = 25_000;

/**
 * POST /asistente/mensaje. `id_mensaje` hace que un Reintentar no duplique la respuesta.
 * `opciones.signal` = botón "Detener" (→ ErrorApi 'cancelado'); a los 25 s → 'tiempo_agotado'.
 */
export async function enviarMensaje(
  solicitud: SolicitudAsistente,
  opciones: OpcionesPedido = {},
): Promise<MensajeAsistente> {
  const conLimite = { ...opciones, tiempoMs: opciones.tiempoMs ?? TIEMPO_ASISTENTE_MS };
  if (USAR_MOCKS) return mockRespuestaAsistente(solicitud, conLimite);
  return pedirJson('/asistente/mensaje', MensajeAsistente, solicitud, conLimite);
}

/**
 * Opcional (02-asistente §3.2): avisa al orquestador qué hizo el tendero con una propuesta.
 * Fire-and-forget: su falla nunca se muestra.
 */
export function reportarResultadoAccion(idAccion: string, estado: 'hecha' | 'rechazada') {
  if (USAR_MOCKS) return;
  pedir(`/asistente/acciones/${encodeURIComponent(idAccion)}/resultado`, z.unknown(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado }),
  }).catch(() => undefined);
}

export async function pedirAyudaTutor(estado: EstadoPantalla) {
  if (USAR_MOCKS)
    return esperar(700).then(
      (): MensajeAsistente => ({ rol: 'tutor', texto: 'Escribe la CLABE de 18 números que te dio tu cliente y toca “Continuar”.' }),
    );
  return pedirJson('/asistente/tutor', MensajeAsistente, estado);
}
