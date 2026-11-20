"""
Exportador centralizado de herramientas de Tiendita IA.
Incluye herramientas de investigación web, scraping, RAG dual, base de datos, POS, finanzas y medios.
"""
from tools.db_client import query_inventory, query_sales, query_expiring_soon
from tools.vision_nim import analyze_catalog_photo, analyze_receipt, analyze_pos_items
from tools.rag_nemo import (
    consultar_conocimiento_comercial,
    indexar_documento_comercial,
    index_strategic_report,
    buscar_reportes_vectoriales
)
from tools.few_shot_retriever import retrieve_few_shots, record_hitl_feedback
from tools.guards import enforce_db_grounding, enforce_max_sentences, prevent_cost_leakage
from tools.mcp_exporter import ALL_COMMERCE_TOOLS, export_mcp_manifest
from tools.inventory_tools import register_product, update_stock, check_expiry_alerts, get_low_stock_alerts
from tools.pos_tools import create_cart, add_to_cart, checkout_cart, suggest_upsell
from tools.analytics_tools import (
    get_cash_flow,
    get_margins_by_sku,
    get_rotation_by_sku,
    get_sales_summary,
    search_web_tavily,
    scrape_webpage_clean,
    search_past_reports,
    save_and_index_report
)
from tools.media_tools import generate_promo_copy, generate_video_prompt, generate_cta

__all__ = [
    "query_inventory",
    "query_sales",
    "query_expiring_soon",
    "analyze_catalog_photo",
    "analyze_receipt",
    "analyze_pos_items",
    "consultar_conocimiento_comercial",
    "indexar_documento_comercial",
    "index_strategic_report",
    "buscar_reportes_vectoriales",
    "retrieve_few_shots",
    "record_hitl_feedback",
    "enforce_db_grounding",
    "enforce_max_sentences",
    "prevent_cost_leakage",
    "ALL_COMMERCE_TOOLS",
    "export_mcp_manifest",
    "register_product",
    "update_stock",
    "check_expiry_alerts",
    "get_low_stock_alerts",
    "create_cart",
    "add_to_cart",
    "checkout_cart",
    "suggest_upsell",
    "get_cash_flow",
    "get_margins_by_sku",
    "get_rotation_by_sku",
    "get_sales_summary",
    "search_web_tavily",
    "scrape_webpage_clean",
    "search_past_reports",
    "save_and_index_report",
    "generate_promo_copy",
    "generate_video_prompt",
    "generate_cta",
]
