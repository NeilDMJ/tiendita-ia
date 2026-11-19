# 00 · Sistema de diseño — App del Tendero

> Autor: `ui-ux-movil` · Implementa: `frontend-implementador` · Audita: `revisor-ui-flat` + `revisor-accesibilidad-hci`
> Stack: Expo SDK 58 + React Native, `StyleSheet` + `src/theme.ts`, iconos `MaterialCommunityIcons` de `@expo/vector-icons`. **Sin librerías de UI.**
> Usuario: **tendero / dueño** de la tienda (adulto, posiblemente mayor, poca experiencia digital, usa el teléfono con una mano mientras atiende el mostrador).

---

## 1. Concepto y enfoque

Una sola "gramática" visual para toda la app, pensada para el mostrador:

- **Flat estricto:** la jerarquía sale de espaciado, bordes sólidos (1 px normal, 2 px seleccionado/foco/estado) y peso tipográfico. Cero `shadow*`, `elevation`, `textShadow*`, gradientes, blur u opacidades decorativas.
- **Tres colores con significado, y nada más:** azul = "esto es lo que haces ahora" (acción principal), rojo = "esto está mal o no se puede deshacer", verde = "quedó guardado". Todo lo demás es negro/gris sobre blanco. Cada color **siempre** va acompañado de icono + texto.
- **Pulgar primero:** la acción principal de cada pantalla vive en una barra inferior fija (tercio inferior), a ancho completo y 56 px de alto.
- **Palabras de tienda:** "Cobrar", "Venta", "Pieza", "Revisa", "Corte de caja". Nunca "modelo", "IA", "inferencia", "agente", "token", "SKU" (al usuario se le dice "código" o "producto del catálogo").

---

## 2. Tokens finales

### 2.1 Colores (cambios respecto a `theme.ts` marcados con **NUEVO**)

| Token (`colores.*`) | Hex | Uso | Estado |
|---|---|---|---|
| `fondo` | `#FFFFFF` | Fondo de pantalla, filas, tarjetas | existe |
| `superficie` | `#F5F5F5` | Zonas agrupadas, barra de total, fila "Revisa" | existe |
| `texto` | `#111111` | Texto principal, bordes de estado "Revisa", foco | existe |
| `textoSecundario` | `#4A4A4A` | Texto de apoyo, etiquetas de campo, pestaña inactiva | existe |
| `borde` | `#767676` | Borde de controles (campos, botón secundario, stepper) **solo sobre `fondo`** | existe |
| `divisor` | `#D6D6D6` | Separadores decorativos entre filas (no esenciales) | existe |
| `acento` | `#0B5FFF` | Botón primario, pestaña activa, enlaces | existe |
| `sobreAcento` | `#FFFFFF` | Texto/icono sobre `acento` | existe |
| `peligro` | `#B00020` | Error, dato obligatorio faltante, eliminar | existe |
| `sobrePeligro` | `#FFFFFF` | Texto/icono sobre `peligro` | existe |
| `exito` | `#1B5E20` | Venta registrada, guardado | **NUEVO** |
| `sobreExito` | `#FFFFFF` | Texto/icono sobre `exito` | **NUEVO** |
| `oscuro` | `#111111` | Barras sobre la vista de cámara, `EtiquetaSimulacion` | **NUEVO** (alias semántico de `texto` para fondos) |
| `sobreOscuro` | `#FFFFFF` | Texto/icono sobre `oscuro` | **NUEVO** |
| `foco` | `#111111` | Anillo de foco 2 px | existe |
| `deshabilitadoFondo` | `#E0E0E0` | Fondo de botón deshabilitado | existe |
| `deshabilitadoTexto` | `#595959` | Texto/icono deshabilitado | existe |

**No se agrega un color "amarillo/ámbar" para confianza baja.** Confianza baja se marca con estructura (borde 2 px `texto` + fondo `superficie` + icono + palabra "Revisa"), así la paleta queda en 1 acento de acción (azul) + 2 semánticos (rojo/verde), cumpliendo "máximo 1–2 acentos".

### 2.2 Tabla de contraste (WCAG 2.x, luminancia relativa calculada)

Luminancias: `#FFFFFF` 1.000 · `#F5F5F5` 0.913 · `#E0E0E0` 0.746 · `#111111` 0.0056 · `#4A4A4A` 0.0685 · `#595959` 0.0999 · `#767676` 0.181 · `#0B5FFF` 0.155 · `#B00020` 0.093 · `#1B5E20` 0.083.

