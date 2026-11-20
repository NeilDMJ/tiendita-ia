# Cambios y resultados (registro vivo)

> Rama local `ui/rediseno`, sin push. Capturas antes: `capturas/antes/` · después: `capturas/despues/` (web, ventana ancha; **no** probado en móvil real).

## Commits

| Fase | Commit | Resumen |
|---|---|---|
| 0–1 | `10b8e92`, `5e3a3ee` | Descubrimiento, capturas y auditoría |
| 1b | `1c5ed6d` | Mover `inicio`/`inventario` a `screens/` (rutas duplicadas), lint limpio |
| 1b | `53f052c` | Asistente tolera roles desconocidos del chat guardado |
| 2 | `9dc2793` | Tokens de la identidad nueva (paleta, Inter, radios, sombras) |
| 3 | `a374826` | Componentes alineados + `Marca` + `ContenedorPantalla` |
| 4 | ver `git log` | Cobrar, Inicio, Inventario, Asistente |

## Fase 4 — pantallas

| Pantalla | Problema (auditoría) | Cambio |
|---|---|---|
| **Cobrar** | #5: la tarea principal no era protagonista; poco contenido | Tarjeta central "Cobra con una foto" (icono, 3 pasos numerados) y botón **Cobrar con foto** anclado abajo, ancho completo y alcance del pulgar. Se quita el FAB. Atajos con icono en recuadro azul suave |
| **Inicio** | #4: título duplicado, sin acción principal clara, asistente compitiendo | Cabecera nativa oculta (el saludo es el título, ahora `headlineLarge`); **Cobrar con foto** es el único botón relleno; "Pregúntale al Asistente IA" pasa a tarjeta azul suave |
| **Inventario** | #7 + título duplicado + doble hueco superior | Título único; búsqueda y filtros **fijos** al hacer scroll; cifras del resumen a 24 sp |
| **Asistente** | título duplicado, banner negro pesado | Cabecera nativa oculta + área segura; banner de simulación en ámbar suave (sigue siempre visible: es requisito marcar lo simulado) |
| Historial / Cámara (permiso) | — | Sin cambios de diseño; verificados con los tokens nuevos |
| **Revisión del cobro** | Contenido a todo el ancho en web | `ContenedorPantalla` (640 dp). Sin otros cambios: ya tenía jerarquía clara (progreso por pasos, "Todo listo", total y botón único abajo) |
| Hoja de cobro / Comprobante | — | Verificados con los tokens: etiqueta SIMULACIÓN en ámbar, "Venta registrada" en verde, un solo botón principal "Nueva venta con foto" |

### Fix encontrado al recorrer el flujo

`findNodeHandle` (para mover el foco del lector de pantalla) lanza error en web y rompía hojas, diálogos y avisos. Se centralizó en `utils/foco-lector.ts`: en web no hace nada, en móvil se comporta igual. Afectaba a `aviso`, `dialogo`, `hoja-inferior`, `hoja-caja`, `pantalla-asistente` y `revision-cobro`.

## Verificación hasta ahora

| Chequeo | Resultado |
|---|---|
| `tsc --noEmit` | ✅ |
| `expo lint` | ✅ |
| Hex/rgb y `fontWeight` fuera de `theme.ts` | ✅ ninguno |
| Flujo de cobro completo en web con datos simulados (Cobrar → Buscar producto → revisión → hoja de cobro → comprobante → Inicio) | ✅ funciona; Inicio muestra 1 venta, $18.00, 100 % efectivo |
| Flujo por **cámara** (foto → detección IA) | ⚠️ no ejecutado: la web no puede tomar la foto ni elegir un archivo desde aquí |
| Móvil 360 px, Android/iOS reales | ⚠️ **no probados** |
| Teclado/foco, lector de pantalla, modo reducir movimiento | ⚠️ no verificados |
| Modo oscuro | ✅ web: Inicio, Cobrar, Inventario, Asistente, hoja de agregar, selector. ⚠️ Cámara, comprobante, historial y diálogos en oscuro **no revisados**; móvil real no probado |

## Pendiente

- Cámara activa y detección con foto (probar en teléfono). Estados de error del cobro (mock `EXPO_PUBLIC_MOCK_VISION=ilegible|vacio|lento`).
- Observaciones sin tocar: el botón "Caja" arriba a la derecha en Revisión es poco claro (¿"Pregúntale a Caja"?); la pista de la barra de pasos es muy tenue.
- Estados vacío/carga/error de Inventario e Inicio con datos reales.
- Onboarding, microinteracciones, modo oscuro (Fase 5).
- Probar en teléfono con Expo Go.

## Fase 5 — modo oscuro

