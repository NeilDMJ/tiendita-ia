import { StyleSheet, Text, View } from 'react-native';

import { parsearDatosAccion, RUTAS_DESTINO, totalVenta, ventaCompleta } from '@/api/acciones-asistente';
import type { PantallaDestino, RolAsistente } from '@/api/esquemas';
import { Boton } from '@/components/boton';
import { TarjetaAccion, type TarjetaAccionProps } from '@/components/tarjeta-accion';
import type { NombreIcono } from '@/constants';
import type { AccionChat } from '@/estado/chat';
import { color, espacio, type } from '@/theme';
import { formatoMoneda } from '@/utils/formato-moneda';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** 'AAAA-MM-DD' → '28 nov 2026' (sin zona horaria: es una fecha de calendario). */
function fechaCorta(iso: string | null): string {
  if (!iso) return 'Sin fecha';
  const [a, m, d] = iso.split('-').map(Number);
  if (!a || !m || !d) return iso;
  return `${d} ${MESES[m - 1]} ${a}`;
}

const ICONO_DESTINO: Record<PantallaDestino, NombreIcono> = {
  cobrar: 'cash-register',
  camara_cobro: 'camera',
  camara_alta: 'camera',
  camara_ticket: 'camera',
  inventario: 'package-variant-closed',
  historial: 'receipt',
  pago: 'bank-transfer',
  promociones: 'bullhorn-outline',
};

export interface TarjetaPropuestaProps {
  accion: AccionChat;
  rol: RolAsistente;
  conectado: boolean;
  /** Fila actual del carrito (solo `modificar_item`), para el renglón "Antes". */
  antes?: { nombre: string; precio: number | null } | null;
  onConfirmar: () => void;
  onRechazar: () => void;
  /** "Revisar y editar" (venta → carrito; modificar_item con error → editar la fila). */
  onEditar?: () => void;
  /** Propuesta ilegible → hacerlo a mano. */
  onHacerAMano: () => void;
  onAbrir: (destino: PantallaDestino) => void;
  onVerResultado?: () => void;
  /** Tarjeta dentro de la hoja de Caja (contorno visible sobre `surfaceContainerLow`). */
  enHoja?: boolean;
}

/**
 * Adaptador `AccionAsistente` → `TarjetaAccion` (02-asistente §3). `abrir_pantalla` NO es tarjeta:
 * es un botón tonal bajo la burbuja (navega, no cambia datos).
 */
