# 02 · Catálogo Detallado de Agentes (1 Supervisor + 6 Especialistas)

Todos los agentes obtienen su LLM dinámicamente en tiempo de ejecución mediante `get_llm(role="<rol>")` desde [config/models.py](../config/models.py), heredando el perfil **100% NVIDIA NIM por defecto**, los overrides individuales en runtime (`set_agent_brain`) y el rescate silencioso `.with_fallbacks()`.

---

## Tabla Resumen de los 7 Roles

| Rol | Archivo | Modelo NVIDIA Default | Temp | Tipo de Agente | Acceso a BD | Pasa por HITL |
|---|---|---|---|---|---|---|
| `supervisor` | [agents/supervisor.py](../agents/supervisor.py) | `nvidia/nemotron-3-super-120b-a12b` | `0.1` | Structured Output (`SupervisorDecision`) | Indirecto (lee estado) | No |
| `control` | [agents/control.py](../agents/control.py) | `nvidia/llama-3.1-nemotron-nano-8b-v1` | `0.1` | ReAct (`create_react_agent`) | Lectura + Escritura | **Sí** |
| `vendedor` | [agents/vendedor.py](../agents/vendedor.py) | `nvidia/llama-3.1-nemotron-nano-8b-v1` | `0.2` | ReAct (`create_react_agent`) | Lectura + Ventas POS | **Sí** |
| `analista` | [agents/analista.py](../agents/analista.py) | `nvidia/nemotron-3-super-120b-a12b` | `0.1` | ReAct (`create_react_agent`) | **Solo Lectura** | No |
| `investigador` | [agents/investigador.py](../agents/investigador.py) | `nvidia/nemotron-3-super-120b-a12b` | `0.2` | ReAct + Structured Output (`StrategicReport`) | RAG + Web + Disco | No |
| `publicista` | [agents/publicista.py](../agents/publicista.py) | `nvidia/llama-3.1-nemotron-nano-8b-v1` | `0.4` | ReAct (`create_react_agent`) | Lectura + Promo vía HITL | **Sí** |
| `tutor_ui` | [agents/tutor_ui.py](../agents/tutor_ui.py) | `nvidia/llama-3.1-nemotron-nano-8b-v1` | `0.0` | RAG directo + Structured Output (`TutorResponse`) | RAG CoDi/SPEI/DiMo | No |

---

## 1. Supervisor Maestro (`supervisor`)
- **Archivo:** [agents/supervisor.py](../agents/supervisor.py) · **Nodo:** `supervisor_node`
- **Perfil cognitivo:** `razonamiento` · **Modelo default:** `nvidia/nemotron-3-super-120b-a12b` (`temp=0.1`).
- **Qué hace:**
  - Evalúa `event_source`, presencia de `vision_payload`, `ui_state`, `db_evidence`, `iteration_count` y el último mensaje del usuario.
  - Decide el especialista óptimo (`next_agent`) y, solo cuando la solicitud exige varios roles en secuencia, construye `compound_chain` (sanitizada sin duplicados).
  - Controla el tope duro `iteration_count <= 6`.
- **Herramientas:** Ninguna (orquestación pura vía `with_structured_output(SupervisorDecision)`).
- **Cómo opera ante fallos de salida estructurada:** Si un modelo falla con `with_structured_output`, intenta extracción JSON por prompting y, como último recurso determinista de emergencia, despacha según metadata de `event_source` (`vision_api`, `catalog-scan`, `receipt-ocr`, `pos-checkout`, `cron`, `ui_state`).

---

## 2. Control de Inventario y Auditoría (`control`)
- **Archivo:** [agents/control.py](../agents/control.py) · **Nodo:** `control_node`
- **Perfil cognitivo:** `balanceado` · **Modelo default:** `nvidia/llama-3.1-nemotron-nano-8b-v1` (LoRA objetivo: `control_inventory_v1`).
- **Qué puede hacer:**
  - Analizar fotos reales de anaqueles/catálogos (`/imagen ... catalog` o `/catalog-scan`) vía NVIDIA NIM Vision y contrastar contra PostgreSQL.
  - Procesar tickets y facturas (`/imagen ... ticket` o `/receipt-ocr`) clasificando estrictamente cada concepto en `inversion_inventario` (mercancía para reventa) vs. `gasto_operativo` (insumos, luz, renta, limpieza).
  - Dar de alta productos nuevos (`register_product`), ajustar stock (`update_stock`) con creación de lotes y movimientos en `movimiento_inventario`.
  - Vigilar lotes próximos a caducar (`check_expiry_alerts` / `query_expiring_soon`) y stock por debajo del mínimo (`get_low_stock_alerts`).
