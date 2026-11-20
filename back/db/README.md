# Base de datos (PostgreSQL 16 + pgvector)

## Arrancar

```bash
cd back
cp .env.example .env          # cambia DB_PASSWORD
docker compose up -d db
docker compose logs -f db     # al final imprime cuántos productos, ventas y alertas cargó
```

Conexión: `postgresql://tiendita:<DB_PASSWORD>@localhost:5432/tiendita` (`DATABASE_URL` en `.env`).

Los scripts de `db/init/` **solo corren la primera vez** (volumen vacío). Si cambias un `.sql` o el catálogo:

```bash
docker compose down -v && docker compose up -d db    # borra TODO y vuelve a crear
```

Consola: `docker exec -it tiendita-db psql -U tiendita -d tiendita`

## Archivos

| Archivo | Contenido |
|---|---|
| `db/init/001_extensiones_tipos.sql` | Extensiones (pgvector, pg_trgm, unaccent) y enums |
| `db/init/002_p0_cobro.sql` | P0: `producto`, `producto_alias`, `inferencia_vision`, `venta`, `venta_item`, `movimiento_inventario`, `pago` |
| `db/init/003_p1_inventario_tickets.sql` | P1: `proveedor`, `comprobante`, `lote`, `deteccion`, `historial_precio`, `corte_caja` |
| `db/init/004_p2_asistente.sql` | P2: `negocio`, `conversacion`, `mensaje`, `accion_propuesta`, `alerta`, `promocion`, `reporte`, RAG |
| `db/init/005_vistas.sql` | Vistas `v_*` para agentes y dashboard + `buscar_productos(q, limite)` |
| `db/init/006_funciones_venta.sql` | `registrar_venta(jsonb)`: la venta completa en una transacción |
| `db/init/007_roles.sql` | Roles `ag_*` por agente (solo lectura de vistas + propuestas) |
| `db/init/090_semilla.sh` + `db/semilla/semilla.sql` | Datos de ejemplo **sintéticos** (`CARGAR_SEMILLA=0` para BD vacía) |
| `datos/catalogo.csv` | **Fuente única del catálogo**: sku, clase del detector, precio, alias. Lo usan la BD y el dataset de visión |

## Cómo usarla desde el back / los agentes

**Registrar una venta** (POST /ventas, `registrar_venta` del Vendedor): no escribas las tablas a mano; llama a la función con el JSON de `SolicitudVenta` de `front/src/api/esquemas.ts`:

```sql
SELECT registrar_venta(%s::jsonb);   -- devuelve el JSON de RespuestaVenta
```

Hace todo en una transacción: idempotencia por `id_local`, descuento de existencia y de lotes (primero el que caduca antes), bitácora, pago ligado (efectivo → `conciliado`, digital → `pendiente`) y alertas.

| SQLSTATE | HTTP | Cuándo | `DETAIL` (JSON) |
|---|---|---|---|
| `TD409` | 409 | Sin existencia suficiente (solo en línea; con `fuera_de_linea: true` se registra y crea alerta) | `{"sku", "existencia"}` |
| `TD404` | 404 | SKU inexistente | `{"sku"}` |
| `TD400` | 400 | Sin `id_local`, sin productos, o cantidad decimal en producto por pieza | `{"sku"}` |

**Buscar productos** (GET /productos?q=, `find_product_by_name_or_alias`): `SELECT * FROM buscar_productos('la coca', 10);` encuentra por nombre, sku, código de barras o alias, con tolerancia a errores.

**SQL de un agente**: dentro de una transacción, `SET LOCAL ROLE ag_analista;` (o el que toque) y `SET LOCAL statement_timeout = '3s';`. Los agentes leen vistas `v_*`; las escrituras de negocio solo se ejecutan cuando el tendero confirma.

**Sesiones de LangGraph**: usar `PostgresSaver` (`langgraph-checkpoint-postgres`) con `DATABASE_URL` y llamar `setup()` una vez; crea sus propias tablas. `conversacion.id` = `thread_id`.

## Pendiente de decidir

- Dimensión de `fragmento.embedding` (hoy `vector(1024)`, para `nv-embedqa-e5-v5`): ajustarla al modelo de embeddings que se use antes de cargar documentos.
- Las ventas de ejemplo son historial: no descuentan la existencia actual, que es la del CSV.
