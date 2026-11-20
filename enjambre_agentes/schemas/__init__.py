"""
Exportaciones principales del paquete schemas de Tiendita IA.
Mantiene compatibilidad temporal con esquemas de agripoli durante la transición.
"""
from schemas.state import OrchestratorState
from schemas.vision import (
    CatalogScanRequest,
    CatalogItemDetected,
    CatalogScanResult,
    POSCheckoutRequest,
    POSItemDetected,
    POSCheckoutResult,
    ReceiptOCRRequest,
    ReceiptLineItem,
    ReceiptOCRResult,
)
from schemas.ui_copilot import UIState, TutorResponse
from schemas.commerce import (
    Producto,
    Lote,
    CartItem,
    CarritoPOS,
    Venta,
    MovimientoFinanciero,
    ApprovalPayload,
)
from schemas.reports import StrategicReport, VideoPrompt, PromoAssets

__all__ = [
    "OrchestratorState",
    "CatalogScanRequest",
    "CatalogItemDetected",
    "CatalogScanResult",
    "POSCheckoutRequest",
    "POSItemDetected",
    "POSCheckoutResult",
    "ReceiptOCRRequest",
    "ReceiptLineItem",
    "ReceiptOCRResult",
    "UIState",
    "TutorResponse",
    "Producto",
    "Lote",
    "CartItem",
    "CarritoPOS",
    "Venta",
    "MovimientoFinanciero",
    "ApprovalPayload",
    "StrategicReport",
    "VideoPrompt",
    "PromoAssets",
]
