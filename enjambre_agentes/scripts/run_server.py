#!/usr/bin/env python3
"""
Lanzador Nativo de Servidor API + WebSockets + Túnel SSH para Tiendita IA.
Usa EXCLUSIVAMENTE librería estándar de Python (`socket`, `subprocess`, `threading`, `re`, `signal`)
junto con `uvicorn`, `fastapi` y `rich` ya presentes en el entorno (cero ngrok/pyngrok).

Uso directo:
  uv run python -m scripts.run_server
  uv run python -m scripts.run_server --port 8000 --tunnel localhost.run
  uv run python -m scripts.run_server --tunnel pinggy
  uv run python -m scripts.run_server --tunnel vps

O desde main.py:
  uv run python main.py --serve
  uv run python main.py --serve --tunnel
  uv run python main.py --serve --tunnel pinggy --agent-brain vendedor=Gemini:gemini-flash-lite-latest
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.keys import API_HOST, API_PORT, SSH_VPS_TARGET, get_tiendita_api_key
from tools.db_client import close_db_pool, verify_db_connection

console = Console()

# Regex para capturar URLs públicas HTTPS emitidas por localhost.run o pinggy
_PUBLIC_HTTPS_RE = re.compile(r"(https://[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}(?::\d+)?)")
_IGNORED_URL_FRAGMENTS = (
    "localhost.run/docs",
    "admin.localhost.run",
    "twitter.com",
    "github.com",
    "dashboard.pinggy.io",
    "pinggy.io/docs",
    "pinggy.io/quickstart",
)


# ---------------------------------------------------------------------------
# Detección de Red Interna (LAN) y Construcción de Comandos SSH Nativos
# ---------------------------------------------------------------------------

def detectar_ip_lan() -> str:
    """
    Detecta la IP local de la interfaz Wi-Fi / Ethernet activa usando `socket` estándar
    sin transmitir paquetes reales hacia Internet.
    """
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80), ("192.168.1.1", 80)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.5)
            sock.connect(target)
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            continue
        finally:
            sock.close()

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return "127.0.0.1"


def construir_comando_ssh(tunnel_mode: str, port: int, vps_target: Optional[str] = None) -> List[str]:
    """Construye el comando `ssh` nativo de Linux según el modo solicitado."""
    mode = tunnel_mode.strip().lower()
    if mode == "localhost.run":
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-R", f"80:localhost:{port}",
            "nokey@localhost.run",
        ]
    if mode == "pinggy":
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-p", "443",
            f"-R0:localhost:{port}",
            "a.pinggy.io",
        ]
    if mode == "vps":
        target = (vps_target or os.getenv("SSH_VPS_TARGET", "") or SSH_VPS_TARGET).strip()
        if not target:
            raise ValueError(
                "El modo '--tunnel vps' requiere definir SSH_VPS_TARGET en .env "
                "(ej. SSH_VPS_TARGET=usuario@tu-vps.com)."
            )
        return [
            "ssh",
            "-N",
            "-o", "ServerAliveInterval=30",
            "-R", f"0.0.0.0:{port}:127.0.0.1:{port}",
            target,
        ]
    raise ValueError(f"Modo de túnel no soportado: '{tunnel_mode}'. Usa: localhost.run, pinggy o vps.")


def extraer_url_publica(linea: str) -> Optional[str]:
    """Extrae una URL pública https:// válida de la salida del subproceso ssh."""
    # Limpiar posibles códigos ANSI de colores emitidos por pinggy/localhost.run
    limpia = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", linea)
    for match in _PUBLIC_HTTPS_RE.findall(limpia):
        url_lower = match.lower()
        if any(ign in url_lower for ign in _IGNORED_URL_FRAGMENTS):
            continue
        # Evitar la URL raíz informativa de localhost.run o pinggy.io sin subdominio asignado
        host = url_lower.replace("https://", "").split(":")[0]
        if host in ("localhost.run", "pinggy.io", "a.pinggy.io", "www.pinggy.io"):
            continue
        return match.rstrip("/")
    return None


