"""
Contratos comerciales de Tiendita IA:
Productos, Lotes, Carrito POS, Ventas, Finanzas y Cargas de Aprobación Humana (HITL).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Producto(BaseModel):
    """Entidad de producto en inventario comercial."""
    sku: str = Field(..., description="Código identificador único de producto (SKU / Código de Barras).")
    nombre: str = Field(..., description="Nombre comercial del producto.")
    categoria: str = Field(default="general", description="Categoría de producto.")
    precio_venta: float = Field(..., gt=0, description="Precio de venta al público en mostrador.")
    costo_unitario: float = Field(..., ge=0, description="Costo de adquisición o reposición (CONFIDENCIAL).")
    unidad_medida: str = Field(default="pieza", description="Unidad de medida (pieza, kg, litro, paquete).")
    stock_actual: int = Field(default=0, ge=0, description="Existencias disponibles en anaquel/bodega.")
    stock_minimo: int = Field(default=5, ge=0, description="Umbral para disparar alerta de stock bajo.")
    fecha_caducidad_proxima: Optional[str] = Field(default=None, description="Fecha de caducidad del lote más próximo (YYYY-MM-DD).")


class Lote(BaseModel):
    """Registro de lote específico para control de caducidad."""
    lote_id: str = Field(..., description="Identificador único del lote.")
    sku: str = Field(..., description="SKU del producto asociado.")
    cantidad_disponible: int = Field(..., ge=0, description="Cantidad restante en este lote.")
    fecha_ingreso: str = Field(..., description="Fecha de recepción (YYYY-MM-DD).")
    fecha_caducidad: str = Field(..., description="Fecha de expiración (YYYY-MM-DD).")
    dias_para_caducar: Optional[int] = Field(default=None, description="Cálculo dinámico de días restantes.")


class CartItem(BaseModel):
    """Partida individual dentro del carrito de ventas."""
    sku: str = Field(..., description="SKU del producto.")
    nombre: str = Field(..., description="Nombre comercial del producto.")
    cantidad: int = Field(default=1, gt=0, description="Cantidad solicitada.")
    precio_unitario: float = Field(..., gt=0, description="Precio pactado por unidad.")
    subtotal: float = Field(..., gt=0, description="Subtotal calculado de la partida.")


class CarritoPOS(BaseModel):
    """Sesión de caja activa o carrito de ventas."""
    cart_id: str = Field(..., description="Identificador único de la sesión de carrito.")
    items: List[CartItem] = Field(default_factory=list, description="Lista de artículos agregados.")
    subtotal: float = Field(default=0.0, ge=0, description="Subtotal antes de impuestos o descuentos.")
    descuento_aplicado: float = Field(default=0.0, ge=0, description="Monto de descuento aplicado.")
    total: float = Field(default=0.0, ge=0, description="Importe total a pagar.")
    metodo_pago_seleccionado: Optional[Literal["efectivo", "tarjeta", "transferencia", "qr"]] = Field(
        default=None, description="Método de liquidación."
    )


class Venta(BaseModel):
    """Registro histórico de venta concretada."""
    venta_id: str = Field(..., description="Identificador único de la venta.")
    cart_id: str = Field(..., description="Referencia al carrito liquidado.")
    items: List[CartItem] = Field(..., description="Artículos transferidos al cliente.")
    total: float = Field(..., gt=0, description="Monto final cobrado.")
    metodo_pago: str = Field(..., description="Forma de pago empleada.")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Momento de cierre de la transacción.")
    atendido_por: str = Field(default="Vendedor-IA", description="Identificador del operador o agente.")


class MovimientoFinanciero(BaseModel):
    """Registro de flujo de caja."""
    movimiento_id: str = Field(..., description="Identificador del movimiento.")
    tipo: Literal["ingreso_venta", "inversion_inventario", "gasto_operativo"] = Field(
        ..., description="Categoría financiera del flujo monetario."
    )
    monto: float = Field(..., gt=0, description="Importe monetario.")
    concepto: str = Field(..., description="Descripción detallada del motivo de ingreso o egreso.")
    comprobante_referencia: Optional[str] = Field(default=None, description="Folio de ticket o factura si aplica.")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ApprovalPayload(BaseModel):
    """
    Carga de aprobación humana (Human-in-the-Loop) para operaciones críticas.
    Se utiliza en `approval_gate` antes de modificar inventario masivo, aplicar descuentos altos
    o publicar campañas publicitarias.
    """
    action_type: Literal[
        "actualizar_stock_masivo",
        "alta_catalogo",
        "publicar_campana",
        "descuento_especial",
        "clasificacion_gasto_critico"
    ] = Field(..., description="Tipo de acción que requiere autorización humana.")
    description: str = Field(..., description="Explicación clara de la propuesta para el operador del negocio.")
    proposed_data: Dict[str, Any] = Field(..., description="Datos exactos que se aplicarán si se aprueba.")
    reason: str = Field(..., description="Motivo generado por el razonamiento del agente.")
    requires_human: bool = Field(default=True, description="Bandera para pausar el grafo en approval_gate.")
    status: Literal["pending", "approved", "rejected", "edited"] = Field(default="pending", description="Estado de la resolución humana.")
    human_notes: Optional[str] = Field(default=None, description="Comentarios o modificaciones ingresadas por el operador.")
