import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { esErrorApi } from '@/api/cliente';
import { registrarVenta } from '@/api/negocio';
import { leerCola, marcarEnviada } from '@/estado/cola-ventas';

import { useConexion } from './use-conexion';

/** Al reconectarse, envía las ventas guardadas en el teléfono y refresca las listas. */
export function useSincronizarCola() {
  const conectado = useConexion();
  const clienteQuery = useQueryClient();
  const enCurso = useRef(false);

  useEffect(() => {
    if (conectado !== true || enCurso.current) return;
    enCurso.current = true;
    (async () => {
      const cola = await leerCola();
      let enviadas = 0;
      for (const pendiente of [...cola].reverse()) {
        try {
          // La venta ya ocurrió sin conexión: el back no la rechaza por existencia (§4.2 del plan de BD).
          const r = await registrarVenta({
            ...pendiente.solicitud,
            ocurrida_en: pendiente.solicitud.ocurrida_en ?? pendiente.creada_en,
            fuera_de_linea: true,
          });
          await marcarEnviada(pendiente.solicitud.id_local, r.venta_id);
          enviadas += 1;
        } catch (e) {
          if (esErrorApi(e) && (e.tipo === 'sin_conexion' || e.tipo === 'tiempo_agotado')) break;
          // Otros errores (p. ej. sin existencia) se quedan en la cola para revisarse a mano.
        }
      }
      if (enviadas > 0 || cola.length > 0) {
        await clienteQuery.invalidateQueries({ queryKey: ['ventas'] });
        await clienteQuery.invalidateQueries({ queryKey: ['inventario'] });
        await clienteQuery.invalidateQueries({ queryKey: ['kpis'] });
      }
    })().finally(() => {
      enCurso.current = false;
    });
  }, [conectado, clienteQuery]);
}
