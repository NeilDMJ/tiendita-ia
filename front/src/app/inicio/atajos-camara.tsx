import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Boton } from '@/components/boton';
import { color, espacio, type } from '@/theme';

import { TarjetaAtajo } from './tarjeta-atajo';

/**
 * Sección de atajos rápidos de cámara y mostrador en Inicio.
 * Enfocada en las operaciones del negocio (surtir mercancía con cámara, escanear notas de compra
 * y consultar a Caja), complementando la pestaña de cobro sin duplicar sus módulos.
 */
export function AtajosCamara() {
  const agregarMercancia = () => router.push('/camara?modo=alta' as any);
  const escanearTicket = () => router.push('/camara?modo=ticket' as any);
  const irAsistente = () => router.push('/asistente');
  const irACobrar = () => router.push('/cobrar');

  return (
    <View style={estilos.contenedor}>
      <View style={estilos.cabecera}>
        <Text style={[estilos.tituloSeccion, estilos.flex]} accessibilityRole="header">
          Atajos a la cámara y tienda
        </Text>
        <Boton
          texto="Ir a cobrar"
          icono="cash-register"
          variante="text"
          anchoCompleto={false}
          onPress={irACobrar}
          accessibilityHint="Abre la pantalla de cobro con foto"
        />
      </View>

      <View style={estilos.grillaAtajos}>
        <TarjetaAtajo
          icono="package-variant-plus"
          titulo="Agregar mercancía"
          detalle="Foto de producto nuevo"
          onPress={agregarMercancia}
          accesibilidadLabel="Agregar mercancía. Foto de producto nuevo para surtir inventario"
          accesibilidadHint="Abre la cámara en modo alta para registrar entradas de productos"
        />

        <TarjetaAtajo
          icono="receipt-text"
          titulo="Escanear ticket"
          detalle="Foto a nota de compra"
          onPress={escanearTicket}
          accesibilidadLabel="Escanear ticket. Foto a notas de compra o proveedores"
          accesibilidadHint="Abre la cámara en modo ticket para registrar compras y gastos"
        />

        <TarjetaAtajo
          icono="chat-outline"
          titulo="Pregúntale a Caja"
          detalle="Cuentas e inventario"
          onPress={irAsistente}
          accesibilidadLabel="Pregúntale a Caja. Asistente para dudas de ventas o inventario"
          accesibilidadHint="Abre la pestaña del asistente de la tienda"
        />
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: {
    gap: espacio.m,
  },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
  },
  flex: {
    flex: 1,
  },
  tituloSeccion: {
    ...type.titleMedium,
    color: color.onSurface,
  },
  grillaAtajos: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: espacio.l,
  },
});
