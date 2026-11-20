const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** El back manda texto plano; si llega markdown se muestra sin `**`, `#` ni `_` (02-asistente §2.1). */
export function limpiarFormato(texto: string): string {
  return texto
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/(^|\s)_(\S.*?\S|\S)_(?=\s|$|[.,;:!?])/g, '$1$2')
    .replace(/\*/g, '');
}

function mismoDia(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** "Hoy" · "Ayer" · "12 nov" · "12 nov 2025" (otro año). */
export function separadorDeDia(iso: string, ahora: Date = new Date()): string {
  const d = new Date(iso);
  if (mismoDia(d, ahora)) return 'Hoy';
  const ayer = new Date(ahora);
  ayer.setDate(ahora.getDate() - 1);
  if (mismoDia(d, ayer)) return 'Ayer';
  const base = `${d.getDate()} ${MESES[d.getMonth()]}`;
  return d.getFullYear() === ahora.getFullYear() ? base : `${base} ${d.getFullYear()}`;
}

/** Clave del día local ('2026-11-19') para agrupar mensajes. */
export function claveDia(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}
