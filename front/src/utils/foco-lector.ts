import { AccessibilityInfo, findNodeHandle, Platform } from 'react-native';

/**
 * Mueve el foco del lector de pantalla (TalkBack / VoiceOver) a un elemento.
 * En web no existe `findNodeHandle` (lanza error), así que no hace nada: el foco ahí lo maneja el navegador.
 */
export function enfocarParaLector(elemento: unknown): void {
  if (Platform.OS === 'web' || !elemento) return;
  const nodo = findNodeHandle(elemento as Parameters<typeof findNodeHandle>[0]);
  if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
}
