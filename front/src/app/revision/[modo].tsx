import { router, useLocalSearchParams } from 'expo-router';

import { ContenedorPantalla } from '@/components/contenedor-pantalla';
import { PantallaPendiente } from '@/components/pantalla-pendiente';
import { Encabezado } from '@/components/encabezado';
import { PantallaRevisionCobro } from '@/screens/revision-cobro';

/** Revisión editable de lo que detectó la cámara: /revision/cobro|alta|ticket */
export default function Revision() {
  const { modo, agregar } = useLocalSearchParams<{ modo: string; agregar?: string }>();
  if (modo === 'cobro') {
    return (
      <ContenedorPantalla>
        <PantallaRevisionCobro abrirAgregar={agregar === '1'} />
      </ContenedorPantalla>
    );
  }
  return (
    <>
      <Encabezado titulo="Revisión" onAtras={() => router.back()} />
      <PantallaPendiente
        titulo={modo === 'alta' ? 'Agregar mercancía' : 'Ticket de gasto'}
        descripcion="Esta revisión todavía no está lista. Por ahora solo funciona Cobrar con foto."
      />
    </>
  );
}
