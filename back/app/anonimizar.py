"""Anonimización en el servidor (segunda barrera). Espejo de front/src/utils/anonimizar.ts.

El teléfono ya anonimiza, pero el servidor NO confía en el cliente: revalida antes de
tocar cualquier modelo. Si hay datos que jamás deben salir, no se llama al modelo.
"""
import re
from dataclasses import dataclass

_CLABE = re.compile(r"\b\d{18}\b")
_TARJETA = re.compile(r"\b(?:\d[ -]?){15}\d\b")
_TELEFONO = re.compile(r"\b\d{10}\b")
_MONTO = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
_CREDENCIAL = re.compile(r"\b(nip|cvv|cvc|token|contrase(?:ñ|n)a|password)\b[^\n]*\d", re.IGNORECASE)


@dataclass(frozen=True)
class Resultado:
    texto: str
    bloquear: bool


def anonimizar(entrada: str) -> Resultado:
    bloquear = bool(_CLABE.search(entrada) or _TARJETA.search(entrada) or _CREDENCIAL.search(entrada))
    texto = _CLABE.sub("[CLABE]", entrada)
    texto = _TARJETA.sub("[TARJETA]", texto)
    texto = _TELEFONO.sub("[CELULAR]", texto)
    texto = _MONTO.sub("[MONTO]", texto)
    return Resultado(texto=texto, bloquear=bloquear)
