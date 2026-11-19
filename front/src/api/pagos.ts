/**
 * SIMULACIÓN — pago digital (transferencia/CoDi/tarjeta). No existe endpoint real:
 * nunca se mueve dinero. Resultado controlable con EXPO_PUBLIC_MOCK_PAGO = ok | falla.
 */
import { esperar } from './mocks';

const ESCENARIO_PAGO = process.env.EXPO_PUBLIC_MOCK_PAGO ?? 'ok';

export type ResultadoPagoSimulado = 'recibido' | 'no_recibido';

// MOCK
export async function simularPagoDigital(_monto: number): Promise<ResultadoPagoSimulado> {
  await esperar(2000);
  return ESCENARIO_PAGO === 'falla' ? 'no_recibido' : 'recibido';
}