| Primer plano | Fondo | Contraste | Requisito | Resultado | Dónde se usa |
|---|---|---|---|---|---|
| `#111111` texto | `#FFFFFF` | **18.9:1** | 4.5 | AAA | Texto general |
| `#111111` texto | `#F5F5F5` | **17.3:1** | 4.5 | AAA | Texto en superficie |
| `#4A4A4A` secundario | `#FFFFFF` | **8.9:1** | 4.5 | AAA | Etiquetas, ayudas |
| `#4A4A4A` secundario | `#F5F5F5` | **8.1:1** | 4.5 | AAA | Ayudas en superficie |
| `#767676` borde | `#FFFFFF` | **4.5:1** | 3.0 (no-texto) | AA | Borde de controles |
| `#767676` borde | `#F5F5F5` | **4.2:1** | 3.0 (no-texto) | AA | Borde de campo dentro de superficie. **Nunca como texto aquí** |
| `#FFFFFF` | `#0B5FFF` acento | **5.1:1** | 4.5 | AA | Texto de botón primario |
| `#0B5FFF` acento | `#FFFFFF` | **5.1:1** | 4.5 | AA | Enlaces, icono de pestaña activa, botón secundario de acento |
| `#0B5FFF` acento | `#F5F5F5` | **4.7:1** | 4.5 | AA | Enlace dentro de superficie |
| `#FFFFFF` | `#B00020` peligro | **7.3:1** | 4.5 | AAA | Botón peligro |
| `#B00020` peligro | `#FFFFFF` | **7.3:1** | 4.5 | AAA | Texto/icono de error |
| `#B00020` peligro | `#F5F5F5` | **6.7:1** | 4.5 | AA | Error dentro de superficie |
| `#FFFFFF` | `#1B5E20` éxito | **7.9:1** | 4.5 | AAA | Encabezado de comprobante |
| `#1B5E20` éxito | `#FFFFFF` | **7.9:1** | 4.5 | AAA | Texto/icono de éxito |
| `#1B5E20` éxito | `#F5F5F5` | **7.2:1** | 4.5 | AAA | Éxito en superficie |
| `#595959` deshab. | `#E0E0E0` | **5.3:1** | 4.5 | AA | Botón deshabilitado (se mantiene legible a propósito) |
| `#FFFFFF` | `#111111` oscuro | **18.9:1** | 4.5 | AAA | Barras de cámara, `EtiquetaSimulacion` |
| `#D6D6D6` divisor | `#FFFFFF` | 1.5:1 | — | decorativo | Solo separadores; ninguna información depende de él |

Pares **prohibidos** (no pasan): `#767676` como texto sobre `#F5F5F5` (4.2), cualquier texto `#D6D6D6`, `#0B5FFF` sobre `#E0E0E0` (3.9).

### 2.3 Bordes, radios, espaciado, táctil

| Token | Valor | Uso |
|---|---|---|
| `bordes.fino` | 1 | Campos, filas, botón secundario, tarjetas |
| `bordes.grueso` | 2 | Foco, seleccionado, error, estado "Revisa", avisos, barra inferior |
| `radios.recto` | 0 | Barras fijas (superior/inferior), franjas de aviso |
| `radios.chico` | 4 | Etiquetas (chips), indicador de confianza |
| `radios.medio` | 8 | Botones, campos, tarjetas, stepper |
| `espacio` | 4 · 8 · 12 · 16 · 24 · 32 | Márgen lateral de pantalla = 16; entre bloques = 24; dentro de componentes = 8/12 |
| `tactil.minimo` | 48 | Toda área tocable ≥ 48×48 (usar `hitSlop` si el dibujo es menor) |
| `tactil.principal` | 56 | **NUEVO** — alto del botón de acción principal (barra inferior) |
| `tactil.separacion` | 8 | Separación mínima entre áreas tocables |

**Excepción documentada — disparador de cámara** (`tactil.disparador = 72`, `medidas.bordeDisparador = 4`): es el único control circular de la app y el único con borde de 4 px. Círculo 72×72 relleno `sobreOscuro #FFFFFF`, borde 4 px `oscuro #111111` y contorno exterior sólido 2 px `#FFFFFF` (para que el borde oscuro se distinga sobre la barra `#111`). Se justifica porque es la acción principal de la cámara, se toca a ciegas con el pulgar mientras se mira el mostrador y sigue la convención universal de "obturador". Al tocar, el borde pasa a `acento` y el texto debajo cambia a "Tomando foto…" (no solo color). Sin sombra ni brillo.

### 2.4 Tipografía (fuente del sistema; `allowFontScaling` activo siempre)

