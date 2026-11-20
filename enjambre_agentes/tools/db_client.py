"""
Cliente de Base de Datos real para Tiendita IA conectado a PostgreSQL (`DATABASE_URL` / tiendita-db).
Gestiona un pool de conexiones reutilizables con cierre limpio (`close_db_pool`) y
verificación en vivo (`verify_db_connection`).

Consulta exclusivamente las vistas y funciones oficiales de PostgreSQL sin datos simulados:
  - v_inventario
  - v_por_caducar
  - v_stock_bajo
  - v_margen_producto
  - v_flujo_caja
  - v_ventas_dia
  - buscar_productos(q, limite)
"""
from __future__ import annotations

import contextlib
import json
import queue
import threading
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Optional

import psycopg
from langchain_core.tools import tool

from config.keys import DATABASE_URL

# ---------------------------------------------------------------------------
# Pool de conexiones PostgreSQL thread-safe con cierre limpio
# ---------------------------------------------------------------------------

_POOL_MAX_SIZE = 8
_pool_queue: queue.LifoQueue[psycopg.Connection] = queue.LifoQueue(maxsize=_POOL_MAX_SIZE)
_pool_lock = threading.Lock()
_pool_closed = False


def _clean_db_url() -> str:
    """Convierte DATABASE_URL (incluyendo formatos asyncpg) a DSN estándar de psycopg."""
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _open_new_connection() -> psycopg.Connection:
    return psycopg.connect(_clean_db_url(), connect_timeout=5)


@contextlib.contextmanager
def _get_connection() -> Iterator[psycopg.Connection]:
    """
    Obtiene una conexión real del pool de PostgreSQL y la devuelve limpia al terminar.
    Compatible con el patrón `with _get_connection() as conn:` en todas las herramientas.
    """
    global _pool_closed
    conn: Optional[psycopg.Connection] = None

    with _pool_lock:
        if _pool_closed:
            _pool_closed = False

    try:
        while True:
            try:
                candidate = _pool_queue.get_nowait()
                if not candidate.closed:
                    conn = candidate
                    break
            except queue.Empty:
                break

        if conn is None:
            conn = _open_new_connection()

        yield conn

        # Si quedó una transacción abierta sin commit explícito, asegurar estado limpio
        if not conn.closed and conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            conn.commit()
    except Exception:
        if conn is not None and not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            conn = None
        raise
    finally:
        if conn is not None and not conn.closed:
            try:
                _pool_queue.put_nowait(conn)
            except queue.Full:
                try:
                    conn.close()
                except Exception:
                    pass


def close_db_pool() -> int:
    """Cierra todas las conexiones activas en el pool de PostgreSQL limpiamente."""
    global _pool_closed
    cerradas = 0
    with _pool_lock:
        _pool_closed = True
        while True:
            try:
                conn = _pool_queue.get_nowait()
                if not conn.closed:
                    conn.close()
                cerradas += 1
            except queue.Empty:
                break
    return cerradas


def verify_db_connection() -> Dict[str, Any]:
    """
    Valida la conexión real contra PostgreSQL (`DATABASE_URL`) y obtiene métricas en vivo
    de las vistas oficiales del negocio. No devuelve datos simulados.
    """
    dsn = _clean_db_url()
    # Ocultar contraseña al mostrar el destino en consola
    safe_dsn = dsn
    if "@" in dsn and "://" in dsn:
        proto, resto = dsn.split("://", 1)
        creds, hostpart = resto.split("@", 1)
        user = creds.split(":", 1)[0]
        safe_dsn = f"{proto}://{user}:***@{hostpart}"

    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user, split_part(version(), ' ', 2)")
                db_name, db_user, pg_ver = cur.fetchone()

                cur.execute("SELECT count(*) FROM v_inventario")
                total_productos = int(cur.fetchone()[0])

                cur.execute("SELECT count(*) FROM v_por_caducar")
                por_caducar = int(cur.fetchone()[0])

                cur.execute("SELECT count(*) FROM v_stock_bajo")
                stock_bajo = int(cur.fetchone()[0])

                cur.execute("SELECT count(*), coalesce(sum(total), 0) FROM venta WHERE estado = 'registrada'")
                total_ventas, ingresos_totales = cur.fetchone()

        return {
            "connected": True,
            "dsn": safe_dsn,
            "database": db_name,
            "user": db_user,
            "pg_version": pg_ver,
            "productos_activos": total_productos,
            "lotes_por_caducar": por_caducar,
            "alertas_stock_bajo": stock_bajo,
            "ventas_registradas": int(total_ventas),
            "ingresos_acumulados": float(ingresos_totales),
        }
    except Exception as exc:
        return {
            "connected": False,
            "dsn": safe_dsn,
            "error": str(exc),
        }


