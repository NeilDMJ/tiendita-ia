import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn, useReducedMotion } from 'react-native-reanimated';

import type { RolAsistente } from '@/api/esquemas';
import { Boton } from '@/components/boton';
import { datosRol } from '@/constants';
import { motivoFallo, type MensajeChat } from '@/estado/chat';
import { color, espacio, iconos, motion, shape, tactil, type } from '@/theme';
import { hora } from '@/utils/fecha';
import { limpiarFormato } from '@/utils/texto-chat';

const ENTRADA = FadeIn.duration(motion.duration.short4);

/** Icono + nombre del oficio sobre la burbuja (rol = icono + nombre, nunca color). */
export function CabeceraRol({ rol }: { rol: RolAsistente }) {
  const r = datosRol(rol);
  return (
    <View style={estilos.cabecera} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <MaterialCommunityIcons name={r.icono} size={iconos.linea} color={color.onSurfaceVariant} />
      <Text style={estilos.nombreRol}>{r.nombre}</Text>
    </View>
  );
}

export interface BurbujaMensajeProps {
  mensaje: MensajeChat;
  /** Primer mensaje de un bloque del mismo autor/rol. */
  cabecera: boolean;
  letraGrande: boolean;
  onReintentar?: () => void;
  onBorrar?: () => void;
  onCancelarEspera?: () => void;
}

/**
 * Burbuja de chat armada con tokens M3 (02-asistente §2.2): tendero a la derecha en `primaryContainer`,
 * asistente a la izquierda en `surfaceContainerHigh`; esquina del autor recortada (`extraSmall`).
 * Un solo elemento accesible por burbuja: "Tú: …. 10:42" / "Cuentas: …. 10:42".
 */
export function BurbujaMensaje({
  mensaje,
  cabecera,
  letraGrande,
  onReintentar,
  onBorrar,
  onCancelarEspera,
}: BurbujaMensajeProps) {
  const reducido = useReducedMotion();
  const esTendero = mensaje.autor === 'tendero';
  const texto = esTendero ? mensaje.texto : limpiarFormato(mensaje.texto);
  const quien = esTendero ? 'Tú' : datosRol(mensaje.rol).nombre;
  const estadoTendero = esTendero ? mensaje.estado : null;
  const fallo = esTendero && mensaje.estado === 'fallido' ? motivoFallo(mensaje.error) : null;
  const etiquetaEstado =
    estadoTendero === 'en_espera' ? ' Se enviará al volver el internet.' : fallo ? ` ${fallo}` : '';

  return (
    <Animated.View
      entering={reducido ? undefined : ENTRADA}
      style={[estilos.bloque, esTendero ? estilos.derecha : estilos.izquierda, letraGrande && estilos.anchoCompleto]}
    >
      {!esTendero && cabecera ? <CabeceraRol rol={mensaje.rol} /> : null}
      {esTendero && cabecera && letraGrande ? <Text style={estilos.tu}>Tú</Text> : null}
      <View
        accessible
        accessibilityLabel={`${quien}: ${texto}. ${hora(mensaje.creado_en)}.${etiquetaEstado}`}
        style={[estilos.burbuja, esTendero ? estilos.burbujaTendero : estilos.burbujaAsistente]}
      >
        <Text style={[estilos.texto, esTendero ? estilos.textoTendero : estilos.textoAsistente]}>{texto}</Text>
      </View>
      <Text
        style={[estilos.hora, esTendero && estilos.horaDerecha]}
        accessibilityElementsHidden
        importantForAccessibility="no"
      >
        {hora(mensaje.creado_en)}
      </Text>

      {estadoTendero === 'en_espera' ? (
        <View style={estilos.estado}>
          <View style={estilos.filaEstado}>
            <MaterialCommunityIcons
              name="clock-outline"
              size={iconos.chico}
              color={color.onSurfaceVariant}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.textoEspera}>Se enviará al volver el internet</Text>
          </View>
          {onCancelarEspera ? (
            <Boton texto="Cancelar envío" variante="text" anchoCompleto={false} onPress={onCancelarEspera} style={estilos.botonDerecha} />
          ) : null}
        </View>
      ) : null}

      {fallo ? (
        <View style={estilos.estado}>
          <View style={estilos.filaEstado}>
            <MaterialCommunityIcons
              name="alert-circle"
              size={iconos.chico}
              color={color.error}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.textoFallo}>{fallo}</Text>
          </View>
          <View style={estilos.accionesFallo}>
            {onBorrar ? <Boton texto="Borrar" variante="text" anchoCompleto={false} onPress={onBorrar} /> : null}
            {onReintentar ? (
              <Boton texto="Reintentar" icono="refresh" variante="text" anchoCompleto={false} onPress={onReintentar} />
            ) : null}
          </View>
        </View>
      ) : null}
    </Animated.View>
  );
}

const estilos = StyleSheet.create({
  bloque: { maxWidth: '85%', gap: espacio.xs },
  derecha: { alignSelf: 'flex-end', alignItems: 'flex-end', marginLeft: tactil.minimo },
  izquierda: { alignSelf: 'flex-start', alignItems: 'flex-start', marginRight: tactil.minimo },
  anchoCompleto: { maxWidth: '100%', marginLeft: 0, marginRight: 0, alignSelf: 'stretch' },
  cabecera: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  nombreRol: { ...type.titleSmall, color: color.onSurface },
  tu: { ...type.titleSmall, color: color.onSurfaceVariant },
  burbuja: { paddingHorizontal: espacio.l, paddingVertical: espacio.m, borderRadius: shape.large },
  burbujaTendero: { backgroundColor: color.primaryContainer, borderBottomRightRadius: shape.extraSmall },
  burbujaAsistente: { backgroundColor: color.surfaceContainerHigh, borderTopLeftRadius: shape.extraSmall },
  texto: { ...type.bodyLargePlus },
  textoTendero: { color: color.onPrimaryContainer },
  textoAsistente: { color: color.onSurface },
  hora: { ...type.labelLarge, color: color.onSurfaceVariant },
  horaDerecha: { textAlign: 'right' },
  estado: { alignItems: 'flex-end', gap: espacio.xs },
  filaEstado: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs, flexWrap: 'wrap', justifyContent: 'flex-end' },
  textoEspera: { ...type.bodyLarge, color: color.onSurfaceVariant, flexShrink: 1 },
  textoFallo: { ...type.labelLarge, color: color.error, flexShrink: 1 },
  accionesFallo: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end', gap: tactil.separacion },
  botonDerecha: { alignSelf: 'flex-end' },
});
