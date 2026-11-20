/* eslint-disable @typescript-eslint/no-redeclare -- patrón zod: esquema y tipo con el mismo nombre */
/**
 * Módulo Asistente ↔ enjambre de agentes (`enjambre_agentes/api.py`).
 *
 * ADICIÓN: no reemplaza a `asistente.ts`. Se activa con `EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1`; con el flag
 * apagado el módulo se comporta como antes. Con el flag encendido el Asistente usa SOLO estos endpoints:
 *
 *   POST /orchestrate          chat (supervisor → agente especialista)          → enviarMensajeEnjambre
 *   POST /orchestrate/resume   aprobar / rechazar una acción pausada (HITL)     → reanudarAprobacion
 *   POST /pago                 tutor de pagos CoDi / SPEI / DiMo                → pedirAyudaTutorEnjambre
 *   GET  /health               salud del servidor y de PostgreSQL               → consultarSaludEnjambre
 *   GET  /state/{thread_id}    estado real del hilo                             → obtenerEstadoHilo
 *   GET  /rag/search           búsqueda en el RAG de pagos                      → buscarEnRagPagos
 *   POST /imagen               foto al agente (NIM Vision del enjambre)         → enviarImagenAlEnjambre
 *
 * `/health`, `/state`, `/rag/search` e `/imagen` están disponibles como funciones pero ninguna pantalla del
 * Asistente las llama todavía (el Asistente no tiene botón de adjuntar foto ni indicador de salud).
 *
 * Los endpoints de visión del modelo ONNX (`/vision/*`) NO pasan por aquí: son de Cobrar e Inventario
 * (`vision.ts`). El enjambre usa su propia visión (NIM Vision) y solo para el módulo Asistente.
 *
 * El enjambre recuerda la conversación por `thread_id` (MemorySaver, en RAM del servidor): la app manda solo el
 * mensaje nuevo y reutiliza el mismo `thread_id` hasta que se borra el chat.
 */
import { z } from 'zod';

import { guardarJson, leerJson } from '@/estado/almacen';
import { crearIdLocal } from '@/utils/id';

import { pedir, pedirJson, type OpcionesPedido } from './cliente';
import type { EstadoPantalla, MensajeAsistente, RolAsistente } from './esquemas';

/** 1 = el Asistente usa la API del enjambre (en vez de /asistente/mensaje y simulaciones). */
export const ASISTENTE_ENJAMBRE = process.env.EXPO_PUBLIC_ASISTENTE_ENJAMBRE === '1';

/** El enjambre es síncrono y encadena modelos grandes: 25 s del asistente bancario no alcanzan. */
export const TIEMPO_ENJAMBRE_MS = 90_000;

// ---------- Respuestas del servidor (ver `_formatear_respuesta_orquestacion` en api.py) ----------

const AprobacionPendiente = z.object({
  action_type: z.string().optional(),
  description: z.string().optional(),
  reason: z.string().optional(),
  proposed_data: z.unknown().optional(),
  requires_human: z.boolean().optional(),
  status: z.string().optional(),
});

export const RespuestaEnjambre = z.object({
  /** `completed` | `pending_approval` | `approved_and_resumed` | `rejected_and_resumed` */
  status: z.string(),
  thread_id: z.string(),
  next_agent: z.string().nullable().optional(),
  reply: z.string(),
  requires_approval: z.boolean().optional(),
  pending_approval: AprobacionPendiente.nullable().optional(),
});
export type RespuestaEnjambre = z.infer<typeof RespuestaEnjambre>;

// ---------- Traducción respuesta del enjambre → mensaje del Asistente ----------

/** Cada agente firma su texto con una etiqueta (`[VENDEDOR]: …`). Se usa para elegir el oficio que se muestra. */
const ROL_POR_ETIQUETA: Record<string, RolAsistente> = {
  VENDEDOR: 'caja',
  CONTROL: 'bodega',
  ANALISTA: 'cuentas',
  PUBLICISTA: 'promociones',
  TUTOR_UI: 'tutor',
  INVESTIGADOR: 'general',
  'HITL APROBADO': 'general',
  'HITL RECHAZADO': 'general',
};

const ETIQUETA = /^\s*\[([A-ZÁÉÍÓÚÑ_ ]+)\]:?\s*/;

/** Separa la etiqueta del agente del texto. Sin etiqueta conocida → rol `general`. */
export function separarEtiqueta(reply: string): { rol: RolAsistente; texto: string } {
  const m = ETIQUETA.exec(reply);
  if (!m) return { rol: 'general', texto: reply.trim() };
  return { rol: ROL_POR_ETIQUETA[m[1].trim()] ?? 'general', texto: reply.slice(m[0].length).trim() };
}

