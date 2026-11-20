# 01 · Recorrido principal: Cobrar con foto (M3)

> Depende de: `00-sistema.md` (roles de color, tipografía, forma, elevación y componentes M3). Endpoint de visión: `POST /vision/pos-checkout` → `RespuestaPosCheckout`.
> Usuario: **tendero** cobrando en el mostrador, con el cliente esperando enfrente. Prioridad: rapidez + cero cobros equivocados.
> Rutas: `(tabs)/cobrar.tsx` → `camara.tsx?modo=cobro` → (`analizando` dentro de `camara`) → `revision/cobro.tsx` → `venta/[id].tsx`.
> **Cambio respecto a la versión flat: solo presentación.** Flujo, estados, errores, reglas de negocio y contrato con back son los mismos.

---

## 1. Concepto y enfoque

**Recorrido:** `Cobrar` → `Cámara` → `Analizando foto…` → `Revisa la venta` → `Cobrar $X` (bottom sheet de pago) → `Venta registrada` (comprobante, stock descontado) → visible en Inicio / Historial.

| Pantalla | Enfoque | Componentes M3 dominantes | Por qué |
|---|---|---|---|
| Pestaña Cobrar | **Tarjetas** (pocas, grandes) + Extended FAB | Extended FAB, cards outlined, list items | La acción dominante ("Cobrar con foto") baja al pulgar como Extended FAB; los atajos son cards. |
| Cámara | **Guiado** | Barras `inverseSurface`, icon buttons, obturador | Momento de mayor incertidumbre. |
| Revisión del carrito | **Lista densa** con `+`/`−` | List items, cards filled/outlined para problemas, barra de total tonal, snackbar | Ver todo el ticket y corregir en 1–2 toques; los problemas arriba. |
| Comprobante | **Guiado/resumen** | Card filled `successContainer`, list items, cards outlined | Cierre claro: qué se cobró, qué se descontó, qué sigue. |

**Progreso del recorrido** (`BarraPasos` = linear progress con pasos): `Foto` · `Revisar` · `Listo`.

**Medición para la demo:** `inicio = Date.now()` al abrir la cámara, `fin` al registrar; el comprobante compara contra la referencia manual (§2.6).

---

## 2. Arquitectura de pantallas

### 2.1 Pestaña **Cobrar** (`(tabs)/cobrar.tsx`)

```
┌──────────────────────────────────────────────┐
│ Cobrar                                       │ Top app bar small (surface → surfaceContainer al desplazar)
├──────────────────────────────────────────────┤
│ [Banner sinConexion — solo sin internet]     │ Aviso franja, surfaceContainerHigh
│                                              │
│ ╭─ Venta sin terminar ────────────────────╮  │ ← solo si hay borrador · Aviso tarjeta tipo info
│ │ (i) Tienes una venta de $88.00 sin cobrar│  │   (surfaceContainerHigh, shape medium)
│ │        [Descartar] (text) [Continuar venta] (tonal) │   ← tonal: el Extended FAB es la única acción filled de la vista
│ ╰──────────────────────────────────────────╯  │
│                                              │
│ ╭─ Card filled (surfaceContainerHighest) ──╮ │ ← guía breve, sin botón (el botón es el FAB)
│ │ [camera 24] Cobra en 3 pasos              │ │ titleMedium 18/500
│ │ 1 Pon los productos en el mostrador       │ │ bodyLarge 16, onSurfaceVariant
│ │ 2 Toca "Cobrar con foto"                  │ │
│ │ 3 Revisa y cobra                          │ │
│ ╰───────────────────────────────────────────╯ │
│                                              │
│ Otras formas de cobrar          (titleMedium)│
│ ╭ Card outlined ──╮ ╭ Card outlined ──╮      │ shape medium, borde outlineVariant, alto ≥ 96,
│ │ [magnify]       │ │ [replay]        │      │ tocables completas (ripple); se apilan con letra grande
│ │ Buscar producto │ │ Repetir última  │      │ titleSmall 16/500 + bodyLarge onSurfaceVariant
│ │ (sin foto)      │ │ venta · $45.00  │      │
│ ╰─────────────────╯ ╰─────────────────╯      │
│                                              │
│ Ventas de hoy                 [Ver todas →]  │ titleMedium + Boton text
│ 13:42  3 productos · Efectivo     $88.00     │ FilaVenta = list item 2 líneas (alto ≥ 64)
│ ─────────────────────────────── outlineVar.  │
│ 13:10  1 producto                 $18.00     │
│        [cloud-upload] Pendiente de enviar    │
│ ...máx 5                                     │
│ (padding inferior 56 + 32 para librar FAB)   │
│                       ╭────────────────────╮ │
│                       │ [camera] Cobrar    │ │ ← EXTENDED FAB primary (#415F91 / blanco 6.46:1)
│                       │          con foto  │ │   56 alto, shape large, level3, 16 dp sobre la barra
│                       ╰────────────────────╯ │
├──────────────────────────────────────────────┤
│ (Inicio) (▣Cobrar) (Inventario) (Asistente)  │ Navigation bar 80, surfaceContainer, píldora 64×32
└──────────────────────────────────────────────┘
```