def _mostrar_panel_lan(host: str, port: int, lan_ip: str) -> None:
    """Imprime el panel Rich con URLs LAN, estado BD, autenticación y comandos de firewall."""
    db_info = verify_db_connection()
    api_key = get_tiendita_api_key()

    db_line = (
        f"[bold green]● PostgreSQL conectado:[/bold green] {db_info['database']} "
        f"({db_info['productos_activos']} productos | {db_info['ventas_registradas']} ventas)"
        if db_info.get("connected")
        else f"[bold red]✗ PostgreSQL no disponible:[/bold red] {db_info.get('error', 'sin conexión')}"
    )
    auth_line = (
        "[bold yellow]🔒 Autenticación X-API-Key / ?api_key ACTIVA[/bold yellow]"
        if api_key
        else "[bold green]🔓 Acceso abierto en LAN[/bold green] [dim](define TIENDITA_API_KEY en .env para proteger)[/dim]"
    )

    cuerpo = (
        f"{db_line}\n"
        f"{auth_line}\n\n"
        f"[bold cyan]Red Local (LAN — accesible desde otras PCs / Apps Móviles en el mismo Wi-Fi):[/bold cyan]\n"
        f"  • REST LAN:               [bold white]http://{lan_ip}:{port}[/bold white]\n"
        f"  • WebSocket LAN:          [bold white]ws://{lan_ip}:{port}/ws/orchestrate[/bold white]\n"
        f"  • Documentación Swagger:  [bold white]http://{lan_ip}:{port}/docs[/bold white]\n"
        f"  • Localhost (esta PC):    [dim]http://127.0.0.1:{port} (bind: {host}:{port})[/dim]\n\n"
        f"[bold yellow]Abrir puerto {port} en firewall Linux (si otras PCs en LAN no conectan):[/bold yellow]\n"
        f"  • Fedora/RHEL (firewalld): [dim]sudo firewall-cmd --add-port={port}/tcp --permanent && sudo firewall-cmd --reload[/dim]\n"
        f"  • Ubuntu/Debian (ufw):     [dim]sudo ufw allow {port}/tcp[/dim]"
    )
    console.print(
        Panel(
            cuerpo,
            title="[bold cyan]TIENDITA IA — Servidor API REST & WebSockets (LAN)[/bold cyan]",
            border_style="cyan",
        )
    )


def _mostrar_panel_tunel_publico(tunnel_mode: str, https_url: str, port: int) -> None:
    """Destaca en un panel Rich la URL pública HTTPS/WSS asignada por el túnel SSH nativo."""
    wss_url = https_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/ws/orchestrate"
    api_key = get_tiendita_api_key()
    ws_hint = f"{wss_url}?api_key=<TIENDITA_API_KEY>" if api_key else wss_url

    cuerpo = (
        f"[bold green]● TÚNEL SSH ACTIVO ({tunnel_mode})[/bold green]\n"
        f"  • REST Público:           [bold white]{https_url}[/bold white]\n"
        f"  • WebSocket Público:      [bold white]{ws_hint}[/bold white]\n"
        f"  • Swagger Público:        [bold white]{https_url}/docs[/bold white]\n\n"
        f"[dim]Firewall LAN (si también expones localmente): "
        f"sudo firewall-cmd --add-port={port}/tcp --permanent && sudo firewall-cmd --reload | sudo ufw allow {port}/tcp[/dim]"
    )
    console.print(
        Panel(
            cuerpo,
            title=f"[bold magenta]Exposición Externa Activa — SSH Nativo ({tunnel_mode})[/bold magenta]",
            border_style="magenta",
        )
    )


# ---------------------------------------------------------------------------
# Gestión del Subproceso SSH y Arranque Coordinado con Uvicorn
# ---------------------------------------------------------------------------

