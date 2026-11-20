"""Contrato con el front. Espejo de front/src/api/esquemas.ts: mantener sincronizado."""
from typing import Literal

from typing import Any

from pydantic import BaseModel, Field, field_validator

Rol = Literal["caja", "bodega", "cuentas", "promociones", "tutor", "general", "banco", "usuario"]


class PasoGuia(BaseModel):
    n: int
    texto: str
    pantalla: str | None = None


class MensajeAsistente(BaseModel):
    rol: Rol
    texto: str
    pasos: list[PasoGuia] | None = None
    advertencias: list[str] | None = None
    guia_verificada: bool | None = None
    sugerencias: list[str] | None = None  # chips de seguimiento: máx. 3 de ≤60 caracteres (contrato del front)
    no_resuelto: bool | None = None
    # Contexto de la conversación: el front lo devuelve en `historial` para los seguimientos.
    banco: str | None = None
    operacion: str | None = None


    @field_validator("sugerencias")
    @classmethod
    def _ajustar(cls, v: list[str] | None) -> list[str] | None:
        return [x[:60] for x in v[:3]] if v else v


class TurnoHistorial(BaseModel):
    """Turno que manda el front (front/src/api/esquemas.ts → TurnoHistorial)."""

    autor: Literal["tendero", "asistente"]
    rol: Rol | None = None
    texto: str = Field(max_length=2000)
    banco: str | None = None
    operacion: str | None = None

    def a_mensaje(self) -> MensajeAsistente:
        if self.autor == "tendero":
            return MensajeAsistente(rol="usuario", texto=self.texto)
        return MensajeAsistente(rol=self.rol or "general", texto=self.texto, banco=self.banco, operacion=self.operacion)


class SolicitudMensaje(BaseModel):
    """POST /asistente/mensaje (front: SolicitudAsistente). `contexto` (pantalla) aún no se usa aquí."""

    texto: str = Field(min_length=1, max_length=2000)
    id_mensaje: str | None = None
    historial: list[TurnoHistorial] = Field(default_factory=list, max_length=40)
    contexto: dict[str, Any] | None = None
