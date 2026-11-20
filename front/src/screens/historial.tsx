import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Aviso } from '@/components/aviso';
import { Encabezado } from '@/components/encabezado';
import { FilaVenta } from '@/components/fila-venta';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { bordes, color, espacio, type } from '@/theme';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

/** Historial: todas las ventas de hoy (enviadas y pendientes de enviar). */
export function PantallaHistorial() {
  const ventas = useVentasHoy();
  const suma = ventas.lista.reduce((s, v) => s + v.total, 0);
  const volver = () => (router.canGoBack() ? router.back() : router.navigate('/cobrar'));
  const [desplazado, setDesplazado] = useState(false);

  return (
    <SafeAreaView edges={['bottom']} style={estilos.pantalla}>
      <Encabezado titulo="Ventas de hoy" onAtras={volver} desplazado={desplazado} />
      {ventas.cargando ? (
        <View style={estilos.centrado} accessibilityLiveRegion="polite">
          <ActivityIndicator size="large" color={color.primary} />
          <Text style={estilos.cuerpo}>Cargando ventas de hoy…</Text>
        </View>
      ) : ventas.error ? (
        <View style={estilos.margen}>
          <Aviso
            tipo="error"
            titulo="No pudimos traer tus ventas de hoy."
            accion={{ texto: 'Reintentar', icono: 'refresh', onPress: ventas.reintentar }}
          />
        </View>
      ) : (
        <FlatList
          data={ventas.lista}
          keyExtractor={(v) => v.id}
          scrollEventThrottle={16}
          onScroll={(e) => setDesplazado(e.nativeEvent.contentOffset.y > 0)}
          renderItem={({ item }) => (
            <FilaVenta venta={item} onPress={() => router.push(`/venta/${item.id}?origen=historial`)} />
          )}
          ListHeaderComponent={
            ventas.lista.length > 0 ? (
              <View
                style={estilos.resumen}
                accessible
                accessibilityLabel={`${ventas.lista.length} ventas, total ${montoParaLector(suma)}`}
              >
                <Text style={estilos.etiqueta}>{ventas.lista.length} ventas</Text>
                <Text style={estilos.total}>{formatoMoneda(suma)}</Text>
              </View>
            ) : undefined
          }
          ListEmptyComponent={
            <View style={estilos.margen}>
              <Aviso tipo="info" titulo="Todavía no hay ventas hoy." mensaje="Tu primera venta aparecerá aquí." />
            </View>
          }
          ListFooterComponent={
            ventas.errorParcial ? (
              <View style={estilos.margen}>
                <Aviso
                  tipo="sinConexion"
                  titulo="Solo ves las ventas guardadas en tu teléfono."
                  accion={{ texto: 'Reintentar', icono: 'refresh', onPress: ventas.reintentar }}
                />
              </View>
            ) : undefined
          }
        />
      )}
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: color.surface },
  centrado: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.m },
  margen: { padding: espacio.l },
  cuerpo: { ...type.bodyLargePlus, color: color.onSurface },
  // franja de resumen tonal (surfaceContainer)
  resumen: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: espacio.l,
    backgroundColor: color.surfaceContainer,
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outlineVariant,
  },
  etiqueta: { ...type.titleMedium, color: color.onSurface },
  total: { ...type.amount, color: color.onSurface },
});