export function TarjetaPropuesta({
  accion,
  rol,
  conectado,
  antes,
  onConfirmar,
  onRechazar,
  onEditar,
  onHacerAMano,
  onAbrir,
  onVerResultado,
  enHoja,
}: TarjetaPropuestaProps) {
  const parseado = parsearDatosAccion(accion);

  if (accion.tipo === 'abrir_pantalla') {
    if (parseado?.tipo !== 'abrir_pantalla') return null;
    const destino = parseado.datos.pantalla;
    const disponible = RUTAS_DESTINO[destino] !== null;
    return (
      <View style={estilos.abrir}>
        <Boton
          texto={accion.titulo}
          icono={ICONO_DESTINO[destino]}
          variante="tonal"
          anchoCompleto={false}
          deshabilitado={!disponible}
          motivoDeshabilitado="Disponible pronto"
          onPress={() => onAbrir(destino)}
        />
        {disponible ? null : <Text style={estilos.pronto}>Disponible pronto</Text>}
      </View>
    );
  }

  const comunes: Pick<
    TarjetaAccionProps,
    'rol' | 'titulo' | 'estado' | 'resultado' | 'motivoCaducada' | 'onConfirmar' | 'onRechazar' | 'onVerResultado' | 'enHoja'
  > = {
    enHoja,
    rol,
    titulo: accion.titulo,
    estado: accion.estado,
    resultado: accion.resultado,
    motivoCaducada: accion.motivo,
    onConfirmar,
    onRechazar,
    onVerResultado,
  };

  if (!parseado || accion.ilegible) {
    return (
      <TarjetaAccion
        {...comunes}
        estado="error"
        textoConfirmar="Confirmar"
        tituloError="No pudimos leer esta propuesta."
        mensajeError="Puedes hacerlo tú directo."
        accionError={{ texto: 'Hacerlo a mano', onPress: onHacerAMano }}
      />
    );
  }

  switch (parseado.tipo) {
    case 'confirmar_venta': {
      const completa = ventaCompleta(parseado.datos);
      const total = totalVenta(parseado.datos);
      return (
        <TarjetaAccion
          {...comunes}
          resumen={parseado.datos.items.map((i) => ({
            izquierda: `${i.cantidad} × ${i.nombre}`,
            derecha:
              i.sku === null
                ? 'Elige producto'
                : i.precio_unitario === null
                  ? 'Falta precio'
                  : formatoMoneda(i.cantidad * i.precio_unitario),
            secundario: i.sku === null || i.precio_unitario === null,
          }))}
          total={completa ? total : undefined}
          soloRevisar={!completa}
          textoConfirmar={`Confirmar cobro ${formatoMoneda(total)}`}
          textoCargando="Cobrando…"
          tituloError="No se pudo cobrar"
          mensajeError={accion.error ?? 'Tu venta sigue aquí.'}
          onEditar={onEditar}
        />
      );
    }
    case 'confirmar_alta': {
      const d = parseado.datos;
      return (
        <TarjetaAccion
          {...comunes}
          resumen={[
            { izquierda: 'Cantidad', derecha: `${d.cantidad} pz` },
            { izquierda: 'Precio de venta', derecha: d.precio_venta === null ? 'Sin precio' : formatoMoneda(d.precio_venta) },
            { izquierda: 'Caduca', derecha: fechaCorta(d.caducidad) },
          ]}
          textoConfirmar="Confirmar alta"
          textoCargando="Guardando…"
          motivoNoDisponible={conectado ? undefined : 'Necesita internet'}
          tituloError="No se pudo guardar"
          mensajeError={accion.error ?? 'Intenta de nuevo en un momento.'}
          // "Revisar y editar" → hoja mínima de edición (HojaEditarAlta) hasta que exista revision/alta (Fase 4).
          onEditar={onEditar}
        />
      );
    }
    case 'aprobar_promo': {
      const d = parseado.datos;
      return (
        <TarjetaAccion
          {...comunes}
          simulacion={d.simulacion}
          resumen={[
            { izquierda: d.copy },
            { izquierda: 'Precio de oferta', derecha: formatoMoneda(d.precio_promo) },
            { izquierda: 'Hasta', derecha: fechaCorta(d.vigente_hasta) },
          ]}
          textoConfirmar="Aprobar promoción"
          textoCargando="Aprobando…"
          motivoNoDisponible={conectado ? undefined : 'Necesita internet'}
          tituloError="No se pudo aprobar"
          mensajeError={accion.error ?? 'Intenta de nuevo en un momento.'}
        />
      );
    }
    case 'aprobar_enjambre': {
      const d = parseado.datos;
      const filas = [d.descripcion, d.motivo, d.detalle]
        .filter((t): t is string => !!t)
        .map((t) => ({ izquierda: t }));
      return (
        <TarjetaAccion
          {...comunes}
          resumen={filas.length > 0 ? filas : [{ izquierda: 'Necesito tu aprobación para continuar.' }]}
          textoConfirmar="Aprobar"
          textoCargando="Aprobando…"
          motivoNoDisponible={conectado ? undefined : 'Necesita internet'}
          tituloError="No se pudo completar"
          mensajeError={accion.error ?? 'Intenta de nuevo en un momento.'}
        />
      );
    }
    case 'modificar_item': {
      const c = parseado.datos.cambios;
      const nombreAntes = antes?.nombre ?? parseado.datos.nombre_actual;
      const precioAntes = antes?.precio ?? null;
      const nombreAhora = c.nombre ?? nombreAntes;
      const precioAhora = c.precio_unitario ?? precioAntes;
      const incompleta = c.sku !== undefined && (c.nombre === undefined || c.precio_unitario === undefined);
      const filaAhora = [nombreAhora, precioAhora === null ? '— —' : formatoMoneda(precioAhora)];
      if (c.cantidad !== undefined) filaAhora.push(`${c.cantidad} pz`);
      return (
        <TarjetaAccion
          {...comunes}
          resumen={[
            {
              izquierda: 'Antes',
              derecha: `${nombreAntes} · ${precioAntes === null ? '— —' : formatoMoneda(precioAntes)}`,
              secundario: true,
            },
            { izquierda: 'Ahora', derecha: filaAhora.join(' · '), destacado: true },
          ]}
          textoConfirmar="Aplicar a la venta"
          textoCargando="Aplicando…"
          soloRevisar={incompleta}
          tituloError="No se pudo aplicar"
          mensajeError={accion.error ?? 'Revisa el producto a mano.'}
          accionError={onEditar ? { texto: 'Revisar y editar', onPress: onEditar } : undefined}
          onEditar={incompleta ? onEditar : undefined}
        />
      );
    }
  }
}

const estilos = StyleSheet.create({
  abrir: { gap: espacio.xs, alignItems: 'flex-start' },
  pronto: { ...type.bodyLarge, color: color.onSurfaceVariant },
});
