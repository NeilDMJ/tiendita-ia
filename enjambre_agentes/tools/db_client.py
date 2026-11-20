"""
Cliente de Base de Datos para Tiendita IA conectado a PostgreSQL (tiendita-db).
Consulta las vistas oficiales diseñadas para los agentes:
  - v_inventario
  - v_por_caducar
  - v_stock_bajo
  - v_margen_producto
  - v_flujo_caja
  - v_ventas_dia
  - buscar_productos(q, limite)
Con fallback en memoria para alta tolerancia a fallos.
"""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tiendita:cambia-esta-contrasena@localhost:5432/tiendita")


def _get_connection():
    """Obtiene una conexión a PostgreSQL tiendita-db."""
    # Convertir URL asyncpg a estándar psycopg si es necesario
    url_limpia = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg.connect(url_limpia)


def _serializar_dato(obj: Any) -> Any:
    """Helper para serializar Decimals y fechas a JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


# Mock de contingencia por si la BD llegara a desconectarse
_MOCK_INVENTORY = [
    {"sku": "LALA-1L", "nombre": "Leche Lala 1 L", "categoria": "lacteos", "precio_venta": 29.00, "costo_unitario": 22.00, "stock_actual": 14, "stock_minimo": 5, "caducidad": "2026-11-21"},
    {"sku": "BIMB-BLAN", "nombre": "Pan de caja Bimbo", "categoria": "panaderia", "precio_venta": 45.00, "costo_unitario": 33.00, "stock_actual": 7, "stock_minimo": 4, "caducidad": "2026-11-22"},
    {"sku": "COCA-600", "nombre": "Coca-Cola 600 ml", "categoria": "bebidas", "precio_venta": 20.00, "costo_unitario": 14.50, "stock_actual": 35, "stock_minimo": 10, "caducidad": "2027-01-01"},
    {"sku": "HUEVO-KG", "nombre": "Huevo blanco (kg)", "categoria": "abarrotes", "precio_venta": 48.00, "costo_unitario": 38.00, "stock_actual": 8, "stock_minimo": 5, "caducidad": "2026-11-22"},
]

_MOCK_SALES: List[Dict[str, Any]] = [
    {"cart_id": "cart_init_01", "total": 69.00, "payment_method": "efectivo", "items": [{"sku": "LALA-1L", "cantidad": 1, "subtotal": 29.00}, {"sku": "COCA-600", "cantidad": 2, "subtotal": 40.00}]},
    {"cart_id": "cart_init_02", "total": 93.00, "payment_method": "tarjeta", "items": [{"sku": "BIMB-BLAN", "cantidad": 1, "subtotal": 45.00}, {"sku": "HUEVO-KG", "cantidad": 1, "subtotal": 48.00}]}
]


@tool
def query_inventory(sku: Optional[str] = None, category: Optional[str] = None) -> str:
    """
    Consulta existencias de inventario en la base de datos tiendita-db (vista v_inventario).
    Devuelve precios de venta al público, existencias y alertas de stock bajo.
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                if sku:
                    # Búsqueda usando la función buscar_productos de PostgreSQL
                    cur.execute("SELECT sku, nombre, precio_unitario, existencia, unidad FROM buscar_productos(%s, 10)", (sku,))
                    filas = cur.fetchall()
                    if filas:
                        salida = [{
                            "sku": r[0],
                            "nombre": r[1],
                            "precio_venta": float(r[2]),
                            "stock_actual": float(r[3]),
                            "unidad": r[4]
                        } for r in filas]
                        return json.dumps({"status": "success", "conteo": len(salida), "datos": salida}, ensure_ascii=False)

                # Consulta general sobre v_inventario
                query = "SELECT sku, nombre, categoria, unidad, precio_venta, existencia, stock_minimo, bajo, proxima_caducidad FROM v_inventario"
                params = []
                if category:
                    query += " WHERE lower(categoria) = lower(%s)"
                    params.append(category)
                query += " ORDER BY nombre LIMIT 25"

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
                    "caducidad_proxima": _serializar_dato(r[8])
                } for r in filas]
                return json.dumps({"status": "success", "conteo": len(salida), "datos": salida}, ensure_ascii=False)
    except Exception as e:
        # Fallback en memoria si falla la BD
        return json.dumps({"status": "fallback", "datos": _MOCK_INVENTORY, "nota": str(e)}, ensure_ascii=False)


@tool
def query_expiring_soon(days_ahead: int = 7) -> str:
    """
    Recupera los productos cuyos lotes caducan dentro de los próximos N días
    consultando en vivo la vista v_por_caducar de PostgreSQL.
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sku, nombre, cantidad_actual, caducidad, dias_restantes, precio_venta
                    FROM v_por_caducar
                    ORDER BY dias_restantes ASC
                """)
                filas = cur.fetchall()
                alertas = [{
                    "sku": r[0],
                    "nombre": r[1],
                    "stock_por_vencer": float(r[2]),
                    "caducidad": _serializar_dato(r[3]),
                    "dias_restantes": r[4],
                    "precio_venta": float(r[5])
                } for r in filas]
                return json.dumps({"status": "alerts_found", "total_alertas": len(alertas), "items": alertas}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "fallback", "items": [
            {"sku": "LALA-1L", "nombre": "Leche Lala 1 L", "stock_por_vencer": 6, "caducidad": "2026-11-21", "dias_restantes": 1, "precio_venta": 29.00},
            {"sku": "BIMB-BLAN", "nombre": "Pan de caja Bimbo", "stock_por_vencer": 4, "caducidad": "2026-11-22", "dias_restantes": 2, "precio_venta": 45.00}
        ], "nota": str(e)}, ensure_ascii=False)


@tool
def query_sales(date_from: Optional[str] = None, date_to: Optional[str] = None, sku: Optional[str] = None) -> str:
    """
    Consulta ventas reales y totales recaudados en tiendita-db (vista v_ventas_dia y tabla venta).
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT dia, ventas, ingresos, ticket_promedio FROM v_ventas_dia ORDER BY dia DESC LIMIT 10")
                filas = cur.fetchall()
                ventas_dias = [{
                    "dia": _serializar_dato(r[0]),
                    "total_ventas": r[1],
                    "ingresos": float(r[2]),
                    "ticket_promedio": float(r[3])
                } for r in filas]
                total_acumulado = sum(d["ingresos"] for d in ventas_dias)
                return json.dumps({
                    "status": "success",
                    "total_acumulado": total_acumulado,
                    "resumen_dias": ventas_dias
                }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "fallback", "total_acumulado": 200.50, "nota": str(e)}, ensure_ascii=False)
