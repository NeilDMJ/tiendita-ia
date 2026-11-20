# 02 · Asistente — chat unificado, tarjetas de acción y "Pregúntale a Caja"

> Autor: `ui-ux-movil` · Implementa: `frontend-implementador` · Audita: `revisor-ui-m3` + `revisor-accesibilidad-hci`
> Fase 3 de `docs/PLAN-frontend.md`. Sistema visual: `00-sistema.md` (M3 + excepciones `EXC-1…10`). Contexto de la revisión: `01-cobrar.md` §2.4.
> Usuario: **tendero / dueño** (no el cliente de la colonia). Atiende el mostrador con una mano, puede tener baja visión y poca práctica con apps.
> Solo especificación: el código va en Fase 3 por `frontend-implementador`.

---

## 1. Concepto y enfoque elegido

**Problema real:** el tendero tiene dudas mientras trabaja ("¿cuánto vendí?", "¿qué se me acaba?", "¿cuánto cuesta esto?") y hoy las resuelve con la libreta, la memoria o llamando al proveedor. El asistente responde **sin salir de la app** y, cuando hace falta guardar algo, **propone** y el tendero **confirma**.

**Enfoque: conversación + tarjetas de confirmación** (mezcla de *Lista densa* para los mensajes y *Tarjetas estructuradas* para lo que cambia datos). Por qué:
- El chat es un solo lugar: el tendero no tiene que saber a qué "área" preguntar. Un orquestador interno decide quién contesta; en pantalla se ve **el oficio** (Caja, Bodega, Cuentas, Promociones, Ayuda de pagos) con icono + nombre, nunca "agente", "modelo" ni "IA".
- Todo lo que mueve dinero, inventario o publica algo llega como **TarjetaAccion** (card elevated) con botón de confirmar explícito y "Revisar y editar" que lleva a la **pantalla editable** (requisito de las bases: revisión y corrección; "pasar lo que entendió a un formulario").
- El asistente aparece **dentro del recorrido principal**: en la revisión del cobro como bottom sheet "Pregúntale a Caja" (§4), con la venta como contexto, y sus propuestas modifican la fila al aplicarlas.

**Nombres de oficio** (`src/constants.ts → ROLES`):

| `rol` (contrato) | Se muestra | Icono (MCI) | Qué atiende (texto del estado vacío) |
|---|---|---|---|
| `caja` | **Caja** | `cash-register` | Ventas, cobros, precios |
| `bodega` | **Bodega** | `package-variant-closed` | Lo que tienes, lo que se acaba, caducidades |
| `cuentas` | **Cuentas** | `calculator-variant` | Ganancias, gastos, reportes (incluye al "investigador" del back) |
| `promociones` | **Promociones** | `bullhorn-outline` | Ofertas para lo que está por caducar |
| `tutor` | **Ayuda de pagos** | `school-outline` | Cómo cobrar con transferencia o tarjeta |
| `general` | **Tu asistente** | `chat-outline` | Cuando aún no se sabe quién contesta, o respuestas generales |

