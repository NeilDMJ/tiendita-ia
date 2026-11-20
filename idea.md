# Tiendita IA: catálogo, cobro y asistente con visión por computadora

## 1. Resumen de la idea

Aplicación móvil para micro y pequeños negocios en la que el vendedor **registra productos usando la cámara del celular**. Un **modelo de visión** identifica los productos y un **chatbot orquestador** coordina varios **agentes con roles especializados**. Los agentes administran el catálogo, registran ventas, generan reportes, sugieren promociones y acompañan al vendedor al recibir pagos digitales.

**Proceso que se digitaliza:** registrar productos, cobrar una venta, ligarla a su forma de pago y conocer el estado del negocio.

| Hoy (sin la app) | Con la app |
|---|---|
| Precios de memoria, suma con calculadora | El vendedor escanea los productos con la cámara y el total sale solo |
| Ventas anotadas en libreta o sin registro | Cada venta queda en la base de datos al momento |
| Transferencias que no se ligan a ninguna venta | Cada pago digital queda vinculado a su venta |
| Inventario "a ojo" | El stock se descuenta en cada venta y avisa cuando falta |
| Sin información para decidir | Reportes y recomendaciones de los agentes |

---

## 2. Componentes

### 2.1 Catálogo e inventario por fotos

- El vendedor toma **fotos del producto**. El **modelo de visión** lo identifica (o propone una clase nueva si no lo conoce).
- El **agente de Control** completa la ficha conversando con el vendedor: nombre, precio de venta, costo, stock inicial y, de forma opcional, la **fecha de caducidad**.
- **Recepción de mercancía:** una foto del lote recibido suma existencias al inventario.
- El catálogo se puede administrar desde el chat: "sube la Coca de 600 a $20", "¿cuántos Gansitos me quedan?".

### 2.2 Cobro con visión (escaneo por el vendedor)

1. El vendedor abre **Cobrar** y pasa los productos frente a la cámara, uno por uno, como si fuera un lector de códigos.
2. La app envía cuadros a la **API de visión**, que devuelve el producto detectado y su confianza.
3. El producto se agrega al carrito. Si se repite suma +1, y si fue un error se quita deslizando.
4. Lo que no tiene empaque (granel, por peso) se agrega **por voz o texto** con el agente Vendedor.
5. El agente Vendedor confirma el total y pregunta el **método de pago** (efectivo, transferencia, QR o tarjeta).
6. El agente **registra la venta** en la base de datos y descuenta el inventario.

> Flujo de datos: **Cámara → API de visión → agente Vendedor → Base de datos**

### 2.3 Chatbot orquestador y agentes

El vendedor habla con **un solo chat**. El **orquestador** interpreta la intención y delega en el agente adecuado; cada agente tiene sus propias herramientas (*tools*) sobre la base de datos.

| Agente | Rol | Tareas principales | Herramientas |
|---|---|---|---|
| **Vendedor** | Operación diaria | Arma el carrito, confirma totales, registra ventas, guía el pago digital | `agregar_al_carrito`, `registrar_venta`, `registrar_pago` |
| **Control** | Inventario y caja | Da el estado del catálogo, avisa de stock bajo y productos por caducar, hace el cierre de caja y la conciliación de pagos | `consultar_inventario`, `ajustar_stock`, `cierre_de_caja` |
| **Analista** | Interpretación de datos | Consulta la BD, calcula ventas, márgenes, productos top y horarios pico, y genera reportes | `consultar_ventas`, `calcular_margenes`, `generar_reporte` |
| **Publicista** | Promoción | Propone promociones para productos lentos o por caducar y genera textos e imágenes para WhatsApp o redes | `productos_por_caducar`, `generar_promocion` |
| **Investigador** | Contexto externo | Compara precios de referencia y consulta información del sector y del mercado para enriquecer los reportes | `buscar_referencias`, `resumen_mercado` |

**Comunicación con el vendedor:** los agentes no solo responden, también **avisan de forma proactiva** con notificaciones en el chat. Por ejemplo: "Te quedan 3 leches", "El pan de caja caduca en 2 días, ¿armo una promoción?", "Hay una transferencia sin venta asociada".

### 2.4 Reportes

El **Analista** genera los reportes con apoyo del **Investigador** y del **Control**, siguiendo esta estructura:

| Sección | Contenido | Fuente |
|---|---|---|
| Identificación | Negocio, periodo, responsable | Perfil del negocio |
| Sector | Giro y tipo de negocio | Perfil + Investigador |
| Tendencias | Productos que suben o bajan, horarios y días pico | BD de ventas |
| Clientes | Ticket promedio, frecuencia, método de pago preferido | BD de ventas y pagos |
| Problemas | Stock agotado, mermas, caducidades, diferencias en caja | Control |
| Hallazgos | Patrones relevantes detectados en los datos | Analista |
| Hipótesis | Posibles causas de los problemas y hallazgos | Analista |
| Soluciones | Acciones concretas (reabastecer, promocionar, ajustar precio) | Analista + Publicista |
| Impacto | Efecto estimado de cada solución en ventas o margen | Analista |
| Objetivos | Metas para el siguiente periodo | Analista + vendedor |
| Estado del mercado | Precios de referencia y contexto del sector | Investigador |

