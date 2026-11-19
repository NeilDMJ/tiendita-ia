import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentRef, Ref } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import { bordes, colores, espacio, iconos, radios, tipografia } from '@/theme';
import type { NivelConfianza } from '@/utils/carrito';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

import { Boton } from './boton';
import { IndicadorConfianza } from './indicador-confianza';
import { StepperCantidad } from './stepper-cantidad';

type Unidad = 'pz' | 'kg' | 'paq';

export interface FilaProductoProps {
  nombre: string;
  precioUnitario: number | null;
  cantidad: number;
  nivel: NivelConfianza;
  textoFalta?: string;
  /** Mensaje concreto bajo el nombre (p. ej. "Solo hay 1 en existencia. Ajusta la cantidad."). */
  problema?: string;
  unidad?: Unidad;
  maximo?: number;
  /** Número que coincide con el recuadro de la foto. */
  numero?: number;
  modo?: 'editable' | 'soloLectura';
  onCambiarCantidad?: (n: number) => void;
  onEditar?: () => void;
  onQuitar?: () => void;
  /** Solo para nivel 'baja': acepta lo detectado. */
  onEstaBien?: () => void;
  onLayout?: (e: LayoutChangeEvent) => void;
  /** Ref al bloque de texto (para mover el foco del lector). */
  refTexto?: Ref<ComponentRef<typeof View>>;
}

const ETIQUETA_NIVEL: Record<NivelConfianza, string> = {
  alta: 'detectado',
  baja: 'revisa este producto',
  falta: 'falta un dato',
  manual: 'tú lo pusiste',
};

/** Fila densa de carrito / revisión / comprobante. */
export function FilaProducto({
  nombre,
  precioUnitario,
  cantidad,
  nivel,
  textoFalta,
  problema,
  unidad = 'pz',
  maximo,
  numero,
  modo = 'editable',
  onCambiarCantidad,
  onEditar,
  onQuitar,
  onEstaBien,
  onLayout,
  refTexto,
}: FilaProductoProps) {
  const subtotal = precioUnitario === null ? null : precioUnitario * cantidad;
  const piezas = `${cantidad} ${cantidad === 1 ? 'pieza' : 'piezas'}`;

  if (modo === 'soloLectura') {
    return (
      <View
        style={estilos.lectura}
        accessible
        accessibilityLabel={`${piezas} de ${nombre}, ${subtotal === null ? 'sin precio' : montoParaLector(subtotal)}`}
      >
        <Text style={estilos.lecturaNombre}>
          {cantidad} × {nombre}
        </Text>
        <Text style={estilos.monto}>{subtotal === null ? '— —' : formatoMoneda(subtotal)}</Text>
      </View>
    );
  }

  const etiquetaLector = [
    numero ? `Producto ${numero}` : null,
    nombre,
    precioUnitario === null ? `${piezas}, sin precio` : `${piezas} a ${montoParaLector(precioUnitario)}`,
    subtotal === null ? null : `subtotal ${montoParaLector(subtotal)}`,
    nivel === 'falta' && textoFalta ? textoFalta : ETIQUETA_NIVEL[nivel],
    problema,
  ]
    .filter(Boolean)
    .join(', ');

  return (
    <View
      onLayout={onLayout}
      style={[estilos.fila, nivel === 'baja' && estilos.filaBaja, nivel === 'falta' && estilos.filaFalta]}
    >
      <View ref={refTexto} accessible accessibilityLabel={etiquetaLector} style={estilos.bloqueTexto}>
        <View style={estilos.lineaSuperior}>
          {numero ? (
            <View style={estilos.numero}>
              <Text style={estilos.textoNumero}>{numero}</Text>
            </View>
          ) : null}
          <Text style={estilos.nombre} numberOfLines={2}>
            {nombre}
          </Text>
          <Text style={estilos.monto}>{subtotal === null ? '— —' : formatoMoneda(subtotal)}</Text>
        </View>
        <View style={estilos.lineaMedia}>
          <Text style={estilos.precio}>
            {precioUnitario === null ? 'Sin precio' : `${formatoMoneda(precioUnitario)} c/u`}
          </Text>
          <IndicadorConfianza nivel={nivel} textoFalta={textoFalta} />
        </View>
        {problema ? (
          <View style={estilos.problema}>
            <MaterialCommunityIcons name="alert-circle" size={iconos.linea} color={colores.peligro} />
            <Text style={estilos.textoProblema}>{problema}</Text>
          </View>
        ) : null}
      </View>

      <View style={estilos.lineaControles}>
        {onCambiarCantidad ? (
          <StepperCantidad
            valor={cantidad}
            onCambiar={onCambiarCantidad}
            maximo={maximo}
            unidad={unidad}
            onQuitar={onQuitar}
            nombreProducto={nombre}
          />
        ) : null}
        <View style={estilos.botones}>
          {nivel === 'baja' && onEstaBien ? (
            <Boton
              texto="Está bien"
              icono="check"
              variante="secundario"
              anchoCompleto={false}
              onPress={onEstaBien}
              accessibilityHint={`Confirma que ${nombre} es correcto`}
            />
          ) : null}
          {onEditar ? (
            nivel === 'falta' ? (
              <Boton
                texto={textoFalta === 'Elige producto' ? 'Elegir producto' : 'Poner precio'}
                variante="peligro"
                anchoCompleto={false}
                onPress={onEditar}
                accessibilityHint={`Corrige ${nombre}`}
              />
            ) : (
              <Boton
                texto="Editar"
                icono="pencil"
                variante="texto"
                anchoCompleto={false}
                onPress={onEditar}
                accessibilityHint={`Cambia producto o precio de ${nombre}`}
              />
            )
          ) : null}
        </View>
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  fila: {
    paddingVertical: espacio.m,
    paddingHorizontal: espacio.l,
    gap: espacio.s,
    backgroundColor: colores.fondo,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.divisor,
  },
  filaBaja: {
    backgroundColor: colores.superficie,
    borderWidth: bordes.grueso,
    borderColor: colores.texto,
    borderBottomColor: colores.texto,
    borderRadius: radios.medio,
    marginBottom: espacio.s,
  },
  filaFalta: {
    borderWidth: bordes.grueso,
    borderColor: colores.peligro,
    borderBottomColor: colores.peligro,
    borderRadius: radios.medio,
    marginBottom: espacio.s,
  },
  bloqueTexto: { gap: espacio.xs },
  lineaSuperior: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.s },
  numero: {
    minWidth: iconos.linea + espacio.xs,
    paddingHorizontal: espacio.xs,
    borderRadius: radios.chico,
    backgroundColor: colores.oscuro,
    alignItems: 'center',
  },
  textoNumero: { ...tipografia.etiqueta, color: colores.sobreOscuro },
  nombre: { ...tipografia.nombreProducto, color: colores.texto, flex: 1 },
  monto: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'] },
  lineaMedia: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espacio.s },
  precio: { ...tipografia.cuerpo, color: colores.textoSecundario },
  problema: { flexDirection: 'row', gap: espacio.xs, alignItems: 'flex-start' },
  textoProblema: { ...tipografia.etiqueta, color: colores.peligro, flex: 1 },
  lineaControles: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: espacio.s,
  },
  botones: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s, justifyContent: 'flex-end' },
  lectura: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: espacio.m,
    paddingVertical: espacio.m,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.divisor,
  },
  lecturaNombre: { ...tipografia.cuerpoGrande, color: colores.texto, flex: 1 },
});