**Estados**
| Estado | Qué se ve |
|---|---|
| Vacío (sin ventas hoy) | En lugar de la lista: `Aviso` tarjeta `info` "Todavía no hay ventas hoy. Tu primera venta aparecerá aquí." "Repetir última venta" se oculta si nunca hubo venta. |
| Cargando ventas | 3 list items esqueleto: bloques `surfaceDim` shape `small`, sin animación (o pulso de opacidad `long2` solo si no hay movimiento reducido) + texto oculto "Cargando ventas de hoy" (live region). |
| Error al cargar ventas | `Aviso` tarjeta `error` "No pudimos traer tus ventas de hoy." [Reintentar] (filled). El Extended FAB **sigue funcionando**. |
| Sin conexión | Banner `sinConexion` arriba. Bajo el FAB no cabe texto: la card guía cambia a `Aviso info` "Sin internet la foto no se puede revisar. Puedes cobrar buscando el producto." y la card "Buscar producto" queda **primera y a ancho completo**. El FAB se mantiene (la cámara funciona; el error de análisis ofrece cobrar buscando). |
| Ventas en cola | List items con `cloud-upload` + "Pendiente de enviar" (texto, no solo icono). |
| Venta recién registrada (al volver del comprobante) | Snackbar "Venta de $88.00 registrada" con acción "Ver" (8 s; sin límite con lector de pantalla), 8 dp sobre el FAB; se anuncia con `anuncio`. |

---

### 2.2 **Cámara** — modo cobro (`camara.tsx?modo=cobro`)

Pantalla completa sin top app bar estándar. Barras en `inverseSurface #2E3036` con contenido `inverseOnSurface #F0F0F7` (11.59:1), opacas.

```
┌──────────────────────────────────────────────┐
│ [✕ Cerrar]     Cobrar con foto     [? Ayuda] │ barra inverseSurface 64; botones text con icono 48 (contenido inverseOnSurface)
├──────────────────────────────────────────────┤
│ ╭──────────────────────────────────────────╮ │ vista previa shape large (16)
│ │  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓    │ │ guía: doble trazo 2 dp #FFFFFF interior + 2 dp #2E3036 exterior
│ │  ┃  Que se vean todos los productos ┃    │ │ texto titleMedium 18/500 inverseOnSurface sobre
│ │  ┃  dentro del cuadro               ┃    │ │ caja inverseSurface shape small (no sobre la imagen)
│ │  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛    │ │
│ ╰──────────────────────────────────────────╯ │
├──────────────────────────────────────────────┤
│ [lightbulb] Consejo: separa los productos y  │ franja inverseSurface, bodyLarge 16
│ evita reflejos de la luz                     │
├──────────────────────────────────────────────┤
│ (image-multiple)   (  ◉  )        (flash)    │ barra inverseSurface, alto ≥ 120
│  Galería          Tomar foto      Luz: No    │ icon buttons tonales 56 (secondaryContainer) + etiqueta 16
└──────────────────────────────────────────────┘
```

- **Disparador** (excepción documentada, no es componente M3): círculo **72** relleno `#FFFFFF`, borde 4 dp `inverseSurface`, contorno exterior 2 dp `#FFFFFF`; sin sombra. Al tocar: bloqueado (evita dobles), borde pasa a `primary` y la etiqueta cambia a "Tomando foto…". Ripple circular 10 %.
- **Galería / Luz**: icon buttons **tonales** 56×56 (`secondaryContainer` / `onSecondaryContainer` 7.24:1) con etiqueta 16/500 `inverseOnSurface` debajo. "Luz: No" / "Luz: Sí" cambia texto **y** el botón pasa a estado seleccionado (`primary` / `onPrimary`), no solo el icono.
- **Ayuda**: bottom sheet modal con 3 ejemplos ("Bien: productos separados, de frente. Mal: amontonados, con reflejo").
- Tras la foto: compresión (`expo-image-manipulator`, lado largo 1280, JPEG 0.7) y paso directo a **Analizando** (sin "¿usar esta foto?").

**Estados de permiso** (fondo `surface`, layout de estado vacío M3: icono 48 `onSurfaceVariant`, `headlineSmall`, `bodyLarge`, botones abajo en el tercio inferior)

| Estado | Contenido y botones |
|---|---|
| Sin decidir | "Necesitamos tu cámara" · "La usamos solo para ver los productos que vas a cobrar. No guardamos fotos de personas." · [Permitir cámara] (filled 56) · [Usar una foto de la galería] (outlined) |
| Denegado (se puede volver a pedir) | "La cámara está apagada para esta app" · [Volver a intentar] (filled) · [Usar foto de la galería] (outlined) |
| Denegado permanente | Igual + "Actívala en Ajustes > Permisos > Cámara." · [Abrir ajustes] (filled, `Linking.openSettings()`) · [Usar foto de la galería] (outlined) · [Cobrar buscando producto] (text) |
| Galería denegada | `Aviso` tarjeta `error` en la hoja: "No tenemos permiso para ver tus fotos." [Abrir ajustes] |
| Cámara no disponible / error al abrir | `Aviso` tarjeta `error` "No se pudo abrir la cámara." [Reintentar] (filled) · [Usar foto de la galería] (text) |

---

### 2.3 **Analizando foto…** (estado de `camara.tsx`, misma ruta)

