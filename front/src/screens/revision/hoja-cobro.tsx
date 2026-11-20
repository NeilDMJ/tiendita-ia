import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { esPagoDigital, MetodoPago } from '@/api/esquemas';
import { simularPagoDigital } from '@/api/pagos';
import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { Campo } from '@/components/campo';
import { ChipFiltro } from '@/components/chip-filtro';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { HojaInferior } from '@/components/hoja-inferior';
import { Tocable } from '@/components/tocable';
import { METODOS_PAGO, type NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, pesoActivo, shape, tactil, type } from '@/theme';
import { formatoMoneda, leerMonto } from '@/utils/formato-moneda';

export type ErrorCobro = 'datos_faltantes' | 'servidor';

export interface HojaCobroProps {
  visible: boolean;
  total: number;
  cargando: boolean;
  error: ErrorCobro | null;
  onCerrar: () => void;
  onRegistrar: (metodo: MetodoPago, recibido: number | null) => void;
  onGuardarDespues: (metodo: MetodoPago, recibido: number | null) => void;
  onIrAlProducto: () => void;
}

const ATAJOS = [100, 200, 500];

/** Orden de las opciones: efectivo primero (el más común en la tiendita). */
const MetodoPagoLista = MetodoPago.options;

type EstadoPago = 'inactivo' | 'esperando' | 'recibido' | 'no_recibido';

/** List item M3 con radio. Elegido = `primaryContainer` + radio relleno + "Elegido" (no solo color). */
function OpcionPago({
  elegida,
  icono,
  texto,
  simulacion,
  onPress,
}: {
  elegida: boolean;
  icono: NombreIcono;
  texto: string;
  simulacion?: boolean;
  onPress: () => void;
}) {
  const contenido = elegida ? color.onPrimaryContainer : color.onSurface;
  return (
    <Tocable
      onPress={onPress}
      colorContenido={contenido}
      radio={shape.medium}
      accessibilityRole="radio"
      accessibilityState={{ checked: elegida }}
      accessibilityLabel={`${texto}${simulacion ? ', simulación' : ''}`}
      style={[estilos.opcion, elegida && estilos.opcionElegida]}
    >
      <MaterialCommunityIcons
        name={elegida ? 'radiobox-marked' : 'radiobox-blank'}
        size={iconos.linea}
        color={elegida ? color.primary : color.outline}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <MaterialCommunityIcons
        name={icono}
        size={iconos.linea}
        color={contenido}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <View style={estilos.textoOpcion}>
        <Text style={[estilos.etiqueta, { color: contenido }]}>{texto}</Text>
        {simulacion ? <EtiquetaSimulacion /> : null}
      </View>
      {elegida ? <Text style={estilos.elegido}>Elegido</Text> : null}
    </Tocable>
  );
}

