import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { RolAsistente } from '@/api/esquemas';
import { ROLES } from '@/constants';
import { bordes, color, elevacion, espacio, iconos, shape, tactil, type } from '@/theme';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import { Aviso } from './aviso';
import { Boton } from './boton';
import { EtiquetaSimulacion } from './etiqueta-simulacion';

export type EstadoTarjeta = 'pendiente' | 'confirmando' | 'hecha' | 'rechazada' | 'error' | 'caducada';

export interface TarjetaAccionProps {
  rol: RolAsistente;
  titulo: string;
  resumen?: { izquierda: string; derecha?: string }[];
  total?: number;
  textoConfirmar: string;
  estado: EstadoTarjeta;
  simulacion?: boolean;
  /** 'Folio V-0042' */
  resultado?: string;
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
  onConfirmar,
  onEditar,
  onRechazar,
  onVerResultado,
}: TarjetaAccionProps) {
  const r = ROLES[rol];
  const visibles = resumen.slice(0, MAX_FILAS);
  const ocultas = resumen.length - visibles.length;
  const activa = estado === 'pendiente' || estado === 'confirmando';

  return (
    <View
      style={[estilos.tarjeta, activa || estado === 'error' ? elevacion.level1 : elevacion.level0]}
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
              <Text style={estilos.textoResumen}>{f.izquierda}</Text>
              {f.derecha ? <Text style={estilos.textoResumen}>{f.derecha}</Text> : null}
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
            <Text style={estilos.textoSecundario}>Esta propuesta ya no está vigente</Text>
          ) : null}
          <Boton
            texto={textoConfirmar}
            onPress={onConfirmar}
            cargando={estado === 'confirmando'}
            textoCargando="Confirmando…"
            deshabilitado={estado === 'caducada'}
            motivoDeshabilitado="Esta propuesta ya no está vigente"
          />
          {onEditar ? (
            <Boton
              texto="Revisar y editar"
              variante="outlined"
              onPress={onEditar}
              deshabilitado={estado !== 'pendiente'}
            />
          ) : null}
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
          {onVerResultado ? <Boton texto="Ver comprobante" variante="text" anchoCompleto={false} onPress={onVerResultado} /> : null}
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
        <Aviso
          tipo="error"
          titulo="No se pudo completar"
          mensaje="Tus datos siguen aquí."
          accion={{ texto: 'Reintentar', icono: 'refresh', onPress: onConfirmar }}
        />
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
  total: { ...type.amount, color: color.onSurface },
  botones: { gap: tactil.separacion },
  resultado: { gap: espacio.xs },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoExito: { ...type.labelLarge, color: color.onSurface, flex: 1 },
  textoSecundario: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
});
