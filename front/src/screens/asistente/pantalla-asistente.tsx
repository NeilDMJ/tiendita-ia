import { useIsFocused } from 'expo-router';
import { useEffect, useRef, useState, type ComponentRef } from 'react';
import { AccessibilityInfo, ActivityIndicator, KeyboardAvoidingView, StyleSheet, Text, TextInput, View } from 'react-native';

import { parsearDatosAccion } from '@/api/acciones-asistente';
import { USAR_MOCKS } from '@/api/cliente';
import type { DatosConfirmarAlta } from '@/api/esquemas';
import { Aviso } from '@/components/aviso';
import { ChipSugerencia } from '@/components/chip-sugerencia';
import { Dialogo } from '@/components/dialogo';
import { Encabezado } from '@/components/encabezado';
import { EtiquetaSimulacion } from '@/components/etiqueta-simulacion';
import { Snackbar } from '@/components/snackbar';
import { CHAT } from '@/constants';
import { CLAVE_CHAT_PESTANA, type AccionChat, type MensajeChat, type MensajeDelAsistente, type MensajeTendero } from '@/estado/chat';
import { useAccionesAsistente } from '@/hooks/use-acciones-asistente';
import { useChat } from '@/hooks/use-chat';
import { useConexion } from '@/hooks/use-conexion';
import { useLetraGrande } from '@/hooks/use-letra-grande';
import { useTecladoVisible } from '@/hooks/use-teclado';
import { color, espacio, tactil, type } from '@/theme';

import { AlternativasNoResuelto } from './alternativas-no-resuelto';
import { Compositor } from './compositor';
import { EstadoVacioChat, SugerenciasIniciales } from './estado-vacio';
import { HojaEditarAlta } from './hoja-editar-alta';
import { ListaMensajes } from './lista-mensajes';
import { TarjetaPropuesta } from './tarjeta-propuesta';
import { nodoAccesible } from '@/utils/nodo-accesible';

type AvisoSnack =
  | { tipo: 'borrado'; copia: MensajeChat[] }
  | { tipo: 'reemplazo'; anterior: MensajeTendero; nuevoId: string; texto: string };

