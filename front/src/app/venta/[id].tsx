import { ContenedorPantalla } from '@/components/contenedor-pantalla';
import { useLocalSearchParams } from 'expo-router';

import { PantallaComprobante } from '@/screens/comprobante';

/** Comprobante de venta: /venta/{id}?origen=historial */
export default function Venta() {
  const { id, origen } = useLocalSearchParams<{ id: string; origen?: string }>();
  return (
    <ContenedorPantalla>
      <PantallaComprobante id={id} desdeHistorial={origen === 'historial'} />
    </ContenedorPantalla>
  );
}
