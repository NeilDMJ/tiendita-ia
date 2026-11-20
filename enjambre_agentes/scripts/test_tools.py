"""
Script de prueba rápida de herramientas POS e Inventario con BD real.
Ejecutar: uv run python scripts/test_tools.py
"""
import json, sys

def ok(msg): print(f"  ✓ {msg}")
def fail(msg): print(f"  ✗ {msg}"); sys.exit(1)

# 1. Importaciones
try:
    from tools.db_client import _MOCK_INVENTORY, _MOCK_SALES, query_inventory, query_expiring_soon, query_sales
    from tools.pos_tools import create_cart, add_to_cart, checkout_cart, get_cart, suggest_upsell, apply_discount
    from tools.inventory_tools import register_product, update_stock, check_expiry_alerts, get_low_stock_alerts, get_product_detail
    from tools.analytics_tools import get_cash_flow, get_margins_by_sku, get_rotation_by_sku, get_sales_summary
    ok("Todos los módulos importados correctamente")
except Exception as e:
    fail(f"ImportError: {e}")

# 2. Consulta de inventario BD real
print("\n--- BD: v_inventario ---")
inv = json.loads(query_inventory.invoke({}))
print(f"  Fuente: {inv.get('status')}, productos: {inv.get('conteo', len(inv.get('datos', [])))}")
if inv.get("datos"):
    p = inv["datos"][0]
    print(f"  Primer producto: {p.get('sku')} | {p.get('nombre')} | precio=${p.get('precio_venta')}")

# 3. Alertas de caducidad
print("\n--- BD: v_por_caducar ---")
cad = json.loads(query_expiring_soon.invoke({"days_ahead": 7}))
print(f"  Alertas caducidad: {cad.get('total_alertas', 0)}")
for item in (cad.get("items") or [])[:2]:
    print(f"    - {item.get('sku')} vence en {item.get('dias_restantes')} días ({item.get('caducidad')})")

# 4. Stock bajo
print("\n--- BD: v_stock_bajo ---")
sbajo = json.loads(get_low_stock_alerts.invoke({}))
print(f"  Alertas stock bajo ({sbajo['fuente']}): {sbajo['total_alertas']}")

# 5. Detalle producto
print("\n--- BD: get_product_detail ---")
det = json.loads(get_product_detail.invoke({"sku": "COCA-600"}))
if det.get("status") == "found":
    p = det["producto"]
    ok(f"COCA-600: existencia={p['existencia']}, precio=${p['precio_venta']}, bajo_minimo={p['bajo_minimo']}")

# 6. Flujo POS completo
print("\n--- POS: flujo completo ---")
cart_resp = json.loads(create_cart.invoke({}))
cart_id = cart_resp["cart_id"]
ok(f"Carrito creado: {cart_id}")

add1 = json.loads(add_to_cart.invoke({"cart_id": cart_id, "sku": "COCA-600", "quantity": 2}))
ok(f"COCA-600 x2 agregado → subtotal: ${add1['cart']['subtotal']}")

add2 = json.loads(add_to_cart.invoke({"cart_id": cart_id, "sku": "LALA-1L", "quantity": 1}))
ok(f"LALA-1L x1 agregado → total: ${add2['cart']['total']}")

upsell = json.loads(suggest_upsell.invoke({"cart_id": cart_id}))
ok(f"Upsell ({upsell['fuente']}): {[s['sku'] for s in upsell['sugerencias']]}")

checkout = json.loads(checkout_cart.invoke({"cart_id": cart_id, "payment_method": "efectivo", "monto_recibido": 100.0}))
ticket = checkout["ticket"]
ok(f"Checkout ({checkout['fuente']}): total=${ticket.get('total')}, cambio=${checkout['cambio']}")

# 7. Analíticas desde BD
print("\n--- Analíticas: BD ---")
cf = json.loads(get_cash_flow.invoke({}))
ok(f"Flujo de caja ({cf['fuente']}): ingresos=${cf['ingresos_totales']}, neto=${cf['flujo_caja_neto']}")

mg = json.loads(get_margins_by_sku.invoke({}))
ok(f"Márgenes ({mg['fuente']}): {len(mg['margenes'])} productos analizados")

rot = json.loads(get_rotation_by_sku.invoke({"days": 30}))
ok(f"Rotación ({rot['fuente']}): {len(rot['analisis_rotacion'])} SKUs evaluados")

ss = json.loads(get_sales_summary.invoke({"period": "week"}))
ok(f"Resumen ventas ({ss['fuente']}): {ss['transacciones']} txs, ticket_avg=${ss['ticket_promedio']}")

# 8. update_stock
print("\n--- Control: update_stock ---")
us = json.loads(update_stock.invoke({"sku": "COCA-600", "cantidad": 12, "tipo_movimiento": "entrada_compra"}))
ok(f"update_stock COCA-600 ({us['fuente']}): {us['stock_anterior']} → {us['stock_nuevo']}")

print("\n✅ Todas las pruebas pasadas correctamente.")
