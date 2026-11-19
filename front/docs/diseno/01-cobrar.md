# 01 · Recorrido principal: Cobrar con foto

> Depende de: `00-sistema.md` (tokens y componentes). Endpoint de visión: `POST /vision/pos-checkout` → `RespuestaPosCheckout`.
> Usuario: **tendero** cobrando en el mostrador, con el cliente esperando enfrente. Prioridad: rapidez + cero cobros equivocados.
> Rutas: `(tabs)/cobrar.tsx` → `camara.tsx?modo=cobro` → (`analizando` dentro de `camara` o `revision`) → `revision/cobro.tsx` → `venta/[id].tsx`.

---

## 1. Concepto y enfoque

**Recorrido:** `Cobrar` → `Cámara` → `Analizando foto…` → `Revisa la venta` → `Cobrar $X` (hoja de pago) → `Venta registrada` (comprobante, stock descontado) → visible en Inicio / Historial.

**Enfoque por pantalla (variabilidad justificada):**

| Pantalla | Enfoque | Por qué |
|---|---|---|
| Pestaña Cobrar | **Tarjetas con borde** (pocas, grandes) | Punto de arranque: 1 acción dominante ("Cobrar con foto") y 2 atajos. Reconocer, no recordar. |
| Cámara | **Guiado** (instrucción + guía de encuadre) | Momento de mayor incertidumbre para quien no usa cámara para "trabajar". |
| Revisión del carrito | **Lista densa** con `+`/`−` | El tendero necesita ver *todo* el ticket en una pantalla y corregir en 1–2 toques mientras el cliente espera. Las tarjetas grandes obligarían a desplazarse y ocultarían el total. Los problemas se agrupan arriba para que no se pierdan. |
| Comprobante | **Guiado/resumen** | Cierre claro: qué se cobró, qué se descontó, qué sigue. |

**BarraPasos del recorrido** (3 pasos, visible en Revisión y Comprobante): `Foto` · `Revisar` · `Listo`.

**Medición para la demo (proceso actual vs. digital):** se guarda `inicio = Date.now()` al abrir la cámara y `fin` al registrar la venta. El comprobante muestra el tiempo real contra una referencia fija de proceso manual (ver §2.6).

---

## 2. Arquitectura de pantallas

### 2.1 Pestaña **Cobrar** (`(tabs)/cobrar.tsx`)

```
┌──────────────────────────────────────────────┐
│ Cobrar                                       │ header de Tabs (título 20 Bold)
├──────────────────────────────────────────────┤
│ [AvisoConexion franja — solo sin internet]   │
│                                              │
│ ┌─ Venta sin terminar ─(borde 2px texto)───┐ │ ← solo si hay borrador
│ │ (i) Tienes una venta de $88.00 sin cobrar │ │
│ │ [Continuar venta]   [Descartar]           │ │
│ └───────────────────────────────────────────┘ │
│                                              │
│ ┌─(borde 2px acento, radio 8, alto ≥ 160)──┐ │
│ │        [camera 48 acento]                 │ │
│ │        Cobrar con foto                    │ │ titulo 24 Bold
│ │  Pon los productos en el mostrador y      │ │ cuerpo 16 secundario
│ │  tómales una foto                         │ │
│ │  [====  Abrir cámara  ====] (primario 56) │ │
│ └───────────────────────────────────────────┘ │
│                                              │
│ Otras formas de cobrar          (subtitulo)  │
│ ┌──────────────────┐ ┌──────────────────┐    │ 2 tarjetas borde 1px, alto ≥ 96
│ │ [magnify]        │ │ [replay]         │    │ (se apilan con letra grande)
│ │ Buscar producto  │ │ Repetir última   │    │
│ │ (sin foto)       │ │ venta · $45.00   │    │
│ └──────────────────┘ └──────────────────┘    │
│                                              │
│ Ventas de hoy                 [Ver todas →]  │ subtitulo + Boton texto
│ ─────────────────────────────────────────────│
│ 13:42  3 productos · Efectivo     $88.00     │ filas 56, tocables → venta/[id]
│ 13:10  1 producto · Pendiente ⟳   $18.00     │ ← en cola: icono cloud-upload + "Pendiente de enviar"
│ ...máx 5                                     │
├──────────────────────────────────────────────┤
│ Inicio │ [Cobrar] │ Inventario │ Asistente   │
└──────────────────────────────────────────────┘
```

