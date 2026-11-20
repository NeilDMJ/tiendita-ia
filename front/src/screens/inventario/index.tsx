import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { buscarProductos } from '@/api/negocio';
import { FabExtendido, RESERVA_FAB } from '@/components/fab-extendido';
import { EXISTENCIA_BAJA } from '@/constants';
import { useConexion } from '@/hooks/use-conexion';
import { color, espacio, type } from '@/theme';

import { BarraBusqueda } from './barra-busqueda';
import { FiltrosInventario } from './filtros-inventario';
import { ListaProductos } from './lista-productos';
import { ResumenInventarioCard } from './resumen-inventario';
import type { FiltroInventario, ProductoInventario, ResumenInventario } from './tipos';

/** Días de anticipación para alertar de caducidad. */
const DIAS_ALERTA_CADUCIDAD = 7;

/** Calcula los días restantes para la caducidad desde hoy. */
function diasHastaCaducidad(fechaIso: string): number {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const fecha = new Date(fechaIso + 'T00:00:00');
  return Math.ceil((fecha.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
}

/** Quitar acentos para búsqueda tolerante. */
const sinAcentos = (t: string) =>
  t
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

/**
 * Pantalla de Inventario — App del Tendero (Material Design 3).
 *
 * Heurísticas de Nielsen aplicadas:
 * - #1 Visibilidad del estado: resumen con métricas + alertas actualizadas.
 * - #2 Correspondencia: palabras de tienda ("pz", "Agotado", "Poco stock").
 * - #3 Control del usuario: filtros reversibles, búsqueda con limpiar.
 * - #4 Consistencia: mismos roles M3 y tokens que Inicio y Cobrar.
 * - #5 Prevención de errores: filtros con conteo para evitar selecciones vacías.
 * - #6 Reconocimiento: toda info visible en la fila, sin navegar.
 * - #7 Flexibilidad: búsqueda como acelerador para tenderos avanzados.
 * - #8 Diseño minimalista: una sola tarjeta de resumen + lista limpia.
 * - #9 Recuperación: estados vacíos con guía ("limpia la búsqueda", "prueba otro filtro").
 * - #10 Ayuda: chips y FAB con accessibilityHint descriptivos.
 *
 * Arquitectura: mismo patrón que PantallaInicio — consume buscarProductos()
 * que respeta USAR_MOCKS. Con mocks funciona con el catálogo de 15 productos;
 * con backend real hace GET /productos.
 */
export function PantallaInventario() {
  const conectado = useConexion();
  const sinConexion = conectado === false;

  const [textoBusqueda, setTextoBusqueda] = useState('');
  const [filtroActivo, setFiltroActivo] = useState<FiltroInventario>('todos');
  const [refrescando, setRefrescando] = useState(false);

  // Consulta del catálogo completo (mismo endpoint que Inicio: buscarProductos)
  const consultaCatalogo = useQuery({
    queryKey: ['productos', 'inventario-completo'],
    queryFn: () => buscarProductos('', 100),
    enabled: !sinConexion,
  });

  // Enriquecer productos con señales de estado
  const productosEnriquecidos: ProductoInventario[] = useMemo(() => {
    const datos = consultaCatalogo.data ?? [];
    return datos.map((p) => {
      const dias = p.caducidad ? diasHastaCaducidad(p.caducidad) : null;
      return {
        ...p,
        stockBajo: p.existencia > 0 && p.existencia <= EXISTENCIA_BAJA,
        agotado: p.existencia <= 0,
        porCaducar: dias !== null && dias >= 0 && dias <= DIAS_ALERTA_CADUCIDAD,
        caducado: dias !== null && dias < 0,
        diasParaCaducar: dias,
      };
    });
  }, [consultaCatalogo.data]);

  // Filtrar por texto de búsqueda (tolerante a acentos)
  const productosFiltradosTexto = useMemo(() => {
    const q = sinAcentos(textoBusqueda.trim());
    if (q === '') return productosEnriquecidos;
    return productosEnriquecidos.filter(
      (p) => sinAcentos(p.nombre).includes(q) || (p.categoria && sinAcentos(p.categoria).includes(q)),
    );
  }, [productosEnriquecidos, textoBusqueda]);

  // Conteos para los chips (calculados ANTES de aplicar filtro activo, sobre la búsqueda)
  const conteos = useMemo(
    () => ({
      todos: productosFiltradosTexto.length,
      poco: productosFiltradosTexto.filter((p) => p.stockBajo).length,
      agotado: productosFiltradosTexto.filter((p) => p.agotado).length,
      'por-caducar': productosFiltradosTexto.filter((p) => p.porCaducar || p.caducado).length,
    }),
    [productosFiltradosTexto],
  );

  // Aplicar filtro de chip activo
  const productosFinal = useMemo(() => {
    switch (filtroActivo) {
      case 'poco':
        return productosFiltradosTexto.filter((p) => p.stockBajo);
      case 'agotado':
        return productosFiltradosTexto.filter((p) => p.agotado);
      case 'por-caducar':
        return productosFiltradosTexto.filter((p) => p.porCaducar || p.caducado);
      default:
        return productosFiltradosTexto;
    }
  }, [productosFiltradosTexto, filtroActivo]);

  // Resumen del inventario
  const resumen: ResumenInventario = useMemo(
    () => ({
      totalProductos: productosEnriquecidos.length,
      totalPiezas: productosEnriquecidos.reduce((s, p) => s + Math.max(0, p.existencia), 0),
      productosConStockBajo: productosEnriquecidos.filter((p) => p.stockBajo).length,
      productosAgotados: productosEnriquecidos.filter((p) => p.agotado).length,
      productosPorCaducar: productosEnriquecidos.filter((p) => p.porCaducar).length,
      productosCaducados: productosEnriquecidos.filter((p) => p.caducado).length,
      valorEstimado: productosEnriquecidos.reduce(
        (s, p) => s + p.precio_unitario * Math.max(0, p.existencia),
        0,
      ),
    }),
    [productosEnriquecidos],
  );

  const alRefrescar = async () => {
    setRefrescando(true);
    await consultaCatalogo.refetch();
    setRefrescando(false);
  };

  const agregarMercancia = () => router.push('/camara?modo=alta' as any);

  return (
    <SafeAreaView edges={['top']} style={estilos.pantalla}>
      <ScrollView
        style={estilos.scroll}
        contentContainerStyle={estilos.contenido}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={alRefrescar}
            tintColor={color.primary}
            colors={[color.primary]}
          />
        }
      >
        {/* Encabezado */}
        <Text style={estilos.tituloSeccion} accessibilityRole="header">
          Inventario de tu tienda
        </Text>

        {/* 1. Tarjeta resumen */}
        <ResumenInventarioCard resumen={resumen} />

        {/* 2. Barra de búsqueda */}
        <BarraBusqueda valor={textoBusqueda} onCambiar={setTextoBusqueda} />

        {/* 3. Chips de filtro */}
        <FiltrosInventario
          filtroActivo={filtroActivo}
          onCambiarFiltro={setFiltroActivo}
          conteos={conteos}
        />

        {/* 4. Lista de productos */}
        <ListaProductos
          productos={productosFinal}
          textoBusqueda={textoBusqueda}
          cargando={consultaCatalogo.isPending}
        />

        {/* Espacio para que el FAB no tape la última fila */}
        <View style={{ height: RESERVA_FAB }} />
      </ScrollView>

      {/* M3 Extended FAB — Atajo para agregar mercancía con cámara */}
      <FabExtendido
        texto="Agregar mercancía"
        icono="package-variant-plus"
        onPress={agregarMercancia}
        accessibilityHint="Abre la cámara para registrar mercancía nueva en el inventario"
        testID="fab-agregar-mercancia"
      />
    </SafeAreaView>
  );
}

export default PantallaInventario;

const estilos = StyleSheet.create({
  pantalla: {
    flex: 1,
    backgroundColor: color.surface,
  },
  scroll: {
    flex: 1,
  },
  contenido: {
    padding: espacio.l,
    gap: espacio.l,
  },
  tituloSeccion: {
    ...type.headlineSmall,
    color: color.onSurface,
  },
});
