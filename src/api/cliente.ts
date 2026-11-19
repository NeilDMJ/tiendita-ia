/**
 * Cliente HTTP con timeout y errores tipados con mensaje humano.
 * La UI nunca muestra términos técnicos: usa `error.mensaje`.
 */
import type { z } from 'zod';

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
export const USAR_MOCKS = process.env.EXPO_PUBLIC_USE_MOCKS === '1';

const TIEMPO_MAXIMO_MS = 30_000;

export type TipoError =
  | 'sin_conexion'
  | 'tiempo_agotado'
  | 'imagen_no_procesable'
  | 'datos_faltantes'
  | 'servidor'
  | 'respuesta_invalida';

const MENSAJES: Record<TipoError, string> = {
  sin_conexion: 'Sin conexión. Revisa tu internet e intenta de nuevo.',
  tiempo_agotado: 'Esto está tardando mucho. Intenta de nuevo en un momento.',
  imagen_no_procesable: 'No pudimos leer la foto. Acércate más, evita reflejos y toma otra.',
  datos_faltantes: 'Faltan datos para continuar. Revisa los campos marcados.',
  servidor: 'El servicio no respondió bien. Intenta de nuevo en un momento.',
  respuesta_invalida: 'Recibimos información incompleta. Intenta de nuevo o captúralo a mano.',
};

export class ErrorApi extends Error {
  constructor(
    public tipo: TipoError,
    public mensaje: string = MENSAJES[tipo],
  ) {
    super(mensaje);
  }
}

function tipoPorEstado(status: number): TipoError {
  if (status === 422) return 'imagen_no_procesable';
  if (status === 400) return 'datos_faltantes';
  return 'servidor';
}

export async function pedir<T>(
  ruta: string,
  esquema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  const control = new AbortController();
  const temporizador = setTimeout(() => control.abort(), TIEMPO_MAXIMO_MS);
  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, { ...init, signal: control.signal });
  } catch {
    throw new ErrorApi(control.signal.aborted ? 'tiempo_agotado' : 'sin_conexion');
  } finally {
    clearTimeout(temporizador);
  }
  if (!respuesta.ok) throw new ErrorApi(tipoPorEstado(respuesta.status));

  const json = await respuesta.json().catch(() => null);
  const resultado = esquema.safeParse(json);
  if (!resultado.success) throw new ErrorApi('respuesta_invalida');
  return resultado.data;
}

export function pedirJson<T>(ruta: string, esquema: z.ZodType<T>, cuerpo: unknown) {
  return pedir(ruta, esquema, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  });
}

export function subirImagen<T>(ruta: string, esquema: z.ZodType<T>, uri: string) {
  const datos = new FormData();
  // React Native acepta { uri, name, type } como archivo en FormData.
  datos.append('imagen', { uri, name: 'foto.jpg', type: 'image/jpeg' } as unknown as Blob);
  return pedir(ruta, esquema, { method: 'POST', body: datos });
}
