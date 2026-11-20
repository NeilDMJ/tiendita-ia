import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import type { ComponentRef, Ref } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Aviso } from '@/components/aviso';
import { Boton } from '@/components/boton';
import { EXISTENCIA_BAJA } from '@/constants';
import { bordes, color, espacio, iconos, shape, type } from '@/theme';
import { plural } from '@/utils/carrito';
import { formatoMoneda } from '@/utils/formato-moneda';

import type { ProductoAlertaStock } from './tipos';

export interface AlertasDiaProps {
  borradorTotal: number;
  borradorCantidad: number;
  onContinuarBorrador: () => void;
  onDescartarBorrador: () => void;
  refDescartar?: Ref<ComponentRef<typeof View>>;
  ventasPendientes: number;
  onSincronizarCola: () => void;
  sinConexion: boolean;
  productosAlerta: ProductoAlertaStock[];
  cargandoStock?: boolean;
}

/**
 * Centro de Alertas operativas del día en Inicio (M3):
 * Supervisa stock bajo en mostrador, ventas en cola sin conexión y ventas pendientes de terminar.
 */
export function AlertasDia({
  borradorTotal,
  borradorCantidad,
  onContinuarBorrador,
  onDescartarBorrador,
  refDescartar,
  ventasPendientes,
  onSincronizarCola,
  sinConexion,
  productosAlerta,
}: AlertasDiaProps) {
  const hayBorrador = borradorCantidad > 0;
  const hayPendientes = ventasPendientes > 0;
  const hayProductosBajoStock = productosAlerta.length > 0;
  const sinAlertas = !hayBorrador && !hayPendientes && !sinConexion && !hayProductosBajoStock;

  return (
    <View style={estilos.contenedor}>
      <Text style={estilos.encabezadoSeccion} accessibilityRole="header">
        Alertas y avisos de la tienda
      </Text>

      {/* 1. Alerta: Venta sin terminar en mostrador */}
      {hayBorrador ? (
        <Aviso
          tipo="info"
          titulo="Venta sin terminar"
          mensaje={`Tienes una venta de ${formatoMoneda(borradorTotal)} sin cobrar (${plural(borradorCantidad, 'producto', 'productos')}).`}
          accion={{
            texto: 'Continuar venta',
            variante: 'tonal',
            onPress: onContinuarBorrador,
          }}
          accionSecundaria={{
            texto: 'Descartar',
            icono: 'trash-can-outline',
            onPress: onDescartarBorrador,
          }}
          refAccionSecundaria={refDescartar}
        />
      ) : null}

      {/* 2. Alerta: Ventas en cola local pendientes de enviar */}
      {hayPendientes ? (
        <Aviso
          tipo="sinConexion"
          titulo={`${ventasPendientes} ${plural(ventasPendientes, 'venta guardada', 'ventas guardadas')} en tu teléfono`}
          mensaje="Se enviarán solas cuando vuelva el internet. Tu corte e inventario se actualizarán al enviarse."
          accion={{
            texto: 'Reintentar enviar ahora',
            icono: 'refresh',
            variante: 'tonal',
            onPress: onSincronizarCola,
          }}
        />
      ) : null}

      {/* 3. Alerta: Sin conexión a internet general */}
      {sinConexion && !hayPendientes ? (
        <Aviso
          tipo="sinConexion"
          titulo="Sin conexión a internet"
          mensaje="Puedes seguir cobrando en el mostrador. Todo lo que registres se guardará de forma segura en tu teléfono."
        />
      ) : null}

      {/* 4. Alerta: Productos con poco stock o agotados */}
      {hayProductosBajoStock ? (
        <View style={estilos.cardStock}>
          <View style={estilos.cabeceraStock}>
            <MaterialCommunityIcons
              name="alert-circle"
              size={iconos.linea}
              color={color.error}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
            <Text style={estilos.tituloStock}>
              {productosAlerta.length} {plural(productosAlerta.length, 'producto necesita mercancía', 'productos necesitan mercancía')}
            </Text>
          </View>

          <Text style={estilos.cuerpoStock}>
            Revisa las piezas en mostrador antes de que se agoten:
          </Text>

          <View style={estilos.listaStock}>
            {productosAlerta.slice(0, 4).map((p) => {
              const agotado = p.existencia <= 0;
              return (
                <View
                  key={p.sku}
                  style={estilos.filaStock}
                  accessible
                  accessibilityLabel={`${p.nombre}, ${agotado ? 'sin existencia' : `quedan ${p.existencia} piezas`}`}
                >
                  <View style={estilos.infoProducto}>
                    <Text style={estilos.nombreProducto}>{p.nombre}</Text>
                    <Text style={estilos.piezasProducto}>
                      {agotado ? 'Sin existencia' : `Quedan ${p.existencia} pz`}
                    </Text>
                  </View>
                  <View style={[estilos.chipStock, agotado ? estilos.chipAgotado : estilos.chipPoco]}>
                    <MaterialCommunityIcons
                      name={agotado ? 'close-circle' : 'alert-circle'}
                      size={iconos.chico}
                      color={agotado ? color.onErrorContainer : color.onTertiaryContainer}
                      accessibilityElementsHidden
                      importantForAccessibility="no"
                    />
                    <Text style={[estilos.textoChip, { color: agotado ? color.onErrorContainer : color.onTertiaryContainer }]}>
                      {agotado ? 'Agotado' : `Poco (≤ ${EXISTENCIA_BAJA} pz)`}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>

          <Boton
            texto="Tomar foto a mercancía para surtir"
            icono="package-variant-plus"
            variante="tonal"
            onPress={() => router.push('/camara?modo=alta' as any)}
            accessibilityHint="Abre la cámara en modo alta para registrar entradas de productos"
          />
        </View>
      ) : null}

      {/* 5. Estado positivo: Todo al día */}
      {sinAlertas ? (
        <Aviso
          tipo="exito"
          titulo="Todo al corriente"
          mensaje="No tienes ventas pendientes por enviar ni productos por agotarse."
        />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: {
    gap: espacio.m,
  },
  encabezadoSeccion: {
    ...type.titleMedium,
    color: color.onSurface,
  },
  cardStock: {
    backgroundColor: color.surfaceContainerLow,
    borderRadius: shape.medium,
    padding: espacio.l,
    gap: espacio.m,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
  },
  cabeceraStock: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  tituloStock: {
    ...type.titleMedium,
    color: color.error,
  },
  cuerpoStock: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  listaStock: {
    gap: espacio.xs,
  },
  filaStock: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: espacio.s,
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outlineVariant,
  },
  infoProducto: {
    flex: 1,
    gap: espacio.xs,
  },
  nombreProducto: {
    ...type.titleSmall,
    color: color.onSurface,
  },
  piezasProducto: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
  },
  chipStock: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.s,
    paddingVertical: espacio.xs,
    borderRadius: shape.small,
  },
  chipPoco: {
    backgroundColor: color.tertiaryContainer,
  },
  chipAgotado: {
    backgroundColor: color.errorContainer,
  },
  textoChip: {
    ...type.labelLarge,
  },
});
