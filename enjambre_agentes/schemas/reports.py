"""
Esquemas Pydantic para reportes estratégicos del Investigador (9 secciones obligatorias)
y activos promocionales del Publicista (copys, CTAs y video vertical 9:16).
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class StrategicReport(BaseModel):
    """
    Reporte estratégico exhaustivo de 9 secciones obligatorias generado por el Investigador.
    """
    identificacion_sector: str = Field(
        ...,
        description="1. Identificación y delimitación del sector comercial, tamaño de mercado local y competencia directa."
    )
    mercado_tendencias: str = Field(
        ...,
        description="2. Tendencias actuales de consumo, estacionalidad, hábitos de compra y evolución tecnológica."
    )
    clientes: str = Field(
        ...,
        description="3. Segmentación del perfil de clientes, demografía, poder adquisitivo y motivaciones de compra."
    )
    problemas: str = Field(
        ...,
        description="4. Puntos de dolor, ineficiencias de suministro, mermas frecuentes y quejas comunes."
    )
    soluciones: str = Field(
        ...,
        description="5. Soluciones comerciales y operativas viables para la tiendita o comercio minorista."
    )
    hipotesis: str = Field(
        ...,
        description="6. Hipótesis de crecimiento comercial, optimización de márgenes y adopción digital."
    )
    objetivos: str = Field(
        ...,
        description="7. Objetivos SMART a corto, mediano y largo plazo para el establecimiento."
    )
    impacto: str = Field(
        ...,
        description="8. Proyección de impacto en ingresos, fidelización de clientes y reducción de mermas."
    )
    hallazgos: str = Field(
        ...,
        description="9. Hallazgos clave finales y recomendaciones prácticas inmediatas para ejecución."
    )


class VideoPrompt(BaseModel):
    """
    Especificación de prompt para generación de video vertical comercial de 5 segundos.
    Disparado ante alertas de caducidad inminente o sobrestock.
    """
    aspect_ratio: Literal["9:16"] = Field(default="9:16", description="Relación de aspecto vertical para Reels/TikTok/WhatsApp Status.")
    duration_seconds: int = Field(default=5, ge=5, le=10, description="Duración exacta del video en segundos.")
    trigger: Literal["caducidad", "sobrestock", "promocion_general"] = Field(
        ..., description="Causa detonante de la creación del activo de video."
    )
    producto_promocionado: str = Field(..., description="Nombre del producto o categoría central del video.")
    prompt_text: str = Field(
        ...,
        description="Prompt visual cinematográfico y descriptivo de alta fidelidad para modelos de generación de video."
    )
    guion_voz_superpuesta: Optional[str] = Field(
        default=None,
        description="Locución breve (máximo 12 palabras) para el audio en off del anuncio."
    )


class PromoAssets(BaseModel):
    """
    Conjunto consolidado de activos promocionales generados por el Agente Publicista.
    """
    copy_text: str = Field(..., description="Texto promocional persuasivo y contextualizado para WhatsApp o redes sociales.")
    cta: str = Field(..., description="Llamado a la acción (Call To Action) conciso y directo para incentivar la visita o compra.")
    descuento_sugerido_pct: Optional[float] = Field(default=None, description="Porcentaje de descuento propuesto según caducidad/stock.")
    video_prompt: Optional[VideoPrompt] = Field(default=None, description="Especificación de video vertical 9:16 si aplica.")
