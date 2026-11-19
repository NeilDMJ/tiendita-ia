import { subirImagen, USAR_MOCKS } from './cliente';
import {
  RespuestaCatalogScan,
  RespuestaPosCheckout,
  RespuestaReceiptOcr,
} from './esquemas';
import { esperar, mockCatalogScan, mockPosCheckout, mockReceiptOcr } from './mocks';

export async function analizarCobro(uri: string): Promise<RespuestaPosCheckout> {
  if (USAR_MOCKS) return esperar(1200).then(() => mockPosCheckout);
  return subirImagen('/vision/pos-checkout', RespuestaPosCheckout, uri);
}

export async function analizarAlta(uri: string): Promise<RespuestaCatalogScan> {
  if (USAR_MOCKS) return esperar(1200).then(() => mockCatalogScan);
  return subirImagen('/vision/catalog-scan', RespuestaCatalogScan, uri);
}

export async function analizarTicket(uri: string): Promise<RespuestaReceiptOcr> {
  if (USAR_MOCKS) return esperar(1500).then(() => mockReceiptOcr);
  return subirImagen('/vision/receipt-ocr', RespuestaReceiptOcr, uri);
}
