/**
 * Ejecuta las propuestas del asistente SOLO después de que el tendero toca Confirmar (02-asistente §3).
 * Llama a las funciones de negocio existentes (`registrarVenta`, `registrarAlta`, `aprobarPromocion`).
 */
import { useQueryClient } from '@tanstack/react-query';
import { router, type Href } from 'expo-router';
import { useRef, useState } from 'react';

import { aprobarPromocion, parsearDatosAccion, RUTAS_DESTINO, solicitudDesdeChat, totalVenta } from '@/api/acciones-asistente';
import { reportarResultadoAccion } from '@/api/asistente';
import { esErrorApi } from '@/api/cliente';
import { ConflictoExistencia, type DatosConfirmarVenta, type PantallaDestino, type SolicitudVenta } from '@/api/esquemas';
import { registrarAlta, registrarVenta } from '@/api/negocio';
import { useCarrito } from '@/estado/carrito';
import type { AccionChat } from '@/estado/chat';
import { encolarVenta, PREFIJO_LOCAL } from '@/estado/cola-ventas';
import type { ItemEditable } from '@/utils/carrito';
import { crearIdLocal } from '@/utils/id';

import type { Chat } from './use-chat';
import { useConexion } from './use-conexion';

const MOTIVO_A_REVISION = 'La pasaste a Revisar la venta.';

function aItemsEditables(datos: DatosConfirmarVenta): ItemEditable[] {
  return datos.items.map((i) => ({
    clave: crearIdLocal(),
    sku: i.sku,
    nombre: i.nombre,
    cantidad: i.cantidad,
    precio_unitario: i.precio_unitario,
    confianza: 1,
    origen: 'manual',
    revisadoPorUsuario: false,
  }));
}

