#!/usr/bin/env python3
"""
cli_tester.py — Mini-chatbot interactivo de terminal para el Ecosistema Multiagente Comercial.

Uso básico:
    python cli_tester.py
    python cli_tester.py --provider NVIDIA --model meta/llama-3.1-8b-instruct
    python cli_tester.py --thread-id sesion_prueba_01

Slash commands disponibles (escríbelos en la consola):
    /pos       Simula cobro POS por cámara (/pos-checkout) + HITL
    /ticket    Simula lectura de factura OCR (/receipt-ocr)
    /vision    Carga payload JSON desde archivo: /vision ruta/archivo.json
    /pago      Simula pantalla de pago con error CVV en app móvil
    /cron      Disparo programado de alertas de caducidad
    /estado    Muestra el estado interno actual de la sesión
    /nuevo     Reinicia la sesión con un nuevo thread_id
    /ayuda     Lista todos los comandos
    /salir     Cierra el CLI
"""
from __future__ import annotations

import sys
import os
import json
import argparse
import uuid
import re
from datetime import datetime
from typing import Any, Dict, Optional

# ─── Añadir el directorio actual al path si es necesario ────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from graph import run_orchestration, run_orchestration_stream, resume_orchestration
from tools_bridge import to_mcp_tool_definitions
from response_formatter import formatear_respuesta, formatear_para_cli, respuesta_json

# ─── Rich: decoración con fallback limpio ────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.text import Text
    from rich.rule import Rule
    from rich import print as rprint
    _RICH = True
    console = Console()
except ImportError:
    _RICH = False
    console = None  # type: ignore

