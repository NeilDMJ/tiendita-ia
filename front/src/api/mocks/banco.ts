/**
 * MOCK — guía bancaria guiada (rol 'banco'). Sin datos reales.
 * Simula lo que hará el backend: detectar banco + operación, devolver la guía
 * verificada si existe, o pasos genéricos marcados como "sin verificar".
 * Los textos de botones de BBVA son supuestos: verificar en la app vigente.
 */
import type { MensajeAsistente, PasoGuia } from '../esquemas';

const BANCOS: [RegExp, string][] = [
  [/bbva/i, 'BBVA'],
  [/banorte/i, 'Banorte'],
  [/santander/i, 'Santander'],
  [/banamex|citibanamex/i, 'Banamex'],
  [/hsbc/i, 'HSBC'],
  [/\bnu\b/i, 'Nu'],
];

type Operacion = 'transferencia' | 'pago_servicio' | 'saldo' | 'cobro';
const OPERACIONES: [RegExp, Operacion][] = [
  [/transfer|enviar dinero|mandar dinero|spei/i, 'transferencia'],
  [/servicio|luz|agua|gas|tel[eé]fono|recibo/i, 'pago_servicio'],
  [/saldo|cu[aá]nto tengo|movimientos/i, 'saldo'],
  [/cobro|dep[oó]sito|me lleg[oó]|me pagaron/i, 'cobro'],
];

const NOMBRE_OP: Record<Operacion, string> = {
  transferencia: 'una transferencia',
  pago_servicio: 'el pago de un servicio',
  saldo: 'tu saldo y movimientos',
  cobro: 'si te llegó un cobro',
};

const FRASE_OP: Record<Operacion, string> = {
  transferencia: 'Quiero hacer una transferencia',
  pago_servicio: 'Quiero pagar un servicio',
  saldo: 'Quiero ver mi saldo',
  cobro: 'Quiero revisar si me llegó un cobro',
};

const AVISO_CLAVES = 'Aquí nunca compartas tu NIP, token, CVV ni contraseñas. Yo nunca te los pediré.';

const pasos = (textos: [string, string?][]): PasoGuia[] =>
  textos.map(([texto, pantalla], i) => ({ n: i + 1, texto, pantalla }));

const BBVA_TRANSFERENCIA: PasoGuia[] = pasos([
  ['Abre tu app de BBVA e inicia sesión como lo haces normalmente.', 'Inicio de sesión'],
  ['En la pantalla principal, busca la opción “Transferir” (o “Enviar dinero”) y tócala.', 'Pantalla principal'],
  ['Elige a quién le vas a enviar: un contacto guardado o agregar una cuenta nueva.', 'Transferir'],
  ['Si es cuenta nueva, captura la CLABE, tarjeta o celular del destinatario directamente en tu app.', 'Transferir'],
  ['Escribe el monto y un concepto (por ejemplo, “pago de mercancía”).', 'Monto y concepto'],
  ['Revisa el resumen: nombre del beneficiario, monto y cuenta.', 'Resumen'],
  ['Si todo está bien, toca “Confirmar” y autoriza con tu método de seguridad.', 'Confirmación'],
  ['Guarda el comprobante que te muestra la app.', 'Comprobante'],
]);

const GENERICAS: Record<Operacion, PasoGuia[]> = {
  transferencia: pasos([
    ['Abre la app de tu banco e inicia sesión.'],
    ['Busca la opción de transferencias o enviar dinero.'],
    ['Elige o agrega al destinatario.'],
    ['Captura el monto y el concepto.'],
    ['Revisa el resumen y confirma con tu método de seguridad.'],
  ]),
  pago_servicio: pasos([
    ['Abre la app de tu banco e inicia sesión.'],
    ['Busca “Pagar servicios” o “Pago de servicios”.'],
    ['Elige el servicio (luz, agua, teléfono…) y captura la referencia de tu recibo.'],
    ['Revisa el importe y la cuenta de cargo, y confirma.'],
  ]),
  saldo: pasos([
    ['Abre la app de tu banco e inicia sesión.'],
    ['En la pantalla principal verás tus cuentas; toca la que quieras revisar.'],
    ['Entra a “Movimientos” para ver los últimos depósitos y cargos.'],
  ]),
  cobro: pasos([
    ['Abre la app de tu banco e inicia sesión.'],
    ['Entra a tu cuenta y busca “Movimientos”.'],
    ['Revisa los depósitos recientes y compara el monto y la hora con tu venta.'],
  ]),
};

const ADVERTENCIAS: Record<Operacion, string[]> = {
  transferencia: [
    AVISO_CLAVES,
    'Antes de confirmar, revisa en tu app el nombre del beneficiario y el monto. Una transferencia no siempre se puede deshacer.',
  ],
  pago_servicio: [AVISO_CLAVES, 'Verifica que la referencia coincida con tu recibo antes de confirmar.'],
  saldo: [AVISO_CLAVES],
  cobro: [AVISO_CLAVES, 'Confirma el depósito en tu app antes de entregar la mercancía.'],
};

export function mockRespuestaBanco(texto: string): MensajeAsistente | null {
  if (/inversi|cr[eé]dito|pr[eé]stamo|acciones|cripto|impuestos|sat\b/i.test(texto)) {
    return {
      rol: 'banco',
      texto:
        'Eso no lo puedo resolver desde aquí. Para eso lo mejor es contactar a tu banco por sus canales oficiales. ¿Te ayudo con alguna operación paso a paso?',
      respuestas_rapidas: ['Quiero hacer una transferencia', 'Quiero ver mi saldo'],
    };
  }

  if (/distint|no coincide|no me sale|no aparece/i.test(texto)) {
    return {
      rol: 'banco',
      texto:
        'Los bancos cambian su app seguido. Cuéntame qué opciones ves en la pantalla (sin escribir números de cuenta ni claves) y buscamos el camino juntos.',
    };
  }

  const banco = BANCOS.find(([re]) => re.test(texto))?.[1];
  const operacion = OPERACIONES.find(([re]) => re.test(texto))?.[1];
  if (!banco && !operacion) return null; // no es tema bancario: lo resuelve el mock general

  if (!operacion) {
    return {
      rol: 'banco',
      texto: `Con gusto. ¿Qué quieres hacer en ${banco}?`,
      respuestas_rapidas: (Object.keys(FRASE_OP) as Operacion[]).map((o) => `${FRASE_OP[o]} en ${banco}`),
      no_resuelto: true,
    };
  }
  if (!banco) {
    return {
      rol: 'banco',
      texto: `Te guío con ${NOMBRE_OP[operacion]}. ¿Qué banco usas?`,
      respuestas_rapidas: ['BBVA', 'Banorte', 'Santander', 'Otro banco'].map((b) => `${FRASE_OP[operacion]} en ${b}`),
      no_resuelto: true,
    };
  }

  const verificada = banco === 'BBVA' && operacion === 'transferencia';
  return {
    rol: 'banco',
    texto: verificada
      ? '¡Claro! Te guío paso a paso en tu app de BBVA.'
      : `Estos son los pasos generales para ${NOMBRE_OP[operacion]}. En ${banco} los nombres de los botones pueden variar.`,
    pasos: verificada ? BBVA_TRANSFERENCIA : GENERICAS[operacion],
    advertencias: ADVERTENCIAS[operacion],
    guia_verificada: verificada,
    respuestas_rapidas: ['Mi pantalla se ve distinta'],
  };
}
