import { SafeAreaView } from 'react-native-safe-area-context';

import { ContenedorPantalla } from '@/components/contenedor-pantalla';
import { PantallaAsistente } from '@/screens/asistente/pantalla-asistente';

/** Pestaña Asistente: chat unificado (02-asistente §2). */
export default function Asistente() {
  // La cabecera nativa se oculta (la pantalla trae la suya con "Borrar chat"): se respeta el área segura superior.
  return (
    <SafeAreaView edges={['top']} style={{ flex: 1 }}>
      <ContenedorPantalla>
        <PantallaAsistente />
      </ContenedorPantalla>
    </SafeAreaView>
  );
}
