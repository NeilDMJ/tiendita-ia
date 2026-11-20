"""
state.py — Estado unificado para el Ecosistema Multiagente Comercial Multimodal.

Alineado a:
- Base de datos PostgreSQL (productos, lotes_inventario, ventas, detalle_ventas,
  movimientos_financieros, campanas_promocionales).
- Contratos de entrada multimodal: vision_payload y ui_state.
- Gobernanza determinista y Human-in-the-Loop (HITL) en LangGraph.
"""
from __future__ import annotations

import operator
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# ─────────────────────────────────────────────────────────────────────────────
# 1. MODELOS DE BASE DE DATOS Y CONTRATOS PYDANTIC (Python 3.11+ / Pydantic v2)
# ─────────────────────────────────────────────────────────────────────────────

class ProductoDB(BaseModel):
    """Esquema de la tabla 'productos' en PostgreSQL."""
    id: Optional[int] = Field(default=None, description="Identificador único")
    sku: str = Field(description="Código único de producto o código de barras")
    nombre: str = Field(description="Nombre comercial del producto")
    categoria: str = Field(description="Categoría (lácteos, abarrotes, bebidas, etc.)")
    precio_venta: float = Field(ge=0.0, description="Precio de venta al público en MXN")
    costo_unitario: float = Field(ge=0.0, description="Costo de adquisición por unidad")
    stock_actual: int = Field(ge=0, description="Existencia física actual")
    stock_minimo: int = Field(default=5, ge=0, description="Umbral de alerta de reorden")
    atributos_visuales: Dict[str, Any] = Field(
        default_factory=dict,
        description="Características visuales (color, empaque, dimensiones, marca)"
    )


class LoteInventarioDB(BaseModel):
    """Esquema de la tabla 'lotes_inventario' en PostgreSQL."""
    id: Optional[int] = Field(default=None)
    producto_id: int = Field(description="ID de referencia a productos.id")
    cantidad: int = Field(ge=0, description="Cantidad en el lote")
    fecha_caducidad: str = Field(description="Fecha de vencimiento formato YYYY-MM-DD")
    estado: Literal["activo", "proximo_a_vencer", "vencido", "agotado"] = Field(
        default="activo", description="Estado operativo del lote"
    )


class DetalleVentaDB(BaseModel):
    """Esquema de la tabla 'detalle_ventas' en PostgreSQL."""
    id: Optional[int] = Field(default=None)
    venta_id: Optional[int] = Field(default=None)
    producto_id: int
    cantidad: int = Field(ge=1)
    precio_unitario: float = Field(ge=0.0)
    subtotal: float = Field(ge=0.0)


class VentaDB(BaseModel):
    """Esquema de la tabla 'ventas' en PostgreSQL."""
    id: Optional[int] = Field(default=None)
    fecha: str = Field(description="Fecha ISO 8601 de la transacción")
    total: float = Field(ge=0.0, description="Monto total cobrado")
    metodo_pago: Literal["efectivo", "tarjeta", "spei", "qr"] = Field(default="efectivo")
    origen_vision: bool = Field(default=False, description="True si provino de detección por cámara")
    detalles: List[DetalleVentaDB] = Field(default_factory=list)


class MovimientoFinancieroDB(BaseModel):
    """Esquema de la tabla 'movimientos_financieros' en PostgreSQL."""
    id: Optional[int] = Field(default=None)
    tipo: Literal["gasto_operativo", "inversion_inventario"] = Field(
        description="Clasificación financiera del movimiento"
    )
    proveedor: str = Field(description="Nombre o razón social del emisor/proveedor")
    monto_total: float = Field(ge=0.0, description="Monto total del movimiento")
    fecha: str = Field(description="Fecha del movimiento YYYY-MM-DD")
    url_ticket: Optional[str] = Field(default=None, description="URL o ruta de imagen del ticket")
    datos_ocr_json: Dict[str, Any] = Field(
        default_factory=dict, description="Extracción estructurada del OCR"
    )


class CampanaPromocionalDB(BaseModel):
    """Esquema de la tabla 'campanas_promocionales' en PostgreSQL."""
    id: Optional[int] = Field(default=None)
    producto_id: int
    motivo: str = Field(description="Razón de la campaña (ej. próxima caducidad, sobrestock)")
    copy_texto: str = Field(description="Texto persuasivo para WhatsApp / Redes sociales")
    video_prompt: str = Field(description="Prompt en inglés cinematográfico vertical 9:16 (5s)")
    video_url: Optional[str] = Field(default=None, description="URL del video generado")
    estado_aprobacion: Literal["borrador", "pendiente_aprobacion", "aprobada", "rechazada"] = Field(
        default="borrador"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONTRATOS DE ENTRADA MULTIMODAL
# ─────────────────────────────────────────────────────────────────────────────

class VisionPayloadModel(BaseModel):
    """Contrato estricto para payloads de Visión Artificial."""
    endpoint: Literal["/catalog-scan", "/pos-checkout", "/receipt-ocr"] = Field(
        description="Endpoint de visión que originó el payload"
    )
    items: List[Dict[str, Any]] = Field(
        default_factory=list, description="Lista de ítems detectados visualmente"
    )
    proveedor: Optional[str] = Field(
        default=None, description="Proveedor detectado en /receipt-ocr"
    )
    total: Optional[float] = Field(
        default=None, description="Total monetario detectado en /receipt-ocr o /pos-checkout"
    )
    tipo_movimiento: Optional[str] = Field(
        default=None, description="Clasificación sugerida para el ticket"
    )
    confianza_global: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Nivel de confianza del modelo de visión"
    )


