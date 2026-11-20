import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { EXISTENCIA_BAJA } from '@/constants';
import { bordes, color, espacio, fuente, iconos, shape, type } from '@/theme';
import { formatoMoneda } from '@/utils/formato-moneda';

import type { ProductoInventario } from './tipos';

export interface FilaInventarioProps {
  producto: ProductoInventario;
}

/**
 * Fila de producto en la lista de inventario (M3 List item de 3 líneas, 00-sistema §9.9).
 *
 * Muestra: nombre, precio, existencia con chip de estado, y fecha de caducidad
 * con señal visual de alerta (por caducar → warningContainer, caducado → errorContainer).
 *
 * Nielsen #6: reconocimiento antes que recuerdo — toda la info relevante está visible.
 * Nielsen #4: consistencia — mismos colores de alerta que en Inicio (stock bajo / agotado).
 */
export function FilaInventario({ producto }: FilaInventarioProps) {
  const { nombre, precio_unitario, existencia, caducidad, categoria, agotado, stockBajo, porCaducar, caducado, diasParaCaducar } =
    producto;

  const textoCaducidad = caducidad ? formatearCaducidad(caducidad, diasParaCaducar, caducado) : 'Sin caducidad';

  const textoExistencia = agotado
    ? 'Sin existencia'
    : `${existencia} ${existencia === 1 ? 'pieza' : 'piezas'}`;

  const etiquetaAccesible = `${nombre}, ${formatoMoneda(precio_unitario)}, ${textoExistencia}${caducidad ? `, caduca ${textoCaducidad}` : ''}`;

  return (
    <View
      style={[estilos.fila, (agotado || caducado) && estilos.filaAlerta]}
      accessible
      accessibilityLabel={etiquetaAccesible}
    >
      {/* Columna izquierda: info del producto */}
      <View style={estilos.info}>
        <Text style={estilos.nombre} numberOfLines={2}>
          {nombre}
        </Text>

        <View style={estilos.detalles}>
          <Text style={estilos.precio}>{formatoMoneda(precio_unitario)}</Text>
          {categoria ? (
            <View style={estilos.separador}>
              <Text style={estilos.categoria}>{categoria}</Text>
            </View>
          ) : null}
        </View>

        {/* Fecha de caducidad */}
        {caducidad ? (
          <View style={estilos.filaCaducidad}>
            <MaterialCommunityIcons
              name={caducado ? 'calendar-alert' : porCaducar ? 'calendar-clock' : 'calendar'}
              size={iconos.chico}
              color={caducado ? color.error : porCaducar ? color.onWarningContainer : color.onSurfaceVariant}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text
              style={[
                estilos.textoCaducidad,
                caducado && estilos.textoCaducado,
                porCaducar && estilos.textoPorCaducar,
              ]}
            >
              {textoCaducidad}
            </Text>
          </View>
        ) : null}
      </View>

      {/* Columna derecha: chip de existencia */}
      <View style={estilos.columnaEstado}>
        <View style={[estilos.chipExistencia, chipEstilo(agotado, stockBajo)]}>
          <MaterialCommunityIcons
            name={agotado ? 'close-circle' : stockBajo ? 'alert-circle' : 'check-circle'}
            size={iconos.chico}
            color={chipColorTexto(agotado, stockBajo)}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={[estilos.textoChip, { color: chipColorTexto(agotado, stockBajo) }]}>
            {agotado ? 'Agotado' : stockBajo ? `Poco (≤ ${EXISTENCIA_BAJA})` : `${existencia} pz`}
          </Text>
        </View>

        {(porCaducar || caducado) && caducidad ? (
          <View style={[estilos.chipCaducidad, caducado ? estilos.chipCaducado : estilos.chipPorCaducar]}>
            <Text style={[estilos.textoChipPeq, { color: caducado ? color.onErrorContainer : color.onWarningContainer }]}>
              {caducado ? 'Caducado' : `${diasParaCaducar} días`}
            </Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

function chipEstilo(agotado: boolean, stockBajo: boolean) {
  if (agotado) return estilos.chipAgotado;
  if (stockBajo) return estilos.chipPoco;
  return estilos.chipNormal;
}

function chipColorTexto(agotado: boolean, stockBajo: boolean): string {
  if (agotado) return color.onErrorContainer;
  if (stockBajo) return color.onWarningContainer;
  return color.onSurfaceVariant;
}

function formatearCaducidad(fecha: string, diasRestantes: number | null, caducado: boolean): string {
  if (caducado) return 'Caducado';
  if (diasRestantes !== null && diasRestantes <= 7) {
    if (diasRestantes === 0) return 'Caduca hoy';
    if (diasRestantes === 1) return 'Caduca mañana';
    return `Caduca en ${diasRestantes} días`;
  }
  // Formato legible: "22 nov 2026"
  const d = new Date(fecha + 'T00:00:00');
  const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  return `${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()}`;
}

const estilos = StyleSheet.create({
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: espacio.m,
    paddingHorizontal: espacio.l,
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outlineVariant,
    gap: espacio.m,
  },
  filaAlerta: {
    backgroundColor: color.surfaceContainerHighest,
  },
  info: {
    flex: 1,
    gap: espacio.xs,
  },
  nombre: {
    ...type.titleSmall,
    color: color.onSurface,
  },
  detalles: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  precio: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  separador: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
  },
  categoria: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  filaCaducidad: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
  },
  textoCaducidad: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  textoCaducado: {
    color: color.error,
    fontFamily: fuente.bold,
  },
  textoPorCaducar: {
    color: color.onWarningContainer,
    fontFamily: fuente.medium,
  },
  columnaEstado: {
    alignItems: 'flex-end',
    gap: espacio.xs,
  },
  chipExistencia: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.s,
    paddingVertical: espacio.xs,
    borderRadius: shape.small,
  },
  chipNormal: {
    backgroundColor: color.surfaceContainerLow,
  },
  chipPoco: {
    backgroundColor: color.warningContainer,
  },
  chipAgotado: {
    backgroundColor: color.errorContainer,
  },
  textoChip: {
    ...type.labelLarge,
  },
  chipCaducidad: {
    paddingHorizontal: espacio.s,
    paddingVertical: espacio.xs,
    borderRadius: shape.small,
  },
  chipPorCaducar: {
    backgroundColor: color.warningContainer,
  },
  chipCaducado: {
    backgroundColor: color.errorContainer,
  },
  textoChipPeq: {
    ...type.labelSmall,
  },
});
