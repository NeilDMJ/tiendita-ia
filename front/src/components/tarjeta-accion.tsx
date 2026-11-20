import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { RolAsistente } from '@/api/esquemas';
import { datosRol } from '@/constants';
import { bordes, color, elevacion, espacio, iconos, pesoActivo, shape, tactil, type } from '@/theme';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import { Aviso } from './aviso';
import { Boton } from './boton';
import { EtiquetaSimulacion } from './etiqueta-simulacion';

export type EstadoTarjeta = 'pendiente' | 'confirmando' | 'hecha' | 'rechazada' | 'error' | 'caducada';

export interface TarjetaAccionProps {
  rol: RolAsistente;
  titulo: string;
  /** `destacado` = lo que cambia (peso 700, señal no cromática). */
  resumen?: { izquierda: string; derecha?: string; destacado?: boolean; secundario?: boolean }[];
  total?: number;
  textoConfirmar: string;
  estado: EstadoTarjeta;
  simulacion?: boolean;
  /** 'Venta registrada · Folio V-0042' */
  resultado?: string;
  /** Texto del botón filled mientras confirma ("Cobrando…", "Guardando…"). Default "Confirmando…". */
  textoCargando?: string;
  /** Por qué ya no está vigente ("Hay una más nueva abajo"). */
  motivoCaducada?: string;
  /** Botón del estado `hecha`. Default "Ver comprobante". */
  textoVerResultado?: string;
  /** Default "Revisar y editar". */
  textoEditar?: string;
  /** Faltan datos: no hay Confirmar; "Revisar y editar" pasa a ser el botón filled (no se cobra incompleto). */
  soloRevisar?: boolean;
  /** Motivo visible por el que Confirmar no se puede usar ahora ("Necesita internet", EXC-4). */
  motivoNoDisponible?: string;
  /** Estado `error`: título y mensaje humanos. */
  tituloError?: string;
  mensajeError?: string;
  /** Acción de recuperación del error. Default "Reintentar" → onConfirmar. */
  accionError?: { texto: string; onPress: () => void };
  /** Dentro de un bottom sheet (`surfaceContainerLow`): contenedor `surfaceContainer` y, sin elevación, borde `outlineVariant`. */
  enHoja?: boolean;
  onConfirmar: () => void;
  onEditar?: () => void;
  onRechazar?: () => void;
  onVerResultado?: () => void;
}

const MAX_FILAS = 4;

/**
 * M3 Card elevated (00-sistema §9.10): confirmación de acciones críticas propuestas por el asistente.
 * Cuando ya no es accionable (hecha/rechazada/caducada) baja a elevación 0.
 */
