import { z } from 'zod';

import { pedir, pedirJson, USAR_MOCKS, type OpcionesPedido } from './cliente';
import {
  MensajeAsistente,
  type AccionAsistente,
  type EstadoPantalla,
  type PasoAgente,
  type RolAsistente,
  type SolicitudAsistente,
} from './esquemas';
import { esperar } from './mocks';
import { mockRespuestaAsistente } from './mocks/asistente';
import { anonimizar } from '@/utils/anonimizar';
import { extraerBloquesThink, limpiarFormato } from '@/utils/texto-chat';

const AVISO_BLOQUEO =
  'No envié tu mensaje porque parece traer datos privados (tarjeta, CLABE, NIP o clave). ' +
  'Por tu seguridad, no los escribas aquí. Cuéntame qué quieres hacer sin esos datos y te guío.';

/**
 * 1 = el chat usa el asistente real del servidor unido aunque el resto siga con mocks.
 * - EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1 → conecta al enjambre multiagente (POST /orchestrate y /pago).
 * - EXPO_PUBLIC_ASISTENTE_ENJAMBRE=0 → conecta al asistente bancario (POST /asistente/mensaje).
 */
const ASISTENTE_REAL = process.env.EXPO_PUBLIC_ASISTENTE_REAL === '1';
const ASISTENTE_ENJAMBRE = process.env.EXPO_PUBLIC_ASISTENTE_ENJAMBRE === '1';

/** Tiempo límite de una respuesta del asistente (más holgura cuando responde el enjambre). */
export const TIEMPO_ASISTENTE_MS = ASISTENTE_ENJAMBRE ? 45_000 : 25_000;

const MensajeCrudoOrquestador = z.object({
  role: z.string(),
  content: z.string(),
});

/** Esquema flexible para la respuesta de POST /orchestrate y POST /pago del enjambre. */
const RespuestaOrquestador = z.object({
  status: z.string().optional(),
  thread_id: z.string().optional(),
  next_agent: z.string().nullable().optional(),
  reply: z.string().nullable().optional(),
  messages: z.array(MensajeCrudoOrquestador).optional(),
  db_evidence: z.string().nullable().optional(),
  requires_approval: z.boolean().optional(),
  pending_approval: z.record(z.string(), z.unknown()).nullable().optional(),
  promo_assets: z.record(z.string(), z.unknown()).nullable().optional(),
});

let hiloEnjambreActual: string | undefined;

const ETIQUETA_AGENTE: Record<string, string> = {
  supervisor: 'Supervisor',
  control: 'Control (Bodega)',
  vendedor: 'Vendedor (Caja)',
  analista: 'Analista (Cuentas)',
  investigador: 'Investigador',
  publicista: 'Publicista (Promociones)',
  tutor_ui: 'Tutor de Pagos',
  hitl: 'Validación HITL',
};

function nombreLegibleAgente(clave?: string | null): string {
  const k = (clave ?? '').trim().toLowerCase();
  return ETIQUETA_AGENTE[k] ?? (k ? k.charAt(0).toUpperCase() + k.slice(1) : 'Agente');
}

function mapearRolEnjambre(agente?: string | null): RolAsistente {
  switch ((agente ?? '').toLowerCase()) {
    case 'vendedor':
      return 'caja';
    case 'control':
      return 'bodega';
    case 'analista':
      return 'cuentas';
    case 'publicista':
      return 'promociones';
    case 'tutor_ui':
      return 'tutor';
    default:
      return 'general';
  }
}

function limpiarPrefijoAgente(texto: string): string {
  return texto
    .replace(/^(?:\([^)]+\)\??\s*)?\[[A-Z_ ]+\]:?\s*/i, '')
    .trim();
}

function detectarAgenteDeMensaje(contenido: string): { rol: string; agente: string; cuerpo: string } {
  const limpio = contenido.trim();
  const matchTag = limpio.match(/^(?:\([^)]+\)\??\s*)?\[([A-Z_ ]+)\]:?\s*([\s\S]*)$/i);
  if (matchTag) {
    const rawTag = matchTag[1].trim().toLowerCase();
    const cuerpo = matchTag[2].trim();
    if (rawTag.startsWith('hitl')) {
      return { rol: 'hitl', agente: 'Validación HITL', cuerpo };
    }
    const rolNorm = rawTag.replace(/\s+/g, '_');
    return { rol: rolNorm, agente: nombreLegibleAgente(rolNorm), cuerpo };
  }
  return { rol: 'general', agente: 'Asistente', cuerpo: limpio };
}

/**
 * Extrae la traza real de interacción entre agentes del último turno (como en el CLI):
 *   Supervisor (razonamiento de enrutamiento) -> Agentes intermedios -> Especialista final / HITL.
 */
