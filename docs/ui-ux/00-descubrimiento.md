# Fase 0 — Descubrimiento: Tendero IA (`tiendita-ia`)

> Solo lectura. No se modificó código. Fuente: las 4 ramas `feature/front-*` clonadas en `Hack_nvi/front-*`.
> Lo marcado como **(suposición)** está inferido, no confirmado.

## 0.1 Stack y estructura

| Tema | Hallazgo |
|---|---|
| Tipo de app | Móvil multiplataforma (Expo / React Native) con salida web (`react-native-web`). Pensada para Expo Go en teléfono físico. |
| Framework | Expo SDK 58, React Native 0.88, React 19.3, TypeScript 6, Expo Router (rutas por archivos). |
| Estado/datos | `@tanstack/react-query`, contexto de carrito, cola offline en `expo-sqlite`, validación con `zod`. Modo mock con `EXPO_PUBLIC_USE_MOCKS=1`. |
| Estilos | `StyleSheet` + **`src/theme.ts`** (tokens Material Design 3). Sin Paper, NativeWind ni librería de UI: componentes propios. |
| Iconos | `@expo/vector-icons` (MaterialCommunityIcons), siempre con etiqueta de texto. |
| Ejecución | `cd front && npm install && npx expo start` (`npm run web` / `android` / `ios`). Checks: `npm run lint`, `npm run typecheck`. No hay tests unitarios configurados. |
| README | Es el de la plantilla de Expo (no describe el proyecto). Lo real está en `front/docs/`. |
| Agentes del repo | `.claude/agents/`: `ui-ux-movil`, `frontend-implementador`, `revisor-ui-m3`, `revisor-accesibilidad-hci`. |

Estructura relevante (`front/`):
```
src/app/        rutas: (tabs)/{index,cobrar,inventario,asistente}, camara, historial, revision/[modo], venta/[id]
src/screens/    cuerpo de pantallas: cobrar, camara, revision-cobro, comprobante, historial, (asistente/)
src/components/ 21 componentes base (boton, campo, tarjeta-accion, hoja-inferior, dialogo, snackbar, aviso, ...)
src/api/        cliente, vision, asistente, negocio, pagos, esquemas (zod), mocks/
src/estado/ hooks/ utils/   carrito, cola de ventas, chat, conexión, accesibilidad, letra grande
src/theme.ts    ÚNICA fuente de color, tipografía, forma, elevación, espacio, movimiento
docs/diseno/    00-sistema.md (659 líneas), 01-cobrar.md, 02-asistente.md, m3/ (generador de esquema)
```

## 0.2 Propósito y usuarios

- **Qué hace:** app para el dueño de una tiendita de abarrotes (hackathon NVIDIA Oaxaca 2026, "digitalización de procesos de negocio"). Cobra con foto del mostrador (visión por IA detecta productos), da de alta inventario, lee tickets y tiene un asistente conversacional con "oficios" (Caja, Bodega, Cuentas, Promociones, Ayuda de pagos).
- **Quién la usa (según docs, no suposición):** el tendero/dueño, atendiendo con una mano, posiblemente baja visión y poca práctica con apps.
- **Tareas principales:**
  1. Cobrar una venta con foto → revisar → confirmar.
  2. Ver cómo va el día (ventas, corte de caja, alertas de stock/caducidad).
  3. Consultar y buscar inventario.
  4. Preguntar al asistente y confirmar sus propuestas.
  5. Registrar ventas sin conexión (cola local que se sincroniza).

## 0.3 Inventario de pantallas y flujos

**Hallazgo clave: las 4 ramas divergen.** Todas parten de `a254a9a` (migración a M3). Cada una añade su pantalla y ninguna contiene las demás:

| Rama | Aporta sobre la base | Estado de su pestaña |
|---|---|---|
| `front-cobrar` | Base: cobrar, cámara, revisión, comprobante, historial | Completa; asistente/inventario/inicio son `pantalla-pendiente` |
| `front-asistente` | + chat, tarjetas de propuesta, hoja de caja en revisión, `estado/chat`, `api/acciones-asistente` | Completa |
| `front-inicio` | + `src/app/inicio/*` (saludo, corte de caja, alertas, atajos, gráficas) | Completa |
| `front-inventario` | + inicio (1er commit) + `src/app/inventario/*` (búsqueda, filtros, resumen, lista) | Completa |

Para rediseñar hay que **integrarlas en una sola base** (ver decisiones al final).