```
┌──────────────────────────────────────────────┐
│ [✕ Cancelar]                                 │ Top app bar small, surface
├──────────────────────────────────────────────┤
│ Paso 1 de 3 · Foto                           │ BarraPasos (linear progress 8 dp, 1/3)
│ ▓▓▓▓▓▓▓▓▓▓▓ ░░░░░░░░░░░░░░░░░░░░░░ •          │
│                                              │
│ ╭──────────────────────────────╮             │ miniatura shape large, alto máx 40 %
│ │        (foto tomada)         │             │
│ ╰──────────────────────────────╯             │
│                                              │
│   (◌ circular progress indeterminado 48,     │ M3 circular progress: indicador primary,
│      primary, pista secondaryContainer)      │ pista secondaryContainer, grosor 4
│   Buscando los productos…                    │ titleLarge 22
│   ✓ Foto lista                               │ list items 1 línea con icono:
│   ◌ Enviando foto                            │ check-circle success · circular 24 · circle-outline onSurfaceVariant
│   ○ Reconociendo productos                   │
│                                              │
│   ╭ (i) Está tardando más de lo normal. ───╮ │ Aviso tarjeta info (tras 8 s)
│   │ Puedes seguir esperando.               │ │
│   ╰────────────────────────────────────────╯ │
├──────────────────────────────────────────────┤
│ [ Tomar otra foto ] (outlined 48)            │
└──────────────────────────────────────────────┘
```

- Etapas reales: `preparando` → `enviando` → `reconociendo` (tras 1.5 s sin respuesta; sin progreso numérico falso).
- Tiempo límite **20 s** (`AbortController`); aviso "tardando" a los 8 s. `Cancelar` aborta y regresa a la cámara.
- Movimiento reducido: el circular progress se reemplaza por icono estático `timer-sand` + el mismo texto (la info no depende del giro).
- Accesibilidad: cada etapa se anuncia; `accessibilityState={{ busy: true }}`.

**Resultados posibles del análisis** (sin cambios)

| Respuesta | Destino / pantalla |
|---|---|
| 200, `items.length > 0`, zod OK | → `revision/cobro` |
| 200, `items.length === 0` | Error **Sin productos detectados** |
| 422 o zod falla | Error **Foto no procesable** |
| Sin conexión antes de enviar | Error **Sin conexión** |
| Timeout 20 s / 503 / 5xx | Error **Tiempo agotado / servicio ocupado** |

**Pantallas de error del análisis:** miniatura arriba · `Aviso` tarjeta (tipo `error` → `errorContainer`/`onErrorContainer` 7.24:1; tipo `sinConexion`/`tiempo` → `surfaceContainerHigh`) · botones en el tercio inferior: acción principal **filled 56**, secundarias **outlined** y **text**.

| Error | Tipo de aviso | Título | Mensaje | Acción principal (filled) | Secundarias |
|---|---|---|---|---|---|
| Foto no procesable (422) | `error` | "No pudimos leer la foto" | "Acércate un poco, que haya buena luz y evita reflejos en los empaques." | [camera] **Tomar otra foto** | Elegir de galería (outlined) · Cobrar buscando producto (text) |
| Sin productos detectados | `error` | "No encontramos productos en la foto" | "Revisa que los productos estén dentro del cuadro y separados entre sí." | **Tomar otra foto** | Agregar productos a mano (outlined) |
| Sin conexión | `sinConexion` | "Sin internet no podemos revisar la foto" | "Puedes cobrar buscando los productos. La venta se guarda y se enviará al reconectarte." | [magnify] **Cobrar buscando producto** | Reintentar cuando haya señal (outlined) |
| Tiempo agotado / 5xx | `tiempo` | "Esto tardó demasiado" | "El servicio está lento ahora. Tu foto sigue aquí." | [refresh] **Reintentar con la misma foto** | Tomar otra foto (outlined) · Cobrar buscando producto (text) |

---

### 2.4 **Revisa la venta** (`revision/cobro.tsx`) — pantalla central

Estado local editable (sin cambios):

```ts
type ItemEditable = {
  clave: string; sku: string | null; nombre: string;
  cantidad: number;              // ≥ 1 en la UI (si viene 0 → 1 y nivel 'baja')
  precio_unitario: number | null; confianza: number;
  origen: 'foto' | 'manual'; revisadoPorUsuario: boolean;
  stockDisponible?: number; libre?: boolean;
};
```
Reglas de nivel (`nivelDeItem`, sin cambios): `sku == null && !libre` o `precio_unitario == null` → **falta** · `revisadoPorUsuario || origen==='manual'` → **manual** · `confianza < 0.6` → **baja** · si no → **alta**.

