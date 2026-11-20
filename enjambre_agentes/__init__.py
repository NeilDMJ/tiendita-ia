"""
enjambre_agentes — Ecosistema Multiagente Comercial Multimodal en LangGraph.

Fachada pública que unifica:
- Modelos de estado y contratos de base de datos (`state.py`).
- Fábrica de modelos de inferencia multi-proveedor (`models.py`).
- 6 Kits de herramientas comerciales tipadas y exportación MCP (`tools_bridge.py`).
- Gobernanza determinista y anti-alucinaciones (`guards.py`).
- Inyección dinámica de ejemplos (`few_shot_retriever.py`).
- Grafo orquestador de 6 agentes y Human-in-the-Loop (`graph.py`).
"""
from state import (
    OrchestratorState,
    ProductoDB,
    LoteInventarioDB,
    DetalleVentaDB,
    VentaDB,
    MovimientoFinancieroDB,
    CampanaPromocionalDB,
    VisionPayloadModel,
    UIStateModel,
    StrategicReportModel,
    PromoAssetsModel,
    PendingApprovalModel,
    SupervisorDecision,
)
from models import (
    get_llm,
    get_embeddings_model,
    get_available_models,
)
from tools_bridge import (
    parse_vision_catalog_item,
    parse_receipt_ocr,
    query_expiring_products,
    commit_inventory_mutation,
    build_pos_cart_from_vision,
    get_cross_sell_recommendations,
    commit_sale_transaction,
    get_cashflow_summary,
    get_product_margins,
    get_sales_cohort_metrics,
    search_market_trends,
    generate_promo_video_job,
    inspect_payment_step,
    # Herramientas integradas del asistente de catálogo (assistant/)
    crear_producto,
    actualizar_precio,
    consultar_inventario,
    ajustar_stock,
    find_product_by_name_or_alias,
    CONTROL_TOOLS,
    VENDEDOR_TOOLS,
    ANALISTA_TOOLS,
    INVESTIGADOR_TOOLS,
    PUBLICISTA_TOOLS,
    TUTOR_UI_TOOLS,
    ALL_TOOLS,
    to_mcp_tool_definitions,
)
from guards import (
    enforce_db_grounding,
    validate_strategic_report,
)
from few_shot_retriever import (
    FewShotRetriever,
)
from graph import (
    build_orchestrator,
    orchestrator_graph,
    run_orchestration,
    run_orchestration_stream,
    resume_orchestration,
)

__all__ = [
    # State & Models
    "OrchestratorState",
    "ProductoDB",
    "LoteInventarioDB",
    "DetalleVentaDB",
    "VentaDB",
    "MovimientoFinancieroDB",
    "CampanaPromocionalDB",
    "VisionPayloadModel",
    "UIStateModel",
    "StrategicReportModel",
    "PromoAssetsModel",
    "PendingApprovalModel",
    "SupervisorDecision",
    # Models Factory
    "get_llm",
    "get_embeddings_model",
    "get_available_models",
    # Tools & Kits
    "parse_vision_catalog_item",
    "parse_receipt_ocr",
    "query_expiring_products",
    "commit_inventory_mutation",
    "build_pos_cart_from_vision",
    "get_cross_sell_recommendations",
    "commit_sale_transaction",
    "get_cashflow_summary",
    "get_product_margins",
    "get_sales_cohort_metrics",
    "search_market_trends",
    "generate_promo_video_job",
    "inspect_payment_step",
    # Herramientas integradas del asistente de catálogo (assistant/)
    "crear_producto",
    "actualizar_precio",
    "consultar_inventario",
    "ajustar_stock",
    "find_product_by_name_or_alias",
    "CONTROL_TOOLS",
    "VENDEDOR_TOOLS",
    "ANALISTA_TOOLS",
    "INVESTIGADOR_TOOLS",
    "PUBLICISTA_TOOLS",
    "TUTOR_UI_TOOLS",
    "ALL_TOOLS",
    "to_mcp_tool_definitions",
    # Guards & Governance
    "enforce_db_grounding",
    "validate_strategic_report",
    # Few-Shot
    "FewShotRetriever",
    # Graph & Runners
    "build_orchestrator",
    "orchestrator_graph",
    "run_orchestration",
    "run_orchestration_stream",
    "resume_orchestration",
]
