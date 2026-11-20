"""
Guardrails y verificaciones de integridad programáticas para Tiendita IA.
Verifica que las respuestas estén fundamentadas en evidencia de base de datos (Grounding)
y valida restricciones críticas de formato (ej. máximo 2 oraciones en Tutor UI).
"""
from __future__ import annotations

import re
from typing import Any, Optional
from config.models import extraer_texto_mensaje


def enforce_db_grounding(response_text: Any, db_evidence: Optional[str]) -> str:
    """
    Verifica que las afirmaciones cuantitativas de existencias o precios
    estén sustentadas en la evidencia obtenida de la base de datos.
    Si no hay evidencia o hay contradicción severa, antepone una nota de cautela formal.
    """
    text = extraer_texto_mensaje(response_text)
    if not db_evidence or "not_found" in db_evidence:
        if re.search(r'\b(tenemos|hay|disponible|existencia)\s+\d+', text, re.IGNORECASE):
            return (
                "(¬_¬) [PRECAUCION: VALIDACION_BD] La base de datos no reporta evidencia confirmada "
                "para estas existencias. Se recomienda verificar físicamente en anaquel antes de cobrar.\n\n" + text
            )
    return text


def enforce_max_sentences(text: Any, max_sentences: int = 2) -> str:
    """
    Garantiza rígidamente que el texto no sobrepase el número estipulado de oraciones.
    Diseñado específicamente para el Tutor UI.
    """
    texto_limpio = extraer_texto_mensaje(text)
    if not texto_limpio:
        return ""
    oraciones = [s.strip() for s in re.split(r'(?<=[.!?])\s+', texto_limpio.strip()) if s.strip()]
    if len(oraciones) <= max_sentences:
        return " ".join(oraciones)

    oraciones_recortadas = oraciones[:max_sentences]
    resultado = " ".join(oraciones_recortadas)
    if not resultado.endswith((".", "!", "?")):
        resultado += "."
    return resultado


def prevent_cost_leakage(text: Any) -> str:
    """
    Elimina cualquier filtración involuntaria del 'costo_unitario' confidencial
    hacia clientes en terminales de mostrador.
    """
    texto_limpio = extraer_texto_mensaje(text)
    patron = re.compile(r'(costo\s*unitario|costo\s*de\s*adquisici[oó]n|nos\s*cuesta)\s*[:=]?\s*\$?\s*\d+(\.\d{1,2})?', re.IGNORECASE)
    return patron.sub("[CONFIDENCIAL]", texto_limpio)