- **Herramientas asignadas (9):**
  `analyze_catalog_photo`, `analyze_receipt`, `register_product`, `update_stock`, `check_expiry_alerts`, `get_low_stock_alerts`, `query_inventory`, `query_expiring_soon`, `retrieve_few_shots`.
- **Manejo multimodal:** Si `vision_payload` contiene `image_b64`, registra la imagen en el buffer de `vision_nim.py` (`set_active_vision_image`) dentro de un bloque `try/finally` para que la herramienta envíe los bytes reales sin saturar la ventana de contexto del LLM.
- **Disparador HITL:** Genera `pending_approval` cuando propone alta de catálogo (`alta_catalogo`) o clasificación contable de gastos críticos (`clasificacion_gasto_critico`).

---

## 3. Vendedor POS de Mostrador (`vendedor`)
- **Archivo:** [agents/vendedor.py](../agents/vendedor.py) · **Nodo:** `vendedor_node`
- **Perfil cognitivo:** `baja_latencia` · **Modelo default:** `nvidia/llama-3.1-nemotron-nano-8b-v1` (LoRA objetivo: `pos_upsell_v1`).
- **Qué puede hacer:**
  - Detectar productos reales en la barra de caja mediante NIM Vision (`/imagen ... pos` o `/pos-checkout`).
  - Cotizar en tiempo real contra `v_inventario` y `buscar_productos()`.
  - Abrir carritos (`create_cart`), agregar artículos (`add_to_cart`), recomendar venta cruzada real basada en coocurrencia histórica (`suggest_upsell` sobre `v_coocurrencia`) y cerrar la transacción atómica en PostgreSQL (`checkout_cart` → `registrar_venta()`).
  - Consultar límites sin comisión, requisitos (CLABE, CEP, QR, celular) y advertencias de seguridad de **CoDi, SPEI y DiMo** en el RAG antes de liquidar cobros digitales (`consultar_reglas_pago_pos`, `consultar_guia_pago_digital`).
- **Herramientas asignadas (9):**
  `analyze_pos_items`, `create_cart`, `add_to_cart`, `checkout_cart`, `suggest_upsell`, `consultar_reglas_pago_pos`, `consultar_guia_pago_digital`, `query_inventory`, `retrieve_few_shots`.
- **Guardia obligatoria:** Toda salida pasa por `prevent_cost_leakage()` para impedir filtrar `costo` / `costo_unitario` al cliente en mostrador.
- **Disparador HITL:** Genera `pending_approval` (`descuento_especial`) ante propuestas de descuentos especiales en mostrador.

---

## 4. Analista Financiero (`analista`)
- **Archivo:** [agents/analista.py](../agents/analista.py) · **Nodo:** `analista_node`
- **Perfil cognitivo:** `razonamiento` · **Modelo default:** `nvidia/nemotron-3-super-120b-a12b` (`temp=0.1`).
- **Restricción absoluta:** Rol **100% de Solo Lectura**. Tiene prohibido modificar inventario, crear carritos o ejecutar cobros.
- **Qué puede hacer:**
  - Calcular flujo de caja neto diario y acumulado (`get_cash_flow` → `v_flujo_caja`).
  - Auditar margen bruto y porcentaje de rentabilidad por SKU (`get_margins_by_sku` → `v_margen_producto`).
  - Identificar los productos más vendidos y artículos estancados (`get_rotation_by_sku` → `v_margen_producto` + `v_inventario`).
  - Entregar resúmenes de ventas y ticket promedio por periodo (`get_sales_summary` / `query_sales` → `v_ventas_dia`).
- **Herramientas asignadas (7):**
  `get_cash_flow`, `get_margins_by_sku`, `get_rotation_by_sku`, `get_sales_summary`, `query_sales`, `query_inventory`, `retrieve_few_shots`.
- **Salidas de estado:** Escribe `db_evidence` y devuelve el diagnóstico cuantitativo directo al usuario (`router_post_specialist` → `END` si no hay cadena compuesta).

---

