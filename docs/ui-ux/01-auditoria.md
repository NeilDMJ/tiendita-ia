# Fase 1 — Auditoría (Tendero IA)

> Base: rama `ui/rediseno` (fusión de las 4 `feature/front-*`, sin conflictos). Evidencia: `capturas/antes/` + lectura de código.
> Alcance de esta pasada: **web, 1434 px de ancho**, Inicio, Cobrar, Inventario y Asistente. **No auditado aún** por falta de verificación en ejecución: cámara, revisión, comprobante, historial, estados de error/carga y móvil a 360 px. Se auditarán en la Fase 4 al tocar cada pantalla.

## Estado técnico de la integración

| Chequeo | Resultado |
|---|---|
| `tsc --noEmit` | ✅ sin errores |
| `expo lint` | ⚠️ 2 errores + 1 aviso (comillas sin escapar en `inventario/lista-productos.tsx:46`; import sin usar en `inicio/tipos.ts`) |
| Arranca en web | ✅ |
| Pestaña Asistente | ❌ **se cae** al abrir (ver P1-1) |

## Identidad nueva: qué se aplica y qué no

El documento pegado es de **BookEase** (landing de reservas). Propongo tomar de él: paleta azul `#1A56DB` + violeta `#5B3FD6`, neutros, semánticos, tipografía sans geométrica (Inter), radios 6/10/16/full, sombras suaves, tono cercano y de interfaz en español. **No aplica:** logo cursivo, calendario, hero, buscador de reservas.

Conflictos que necesito que decidas (ver final):
- **Gradiente:** el sistema actual lo prohíbe y en React Native requiere `expo-linear-gradient` (dependencia nueva).
- **Inter:** requiere `expo-font` + `@expo-google-fonts/inter` (el repo ya trae `expo-font`; falta el paquete de la fuente).
- **Contraste:** `#6B7280` sobre `#F5F7FB` da ≈4.6:1 (pasa justo); `#4B5563` pasa. Se verificará cada par en la Fase 2.
- **Material 3:** la identidad nueva no es M3. Mantendría la **estructura** (roles de color, estados, tokens, reglas de accesibilidad) y cambiaría **valores y forma**, no el sistema.
- **Tamaños:** la guía usa px de web; en la app los tamaños mínimos de 16 sp (EXC-1) se conservan.

## Los 10 problemas más importantes

| # | Pantalla | Problema | Por qué afecta | Gravedad | Esfuerzo | Propuesta |
|---|---|---|---|---|---|---|
| 1 | Asistente | Se cae con `Cannot read properties of undefined (reading 'nombre')` en `BurbujaMensaje` (`burbuja-mensaje.tsx:52`, `ROLES[mensaje.rol]`). Un mensaje guardado llega sin `rol`. Los mocks y los tipos están bien: sospecho de un chat persistido en SQLite del navegador, sin comprobar. | Pestaña principal inutilizable; una pantalla en blanco sin forma de recuperarse | **Alta** | Bajo | Tolerar `rol` ausente (fallback a `general`) y validar con zod al leer el chat guardado. **Toca lógica de lectura → necesito tu OK.** |
| 2 | Inventario / Inicio | Carpetas `app/inventario/` y `app/inicio/` crean **rutas duplicadas**. `/inventario` abre otra pantalla, sin barra de pestañas y con título crudo "inventario/index" | Navegación inconsistente, texto técnico visible, usuario sin salida | **Alta** | Bajo | Mover esos archivos a `src/screens/` (como el resto). Solo reubicación |
| 3 | Todas | Jerarquía tipográfica débil: 6 estilos distintos miden 16/24 (`bodyMedium`, `bodySmall`, `labelLarge/Medium/Small`…), todo se distingue solo por peso | Todo "pesa" parecido; cuesta ver lo importante en 3 segundos | Alta | Medio | Nueva escala con saltos reales (16/20/24/32, caption 14 con excepción documentada si el diseño la necesita) |
| 4 | Inicio | Encabezado "Inicio" duplica el saludo "¡Buenos días!"; tarjeta "Reporte de ventas de hoy" con tarjetas dentro de tarjetas; el CTA azul oscuro "Pregúntale al Asistente IA" compite con el resto | Densidad y ruido; no hay una acción principal obvia (cobrar) | Alta | Medio | Quitar el título duplicado, aplanar el reporte y hacer de "Cobrar" la acción principal del día |
| 5 | Cobrar | Pantalla casi vacía: bloque gris "Cobra en 3 pasos" + tarjeta de búsqueda; el botón principal "Cobrar con foto" flota abajo a la derecha y tapa contenido | La tarea #1 no es el protagonista | Alta | Medio | Botón primario grande y visible (zona del pulgar), pasos como ayuda secundaria |
| 6 | Todas | No hay layout responsive: en 1434 px el contenido se estira a todo el ancho (tarjetas de 1380 px) | Ilegible en tablet/web | Media | Bajo | Contenedor con ancho máximo (~640 dp) centrado |
| 7 | Inventario | Resumen con 4 datos en 2 líneas muy pequeñas; el chip de filtro activo se distingue por una palomita y un fondo suave | Datos clave poco legibles | Media | Bajo | Mejor jerarquía numérica; filtros más claros |
| 8 | Todas | Sin modo oscuro y sin jerarquía semántica de color (todo azul grisáceo M3) | Poco carácter; riesgo de deslumbramiento en tienda | Media | Medio | Tokens oscuros en Fase 2 si lo aprueban |
| 9 | Sistema | `theme.ts` sigue el esquema M3 `TonalSpot` con semilla `#769CDF`; no refleja la marca nueva | Identidad inexistente | Alta | Medio | Fase 2: nuevos valores de color, radios y sombras |
| 10 | Código | Lint con 2 errores; `camara.tsx` (766 líneas) y `revision-cobro.tsx` (629) concentran demasiado | Cambios de UI arriesgados | Baja | Medio | Corregir lint ya; dividir solo si se toca |

## Matriz de prioridad

- **P1 — Hacer ya (alto impacto, poco esfuerzo):** #2, #6, #7, #10 (lint) y #1 (con tu OK).
- **P2 — Planificar (alto impacto, esfuerzo alto):** #3, #4, #5, #9 (se resuelven con las Fases 2–4).
- **P3 — Si hay tiempo:** #8 (modo oscuro).
- **Descartar:** dividir `camara.tsx` por completo, a menos que haga falta.

## Pendiente de auditar (no inventar resultados)

Estados vacío/carga/error/éxito, accesibilidad con teclado y foco, `prefers-reduced-motion`, contraste de cada par con los nuevos colores, cámara, revisión, comprobante, historial y móvil a 360 px. Se auditarán al tocar cada pantalla.

## Plan propuesto (si apruebas)

1. **Fase 1b — arreglos sin riesgo:** #2 (mover carpetas), #10 (lint), #6 (ancho máximo). Un commit por cambio.
2. **Fase 2 — tokens de la nueva identidad** en `theme.ts` + `docs/ui-ux/02-sistema-de-diseno.md`, con tabla de contrastes verificada.
3. **Fase 3 — componentes base** (botón, tarjeta, campo, chips, barra de navegación).
4. **Fase 4 — pantallas:** Inicio → Cobrar → Inventario → Asistente.
5. **Fase 6 — verificación** y capturas "después".
