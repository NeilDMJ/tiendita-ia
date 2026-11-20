import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRef, type ComponentRef } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';

import { Tocable } from '@/components/tocable';
import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';

export interface BarraBusquedaProps {
  valor: string;
  onCambiar: (texto: string) => void;
  placeholder?: string;
}

/**
 * Barra de búsqueda M3 (00-sistema §9.2 adaptada) para filtrar productos por nombre.
 * Campo outlined con icono de lupa y botón de limpiar cuando hay texto.
 * Nielsen #7: acelerador para el tendero que sabe qué busca.
 */
export function BarraBusqueda({ valor, onCambiar, placeholder = 'Buscar producto…' }: BarraBusquedaProps) {
  const refInput = useRef<ComponentRef<typeof TextInput>>(null);

  return (
    <View style={estilos.contenedor}>
      <MaterialCommunityIcons
        name="magnify"
        size={iconos.linea}
        color={color.onSurfaceVariant}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <TextInput
        ref={refInput}
        value={valor}
        onChangeText={onCambiar}
        placeholder={placeholder}
        placeholderTextColor={color.onSurfaceVariant}
        allowFontScaling
        accessibilityLabel="Buscar producto en inventario"
        accessibilityHint="Escribe el nombre del producto para filtrar la lista"
        style={estilos.input}
        returnKeyType="search"
        autoCorrect={false}
      />
      {valor.length > 0 ? (
        <Tocable
          onPress={() => {
            onCambiar('');
            refInput.current?.focus();
          }}
          colorContenido={color.onSurfaceVariant}
          radio={shape.full}
          rippleSinLimite
          accessibilityRole="button"
          accessibilityLabel="Limpiar búsqueda"
          style={estilos.botonLimpiar}
        >
          <MaterialCommunityIcons
            name="close"
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
        </Tocable>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    borderWidth: bordes.fino,
    borderColor: color.outline,
    borderRadius: shape.extraLarge,
    backgroundColor: color.surfaceContainerLowest,
  },
  input: {
    ...type.bodyLargePlus,
    color: color.onSurface,
    flex: 1,
    minHeight: tactil.principal - bordes.grueso * 2,
    paddingVertical: espacio.s,
  },
  botonLimpiar: {
    width: tactil.minimo,
    height: tactil.minimo,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: shape.full,
    marginRight: -espacio.s,
  },
});