def _terminar_proceso_limpio(proc: Optional[subprocess.Popen], nombre: str) -> None:
    """Termina limpiamente un subproceso sin dejar procesos huérfanos."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
        console.print(f"[dim]Subproceso {nombre} detenido limpiamente.[/dim]")
    except Exception:
        pass


def _lanzar_tunel_ssh(
    tunnel_mode: str,
    port: int,
    stop_event: threading.Event,
) -> Optional[subprocess.Popen]:
    """Lanza el subproceso `ssh` nativo y vigila su salida en un hilo secundario para capturar la URL pública."""
    if not shutil.which("ssh"):
        console.print("[bold red]✗ No se encontró el binario 'ssh' en el sistema Linux.[/bold red]")
        return None

    try:
        cmd = construir_comando_ssh(tunnel_mode, port)
    except ValueError as err:
        console.print(f"[bold red]✗ {err}[/bold red]")
        return None

    console.print(f"[yellow]▶ Iniciando túnel SSH nativo ({tunnel_mode})...[/yellow] [dim]{' '.join(cmd)}[/dim]")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    if tunnel_mode == "vps":
        target = (os.getenv("SSH_VPS_TARGET", "") or SSH_VPS_TARGET).strip()
        vps_host = target.split("@", 1)[-1].split(":", 1)[0]
        _mostrar_panel_tunel_publico("vps", f"http://{vps_host}:{port}", port)
        return proc

    def _leer_salida_ssh():
        url_mostrada = False
        assert proc.stdout is not None
        try:
            for linea in proc.stdout:
                if stop_event.is_set():
                    break
                if not url_mostrada:
                    url = extraer_url_publica(linea)
                    if url:
                        url_mostrada = True
                        _mostrar_panel_tunel_publico(tunnel_mode, url, port)
        except Exception:
            pass

    hilo = threading.Thread(target=_leer_salida_ssh, name="ssh-tunnel-reader", daemon=True)
    hilo.start()
    return proc


def start_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    tunnel: Optional[str] = None,
    reload: bool = False,
) -> None:
    """
    Inicia el servidor FastAPI (`uvicorn`) en LAN y opcionalmente abre un túnel `ssh` nativo.
    Captura `SIGINT` y `SIGTERM` para apagar limpiamente uvicorn, el subproceso ssh y el pool de PostgreSQL.
    """
    bind_host = host or os.getenv("API_HOST", API_HOST) or "0.0.0.0"
    bind_port = int(port or os.getenv("API_PORT", str(API_PORT)) or 8000)
    lan_ip = detectar_ip_lan()

    _mostrar_panel_lan(bind_host, bind_port, lan_ip)

    stop_event = threading.Event()
    ssh_proc: Optional[subprocess.Popen] = None
    uvicorn_proc: Optional[subprocess.Popen] = None
    uvicorn_server = None

    def _handle_shutdown(signum, _frame):
        if stop_event.is_set():
            return
        stop_event.set()
        sig_name = signal.Signals(signum).name if signum in signal.Signals._value2member_map_ else str(signum)
        console.print(f"\n[yellow]Señal {sig_name} recibida. Cerrando servidor y túnel SSH limpiamente...[/yellow]")
        if uvicorn_server is not None:
            uvicorn_server.should_exit = True
        _terminar_proceso_limpio(uvicorn_proc, "uvicorn")
        _terminar_proceso_limpio(ssh_proc, "ssh-tunnel")

    prev_sigint = signal.signal(signal.SIGINT, _handle_shutdown)
    prev_sigterm = signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        if tunnel:
            ssh_proc = _lanzar_tunel_ssh(tunnel, bind_port, stop_event)

        if reload:
            # Con --reload uvicorn requiere ejecutarse como subproceso CLI
            uvicorn_cmd = [
                sys.executable, "-m", "uvicorn", "api:app",
                "--host", bind_host,
                "--port", str(bind_port),
                "--reload",
            ]
            uvicorn_proc = subprocess.Popen(uvicorn_cmd, cwd=str(_PROJECT_ROOT))
            while uvicorn_proc.poll() is None and not stop_event.is_set():
                time.sleep(0.3)
        else:
            # En el mismo proceso: preserva overrides --agent-brain aplicados desde main.py
            import uvicorn
            import api as api_module

            config = uvicorn.Config(
                app=api_module.app,
                host=bind_host,
                port=bind_port,
                log_level="info",
                ws="websockets",
            )
            uvicorn_server = uvicorn.Server(config)
            # Evitar que uvicorn sobreescriba nuestros signal handlers coordinados
            uvicorn_server.install_signal_handlers = lambda: None
            uvicorn_server.run()
    finally:
        stop_event.set()
        _terminar_proceso_limpio(uvicorn_proc, "uvicorn")
        _terminar_proceso_limpio(ssh_proc, "ssh-tunnel")
        cerradas = close_db_pool()
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)
        console.print(f"[dim]Servidor detenido y pool de PostgreSQL cerrado ({cerradas} conexiones liberadas).[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tiendita IA — Lanzador Nativo de API REST + WebSockets + Túnel SSH",
    )
    parser.add_argument("--host", type=str, default=None, help="Host de enlace (default: API_HOST o 0.0.0.0).")
    parser.add_argument("--port", type=int, default=None, help="Puerto HTTP/WS (default: API_PORT o 8000).")
    parser.add_argument(
        "--tunnel",
        nargs="?",
        const="localhost.run",
        default=None,
        choices=["localhost.run", "pinggy", "vps"],
        help="Expone el servidor a Internet con ssh nativo: localhost.run (default), pinggy o vps.",
    )
    parser.add_argument("--reload", action="store_true", help="Activa recarga automática de uvicorn (desarrollo).")
    args = parser.parse_args()
    start_server(host=args.host, port=args.port, tunnel=args.tunnel, reload=args.reload)


if __name__ == "__main__":
    main()
