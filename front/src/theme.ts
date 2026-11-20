import Storage from 'expo-sqlite/kv-store';
import { Appearance, Platform, type TextStyle, type ViewStyle } from 'react-native';

/**
 * Tokens de diseño — identidad "BookEase" aplicada a Tendero IA (docs/ui-ux/02-sistema-de-diseno.md).
 * ÚNICO archivo de la app con valores de color: los componentes piden ROLES (`color.primary`…).
 * Se conserva la estructura de roles de Material 3 (nombres, capas de estado, accesibilidad); cambian los valores.
 * Todos los pares texto/fondo cumplen WCAG AA (tabla de contrastes en el doc de sistema).
 * Prohibido en toda la app: blur, textShadow y sombras fuera de `elevacion`.
 * Gradiente: SOLO `gradienteMarca`, y solo en el logotipo y en 1–2 palabras clave del titular.
 */
export const colorClaro = {
  primary: '#1A56DB',
  onPrimary: '#FFFFFF',
  primaryContainer: '#E8F0FE',
  onPrimaryContainer: '#1543B0',
  inversePrimary: '#A9C4F9',
  secondary: '#4B5563',
  onSecondary: '#FFFFFF',
  secondaryContainer: '#E3E8F4',
  onSecondaryContainer: '#1F2937',
  /** Acento violeta de la marca (final del gradiente). */
  tertiary: '#5B3FD6',
  onTertiary: '#FFFFFF',
  tertiaryContainer: '#ECE7FD',
  onTertiaryContainer: '#3B2A8C',
  error: '#DC2626',
  onError: '#FFFFFF',
  errorContainer: '#FEE2E2',
  onErrorContainer: '#991B1B',
  surface: '#F5F7FB',
  surfaceDim: '#E5E9F2',
  surfaceBright: '#FFFFFF',
  surfaceContainerLowest: '#FFFFFF',
  surfaceContainerLow: '#FFFFFF',
  surfaceContainer: '#EEF1F7',
  surfaceContainerHigh: '#E8ECF4',
  surfaceContainerHighest: '#E2E7F0',
  onSurface: '#0F172A',
  surfaceVariant: '#E5E9F2',
  onSurfaceVariant: '#4B5563',
  outline: '#6B7280',
  outlineVariant: '#E5E7EB',
  inverseSurface: '#0F172A',
  inverseOnSurface: '#F5F7FB',
  shadow: '#0F172A',
  scrim: '#000000',
  /** Semánticos personalizados. `success` es #15803D (no #16A34A): con texto blanco este último solo da 3.3:1. */
  success: '#15803D',
  onSuccess: '#FFFFFF',
  successContainer: '#DCFCE7',
  onSuccessContainer: '#14532D',
  /** `warning` es #B45309 (no #D97706, 3.2:1 con blanco). Pendiente / por confirmar / poco stock. */
  warning: '#B45309',
  onWarning: '#FFFFFF',
  warningContainer: '#FEF3C7',
  onWarningContainer: '#78350F',
} as const;

export type RolColor = keyof typeof colorClaro;

