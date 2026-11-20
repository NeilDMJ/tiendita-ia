#!/usr/bin/env python3
"""
Tiendita IA — Ecosistema Comercial Multimodal con Visión Artificial y Orquestación Multiagente.
Tecnología NVIDIA (NIM / NeMo) + LangGraph + PostgreSQL Real (`DATABASE_URL`).

Punto de entrada principal:
  uv run python main.py
  uv run python main.py --agent-brain vendedor=Gemini:gemini-flash-lite-latest
  uv run python main.py --agent-brain investigador=Groq:openai/gpt-oss-120b --agent-brain tutor_ui=Ollama:llama3.2
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import List, Tuple

from config.models import (
    AGENT_ROLES,
    extraer_texto_mensaje,
    get_active_brains,
    listar_modelos_disponibles,
    set_agent_brain,
)
from agents.graph import run_orchestration
from tools.db_client import close_db_pool


def _parse_agent_brain_spec(spec: str) -> Tuple[str, str, str]:
    """
    Parsea `<rol>=<proveedor>:<modelo>` (ej. `vendedor=Gemini:gemini-flash-lite-latest`
    o `supervisor=NVIDIA:nvidia/nemotron-3-super-120b-a12b`).
    """
    if "=" not in spec:
        raise ValueError(f"Formato inválido '{spec}'. Usa <rol>=<proveedor>:<modelo>.")
    role, rest = spec.split("=", 1)
    if ":" not in rest:
        raise ValueError(f"Formato inválido '{spec}'. Usa <rol>=<proveedor>:<modelo>.")
    provider, model_name = rest.split(":", 1)
    return role.strip(), provider.strip(), model_name.strip()


def aplicar_cerebros_cli(specs: List[str]) -> None:
    """Aplica todos los overrides `--agent-brain` antes de lanzar el CLI o la consulta."""
    for spec in specs:
        role, provider, model_name = _parse_agent_brain_spec(spec)
        set_agent_brain(role, provider, model_name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tiendita IA — Interfaz CLI Interactiva Conectada a PostgreSQL Real",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  uv run python main.py
  uv run python main.py --agent-brain vendedor=Gemini:gemini-flash-lite-latest
  uv run python main.py --agent-brain investigador=Groq:openai/gpt-oss-120b --agent-brain tutor_ui=Ollama:llama3.2
  uv run python main.py --query "¿Qué productos están próximos a caducar?"
  uv run python main.py --list-models
        """,
    )

    parser.add_argument(
        "--agent-brain",
        action="append",
        default=[],
        metavar="ROL=PROVEEDOR:MODELO",
        help=(
            "Asigna un proveedor y modelo personalizado a un subagente al iniciar "
            f"(repetible). Roles: {', '.join(AGENT_ROLES)}."
        ),
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Ejecuta una sola consulta no interactiva contra el grafo y finaliza.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="chat",
        choices=["chat", "vision_api", "ui_copilot", "cron", "catalog-scan", "pos-checkout", "receipt-ocr"],
        help="event_source para ejecución de una sola consulta (--query).",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Lista los modelos disponibles por proveedor y finaliza.",
    )
    parser.add_argument(
        "--brains",
        action="store_true",
        help="Muestra la configuración activa de los 7 cerebros en formato JSON y finaliza.",
    )

    args = parser.parse_args()

    # 1. Aplicar overrides individuales por agente si se pasaron por CLI
    if args.agent_brain:
        try:
            aplicar_cerebros_cli(args.agent_brain)
        except ValueError as err:
            print(f"[ERROR] {err}", file=sys.stderr)
            sys.exit(2)

    # 2. Comandos informativos puntuales
    if args.list_models:
        modelos = listar_modelos_disponibles()
        for prov, mods in modelos.items():
            print(f"\n[{prov}] ({len(mods)}):")
            for m in mods[:10]:
                print(f"  - {m}")
        sys.exit(0)

    if args.brains:
        print(json.dumps(get_active_brains(), indent=2, ensure_ascii=False))
        sys.exit(0)

    # 3. Modo one-shot opcional (--query)
    if args.query:
        try:
            res = run_orchestration(
                input_text=args.query,
                thread_id=str(uuid.uuid4()),
                event_source=args.source,
            )
            for m in res.get("messages", []):
                if getattr(m, "type", "ai") != "human":
                    print(extraer_texto_mensaje(m.content if hasattr(m, "content") else m))
        finally:
            close_db_pool()
        sys.exit(0)

    # 4. Por defecto: lanzar directamente el CLI interactivo completo
    from scripts.cli_tester import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
