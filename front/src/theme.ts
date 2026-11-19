/**
 * Tokens de diseño — estética FLAT estricta.
 * Prohibido en toda la app: shadow*, elevation > 0, gradientes, blur, glow.
 * Jerarquía solo con espaciado, bordes sólidos 1–2px, tipografía y color plano.
 * Contrastes calculados sobre #FFFFFF (WCAG).
 */
export const colores = {
  fondo: '#FFFFFF',
  superficie: '#F5F5F5',
  texto: '#111111', // 18.9:1
  textoSecundario: '#4A4A4A', // 8.9:1
  borde: '#767676', // 4.5:1 — bordes de controles
  divisor: '#D6D6D6', // solo separadores no esenciales
  acento: '#0B5FFF', // 5.1:1 — acción principal (texto blanco encima 5.1:1)
  sobreAcento: '#FFFFFF',
  peligro: '#B00020', // 7.3:1 — errores y destructivo (siempre con icono + texto)
  sobrePeligro: '#FFFFFF',
  exito: '#1B5E20', // 7.9:1 — venta registrada, guardado (blanco encima 7.9:1)
  sobreExito: '#FFFFFF',
  oscuro: '#111111', // barras de cámara, EtiquetaSimulacion (blanco encima 18.9:1)
  sobreOscuro: '#FFFFFF',
  acentoPresionado: '#0848C2', // blanco encima 7.7:1
  peligroPresionado: '#8A0019', // blanco encima 10.0:1
  foco: '#111111',
  deshabilitadoFondo: '#E0E0E0',
  deshabilitadoTexto: '#595959', // 5.3:1 sobre #E0E0E0
} as const;

export const bordes = {
  fino: 1,
  grueso: 2,
} as const;

export const radios = {
  recto: 0,
  chico: 4,
  medio: 8,
} as const;

export const espacio = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 24,
  xxl: 32,
} as const;

export const tipografia = {
  cuerpo: { fontSize: 16, lineHeight: 24, fontWeight: '400' as const },
  cuerpoGrande: { fontSize: 18, lineHeight: 26, fontWeight: '400' as const },
  nombreProducto: { fontSize: 18, lineHeight: 26, fontWeight: '700' as const },
  etiqueta: { fontSize: 16, lineHeight: 22, fontWeight: '700' as const },
  monto: { fontSize: 20, lineHeight: 26, fontWeight: '700' as const },
  montoGrande: { fontSize: 32, lineHeight: 40, fontWeight: '700' as const },
  subtitulo: { fontSize: 20, lineHeight: 26, fontWeight: '700' as const },
  titulo: { fontSize: 24, lineHeight: 30, fontWeight: '700' as const },
} as const;

export const tactil = {
  minimo: 48,
  principal: 56, // alto del botón de acción principal (barra inferior)
  separacion: 8,
  disparador: 72, // botón circular de la cámara
} as const;

export const iconos = {
  chico: 20, // dentro de chips
  linea: 24, // en línea con texto
  pestana: 28,
  camara: 32,
  grande: 48, // ilustrativo en estados vacíos / comprobante
} as const;

/** Alturas fijas de piezas de layout (no tocables). */
export const medidas = {
  barraSuperior: 56,
  barraPestanas: 72,
  chip: 32,
  segmentoPasos: 8,
  franjaSimulacion: 40,
  bordeDisparador: 4,
  miniaturaFoto: 200,
  barraCamaraInferior: 120,
  tarjetaAtajoAlto: 96,
  tarjetaAtajoAncho: 140, // base flexible: con letra grande se apilan
} as const;

/**
 * Anillo de foco (teclado externo / lector): contorno sólido 2px separado 2px del control,
 * distinguible aun cuando el borde del control ya es #111. Sin glow.
 */
export const anilloFoco = {
  outlineColor: colores.foco,
  outlineWidth: bordes.grueso,
  outlineOffset: bordes.grueso,
  outlineStyle: 'solid' as const,
};