**Estados**
| Estado | Qué se ve |
|---|---|
| Vacío (sin ventas hoy) | En lugar de la lista: `Aviso info` "Todavía no hay ventas hoy. Tu primera venta aparecerá aquí." Sin botón extra (el principal ya está arriba). "Repetir última venta" se oculta si nunca hubo venta. |
| Cargando ventas | 3 filas "esqueleto" planas: rectángulos `superficie` sin animación + texto oculto "Cargando ventas de hoy" (`accessibilityLiveRegion`). |
| Error al cargar ventas | `Aviso error` "No pudimos traer tus ventas de hoy." [Reintentar]. El botón "Cobrar con foto" **sigue funcionando**. |
| Sin conexión | Franja `sinConexion` arriba. "Cobrar con foto" muestra debajo en 16 secundario: "Sin internet la foto no se puede revisar. Puedes cobrar buscando el producto." y la tarjeta "Buscar producto" sube de posición (queda primera). |
| Ventas en cola | Filas con `cloud-upload` + "Pendiente de enviar" (texto, no solo icono). |

---

### 2.2 **Cámara** — modo cobro (`camara.tsx?modo=cobro`)

Pantalla completa, fondo `oscuro`. Sin `Encabezado` estándar.

```
┌──────────────────────────────────────────────┐
│ [✕ Cerrar]     Cobrar con foto     [? Ayuda] │ barra oscuro #111, alto 56, texto blanco
├──────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────┐ │
│ │      (vista previa de la cámara)         │ │
│ │  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓    │ │ guía: rectángulo 2px blanco + 2px #111 por fuera
│ │  ┃                                  ┃    │ │ (se ve sobre fondos claros y oscuros)
│ │  ┃   Que se vean todos los          ┃    │ │
│ │  ┃   productos dentro del cuadro    ┃    │ │ texto 18 Bold blanco sobre caja #111 (no sobre la imagen)
│ │  ┃                                  ┃    │ │
│ │  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛    │ │
│ └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ Consejo: separa los productos y evita        │ franja #111, texto 16 blanco; rota entre 3 consejos
│ reflejos de la luz                           │ solo al abrir (no cambia sola mientras lee)
├──────────────────────────────────────────────┤
│ [image-multiple]   (  ◉  TOMAR  )   [flash]  │ barra oscuro, alto ≥ 120
│  Galería            Tomar foto       Luz: No │ disparador 72×72 círculo blanco borde 4px #111 + texto debajo
└──────────────────────────────────────────────┘
```

- **Disparador**: 72×72, centrado en el tercio inferior (pulgar). Al tocar: se bloquea (evita dobles fotos), el borde pasa a `acento` y aparece texto "Tomando foto…".
- **Galería**: `expo-image-picker`, una sola imagen, sin recorte obligatorio.
- **Luz (flash/linterna)**: alterna "Luz: No" / "Luz: Sí" (texto cambia, no solo el icono).
- **Ayuda**: hoja inferior plana con 3 ejemplos de texto ("Bien: productos separados, de frente. Mal: amontonados, con reflejo").
- Tras la foto: compresión con `expo-image-manipulator` (lado largo 1280 px, JPEG 0.7) y paso directo a **Analizando** (sin pantalla "¿usar esta foto?": ahorra 1 toque; si sale mal, el error ofrece tomar otra).

**Estados de permiso**

| Estado | Pantalla (fondo `fondo`, no oscuro) |
|---|---|
| Sin decidir | Antes del diálogo del sistema: icono `camera` 48, título "Necesitamos tu cámara", texto "La usamos solo para ver los productos que vas a cobrar. No guardamos fotos de personas." [Permitir cámara] (primario) · [Usar una foto de la galería] (secundario) |
| Denegado (se puede volver a pedir) | Mismo layout, título "La cámara está apagada para esta app" · [Volver a intentar] · [Usar foto de la galería] |
| Denegado permanente | Título igual; texto "Actívala en Ajustes > Permisos > Cámara." · [Abrir ajustes] (`Linking.openSettings()`) · [Usar foto de la galería] · [Cobrar buscando producto] (texto) |
| Galería denegada | `Aviso error` en la hoja: "No tenemos permiso para ver tus fotos." [Abrir ajustes] |
| Cámara no disponible / error al abrir | `Aviso error` "No se pudo abrir la cámara." [Reintentar] · [Usar foto de la galería] |

---

### 2.3 **Analizando foto…** (estado de `camara.tsx`, misma ruta; no se navega todavía)

