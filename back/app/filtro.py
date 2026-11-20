"""Filtro de salida: descarta el texto del modelo si inventa botones, enumera pasos o pide claves.

Los LLM pequeños (y a veces los grandes) inventan nombres de botones; la guía es la única fuente
de verdad. Si el texto no pasa, el servicio usa un texto de respaldo.
"""
import re

from .deteccion import BANCOS

_LISTA = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s", re.M)
_CITADO = re.compile(r"""[“"«](.{2,40}?)[”"»]|\*\*(.{2,40}?)\*\*|(?<!\w)['‘](.{2,40}?)['’](?!\w)""")
_PIDE_CLAVES = re.compile(
    r"(dame|comparte|env[ií]a|dime|escribe|p[aá]same|ingresa|proporciona)\s+(aqu[ií]\s+)?(tu|el|la)\s+(nip|token|cvv|cvc|contrase|clave)",
    re.I,
)
# El modelo a veces filtra sus propias instrucciones al usuario.
_FILTRA_REGLAS = re.compile(r"\b(referencia|instrucciones|no invento|mis reglas|prompt)\b", re.I)
MAX_CARACTERES = 600


def texto_valido(texto: str, permitido: str, banco: str | None) -> bool:
    """permitido = texto de la guía (pasos + pantallas): lo único que puede aparecer entre comillas."""
    if len(texto) > MAX_CARACTERES or _LISTA.search(texto) or _PIDE_CLAVES.search(texto) or _FILTRA_REGLAS.search(texto):
        return False
    base = f"{permitido} {banco or ''}".lower()
    for grupos in _CITADO.findall(texto):
        fragmento = next((g for g in grupos if g), "").strip().lower()
        if fragmento and fragmento not in base:
            return False
    # Habla de otro banco distinto al del usuario → se confundió.
    return not any(nombre != banco and patron.search(texto) for patron, nombre in BANCOS)
