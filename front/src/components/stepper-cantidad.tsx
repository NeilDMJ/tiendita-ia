import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { StyleSheet, Text, TextInput, View, type StyleProp, type ViewStyle } from 'react-native';

import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';

import { Tocable } from './tocable';

type Unidad = 'pz' | 'kg' | 'paq';

export interface StepperCantidadProps {
  valor: number;
  onCambiar: (n: number) => void;
  minimo?: number;
  /** Existencia disponible; bloquea el + al llegar. */
  maximo?: number;
  unidad?: Unidad;
  /** Si se pasa, en el mínimo el − se vuelve "Quitar". */
  onQuitar?: () => void;
  nombreProducto: string;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

const NOMBRE_UNIDAD: Record<Unidad, [string, string]> = {
  pz: ['pieza', 'piezas'],
  kg: ['kilo', 'kilos'],
  paq: ['paquete', 'paquetes'],
};

/**
 * Cantidad con − / + (00-sistema §9.3): dos icon buttons tonales 48 + valor tocable.
 * Tocar el número permite escribirlo (cantidades grandes sin 12 toques).
 */
export function StepperCantidad({
  valor,
  onCambiar,
  minimo = 1,
  maximo,
  unidad = 'pz',
  onQuitar,
  nombreProducto,
  testID,
  style,
}: StepperCantidadProps) {
  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState('');
  const enMinimo = valor <= minimo;
  const enMaximo = maximo !== undefined && valor >= maximo;
  const modoQuitar = enMinimo && onQuitar !== undefined;
  const [singular, plural] = NOMBRE_UNIDAD[unidad];
  const textoValor = `${valor} ${valor === 1 ? singular : plural}`;

  const limitar = (n: number) => Math.max(minimo, maximo !== undefined ? Math.min(n, maximo) : n);

  function restar() {
    if (modoQuitar) onQuitar?.();
    else if (!enMinimo) onCambiar(valor - 1);
  }
  function sumar() {
    if (!enMaximo) onCambiar(valor + 1);
  }
  function terminarEdicion() {
    const n = parseInt(borrador, 10);
    if (!Number.isNaN(n)) onCambiar(limitar(n));
    setEditando(false);
  }

  const menosInactivo = enMinimo && !modoQuitar;
  const colorMenos = modoQuitar ? color.error : menosInactivo ? color.onSurfaceVariant : color.onSecondaryContainer;
  const colorMas = enMaximo ? color.onSurfaceVariant : color.onSecondaryContainer;

  return (
    <View style={[estilos.contenedor, style]} testID={testID}>
      <View style={estilos.grupo}>
        <Tocable
          onPress={restar}
          disabled={menosInactivo}
          colorContenido={colorMenos}
          radio={shape.full}
          sinCapa={menosInactivo}
          accessibilityRole="button"
          accessibilityLabel={
            modoQuitar ? `Quitar ${nombreProducto} de la venta` : `Quitar una ${singular} de ${nombreProducto}`
          }
          accessibilityState={{ disabled: menosInactivo }}
          style={[
            estilos.boton,
            modoQuitar ? estilos.botonQuitar : menosInactivo ? estilos.botonDeshabilitado : estilos.botonTonal,
          ]}
        >
          <MaterialCommunityIcons
            name={modoQuitar ? 'trash-can-outline' : 'minus'}
            size={iconos.linea}
            color={colorMenos}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        </Tocable>

        {editando ? (
          <TextInput
            value={borrador}
            onChangeText={(t) => setBorrador(t.replace(/\D/g, ''))}
            onBlur={terminarEdicion}
            onSubmitEditing={terminarEdicion}
            keyboardType="number-pad"
            inputMode="numeric"
            autoFocus
            selectTextOnFocus
            accessibilityLabel={`Escribe la cantidad de ${nombreProducto}`}
            style={[estilos.valor, estilos.valorCaja, estilos.valorEditando]}
          />
        ) : (
          <Tocable
            onPress={() => {
              setBorrador(String(valor));
              setEditando(true);
            }}
            colorContenido={color.onSurface}
            radio={shape.extraSmall}
            accessibilityRole="adjustable"
            accessibilityLabel={`Cantidad de ${nombreProducto}`}
            accessibilityValue={{ now: valor, min: minimo, max: maximo, text: textoValor }}
            accessibilityHint="Desliza arriba o abajo para cambiar. Toca dos veces para escribir la cantidad."
            accessibilityActions={[{ name: 'increment' }, { name: 'decrement' }]}
            onAccessibilityAction={(e) => {
              if (e.nativeEvent.actionName === 'increment') sumar();
              if (e.nativeEvent.actionName === 'decrement' && !enMinimo) onCambiar(valor - 1);
            }}
            style={estilos.valorCaja}
          >
            <Text style={estilos.valor}>
              {valor} {unidad}
            </Text>
          </Tocable>
        )}

        <Tocable
          onPress={sumar}
          disabled={enMaximo}
          colorContenido={colorMas}
          radio={shape.full}
          sinCapa={enMaximo}
          accessibilityRole="button"
          accessibilityLabel={`Agregar una ${singular} de ${nombreProducto}`}
          accessibilityState={{ disabled: enMaximo }}
          accessibilityHint={enMaximo ? `Solo hay ${maximo} en existencia` : undefined}
          style={[estilos.boton, enMaximo ? estilos.botonDeshabilitado : estilos.botonTonal]}
        >
          <MaterialCommunityIcons
            name="plus"
            size={iconos.linea}
            color={colorMas}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        </Tocable>
      </View>
      {enMaximo ? (
        <View style={estilos.aviso}>
          <MaterialCommunityIcons
            name="information"
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.textoAviso}>Solo hay {maximo} en existencia</Text>
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { gap: espacio.xs },
  grupo: { flexDirection: 'row', alignSelf: 'flex-start', alignItems: 'center', gap: espacio.s },
  boton: {
    width: tactil.minimo,
    height: tactil.minimo,
    borderRadius: shape.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  botonTonal: { backgroundColor: color.secondaryContainer },
  // icon button outlined error (modo "Quitar")
  botonQuitar: { borderWidth: bordes.fino, borderColor: color.error },
  // EXC-4
  botonDeshabilitado: { backgroundColor: color.surfaceContainerHighest },
  valorCaja: {
    minWidth: tactil.principal,
    minHeight: tactil.minimo,
    paddingHorizontal: espacio.s,
    alignItems: 'center',
    justifyContent: 'center',
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outline,
    borderTopLeftRadius: shape.extraSmall,
    borderTopRightRadius: shape.extraSmall,
  },
  valor: { ...type.amount, color: color.onSurface, textAlign: 'center' },
  valorEditando: { borderBottomWidth: bordes.grueso, borderBottomColor: color.primary },
  aviso: { flexDirection: 'row', gap: espacio.xs, alignItems: 'center' },
  textoAviso: { ...type.bodyLarge, color: color.onSurfaceVariant, flexShrink: 1 },
});
