"""
guards.py — Gobernanza determinista y validadores anti-alucinaciones.

Implementa:
1. `enforce_db_grounding`: Valida que los datos monetarios y cantidades críticas
   mencionadas por los agentes estén respaldados matemáticamente por la evidencia
   recuperada de PostgreSQL (`db_evidence`).
2. `validate_strategic_report`: Verifica el cumplimiento de las 9 secciones
   obligatorias del reporte estratégico comercial generado por el Investigador.
3. Capa híbrida NeMo Guardrails + reglas deterministas (sección 4):
   - Input rails: prompt injection en chat o en texto extraído por OCR/visión.
   - Output rails: Tutor UI (≤ 2 oraciones, solo elementos visibles) y ocultamiento de
     costos internos de proveedor en interacciones públicas de mostrador.

Las reglas viven en funciones puras de Python (siempre activas). Si NEMO_GUARDRAILS_ENABLED=true y
`nemoguardrails` está instalado, `config/guardrails/` ejecuta además los mismos controles como flujos
Colang. `enforce_db_grounding` sigue siendo la barrera final y no depende de ninguna de las dos capas.
"""
from __future__ import annotations

import contextvars
import functools
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, Field, ValidationError

from models import run_sync
from state import StrategicReportModel

logger = logging.getLogger(__name__)


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


# ────────────────────────────────────────────────────────────────────────────────
# 4. CAPA HÍBRIDA: NEMO GUARDRAILS + VALIDACIÓN DETERMINISTA
# ────────────────────────────────────────────────────────────────────────────────

GUARDRAILS_CONFIG_DIR = Path(__file__).resolve().parent / "config" / "guardrails"

# Interacciones de cara al cliente en mostrador: cámara POS y copiloto de pagos de la app.
# `chat` (dueño/dashboard) y `cron_trigger` (interno) son internas.
PUBLIC_EVENT_SOURCES: FrozenSet[str] = frozenset({"vision_api", "ui_copilot"})

# Claves que revelan el costo de proveedor (directa o derivadamente)
INTERNAL_COST_KEYS: FrozenSet[str] = frozenset(
    {"costo_unitario", "costo", "costo_total", "margen_pesos", "margen_porcentaje"}
)
_COST_VALUE_KEYS: FrozenSet[str] = frozenset({"costo_unitario", "costo", "costo_total"})
_PRICE_VALUE_KEYS: FrozenSet[str] = frozenset(
    {"precio_venta", "precio_unitario", "precio", "subtotal", "total", "total_a_cobrar"}
)

INJECTION_REFUSAL = (
    "Detecté instrucciones sospechosas dentro del contenido recibido y lo bloqueé. "
    "Envía solo datos de la tienda."
)
INTERNAL_ONLY_MESSAGE = "Esa información es de uso interno del negocio y no se muestra en mostrador."


class GuardrailVerdict(BaseModel):
    """
    Resultado de un rail. `text` siempre es seguro de usar: es el original si `allowed` es True,
    o la versión reparada / mensaje de rechazo si hubo violaciones.
    """
    allowed: bool = True
    text: str = ""
    violations: List[str] = Field(default_factory=list)
    engine: Literal["python", "nemo+python"] = "python"


# ── utilidades de texto ──

def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _split_units(text: str) -> List[str]:
    """Divide en oraciones y líneas (los informes del Analista usan saltos de línea)."""
    return [u.strip() for u in re.split(r"(?<=[.!?])\s+|\n+", text) if u.strip()]


def _join_units(units: List[str], original: str) -> str:
    return ("\n" if "\n" in original else " ").join(units)


def _iter_strings(obj: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(obj, str):
        yield path or "$", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{path}[{i}]")


# ── INPUT RAIL: prompt injection ──

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)

