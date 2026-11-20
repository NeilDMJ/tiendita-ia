/**
 * Almacenamiento local clave-valor (SQLite, incluido en Expo Go).
 * Guarda el borrador de la venta y la cola de ventas sin conexión.
 */
import Storage from 'expo-sqlite/kv-store';

export async function leerJson<T>(clave: string, porDefecto: T): Promise<T> {
  try {
    const texto = await Storage.getItemAsync(clave);
    return texto ? (JSON.parse(texto) as T) : porDefecto;
  } catch {
    return porDefecto;
  }
}

export async function guardarJson(clave: string, valor: unknown): Promise<void> {
  try {
    await Storage.setItemAsync(clave, JSON.stringify(valor));
  } catch {
    // Si el almacenamiento falla, la app sigue funcionando en memoria.
  }
}

/** Igual que `leerJson`, pero dice si la lectura falló (para avisar "No pudimos abrir…"). */
export async function leerJsonConError<T>(clave: string): Promise<{ valor: T | null; error: boolean }> {
  try {
    const texto = await Storage.getItemAsync(clave);
    return { valor: texto ? (JSON.parse(texto) as T) : null, error: false };
  } catch {
    return { valor: null, error: true };
  }
}
