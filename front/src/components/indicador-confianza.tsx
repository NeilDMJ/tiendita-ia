import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, colores, espacio, iconos, medidas, radios, tipografia } from '@/theme';
import type { NivelConfianza } from '@/utils/carrito';

export interface IndicadorConfianzaProps {
  nivel: NivelConfianza;
  /** 'Falta precio' | 'Elige producto' */
  textoFalta?: string;
}

const NIVELES: Record<NivelConfianza, { icono: NombreIcono; colorIcono: string; texto: string }> = {
  alta: { icono: 'check-circle', colorIcono: colores.exito, texto: 'Detectado' },
  baja: { icono: 'help-circle', colorIcono: colores.texto, texto: 'Revisa' },
  falta: { icono: 'alert-circle', colorIcono: colores.peligro, texto: 'Falta precio' },
  manual: { icono: 'pencil', colorIcono: colores.textoSecundario, texto: 'Tú lo pusiste' },
};

/**
 * Chip de estado de lo detectado. Nunca muestra porcentaje ni la palabra "confianza".
 * No es elemento separado para el lector: su texto va en el label de la fila.
 */
export function IndicadorConfianza({ nivel, textoFalta }: IndicadorConfianzaProps) {
  const n = NIVELES[nivel];
  const texto = nivel === 'falta' && textoFalta ? textoFalta : n.texto;
  return (
    <View
      style={[estilos.chip, nivel === 'baja' && estilos.baja, nivel === 'falta' && estilos.falta]}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      <MaterialCommunityIcons name={n.icono} size={iconos.chico} color={n.colorIcono} />
      <Text
        style={[
          estilos.texto,
          nivel === 'baja' && estilos.textoBaja,
          nivel === 'falta' && estilos.textoFalta,
        ]}
      >
        {texto}
      </Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: espacio.xs,
    minHeight: medidas.chip,
    paddingHorizontal: espacio.s,
    borderRadius: radios.chico,
  },
  baja: { borderWidth: bordes.grueso, borderColor: colores.texto, backgroundColor: colores.fondo },
  falta: { borderWidth: bordes.grueso, borderColor: colores.peligro, backgroundColor: colores.fondo },
  texto: { ...tipografia.etiqueta, color: colores.textoSecundario },
  textoBaja: { color: colores.texto },
  textoFalta: { color: colores.peligro },
});
