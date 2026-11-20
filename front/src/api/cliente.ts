/**
 * Cliente HTTP con timeout y errores tipados con mensaje humano.
 * La UI nunca muestra términos técnicos: usa `error.mensaje`.
 */
import { File } from 'expo-file-system';
import { Platform } from 'react-native';
import type { z } from 'zod';

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
export const USAR_MOCKS = process.env.EXPO_PUBLIC_USE_MOCKS === '1';

const TIEMPO_MAXIMO_MS = 30_000;

export type TipoError =
  | 'sin_conexion'
  | 'tiempo_agotado'
  | 'imagen_no_procesable'
  | 'datos_faltantes'
  | 'sin_existencia'
  | 'servidor'
  | 'respuesta_invalida'
  | 'cancelado';

const MENSAJES: Record<TipoError, string> = {
  sin_conexion: 'Sin conexión. Revisa tu internet e intenta de nuevo.',
  tiempo_agotado: 'Esto está tardando mucho. Intenta de nuevo en un momento.',
  imagen_no_procesable: 'No pudimos leer la foto. Acércate más, evita reflejos y toma otra.',
  datos_faltantes: 'Faltan datos para continuar. Revisa los campos marcados.',
  sin_existencia: 'No hay suficientes piezas en existencia. Ajusta la cantidad.',
  servidor: 'El servicio no respondió bien. Intenta de nuevo en un momento.',
  respuesta_invalida: 'Recibimos información incompleta. Intenta de nuevo o captúralo a mano.',
  cancelado: 'Cancelaste la operación.',
};

export class ErrorApi extends Error {
  constructor(
    public tipo: TipoError,
    public mensaje: string = MENSAJES[tipo],
    /** Cuerpo del error (p. ej. 409 → { sku, existencia }). */
    public detalle: unknown = null,
  ) {
    super(mensaje);
  }
}

export function esErrorApi(e: unknown): e is ErrorApi {
  return e instanceof ErrorApi;
}

function tipoPorEstado(status: number): TipoError {
  if (status === 422) return 'imagen_no_procesable';
  if (status === 400) return 'datos_faltantes';
  if (status === 409) return 'sin_existencia';
  return 'servidor';
}

export type OpcionesPedido = {
  /** Para que la UI pueda cancelar (p. ej. "Cancelar" durante el análisis). */
  signal?: AbortSignal;
  tiempoMs?: number;
};

export async function pedir<T>(
  ruta: string,
  esquema: z.ZodType<T>,
  init: RequestInit = {},
  opciones: OpcionesPedido = {},
): Promise<T> {
  const control = new AbortController();
  let porTiempo = false;
  const temporizador = setTimeout(() => {
    porTiempo = true;
    control.abort();
  }, opciones.tiempoMs ?? TIEMPO_MAXIMO_MS);
  const alCancelar = () => control.abort();
  opciones.signal?.addEventListener('abort', alCancelar);

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, { ...init, signal: control.signal });
  } catch {
    if (opciones.signal?.aborted) throw new ErrorApi('cancelado');
    throw new ErrorApi(porTiempo ? 'tiempo_agotado' : 'sin_conexion');
  } finally {
    clearTimeout(temporizador);
    opciones.signal?.removeEventListener('abort', alCancelar);
  }
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    throw new ErrorApi(tipoPorEstado(respuesta.status), undefined, cuerpo);
  }

  const json = await respuesta.json().catch(() => null);
  const resultado = esquema.safeParse(json);
  if (!resultado.success) throw new ErrorApi('respuesta_invalida');
  return resultado.data;
}

export function pedirJson<T>(ruta: string, esquema: z.ZodType<T>, cuerpo: unknown, opciones?: OpcionesPedido) {
  return pedir(
    ruta,
    esquema,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    },
    opciones,
  );
}

export async function subirImagen<T>(ruta: string, esquema: z.ZodType<T>, uri: string, opciones?: OpcionesPedido) {
  const datos = new FormData();
  if (Platform.OS === 'web') {
    // En web la URI es blob:/data:; se sube como Blob.
    const blob = await (await fetch(uri)).blob();
    datos.append('imagen', blob, 'foto.jpg');
  } else {
    // El fetch de Expo (SDK 52+) NO acepta { uri, name, type } de React Native
    // ("Unsupported FormDataPart implementation"): necesita un objeto con bytes(), como File.
    datos.append('imagen', new File(uri) as unknown as Blob, 'foto.jpg');
  }
  return pedir(ruta, esquema, { method: 'POST', body: datos }, opciones);
}
