import { ScrollView, StyleSheet, View } from 'react-native';

import { ChipFiltro } from '@/components/chip-filtro';
import { espacio } from '@/theme';

import type { FiltroInventario } from './tipos';

const FILTROS: { id: FiltroInventario; texto: string; hint: string }[] = [
  { id: 'todos', texto: 'Todos', hint: 'Muestra todos los productos del inventario' },
  { id: 'poco', texto: 'Poco stock', hint: 'Solo productos con pocas piezas en mostrador' },
  { id: 'agotado', texto: 'Agotados', hint: 'Solo productos sin existencia' },
  { id: 'por-caducar', texto: 'Por caducar', hint: 'Productos que caducan esta semana o ya caducaron' },
];

export interface FiltrosInventarioProps {
  filtroActivo: FiltroInventario;
  onCambiarFiltro: (filtro: FiltroInventario) => void;
  conteos: Record<FiltroInventario, number>;
}

/**
 * Fila horizontal de M3 Filter chips (00-sistema §9.6).
 * Cada chip muestra el conteo entre paréntesis para dar retroalimentación inmediata (Nielsen #1).
 * Los chips son mutuamente excluyentes: `rol="radio"` dentro de un `radiogroup`.
 */
export function FiltrosInventario({ filtroActivo, onCambiarFiltro, conteos }: FiltrosInventarioProps) {
  return (
    <View accessibilityRole="radiogroup" accessibilityLabel="Filtrar productos por estado">
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={estilos.contenedor}
      >
        {FILTROS.map((f) => (
          <ChipFiltro
            key={f.id}
            texto={`${f.texto} (${conteos[f.id]})`}
            seleccionado={filtroActivo === f.id}
            rol="radio"
            onPress={() => onCambiarFiltro(f.id)}
            accessibilityHint={f.hint}
          />
        ))}
      </ScrollView>
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: {
    flexDirection: 'row',
    gap: espacio.s,
    paddingVertical: espacio.xs,
  },
});
