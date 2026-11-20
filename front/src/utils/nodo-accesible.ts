import { findNodeHandle, Platform } from 'react-native';

/**
 * Id nativo de un nodo para `AccessibilityInfo.setAccessibilityFocus`.
 * En web `findNodeHandle` no existe (lanza "findNodeHandle is not supported on web"): devuelve null y el foco no se mueve.
 */
export function nodoAccesible(ref: unknown): number | null {
  if (Platform.OS === 'web' || !ref) return null;
  return findNodeHandle(ref as Parameters<typeof findNodeHandle>[0]) ?? null;
}