_INJECTION_RULES: Tuple[Tuple[str, str], ...] = (
    ("ignorar_instrucciones", r"\b(ignor\w*|olvid\w*|descart\w*|omit\w*|desestim\w*|saltate)\b[^.\n]{0,40}\b(instrucciones|reglas|indicaciones|directrices|restricciones|politicas)\b"),
    ("ignore_instructions_en", r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(instructions?|prompts?|rules|guidelines|restrictions)\b"),
    ("revelar_prompt", r"\b(muestra\w*|revela\w*|imprime\w*|repite\w*|dime|dame|filtra\w*)\b[^.\n]{0,30}\b(system prompt|prompt del sistema|prompt de sistema|instrucciones internas|instrucciones ocultas|tu prompt)\b"),
    ("reveal_prompt_en", r"\b(reveal|show|print|repeat|leak)\b[^.\n]{0,30}\b(system prompt|hidden instructions|your prompt|your instructions)\b"),
    ("cambio_de_rol", r"\b(ahora eres|a partir de ahora eres|actua como si|finge ser|simula ser|haz de cuenta que eres|nuevo rol)\b"),
    ("role_override_en", r"\b(you are now|from now on you are|pretend (to be|you are)|new role)\b"),
    ("marcador_de_rol", r"(^|\n)\s*(system|sistema|assistant|asistente|developer)\s*:"),
    ("tokens_de_control", r"<\|?(im_start|im_end|system|endoftext)\|?>|\[/?inst\]|<<sys>>"),
    ("jailbreak", r"\b(do anything now|modo desarrollador|developer mode|jailbreak)\b"),
    ("exfiltracion", r"\b(envia\w*|manda\w*|exfiltr\w*|filtra\w*|send|leak)\b[^.\n]{0,50}\b(api[ _-]?key|contrasena|password|token|credenciales|secret\w*)\b"),
    ("saltar_hitl", r"\b(omit\w*|salta\w*|evita\w*|desactiva\w*|skip|bypass)\b[^.\n]{0,25}\b(aprobacion|confirmacion|hitl|approval|confirmation)\b"),
    ("html_oculto", r"<!--|<\s*(script|iframe|style)\b"),
)
_COMPILED_INJECTION = tuple((name, re.compile(pat)) for name, pat in _INJECTION_RULES)


def _has_invisible_text(text: str) -> bool:
    """Caracteres de formato usados para ocultar instrucciones (tag chars U+E0000 o ráfagas de ancho cero)."""
    if any(0xE0000 <= ord(c) <= 0xE007F for c in text):
        return True
    return len(text) - len(text.translate(_ZERO_WIDTH)) >= 8


def detect_prompt_injection(text: str) -> List[str]:
    """Devuelve los nombres de las reglas de prompt injection que coinciden (lista vacía = limpio)."""
    if not text:
        return []
    found: List[str] = []
    if _has_invisible_text(text):
        found.append("texto_invisible")
    cleaned = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    cleaned = "".join(c for c in cleaned if c in "\n\t" or unicodedata.category(c)[0] != "C")
    scan = _strip_accents(cleaned).lower()
    found.extend(name for name, pat in _COMPILED_INJECTION if pat.search(scan))
    return found


# ── OUTPUT RAIL: Tutor UI ──

# Catálogo por defecto (subcadena de `pantalla`). Solo contiene nombres que el propio sistema usa.
# La app móvil puede enviar `ui_state["elementos_visibles"]` para una validación autoritativa.
UI_ELEMENT_CATALOG: Dict[str, FrozenSet[str]] = {
    "spei": frozenset({"CLABE Interbancaria", "Confirmar Transferencia", "Verificar Pago SPEI", "Verificar y Continuar"}),
    "tarjeta": frozenset({"CVV", "Pagar con Tarjeta"}),
    "qr": frozenset(),
}
_QUOTED_UI_REF = re.compile(
    r"['\u2018\u2019\"\u201c\u201d\u00ab]([^'\u2018\u2019\"\u201c\u201d\u00ab\u00bb\n]{2,60})['\u2018\u2019\"\u201c\u201d\u00bb]"
)


def _norm_ui(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _strip_accents(text).lower()).strip()


def allowed_ui_elements(ui_state: Dict[str, Any]) -> Optional[Set[str]]:
    """
    Elementos de UI que el tutor puede nombrar: campos vacíos + (`elementos_visibles` declarados
    por la app, o el catálogo por pantalla). None si la pantalla no se puede verificar.
    """
    fields = {_norm_ui(str(c)) for c in (ui_state.get("campos_vacios") or [])}
    declared = ui_state.get("elementos_visibles")
    if declared is not None:
        return {_norm_ui(str(e)) for e in declared} | fields
    pantalla = _norm_ui(str(ui_state.get("pantalla", "")))
    for key, elements in UI_ELEMENT_CATALOG.items():
        if key in pantalla:
            return {_norm_ui(e) for e in elements} | fields
    return None


def _is_known_ui_element(ref: str, allowed: Set[str]) -> bool:
    r = _norm_ui(ref)
    return any(a and (r == a or r in a or a in r) for a in allowed)


def _tutor_fallback(ui_state: Dict[str, Any]) -> List[str]:
    """Guía segura construida solo con datos de `ui_state` cuando no sobrevive ninguna oración."""
    out: List[str] = []
    fields = ui_state.get("campos_vacios") or []
    if fields:
        out.append(f"Completa el campo '{str(fields[0]).replace('_', ' ').title()}' antes de continuar.")
    if ui_state.get("error_visible"):
        out.append(f"La pantalla indica: {ui_state['error_visible']}")
    return out[:2] or ["Revisa los datos de la pantalla actual y vuelve a intentarlo."]


def _tutor_rules(text: str, ui_state: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
    ui = ui_state or {}
    violations: List[str] = []
    units = _split_units(text)
    allowed = allowed_ui_elements(ui)
    kept: List[str] = []
    for unit in units:
        unknown = (
            [r for r in _QUOTED_UI_REF.findall(unit) if not _is_known_ui_element(r, allowed)]
            if allowed is not None else []
        )
        if unknown:
            violations.extend(f"tutor_ui:elemento_inexistente:{r}" for r in unknown)
            continue
        kept.append(unit)
    if len(units) > 2:
        violations.append("tutor_ui:mas_de_2_oraciones")
    kept = kept[:2]
    if not kept:
        violations.append("tutor_ui:sin_contenido_valido")
        kept = _tutor_fallback(ui)
    return " ".join(kept), violations


# ── OUTPUT RAIL: costos internos en mostrador ──

_COST_KEYWORDS = re.compile(
    r"\b(costos?|coste|costo[ _]unitario|precio de (compra|costo|proveedor|mayoreo)|"
    r"margen(es)?|utilidad(es)?|ganancia bruta|markup)\b"
)


def is_public_event_source(event_source: Optional[str]) -> bool:
    return event_source in PUBLIC_EVENT_SOURCES


def _collect_keyed_numbers(data: Any, keys: FrozenSet[str]) -> Set[float]:
    found: Set[float] = set()
    if isinstance(data, dict):
        for k, v in data.items():
            if k in keys and isinstance(v, (int, float)) and not isinstance(v, bool):
                found.add(round(float(v), 2))
            found.update(_collect_keyed_numbers(v, keys))
    elif isinstance(data, list):
        for item in data:
            found.update(_collect_keyed_numbers(item, keys))
    return found


def _cost_rules(text: str, event_source: Optional[str], db_evidence: Optional[List[Dict[str, Any]]]) -> Tuple[str, List[str]]:
    if not is_public_event_source(event_source):
        return text, []
    evidence = db_evidence or []
    leaking = _collect_keyed_numbers(evidence, _COST_VALUE_KEYS) - _collect_keyed_numbers(evidence, _PRICE_VALUE_KEYS)

    violations: List[str] = []
    kept: List[str] = []
    for unit in _split_units(text):
        if _COST_KEYWORDS.search(_strip_accents(unit).lower()):
            violations.append("costos_internos:palabra_clave")
        elif any(abs(a - c) < 0.005 for a in _extract_monetary_values(unit) for c in leaking):
            violations.append("costos_internos:monto_igual_a_costo_unitario")
        else:
            kept.append(unit)
    if not violations:
        return text, []
    return (_join_units(kept, text) if kept else INTERNAL_ONLY_MESSAGE), violations


def redact_internal_costs(data: Any) -> Any:
    """Copia de `data` sin las claves de costo/margen (para evidencia expuesta en mostrador)."""
    if isinstance(data, dict):
        return {k: redact_internal_costs(v) for k, v in data.items() if k not in INTERNAL_COST_KEYS}
    if isinstance(data, list):
        return [redact_internal_costs(v) for v in data]
    return data


# ── CAPA NEMO GUARDRAILS (opcional) ──

# Contexto visible por las acciones Colang (rol, ui_state, event_source, db_evidence).
_RAIL_CTX: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("guardrails_ctx", default={})


async def _action_check_prompt_injection(text: str = "") -> bool:
    return not detect_prompt_injection(text)


async def _action_check_tutor_output(text: str = "") -> bool:
    ctx = _RAIL_CTX.get()
    if ctx.get("role") != "tutor_ui":
        return True
    return not _tutor_rules(text, ctx.get("ui_state"))[1]


async def _action_check_cost_exposure(text: str = "") -> bool:
    ctx = _RAIL_CTX.get()
    if ctx.get("role") not in ("vendedor", "analista"):
        return True
    return not _cost_rules(text, ctx.get("event_source"), ctx.get("db_evidence"))[1]


_RAIL_ACTIONS: Dict[str, Callable[..., Any]] = {
    "check_prompt_injection": _action_check_prompt_injection,
    "check_tutor_output": _action_check_tutor_output,
    "check_cost_exposure": _action_check_cost_exposure,
}


def _nemo_enabled() -> bool:
    return os.getenv("NEMO_GUARDRAILS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


@functools.lru_cache(maxsize=1)
def _load_rails() -> Optional[Any]:
    """Carga `config/guardrails/` una sola vez; None si el paquete o la config no están disponibles."""
    try:
        from nemoguardrails import RailsConfig
    except ImportError:
        logger.warning(
            "NEMO_GUARDRAILS_ENABLED=true pero `nemoguardrails` no está instalado "
            "(uv sync --extra guardrails). Se usa solo la capa determinista."
        )
        return None
    try:
        config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_DIR))
        try:
            from nemoguardrails import Guardrails
            rails = Guardrails(config, use_iorails=False)
        except (ImportError, TypeError):
            from nemoguardrails import LLMRails
            rails = LLMRails(config)
        for name, action in _RAIL_ACTIONS.items():
            rails.register_action(action, name)
        return rails
    except Exception as exc:
        logger.warning("No se pudo cargar NeMo Guardrails desde %s: %s", GUARDRAILS_CONFIG_DIR, exc)
        return None


async def _nemo_check_async(
    messages: List[Dict[str, str]], rail_type: Literal["INPUT", "OUTPUT"], ctx: Dict[str, Any]
) -> Optional[Tuple[bool, Optional[str]]]:
    rails = _load_rails()
    if rails is None:
        return None
    from nemoguardrails.rails.llm.options import RailStatus, RailType

    token = _RAIL_CTX.set(ctx)
    try:
        result = await rails.check_async(messages, rail_types=[getattr(RailType, rail_type)])
    finally:
        _RAIL_CTX.reset(token)
    return (result.status != RailStatus.BLOCKED), getattr(result, "rail", None)


def _nemo_check(
    messages: List[Dict[str, str]], rail_type: Literal["INPUT", "OUTPUT"], ctx: Dict[str, Any]
) -> Optional[Tuple[bool, Optional[str]]]:
    """(permitido, rail_que_bloqueó) o None si la capa NeMo está desactivada/no disponible."""
    if not _nemo_enabled():
        return None
    try:
        return run_sync(_nemo_check_async(messages, rail_type, ctx))
    except Exception as exc:  # un fallo de NeMo nunca debe tumbar el grafo
        logger.warning("NeMo Guardrails falló (%s); continúa la capa determinista.", exc)
        return None


# ── API PÚBLICA DE LA CAPA HÍBRIDA ──

def check_input(text: str) -> GuardrailVerdict:
    """Input rail sobre un texto no confiable (mensaje de chat o texto extraído de un ticket/imagen)."""
    violations: List[str] = []
    engine: Literal["python", "nemo+python"] = "python"

    nemo = _nemo_check([{"role": "user", "content": text}], "INPUT", {})
    if nemo is not None:
        engine = "nemo+python"
        if not nemo[0]:
            violations.append(f"nemo:{nemo[1]}")

    violations.extend(f"prompt_injection:{r}" for r in detect_prompt_injection(text))
    allowed = not violations
    return GuardrailVerdict(
        allowed=allowed, text=text if allowed else INJECTION_REFUSAL, violations=violations, engine=engine
    )


def scan_untrusted_inputs(query: str = "", vision_payload: Optional[Dict[str, Any]] = None) -> GuardrailVerdict:
    """
    Input rails sobre el mensaje de chat y sobre TODOS los textos del `vision_payload`
    (nombres, descripciones, proveedor...): es donde viaja la injection oculta de un ticket.
    """
    sources: List[Tuple[str, str]] = []
    if query and query.strip():
        sources.append(("query", query))
    for path, value in _iter_strings(vision_payload or {}):
        if len(value) >= 8:
            sources.append((f"vision_payload.{path}", value))

    violations: List[str] = []
    engine: Literal["python", "nemo+python"] = "python"
    for label, value in sources:
        verdict = check_input(value)
        if verdict.engine != "python":
            engine = verdict.engine
        violations.extend(f"{v}@{label}" for v in verdict.violations)

    allowed = not violations
    return GuardrailVerdict(
        allowed=allowed, text=query if allowed else INJECTION_REFUSAL, violations=violations, engine=engine
    )


def check_tutor_output(text: str, ui_state: Optional[Dict[str, Any]] = None) -> GuardrailVerdict:
    """Output rail de `tutor_ui`: ≤ 2 oraciones y sin botones/campos que no existan en `ui_state`."""
    engine: Literal["python", "nemo+python"] = "python"
    nemo_violations: List[str] = []
    nemo = _nemo_check(
        [{"role": "user", "content": ""}, {"role": "assistant", "content": text}],
        "OUTPUT", {"role": "tutor_ui", "ui_state": ui_state or {}},
    )
    if nemo is not None:
        engine = "nemo+python"
        if not nemo[0]:
            nemo_violations.append(f"nemo:{nemo[1]}")

    final, violations = _tutor_rules(text, ui_state)
    violations = nemo_violations + violations
    return GuardrailVerdict(allowed=not violations, text=final, violations=violations, engine=engine)


def check_cost_exposure(
    role: str,
    text: str,
    event_source: Optional[str],
    db_evidence: Optional[List[Dict[str, Any]]] = None,
) -> GuardrailVerdict:
    """Output rail de `vendedor`/`analista`: oculta costos de proveedor en interacciones públicas."""
    if role not in ("vendedor", "analista"):
        return GuardrailVerdict(text=text)
    engine: Literal["python", "nemo+python"] = "python"
    nemo_violations: List[str] = []
    if is_public_event_source(event_source):
        nemo = _nemo_check(
            [{"role": "user", "content": ""}, {"role": "assistant", "content": text}],
            "OUTPUT", {"role": role, "event_source": event_source, "db_evidence": db_evidence or []},
        )
        if nemo is not None:
            engine = "nemo+python"
            if not nemo[0]:
                nemo_violations.append(f"nemo:{nemo[1]}")

    final, violations = _cost_rules(text, event_source, db_evidence)
    violations = nemo_violations + violations
    return GuardrailVerdict(allowed=not violations, text=final, violations=violations, engine=engine)
