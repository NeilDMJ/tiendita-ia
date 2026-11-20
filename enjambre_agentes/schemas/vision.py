"""
Contratos y esquemas de validación Pydantic para visión artificial multimodal en Tiendita IA.
Modelos para escaneo de catálogo, checkout POS y OCR de comprobantes/tickets.
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# --- /catalog-scan ---
class CatalogScanRequest(BaseModel):
    """Solicitud de procesamiento de imagen de catálogo o estante."""
    image_b64: str = Field(..., description="Imagen codificada en Base64.")
    mime_type: str = Field(default="image/jpeg", description="Tipo MIME de la imagen (image/jpeg, image/png).")
    categoria_sugerida: Optional[str] = Field(default=None, description="Categoría opcional sugerida para contextualizar.")


class CatalogItemDetected(BaseModel):
    """Producto detectado durante el escaneo de catálogo."""
    sku_sugerido: str = Field(..., description="Código SKU sugerido o normalizado.")
    nombre: str = Field(..., description="Nombre comercial del producto detectado.")
    categoria: str = Field(..., description="Categoría de producto asignada.")
    precio_estimado: Optional[float] = Field(default=None, description="Precio unitario inferido en la etiqueta o empaque.")
    confianza_deteccion: float = Field(default=0.0, ge=0.0, le=1.0, description="Nivel de certeza de la detección (0.0 a 1.0).")
    lote_sugerido: Optional[str] = Field(default=None, description="Identificador de lote detectado si es visible.")


class CatalogScanResult(BaseModel):
    """Resultado estructurado del análisis de catálogo con NIM Vision."""
    productos_detectados: List[CatalogItemDetected] = Field(default_factory=list, description="Lista de productos identificados.")
    conteo_total: int = Field(default=0, description="Cantidad total de productos detectados.")
    observaciones: Optional[str] = Field(default=None, description="Notas del modelo sobre condiciones de iluminación o visibilidad.")


# --- /pos-checkout ---
class POSCheckoutRequest(BaseModel):
    """Solicitud de identificación visual de productos en mostrador POS."""
    image_b64: str = Field(..., description="Fotografía en base64 de los artículos en la caja.")
    mime_type: str = Field(default="image/jpeg", description="Tipo MIME.")
    id_carrito_activo: Optional[str] = Field(default=None, description="ID de sesión de carrito en curso.")


class POSItemDetected(BaseModel):
    """Artículo identificado en mostrador."""
    sku: str = Field(..., description="SKU del producto.")
    nombre: str = Field(..., description="Nombre común del producto.")
    cantidad_detectada: int = Field(default=1, ge=1, description="Unidades visualizadas en la imagen.")
    confianza: float = Field(default=0.0, ge=0.0, le=1.0, description="Certeza de identificación.")


class POSCheckoutResult(BaseModel):
    """Items detectados listos para agregar o cotizar en el carrito."""
    items: List[POSItemDetected] = Field(default_factory=list, description="Artículos contabilizados visualmente.")
    requiere_verificacion_manual: bool = Field(default=False, description="True si alguna detección tuvo baja confianza.")


# --- /receipt-ocr ---
class ReceiptOCRRequest(BaseModel):
    """Solicitud de lectura y clasificación contable de un ticket o factura de compra."""
    image_b64: str = Field(..., description="Imagen del ticket en base64.")
    mime_type: str = Field(default="image/jpeg", description="Tipo MIME.")


class ReceiptLineItem(BaseModel):
    """Línea de detalle en el ticket."""
    descripcion: str = Field(..., description="Descripción del insumo o producto comprado.")
    cantidad: float = Field(default=1.0, description="Cantidad adquirida.")
    precio_unitario: float = Field(..., description="Precio por unidad.")
    subtotal: float = Field(..., description="Importe total de la partida.")


class ReceiptOCRResult(BaseModel):
    """Resultado del OCR y clasificación de ticket de compra."""
    proveedor: Optional[str] = Field(default=None, description="Nombre o razón social del emisor del comprobante.")
    folio_o_numero: Optional[str] = Field(default=None, description="Número de ticket o factura.")
    fecha_emision: Optional[str] = Field(default=None, description="Fecha detectada en formato YYYY-MM-DD si es legible.")
    total_importe: float = Field(..., description="Monto total del comprobante.")
    clasificacion_contable: Literal["inversion_inventario", "gasto_operativo"] = Field(
        ...,
        description="Clasificación estricta: 'inversion_inventario' si son mercancías para reventa, 'gasto_operativo' si son insumos/servicios del local."
    )
    justificacion_clasificacion: str = Field(..., description="Razón analítica por la que se determinó la clasificación contable.")
    partidas: List[ReceiptLineItem] = Field(default_factory=list, description="Detalle de productos o conceptos leídos.")