/** Pestaña Asistente: chat unificado con tarjetas de confirmación (02-asistente §2). */
export function PantallaAsistente() {
  const enfocada = useIsFocused();
  const chat = useChat({ clave: CLAVE_CHAT_PESTANA, conCola: true, activo: enfocada });
  const acciones = useAccionesAsistente(chat);
  const conectado = useConexion();
  const letraGrande = useLetraGrande();
  const teclado = useTecladoVisible();

  const [texto, setTexto] = useState('');
  const [confirmarBorrar, setConfirmarBorrar] = useState(false);
  const [snack, setSnack] = useState<AvisoSnack | null>(null);
  const [cargaLenta, setCargaLenta] = useState(false);
  const [offsetTeclado, setOffsetTeclado] = useState(0);
  const [desplazado, setDesplazado] = useState(false);
  const [editandoAlta, setEditandoAlta] = useState<{ idMensaje: string; accion: AccionChat; datos: DatosConfirmarAlta } | null>(
    null,
  );
  const refCampo = useRef<ComponentRef<typeof TextInput>>(null);
  const refRaiz = useRef<ComponentRef<typeof View>>(null);

  // "Cargando tu conversación…" solo si tarda más de 300 ms.
  useEffect(() => {
    if (chat.cargado) return;
    const t = setTimeout(() => setCargaLenta(true), CHAT.cargaVisibleMs);
    return () => clearTimeout(t);
  }, [chat.cargado]);

  const hayMensajes = chat.mensajes.length > 0;

  /** Tras enviar, el foco (teclado y lector) regresa al campo: no salta a la respuesta. */
  function enfocarCampo() {
    refCampo.current?.focus();
    const nodo = refCampo.current ? nodoAccesible(refCampo.current) : null;
    if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
  }

  function enviar(t: string) {
    const r = chat.enviar(t);
    if (r.tipo === 'ocupado') return;
    setTexto('');
    enfocarCampo();
    if (r.tipo === 'reemplazo') setSnack({ tipo: 'reemplazo', anterior: r.anterior, nuevoId: r.nuevoId, texto: t });
  }

  const enviarSugerencia = enviar;

  function editar(idMensaje: string, a: AccionChat) {
    if (a.tipo === 'confirmar_venta') acciones.revisar(idMensaje, a);
    if (a.tipo === 'confirmar_alta') {
      const p = parsearDatosAccion(a);
      if (p?.tipo === 'confirmar_alta') setEditandoAlta({ idMensaje, accion: a, datos: p.datos });
    }
  }

  function renderExtras(m: MensajeDelAsistente, ultimo: boolean) {
    const tarjetas = (m.acciones ?? []).filter((a) => !(m.no_resuelto && a.tipo === 'abrir_pantalla'));
    return (
      <View style={estilos.extras}>
        {tarjetas.map((a) => (
          <TarjetaPropuesta
            key={a.id}
            accion={a}
            rol={m.rol}
            conectado={acciones.conectado}
            onConfirmar={() => acciones.confirmar(m.id, a)}
            onRechazar={() => acciones.rechazar(m.id, a)}
            onEditar={
              a.tipo === 'confirmar_venta' || a.tipo === 'confirmar_alta' ? () => editar(m.id, a) : undefined
            }
            onHacerAMano={() => acciones.hacerAMano(a)}
            onAbrir={acciones.abrir}
            onVerResultado={a.idVenta ? () => acciones.verComprobante(a.idVenta as string) : undefined}
          />
        ))}
        {m.no_resuelto ? <AlternativasNoResuelto acciones={m.acciones} onAbrir={acciones.abrir} /> : null}
        {ultimo ? (
          <View style={estilos.sugerencias}>
            {(m.sugerencias ?? []).map((s) => (
              <ChipSugerencia key={s} texto={s} anchoCompleto={letraGrande} onPress={() => enviarSugerencia(s)} />
            ))}
            {m.no_resuelto ? (
              <ChipSugerencia
                texto="Preguntar de otra forma"
                icono="pencil"
                anchoCompleto={letraGrande}
                onPress={() => refCampo.current?.focus()}
              />
            ) : null}
          </View>
        ) : null}
      </View>
    );
  }

  return (
    <View
      ref={refRaiz}
      style={estilos.pantalla}
      onLayout={() =>
        // KeyboardAvoidingView mide su marco relativo al padre: el offset es su Y real en la ventana.
        refRaiz.current?.measureInWindow((_x, y) => setOffsetTeclado(y))
      }
    >
      {/* Android edge-to-edge (SDK 58): la ventana no se redimensiona → `padding` en ambas plataformas. */}
      <KeyboardAvoidingView behavior="padding" keyboardVerticalOffset={offsetTeclado} style={estilos.pantalla}>
        <Encabezado
          titulo="Asistente"
          desplazado={hayMensajes && desplazado}
          accionDerecha={
            hayMensajes
              ? { texto: 'Borrar chat', icono: 'broom', onPress: () => setConfirmarBorrar(true) }
              : undefined
          }
        />
        {USAR_MOCKS ? <EtiquetaSimulacion modo="franja" detalle="respuestas de ejemplo" /> : null}
        {chat.errorCarga ? (
          <Aviso
            style={estilos.margen}
            tipo="info"
            titulo="No pudimos abrir la conversación anterior."
            mensaje="Puedes empezar una nueva."
          />
        ) : null}

        {!chat.cargado ? (
          cargaLenta ? (
            <View style={estilos.cargando} accessibilityLiveRegion="polite">
              <ActivityIndicator color={color.primary} />
              <Text style={estilos.textoCargando}>Cargando tu conversación…</Text>
            </View>
          ) : (
            <View style={estilos.pantalla} />
          )
        ) : hayMensajes ? (
          <ListaMensajes
            mensajes={chat.mensajes}
            esperando={chat.esperando}
            letraGrande={letraGrande}
            onDetener={chat.detener}
            onReintentar={chat.reintentar}
            onBorrar={chat.borrarMensaje}
            onCancelarEspera={chat.borrarMensaje}
            renderExtras={renderExtras}
            onDesplazado={setDesplazado}
          />
        ) : (
          <>
            <View style={estilos.pantalla}>
              <EstadoVacioChat />
            </View>
            {teclado ? null : <SugerenciasIniciales onEnviar={enviarSugerencia} />}
          </>
        )}

        <Compositor
          refCampo={refCampo}
          valor={texto}
          onCambiar={setTexto}
          onEnviar={enviar}
          onDetener={chat.detener}
          esperando={chat.esperando}
          letraGrande={letraGrande}
          ayuda={conectado === false ? { texto: 'Sin internet: se enviará al volver', icono: 'wifi-off' } : null}
        />
      </KeyboardAvoidingView>

      <Snackbar
        visible={snack !== null}
        mensaje={snack?.tipo === 'borrado' ? 'Borraste la conversación.' : 'Cambiamos tu pregunta en espera.'}
        icono="undo"
        anuncio={
          snack?.tipo === 'borrado'
            ? 'Borraste la conversación. Botón Deshacer disponible.'
            : snack
              ? 'Cambiamos tu pregunta en espera. Botón Deshacer disponible.'
              : undefined
        }
        accion={{
          texto: 'Deshacer',
          onPress: () => {
            if (snack?.tipo === 'borrado') chat.restaurar(snack.copia);
            if (snack?.tipo === 'reemplazo') {
              chat.deshacerReemplazo(snack.anterior, snack.nuevoId);
              setTexto(snack.texto);
            }
            setSnack(null);
          },
        }}
        onCerrar={() => setSnack(null)}
        separacionInferior={tactil.principal + espacio.xl}
      />

      <Dialogo
        visible={confirmarBorrar}
        icono="broom"
        titulo="¿Borrar la conversación?"
        mensaje="Se borran los mensajes de este teléfono. Tus ventas y tu inventario no cambian."
        acciones={[
          { texto: 'No, regresar', variante: 'tonal', onPress: () => setConfirmarBorrar(false) },
          {
            texto: 'Sí, borrar',
            icono: 'trash-can-outline',
            variante: 'filledError',
            onPress: () => {
              const copia = chat.borrarTodo();
              setConfirmarBorrar(false);
              setSnack({ tipo: 'borrado', copia });
            },
          },
        ]}
      />

      {editandoAlta ? (
        <HojaEditarAlta
          key={editandoAlta.accion.id}
          visible
          datos={editandoAlta.datos}
          conectado={acciones.conectado}
          onCerrar={() => setEditandoAlta(null)}
          onConfirmar={(datos) => {
            const e = editandoAlta;
            setEditandoAlta(null);
            acciones.confirmar(e.idMensaje, e.accion, datos);
          }}
        />
      ) : null}

      <Dialogo
        visible={acciones.dialogoBorrador.visible}
        icono="cart-outline"
        titulo="Ya tienes una venta sin terminar"
        mensaje="Si la reemplazas, se quitan los productos que tenías en la revisión."
        onCerrar={acciones.dialogoBorrador.mantener}
        acciones={[
          { texto: 'Mantener la mía', variante: 'tonal', onPress: acciones.dialogoBorrador.mantener },
          { texto: 'Reemplazarla', variante: 'filled', onPress: acciones.dialogoBorrador.reemplazar },
        ]}
      />
    </View>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: color.surface },
  margen: { marginHorizontal: espacio.l, marginTop: espacio.s },
  cargando: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.m },
  textoCargando: { ...type.bodyLarge, color: color.onSurfaceVariant },
  extras: { gap: espacio.s },
  sugerencias: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion },
});
