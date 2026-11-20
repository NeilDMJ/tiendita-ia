import { MaterialCommunityIcons } from '@expo/vector-icons';
import { FlatList, StyleSheet, Text, View } from 'react-native';

import { color, espacio, iconos, type } from '@/theme';

import { FilaInventario } from './fila-inventario';
import type { ProductoInventario } from './tipos';

export interface ListaProductosProps {
  productos: ProductoInventario[];
  textoBusqueda: string;
  cargando: boolean;
}

/**
 * Lista de productos del inventario con FlatList para rendimiento.
 * Incluye estado vacío con retroalimentación contextual (Nielsen #1) y
 * estado de búsqueda sin resultados con ayuda de recuperación (Nielsen #9).
 */
export function ListaProductos({ productos, textoBusqueda, cargando }: ListaProductosProps) {
  if (cargando) {
    return (
      <View style={estilos.estadoVacio}>
        <MaterialCommunityIcons
          name="package-variant-closed"
          size={iconos.grande}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.tituloVacio}>Cargando inventario…</Text>
      </View>
    );
  }

  if (productos.length === 0 && textoBusqueda.length > 0) {
    return (
      <View style={estilos.estadoVacio}>
        <MaterialCommunityIcons
          name="magnify-close"
          size={iconos.grande}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.tituloVacio}>No encontramos “{textoBusqueda}”</Text>
        <Text style={estilos.mensajeVacio}>
          Revisa que el nombre esté bien escrito o limpia la búsqueda para ver todo el inventario.
        </Text>
      </View>
    );
  }

  if (productos.length === 0) {
    return (
      <View style={estilos.estadoVacio}>
        <MaterialCommunityIcons
          name="package-variant"
          size={iconos.grande}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.tituloVacio}>Inventario vacío con este filtro</Text>
        <Text style={estilos.mensajeVacio}>
          No hay productos que coincidan con el filtro seleccionado. Prueba otro filtro o agrega mercancía con la cámara.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={productos}
      keyExtractor={(p) => p.sku}
      renderItem={({ item }) => <FilaInventario producto={item} />}
      scrollEnabled={false}
      accessibilityRole="list"
      accessibilityLabel={`Lista de ${productos.length} productos en inventario`}
    />
  );
}

const estilos = StyleSheet.create({
  estadoVacio: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: espacio.xxl * 2,
    paddingHorizontal: espacio.xl,
    gap: espacio.m,
  },
  tituloVacio: {
    ...type.titleMedium,
    color: color.onSurface,
    textAlign: 'center',
  },
  mensajeVacio: {
    ...type.bodyLarge,
    color: color.onSurfaceVariant,
    textAlign: 'center',
  },
});
