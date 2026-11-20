"""
Exportador de herramientas en formato compatible con Model Context Protocol (MCP).
Permite exponer las herramientas de Tiendita IA a clientes externos o agentes remotos.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List
from langchain_core.tools import BaseTool

from tools.db_client import query_inventory, query_sales, query_expiring_soon
from tools.vision_nim import analyze_catalog_photo, analyze_receipt, analyze_pos_items
from tools.rag_nemo import consultar_conocimiento_comercial
from tools.inventory_tools import register_product, update_stock, check_expiry_alerts, get_low_stock_alerts
from tools.pos_tools import create_cart, add_to_cart, checkout_cart, suggest_upsell
from tools.analytics_tools import get_cash_flow, get_margins_by_sku, get_rotation_by_sku, get_sales_summary
from tools.media_tools import generate_promo_copy, generate_video_prompt, generate_cta


ALL_COMMERCE_TOOLS: List[BaseTool] = [
    query_inventory,
    query_sales,
    query_expiring_soon,
    analyze_catalog_photo,
    analyze_receipt,
    analyze_pos_items,
    consultar_conocimiento_comercial,
    register_product,
    update_stock,
    check_expiry_alerts,
    get_low_stock_alerts,
    create_cart,
    add_to_cart,
    checkout_cart,
    suggest_upsell,
    get_cash_flow,
    get_margins_by_sku,
    get_rotation_by_sku,
    get_sales_summary,
    generate_promo_copy,
    generate_video_prompt,
    generate_cta,
]


def export_mcp_manifest() -> Dict[str, Any]:
    """Genera el manifiesto estructurado de herramientas en estándar MCP Tools."""
    tools_manifest = []
    for t in ALL_COMMERCE_TOOLS:
        tools_manifest.append({
            "name": t.name,
            "description": t.description,
            "inputSchema": t.args_schema.schema() if t.args_schema else {}
        })
    return {
        "server": "tiendita-ia-mcp",
        "version": "1.0.0",
        "tools": tools_manifest
    }
