# Fase 2 — Sistema de diseño (identidad nueva)

> Fuente única: `front/src/theme.ts`. Este documento **sustituye los valores** de `front/docs/diseno/00-sistema.md` (que sigue describiendo la estructura de componentes y las excepciones de accesibilidad EXC-1…10).
> Origen de la identidad: documento "BookEase" (paleta, tipografía, formas, sombras). Se adaptó a una app móvil para tenderos.
> Contrastes calculados con `docs/ui-ux/contraste.mjs` (`node docs/ui-ux/contraste.mjs`).

## Qué cambió y qué se conservó

| Se conserva | Cambia |
|---|---|
| Nombres de rol de color (`primary`, `surface`, `onSurface`…), así ningún componente se rompe | Todos los **valores** de color |
| Reglas de accesibilidad: texto ≥ 16 sp, táctil ≥ 48, un solo primario, icono + texto | Tipografía: Material del sistema → **Inter** |
| Capas de estado, movimiento, grid de 4 dp | Radios 4/8/12/16/28 → **4/6/10/16/20** |
| Elevación como única fuente de sombras | Sombras Material → **suaves y difusas** (azul pizarra, 6–12 % de opacidad) |

## Color (claro)

| Rol | Valor | Uso |
|---|---|---|
| `primary` | `#1A56DB` | Botón principal, enlace, ítem activo |
| `onPrimary` | `#FFFFFF` | Texto sobre primario |
| `primaryContainer` | `#E8F0FE` | Badges, chips seleccionados, fondos suaves (`--color-primary-soft`) |
| `onPrimaryContainer` | `#1543B0` | Texto sobre `primaryContainer` (hover del primario de la marca) |
| `secondary` | `#4B5563` | Neutro oscuro: anillo de foco, texto secundario |
| `secondaryContainer` | `#E3E8F4` | Superficies neutras destacadas |
| `tertiary` | `#5B3FD6` | **Acento violeta** (fin del gradiente) |
| `tertiaryContainer` | `#ECE7FD` | Fondo suave del acento |
| `surface` | `#F5F7FB` | Fondo de pantalla (`--color-bg-alt`) |
| `surfaceContainerLowest/Low` | `#FFFFFF` | Tarjetas, header, campos (`--color-bg`) |
| `surfaceContainer … Highest` | `#EEF1F7 · #E8ECF4 · #E2E7F0` | Niveles tonales |
| `onSurface` | `#0F172A` | Titulares y texto principal |
| `onSurfaceVariant` | `#4B5563` | Párrafos y descripciones |
| `outline` | `#6B7280` | Borde de campos, iconos auxiliares |
| `outlineVariant` | `#E5E7EB` | Bordes de tarjetas y separadores (1 px) |
| `inverseSurface` | `#0F172A` | Snackbar, banda de simulación, cámara |
| `error` / `errorContainer` | `#DC2626` / `#FEE2E2` | Error, cancelada |
| `success` / `successContainer` | `#15803D` / `#DCFCE7` | Venta registrada, confirmado |
| `warning` / `warningContainer` | `#B45309` / `#FEF3C7` | Poco stock, por caducar, pendiente |

**Desviaciones respecto al documento de identidad (con motivo):**
- `success` `#16A34A` → **`#15803D`**: con texto blanco el original da 3.3:1 (falla AA); el nuevo da 5.0:1.
- `warning` `#D97706` → **`#B45309`**: el original da 3.2:1 con blanco; el nuevo da 5.0:1.
- `--color-text-subtle` `#6B7280` solo se usa para bordes/iconos (4.5:1 sobre el fondo). **No se usa para texto de lectura**: EXC-1 pide ≥ 4.5:1 y, por tamaño mínimo 16 sp, el texto auxiliar usa `onSurfaceVariant`.
- Colores de evento del calendario (`#1E90FF`…): no aplican (la app no tiene calendario).

**Gradiente de marca** (`gradienteMarca`: `#1D4ED8 → #5B3FD6`, 90°): solo en el logotipo y en 1–2 palabras clave del titular. En móvil requiere `expo-linear-gradient` (instalado).

**Regla 60-30-10:** ~60 % `surface` y blanco · ~30 % texto y neutros · ~10 % `primary` y gradiente (solo acciones y acentos).

## Contrastes WCAG 2.1 AA (verificados)

