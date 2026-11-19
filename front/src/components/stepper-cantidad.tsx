import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View, type StyleProp, type ViewStyle } from 'react-native';

import { anilloFoco, bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';

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

/** Cantidad con − / +. Tocar el número permite escribirlo (cantidades grandes sin 12 toques). */
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
  const [foco, setFoco] = useState<'menos' | 'valor' | 'mas' | null>(null);
  const enfocar = (zona: 'menos' | 'valor' | 'mas') => ({
    onFocus: () => setFoco(zona),
    onBlur: () => setFoco((f) => (f === zona ? null : f)),
  });
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

  return (
    <View style={[estilos.contenedor, style]} testID={testID}>
      <View style={estilos.grupo}>
        <Pressable
          onPress={restar}
          disabled={enMinimo && !modoQuitar}
          accessibilityRole="button"
          accessibilityLabel={
            modoQuitar ? `Quitar ${nombreProducto} de la venta` : `Quitar una ${singular} de ${nombreProducto}`
          }
          accessibilityState={{ disabled: enMinimo && !modoQuitar }}
          {...enfocar('menos')}
          style={({ pressed }) => [
            estilos.boton,
            estilos.botonIzquierdo,
            enMinimo && !modoQuitar && estilos.botonDeshabilitado,
            pressed && estilos.presionado,
            foco === 'menos' && anilloFoco,
          ]}
        >
          <MaterialCommunityIcons
            name={modoQuitar ? 'trash-can-outline' : 'minus'}
            size={iconos.linea}
            color={modoQuitar ? colores.peligro : enMinimo ? colores.deshabilitadoTexto : colores.texto}
          />
        </Pressable>

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
            style={[estilos.valor, estilos.valorEditando]}
          />
        ) : (
          <Pressable
            onPress={() => {
              setBorrador(String(valor));
              setEditando(true);
            }}
            accessibilityRole="adjustable"
            accessibilityLabel={`Cantidad de ${nombreProducto}`}
            accessibilityValue={{ now: valor, min: minimo, max: maximo, text: textoValor }}
            accessibilityHint="Desliza arriba o abajo para cambiar. Toca dos veces para escribir la cantidad."
            accessibilityActions={[{ name: 'increment' }, { name: 'decrement' }]}
            onAccessibilityAction={(e) => {
              if (e.nativeEvent.actionName === 'increment') sumar();
              if (e.nativeEvent.actionName === 'decrement' && !enMinimo) onCambiar(valor - 1);
            }}
            {...enfocar('valor')}
            style={({ pressed }) => [estilos.valorCaja, pressed && estilos.presionado, foco === 'valor' && anilloFoco]}
          >
            <Text style={estilos.valor}>
              {valor} {unidad}
            </Text>
          </Pressable>
        )}

        <Pressable
          onPress={sumar}
          disabled={enMaximo}
          accessibilityRole="button"
          accessibilityLabel={`Agregar una ${singular} de ${nombreProducto}`}
          accessibilityState={{ disabled: enMaximo }}
          accessibilityHint={enMaximo ? `Solo hay ${maximo} en existencia` : undefined}
          {...enfocar('mas')}
          style={({ pressed }) => [
            estilos.boton,
            estilos.botonDerecho,
            enMaximo && estilos.botonDeshabilitado,
            pressed && estilos.presionado,
            foco === 'mas' && anilloFoco,
          ]}
        >
          <MaterialCommunityIcons
            name="plus"
            size={iconos.linea}
            color={enMaximo ? colores.deshabilitadoTexto : colores.texto}
          />
        </Pressable>
      </View>
      {enMaximo ? (
        <View style={estilos.aviso}>
          <MaterialCommunityIcons
            name="information"
            size={iconos.linea}
            color={colores.textoSecundario}
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
  grupo: {
    flexDirection: 'row',
    alignSelf: 'flex-start',
    borderWidth: bordes.fino,
    borderColor: colores.borde,
    borderRadius: radios.medio,
  },
  boton: {
    width: tactil.minimo,
    minHeight: tactil.minimo,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colores.fondo,
  },
  // radios internos = radio exterior − borde, para no tapar las esquinas redondeadas
  botonIzquierdo: { borderTopLeftRadius: radios.medio - bordes.fino, borderBottomLeftRadius: radios.medio - bordes.fino },
  botonDerecho: { borderTopRightRadius: radios.medio - bordes.fino, borderBottomRightRadius: radios.medio - bordes.fino },
  botonDeshabilitado: { backgroundColor: colores.deshabilitadoFondo },
  presionado: { backgroundColor: colores.superficie },
  valorCaja: {
    minWidth: tactil.principal,
    minHeight: tactil.minimo,
    paddingHorizontal: espacio.s,
    alignItems: 'center',
    justifyContent: 'center',
    borderLeftWidth: bordes.fino,
    borderRightWidth: bordes.fino,
    borderColor: colores.borde,
    backgroundColor: colores.fondo,
  },
  valor: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'], textAlign: 'center' },
  valorEditando: {
    minWidth: tactil.principal,
    minHeight: tactil.minimo,
    borderLeftWidth: bordes.fino,
    borderRightWidth: bordes.fino,
    borderColor: colores.borde,
    paddingHorizontal: espacio.s,
  },
  aviso: { flexDirection: 'row', gap: espacio.xs, alignItems: 'center' },
  textoAviso: { ...tipografia.cuerpo, color: colores.textoSecundario, flexShrink: 1 },
});
