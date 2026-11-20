#!/usr/bin/env python3
"""
export_nemo_sft.py — Exporta el dataset SFT (Data Flywheel) para NeMo Customizer.

Lee los ejemplos verificados (PostgreSQL `ejemplos_few_shot` si hay DATABASE_URL, más el buffer
local `datasets/hitl_feedback.jsonl`) y escribe JSONL conversacional:
    {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

Customizer espera archivos de entrenamiento y de validación separados; por defecto se reserva
el 10 % (split determinista por hash del registro, estable entre ejecuciones).

Uso:
    uv run python scripts/export_nemo_sft.py
    uv run python scripts/export_nemo_sft.py --rol vendedor --solo-hitl
    uv run python scripts/export_nemo_sft.py --rol tutor_ui --output datasets/tutor_train.jsonl --val-ratio 0.2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from few_shot_retriever import DEFAULT_SFT_PATH, FewShotRetriever  # noqa: E402

MIN_RECOMMENDED = 50  # mínimo orientativo de la guía de Customizer para tareas simples


def _val_path(train_path: Path) -> Path:
    if "train" in train_path.name:
        return train_path.with_name(train_path.name.replace("train", "val", 1))
    return train_path.with_name(f"{train_path.stem}_val{train_path.suffix}")


def _is_validation(record: dict, ratio: float) -> bool:
    digest = hashlib.sha1(json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF < ratio


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta el dataset SFT para NeMo Customizer.")
    parser.add_argument("--output", default=DEFAULT_SFT_PATH, help=f"Archivo de entrenamiento (default: {DEFAULT_SFT_PATH})")
    parser.add_argument("--rol", action="append", dest="roles", metavar="ROL",
                        help="Limita a un rol (repetible): control, vendedor, publicista, orquestador, tutor_ui, ocr, investigador. "
                             "Úsalo para entrenar un adaptador LoRA por rol (NEMO_MODEL_<ROL>).")
    parser.add_argument("--solo-hitl", action="store_true",
                        help="Solo interacciones aprobadas/editadas por operadores (excluye semillas y dataset del asistente).")
    parser.add_argument("--val-ratio", type=float, default=0.1,
                        help="Fracción para el archivo de validación (0 = sin archivo de validación). Default 0.1.")
    args = parser.parse_args()
    if not 0.0 <= args.val_ratio < 1.0:
        parser.error("--val-ratio debe estar en [0, 1).")

    retriever = FewShotRetriever()
    train_path = Path(args.output)
    val_path = _val_path(train_path)
    train_path.parent.mkdir(parents=True, exist_ok=True)

    n_train = n_val = 0
    val_file = open(val_path, "w", encoding="utf-8") if args.val_ratio > 0 else None
    try:
        with open(train_path, "w", encoding="utf-8") as train_file:
            for record in retriever.iter_sft_records(roles=args.roles, solo_hitl=args.solo_hitl):
                line = json.dumps(record, ensure_ascii=False) + "\n"
                if val_file is not None and _is_validation(record, args.val_ratio):
                    val_file.write(line)
                    n_val += 1
                else:
                    train_file.write(line)
                    n_train += 1
    finally:
        if val_file is not None:
            val_file.close()

    total = n_train + n_val
    print(f"Entrenamiento: {n_train} registros -> {train_path}")
    if args.val_ratio > 0:
        print(f"Validación:    {n_val} registros -> {val_path}")
    if total == 0:
        print("No hay registros verificados. Aprueba acciones en el flujo HITL o ejecuta `few_shot_retriever.py seed`.")
        return 1
    if total < MIN_RECOMMENDED:
        print(f"Aviso: {total} registros; la guía de Customizer sugiere al menos {MIN_RECOMMENDED}-100 para tareas simples.")
    if args.val_ratio > 0 and n_val == 0:
        print("Aviso: el split de validación quedó vacío (pocos registros); Customizer necesita validación para detectar overfitting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