## 5. Investigador Comercial y Estratégico (`investigador`)
- **Archivo:** [agents/investigador.py](../agents/investigador.py) · **Nodo:** `investigador_node`
- **Perfil cognitivo:** `velocidad_contexto` · **Modelo default:** `nvidia/nemotron-3-super-120b-a12b` (`temp=0.2`).
- **Qué puede hacer:**
  - Consultar reportes estratégicos previos en memoria vectorial antes de investigar desde cero (`search_past_reports`).
  - Investigar tendencias, competencia, precios de referencia y proveedores en la web en vivo (`search_web_tavily` + `scrape_webpage_clean` con `httpx` + `BeautifulSoup`).
  - Cruzar con políticas locales del negocio (`consultar_conocimiento_comercial`).
  - Sintetizar un **reporte estructurado en 9 secciones obligatorias** (`StrategicReport`) usando `with_structured_output`:
    1. `identificacion_sector`
    2. `mercado_tendencias`
    3. `clientes`
    4. `problemas`
    5. `soluciones`
    6. `hipotesis`
    7. `objetivos`
    8. `impacto`
    9. `hallazgos`
  - Persistir automáticamente el reporte en `data/reportes/*.json` + `*.md` e indexarlo en FAISS (`index_strategic_report`) para futuras sesiones.
- **Herramientas asignadas (6):**
  `search_past_reports`, `search_web_tavily`, `scrape_webpage_clean`, `consultar_conocimiento_comercial`, `save_and_index_report`, `retrieve_few_shots`.
- **Salidas de estado:** Rellena `state["strategic_report"]` y devuelve el resumen en Markdown.

---

## 6. Publicista y Creador de Campañas (`publicista`)
- **Archivo:** [agents/publicista.py](../agents/publicista.py) · **Nodo:** `publicista_node`
- **Perfil cognitivo:** `balanceado` · **Modelo default:** `nvidia/llama-3.1-nemotron-nano-8b-v1` (`temp=0.4`, LoRA objetivo: `promo_copy_v1`).
- **Qué puede hacer:**
  - Detectar productos reales próximos a caducar en PostgreSQL (`query_expiring_soon` sobre `lote`/`v_por_caducar`) para proponer remates preventivos (ej. 20% de descuento).
  - Redactar copys persuasivos para WhatsApp Status / mostrador (`generate_promo_copy`) y llamados a la acción (`generate_cta`).
  - Generar especificaciones técnicas de **video vertical 9:16 de 5 segundos** (`generate_video_prompt`, contrato `VideoPrompt`).
- **Herramientas asignadas (6):**
  `generate_promo_copy`, `generate_video_prompt`, `generate_cta`, `query_expiring_soon`, `query_inventory`, `retrieve_few_shots`.
- **Disparador HITL obligatorio:** Toda campaña creada empaqueta `state["promo_assets"]` y `state["pending_approval"]` (`action_type="publicar_campana"`, `op="publicar_campana"`). El grafo se pausa en `approval_gate` y solo tras aprobación humana inserta el registro real en la tabla PostgreSQL `promocion` (`estado='publicada', simulada=false`).

---

## 7. Tutor UI de Pagos Digitales (`tutor_ui`)
- **Archivo:** [agents/tutor_ui.py](../agents/tutor_ui.py) · **Nodo:** `tutor_ui_node`
- **Perfil cognitivo:** `baja_latencia` · **Modelo default:** `nvidia/llama-3.1-nemotron-nano-8b-v1` (`temp=0.0`, LoRA objetivo: `tutor_ui_concise_v1`).
- **Qué puede hacer:**
  - Recibe `ui_state` (`payment_method`: `codi | spei | dimo`, `screen`, `step`, `error_code`).
  - **Paso 1 (Grounding obligatorio):** Consulta `consultar_guia_pago_digital` contra el RAG oficial de Banxico (`guias.json` + `conocimiento.jsonl`) para recuperar los pasos exactos, límites y advertencias de seguridad (nunca pedir NIP/token/CVV).
  - **Paso 2 (Síntesis concisa):** Genera una respuesta estructurada (`TutorResponse`) estrictamente fundamentada en los fragmentos recuperados y recortada de forma determinista con `enforce_max_sentences(..., max_sentences=2)` para garantizar **máximo 2 oraciones accionables**.
- **Salidas de estado:** Escribe las fuentes RAG recuperadas con su score en `state["db_evidence"]` y emite la guía corta en `messages`.