def _serializar_dato(obj: Any) -> Any:
    """Helper para serializar Decimals y fechas a JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


# Contenedores vacíos mantenidos solo por compatibilidad de firmas legacy (cero datos simulados)
_MOCK_INVENTORY: List[Dict[str, Any]] = []
_MOCK_SALES: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Herramientas @tool conectadas exclusivamente a PostgreSQL real
# ---------------------------------------------------------------------------

@tool
def query_inventory(sku: Optional[str] = None, category: Optional[str] = None) -> str:
    """
    Consulta existencias reales de inventario en PostgreSQL (vista v_inventario / buscar_productos).
    Devuelve precios de venta al público, existencias y alertas de stock bajo.
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                if sku:
                    cur.execute(
                        "SELECT sku, nombre, precio_unitario, existencia, unidad "
                        "FROM buscar_productos(%s, 10)",
                        (sku,),
                    )
                    filas = cur.fetchall()
                    if filas:
                        salida = [{
                            "sku": r[0],
                            "nombre": r[1],
                            "precio_venta": float(r[2]),
                            "stock_actual": float(r[3]),
                            "unidad": r[4],
                        } for r in filas]
                        return json.dumps(
                            {"status": "success", "fuente": "postgresql", "conteo": len(salida), "datos": salida},
                            ensure_ascii=False,
                        )

                query = (
                    "SELECT sku, nombre, categoria, unidad, precio_venta, existencia, "
                    "stock_minimo, bajo, proxima_caducidad FROM v_inventario"
                )
                params: list[Any] = []
                if category:
                    query += " WHERE lower(categoria) = lower(%s)"
                    params.append(category)
                query += " ORDER BY nombre LIMIT 50"

                cur.execute(query, tuple(params))
                filas = cur.fetchall()
                salida = [{
                    "sku": r[0],
                    "nombre": r[1],
                    "categoria": r[2] or "general",
                    "unidad": r[3],
                    "precio_venta": float(r[4]),
                    "stock_actual": float(r[5]),
                    "stock_minimo": float(r[6]),
                    "bajo": r[7],
                    "caducidad_proxima": _serializar_dato(r[8]),
                } for r in filas]
                return json.dumps(
                    {"status": "success", "fuente": "postgresql", "conteo": len(salida), "datos": salida},
                    ensure_ascii=False,
                )
    except Exception as e:
        return json.dumps({"status": "error", "fuente": "postgresql", "error": str(e)}, ensure_ascii=False)


@tool
def query_expiring_soon(days_ahead: int = 7) -> str:
    """
    Recupera los productos cuyos lotes caducan dentro de los próximos N días
    consultando en vivo la vista v_por_caducar / tabla lote de PostgreSQL.
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.sku, p.nombre, l.cantidad_actual, l.caducidad,
                           (l.caducidad - current_date) AS dias_restantes,
                           p.precio_venta, l.id AS lote_id
                      FROM lote l
                      JOIN producto p ON p.id = l.producto_id
                     WHERE l.cantidad_actual > 0
                       AND l.caducidad IS NOT NULL
                       AND l.caducidad <= current_date + (%s * interval '1 day')
                     ORDER BY dias_restantes ASC
                    """,
                    (days_ahead,),
                )
                filas = cur.fetchall()
                alertas = [{
                    "sku": r[0],
                    "nombre": r[1],
                    "stock_por_vencer": float(r[2]),
                    "caducidad": _serializar_dato(r[3]),
                    "dias_restantes": int(r[4]),
                    "precio_venta": float(r[5]),
                    "lote_id": str(r[6]),
                } for r in filas]
                return json.dumps(
                    {
                        "status": "alerts_found" if alertas else "no_alerts",
                        "fuente": "postgresql",
                        "days_ahead": days_ahead,
                        "total_alertas": len(alertas),
                        "items": alertas,
                    },
                    ensure_ascii=False,
                )
    except Exception as e:
        return json.dumps({"status": "error", "fuente": "postgresql", "error": str(e)}, ensure_ascii=False)


@tool
def query_sales(date_from: Optional[str] = None, date_to: Optional[str] = None, sku: Optional[str] = None) -> str:
    """
    Consulta ventas reales y totales recaudados en PostgreSQL (vista v_ventas_dia).
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT dia, ventas, ingresos, ticket_promedio FROM v_ventas_dia"
                params: list[Any] = []
                condiciones: list[str] = []
                if date_from:
                    condiciones.append("dia >= %s")
                    params.append(date_from)
                if date_to:
                    condiciones.append("dia <= %s")
                    params.append(date_to)
                if condiciones:
                    query += " WHERE " + " AND ".join(condiciones)
                query += " ORDER BY dia DESC LIMIT 30"

                cur.execute(query, tuple(params))
                filas = cur.fetchall()
                ventas_dias = [{
                    "dia": _serializar_dato(r[0]),
                    "total_ventas": int(r[1]),
                    "ingresos": float(r[2]),
                    "ticket_promedio": float(r[3]),
                } for r in filas]
                total_acumulado = round(sum(d["ingresos"] for d in ventas_dias), 2)
                return json.dumps({
                    "status": "success",
                    "fuente": "postgresql",
                    "total_acumulado": total_acumulado,
                    "resumen_dias": ventas_dias,
                }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "fuente": "postgresql", "error": str(e)}, ensure_ascii=False)
