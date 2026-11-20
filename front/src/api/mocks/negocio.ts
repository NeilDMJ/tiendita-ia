/**
 * MOCK — catálogo y ventas sintéticos en memoria (EXPO_PUBLIC_USE_MOCKS=1).
 * Productos genéricos de abarrotes; ningún dato real. Se reinicia al recargar la app.
 */
import NetInfo from '@react-native-community/netinfo';

import { EXISTENCIA_BAJA } from '@/constants';

import { ErrorApi } from '../cliente';
import type {
  DatosConfirmarAlta,
  DetalleVenta,
  Producto,
  RespuestaAlta,
  RespuestaVenta,
  SolicitudVenta,
} from '../esquemas';

const catalogo: Producto[] = [
  { sku: 'REF-COLA-600', nombre: 'Refresco de cola 600 ml', precio_unitario: 18, existencia: 12 },
  { sku: 'PAN-BLANCO-680', nombre: 'Pan blanco grande', precio_unitario: 52, existencia: 3 },
  { sku: 'JABON-BARRA-150', nombre: 'Jabón de barra 150 g', precio_unitario: 22, existencia: 8 },
  { sku: 'GALL-MARIA-170', nombre: 'Galletas María 170 g', precio_unitario: 16, existencia: 12 },
  { sku: 'GALL-CHOC-90', nombre: 'Galletas de chocolate 90 g', precio_unitario: 14, existencia: 3 },
  { sku: 'LECHE-ENT-1L', nombre: 'Leche entera 1 L', precio_unitario: 28, existencia: 10 },
  { sku: 'HUEVO-12', nombre: 'Huevo blanco 12 piezas', precio_unitario: 45, existencia: 6 },
  { sku: 'TORT-1KG', nombre: 'Tortillas de maíz 1 kg', precio_unitario: 24, existencia: 2 },
  { sku: 'FRIJOL-900', nombre: 'Frijol negro 900 g', precio_unitario: 38, existencia: 7 },
  { sku: 'ARROZ-1KG', nombre: 'Arroz 1 kg', precio_unitario: 32, existencia: 9 },
  { sku: 'ACEITE-1L', nombre: 'Aceite vegetal 1 L', precio_unitario: 49, existencia: 5 },
  { sku: 'AZUCAR-1KG', nombre: 'Azúcar estándar 1 kg', precio_unitario: 34, existencia: 8 },
  { sku: 'AGUA-1L', nombre: 'Agua natural 1 L', precio_unitario: 12, existencia: 20 },
  { sku: 'PAPAS-45', nombre: 'Papas fritas 45 g', precio_unitario: 17, existencia: 15 },
  { sku: 'ATUN-140', nombre: 'Atún en agua 140 g', precio_unitario: 26, existencia: 4 },
];

const masVendidosSkus = ['REF-COLA-600', 'TORT-1KG', 'HUEVO-12', 'LECHE-ENT-1L', 'PAN-BLANCO-680', 'AGUA-1L'];

const ventas: DetalleVenta[] = [];
const porIdLocal = new Map<string, RespuestaVenta>();

export const quitarAcentos = (t: string) =>
  t
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export async function exigirConexion() {
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

// ---------- Consultas para las respuestas del asistente (MOCK) ----------

/** Copia del catálogo sintético (para que el asistente mock conteste con los mismos datos). */
export function mockCatalogo(): Producto[] {
  return catalogo.map((p) => ({ ...p }));
}

/** Ventas registradas en esta sesión de la app (en memoria). */
export function mockResumenVentasHoy() {
  const conteo = new Map<string, { nombre: string; piezas: number }>();
  for (const v of ventas) {
    for (const i of v.items) {
      const clave = i.sku ?? i.nombre;
      const previo = conteo.get(clave);
      conteo.set(clave, { nombre: i.nombre, piezas: (previo?.piezas ?? 0) + i.cantidad });
    }
  }
  const masVendido = [...conteo.values()].sort((a, b) => b.piezas - a.piezas)[0] ?? null;
  return { numero: ventas.length, total: ventas.reduce((s, v) => s + v.total, 0), masVendido };
}

export function mockStockBajo(): Producto[] {
  return catalogo.filter((p) => p.existencia <= EXISTENCIA_BAJA).map((p) => ({ ...p }));
}

/** MOCK — POST /inventario/altas (propuesta; la pantalla de alta es Fase 4). */
export async function mockRegistrarAlta(datos: DatosConfirmarAlta): Promise<RespuestaAlta> {
  await exigirConexion();
  const producto = catalogo.find((p) => p.sku === datos.sku);
  if (producto) {
    producto.existencia += datos.cantidad;
    if (datos.precio_venta !== null) producto.precio_unitario = datos.precio_venta;
    return { sku: producto.sku, nombre: producto.nombre, quedan: producto.existencia };
  }
  const nuevo: Producto = {
    sku: datos.sku ?? `MOCK-${catalogo.length + 1}`,
    nombre: datos.nombre,
    precio_unitario: datos.precio_venta ?? 0,
    existencia: datos.cantidad,
  };
  catalogo.push(nuevo);
  return { sku: nuevo.sku, nombre: nuevo.nombre, quedan: nuevo.existencia };
}