| Token | Tamaño / alto de línea / peso | Uso | Estado |
|---|---|---|---|
| `cuerpo` | 16 / 24 / 400 | Texto general (mínimo absoluto) | existe |
| `cuerpoGrande` | 18 / 26 / 400 | Nombre de producto en fila, mensajes de aviso | existe |
| `etiqueta` | 16 / 22 / 700 | Botones, etiquetas de campo, chips | existe |
| `monto` | 20 / 26 / 700 | Precios, subtotales | existe |
| `montoGrande` | 32 / 40 / 700 | Total de la venta | **NUEVO** |
| `titulo` | 24 / 30 / 700 | Título de pantalla | existe |
| `subtitulo` | 20 / 26 / 700 | Títulos de sección y de aviso | **NUEVO** |

Reglas: nunca < 16 px (incluye etiquetas de la barra de pestañas, ver §5). Montos con `fontVariant: ['tabular-nums']` para que el total no "baile". Con letra del sistema al 200 %, los textos **envuelven** (no `numberOfLines` en montos ni mensajes de error); solo los nombres de producto pueden truncarse a 2 líneas con el nombre completo en `accessibilityLabel`.

### 2.5 Iconografía

`MaterialCommunityIcons`, 24 px en línea con texto, 28 px en pestañas, 32 px en botones de cámara. **Siempre** con texto visible al lado o debajo; el icono lleva `accessibilityElementsHidden` / `importantForAccessibility="no"` porque el texto ya lo describe.

| Significado | Icono |
|---|---|
| Error | `alert-circle` |
| Revisa / confianza baja | `help-circle` |
| Confianza alta | `check-circle` |
| Éxito | `check-circle` |
| Info | `information` |
| Sin conexión | `wifi-off` |
| Tiempo agotado | `timer-sand` |
| Eliminar | `trash-can-outline` |
| Deshacer | `undo` |
| Simulación | `flask-outline` |
| Cámara / tomar foto | `camera` |
| Galería | `image-multiple` |
| Caja (asistente) | `cash-register` |

### 2.6 Movimiento

Sin animaciones decorativas. Permitidas solo: indicador de actividad (`ActivityIndicator`) y aparición del aviso de "deshacer". Si `AccessibilityInfo.isReduceMotionEnabled()` es `true`, nada se desliza: aparece/desaparece directo. Duración máxima 150 ms.

### 2.7 Foco

En RN táctil el foco visible aplica a teclado externo / TV / lectores. Cada componente tocable acepta un estado `enfocado` (vía `onFocus`/`onBlur` del `Pressable`) que dibuja **borde 2 px `foco`** con `padding` compensado (−1 px) para no mover el layout. Nunca usar `outline` con glow. Implementado como token `anilloFoco` en `theme.ts`: contorno sólido 2 px `foco` separado 2 px del control (`outlineOffset`), para que se distinga incluso en controles cuyo borde ya es `#111` (botón secundario).

---

## 3. Componentes base

Convención general para todos:
- Archivo kebab-case en `src/components/` (ej. `boton.tsx`), export nombrado en PascalCase.
- Tocables con `Pressable`; estado presionado = **cambio de color de fondo plano** (no opacidad, no escala, no ripple con sombra). En Android `android_ripple` **no** se usa.
- Todos aceptan `testID?: string` y `style?: StyleProp<ViewStyle>` (solo para márgenes externos).

---

### 3.1 `Boton`

**Anatomía** `[icono 24 opc.] [texto etiqueta]` centrados, o `[ActivityIndicator] [texto de carga]`.

**Medidas:** alto mínimo 48 (variante `tamano="principal"` = 56), padding horizontal 16, gap icono-texto 8, radio 8, ancho completo por defecto en barras inferiores; texto puede envolver a 2 líneas (alto crece).

| Variante | Fondo | Borde | Texto/icono | Presionado (fondo) |
|---|---|---|---|---|
| `primario` | `acento` | — | `sobreAcento` | `#0848C2` (blanco encima 7.7:1) |
| `secundario` | `fondo` | 2 px `texto` | `texto` | `superficie` |
| `peligro` | `fondo` | 2 px `peligro` | `peligro` | `superficie` (rojo sobre F5 6.7:1) |
| `peligroLleno` | `peligro` | — | `sobrePeligro` | `#8A0019` (blanco 10.0:1) |
| `texto` (enlace) | transparente | — | `acento`, subrayado | `superficie` |
| deshabilitado (cualquiera) | `deshabilitadoFondo` | — | `deshabilitadoTexto` | sin cambio |
| cargando | igual a su variante | igual | spinner del color de texto + `textoCargando` | sin cambio, no tocable |

> `peligroLleno` solo para la confirmación final de algo destructivo (diálogo). En listas, eliminar usa `peligro` contorneado o icono+texto.
> Nuevos colores de presionado: `acentoPresionado #0848C2` y `peligroPresionado #8A0019` (**NUEVOS**, ver §5).