```
┌──────────────────────────────────────────────┐
│ [✕ Cancelar]                                 │ barra fondo blanco, borde inf. 1px divisor
├──────────────────────────────────────────────┤
│ BarraPasos: Paso 1 de 3 · Foto               │
│                                              │
│ ┌──────────────────────────────┐             │ miniatura de la foto, borde 1px borde,
│ │        (foto tomada)         │             │ alto máx 40% pantalla
│ └──────────────────────────────┘             │
│                                              │
│   [ActivityIndicator 48 acento]              │
│   Buscando los productos…                    │ subtitulo 20 Bold
│   ✓ Foto lista                               │ lista de etapas con icono + texto
│   ⟳ Enviando foto                            │ (check exito / spinner / circle-outline)
│   ○ Reconociendo productos                   │
│                                              │
│   (tras 8 s) (i) Está tardando más de lo     │ Aviso info inline
│   normal. Puedes seguir esperando.           │
├──────────────────────────────────────────────┤
│ [ Tomar otra foto ] (secundario 48)          │
└──────────────────────────────────────────────┘
```

- Etapas reales: `preparando` (compresión) → `enviando` (fetch en curso) → `reconociendo` (tras 1.5 s de envío sin respuesta, solo texto; no fingimos progreso numérico).
- Tiempo límite: **20 s** (`AbortController` en `cliente.ts`). A los 8 s aparece el aviso de "tardando".
- `Cancelar` aborta la petición y regresa a la cámara.
- Accesibilidad: cada cambio de etapa se anuncia (`announceForAccessibility`), y la pantalla tiene `accessibilityState={{ busy: true }}`.

**Resultados posibles del análisis**

| Respuesta | Destino / pantalla |
|---|---|
| 200, `items.length > 0`, zod OK | → `revision/cobro` |
| 200, `items.length === 0` | Error **Sin productos detectados** (abajo) |
| 422 o zod falla | Error **Foto no procesable** |
| Sin conexión antes de enviar | Error **Sin conexión** |
| Timeout 20 s / 503 / 5xx | Error **Tiempo agotado / servicio ocupado** |

**Pantallas de error del análisis** (mismo layout: miniatura arriba, `Aviso` tarjeta, botones abajo en el tercio inferior):

| Error | Título | Mensaje | Acción principal | Secundarias |
|---|---|---|---|---|
| Foto no procesable (422) | "No pudimos leer la foto" | "Acércate un poco, que haya buena luz y evita reflejos en los empaques." | [camera] **Tomar otra foto** | Elegir de galería · Cobrar buscando producto |
| Sin productos detectados | "No encontramos productos en la foto" | "Revisa que los productos estén dentro del cuadro y separados entre sí." | **Tomar otra foto** | Agregar productos a mano (→ revisión vacía con buscador abierto) |
| Sin conexión | "Sin internet no podemos revisar la foto" | "Puedes cobrar buscando los productos. La venta se guarda y se enviará al reconectarte." | [magnify] **Cobrar buscando producto** | Reintentar cuando haya señal |
| Tiempo agotado / 5xx | "Esto tardó demasiado" | "El servicio está lento ahora. Tu foto sigue aquí." | [refresh] **Reintentar con la misma foto** | Tomar otra foto · Cobrar buscando producto |

---

### 2.4 **Revisa la venta** (`revision/cobro.tsx`) — pantalla central

Datos de entrada: `RespuestaPosCheckout`. Se convierten a estado local editable:

```ts
type ItemEditable = {
  clave: string;                 // id local estable (uuid) para listas y deshacer
  sku: string | null;
  nombre: string;
  cantidad: number;              // ≥ 1 en la UI (si viene 0 → se fuerza a 1 y queda nivel 'baja')
  precio_unitario: number | null;
  confianza: number;             // original del servidor
  origen: 'foto' | 'manual';
  revisadoPorUsuario: boolean;   // true tras "Está bien" o editar → nivel 'manual'
  stockDisponible?: number;      // si el catálogo lo conoce
  libre?: boolean;               // "producto suelto" fuera de catálogo (ver §5)
};
```

Reglas de nivel (`nivelDeItem`): `sku == null && !libre` o `precio_unitario == null` → **falta** · `revisadoPorUsuario || origen==='manual'` → **manual** · `confianza < 0.6` → **baja** · si no → **alta**.

