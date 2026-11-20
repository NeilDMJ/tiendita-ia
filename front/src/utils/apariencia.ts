import { reloadAppAsync } from 'expo';
import Storage from 'expo-sqlite/kv-store';
import { DevSettings, Platform } from 'react-native';

import { CLAVE_APARIENCIA, type PreferenciaApariencia } from '@/theme';

/**
 * Guarda la preferencia de apariencia e INTENTA reiniciar la app para aplicarla.
 * Hay que reiniciar porque los estilos congelan los colores al cargar (ver `theme.ts`).
 * Las ventas en borrador, la cola sin conexión y el chat están en SQLite: el reinicio no los borra.
 *
 * El reinicio automático NO está garantizado: si funciona, la app se recarga y esta función no vuelve;
 * si no, la preferencia ya quedó guardada y quien llama debe pedir cerrar y abrir la app a mano
 * (la pantalla lo hace con un temporizador). Nunca debe quedarse esperando para siempre.
 *
 * - Web: recarga la página.
 * - Expo Go / desarrollo: `DevSettings.reload()` (`reloadAppAsync` no recarga ahí).
 * - Compilación de producción: `reloadAppAsync`.
 */
export async function aplicarApariencia(preferencia: PreferenciaApariencia): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(CLAVE_APARIENCIA, preferencia);
    else Storage.setItemSync(CLAVE_APARIENCIA, preferencia);
  } catch {
    // Si no se pudo guardar, igual se intenta reiniciar: quedará la preferencia anterior.
  }

  if (Platform.OS === 'web') {
    globalThis.location?.reload();
    return;
  }

  try {
    if (__DEV__) DevSettings.reload();
    else await reloadAppAsync('Cambio de apariencia');
  } catch {
    // Sin reinicio automático: la pantalla avisa que hay que reabrir la app.
  }
}