class UIStateModel(BaseModel):
    """Contrato estricto para el estado de la interfaz móvil (Copiloto de Pagos)."""
    pantalla: str = Field(description="Nombre de la pantalla actual (ej. Checkout, PagoSPEI, EscaneoQR)")
    paso_actual: str = Field(description="Subpaso o acción en curso")
    campos_vacios: List[str] = Field(default_factory=list, description="Campos requeridos pendientes")
    error_visible: Optional[str] = Field(default=None, description="Mensaje de error mostrado al usuario")
    intentos: int = Field(default=1, ge=1, description="Número de intentos realizados")


class StrategicReportModel(BaseModel):
    """Contrato estricto para el reporte del Investigador (9 secciones obligatorias)."""
    identificacion_sector: str = Field(description="1. Identificación y delimitación del sector")
    mercado_tendencias: str = Field(description="2. Mercado y macrotendencias del consumo")
    clientes: str = Field(description="3. Clientes y perfiles de compradores clave")
    problemas: str = Field(description="4. Problemas y cuellos de botella detectados")
    soluciones: str = Field(description="5. Soluciones estratégicas sugeridas")
    hipotesis: str = Field(description="6. Hipótesis comerciales validadas o por validar")
    objetivos: str = Field(description="7. Objetivos comerciales cuantitativos y cualitativos")
    impacto: str = Field(description="8. Impacto estimado en margen, rotación y ventas")
    hallazgos: str = Field(description="9. Hallazgos principales y recomendaciones de ejecución")


class PromoAssetsModel(BaseModel):
    """Contrato estricto para los activos del Agente Publicista."""
    video_prompt: str = Field(description="Prompt cinematográfico en inglés vertical 9:16 (5s)")
    copy_promocional: str = Field(description="Copy persuasivo en español con tono comercial")
    call_to_action: str = Field(description="Llamado a la acción directo para la app o WhatsApp")
    video_url: Optional[str] = Field(default=None, description="URL del video renderizado")


class PendingApprovalModel(BaseModel):
    """Contrato estricto para acciones que requieren Human-in-the-Loop (HITL)."""
    action_type: Literal[
        "inventory_mutation", "sale_transaction", "promo_campaign", "financial_entry"
    ] = Field(description="Tipo de acción que mutaría datos")
    summary: str = Field(description="Resumen legible para el usuario en la app móvil")
    payload: Dict[str, Any] = Field(description="Parámetros técnicos de la mutación a ejecutar")
    requires_confirmation: bool = Field(default=True)


class SupervisorDecision(BaseModel):
    """Decisión de enrutamiento tomada por el Supervisor."""
    next_step: Literal[
        "control", "vendedor", "analista", "investigador", "publicista", "tutor_ui", "aprobacion_hitl", "FIN"
    ] = Field(description="Siguiente agente o nodo a ejecutar")
    reasoning: str = Field(description="Justificación técnica del enrutamiento")
    instructions_for_agent: str = Field(default="", description="Instrucciones directas para el especialista")


# ─────────────────────────────────────────────────────────────────────────────
# 3. ESTADO GLOBAL MULTIMODAL (OrchestratorState)
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorState(TypedDict, total=False):
    """
    Estado global unificado de LangGraph para el Ecosistema Multiagente Comercial.
    
    Gestiona el flujo continuo entre:
    - Supervisor / Enrutador multicanal
    - Agente de Control de Inventario y Validación OCR
    - Agente Vendedor y Copiloto POS
    - Agente Analista Financiero (Solo lectura)
    - Agente Investigador de Mercado
    - Agente Publicista Multimedia
    - Agente Tutor de Pasarelas de Pago UI
    - Nodo de Confirmación Human-in-the-Loop (HITL)
    """
    # ── Conversación y Eventos ──
    messages: Annotated[List[AnyMessage], add_messages]
    event_source: Literal["chat", "vision_api", "ui_copilot", "cron_trigger"]
    
    # ── Cargas Multimodales ──
    vision_payload: Optional[Dict[str, Any]]
    ui_state: Optional[Dict[str, Any]]
    
    # ── Evidencia Real de Base de Datos para Grounding Determinista ──
    db_evidence: Annotated[List[Dict[str, Any]], operator.add]
    
    # ── Inyección Dinámica de Ejemplos ──
    few_shot_examples: Optional[List[Dict[str, Any]]]
    
    # ── Salidas Especializadas ──
    strategic_report: Optional[Dict[str, Any]]  # 9 claves fijas
    promo_assets: Optional[Dict[str, Any]]       # video_prompt, copy, cta, video_url
    
    # ── Gobernanza Human-in-the-Loop ──
    pending_approval: Optional[Dict[str, Any]]   # action_type, summary, payload, requires_confirmation
    
    # ── Diagnóstico y Control de Ciclo ──
    validation_errors: Optional[List[str]]
    next_agent: str
    iteration_count: int
    
    # ── Metadatos Operativos Auxiliares ──
    query: Optional[str]
    sender: Optional[str]
    supervisor_notes: Optional[str]
    provider: Optional[str]
    model_name: Optional[str]
    temperature: Optional[float]
    final_response: Optional[str]
    retry_count: Optional[int]