```
┌──────────────────────────────────────────────┐
│ [← Atrás]  Revisa la venta    [cash-register │ Encabezado; acción derecha:
│                                 Caja]        │ "Caja" = Pregúntale a Caja
├──────────────────────────────────────────────┤
│ Paso 2 de 3 · Revisar  [■■■■][■■■■][□□□□]    │ BarraPasos
├──────────────────────────────────────────────┤
│ Encontramos 3 productos.                     │ cuerpoGrande 18
│ [image ▸ Ver foto]                           │ Boton texto: despliega miniatura (toggle)
│                                              │
│ ┌ (!) 1 producto necesita tu ayuda ───────┐  │ Aviso error compacto (solo si hay 'falta')
│ └──────────────────────────────────────────┘ │
│                                              │
│ NECESITAN TU AYUDA (1)            (subtitulo)│ sección solo si hay falta/baja
│ ┌─(2px peligro, radio 8)────────────────────┐│
│ │ Galletas (sin identificar)        — —     ││ FilaProducto estado "falta"
│ │ Sin precio · [! Elige producto]           ││
│ │ [ − ][1 pz][ + ]   [ Elegir producto ]    ││ ← Boton peligro 48
│ └───────────────────────────────────────────┘│
│ ┌─(2px texto, fondo F5)─────────────────────┐│ (ejemplo de fila 'baja' con precio)
│ │ Jabón de barra 150 g             $22.00   ││
│ │ $22.00 c/u · [? Revisa]                   ││
│ │ [ − ][1 pz][ + ]  [Está bien] [Editar]    ││ ← "Está bien" la pasa a 'manual'
│ └───────────────────────────────────────────┘│
│                                              │
│ LISTOS (2)                                   │
│ Refresco de cola 600 ml          $36.00      │ FilaProducto normal
│ $18.00 c/u · [✓ Detectado]                   │
│ [ − ][2 pz][ + ]                 [Editar]    │
│ ─────────────────────────────────────────    │
│ Pan blanco grande                $52.00      │
│ $52.00 c/u · [✓ Detectado]                   │
│ [ − ][1 pz][ + ]                 [Editar]    │
│                                              │
│ [+ Agregar otro producto]  (secundario 48)   │
│ [cash-register ¿Dudas? Pregúntale a Caja]    │ Boton texto
│ [Empezar de nuevo] (Boton texto, peligro)    │ abre confirmación
│  (espacio inferior = alto de barra fija)     │
├──────────────────────────────────────────────┤ BARRA FIJA INFERIOR (borde sup. 2px texto, fondo superficie)
│ [undo] Quitaste "Galletas". [ Deshacer ]     │ ← franja de deshacer (solo tras quitar)
│ Total (3 productos)            $88.00        │ etiqueta 16 · montoGrande 32 tabular
│ + 1 producto sin precio                      │ ← 16 Bold peligro con alert-circle, solo si aplica
│ [==== Corrige 1 producto para cobrar ====]   │ ← Boton secundario 56 (ver regla abajo)
│        ó                                     │
│ [========== Cobrar $88.00 ==========]        │ ← Boton primario 56 cuando todo está listo
└──────────────────────────────────────────────┘
```

**Reglas de interacción**

1. **Orden:** primero "Necesitan tu ayuda" (falta → baja), luego "Listos" en el orden que vino del servidor. Al corregir una fila **no salta de sección** hasta que el usuario sale del editor (evita que la fila "desaparezca" bajo el dedo); entonces se mueve con aviso al lector "Galletas María 170 g pasó a Listos".
2. **Total en vivo:** `Σ cantidad × precio_unitario` de filas con precio. Se actualiza en cada `+`/`−`/edición. Con filas sin precio, el texto "+ N producto sin precio" acompaña al total (el total nunca finge estar completo). `accessibilityLiveRegion="polite"` en el total con *debounce* de 600 ms (no anunciar cada toque).
3. **Botón principal nunca "muerto":** si hay filas `falta`, el botón es **secundario** con texto "Corrige N producto(s) para cobrar" y al tocarlo hace scroll a la primera fila con problema y le pone el foco del lector. Filas `baja` **no bloquean** (solo se marcan): el tendero ve el producto y decide; bloquear todo lo dudoso frenaría el mostrador.
4. **Cantidad:** `StepperCantidad` mín. 1, máx. `stockDisponible` si existe ("Solo hay 3 en existencia"). Tocar el número permite escribirlo.
5. **Quitar con deshacer:** el `−` en 1 se vuelve "Quitar" (o "Quitar de la venta" en el editor). La fila desaparece **sin diálogo**; aparece la franja "Quitaste {nombre}. [Deshacer]" en la barra inferior por **10 s** (sin límite si hay lector de pantalla activo; se va al hacer otro cambio). Deshacer la regresa a su posición original.
6. **Si se quitan todos:** estado vacío (abajo); el botón principal pasa a "Agregar producto".
7. **Atrás / Cerrar con cambios:** diálogo plano (sin velo `rgba` semitransparente: hoja inferior opaca `fondo` con borde superior 2 px `texto`): "¿Salir sin cobrar?" · "Guardamos esta venta como borrador para que la termines después." [Seguir revisando] (primario) · [Salir y guardar borrador] (secundario) · [Descartar venta] (peligro texto). El borrador aparece en la pestaña Cobrar (§2.1).
8. **Empezar de nuevo:** confirmación "¿Borrar los 3 productos?" [No, regresar] (primario) · [Sí, borrar] (peligroLleno). Esta sí lleva diálogo porque borra todo.
9. **Ver foto:** miniatura colapsable (alto máx 200) con la foto original para comparar contra el mostrador. Si `caja` viene en los items, se dibujan rectángulos 2 px (`acento` para alta, `texto` para revisa, `peligro` para falta) **con número** (1, 2, 3) que coincide con un número al inicio de cada fila; nunca solo color.