# ─────────────────────────────────────────────────────────────────────────────
# PALETA DE COLORES / ESTILOS
# ─────────────────────────────────────────────────────────────────────────────
_AGENT_COLORS = {
    "supervisor":      "bold cyan",
    "control":         "bold yellow",
    "vendedor":        "bold green",
    "analista":        "bold blue",
    "investigador":    "bold magenta",
    "publicista":      "bold red",
    "tutor_ui":        "bold white",
    "aprobacion_hitl": "bold bright_red",
    "FIN":             "dim",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE IMPRESIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _hr(label: str = "") -> None:
    if _RICH:
        console.print(Rule(f"[dim]{label}[/dim]", style="dim"))
    else:
        print(f"\n{'─'*60}{'  ' + label if label else ''}")


def _print(msg: str, style: str = "") -> None:
    if _RICH:
        console.print(msg, style=style or None)
    else:
        # Quitar marcado Rich para fallback
        clean = re.sub(r"\[/?[^\]]*\]", "", msg)
        print(clean)


def _panel(content: str, title: str, style: str = "cyan") -> None:
    if _RICH:
        console.print(Panel(content, title=title, border_style=style))
    else:
        print(f"\n┌── {title} ──\n{content}\n└─────────────")


def _header() -> None:
    banner = (
        "  🛒  TIENDITA IA — Ecosistema Multiagente Comercial  🛒\n"
        "  LangGraph · 6 Agentes · HITL · Visión Artificial · MCP"
    )
    _panel(banner, "CLI Tester v0.3", "bright_cyan")
    _print("[dim]Escribe tu mensaje o un /comando. Usa /ayuda para ver opciones.[/dim]")


def _print_node_transition(node: str, state: Dict[str, Any]) -> None:
    """Muestra en tiempo real cada transición de nodo del grafo."""
    color = _AGENT_COLORS.get(node, "white")
    iteration = state.get("iteration_count", "?")
    next_a = state.get("next_agent", "?")
    db_ev = len(state.get("db_evidence", []))
    errors = state.get("validation_errors", [])

    if _RICH:
        line = (
            f"  [{color}]▶ {node.upper()}[/{color}]"
            f"  iter [bold]{iteration}/6[/bold]"
            f"  → [cyan]{next_a}[/cyan]"
            f"  db_evidence=[green]{db_ev}[/green]"
        )
        if errors:
            line += f"  [red]⚠ {len(errors)} error(es)[/red]"
        console.print(line)
    else:
        print(f"  ▶ {node.upper()}  iter {iteration}/6  → {next_a}  db_evidence={db_ev}")
        if errors:
            print(f"  ⚠ Errores: {errors}")


def _print_last_message(result: Dict[str, Any]) -> None:
    """Imprime el último mensaje usando el formato estructurado del response_formatter."""
    formateada = formatear_respuesta(result)
    print(formatear_para_cli(formateada))


def _render_strategic_report(report: Dict[str, Any]) -> None:
    """Renderiza el reporte estratégico de 9 secciones del Investigador."""
    _hr("REPORTE ESTRATÉGICO — 9 SECCIONES")
    if _RICH:
        tbl = Table(title="Reporte Comercial Tiendita IA", show_lines=True, border_style="magenta")
        tbl.add_column("Sección", style="bold magenta", width=24)
        tbl.add_column("Contenido", style="white", width=70)
        for key, val in report.items():
            tbl.add_row(key.replace("_", " ").title(), str(val))
        console.print(tbl)
    else:
        for key, val in report.items():
            print(f"  [{key.upper()}] {val}")


def _render_promo_assets(assets: Dict[str, Any]) -> None:
    """Renderiza los activos promocionales del Publicista (video 9:16 + copy + CTA)."""
    _hr("ACTIVOS PROMOCIONALES 🎬")
    _panel(
        assets.get("video_prompt", ""),
        "🎥 Video Prompt (9:16 · 5s · Inglés cinematográfico)",
        style="red",
    )
    _panel(assets.get("copy_promocional", ""), "📝 Copy Promocional", style="yellow")
    _panel(assets.get("call_to_action", ""), "📣 Call to Action", style="green")
    if assets.get("video_url"):
        _print(f"  🔗 Video URL: [dim]{assets['video_url']}[/dim]")


def _render_db_evidence(evidence: list) -> None:
    """Muestra registros reales de db_evidence para transparencia del grounding."""
    if not evidence:
        return
    _hr(f"db_evidence ({len(evidence)} registro(s))")
    for i, ev in enumerate(evidence, 1):
        _print(f"  [{i}] {json.dumps(ev, ensure_ascii=False, default=str)[:200]}", style="dim")


def _handle_hitl(pending: Dict[str, Any], thread_id: str, provider: str, model_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Muestra la interrupción HITL y espera la decisión del operador.
    Opciones: s=aprobar, n=rechazar, e=editar JSON y luego aprobar.
    """
    _hr("⏸  INTERRUPCIÓN HITL — SE REQUIERE APROBACIÓN HUMANA")

    if _RICH:
        tbl = Table(title="Acción Pendiente de Confirmación", show_lines=True, border_style="bright_red")
        tbl.add_column("Campo", style="bold", width=20)
        tbl.add_column("Valor", style="white", width=74)
        tbl.add_row("action_type", pending.get("action_type", ""))
        tbl.add_row("summary", pending.get("summary", ""))
        tbl.add_row("payload", json.dumps(pending.get("payload", {}), ensure_ascii=False, indent=2)[:600])
        console.print(tbl)
    else:
        print(f"  Tipo     : {pending.get('action_type')}")
        print(f"  Resumen  : {pending.get('summary')}")
        print(f"  Payload  : {json.dumps(pending.get('payload', {}), indent=2)[:400]}")

    while True:
        raw = input("\n  ¿Aprobar esta acción? [s = aprobar / n = rechazar / e = editar JSON]: ").strip().lower()
        if raw in ("s", "si", "sí", "y", "yes"):
            return resume_orchestration(thread_id=thread_id, approved=True)
        elif raw in ("n", "no"):
            return resume_orchestration(thread_id=thread_id, approved=False)
        elif raw in ("e", "editar", "edit"):
            print("  Pega el JSON editado del payload (en una sola línea) y presiona Enter:")
            raw_json = input("  > ").strip()
            try:
                edited = json.loads(raw_json)
                return resume_orchestration(thread_id=thread_id, approved=True, edited_payload=edited)
            except json.JSONDecodeError as ex:
                _print(f"  [red]JSON inválido: {ex}. Intenta de nuevo.[/red]")
        else:
            _print("  [yellow]Opción no reconocida. Escribe 's', 'n' o 'e'.[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────
# SLASH COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

SLASH_HELP = """
[bold cyan]Slash Commands disponibles:[/bold cyan]

  /pos              Simula cobro POS por cámara (/pos-checkout) → HITL
  /ticket           Simula lectura de factura OCR (/receipt-ocr) → HITL
  /vision <archivo> Carga un archivo JSON como vision_payload personalizado
  /pago             Simula error CVV en pantalla de pago móvil (Tutor UI)
  /cron             Disparo de alertas de caducidad (cron_trigger → control)
  /estado           Inspecciona el estado interno de la sesión actual
  /nuevo            Reinicia la sesión con un thread_id fresco
  /ayuda            Muestra este menú
  /salir            Cierra el CLI

[dim]O escribe cualquier mensaje en lenguaje natural:[/dim]
  "¿Cuánto me queda de la Coca?"
  "Sube la leche a $31"
  "Genera el reporte estratégico de mercado"
  "Haz una promo de video para los Takis"
"""

_POS_PAYLOAD = {
    "endpoint": "/pos-checkout",
    "items": [
        {"sku": "COCA-600", "cantidad": 2},
        {"sku": "BIMB-BLAN", "cantidad": 1},
    ],
    "confianza_global": 0.98,
}

_TICKET_PAYLOAD = {
    "endpoint": "/receipt-ocr",
    "proveedor": "Distribuidora de Lácteos del Centro S.A.",
    "items": [{"descripcion": "Caja Leche Lala 12 pzas", "cantidad": 2, "precio_unitario": 260.00, "subtotal": 520.00}],
    "total": 520.00,
    "tipo_movimiento": "inversion_inventario",
    "confianza_global": 0.96,
}

_PAGO_UI_STATE = {
    "pantalla": "checkout_tarjeta",
    "paso_actual": "cvv_invalido",
    "campos_vacios": ["cvv"],
    "error_visible": "CVV_INVALID: El código de seguridad no es correcto.",
    "intentos": 2,
}


# ─────────────────────────────────────────────────────────────────────────────
# EJECUTOR PRINCIPAL DE UN TURNO
# ─────────────────────────────────────────────────────────────────────────────

def _run_turn(
    *,
    query: str = "",
    event_source: str = "chat",
    vision_payload: Optional[Dict[str, Any]] = None,
    ui_state: Optional[Dict[str, Any]] = None,
    thread_id: str,
    provider: str,
    model_name: Optional[str],
    session_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ejecuta un turno completo del grafo vía streaming e imprime cada transición.
    Detecta HITL y llama al handler interactivo.
    Retorna el estado final del turno.
    """
    _hr(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]")
    _print(f"[bold]Enviando al enjambre...[/bold] [dim]thread={thread_id}  event={event_source}[/dim]")

    result_buffer: Dict[str, Any] = {}
    hitl_pending: Optional[Dict[str, Any]] = None

    if _RICH:
        spinner = Spinner("dots", text="Procesando...")
        with Live(spinner, console=console, transient=True):
            for step in run_orchestration_stream(
                query=query,
                thread_id=thread_id,
                event_source=event_source,
                vision_payload=vision_payload,
                ui_state=ui_state,
                provider=provider,
                model_name=model_name,
            ):
                pass  # Collect stream silently while spinner shows
        # Second pass: render transitions
        for step in _replay_steps_from_result(
            query=query,
            thread_id=thread_id,
            event_source=event_source,
            vision_payload=vision_payload,
            ui_state=ui_state,
            provider=provider,
            model_name=model_name,
        ):
            node_name = list(step.keys())[0] if step else None
            if node_name:
                node_state = step[node_name]
                _print_node_transition(node_name, node_state)
                result_buffer.update(node_state)
                pending = node_state.get("pending_approval")
                if pending and pending.get("requires_confirmation"):
                    hitl_pending = pending
    else:
        for step in run_orchestration_stream(
            query=query,
            thread_id=thread_id,
            event_source=event_source,
            vision_payload=vision_payload,
            ui_state=ui_state,
            provider=provider,
            model_name=model_name,
        ):
            node_name = list(step.keys())[0] if step else None
            if node_name:
                node_state = step[node_name]
                _print_node_transition(node_name, node_state)
                result_buffer.update(node_state)
                pending = node_state.get("pending_approval")
                if pending and pending.get("requires_confirmation"):
                    hitl_pending = pending

    # Renderizar salidas especiales
    if result_buffer.get("strategic_report"):
        _render_strategic_report(result_buffer["strategic_report"])
    if result_buffer.get("promo_assets"):
        _render_promo_assets(result_buffer["promo_assets"])
    _render_db_evidence(result_buffer.get("db_evidence", []))
    _print_last_message(result_buffer)

    # HITL: si el grafo pausó, pedir decisión
    if hitl_pending:
        hitl_result = _handle_hitl(hitl_pending, thread_id=thread_id, provider=provider, model_name=model_name)
        if hitl_result:
            _print_last_message(hitl_result)
            result_buffer.update(hitl_result)

    session_state.update(result_buffer)
    return result_buffer


def _replay_steps_from_result(*, query, thread_id, event_source, vision_payload, ui_state, provider, model_name):
    """Re-runs stream with a new thread_id suffix for rendering — avoids checkpointer replay issues."""
    replay_thread = thread_id + "_replay_" + uuid.uuid4().hex[:6]
    yield from run_orchestration_stream(
        query=query,
        thread_id=replay_thread,
        event_source=event_source,
        vision_payload=vision_payload,
        ui_state=ui_state,
        provider=provider,
        model_name=model_name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL DEL CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Tester del Ecosistema Multiagente Comercial — Tiendita IA")
    parser.add_argument("--provider",  default=os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"), help="Proveedor LLM (NVIDIA, Gemini, Groq, Ollama)")
    parser.add_argument("--model",     default=None, help="Nombre del modelo (opcional)")
    parser.add_argument("--thread-id", default=None, help="Thread ID de sesión (se genera automáticamente si no se especifica)")
    args = parser.parse_args()

    provider   = args.provider
    model_name = args.model
    thread_id  = args.thread_id or f"cli_{uuid.uuid4().hex[:8]}"
    session_state: Dict[str, Any] = {}

    _header()
    _print(f"[dim]Sesión iniciada:  thread_id=[bold]{thread_id}[/bold]  provider=[bold]{provider}[/bold]  model={model_name or 'default'}[/dim]")
    _hr()

    while True:
        try:
            if _RICH:
                raw = console.input("[bold cyan]Tú>[/bold cyan] ").strip()
            else:
                raw = input("Tú> ").strip()
        except (KeyboardInterrupt, EOFError):
            _print("\n[dim]Sesión terminada por interrupción.[/dim]")
            break

        if not raw:
            continue

        # ── Slash Commands ─────────────────────────────────────────────────
        lower = raw.lower()

        if lower in ("/salir", "/exit", "/quit", "/q"):
            _print("[dim]¡Hasta luego! Cerrando CLI.[/dim]")
            break

        elif lower in ("/ayuda", "/help", "/h", "/?"):
            if _RICH:
                console.print(SLASH_HELP)
            else:
                print(re.sub(r"\[/?[^\]]*\]", "", SLASH_HELP))

        elif lower == "/pos":
            _print("[bold green]▶ Simulando POS por cámara (/pos-checkout)...[/bold green]")
            _run_turn(
                event_source="vision_api",
                vision_payload=_POS_PAYLOAD,
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                session_state=session_state,
            )

        elif lower == "/ticket":
            _print("[bold yellow]▶ Simulando lectura de factura OCR (/receipt-ocr)...[/bold yellow]")
            _run_turn(
                event_source="vision_api",
                vision_payload=_TICKET_PAYLOAD,
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                session_state=session_state,
            )

        elif lower.startswith("/vision"):
            parts = raw.split(maxsplit=1)
            if len(parts) < 2:
                _print("[red]Uso: /vision <ruta/al/archivo.json>[/red]")
                continue
            filepath = parts[1].strip()
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    custom_payload = json.load(f)
                _print(f"[bold]Cargando vision_payload desde {filepath}...[/bold]")
                _run_turn(
                    event_source="vision_api",
                    vision_payload=custom_payload,
                    thread_id=thread_id,
                    provider=provider,
                    model_name=model_name,
                    session_state=session_state,
                )
            except FileNotFoundError:
                _print(f"[red]Archivo no encontrado: {filepath}[/red]")
            except json.JSONDecodeError as ex:
                _print(f"[red]JSON inválido en {filepath}: {ex}[/red]")

        elif lower == "/pago":
            _print("[bold white]▶ Simulando error de pago en app móvil (Tutor UI)...[/bold white]")
            _run_turn(
                event_source="ui_copilot",
                ui_state=_PAGO_UI_STATE,
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                session_state=session_state,
            )

        elif lower == "/cron":
            _print("[bold cyan]▶ Disparando cron_trigger de alertas de caducidad...[/bold cyan]")
            _run_turn(
                event_source="cron_trigger",
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                session_state=session_state,
            )

        elif lower == "/estado":
            _hr("ESTADO INTERNO DE LA SESIÓN")
            info = {
                "thread_id":        thread_id,
                "provider":         provider,
                "model_name":       model_name or "default",
                "iteration_count":  session_state.get("iteration_count", 0),
                "pending_approval": session_state.get("pending_approval"),
                "db_evidence_len":  len(session_state.get("db_evidence", [])),
                "validation_errors": session_state.get("validation_errors", []),
                "next_agent":       session_state.get("next_agent", "supervisor"),
                "sender":           session_state.get("sender", "—"),
            }
            if _RICH:
                tbl = Table(show_header=True, border_style="cyan")
                tbl.add_column("Clave", style="bold cyan", width=22)
                tbl.add_column("Valor", style="white")
                for k, v in info.items():
                    tbl.add_row(k, json.dumps(v, ensure_ascii=False, default=str))
                console.print(tbl)
            else:
                for k, v in info.items():
                    print(f"  {k}: {v}")

        elif lower == "/nuevo":
            thread_id = f"cli_{uuid.uuid4().hex[:8]}"
            session_state.clear()
            _print(f"[bold green]✓ Nueva sesión iniciada. thread_id=[bold]{thread_id}[/bold][/bold green]")

        else:
            # Mensaje en lenguaje natural → chat
            _run_turn(
                query=raw,
                event_source="chat",
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                session_state=session_state,
            )

    _hr()
    _print(f"[dim]Sesión '{thread_id}' finalizada.[/dim]")


if __name__ == "__main__":
    main()
