# Plan del Frontend — App del Tendero (Expo + React Native)

> Hackathon NVIDIA Oaxaca 2026 · Digitalización en procesos de negocios
> Fuentes: `informacion/idea.txt` (producto) y `informacion/Bases del hackathon…pdf` (reglas).
> Agentes: `ui-ux-movil` (diseño) → `frontend-implementador` (código) → `revisor-ui-flat` + `revisor-accesibilidad-hci` (auditoría).

---

## 0. Decisiones técnicas

| Tema | Decisión | Por qué |
|---|---|---|
| Base | `npx create-expo-app@latest` (Expo SDK 58, TypeScript, Expo Router) directamente en `front/` (si ya tiene `docs/`, generar en carpeta temporal y mover) | Plantilla estándar, rutas por archivos |
| Ejecución en demo | **Expo Go** en teléfono físico (sin build nativo) | Cero tiempo en compilación; cámara funciona en Expo Go |
| Navegación | Expo Router: `Tabs` (4 pestañas) + `Stack` con modales | Barra inferior ≤ 4 opciones (Nielsen #4) |
| Estilos | `StyleSheet` + `src/theme.ts` con tokens; **sin NativeWind, sin librerías de UI con sombras** (Paper, NativeBase, etc.) | Control total para cumplir la regla flat (sin sombra/elevation/gradiente) |
| Componentes nativos | Revisar `@expo/ui` caso por caso; solo usarlo si se puede quitar toda elevación/sombra. Por defecto, componentes propios | Las primitivas Material/SwiftUI traen elevación por defecto |
| Iconos | `@expo/vector-icons` (MaterialCommunityIcons), siempre con etiqueta de texto | Ya viene en la plantilla |
| Cámara / imágenes | `expo-camera`, `expo-image-picker` (galería), `expo-image-manipulator` (redimensionar/comprimir antes de subir) | 3 modos de visión |
| Datos remotos | `@tanstack/react-query` + `fetch` | Estados de carga/error/reintento gratis (Nielsen #1, #9) |
| Validación | `zod` (respuestas de API y formularios de revisión) | El JSON de la IA puede venir incompleto |
| Sin conexión | `@react-native-community/netinfo` + cola local en `expo-sqlite` (o `AsyncStorage` si falta tiempo) | "Sin conexión: se guardó y se enviará al reconectarte" |
| Config | `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_USE_MOCKS=1` en `.env` (no se sube `.env`) | Front avanza en paralelo mientras back entrena modelos |
| Calidad | `npx expo lint`, `npx tsc --noEmit` | Rápido y suficiente para 24 h |

Instalar siempre con `npx expo install <paquete>` (versiones compatibles con el SDK).

> **Nota de reglas (§10 de las bases):** se permite usar bibliotecas y componentes de propósito general, pero la preparación específica de la solución debe hacerse dentro de las 24 h. Antes del inicio solo se pueden preparar cosas genéricas (instalar Node/Expo Go, practicar). El scaffolding y las pantallas se hacen durante el hackathon.

---

## 1. Estructura de carpetas

```
front/
├── app.json
├── .env.example                  # EXPO_PUBLIC_API_URL, EXPO_PUBLIC_USE_MOCKS
├── docs/
│   ├── PLAN-frontend.md          # este archivo
│   └── diseno/                   # specs de ui-ux-movil, una por pantalla
└── src/
    ├── app/                      # SOLO rutas
    │   ├── _layout.tsx           # Stack raíz + QueryClientProvider + banner de conexión
    │   ├── (tabs)/
    │   │   ├── _layout.tsx       # Inicio · Cobrar · Inventario · Asistente
    │   │   ├── index.tsx         # Inicio (dashboard)
    │   │   ├── cobrar.tsx
    │   │   ├── inventario.tsx
    │   │   └── asistente.tsx
    │   ├── camara.tsx            # modal, ?modo=cobro|alta|ticket
    │   ├── revision/[modo].tsx   # revisar y corregir lo que detectó la IA
    │   ├── venta/[id].tsx        # comprobante de venta
    │   ├── historial.tsx         # ventas / altas / tickets guardados
    │   ├── pago/index.tsx        # flujo de pago digital + tutor
    │   └── promociones.tsx       # propuestas por caducidad (aprobar / rechazar)
    ├── screens/                  # cuerpo de cada pantalla + sus subcomponentes
    ├── components/               # boton.tsx, campo.tsx, stepper-cantidad.tsx, aviso.tsx,
    │                             # barra-estado.tsx, fila-producto.tsx, tarjeta-accion.tsx,
    │                             # indicador-confianza.tsx, etiqueta-simulacion.tsx …
    ├── api/
    │   ├── cliente.ts            # fetch con timeout, errores tipados
    │   ├── vision.ts             # posCheckout, catalogScan, receiptOcr
    │   ├── asistente.ts          # enviarMensaje, ayudaTutor
    │   ├── negocio.ts            # ventas, inventario, gastos, kpis
    │   ├── esquemas.ts           # tipos + zod (contrato con back/)
    │   └── mocks/                # respuestas sintéticas (marcadas como MOCK)
    ├── hooks/                    # use-conexion.ts, use-cola-offline.ts, use-tutor.ts
    ├── utils/                    # formato-moneda.ts (+ .test.ts), imagen.ts
    ├── constants.ts
    └── theme.ts                  # tokens flat (colores, bordes, radios, tipografía, espaciado)
```

---

## 2. Contrato con el backend (acordar con el equipo de `back/` en la hora 1)

Definirlo en `src/api/esquemas.ts` y copiarlo al back. Propuesta mínima:

```ts
// Visión
type ItemDetectado = { sku: string | null; nombre: string; cantidad: number;
                       precio_unitario: number | null; confianza: number /*0-1*/; caja?: [number,number,number,number] };
type RespuestaPosCheckout = { items: ItemDetectado[]; imagen_id: string };
type RespuestaCatalogScan = { items: ItemDetectado[]; categoria?: string; caducidad_ocr?: string | null };
type RespuestaReceiptOcr  = { fecha: string|null; proveedor: string|null; total: number|null;
                              conceptos: { descripcion: string; monto: number|null }[];
                              tipo: 'gasto'|'compra'|'inversion'|null; confianza: number };

// Asistente (un solo endpoint; el orquestador decide)
type MensajeAsistente = {
  rol: 'caja'|'bodega'|'cuentas'|'promociones'|'tutor'|'general'; // se muestra con nombre de oficio
  texto: string;
  acciones?: { id: string; tipo: 'confirmar_venta'|'confirmar_alta'|'aprobar_promo'|'abrir_pantalla';
               titulo: string; datos: unknown }[];
  no_resuelto?: boolean;   // → mostrar alternativa (formulario manual / contacto)
};

// Tutor de pagos: la app envía estado de pantalla, no capturas
type EstadoPantalla = { pantalla: string; paso: number; campos: Record<string, 'vacio'|'lleno'|'error'>;
                        errores_visibles: string[]; segundos_inactivo: number };
```

Errores HTTP esperados: `422` imagen no procesable · `400` datos faltantes · `503/timeout` servidor. Cada uno tiene mensaje humano en el front.

---

## 3. Fases de trabajo (24 h)

Cada fase sigue el mismo ciclo: **diseño (`ui-ux-movil`) → código (`frontend-implementador`) → auditoría (`revisor-ui-flat` + `revisor-accesibilidad-hci`) → corregir bloqueantes**.

### Fase 0 · Arranque (h 0–1)
- [ ] `npx create-expo-app@latest` → contenido a `front/`, `npm run reset-project` para limpiar la plantilla, confirmar que usa `src/app`.
- [ ] Instalar dependencias de la sección 0.
- [ ] `.env.example`, cliente API con modo mock.
- [ ] Acordar contrato de la sección 2 con back.
- **Listo cuando:** la app abre en Expo Go con 4 pestañas vacías y lint + tsc pasan.

### Fase 1 · Sistema de diseño (h 1–3)
- [ ] `ui-ux-movil`: spec de tokens y componentes base → `docs/diseno/00-sistema.md`.
- [ ] `theme.ts` + componentes: `Boton` (primario/secundario/peligro, ≥48 px), `Campo` (con error en línea), `StepperCantidad` (+/−), `Aviso` (error/éxito/sin conexión, icono + texto), `IndicadorConfianza`, `EtiquetaSimulacion`, `BarraEstado` (pasos), `FilaProducto`, `TarjetaAccion`.
- [ ] Revisión flat + accesibilidad (tabla de contraste).
- **Listo cuando:** cero `shadow*`/`elevation>0`/gradientes; todos los pares de color ≥ 4.5:1.

### Fase 2 · Recorrido principal: Cobrar con foto (h 3–9) ⭐ prioridad máxima
Flujo: **Cobrar → Cámara (modo cobro) → Analizando foto… → Revisión editable → Confirmar → Venta registrada → stock descontado → visible en historial/Inicio.**
- [ ] Cámara: guía de encuadre, botón grande de disparo, "Elegir de galería", permiso denegado con explicación.
- [ ] Compresión de imagen antes de subir; estado de carga con texto.
- [ ] Revisión: lista densa con +/−, eliminar con deshacer, agregar producto manual (buscador), confianza baja marcada con icono + texto, total en vivo.
- [ ] Confirmación y comprobante (`venta/[id]`).
- [ ] Errores: foto ilegible (reintentar), sin productos detectados, sin conexión (cola), timeout.
- **Listo cuando:** se completa el flujo con mocks y con el endpoint real `/vision/pos-checkout`.

### Fase 3 · Asistente (h 9–13)
- [ ] Chat con burbujas planas (borde 1 px), nombre de oficio + icono por rol ("Caja", "Bodega", "Cuentas", "Promociones").
- [ ] Sugerencias rápidas ("¿Cuánto vendí hoy?", "¿Qué se me acaba?").
- [ ] `TarjetaAccion` para confirmar acciones críticas dentro del chat.
- [ ] Estado "escribiendo…", error de conexión, `no_resuelto` con alternativa.
- [ ] Acceso al asistente desde la pantalla de revisión ("Pregúntale a Caja").
- **Listo cuando:** el asistente puede registrar/explicar una venta y responder métricas con el modelo del equipo.

### Fase 4 · Inventario, alta de mercancía y tickets (h 13–16)
- [ ] Inventario: lista con buscador, filtros (stock bajo, por caducar) con icono + texto.
- [ ] Cámara modo **alta** (`/vision/catalog-scan`) → revisión → guardar.
- [ ] Cámara modo **ticket** (`/vision/receipt-ocr`) → revisión de fecha/monto/conceptos → guardar gasto.
- **Listo cuando:** ambos flujos guardan y se ven en historial.

### Fase 5 · Tutor de pagos digitales (h 16–19)
- [ ] Pantalla `pago/` con flujo de cobro digital (transferencia/CoDi/tarjeta) etiquetado **"Simulación"**, con caso de éxito y al menos un caso de fallo.
- [ ] `use-tutor.ts`: envía `EstadoPantalla` al pedir ayuda o tras inactividad.
- [ ] Panel inferior plano (borde superior 2 px) con paso actual y guía; nunca tapa campos ni botón principal; se puede cerrar.
- **Listo cuando:** el tutor guía un pago de principio a fin y reacciona a un error de captura.

### Fase 6 · Inicio y promociones (h 19–21)
- [ ] Inicio: ventas del día, gastos vs. ingresos, alertas, accesos rápidos a los 3 modos de cámara, "Repetir última venta".
- [ ] Indicador para la demo: proceso actual vs. digitalizado (tiempo / pasos).
- [ ] Promociones: tarjeta con copy (y video si existe) → aprobar / rechazar; lo no implementado marcado "Simulación".

### Fase 7 · Pulido y demo (h 21–24)
- [ ] Auditoría completa con ambos revisores sobre todo `front/`; corregir bloqueantes.
- [ ] Probar con letra grande del sistema, con una mano, sin conexión.
- [ ] Datos de demo sintéticos; quitar logs y URLs privadas.
- [ ] Guion de demo de 10 min centrado en el recorrido principal.

---

## 4. Reparto sugerido (4 integrantes)

| Persona | Foco |
|---|---|
| A | Front: Fases 0–2 (sistema de diseño + Cobrar) |
| B | Front: Fases 3, 5 (asistente + tutor) y luego 4 |
| C | Back: modelo de visión (entrenamiento en servidores NVIDIA) + endpoints de visión |
| D | Back: asistente (ajuste/RAG + orquestador) + BD + endpoints de negocio |

Front trabaja con `EXPO_PUBLIC_USE_MOCKS=1` hasta que back publique cada endpoint.

---

## 5. Definición de "terminado" por pantalla
- [ ] Diseño en `docs/diseno/` aprobado.
- [ ] Estados: vacío, cargando, error, éxito, sin conexión.
- [ ] Lo interpretado por IA es editable antes de guardar.
- [ ] `revisor-ui-flat` ✅ y `revisor-accesibilidad-hci` sin bloqueantes.
- [ ] Lint y `tsc` pasan; probado en teléfono con Expo Go.