**Hoja "Editar producto"** (panel inferior, fondo `fondo`, borde superior 2 px `texto`, radio superior 0, sin oscurecer el fondo con transparencias: el resto de la pantalla queda visible pero inerte con `importantForAccessibility="no-hide-descendants"`):

```
┌─(borde sup. 2px texto)───────────────────────┐
│ Editar producto                  [✕ Cerrar]  │ subtitulo
│ Producto *                                   │ Campo con buscador (magnify)
│ [ galletas                       ][magnify]  │ escribe → sugerencias del catálogo
│  ○ Galletas María 170 g     $16.00  (12 en existencia)  │ filas 56, radio grande tocable
│  ○ Galletas de chocolate 90 g $14.00 (3 en existencia)  │
│  [No está en mi lista: cobrar como producto suelto]     │ Boton texto → pide nombre + precio
│ Precio por pieza *                           │ Campo moneda, prefijo $
│ [$ 16.00                         ]           │ se llena al elegir del catálogo; editable
│ (!) Escribe el precio. Ej. 18.50             │ error en línea
│ Cantidad   [ − ][1 pz][ + ]                  │
│ [ Quitar de la venta ] (peligro contorno)    │
│ [======== Guardar cambios ========] (56)     │ primario; deshabilitado con motivo si falta dato
└──────────────────────────────────────────────┘
```
- Si el ítem trae `sku` pero no precio → foco directo en "Precio". Si trae `sku: null` → foco en "Producto" con el texto detectado ya escrito ("Galletas") para buscar sin teclear.
- Elegir del catálogo llena `sku`, `nombre`, `precio_unitario`, `stockDisponible`.

**Agregar producto manual:** misma hoja con título "Agregar producto", buscador vacío y autoenfocado; arriba del buscador, una fila "Más vendidos" con 6 chips 48 alto (reconocer > recordar). Nuevo ítem: `origen: 'manual'`, chip "Tú lo pusiste".

**Pregúntale a Caja** (acción derecha del encabezado + botón texto en la lista): abre el asistente **como hoja inferior a 90 % de alto** (no cambia de pestaña, no pierde la revisión), con rol `caja` preseleccionado y contexto enviado: `{ pantalla: 'revision_cobro', items: ItemEditable[] }`. Sugerencias rápidas (chips 48): "¿Cuánto cuesta este producto?", "¿Qué producto es el que no reconoció?", "¿Me alcanza el stock?". Si Caja propone un cambio, llega como `TarjetaAccion` ("Cambiar Galletas por Galletas María 170 g · $16.00" [Aplicar a la venta]) y al aplicarlo la hoja se cierra y la fila se actualiza (pasar lo entendido al formulario). Si `no_resuelto`: "Caja no supo responder. Puedes buscar el producto a mano." [Buscar producto].

**Estados de la revisión**

| Estado | Qué se ve |
|---|---|
| Normal (con problemas) | Como el wireframe |
| Todo listo | Sin sección "Necesitan tu ayuda"; arriba `Aviso exito` compacto: "Todo listo. Revisa las cantidades y cobra." Botón primario "Cobrar $88.00". |
| Vacío (se quitaron todos / "Agregar a mano" desde error) | Icono `cart-outline` 48, "No hay productos en esta venta", [camera Tomar otra foto] (secundario) · [+ Agregar producto] (primario en la barra inferior). Total "$0.00". |
| Sin conexión (durante la revisión) | Franja `sinConexion` arriba. Todo sigue editable. El buscador usa el catálogo guardado en el teléfono; si no hay, `Aviso info` "Sin internet solo puedes buscar productos que ya cargaste antes." "Pregúntale a Caja" queda **deshabilitado con motivo** "Necesita internet". El cobro se puede hacer (va a cola). |
| Cargando catálogo en buscador | Texto "Buscando…" con spinner 24 bajo el campo. |
| Error del buscador | `Aviso error` en la hoja: "No pudimos buscar. [Reintentar]". |

