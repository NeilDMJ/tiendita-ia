// Uso:  cd <scratchpad>/m3 && npm install && node generar.mjs [#semilla] [#verdeExito]
// Salida: tabla markdown de roles (hex + tono) y contrastes WCAG de los pares usados en front/.
import {
  argbFromHex,
  hexFromArgb,
  Hct,
  SchemeTonalSpot,
  MaterialDynamicColors,
  Blend,
  TonalPalette,
} from '@material/material-color-utilities';

const SEMILLA = process.argv[2] ?? '#769CDF'; // azul mezclilla "de confianza"
const VERDE_EXITO = process.argv[3] ?? '#1B5E20'; // verde de "venta registrada" del sistema flat

const fuente = Hct.fromInt(argbFromHex(SEMILLA));
const esquema = new SchemeTonalSpot(fuente, /* isDark */ false, /* contrastLevel */ 0.0);

const ROLES = [
  'primary', 'onPrimary', 'primaryContainer', 'onPrimaryContainer', 'inversePrimary',
  'secondary', 'onSecondary', 'secondaryContainer', 'onSecondaryContainer',
  'tertiary', 'onTertiary', 'tertiaryContainer', 'onTertiaryContainer',
  'error', 'onError', 'errorContainer', 'onErrorContainer',
  'surface', 'surfaceDim', 'surfaceBright',
  'surfaceContainerLowest', 'surfaceContainerLow', 'surfaceContainer',
  'surfaceContainerHigh', 'surfaceContainerHighest',
  'onSurface', 'surfaceVariant', 'onSurfaceVariant', 'outline', 'outlineVariant',
  'inverseSurface', 'inverseOnSurface', 'shadow', 'scrim',
];

// Compatibilidad entre versiones de MCU: getter del esquema (0.3+) o MaterialDynamicColors estático (0.2).
function argbDeRol(rol) {
  if (typeof esquema[rol] === 'number') return esquema[rol];
  const dc = MaterialDynamicColors[rol];
  if (dc && typeof dc.getArgb === 'function') return dc.getArgb(esquema);
  throw new Error(`Rol no soportado por esta versión de MCU: ${rol}`);
}

const hex = {};
for (const rol of ROLES) hex[rol] = hexFromArgb(argbDeRol(rol)).toUpperCase();

// Rol personalizado success: igual que "custom colors" de Material Theme Builder.
// 1) armonizar el verde hacia la semilla (rota el tono máx. 15°), 2) paleta con croma ≥ 48,
// 3) tonos claros: color T40, onColor T100, container T90, onContainer T30 (MCU actual; T10 en MCU 2021).
const armonizado = Hct.fromInt(Blend.harmonize(argbFromHex(VERDE_EXITO), argbFromHex(SEMILLA)));
const paletaExito = TonalPalette.fromHueAndChroma(armonizado.hue, Math.max(48, armonizado.chroma));
hex.success = hexFromArgb(paletaExito.tone(40)).toUpperCase();
hex.onSuccess = hexFromArgb(paletaExito.tone(100)).toUpperCase();
hex.successContainer = hexFromArgb(paletaExito.tone(90)).toUpperCase();
hex.onSuccessContainer = hexFromArgb(paletaExito.tone(30)).toUpperCase();