const TITULO_APROBACION: Record<string, string> = {
  descuento_especial: 'Aprobar descuento',
  alta_catalogo: 'Aprobar alta de catálogo',
  clasificacion_gasto_critico: 'Aprobar clasificación del gasto',
  publicar_campana: 'Aprobar campaña',
};

/** `proposed_data` es texto libre del agente: se reduce a una frase corta para la tarjeta. */
function resumirPropuesta(p: unknown): string | null {
  if (p == null) return null;
  if (typeof p === 'string') return p.slice(0, 300);
  if (typeof p === 'object') {
    const msg = (p as Record<string, unknown>).mensaje;
    if (typeof msg === 'string') return msg.slice(0, 300);
    try {
      return JSON.stringify(p).slice(0, 300);
    } catch {
      return null;
    }
  }
  return String(p).slice(0, 300);
}

/**
 * Convierte la respuesta del enjambre al `MensajeAsistente` que ya entiende la pantalla.
 * - `reply` vacío → `no_resuelto` (la pantalla ofrece salidas directas).
 * - `pending_approval` (HITL) → una acción `aprobar_enjambre` que la persona confirma o rechaza.
 */
export function interpretarRespuesta(r: RespuestaEnjambre): MensajeAsistente {
  const { rol, texto } = separarEtiqueta(r.reply);
  const pendiente = r.requires_approval || r.status === 'pending_approval' ? r.pending_approval : null;

  if (pendiente) {
    const tipo = pendiente.action_type ?? 'accion';
    return {
      rol,
      texto: texto || pendiente.description || 'Necesito tu aprobación para continuar.',
      acciones: [
        {
          id: `enj-${crearIdLocal()}`,
          tipo: 'aprobar_enjambre',
          titulo: TITULO_APROBACION[tipo] ?? 'Aprobar acción',
          datos: {
            thread_id: r.thread_id,
            tipo_operacion: tipo,
            descripcion: pendiente.description ?? null,
            motivo: pendiente.reason ?? null,
            detalle: resumirPropuesta(pendiente.proposed_data),
          },
        },
      ],
    };
  }

  if (texto === '') {
    return { rol: 'general', texto: 'No encontré una respuesta para eso. Intenta de otra forma.', no_resuelto: true };
  }
  return { rol, texto };
}

// ---------- Hilo de conversación ----------

/**
 * Un hilo por canal, para que las conversaciones no se mezclen:
 * - `asistente`: la pestaña Asistente.
 * - `caja`: la hoja "Pregúntale a Caja" dentro de la revisión del cobro (se borra al cobrar o descartar).
 * El enjambre NO recibe el contexto de la venta en revisión (`contexto.items`): solo el texto del mensaje.
 */
export type CanalEnjambre = 'asistente' | 'caja';

const CLAVE_HILO: Record<CanalEnjambre, string> = {
  asistente: 'enjambre-thread-id',
  caja: 'enjambre-thread-id-caja',
};
const hilosEnMemoria: Partial<Record<CanalEnjambre, string>> = {};

/** Mismo `thread_id` durante toda la conversación (se guarda en el teléfono: sobrevive al cierre de la app). */
export async function obtenerThreadId(canal: CanalEnjambre = 'asistente'): Promise<string> {
  const enMemoria = hilosEnMemoria[canal];
  if (enMemoria) return enMemoria;
  const guardado = await leerJson<string | null>(CLAVE_HILO[canal], null);
  const hilo = guardado ?? `app-${canal}-${crearIdLocal()}`;
  hilosEnMemoria[canal] = hilo;
  if (!guardado) await guardarJson(CLAVE_HILO[canal], hilo);
  return hilo;
}

/** Empieza una conversación nueva en el enjambre (se llama al borrar el chat). */
export async function reiniciarThread(canal: CanalEnjambre = 'asistente'): Promise<void> {
  if (!ASISTENTE_ENJAMBRE) return; // con el flag apagado no se toca el almacenamiento
  const hilo = `app-${canal}-${crearIdLocal()}`;
  hilosEnMemoria[canal] = hilo;
  await guardarJson(CLAVE_HILO[canal], hilo);
}

// ---------- Endpoints ----------