> **Cambio en `constants.ts`:** `general.nombre` pasa de `'Asistente'` a `'Tu asistente'` (se distingue del nombre de la pestaña y suena cercano). `tutor` se queda como **"Ayuda de pagos"** (ya usado en 00-sistema §9.10; "Tutor" suena escolar y no dice para qué sirve).
> Sin color por rol: todos los roles usan el mismo estilo; se distinguen por **icono + nombre** (Nielsen #8, no depender del color).

---

## 2. Pestaña Asistente (chat unificado)

Ruta: `src/app/(tabs)/asistente.tsx` → `src/screens/asistente.tsx`.

### 2.1 Wireframe — conversación con mensajes

```
┌──────────────────────────────────────────────┐
│ Asistente                [broom Borrar chat] │ Top app bar small 64 (surface → surfaceContainer al desplazar)
├──────────────────────────────────────────────┤   titleLarge 22 · acción Boton text con icono (solo si hay mensajes)
│ [flask] Simulación: respuestas de ejemplo    │ ← Banner EtiquetaSimulacion franja SOLO si EXPO_PUBLIC_USE_MOCKS=1
│ [wifi-off] Sin conexión: tus preguntas se    │ ← Banner Aviso franja 'sinConexion' SOLO sin internet
│ enviarán al volver el internet.              │
├──────────────────────────────────────────────┤
│                    Hoy                       │ separador de día: labelLarge 16 onSurfaceVariant, centrado
│                                              │
│              ╭───────────────────────────╮   │ BURBUJA TENDERO (derecha, máx 85 %)
│              │ ¿Cuánto vendí hoy?        │   │ primaryContainer / onPrimaryContainer, bodyLargePlus 18
│              ╰───────────────────────╮4dp│   │ esquinas 16, la inferior derecha 4
│                               10:42      │   │ hora: labelLarge 16 onSurfaceVariant
│                                              │
│ [calculator-variant] Cuentas                 │ cabecera de rol: icono 24 onSurfaceVariant + titleSmall 16/500 onSurface
│ ╭───────────────────────────╮                │ BURBUJA ASISTENTE (izquierda, máx 85 %)
│ │ Hoy llevas $1,245.00 en 23│                │ surfaceContainerHigh / onSurface, bodyLargePlus 18
│ │ ventas. Lo que más salió  │                │ esquinas 16, la superior izquierda 4
│ │ fue refresco de 600 ml.   │                │
│ ╰───────────────────────────╯                │
│ 10:42                                        │
│ [Ver ventas de hoy] (tonal 48, icono receipt)│ ← acción abrir_pantalla: botón, NO tarjeta
│                                              │
│              ╭───────────────────────────╮   │
│              │ vendí 2 cocas y un pan    │   │
│              ╰───────────────────────────╯   │
│ [cash-register] Caja                         │
│ ╭───────────────────────────╮                │
│ │ Va. ¿Lo cobro así?        │                │
│ ╰───────────────────────────╯                │
│ ╭─ TarjetaAccion (card elevated) ──────────╮ │ ancho completo (−32), ver §3
│ │ [cash-register] Caja propone:            │ │
│ │ Cobrar venta de 2 productos              │ │
│ │ ──────────────────────────────────────── │ │
│ │ 2 × Refresco de cola 600 ml      $36.00  │ │
│ │ 1 × Pan blanco grande            $52.00  │ │
│ │ Total                            $88.00  │ │
│ │ ──────────────────────────────────────── │ │
│ │ [====== Confirmar cobro $88.00 ======]   │ │ filled 48
│ │ [        Revisar y editar         ]      │ │ outlined 48
│ │            No, gracias                   │ │ text 48
│ ╰──────────────────────────────────────────╯ │
│                                              │
│ (¿Qué más se me acaba?) (Ventas de ayer)     │ ← sugerencias de la última respuesta (suggestion chips 48)
├──────────────────────────────────────────────┤ COMPOSITOR: surfaceContainer, divisor sup. 1 dp outlineVariant
│ ╭──────────────────────────────╮ ╭─────────╮ │ Campo outlined multilínea (56 → máx 5 líneas)
│ │ Escribe tu pregunta…         │ │[send]   │ │ + Boton filled 56 "Enviar" con icono send
│ ╰──────────────────────────────╯ │ Enviar  │ │
│                                  ╰─────────╯ │
├──────────────────────────────────────────────┤
│ (Inicio) (Cobrar) (Inventario) (▣Asistente)  │ Navigation bar 80 (se oculta con el teclado abierto)
└──────────────────────────────────────────────┘
```

**Reglas de la lista**
1. `FlatList` **no invertida** (las listas invertidas desordenan la lectura en TalkBack); al llegar un mensaje se hace `scrollToEnd` (`animated: false` con movimiento reducido). `maintainVisibleContentPosition` para no saltar al cargar historial.
2. Si el tendero subió a leer y llega un mensaje nuevo, **no** se le mueve: aparece arriba del compositor un botón **tonal** "[arrow-down] Mensaje nuevo de Bodega" (48, shape `full`) que baja al final. Nielsen #1 + #3.
3. Separadores de día ("Hoy", "Ayer", "12 nov"). Hora debajo de cada burbuja (no hace falta "palomitas": el estado solo se muestra cuando algo falla o está en espera).
4. Respuestas en **texto plano** con saltos de línea y viñetas "• " (el back no manda markdown; si llega, se muestra tal cual sin asteriscos: `limpiarFormato()` quita `**`, `#`, `_`).
5. Sin truncar mensajes (no hay "Ver más"); el texto envuelve con cualquier tamaño de letra.
6. Hasta **3 sugerencias** (`sugerencias` del contrato, §5) debajo de la **última** respuesta; desaparecen al enviar otro mensaje.

### 2.2 Burbujas M3

M3 no tiene un componente "chat bubble"; se arma con tokens de color, forma y tipografía (patrón de mensajería de Material: forma redondeada con la esquina del autor recortada).

| Parte | Tendero | Asistente |
|---|---|---|
| Alineación | derecha, margen izq. ≥ 48 | izquierda, margen der. ≥ 48 |
| Ancho máx. | 85 % (100 % − 32 con letra ≥ 1.3×) | 85 % (ídem) |
| Contenedor | `primaryContainer #D6E3FF` | `surfaceContainerHigh #E7E8EE` |
| Texto | `onPrimaryContainer #284777` **7.24:1** | `onSurface #191C20` **14.0:1** |
| Tipografía | `bodyLargePlus` 18/26 | `bodyLargePlus` 18/26 |
| Forma | `large` 16; inferior derecha `extraSmall` 4 | `large` 16; superior izquierda `extraSmall` 4 |
| Padding | 16 horiz. / 12 vert. | 16 / 12 |
| Elevación | 0 | 0 |
| Cabecera | Ninguna (con letra ≥ 1.3×: "Tú" `titleSmall` `onSurfaceVariant`, porque la alineación ya no se nota) | Icono de rol 24 `onSurfaceVariant` (8.89) + nombre `titleSmall` 16/500 `onSurface` (16.3), 4 dp sobre la burbuja |
| Hora | `labelLarge` 16 `onSurfaceVariant` 8.89:1, alineada a su lado | ídem |
| Separación | 8 entre burbujas del mismo autor; 16 al cambiar de autor | |

- El borde de las burbujas vs. `surface` es bajo (1.23 y 1.17:1) **a propósito**: no son controles (WCAG 1.4.11 no aplica) y quién habla se sabe por **alineación + cabecera con icono y nombre** + label del lector. No se agrega borde (Nielsen #8).
- Las burbujas no son tocables (copiar con pulsación larga: **fuera de alcance**).

**Estados de la burbuja del tendero** (fila debajo de la burbuja, alineada a la derecha):

| Estado | Visual | Acciones |
|---|---|---|
| `enviando` | Solo la hora; el indicador "escribiendo…" aparece abajo | — |
| `enviado` | Hora | — |
| `en_espera` (sin internet) | `clock-outline` 20 + "Se enviará al volver el internet" `bodyLarge` `onSurfaceVariant` (8.89) | [Cancelar envío] text |
| `fallido` | `alert-circle` 20 `error` + motivo humano en `error` 16/500 (6.15:1): "No se envió: sin conexión." / "Tardó mucho en contestar." / "No pudimos traer la respuesta." | [refresh Reintentar] text `primary` · [Borrar] text |

### 2.3 Indicador "escribiendo…"

```
│ [chat-outline] Tu asistente                  │ ← rol 'general' (aún no se sabe quién contesta)
│ ╭──────────────────────╮                     │
│ │ ● ● ●  Escribiendo…  │                     │ surfaceContainerHigh; puntos 8 dp onSurfaceVariant + bodyLarge onSurfaceVariant 7.63:1
│ ╰──────────────────────╯                     │
```
- Puntos **estáticos** (sin animación) o, si no hay movimiento reducido, opacidad que alterna en 3 pasos cada 400 ms (`standard`), nunca rebote. El texto "Escribiendo…" siempre está (no depende de la animación).
- **A los 8 s** el texto cambia a "Está tardando más de lo normal…" y aparece [Detener] text debajo.
- **A los 25 s** (tiempo límite, §5.4) se quita el indicador y la burbuja del tendero pasa a `fallido` "Tardó mucho en contestar." [Reintentar].
- Mientras espera, el botón Enviar se cambia por **[stop Detener]** (tonal 56): el botón nunca queda "muerto" (00-sistema `EXC-4`, regla de negocio). El campo sigue editable. Detener cancela (`AbortController`) y deja la burbuja en `fallido` "Detuviste la respuesta." [Reintentar].
- Lector: se anuncia **una vez** "Enviado. Tu asistente está escribiendo." (no cada segundo).

### 2.4 Estado vacío (sin mensajes)

```
┌──────────────────────────────────────────────┐
│ Asistente                                    │ (sin "Borrar chat")
├──────────────────────────────────────────────┤
│        [chat-outline 48 onSurfaceVariant]    │
│        ¿En qué te ayudo hoy?                 │ headlineSmall 24 onSurface
│  Pregunta por tus ventas, lo que se te acaba │ bodyLarge onSurfaceVariant
│  o cómo cobrar. Antes de guardar o cobrar    │
│  algo, siempre te pido que lo confirmes.     │
│                                              │
│  Te contestan:                               │ titleSmall 16/500
│  [cash-register]  Caja · ventas y precios    │ list items de 1 línea, alto 48, NO tocables
│  [package-…]      Bodega · lo que tienes     │ icono 24 onSurfaceVariant + bodyLarge onSurface
│  [calculator-…]   Cuentas · ganancias, gastos│
│  [bullhorn-…]     Promociones · ofertas      │
│  [school-…]       Ayuda de pagos · cobro     │
│                   digital                    │
│                                              │
│  [microphone] También puedes dictar con el   │ bodyLarge onSurfaceVariant (pista: micrófono del teclado)
│  micrófono de tu teclado.                    │
│ ─ ─ ─ ─ ─ ─ (zona del pulgar) ─ ─ ─ ─ ─ ─ ─  │
│ Prueba con:                                  │ titleSmall
│ ╭──────────────────────────────────────────╮ │ SUGGESTION CHIPS apilados a ancho completo, 48 alto,
│ │ [trending-up] ¿Cuánto vendí hoy?         │ │ gap 8, anclados JUSTO ARRIBA del compositor
│ ╰──────────────────────────────────────────╯ │
│ ╭──────────────────────────────────────────╮ │
│ │ [package-down] ¿Qué se me está acabando? │ │
│ ╰──────────────────────────────────────────╯ │
│ ╭──────────────────────────────────────────╮ │
│ │ [cash-register] Registrar una venta      │ │
│ ╰──────────────────────────────────────────╯ │
│ ╭──────────────────────────────────────────╮ │
│ │ [bank-transfer] ¿Cómo cobro con          │ │
│ │ transferencia?                           │ │
│ ╰──────────────────────────────────────────╯ │
├──────────────────────────────────────────────┤
│ [ Escribe tu pregunta…        ] [send Enviar]│
└──────────────────────────────────────────────┘
```
- Tocar un chip **envía** ese texto de inmediato (no lo pega en el campo): menos pasos para quien no escribe bien (Nielsen #7).
- "Registrar una venta" → Caja responde "Dime qué vendiste, por ejemplo: *2 refrescos y un pan*. O cóbralo con foto." + botón `abrir_pantalla` [camera Cobrar con foto]. Cuando el tendero escribe la venta, llega la tarjeta `confirmar_venta` (§3).
- "¿Cómo cobro con transferencia?" → Ayuda de pagos responde con pasos numerados + [Practicar un cobro (Simulación)] → `abrir_pantalla: pago` (Fase 5).
- Con letra grande, la lista "Te contestan" se puede desplazar; los chips siguen pegados al compositor.

### 2.5 Compositor (campo + Enviar)

- Barra fija inferior `surfaceContainer #EDEDF4` (nivel 2 tonal, sin sombra), divisor superior 1 dp `outlineVariant`, padding 8/16, `paddingBottom` = safe area si la navigation bar está oculta.
- **Campo:** `Campo` outlined (00-sistema §9.2) en modo multilínea: alto mín. 56, crece hasta **5 líneas** (3 con letra ≥ 1.3×) y luego hace scroll; fondo `surfaceContainerLowest`, borde 1 dp `outline` (4.48:1), enfocado 2 dp `primary`. Texto `bodyLargePlus` 18 `onSurface` (17.1:1), igual que el resto de los `Campo`. Placeholder "Escribe tu pregunta…" `onSurfaceVariant` (9.34:1). **Sin etiqueta visible** (`EXC-11` en 00-sistema §10, excepción a `EXC-3` justificada: el placeholder no es la única pista: hay un label accesible "Tu pregunta" y el contexto de chat es inequívoco); el placeholder desaparece al escribir pero el botón "Enviar" deja claro el propósito.
- Límite 500 caracteres; contador "480 de 500" (`bodyLarge` `onSurfaceVariant` 8.03:1) solo desde 450.
- **Botón Enviar:** `Boton` filled `tamano="principal"` 56, icono `send` + "Enviar", `anchoCompleto={false}`, gap 8 con el campo, alineado abajo. Con letra ≥ 1.3× pasa **debajo del campo a ancho completo**.
  - Campo vacío: el botón **no** se deshabilita en gris; al tocarlo, el campo muestra el error en línea "Escribe tu pregunta primero" y recibe foco (`EXC-4`: el botón principal nunca muere). Espacios en blanco = vacío.
  - Esperando respuesta: [stop Detener] tonal (§2.3).
  - Sin internet: sigue siendo "Enviar"; el supporting text del campo dice "Sin internet: se enviará al volver" (`wifi-off`) — ver §2.7.
- `returnKeyType="default"` (Enter = salto de línea; enviar solo con el botón para evitar envíos accidentales con el dedo grueso).
- **Teclado:** `tabBarHideOnKeyboard: true` en `(tabs)/_layout.tsx` para que el compositor quede pegado al teclado; `KeyboardAvoidingView` (`behavior="padding"` en iOS; en Android, `softwareKeyboardLayoutMode: "resize"` en `app.json`). Con edge-to-edge de Android probar en el teléfono que el campo no quede tapado; si falla, revisar en la doc de Expo SDK 58 si `react-native-keyboard-controller` viene en Expo Go antes de agregarlo.

### 2.6 `no_resuelto` — el asistente no pudo

```
│ [chat-outline] Tu asistente                  │
│ ╭───────────────────────────────────╮        │
│ │ No entendí bien. ¿Quieres cobrar, │        │ texto del back (burbuja normal)
│ │ revisar tu inventario o ver tus   │        │
│ │ ventas?                           │        │
│ ╰───────────────────────────────────╯        │
│ ╭─ Card outlined (borde 1 dp outline) ─────╮ │ shape medium, fondo surface, padding 16
│ │ [help-circle] No pude resolverlo.        │ │ titleMedium 18 onSurface · icono onSurfaceVariant
│ │ Puedes hacerlo tú directo:               │ │ bodyLarge onSurfaceVariant
│ │ [camera  Cobrar con foto      ] tonal 48 │ │ acciones abrir_pantalla que mande el back,
│ │ [package Ver inventario       ] tonal 48 │ │ o este conjunto por defecto
│ │ [receipt Ver ventas de hoy    ] tonal 48 │ │
│ │ [whatsapp Escribir a soporte  ] text  48 │ │ solo si EXPO_PUBLIC_SOPORTE_WHATSAPP existe
│ ╰──────────────────────────────────────────╯ │
│ (Preguntar de otra forma)                    │ suggestion chip: enfoca el campo
```
- Se usa card **outlined** con borde `outline` (no `outlineVariant`) porque agrupa controles (`EXC-10`, 4.27:1). No es rojo: no es un error del tendero (Nielsen #9: mensaje humano + salida directa).
- Si el back manda `acciones` tipo `abrir_pantalla` en un `no_resuelto`, se usan esas (máx. 3); si no, el conjunto por defecto.
- Soporte: abre `https://wa.me/<número>` con `Linking`; el número viene de `.env` (en la demo, número del equipo o se oculta; nunca datos reales en mocks).

### 2.7 Sin conexión

Decisión: **un solo mensaje en cola**, nunca acciones en cola.
- Banner `Aviso` franja `sinConexion` bajo la top app bar: "Sin conexión: tus preguntas se enviarán al volver el internet."
- Si el tendero envía sin internet: la burbuja queda `en_espera` (§2.2) con [Cancelar envío]. Al reconectar (`useConexion`) se envía sola, una vez, y se anuncia "Se envió tu pregunta". Si hay ya uno en espera y escribe otro, el nuevo **reemplaza** al anterior y sale snackbar "Cambiamos tu pregunta en espera. [Deshacer]" (evita que lleguen 5 respuestas viejas de golpe).
- Las tarjetas pendientes: `confirmar_venta` **sí** se puede confirmar sin internet (usa la cola de ventas de 01-cobrar; resultado "Venta guardada · Pendiente de enviar"). `confirmar_alta` y `aprobar_promo`: el botón de confirmar muestra "Necesita internet" (`EXC-4`, motivo visible) y sigue habiendo "No, gracias".
- Historial: se lee del teléfono, así que la conversación anterior se ve completa sin internet.

### 2.8 Historial persistente y Borrar chat

- Se guarda en `expo-sqlite/kv-store` (`src/estado/almacen.ts`) con clave `asistente-chat-v1`: últimos **100** mensajes (los más viejos se descartan), incluyendo el estado de cada tarjeta.
- Al abrir la app, las tarjetas `pendiente` con más de **30 min** (o con `vence_en` pasado) se marcan `caducada`. Las que estaban `confirmando` cuando se cerró la app pasan a `error` con [Reintentar] (el `id_local` evita cobros dobles).
- Al servidor solo se manda el historial resumido (§5.1), nunca los 100.
- **Borrar chat** (acción de la top app bar, solo con mensajes; arriba = lejos del pulgar a propósito, es destructiva y rara):
  `Dialogo` M3: icono `broom` · "¿Borrar la conversación?" · "Se borran los mensajes de este teléfono. Tus ventas y tu inventario no cambian." · [No, regresar] (tonal) · [Sí, borrar] (`filledError`). Sin cierre por velo.
  Después: estado vacío + `Snackbar` "Borraste la conversación. [Deshacer]" (10 s; sin límite con lector activo). Deshacer restaura la copia en memoria.

### 2.9 Estados de la pantalla (resumen)

| Estado | Qué se ve |
|---|---|
| Cargando historial | Circular progress 24 + "Cargando tu conversación…" (casi instantáneo; si < 300 ms no se muestra) |
| Vacío | §2.4 |
| Con mensajes | §2.1 |
| Escribiendo | §2.3 |
| Error de envío | Burbuja `fallido` con [Reintentar] (§2.2) |
| No resuelto | §2.6 |
| Sin conexión | §2.7 |
| Error al leer el historial | Estado vacío + `Aviso` tarjeta `info` "No pudimos abrir la conversación anterior. Puedes empezar una nueva." (sin acción obligatoria: no se pierde nada importante, las ventas están en Historial) |
| Mocks | Banner `EtiquetaSimulacion` franja "Simulación: respuestas de ejemplo" |

---

## 3. Tarjetas de acción (acciones críticas)

Reutiliza `TarjetaAccion` (00-sistema §9.10, card elevated `surfaceContainerLow`, shape `medium`, level1). Un adaptador `TarjetaPropuesta` convierte cada `AccionAsistente` en props de `TarjetaAccion` según su `tipo`.

**Regla de oro:** el back **nunca** ejecuta nada por su cuenta. Las acciones llegan como *propuestas*; el front solo llama al endpoint de negocio (p. ej. `POST /ventas`) **después** de que el tendero toca el botón de confirmar. Siempre hay "Revisar y editar" (pantalla editable) o "No, gracias".

### 3.1 Anatomía (recordatorio) y mapeo por tipo

```
[icono rol] {Rol} propone:                 [Simulación?]   labelLarge onSurfaceVariant (8.46:1 sobre T96)
{titulo}                                                    titleLarge 22 onSurface (15.5:1)
──────────── resumen (máx. 4 filas + "y N más") ────────────
{izquierda}                               {derecha}         bodyLarge / amount
Total                                     $88.00
────────────────────────────────────────────────────────────
[==== {textoConfirmar} ====]   filled 48
[    Revisar y editar     ]    outlined 48   (si aplica)
        No, gracias            text 48
```

| `tipo` | Rol típico | Título / resumen | Confirmar (filled) | Revisar y editar | Al confirmar | Resultado (`hecha`) |
|---|---|---|---|---|---|---|
| `confirmar_venta` | Caja | "Cobrar venta de N productos" · filas "2 × Nombre  $36.00" · Total | "Confirmar cobro $88.00" | Carga los items al carrito → `revision/cobro` (si hay borrador: `Dialogo` "Ya tienes una venta sin terminar" [Reemplazarla] / [Mantener la mía]) | `POST /ventas` con `id_local = 'chat-' + accion.id` (o cola sin internet) | "Venta registrada · Folio V-0043" + [Ver comprobante] → `venta/[id]` |
| `confirmar_alta` | Bodega | "Dar de alta 12 pz de Leche entera 1 L" · Precio, Caduca | "Confirmar alta" | → `revision/alta` precargada (Fase 4; mientras no exista, se oculta este botón) | `POST /inventario/altas` (acordar en Fase 4) | "Agregado a tu inventario · Quedan 15 pz" |
| `aprobar_promo` | Promociones | "Promoción: Yogur natural 1 L a $30" · copy de la promo · "Hasta el viernes" · miniatura de video si hay | "Aprobar promoción" | "Cambiar texto" → `promociones` (Fase 6) | `POST /promociones/{id}/aprobar` | "Promoción aprobada" + **chip Simulación** si no se publica de verdad: "Simulación: no se publicó en redes" |
| `modificar_item` | Caja | Solo en "Pregúntale a Caja" (§4) | "Aplicar a la venta" | — | Cambia la fila localmente (sin red) | Snackbar con Deshacer (§4.3) |
| `abrir_pantalla` | cualquiera | **No es tarjeta**: botón tonal 48 con icono + `titulo` bajo la burbuja | — | — | Navega (no cambia datos; se puede volver) | — |

- Si un item de `confirmar_venta` viene sin precio o sin producto del catálogo, el botón filled pasa a ser **"Revisar y editar"** y no aparece "Confirmar cobro" (no se cobra con datos incompletos; prevención de errores). La fila muestra `IndicadorConfianza` `falta` ("Falta precio").
- Un mensaje trae **máx. 3** acciones; cada tarjeta es independiente.

### 3.2 Estados

El componente ya usa `pendiente · confirmando · hecha · rechazada · error · caducada`. Equivalencia con el pedido: **confirmada = `hecha`**, **expirada = `caducada`**.

| Estado | Visual | Elevación | Lector |
|---|---|---|---|
| `pendiente` | Botones activos | level1 | Label "Caja propone: Cobrar venta de 2 productos, total 88 pesos" |
| `confirmando` | Filled en cargando ("Cobrando…", "Guardando…", "Aprobando…"); outlined deshabilitado; "No, gracias" oculto | level1 | `busy` |
| `hecha` | `check-circle` `success` (6.13:1) + resultado + [Ver comprobante] | 0 | Live region "Listo. Venta registrada, folio V-0043" |
| `rechazada` | `close-circle` `onSurfaceVariant` + "Cancelaste esta acción" | 0 | "Cancelaste esta acción" |
| `error` | `Aviso` error embebido con mensaje humano según `TipoError` ("No se pudo cobrar. Tu venta sigue aquí.", "No hay suficientes piezas: solo quedan 2.") + [Reintentar] filled + [Revisar y editar] outlined | level1 | `alert` |
| `caducada` | "Esta propuesta ya no está vigente" + motivo ("Hay una más nueva abajo" / "Pasó mucho tiempo" / "La venta cambió") + botones deshabilitados `EXC-4` | 0 | Motivo leído |
| *(nuevo)* datos ilegibles | Si `datos` no pasa zod: tarjeta en `error` "No pudimos leer esta propuesta." + [Hacerlo a mano] → pantalla del tipo | 0 | `alert` |

**Cuándo caduca:**
1. Llega otra propuesta del **mismo tipo** → la anterior pendiente pasa a `caducada` ("Hay una más nueva abajo").
2. `vence_en` (del back) pasó, o > 30 min sin respuesta.
3. `modificar_item`: la fila ya no coincide (`clave` o `nombre_actual` distintos) → "La venta cambió desde que Caja lo propuso. Pregúntale otra vez."
4. Al salir de la revisión (venta cobrada o descartada), las tarjetas de esa hoja de Caja se descartan junto con la conversación.

**Opcional (si el back lo pide):** tras confirmar/rechazar, `POST /asistente/acciones/{id}/resultado { estado }` *fire-and-forget* para que el orquestador sepa qué pasó. Su falla no se muestra.

---

## 4. "Pregúntale a Caja" dentro de la revisión del carrito

Abre desde la acción "Caja" de la top app bar y el botón "¿Dudas? Pregúntale a Caja" de `revision-cobro` (01-cobrar §2.4). Archivo: `src/screens/revision/hoja-caja.tsx`.

### 4.1 Wireframe

```
          (revisión atrás, con velo 32 %, inerte)
╭──────────────────────────────────────────────╮
│                    ▬▬▬▬                      │ drag handle (48 táctil)
│ [cash-register] Pregúntale a Caja [✕ Cerrar] │ titleLarge 22 · Boton text con icono (EXC-7)
│ [eye-outline] Caja ve tu venta: 4 productos, │ bodyLarge onSurfaceVariant (8.46:1 sobre T96)
│ $88.00 (1 sin precio)                        │ ← qué datos se comparten (confianza, Nielsen #1)
│ ──────────────────────────────────────────── │
│              ╭─────────────────────────────╮ │
│              │ ¿Qué producto es el que no  │ │
│              │ reconoció?                  │ │
│              ╰─────────────────────────────╯ │
│ [cash-register] Caja                         │
│ ╭────────────────────────────────╮           │
│ │ El producto 1 parecen Galletas │           │
│ │ María 170 g, cuestan $16.00.   │           │
│ ╰────────────────────────────────╯           │
│ ╭─ TarjetaAccion (modificar_item) ─────────╮ │
│ │ [cash-register] Caja propone:            │ │
│ │ Cambiar el producto 1                    │ │ titleLarge
│ │ ──────────────────────────────────────── │ │
│ │ Antes   Galletas (sin identificar) · — — │ │ bodyLarge onSurfaceVariant
│ │ Ahora   Galletas María 170 g · $16.00    │ │ bodyLarge onSurface, peso 700 en lo que cambia
│ │ ──────────────────────────────────────── │ │
│ │ [====== Aplicar a la venta ======]       │ │ filled 48
│ │            No, gracias                   │ │ text 48
│ ╰──────────────────────────────────────────╯ │
│ ──────────── pie fijo (divisor) ──────────── │
│ (¿Cuánto cuesta este producto?)              │ suggestion chips 48, scroll horizontal
│ (¿Qué producto no reconoció?) (¿Me alcanza   │ (con letra grande: apilados, máx. 2 visibles)
│  el stock?)                                  │
│ [ Pregúntale a Caja…          ] [send Enviar]│ compositor (§2.5)
╰──────────────────────────────────────────────╯
```

- `HojaInferior` **modal**, `altoMaximo={0.9}`: la revisión queda visible arriba (10 %) y se mantiene intacta debajo; cerrar regresa exactamente al mismo scroll. **No cambia de pestaña.**
- **Cambio requerido en `HojaInferior`:** prop nueva `sinScroll?: boolean` para que el hijo maneje su propia `FlatList` (evita lista virtual dentro de `ScrollView`). El compositor va en `pie` y debe subir con el teclado (la hoja ya usa `KeyboardAvoidingView`).
- Rol fijo esperado `caja`; si el back responde con otro rol (p. ej. Bodega para "¿Me alcanza el stock?") se muestra ese rol sin problema.
- **Conversación propia de la venta:** no se mezcla con la pestaña Asistente (las propuestas "Aplicar a la venta" no tienen sentido fuera de la revisión). Se guarda junto al borrador del carrito (`chat-caja-borrador`) y se borra al cobrar o descartar la venta.
- Estado vacío de la hoja: texto "Pregúntale lo que no sepas de esta venta." + los 3 chips apilados arriba del compositor.
- Sin conexión: el acceso ya está deshabilitado en la revisión con "Necesita internet" (01-cobrar). Si se cae el internet con la hoja abierta: banner `sinConexion` dentro de la hoja, el mensaje **no** se pone en cola (la venta puede cambiar), burbuja `fallido` "No se envió: sin conexión." [Reintentar].

### 4.2 Contexto enviado

`contexto = { pantalla: 'revision_cobro', imagen_id, total, items: ItemContexto[] }`, construido con `aContextoCobro(carrito)` en el momento de **cada** envío (siempre la versión actual de la revisión). `indice` = posición en `carrito.items` (orden del servidor, no el orden visual por secciones); `numero_en_foto` = el número que ve el tendero en la fila (para que Caja diga "el producto 1").

### 4.3 Aplicar una propuesta `modificar_item`

1. Tocar [Aplicar a la venta] → validar contra el carrito **actual**: `items[indice].clave === datos.clave` y `nombre === datos.nombre_actual`; `cantidad` entre 1 y `stockDisponible`; `precio_unitario ≥ 0`.
2. Si no coincide → tarjeta `caducada` "La venta cambió desde que Caja lo propuso. Pregúntale otra vez." Si excede existencia → tarjeta `error` "Solo hay 3 en existencia." [Revisar y editar] (abre "Editar producto" de esa fila al cerrar la hoja).
3. Si es válida → `actualizarItem(clave, { ...cambios, revisadoPorUsuario: true })` (la fila queda con chip "Tú lo pusiste": el tendero la confirmó). Se guarda una copia previa para Deshacer.
4. Si **no** quedan otras tarjetas pendientes en la hoja → la hoja se cierra; si quedan, se queda abierta y la tarjeta pasa a `hecha` "Aplicado a la venta".
5. En la revisión: la fila se mueve de "Necesitan tu ayuda" a "Listos" si corresponde; el **foco del lector va a esa fila**; `Snackbar` "Caja cambió Galletas por Galletas María 170 g. [Deshacer]" (10 s, sin límite con lector; anuncio único vía prop `anuncio`). El total se recalcula en vivo.
6. Nada se guarda en el servidor: el cobro sigue requiriendo "Cobrar $88.00" (doble control).

### 4.4 "Caja no supo responder"

Si `no_resuelto` en la hoja, en vez de la card de §2.6:
`Aviso` tarjeta `info` (`surfaceContainerHigh`, `onSurface` 14.0:1, icono `information`): **"Caja no supo responder."** "Puedes buscar el producto a mano." · [magnify Buscar producto] (filled) → cierra la hoja y abre "Editar producto" sobre la **primera fila con problema** (o "Agregar producto" si no hay) con el buscador enfocado · [Preguntar de otra forma] (text) → enfoca el campo.

---

## 5. Contrato propuesto (front ↔ back)

Para `src/api/esquemas.ts` (y copiar a `back/`). Compatibilidad: `MensajeAsistente` solo **agrega** campos opcionales; `AccionAsistente.tipo` agrega `modificar_item`.

### 5.1 Solicitud — `POST /asistente/mensaje`

```ts
export const PantallaAsistente = z.enum(['asistente', 'revision_cobro', 'inicio', 'inventario', 'pago']);

export const NivelItem = z.enum(['alta', 'baja', 'falta', 'manual']); // = nivelDeItem() del front

export const ItemContexto = z.object({
  indice: z.number().int().nonnegative(),       // posición en carrito.items
  clave: z.string(),                            // id local estable de la fila
  numero_en_foto: z.number().int().positive().nullable(),
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_unitario: z.number().nonnegative().nullable(),
  existencia: z.number().int().nullable(),
  nivel: NivelItem,
  confianza: z.number().min(0).max(1),          // solo para el back; nunca se muestra
});
export type ItemContexto = z.infer<typeof ItemContexto>;

export const ContextoAsistente = z.discriminatedUnion('pantalla', [
  z.object({ pantalla: z.literal('asistente') }),
  z.object({ pantalla: z.literal('inicio') }),
  z.object({ pantalla: z.literal('inventario') }),
  z.object({ pantalla: z.literal('pago') }),     // el tutor usa /asistente/tutor con EstadoPantalla
  z.object({
    pantalla: z.literal('revision_cobro'),
    imagen_id: z.string().nullable(),
    total: z.number().nonnegative(),
    items: z.array(ItemContexto).max(50),
  }),
]);
export type ContextoAsistente = z.infer<typeof ContextoAsistente>;

export const TurnoHistorial = z.object({
  autor: z.enum(['tendero', 'asistente']),
  rol: RolAsistente.optional(),                 // solo si autor = asistente
  texto: z.string().max(2000),
});

export const SolicitudAsistente = z.object({
  id_mensaje: z.string(),                       // id del teléfono: un Reintentar no duplica la respuesta
  texto: z.string().trim().min(1).max(500),
  historial: z.array(TurnoHistorial).max(12),   // últimos 12 turnos, sin tarjetas
  contexto: ContextoAsistente.optional(),       // ausente = { pantalla: 'asistente' }
});
export type SolicitudAsistente = z.infer<typeof SolicitudAsistente>;
```

> Reemplaza la firma actual `enviarMensaje(texto, historial: MensajeAsistente[])`, que no incluía los mensajes del tendero. Nueva: `enviarMensaje(solicitud: SolicitudAsistente, opciones?: OpcionesPedido)`.

### 5.2 Respuesta — `MensajeAsistente` (extendido)

```ts
export const TipoAccion = z.enum([
  'confirmar_venta', 'confirmar_alta', 'aprobar_promo', 'abrir_pantalla',
  'modificar_item', // NUEVO: solo con contexto revision_cobro
]);

export const AccionAsistente = z.object({
  id: z.string(),
  tipo: TipoAccion,
  titulo: z.string(),                           // texto del botón/tarjeta, en lenguaje de tienda
  datos: z.unknown(),                           // se valida POR TIPO al mostrar (5.3)
  vence_en: z.string().datetime().optional(),   // NUEVO
});

export const MensajeAsistente = z.object({
  rol: RolAsistente,
  texto: z.string(),
  acciones: z.array(AccionAsistente).max(3).optional(),
  no_resuelto: z.boolean().optional(),
  sugerencias: z.array(z.string().max(60)).max(3).optional(), // NUEVO: chips de seguimiento
});
```

`datos` se mantiene `unknown` a nivel de mensaje **a propósito**: si una acción viene mal, se muestra el texto y esa tarjeta en estado "No pudimos leer esta propuesta", en vez de perder toda la respuesta.

### 5.3 `datos` por tipo (validar con `parsearDatosAccion(accion)`)

```ts
const ItemPropuesto = z.object({
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_unitario: z.number().nonnegative().nullable(), // null → tarjeta obliga a "Revisar y editar"
});

export const DatosConfirmarVenta = z.object({
  items: z.array(ItemPropuesto).min(1).max(50),
  metodo_pago: MetodoPago.optional(),           // default 'efectivo'
});

export const DatosConfirmarAlta = z.object({
  sku: z.string().nullable(),
  nombre: z.string(),
  cantidad: z.number().int().positive(),
  precio_venta: z.number().nonnegative().nullable(),
  caducidad: z.string().nullable(),             // 'AAAA-MM-DD'
});

export const DatosAprobarPromo = z.object({
  promo_id: z.string(),
  producto: z.string(),
  copy: z.string().max(280),
  precio_promo: z.number().nonnegative(),
  vigente_hasta: z.string(),                    // 'AAAA-MM-DD'
  video_url: z.string().url().nullable(),
  simulacion: z.boolean(),                      // true → chip "Simulación" obligatorio
});

export const DatosAbrirPantalla = z.object({
  pantalla: z.enum(['cobrar', 'camara_cobro', 'camara_alta', 'camara_ticket',
                    'inventario', 'historial', 'pago', 'promociones']),
});

export const DatosModificarItem = z.object({
  indice: z.number().int().nonnegative(),
  clave: z.string(),                            // debe coincidir con la fila actual
  nombre_actual: z.string(),                    // segunda verificación + texto "Antes"
  cambios: z.object({
    sku: z.string().nullable().optional(),
    nombre: z.string().optional(),
    precio_unitario: z.number().nonnegative().optional(),
    cantidad: z.number().int().positive().optional(),
  }).refine((c) => Object.keys(c).length > 0, 'sin cambios'),
});
```
Reglas: `modificar_item` fuera de `revision_cobro` → se ignora y se muestra solo el texto. Si `cambios.sku` llega, también deben llegar `nombre` y `precio_unitario` (si no, la tarjeta ofrece "Revisar y editar").

### 5.4 Errores y tiempo límite

| Caso | Cómo llega | Qué ve el tendero |
|---|---|---|
| No entendió / no puede | **200** con `no_resuelto: true` (no un error HTTP) | §2.6 / §4.4 |
| Texto vacío o > 500 | 400 (el front lo previene antes) | Error en línea del campo |
| Sin internet | `fetch` falla → `sin_conexion` | `en_espera` (pestaña) o `fallido` (hoja) |
| Tardó > **25 s** | `tiempoMs: 25_000` → `tiempo_agotado` | "Tardó mucho en contestar." [Reintentar]; aviso "tardando" a los 8 s |
| 5xx / 429 | `servidor` | "No pudimos traer la respuesta. Intenta de nuevo." [Reintentar] |
| JSON no pasa zod | `respuesta_invalida` | Igual que servidor |
| Detener | `cancelado` | "Detuviste la respuesta." [Reintentar] |
| Error al ejecutar la acción (`POST /ventas` 409, etc.) | Error del endpoint de negocio | Tarjeta `error` con mensaje de `cliente.ts` |

Reintentar reusa el **mismo** `id_mensaje` (el back devuelve la misma respuesta si ya la tenía). Mocks: `mockRespuestaAsistente(solicitud)` debe cubrir: métricas (Cuentas), stock bajo (Bodega), "vendí 2 cocas y un pan" (Caja + `confirmar_venta`), transferencia (Ayuda de pagos + `abrir_pantalla: pago`), revisión (Caja + `modificar_item` sobre la primera fila `falta`), `no_resuelto`, y escenario `EXPO_PUBLIC_MOCK_ASISTENTE=lento|error` para probar §2.3 y §2.2.

---

## 6. Accesibilidad

| Tema | Regla |
|---|---|
| Mensaje nuevo | Al llegar una respuesta (con la pantalla/hoja enfocada) se llama **una vez** `AccessibilityInfo.announceForAccessibility("{Rol} dice: {texto}")`; si trae tarjeta, se agrega ". Tiene una propuesta para confirmar." No se usa además live region en la lista (evita doble lectura). |
| Burbuja | Un solo elemento accesible por burbuja: `accessible`, label "Tú: {texto}. 10:42" o "Cuentas: {texto}. 10:42"; icono con `importantForAccessibility="no"`. Estados en el label: "No se envió, sin conexión" + acciones como botones separados. |
| Foco tras enviar | El foco **se queda en el campo** (teclado abierto para seguir) y se anuncia "Enviado. Tu asistente está escribiendo." El foco **no** salta a la respuesta (no se roba). Tocar una sugerencia: foco al campo. |
| Foco tras aplicar (hoja de Caja) | Al cerrar la hoja, foco a la fila modificada en la revisión; anuncio único del snackbar. |
| Orden de lectura | Top app bar → banners → mensajes en orden cronológico (lista no invertida) → sugerencias → campo → Enviar → navigation bar. |
| Letra grande | Todo envuelve; burbujas a ancho completo con cabecera "Tú" desde 1.3×; campo máx. 3 líneas; Enviar debajo del campo a ancho completo; chips apilados. Sin `numberOfLines` en mensajes. |
| Una mano | Campo, Enviar, sugerencias y botones de las tarjetas en el tercio inferior. "Borrar chat" arriba (raro y destructivo). |
| Teclado | Navigation bar oculta con teclado; compositor siempre visible sobre el teclado; la lista se ajusta y el último mensaje sigue visible. |
| Táctiles | Chips, botones y acciones de burbuja ≥ 48 dp, separación ≥ 8. Enviar 56. |
| Movimiento | Sin animación de puntos con movimiento reducido; scroll sin animar; hoja aparece directo. |
| Color | Rol = icono + nombre; estado = icono + texto; nunca solo color. |
| Lector activo | Snackbars sin tiempo límite; tarjetas sin caducidad por tiempo mientras el lector esté activo **y** la pantalla abierta (solo caducan por cambio de datos). |

**Contraste de los pares nuevos** (todos desde 00-sistema §2.3):

| Primer plano | Fondo | Contraste | Dónde |
|---|---|---|---|
| `onPrimaryContainer #284777` | `primaryContainer #D6E3FF` | **7.24:1** AAA | Burbuja del tendero |
| `onSurface #191C20` | `surfaceContainerHigh #E7E8EE` | **14.0:1** AAA | Burbuja del asistente |
| `onSurfaceVariant #44474E` | `surfaceContainerHigh` | **7.63:1** AAA | "Escribiendo…", puntos |
| `onSurfaceVariant` | `surface #F9F9FF` | **8.89:1** AAA | Hora, icono de rol, separador de día, "en espera" |
| `onSurface` | `surface` | **16.3:1** AAA | Nombre del rol |
| `error #BA1A1A` | `surface` | **6.15:1** AA | "No se envió…" |
| `primary #415F91` | `surface` | **6.15:1** AA | [Reintentar] text |
| `outline #74777F` | `surface` / `surfaceContainerLow` | **4.27 / 4.06:1** (≥ 3) | Borde de suggestion chip (`EXC-10`), card de `no_resuelto` |
| `onSurfaceVariant` | `surfaceContainerLow #F3F3FA` | **8.46:1** AAA | "Caja ve tu venta…", chips dentro de la hoja |
| `onSurface` | `surfaceContainerLowest #FFFFFF` | **17.1:1** AAA | Texto del campo |
| `onSurfaceVariant` | `surfaceContainerLowest` | **9.34:1** AAA | Placeholder |
| `outline` | `surfaceContainerLowest` | **4.48:1** (≥ 3) | Borde del campo |
| `onPrimary #FFFFFF` | `primary` | **6.46:1** AA | Enviar, Confirmar |
| `onSecondaryContainer #3E4759` | `secondaryContainer #DAE2F9` | **7.24:1** AAA | Detener, "Mensaje nuevo", botones abrir_pantalla |
| `success #006D43` | `surfaceContainerLow` | **5.85:1** AA | Check de tarjeta `hecha` |
| `inverseOnSurface` / `inversePrimary` | `inverseSurface #2E3036` | **11.59 / 7.72:1** | Snackbars |

---

## 7. Especificaciones UI (tokens)

| Elemento | Token / valor |
|---|---|
| Fondo pantalla | `surface #F9F9FF` |
| Top app bar | 64 dp, `surface` → `surfaceContainer` al desplazar, título `titleLarge` 22 |
| Burbujas | ver §2.2 · shape `large` 16 + esquina `extraSmall` 4 · padding 16/12 · elevación 0 |
| Cabecera de rol | icono 24 + `titleSmall` 16/500, gap 8, margen inferior 4 |
| Suggestion chip | alto **48** (`EXC-2`; M3 = 32), shape `small` 8, borde 1 dp `outline` (`EXC-10`), padding 16 (12 con icono), icono 20 `primary` (`iconos.chico`), texto `labelLarge` 16/500 `onSurfaceVariant`; presionado capa 10 % `onSurfaceVariant`; `accessibilityRole="button"` |
| Compositor | `surfaceContainer #EDEDF4`, divisor 1 dp `outlineVariant`, padding 8/16, campo 56 mín., Enviar 56 |
| TarjetaAccion | `surfaceContainerLow`, shape `medium` 12, level1 (0 cuando no es accionable), padding 16, gap 12 |
| Card `no_resuelto` | outlined, borde 1 dp `outline`, shape `medium`, fondo `surface`, padding 16 |
| Hoja de Caja | `HojaInferior` modal, `surfaceContainerLow`, esquinas sup. 28, level1, scrim 32 %, alto 90 % |
| Espaciado | margen lateral 16 · entre burbujas 8 / 16 · entre tarjeta y burbuja 8 · entre bloques 24 |
| Iconos | 24 (rol, botones), 20 (estado de burbuja), 48 (estado vacío) |
| Movimiento | Burbuja nueva: fade 200 ms `standard` (0 con movimiento reducido); hoja `medium4` `emphasizedDecelerate` |
| Tiempos | "tardando" 8 s · límite 25 s · caducidad 30 min · snackbar 10 s |

---

## 8. Justificación HCI / Nielsen

| # | Heurística | Aplicación |
|---|---|---|
| 1 | Visibilidad del estado | "Escribiendo…" con texto, "tardando" a los 8 s, burbujas `en_espera`/`fallido`, banner sin conexión, "Caja ve tu venta: 4 productos" (qué se comparte), tarjeta que baja de elevación al resolverse, "Mensaje nuevo" si estás leyendo arriba |
| 2 | Mundo real | Oficios de tienda (Caja, Bodega, Cuentas), "Cobrar", "pz", "Pregúntale a Caja", ejemplos como "2 refrescos y un pan"; nunca "agente", "modelo", "IA", "SKU" |
| 3 | Control y libertad | "No, gracias" en cada propuesta, Detener, Cancelar envío, Deshacer al aplicar cambios de Caja y al borrar el chat, Cerrar visible en la hoja |
| 4 | Consistencia | Mismos `TarjetaAccion`, `HojaInferior`, `Snackbar`, `Dialogo`, `Aviso` que en Cobrar; un solo filled por tarjeta; bottom sheet como en Editar producto |
| 5 | Prevención de errores | Nada se ejecuta sin tocar Confirmar; validación de `clave`/`nombre_actual` antes de aplicar; sin cobro con datos incompletos; `id_local`/`id_mensaje` contra duplicados; solo 1 pregunta en cola; Dialog antes de borrar |
| 6 | Reconocer > recordar | Sugerencias tocables, lista "Te contestan", seguimiento sugerido por respuesta, historial guardado |
| 7 | Flexibilidad | Chips que envían directo para novatos; escribir o dictar para expertos; "vendí 2 cocas y un pan" como atajo al cobro sin foto |
| 8 | Minimalista | Sin colores por rol, sin bordes en burbujas, sin avatares ni ilustraciones; elevación solo en tarjetas accionables |
| 9 | Recuperación de errores | Cada falla con motivo humano + [Reintentar]; `no_resuelto` con salidas directas (Cobrar con foto, Inventario, Buscar producto, soporte) |
| 10 | Ayuda | El asistente **es** la ayuda contextual; Ayuda de pagos enlaza a la práctica del cobro digital; contacto por WhatsApp |

**Bases del hackathon cubiertas:** asistente conversacional integrado al recorrido principal (hoja de Caja en la revisión), sugerencias rápidas, estado "escribiendo…", paso de lo entendido a un formulario ("Revisar y editar" → `revision/cobro`), revisión obligatoria antes de guardar, errores visibles (sin conexión, no resuelto, tiempo, datos ilegibles), lo simulado etiquetado ("Simulación").

---

## 9. Componentes y archivos

### 9.1 Componentes

| Componente | Estado | Archivo | Notas |
|---|---|---|---|
| `TarjetaAccion` | Reutilizado | `src/components/tarjeta-accion.tsx` | Agregar props `textoCargando?`, `motivoCaducada?`, `textoResultado?` (hoy dice fijo "Confirmando…"/"Listo"/"Ver comprobante") y `soloRevisar?` (sin botón Confirmar cuando faltan datos) |
| `HojaInferior` | Reutilizado + prop | `src/components/hoja-inferior.tsx` | Nueva `sinScroll?: boolean` |
| `Aviso`, `Snackbar`, `Dialogo`, `Boton`, `Campo`, `Encabezado`, `EtiquetaSimulacion`, `AvisoConexion`, `IndicadorConfianza` | Reutilizados | `src/components/*` | `Campo`: soportar `multiline` + `maxLength` (si no lo tiene) |
| `ChipSugerencia` | **Nuevo** | `src/components/chip-sugerencia.tsx` | Suggestion chip M3 (§7), `role="button"` (no reutilizar `ChipFiltro`, que es `checkbox`) |
| `BurbujaMensaje` | **Nuevo** | `src/screens/asistente/burbuja-mensaje.tsx` | Tendero/asistente, cabecera de rol, estados |
| `IndicadorEscribiendo` | **Nuevo** | `src/screens/asistente/indicador-escribiendo.tsx` | Puntos + texto, "tardando" |
| `Compositor` | **Nuevo** | `src/screens/asistente/compositor.tsx` | Campo + Enviar/Detener, contador, error en línea |
| `ListaMensajes` | **Nuevo** | `src/screens/asistente/lista-mensajes.tsx` | FlatList no invertida, separadores de día, "Mensaje nuevo" |
| `EstadoVacioChat` | **Nuevo** | `src/screens/asistente/estado-vacio.tsx` | §2.4 (prop `variante: 'pestana' | 'caja'`) |
| `TarjetaPropuesta` | **Nuevo** | `src/screens/asistente/tarjeta-propuesta.tsx` | Adaptador `AccionAsistente` → `TarjetaAccion` / botón `abrir_pantalla` |
| `AlternativasNoResuelto` | **Nuevo** | `src/screens/asistente/alternativas-no-resuelto.tsx` | §2.6 |
| `HojaCaja` | **Nuevo** | `src/screens/revision/hoja-caja.tsx` | §4; reusa Lista/Compositor/TarjetaPropuesta |

### 9.2 Archivos

| Ruta | Contenido |
|---|---|
| `src/app/(tabs)/asistente.tsx` | Solo ruta → `<PantallaAsistente />` |
| `src/app/(tabs)/_layout.tsx` | `tabBarHideOnKeyboard: true` |
| `src/screens/asistente.tsx` | Pantalla: encabezado, banners, lista, sugerencias, compositor, Dialog de borrar, Snackbar |
| `src/screens/asistente/*.tsx` | Subcomponentes de §9.1 |
| `src/screens/revision/hoja-caja.tsx` + `src/screens/revision-cobro.tsx` | Hoja + integración (abrir, aplicar, foco a la fila, snackbar) |
| `src/api/esquemas.ts` | §5 (contexto, solicitud, acciones extendidas, datos por tipo) |
| `src/api/asistente.ts` | `enviarMensaje(solicitud, opciones)` con `tiempoMs: 25_000`; `reportarResultadoAccion` (opcional) |
| `src/api/acciones-asistente.ts` | `parsearDatosAccion`, `ejecutarAccion` (llama a `negocio.ts`, nunca antes de confirmar) |
| `src/api/mocks/index.ts` | Respuestas sintéticas de §5.4 (marcadas MOCK) |
| `src/estado/chat.ts` | Tipos `MensajeChat`, reducer, persistencia `asistente-chat-v1` (100 msgs), caducidad al cargar |
| `src/hooks/use-chat.ts` | Enviar, detener, reintentar, cola de 1 mensaje, anuncios; parámetro `contexto` (pestaña u hoja de Caja) |
| `src/utils/contexto-cobro.ts` | `aContextoCobro(carrito)`, `validarModificacion(item, datos)`, `aplicarModificacion` |
| `src/utils/texto-chat.ts` | `limpiarFormato`, `separadorDeDia` |
| `src/constants.ts` | `ROLES.general.nombre = 'Tu asistente'`; `SUGERENCIAS_INICIO`, `SUGERENCIAS_CAJA`; textos de "Te contestan" |
| `.env.example` | `EXPO_PUBLIC_SOPORTE_WHATSAPP=` (vacío), `EXPO_PUBLIC_MOCK_ASISTENTE=ok` |

Modelo local sugerido (no se envía tal cual al back):
```ts
type EstadoEnvio = 'enviando' | 'enviado' | 'en_espera' | 'fallido';
type MensajeChat =
  | { id: string; autor: 'tendero'; texto: string; creado_en: string; estado: EstadoEnvio; error?: TipoError }
  | { id: string; autor: 'asistente'; rol: RolAsistente; texto: string; creado_en: string;
      no_resuelto?: boolean; sugerencias?: string[];
      acciones?: (AccionAsistente & { estado: EstadoTarjeta; resultado?: string; motivo?: string })[] };
```

**Listo cuando:** desde la pestaña se pregunta "¿Cuánto vendí hoy?" y "vendí 2 cocas y un pan" → tarjeta → Confirmar → venta en Historial; desde la revisión, Caja corrige la fila "falta" con "Aplicar a la venta" + Deshacer; los estados de §2.9 se ven con mocks; lint + tsc pasan; probado con letra grande, TalkBack y sin internet.