```
┌──────────────────────────────────────────────┐
│ [← Atrás]  Revisa la venta   [cash-register  │ Top app bar small; acción final Boton text
│                                Caja]         │ (surface → surfaceContainer al desplazar)
├──────────────────────────────────────────────┤
│ Paso 2 de 3 · Revisar                        │ BarraPasos 2/3
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ░░░░░░░░░░░ •          │
├──────────────────────────────────────────────┤
│ Encontramos 3 productos.                     │ bodyLargePlus 18
│ [image  Ver foto]                            │ Boton text (toggle de miniatura)
│                                              │
│ ╭ (!) 1 producto necesita tu ayuda ────────╮ │ Aviso tarjeta error compacto (solo si hay 'falta')
│ ╰──────────────────────────────────────────╯ │
│                                              │
│ Necesitan tu ayuda (2)          (titleMedium)│ sección solo si hay falta/baja
│ ╭─ Card outlined, 2 dp error, shape medium ─╮│ FilaProducto 'falta'
│ │ (1) Galletas (sin identificar)     — —    ││
│ │ Sin precio · [! Elige producto]           ││ chip errorContainer
│ │ [(−) 1 pz (+)]   [ Elegir producto ]      ││ Boton filled 48
│ ╰───────────────────────────────────────────╯│
│ ╭─ Card filled surfaceContainerHighest ─────╮│ FilaProducto 'baja'
│ ┃ (3) Jabón de barra 150 g          $22.00  ││ ← borde izquierdo 4 dp tertiary
│ ┃ $22.00 c/u · [? Revisa]                   ││ chip tertiaryContainer
│ ┃ [(−) 1 pz (+)]  [Está bien] [Editar]      ││ tonal · text
│ ╰───────────────────────────────────────────╯│
│                                              │
│ Listos (2)                      (titleMedium)│
│ (2) Refresco de cola 600 ml        $36.00    │ List item 3 líneas sobre surface
│     $18.00 c/u · [✓ Detectado]               │ chip outlined
│     [(−) 2 pz (+)]                 [Editar]  │
│ ─────────────────────────────── outlineVar.  │
│ (4) Pan blanco grande              $52.00    │
│     $52.00 c/u · [✓ Detectado]               │
│     [(−) 1 pz (+)]                 [Editar]  │
│                                              │
│ [+ Agregar otro producto]  (outlined 48)     │
│ [cash-register ¿Dudas? Pregúntale a Caja]    │ Boton text
│ [Empezar de nuevo]  (Boton text color error) │ abre Dialog
│  (padding inferior = alto de la barra fija)  │
├──────────────────────────────────────────────┤
│        ╭ Quitaste "Galletas".  [DESHACER] ╮  │ ← SNACKBAR (inverseSurface, level3), 8 dp sobre la barra,
│        ╰──────────────────────────────────╯  │   solo tras quitar; nunca tapa el botón
├──────────────────────────────────────────────┤ BARRA DE TOTAL: surfaceContainer (nivel 2 tonal), divisor sup. 1 dp outlineVariant
│ Total (3 productos)            $88.00        │ titleMedium · headlineLarge 32/500 tabular
│ [!] + 1 producto sin precio                  │ ← labelLarge error con alert-circle (5.55:1), solo si aplica
│ [==[alert-circle] Corrige 1 producto para cobrar==] │ ← Boton TONAL 56 cuando hay 'falta'
│        ó                                     │
│ [============ Cobrar $88.00 ============]    │ ← Boton FILLED 56 cuando todo está listo
└──────────────────────────────────────────────┘
```

**Reglas de interacción** (sin cambios de comportamiento)

1. **Orden:** "Necesitan tu ayuda" (falta → baja), luego "Listos" en el orden del servidor. Al corregir, la fila **no salta de sección** hasta salir del editor; entonces se mueve y se anuncia "Galletas María 170 g pasó a Listos".
2. **Total en vivo:** `Σ cantidad × precio_unitario` de filas con precio; con filas sin precio aparece "+ N producto sin precio". Live region con *debounce* 600 ms.
3. **Botón principal nunca "muerto":** con filas `falta` el botón es **tonal** "Corrige N producto(s) para cobrar" (icono `alert-circle`); al tocarlo hace scroll a la primera fila con problema y le pone el foco del lector. Filas `baja` **no bloquean**.
4. **Cantidad:** `StepperCantidad` mín. 1, máx. `stockDisponible` ("Solo hay 3 en existencia"). Tocar el número permite escribirlo.
5. **Quitar con deshacer:** el `−` en 1 se vuelve "Quitar" (icon button outlined error). La fila desaparece **sin diálogo**; aparece el **Snackbar** "Quitaste {nombre}." [Deshacer] por **10 s** (sin límite con lector activo; se va al hacer otro cambio). Deshacer la regresa a su posición original.
6. **Si se quitan todos:** estado vacío; el botón principal pasa a "Agregar producto".
7. **Atrás / Cerrar con cambios:** **Dialog** M3 (`surfaceContainerHigh`, shape 28, level3, scrim 32 %): icono `cart-outline`, "¿Salir sin cobrar?", "Guardamos esta venta como borrador para que la termines después." · acciones apiladas: [Seguir revisando] (filled) · [Salir y guardar borrador] (outlined) · [Descartar venta] (text, `error`). El borrador aparece en la pestaña Cobrar.
8. **Empezar de nuevo:** **Dialog** "¿Borrar los 3 productos?" · [No, regresar] (tonal) · [Sí, borrar] (filledError) — una sola acción llena. Sin `onCerrar` por scrim (obliga a elegir).
9. **Ver foto:** miniatura colapsable (alto máx 200, shape large). Si vienen `caja`s: rectángulos 2 dp `primary` (alta), `tertiary` (revisa), `error` (falta), cada uno **con número** en caja `inverseSurface` + `inverseOnSurface` 16/500 que coincide con el leading de la fila; nunca solo color.

