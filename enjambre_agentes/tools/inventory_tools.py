"""
Herramientas de Inventario y Control de Stock para el Agente de Control.
Todas las operaciones de escritura (registro, actualización de stock) van a PostgreSQL.
Las consultas de lectura usan las vistas oficiales (v_inventario, v_stock_bajo, v_por_caducar).
Fallback en memoria (_MOCK_INVENTORY) si la BD no está disponible.
"""
from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from langchain_core.tools import tool

from tools.db_client import _MOCK_INVENTORY, _get_connection, _serializar_dato


# ---------------------------------------------------------------------------
# Escritura: registro y actualización de productos
# ---------------------------------------------------------------------------

@tool
def register_product(
    sku: str,
    nombre: str,
    precio_venta: float,
    costo_unitario: float,
    categoria: str = "general",
    stock_inicial: float = 0,
    unidad: Literal["pieza", "kg", "litro", "paquete", "caja"] = "pieza",
    fecha_caducidad: Optional[str] = None,
) -> str:
    """
    Registra un nuevo producto en el catálogo PostgreSQL y, si se indica fecha_caducidad,
    crea su primer lote. Fallback: agrega al catálogo en memoria.

    Args:
        sku: Código único del producto (se normaliza a mayúsculas).
        nombre: Nombre visible en mostrador.
        precio_venta: Precio de venta al público (MXN).
        costo_unitario: Costo de compra (MXN) — protegido, no visible en mostrador.
        categoria: Categoría del producto (ej. 'lacteos', 'bebidas', 'abarrotes').
        stock_inicial: Existencias al momento del alta.
        unidad: Unidad de medida ('pieza', 'kg', 'litro', 'paquete', 'caja').
        fecha_caducidad: ISO 8601 (YYYY-MM-DD) si el producto caduca.
    """
    sku_norm = sku.strip().upper()

    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si ya existe
                cur.execute("SELECT sku FROM producto WHERE sku = %s", (sku_norm,))
                if cur.fetchone():
                    return json.dumps({"status": "error", "message": f"El producto {sku_norm} ya existe."}, ensure_ascii=False)

                # Buscar o crear categoría
                cur.execute(
                    "INSERT INTO categoria (nombre) VALUES (lower(%s)) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING id",
                    (categoria,),
                )
                cat_id = cur.fetchone()[0]

                # Insertar producto
                cur.execute("""
                    INSERT INTO producto (sku, nombre, categoria_id, precio_venta, costo, existencia,
                                         stock_minimo, unidad, origen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'chat')
                    RETURNING id
                """, (sku_norm, nombre, cat_id, precio_venta, costo_unitario, stock_inicial, 3, unidad))
                prod_id = cur.fetchone()[0]

                # Crear lote inicial si tiene caducidad o stock
                if stock_inicial > 0:
                    cur.execute("""
                        INSERT INTO lote (producto_id, cantidad_inicial, cantidad_actual, caducidad, costo_unitario)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (prod_id, stock_inicial, stock_inicial, fecha_caducidad, costo_unitario))

                    # Registrar movimiento de entrada (enum Postgres: 'entrada')
                    cur.execute("""
                        INSERT INTO movimiento_inventario (producto_id, tipo, cantidad)
                        VALUES (%s, 'entrada', %s)
                    """, (prod_id, stock_inicial))

            conn.commit()

        nuevo = {
            "sku": sku_norm, "nombre": nombre, "categoria": categoria,
            "precio_venta": precio_venta, "costo_unitario": costo_unitario,
            "stock_actual": stock_inicial, "unidad": unidad,
            "caducidad": fecha_caducidad,
        }
        return json.dumps({"status": "created", "fuente": "postgresql", "producto": nuevo}, ensure_ascii=False)

    except Exception as e:
        # Fallback en memoria
        for p in _MOCK_INVENTORY:
            if p["sku"] == sku_norm:
                return json.dumps({"status": "error", "message": f"El producto {sku_norm} ya existe."}, ensure_ascii=False)
        nuevo = {
            "sku": sku_norm, "nombre": nombre, "categoria": categoria.lower(),
            "precio_venta": precio_venta, "costo_unitario": costo_unitario,
            "stock_actual": stock_inicial, "stock_minimo": 3,
            "caducidad": fecha_caducidad or "2027-12-31",
        }
        _MOCK_INVENTORY.append(nuevo)
        return json.dumps({
            "status": "created",
            "fuente": "fallback_memoria",
            "nota": f"BD no disponible: {e}",
            "producto": nuevo,
        }, ensure_ascii=False)


@tool
def update_stock(
    sku: str,
    cantidad: float,
    tipo_movimiento: Literal["entrada_compra", "merma", "ajuste_inventario"],
    fecha_caducidad: Optional[str] = None,
    costo_unitario: Optional[float] = None,
) -> str:
    """
    Modifica las existencias físicas de un producto. Escribe en movimiento_inventario
    (y lote si es entrada_compra con caducidad). Fallback en memoria.

    Args:
        sku: SKU del producto a actualizar.
        cantidad: Unidades a sumar (entradas) o restar (mermas/ajustes). Siempre positivo.
        tipo_movimiento: Tipo de movimiento ('entrada_compra', 'merma', 'ajuste_inventario').
        fecha_caducidad: Requerido para entrada_compra con caducidad (YYYY-MM-DD).
        costo_unitario: Costo por unidad para el nuevo lote (opcional, para entrada_compra).
    """
    sku_norm = sku.strip().upper()
    delta = abs(cantidad) if tipo_movimiento == "entrada_compra" else -abs(cantidad)

    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, existencia FROM producto WHERE sku = %s AND activo FOR UPDATE",
                    (sku_norm,)
                )
                row = cur.fetchone()
                if not row:
                    return json.dumps({"status": "not_found", "message": f"SKU {sku_norm} no registrado."}, ensure_ascii=False)

                prod_id, existencia_anterior = row
                existencia_nueva = float(existencia_anterior) + delta

                cur.execute(
                    "UPDATE producto SET existencia = %s WHERE id = %s",
                    (existencia_nueva, prod_id)
                )

                # Crear lote en entradas con caducidad
                lote_id = None
                if tipo_movimiento == "entrada_compra":
                    cur.execute("""
                        INSERT INTO lote (producto_id, cantidad_inicial, cantidad_actual,
                                          caducidad, costo_unitario)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (prod_id, abs(cantidad), abs(cantidad), fecha_caducidad, costo_unitario))
                    lote_id = cur.fetchone()[0]

                tipo_db_map = {
                    "entrada_compra": "entrada",
                    "merma": "merma",
                    "ajuste_inventario": "salida",
                }
                tipo_db = tipo_db_map.get(tipo_movimiento, "entrada" if delta >= 0 else "salida")

                cur.execute("""
                    INSERT INTO movimiento_inventario (producto_id, lote_id, tipo, cantidad)
                    VALUES (%s, %s, %s, %s)
                """, (prod_id, lote_id, tipo_db, delta))

            conn.commit()

        return json.dumps({
            "status": "updated",
            "fuente": "postgresql",
            "sku": sku_norm,
            "stock_anterior": float(existencia_anterior),
            "stock_nuevo": existencia_nueva,
            "tipo_movimiento": tipo_movimiento,
        }, ensure_ascii=False)

    except Exception as e:
        # Fallback en memoria
        for p in _MOCK_INVENTORY:
            if p["sku"] == sku_norm:
                anterior = p.get("stock_actual", 0)
                p["stock_actual"] = max(0, anterior + delta)
                return json.dumps({
                    "status": "updated",
                    "fuente": "fallback_memoria",
                    "nota": f"BD no disponible: {e}",
                    "sku": sku_norm,
                    "stock_anterior": anterior,
                    "stock_nuevo": p["stock_actual"],
                    "tipo_movimiento": tipo_movimiento,
                }, ensure_ascii=False)
        return json.dumps({"status": "not_found", "message": f"SKU {sku_norm} no registrado."}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Consultas de lectura
# ---------------------------------------------------------------------------

@tool
def check_expiry_alerts(days_ahead: int = 7) -> str:
    """
    Evalúa productos con riesgo de vencimiento cercano en PostgreSQL (v_por_caducar)
    para sugerir acciones: remate de precio, merma o priorización en ventas.

    Args:
        days_ahead: Número de días hacia adelante para alertar (default: 7).
    """
    from tools.db_client import query_expiring_soon
    return query_expiring_soon.invoke({"days_ahead": days_ahead})


@tool
def get_low_stock_alerts(threshold: Optional[float] = None) -> str:
    """
    Identifica artículos cuyo inventario está igual o por debajo del mínimo configurado,
    consultando la vista v_stock_bajo en PostgreSQL. Fallback en memoria.

    Args:
        threshold: Umbral personalizado. Si es None, usa el stock_minimo de cada producto.
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                if threshold is not None:
                    cur.execute("""
                        SELECT sku, nombre, unidad, existencia, stock_minimo
                          FROM producto
                         WHERE activo AND existencia <= %s
                         ORDER BY existencia ASC
                    """, (threshold,))
                else:
                    cur.execute("""
                        SELECT sku, nombre, unidad, existencia, stock_minimo
                          FROM v_stock_bajo
                         ORDER BY existencia ASC
                    """)
                filas = cur.fetchall()
                alertas = [
                    {
                        "sku": r[0],
                        "nombre": r[1],
                        "unidad": r[2],
                        "stock_actual": float(r[3]),
                        "stock_minimo": float(r[4]),
                        "sugerencia_pedido": round(float(r[4]) * 3 - float(r[3]), 1),
                    }
                    for r in filas
                ]
        return json.dumps({
            "status": "success",
            "fuente": "postgresql",
            "total_alertas": len(alertas),
            "alertas_stock_bajo": alertas,
        }, ensure_ascii=False)

    except Exception as e:
        # Fallback en memoria
        alertas = []
        for p in _MOCK_INVENTORY:
            umbral = threshold if threshold is not None else p.get("stock_minimo", 5)
            if p.get("stock_actual", 0) <= umbral:
                alertas.append({
                    "sku": p["sku"],
                    "nombre": p["nombre"],
                    "stock_actual": p.get("stock_actual", 0),
                    "stock_minimo": umbral,
                    "sugerencia_pedido": int(umbral * 3) - p.get("stock_actual", 0),
                })
        return json.dumps({
            "status": "success",
            "fuente": "fallback_memoria",
            "nota": str(e),
            "total_alertas": len(alertas),
            "alertas_stock_bajo": alertas,
        }, ensure_ascii=False)


@tool
def get_product_detail(sku: str) -> str:
    """
    Consulta el detalle completo de un producto en v_inventario: precio, costo,
    existencia, stock mínimo, categoría y próxima caducidad de lote activo.

    Args:
        sku: SKU exacto del producto (ej. 'COCA-600').
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sku, nombre, categoria, unidad, precio_venta, costo,
                           existencia, stock_minimo, bajo, proxima_caducidad
                      FROM v_inventario
                     WHERE sku = %s
                """, (sku.strip().upper(),))
                row = cur.fetchone()
                if not row:
                    return json.dumps({"status": "not_found", "message": f"SKU {sku} no encontrado."}, ensure_ascii=False)
                return json.dumps({
                    "status": "found",
                    "producto": {
                        "sku": row[0], "nombre": row[1], "categoria": row[2],
                        "unidad": row[3], "precio_venta": float(row[4]),
                        "costo": float(row[5]) if row[5] else None,
                        "existencia": float(row[6]), "stock_minimo": float(row[7]),
                        "bajo_minimo": row[8],
                        "proxima_caducidad": _serializar_dato(row[9]),
                    }
                }, ensure_ascii=False)
    except Exception as e:
        prod = next((p for p in _MOCK_INVENTORY if p["sku"] == sku.strip().upper()), None)
        if prod:
            return json.dumps({"status": "found", "fuente": "fallback_memoria", "producto": prod}, ensure_ascii=False)
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