---

### 2.5 **Hoja de cobro** (al tocar "Cobrar $88.00")

```
┌─(borde sup. 2px texto)───────────────────────┐
│ Cobrar $88.00                    [✕ Cerrar]  │ titulo 24
│ ¿Cómo te pagan?                              │
│ ┌──────────────────────────────────────────┐ │ opciones tipo radio, alto 56, borde 1px;
│ │ (●) [cash] Efectivo                       │ │ seleccionada: borde 2px acento + radio lleno
│ └──────────────────────────────────────────┘ │ + texto "Elegido" (no solo color)
│ ┌──────────────────────────────────────────┐ │
│ │ ( ) [cellphone] Pago digital [SIMULACIÓN] │ │ lleva al flujo pago/ (Fase 5)
│ └──────────────────────────────────────────┘ │
│ Te dan (opcional)                            │ Campo moneda
│ [$ 100.00                       ]            │
│ Cambio: $12.00                               │ monto 20 Bold; si < total: error en línea
│                                              │ "Faltan $X" (peligro + icono)
│ [====== Registrar venta $88.00 ======] (56)  │ primario; cargando: "Guardando venta…"
└──────────────────────────────────────────────┘
```
- Atajos de efectivo (flexibilidad): chips "$100", "$200", "$500", "Exacto" de 48 alto.
- Al tocar "Registrar venta": el botón entra en `cargando`, no se puede tocar otra vez, se envía `POST /ventas` con `id_local` (uuid) para que un reintento nunca duplique la venta.

**Resultados del registro**

| Respuesta | Qué pasa |
|---|---|
| 200/201 | → `venta/[id]` (comprobante) |
| Sin conexión | Se guarda en la cola local → comprobante en variante **"Guardada en tu teléfono"** |
| 409 stock insuficiente | Se cierra la hoja; la fila afectada pasa a "falta" con texto "Solo hay 1 en existencia. Ajusta la cantidad." y `Aviso error` arriba. |
| 400 datos faltantes | `Aviso error` en la hoja: "Falta un dato de un producto. Revísalo." [Ir al producto] |
| 5xx / timeout | `Aviso error` en la hoja: "No se pudo registrar la venta. Tu venta sigue aquí, no se cobró dos veces." [Reintentar] · [Guardar y enviar después] |

---

### 2.6 **Venta registrada** (`venta/[id].tsx`) — comprobante

```
┌──────────────────────────────────────────────┐
│ [✕ Cerrar]   Venta registrada                │ Encabezado (Cerrar → pestaña Cobrar)
├──────────────────────────────────────────────┤
│ Paso 3 de 3 · Listo  [■■■■][■■■■][■■■■]      │
│                                              │
│  [check-circle 48 exito]                     │
│  ¡Venta registrada!                          │ titulo 24 Bold exito
│  Folio V-0042 · 19 nov 2026, 13:42           │ cuerpo 16 secundario
│  Efectivo · Te dieron $100.00 · Cambio $12.00│
│                                              │
│  2 × Refresco de cola 600 ml        $36.00   │ FilaProducto soloLectura
│  1 × Pan blanco grande              $52.00   │
│  ─────────────────────────────────────────── │
│  Total                              $88.00   │ montoGrande
│                                              │
│ ┌─ Inventario actualizado ─(1px borde)─────┐ │ ← evidencia del descuento de stock
│ │ [package-variant] Quedan:                │ │
│ │ Refresco de cola 600 ml   10 pz          │ │
│ │ Pan blanco grande          2 pz [! Poco] │ │ ← alerta de stock bajo con icono + texto
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌─ Antes vs. ahora ─(1px borde, superficie)┐ │ ← indicador para la demo
│ │ [timer-outline] Esta venta: 42 segundos  │ │
│ │ A mano (libreta y calculadora): ~3 min   │ │ "estimado" en 16 secundario
│ │ Sin sumar a mano · Inventario al día     │ │ pasos eliminados (texto)
│ └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ [==== camera Nueva venta con foto ====] (56) │ primario
│ [ Ver ventas de hoy ]   [ Ir a Inicio ]      │ secundario 48 / texto
└──────────────────────────────────────────────┘
```