function construirTrazaAgentes(resp: z.infer<typeof RespuestaOrquestador>): {
  traza: PasoAgente[] | undefined;
  textoLimpio: string;
} {
  const todos = resp.messages ?? [];
  // Tomar únicamente los mensajes posteriores al último turno del usuario
  let indiceUltimoHumano = -1;
  for (let i = todos.length - 1; i >= 0; i -= 1) {
    if (todos[i].role === 'human' || todos[i].role === 'user') {
      indiceUltimoHumano = i;
      break;
    }
  }
  const mensajesTurno = (indiceUltimoHumano >= 0 ? todos.slice(indiceUltimoHumano + 1) : todos).filter(
    (m) => m.role === 'ai' || m.role === 'assistant',
  );

  const pasos: PasoAgente[] = [];
  const indiceFinal = mensajesTurno.length - 1;

  mensajesTurno.forEach((m, idx) => {
    const { rol, agente, cuerpo } = detectarAgenteDeMensaje(m.content);
    const { limpio, pensamientos } = extraerBloquesThink(cuerpo);

    for (const p of pensamientos) {
      pasos.push({
        agente: `${agente} · Razonamiento`,
        rol,
        resumen: limpiarFormato(p).slice(0, 260),
      });
    }

    if (rol === 'supervisor') {
      // Embellecer "Enrutando a 'analista'. Motivo: ..." con nombres legibles
      const textoSup = limpiarFormato(limpio).replace(
        /Enrutando a ['"]?([a-z_]+)['"]?/i,
        (_, ag: string) => `Enrutando a ${nombreLegibleAgente(ag)}`,
      );
      if (textoSup) {
        pasos.push({ agente: 'Supervisor', rol: 'supervisor', resumen: textoSup });
      }
      return;
    }

    // Si es un especialista intermedio en cadena compuesta (ej. Control -> Publicista), incluir su aporte
    if (idx < indiceFinal) {
      const resumenIntermedio = limpiarFormato(limpio);
      if (resumenIntermedio) {
        const corto =
          resumenIntermedio.length > 220
            ? `${resumenIntermedio.slice(0, 217).trimEnd()}…`
            : resumenIntermedio;
        pasos.push({ agente, rol, resumen: corto });
      }
      return;
    }

    // Especialista final: mostrar qué agente resolvió y qué fuente/evidencia usó
    const evidencia = (resp.db_evidence ?? '').trim();
    const esFuenteCorta = evidencia.startsWith('RAG ') || evidencia.startsWith('COMMIT ');
    const resumenFinal = esFuenteCorta
      ? `Respondió con evidencia en vivo: ${evidencia.slice(0, 180)}`
      : `Consultó datos reales de la tienda y generó la respuesta.`;
    pasos.push({ agente, rol, resumen: resumenFinal });
  });

  if (resp.requires_approval && resp.pending_approval) {
    const desc =
      typeof resp.pending_approval.description === 'string'
        ? resp.pending_approval.description
        : 'Acción sensible pausada esperando tu confirmación.';
    pasos.push({
      agente: 'Control Humano (HITL)',
      rol: 'hitl',
      resumen: desc,
    });
  }

  // Limpiar respuesta principal (quitar prefijo [AGENTE], <think> y markdown crudo)
  const rawReply = resp.reply ?? (mensajesTurno[indiceFinal]?.content ?? '');
  const sinPrefijo = limpiarPrefijoAgente(rawReply);
  const { limpio: replySinThink, pensamientos: thinkReply } = extraerBloquesThink(sinPrefijo);
  if (thinkReply.length > 0 && pasos.length === 0) {
    pasos.push({
      agente: nombreLegibleAgente(resp.next_agent),
      rol: resp.next_agent ?? 'general',
      resumen: limpiarFormato(thinkReply[0]).slice(0, 260),
    });
  }

  const textoLimpio = limpiarFormato(replySinThink) || 'Listo, procesé tu consulta.';
  return {
    traza: pasos.length > 0 ? pasos : undefined,
    textoLimpio,
  };
}

function construirAccionesEnjambre(
  resp: z.infer<typeof RespuestaOrquestador>,
): AccionAsistente[] | undefined {
  if (!resp.requires_approval || !resp.thread_id) return undefined;
  const promo = resp.promo_assets;
  if (promo && typeof promo.producto_promocionado === 'string') {
    const manana = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    const precio = typeof promo.precio_promo === 'number' && promo.precio_promo >= 0 ? promo.precio_promo : 0;
    const copy = limpiarFormato(String(promo.copy_text ?? promo.cta ?? 'Promoción especial en mostrador')).slice(0, 280);
    return [
      {
        id: `swarm:${resp.thread_id}`,
        tipo: 'aprobar_promo',
        titulo: `Aprobar promoción: ${promo.producto_promocionado}`,
        datos: {
          promo_id: `swarm:${resp.thread_id}`,
          producto: promo.producto_promocionado,
          copy,
          precio_promo: precio,
          vigente_hasta: manana,
          video_url: null,
          simulacion: false,
        },
      },
    ];
  }
  return undefined;
}

async function enviarAlEnjambre(
  solicitud: SolicitudAsistente,
  opciones: OpcionesPedido,
): Promise<MensajeAsistente> {
  if (solicitud.historial.length === 0) {
    hiloEnjambreActual = undefined;
  }

  let inputText = solicitud.texto;
  if (solicitud.contexto?.pantalla === 'revision_cobro' && solicitud.contexto.items.length > 0) {
    const resumen = solicitud.contexto.items
      .map((i) => `${i.cantidad}x ${i.nombre} ($${i.precio_unitario ?? '?'})`)
      .join(', ');
    inputText = `[Pantalla revisión de cobro | Total $${solicitud.contexto.total} | Carrito: ${resumen}] ${solicitud.texto}`;
  }

  const cuerpo: Record<string, unknown> = {
    input_text: inputText,
    event_source: solicitud.contexto?.pantalla === 'pago' ? 'ui_copilot' : 'chat',
  };
  if (hiloEnjambreActual) {
    cuerpo.thread_id = hiloEnjambreActual;
  }

  const resp = await pedirJson('/orchestrate', RespuestaOrquestador, cuerpo, opciones);
  if (resp.thread_id) {
    hiloEnjambreActual = resp.thread_id;
  }

  const { traza, textoLimpio } = construirTrazaAgentes(resp);
  const acciones = construirAccionesEnjambre(resp);

  return MensajeAsistente.parse({
    rol: mapearRolEnjambre(resp.next_agent),
    texto: textoLimpio,
    ...(traza ? { traza_agentes: traza } : {}),
    ...(acciones ? { acciones } : {}),
  });
}

/**
 * Envía el mensaje del chat al enjambre (/orchestrate) si EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1,
 * o al asistente bancario (/asistente/mensaje) si EXPO_PUBLIC_ASISTENTE_REAL=1.
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
  if (ASISTENTE_ENJAMBRE) return enviarAlEnjambre(solicitud, conLimite);
  if (USAR_MOCKS && !ASISTENTE_REAL) return mockRespuestaAsistente(solicitud, conLimite);
  return pedirJson('/asistente/mensaje', MensajeAsistente, solicitud, conLimite);
}

/**
 * Opcional (02-asistente §3.2): avisa al orquestador qué hizo el tendero con una propuesta.
 * Fire-and-forget: su falla nunca se muestra.
 */
export function reportarResultadoAccion(idAccion: string, estado: 'hecha' | 'rechazada') {
  if (ASISTENTE_ENJAMBRE && idAccion.startsWith('swarm:')) {
    const threadId = idAccion.slice('swarm:'.length);
    if (estado === 'rechazada') {
      pedirJson('/orchestrate/resume', z.unknown(), { thread_id: threadId, action: 'reject' }).catch(() => undefined);
    }
    return;
  }
  if (USAR_MOCKS) return;
  pedir(`/asistente/acciones/${encodeURIComponent(idAccion)}/resultado`, z.unknown(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado }),
  }).catch(() => undefined);
}

export async function pedirAyudaTutor(estado: EstadoPantalla): Promise<MensajeAsistente> {
  if (ASISTENTE_ENJAMBRE) {
    const pantallaLower = estado.pantalla.toLowerCase();
    const metodo = pantallaLower.includes('spei')
      ? 'spei'
      : pantallaLower.includes('dimo')
        ? 'dimo'
        : 'codi';
    const resp = await pedirJson('/pago', RespuestaOrquestador, {
      metodo_pago: metodo,
      pantalla: estado.pantalla,
      paso: estado.paso,
      error_code: estado.errores_visibles[0] ?? null,
    });
    const { traza, textoLimpio } = construirTrazaAgentes(resp);
    return MensajeAsistente.parse({
      rol: 'tutor',
      texto: textoLimpio,
      ...(traza ? { traza_agentes: traza } : {}),
    });
  }
  if (USAR_MOCKS)
    return esperar(700).then(
      (): MensajeAsistente => ({ rol: 'tutor', texto: 'Escribe la CLABE de 18 números que te dio tu cliente y toca “Continuar”.' }),
    );
  return pedirJson('/asistente/tutor', MensajeAsistente, estado);
}
