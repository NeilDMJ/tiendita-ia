"""Guías por banco y operación. Los pasos salen de aquí, NUNCA del modelo (los LLM inventan botones)."""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .esquemas import PasoGuia

_ARCHIVO = Path(__file__).parent / "datos" / "guias.json"


@dataclass(frozen=True)
class Guia:
    pasos: list[PasoGuia]
    advertencias: list[str]
    verificada: bool


@lru_cache(maxsize=1)
def _datos() -> dict:
    return json.loads(_ARCHIVO.read_text(encoding="utf-8"))


def _pasos(items: list[dict]) -> list[PasoGuia]:
    return [PasoGuia(n=i + 1, texto=p["texto"], pantalla=p.get("pantalla")) for i, p in enumerate(items)]


def obtener_guia(banco: str, operacion: str) -> Guia:
    datos = _datos()
    adv = datos["advertencias"]
    avisos = [adv["_claves"], *adv.get(operacion, [])]
    especifica = datos["verificadas"].get(f"{banco}:{operacion}")
    if especifica:
        return Guia(pasos=_pasos(especifica["pasos"]), advertencias=avisos, verificada=True)
    return Guia(pasos=_pasos(datos["genericas"][operacion]), advertencias=avisos, verificada=False)