// WCAG 2.x
function luminancia(h) {
  const n = parseInt(h.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const s = v / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contraste(a, b) {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}
// Mezcla de capa de estado (contenido al alfa sobre contenedor) para verificar "presionado".
function mezcla(sobre, base, alfa) {
  const a = parseInt(sobre.slice(1), 16), b = parseInt(base.slice(1), 16);
  const ch = (s) => Math.round(((a >> s) & 255) * alfa + ((b >> s) & 255) * (1 - alfa));
  return '#' + [16, 8, 0].map((s) => ch(s).toString(16).padStart(2, '0')).join('').toUpperCase();
}

const PARES = [
  // [primer plano, fondo, mínimo, uso]
  ['onPrimary', 'primary', 4.5, 'Botón filled, Extended FAB primario'],
  ['onPrimaryContainer', 'primaryContainer', 4.5, 'Contenedor primario'],
  ['primary', 'surface', 4.5, 'Botón text/outlined, enlaces'],
  ['primary', 'surfaceContainerLow', 4.5, 'Texto primario en hoja inferior / card elevated'],
  ['primary', 'surfaceContainerHighest', 4.5, 'Texto primario en card filled'],
  ['onSecondaryContainer', 'secondaryContainer', 4.5, 'Botón tonal, indicador de navegación'],
  ['onTertiaryContainer', 'tertiaryContainer', 4.5, 'Chip "Revisa"'],
  ['onError', 'error', 4.5, 'Botón filled de peligro'],
  ['onErrorContainer', 'errorContainer', 4.5, 'Aviso de error, chip "Falta precio"'],
  ['error', 'surface', 4.5, 'Texto de error en campos'],
  ['error', 'surfaceContainerLow', 4.5, 'Error en hoja inferior'],
  ['onSuccess', 'success', 4.5, 'Botón/insignia de éxito'],
  ['onSuccessContainer', 'successContainer', 4.5, 'Aviso de éxito'],
  ['success', 'surface', 4.5, 'Icono/título de éxito'],
  ['onSurface', 'surface', 4.5, 'Texto general'],
  ['onSurface', 'surfaceContainerLowest', 4.5, ''],
  ['onSurface', 'surfaceContainerLow', 4.5, ''],
  ['onSurface', 'surfaceContainer', 4.5, ''],
  ['onSurface', 'surfaceContainerHigh', 4.5, ''],
  ['onSurface', 'surfaceContainerHighest', 4.5, ''],
  ['onSurfaceVariant', 'surface', 4.5, 'Texto secundario'],
  ['onSurfaceVariant', 'surfaceContainerLow', 4.5, ''],
  ['onSurfaceVariant', 'surfaceContainer', 4.5, ''],
  ['onSurfaceVariant', 'surfaceContainerHigh', 4.5, ''],
  ['onSurfaceVariant', 'surfaceContainerHighest', 4.5, 'También: deshabilitado (excepción del proyecto)'],
  ['outline', 'surface', 3.0, 'Borde de campos/botón outlined (no texto)'],
  ['outline', 'surfaceContainerLow', 3.0, ''],
  ['outline', 'surfaceContainerHighest', 3.0, ''],
  ['outlineVariant', 'surface', 0, 'Divisor decorativo'],
  ['inverseOnSurface', 'inverseSurface', 4.5, 'Snackbar, etiqueta Simulación, barras de cámara'],
  ['inversePrimary', 'inverseSurface', 4.5, 'Acción "Deshacer" del snackbar'],
  ['primary', 'secondaryContainer', 3.0, 'Progreso lineal: indicador vs. pista'],
];

console.log(`# Esquema M3 claro · SchemeTonalSpot · semilla ${SEMILLA} · éxito base ${VERDE_EXITO}\n`);
console.log('| Rol | Hex | Tono HCT |');
console.log('|---|---|---|');
for (const [rol, h] of Object.entries(hex)) {
  console.log(`| ${rol} | ${h} | ${Math.round(Hct.fromInt(argbFromHex(h)).tone)} |`);
}
console.log('\n| Primer plano | Fondo | Contraste | Mínimo | OK | Uso |');
console.log('|---|---|---|---|---|---|');
for (const [a, b, min, uso] of PARES) {
  const r = contraste(hex[a], hex[b]);
  console.log(`| ${a} ${hex[a]} | ${b} ${hex[b]} | ${r.toFixed(2)}:1 | ${min || '—'} | ${r >= min ? 'sí' : 'NO'} | ${uso} |`);
}
// Capas de estado (presionado/enfoque 10 %, arrastre 16 %)
const presFilled = mezcla(hex.onPrimary, hex.primary, 0.10);
const arrFilled = mezcla(hex.onPrimary, hex.primary, 0.16);
const presTonal = mezcla(hex.onSecondaryContainer, hex.secondaryContainer, 0.10);
const presText = mezcla(hex.primary, hex.surface, 0.10);
console.log('\n| Capa de estado | Fondo resultante | Contraste del contenido |');
console.log('|---|---|---|');
console.log(`| filled presionado 10 % | ${presFilled} | ${contraste(hex.onPrimary, presFilled).toFixed(2)}:1 |`);
console.log(`| filled arrastre 16 % | ${arrFilled} | ${contraste(hex.onPrimary, arrFilled).toFixed(2)}:1 |`);
console.log(`| tonal presionado 10 % | ${presTonal} | ${contraste(hex.onSecondaryContainer, presTonal).toFixed(2)}:1 |`);
console.log(`| text presionado 10 % | ${presText} | ${contraste(hex.primary, presText).toFixed(2)}:1 |`);
const dis = mezcla(hex.onSurface, hex.surface, 0.38);
const disC = mezcla(hex.onSurface, hex.surface, 0.12);
console.log(`| deshabilitado M3 (38 % sobre 12 %) | ${disC} | ${contraste(dis, disC).toFixed(2)}:1 (por eso el proyecto NO lo usa) |`);

console.log('\nJSON para theme.ts:\n' + JSON.stringify(hex, null, 2));