| Par | Ratio | Mín. |
|---|---|---|
| `onPrimary` / `primary` | 6.18 | 4.5 |
| `onPrimaryContainer` / `primaryContainer` | 7.44 | 4.5 |
| `onSecondary` / `secondary` | 7.56 | 4.5 |
| `onSecondaryContainer` / `secondaryContainer` | 11.96 | 4.5 |
| `onTertiary` / `tertiary` | 6.72 | 4.5 |
| `onTertiaryContainer` / `tertiaryContainer` | 9.19 | 4.5 |
| `onError` / `error` | 4.83 | 4.5 |
| `onErrorContainer` / `errorContainer` | 6.80 | 4.5 |
| `onSuccess` / `success` | 5.02 | 4.5 |
| `onSuccessContainer` / `successContainer` | 8.30 | 4.5 |
| `onWarning` / `warning` | 5.02 | 4.5 |
| `onWarningContainer` / `warningContainer` | 8.15 | 4.5 |
| `onSurface` / `surface` | 16.65 | 4.5 |
| `onSurface` / blanco | 17.85 | 4.5 |
| `onSurface` / `surfaceContainerHighest` | 14.39 | 4.5 |
| `onSurfaceVariant` / `surface` | 7.05 | 4.5 |
| `onSurfaceVariant` / blanco | 7.56 | 4.5 |
| `onSurfaceVariant` / `surfaceContainerHighest` | 6.09 | 4.5 |
| `primary` como texto / `surface` | 5.76 | 4.5 |
| `error` como texto / `surface` | **4.50** (justo en el límite) | 4.5 |
| `success` como texto / `surface` | 4.68 | 4.5 |
| `warning` como texto / `surface` | 4.68 | 4.5 |
| `outline` / `surface` (bordes de campo) | 4.51 | 3 |
| `primary` / `surface` (foco, iconos) | 5.76 | 3 |
| `inverseOnSurface` / `inverseSurface` | 16.65 | 4.5 |

El modo oscuro (`colorOscuro`) también pasa todos los pares (ver el script). **Aún no está conectado a la app**: los componentes importan `color` como constante; activarlo exige un proveedor de tema (Fase 5).

## Tipografía (Inter)

En React Native el peso va en el nombre de la fuente: `fuente.regular|medium|semibold|bold|extrabold` (`Inter_400Regular`…`Inter_800ExtraBold`). **No usar `fontWeight`** (se reemplazó en toda la app; `pesoActivo` es ahora `{ fontFamily: Inter bold }`). La app espera a que Inter cargue; si falla, usa la fuente del sistema.

| Estilo | Tamaño / interlínea | Fuente | Tracking | Equivale a |
|---|---|---|---|---|
| `displaySmall` | 40 / 46 | ExtraBold | −1.2 | display |
| `headlineLarge` | 32 / 38 | Bold | −0.64 | h1 / h2 |
| `headlineSmall` | 24 / 30 | Bold | −0.24 | h2 |
| `titleLarge` | 22 / 28 | SemiBold | 0 | h3 |
| `titleMedium` | 18 / 26 | SemiBold | 0 | h3 |
| `titleSmall` | 16 / 24 | SemiBold | 0 | — |
| `bodyLargePlus` | 20 / 30 | Regular | 0 | body-lg (modo letra grande) |
| `bodyLarge/Medium/Small` | 16 / 24–26 | Regular | 0 | body y body-sm |
| `labelLarge` | 16 / 24 | SemiBold | 0 | botón |
| `labelMedium/Small` | 16 / 24 | Medium | 0 | etiquetas |
| `amount` | 20 / 28 | Bold, cifras tabulares | 0 | importes |

**Desviación:** la identidad define `body-sm` 14 px y `caption` 12 px. Se **mantiene el mínimo de 16 sp (EXC-1)** porque el usuario es un tendero con una mano, posible baja visión y poca práctica con apps. La jerarquía se logra con saltos de tamaño en los titulares (16 → 18 → 22 → 24 → 32 → 40), peso y color.

## Forma, espacio y sombra

| Token | Valores |
|---|---|
| `shape` | `extraSmall` 4 · `small` **6** (badges) · `medium` **10** (botones, inputs) · `large` 16 (tarjetas) · `extraLarge` **20** (diálogos, sheets) · `full` (píldoras) |
| `espacio` | 4 · 8 · 12 · 16 · 24 · 32 (grid de 4 dp) |
| `elevacion` | `level1` `0 1 2 /6 %` · `level2` `0 4 12 /7 %` · `level3` `0 8 24 /8 %` · `level4` `0 12 28 /10 %` · `level5` `0 16 40 /12 %`; color `#0F172A`. Android usa `elevation` nativa (más dura: limitación de la plataforma) |
| `medidas.contenidoAnchoMaximo` | 640 (para centrar el contenido en web/tablet; se aplica en Fase 3) |

