/**
 * Anonimización en el dispositivo, ANTES de enviar un mensaje al backend/NIM.
 * Los pasos de una guía bancaria no dependen de cifras ni de cuentas, así que se enmascaran.
 * Si aparece algo que jamás debe salir (tarjeta, CLABE, NIP/CVV/token), el mensaje se bloquea.
 * Ver docs/DISENO-agente-bancario.md §2.
 */
export type ResultadoAnonimizar = {
  /** Texto con datos enmascarados, listo para enviar. */
  texto: string;
  /** true = no enviar: contiene datos que no deben salir del teléfono. */
  bloquear: boolean;
};

const CLABE = /\b\d{18}\b/g;
const TARJETA = /\b(?:\d[ -]?){15}\d\b/g;
const TELEFONO = /\b\d{10}\b/g;
const MONTO = /\$\s?\d[\d,]*(?:\.\d+)?/g;
const CREDENCIAL = /\b(nip|cvv|cvc|token|contrase(?:ñ|n)a|password)\b[^\n]*\d/i;

export function anonimizar(entrada: string): ResultadoAnonimizar {
  const bloquear = CLABE.test(entrada) || TARJETA.test(entrada) || CREDENCIAL.test(entrada);
  // Los regex con /g conservan estado: reiniciar tras .test()
  CLABE.lastIndex = 0;
  TARJETA.lastIndex = 0;

  const texto = entrada
    .replace(CLABE, '[CLABE]')
    .replace(TARJETA, '[TARJETA]')
    .replace(TELEFONO, '[CELULAR]')
    .replace(MONTO, '[MONTO]');
  return { texto, bloquear };
}
