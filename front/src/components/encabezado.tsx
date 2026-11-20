import { StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import { color, espacio, medidas, type } from '@/theme';

import { Boton } from './boton';
import { EtiquetaSimulacion } from './etiqueta-simulacion';

export interface EncabezadoProps {
  titulo: string;
  onAtras?: () => void;
  tipoAtras?: 'atras' | 'cerrar';
  accionDerecha?: {
    texto: string;
    icono: NombreIcono;
    onPress: () => void;
    accessibilityHint?: string;
    deshabilitado?: boolean;
  };
  etiquetaSimulacion?: boolean;
  /**
   * La pantalla pasa `scrollY > 0`: la barra cambia a `surfaceContainer` (elevación nivel 2 SOLO tonal,
   * sin sombra; 00-sistema §9.13 `elevadoAlDesplazar`).
   */
  desplazado?: boolean;
}

/**
 * M3 Top app bar small (00-sistema §9.13). Alto 64; título `titleLarge` que envuelve.
 * EXC-8: "Atrás"/"Cerrar" con icono + texto (Boton text).
 */
export function Encabezado({
  titulo,
  onAtras,
  tipoAtras = 'atras',
  accionDerecha,
  etiquetaSimulacion,
  desplazado = false,
}: EncabezadoProps) {
  return (
    <View>
      <View style={[estilos.barra, desplazado && estilos.desplazado]}>
        {onAtras ? (
          <Boton
            texto={tipoAtras === 'cerrar' ? 'Cerrar' : 'Atrás'}
            icono={tipoAtras === 'cerrar' ? 'close' : 'arrow-left'}
            variante="text"
            anchoCompleto={false}
            onPress={onAtras}
            style={estilos.boton}
          />
        ) : null}
        <Text style={[estilos.titulo, !onAtras && estilos.tituloSolo]} accessibilityRole="header">
          {titulo}
        </Text>
        {accionDerecha ? (
          <Boton
            texto={accionDerecha.texto}
            icono={accionDerecha.icono}
            variante="text"
            anchoCompleto={false}
            onPress={accionDerecha.onPress}
            accessibilityHint={accionDerecha.accessibilityHint}
            deshabilitado={accionDerecha.deshabilitado}
            motivoDeshabilitado={accionDerecha.accessibilityHint}
            style={estilos.boton}
          />
        ) : null}
      </View>
      {etiquetaSimulacion ? <EtiquetaSimulacion modo="franja" /> : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  barra: {
    minHeight: medidas.barraSuperior,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.xs,
    paddingVertical: espacio.s,
    backgroundColor: color.surface,
  },
  desplazado: { backgroundColor: color.surfaceContainer },
  boton: { alignSelf: 'center' },
  titulo: { ...type.titleLarge, color: color.onSurface, flex: 1, paddingHorizontal: espacio.xs },
  tituloSolo: { paddingHorizontal: espacio.m },
});