## Verificación de esta fase

| Chequeo | Resultado |
|---|---|
| `tsc --noEmit` | ✅ |
| `expo lint` | ✅ |
| Hex/rgb fuera de `theme.ts` | ✅ ninguno |
| `fontWeight` fuera de `theme.ts` | ✅ ninguno (13 archivos migrados) |
| Arranque web | ✅ Inter cargada, primario azul visible |
| Móvil real / Android | ⚠️ no probado (solo web) |

## Pendiente para fases siguientes

- Ancho máximo del contenido (usa `medidas.contenidoAnchoMaximo`).
- Logotipo con gradiente de marca (componente `Marca`) y titular con palabra destacada.
- Modo oscuro (proveedor de tema).
- Revisar visualmente cada pantalla: los cambios de radio y color afectan a los 21 componentes y no se auditó cada estado.

---

# Fase 3 — Componentes base

Los componentes ya existían (una sola versión de cada uno, en `front/src/components/`). No se crearon variantes nuevas: se **alinearon a la identidad** y se corrigió el significado del color.

## Cambios por componente

| Componente | Cambio |
|---|---|
| `Boton` | Radio 10 (antes píldora). `filled` primario; `outlined` con borde y texto `primary`; `tonal` en azul suave (`primaryContainer`). Sigue: alto 48/56, estado cargando y deshabilitado legible. **Un solo `filled` por sección.** |
| `Campo` | Radio 10 (antes 4). Etiqueta visible, ayuda y error debajo (ya existían). |
| `ChipFiltro`, `ChipSugerencia` | Píldora (`full`). Seleccionado = `primaryContainer` + check + Inter bold (no depende solo del color). |
| `BarraNavegacion` | Indicador activo en `primaryContainer`, icono relleno y etiqueta en negrita. |
| `StepperCantidad` | Botones tonales en azul suave; radio 10. |
| `TarjetaAccion`, `FilaProducto`, `Aviso` (tarjeta) | Radio 16, borde 1 px `outlineVariant`, sombra suave. |
| `Snackbar` | Radio 6, fondo `inverseSurface`. |
| Hojas de cobro / edición, cámara | Opción elegida en azul suave (antes gris azulado). |
| **`Marca` (nuevo)** | Logotipo: icono de tienda blanco sobre el degradado de marca (48 dp). Uno de los dos únicos usos permitidos del degradado. Se usa en la cabecera de Inicio. |
| **`ContenedorPantalla` (nuevo)** | Centra el contenido con ancho máximo 640 dp en web/tablet; en teléfono no cambia nada. Aplicado a Inicio, Cobrar, Inventario, Asistente, Historial y Venta. |

## Color con significado

El violeta (`tertiary`) se usaba para "ojo / por revisar / poco stock / por caducar". Con la identidad nueva el violeta es el **acento de marca**, no una alerta, así que esos usos pasaron al semántico `warning` (ámbar `#B45309` + `warningContainer` + `onWarningContainer`, todos ≥ 4.5:1):

`FilaProducto` (borde "Revisa") · `IndicadorConfianza` · alertas de Inicio · filas y resumen de Inventario · recuadros de `foto-detecciones`.

El gráfico del corte de caja sigue usando el violeta como una de sus 4 series (es acento, no alerta).

## Estados de cada componente (Fase 3: lo que está cubierto)

| Componente | Normal | Hover/pressed | Foco | Deshabilitado | Cargando | Error |
|---|---|---|---|---|---|---|
| Boton | ✅ | ✅ | ✅ (anillo) | ✅ | ✅ | variantes `*Error` |
| Campo | ✅ | — | ✅ | ✅ | — | ✅ |
| Chips | ✅ | ✅ | ✅ | — | — | — |
| Tarjeta | ✅ | ✅ | ✅ | — | — | — |

No se auditó el aspecto de **cada** estado en pantalla (solo se revisó Inicio, Cobrar, Inventario y Asistente en estado normal, en web).

## Pendiente conocido (para la Fase 4)

- En Inventario el botón flotante "Agregar mercancía" tapa los chips de filtro y las filas (también "Cobrar con foto" en Cobrar).
- Título duplicado en Asistente (cabecera de pestaña + cabecera propia).
- La pista de `BarraPasos` usa `secondaryContainer` (#E3E8F4) sobre `surface`: bajo contraste (~1.1:1). Es decorativa (el indicador `primary` y el texto "Paso X de 3" llevan la información), pero se revisará.
