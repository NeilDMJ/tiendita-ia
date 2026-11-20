import { useLocalSearchParams } from 'expo-router';

import { PantallaCamara } from '@/screens/camara';

/** Ruta modal de cámara: /camara?modo=cobro|alta|ticket */
export default function Camara() {
  const { modo } = useLocalSearchParams<{ modo?: string }>();
  return <PantallaCamara modo={modo} />;
}