/** Mismos roles, valores para modo oscuro. Todos los pares pasan WCAG AA (docs/ui-ux/contraste.mjs). */
export const colorOscuro: Record<RolColor, string> = {
  primary: '#7BA3F5',
  onPrimary: '#0B1F55',
  primaryContainer: '#16328A',
  onPrimaryContainer: '#DCE7FD',
  inversePrimary: '#1A56DB',
  secondary: '#B6BECC',
  onSecondary: '#1F2937',
  secondaryContainer: '#2A3446',
  onSecondaryContainer: '#E3E8F4',
  tertiary: '#B9A8FA',
  onTertiary: '#2A1B73',
  tertiaryContainer: '#3B2A8C',
  onTertiaryContainer: '#ECE7FD',
  error: '#F87171',
  onError: '#450A0A',
  errorContainer: '#7F1D1D',
  onErrorContainer: '#FEE2E2',
  surface: '#0B1220',
  surfaceDim: '#070C17',
  surfaceBright: '#243251',
  surfaceContainerLowest: '#111A2C',
  surfaceContainerLow: '#111A2C',
  surfaceContainer: '#17233A',
  surfaceContainerHigh: '#1D2A45',
  surfaceContainerHighest: '#243251',
  onSurface: '#E5E9F2',
  surfaceVariant: '#243251',
  onSurfaceVariant: '#A7B0C0',
  outline: '#7C879B',
  outlineVariant: '#2A3650',
  inverseSurface: '#E5E9F2',
  inverseOnSurface: '#0F172A',
  shadow: '#000000',
  scrim: '#000000',
  success: '#4ADE80',
  onSuccess: '#052E16',
  successContainer: '#14532D',
  onSuccessContainer: '#DCFCE7',
  warning: '#FBBF24',
  onWarning: '#451A03',
  warningContainer: '#78350F',
  onWarningContainer: '#FEF3C7',
};

// ---------------------------------------------------------------------------------------------
// Esquema activo (claro / oscuro)
// ---------------------------------------------------------------------------------------------
// `StyleSheet.create` congela los colores cuando se carga cada archivo, así que el esquema se decide UNA vez,
// aquí, al abrir la app: la preferencia guardada por la persona o, si eligió "sistema", la del teléfono.
// Cambiarla desde la app guarda la preferencia y reinicia la app (ver `utils/apariencia.ts`).

export type PreferenciaApariencia = 'sistema' | 'claro' | 'oscuro';
export const CLAVE_APARIENCIA = 'tendero-apariencia';

function leerPreferencia(): PreferenciaApariencia {
  try {
    const valor =
      Platform.OS === 'web'
        ? globalThis.localStorage?.getItem(CLAVE_APARIENCIA)
        : Storage.getItemSync(CLAVE_APARIENCIA);
    return valor === 'claro' || valor === 'oscuro' ? valor : 'sistema';
  } catch {
    return 'sistema';
  }
}

/** Lo que la persona eligió (para mostrarlo seleccionado en la hoja "Apariencia"). */
export const preferenciaApariencia: PreferenciaApariencia = leerPreferencia();

/** Lo que realmente se está usando ahora. */
export const esquemaActivo: 'claro' | 'oscuro' =
  preferenciaApariencia === 'sistema'
    ? Appearance.getColorScheme() === 'dark'
      ? 'oscuro'
      : 'claro'
    : preferenciaApariencia;

/** Roles de color vigentes. Los componentes siempre piden roles (`color.primary`), nunca valores. */
export const color: Record<RolColor, string> = esquemaActivo === 'oscuro' ? colorOscuro : colorClaro;

/** Color fijo de lo que va sobre el degradado de marca (blanco en ambos esquemas: 6:1 sobre #1D4ED8 y #5B3FD6). */
export const sobreMarca = '#FFFFFF';

/** Degradado de marca (azul → violeta, 90°). Uso restringido: logotipo y 1–2 palabras clave del titular. */
export const gradienteMarca = {
  colores: ['#1D4ED8', '#5B3FD6'],
  inicio: { x: 0, y: 0.5 },
  fin: { x: 1, y: 0.5 },
} as const;

