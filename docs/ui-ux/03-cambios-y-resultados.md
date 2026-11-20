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
| Modo oscuro | ❌ tokens listos, no conectado |

## Pendiente

- Cámara activa y detección con foto (probar en teléfono). Estados de error del cobro (mock `EXPO_PUBLIC_MOCK_VISION=ilegible|vacio|lento`).
- Observaciones sin tocar: el botón "Caja" arriba a la derecha en Revisión es poco claro (¿"Pregúntale a Caja"?); la pista de la barra de pasos es muy tenue.
- Estados vacío/carga/error de Inventario e Inicio con datos reales.
- Onboarding, microinteracciones, modo oscuro (Fase 5).
- Probar en teléfono con Expo Go.
