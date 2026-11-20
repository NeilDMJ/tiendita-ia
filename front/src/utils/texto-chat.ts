const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** Extrae bloques `<think>...</think>` si un modelo los incluye y devuelve el texto limpio aparte. */
export function extraerBloquesThink(texto: string): { limpio: string; pensamientos: string[] } {
  const pensamientos: string[] = [];
  const limpio = texto
    .replace(/<think>([\s\S]*?)<\/think>/gi, (_, contenido: string) => {
      const t = contenido.trim();
      if (t) pensamientos.push(t);
      return '';
    })
    .trim();
  return { limpio, pensamientos };
}

/** Convierte tablas Markdown (`| col | col |`) en viñetas limpias y legibles en pantalla móvil. */
function convertirTablasMarkdown(texto: string): string {
  const lineas = texto.split('\n');
  const salida: string[] = [];
  let i = 0;

  while (i < lineas.length) {
    const linea = lineas[i].trim();
    const esFilaTabla = linea.startsWith('|') && linea.endsWith('|') && linea.split('|').length >= 3;
    const siguiente = lineas[i + 1]?.trim() ?? '';
    const esSeparador = /^\|[\s:|-]+\|$/.test(siguiente);

    if (esFilaTabla && esSeparador) {
      const encabezados = linea
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim().replace(/\*\*/g, ''));
      i += 2; // saltar encabezado + separador |---|---|
      while (i < lineas.length) {
        const fila = lineas[i].trim();
        if (!fila.startsWith('|') || !fila.endsWith('|')) break;
        const celdas = fila
          .slice(1, -1)
          .split('|')
          .map((c) => c.trim().replace(/\*\*/g, ''));
        if (celdas.some(Boolean)) {
          const pares = celdas
            .map((valor, idx) => {
              if (!valor) return null;
              const col = encabezados[idx];
              // Evitar repetir etiqueta obvia en columna # / Posición
              if (!col || /^(#|posici[oó]n|no\.?)$/i.test(col)) return valor;
              return `${col}: ${valor}`;
            })
            .filter(Boolean);
          salida.push(`• ${pares.join(' · ')}`);
        }
        i += 1;
      }
      continue;
    }

    salida.push(lineas[i]);
    i += 1;
  }

  return salida.join('\n');
}

/**
 * Normaliza la respuesta de los LLMs para móvil (sin markdown crudo como `**`, `|---|`, backticks ni `<think>`),
 * conservando títulos, viñetas y saltos claros como en el CLI.
 */
export function limpiarFormato(texto: string): string {
  const { limpio } = extraerBloquesThink(texto);
  const sinTablas = convertirTablasMarkdown(limpio);
  return sinTablas
    .replace(/```[a-zA-Z0-9_-]*\n([\s\S]*?)```/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*[-*_]{3,}\s*$/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/(^|\s)_(\S.*?\S|\S)_(?=\s|$|[.,;:!?])/g, '$1$2')
    .replace(/\*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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
