import { z } from 'zod';

import { pedir, pedirJson, USAR_MOCKS } from './cliente';
import { DetalleVenta, Producto, RespuestaVenta, type SolicitudVenta } from './esquemas';
import { esperar } from './mocks';
import {
  mockBuscarProductos,
  mockDetalleVenta,
  mockMasVendidos,
  mockRegistrarVenta,
  mockVentasDeHoy,
} from './mocks/negocio';

export async function buscarProductos(texto: string, limite = 10): Promise<Producto[]> {
  if (USAR_MOCKS) return esperar(300).then(() => mockBuscarProductos(texto, limite));
  const q = encodeURIComponent(texto);
  return pedir(`/productos?q=${q}&limite=${limite}`, z.array(Producto));
}

export async function masVendidos(limite = 6): Promise<Producto[]> {
  if (USAR_MOCKS) return esperar(200).then(() => mockMasVendidos(limite));
  return pedir(`/productos/mas-vendidos?limite=${limite}`, z.array(Producto));
}

/** POST /ventas — `id_local` hace que un reintento nunca duplique la venta. */
export async function registrarVenta(solicitud: SolicitudVenta): Promise<RespuestaVenta> {
  if (USAR_MOCKS) return esperar(900).then(() => mockRegistrarVenta(solicitud));
  return pedirJson('/ventas', RespuestaVenta, solicitud);
}

export async function ventasDeHoy(): Promise<DetalleVenta[]> {
  if (USAR_MOCKS) return esperar(400).then(() => mockVentasDeHoy());
  return pedir('/ventas?dia=hoy', z.array(DetalleVenta));
}

export async function detalleVenta(id: string): Promise<DetalleVenta> {
  if (USAR_MOCKS) return esperar(300).then(() => mockDetalleVenta(id));
  return pedir(`/ventas/${encodeURIComponent(id)}`, DetalleVenta);
}
