import { ErrorApi, subirImagen, USAR_MOCKS, type OpcionesPedido } from './cliente';
import {
  RespuestaCatalogScan,
  RespuestaPosCheckout,
  RespuestaReceiptOcr,
} from './esquemas';
import {
  ESCENARIO_VISION,
  esperar,
  esperarCancelable,
  mockCatalogScan,
  mockPosCheckout,
  mockPosCheckoutVacio,
  mockReceiptOcr,
} from './mocks';

/**
 * 1 = la cámara usa el modelo real (back/vision) aunque el resto de la app siga con mocks
 * (productos, ventas y asistente todavía no tienen endpoint en el back).
 */
const VISION_REAL = process.env.EXPO_PUBLIC_VISION_REAL === '1';
const MOCK_VISION = USAR_MOCKS && !VISION_REAL;

/** MOCK — simula los casos de error del análisis según EXPO_PUBLIC_MOCK_VISION. */
async function simularVision<T>(datos: T, vacio: T, opciones?: OpcionesPedido): Promise<T> {
  const lento = ESCENARIO_VISION === 'lento';
  await esperarCancelable(lento ? 25_000 : 1_800, opciones?.signal, opciones?.tiempoMs);
  if (ESCENARIO_VISION === 'ilegible') throw new ErrorApi('imagen_no_procesable');
  if (ESCENARIO_VISION === 'vacio') return vacio;
  return datos;
}

export async function analizarCobro(uri: string, opciones?: OpcionesPedido): Promise<RespuestaPosCheckout> {
  if (MOCK_VISION) return simularVision(mockPosCheckout, mockPosCheckoutVacio, opciones);
  return subirImagen('/vision/pos-checkout', RespuestaPosCheckout, uri, opciones);
}

export async function analizarAlta(uri: string, opciones?: OpcionesPedido): Promise<RespuestaCatalogScan> {
  if (MOCK_VISION) return simularVision(mockCatalogScan, { items: [] }, opciones);
  return subirImagen('/vision/catalog-scan', RespuestaCatalogScan, uri, opciones);
}

export async function analizarTicket(uri: string, opciones?: OpcionesPedido): Promise<RespuestaReceiptOcr> {
  if (USAR_MOCKS) return esperar(1500).then(() => mockReceiptOcr);
  return subirImagen('/vision/receipt-ocr', RespuestaReceiptOcr, uri, opciones);
}