**Variantes**
| Variante | Diferencias |
|---|---|
| Guardada sin conexión | Icono `cloud-upload` 48 `texto` (no verde), título "Venta guardada en tu teléfono", texto "Se enviará sola cuando vuelva el internet. El inventario se actualizará en ese momento." Bloque "Inventario actualizado" → "Inventario: pendiente". Folio local "Pendiente-3". |
| Pago digital simulado | `EtiquetaSimulacion` franja bajo el encabezado: "Simulación: este cobro no movió dinero real". |
| Abierta desde Historial | Sin `BarraPasos`; sin bloque "Antes vs. ahora"; botón principal "Volver". |
| Cargando (desde historial) | Spinner + "Cargando venta…". |
| No encontrada / error | `Aviso error` "No encontramos esta venta." [Volver a ventas de hoy]. |

El lector anuncia al entrar: "Venta registrada. Total 88 pesos. Folio V-0042."

**Visible después:** la venta aparece arriba en "Ventas de hoy" (pestaña Cobrar), en `historial.tsx` y suma en "Ventas del día" de Inicio (invalidar queries `['ventas','hoy']`, `['kpis']`, `['inventario']` al registrar).

---

## 3. Especificaciones UI (tokens usados)

| Elemento | Valores | Contraste |
|---|---|---|
| Fondo de pantallas | `fondo #FFFFFF` | — |
| Barra fija inferior de revisión | fondo `superficie #F5F5F5`, borde superior 2 px `texto #111111` | texto 17.3:1; total 32 Bold |
| Fila "falta" | borde 2 px `peligro #B00020`, fondo blanco, chip rojo | rojo/blanco 7.3:1 |
| Fila "revisa" | borde 2 px `texto #111111`, fondo `superficie` | 17.3:1 |
| Fila "listo" | divisor 1 px `#D6D6D6` (decorativo; la fila se entiende sin él) | — |
| Botón principal | `acento #0B5FFF`, texto blanco 16 Bold, alto 56, radio 8 | 5.1:1 |
| Botón "Corrige N…" | secundario: fondo blanco, borde 2 px `#111111`, texto `#111111` | 18.9:1 |
| Cámara: barras | fondo `oscuro #111111`, texto/iconos `#FFFFFF` | 18.9:1 |
| Cámara: guía de encuadre | doble trazo: 2 px `#FFFFFF` interior + 2 px `#111111` exterior | ≥ 3:1 contra cualquier fondo de imagen (uno de los dos trazos siempre contrasta) |
| Cámara: disparador | círculo 72, relleno `#FFFFFF`, borde 4 px `#111111`; texto "Tomar foto" 16 Bold blanco sobre `#111111` | 18.9:1 |
| Rectángulos sobre foto (`caja`) | 2 px + número en caja `#111111` con texto blanco 16 Bold | 18.9:1 en el número |
| Comprobante éxito | icono y título `exito #1B5E20` sobre blanco | 7.9:1 |
| Opción de pago seleccionada | borde 2 px `acento`, radio relleno `acento`, texto "Elegido" | 5.1:1 |
| Espaciado | margen lateral 16; entre secciones 24; dentro de filas 8/12; barra inferior padding 16 | — |
| Radios | botones/campos/filas con estado 8; chips 4; barras 0 | — |
| Tipografía | título 24 Bold; secciones 20 Bold; nombre producto 18 Bold; precio c/u 16 Regular secundario; subtotal 20 Bold; total 32 Bold | — |

Prohibido en todo el recorrido: `shadow*`, `elevation`, `textShadow*`, `LinearGradient`, `BlurView`, fondos semitransparentes sobre la cámara o los modales (usar `#111111` sólido o `superficie` sólida).

---

## 4. Justificación HCI / Nielsen

