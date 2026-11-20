# 00 · Sistema de diseño M3 — App del Tendero

> Autor: `ui-ux-movil` · Implementa: `frontend-implementador` · Audita: `revisor-ui-m3` + `revisor-accesibilidad-hci`
> Stack: Expo SDK 58 (RN 0.88, Nueva Arquitectura) · `StyleSheet` + `src/theme.ts` · iconos `MaterialCommunityIcons` · **componentes propios, sin react-native-paper**.
> Sistema: **Material Design 3** (m3.material.io) con **excepciones de accesibilidad del proyecto** marcadas como `EXC-n`. Cuando M3 y accesibilidad chocan, gana accesibilidad.
> Usuario: **tendero / dueño** (adulto, posiblemente mayor, poca experiencia digital, una mano libre mientras atiende el mostrador).
> Reemplaza la versión flat. Los nombres de componentes y sus props se **conservan** (con alias) para migrar sin tocar la lógica de las pantallas (ver §9).

---

## 1. Concepto

- **Color por roles, no por valores.** Toda pieza pide un rol (`primary`, `onSurface`, `errorContainer`…) al tema; ningún componente escribe un hex.
- **Azul = "lo que haces ahora"**, **verde (`success`) = "quedó guardado"**, **rojo (`error`) = "algo está mal"**, **malva (`tertiary`) = "revisa esto"**. Cada uno **siempre** con icono + texto.
- **Jerarquía con superficies tonales + elevación M3** (niveles 0–5). La sombra solo aparece donde M3 la pide (FAB, card elevated, hoja, diálogo, snackbar), nunca como adorno.
- **Pulgar primero:** la acción principal vive en el tercio inferior (Extended FAB o botón filled de 56 dp en la barra inferior).
- **Palabras de tienda:** "Cobrar", "Venta", "pz", "Revisa", "Corte de caja". Nunca "modelo", "IA", "inferencia", "agente", "token", "SKU", "confianza".

---

## 2. Color

### 2.1 Semilla y método

