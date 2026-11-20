import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { ResumenVenta } from '@/hooks/use-ventas-hoy';
import { bordes, color, espacio, iconos, medidas, type } from '@/theme';
import { hora } from '@/utils/fecha';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import { Tocable } from './tocable';

export interface FilaVentaProps {
  venta: ResumenVenta;
  onPress: () => void;
}

/** M3 List item de 2 líneas, tocable. "Pendiente de enviar" con icono + texto. */
export function FilaVenta({ venta, onPress }: FilaVentaProps) {
  const productos = `${venta.productos} ${venta.productos === 1 ? 'producto' : 'productos'}`;
  const metodo = venta.metodo === 'efectivo' ? 'Efectivo' : 'Pago digital (simulación)';
  return (
    <Tocable
      onPress={onPress}
      colorContenido={color.onSurface}
      accessibilityRole="button"
      accessibilityLabel={`${hora(venta.creadaEn)}, ${productos}, ${venta.pendiente ? 'pendiente de enviar' : metodo}, ${montoParaLector(venta.total)}`}
      accessibilityHint="Abre el comprobante"
      style={estilos.fila}
    >
      <Text style={estilos.hora}>{hora(venta.creadaEn)}</Text>
      <View style={estilos.centro}>
        <Text style={estilos.texto}>{productos}</Text>
        {venta.pendiente ? (
          <View style={estilos.pendiente}>
            <MaterialCommunityIcons
              name="cloud-upload"
              size={iconos.chico}
              color={color.onSurfaceVariant}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.textoPendiente}>Pendiente de enviar</Text>
          </View>
        ) : (
          <Text style={estilos.secundario}>{metodo}</Text>
        )}
      </View>
      <Text style={estilos.monto}>{formatoMoneda(venta.total)}</Text>
      <View style={estilos.divisor} />
    </Tocable>
  );
}

const estilos = StyleSheet.create({
  fila: {
    minHeight: medidas.filaVenta,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.l,
    paddingVertical: espacio.s,
    paddingHorizontal: espacio.l,
    backgroundColor: color.surface,
  },
  divisor: {
    position: 'absolute',
    left: espacio.l,
    right: 0,
    bottom: 0,
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
  },
  hora: { ...type.labelLarge, color: color.onSurface, fontVariant: ['tabular-nums'] },
  centro: { flex: 1, gap: espacio.xs },
  texto: { ...type.bodyLarge, color: color.onSurface },
  secundario: { ...type.bodyLarge, color: color.onSurfaceVariant },
  pendiente: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoPendiente: { ...type.labelLarge, color: color.onSurfaceVariant },
  monto: { ...type.amount, color: color.onSurface },
});