**Props**
```ts
type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'peligroLleno' | 'texto';
interface BotonProps {
  texto: string;
  onPress: () => void;
  variante?: VarianteBoton;          // default 'primario'
  icono?: NombreIcono;               // MaterialCommunityIcons
  tamano?: 'normal' | 'principal';   // 48 | 56
  deshabilitado?: boolean;
  motivoDeshabilitado?: string;      // se lee en accessibilityHint: "Corrige 1 producto para continuar"
  cargando?: boolean;
  textoCargando?: string;            // "Guardando venta…"
  anchoCompleto?: boolean;           // default true
  accessibilityHint?: string;
}
```

**Accesibilidad:** `accessibilityRole="button"`, `accessibilityLabel={texto}`, `accessibilityState={{ disabled, busy: cargando }}`. Deshabilitado **sigue siendo enfocable** por lector y anuncia `motivoDeshabilitado` como hint (el usuario sabe *por qué* no puede). Mientras `cargando`, no dispara `onPress` (evita doble cobro).

---

### 3.2 `Campo` (texto y numérico)

**Anatomía**
```
Etiqueta (etiqueta 16 Bold, textoSecundario→texto)         * Obligatorio
┌───────────────────────────────────────────┐
│ $ │ 18.00                                 │   ← prefijo opcional ("$", "pz")
└───────────────────────────────────────────┘
(i) Ayuda opcional (cuerpo 16, textoSecundario)
(!) Mensaje de error (cuerpo 16 Bold, peligro)   ← reemplaza a la ayuda
```

**Medidas:** caja alto mín. 48, padding horizontal 12, radio 8, etiqueta→caja 4, caja→mensaje 4, separación entre campos 16. Texto de entrada `cuerpoGrande` (18).

| Estado | Borde | Fondo | Extra |
|---|---|---|---|
| normal | 1 px `borde` | `fondo` | — |
| enfocado | 2 px `acento` | `fondo` | — |
| error | 2 px `peligro` | `fondo` | icono `alert-circle` + mensaje en rojo debajo |
| deshabilitado | 1 px `divisor` | `deshabilitadoFondo` | texto `deshabilitadoTexto` |
| solo lectura | sin borde | `superficie` | texto `texto` |

**Numérico:** `keyboardType="decimal-pad"` (montos) o `"number-pad"` (piezas), `inputMode` igual. Acepta coma o punto; formatea a 2 decimales al perder foco. Prefijo `$` visible fuera del texto editable.

**Validación:** en tiempo real *después* del primer `onBlur` (no grita mientras escribe). Mensajes concretos: "Escribe el precio. Ej. 18.50", "El precio no puede ser 0".

**Props**
```ts
interface CampoProps {
  etiqueta: string;
  valor: string;
  onCambiar: (v: string) => void;
  tipo?: 'texto' | 'moneda' | 'entero';
  prefijo?: string;            // '$'
  sufijo?: string;             // 'pz'
  placeholder?: string;        // solo ejemplo, nunca reemplaza la etiqueta
  ayuda?: string;
  error?: string | null;
  obligatorio?: boolean;
  deshabilitado?: boolean;
  autoFocus?: boolean;
  onBlur?: () => void;
}
```

**Accesibilidad:** `accessibilityLabel={etiqueta + (obligatorio ? ', obligatorio' : '')}`; con error: `accessibilityHint={error}` y el mensaje con `accessibilityLiveRegion="polite"` (Android) / `AccessibilityInfo.announceForAccessibility(error)` (iOS) al aparecer. La etiqueta visible siempre está; el placeholder nunca es la etiqueta.

---

### 3.3 `StepperCantidad` (+/−)

**Anatomía** `[ − ] [ 2 pz ] [ + ]` en un solo grupo con borde.

**Medidas:** botones 48×48 cada uno, valor central mín. 56 de ancho × 48 alto, total ≈ 152×48. Borde exterior 1 px `borde`, radio 8, divisores internos 1 px `borde`. Iconos `minus` / `plus` 24 px `texto`. Valor `monto` (20 Bold, tabular).

| Estado | Comportamiento |
|---|---|
| normal | − y + activos |
| en mínimo (1) | el **−** se convierte en icono `trash-can-outline` rojo con texto oculto "Quitar"; tocarlo dispara `onQuitar` (con deshacer, no diálogo) |
| en máximo (stock) | + deshabilitado (`deshabilitadoFondo`), y debajo texto "Solo hay 3 en existencia" con `information` |
| presionado | fondo `superficie` |
| edición directa | tocar el número abre teclado numérico (`number-pad`) para escribir "12" sin 12 toques |