| Decisión | Valor | Por qué |
|---|---|---|
| Semilla | **`#769CDF`** (azul mezclilla) | Azul = confianza en dinero y pagos digitales (bancos, CoDi, SPEI usan azul); el tendero va a cobrar y pagar con la app. Se descartó verde como semilla porque `primary` y `success` quedarían casi iguales: el botón "Cobrar" y el mensaje "Venta registrada" se confundirían (rompe Nielsen #4). Azul también queda lejos del rojo de `error` y del verde de `success`, así los tres significados se distinguen incluso con daltonismo rojo-verde (además del icono + texto). |
| Esquema | `SchemeTonalSpot`, claro, `contrastLevel 0` | Es el esquema por defecto de M3 / Android 12+; croma moderado: no cansa la vista en jornadas largas. |
| Rol personalizado | `success*` desde `#1B5E20` (verde del sistema anterior), **armonizado** hacia la semilla con `Blend.harmonize` (rota ≤ 15°), paleta con croma ≥ 48, tonos 40/100/90/30 | Mismo procedimiento que los *custom colors* de Material Theme Builder. |
| Script | `…/scratchpad/m3/generar.mjs` (`npm install && node generar.mjs '#769CDF' '#1B5E20'`) | Fuera de `front/`; no es dependencia de la app. Imprime roles, tonos y la tabla de contraste. |

> **Garantía de contraste por tono.** En HCT el *tono* es la luminancia L\* de CIELAB, que determina exactamente la luminancia relativa WCAG (`Y = ((T+16)/116)³`). Por eso los contrastes de abajo dependen **solo del par de tonos** (p. ej. T40 vs T100 = 6.46:1 siempre). Si al correr el script algún hex difiere en 1–2 unidades por canal (versión de MCU), los contrastes se mantienen. **Antes de cerrar la Fase 1, correr el script y pegar su JSON en `theme.ts`** (los hex de esta tabla son la salida esperada de MCU 0.3 para esa semilla; los de `success*` se verificaron a mano contra su tono objetivo). **Verificado:** la salida real de MCU está en `m3/esquema-generado.md`; `success*` quedó en `#006D43 / #FFFFFF / #92F7BC / #005231` (6.42:1 y 7.22:1) y es lo que usa `theme.ts`.

Luminancias por tono usadas en los cálculos: T100 1.000 · T98 0.949 · T96 0.900 · T95 0.876 · T94 0.853 · T92 0.807 · T90 0.763 · T87 0.700 · T80 0.567 · T50 0.184 · T40 0.1125 · T30 0.0624 · T20 0.0299 · T10 0.0113.

### 2.2 Roles (esquema claro)

| Rol (`color.*`) | Hex | Tono | Uso en la app |
|---|---|---|---|
| `primary` | `#415F91` | 40 | Botón filled, Extended FAB "Cobrar con foto", botón text/outlined (texto), radio/campo enfocado, progreso |
| `onPrimary` | `#FFFFFF` | 100 | Texto/icono sobre `primary` |
| `primaryContainer` | `#D6E3FF` | 90 | Fondo de selección fuerte (opción de pago elegida), cajas sobre la foto "alta" |
| `onPrimaryContainer` | `#284777` | 30 | Texto sobre `primaryContainer` |
| `inversePrimary` | `#AAC7FF` | 80 | Acción "Deshacer" dentro del snackbar |
| `secondary` | `#565F71` | 40 | Anillo de foco |
| `onSecondary` | `#FFFFFF` | 100 | — |
| `secondaryContainer` | `#DAE2F9` | 90 | Botón tonal, indicador píldora de la barra de navegación, pista del progreso, botones del stepper, chips de atajo seleccionados |
| `onSecondaryContainer` | `#3E4759` | 30 | Texto/icono sobre `secondaryContainer` |
| `tertiary` | `#705575` | 40 | Borde 2 dp de fila "Revisa", cajas "revisa" sobre la foto |
| `onTertiary` | `#FFFFFF` | 100 | — |
| `tertiaryContainer` | `#FAD8FD` | 90 | Chip "Revisa" (confianza baja) |
| `onTertiaryContainer` | `#573E5C` | 30 | Texto/icono del chip "Revisa" |
| `error` | `#BA1A1A` | 40 | Texto/icono de error, borde de campo/fila con error, botón filled destructivo |
| `onError` | `#FFFFFF` | 100 | Texto sobre `error` |
| `errorContainer` | `#FFDAD6` | 90 | Aviso de error, chip "Falta precio" |
| `onErrorContainer` | `#93000A` | 30 | Texto/icono sobre `errorContainer` |
| `success` *(pers.)* | `#006D43` | 40 | Icono/título "Venta registrada", icono del chip "Detectado" |
| `onSuccess` *(pers.)* | `#FFFFFF` | 100 | Texto sobre `success` |
| `successContainer` *(pers.)* | `#92F7BC` | 90 | Aviso de éxito ("Todo listo"), encabezado del comprobante |
| `onSuccessContainer` *(pers.)* | `#005231` | 30 | Texto/icono sobre `successContainer` |
| `surface` | `#F9F9FF` | 98 | Fondo de todas las pantallas, top app bar en reposo |
| `surfaceDim` | `#D9D9E0` | 87 | Esqueletos de carga |
| `surfaceBright` | `#F9F9FF` | 98 | — |
| `surfaceContainerLowest` | `#FFFFFF` | 100 | Campos de texto (relleno interno), vista del comprobante |
| `surfaceContainerLow` | `#F3F3FA` | 96 | Card elevated (`TarjetaAccion`), bottom sheet |
| `surfaceContainer` | `#EDEDF4` | 94 | Navigation bar, top app bar con scroll, barra de total |
| `surfaceContainerHigh` | `#E7E8EE` | 92 | Diálogo, banner de info/sin conexión |
| `surfaceContainerHighest` | `#E2E2E9` | 90 | Card filled, fila "Revisa", contenedor deshabilitado |
| `surfaceVariant` | `#E0E2EC` | 90 | (solo compatibilidad; preferir `surfaceContainerHighest`) |
| `onSurface` | `#191C20` | 10 | Texto principal |
| `onSurfaceVariant` | `#44474E` | 30 | Texto secundario, iconos inactivos, contenido deshabilitado (`EXC-4`) |
| `outline` | `#74777F` | 50 | Borde de text field, botón outlined, stepper, radio inactivo |
| `outlineVariant` | `#C4C6D0` | 80 | Divisores, borde de card outlined (decorativo) |
| `inverseSurface` | `#2E3036` | 20 | Snackbar, `EtiquetaSimulacion`, barras de la cámara |
| `inverseOnSurface` | `#F0F0F7` | 95 | Texto sobre `inverseSurface` |
| `shadow` | `#000000` | 0 | Color de sombras |
| `scrim` | `#000000` | 0 | Velo de bottom sheet modal y diálogo, **al 32 %** |

### 2.3 Contraste WCAG de cada par usado

| Primer plano | Fondo | Contraste | Mín. | Resultado | Dónde |
|---|---|---|---|---|---|
| `onPrimary` T100 | `primary` T40 | **6.46:1** | 4.5 | AA | Botón filled, Extended FAB |
| `onPrimaryContainer` T30 | `primaryContainer` T90 | **7.24:1** | 4.5 | AAA | Opción elegida |
| `primary` T40 | `surface` T98 | **6.15:1** | 4.5 | AA | Botón text/outlined, enlaces |
| `primary` T40 | `surfaceContainerLow` T96 | **5.85:1** | 4.5 | AA | Botones dentro de hoja / card elevated |
| `primary` T40 | `surfaceContainer` T94 | **5.55:1** | 4.5 | AA | Barra de total |
| `primary` T40 | `surfaceContainerHigh` T92 | **5.27:1** | 4.5 | AA | Botón en diálogo/banner |
| `primary` T40 | `surfaceContainerHighest` T90 | **5.00:1** | 4.5 | AA | Botón en card filled / fila "Revisa" |
| `onSecondaryContainer` T30 | `secondaryContainer` T90 | **7.24:1** | 4.5 | AAA | Botón tonal, pestaña activa, stepper |
| `onTertiaryContainer` T30 | `tertiaryContainer` T90 | **7.24:1** | 4.5 | AAA | Chip "Revisa" |
| `onError` T100 | `error` T40 | **6.46:1** | 4.5 | AA | Botón destructivo |
| `onErrorContainer` T30 | `errorContainer` T90 | **7.24:1** | 4.5 | AAA | Aviso de error, chip "Falta" |
| `error` T40 | `surface` T98 | **6.15:1** | 4.5 | AA | Mensaje de error de campo |
| `error` T40 | `surfaceContainerLow` T96 | **5.85:1** | 4.5 | AA | Error en hoja inferior |
| `onSuccess` T100 | `success` T40 | **6.42:1** | 4.5 | AA | — |
| `onSuccessContainer` T30 | `successContainer` T90 | **7.22:1** | 4.5 | AAA | Aviso de éxito, comprobante |
| `success` T40 | `surface` T98 | **6.13:1** | 4.5 | AA | Icono/título "Venta registrada" |
| `onSurface` T10 | `surface` / `Lowest` / `Low` / `—` / `High` / `Highest` | **16.3 / 17.1 / 15.5 / 14.7 / 14.0 / 13.3 :1** | 4.5 | AAA | Texto principal en cualquier superficie |
| `onSurfaceVariant` T30 | `surface` / `Low` / `—` / `High` / `Highest` | **8.89 / 8.46 / 8.03 / 7.63 / 7.24 :1** | 4.5 | AAA | Texto secundario; deshabilitado |
| `outline` T50 | `surface` / `Lowest` / `Low` / `—` / `Highest` | **4.27 / 4.48 / 4.06 / 3.85 / 3.47 :1** | 3.0 (no texto) | AA | Bordes de controles. **Nunca como texto.** |
| `outlineVariant` T80 | `surface` | 1.62:1 | — | decorativo | Solo divisores y borde de card outlined; ninguna información depende de él |
| `inverseOnSurface` T95 | `inverseSurface` T20 | **11.59:1** | 4.5 | AAA | Snackbar, Simulación, cámara |
| `inversePrimary` T80 | `inverseSurface` T20 | **7.72:1** | 4.5 | AAA | "Deshacer" del snackbar |
| `primary` T40 | `secondaryContainer` T90 | **5.00:1** | 3.0 | AA | Progreso: indicador vs. pista |
| `onSurfaceVariant` T30 | `surfaceContainerHighest` T90 | **7.24:1** | 4.5 | AAA | Botón deshabilitado (`EXC-4`) |

**Pares prohibidos:** `outline` como texto (< 4.5 en todas las superficies) · cualquier texto en `outlineVariant` · `primaryContainer`/`secondaryContainer` como color de texto · texto `onSurface` al 38 % (deshabilitado M3 estándar: ≈ 2.3:1).

---

## 3. Tipografía

Fuente del sistema (`fontFamily` sin definir): **Roboto** en Android (la de M3) y SF Pro en iOS. Así se respeta el tamaño de letra del sistema sin cargar fuentes. `allowFontScaling` siempre activo; `maxFontSizeMultiplier` **no** se usa.

**`EXC-1` (accesibilidad):** ningún texto baja de **16 sp**. Los estilos M3 de 11–14 sp se suben a 16 sp; el resto de la escala queda como M3.

| Token (`type.*`) | M3 original (tamaño/línea/peso) | **Proyecto** | Uso | Reemplaza a (flat) |
|---|---|---|---|---|
| `displaySmall` | 36/44/400 | 36/44/400 | Monto grande del comprobante (opcional) | — |
| `headlineLarge` | 32/40/400 | **32/40/500** tabular | Total de la venta | `montoGrande` |
| `headlineSmall` | 24/32/400 | 24/32/400 | Título de diálogo, título de estados vacíos/éxito | `titulo` |
| `titleLarge` | 22/28/400 | 22/28/400 | Título de top app bar, título de hoja | `subtitulo` |
| `titleMedium` | 16/24/500 | **18/26/500** | Nombre de producto, título de aviso, encabezado de sección | `nombreProducto` |
| `titleSmall` | 14/20/500 | **16/24/500** | Subtítulos de card | — |
| `bodyLarge` | 16/24/400 | 16/24/400 | Texto general, entrada de campos | `cuerpo` |
| `bodyLargePlus` *(proyecto)* | — | **18/26/400** | Mensajes de aviso, texto de entrada numérica | `cuerpoGrande` |
| `bodyMedium` | 14/20/400 | **16/24/400** | Texto de apoyo de card, cuerpo de snackbar | — |
| `bodySmall` | 12/16/400 | **16/24/400** | *Supporting text* de campos, contador | — |
| `labelLarge` | 14/20/500 | **16/24/500** | Botones, chips, acciones de snackbar | `etiqueta` |
| `labelMedium` | 12/16/500 | **16/24/500** | Etiquetas de la navigation bar | — |
| `labelSmall` | 11/16/500 | **16/24/500** | Badges, `EtiquetaSimulacion` | — |
| `amount` *(proyecto)* | — | **20/28/500** tabular | Precios, subtotales | `monto` |

Reglas: montos con `fontVariant: ['tabular-nums']`; con letra del sistema al 200 % los textos **envuelven** (sin `numberOfLines` en montos ni errores); solo nombres de producto se truncan a 2 líneas con el nombre completo en `accessibilityLabel`. Estado activo/seleccionado puede subir a peso **700** como señal no cromática.

---

## 4. Forma

| Token (`shape.*`) | Radio | Componentes |
|---|---|---|
| `none` | 0 | List items, barra de total, navigation bar, top app bar, franjas de banner |
| `extraSmall` | 4 | Text field outlined, snackbar, menú, badges con texto |
| `small` | 8 | Chips, cajas numeradas sobre la foto |
| `medium` | 12 | Cards (elevated/filled/outlined), `TarjetaAccion`, aviso en modo tarjeta, filas "Revisa"/"Falta" |
| `large` | 16 | FAB y Extended FAB, vista previa de cámara, miniatura de foto |
| `extraLarge` | 28 | Bottom sheet (solo esquinas superiores), diálogo |
| `full` | 9999 | Botones (todas las variantes), icon buttons, indicador de navegación, progreso, botones del stepper |

---

## 5. Elevación

M3 combina **color tonal** (qué `surfaceContainer*` usa el componente) y **sombra**. En RN 0.88 (Nueva Arquitectura) se usa `boxShadow` en iOS (dos sombras M3: *key* + *ambient*) y `elevation` nativa en Android (Material la dibuja). La sombra solo funciona sobre un `View` con `backgroundColor` opaco.

| Nivel | dp | Android | iOS (`boxShadow`) | Fallback iOS (`shadow*`) | Componentes del proyecto (superficie) |
|---|---|---|---|---|---|
| `level0` | 0 | `elevation: 0` | — | — | Botón filled/tonal/outlined en reposo, card filled/outlined, list items, text field, top app bar, **navigation bar** (`surfaceContainer`, sin sombra), barra de total (`surfaceContainer`) |
| `level1` | 1 | `elevation: 1` | `0px 1px 2px 0px rgba(0,0,0,0.30), 0px 1px 3px 1px rgba(0,0,0,0.15)` | `shadowColor:'#000', shadowOffset:{width:0,height:1}, shadowOpacity:0.15, shadowRadius:3` | Card elevated / `TarjetaAccion` (`surfaceContainerLow`), bottom sheet modal (`surfaceContainerLow`), botón filled en hover/foco |
| `level2` | 3 | `elevation: 3` | `0px 1px 2px 0px rgba(0,0,0,0.30), 0px 2px 6px 2px rgba(0,0,0,0.15)` | `…offset {0,2}, opacity 0.15, radius 6` | Menú (`surfaceContainer`), card elevated presionada, top app bar con scroll (**solo tonal** `surfaceContainer`, sin sombra) |
| `level3` | 6 | `elevation: 6` | `0px 1px 3px 0px rgba(0,0,0,0.30), 0px 4px 8px 3px rgba(0,0,0,0.15)` | `…offset {0,4}, opacity 0.15, radius 8` | **Extended FAB** (reposo y presionado), diálogo (`surfaceContainerHigh`), snackbar (`inverseSurface`) |
| `level4` | 8 | `elevation: 8` | `0px 2px 3px 0px rgba(0,0,0,0.30), 0px 6px 10px 4px rgba(0,0,0,0.15)` | `…offset {0,6}, opacity 0.15, radius 10` | Extended FAB en hover/foco (teclado externo) |
| `level5` | 12 | `elevation: 12` | `0px 4px 4px 0px rgba(0,0,0,0.30), 0px 8px 12px 6px rgba(0,0,0,0.15)` | `…offset {0,8}, opacity 0.15, radius 12` | (reservado; no se usa) |

Token propuesto:
```ts
export const elevacion = {
  level0: {},
  level1: Platform.select({ android: { elevation: 1 }, default: { boxShadow: '0px 1px 2px 0px rgba(0,0,0,0.30), 0px 1px 3px 1px rgba(0,0,0,0.15)' } }),
  // … level2–5 con los valores de la tabla
} as const;
```
Reglas: nunca sombra en texto (`textShadow*` prohibido); sin gradientes ni blur (M3 no los usa); la elevación indica **jerarquía o que algo flota**, no decoración (Nielsen #8). La información nunca depende de la sombra (el contraste de los contenidos ya cumple por sí solo).

---

## 6. Estados (capas de estado M3)

| Estado | Capa (color del **contenido** del componente) | Implementación RN |
|---|---|---|
| Hover | 8 % | Solo teclado/mouse externo (`onHoverIn`) |
| Focus | 10 % **+ anillo de foco** 3 dp `secondary`, separado 2 dp (`outlineOffset: 2`); sobre `inverseSurface` (snackbar, cámara) el anillo usa `inverseOnSurface`/`inversePrimary` (prop `colorAnillo` de `Tocable`) | `onFocus/onBlur` del `Pressable` |
| Pressed | 10 % | Android: `android_ripple={{ color: alfa(contenido, 0.10), foreground: true }}` (ripple M3 nativo). iOS: `View` absoluto con `backgroundColor: contenido`, `opacity: 0.10` mientras `pressed` |
| Dragged | 16 % | No se usa en botones (blanco 16 % sobre `primary` baja a 4.4:1); solo en filas arrastrables futuras |
| Seleccionado | Contenedor `secondaryContainer` + icono relleno + peso 700 | Nunca solo color |

Contraste verificado con capa aplicada: filled presionado (`#546F9C`) → blanco **5.08:1**; tonal presionado → **≈ 6.6:1**; text presionado → **≈ 5.7:1**.

**`EXC-4` Deshabilitado:** M3 indica contenido `onSurface` 38 % sobre contenedor `onSurface` 12 % (≈ 2.3:1, ilegible para baja visión). El proyecto usa **contenedor `surfaceContainerHighest` + contenido `onSurfaceVariant` (7.24:1)**, outlined con borde `outlineVariant`, y **siempre** texto visible de motivo junto al control ("Necesita internet") además del `accessibilityHint`. Regla de negocio: el botón principal de un flujo **nunca** se deshabilita; se cambia por una acción que explica qué falta (p. ej. "Corrige 1 producto para cobrar").

---

## 7. Movimiento

| Token (`motion.*`) | Valor | Uso |
|---|---|---|
| `easing.emphasized` | `cubic-bezier(0.2, 0, 0, 1)` | Cambios de pantalla dentro del Stack |
| `easing.emphasizedDecelerate` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | Entrada de bottom sheet, snackbar, diálogo |
| `easing.emphasizedAccelerate` | `cubic-bezier(0.3, 0, 0.8, 0.15)` | Salida de bottom sheet, snackbar, diálogo |
| `easing.standard` | `cubic-bezier(0.2, 0, 0, 1)` | Cambios de estado (chip, indicador de navegación) |
| `duration.short2` / `short4` | 100 / 200 ms | Capas de estado / salidas |
| `duration.medium2` | 300 ms | Indicador de la navigation bar, snackbar entrada |
| `duration.medium4` | 400 ms | Bottom sheet y diálogo entrada |

Implementación con `react-native-reanimated` (`Easing.bezier(...)`, ya instalado). **Movimiento reducido:** `useReducedMotion()` → duración 0 (aparece/desaparece directo) y `scrollTo({ animated: false })`. Prohibido: animaciones en bucle salvo el indicador de progreso, rebotes, parallax, escalado al presionar.

---

## 8. Iconografía y medidas comunes

`MaterialCommunityIcons`: 24 dp en botones, listas y barras; 24 dp en navigation bar; 32 dp en controles de cámara; 48 dp ilustrativo en estados vacíos/éxito. **Siempre** con texto visible; el icono va con `accessibilityElementsHidden` / `importantForAccessibility="no"`.

| Significado | Icono |
|---|---|
| Error | `alert-circle` |
| Revisa (confianza baja) | `help-circle` |
| Detectado / éxito | `check-circle` |
| Tú lo pusiste | `pencil` |
| Info | `information` |
| Sin conexión | `wifi-off` |
| Tiempo agotado | `timer-sand` |
| Quitar | `trash-can-outline` |
| Deshacer | `undo` |
| Simulación | `flask-outline` |
| Cámara | `camera` |
| Galería | `image-multiple` |
| Caja (asistente) | `cash-register` |

Espaciado (grid 4 dp): 4 · 8 · 12 · 16 · 24 · 32. Margen lateral de pantalla 16; entre bloques 24. **Táctil:** ≥ 48×48 dp siempre (si el dibujo M3 es menor, `hitSlop`), separación ≥ 8 dp; acción principal 56 dp.

---

## 9. Componentes

Convención: archivos kebab-case en `src/components/`, export PascalCase; todos aceptan `testID` y `style` (solo márgenes). Todo tocable = `Pressable` con capas de estado (§6) y anillo de foco. **Los nombres y props actuales se mantienen**; los valores nuevos se agregan y los antiguos quedan como alias para que las pantallas compilen sin cambios.

### Mapa de migración

| Componente actual | Componente M3 | Archivo | Cambio para pantallas |
|---|---|---|---|
| `Boton` | Buttons: filled / tonal / outlined / text / elevated | `boton.tsx` | Variantes con nombre M3 (alias flat eliminados) |
| `Campo` | Text field **outlined** | `campo.tsx` | Ninguno |
| `StepperCantidad` | Grupo de 2 icon buttons tonales + valor (no hay stepper M3) | `stepper-cantidad.tsx` | Ninguno |
| `Aviso` | **Banner** (franja bajo la top app bar) o **card de mensaje**; lo transitorio → `Snackbar` | `aviso.tsx` | Ninguno; `AvisoConexion` usa `Aviso` modo franja |
| — (nuevo) | **Snackbar** ("Deshacer", confirmaciones breves) | `snackbar.tsx` | Reemplaza la franja de deshacer de la revisión |
| `IndicadorConfianza` | **Assist chip** (presentacional) | `indicador-confianza.tsx` | Ninguno |
| `EtiquetaSimulacion` | **Badge grande / chip de estado** en `inverseSurface`; franja = banner | `etiqueta-simulacion.tsx` | Ninguno |
| `BarraPasos` | **Linear progress** determinado con paradas + texto de paso | `barra-pasos.tsx` | Ninguno |
| `FilaProducto` | **List item** de 3 líneas (en "Necesitan tu ayuda": dentro de card) | `fila-producto.tsx` | Ninguno |
| `FilaVenta` | **List item** de 2 líneas | `fila-venta.tsx` | Ninguno |
| `TarjetaAccion` | **Card elevated** | `tarjeta-accion.tsx` | Ninguno |
| `HojaInferior` | **Bottom sheet** modal (y estándar para el tutor) | `hoja-inferior.tsx` | Prop nueva opcional `tipo` |
| `Encabezado` | **Top app bar** small | `encabezado.tsx` | Ninguno |
| Pestañas `(tabs)/_layout.tsx` | **Navigation bar** con indicador píldora | `barra-navegacion.tsx` (nuevo, como `tabBar`) | Cambio en `_layout.tsx` |
| — (nuevo) | **Extended FAB** "Cobrar con foto" | `fab-extendido.tsx` | Se agrega en Inicio y Cobrar |
| — (nuevo) | **Dialog** básico (confirmaciones destructivas) | `dialogo.tsx` | Reemplaza las hojas de confirmación |
| `PantallaPendiente` | Estado vacío (headlineSmall + bodyLarge sobre `surface`) | `pantalla-pendiente.tsx` | Ninguno |

---

### 9.1 `Boton` → M3 Buttons

**Anatomía:** contenedor píldora (`full`) · icono inicial opcional 24 · etiqueta `labelLarge` 16/500 · (cargando: `ActivityIndicator` 24 + `textoCargando`).

**Medidas:** alto **48** (`tamano="normal"`; M3 = 40 → `EXC-2`), **56** (`tamano="principal"`, tamaño *medium* M3); padding horizontal 24 (16 a la izquierda si hay icono), gap icono-texto 8; ancho completo por defecto en barras; la etiqueta envuelve a 2 líneas (el alto crece). Separación entre botones 8.

| Variante (`variante`) | Contenedor | Contenido | Borde | Elevación |
|---|---|---|---|---|
| `filled` | `primary` | `onPrimary` (6.46) | — | 0 (hover/foco 1) |
| `tonal` | `secondaryContainer` | `onSecondaryContainer` (7.24) | — | 0 (hover 1) |
| `outlined` | transparente | `primary` (6.15 sobre `surface`) | 1 dp `outline` (foco: 1 dp `primary`) | 0 |
| `text` | transparente | `primary` | — | 0 |
| `elevated` | `surfaceContainerLow` | `primary` (5.85) | — | 1 (presionado 1, hover 2) |
| `outlinedError` | transparente | `error` (6.15) | 1 dp `error` | 0 |
| `filledError` | `error` | `onError` (6.46) | — | 0 |
| `textError` | transparente | `error` (6.15) | — | 0 |

> Los alias de la versión flat (`primario`, `secundario`, `peligro`, `peligroLleno`, `texto`) **se eliminaron** al terminar la migración; ya no existen en el código.

> Se elimina el subrayado del botón `text` (M3) — su forma de botón (capa al presionar, `accessibilityRole="button"`, posición) basta; dentro de párrafos se usa un enlace con subrayado.

| Estado | Visual |
|---|---|
| Presionado | Capa 10 % del contenido (ripple Android) |
| Foco | Capa 10 % + anillo 3 dp `secondary` a 2 dp |
| Deshabilitado | `EXC-4`: contenedor `surfaceContainerHighest`, contenido `onSurfaceVariant`; outlined: borde `outlineVariant`; sin ripple; sigue enfocable con `motivoDeshabilitado` |
| Cargando | Igual a su variante, spinner del color del contenido + `textoCargando`; no dispara `onPress` (evita doble cobro) |

```ts
type VarianteBoton = 'filled' | 'tonal' | 'outlined' | 'text' | 'elevated' | 'outlinedError' | 'filledError' | 'textError';
interface BotonProps {
  texto: string; onPress: () => void;
  variante?: VarianteBoton;            // default 'filled'
  icono?: NombreIcono;
  tamano?: 'normal' | 'principal';     // 48 | 56
  deshabilitado?: boolean; motivoDeshabilitado?: string;
  cargando?: boolean; textoCargando?: string;
  anchoCompleto?: boolean;             // default true
  accessibilityHint?: string; testID?: string; style?: StyleProp<ViewStyle>;
}
```
**Accesibilidad:** igual que antes — `role="button"`, `accessibilityState={{ disabled, busy }}`, hint con el motivo si está deshabilitado.

**Regla de jerarquía por pantalla:** máximo **un** `filled` (o un Extended FAB) por vista; lo secundario `tonal`/`outlined`; lo terciario `text`.

---

### 9.2 `Campo` → Text field outlined

**Anatomía (con `EXC-3`):**
```
Precio por pieza *                         ← etiqueta FIJA arriba, titleSmall 16/500 onSurface
┌────────────────────────────────────────┐ ← contenedor 56 dp, shape extraSmall (4), fondo surfaceContainerLowest
│ $ │ 18.00                         [✕]  │ ← prefijo onSurfaceVariant · entrada bodyLargePlus 18 · icono final opcional 24 (48 táctil)
└────────────────────────────────────────┘
(i) Ej. 18.50                              ← supporting text bodySmall→16, onSurfaceVariant
```
`EXC-3`: M3 mete la etiqueta dentro del borde y la encoge a 12 sp al enfocar. El proyecto la deja **siempre visible arriba a 16 sp** (no desaparece, no se encoge; placeholder nunca sustituye la etiqueta). El resto es outlined M3.

| Estado | Borde | Etiqueta | Supporting text |
|---|---|---|---|
| Normal | 1 dp `outline` (4.27–4.48:1) | `onSurface` | `onSurfaceVariant` |
| Presionado/hover | 1 dp `onSurface` | `onSurface` | — |
| Enfocado | **2 dp `primary`** | `primary` + peso 700 | — |
| Error | **2 dp `error`** | `error` | icono `alert-circle` + mensaje `error` 16/500 (6.15) |
| Deshabilitado | 1 dp `outlineVariant`, fondo `surfaceContainerHighest` | `onSurfaceVariant` | motivo visible |
| Solo lectura | sin borde, fondo `surfaceContainerHighest` | `onSurfaceVariant` | — |

Medidas: alto 56, padding horizontal 16, etiqueta→contenedor 4, contenedor→supporting 4, separación entre campos 16. Numérico/validación/props **sin cambios** (`etiqueta, valor, onCambiar, tipo, prefijo, sufijo, placeholder, ayuda, error, obligatorio, deshabilitado, autoFocus, onBlur`). Accesibilidad sin cambios (error anunciado con live region).

---

### 9.3 `StepperCantidad`

M3 no tiene stepper; se compone con **icon buttons tonales** (forma `full`).

**Anatomía:** `[ (−) ]  2 pz  [ (+) ]`
- Botones: círculo **48×48** `secondaryContainer`, icono `minus`/`plus` 24 `onSecondaryContainer` (7.24).
- Valor: `amount` 20/500 tabular + unidad, ancho mín. 56, alto 48, tocable (abre `number-pad`); con borde inferior 1 dp `outline` para indicar que se puede escribir.
- Gap 8 → ancho total ≈ 168.

| Estado | Visual |
|---|---|
| Normal | Ambos tonales |
| En mínimo con `onQuitar` | El `−` pasa a icon button **outlined error**: borde 1 dp `error`, icono `trash-can-outline` `error`; label accesible "Quitar {producto}" |
| En máximo (stock) | `+` deshabilitado (`EXC-4`) y debajo `information` + "Solo hay 3 en existencia" (`bodyLarge`, `onSurfaceVariant`) |
| Presionado/foco | Capa 10 % / anillo `secondary` |

Props y accesibilidad (`adjustable`, `increment/decrement`) **sin cambios**.

---

### 9.4 `Aviso` → Banner / card de mensaje (y cuándo usar Snackbar)

| Caso | Componente | Por qué |
|---|---|---|
| Error que **bloquea** o requiere acción (foto ilegible, sin productos, falla al registrar) | `Aviso modo="tarjeta"` (card de mensaje) | Debe quedarse hasta que el tendero actúe (Nielsen #9). |
| Estado persistente de la pantalla (sin conexión, simulación, "tardando más de lo normal") | `Aviso modo="franja"` = **Banner** bajo la top app bar | Visible sin tapar contenido. M3 no tiene banner propio; se usa el patrón Material de banner con tokens M3. |
| Confirmación breve o deshacer ("Quitaste Galletas", "Venta guardada") | **`Snackbar`** (§9.5) | Transitorio, no bloquea. **Nunca** errores con acción obligatoria en un snackbar. |

**Anatomía (tarjeta):** contenedor shape `medium` (12), padding 16, elevación 0 · icono 24 · título `titleMedium` 18/500 · mensaje `bodyLargePlus` 18 · acciones (botones 48, gap 8, alineadas al final; se apilan con letra grande).
**Anatomía (franja/banner):** ancho completo, shape `none`, padding 16/12, divisor inferior 1 dp `outlineVariant`, icono + texto + hasta 2 botones `text`.

| `tipo` | Contenedor | Título / icono / texto | Contraste | Icono |
|---|---|---|---|---|
| `error` | `errorContainer` | `onErrorContainer` | 7.24 | `alert-circle` |
| `exito` | `successContainer` | `onSuccessContainer` | 7.22 | `check-circle` |
| `info` | `surfaceContainerHigh` | `onSurface` / icono `onSurfaceVariant` | 13.99 / 7.63 | `information` |
| `sinConexion` | `surfaceContainerHigh` | `onSurface` | 13.99 | `wifi-off` |
| `tiempo` | `surfaceContainerHigh` | `onSurface` | 13.99 | `timer-sand` |

Acción principal dentro del aviso = botón **filled** (`primary`, contenedor vs. fondo ≥ 5:1); secundarias `text` (`primary` sobre `errorContainer` T90 = 5.00:1). Recuperar no es destructivo → nunca botón rojo para "Tomar otra foto".

Props **sin cambios** (`tipo, titulo, mensaje, accion, accionSecundaria, modo, onCerrar`); regla: `accion` obligatoria si `tipo='error'`. Accesibilidad sin cambios (`alert` / live region, foco al aviso si bloquea).

---

### 9.5 `Snackbar` (nuevo)

**Anatomía:** contenedor `inverseSurface`, shape `extraSmall` (4), elevación **level3** · icono opcional 24 `inverseOnSurface` · texto `bodyMedium`→16 `inverseOnSurface` (11.59) · acción `text` en `inversePrimary` (7.72) · botón cerrar opcional (icono `close` + label accesible "Cerrar aviso", 48×48).

**Medidas:** alto mín. 48 (una línea) / 68 (dos líneas; con letra grande la acción baja a su propia línea), ancho = pantalla − 32, padding 16/8, acción 48 de alto.
**Posición:** 8 dp **encima** de la barra inferior de la pantalla (barra de total, navigation bar o Extended FAB). **Nunca tapa el botón principal ni campos.**
**Tiempo:** `duracion` por defecto 10 s para "Deshacer" (WCAG 2.2.1: si hay lector de pantalla activo, `AccessibilityInfo.isScreenReaderEnabled()` → sin límite hasta que se cierre o haya otro cambio). Uno a la vez; el nuevo reemplaza al anterior.
**Movimiento:** entra `medium2` `emphasizedDecelerate` desde abajo; sale `short4`; con movimiento reducido, aparece directo.

```ts
interface SnackbarProps {
  visible: boolean;
  mensaje: string;                    // 'Quitaste "Galletas".'
  icono?: NombreIcono;                // 'undo'
  accion?: { texto: string; onPress: () => void };   // 'Deshacer'
  duracionMs?: number | null;         // default 10000; null = hasta cerrar
  onCerrar: () => void;
  separacionInferior: number;         // alto de la barra fija que debe librar
}
```
**Accesibilidad:** **un solo mecanismo de anuncio** para no leer dos veces: si se pasa la prop `anuncio` (p. ej. `'Quitaste Galletas. Botón Deshacer disponible.'`), el Snackbar llama `announceForAccessibility` (iOS y Android) y desactiva su live region; si no se pasa, usa `accessibilityLiveRegion="polite"` (solo Android). La pantalla **no** anuncia por su cuenta el mismo evento. Prop: `anuncio?: string`. Anillo de foco de sus botones en `inverseOnSurface` (el `secondary` sobre `inverseSurface` da 2.05:1).

---

### 9.6 `IndicadorConfianza` → Assist chip (presentacional)

**Anatomía:** chip alto **32** (no tocable; la fila es la que se toca), shape `small` (8), padding 8, icono 18–20 + gap 8, etiqueta `labelLarge` 16/500. Elevación 0. Nunca porcentajes ni la palabra "confianza".

| `nivel` | Contenedor / borde | Icono | Texto | Contraste |
|---|---|---|---|---|
| `alta` | transparente, borde 1 dp `outlineVariant` | `check-circle` `success` | "Detectado" `onSurfaceVariant` | 8.89 (texto) / 6.13 (icono) |
| `baja` | `tertiaryContainer` | `help-circle` `onTertiaryContainer` | "Revisa" `onTertiaryContainer` | 7.24 |
| `falta` | `errorContainer` | `alert-circle` `onErrorContainer` | "Falta precio" / "Elige producto" | 7.24 |
| `manual` | transparente, borde 1 dp `outlineVariant` | `pencil` `onSurfaceVariant` | "Tú lo pusiste" | 8.89 |

Props, helper `nivelDeItem` y umbral `UMBRAL_CONFIANZA = 0.6` **sin cambios**. Accesibilidad: el chip no es elemento separado; su texto se integra al label de la fila.

---

### 9.7 `EtiquetaSimulacion` → Badge grande / banner

- `modo="chip"`: contenedor `inverseSurface`, texto `labelSmall`→16/500 `inverseOnSurface` (11.59), icono `flask-outline` 18, shape `small`, alto 32, padding 8. (El badge M3 de 16 dp con 11 sp es ilegible para el usuario objetivo → `EXC-1`.)
- `modo="franja"`: banner ancho completo `inverseSurface`, alto mín. 48, "Simulación: este cobro no mueve dinero real" 16/500.

Props y accesibilidad sin cambios (debe ser lo primero que lea el lector).

---

### 9.8 `BarraPasos` → Linear progress con pasos

**Anatomía:**
```
Paso 2 de 3 · Revisar                     ← titleSmall 16/500 onSurface
████████████████████▪ ░░░░░░░░░░░░░░░ •   ← indicador primary · gap 4 · pista secondaryContainer · stop indicator 4 dp primary
✓ Foto     ● Revisar     ○ Listo          ← labelLarge 16; completado con check, actual peso 700
```
- Progreso determinado = `(actual + 1) / pasos.length`; alto **8 dp** (M3 = 4 dp; `EXC-5` baja visión), shape `full`, gap 4 entre indicador y pista, *stop indicator* (punto 4 dp `primary`) al final de la pista.
- Contraste indicador/pista 5.00:1 (≥ 3 no texto). Fila de nombres opcional (se oculta si no cabe con letra grande).
- Sin animación salvo transición `medium2` `standard` al cambiar de paso (0 ms con movimiento reducido).

Props (`pasos, actual, mostrarNombres`) y accesibilidad (`progressbar` con `accessibilityValue`) **sin cambios**.

---

### 9.9 `FilaProducto` → List item de 3 líneas

**Anatomía (editable):**
```
┌ leading ┬────────────────────────────────────────┬ trailing ─┐
│  (1)    │ Refresco de cola 600 ml                │  $36.00   │ ← headline titleMedium 18/500 (2 líneas máx) · trailing amount 20/500
│         │ $18.00 c/u · [✓ Detectado]             │           │ ← supporting bodyLarge onSurfaceVariant + IndicadorConfianza
│         │ [(−) 2 pz (+)]                [Editar] │           │ ← StepperCantidad · Boton text
└─────────┴────────────────────────────────────────┴───────────┘
```
- Leading opcional: número del producto en la foto (caja 32×32 shape `small`, `inverseSurface` + `inverseOnSurface` 16/500).
- Padding 16 horizontal / 12 vertical; alto mín. ≈ 136 editable, **56** en `soloLectura` ("2 × Refresco…  $36.00", one-line list item).
- Divisor entre filas: 1 dp `outlineVariant` con inset 16 (decorativo).

| Estado | Presentación M3 |
|---|---|
| Normal ("Listos") | List item sobre `surface`, elevación 0 |
| `baja` ("Revisa") | Dentro de **card filled** (`surfaceContainerHighest`, shape `medium`) con **borde izquierdo 4 dp `tertiary`** + chip "Revisa" + botón `tonal` "Está bien"; margen 8 entre cards |
| `falta` | **Card outlined** con borde **2 dp `error`** (M3 usa 1 dp `outlineVariant`; `EXC-6`: el borde es parte del mensaje de error, como en el text field) + chip "Falta precio"; subtotal "— —"; botón **filled** "Poner precio"/"Elegir producto" en lugar de "Editar" |
| Agotado | `+` deshabilitado y `alert-circle` `error` + "Sin existencia" |
| Eliminado | Desaparece; aparece `Snackbar` "Quitaste {nombre}. Deshacer" |

Props **sin cambios**. Accesibilidad sin cambios (bloque de texto con label completo, montos en palabras).

`FilaVenta` → one/two-line list item tocable: leading hora `labelLarge` tabular, headline "3 productos", supporting "Efectivo" o `cloud-upload` + "Pendiente de enviar", trailing `amount`; alto mín. 64; ripple; divisor `outlineVariant`.

---

### 9.10 `TarjetaAccion` → Card elevated

**Anatomía:** contenedor `surfaceContainerLow`, shape `medium` (12), **elevación level1**, padding 16.
```
[cash-register] Caja propone:            [SIMULACIÓN]   ← labelLarge 16/500 onSurfaceVariant + EtiquetaSimulacion chip
Cobrar venta de 3 productos                             ← titleLarge 22 onSurface
─────────────────────────────── (outlineVariant)
2 × Refresco de cola 600 ml                 $36.00      ← bodyLarge / amount
1 × Pan blanco grande                       $52.00
Total                                       $88.00      ← titleMedium / amount
───────────────────────────────
[ Revisar y editar ] (outlined)  [ Confirmar cobro ] (filled)   ← 48, se apilan con letra grande (filled arriba)
           No, gracias (text)
```

| Estado | Visual |
|---|---|
| `pendiente` | Como arriba |
| `confirmando` | Filled en `cargando` "Cobrando…"; outlined deshabilitado |
| `hecha` | Botones → fila `check-circle` `success` + "Venta registrada · Folio V-0042" `onSurface` + botón `text` "Ver comprobante"; la card baja a elevación 0 (ya no es accionable) |
| `rechazada` | `close-circle` `onSurfaceVariant` + "Cancelaste esta acción"; elevación 0 |
| `error` | `Aviso` error embebido "No se pudo cobrar. Tu carrito sigue aquí." + [Reintentar] |
| `caducada` | "Esta propuesta ya no está vigente" + botones deshabilitados (`EXC-4`); elevación 0 |

Props, nombres de oficio (Caja, Bodega, Cuentas, Promociones, Ayuda de pagos, Asistente) y accesibilidad **sin cambios**.

---

### 9.11 `HojaInferior` → Bottom sheet

**Anatomía (modal):**
```
          ▬▬▬▬  (drag handle 32×4, onSurfaceVariant, área táctil 48)
Editar producto                         [✕ Cerrar]   ← titleLarge 22 · Boton text con icono
(contenido con scroll)
──────────────── (pie fijo, divisor outlineVariant)
[======== Guardar cambios ========]                  ← filled 56
```
- Contenedor `surfaceContainerLow`, esquinas superiores `extraLarge` (28), elevación **level1**, alto máx. 90 %, ancho completo (≤ 640 dp).
- **Scrim** `#000000` al **32 %** detrás (M3); tocarlo cierra salvo `sinCerrar`. El contenido detrás queda inerte (`importantForAccessibility="no-hide-descendants"`).
- Drag handle: arrastrar hacia abajo cierra (M3), **pero** siempre hay botón visible "Cerrar" (icono + texto) para quien no hace gestos (`EXC-7`).
- Entrada `medium4` `emphasizedDecelerate`; salida `short4` `emphasizedAccelerate`; movimiento reducido → directo.
- `tipo="estandar"` (no modal, sin scrim, coexiste con la pantalla): para el **tutor de pagos**; se ancla encima de la barra inferior y la pantalla reserva su alto para no tapar campos ni el botón principal.

```ts
interface HojaInferiorProps {
  visible: boolean; titulo: string; onCerrar: () => void; children: ReactNode;
  pie?: ReactNode; sinCerrar?: boolean;
  tipo?: 'modal' | 'estandar';   // NUEVO, default 'modal'
  altoMaximo?: number;           // NUEVO, fracción 0–1, default 0.9
}
```
Accesibilidad: `accessibilityViewIsModal`, foco inicial en el título, `onRequestClose` = Cerrar.

---

### 9.12 `Dialog` (nuevo) — confirmaciones destructivas

Contenedor `surfaceContainerHigh`, shape `extraLarge` (28), elevación **level3**, scrim 32 %, ancho 280–560, padding 24. Icono opcional 24 `secondary` centrado · titular `headlineSmall` 24 `onSurface` · cuerpo `bodyMedium`→16 `onSurfaceVariant` (7.63) · acciones alineadas al final, gap 8; con 3 acciones o letra grande se **apilan** a ancho completo. La acción segura va en `filled`/`tonal`; la destructiva en `text` color `error` (5.27 sobre T92) o `filledError` si es el último paso.

```ts
interface DialogoProps {
  visible: boolean; titulo: string; mensaje?: string; icono?: NombreIcono;
  acciones: { texto: string; onPress: () => void; variante: VarianteBoton }[]; // orden visual
  onCerrar?: () => void;  // ausente = obliga a elegir
}
```
Accesibilidad: `accessibilityViewIsModal`, `role="alert"` en el título, foco inicial en el título.

---

### 9.13 `Encabezado` → Top app bar (small)

**Anatomía:** alto **64**, padding horizontal 4–16.
`[← Atrás]` (Boton `text` con icono, 48 mín.; `EXC-8`: M3 usa solo icono, aquí icono + texto) · título `titleLarge` 22 `onSurface` (envuelve a 2 líneas; la barra crece) · acción final opcional (Boton `text` con icono + texto, p. ej. "Caja").
- Contenedor `surface` en reposo (elevación 0); al hacer scroll → `surfaceContainer` (nivel 2 **tonal**, sin sombra), transición `short4`.
- `etiquetaSimulacion` → banner `EtiquetaSimulacion` franja debajo.
- `headerShadowVisible: false` en headers de Expo Router (la separación es tonal).

Props sin cambios + `elevadoAlDesplazar?: boolean` (default true; la pantalla pasa `scrollY > 0`).

---

### 9.14 Navigation bar (pestañas)

Reemplaza el `tabBar` por defecto (`tabBar={(p) => <BarraNavegacion {...p} />}` en `(tabs)/_layout.tsx`).

**Anatomía por destino:** indicador píldora **64×32** (`secondaryContainer`, shape `full`) con icono 24 dentro · etiqueta debajo (gap 4).
- Contenedor `surfaceContainer`, alto **80** + safe area, elevación 0 (tonal), sin borde.
- 4 destinos: Inicio · Cobrar · Inventario · Asistente (cada uno ≥ 90 dp de ancho en 360 dp).

| Estado | Indicador | Icono | Etiqueta |
|---|---|---|---|
| Activo | `secondaryContainer` visible | **relleno** (`home`, `cash-register`, `package-variant`, `chat`) `onSecondaryContainer` (7.24) | `labelMedium`→**16/700** `onSurface` (14.74) |
| Inactivo | — | contorno (`home-outline`, `cash-register`, `package-variant-closed`, `chat-outline`) `onSurfaceVariant` (8.03) | 16/500 `onSurfaceVariant` |
| Presionado | Capa 10 % en el área del indicador | | |

Tres señales de "activo" (píldora, icono relleno, peso 700) → no depende del color. Etiquetas **siempre visibles** (M3 permite ocultarlas; aquí no). Badge opcional (p. ej. alertas en Inicio): círculo `error` con número `onError` 16/500 alto 24 (`EXC-1`), con texto en el label accesible ("Inicio, 2 alertas").
Indicador entra con `medium2` `standard` (sin animación con movimiento reducido).
Accesibilidad: `accessibilityRole="tab"`, `accessibilityState={{ selected }}`, contenedor `role="tablist"`.

---

### 9.15 Extended FAB "Cobrar con foto" (nuevo)

**Anatomía:** icono `camera` 24 + etiqueta "Cobrar con foto" `labelLarge` 16/500.
- **Color: variante *primary*** (M3 Expressive): contenedor `primary`, contenido `onPrimary` (**6.46:1**). Se elige sobre el *primaryContainer* por defecto porque sobre `surface` T98 un contenedor T90 se distingue poco (1.2:1) y es **la** acción principal de la app.
- Alto **56**, ancho mín. 80, padding 16 (icono) / 20 (texto), gap 12, shape `large` (16), elevación **level3** (foco/hover level4; presionado level3 + capa 10 %).
- Posición: esquina inferior derecha, 16 dp del borde y 16 dp sobre la navigation bar (tercio inferior, zona del pulgar). Las listas agregan `paddingBottom = 56 + 32` para que el FAB no tape el último elemento.
- **Nunca se colapsa a solo icono** al hacer scroll (`EXC-9`: iconos siempre con texto).
- Pantallas: **Inicio** y **Cobrar**. No aparece en pantallas con barra de acción inferior propia (revisión, comprobante) ni con teclado abierto.
- Estado `cargando` no aplica (navega de inmediato a la cámara).

```ts
interface FabExtendidoProps {
  texto: string; icono: NombreIcono; onPress: () => void;
  accessibilityHint?: string;   // 'Abre la cámara para cobrar los productos del mostrador'
  separacionInferior?: number;  // default 16
}
```
Accesibilidad: `role="button"`, label = texto visible; es el último elemento en el orden de foco de la pantalla (después del contenido), salvo que sea la única acción.

---

## 10. Excepciones de accesibilidad sobre M3

| Id | M3 dice | Proyecto hace | Motivo |
|---|---|---|---|
| `EXC-1` | Body S 12, Label M/S 12/11, badge 11 | Todo texto ≥ 16 sp | Baja visión, adultos mayores |
| `EXC-2` | Botón 40 dp (48 de área táctil) | Botón visual 48 dp; principal 56 | Pulgar con prisa, temblor |
| `EXC-3` | Etiqueta flotante dentro del campo (12 sp al enfocar) | Etiqueta fija arriba, 16 sp | La etiqueta no se encoge ni se mueve |
| `EXC-4` | Deshabilitado 38 % / 12 % | `onSurfaceVariant` sobre `surfaceContainerHighest` + motivo visible | Saber qué falta (Nielsen #5, #9) |
| `EXC-5` | Progreso lineal 4 dp | 8 dp | Visibilidad del paso |
| `EXC-6` | Card outlined 1 dp `outlineVariant` | Fila con error: 2 dp `error` | El borde es parte del estado (con icono + texto) |
| `EXC-7` | Bottom sheet se cierra arrastrando | Además, botón "Cerrar" visible | Gestos difíciles para usuarios nuevos |
| `EXC-8` | Navegación "atrás" solo icono | Icono + "Atrás" | Iconos siempre con texto |
| `EXC-9` | Extended FAB se colapsa al hacer scroll | Nunca se colapsa | Iconos siempre con texto |
| `EXC-10` | Filter chip sin seleccionar: borde 1 dp `outlineVariant` | Borde 1 dp `outline` (4.27:1 sobre `surface`, 4.06:1 sobre `surfaceContainerLow`), fondo transparente | El límite de un control tocable debe tener ≥ 3:1 (WCAG 1.4.11) |
| `EXC-11` | Text field con etiqueta visible | Compositor del chat (02-asistente §2.5) **sin etiqueta visible**: label accesible "Tu pregunta", placeholder "Escribe tu pregunta…" y botón "Enviar" con icono + texto al lado. Solo aplica al compositor de chat; todo otro campo sigue con `EXC-3` | Patrón de mensajería estándar; el contexto (chat + Enviar) es inequívoco y la etiqueta restaría espacio sobre el teclado |

---

## 11. Justificación HCI / Nielsen

| # | Heurística | Cómo la cubre el sistema |
|---|---|---|
| 1 | Visibilidad del estado | Linear progress con "Paso X de N"; botones con estado cargando y texto; banner de sin conexión persistente; top app bar cambia de tono al desplazar; card de acción baja de elevación cuando ya se ejecutó |
| 2 | Mundo real | Nombres de oficio, "pz", "c/u", "Revisa", montos leídos como "pesos" |
| 3 | Control y libertad | Snackbar "Deshacer"; "Revisar y editar" en cards; "Cerrar" visible en hojas; "Atrás" que guarda borrador |
| 4 | Consistencia | Patrones M3 nativos de Android (navigation bar, FAB, snackbar, bottom sheet); un solo filled/FAB por vista; mismos 5 tipos de aviso |
| 5 | Prevención de errores | Diálogo antes de borrar todo; tope de stock; botón principal nunca muerto; motivo visible en deshabilitados |
| 6 | Reconocer > recordar | Chips de estado con texto; list items con precio c/u y subtotal; números que ligan foto y filas |
| 7 | Flexibilidad | Escribir cantidad directa; atajos de efectivo como chips; arrastrar para cerrar hojas (opcional) |
| 8 | Minimalismo | Elevación y color solo con función; sin gradientes, blur ni ilustraciones decorativas |
| 9 | Recuperación de errores | `Aviso` error exige acción; errores de campo en línea con ejemplo |
| 10 | Ayuda | Acción "Caja" en la top app bar; supporting text en campos; tutor como bottom sheet estándar |

**Accesibilidad:** todos los pares de texto ≥ 4.5:1 (mín. 5.00:1) y bordes/indicadores ≥ 3:1 (§2.3) · táctil ≥ 48 dp con 8 dp de separación · todo texto ≥ 16 sp y escalable · estados con icono + texto (+ peso / forma) · acciones principales en el tercio inferior (Extended FAB, barra de total) · lector: roles, labels, live regions definidos por componente · movimiento M3 con `useReducedMotion`.

---

## 12. Cambios a `src/theme.ts`

Estructura nueva, conservando exportaciones viejas como alias para migrar por partes:

```ts
export const color = { primary: '#415F91', onPrimary: '#FFFFFF', /* …todos los roles de §2.2… */ } as const;
export const type = { headlineLarge: {...}, titleLarge: {...}, /* §3 */ } as const;
export const shape = { none: 0, extraSmall: 4, small: 8, medium: 12, large: 16, extraLarge: 28, full: 9999 } as const;
export const elevacion = { level0, level1, level2, level3, level4, level5 };   // §5
export const estado = { hover: 0.08, focus: 0.10, pressed: 0.10, dragged: 0.16 } as const;
export const motion = { easing: {...}, duration: {...} } as const;           // §7
export const anilloFoco = { outlineColor: color.secondary, outlineWidth: 3, outlineOffset: 2, outlineStyle: 'solid' };
export const scrim = 'rgba(0,0,0,0.32)';

/** @deprecated alias flat → M3 (borrar al terminar la migración) */
export const colores = {
  fondo: color.surface, superficie: color.surfaceContainer, texto: color.onSurface,
  textoSecundario: color.onSurfaceVariant, borde: color.outline, divisor: color.outlineVariant,
  acento: color.primary, sobreAcento: color.onPrimary, peligro: color.error, sobrePeligro: color.onError,
  exito: color.success, sobreExito: color.onSuccess, oscuro: color.inverseSurface, sobreOscuro: color.inverseOnSurface,
  foco: color.secondary, deshabilitadoFondo: color.surfaceContainerHighest, deshabilitadoTexto: color.onSurfaceVariant,
  // acentoPresionado / peligroPresionado: eliminados → capas de estado
};
export const tipografia = { cuerpo: type.bodyLarge, cuerpoGrande: type.bodyLargePlus, nombreProducto: type.titleMedium,
  etiqueta: type.labelLarge, monto: type.amount, montoGrande: type.headlineLarge, subtitulo: type.titleLarge, titulo: type.headlineSmall };
export const radios = { recto: shape.none, chico: shape.small, medio: shape.medium };
// bordes, espacio, tactil, iconos, medidas: se conservan (medidas.barraSuperior 56→64, barraPestanas 72→80).
```
Además: utilidad `conAlfa(hex, alfa)` para capas de estado y ripple; componente interno `CapaEstado` (overlay iOS + `android_ripple`) reutilizado por todos los tocables.
