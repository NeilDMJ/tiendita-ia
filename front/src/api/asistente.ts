import { z } from 'zod';

import { pedir, pedirJson, USAR_MOCKS, type OpcionesPedido } from './cliente';
import { MensajeAsistente, type EstadoPantalla, type SolicitudAsistente } from './esquemas';
import { esperar } from './mocks';
import { mockRespuestaAsistente } from './mocks/asistente';
import { anonimizar } from '@/utils/anonimizar';

const AVISO_BLOQUEO =
  'No envié tu mensaje porque parece traer datos privados (tarjeta, CLABE, NIP o clave). ' +
  'Por tu seguridad, no los escribas aquí. Cuéntame qué quieres hacer sin esos datos y te guío.';

/**
 * 1 = el chat usa el asistente real (POST /asistente/mensaje del servidor unido) aunque el resto
 * siga con mocks. /asistente/acciones y /asistente/tutor aún no existen en el back: siguen simulados.
 */
const ASISTENTE_REAL = process.env.EXPO_PUBLIC_ASISTENTE_REAL === '1';

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
  // Privacidad: lo sensible nunca sale del teléfono; montos y celulares se enmascaran antes de enviar.
  const limpio = anonimizar(solicitud.texto);
  if (limpio.bloquear) return { rol: 'banco', texto: AVISO_BLOQUEO };
  solicitud = {
    ...solicitud,
    texto: limpio.texto,
    historial: solicitud.historial
      .map((t) => ({ ...t, texto: anonimizar(t.texto) }))
      .filter((t) => !(t.autor === 'tendero' && t.texto.bloquear))
      .map((t) => ({ ...t, texto: t.texto.texto })),
  };
  if (USAR_MOCKS && !ASISTENTE_REAL) return mockRespuestaAsistente(solicitud, conLimite);
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
