/** "$1,234.50" (sin depender de Intl, que varía entre motores JS). */
export function formatoMoneda(monto: number): string {
  const signo = monto < 0 ? '-' : '';
  const [entero, decimales] = Math.abs(monto).toFixed(2).split('.');
  const conComas = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${signo}$${conComas}.${decimales}`;
}

/** "36 pesos" · "18 pesos con 50 centavos" — para lectores de pantalla. */
export function montoParaLector(monto: number): string {
  const centavosTotales = Math.round(monto * 100);
  const pesos = Math.floor(centavosTotales / 100);
  const centavos = centavosTotales % 100;
  const textoPesos = `${pesos} ${pesos === 1 ? 'peso' : 'pesos'}`;
  return centavos === 0 ? textoPesos : `${textoPesos} con ${centavos} centavos`;
}

/** Convierte texto escrito por el usuario ("18,5" o "18.50") a número; null si no es válido. */
export function leerMonto(texto: string): number | null {
  const limpio = texto.replace(/[$\s]/g, '').replace(',', '.');
  if (limpio === '' || !/^\d+(\.\d{0,2})?$/.test(limpio)) return null;
  return Number(limpio);
}
