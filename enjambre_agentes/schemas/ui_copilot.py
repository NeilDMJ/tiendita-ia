"""
Contratos de interfaz y validaciones para el Tutor UI de pagos digitales.
Garantiza respuestas concisas de máximo 2 oraciones accionables.
"""
from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UIState(BaseModel):
    """Representa el estado actual de la pantalla en la terminal o punto de venta."""
    screen: str = Field(..., description="Identificador de la pantalla actual (ej. 'seleccion_pago', 'cobro_qr', 'transferir', 'confirmacion', 'comprobante').")
    step: int = Field(default=1, description="Paso del flujo actual.")
    payment_method: Optional[str] = Field(default=None, description="Método de pago digital (codi, spei, dimo, tarjeta, transferencia, efectivo, qr).")
    error_code: Optional[str] = Field(default=None, description="Código o mensaje de error visible en pantalla si existe.")
    monto_pendiente: Optional[float] = Field(default=None, description="Monto total a cobrar pendiente de confirmación.")


class TutorResponse(BaseModel):
    """
    Respuesta del Tutor UI orientada al usuario en caja.
    REGLA ESTRICTA: Máximo 2 oraciones accionables sin rodeos técnicos ni alucinaciones.
    """
    action_sentence_1: str = Field(
        ...,
        max_length=150,
        description="Primera oración clara y accionable para resolver o guiar la operación en pantalla."
    )
    action_sentence_2: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Segunda oración complementaria opcional (máximo permitido: 2 oraciones en total)."
    )
    mensaje_unificado: str = Field(
        default="",
        description="Texto completo consolidado para mostrar en la interfaz de usuario."
    )

    @field_validator("action_sentence_1", "action_sentence_2")
    @classmethod
    def validar_oracion_sin_saltos(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip().replace("\n", " ")
        if not v_clean:
            return None
        # Asegurar que no contenga más de un punto intermedio que forme múltiples oraciones
        partes = [p.strip() for p in re.split(r'[.!?]+', v_clean) if p.strip()]
        if len(partes) > 1:
            # Si hay más de una oración en un solo campo, nos quedamos con la primera bien formulada
            return partes[0] + "."
        if not v_clean.endswith((".", "!", "?")):
            v_clean += "."
        return v_clean

    def model_post_init(self, __context) -> None:
        if self.action_sentence_2:
            self.mensaje_unificado = f"{self.action_sentence_1} {self.action_sentence_2}".strip()
        else:
            self.mensaje_unificado = self.action_sentence_1.strip()
