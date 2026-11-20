#!/usr/bin/env python3
"""
Script de exportación de feedback Human-in-the-Loop (HITL) hacia formato SFT
(Supervised Fine-Tuning) para entrenamiento de adaptadores LoRA con NVIDIA NeMo Customizer.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "hitl_feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_FILE = FEEDBACK_DIR / "nemo_sft_dataset.jsonl"
EXPORT_FILE = FEEDBACK_DIR / "nemo_customizer_train.jsonl"

# Muestras sintéticas base para validar el pipeline de exportación si aún no hay interacción humana
_MUESTRAS_BASE = [
    {
        "timestamp": datetime.utcnow().isoformat(),
        "role": "control",
        "input": "Ticket de compra por 3 cajas de mayonesa y 2 rollos de cinta canela",
        "agent_output": "Mayonesa: inversion_inventario ($810.00). Cinta canela: gasto_operativo ($90.00).",
        "approved": True,
        "correction": None,
        "operator_notes": "Aprobado por el dueño."
    },
    {
        "timestamp": datetime.utcnow().isoformat(),
        "role": "vendedor",
        "input": "Cliente comprando 2 litros de leche Lala en caja",
        "agent_output": "¿Gusta agregar pan blanco Bimbo o unas galletas Marías para el desayuno?",
        "approved": True,
        "correction": None,
        "operator_notes": "Excelente sugerencia de upselling matutino."
    },
    {
        "timestamp": datetime.utcnow().isoformat(),
        "role": "tutor_ui",
        "input": "Terminal en pantalla 'ingreso_nip' con error 'CHIP_NO_DETECTADO'",
        "agent_output": "Retire la tarjeta y limpie el chip suavemente. Intente insertarla de nuevo con firmeza o use el sensor sin contacto.",
        "approved": True,
        "correction": None,
        "operator_notes": "Cumple estrictamente con el límite de 2 oraciones accionables."
    }
]


def asegurar_dataset_base():
    """Si no existe el archivo de feedback, inicializa con muestras de alta fidelidad."""
    if not FEEDBACK_FILE.exists() or FEEDBACK_FILE.stat().st_size == 0:
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            for m in _MUESTRAS_BASE:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")


def exportar_dataset():
    asegurar_dataset_base()
    registros_sft = []

    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                item = json.loads(linea)
            except Exception:
                continue

            if item.get("approved"):
                respuesta_objetivo = item.get("correction") or str(item.get("agent_output"))
                muestra_sft = {
                    "messages": [
                        {"role": "system", "content": f"Eres el agente especialista en {item.get('role', 'comercio')} de Tiendita IA."},
                        {"role": "user", "content": item.get("input", "")},
                        {"role": "assistant", "content": respuesta_objetivo}
                    ]
                }
                registros_sft.append(muestra_sft)

    with open(EXPORT_FILE, "w", encoding="utf-8") as out:
        for r in registros_sft:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Exportadas {len(registros_sft)} muestras en formato SFT listas para NeMo Customizer en:")
    print(f"-> {EXPORT_FILE}")


if __name__ == "__main__":
    exportar_dataset()