/** Hex `#RRGGBB` + alfa 0–1 → `rgba()`. Para capas de estado, ripple y scrim. */
export function conAlfa(hex: string, alfa: number): string {
  const limpio = hex.replace('#', '');
  const r = parseInt(limpio.slice(0, 2), 16);
  const g = parseInt(limpio.slice(2, 4), 16);
  const b = parseInt(limpio.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alfa})`;
}

/** Velo de bottom sheet modal y diálogo (scrim al 32 %). */
export const scrim = conAlfa(color.scrim, 0.32);

/**
 * Colores FIJOS de la cámara (excepción documentada en 01-cobrar §2.2). La cámara es oscura en ambos esquemas,
 * por eso no usa los roles `inverse*` (que en modo oscuro se vuelven claros).
 */
export const camara = {
  claro: '#FFFFFF',
  oscuro: '#0F172A',
  /** Acento claro para anillos y enlaces sobre fondo oscuro. */
  acento: '#A9C4F9',
} as const;

/** Familias Inter (una por peso: en RN el peso va en el nombre de la fuente, no en `fontWeight`). */
export const fuente = {
  regular: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  semibold: 'Inter_600SemiBold',
  bold: 'Inter_700Bold',
  extrabold: 'Inter_800ExtraBold',
} as const;

type Estilo = Pick<TextStyle, 'fontFamily' | 'fontSize' | 'lineHeight' | 'letterSpacing' | 'fontVariant'>;

/**
 * Escala tipográfica con EXC-1: ningún texto < 16 sp (usuario con baja visión, una mano, poca práctica).
 * Titulares: peso 700–800 y tracking negativo (identidad). Cuerpo: Inter 400/500. Siempre escalable.
 * La jerarquía sale del TAMAÑO (16 · 18 · 20 · 22 · 24 · 32 · 40) y del peso, no solo del peso.
 */
export const type = {
  displaySmall: { fontFamily: fuente.extrabold, fontSize: 40, lineHeight: 46, letterSpacing: -1.2 },
  headlineLarge: { fontFamily: fuente.bold, fontSize: 32, lineHeight: 38, letterSpacing: -0.64, fontVariant: ['tabular-nums'] },
  headlineSmall: { fontFamily: fuente.bold, fontSize: 24, lineHeight: 30, letterSpacing: -0.24 },
  titleLarge: { fontFamily: fuente.semibold, fontSize: 22, lineHeight: 28 },
  titleMedium: { fontFamily: fuente.semibold, fontSize: 18, lineHeight: 26 },
  titleSmall: { fontFamily: fuente.semibold, fontSize: 16, lineHeight: 24 },
  bodyLarge: { fontFamily: fuente.regular, fontSize: 16, lineHeight: 26 },
  bodyLargePlus: { fontFamily: fuente.regular, fontSize: 20, lineHeight: 30 },
  bodyMedium: { fontFamily: fuente.regular, fontSize: 16, lineHeight: 24 },
  bodySmall: { fontFamily: fuente.regular, fontSize: 16, lineHeight: 24 },
  labelLarge: { fontFamily: fuente.semibold, fontSize: 16, lineHeight: 24 },
  labelMedium: { fontFamily: fuente.medium, fontSize: 16, lineHeight: 24 },
  labelSmall: { fontFamily: fuente.medium, fontSize: 16, lineHeight: 24 },
  amount: { fontFamily: fuente.bold, fontSize: 20, lineHeight: 28, fontVariant: ['tabular-nums'] },
} as const satisfies Record<string, Estilo>;

/** Peso usado como señal no cromática de "activo / seleccionado". Se esparce: `{ ...pesoActivo }`. */
export const pesoActivo = { fontFamily: fuente.bold } as const;

/** Escala de esquinas de la identidad: 6 (badges) · 10 (botones, inputs) · 16 (tarjetas) · full (píldoras). */
export const shape = {
  none: 0,
  extraSmall: 4,
  small: 6,
  medium: 10,
  large: 16,
  extraLarge: 20,
  full: 9999,
} as const;

export type NivelElevacion = 'level0' | 'level1' | 'level2' | 'level3' | 'level4' | 'level5';

const SOMBRAS: Record<Exclude<NivelElevacion, 'level0'>, { dp: number; css: string }> = {
  level1: { dp: 1, css: '0px 1px 2px 0px rgba(15,23,42,0.06)' },
  level2: { dp: 3, css: '0px 4px 12px 0px rgba(15,23,42,0.07)' },
  level3: { dp: 6, css: '0px 8px 24px 0px rgba(15,23,42,0.08)' },
  level4: { dp: 8, css: '0px 12px 28px 0px rgba(15,23,42,0.10)' },
  level5: { dp: 12, css: '0px 16px 40px 0px rgba(15,23,42,0.12)' },
};

function sombra(nivel: Exclude<NivelElevacion, 'level0'>): ViewStyle {
  const s = SOMBRAS[nivel];
  return Platform.select<ViewStyle>({
    android: { elevation: s.dp, shadowColor: color.shadow },
    default: { boxShadow: s.css },
  });
}

/**
 * ÚNICA fuente de sombras (niveles 0–5, suaves y difusas). Android: `elevation` nativa; iOS/web: `boxShadow`.
 * Solo sobre vistas con `backgroundColor` opaco. Nunca como adorno.
 */
export const elevacion: Record<NivelElevacion, ViewStyle> = {
  level0: Platform.select<ViewStyle>({ android: { elevation: 0 }, default: {} }),
  level1: sombra('level1'),
  level2: sombra('level2'),
  level3: sombra('level3'),
  level4: sombra('level4'),
  level5: sombra('level5'),
};

/** Opacidad de las capas de estado (color del contenido del componente). */
export const estado = {
  hover: 0.08,
  focus: 0.1,
  pressed: 0.1,
  dragged: 0.16,
} as const;

/** Movimiento. Con movimiento reducido las duraciones pasan a 0. */
export const motion = {
  easing: {
    emphasized: [0.2, 0, 0, 1],
    emphasizedDecelerate: [0.05, 0.7, 0.1, 1],
    emphasizedAccelerate: [0.3, 0, 0.8, 0.15],
    standard: [0.2, 0, 0, 1],
  },
  duration: {
    short2: 100,
    short4: 200,
    medium2: 300,
    medium4: 400,
  },
} as const satisfies {
  easing: Record<string, readonly [number, number, number, number]>;
  duration: Record<string, number>;
};

export const bordes = {
  fino: 1,
  grueso: 2,
  /** Borde izquierdo de la fila "Revisa". */
  acento: 4,
} as const;

/** Grid de 4 dp. */
export const espacio = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 24,
  xxl: 32,
} as const;

export const tactil = {
  minimo: 48,
  principal: 56, // botón principal, Extended FAB, icon buttons de cámara
  separacion: 8,
  disparador: 72, // obturador de la cámara
} as const;

export const iconos = {
  chico: 20, // dentro de chips
  linea: 24, // botones, listas, barras, navigation bar
  grande: 48, // ilustrativo en estados vacíos / comprobante
} as const;

/** Medidas fijas de piezas (no tocables salvo indicación). */
export const medidas = {
  barraSuperior: 64,
  barraNavegacion: 80,
  indicadorNavAncho: 64,
  indicadorNavAlto: 32,
  chip: 32,
  progresoAlto: 8, // EXC-5
  progresoParada: 4,
  numeroFoto: 32,
  asaAncho: 32,
  asaAlto: 4,
  badge: 24,
  franjaSimulacion: 48,
  bordeDisparador: 4,
  miniaturaFoto: 200,
  barraCamaraInferior: 120,
  tarjetaAtajoAlto: 96,
  tarjetaAtajoAncho: 140, // base flexible: con letra grande se apilan
  filaVenta: 64,
  hojaAnchoMaximo: 640,
  dialogoAnchoMinimo: 280,
  dialogoAnchoMaximo: 560,
  puntoEscribiendo: 8, // puntos del indicador "Escribiendo…" del chat
  /** Ancho máximo del contenido de una pantalla (web/tablet): evita tarjetas de 1400 px. */
  contenidoAnchoMaximo: 640,
} as const;

/** Anillo de foco: 3 dp `secondary`, separado 2 dp. */
export const anilloFoco: ViewStyle = {
  outlineColor: color.secondary,
  outlineWidth: 3,
  outlineOffset: 2,
  outlineStyle: 'solid',
};
