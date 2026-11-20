import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRef, useState, type ComponentRef } from 'react';
import { AccessibilityInfo, findNodeHandle, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { parsearDatosAccion } from '@/api/acciones-asistente';
import type { DatosModificarItem } from '@/api/esquemas';
import { Aviso } from '@/components/aviso';
import { ChipSugerencia } from '@/components/chip-sugerencia';
import { HojaInferior } from '@/components/hoja-inferior';
import { SUGERENCIAS_CAJA } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { CLAVE_CHAT_CAJA, type AccionChat, type MensajeDelAsistente } from '@/estado/chat';
import { useAccionesAsistente } from '@/hooks/use-acciones-asistente';
import { useChat } from '@/hooks/use-chat';
import { useConexion } from '@/hooks/use-conexion';
import { useLetraGrande } from '@/hooks/use-letra-grande';
import { bordes, color, espacio, iconos, tactil, type } from '@/theme';
import { calcularTotal, plural } from '@/utils/carrito';
import { aContextoCobro, type ResultadoValidacion } from '@/utils/contexto-cobro';
import { formatoMoneda } from '@/utils/formato-moneda';

import { Compositor } from '../asistente/compositor';
import { ListaMensajes } from '../asistente/lista-mensajes';
import { TarjetaPropuesta } from '../asistente/tarjeta-propuesta';

export interface HojaCajaProps {
  visible: boolean;
  onCerrar: () => void;
  /** Valida contra el carrito ACTUAL y, si procede, cambia la fila (con Deshacer en la revisión). */
  onAplicar: (datos: DatosModificarItem) => ResultadoValidacion;
  /** Cierra la hoja y abre "Editar producto" de esa fila. */
  onEditarFila: (clave: string) => void;
  /** "Caja no supo responder" → buscar a mano (primera fila con problema o "Agregar producto"). */
  onBuscarProducto: () => void;
}

const MAX_CHIPS_LETRA_GRANDE = 2;

/**
 * "Pregúntale a Caja" (02-asistente §4): bottom sheet modal al 90 % sobre la revisión, con la venta
 * como contexto. Conversación propia de esta venta (no se mezcla con la pestaña); sin cola sin conexión.
 */
export function HojaCaja({ visible, onCerrar, onAplicar, onEditarFila, onBuscarProducto }: HojaCajaProps) {
  const { carrito } = useCarrito();
  const conectado = useConexion();
  const letraGrande = useLetraGrande();
  const chat = useChat({
    clave: CLAVE_CHAT_CAJA,
    sesion: carrito.sesion ?? null,
    conCola: false,
    activo: visible,
    contexto: () => aContextoCobro(carrito),
  });
  const acciones = useAccionesAsistente(chat);
  const [texto, setTexto] = useState('');
  const refCampo = useRef<ComponentRef<typeof TextInput>>(null);

  const { total, sinPrecio } = calcularTotal(carrito.items);
  const resumenVenta = `Caja ve tu venta: ${plural(carrito.items.length, 'producto', 'productos')}, ${formatoMoneda(total)}${
    sinPrecio > 0 ? ` (${sinPrecio} sin precio)` : ''
  }`;

  function enviar(t: string) {
    const r = chat.enviar(t);
    if (r.tipo === 'ocupado') return;
    setTexto('');
    // El foco (teclado y lector) regresa al campo; no salta a la respuesta.
    refCampo.current?.focus();
    const nodo = refCampo.current ? findNodeHandle(refCampo.current) : null;
    if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
  }

  function aplicar(m: MensajeDelAsistente, a: AccionChat) {
    const p = parsearDatosAccion(a);
    if (p?.tipo !== 'modificar_item') return;
    const r = onAplicar(p.datos);
    if (r.ok) {
      chat.actualizarAccion(m.id, a.id, { estado: 'hecha', resultado: 'Aplicado a la venta' });
      const quedan = chat.mensajes.some(
        (x) => x.autor === 'asistente' && x.acciones?.some((y) => y.id !== a.id && y.estado === 'pendiente' && y.tipo === 'modificar_item'),
      );
      if (!quedan) onCerrar();
    } else if (r.tipo === 'cambio') {
      chat.actualizarAccion(m.id, a.id, { estado: 'caducada', motivo: r.mensaje });
    } else {
      chat.actualizarAccion(m.id, a.id, { estado: 'error', error: r.mensaje, claveFila: r.clave });
    }
  }

  function renderExtras(m: MensajeDelAsistente, ultimo: boolean) {
    // En la hoja solo tienen sentido modificar_item y abrir_pantalla (lo demás se ve como texto).
    const tarjetas = (m.acciones ?? []).filter((a) => a.tipo === 'modificar_item' || a.tipo === 'abrir_pantalla');
    return (
      <View style={estilos.extras}>
        {tarjetas.map((a) => {
          const p = parsearDatosAccion(a);
          const clave = p?.tipo === 'modificar_item' ? p.datos.clave : null;
          const fila = clave ? carrito.items.find((i) => i.clave === clave) : undefined;
          const claveEditar = a.claveFila ?? clave;
          return (
            <TarjetaPropuesta
              key={a.id}
              accion={a}
              rol={m.rol}
              conectado={conectado !== false}
              enHoja
              antes={fila ? { nombre: fila.nombre, precio: fila.precio_unitario } : null}
              onConfirmar={() => aplicar(m, a)}
              onRechazar={() => chat.actualizarAccion(m.id, a.id, { estado: 'rechazada' })}
              onEditar={claveEditar && (a.estado === 'error' || a.estado === 'pendiente') ? () => onEditarFila(claveEditar) : undefined}
              onHacerAMano={onBuscarProducto}
              onAbrir={(destino) => {
                onCerrar();
                acciones.abrir(destino);
              }}
            />
          );
        })}
        {m.no_resuelto ? (
          <Aviso
            tipo="info"
            titulo="Caja no supo responder."
            mensaje="Puedes buscar el producto a mano."
            accion={{ texto: 'Buscar producto', icono: 'magnify', onPress: onBuscarProducto }}
            accionSecundaria={ultimo ? { texto: 'Preguntar de otra forma', onPress: () => refCampo.current?.focus() } : undefined}
          />
        ) : null}
      </View>
    );
  }

  const vacio = chat.cargado && chat.mensajes.length === 0;
  // Un solo grupo de chips en el pie: las sugerencias de la última respuesta o, si no hay, las de Caja.
  const ultimo = chat.mensajes[chat.mensajes.length - 1];
  const delAsistente = ultimo?.autor === 'asistente' && ultimo.sugerencias?.length ? ultimo.sugerencias : null;
  const base = delAsistente ?? SUGERENCIAS_CAJA;
  const chips = letraGrande ? base.slice(0, MAX_CHIPS_LETRA_GRANDE) : base;

  return (
    <HojaInferior
      visible={visible}
      titulo="Pregúntale a Caja"
      icono="cash-register"
      onCerrar={onCerrar}
      altoMaximo={0.9}
      sinScroll
      pie={
        <>
          {chat.esperando ? null : letraGrande || vacio ? (
            <View style={estilos.chipsColumna}>
              {chips.map((s) => (
                <ChipSugerencia key={s} texto={s} anchoCompleto onPress={() => enviar(s)} />
              ))}
            </View>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={estilos.chipsHorizontal} keyboardShouldPersistTaps="handled">
              {chips.map((s) => (
                <ChipSugerencia key={s} texto={s} onPress={() => enviar(s)} />
              ))}
            </ScrollView>
          )}
          <Compositor
            refCampo={refCampo}
            variante="plano"
            placeholder="Pregúntale a Caja…"
            valor={texto}
            onCambiar={setTexto}
            onEnviar={enviar}
            onDetener={chat.detener}
            esperando={chat.esperando}
            letraGrande={letraGrande}
          />
        </>
      }
    >
      <View style={estilos.contexto}>
        <MaterialCommunityIcons
          name="eye-outline"
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.textoContexto}>{resumenVenta}</Text>
      </View>
      {conectado === false ? (
        <Aviso
          tipo="sinConexion"
          modo="franja"
          titulo="Sin conexión"
          mensaje="Caja necesita internet. Tu venta sigue aquí."
        />
      ) : null}
      {vacio ? (
        <View style={estilos.vacio}>
          <Text style={estilos.textoVacio}>Pregúntale lo que no sepas de esta venta.</Text>
        </View>
      ) : (
        <ListaMensajes
          mensajes={chat.mensajes}
          esperando={chat.esperando}
          letraGrande={letraGrande}
          onDetener={chat.detener}
          onReintentar={chat.reintentar}
          onBorrar={chat.borrarMensaje}
          onCancelarEspera={chat.borrarMensaje}
          renderExtras={renderExtras}
        />
      )}
    </HojaInferior>
  );
}

const estilos = StyleSheet.create({
  contexto: {
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outlineVariant,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
  },
  textoContexto: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
  vacio: { flex: 1, padding: espacio.l },
  textoVacio: { ...type.bodyLarge, color: color.onSurfaceVariant },
  extras: { gap: espacio.s },
  chipsHorizontal: { flexDirection: 'row', gap: tactil.separacion },
  chipsColumna: { gap: tactil.separacion },
});
