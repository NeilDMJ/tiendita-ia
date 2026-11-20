import { useWindowDimensions } from 'react-native';

/** Letra del sistema ≥ 1.3×: burbujas a ancho completo, botones debajo del campo, chips apilados. */
export const ESCALA_LETRA_GRANDE = 1.3;

export function useLetraGrande() {
  return useWindowDimensions().fontScale >= ESCALA_LETRA_GRANDE;
}
