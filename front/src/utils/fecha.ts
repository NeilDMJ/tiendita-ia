const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

const dos = (n: number) => String(n).padStart(2, '0');

/** "13:42" */
export function hora(iso: string): string {
  const d = new Date(iso);
  return `${dos(d.getHours())}:${dos(d.getMinutes())}`;
}

/** "19 nov 2026, 13:42" */
export function fechaCompleta(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()} ${MESES[d.getMonth()]} ${d.getFullYear()}, ${hora(iso)}`;
}

/** "42 segundos" · "2 min 5 s" */
export function duracionLegible(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  if (s < 60) return `${s} segundos`;
  const m = Math.floor(s / 60);
  const resto = s % 60;
  return resto === 0 ? `${m} min` : `${m} min ${resto} s`;
}