**Bottom sheet "Editar producto"** (`HojaInferior` modal: `surfaceContainerLow`, esquinas 28, level1, drag handle + "Cerrar" visible, scrim 32 %):

```
                  ▬▬▬▬
Editar producto                     [✕ Cerrar]   titleLarge 22 · Boton text
Producto *                                       Campo (etiqueta fija arriba)
╭────────────────────────────────── [magnify] ╮  text field outlined 56, sugerencias del catálogo
│ galletas                                     │
╰──────────────────────────────────────────────╯
 (○) Galletas María 170 g      $16.00            list items 2 líneas con radio M3 (48 táctil):
     12 en existencia                            supporting onSurfaceVariant
 (○) Galletas de chocolate 90 g $14.00
     3 en existencia
 [No está en mi lista: cobrar como producto suelto]   Boton text
Precio por pieza *
╭ $ │ 16.00                                    ╮  Campo moneda
╰──────────────────────────────────────────────╯
 (!) Escribe el precio. Ej. 18.50                 supporting error (6.15… 5.85:1 sobre surfaceContainerLow)
Cantidad   [(−) 1 pz (+)]
[ Quitar de la venta ] (outlinedError)
────────────────────────────── (pie fijo)
[========= Guardar cambios =========] (filled 56; deshabilitado EXC-4 con motivo visible si falta dato)
```
- Opción del catálogo elegida: list item con contenedor `secondaryContainer`, radio relleno `primary` y texto "Elegido" (no solo color).
- Si el ítem trae `sku` pero no precio → foco en "Precio". Si `sku: null` → foco en "Producto" con el texto detectado ya escrito.
- Elegir del catálogo llena `sku`, `nombre`, `precio_unitario`, `stockDisponible`.

**Agregar producto manual:** misma hoja, título "Agregar producto", buscador vacío y autoenfocado; arriba, "Más vendidos" como **assist chips** tocables (alto 48 por `EXC-2`, shape small, borde `outline`) con nombre + precio. Nuevo ítem: `origen: 'manual'`, chip "Tú lo pusiste".

**Pregúntale a Caja** (acción de la top app bar + botón text en la lista): abre el asistente como **bottom sheet modal al 90 %** (no cambia de pestaña, no pierde la revisión), rol `caja` y contexto `{ pantalla: 'revision_cobro', items: ItemEditable[] }`. Sugerencias rápidas como **suggestion chips** de 48: "¿Cuánto cuesta este producto?", "¿Qué producto es el que no reconoció?", "¿Me alcanza el stock?". Estado "Caja está escribiendo…" con tres puntos estáticos + texto (sin animación con movimiento reducido). Si Caja propone un cambio, llega como `TarjetaAccion` (card elevated) "Cambiar Galletas por Galletas María 170 g · $16.00" [Aplicar a la venta] (filled); al aplicarlo la hoja se cierra, la fila se actualiza y sale un snackbar "Caja cambió Galletas por Galletas María 170 g. [Deshacer]". Si `no_resuelto`: `Aviso info` "Caja no supo responder. Puedes buscar el producto a mano." [Buscar producto].

**Estados de la revisión**

| Estado | Qué se ve |
|---|---|
| Normal (con problemas) | Como el wireframe |
| Todo listo | Sin sección "Necesitan tu ayuda"; arriba `Aviso` tarjeta `exito` (`successContainer`/`onSuccessContainer` 7.22:1) "Todo listo. Revisa las cantidades y cobra." Botón filled "Cobrar $88.00". |
| Vacío | Estado vacío M3: icono `cart-outline` 48 `onSurfaceVariant`, `headlineSmall` "No hay productos en esta venta", [camera Tomar otra foto] (outlined) · en la barra: [+ Agregar producto] (filled 56). Total "$0.00". |
| Sin conexión | Banner `sinConexion` bajo la top app bar. Todo editable. Buscador con catálogo local; si no hay, `Aviso info` "Sin internet solo puedes buscar productos que ya cargaste antes." "Pregúntale a Caja" **deshabilitado** (`EXC-4`) con texto visible "Necesita internet". El cobro se puede hacer (va a cola). |
| Cargando catálogo en buscador | Circular progress 24 + "Buscando…" bajo el campo. |
| Error del buscador | `Aviso` tarjeta `error` en la hoja: "No pudimos buscar." [Reintentar]. |

---

### 2.5 **Bottom sheet de cobro** (al tocar "Cobrar $88.00")

