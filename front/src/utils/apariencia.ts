import { reloadAppAsync } from 'expo';
import Storage from 'expo-sqlite/kv-store';
import { Platform } from 'react-native';

import { CLAVE_APARIENCIA, type PreferenciaApariencia } from '@/theme';

/**
 * Guarda la preferencia de apariencia y reinicia la app para aplicarla.
 * Hay que reiniciar porque los estilos congelan los colores al cargar (ver `theme.ts`).
 * Las ventas en borrador, la cola sin conexión y el chat están en SQLite: el reinicio no los borra.
 */
export async function aplicarApariencia(preferencia: PreferenciaApariencia): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(CLAVE_APARIENCIA, preferencia);
    else Storage.setItemSync(CLAVE_APARIENCIA, preferencia);
  } catch {
    // Si no se pudo guardar, igual se reinicia: quedará la preferencia anterior.
  }
  if (Platform.OS === 'web') {
    globalThis.location?.reload();
    return;
  }
  await reloadAppAsync('Cambio de apariencia');
}