/** Hoja "Cobrar $X": método de pago, efectivo recibido y cambio. */
export function HojaCobro({
  visible,
  total,
  cargando,
  error,
  onCerrar,
  onRegistrar,
  onGuardarDespues,
  onIrAlProducto,
}: HojaCobroProps) {
  const [metodo, setMetodo] = useState<MetodoPago>('efectivo');
  const [recibido, setRecibido] = useState('');
  const [tocado, setTocado] = useState(false);
  const [pago, setPago] = useState<EstadoPago>('inactivo');

  const recibidoNumero = metodo === 'efectivo' ? leerMonto(recibido) : null;
  const vacio = recibido.trim() === '';
  const faltan = recibidoNumero !== null && recibidoNumero < total ? total - recibidoNumero : 0;
  const errorRecibido =
    metodo !== 'efectivo' || vacio
      ? null
      : recibidoNumero === null
        ? 'Escribe solo números. Ej. 100'
        : faltan > 0
          ? `Faltan ${formatoMoneda(faltan)}`
          : null;
  const cambio = recibidoNumero !== null && faltan === 0 ? recibidoNumero - total : null;
  const bloqueado = errorRecibido !== null;
  const digital = esPagoDigital(metodo);
  // si el pago ya llegó pero falló el registro, reintentar solo registra (no se cobra dos veces)
  const esperandoPago = pago === 'esperando' || (pago === 'recibido' && error === null);

  function elegirMetodo(m: MetodoPago) {
    setMetodo(m);
    setPago('inactivo');
  }

  /** SIMULACIÓN: espera el pago digital; solo si "llega" se registra la venta. */
  async function cobrarDigital() {
    setPago('esperando');
    AccessibilityInfo.announceForAccessibility('Esperando el pago del cliente. Simulación.');
    const resultado = await simularPagoDigital(total);
    if (resultado === 'recibido') {
      setPago('recibido');
      AccessibilityInfo.announceForAccessibility('Pago recibido. Simulación. Guardando venta.');
      onRegistrar(metodo, null);
    } else {
      setPago('no_recibido');
    }
  }

  return (
    <HojaInferior
      visible={visible}
      titulo={`Cobrar ${formatoMoneda(total)}`}
      onCerrar={cargando || esperandoPago ? () => undefined : onCerrar}
      pie={
        digital ? (
          <Boton
            texto={
              pago === 'recibido' ? `Registrar venta ${formatoMoneda(total)}` : `Cobrar ${formatoMoneda(total)} con ${METODOS_PAGO[metodo].nombre.toLowerCase().replace('qr', 'QR')}`
            }
            tamano="principal"
            icono="cellphone"
            cargando={esperandoPago || cargando}
            textoCargando={pago === 'esperando' ? 'Esperando el pago…' : 'Guardando venta…'}
            accessibilityHint="Simulación: no se mueve dinero real"
            onPress={pago === 'recibido' ? () => onRegistrar(metodo, null) : cobrarDigital}
          />
        ) : (
          <Boton
            texto={`Registrar venta ${formatoMoneda(total)}`}
            tamano="principal"
            icono="check"
            cargando={cargando}
            textoCargando="Guardando venta…"
            deshabilitado={bloqueado}
            motivoDeshabilitado={errorRecibido ?? undefined}
            accessibilityHint="Registra la venta y descuenta del inventario"
            onPress={() => onRegistrar(metodo, recibidoNumero)}
          />
        )
      }
    >
      {error === 'servidor' ? (
        <Aviso
          tipo="error"
          titulo="No se pudo registrar la venta."
          mensaje="Tu venta sigue aquí, no se cobró dos veces."
          accion={{ texto: 'Reintentar', icono: 'refresh', onPress: () => onRegistrar(metodo, recibidoNumero) }}
          accionSecundaria={{ texto: 'Guardar y enviar después', onPress: () => onGuardarDespues(metodo, recibidoNumero) }}
          enfocar
        />
      ) : error === 'datos_faltantes' ? (
        <Aviso
          tipo="error"
          titulo="Falta un dato de un producto."
          mensaje="Revísalo antes de cobrar."
          accion={{ texto: 'Ir al producto', onPress: onIrAlProducto }}
          enfocar
        />
      ) : null}

      <View style={estilos.grupo} accessibilityRole="radiogroup" accessibilityLabel="¿Cómo te pagan?">
        <Text style={estilos.etiqueta}>¿Cómo te pagan?</Text>
        {MetodoPagoLista.map((m) => (
          <OpcionPago
            key={m}
            elegida={metodo === m}
            icono={METODOS_PAGO[m].icono}
            texto={METODOS_PAGO[m].nombre}
            simulacion={esPagoDigital(m)}
            onPress={() => elegirMetodo(m)}
          />
        ))}
      </View>

      {metodo === 'efectivo' ? (
        <View style={estilos.grupo}>
          <Campo
            etiqueta="Te dan (opcional)"
            valor={recibido}
            onCambiar={setRecibido}
            tipo="moneda"
            prefijo="$"
            placeholder="0.00"
            error={tocado || !vacio ? errorRecibido : null}
            onBlur={() => setTocado(true)}
          />
          <View style={estilos.atajos} accessibilityRole="radiogroup" accessibilityLabel="¿Con cuánto te pagan?">
            {ATAJOS.map((m) => (
              <ChipFiltro
                key={m}
                rol="radio"
                texto={formatoMoneda(m).replace('.00', '')}
                seleccionado={recibido === m.toFixed(2)}
                accessibilityHint={`Te dan ${m} pesos`}
                onPress={() => setRecibido(m.toFixed(2))}
              />
            ))}
            <ChipFiltro
              rol="radio"
              texto="Exacto"
              seleccionado={!ATAJOS.some((m) => recibido === m.toFixed(2)) && recibido === total.toFixed(2)}
              onPress={() => setRecibido(total.toFixed(2))}
            />
          </View>
          {cambio !== null ? (
            <Text style={estilos.cambio} accessibilityLiveRegion="polite">
              Cambio: {formatoMoneda(cambio)}
            </Text>
          ) : null}
        </View>
      ) : (
        <View style={estilos.grupo}>
          <EtiquetaSimulacion modo="franja" detalle="este cobro no mueve dinero real" />
          {pago === 'inactivo' ? (
            <Text style={estilos.cuerpo}>
              Pide al cliente que haga el pago desde su celular. La venta se registra cuando el pago llegue.
            </Text>
          ) : pago === 'esperando' ? (
            <View style={estilos.estadoPago} accessibilityLiveRegion="polite">
              <ActivityIndicator color={color.primary} />
              <Text style={estilos.cuerpo}>Esperando el pago del cliente…</Text>
            </View>
          ) : pago === 'recibido' ? (
            <View style={estilos.estadoPago} accessibilityLiveRegion="polite">
              <MaterialCommunityIcons
                name="check-circle"
                size={iconos.linea}
                color={color.success}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={[estilos.cuerpo, estilos.textoExito]}>Pago recibido. Guardando venta…</Text>
            </View>
          ) : (
            <Aviso
              tipo="error"
              titulo="Pago no recibido"
              mensaje="No se cobró nada. Pide al cliente que lo intente otra vez o cobra en efectivo."
              accion={{ texto: 'Reintentar', icono: 'refresh', onPress: cobrarDigital }}
              accionSecundaria={{ texto: 'Cobrar en efectivo', icono: 'cash', onPress: () => elegirMetodo('efectivo') }}
              enfocar
            />
          )}
        </View>
      )}
    </HojaInferior>
  );
}

const estilos = StyleSheet.create({
  grupo: { gap: espacio.s },
  etiqueta: { ...type.titleSmall, color: color.onSurface },
  cuerpo: { ...type.bodyLargePlus, color: color.onSurface },
  opcion: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    borderRadius: shape.medium,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
  },
  opcionElegida: { backgroundColor: color.primaryContainer, borderColor: color.primaryContainer },
  textoOpcion: { flex: 1, gap: espacio.xs },
  elegido: { ...type.labelLarge, color: color.onPrimaryContainer, ...pesoActivo },
  atajos: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion },
  estadoPago: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoExito: { color: color.onSurface },
  cambio: { ...type.amount, color: color.onSurface },
});