```
                  ▬▬▬▬
Cobrar $88.00                       [✕ Cerrar]   titleLarge 22 (monto también en headlineSmall si cabe)
¿Cómo te pagan?                                  titleSmall 16/500
╭──────────────────────────────────────────╮     list items con radio M3, alto 56, shape medium,
│ (●) [cash] Efectivo              Elegido  │ ←   elegido: contenedor secondaryContainer + radio primary + "Elegido"
╰──────────────────────────────────────────╯
╭──────────────────────────────────────────╮
│ ( ) [cellphone] Pago digital [SIMULACIÓN]│ ←   EtiquetaSimulacion chip; lleva al flujo pago/ (Fase 5)
╰──────────────────────────────────────────╯
Te dan (opcional)
╭ $ │ 100.00                               ╮     Campo moneda
╰──────────────────────────────────────────╯
[$100] [$200] [$500] [Exacto]                    filter chips 48 (seleccionado: secondaryContainer + check)
Cambio: $12.00                                   amount 20/500; si < total: supporting error "Faltan $X" + icono
──────────────────────────────── (pie fijo)
[====== Registrar venta $88.00 ======] (filled 56; cargando: "Guardando venta…")
```
- Al tocar "Registrar venta": `cargando`, no se puede tocar otra vez; `POST /ventas` con `id_local` (uuid) → un reintento nunca duplica la venta.

**Resultados del registro** (sin cambios)

| Respuesta | Qué pasa |
|---|---|
| 200/201 | → `venta/[id]` (comprobante) |
| Sin conexión | Cola local → comprobante variante **"Guardada en tu teléfono"** |
| 409 stock insuficiente | Se cierra la hoja; la fila pasa a "falta" con "Solo hay 1 en existencia. Ajusta la cantidad." y `Aviso error` arriba. |
| 400 datos faltantes | `Aviso` tarjeta `error` en la hoja: "Falta un dato de un producto. Revísalo." [Ir al producto] |
| 5xx / timeout | `Aviso` tarjeta `error` en la hoja: "No se pudo registrar la venta. Tu venta sigue aquí, no se cobró dos veces." [Reintentar] (filled) · [Guardar y enviar después] (text) |

---

### 2.6 **Venta registrada** (`venta/[id].tsx`) — comprobante

```
┌──────────────────────────────────────────────┐
│ [✕ Cerrar]   Venta registrada                │ Top app bar small (Cerrar → pestaña Cobrar)
├──────────────────────────────────────────────┤
│ Paso 3 de 3 · Listo                          │ BarraPasos 3/3 (completo)
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓      │
│ ╭─ Card filled successContainer ──────────╮  │ shape medium, level0
│ │ [check-circle 48 onSuccessContainer]     │  │
│ │ ¡Venta registrada!                       │  │ headlineSmall 24 onSuccessContainer (7.22:1)
│ │ Folio V-0042 · 19 nov 2026, 13:42        │  │ bodyLarge onSuccessContainer
│ │ Efectivo · Te dieron $100.00 · Cambio $12.00 │
│ ╰──────────────────────────────────────────╯  │
│                                              │
│  2 × Refresco de cola 600 ml        $36.00   │ FilaProducto soloLectura (list item 1 línea, 56)
│  1 × Pan blanco grande              $52.00   │
│  ─────────────────────────────── outlineVar. │
│  Total                              $88.00   │ headlineLarge
│                                              │
│ ╭─ Card outlined · Inventario actualizado ─╮ │ shape medium, borde outlineVariant
│ │ [package-variant] Quedan:                │ │ titleSmall
│ │ Refresco de cola 600 ml   10 pz          │ │ list items densos
│ │ Pan blanco grande          2 pz [! Poco] │ │ ← chip errorContainer "Poco" con icono
│ ╰──────────────────────────────────────────╯ │
│                                              │
│ ╭─ Card filled surfaceContainerHighest ────╮ │ ← "Antes vs. ahora" (demo)
│ │ [timer-outline] Esta venta: 42 segundos  │ │ titleMedium
│ │ A mano (libreta y calculadora): ~3 min   │ │ bodyLarge onSurfaceVariant + "estimado"
│ │ Sin sumar a mano · Inventario al día     │ │
│ ╰──────────────────────────────────────────╯ │
├──────────────────────────────────────────────┤ barra inferior surfaceContainer
│ [===== camera Nueva venta con foto =====](56)│ filled
│ [ Ver ventas de hoy ] (outlined) [ Ir a Inicio ] (text) │
└──────────────────────────────────────────────┘
```

**Variantes** (sin cambios de contenido)
| Variante | Diferencias de presentación |
|---|---|
| Guardada sin conexión | Card de cabecera en `surfaceContainerHigh` (no verde), icono `cloud-upload` 48 `onSurfaceVariant`, título "Venta guardada en tu teléfono", texto "Se enviará sola cuando vuelva el internet. El inventario se actualizará en ese momento." Card de inventario → "Inventario: pendiente". Folio local "Pendiente-3". |
| Pago digital simulado | `EtiquetaSimulacion` franja (banner `inverseSurface`) bajo la top app bar: "Simulación: este cobro no movió dinero real". |
| Abierta desde Historial | Sin `BarraPasos`; sin "Antes vs. ahora"; barra inferior solo [Volver] (filled). |
| Cargando | Circular progress 48 + "Cargando venta…". |
| No encontrada / error | `Aviso` tarjeta `error` "No encontramos esta venta." [Volver a ventas de hoy]. |

Lector al entrar: "Venta registrada. Total 88 pesos. Folio V-0042."

**Visible después:** arriba en "Ventas de hoy" (pestaña Cobrar, con snackbar de confirmación), en `historial.tsx` y en "Ventas del día" de Inicio (invalidar `['ventas','hoy']`, `['kpis']`, `['inventario']`).

