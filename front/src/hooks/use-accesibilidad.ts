import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

/** Estado de ajustes de accesibilidad del sistema (movimiento reducido y lector de pantalla). */
export function useAccesibilidad() {
  const [reducirMovimiento, setReducirMovimiento] = useState(false);
  const [lectorActivo, setLectorActivo] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducirMovimiento).catch(() => undefined);
    AccessibilityInfo.isScreenReaderEnabled().then(setLectorActivo).catch(() => undefined);
    const a = AccessibilityInfo.addEventListener('reduceMotionChanged', setReducirMovimiento);
    const b = AccessibilityInfo.addEventListener('screenReaderChanged', setLectorActivo);
    return () => {
      a.remove();
      b.remove();
    };
  }, []);

  return { reducirMovimiento, lectorActivo };
}