| Pantalla / ruta | Archivo | Propósito | Componentes principales | Acciones |
|---|---|---|---|---|
| Inicio `(tabs)/index` | `app/inicio/index.tsx` (+ `corte-caja`, `alertas-dia`, `atajos-camara`, `tarjeta-atajo`) | Saludo, métricas del día, alertas | TarjetaAtajo, CorteCaja, AlertasDia, Dialogo | Ir a cobrar/cámara, ver alertas, retomar venta en curso |
| Cobrar `(tabs)/cobrar` | `screens/cobrar.tsx` | Punto de entrada de la venta | Extended FAB, tarjetas, FilaVenta | "Cobrar con foto", venta manual, ver historial |
| Inventario `(tabs)/inventario` | `app/inventario/*` | Consultar stock | BarraBusqueda, Filtros, Resumen, FilaInventario | Buscar, filtrar, ver existencias |
| Asistente `(tabs)/asistente` | `screens/asistente/*` | Chat con oficios | Burbuja, Compositor, TarjetaPropuesta, Chips | Preguntar, confirmar/editar propuesta |
| Cámara `camara` (modal) | `screens/camara.tsx` (766 líneas) | Capturar foto (modos cobro/alta/ticket) | Barras `inverseSurface`, obturador, guía de encuadre | Tomar foto, galería, cancelar |
| Revisión `revision/[modo]` | `screens/revision-cobro.tsx` (629 l.) + `revision/*` | Corregir lo que detectó la IA | FilaProducto, StepperCantidad, HojaCobro, Indicador de confianza | Editar cantidades, resolver dudas, cobrar |
| Comprobante `venta/[id]` | `screens/comprobante.tsx` | Cierre de venta | Card éxito, filas | Nueva venta, ver historial |
| Historial `historial` | `screens/historial.tsx` | Ventas guardadas | FilaVenta | Abrir venta |

**Flujo principal:** Inicio/Cobrar → Cámara (guiada) → "Analizando foto…" → Revisión (problemas arriba, `+/−`, preguntar a Caja) → bottom sheet "Cobrar $X" (efectivo/digital) → Comprobante (stock descontado) → visible en Inicio/Historial. Sin conexión: se guarda en cola y se envía al reconectar (banner global).

**Pendientes según el plan, no implementados en ninguna rama:** `pago/index` (tutor de pago digital), `promociones`, alta de inventario con foto y OCR de tickets (el modo existe en cámara/revisión; falta confirmar el flujo completo).

## 0.4 Inventario visual actual

Esto es **mejor de lo habitual**: ya existe un sistema M3 formal.

- **Colores:** `theme.ts` define los roles M3 (esquema `TonalSpot`, semilla `#769CDF`, primario `#415F91`) + rol personalizado `success`. **Cero hex/rgb fuera de `theme.ts`** (grep sobre `src/`: sin resultados). Solo modo claro; **no hay modo oscuro**.
- **Tipografía:** fuente del sistema (Roboto/SF). Escala M3 con regla propia EXC-1: **ningún texto < 16 sp**. Hay 14 estilos, pero varios son idénticos en tamaño (`bodyMedium`, `bodySmall`, `labelLarge/Medium/Small`, todos 16/24) → la jerarquía depende solo del peso. Sin `fontSize` sueltos fuera del tema.
- **Espaciado:** grid de 4 dp (`xs 4, s 8, m 12, l 16, xl 24, xxl 32`).
- **Formas:** escala M3 (4, 8, 12, 16, 28, full). **Elevación:** niveles 0–5, con la regla "sin sombras como adorno".
- **Movimiento:** easing/duraciones M3; respeta movimiento reducido (`use-accesibilidad`).
- **Táctil:** mínimo 48, principal 56.
- **Prohibido por diseño:** gradientes, blur, textShadow.
- **Iconos:** MaterialCommunityIcons, 20/24/48.
- **Componentes y variantes:** Boton (primario/secundario/peligro…), Campo, StepperCantidad, Aviso, Snackbar, Dialogo, HojaInferior, TarjetaAccion, FilaProducto, FilaVenta, BarraNavegacion, FabExtendido, ChipFiltro, ChipSugerencia, IndicadorConfianza, EtiquetaSimulacion, BarraPasos. Una sola versión de cada uno (pendiente de confirmar variantes en la Fase 1).
- **Tema/tokens:** sí, `src/theme.ts` + `docs/diseno/00-sistema.md`. Reglas de accesibilidad propias (EXC-1…10) y soporte "letra grande".
- **Ojo (a verificar en Fase 1):** pantallas de inicio e inventario viven en `src/app/inicio|inventario/` (carpetas dentro de `app/`, que debería contener solo rutas) y no en `screens/` como indica el plan; archivos grandes (`camara` 766, `revision-cobro` 629).

## 0.5 Capturas

**No tomadas.** Requieren `npm install` en cada clon y arrancar Expo (web o emulador). Las pantallas dependen de la integración de ramas, así que propongo capturar después de unificarlas. Carpeta destino: `docs/ui-ux/capturas/antes/`.

## Resumen y decisiones que necesito de ti

1. **Base de trabajo.** Propongo crear un único repositorio `tiendita-ia` y una rama `ui/rediseno` que fusione las 4 ramas (hay conflictos probables en `(tabs)/*.tsx`, `constants.ts`, `theme.ts`). Alternativa: rediseñar solo sobre `front-inventario` (la más completa tras inicio). **¿Cuál prefieres?**
2. **Alcance del "rediseño".** El proyecto ya tiene un sistema M3 maduro. ¿Quieres (a) **refinarlo** (jerarquía tipográfica, modo oscuro, pulido, estados faltantes) o (b) **cambiar la identidad visual** (nueva paleta/estilo, saliendo de M3)? La guía dice no inventar identidad: necesito colores/logo/apps de referencia si es (b).
3. **Prioridad y plazo.** ¿Hay demo o fecha? ¿Qué pantalla pesa más (supongo Cobrar)?
4. **Capturas:** ¿las generamos instalando dependencias y corriendo la versión web?
5. **Commits:** ¿puedo hacer commits locales por mejora en `ui/rediseno` (sin push)?
