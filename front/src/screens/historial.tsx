import { router } from 'expo-router';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Aviso } from '@/components/aviso';
import { Encabezado } from '@/components/encabezado';
import { FilaVenta } from '@/components/fila-venta';
import { useVentasHoy } from '@/hooks/use-ventas-hoy';
import { bordes, colores, espacio, tipografia } from '@/theme';
import { formatoMoneda, montoParaLector } from '@/utils/formato-moneda';

/** Historial: todas las ventas de hoy (enviadas y pendientes de enviar). */
export function PantallaHistorial() {
  const ventas = useVentasHoy();
  const suma = ventas.lista.reduce((s, v) => s + v.total, 0);
  const volver = () => (router.canGoBack() ? router.back() : router.navigate('/cobrar'));

  return (
    <SafeAreaView edges={['bottom']} style={estilos.pantalla}>
      <Encabezado titulo="Ventas de hoy" onAtras={volver} />
      {ventas.cargando ? (
        <View style={estilos.centrado} accessibilityLiveRegion="polite">
          <ActivityIndicator size="large" color={colores.acento} />
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
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  centrado: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.m },
  margen: { padding: espacio.l },
  cuerpo: { ...tipografia.cuerpoGrande, color: colores.texto },
  resumen: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: espacio.l,
    backgroundColor: colores.superficie,
    borderBottomWidth: bordes.fino,
    borderBottomColor: colores.divisor,
  },
  etiqueta: { ...tipografia.etiqueta, color: colores.texto },
  total: { ...tipografia.monto, color: colores.texto, fontVariant: ['tabular-nums'] },
});
