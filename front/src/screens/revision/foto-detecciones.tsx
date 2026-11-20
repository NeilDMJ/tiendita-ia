import { Image } from 'expo-image';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { bordes, camara, color, espacio, medidas, shape, type } from '@/theme';
import { nivelDeItem, type ItemEditable } from '@/utils/carrito';

export interface FotoDeteccionesProps {
  uri: string;
  items: ItemEditable[];
}

type Tamano = { ancho: number; alto: number };

/**
 * Foto original con recuadros numerados (mismo número que la fila).
 * Los recuadros se posicionan sobre el rectángulo REAL de la imagen (no sobre el contenedor),
 * porque `contentFit="contain"` deja franjas vacías según la proporción de la foto.
 * `caja` = [x, y, ancho, alto] normalizada 0–1 respecto a la foto.
 */
export function FotoDetecciones({ uri, items }: FotoDeteccionesProps) {
  const [contenedor, setContenedor] = useState<Tamano | null>(null);
  const [foto, setFoto] = useState<Tamano | null>(null);

  let area: (Tamano & { x: number; y: number }) | null = null;
  if (contenedor && foto && foto.ancho > 0 && foto.alto > 0) {
    const escala = Math.min(contenedor.ancho / foto.ancho, contenedor.alto / foto.alto);
    const ancho = foto.ancho * escala;
    const alto = foto.alto * escala;
    area = { ancho, alto, x: (contenedor.ancho - ancho) / 2, y: (contenedor.alto - alto) / 2 };
  }

  return (
    <View
      style={estilos.contenedor}
      onLayout={(e) => setContenedor({ ancho: e.nativeEvent.layout.width, alto: e.nativeEvent.layout.height })}
    >
      <Image
        source={{ uri }}
        style={StyleSheet.absoluteFill}
        contentFit="contain"
        accessibilityLabel="Foto de los productos. Los números coinciden con los de la lista."
        onLoad={(e) => setFoto({ ancho: e.source.width, alto: e.source.height })}
      />
      {area ? (
        <View
          pointerEvents="none"
          style={[estilos.area, { left: area.x, top: area.y, width: area.ancho, height: area.alto }]}
        >
          {items
            .filter((i) => i.caja)
            .map((i) => {
              const [x, y, w, h] = i.caja!;
              const nivel = nivelDeItem(i);
              const borde = nivel === 'falta' ? color.error : nivel === 'baja' ? color.warning : color.primary;
              return (
                <View
                  key={i.clave}
                  style={[
                    estilos.caja,
                    {
                      left: `${x * 100}%`,
                      top: `${y * 100}%`,
                      width: `${w * 100}%`,
                      height: `${h * 100}%`,
                      borderColor: borde,
                    },
                  ]}
                >
                  <Text style={estilos.numero}>{i.numero}</Text>
                </View>
              );
            })}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: {
    height: medidas.miniaturaFoto,
    marginTop: espacio.s,
    borderRadius: shape.large,
    backgroundColor: color.surfaceContainerHighest,
    overflow: 'hidden',
  },
  area: { position: 'absolute' },
  caja: { position: 'absolute', borderWidth: bordes.grueso },
  numero: {
    ...type.labelLarge,
    alignSelf: 'flex-start',
    paddingHorizontal: espacio.xs,
    borderBottomRightRadius: shape.small,
    backgroundColor: camara.oscuro,
    color: camara.claro,
  },
});