---

## 3. Especificaciones UI (tokens M3 usados)

| Elemento | Roles / valores | Contraste |
|---|---|---|
| Fondo de pantallas | `surface #F9F9FF` | — |
| Top app bar | `surface` → `surfaceContainer #EDEDF4` al desplazar; título `titleLarge` `onSurface` | 16.3 / 14.7:1 |
| Extended FAB "Cobrar con foto" | `primary #415F91` / `onPrimary #FFFFFF`, 56, shape 16, level3 | 6.46:1 |
| Navigation bar | `surfaceContainer`; píldora `secondaryContainer #DAE2F9`; icono activo `onSecondaryContainer #3E4759`; etiqueta activa `onSurface` 16/700; inactiva `onSurfaceVariant #44474E` | 7.24 / 14.7 / 8.03:1 |
| Barra de total (revisión) | `surfaceContainer`, divisor sup. 1 dp `outlineVariant`; total `headlineLarge` 32/500 `onSurface` | 14.7:1 |
| Botón "Cobrar $X" | filled `primary` / `onPrimary`, 56, shape full | 6.46:1 |
| Botón "Corrige N…" | tonal `secondaryContainer` / `onSecondaryContainer`, 56 | 7.24:1 |
| "+ N producto sin precio" | `error #BA1A1A` 16/500 + `alert-circle` sobre `surfaceContainer` | 5.55:1 |
| Fila "falta" | card outlined 2 dp `error`, chip `errorContainer #FFDAD6` / `onErrorContainer #93000A` | 6.15 (borde/texto) / 7.24:1 |
| Fila "revisa" | card filled `surfaceContainerHighest #E2E2E9` + borde izq. 4 dp `tertiary #705575`; chip `tertiaryContainer #FAD8FD` / `onTertiaryContainer #573E5C`; textos `onSurface` / `onSurfaceVariant` | 13.3 / 7.24 / 7.24:1; borde 5.00:1 |
| Fila "listo" | list item sobre `surface`; chip outlined, icono `success #006D43` | 6.13:1 icono; 8.89:1 texto |
| Stepper | icon buttons tonales 48 `secondaryContainer` / `onSecondaryContainer` | 7.24:1 |
| Snackbar "Deshacer" | `inverseSurface #2E3036` / `inverseOnSurface #F0F0F7`; acción `inversePrimary #AAC7FF`; shape 4; level3 | 11.59 / 7.72:1 |
| Bottom sheets | `surfaceContainerLow #F3F3FA`, esquinas 28, level1, scrim negro 32 % | textos ≥ 5.85:1 |
| Dialog | `surfaceContainerHigh #E7E8EE`, shape 28, level3, scrim 32 % | 14.0 / 7.63:1 |
| Cámara: barras | `inverseSurface` / `inverseOnSurface` | 11.59:1 |
| Cámara: guía de encuadre | doble trazo 2 dp `#FFFFFF` + 2 dp `#2E3036` | ≥ 3:1 contra cualquier imagen (uno de los dos contrasta) |
| Cámara: disparador | 72, relleno `#FFFFFF`, borde 4 dp `inverseSurface`; etiqueta `inverseOnSurface` | 11.59:1 |
| Cámara: Galería / Luz | icon buttons tonales 56 | 7.24:1 |
| Cajas sobre foto | 2 dp `primary` / `tertiary` / `error` + número `inverseSurface`/`inverseOnSurface` 16/500 | 11.59:1 el número |
| Comprobante éxito | card filled `successContainer #92F7BC` / `onSuccessContainer #005231` | 7.22:1 |
| Opción de pago elegida | `secondaryContainer` + radio `primary` + "Elegido" | 7.24:1 |
| Espaciado | margen lateral 16; entre secciones 24; dentro de filas 8/12; barras inferiores padding 16 | — |
| Forma | botones/stepper full; cards/filas con estado 12; chips 8; snackbar/campos 4; FAB/miniaturas 16; hojas/diálogos 28; barras 0 | — |
| Tipografía | total 32/500; título de barra 22; secciones y producto 18/500; precio c/u 16; subtotal 20/500; botones 16/500 | — |

Prohibido en el recorrido: `textShadow*`, gradientes, blur; sombras fuera de los niveles de §5 de `00-sistema.md`; texto sobre la imagen de la cámara sin caja opaca.

---

## 4. Justificación HCI / Nielsen