> Corrección posterior (`cb2326f`): el selector se quedaba en "Reiniciando…" en Expo Go porque `reloadAppAsync` no recarga ahí. Ahora usa `DevSettings.reload()` en desarrollo y, si el reinicio no ocurre en 2.5 s, avisa que hay que reabrir la app. Confirmado funcionando por el usuario en el teléfono.
| Cambio | Detalle |
|---|---|
| Esquema decidido al abrir la app | `theme.ts`: preferencia guardada → o la del teléfono. Sin tocar los 60+ archivos que usan `color` |
| Selector "Apariencia" | Botón de icono en Inicio → hoja *Igual que el teléfono / Claro / Oscuro* → reinicia la app |
| Cámara y fotos | Colores fijos oscuros (no invierten) |
| Contraste | Paleta oscura verificada: 0 fallos AA; tarjetas ajustadas para quedar sobre el fondo |
| `app.json` | `userInterfaceStyle: automatic` |

Capturas: `capturas/despues/11…16-oscuro-*.jpg`.

---

# Cierre (Fase 6)

## Último cambio pedido

- **Soporte por WhatsApp eliminado** del módulo Asistente: se quitó el botón "Escribir a soporte" de la tarjeta "No pude resolverlo", la constante `SOPORTE_WHATSAPP` y la variable `EXPO_PUBLIC_SOPORTE_WHATSAPP` (`.env.example` y `.env`). La tarjeta conserva las 3 salidas dentro de la app. Se actualizó `front/docs/diseno/02-asistente.md`.

## Checklist de la auditoría

| # | Problema | Estado |
|---|---|---|
| 1 | Asistente se caía | ✅ Resuelto (causa: chat guardado con rol `banco` de otra rama) |
| 2 | Rutas duplicadas `inicio`/`inventario` | ✅ Resuelto |
| 3 | Jerarquía tipográfica débil | ✅ Escala con saltos reales (16 · 18 · 20 · 22 · 24 · 32 · 40); mínimo 16 sp se conserva por accesibilidad |
| 4 | Inicio: título duplicado, sin acción principal | ✅ Resuelto |
| 5 | Cobrar: tarea principal sin protagonismo | ✅ Resuelto |
| 6 | Sin ancho máximo en web/tablet | ✅ `ContenedorPantalla` (640 dp) |
| 7 | Inventario: cifras pequeñas, búsqueda se perdía al bajar | ✅ Resuelto |
| 8 | Sin modo oscuro | ✅ Implementado; verificado en web y **confirmado en el teléfono (Expo Go)** por el usuario |
| 9 | Tema no refleja la marca | ✅ Identidad nueva en `theme.ts` |
| 10 | Lint con errores | ✅ 0 errores, 0 avisos |

## Verificación final

| Chequeo | Resultado |
|---|---|
| `tsc --noEmit` | ✅ |
| `expo lint` | ✅ 0 errores, 0 avisos |
| Colores (hex/rgb) fuera de `theme.ts` | ✅ ninguno (una coincidencia es un comentario) |
| `fontWeight` / `fontSize` sueltos | ✅ ninguno |
| Contraste WCAG AA, claro y oscuro | ✅ 0 fallos (`node docs/ui-ux/contraste.mjs`) |
| Flujo de cobro completo (web, datos simulados) | ✅ |
| App en teléfono real (Expo Go) | ✅ según el usuario: "la app ya agarra bien el teléfono" |
| Modo oscuro en teléfono (Expo Go) | ✅ confirmado por el usuario tras corregir el bloqueo en "Reiniciando…" (`cb2326f`) |
| Flujo con cámara real | ⚠️ no verificado por mí (web no puede tomar foto) |
| Cámara, comprobante, historial y diálogos en oscuro | ⚠️ no revisados |
| Móvil 360 px, lector de pantalla, movimiento reducido | ⚠️ no verificados |
| Pruebas automáticas | — el proyecto no tiene tests |

## Pendiente conocido

1. **Modo oscuro: lo que sigue sin confirmar.** Funciona en Expo Go. No se ha verificado (a) si el reinicio automático recarga solo o hay que reabrir la app a mano, (b) una compilación de producción (`reloadAppAsync`), ni (c) la cámara, el comprobante, el historial y los diálogos en oscuro.
2. Cambio de modo del sistema con la app abierta no se refleja hasta reabrirla (limitación de diseño, ver `02-sistema-de-diseno.md`).
3. Sin hacer: onboarding, microinteracciones, estados vacíos con ilustración.
4. Observaciones sin tocar: botón "Caja" en Revisión poco claro; pista de la barra de pasos tenue.
5. Rama `ui/rediseno` **solo local**: no se ha hecho `push` ni Pull Request.

## Recomendaciones futuras

- Mover los estilos a una fábrica con contexto de tema para que el modo oscuro cambie en caliente.
- Tests de componentes (Jest) y de contraste automatizados en CI.
- Revisar con tenderos reales el botón de enviar solo con ícono y el tamaño mínimo de 16 sp.
