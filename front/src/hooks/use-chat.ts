/**
 * Conversación con el asistente (02-asistente §2 y §4): enviar, detener, reintentar con el mismo
 * `id_mensaje`, cola de UNA pregunta sin conexión (solo pestaña), persistencia y anuncios al lector.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

import { parsearDatosAccion } from '@/api/acciones-asistente';
import { enviarMensaje } from '@/api/asistente';
import { esErrorApi, type TipoError } from '@/api/cliente';
import type { ContextoAsistente, MensajeAsistente } from '@/api/esquemas';
import { datosRol } from '@/constants';
import {
  caducarVencidas,
  guardarChat,
  historialParaServidor,
  leerChat,
  MOTIVO_CADUCA_NUEVA,
  motivoFallo,
  recortar,
  type AccionChat,
  type MensajeChat,
  type MensajeDelAsistente,
  type MensajeTendero,
} from '@/estado/chat';
import { crearIdLocal } from '@/utils/id';

import { useAccesibilidad } from './use-accesibilidad';
import { useConexion } from './use-conexion';

export interface OpcionesChat {
  /** Clave en el almacenamiento local. */
  clave: string;
  /** Conversación ligada a una venta: si cambia, se empieza vacía. */
  sesion?: string | null;
  /** Se llama en CADA envío (la revisión puede haber cambiado). */
  contexto?: () => ContextoAsistente | undefined;
  /** Pestaña: sin conexión la pregunta queda en espera (máx. 1). Hoja de Caja: falla con [Reintentar]. */
  conCola: boolean;
  /** La pantalla/hoja está a la vista: se anuncian las respuestas al lector. */
  activo: boolean;
}

export type ResultadoEnvio =
  | { tipo: 'enviado' | 'en_espera' | 'ocupado' }
  /** Ya había una pregunta en espera y se reemplazó (snackbar con Deshacer). */
  | { tipo: 'reemplazo'; anterior: MensajeTendero; nuevoId: string };

const REVISION_CADUCIDAD_MS = 60_000;
const ESPERA_RECONEXION_MS = 500;

function anunciar(texto: string) {
  AccessibilityInfo.announceForAccessibility(texto);
}

/** Respuesta del servidor → mensaje local con el estado de cada tarjeta. */
function aMensajeLocal(respuesta: MensajeAsistente, contexto: ContextoAsistente | undefined): MensajeDelAsistente {
  const enRevision = contexto?.pantalla === 'revision_cobro';
  const acciones: AccionChat[] = (respuesta.acciones ?? [])
    // modificar_item fuera de la revisión se ignora (solo se muestra el texto)
    .filter((a) => a.tipo !== 'modificar_item' || enRevision)
    .map((a) =>
      parsearDatosAccion(a)
        ? { ...a, estado: 'pendiente' as const }
        : { ...a, estado: 'error' as const, ilegible: true, error: 'No pudimos leer esta propuesta.' },
    );
  return {
    id: crearIdLocal(),
    autor: 'asistente',
    rol: respuesta.rol,
    texto: respuesta.texto,
    creado_en: new Date().toISOString(),
    no_resuelto: respuesta.no_resuelto,
    sugerencias: respuesta.sugerencias?.slice(0, 3),
    acciones: acciones.length > 0 ? acciones : undefined,
    pasos: respuesta.pasos,
    advertencias: respuesta.advertencias,
    guia_verificada: respuesta.guia_verificada,
    banco: respuesta.banco,
    operacion: respuesta.operacion,
  };
}

/** Llega una propuesta nueva de un tipo → la anterior pendiente del mismo tipo caduca. */
function caducarDelMismoTipo(mensajes: MensajeChat[], nuevo: MensajeDelAsistente): MensajeChat[] {
  const tipos = new Set((nuevo.acciones ?? []).filter((a) => a.tipo !== 'abrir_pantalla').map((a) => a.tipo));
  if (tipos.size === 0) return mensajes;
  return mensajes.map((m) =>
    m.autor !== 'asistente' || !m.acciones?.some((a) => a.estado === 'pendiente' && tipos.has(a.tipo))
      ? m
      : {
          ...m,
          acciones: m.acciones.map((a) =>
            a.estado === 'pendiente' && tipos.has(a.tipo)
              ? { ...a, estado: 'caducada' as const, motivo: MOTIVO_CADUCA_NUEVA }
              : a,
          ),
        },
  );
}