export function useAccionesAsistente(chat: Pick<Chat, 'actualizarAccion'>) {
  const { carrito, cargarItems } = useCarrito();
  const conectado = useConexion();
  const clienteQuery = useQueryClient();
  const [reemplazo, setReemplazo] = useState<{ idMensaje: string; accion: AccionChat; datos: DatosConfirmarVenta } | null>(
    null,
  );

  const actualizar = chat.actualizarAccion;
  /** Candado contra doble toque: ids de acciones que se están ejecutando (el estado tarda un render). */
  const enCurso = useRef<Set<string>>(new Set());

  async function refrescar() {
    await Promise.all([
      clienteQuery.invalidateQueries({ queryKey: ['ventas'] }),
      clienteQuery.invalidateQueries({ queryKey: ['kpis'] }),
      clienteQuery.invalidateQueries({ queryKey: ['inventario'] }),
      clienteQuery.invalidateQueries({ queryKey: ['productos'] }),
    ]);
  }

  async function guardarEnTelefono(idMensaje: string, accion: AccionChat, solicitud: SolicitudVenta, total: number) {
    await encolarVenta(solicitud, total);
    await clienteQuery.invalidateQueries({ queryKey: ['ventas'] });
    actualizar(idMensaje, accion.id, {
      estado: 'hecha',
      resultado: 'Venta guardada · Pendiente de enviar',
      idVenta: `${PREFIJO_LOCAL}${solicitud.id_local}`,
    });
  }

  /** `datosEditados`: lo que el tendero corrigió en "Revisar y editar" (alta). */
  async function confirmar(idMensaje: string, accion: AccionChat, datosEditados?: unknown) {
    const p = parsearDatosAccion(datosEditados === undefined ? accion : { ...accion, datos: datosEditados });
    if (!p || accion.estado === 'confirmando' || enCurso.current.has(accion.id)) return;
    enCurso.current.add(accion.id);
    actualizar(idMensaje, accion.id, {
      estado: 'confirmando',
      error: undefined,
      ...(datosEditados === undefined ? {} : { datos: datosEditados }),
    });
    try {
      if (p.tipo === 'confirmar_venta') {
        const solicitud = solicitudDesdeChat(accion.id, p.datos);
        const total = totalVenta(p.datos);
        // Sin internet la venta SÍ se puede confirmar: va a la cola (01-cobrar).
        if (conectado === false) {
          await guardarEnTelefono(idMensaje, accion, solicitud, total);
        } else {
          try {
            const r = await registrarVenta(solicitud);
            await refrescar();
            actualizar(idMensaje, accion.id, {
              estado: 'hecha',
              resultado: `Venta registrada · Folio ${r.folio}`,
              idVenta: r.venta_id,
            });
          } catch (e) {
            if (esErrorApi(e) && e.tipo === 'sin_conexion') await guardarEnTelefono(idMensaje, accion, solicitud, total);
            else throw e;
          }
        }
      } else if (p.tipo === 'confirmar_alta') {
        const r = await registrarAlta(p.datos);
        await refrescar();
        actualizar(idMensaje, accion.id, { estado: 'hecha', resultado: `Agregado a tu inventario · Quedan ${r.quedan} pz` });
      } else if (p.tipo === 'aprobar_promo') {
        await aprobarPromocion(p.datos.promo_id);
        actualizar(idMensaje, accion.id, {
          estado: 'hecha',
          resultado: p.datos.simulacion ? 'Promoción aprobada · Simulación: no se publicó en redes' : 'Promoción aprobada',
        });
      } else {
        return;
      }
      reportarResultadoAccion(accion.id, 'hecha');
    } catch (e) {
      let error = 'No se pudo completar. Tus datos siguen aquí.';
      if (esErrorApi(e)) {
        if (e.tipo === 'sin_existencia') {
          const c = ConflictoExistencia.safeParse(e.detalle);
          error = c.success
            ? `No hay suficientes piezas: solo quedan ${c.data.existencia}.`
            : 'No hay suficientes piezas en existencia.';
        } else if (p.tipo === 'confirmar_venta') {
          error = 'No se pudo cobrar. Tu venta sigue aquí.';
        } else {
          error = e.mensaje;
        }
      }
      actualizar(idMensaje, accion.id, { estado: 'error', error });
    } finally {
      enCurso.current.delete(accion.id);
    }
  }

  function rechazar(idMensaje: string, accion: AccionChat) {
    actualizar(idMensaje, accion.id, { estado: 'rechazada' });
    reportarResultadoAccion(accion.id, 'rechazada');
  }

  function pasarARevision(idMensaje: string, accion: AccionChat, datos: DatosConfirmarVenta) {
    cargarItems(aItemsEditables(datos));
    // Caduca para que no se cobre dos veces (aquí y en la revisión).
    actualizar(idMensaje, accion.id, { estado: 'caducada', motivo: MOTIVO_A_REVISION });
    router.push('/revision/cobro');
  }

  /** "Revisar y editar" de confirmar_venta: carga los productos en la revisión del cobro. */
  function revisar(idMensaje: string, accion: AccionChat) {
    const p = parsearDatosAccion(accion);
    if (p?.tipo !== 'confirmar_venta') return;
    if (carrito.items.length > 0) {
      setReemplazo({ idMensaje, accion, datos: p.datos });
      return;
    }
    pasarARevision(idMensaje, accion, p.datos);
  }

  function abrir(destino: PantallaDestino) {
    const ruta = RUTAS_DESTINO[destino];
    if (ruta) router.push(ruta);
  }

  function hacerAMano(accion: AccionChat) {
    const ruta: Href =
      accion.tipo === 'confirmar_venta'
        ? '/cobrar'
        : accion.tipo === 'confirmar_alta'
          ? '/camara?modo=alta'
          : '/inventario';
    router.push(ruta);
  }

  function verComprobante(idVenta: string) {
    router.push(`/venta/${idVenta}`);
  }

  return {
    conectado: conectado !== false,
    confirmar,
    rechazar,
    revisar,
    abrir,
    hacerAMano,
    verComprobante,
    /** Dialogo "Ya tienes una venta sin terminar". */
    dialogoBorrador: {
      visible: reemplazo !== null,
      reemplazar: () => {
        const r = reemplazo;
        setReemplazo(null);
        if (r) pasarARevision(r.idMensaje, r.accion, r.datos);
      },
      mantener: () => setReemplazo(null),
    },
  };
}
