import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { medidas } from '@/theme';

/**
 * Centra el contenido de una pantalla con ancho máximo (640 dp) en web y tablet.
 * En un teléfono (< 640 dp) no cambia nada. La barra de pestañas y el fondo siguen a todo el ancho.
 * Se usa en los archivos de ruta: `<ContenedorPantalla><PantallaX /></ContenedorPantalla>`.
 */
export function ContenedorPantalla({ children }: { children: ReactNode }) {
  return (
    <View style={estilos.fuera}>
      <View style={estilos.dentro}>{children}</View>
    </View>
  );
}

const estilos = StyleSheet.create({
  fuera: { flex: 1, alignItems: 'center' },
  dentro: { flex: 1, width: '100%', maxWidth: medidas.contenidoAnchoMaximo },
});