export function useChat({ clave, sesion = null, contexto, conCola, activo }: OpcionesChat) {
  const conectado = useConexion();
  const { lectorActivo } = useAccesibilidad();
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  /** Conversación (clave + sesión) que ya se leyó: si cambia la venta, no se guarda la anterior encima. */
  const idConversacion = `${clave}|${sesion ?? ''}`;
  const [cargadoPara, setCargadoPara] = useState<string | null>(null);
  const cargado = cargadoPara === idConversacion;
  const [errorCarga, setErrorCarga] = useState(false);
  /** id del mensaje del tendero que espera respuesta (indicador "escribiendo…"). */
  const [esperando, setEsperando] = useState<string | null>(null);

  const refMensajes = useRef<MensajeChat[]>([]);
  const refControl = useRef<AbortController | null>(null);
  const refActivo = useRef(activo);
  const refContexto = useRef(contexto);

  useEffect(() => {
    refMensajes.current = mensajes;
  }, [mensajes]);
  useEffect(() => {
    refActivo.current = activo;
    refContexto.current = contexto;
  }, [activo, contexto]);

  // ---------- cargar / guardar ----------
  useEffect(() => {
    let vigente = true;
    leerChat(clave, sesion).then((r) => {
      if (!vigente) return;
      setMensajes(r.mensajes);
      refMensajes.current = r.mensajes;
      setErrorCarga(r.error);
      setCargadoPara(`${clave}|${sesion ?? ''}`);
    });
    return () => {
      vigente = false;
    };
  }, [clave, sesion]);

  useEffect(() => {
    if (cargado) guardarChat(clave, sesion, mensajes);
  }, [cargado, clave, sesion, mensajes]);

  // Cancelar la respuesta en curso si la pantalla/hoja desaparece.
  useEffect(() => () => refControl.current?.abort(), []);

  // Caducidad por tiempo con la pantalla abierta (no con lector activo: solo por cambio de datos).
  useEffect(() => {
    if (!cargado || lectorActivo) return;
    const t = setInterval(() => setMensajes((ms) => caducarVencidas(ms)), REVISION_CADUCIDAD_MS);
    return () => clearInterval(t);
  }, [cargado, lectorActivo]);

  const actualizarTendero = useCallback((id: string, cambios: Partial<MensajeTendero>) => {
    setMensajes((ms) => ms.map((m) => (m.id === id && m.autor === 'tendero' ? { ...m, ...cambios } : m)));
  }, []);

  // ---------- pedir respuesta ----------
  const pedirRespuesta = useCallback(
    async (id: string, texto: string, anuncio = 'Enviado. Tu asistente está escribiendo.') => {
      const control = new AbortController();
      refControl.current = control;
      setEsperando(id);
      const ctx = refContexto.current?.();
      if (refActivo.current) anunciar(anuncio);
      try {
        const respuesta = await enviarMensaje(
          {
            id_mensaje: id,
            texto,
            historial: historialParaServidor(refMensajes.current, id),
            contexto: ctx,
          },
          { signal: control.signal },
        );
        const nuevo = aMensajeLocal(respuesta, ctx);
        setMensajes((ms) =>
          recortar([
            ...caducarDelMismoTipo(ms, nuevo).map((m) =>
              m.id === id && m.autor === 'tendero' ? { ...m, estado: 'enviado' as const, error: undefined } : m,
            ),
            nuevo,
          ]),
        );
        if (refActivo.current) {
          const propuesta = nuevo.acciones?.some((a) => a.tipo !== 'abrir_pantalla' && a.estado === 'pendiente');
          anunciar(`${datosRol(nuevo.rol).nombre} dice: ${nuevo.texto}${propuesta ? '. Tiene una propuesta para confirmar.' : ''}`);
        }
      } catch (e) {
        const tipo: TipoError = esErrorApi(e) ? e.tipo : 'servidor';
        if (tipo === 'sin_conexion' && conCola) {
          actualizarTendero(id, { estado: 'en_espera', error: undefined });
          if (refActivo.current) anunciar('Se enviará al volver el internet');
        } else {
          actualizarTendero(id, { estado: 'fallido', error: tipo });
          if (refActivo.current) anunciar(`${motivoFallo(tipo)} Botón Reintentar disponible.`);
        }
      } finally {
        if (refControl.current === control) refControl.current = null;
        setEsperando((actual) => (actual === id ? null : actual));
      }
    },
    [actualizarTendero, conCola],
  );

  // ---------- acciones públicas ----------
  const enviar = useCallback(
    (texto: string): ResultadoEnvio => {
      const limpio = texto.trim();
      if (refControl.current) return { tipo: 'ocupado' };
      const nuevo: MensajeTendero = {
        id: crearIdLocal(),
        autor: 'tendero',
        texto: limpio,
        creado_en: new Date().toISOString(),
        estado: 'enviando',
      };
      if (conCola && conectado === false) {
        const anterior = refMensajes.current.find(
          (m): m is MensajeTendero => m.autor === 'tendero' && m.estado === 'en_espera',
        );
        const enEspera = { ...nuevo, estado: 'en_espera' as const };
        setMensajes((ms) => recortar([...ms.filter((m) => m.id !== anterior?.id), enEspera]));
        // Con reemplazo, el Snackbar hace su propio anuncio.
        if (!anterior && refActivo.current) anunciar('Se enviará al volver el internet');
        return anterior ? { tipo: 'reemplazo', anterior, nuevoId: nuevo.id } : { tipo: 'en_espera' };
      }
      setMensajes((ms) => recortar([...ms, nuevo]));
      refMensajes.current = [...refMensajes.current, nuevo];
      pedirRespuesta(nuevo.id, limpio);
      return { tipo: 'enviado' };
    },
    [conCola, conectado, pedirRespuesta],
  );

  const detener = useCallback(() => refControl.current?.abort(), []);

  const reintentar = useCallback(
    (id: string) => {
      if (refControl.current) return false;
      const m = refMensajes.current.find((x) => x.id === id);
      if (!m || m.autor !== 'tendero') return false;
      if (conCola && conectado === false) {
        actualizarTendero(id, { estado: 'en_espera', error: undefined });
        return true;
      }
      actualizarTendero(id, { estado: 'enviando', error: undefined });
      pedirRespuesta(id, m.texto); // mismo id_mensaje: el back no duplica la respuesta
      return true;
    },
    [actualizarTendero, conCola, conectado, pedirRespuesta],
  );

  const borrarMensaje = useCallback((id: string) => {
    setMensajes((ms) => ms.filter((m) => m.id !== id));
  }, []);

  const deshacerReemplazo = useCallback((anterior: MensajeTendero, nuevoId: string) => {
    setMensajes((ms) => recortar([...ms.filter((m) => m.id !== nuevoId), anterior]));
  }, []);

  const actualizarAccion = useCallback((idMensaje: string, idAccion: string, cambios: Partial<AccionChat>) => {
    setMensajes((ms) =>
      ms.map((m) =>
        m.id === idMensaje && m.autor === 'asistente' && m.acciones
          ? { ...m, acciones: m.acciones.map((a) => (a.id === idAccion ? { ...a, ...cambios } : a)) }
          : m,
      ),
    );
  }, []);

  /** Devuelve la copia para Deshacer. */
  const borrarTodo = useCallback(() => {
    refControl.current?.abort();
    const copia = refMensajes.current;
    setMensajes([]);
    return copia;
  }, []);

  const restaurar = useCallback((copia: MensajeChat[]) => setMensajes(copia), []);

  // ---------- al volver el internet: se envía la pregunta en espera (una vez) ----------
  useEffect(() => {
    if (!conCola || !cargado || conectado !== true || esperando) return;
    const pendiente = mensajes.find((m): m is MensajeTendero => m.autor === 'tendero' && m.estado === 'en_espera');
    if (!pendiente) return;
    // Breve espera: NetInfo suele avisar "conectado" un instante antes de que la red responda.
    const t = setTimeout(() => {
      if (refControl.current) return;
      actualizarTendero(pendiente.id, { estado: 'enviando' });
      pedirRespuesta(pendiente.id, pendiente.texto, 'Se envió tu pregunta. Tu asistente está escribiendo.');
    }, ESPERA_RECONEXION_MS);
    return () => clearTimeout(t);
  }, [conCola, cargado, conectado, esperando, mensajes, actualizarTendero, pedirRespuesta]);

  return {
    cargado,
    errorCarga,
    mensajes,
    esperando: esperando !== null,
    enviar,
    detener,
    reintentar,
    borrarMensaje,
    deshacerReemplazo,
    actualizarAccion,
    borrarTodo,
    restaurar,
  };
}

export type Chat = ReturnType<typeof useChat>;
