/**
 * MOCK — catálogo y ventas sintéticos en memoria (EXPO_PUBLIC_USE_MOCKS=1).
 * Productos genéricos de abarrotes; ningún dato real. Se reinicia al recargar la app.
 */
import NetInfo from '@react-native-community/netinfo';

import { EXISTENCIA_BAJA } from '@/constants';

import { ErrorApi } from '../cliente';
import type { DetalleVenta, Producto, RespuestaVenta, SolicitudVenta } from '../esquemas';

const catalogo: Producto[] = [
  { sku: 'REF-COLA-600', nombre: 'Refresco de cola 600 ml', precio_unitario: 18, existencia: 12, caducidad: '2027-04-15', categoria: 'Bebidas' },
  { sku: 'PAN-BLANCO-680', nombre: 'Pan blanco grande', precio_unitario: 52, existencia: 3, caducidad: '2026-11-22', categoria: 'Panadería' },
  { sku: 'JABON-BARRA-150', nombre: 'Jabón de barra 150 g', precio_unitario: 22, existencia: 8, caducidad: null, categoria: 'Limpieza' },
  { sku: 'GALL-MARIA-170', nombre: 'Galletas María 170 g', precio_unitario: 16, existencia: 12, caducidad: '2027-02-10', categoria: 'Abarrotes' },
  { sku: 'GALL-CHOC-90', nombre: 'Galletas de chocolate 90 g', precio_unitario: 14, existencia: 3, caducidad: '2027-01-05', categoria: 'Abarrotes' },
  { sku: 'LECHE-ENT-1L', nombre: 'Leche entera 1 L', precio_unitario: 28, existencia: 10, caducidad: '2026-11-25', categoria: 'Lácteos' },
  { sku: 'HUEVO-12', nombre: 'Huevo blanco 12 piezas', precio_unitario: 45, existencia: 6, caducidad: '2026-12-01', categoria: 'Lácteos' },
  { sku: 'TORT-1KG', nombre: 'Tortillas de maíz 1 kg', precio_unitario: 24, existencia: 2, caducidad: '2026-11-21', categoria: 'Panadería' },
  { sku: 'FRIJOL-900', nombre: 'Frijol negro 900 g', precio_unitario: 38, existencia: 7, caducidad: '2027-06-30', categoria: 'Abarrotes' },
  { sku: 'ARROZ-1KG', nombre: 'Arroz 1 kg', precio_unitario: 32, existencia: 9, caducidad: '2027-08-20', categoria: 'Abarrotes' },
  { sku: 'ACEITE-1L', nombre: 'Aceite vegetal 1 L', precio_unitario: 49, existencia: 5, caducidad: '2027-05-14', categoria: 'Abarrotes' },
  { sku: 'AZUCAR-1KG', nombre: 'Azúcar estándar 1 kg', precio_unitario: 34, existencia: 8, caducidad: null, categoria: 'Abarrotes' },
  { sku: 'AGUA-1L', nombre: 'Agua natural 1 L', precio_unitario: 12, existencia: 20, caducidad: '2027-12-01', categoria: 'Bebidas' },
  { sku: 'PAPAS-45', nombre: 'Papas fritas 45 g', precio_unitario: 17, existencia: 15, caducidad: '2027-03-18', categoria: 'Abarrotes' },
  { sku: 'ATUN-140', nombre: 'Atún en agua 140 g', precio_unitario: 26, existencia: 4, caducidad: '2028-01-10', categoria: 'Abarrotes' },
];

const masVendidosSkus = ['REF-COLA-600', 'TORT-1KG', 'HUEVO-12', 'LECHE-ENT-1L', 'PAN-BLANCO-680', 'AGUA-1L'];

const ventas: DetalleVenta[] = [];
const porIdLocal = new Map<string, RespuestaVenta>();

const quitarAcentos = (t: string) =>
  t
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

async function exigirConexion() {
  const estado = await NetInfo.fetch();
  if (estado.isConnected === false || estado.isInternetReachable === false) throw new ErrorApi('sin_conexion');
}

export function mockBuscarProductos(texto: string, limite: number): Producto[] {
  const q = quitarAcentos(texto.trim());
  return catalogo.filter((p) => q === '' || quitarAcentos(p.nombre).includes(q)).slice(0, limite);
}

export function mockMasVendidos(limite: number): Producto[] {
  return masVendidosSkus
    .map((sku) => catalogo.find((p) => p.sku === sku))
    .filter((p): p is Producto => p !== undefined)
    .slice(0, limite);
}

export async function mockRegistrarVenta(solicitud: SolicitudVenta): Promise<RespuestaVenta> {
  await exigirConexion();
  const previa = porIdLocal.get(solicitud.id_local);
  if (previa) return previa; // idempotencia: el reintento no duplica

  for (const item of solicitud.items) {
    if (item.libre || !item.sku) continue;
    const producto = catalogo.find((p) => p.sku === item.sku);
    if (producto && producto.existencia < item.cantidad) {
      throw new ErrorApi('sin_existencia', undefined, { sku: producto.sku, existencia: producto.existencia });
    }
  }

  const existencias: RespuestaVenta['existencias'] = [];
  for (const item of solicitud.items) {
    if (item.libre || !item.sku) continue;
    const producto = catalogo.find((p) => p.sku === item.sku);
    if (!producto) continue;
    producto.existencia -= item.cantidad;
    existencias.push({
      sku: producto.sku,
      nombre: producto.nombre,
      quedan: producto.existencia,
      bajo: producto.existencia <= EXISTENCIA_BAJA,
    });
  }

  const numero = ventas.length + 42;
  const total = solicitud.items.reduce((s, i) => s + i.cantidad * i.precio_unitario, 0);
  const respuesta: RespuestaVenta = {
    venta_id: `mock-v-${numero}`,
    folio: `V-${String(numero).padStart(4, '0')}`,
    total,
    creada_en: new Date().toISOString(),
    existencias,
  };
  ventas.unshift({
    venta_id: respuesta.venta_id,
    folio: respuesta.folio,
    total,
    creada_en: respuesta.creada_en,
    metodo_pago: solicitud.metodo_pago,
    recibido: solicitud.recibido,
    items: solicitud.items,
  });
  porIdLocal.set(solicitud.id_local, respuesta);
  return respuesta;
}

export async function mockVentasDeHoy(): Promise<DetalleVenta[]> {
  await exigirConexion();
  return [...ventas];
}

export async function mockDetalleVenta(id: string): Promise<DetalleVenta> {
  await exigirConexion();
  const venta = ventas.find((v) => v.venta_id === id);
  if (!venta) throw new ErrorApi('datos_faltantes', 'No encontramos esta venta.');
  return venta;
}
