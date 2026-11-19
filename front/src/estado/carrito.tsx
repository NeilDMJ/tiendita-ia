/**
 * Estado de la venta en curso (carrito editable) + última venta registrada.
 * El carrito se persiste como borrador: si el tendero sale sin cobrar, lo retoma en "Cobrar".
 */
import { createContext, use, useEffect, useState, type ReactNode } from 'react';

import type { RespuestaPosCheckout, RespuestaVenta, SolicitudVenta } from '@/api/esquemas';
import { desdeDetectado, type ItemEditable } from '@/utils/carrito';

import { guardarJson, leerJson } from './almacen';

const CLAVE_BORRADOR = 'carrito-borrador';

export type DatosCarrito = {
  items: ItemEditable[];
  imagenId: string | null;
  imagenUri: string | null;
  /** Date.now() al abrir la cámara, para el indicador "Antes vs. ahora". */
  inicio: number | null;
};

export type UltimaVenta = {
  /** venta_id real o `local-<id_local>` si quedó en cola */
  id: string;
  solicitud: SolicitudVenta;
  total: number;
  respuesta: RespuestaVenta | null;
  folioLocal?: string;
  creadaEn: string;
};

const VACIO: DatosCarrito = { items: [], imagenId: null, imagenUri: null, inicio: null };

type ContextoCarrito = {
  cargado: boolean;
  carrito: DatosCarrito;
  iniciarCronometro: () => void;
  cargarDeFoto: (respuesta: RespuestaPosCheckout, uri: string) => void;
  cargarItems: (items: ItemEditable[]) => void;
  actualizarItem: (clave: string, cambios: Partial<ItemEditable>) => void;
  quitarItem: (clave: string) => { item: ItemEditable; indice: number } | null;
  restaurarItem: (item: ItemEditable, indice: number) => void;
  agregarItem: (item: ItemEditable) => void;
  vaciar: () => void;
  ultimaVenta: UltimaVenta | null;
  setUltimaVenta: (v: UltimaVenta | null) => void;
};

const Contexto = createContext<ContextoCarrito | null>(null);

export function ProveedorCarrito({ children }: { children: ReactNode }) {
  const [cargado, setCargado] = useState(false);
  const [carrito, setCarrito] = useState<DatosCarrito>(VACIO);
  const [ultimaVenta, setUltimaVenta] = useState<UltimaVenta | null>(null);

  useEffect(() => {
    leerJson<DatosCarrito>(CLAVE_BORRADOR, VACIO).then((d) => {
      setCarrito((actual) => (actual.items.length > 0 ? actual : d));
      setCargado(true);
    });
  }, []);

  useEffect(() => {
    if (cargado) guardarJson(CLAVE_BORRADOR, carrito);
  }, [carrito, cargado]);

  const valor: ContextoCarrito = {
    cargado,
    carrito,
    iniciarCronometro: () => setCarrito((c) => (c.items.length > 0 && c.inicio ? c : { ...c, inicio: Date.now() })),
    cargarDeFoto: (respuesta, uri) =>
      setCarrito((c) => ({
        items: respuesta.items.map(desdeDetectado),
        imagenId: respuesta.imagen_id,
        imagenUri: uri,
        inicio: c.inicio ?? Date.now(),
      })),
    cargarItems: (items) => setCarrito({ items, imagenId: null, imagenUri: null, inicio: Date.now() }),
    actualizarItem: (clave, cambios) =>
      setCarrito((c) => ({ ...c, items: c.items.map((i) => (i.clave === clave ? { ...i, ...cambios } : i)) })),
    quitarItem: (clave) => {
      const indice = carrito.items.findIndex((i) => i.clave === clave);
      if (indice < 0) return null;
      const item = carrito.items[indice];
      setCarrito((c) => ({ ...c, items: c.items.filter((i) => i.clave !== clave) }));
      return { item, indice };
    },
    restaurarItem: (item, indice) =>
      setCarrito((c) => {
        const items = [...c.items];
        items.splice(Math.min(indice, items.length), 0, item);
        return { ...c, items };
      }),
    agregarItem: (item) =>
      setCarrito((c) => ({ ...c, items: [...c.items, item], inicio: c.inicio ?? Date.now() })),
    vaciar: () => setCarrito(VACIO),
    ultimaVenta,
    setUltimaVenta,
  };

  return <Contexto value={valor}>{children}</Contexto>;
}

export function useCarrito() {
  const ctx = use(Contexto);
  if (!ctx) throw new Error('useCarrito debe usarse dentro de ProveedorCarrito');
  return ctx;
}
