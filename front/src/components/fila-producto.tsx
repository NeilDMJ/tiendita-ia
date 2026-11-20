import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentRef, Ref } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import { bordes, color, espacio, iconos, medidas, shape, tactil, type } from '@/theme';
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

/**
 * M3 List item de 3 líneas (00-sistema §9.9). Problemas como cards:
 * `baja` = card filled + borde izquierdo 4 dp `tertiary`; `falta` = card outlined 2 dp `error` (EXC-6).
 * `soloLectura` = list item de 1 línea (56).
 */
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
        <View style={[estilos.divisor, estilos.divisorCompleto]} />
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
      {nivel === 'baja' || nivel === 'falta' ? null : <View style={estilos.divisor} />}
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
            <MaterialCommunityIcons
              name="alert-circle"
              size={iconos.linea}
              color={color.error}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
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
              variante="tonal"
              anchoCompleto={false}
              onPress={onEstaBien}
              accessibilityHint={`Confirma que ${nombre} es correcto`}
            />
          ) : null}
          {onEditar ? (
            nivel === 'falta' ? (
              <Boton
                texto={textoFalta === 'Elige producto' ? 'Elegir producto' : 'Poner precio'}
                variante="filled"
                anchoCompleto={false}
                onPress={onEditar}
                accessibilityHint={`Corrige ${nombre}`}
              />
            ) : (
              <Boton
                texto="Editar"
                icono="pencil"
                variante="text"
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
    backgroundColor: color.surface,
  },
  // divisor decorativo con inset 16 (outlineVariant)
  divisor: {
    position: 'absolute',
    left: espacio.l,
    right: 0,
    bottom: 0,
    height: bordes.fino,
    backgroundColor: color.outlineVariant,
  },
  divisorCompleto: { left: 0 },
  // card filled + borde izquierdo tertiary (forma además del chip "Revisa")
  filaBaja: {
    backgroundColor: color.surfaceContainerHighest,
    borderRadius: shape.medium,
    borderLeftWidth: bordes.acento,
    borderLeftColor: color.tertiary,
    paddingLeft: espacio.l - bordes.acento,
    marginBottom: espacio.s,
  },
  // card outlined con borde 2 dp error (EXC-6)
  filaFalta: {
    backgroundColor: color.surface,
    borderWidth: bordes.grueso,
    borderColor: color.error,
    borderRadius: shape.medium,
    paddingHorizontal: espacio.l - bordes.grueso,
    marginBottom: espacio.s,
  },
  bloqueTexto: { gap: espacio.xs },
  lineaSuperior: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.m },
  numero: {
    width: medidas.numeroFoto,
    height: medidas.numeroFoto,
    borderRadius: shape.small,
    backgroundColor: color.inverseSurface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textoNumero: { ...type.labelLarge, color: color.inverseOnSurface },
  nombre: { ...type.titleMedium, color: color.onSurface, flex: 1 },
  monto: { ...type.amount, color: color.onSurface },
  lineaMedia: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espacio.s },
  precio: { ...type.bodyLarge, color: color.onSurfaceVariant },
  problema: { flexDirection: 'row', gap: espacio.xs, alignItems: 'flex-start' },
  textoProblema: { ...type.labelLarge, color: color.error, flex: 1 },
  lineaControles: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: espacio.s,
  },
  botones: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion, justifyContent: 'flex-end' },
  lectura: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: espacio.m,
    paddingVertical: espacio.s,
  },
  lecturaNombre: { ...type.bodyLarge, color: color.onSurface, flex: 1 },
});
