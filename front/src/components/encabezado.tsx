import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, colores, espacio, iconos, medidas, radios, tactil, tipografia } from '@/theme';

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
}

function BotonEncabezado({
  texto,
  icono,
  onPress,
  hint,
  deshabilitado,
}: {
  texto: string;
  icono: NombreIcono;
  onPress: () => void;
  hint?: string;
  deshabilitado?: boolean;
}) {
  const color = deshabilitado ? colores.deshabilitadoTexto : colores.texto;
  return (
    <Pressable
      onPress={deshabilitado ? undefined : onPress}
      accessibilityRole="button"
      accessibilityLabel={texto}
      accessibilityHint={hint}
      accessibilityState={{ disabled: deshabilitado }}
      style={({ pressed }) => [estilos.boton, pressed && !deshabilitado && estilos.presionado]}
    >
      <MaterialCommunityIcons name={icono} size={iconos.linea} color={color} />
      <Text style={[estilos.textoBoton, { color }]}>{texto}</Text>
    </Pressable>
  );
}

/** Encabezado plano de pantallas del Stack: Atrás/Cerrar + título + una acción opcional. */
export function Encabezado({ titulo, onAtras, tipoAtras = 'atras', accionDerecha, etiquetaSimulacion }: EncabezadoProps) {
  return (
    <View>
      <View style={estilos.barra}>
        {onAtras ? (
          <BotonEncabezado
            texto={tipoAtras === 'cerrar' ? 'Cerrar' : 'Atrás'}
            icono={tipoAtras === 'cerrar' ? 'close' : 'arrow-left'}
            onPress={onAtras}
          />
        ) : null}
        <Text style={estilos.titulo} accessibilityRole="header">
          {titulo}
        </Text>
        {accionDerecha ? (
          <BotonEncabezado
            texto={accionDerecha.texto}
            icono={accionDerecha.icono}
            onPress={accionDerecha.onPress}
            hint={accionDerecha.accessibilityHint}
            deshabilitado={accionDerecha.deshabilitado}
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
    gap: espacio.s,
    paddingHorizontal: espacio.s,
    backgroundColor: colores.fondo,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.divisor,
  },
  titulo: { ...tipografia.subtitulo, color: colores.texto, flex: 1, paddingHorizontal: espacio.s },
  boton: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.s,
    borderRadius: radios.medio,
  },
  presionado: { backgroundColor: colores.superficie },
  textoBoton: { ...tipografia.etiqueta },
});
