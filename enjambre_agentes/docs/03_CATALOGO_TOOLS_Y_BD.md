# 03 · Catálogo de Herramientas (`@tool`), PostgreSQL y MCP

Este documento enumera **todas las herramientas `@tool`** registradas en `tools/`, su contrato de entrada/salida, qué vistas o funciones reales de PostgreSQL (`tiendita-db`) utilizan y cómo se exponen vía MCP.

---

## 1. Conexión y Pool de PostgreSQL ([tools/db_client.py](../tools/db_client.py))

- **DSN:** Leído desde `config.keys.DATABASE_URL` (cargado automáticamente desde `.env`). Ejemplo activo: `postgresql://tiendita:***@localhost:5432/tiendita`.
- **Pool thread-safe:** Implementado con `queue.LifoQueue(maxsize=8)` y context manager `_get_connection()`, con `connect_timeout=5`, `rollback()` automático en caso de error y liberación limpia al cerrar la sesión.
- **Funciones de ciclo de vida:**
  - `verify_db_connection() -> dict`: verifica conectividad real contra `tiendita-db` y devuelve métricas en vivo (`database`, `user`, `pg_version`, `productos_activos`, `lotes_por_caducar`, `alertas_stock_bajo`, `ventas_registradas`, `ingresos_acumulados`).
  - `close_db_pool() -> int`: cierra todas las conexiones abiertas del pool (invocado automáticamente por `/salir`, `/exit` y `finally` de `main.py` / `cli_tester.py`).

### Enums Oficiales de PostgreSQL (`back/db/init/`)
Al escribir herramientas SQL nuevas, **respetar exactamente** estos valores de enum:
- `origen_venta`: `'camara'`, `'manual'`, `'asistente'` (las ventas de agentes usan `'asistente'`).
- `tipo_movimiento`: `'venta'`, `'entrada'`, `'salida'`, `'merma'`, `'cancelacion'`.
- `metodo_pago`: `'efectivo'`, `'transferencia'`, `'qr'`, `'tarjeta'` (mapeo POS: `codi → qr`, `spei/dimo → transferencia`).

---

## 2. Inventario Completo de Herramientas `@tool`

### A. Consultas de Base de Datos ([tools/db_client.py](../tools/db_client.py))

| Tool | Parámetros | Vistas / Funciones PostgreSQL | Descripción |
|---|---|---|---|
| `query_inventory` | `sku: Optional[str]`, `category: Optional[str]` | `buscar_productos(q, 10)`, `v_inventario` | Consulta existencias, precios de venta al público, stock mínimo y próxima caducidad. |
| `query_expiring_soon` | `days_ahead: int = 7` | `lote` JOIN `producto` | Lista lotes activos cuya fecha de caducidad está dentro de los próximos `N` días. |
| `query_sales` | `date_from`, `date_to`, `sku` (opcionales) | `v_ventas_dia` | Devuelve ingresos diarios, número de ventas y ticket promedio reales. |

### B. Control de Inventario ([tools/inventory_tools.py](../tools/inventory_tools.py))

| Tool | Parámetros | Tablas / Vistas PostgreSQL | Descripción |
|---|---|---|---|
| `register_product` | `sku`, `nombre`, `precio_venta`, `costo_unitario`, `categoria`, `stock_inicial`, `unidad`, `fecha_caducidad` | `categoria`, `producto`, `lote`, `movimiento_inventario` | Da de alta un nuevo SKU en el catálogo real, crea su lote inicial y registra movimiento `'entrada'`. |
| `update_stock` | `sku`, `cantidad`, `tipo_movimiento` (`entrada_compra\|merma\|ajuste_inventario`), `fecha_caducidad`, `costo_unitario` | `producto` (`FOR UPDATE`), `lote`, `movimiento_inventario` | Ajusta existencias reales de forma transaccional mapeando al enum de BD (`entrada`, `merma`, `salida`). |
| `check_expiry_alerts` | `days_ahead: int = 7` | Delega en `query_expiring_soon` | Evalúa lotes próximos a vencer para detonar remates o control de mermas. |
| `get_low_stock_alerts` | `threshold: Optional[float]` | `v_stock_bajo` / `producto` | Detecta SKUs con existencia ≤ mínimo y calcula `sugerencia_pedido`. |
| `get_product_detail` | `sku: str` | `v_inventario` | Consulta detallada (precio, costo interno, existencia, stock mínimo y próxima caducidad). |

### C. Punto de Venta / Mostrador ([tools/pos_tools.py](../tools/pos_tools.py))

| Tool | Parámetros | Tablas / Funciones / RAG | Descripción |
|---|---|---|---|
| `create_cart` | *(ninguno)* | Memoria de sesión (`_ACTIVE_CARTS`) | Inicia una sesión de venta devolviendo un `cart_id` único (`CART-XXXXXXXX`). |
| `add_to_cart` | `cart_id`, `sku`, `quantity: float = 1` | `buscar_productos(sku, 1)` | Cotiza el SKU contra PostgreSQL, acumula cantidades (soporta decimales kg/L) y recalcula totales. |
| `apply_discount` | `cart_id`, `discount_amount: float` | Memoria de sesión | Aplica descuento fijo en MXN al carrito activo. |
| `get_cart` | `cart_id` | Memoria de sesión | Inspecciona ítems, subtotal, descuento y total del carrito actual. |
| `suggest_upsell` | `cart_id` | `v_coocurrencia` JOIN `producto` | Sugiere hasta 2 productos complementarios comprados frecuentemente juntos en ventas reales. |
| `consultar_reglas_pago_pos` | `metodo_pago` (`codi\|spei\|dimo\|qr\|transferencia`), `monto: float`, `duda: str` | RAG (`buscar_guia_pago` + `guias.json`) | Recupera límites sin comisión, requisitos (CLABE/CEP/QR/celular) y advertencias antes de cobrar. |
| `checkout_cart` | `cart_id`, `payment_method`, `monto_recibido`, `fuera_de_linea` | `SELECT registrar_venta(jsonb)` + RAG pagos | Ejecuta la venta atómica en PostgreSQL (valida stock, descuenta lotes FEFO, crea `venta`, `venta_item`, `pago`, `movimiento_inventario` y `alerta`). Si el pago es digital (`codi`/`spei`/`dimo`), adjunta las reglas oficiales del RAG. |

