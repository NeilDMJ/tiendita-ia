"""
guards.py — Gobernanza determinista y validadores anti-alucinaciones.

Implementa:
1. `enforce_db_grounding`: Valida que los datos monetarios y cantidades críticas
   mencionadas por los agentes estén respaldados matemáticamente por la evidencia
   recuperada de PostgreSQL (`db_evidence`).
2. `validate_strategic_report`: Verifica el cumplimiento de las 9 secciones
   obligatorias del reporte estratégico comercial generado por el Investigador.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from pydantic import ValidationError
from state import StrategicReportModel


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXTRACCIÓN Y RECOLECCIÓN DETERMINISTA DE NÚMEROS Y MONTOS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_monetary_values(text: str) -> List[float]:
    """
    Extrae cantidades monetarias expresadas con signo de pesos ($) o sufijos de moneda.
    Ejemplos: $120.50, $1,500, $ 45.00, 350.00 MXN.
    """
    if not text:
        return []

    # Patrones para $1,234.56 o $1234.56 o $50
    pattern_symbol = r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)"
    # Patrones para 120.50 MXN / pesos
    pattern_currency = r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:MXN|pesos|pesos mexicanos)\b"

    extracted: List[float] = []

    for match in re.finditer(pattern_symbol, text, re.IGNORECASE):
        val_str = match.group(1).replace(",", "")
        try:
            val = float(val_str)
            extracted.append(round(val, 2))
        except ValueError:
            pass

    for match in re.finditer(pattern_currency, text, re.IGNORECASE):
        val_str = match.group(1).replace(",", "")
        try:
            val = float(val_str)
            val_round = round(val, 2)
            if val_round not in extracted:
                extracted.append(val_round)
        except ValueError:
            pass

    return extracted


def _collect_numbers_from_evidence(data: Any) -> Set[float]:
    """
    Recorre recursivamente diccionarios y listas de `db_evidence` para extraer
    todos los valores numéricos (precios, subtotales, totales, márgenes, existencias).
    """
    numbers: Set[float] = set()

    if isinstance(data, (int, float)):
        val = float(data)
        numbers.add(round(val, 2))
    elif isinstance(data, dict):
        for v in data.values():
            numbers.update(_collect_numbers_from_evidence(v))
    elif isinstance(data, list):
        for item in data:
            numbers.update(_collect_numbers_from_evidence(item))
    elif isinstance(data, str):
        # Si contiene cadenas numéricas exactas
        clean = data.strip().replace("$", "").replace(",", "")
        try:
            val = float(clean)
            numbers.add(round(val, 2))
        except ValueError:
            pass

    return numbers


# ─────────────────────────────────────────────────────────────────────────────
# 2. VALIDADOR DE GROUNDING EN BASE DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

def enforce_db_grounding(
    agent_response: str,
    db_evidence: List[Dict[str, Any]],
    tolerance: float = 0.05
) -> Tuple[bool, List[str]]:
    """
    Extrae montos monetarios ($X,XXX.XX) y valida que cada uno esté respaldado
    en la evidencia real de PostgreSQL provista en `db_evidence`.
    
    Reglas:
    - Si el texto afirma cifras monetarias y `db_evidence` está vacío: Falla inmediatamente.
    - Si una cifra monetaria no coincide con ningún valor de `db_evidence` (con tolerancia permitida):
      Se registra como error de grounding.
    - Las cantidades relativas (porcentajes de margen, etc.) se toleran si derivan de la evidencia.
    
    Retorna:
        Tuple[bool, List[str]]: (es_valido, lista_de_errores)
    """
    claimed_amounts = _extract_monetary_values(agent_response)
    if not claimed_amounts:
        # No hay afirmaciones monetarias explícitas sujetas a validación estricta
        return True, []

    if not db_evidence:
        return False, [
            f"El agente realizó afirmaciones monetarias {claimed_amounts} pero `db_evidence` "
            f"está vacío. Se requiere consulta a base de datos para respaldo numérico."
        ]

    evidence_numbers = _collect_numbers_from_evidence(db_evidence)
    errors: List[str] = []

    for claimed in claimed_amounts:
        # Cero o valores insignificantes
        if claimed == 0.0:
            continue

        matched = False
        for ev_num in evidence_numbers:
            # Tolerancia absoluta o relativa (hasta tolerance %)
            diff = abs(claimed - ev_num)
            max_allowed_diff = max(tolerance, claimed * tolerance)
            if diff <= max_allowed_diff:
                matched = True
                break

        if not matched:
            errors.append(
                f"El monto afirmado '${claimed:,.2f}' no se encuentra respaldado por ningún "
                f"registro en `db_evidence`. Valores observados en evidencia: {sorted(list(evidence_numbers))[:10]}..."
            )

    is_grounded = len(errors) == 0
    return is_grounded, errors


# ─────────────────────────────────────────────────────────────────────────────
# 3. VALIDADOR DE REPORTE ESTRATÉGICO (9 SECCIONES OBLIGATORIAS)
# ─────────────────────────────────────────────────────────────────────────────

MANDATORY_REPORT_KEYS = [
    "identificacion_sector",
    "mercado_tendencias",
    "clientes",
    "problemas",
    "soluciones",
    "hipotesis",
    "objetivos",
    "impacto",
    "hallazgos",
]


def validate_strategic_report(report: Any) -> bool:
    """
    Asegura que el reporte estratégico del Investigador contenga las 9 secciones
    obligatorias sin campos vacíos ni nulos.
    
    Secciones:
    1. identificacion_sector
    2. mercado_tendencias
    3. clientes
    4. problemas
    5. soluciones
    6. hipotesis
    7. objetivos
    8. impacto
    9. hallazgos
    """
    if not isinstance(report, dict):
        return False

    # Validación mediante esquema Pydantic
    try:
        validated = StrategicReportModel(**report)
        # Verificar que no sean cadenas vacías o solo espacios
        for key in MANDATORY_REPORT_KEYS:
            val = getattr(validated, key, "")
            if not isinstance(val, str) or not val.strip():
                return False
        return True
    except (ValidationError, TypeError, AttributeError):
        # Fallback a chequeo directo por clave
        for key in MANDATORY_REPORT_KEYS:
            if key not in report:
                return False
            val = report[key]
            if val is None or (isinstance(val, str) and not val.strip()):
                return False
        return True
