import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ResumenVenta } from '@/hooks/use-ventas-hoy';
import { bordes, colores, espacio, iconos, tactil, tipografia } from '@/theme';
import { hora } from '@/utils/fecha';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

export interface FilaVentaProps {
  venta: ResumenVenta;
  onPress: () => void;
}

/** Fila tocable de una venta del día. "Pendiente de enviar" con icono + texto. */
export function FilaVenta({ venta, onPress }: FilaVentaProps) {
  const productos = `${venta.productos} ${venta.productos === 1 ? 'producto' : 'productos'}`;
  const metodo = venta.metodo === 'efectivo' ? 'Efectivo' : 'Pago digital (simulación)';
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${hora(venta.creadaEn)}, ${productos}, ${venta.pendiente ? 'pendiente de enviar' : metodo}, ${montoParaLector(venta.total)}`}
      accessibilityHint="Abre el comprobante"
      style={({ pressed }) => [estilos.fila, pressed && estilos.presionado]}
    >
      <Text style={estilos.hora}>{hora(venta.creadaEn)}</Text>
      <View style={estilos.centro}>
        <Text style={estilos.texto}>{productos}</Text>
        {venta.pendiente ? (
          <View style={estilos.pendiente}>
            <MaterialCommunityIcons name="cloud-upload" size={iconos.chico} color={colores.texto} />
            <Text style={estilos.textoPendiente}>Pendiente de enviar</Text>
          </View>
        ) : (
          <Text style={estilos.secundario}>{metodo}</Text>
        )}
      </View>
      <Text style={estilos.monto}>{formatoMoneda(venta.total)}</Text>
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  fila: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    paddingVertical: espacio.s,
    paddingHorizontal: espacio.l,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.divisor,
  },
  presionado: { backgroundColor: colores.superficie },
  hora: { ...tipografia.etiqueta, color: colores.texto, fontVariant: ['tabular-nums'] },
  centro: { flex: 1, gap: espacio.xs },
  texto: { ...tipografia.cuerpo, color: colores.texto },
  secundario: { ...tipografia.cuerpo, color: colores.textoSecundario },
  pendiente: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoPendiente: { ...tipografia.etiqueta, color: colores.texto },
  monto: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'] },
});
