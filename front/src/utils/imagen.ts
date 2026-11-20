import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

import { IMAGEN_CALIDAD, IMAGEN_LADO_MAXIMO } from '@/constants';

/** Reduce la foto a lado largo ≤ 1280 px y JPEG 0.7 antes de subirla. */
export async function comprimirImagen(uri: string): Promise<string> {
  const contexto = ImageManipulator.manipulate(uri, {
    maxWidth: IMAGEN_LADO_MAXIMO,
    maxHeight: IMAGEN_LADO_MAXIMO,
  });
  try {
    const imagen = await contexto.renderAsync();
    try {
      const resultado = await imagen.saveAsync({ compress: IMAGEN_CALIDAD, format: SaveFormat.JPEG });
      return resultado.uri;
    } finally {
      imagen.release();
    }
  } finally {
    contexto.release();
  }
}