**Props**
```ts
interface StepperCantidadProps {
  valor: number;
  onCambiar: (n: number) => void;
  minimo?: number;          // default 1
  maximo?: number;          // stock disponible, opcional
  unidad?: 'pz' | 'kg' | 'paq';
  onQuitar?: () => void;    // si se pasa, en mínimo el − se vuelve "Quitar"
  nombreProducto: string;   // para etiquetas accesibles
}
```

**Accesibilidad:** el grupo es `accessibilityRole="adjustable"` con `accessibilityLabel={`Cantidad de ${nombreProducto}`}`, `accessibilityValue={{ now: valor, text: `${valor} piezas` }}` y `onAccessibilityAction` para `increment`/`decrement` (gesto de deslizar arriba/abajo en VoiceOver/TalkBack). Los botones individuales: "Quitar una pieza de Pan blanco", "Agregar una pieza de Pan blanco".

---

### 3.4 `Aviso` (error / éxito / info / sin conexión / tiempo agotado)

**Anatomía**
```
┌─(borde 2px color del tipo)──────────────────────┐
│ [icono 24]  Título (subtitulo 20 Bold)           │
│             Mensaje humano (cuerpoGrande 18)     │
│             [Acción principal]  [Acción 2]       │
└──────────────────────────────────────────────────┘
```

**Medidas:** padding 16, gap icono-texto 12, radio 8 (en modo `franja` radio 0 y solo borde inferior 2 px), botones de acción 48 alto, separados 8.

| Tipo | Borde / icono / color del título | Icono | Fondo |
|---|---|---|---|
| `error` | `peligro` | `alert-circle` | `fondo` |
| `exito` | `exito` | `check-circle` | `fondo` |
| `info` | `texto` | `information` | `superficie` |
| `sinConexion` | `texto` | `wifi-off` | `superficie` |
| `tiempo` | `texto` | `timer-sand` | `superficie` |

