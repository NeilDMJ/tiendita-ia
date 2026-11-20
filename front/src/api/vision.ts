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

/** MOCK — simula los casos de error del análisis según EXPO_PUBLIC_MOCK_VISION. */
async function simularVision<T>(datos: T, vacio: T, opciones?: OpcionesPedido): Promise<T> {
  const lento = ESCENARIO_VISION === 'lento';
  await esperarCancelable(lento ? 25_000 : 1_800, opciones?.signal, opciones?.tiempoMs);
  if (ESCENARIO_VISION === 'ilegible') throw new ErrorApi('imagen_no_procesable');
  if (ESCENARIO_VISION === 'vacio') return vacio;
  return datos;
}

export async function analizarCobro(uri: string, opciones?: OpcionesPedido): Promise<RespuestaPosCheckout> {
  if (USAR_MOCKS) return simularVision(mockPosCheckout, mockPosCheckoutVacio, opciones);
  return subirImagen('/vision/pos-checkout', RespuestaPosCheckout, uri, opciones);
}

export async function analizarAlta(uri: string, opciones?: OpcionesPedido): Promise<RespuestaCatalogScan> {
  if (USAR_MOCKS) return simularVision(mockCatalogScan, { items: [] }, opciones);
  return subirImagen('/vision/catalog-scan', RespuestaCatalogScan, uri, opciones);
}

export async function analizarTicket(uri: string, opciones?: OpcionesPedido): Promise<RespuestaReceiptOcr> {
  if (USAR_MOCKS) return esperar(1500).then(() => mockReceiptOcr);
  return subirImagen('/vision/receipt-ocr', RespuestaReceiptOcr, uri, opciones);
}
