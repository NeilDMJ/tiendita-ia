import { Platform, type TextStyle, type ViewStyle } from 'react-native';

/**
 * Tokens de diseño — Material Design 3 (docs/diseno/00-sistema.md).
 * ÚNICO archivo de la app con valores de color: los componentes piden ROLES (`color.primary`…).
 * Esquema claro SchemeTonalSpot, semilla #769CDF; `success*` = rol personalizado armonizado.
 * Salida verificada de material-color-utilities: docs/diseno/m3/esquema-generado.md.
 * Prohibido en toda la app: gradientes, blur, textShadow y sombras fuera de `elevacion`.
 */
export const color = {
  primary: '#415F91',
  onPrimary: '#FFFFFF',
  primaryContainer: '#D6E3FF',
  onPrimaryContainer: '#284777',
  inversePrimary: '#AAC7FF',
  secondary: '#565F71',
  onSecondary: '#FFFFFF',
  secondaryContainer: '#DAE2F9',
  onSecondaryContainer: '#3E4759',
  tertiary: '#705575',
  onTertiary: '#FFFFFF',
  tertiaryContainer: '#FAD8FD',
  onTertiaryContainer: '#573E5C',
  error: '#BA1A1A',
  onError: '#FFFFFF',
  errorContainer: '#FFDAD6',
  onErrorContainer: '#93000A',
  surface: '#F9F9FF',
  surfaceDim: '#D9D9E0',
  surfaceBright: '#F9F9FF',
  surfaceContainerLowest: '#FFFFFF',
  surfaceContainerLow: '#F3F3FA',
  surfaceContainer: '#EDEDF4',
  surfaceContainerHigh: '#E7E8EE',
  surfaceContainerHighest: '#E2E2E9',
  onSurface: '#191C20',
  surfaceVariant: '#E0E2EC',
  onSurfaceVariant: '#44474E',
  outline: '#74777F',
  outlineVariant: '#C4C6D0',
  inverseSurface: '#2E3036',
  inverseOnSurface: '#F0F0F7',
  shadow: '#000000',
  scrim: '#000000',
  success: '#006D43',
  onSuccess: '#FFFFFF',
  successContainer: '#92F7BC',
  onSuccessContainer: '#005231',
} as const;

export type RolColor = keyof typeof color;

/** Hex `#RRGGBB` + alfa 0–1 → `rgba()`. Para capas de estado, ripple y scrim. */
export function conAlfa(hex: string, alfa: number): string {
  const limpio = hex.replace('#', '');
  const r = parseInt(limpio.slice(0, 2), 16);
  const g = parseInt(limpio.slice(2, 4), 16);
  const b = parseInt(limpio.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alfa})`;
}

/** Velo de bottom sheet modal y diálogo (M3: scrim al 32 %). */
export const scrim = conAlfa(color.scrim, 0.32);

/** Colores fijos de la cámara (excepción documentada en 01-cobrar §2.2: disparador y guía de encuadre). */
export const camara = {
  claro: color.surfaceContainerLowest,
  oscuro: color.inverseSurface,
} as const;

type Estilo = Pick<TextStyle, 'fontSize' | 'lineHeight' | 'fontWeight' | 'letterSpacing' | 'fontVariant'>;

/**
 * Escala tipográfica M3 con EXC-1: ningún texto < 16 sp.
 * Fuente del sistema (Roboto en Android, SF en iOS); siempre escalable.
 */
export const type = {
  displaySmall: { fontSize: 36, lineHeight: 44, fontWeight: '400' },
  headlineLarge: { fontSize: 32, lineHeight: 40, fontWeight: '500', fontVariant: ['tabular-nums'] },
  headlineSmall: { fontSize: 24, lineHeight: 32, fontWeight: '400' },
  titleLarge: { fontSize: 22, lineHeight: 28, fontWeight: '400' },
  titleMedium: { fontSize: 18, lineHeight: 26, fontWeight: '500' },
  titleSmall: { fontSize: 16, lineHeight: 24, fontWeight: '500' },
  bodyLarge: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  bodyLargePlus: { fontSize: 18, lineHeight: 26, fontWeight: '400' },
  bodyMedium: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  bodySmall: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  labelLarge: { fontSize: 16, lineHeight: 24, fontWeight: '500' },
  labelMedium: { fontSize: 16, lineHeight: 24, fontWeight: '500' },
  labelSmall: { fontSize: 16, lineHeight: 24, fontWeight: '500' },
  amount: { fontSize: 20, lineHeight: 28, fontWeight: '500', fontVariant: ['tabular-nums'] },
} as const satisfies Record<string, Estilo>;

/** Peso usado como señal no cromática de "activo / seleccionado". */
export const pesoActivo = '700' as const;

/** Escala de esquinas M3. */
export const shape = {
  none: 0,
  extraSmall: 4,
  small: 8,
  medium: 12,
  large: 16,
  extraLarge: 28,
  full: 9999,
} as const;

export type NivelElevacion = 'level0' | 'level1' | 'level2' | 'level3' | 'level4' | 'level5';

const SOMBRAS: Record<Exclude<NivelElevacion, 'level0'>, { dp: number; css: string }> = {
  level1: { dp: 1, css: '0px 1px 2px 0px rgba(0,0,0,0.30), 0px 1px 3px 1px rgba(0,0,0,0.15)' },
  level2: { dp: 3, css: '0px 1px 2px 0px rgba(0,0,0,0.30), 0px 2px 6px 2px rgba(0,0,0,0.15)' },
  level3: { dp: 6, css: '0px 1px 3px 0px rgba(0,0,0,0.30), 0px 4px 8px 3px rgba(0,0,0,0.15)' },
  level4: { dp: 8, css: '0px 2px 3px 0px rgba(0,0,0,0.30), 0px 6px 10px 4px rgba(0,0,0,0.15)' },
  level5: { dp: 12, css: '0px 4px 4px 0px rgba(0,0,0,0.30), 0px 8px 12px 6px rgba(0,0,0,0.15)' },
};

function sombra(nivel: Exclude<NivelElevacion, 'level0'>): ViewStyle {
  const s = SOMBRAS[nivel];
  return Platform.select<ViewStyle>({
    android: { elevation: s.dp, shadowColor: color.shadow },
    default: { boxShadow: s.css },
  });
}

/**
 * ÚNICA fuente de sombras (M3 niveles 0–5). Android: `elevation` nativa; iOS/web: `boxShadow`
 * (key + ambient). Solo sobre vistas con `backgroundColor` opaco. Nunca como adorno.
 */
export const elevacion: Record<NivelElevacion, ViewStyle> = {
  level0: Platform.select<ViewStyle>({ android: { elevation: 0 }, default: {} }),
  level1: sombra('level1'),
  level2: sombra('level2'),
  level3: sombra('level3'),
  level4: sombra('level4'),
  level5: sombra('level5'),
};

/** Opacidad de las capas de estado M3 (color del contenido del componente). */
export const estado = {
  hover: 0.08,
  focus: 0.1,
  pressed: 0.1,
  dragged: 0.16,
} as const;

/** Movimiento M3. Con movimiento reducido las duraciones pasan a 0. */
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

/** Medidas fijas de piezas M3 (no tocables salvo indicación). */
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
} as const;

/** Anillo de foco M3: 3 dp `secondary`, separado 2 dp. */
export const anilloFoco: ViewStyle = {
  outlineColor: color.secondary,
  outlineWidth: 3,
  outlineOffset: 2,
  outlineStyle: 'solid',
};
