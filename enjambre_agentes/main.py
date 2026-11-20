#!/usr/bin/env python3
"""
Tiendita IA — Ecosistema Comercial Multimodal con Visión Artificial y Orquestación Multiagente.
Tecnología NVIDIA (NIM / NeMo) + LangGraph + PostgreSQL Vectorial + Dual RAG.

Punto de entrada CLI principal.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from config.keys import validate_keys
from config.models import listar_modelos_disponibles
from agents.graph import run_orchestration

TEST_CASES_PATH = Path(__file__).resolve().parent / "tests" / "test_cases.json"


def ejecutar_banco_pruebas() -> None:
    """Ejecuta los escenarios base de tests/test_cases.json sin requerir modo interactivo."""
    if not TEST_CASES_PATH.exists():
        print(f"Error: No se encontró {TEST_CASES_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        casos = json.load(f)

    print("\n" + "=" * 70)
    print("  (^_^) [TIENDITA IA] — EJECUCIÓN DEL BANCO DE PRUEBAS")
    print(f"  Total de escenarios: {len(casos)}")
    print("=" * 70 + "\n")

    for i, c in enumerate(casos, 1):
        print(f"\n--- [ESCENARIO {i}/{len(casos)}]: {c['id']} - {c['nombre']} ---")
        print(f"  Fuente:      {c['event_source']}")
        print(f"  Descripción: {c['descripcion']}")
        tid = f"test-{c['id']}-{str(uuid.uuid4())[:6]}"
        try:
            res = run_orchestration(
                input_text=c["input_text"],
                thread_id=tid,
                event_source=c["event_source"],
                vision_payload=c.get("vision_payload"),
                ui_state=c.get("ui_state")
            )
            mensajes = res.get("messages", [])
            ultimo = mensajes[-1].content if mensajes else "Completado."
            print(f"  Resultado:   {ultimo[:200]}...")
            if res.get("pending_approval"):
                print(f"  [HITL]:      Acción sensible detenida en approval_gate: {res['pending_approval'].get('action_type')}")
            print(f"  (^_^)/ [OK] Escenario {c['id']} completado exitosamente.")
        except Exception as e:
            print(f"  [X_X] [ERROR] Falló escenario {c['id']}: {e}", file=sys.stderr)

    print("\n" + "=" * 70)
    print("  (^_^) [TODOS LOS CASOS DE PRUEBA COMPLETADOS]")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tiendita IA — Ecosistema Comercial Multimodal Multiagente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py "Registrar compra de mercancía por $1,200 en abarrotes"
  python main.py "Cobro en mostrador de 2 leches Lala y 1 pan Bimbo" --source pos-checkout
  python main.py "Elaborar reporte estratégico para tiendita de barrio" --provider NVIDIA
  python main.py --list-models
  python main.py --test
        """
    )

    parser.add_argument("consulta", type=str, nargs="?", default="", help="Instrucción comercial o consulta para el enjambre.")
    parser.add_argument("--source", type=str, default="chat", choices=["chat", "catalog-scan", "pos-checkout", "receipt-ocr", "cron"], help="Fuente del evento detonante.")
    parser.add_argument("--provider", type=str, default="NVIDIA", help="Proveedor de LLM a utilizar (default: NVIDIA).")
    parser.add_argument("--thread-id", type=str, default=None, help="Identificador único del hilo de sesión.")
    parser.add_argument("--list-models", action="store_true", help="Lista en vivo los modelos soportados por cada proveedor y finaliza.")
    parser.add_argument("--test", action="store_true", help="Ejecuta automáticamente los 5 escenarios base de tests/test_cases.json.")

    args = parser.parse_args()

    if args.list_models:
        print("\n=== Modelos Disponibles en Vivo ===")
        modelos = listar_modelos_disponibles()
        for prov, mods in modelos.items():
            print(f"\n[{prov}]:")
            for m in mods[:6]:
                print(f"  - {m}")
        sys.exit(0)

    if args.test:
        ejecutar_banco_pruebas()
        sys.exit(0)

    if not args.consulta:
        parser.print_help()
        sys.exit(1)

    tid = args.thread_id or str(uuid.uuid4())

    print("\n" + "=" * 70)
    print("  (^-^)/ [TIENDITA IA] — Ecosistema Comercial Multimodal Multiagente")
    print("=" * 70)
    print(f"  Instrucción:  {args.consulta}")
    print(f"  Fuente:       {args.source}")
    print(f"  Proveedor:    {args.provider}")
    print(f"  Thread ID:    {tid[:8]}...")
    print(f"  Inicio:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    try:
        resultado = run_orchestration(
            input_text=args.consulta,
            thread_id=tid,
            event_source=args.source,
            provider=args.provider
        )

        print("\n" + "=" * 70)
        print("  (^_^) [OK] ORQUESTACION COMPLETADA")
        print("=" * 70)

        mensajes = resultado.get("messages", [])
        for m in mensajes:
            texto = m.content if hasattr(m, "content") else str(m)
            print(f"\n{texto}")

        if resultado.get("pending_approval"):
            print("\n[!_!] ACCION PENDIENTE DE APROBACION HUMANA (HITL):")
            print(json.dumps(resultado["pending_approval"], indent=2, ensure_ascii=False))

    except Exception as err:
        print(f"\n[X_X] [ERROR: ORQUESTACION] {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