| # | Aplicación concreta |
|---|---|
| 1 Visibilidad del estado | `BarraPasos` (Foto/Revisar/Listo); etapas reales del análisis; "tardando más de lo normal" a los 8 s; total en vivo; "Pendiente de enviar" en ventas en cola; bloque "Inventario actualizado" prueba el descuento de stock. |
| 2 Mundo real | "Cobrar", "Te dan", "Cambio", "pz", "c/u", "producto suelto", "Caja"; nunca "SKU", "confianza", "detección", "IA". |
| 3 Control y libertad | Quitar sin diálogo con **Deshacer**; "Está bien" para aceptar lo dudoso; Atrás guarda borrador; "Empezar de nuevo" con confirmación; Cancelar durante el análisis. |
| 4 Consistencia | Un solo botón primario azul abajo en cada paso; la hoja inferior (editar, agregar, cobrar, Caja) se comporta igual siempre; iconos siempre con texto. |
| 5 Prevención de errores | No se puede cobrar con productos sin precio/sin producto; tope de cantidad por existencia; `id_local` evita cobros duplicados; botón bloqueado mientras guarda; "Faltan $X" si el efectivo no alcanza. |
| 6 Reconocer > recordar | Sugerencias del catálogo con precio y existencia; "Más vendidos"; "Repetir última venta"; "Ver foto" con números que coinciden con las filas. |
| 7 Flexibilidad | Atajos de efectivo ($100/$200/$500/Exacto); escribir cantidad directa; "Repetir última venta"; cobrar sin foto. |
| 8 Minimalista | Lista densa sin imágenes de producto ni decoración; la foto solo aparece si se pide. |
| 9 Recuperación de errores | Cada error del análisis y del registro tiene mensaje humano + acción (tomar otra, reintentar con la misma foto, cobrar buscando, guardar y enviar después). |
| 10 Ayuda | "Ayuda" en la cámara con ejemplos; "Pregúntale a Caja" con contexto de la venta sin salir de la revisión. |

**Accesibilidad:** pares de color declarados arriba (todos ≥ 4.5:1 en texto, ≥ 3:1 en bordes/guías) · todos los tocables ≥ 48 (disparador 72, principal 56) con ≥ 8 de separación · disparador, galería, total y botón de cobro en el tercio inferior (una mano) · estados por icono + texto ("Revisa", "Falta precio", "Elegido", "Pendiente de enviar") · lector: anuncios en cambios de etapa, al quitar ("Quitaste Galletas. Botón Deshacer disponible"), al registrar; foco movido al primer problema con "Corrige N productos" · franja de deshacer sin límite de tiempo con lector activo (WCAG 2.2.1) · letra del sistema al 200 %: filas crecen en alto, botones de la fila se apilan, nada se corta en montos · sin animaciones salvo spinner; con `reduceMotion` el scroll a la fila con problema es sin animación (`animated: false`).

---

## 5. Notas para el contrato con back (`src/api/esquemas.ts`)

El contrato actual cubre la visión pero **no** el registro de la venta ni el buscador. Propuesta mínima para acordar:

```ts
// GET /productos?q=texto&limite=10   y   GET /productos/mas-vendidos?limite=6
export const Producto = z.object({
  sku: z.string(), nombre: z.string(),
  precio_unitario: z.number().nonnegative(),
  existencia: z.number().int(),          // para tope del stepper y "Poco"
});

// POST /ventas
export const SolicitudVenta = z.object({
  id_local: z.string(),                   // uuid del teléfono → idempotencia
  imagen_id: z.string().nullable(),       // de RespuestaPosCheckout, null si fue sin foto
  metodo_pago: z.enum(['efectivo', 'digital_simulado']),
  recibido: z.number().nullable(),
  items: z.array(z.object({
    sku: z.string().nullable(),           // null solo si libre === true
    nombre: z.string(),
    cantidad: z.number().int().positive(),
    precio_unitario: z.number().nonnegative(),
    libre: z.boolean().optional(),        // producto suelto: no descuenta inventario
    corregido: z.boolean(),               // útil para medir/reentrenar la visión
  })),
  duracion_seg: z.number().optional(),    // para el indicador "Antes vs. ahora"
});

export const RespuestaVenta = z.object({
  venta_id: z.string(), folio: z.string(), total: z.number(), creada_en: z.string(),
  existencias: z.array(z.object({ sku: z.string(), nombre: z.string(), quedan: z.number().int(), bajo: z.boolean() })),
});
// 409 → { sku, existencia } para marcar la fila
```

Mock sugerido (`mocks/index.ts`): `mockPosCheckout` ya trae el caso "falta" (galletas sin sku/precio, 0.41). Agregar un ítem con precio y confianza 0.52 (fila "Revisa" no bloqueante) y variantes `mockPosCheckoutVacio` (`items: []`) y un modo de mock que responda 422 / timeout para probar errores en la demo.

**Referencia "A mano ~3 min":** valor fijo en `constants.ts` (`SEGUNDOS_VENTA_MANUAL = 180`), etiquetado "estimado". Si el equipo mide el proceso real en una tienda, reemplazar el número.