> Cada dato del reporte indica si viene de la **BD del negocio** o de una **fuente externa**, para no presentar suposiciones como hechos.

### 2.5 Acompañante para pagos digitales

El agente Vendedor funciona como **tutor** al recibir pagos digitales, en línea con la Ley de Economía Digital para Pagos Digitales y Electrónicos:

- La app tiene **pantallas de estado del pago**: *pendiente → enviado → recibido → conciliado*.
- La app le informa al agente **en qué paso está el usuario** y qué acción hizo, mediante eventos de la interfaz. Así el agente puede guiarlo: "Muéstrale el QR al cliente", "Ahora captura la referencia", "Listo, el pago quedó ligado a la venta #124".
- **Verificación con visión:** el vendedor puede tomar foto del comprobante de transferencia y el sistema extrae monto, referencia y hora para ligarlos a la venta.
- Al cierre, el agente Control **concilia** las ventas digitales contra los pagos registrados y señala las diferencias.

### 2.6 Interfaces

**Dashboard móvil**
- Ventas del día y de la semana
- Efectivo contra pagos digitales
- Productos más vendidos y de menor rotación
- Alertas: stock bajo, por caducar, pagos sin conciliar
- Acceso rápido a **Cobrar**, **Agregar producto** y **Chat**

**Interfaz de chat**
- Un chat único con el orquestador
- Etiqueta visible del agente que responde (Vendedor, Analista, etc.)
- Tarjetas enriquecidas: carrito, reporte, promoción y estado del pago
- Entrada por texto y por voz

---

## 3. Extras

| Extra | Descripción |
|---|---|
| **Tickets y comprobantes** | Fotos de tickets de **gastos, compras e inversiones**. El sistema extrae fecha, monto y concepto y los registra como egresos, para calcular la utilidad real y organizar comprobantes fiscales. |
| **Promociones automáticas** | Cuando un producto está **por caducar** o no se vende, el Publicista genera una promoción (texto e imagen, o un video corto) lista para compartir. |

---

## 4. Modelos de IA

| Modelo | Tipo | Entrenamiento / ajuste | Función en el proceso |
|---|---|---|---|
| **Visión** | Detector de objetos (familia YOLO) | Ajustado con fotos propias de los productos del negocio, en los servidores de NVIDIA; optimizado con TensorRT | Alta de productos, escaneo en el cobro, recepción de mercancía y lectura de comprobantes |
| **Asistente** | LLM pequeño (unos 8B) con LoRA | Ajustado con diálogos de tendero en español mexicano y llamadas a herramientas en JSON | Orquestador y agentes: interpretar pedidos, usar herramientas, generar reportes y promociones |

Los agentes comparten **el mismo modelo ajustado** con distintas instrucciones de rol y herramientas. Esto reduce el costo de servirlos y mantiene un estilo consistente.

**Herramientas de NVIDIA** (a confirmar según lo disponible en el concurso): NeMo para el ajuste del LLM, NIM o vLLM para servirlo, TAO Toolkit o Ultralytics más TensorRT para el detector, y Riva para la entrada por voz (opcional).

---

## 5. Arquitectura

```
┌──────────────────────────── App móvil ────────────────────────────┐
│  Dashboard  │  Cobrar (cámara)  │  Catálogo  │  Chat  │  Pagos    │
└──────┬───────────────┬──────────────────┬──────────────┬──────────┘
       │               │ cuadros/fotos    │ mensajes     │ eventos de pantalla
       ▼               ▼                  ▼              ▼
┌─────────────────────── Backend (servidor NVIDIA) ─────────────────┐
│  API de visión (TensorRT)                                         │
│  Orquestador ─► Vendedor │ Control │ Analista │ Publicista │ Invest.│
│  LLM ajustado (NIM / vLLM)                                        │
└──────────────────────────────┬────────────────────────────────────┘
                               ▼
                 Base de datos (PostgreSQL / SQLite)
```

## 6. Base de datos (esquema mínimo)

| Tabla | Campos clave |
|---|---|
| `productos` | id, nombre, clase_vision, precio, costo, stock, caducidad |
| `ventas` | id, fecha, total, metodo_pago, estado |
| `venta_detalle` | venta_id, producto_id, cantidad, precio |
| `pagos` | id, venta_id, tipo, referencia, monto, estado, comprobante |
| `gastos` | id, fecha, concepto, monto, tipo (gasto/compra/inversión), ticket |
| `movimientos_inventario` | producto_id, tipo (entrada/salida/merma), cantidad, fecha |
| `reportes` | id, periodo, contenido, generado_por |

## 7. Recorrido de la demo

1. **Alta:** foto de un producto nuevo; el agente Control pregunta precio y caducidad y lo guarda.
2. **Cobro:** el vendedor escanea 4 productos, agrega "medio kilo de tortillas" por voz y cobra con transferencia.
3. **Pago guiado:** el agente acompaña el pago paso a paso, se toma foto del comprobante y la venta queda conciliada.
4. **Alerta:** el agente Control avisa que un producto está por caducar y el Publicista genera la promoción.
5. **Reporte:** "¿Cómo me fue hoy?" devuelve el cierre de caja y un reporte resumido del Analista.
6. **Comparación:** la misma venta con libreta y con la app, en tiempo y en errores.