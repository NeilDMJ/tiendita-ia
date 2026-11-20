"""
Herramientas de Mostrador y Punto de Venta (POS) para el Agente Vendedor.
Gestión de carritos en memoria + liquidación real vía función registrar_venta() en PostgreSQL.

Flujo:
  create_cart() → add_to_cart() [× N] → (optional) suggest_upsell() → checkout_cart()

checkout_cart() llama a SELECT registrar_venta(sol jsonb) definida en 006_funciones_venta.sql,
que valida existencias, descuenta stock, registra lotes FEFO y persiste el pago en una sola
transacción atómica. El mock _MOCK_SALES/INVENTORY sólo actúa si falla la conexión a BD.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Literal, Optional

from langchain_core.tools import tool

from tools.db_client import _MOCK_INVENTORY, _MOCK_SALES, _get_connection, _serializar_dato

# Sesiones de carritos en memoria (una por conversación; se persisten al hacer checkout)
_ACTIVE_CARTS: Dict[str, Dict] = {}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _lookup_product_db(sku: str) -> Optional[Dict[str, Any]]:
    """Busca un producto por SKU en la BD (v_inventario / buscar_productos)."""
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sku, nombre, precio_unitario, existencia, unidad "
                    "FROM buscar_productos(%s, 1)",
                    (sku,)
                )
                row = cur.fetchone()
                if row:
                    return {
                        "sku": row[0],
                        "nombre": row[1],
                        "precio_venta": float(row[2]),
                        "stock_actual": float(row[3]),
                        "unidad": row[4],
                    }
    except Exception:
        pass
    return None


def _lookup_product_fallback(sku: str) -> Optional[Dict[str, Any]]:
    """Fallback en memoria si falla la BD."""
    return next((p for p in _MOCK_INVENTORY if p["sku"] == sku.strip().upper()), None)


# ---------------------------------------------------------------------------
# Herramientas POS
# ---------------------------------------------------------------------------

@tool
def create_cart() -> str:
    """
    Inicia una nueva sesión de venta / carrito en mostrador.
    Devuelve un cart_id único para usarlo en add_to_cart y checkout_cart.
    """
    cid = f"CART-{str(uuid.uuid4())[:8].upper()}"
    _ACTIVE_CARTS[cid] = {
        "cart_id": cid,
        "items": [],
        "subtotal": 0.0,
        "descuento": 0.0,
        "total": 0.0,
    }
    return json.dumps({"status": "created", "cart_id": cid}, ensure_ascii=False)


@tool
def add_to_cart(cart_id: str, sku: str, quantity: float = 1) -> str:
    """
    Agrega un producto al carrito activo cotizando su precio desde la base de datos.
    Busca primero en PostgreSQL (buscar_productos); si falla, usa el catálogo en memoria.

    Args:
        cart_id: Identificador del carrito activo (de create_cart).
        sku: SKU exacto del producto (ej. 'COCA-600') o nombre parcial para búsqueda.
        quantity: Cantidad a agregar (soporta decimales para productos por kg/l).
    """
    if cart_id not in _ACTIVE_CARTS:
        _ACTIVE_CARTS[cart_id] = {
            "cart_id": cart_id, "items": [], "subtotal": 0.0, "descuento": 0.0, "total": 0.0
        }
    cart = _ACTIVE_CARTS[cart_id]

    sku_norm = sku.strip().upper()
    prod = _lookup_product_db(sku_norm) or _lookup_product_fallback(sku_norm)

    if not prod:
        return json.dumps(
            {"status": "error", "message": f"Producto '{sku}' no encontrado en inventario."},
            ensure_ascii=False,
        )

    precio = prod["precio_venta"]
    subtotal_item = round(precio * quantity, 2)

    # Si el SKU ya existe en el carrito, suma las cantidades
    for item in cart["items"]:
        if item["sku"] == prod["sku"]:
            item["cantidad"] = round(item["cantidad"] + quantity, 3)
            item["subtotal"] = round(item["cantidad"] * precio, 2)
            break
    else:
        cart["items"].append({
            "sku": prod["sku"],
            "nombre": prod["nombre"],
            "cantidad": quantity,
            "precio_unitario": precio,
            "subtotal": subtotal_item,
        })

    cart["subtotal"] = round(sum(it["subtotal"] for it in cart["items"]), 2)
    cart["total"] = round(cart["subtotal"] - cart.get("descuento", 0.0), 2)

    return json.dumps({"status": "item_added", "cart": cart}, ensure_ascii=False)


@tool
def apply_discount(cart_id: str, discount_amount: float) -> str:
    """
    Aplica un descuento monetario fijo al carrito (en pesos MXN).

    Args:
        cart_id: Identificador del carrito.
        discount_amount: Monto a descontar del total (ej. 5.00 para $5 de descuento).
    """
    if cart_id not in _ACTIVE_CARTS:
        return json.dumps({"status": "error", "message": "Carrito no encontrado."}, ensure_ascii=False)

    cart = _ACTIVE_CARTS[cart_id]
    cart["descuento"] = round(discount_amount, 2)
    cart["total"] = round(cart["subtotal"] - cart["descuento"], 2)
    return json.dumps({"status": "discount_applied", "cart": cart}, ensure_ascii=False)


@tool
def checkout_cart(
    cart_id: str,
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "qr"],
    monto_recibido: float = 0.0,
    fuera_de_linea: bool = False,
) -> str:
    """
    Cierra la venta del carrito: persiste en PostgreSQL vía registrar_venta(),
    que valida existencias, descuenta stock, gestiona lotes FEFO y registra el pago.
    Si la BD no está disponible, usa el fallback en memoria (_MOCK_SALES).

    Args:
        cart_id: Identificador del carrito a cerrar.
        payment_method: Método de pago ('efectivo', 'tarjeta', 'transferencia', 'qr').
        monto_recibido: Efectivo entregado por el cliente (para calcular cambio).
        fuera_de_linea: Si True, permite vender aunque la existencia llegue a cero (venta offline).
    """
    cart = _ACTIVE_CARTS.get(cart_id)
    if not cart or not cart.get("items"):
        return json.dumps({"status": "error", "message": "Carrito vacío o no encontrado."}, ensure_ascii=False)

    id_local = str(uuid.uuid4())

    # --- Intentar con PostgreSQL (registrar_venta) ---
    items_jsonb = [
        {
            "sku": it["sku"],
            "cantidad": it["cantidad"],
            "precio_unitario": it["precio_unitario"],
        }
        for it in cart["items"]
    ]
    solicitud = {
        "id_local": id_local,
        "metodo_pago": payment_method,
        "recibido": monto_recibido or cart["total"],
        "fuera_de_linea": fuera_de_linea,
        "origen": "chat",
        "items": items_jsonb,
    }

    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT registrar_venta(%s::jsonb)", (json.dumps(solicitud),))
                respuesta = cur.fetchone()[0]  # jsonb devuelto por la función
            conn.commit()

        respuesta_dict = respuesta if isinstance(respuesta, dict) else json.loads(respuesta)
        cambio = round(monto_recibido - float(respuesta_dict.get("total", 0)), 2) if monto_recibido else 0.0
        del _ACTIVE_CARTS[cart_id]

        return json.dumps({
            "status": "success",
            "fuente": "postgresql",
            "ticket": respuesta_dict,
            "cambio": cambio,
            "items": cart["items"],
        }, ensure_ascii=False, default=_serializar_dato)

    except Exception as e:
        # --- Fallback en memoria ---
        venta_id = f"V-{str(uuid.uuid4())[:6].upper()}"
        for it in cart["items"]:
            prod = next((p for p in _MOCK_INVENTORY if p["sku"] == it["sku"]), None)
            if prod:
                prod["stock_actual"] = max(0, prod.get("stock_actual", 0) - it["cantidad"])

        registro = {
            "venta_id": venta_id,
            "cart_id": cart_id,
            "total": cart["total"],
            "metodo_pago": payment_method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "items": cart["items"],
        }
        _MOCK_SALES.append(registro)
        del _ACTIVE_CARTS[cart_id]

        cambio = round(monto_recibido - cart["total"], 2) if monto_recibido else 0.0
        return json.dumps({
            "status": "success",
            "fuente": "fallback_memoria",
            "nota": f"BD no disponible: {e}",
            "ticket": registro,
            "cambio": cambio,
        }, ensure_ascii=False)


@tool
def get_cart(cart_id: str) -> str:
    """
    Consulta el estado actual del carrito (ítems, subtotal, descuento, total).

    Args:
        cart_id: Identificador del carrito activo.
    """
    cart = _ACTIVE_CARTS.get(cart_id)
    if not cart:
        return json.dumps({"status": "not_found", "message": "El carrito no existe o ya fue cerrado."}, ensure_ascii=False)
    return json.dumps({"status": "ok", "cart": cart}, ensure_ascii=False)


@tool
def suggest_upsell(cart_id: str) -> str:
    """
    Consulta la vista v_coocurrencia en PostgreSQL para sugerir productos complementarios
    de alta coocurrencia en ventas reales. Fallback: reglas estáticas básicas.

    Args:
        cart_id: Identificador del carrito activo para obtener los SKUs ya agregados.
    """
    cart = _ACTIVE_CARTS.get(cart_id, {})
    skus = [it["sku"] for it in cart.get("items", [])]

    if skus:
        try:
            with _get_connection() as conn:
                with conn.cursor() as cur:
                    # Sugerencias basadas en coocurrencia real de ventas
                    placeholders = ",".join(["%s"] * len(skus))
                    cur.execute(f"""
                        SELECT pb.sku, pb.nombre, SUM(vc.veces) AS frecuencia
                          FROM v_coocurrencia vc
                          JOIN producto pb ON pb.sku = vc.sku_b
                         WHERE vc.sku_a = ANY(%s::text[])
                           AND vc.sku_b != ALL(%s::text[])
                           AND pb.activo AND pb.existencia > 0
                         GROUP BY pb.sku, pb.nombre
                         ORDER BY frecuencia DESC
                         LIMIT 2
                    """, (skus, skus))
                    rows = cur.fetchall()
                    if rows:
                        sugerencias = [
                            {"sku": r[0], "nombre": r[1], "motivo": f"Comprado junto {r[2]} veces con artículos de tu carrito."}
                            for r in rows
                        ]
                        return json.dumps({"status": "upsell_ready", "fuente": "coocurrencia_bd", "sugerencias": sugerencias}, ensure_ascii=False)
        except Exception:
            pass

    # Fallback estático
    sugerencias = []
    if any(s in ("LALA-1L", "BIMB-BLAN") for s in skus):
        sugerencias.append({"sku": "HUEVO-KG", "nombre": "Huevo blanco (kg)", "motivo": "Desayuno completo — alta demanda matutina."})
    if not sugerencias:
        sugerencias.append({"sku": "COCA-600", "nombre": "Coca-Cola 600 ml", "motivo": "Producto de alta rotación para acompañar cualquier compra."})

    return json.dumps({"status": "upsell_ready", "fuente": "fallback_estatico", "sugerencias": sugerencias}, ensure_ascii=False)