### D. Analítica Financiera e Investigación Web ([tools/analytics_tools.py](../tools/analytics_tools.py))

| Tool | Parámetros | Fuente de datos | Descripción |
|---|---|---|---|
| `get_cash_flow` | `date_from`, `date_to` | PostgreSQL `v_flujo_caja` | Flujo de caja neto (ingresos por ventas, gastos operativos e inversión en inventario). |
| `get_margins_by_sku` | `sku: Optional[str]` | PostgreSQL `v_margen_producto` | Unidades vendidas, ingresos, margen bruto y porcentaje por SKU (uso interno, solo `analista`). |
| `get_rotation_by_sku` | `days: int = 30` | PostgreSQL `v_margen_producto` JOIN `v_inventario` | Clasifica cada SKU por velocidad de rotación (`alta`, `media`, `lenta`). |
| `get_sales_summary` | `period` (`day\|week\|month`) | PostgreSQL `v_ventas_dia` | Total recaudado, transacciones y ticket promedio del periodo. |
| `search_web_tavily` | `query`, `max_results: int = 5` | API Tavily (`TAVILY_API_KEY`) | Búsqueda web en vivo de tendencias, competidores y precios de mercado. |
| `scrape_webpage_clean` | `url: str` | `httpx` + `BeautifulSoup` (`lxml`) | Extrae texto limpio de páginas web detectadas (máx. 3,500 caracteres). |
| `search_past_reports` | `query`, `top_k: int = 3` | FAISS (`buscar_reportes_vectoriales`) | Recupera reportes estratégicos previos antes de investigar desde cero. |
| `save_and_index_report` | 9 campos de `StrategicReport` | Disco (`data/reportes/`) + FAISS | Persiste el reporte en JSON/Markdown y lo vectoriza para consultas futuras. |

### E. Visión Multimodal ([tools/vision_nim.py](../tools/vision_nim.py))

| Tool | Parámetros | Motor | Descripción |
|---|---|---|---|
| `analyze_catalog_photo` | `image_b64="ACTIVE_IMAGE"`, `categoria_sugerida` | NVIDIA NIM Vision VL | Detecta productos visibles en anaquel/catálogo y propone SKU, categoría y precio estimado. |
| `analyze_receipt` | `image_b64="ACTIVE_IMAGE"` | NVIDIA NIM Vision VL | Ejecuta OCR sobre comprobantes/facturas y clasifica en `inversion_inventario` vs `gasto_operativo`. |
| `analyze_pos_items` | `image_b64="ACTIVE_IMAGE"` | NVIDIA NIM Vision VL | Detecta artículos y cantidades colocados sobre la barra POS para cotizar contra PostgreSQL. |

### F. Medios, Pagos Digitales, RAG y Few-Shot ([tools/media_tools.py](../tools/media_tools.py), [tools/rag_nemo.py](../tools/rag_nemo.py), [tools/few_shot_retriever.py](../tools/few_shot_retriever.py))

| Tool | Parámetros | Motor | Descripción |
|---|---|---|---|
| `consultar_guia_pago_digital` | `metodo_pago`, `pantalla`, `error_code`, `duda` | RAG CoDi/SPEI/DiMo (`buscar_guia_pago`) | Recupera pasos exactos, límites, solución de errores y advertencias de seguridad de `guias.json` y `conocimiento.jsonl`. |
| `generate_promo_copy` | `product_name`, `trigger` | Plantilla comercial | Genera copy persuasivo para WhatsApp Status o mostrador. |
| `generate_video_prompt` | `product_name`, `trigger` | Especificación 9:16 | Produce prompt cinematográfico vertical 9:16 de 5 s y guion de locución. |
| `generate_cta` | `product_name`, `discount_pct` | Plantilla comercial | Genera llamado a la acción inmediato. |
| `consultar_conocimiento_comercial` | `consulta`, `categoria` | RAG Dual (FAISS + NeMo Rerank) | Consulta políticas locales y normativa de pagos digitales. |
| `indexar_documento_comercial` | `texto`, `categoria`, `tema` | FAISS persistente | Agrega dinámicamente nuevas reglas comerciales al índice vectorial. |
| `retrieve_few_shots` | `agent_role`, `query`, `k: int = 2` | Repositorio interno | Recupera ejemplos Few-Shot específicos por rol. |

---

## 3. Exportador MCP ([tools/mcp_exporter.py](../tools/mcp_exporter.py))

El módulo agrupa las **24 herramientas comerciales** en `ALL_COMMERCE_TOOLS` y expone `export_mcp_manifest()`, generando un JSON compatible con **Model Context Protocol (MCP)** (`server: "tiendita-ia-mcp"`, `version: "1.0.0"`) con `name`, `description` y `inputSchema` listo para clientes externos o agentes remotos.
