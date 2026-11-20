"""
Recuperador dinámico de ejemplos Few-Shot y registrador de feedback HITL.
Alimenta ejemplos en tiempo de ejecución y almacena datos para fine-tuning LoRA / SFT con NeMo Customizer.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "hitl_feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_FILE = FEEDBACK_DIR / "nemo_sft_dataset.jsonl"

_FEW_SHOT_REPOSITORY: Dict[str, List[Dict[str, str]]] = {
    "control": [
        {
            "input": "Ticket de compra por 2 cajas de mayonesa y 1 rollo de cinta canela",
            "output": "Mayonesa: inversion_inventario ($540.00). Cinta canela: gasto_operativo ($45.00). Total validado."
        },
        {
            "input": "Foto de anaquel con 3 cajas de cereal abolladas y fecha 2026-11-21",
            "output": "Alerta de caducidad crítica (1 día). Sugerir merma o descuento inmediato del 40%."
        }
    ],
    "vendedor": [
        {
            "input": "Cliente comprando 1 café soluble grande de 200g",
            "output": "Sugerir sustituto de crema o pan dulce con frase: '¿Gusta agregar unas galletas Marías o leche Lala para acompañar su café?'"
        }
    ],
    "tutor_ui": [
        {
            "input": "Pantalla 'ingreso_nip' con error 'FALLA_CHIP'",
            "output": "action_sentence_1: 'Retire la tarjeta y limpie suavemente el chip dorado.' action_sentence_2: 'Intente insertarla de nuevo con firmeza o use el sensor sin contacto.'"
        }
    ]
}


@tool
def retrieve_few_shots(agent_role: str, query: Optional[str] = None, k: int = 2) -> str:
    """
    Recupera ejemplos de referencia Few-Shot dinámicos según el rol del agente activo
    (control, vendedor, analista, investigador, publicista, tutor_ui) para optimizar el razonamiento del LLM.
    """
    rol_key = agent_role.strip().lower()
    ejemplos = _FEW_SHOT_REPOSITORY.get(rol_key, [])
    if not ejemplos:
        return "Sin ejemplos few-shot específicos registrados para este rol."
    
    seleccionados = ejemplos[:k]
    formato = "\n---\n".join([f"Entrada: {e['input']}\nSalida Ideal: {e['output']}" for e in seleccionados])
    return f"Ejemplos Few-Shot de referencia para {rol_key.upper()}:\n{formato}"


def record_hitl_feedback(
    agent_role: str,
    user_input: str,
    agent_output: Any,
    human_approved: bool,
    correction: Optional[str] = None,
    notes: Optional[str] = None
) -> None:
    """
    Persiste en formato JSONL cada interacción revisada por un operador humano.
    Genera el corpus para entrenamiento de adaptadores LoRA con NeMo Customizer.
    """
    registro = {
        "timestamp": datetime.utcnow().isoformat(),
        "role": agent_role,
        "input": user_input,
        "agent_output": agent_output,
        "approved": human_approved,
        "correction": correction,
        "operator_notes": notes
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
