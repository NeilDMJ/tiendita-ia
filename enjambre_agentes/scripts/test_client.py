#!/usr/bin/env python3
"""
Cliente de Prueba Remoto/LAN (REST + WebSockets + HITL) para Tiendita IA.
Permite validar desde otra PC o localmente que el servidor responde por HTTP JSON y WebSockets.

Ejemplos:
  uv run python -m scripts.test_client --url http://127.0.0.1:8000
  uv run python -m scripts.test_client --url http://192.168.1.50:8000 --api-key mi_clave
  uv run python -m scripts.test_client --url https://abc123.lhr.life --mode ws --hitl-action reject
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
import websockets
from rich.console import Console
from rich.panel import Panel

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.keys import get_tiendita_api_key

console = Console()


def _http_to_ws_url(base_url: str, api_key: str) -> str:
    clean = base_url.rstrip("/")
    if clean.startswith("https://"):
        ws_base = "wss://" + clean[len("https://"):]
    elif clean.startswith("http://"):
        ws_base = "ws://" + clean[len("http://"):]
    else:
        ws_base = f"ws://{clean}"
    ws_url = f"{ws_base}/ws/orchestrate"
    if api_key:
        ws_url += "?" + urlencode({"api_key": api_key})
    return ws_url


def probar_rest(base_url: str, api_key: str, message: str) -> None:
    headers = {"X-API-Key": api_key} if api_key else {}
    console.print(f"\n[bold cyan]=== 1. PRUEBA REST ({base_url}) ===[/bold cyan]")

    with httpx.Client(timeout=45.0) as client:
        r_health = client.get(f"{base_url.rstrip('/')}/health")
        r_health.raise_for_status()
        h = r_health.json()
        console.print(
            f"[green]✓ GET /health:[/green] status={h['status']} | auth={h.get('auth_enabled')} | "
            f"db_connected={h.get('database', {}).get('connected')}"
        )

        r_orch = client.post(
            f"{base_url.rstrip('/')}/orchestrate",
            headers=headers,
            json={"input_text": message, "event_source": "chat"},
        )
        r_orch.raise_for_status()
        d = r_orch.json()
        console.print(
            Panel(
                d.get("reply", "(sin respuesta)"),
                title=f"POST /orchestrate (agent={d.get('next_agent')}, thread={str(d.get('thread_id'))[:8]}...)",
                border_style="green",
            )
        )


async def probar_websocket(
    base_url: str,
    api_key: str,
    message: str,
    event_source: str = "chat",
    hitl_action: Optional[str] = None,
) -> None:
    ws_url = _http_to_ws_url(base_url, api_key)
    console.print(f"\n[bold cyan]=== 2. PRUEBA WEBSOCKET ({ws_url.split('?')[0]}) ===[/bold cyan]")

    async with websockets.connect(ws_url, open_timeout=15) as ws:
        hello = json.loads(await ws.recv())
        console.print(f"[green]✓ Conectado:[/green] {hello}")

        await ws.send(json.dumps({
            "message": message,
            "event_source": event_source,
            "thread_id": hello.get("thread_id"),
        }))

        while True:
            ev = json.loads(await ws.recv())
            ev_type = ev.get("type")

            if ev_type == "session_started":
                console.print(f"[dim]▶ Sesión iniciada: thread={ev.get('thread_id')} source={ev.get('event_source')}[/dim]")
            elif ev_type == "node_update":
                console.print(f"  [magenta]● Nodo ejecutado:[/magenta] {ev.get('node')}")
            elif ev_type == "hitl_required":
                console.print(
                    Panel(
                        json.dumps(ev.get("approval"), indent=2, ensure_ascii=False),
                        title="[bold red]HITL REQUERIDO EN WEBSOCKET[/bold red]",
                        border_style="magenta",
                    )
                )
                accion = hitl_action
                if not accion:
                    accion = input("Decisión HITL [approve / reject]: ").strip().lower() or "reject"
                await ws.send(json.dumps({
                    "action": accion,
                    "notes": f"Respuesta desde test_client ({accion})",
                }))
            elif ev_type == "hitl_resolved":
                res = ev.get("result", {})
                console.print(
                    Panel(
                        res.get("reply", "(resuelto)"),
                        title=f"HITL Resuelto (approved={ev.get('approved')})",
                        border_style="green",
                    )
                )
                break
            elif ev_type == "completed":
                res = ev.get("result", {})
                console.print(
                    Panel(
                        res.get("reply", "(completado)"),
                        title=f"WebSocket Completado (agent={res.get('next_agent')})",
                        border_style="green",
                    )
                )
                break
            elif ev_type == "error":
                console.print(f"[bold red]✗ Error en WebSocket:[/bold red] {ev.get('detail')}")
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Cliente de prueba REST + WebSocket para Tiendita IA")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL base del servidor (LAN o túnel HTTPS).")
    parser.add_argument("--api-key", default=None, help="API Key opcional (default: TIENDITA_API_KEY de .env).")
    parser.add_argument("--message", default="¿Cuáles son los 3 productos más vendidos?", help="Mensaje de prueba.")
    parser.add_argument("--source", default="chat", choices=["chat", "vision_api", "ui_copilot", "cron_trigger"])
    parser.add_argument("--mode", default="all", choices=["rest", "ws", "all"], help="Protocolo a probar.")
    parser.add_argument("--hitl-action", default=None, choices=["approve", "reject"], help="Respuesta automática si salta HITL.")
    args = parser.parse_args()

    api_key = args.api_key if args.api_key is not None else get_tiendita_api_key()

    if args.mode in ("rest", "all"):
        probar_rest(args.url, api_key, args.message)
    if args.mode in ("ws", "all"):
        asyncio.run(probar_websocket(args.url, api_key, args.message, args.source, args.hitl_action))


if __name__ == "__main__":
    main()