| # | Aplicación concreta |
|---|---|
| 1 Visibilidad del estado | Linear progress Foto/Revisar/Listo; circular progress + etapas reales; "tardando" a los 8 s; total en vivo; "Pendiente de enviar"; card "Inventario actualizado"; snackbar "Venta registrada" al volver. |
| 2 Mundo real | "Cobrar", "Te dan", "Cambio", "pz", "c/u", "producto suelto", "Caja"; nunca "SKU", "confianza", "detección", "IA". |
| 3 Control y libertad | Snackbar **Deshacer** al quitar; "Está bien" para lo dudoso; Atrás guarda borrador (Dialog); "Empezar de nuevo" con Dialog; Cancelar el análisis; "Cerrar" visible en hojas además del arrastre. |
| 4 Consistencia | Patrones M3 nativos de Android: Extended FAB para la acción principal, navigation bar, bottom sheets iguales para editar/agregar/cobrar/Caja, snackbar para deshacer, dialog para destructivo. Un solo filled/FAB por vista. |
| 5 Prevención de errores | No se cobra con productos sin precio; tope por existencia; `id_local` evita duplicados; botón bloqueado mientras guarda; "Faltan $X"; Dialog antes de borrar todo. |
| 6 Reconocer > recordar | Sugerencias con precio y existencia; "Más vendidos" como chips; "Repetir última venta"; números foto ↔ fila. |
| 7 Flexibilidad | Chips $100/$200/$500/Exacto; escribir cantidad; cobrar sin foto; arrastrar para cerrar hojas. |
| 8 Minimalista | La elevación solo marca lo que flota (FAB, hojas, snackbar, diálogos); colores con función (azul acción, malva revisa, rojo falta, verde listo). |
| 9 Recuperación de errores | Cada error del análisis y del registro en `Aviso` tarjeta con acción filled de recuperación. |
| 10 Ayuda | Card guía en la pestaña Cobrar; "Ayuda" en la cámara; "Pregúntale a Caja" sin salir de la revisión. |

**Accesibilidad:** todos los pares de texto ≥ 4.5:1 (mín. 5.00:1) y bordes/indicadores ≥ 3:1 (§3 y `00-sistema.md` §2.3) · táctiles ≥ 48 (disparador 72, FAB/principal/icon buttons de cámara 56) con ≥ 8 de separación · disparador, galería, FAB, total y botón de cobro en el tercio inferior · estados con icono + texto ("Revisa", "Falta precio", "Elegido", "Pendiente de enviar", "Poco") y además forma (borde izquierdo malva, borde rojo 2 dp) · snackbar sin límite de tiempo con lector activo (WCAG 2.2.1) y nunca sobre el botón principal · lector: anuncios en cambios de etapa, al quitar, al registrar; foco al primer problema con "Corrige N productos" · letra al 200 %: list items crecen, botones de fila y de diálogo se apilan, el FAB no se colapsa y el contenido reserva su alto · movimiento M3 con `useReducedMotion` (circular progress → icono estático, scroll sin animación, hojas/snackbar sin deslizamiento).

---

## 5. Notas para el contrato con back (`src/api/esquemas.ts`)

Sin cambios respecto a la versión anterior:

```ts
// GET /productos?q=texto&limite=10   y   GET /productos/mas-vendidos?limite=6
export const Producto = z.object({
  sku: z.string(), nombre: z.string(),
  precio_unitario: z.number().nonnegative(),
  existencia: z.number().int(),
});

// POST /ventas
export const SolicitudVenta = z.object({
  id_local: z.string(),
  imagen_id: z.string().nullable(),
  metodo_pago: z.enum(['efectivo', 'digital_simulado']),
  recibido: z.number().nullable(),
  items: z.array(z.object({
    sku: z.string().nullable(), nombre: z.string(),
    cantidad: z.number().int().positive(), precio_unitario: z.number().nonnegative(),
    libre: z.boolean().optional(), corregido: z.boolean(),
  })),
  duracion_seg: z.number().optional(),
});

export const RespuestaVenta = z.object({
  venta_id: z.string(), folio: z.string(), total: z.number(), creada_en: z.string(),
  existencias: z.array(z.object({ sku: z.string(), nombre: z.string(), quedan: z.number().int(), bajo: z.boolean() })),
});
// 409 → { sku, existencia } para marcar la fila
```

Mocks (`mocks/index.ts`): caso "falta" (galletas sin sku/precio, 0.41), ítem con precio y confianza 0.52 (fila "Revisa"), `mockPosCheckoutVacio` y modo que responda 422 / timeout. Referencia manual `SEGUNDOS_VENTA_MANUAL = 180` en `constants.ts`, etiquetada "estimado".

---

## 6. Impacto en código de pantallas (migración)

| Archivo | Cambio |
|---|---|
| `src/screens/cobrar.tsx` | La tarjeta "Cobrar con foto" con botón se reemplaza por card filled de guía + `FabExtendido`; `paddingBottom` para librar el FAB; snackbar al volver de una venta. |
| `src/screens/revision-cobro.tsx` | La franja de deshacer de la barra inferior pasa a `Snackbar` (`separacionInferior` = alto de la barra); "Corrige N…" usa `variante="tonal"`; confirmaciones "¿Salir sin cobrar?" y "Empezar de nuevo" pasan de `HojaInferior` a `Dialogo`. Lógica de estado intacta. |
| `src/screens/revision/hoja-editar-producto.tsx`, `hoja-cobro.tsx` | Sin cambios de lógica; opciones de catálogo/pago como list items con radio; atajos de efectivo como filter chips. |
| `src/screens/camara.tsx` | Colores `oscuro` → `inverseSurface`; Galería/Luz como icon buttons tonales 56; circular progress en "Analizando". |
| `src/screens/comprobante.tsx` | Cabecera en card filled `successContainer`; inventario y "Antes vs. ahora" en cards. |
| `src/app/(tabs)/_layout.tsx` | `tabBar` personalizado `BarraNavegacion` (píldora, icono relleno, etiqueta 16). |
