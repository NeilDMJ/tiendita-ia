import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import type { MetodoPago } from '@/api/esquemas';
import { simularPagoDigital } from '@/api/pagos';
import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { Campo } from '@/components/campo';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { HojaInferior } from '@/components/hoja-inferior';
import type { NombreIcono } from '@/constants';
import { anilloFoco, bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';
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

type EstadoPago = 'inactivo' | 'esperando' | 'recibido' | 'no_recibido';

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
  const [enfocado, setEnfocado] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onFocus={() => setEnfocado(true)}
      onBlur={() => setEnfocado(false)}
      accessibilityRole="radio"
      accessibilityState={{ checked: elegida }}
      accessibilityLabel={`${texto}${simulacion ? ', simulación' : ''}`}
      style={({ pressed }) => [
        estilos.opcion,
        elegida && estilos.opcionElegida,
        pressed && estilos.presionado,
        enfocado && anilloFoco,
      ]}
    >
      <MaterialCommunityIcons
        name={elegida ? 'radiobox-marked' : 'radiobox-blank'}
        size={iconos.linea}
        color={elegida ? colores.acento : colores.texto}
      />
      <MaterialCommunityIcons name={icono} size={iconos.linea} color={colores.texto} />
      <View style={estilos.textoOpcion}>
        <Text style={estilos.etiqueta}>{texto}</Text>
        {simulacion ? <EtiquetaSimulacion /> : null}
      </View>
      {elegida ? <Text style={estilos.elegido}>Elegido</Text> : null}
    </Pressable>
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
  const digital = metodo === 'digital_simulado';
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
      onRegistrar('digital_simulado', null);
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
              pago === 'recibido' ? `Registrar venta ${formatoMoneda(total)}` : `Cobrar ${formatoMoneda(total)} con pago digital`
            }
            tamano="principal"
            icono="cellphone"
            cargando={esperandoPago || cargando}
            textoCargando={pago === 'esperando' ? 'Esperando el pago…' : 'Guardando venta…'}
            accessibilityHint="Simulación: no se mueve dinero real"
            onPress={pago === 'recibido' ? () => onRegistrar('digital_simulado', null) : cobrarDigital}
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
        <OpcionPago elegida={metodo === 'efectivo'} icono="cash" texto="Efectivo" onPress={() => elegirMetodo('efectivo')} />
        <OpcionPago
          elegida={metodo === 'digital_simulado'}
          icono="cellphone"
          texto="Pago digital"
          simulacion
          onPress={() => elegirMetodo('digital_simulado')}
        />
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
          <View style={estilos.atajos}>
            {ATAJOS.map((m) => (
              <Boton
                key={m}
                texto={formatoMoneda(m).replace('.00', '')}
                variante="secundario"
                anchoCompleto={false}
                accessibilityHint={`Te dan ${m} pesos`}
                onPress={() => setRecibido(m.toFixed(2))}
              />
            ))}
            <Boton
              texto="Exacto"
              variante="secundario"
              anchoCompleto={false}
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
              <ActivityIndicator color={colores.texto} />
              <Text style={estilos.cuerpo}>Esperando el pago del cliente…</Text>
            </View>
          ) : pago === 'recibido' ? (
            <View style={estilos.estadoPago} accessibilityLiveRegion="polite">
              <MaterialCommunityIcons name="check-circle" size={iconos.linea} color={colores.exito} />
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
  etiqueta: { ...tipografia.etiqueta, color: colores.texto },
  cuerpo: { ...tipografia.cuerpoGrande, color: colores.texto },
  opcion: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.m,
    paddingVertical: espacio.s,
    borderWidth: bordes.fino,
    borderColor: colores.borde,
    borderRadius: radios.medio,
  },
  opcionElegida: { borderWidth: bordes.grueso, borderColor: colores.acento },
  presionado: { backgroundColor: colores.superficie },
  textoOpcion: { flex: 1, gap: espacio.xs },
  elegido: { ...tipografia.etiqueta, color: colores.acento },
  atajos: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion },
  estadoPago: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoExito: { color: colores.exito },
  cambio: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'] },
});
