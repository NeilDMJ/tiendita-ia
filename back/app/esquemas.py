"""Contrato con el front. Espejo de front/src/api/esquemas.ts: mantener sincronizado."""
from typing import Literal

from pydantic import BaseModel, Field

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
    respuestas_rapidas: list[str] | None = None
    no_resuelto: bool | None = None
    # Contexto de la conversación: el front lo devuelve en `historial` para los seguimientos.
    banco: str | None = None
    operacion: str | None = None


class SolicitudMensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
    historial: list[MensajeAsistente] = Field(default_factory=list, max_length=40)
