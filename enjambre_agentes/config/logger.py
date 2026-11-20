"""
Sistema de logging expresivo y trazabilidad para Tiendita IA.
Combina etiquetas formales en mayúsculas con kaomojis ASCII para estados comerciales y cognitivos.
"""
from __future__ import annotations

import sys
from typing import Any

# Códigos de color ANSI para terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

_USAR_COLORES = True

KAOMOJIS_COMERCIO = {
    "BIENVENIDA": "(^-^)/",
    "VENTA": "(^o^)/",
    "COBRO": "\\(^o^)/",
    "INSPECCION": "(・_・)?",
    "ALERTA_STOCK": "(ಠ_ಠ)",
    "CADUCIDAD": "(¬_¬)",
    "AUDITORIA": "(˘_˘)",
    "ESTRATEGIA": "(ง •̀_•́)ง",
    "HITL": "[!_!]",
    "ERROR": "[X_X]",
    "OK": "(^_^)/"
}


def _fmt(tag: str, kaomoji: str, msg: str, color: str = "") -> str:
    if _USAR_COLORES and color:
        return f"{color}{BOLD}{kaomoji} {tag}{RESET} {msg}"
    return f"{kaomoji} {tag} {msg}"


def log_agente(agente: str, msg: str, kaomoji: str = "(o_o)"):
    """Registra la actividad de un agente especialista."""
    tag = f"[AGENTE: {agente.upper()}]"
    print(_fmt(tag, kaomoji, msg, CYAN), flush=True)


def log_herramienta(nombre: str, msg: str, kaomoji: str = "(>_<)"):
    """Registra la ejecución de una herramienta comercial."""
    tag = f"[TOOL: {nombre}]"
    print(_fmt(tag, kaomoji, msg, YELLOW), flush=True)


def log_hitl(msg: str, kaomoji: str = "[!_!]"):
    """Registra una pausa o reanudación Human-in-the-Loop."""
    tag = "[HITL: APROBACION_HUMANA]"
    print(_fmt(tag, kaomoji, msg, MAGENTA), flush=True)


def log_ok(msg: str, kaomoji: str = "(^_^)/"):
    """Registra una operación exitosa."""
    print(_fmt("[OK]", kaomoji, msg, GREEN), flush=True)


def log_alerta(msg: str, kaomoji: str = "(¬_¬)"):
    """Registra una alerta operativa."""
    print(_fmt("[ALERTA]", kaomoji, msg, YELLOW), flush=True)


def log_error(msg: str, kaomoji: str = "[X_X]"):
    """Registra un error controlado."""
    print(_fmt("[ERROR]", kaomoji, msg, RED), flush=True)
