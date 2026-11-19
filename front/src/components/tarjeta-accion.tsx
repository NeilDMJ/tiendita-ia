import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import type { RolAsistente } from '@/api/esquemas';
import { ROLES } from '@/constants';
import { bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';
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

/** Confirmación de acciones críticas propuestas por el asistente (dentro del chat). */
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
      style={estilos.tarjeta}
      accessibilityRole="summary"
      accessibilityLabel={`${r.nombre} propone: ${titulo}${total !== undefined ? `, total ${montoParaLector(total)}` : ''}`}
    >
      <View style={estilos.cabecera}>
        <MaterialCommunityIcons name={r.icono} size={iconos.linea} color={colores.textoSecundario} />
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
              variante="secundario"
              onPress={onEditar}
              deshabilitado={estado !== 'pendiente'}
            />
          ) : null}
          {onRechazar && estado === 'pendiente' ? (
            <Boton texto="No, gracias" variante="texto" onPress={onRechazar} />
          ) : null}
        </View>
      ) : null}

      {estado === 'hecha' ? (
        <View style={estilos.resultado} accessibilityLiveRegion="polite">
          <View style={estilos.filaIcono}>
            <MaterialCommunityIcons name="check-circle" size={iconos.linea} color={colores.exito} />
            <Text style={estilos.textoExito}>Listo{resultado ? ` · ${resultado}` : ''}</Text>
          </View>
          {onVerResultado ? <Boton texto="Ver comprobante" variante="texto" onPress={onVerResultado} /> : null}
        </View>
      ) : null}

      {estado === 'rechazada' ? (
        <View style={estilos.filaIcono}>
          <MaterialCommunityIcons name="close-circle" size={iconos.linea} color={colores.textoSecundario} />
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
    borderWidth: bordes.grueso,
    borderColor: colores.texto,
    borderRadius: radios.medio,
    padding: espacio.l,
    gap: espacio.m,
    backgroundColor: colores.fondo,
  },
  cabecera: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espacio.s },
  quien: { ...tipografia.etiqueta, color: colores.textoSecundario, flex: 1 },
  titulo: { ...tipografia.subtitulo, color: colores.texto },
  resumen: {
    gap: espacio.xs,
    paddingVertical: espacio.s,
    borderTopWidth: bordes.fino,
    borderBottomWidth: bordes.fino,
    borderColor: colores.divisor,
  },
  filaResumen: { flexDirection: 'row', justifyContent: 'space-between', gap: espacio.m },
  textoResumen: { ...tipografia.cuerpo, color: colores.texto, flexShrink: 1 },
  total: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'] },
  botones: { gap: tactil.separacion },
  resultado: { gap: espacio.xs },
  filaIcono: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoExito: { ...tipografia.etiqueta, color: colores.exito, flex: 1 },
  textoSecundario: { ...tipografia.cuerpo, color: colores.textoSecundario, flex: 1 },
});