/** POST /orchestrate. Solo se manda el mensaje nuevo: el enjambre guarda el historial por `thread_id`. */
export async function enviarMensajeEnjambre(
  texto: string,
  opciones: OpcionesPedido = {},
  canal: CanalEnjambre = 'asistente',
): Promise<MensajeAsistente> {
  const thread_id = await obtenerThreadId(canal);
  const r = await pedirJson(
    '/orchestrate',
    RespuestaEnjambre,
    { input_text: texto, thread_id, event_source: 'chat' },
    { ...opciones, tiempoMs: opciones.tiempoMs ?? TIEMPO_ENJAMBRE_MS },
  );
  return interpretarRespuesta(r);
}

/**
 * POST /orchestrate/resume. `aprobado = true` confirma el COMMIT en PostgreSQL; `false` cancela sin escribir.
 * Devuelve el texto con que respondió el enjambre (se muestra como resultado de la tarjeta).
 */
export async function reanudarAprobacion(
  thread_id: string,
  aprobado: boolean,
  opciones: OpcionesPedido = {},
): Promise<{ texto: string }> {
  const r = await pedirJson(
    '/orchestrate/resume',
    RespuestaEnjambre,
    { thread_id, approved: aprobado },
    { ...opciones, tiempoMs: opciones.tiempoMs ?? TIEMPO_ENJAMBRE_MS },
  );
  const { texto } = separarEtiqueta(r.reply);
  return { texto: texto || (aprobado ? 'Listo, aprobado.' : 'Cancelado, no se guardó nada.') };
}

/**
 * POST /pago (tutor de pagos). El servidor exige el método (`codi|spei|dimo|tarjeta`): la app todavía no tiene la
 * pantalla de pago digital, así que `metodo` es opcional y por defecto `spei`.
 */
export async function pedirAyudaTutorEnjambre(
  estado: EstadoPantalla,
  metodo: 'codi' | 'spei' | 'dimo' | 'tarjeta' = 'spei',
  opciones: OpcionesPedido = {},
): Promise<MensajeAsistente> {
  const r = await pedirJson(
    '/pago',
    RespuestaEnjambre,
    {
      metodo_pago: metodo,
      pantalla: estado.pantalla,
      paso: Math.max(1, Math.floor(estado.paso)),
      error_code: estado.errores_visibles[0] ?? null,
      thread_id: await obtenerThreadId(),
    },
    { ...opciones, tiempoMs: opciones.tiempoMs ?? TIEMPO_ENJAMBRE_MS },
  );
  const { texto } = separarEtiqueta(r.reply);
  return { rol: 'tutor', texto: texto || 'Sigue las instrucciones de la pantalla.' };
}

const SaludEnjambre = z.object({
  status: z.string(),
  database: z.object({ connected: z.boolean().optional() }).optional(),
});
export type SaludEnjambre = z.infer<typeof SaludEnjambre>;

/** GET /health. `status` = `healthy` | `degraded` (sin PostgreSQL). */
export function consultarSaludEnjambre(opciones?: OpcionesPedido) {
  return pedir('/health', SaludEnjambre, {}, opciones);
}

const EstadoHilo = z.object({
  status: z.string(),
  thread_id: z.string(),
  state: z.object({ pending_approval: z.unknown().optional(), next_agent: z.string().nullable().optional() }),
});

/** GET /state/{thread_id}: estado real del grafo (p. ej. si sigue esperando una aprobación). */
export function obtenerEstadoHilo(thread_id: string, opciones?: OpcionesPedido) {
  return pedir(`/state/${encodeURIComponent(thread_id)}`, EstadoHilo, {}, opciones);
}

const ResultadoRag = z.object({ status: z.string() }).catchall(z.unknown());

/** GET /rag/search: fragmentos oficiales de CoDi, SPEI y DiMo. */
export function buscarEnRagPagos(consulta: string, metodo?: 'codi' | 'spei' | 'dimo', opciones?: OpcionesPedido) {
  const q = new URLSearchParams({ q: consulta, ...(metodo ? { metodo } : {}) });
  return pedir(`/rag/search?${q.toString()}`, ResultadoRag, {}, opciones);
}

/** POST /imagen: foto en base64 para el agente (NIM Vision del enjambre). Modo `pos`, `catalog` o `ticket`. */
export async function enviarImagenAlEnjambre(
  imagenBase64: string,
  modo: 'pos' | 'catalog' | 'ticket',
  mime = 'image/jpeg',
  opciones: OpcionesPedido = {},
): Promise<MensajeAsistente> {
  const r = await pedirJson(
    '/imagen',
    RespuestaEnjambre,
    { image_b64: imagenBase64, mode: modo, mime_type: mime, thread_id: await obtenerThreadId() },
    { ...opciones, tiempoMs: opciones.tiempoMs ?? TIEMPO_ENJAMBRE_MS },
  );
  return interpretarRespuesta(r);
}
