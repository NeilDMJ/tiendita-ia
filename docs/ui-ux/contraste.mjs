// Verifica contraste WCAG de la paleta propuesta. Uso: node contraste.mjs
const lum = (h) => {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
export const ratio = (a, b) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};

const claro = {
  primary: '#1A56DB', onPrimary: '#FFFFFF', primaryContainer: '#E8F0FE', onPrimaryContainer: '#1543B0',
  secondary: '#4B5563', onSecondary: '#FFFFFF', secondaryContainer: '#E3E8F4', onSecondaryContainer: '#1F2937',
  tertiary: '#5B3FD6', onTertiary: '#FFFFFF', tertiaryContainer: '#ECE7FD', onTertiaryContainer: '#3B2A8C',
  error: '#DC2626', onError: '#FFFFFF', errorContainer: '#FEE2E2', onErrorContainer: '#991B1B',
  success: '#15803D', onSuccess: '#FFFFFF', successContainer: '#DCFCE7', onSuccessContainer: '#14532D',
  warning: '#B45309', onWarning: '#FFFFFF', warningContainer: '#FEF3C7', onWarningContainer: '#78350F',
  surface: '#F5F7FB', surfaceContainerLowest: '#FFFFFF', surfaceContainerLow: '#FFFFFF', surfaceContainer: '#EEF1F7',
  surfaceContainerHigh: '#E8ECF4', surfaceContainerHighest: '#E2E7F0',
  onSurface: '#0F172A', onSurfaceVariant: '#4B5563', outline: '#6B7280', outlineVariant: '#E5E7EB',
  inverseSurface: '#0F172A', inverseOnSurface: '#F5F7FB', inversePrimary: '#A9C4F9',
};
const oscuro = {
  primary: '#7BA3F5', onPrimary: '#0B1F55', primaryContainer: '#16328A', onPrimaryContainer: '#DCE7FD',
  secondary: '#B6BECC', onSecondary: '#1F2937', secondaryContainer: '#2A3446', onSecondaryContainer: '#E3E8F4',
  tertiary: '#B9A8FA', onTertiary: '#2A1B73', tertiaryContainer: '#3B2A8C', onTertiaryContainer: '#ECE7FD',
  error: '#F87171', onError: '#450A0A', errorContainer: '#7F1D1D', onErrorContainer: '#FEE2E2',
  success: '#4ADE80', onSuccess: '#052E16', successContainer: '#14532D', onSuccessContainer: '#DCFCE7',
  warning: '#FBBF24', onWarning: '#451A03', warningContainer: '#78350F', onWarningContainer: '#FEF3C7',
  surface: '#0B1220', surfaceContainerLowest: '#070C17', surfaceContainerLow: '#111A2C', surfaceContainer: '#152036',
  surfaceContainerHigh: '#1B2740', surfaceContainerHighest: '#222F4A',
  onSurface: '#E5E9F2', onSurfaceVariant: '#A7B0C0', outline: '#7C879B', outlineVariant: '#2A3650',
  inverseSurface: '#E5E9F2', inverseOnSurface: '#0F172A', inversePrimary: '#1A56DB',
};

const pares = (p) => [
  ['onPrimary/primary', p.onPrimary, p.primary, 4.5],
  ['onPrimaryContainer/primaryContainer', p.onPrimaryContainer, p.primaryContainer, 4.5],
  ['onSecondary/secondary', p.onSecondary, p.secondary, 4.5],
  ['onSecondaryContainer/secondaryContainer', p.onSecondaryContainer, p.secondaryContainer, 4.5],
  ['onTertiary/tertiary', p.onTertiary, p.tertiary, 4.5],
  ['onTertiaryContainer/tertiaryContainer', p.onTertiaryContainer, p.tertiaryContainer, 4.5],
  ['onError/error', p.onError, p.error, 4.5],
  ['onErrorContainer/errorContainer', p.onErrorContainer, p.errorContainer, 4.5],
  ['onSuccess/success', p.onSuccess, p.success, 4.5],
  ['onSuccessContainer/successContainer', p.onSuccessContainer, p.successContainer, 4.5],
  ['onWarning/warning', p.onWarning, p.warning, 4.5],
  ['onWarningContainer/warningContainer', p.onWarningContainer, p.warningContainer, 4.5],
  ['onSurface/surface', p.onSurface, p.surface, 4.5],
  ['onSurface/surfaceContainerLowest', p.onSurface, p.surfaceContainerLowest, 4.5],
  ['onSurface/surfaceContainerHighest', p.onSurface, p.surfaceContainerHighest, 4.5],
  ['onSurfaceVariant/surface', p.onSurfaceVariant, p.surface, 4.5],
  ['onSurfaceVariant/surfaceContainerLowest', p.onSurfaceVariant, p.surfaceContainerLowest, 4.5],
  ['onSurfaceVariant/surfaceContainerHighest', p.onSurfaceVariant, p.surfaceContainerHighest, 4.5],
  ['primary/surface (texto-enlace)', p.primary, p.surface, 4.5],
  ['primary/surfaceContainerLowest', p.primary, p.surfaceContainerLowest, 4.5],
  ['error/surface (texto-error)', p.error, p.surface, 4.5],
  ['success/surface (texto-éxito)', p.success, p.surface, 4.5],
  ['warning/surface (texto-aviso)', p.warning, p.surface, 4.5],
  ['outline/surface (borde de campo, UI)', p.outline, p.surface, 3],
  ['outline/surfaceContainerLowest (UI)', p.outline, p.surfaceContainerLowest, 3],
  ['primary/surface (UI: foco, icono)', p.primary, p.surface, 3],
  ['inverseOnSurface/inverseSurface', p.inverseOnSurface, p.inverseSurface, 4.5],
  ['inversePrimary/inverseSurface (enlace sobre snackbar)', p.inversePrimary, p.inverseSurface, 4.5],
];

for (const [nombre, p] of [['CLARO', claro], ['OSCURO', oscuro]]) {
  console.log(`\n== ${nombre}`);
  let fallos = 0;
  for (const [n, a, b, min] of pares(p)) {
    const r = ratio(a, b);
    const ok = r >= min;
    if (!ok) fallos++;
    console.log(`${ok ? 'OK ' : 'FALLA'} ${r.toFixed(2).padStart(5)}:1 (min ${min})  ${n}`);
  }
  console.log(`fallos: ${fallos}`);
}
