/**
 * MOCK — datos sintéticos para desarrollar sin backend (EXPO_PUBLIC_USE_MOCKS=1).
 * No contienen datos reales de personas ni negocios.
 */
import type {
  MensajeAsistente,
  RespuestaCatalogScan,
  RespuestaPosCheckout,
  RespuestaReceiptOcr,
} from '../esquemas';

export const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const mockPosCheckout: RespuestaPosCheckout = {
  imagen_id: 'mock-001',
  items: [
    { sku: 'REF-COLA-600', nombre: 'Refresco de cola 600 ml', cantidad: 2, precio_unitario: 18, confianza: 0.94 },
    { sku: 'PAN-BLANCO-680', nombre: 'Pan blanco grande', cantidad: 1, precio_unitario: 52, confianza: 0.88 },
    { sku: null, nombre: 'Galletas (sin identificar)', cantidad: 1, precio_unitario: null, confianza: 0.41 },
  ],
};

export const mockCatalogScan: RespuestaCatalogScan = {
  categoria: 'Lácteos',
  caducidad_ocr: '2026-11-28',
  items: [{ sku: 'LECHE-ENT-1L', nombre: 'Leche entera 1 L', cantidad: 12, precio_unitario: 28, confianza: 0.91 }],
};

export const mockReceiptOcr: RespuestaReceiptOcr = {
  fecha: '2026-11-19',
  proveedor: 'Distribuidora Ejemplo',
  total: 1340,
  conceptos: [
    { descripcion: 'Caja de refrescos 24 pz', monto: 980 },
    { descripcion: 'Bolsas de pan 10 pz', monto: 360 },
  ],
  tipo: 'compra',
  confianza: 0.83,
};

export const mockRespuestaAsistente = (texto: string): MensajeAsistente =>
  /vend/i.test(texto)
    ? { rol: 'cuentas', texto: 'Hoy llevas $1,245 en 23 ventas. Lo que más salió fue refresco de 600 ml.' }
    : /acab|stock|falta/i.test(texto)
      ? { rol: 'bodega', texto: 'Te quedan 3 litros de leche y 2 paquetes de tortillas. ¿Los agrego al pedido del proveedor?' }
      : { rol: 'general', texto: 'No entendí bien. ¿Quieres cobrar, revisar tu inventario o ver tus ventas?', no_resuelto: true };