export function TarjetaAccion({
  rol,
  titulo,
  resumen = [],
  total,
  textoConfirmar,
  estado,
  simulacion,
  resultado,
  textoCargando = 'Confirmando…',
  motivoCaducada,
  textoVerResultado = 'Ver comprobante',
  textoEditar = 'Revisar y editar',
  soloRevisar = false,
  motivoNoDisponible,
  tituloError = 'No se pudo completar',
  mensajeError = 'Tus datos siguen aquí.',
  accionError,
  enHoja = false,
  onConfirmar,
  onEditar,
  onRechazar,
  onVerResultado,
}: TarjetaAccionProps) {
  const r = datosRol(rol);
  const visibles = resumen.slice(0, MAX_FILAS);
  const ocultas = resumen.length - visibles.length;
  const activa = estado === 'pendiente' || estado === 'confirmando';

  return (
    <View
      style={[
        estilos.tarjeta,
        enHoja && estilos.tarjetaEnHoja,
        activa || estado === 'error' ? elevacion.level1 : [elevacion.level0, enHoja && estilos.bordeEnHoja],
      ]}
      accessibilityRole="summary"
      accessibilityLabel={`${r.nombre} propone: ${titulo}${total !== undefined ? `, total ${montoParaLector(total)}` : ''}`}
    >
      <View style={estilos.cabecera}>
        <MaterialCommunityIcons
          name={r.icono}
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.quien}>{r.nombre} propone:</Text>
        {simulacion ? <EtiquetaSimulacion /> : null}
      </View>
      <Text style={estilos.titulo}>{titulo}</Text>

      {visibles.length > 0 || total !== undefined ? (
        <View style={estilos.resumen}>
          {visibles.map((f, i) => (
            <View key={`${f.izquierda}-${i}`} style={estilos.filaResumen}>
              <Text style={[estilos.textoResumen, f.secundario && estilos.textoResumenSecundario]}>{f.izquierda}</Text>
              {f.derecha ? (
                <Text
                  style={[estilos.textoResumen, f.secundario && estilos.textoResumenSecundario, f.destacado && estilos.destacado]}
                >
                  {f.derecha}
                </Text>
              ) : null}
            </View>
          ))}
          {ocultas > 0 ? <Text style={estilos.textoSecundario}>y {ocultas} más</Text> : null}
          {total !== undefined ? (
            <View style={estilos.filaResumen}>
              <Text style={estilos.total}>Total</Text>
              <Text style={estilos.total}>{formatoMoneda(total)}</Text>
            </View>
          ) : null}
        </View>
      ) : null}

      {activa || estado === 'caducada' ? (
        <View style={estilos.botones}>
          {estado === 'caducada' ? (
            <View style={estilos.filaIcono}>
              <MaterialCommunityIcons
                name="clock-alert-outline"
                size={iconos.linea}
                color={color.onSurfaceVariant}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.textoSecundario}>
                Esta propuesta ya no está vigente.{motivoCaducada ? ` ${motivoCaducada}` : ''}
              </Text>
            </View>
          ) : null}
          {motivoNoDisponible && estado === 'pendiente' && !soloRevisar ? (
            <View style={estilos.filaIcono}>
              <MaterialCommunityIcons
                name="wifi-off"
                size={iconos.linea}
                color={color.onSurfaceVariant}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.textoSecundario}>{motivoNoDisponible}</Text>
            </View>
          ) : null}
          {soloRevisar && onEditar ? (
            <Boton
              texto={textoEditar}
              icono="pencil"
              onPress={onEditar}
              deshabilitado={estado !== 'pendiente'}
              motivoDeshabilitado="Esta propuesta ya no está vigente"
            />
          ) : (
            <>
              <Boton
                texto={textoConfirmar}
                onPress={onConfirmar}
                cargando={estado === 'confirmando'}
                textoCargando={textoCargando}
                deshabilitado={estado === 'caducada' || motivoNoDisponible !== undefined}
                motivoDeshabilitado={motivoNoDisponible ?? 'Esta propuesta ya no está vigente'}
              />
              {onEditar ? (
                <Boton
                  texto={textoEditar}
                  variante="outlined"
                  onPress={onEditar}
                  deshabilitado={estado !== 'pendiente'}
                  motivoDeshabilitado="Esta propuesta ya no está vigente"
                />
              ) : null}
            </>
          )}
          {onRechazar && estado === 'pendiente' ? (
            <Boton texto="No, gracias" variante="text" onPress={onRechazar} />
          ) : null}
        </View>
      ) : null}

      {estado === 'hecha' ? (
        <View style={estilos.resultado} accessibilityLiveRegion="polite">
          <View style={estilos.filaIcono}>
            <MaterialCommunityIcons
              name="check-circle"
              size={iconos.linea}
              color={color.success}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.textoExito}>Listo{resultado ? ` · ${resultado}` : ''}</Text>
          </View>
          {onVerResultado ? (
            <Boton texto={textoVerResultado} variante="text" anchoCompleto={false} onPress={onVerResultado} />
          ) : null}
        </View>
      ) : null}

      {estado === 'rechazada' ? (
        <View style={estilos.filaIcono}>
          <MaterialCommunityIcons
            name="close-circle"
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.textoSecundario}>Cancelaste esta acción</Text>
        </View>
      ) : null}

      {estado === 'error' ? (
        <View style={estilos.botones}>
          <Aviso
            tipo="error"
            titulo={tituloError}
            mensaje={mensajeError}
            accion={
              accionError
                ? { texto: accionError.texto, onPress: accionError.onPress }
                : { texto: 'Reintentar', icono: 'refresh', onPress: onConfirmar }
            }
          />
          {onEditar && !accionError ? <Boton texto={textoEditar} variante="outlined" onPress={onEditar} /> : null}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  tarjeta: {
    borderRadius: shape.medium,
    padding: espacio.l,
    gap: espacio.m,
    backgroundColor: color.surfaceContainerLow,
  },
  tarjetaEnHoja: { backgroundColor: color.surfaceContainer },
  bordeEnHoja: { borderWidth: bordes.fino, borderColor: color.outlineVariant },
  cabecera: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espacio.s },
  quien: { ...type.labelLarge, color: color.onSurfaceVariant, flex: 1 },
  titulo: { ...type.titleLarge, color: color.onSurface },
  resumen: {
    gap: espacio.xs,
    paddingVertical: espacio.s,
    borderTopWidth: bordes.fino,
    borderBottomWidth: bordes.fino,
    borderColor: color.outlineVariant,
  },
  filaResumen: { flexDirection: 'row', justifyContent: 'space-between', gap: espacio.m },
  textoResumen: { ...type.bodyLarge, color: color.onSurface, flexShrink: 1 },
  textoResumenSecundario: { color: color.onSurfaceVariant },
  destacado: { ...pesoActivo },
  total: { ...type.amount, color: color.onSurface },
  botones: { gap: tactil.separacion },
  resultado: { gap: espacio.xs },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoExito: { ...type.labelLarge, color: color.onSurface, flex: 1 },
  textoSecundario: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
});