> El cuerpo del mensaje siempre en `texto` (#111), solo el título e icono toman el color semántico. Así el rojo/verde nunca es el único portador de significado.
> Se recomienda que la `AvisoConexion` existente use `sinConexion` (borde `texto`) en lugar de `peligro`: no tener internet no es un error del usuario y el rojo genera alarma innecesaria; el mensaje ya tranquiliza ("se guarda y se enviará").

**Props**
```ts
type TipoAviso = 'error' | 'exito' | 'info' | 'sinConexion' | 'tiempo';
interface AvisoProps {
  tipo: TipoAviso;
  titulo: string;
  mensaje?: string;
  accion?: { texto: string; onPress: () => void; icono?: NombreIcono };
  accionSecundaria?: { texto: string; onPress: () => void };
  modo?: 'tarjeta' | 'franja';   // franja = ancho completo arriba de la pantalla
  onCerrar?: () => void;         // muestra botón "Cerrar" (48×48, icono close + texto oculto)
}
```

**Accesibilidad:** `error`/`sinConexion`/`tiempo` → `accessibilityRole="alert"`; `exito`/`info` → `accessibilityLiveRegion="polite"`. Al montarse un error se anuncia "Error: {titulo}. {mensaje}". El foco del lector se mueve al aviso cuando bloquea el flujo (`AccessibilityInfo.setAccessibilityFocus`).

---

### 3.5 `IndicadorConfianza`

Comunica qué tan segura está la app de lo que detectó. Al usuario **nunca** se le muestra un porcentaje ni la palabra "confianza".

| Nivel | Regla | Icono | Texto visible | Estilo |
|---|---|---|---|---|
| `alta` | `confianza >= 0.6` | `check-circle` (`exito`) | "Detectado" | chip: sin borde, texto `textoSecundario` 16 Bold |
| `baja` | `confianza < 0.6` | `help-circle` (`texto`) | "Revisa" | chip: borde 2 px `texto`, fondo `fondo`, texto `texto` 16 Bold |
| `falta` | `sku == null` o `precio_unitario == null` | `alert-circle` (`peligro`) | "Falta precio" / "Elige producto" | chip: borde 2 px `peligro`, texto `peligro` 16 Bold |
| `manual` | agregado o corregido por el tendero | `pencil` (`textoSecundario`) | "Tú lo pusiste" | chip: sin borde, `textoSecundario` |

`falta` tiene prioridad sobre `baja`. Umbral en constante `UMBRAL_CONFIANZA = 0.6` en `src/constants.ts`.

**Medidas:** alto 32 (no tocable por sí mismo; la fila es la que se toca), padding horizontal 8, radio 4, icono 20 + gap 4.

**Props**
```ts
type NivelConfianza = 'alta' | 'baja' | 'falta' | 'manual';
interface IndicadorConfianzaProps {
  nivel: NivelConfianza;
  textoFalta?: string;     // 'Falta precio' | 'Elige producto'
}
export function nivelDeItem(item: ItemEditable): NivelConfianza; // helper puro, testeable
```

**Accesibilidad:** el chip no es un elemento separado para el lector; su texto se integra en el `accessibilityLabel` de la fila ("…, revisa este producto" / "…, falta precio").

---

### 3.6 `EtiquetaSimulacion`

Obligatoria (bases) en cualquier pantalla o dato que no sea real: pago digital simulado, video promocional simulado, datos de demo.

**Anatomía:** chip `[flask-outline] SIMULACIÓN` fondo `oscuro`, texto `sobreOscuro` 16 Bold, radio 4, padding 4×8, alto 32.
Variante `franja`: ancho completo bajo el encabezado, alto 40, texto "Simulación: este cobro no mueve dinero real".

```ts
interface EtiquetaSimulacionProps {
  modo?: 'chip' | 'franja';
  detalle?: string;   // texto de la franja
}
```

**Accesibilidad:** `accessibilityRole="text"`, label "Simulación. {detalle}". Debe ser lo primero que lea el lector en la pantalla simulada.

---

### 3.7 `BarraPasos`

Muestra en qué parte del recorrido va el tendero (Nielsen #1).

**Anatomía** (texto siempre visible, no solo puntos):
```
Paso 2 de 3 · Revisa los productos
[■■■■■■■■■■][■■■■■■■■■■][□□□□□□□□□□]
 Foto ✓       Revisar      Listo
```
- Línea 1: "Paso X de N · {nombre del paso}" (`etiqueta` 16 Bold, `texto`).
- Línea 2: N segmentos de 8 px de alto, gap 4. Completado = relleno `texto`; actual = relleno `acento`; pendiente = borde 1 px `borde`, fondo `fondo`.
- Línea 3 (opcional, se oculta si no cabe con letra grande): nombre de cada paso, 16 px; el completado con `check` 16.

**Medidas:** padding 16 horizontal, 8 vertical; alto total ≈ 64–80.

```ts
interface BarraPasosProps {
  pasos: string[];        // ['Foto', 'Revisar', 'Listo']
  actual: number;         // índice 0-based
  mostrarNombres?: boolean;
}
```

**Accesibilidad:** `accessibilityRole="progressbar"`, `accessibilityLabel="Paso 2 de 3, Revisar"`, `accessibilityValue={{ min: 1, max: N, now: actual + 1 }}`. Los segmentos van ocultos al lector.

---

### 3.8 `FilaProducto`

Fila densa para listas de carrito, inventario y revisión.

**Anatomía**
```
┌──────────────────────────────────────────────────────────┐
│ Refresco de cola 600 ml                     $36.00       │  ← nombre (18 Bold, 2 líneas máx) · subtotal (monto 20)
│ $18.00 c/u  ·  [✓ Detectado]                             │  ← precio unitario (16, secundario) · IndicadorConfianza
│ [ − ][ 2 pz ][ + ]                         [Editar]      │  ← StepperCantidad · Boton 'texto'
└──────────────────────────────────────────────────────────┘
```
- Línea 3 izquierda: stepper; derecha: "Editar" (abre hoja de edición: nombre/producto del catálogo, precio).
- Separación entre filas: divisor 1 px `divisor` (modo normal).

**Medidas:** padding 12 vertical / 16 horizontal; alto mín. ≈ 128 en modo editable; en modo `soloLectura` (comprobante) ≈ 56 (una línea: "2 × Refresco…  $36.00").

| Estado | Fondo | Borde | Extra |
|---|---|---|---|
| normal | `fondo` | divisor inferior 1 px | — |
| revisa (confianza baja) | `superficie` | 2 px `texto` en los 4 lados, radio 8, margen 8 entre filas | chip "Revisa" |
| falta dato | `fondo` | 2 px `peligro` en los 4 lados, radio 8 | chip "Falta precio"; el subtotal muestra "— —" y debajo botón `peligro` "Poner precio" (48) en lugar de "Editar" |
| agotado / sin stock | `fondo` | divisor | + deshabilitado, texto "Sin existencia" con `alert-circle` en `peligro` |
| eliminado | la fila desaparece; aparece `Aviso` deshacer (ver 01-cobrar) | | |

```ts
interface FilaProductoProps {
  nombre: string;
  precioUnitario: number | null;
  cantidad: number;
  nivel: NivelConfianza;
  unidad?: 'pz' | 'kg' | 'paq';
  maximo?: number;
  modo?: 'editable' | 'soloLectura';
  onCambiarCantidad?: (n: number) => void;
  onEditar?: () => void;
  onQuitar?: () => void;
}
```

**Accesibilidad:** la fila no es un único botón (contiene controles); el bloque de texto es un `View accessible` con label "Refresco de cola 600 ml, 2 piezas a 18 pesos, subtotal 36 pesos, detectado". Los montos se leen en palabras ("36 pesos", no "$36.00") usando el helper de `formato-moneda.ts` con variante `paraLector`.

---

### 3.9 `TarjetaAccion` (confirmaciones dentro del chat)

Para acciones críticas que propone el asistente (`AccionAsistente`: `confirmar_venta`, `confirmar_alta`, `aprobar_promo`, `abrir_pantalla`).

**Anatomía**
```
┌─ borde 2px texto ── radio 8 ─────────────────────────┐
│ [cash-register] Caja propone:            [SIMULACIÓN?]│ ← 16 Bold, secundario
│ Cobrar venta de 3 productos                           │ ← subtitulo 20 Bold (titulo de la acción)
│ ───────────────────────────────────────────── (1px)   │
│ 2 × Refresco de cola 600 ml            $36.00         │ ← resumen (máx 4 filas + "y 2 más")
│ 1 × Pan blanco grande                  $52.00         │
│ Total                                  $88.00         │ ← monto 20 Bold
│ ───────────────────────────────────────────────────── │
│ [ Revisar y editar ]  [  Confirmar cobro  ]           │ ← secundario | primario, 48 alto
└───────────────────────────────────────────────────────┘
```
- Si no caben lado a lado (letra grande), los botones se apilan: primario arriba.
- "Revisar y editar" lleva a la pantalla de revisión con los datos (pasar lo entendido a formulario).

| Estado | Visual |
|---|---|
| `pendiente` | como arriba |
| `confirmando` | primario en `cargando` "Cobrando…"; secundario deshabilitado |
| `hecha` | botones reemplazados por línea `check-circle` verde "Venta registrada · Folio V-0042" + enlace "Ver comprobante" |
| `rechazada` | línea `close-circle` `textoSecundario` "Cancelaste esta acción" |
| `error` | `Aviso` error embebido "No se pudo cobrar. Tu carrito sigue aquí." + "Reintentar" |
| `caducada` | si la tarjeta es vieja (otra venta ya se hizo): "Esta propuesta ya no está vigente" + botones deshabilitados |

```ts
type EstadoTarjeta = 'pendiente' | 'confirmando' | 'hecha' | 'rechazada' | 'error' | 'caducada';
interface TarjetaAccionProps {
  rol: RolAsistente;                 // para icono + nombre de oficio
  titulo: string;                    // AccionAsistente.titulo
  resumen?: { izquierda: string; derecha?: string }[];
  total?: number;
  textoConfirmar: string;            // 'Confirmar cobro' | 'Dar de alta' | 'Publicar promoción'
  estado: EstadoTarjeta;
  simulacion?: boolean;
  resultado?: string;                // 'Folio V-0042'
  onConfirmar: () => void;
  onEditar?: () => void;
  onRechazar?: () => void;           // Boton 'texto' "No, gracias" bajo los botones
}
```

**Nombres de oficio** (mapa único en `src/constants.ts`):

| `rol` | Nombre visible | Icono |
|---|---|---|
| `caja` | Caja | `cash-register` |
| `bodega` | Bodega | `package-variant-closed` |
| `cuentas` | Cuentas | `calculator-variant` |
| `promociones` | Promociones | `bullhorn-outline` |
| `tutor` | Ayuda de pagos | `school-outline` |
| `general` | Asistente | `chat-outline` |

**Accesibilidad:** contenedor `accessibilityRole="summary"` (iOS) con label "Caja propone: Cobrar venta de 3 productos, total 88 pesos". Confirmar: `accessibilityHint="Registra la venta y descuenta del inventario"`. Al cambiar a `hecha`, anunciar "Venta registrada".

---

### 3.10 `Encabezado` de pantalla

Para pantallas del `Stack` (cámara no lo usa; usa su propia barra oscura). Las pestañas usan el header de Tabs con los mismos valores.

**Anatomía**
```
┌──────────────────────────────────────────────────────┐
│ [← Atrás]   Revisa la venta              [Ayuda ?]   │  alto 56, borde inferior 1px divisor
└──────────────────────────────────────────────────────┘
```
- Izquierda: botón 48×48 mín. con icono `arrow-left` + texto "Atrás" (o "Cerrar" con `close` en modales). Si hay cambios sin guardar, `onAtras` pregunta antes (ver 01-cobrar).
- Centro/izquierda: título `subtitulo` 20 Bold (envuelve a 2 líneas con letra grande; el header crece).
- Derecha opcional: una sola acción con icono + texto ("Ayuda", "Caja").
- Fondo `fondo`; `headerShadowVisible: false`; borde inferior 1 px `divisor`.

```ts
interface EncabezadoProps {
  titulo: string;
  onAtras?: () => void;
  tipoAtras?: 'atras' | 'cerrar';
  accionDerecha?: { texto: string; icono: NombreIcono; onPress: () => void; accessibilityHint?: string };
  etiquetaSimulacion?: boolean;
}
```

**Accesibilidad:** título con `accessibilityRole="header"`; primer elemento enfocado al entrar a la pantalla es el título (no el botón Atrás).

---

## 4. Justificación HCI / Nielsen

| # | Heurística | Cómo la cubre el sistema |
|---|---|---|
| 1 | Visibilidad del estado | `BarraPasos`, `Boton cargando` con texto, `TarjetaAccion` con estados, `Aviso sinConexion` fijo |
| 2 | Mundo real | Nombres de oficio (Caja, Bodega, Cuentas), "pz", "c/u", "Revisa", montos leídos como "pesos" |
| 3 | Control y libertad | Stepper que pasa a "Quitar" con deshacer; "Revisar y editar" en tarjetas; "Atrás" que no pierde datos |
| 4 | Consistencia | Un solo botón primario por pantalla, siempre azul, siempre abajo; iconos siempre con texto; mismos 5 tipos de aviso |
| 5 | Prevención de errores | Botón deshabilitado con motivo leído; + bloqueado al llegar al stock; validación tras `onBlur` |
| 6 | Reconocer > recordar | Fila muestra precio c/u y subtotal; tarjeta resume productos antes de confirmar |
| 7 | Flexibilidad | Tocar el número del stepper para escribir cantidades grandes; gestos `adjustable` para lector |
| 8 | Minimalismo | 3 colores con significado; sin decoración; divisores claros solo donde ayudan a escanear |
| 9 | Recuperación de errores | Cada `Aviso` de error **exige** una `accion` de recuperación (la prop debería ser obligatoria cuando `tipo='error'`) |
| 10 | Ayuda | Acción derecha del `Encabezado` para "Caja"/"Ayuda"; textos de ayuda bajo campos |

**Accesibilidad:** todos los pares ≥ 4.5:1 (texto) y ≥ 3:1 (bordes de controles), ver §2.2 · áreas táctiles ≥ 48 con 8 de separación · cuerpo ≥ 16 y escalable · ningún estado solo por color · acciones principales en el tercio inferior · etiquetas accesibles definidas por componente · movimiento mínimo con `reduceMotion`.

---

## 5. Cambios propuestos a `src/theme.ts`

```ts
// colores — agregar
exito: '#1B5E20',            // 7.9:1 sobre blanco; blanco encima 7.9:1
sobreExito: '#FFFFFF',
oscuro: '#111111',           // barras de cámara, EtiquetaSimulacion (blanco encima 18.9:1)
sobreOscuro: '#FFFFFF',
acentoPresionado: '#0848C2', // blanco encima 7.7:1
peligroPresionado: '#8A0019',// blanco encima 10.0:1

// tipografia — agregar
montoGrande: { fontSize: 32, lineHeight: 40, fontWeight: '700' },
subtitulo:   { fontSize: 20, lineHeight: 26, fontWeight: '700' },

// tactil — agregar
principal: 56,
```

Corrección de comentario: `peligro` es **7.3:1** (no 7.4). Los demás valores del archivo coinciden con el cálculo.

**Ajustes a `(tabs)/_layout.tsx` (bloqueantes de accesibilidad):**
1. `tabBarLabelStyle.fontSize: 14` → **16** (regla de mínimo 16 px). Con 4 pestañas en 360 dp caben ~90 dp cada una; "Inventario" en 16 Bold mide ≈ 80 dp.
2. Pestaña activa hoy se distingue **solo por color** (azul vs gris). Agregar señal no cromática: icono relleno cuando está activa (`home` / `home-outline`, `chat` / `chat-outline`, `package-variant` / `package-variant-closed`, `cash-register` en ambos + barra superior 2 px `acento` en el ítem activo vía `tabBarItemStyle` / `tabBarButton`).

**Ajuste a `aviso-conexion.tsx`:** borde inferior `texto` en vez de `peligro` y fondo `superficie` (tipo `sinConexion`). Icono `wifi-off` en `texto`.
