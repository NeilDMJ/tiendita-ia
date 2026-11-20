#!/usr/bin/env python3
"""
CLI Interactivo Real de Tiendita IA (Python puro + Rich + PostgreSQL + LangGraph).
Ejecutable con:
  uv run python -m scripts.cli_tester
  uv run python main.py [--agent-brain rol=proveedor:modelo ...]

Comandos disponibles:
  <texto libre>                                  -> Consulta/acción comercial real (PostgreSQL + Tavily/RAG)
  /cerebro <agente> <proveedor> <modelo>         -> Cambia en vivo el LLM de un subagente específico
  /cerebros                                      -> Asistente interactivo para asignar modelos por subagente
  /reset-cerebros                                -> Restaura todos los agentes al perfil 100% NVIDIA NIM
  /imagen <ruta_archivo.jpg|png> <catalog|pos|ticket> -> Procesa una imagen real del disco vía NIM Vision
  /pago <metodo:codi|spei|dimo> <pantalla> <paso> [error_code] -> Asistencia Tutor UI respaldada por RAG CoDi/SPEI/DiMo
  /rag <consulta>                                -> Consulta el índice RAG (FAISS / pgvector) de CoDi, SPEI y DiMo con relevancia
  /cron                                          -> Barrido real de caducidades y stock crítico en PostgreSQL
  /estado                                        -> Inspecciona OrchestratorState real y métricas de PostgreSQL
  /ayuda                                         -> Muestra la lista de comandos
  /salir | /exit                                 -> Cierra limpiamente el pool de PostgreSQL y sale
"""
from __future__ import annotations

import base64
import json
import mimetypes
import shlex
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# Asegurar que la raíz del proyecto esté en sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.models import (
    AGENT_ROLES,
    PROVIDERS,
    extraer_texto_mensaje,
    get_active_brains,
    listar_modelos_disponibles,
    reset_brains_to_nvidia_default,
    set_agent_brain,
)
from agents.graph import get_graph_state, resume_orchestration, run_orchestration
from tools.db_client import close_db_pool, verify_db_connection
from tools.rag_nemo import buscar_rag_pagos

console = Console()

_ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_IMAGE_MODE_ENDPOINTS = {
    "catalog": "/catalog-scan",
    "pos": "/pos-checkout",
    "ticket": "/receipt-ocr",
}


# ---------------------------------------------------------------------------
# Renderizado Rich: Panel de BD Real + Tabla de 7 Cerebros
# ---------------------------------------------------------------------------

def mostrar_panel_inicio() -> Dict[str, Any]:
    """Valida conexión real a PostgreSQL (DATABASE_URL) y muestra estado de BD + tabla de 7 cerebros."""
    db_info = verify_db_connection()

    if db_info.get("connected"):
        db_body = (
            f"[bold green]● CONECTADO A POSTGRESQL[/bold green]\n"
            f"[bold]DSN:[/bold] {db_info['dsn']}\n"
            f"[bold]Base de datos:[/bold] {db_info['database']} (usuario: {db_info['user']}, PostgreSQL {db_info['pg_version']})\n"
            f"[bold]Inventario real:[/bold] {db_info['productos_activos']} productos activos | "
            f"[yellow]{db_info['lotes_por_caducar']} lotes por caducar[/yellow] | "
            f"[red]{db_info['alertas_stock_bajo']} alertas stock bajo[/red]\n"
            f"[bold]Ventas registradas:[/bold] {db_info['ventas_registradas']} transacciones "
            f"(${db_info['ingresos_acumulados']:,.2f} MXN acumulados)"
        )
        border = "green"
    else:
        db_body = (
            f"[bold red]✗ ERROR DE CONEXIÓN A POSTGRESQL[/bold red]\n"
            f"[bold]DSN:[/bold] {db_info.get('dsn', 'No configurado')}\n"
            f"[bold]Detalle:[/bold] {db_info.get('error', 'Error desconocido')}\n"
            f"[yellow]Verifica que el contenedor tiendita-db esté activo y DATABASE_URL en .env sea correcta.[/yellow]"
        )
        border = "red"

    console.print(
        Panel.fit(
            "[bold cyan]TIENDITA IA — CLI Interactivo Real (PostgreSQL + LangGraph + NVIDIA NIM)[/bold cyan]\n"
            "[dim]Comandos: /cerebro, /cerebros, /reset-cerebros, /imagen, /pago, /rag, /cron, /estado, /ayuda, /salir[/dim]",
            border_style="cyan",
        )
    )
    console.print(Panel(db_body, title="Estado de Base de Datos PostgreSQL (En Vivo)", border_style=border))
    mostrar_tabla_cerebros()
    return db_info


def mostrar_tabla_cerebros(force_refresh: bool = False) -> None:
    """Muestra la tabla de los 7 agentes con su proveedor/modelo activo y rescate silencioso."""
    cerebros = get_active_brains(force_refresh=force_refresh)

    tabla = Table(title="Cerebros Activos por Subagente (7 Roles)", border_style="cyan")
    tabla.add_column("Agente", style="bold cyan", no_wrap=True)
    tabla.add_column("Proveedor", style="magenta", no_wrap=True)
    tabla.add_column("Modelo Activo", style="bold white")
    tabla.add_column("Modo", no_wrap=True)
    tabla.add_column("Temp", justify="right", style="dim")
    tabla.add_column("Rescate Silencioso (.with_fallbacks)", style="yellow")

    for rol, cfg in cerebros.items():
        modo_badge = (
            "[bold yellow]Personalizado[/bold yellow]"
            if cfg.get("is_custom")
            else "[bold green]NVIDIA Default[/bold green]"
        )
        fbs = cfg.get("fallbacks", [])
        rescate_str = " → ".join(fb["provider"] for fb in fbs) if fbs else "Sin respaldos"
        tabla.add_row(
            rol,
            cfg["provider"],
            cfg["model"],
            modo_badge,
            str(cfg["temperature"]),
            rescate_str,
        )
    console.print(tabla)


def mostrar_ayuda() -> None:
    tabla = Table(title="Comandos Disponibles en Tiendita IA", border_style="blue")
    tabla.add_column("Comando", style="bold cyan", no_wrap=True)
    tabla.add_column("Descripción", style="white")

    comandos = [
        ("<texto libre>", "Consulta inventario real, registra ventas, pide análisis financieros o investigaciones web."),
        ("/cerebro <agente> <proveedor> <modelo>", "Cambia el LLM de un subagente en vivo (ej. /cerebro vendedor Gemini gemini-flash-lite-latest)."),
        ("/cerebros", "Asistente interactivo que consulta listar_modelos_disponibles() y asigna modelos por subagente."),
        ("/reset-cerebros", "Devuelve los 7 agentes al perfil exclusivo 100% NVIDIA NIM."),
        ("/imagen <ruta.jpg|png> <catalog|pos|ticket>", "Lee una imagen real del disco, la codifica en base64 y la procesa vía NIM Vision."),
        ("/pago <metodo:codi|spei|dimo> <pantalla> <paso> [error_code]", "Envía ui_state de pagos digitales MX al Tutor UI (máx. 2 oraciones respaldadas por RAG)."),
        ("/rag <consulta>", "Busca en data/vectorstores/faiss/ o pgvector guías de CoDi, SPEI y DiMo con puntuación."),
        ("/cron", "Barrido real de lotes próximos a caducar y stock crítico en PostgreSQL (control → publicista)."),
        ("/estado", "Inspecciona el OrchestratorState real y las métricas en vivo de PostgreSQL."),
        ("/salir | /exit", "Cierra limpiamente el pool de PostgreSQL y finaliza la sesión."),
    ]
    for cmd, desc in comandos:
        tabla.add_row(cmd, desc)
    console.print(tabla)


# ---------------------------------------------------------------------------
# Gestión de Cerebros por Agente en Runtime
# ---------------------------------------------------------------------------

def comando_cerebro_directo(args: List[str]) -> None:
    """Procesa `/cerebro <agente> <proveedor> <modelo>`."""
    if len(args) < 3:
        console.print(
            "[yellow]Uso:[/yellow] /cerebro <agente> <proveedor> <modelo>\n"
            f"[dim]Agentes válidos: {', '.join(AGENT_ROLES)}[/dim]\n"
            f"[dim]Ejemplo: /cerebro vendedor Gemini gemini-flash-lite-latest[/dim]"
        )
        return

    agente = args[0]
    proveedor = args[1]
    modelo = " ".join(args[2:])
    try:
        prov_ok, mod_ok = set_agent_brain(agente, proveedor, modelo)
        console.print(
            f"[bold green]✓ Cerebro actualizado en vivo:[/bold green] "
            f"[cyan]{agente.lower()}[/cyan] → [magenta]{prov_ok}[/magenta] / [bold white]{mod_ok}[/bold white]"
        )
        mostrar_tabla_cerebros()
    except ValueError as err:
        console.print(f"[bold red]✗ {err}[/bold red]")


def comando_asistente_cerebros() -> None:
    """Asistente interactivo `/cerebros` conectado a `listar_modelos_disponibles()`."""
    console.print("\n[bold yellow]Consultando modelos disponibles por proveedor...[/bold yellow]")
    catalogo = listar_modelos_disponibles()

    t_cat = Table(title="Catálogo de Modelos Disponibles (En Vivo)", border_style="yellow")
    t_cat.add_column("Proveedor", style="cyan", no_wrap=True)
    t_cat.add_column("Total", justify="right", style="dim")
    t_cat.add_column("Modelos Principales", style="white")
    for prov, mods in catalogo.items():
        preview = ", ".join(mods[:5]) + (f" (+{len(mods) - 5} más)" if len(mods) > 5 else "")
        t_cat.add_row(prov, str(len(mods)), preview)
    console.print(t_cat)

    mostrar_tabla_cerebros()

    while True:
        rol = Prompt.ask(
            "Elige un agente a modificar (o Enter / 'fin' para salir)",
            choices=[*AGENT_ROLES, "fin", ""],
            default="",
            show_choices=False,
        ).strip().lower()
        if not rol or rol == "fin":
            break

        prov_input = Prompt.ask(
            f"Proveedor para [bold cyan]{rol}[/bold cyan] ({'/'.join(PROVIDERS)})",
            default="NVIDIA",
        ).strip()
        prov_match = next((p for p in catalogo.keys() if p.lower() == prov_input.lower()), prov_input)
        mods_disp = catalogo.get(prov_match, [])

        if mods_disp:
            console.print(f"[dim]Modelos en {prov_match}:[/dim]")
            for idx, m in enumerate(mods_disp[:12], 1):
                console.print(f"  [cyan]{idx:2d}.[/cyan] {m}")
            seleccion = Prompt.ask(
                f"Ingresa el número (1-{min(12, len(mods_disp))}) o nombre exacto del modelo",
                default="1",
            ).strip()
            if seleccion.isdigit() and 1 <= int(seleccion) <= len(mods_disp):
                modelo_elegido = mods_disp[int(seleccion) - 1]
            else:
                modelo_elegido = seleccion
        else:
            modelo_elegido = Prompt.ask(f"Nombre exacto del modelo para {prov_match}").strip()

        try:
            prov_ok, mod_ok = set_agent_brain(rol, prov_match, modelo_elegido)
            console.print(
                f"[bold green]✓ {rol}[/bold green] → [magenta]{prov_ok}[/magenta] / [bold white]{mod_ok}[/bold white]"
            )
        except ValueError as err:
            console.print(f"[bold red]✗ {err}[/bold red]")

    mostrar_tabla_cerebros()


# ---------------------------------------------------------------------------
# Ejecución Real sobre Grafo, PostgreSQL y Human-in-the-Loop (HITL)
# ---------------------------------------------------------------------------

def _mostrar_respuesta_orquestacion(res: Dict[str, Any], prev_msg_count: int) -> None:
    mensajes = res.get("messages", [])
    nuevos = mensajes[prev_msg_count:] if prev_msg_count < len(mensajes) else mensajes[-2:]

    for m in nuevos:
        rol_tipo = getattr(m, "type", "ai")
        if rol_tipo == "human":
            continue
        contenido = extraer_texto_mensaje(m.content if hasattr(m, "content") else m)
        console.print(Panel(contenido, title=f"Respuesta ({res.get('next_agent') or 'Orquestador'})", border_style="green"))

    if res.get("strategic_report"):
        rep = res["strategic_report"]
        t_rep = Table(title="Reporte Estratégico (9 Secciones Obligatorias)", border_style="blue")
        t_rep.add_column("Sección", style="cyan", no_wrap=True)
        t_rep.add_column("Contenido", style="white")
        for k, v in rep.items():
            t_rep.add_row(k.replace("_", " ").title(), str(v))
        console.print(t_rep)

    if res.get("promo_assets"):
        pa = res["promo_assets"]
        console.print(
            Panel(
                f"[bold]Producto:[/bold] {pa.get('producto_promocionado', 'N/A')} (SKU: {pa.get('sku', 'N/A')})\n"
                f"[bold]Copy:[/bold] {pa.get('copy_text')}\n"
                f"[bold]CTA:[/bold] {pa.get('cta')}\n"
                f"[bold]Video 9:16:[/bold] {json.dumps(pa.get('video_prompt'), indent=2, ensure_ascii=False)}",
                title="Activos Promocionales (Publicista)",
                border_style="magenta",
            )
        )


def manejar_hitl(pending_approval: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    """Muestra el ApprovalPayload real en terminal y confirma [s/n/e] antes del COMMIT en PostgreSQL."""
    cuerpo_hitl = (
        f"[bold]Acción:[/bold] {pending_approval.get('action_type')}\n"
        f"[bold]Descripción:[/bold] {pending_approval.get('description')}\n"
        f"[bold]Motivo:[/bold] {pending_approval.get('reason')}\n"
        f"[bold]Datos propuestos para PostgreSQL:[/bold]\n"
        f"{json.dumps(pending_approval.get('proposed_data'), indent=2, ensure_ascii=False)}"
    )
    console.print(Panel(cuerpo_hitl, title="[bold red]PAUSA HUMAN-IN-THE-LOOP (approval_gate)[/bold red]", border_style="magenta"))

    decision = Prompt.ask(
        "Confirmación requerida: [s] Aprobar / [n] Rechazar / [e] Editar",
        choices=["s", "n", "e"],
        default="s",
    )

    prev_snap = get_graph_state(thread_id)
    prev_len = len((prev_snap.get("values") or {}).get("messages", []))

    if decision == "s":
        res_post = resume_orchestration(
            thread_id=thread_id,
            approved=True,
            notes="Aprobado por operador en CLI.",
        )
        console.print("[bold green]✓ Acción APROBADA — resume_orchestration() ejecutado y COMMIT confirmado.[/bold green]")
    elif decision == "n":
        motivo = Prompt.ask("Indica el motivo del rechazo", default="Rechazado por operador")
        res_post = resume_orchestration(
            thread_id=thread_id,
            approved=False,
            notes=motivo,
        )
        console.print("[bold yellow]✗ Acción RECHAZADA — sin escritura en PostgreSQL.[/bold yellow]")
    else:
        edicion = Prompt.ask("Ingresa los datos o instrucción corregida")
        res_post = resume_orchestration(
            thread_id=thread_id,
            approved=True,
            correction=edicion,
            notes=edicion,
        )
        console.print("[bold green]✓ Acción APROBADA CON EDICIÓN — resume_orchestration() ejecutado.[/bold green]")

    _mostrar_respuesta_orquestacion(res_post, prev_len)
    return res_post


def ejecutar_turno(
    input_text: str,
    thread_id: str,
    event_source: str = "chat",
    vision_payload: Optional[Dict[str, Any]] = None,
    ui_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Ejecuta un turno real contra el grafo LangGraph y maneja pausas HITL en approval_gate."""
    prev_snap = get_graph_state(thread_id)
    prev_len = len((prev_snap.get("values") or {}).get("messages", []))

    console.print(f"\n[bold cyan]▶ Ejecutando grafo [event_source={event_source}]...[/bold cyan]")
    res = run_orchestration(
        input_text=input_text,
        thread_id=thread_id,
        event_source=event_source,
        vision_payload=vision_payload,
        ui_state=ui_state,
    )
    _mostrar_respuesta_orquestacion(res, prev_len)

    # Verificar si el grafo quedó pausado en approval_gate (HITL real)
    snap = get_graph_state(thread_id)
    pending = (snap.get("values") or {}).get("pending_approval") or res.get("pending_approval")
    pausado_en_gate = "approval_gate" in (snap.get("next") or [])

    if pausado_en_gate or (pending and pending.get("requires_human") and pending.get("status") == "pending"):
        res = manejar_hitl(pending, thread_id)

    return res


# ---------------------------------------------------------------------------
# Comandos Especializados Reales (/imagen, /pago, /cron, /estado)
# ---------------------------------------------------------------------------

def comando_imagen(args: List[str], thread_id: str) -> None:
    """Procesa `/imagen <ruta_archivo.jpg|png> <catalog|pos|ticket>` leyendo un archivo real del disco."""
    if len(args) < 2:
        console.print(
            "[yellow]Uso:[/yellow] /imagen <ruta_archivo.jpg|png> <catalog|pos|ticket>\n"
            "[dim]Ejemplo: /imagen ./fotos/ticket_compra.jpg ticket[/dim]"
        )
        return

    ruta_str, modo_raw = args[0], args[1].strip().lower()
    if modo_raw not in _IMAGE_MODE_ENDPOINTS:
        console.print(f"[bold red]✗ Modo inválido '{modo_raw}'. Usa uno de: catalog, pos, ticket.[/bold red]")
        return

    ruta = Path(ruta_str).expanduser().resolve()
    if not ruta.is_file():
        console.print(f"[bold red]✗ Archivo no encontrado en disco:[/bold red] {ruta}")
        return
    if ruta.suffix.lower() not in _ALLOWED_IMAGE_EXTS:
        console.print(f"[bold red]✗ Extensión no soportada '{ruta.suffix}'. Usa .jpg, .jpeg, .png o .webp.[/bold red]")
        return

    try:
        raw_bytes = ruta.read_bytes()
        image_b64 = base64.b64encode(raw_bytes).decode("ascii")
        mime_type = mimetypes.guess_type(str(ruta))[0] or "image/jpeg"
    except Exception as exc:
        console.print(f"[bold red]✗ No se pudo leer la imagen:[/bold red] {exc}")
        return

    console.print(
        f"[green]✓ Imagen real cargada:[/green] {ruta.name} ({len(raw_bytes):,} bytes, {mime_type}) → modo=[cyan]{modo_raw}[/cyan]"
    )

    prompts_por_modo = {
        "catalog": f"Analiza esta fotografía real de anaquel/catálogo ({ruta.name}) con NIM Vision y contrasta con el inventario en PostgreSQL.",
        "pos": f"Identifica los artículos reales en mostrador POS en esta foto ({ruta.name}) con NIM Vision y cotízalos contra PostgreSQL.",
        "ticket": f"Ejecuta OCR real sobre este comprobante/ticket ({ruta.name}) con NIM Vision y clasifica contablemente el gasto.",
    }
    vision_payload = {
        "mode": modo_raw,
        "endpoint": _IMAGE_MODE_ENDPOINTS[modo_raw],
        "file_path": str(ruta),
        "mime_type": mime_type,
        "image_b64": image_b64,
    }
    ejecutar_turno(
        input_text=prompts_por_modo[modo_raw],
        thread_id=thread_id,
        event_source="vision_api",
        vision_payload=vision_payload,
    )


def comando_pago(args: List[str], thread_id: str) -> None:
    """Procesa `/pago <metodo:codi|spei|dimo> <pantalla> <paso> [error_code]` enviando ui_state real al Tutor UI."""
    metodos_validos = {"codi", "spei", "dimo", "tarjeta"}
    if len(args) < 3:
        console.print(
            "[yellow]Uso:[/yellow] /pago <metodo:codi|spei|dimo> <pantalla> <paso> [error_code]\n"
            "[dim]Ejemplos:[/dim]\n"
            "[dim]  /pago codi cobro_qr 2 LIMITE_8000[/dim]\n"
            "[dim]  /pago spei comprobante 5 CEP_NO_ENCONTRADO[/dim]\n"
            "[dim]  /pago dimo transferir 3 CELULAR_NO_VINCULADO[/dim]"
        )
        return

    metodo = args[0].strip().lower()
    if metodo not in metodos_validos:
        console.print(f"[bold red]✗ Método inválido '{metodo}'. Usa: codi, spei o dimo.[/bold red]")
        return

    pantalla = args[1].strip()
    try:
        paso = int(args[2])
    except ValueError:
        console.print(f"[bold red]✗ El paso debe ser un número entero (recibido: '{args[2]}').[/bold red]")
        return

    error_code = " ".join(args[3:]) if len(args) >= 4 else None
    ui_state = {
        "payment_method": metodo,
        "screen": pantalla,
        "step": paso,
        "error_code": error_code,
    }
    texto = (
        f"Asistencia de pago digital {metodo.upper()} en pantalla '{pantalla}' (paso {paso})"
        + (f" con error '{error_code}'." if error_code else ".")
    )
    ejecutar_turno(
        input_text=texto,
        thread_id=thread_id,
        event_source="ui_copilot",
        ui_state=ui_state,
    )


def comando_rag(args: List[str]) -> None:
    """Procesa `/rag <consulta>` mostrando documentos de CoDi, SPEI o DiMo y su puntuación de relevancia."""
    if not args:
        console.print(
            "[yellow]Uso:[/yellow] /rag <consulta>\n"
            "[dim]Ejemplos:[/dim]\n"
            "[dim]  /rag limite monto maximo sin comision CoDi[/dim]\n"
            "[dim]  /rag cuando se rechaza una transferencia SPEI[/dim]\n"
            "[dim]  /rag como enviar dinero con numero celular DiMo[/dim]"
        )
        return

    # Permitir filtro opcional si el primer token es codi/spei/dimo seguido de ':' (ej. /rag codi: limite)
    metodo_filtro: Optional[str] = None
    consulta_tokens = list(args)
    if consulta_tokens[0].lower() in ("codi:", "spei:", "dimo:") and len(consulta_tokens) > 1:
        metodo_filtro = consulta_tokens[0].rstrip(":").lower()
        consulta_tokens = consulta_tokens[1:]
    consulta = " ".join(consulta_tokens)

    console.print(f"\n[bold cyan]Consultando índice RAG de pagos digitales (CoDi / SPEI / DiMo)...[/bold cyan]")
    res = buscar_rag_pagos(consulta=consulta, top_k=5, metodo_pago=metodo_filtro)

    pg_info = res.get("pgvector", {})
    pg_badge = (
        f"[green]pgvector sincronizado ({pg_info.get('fragmentos', 0)} fragmentos)[/green]"
        if pg_info.get("synced")
        else f"[yellow]pgvector no disponible ({pg_info.get('error', 'offline')})[/yellow]"
    )
    console.print(
        f"[dim]Motor: {res['motor_usado']} | FAISS: {res['faiss_dir']} | {pg_badge}[/dim]"
    )

    tabla = Table(title=f"Resultados RAG Pagos Digitales — '{consulta}'", border_style="blue")
    tabla.add_column("#", justify="right", style="dim", no_wrap=True)
    tabla.add_column("Método", style="bold magenta", no_wrap=True)
    tabla.add_column("Documento / Sección", style="cyan")
    tabla.add_column("Score", justify="right", style="bold green", no_wrap=True)
    tabla.add_column("Extracto", style="white")

    for idx, item in enumerate(res.get("resultados", []), 1):
        doc_sec = f"{item.get('doc', '')}\n[dim]{item.get('seccion') or item.get('pantalla') or '-'}[/dim]"
        extracto = item.get("texto", "").replace("\n", " ")[:220] + "..."
        tabla.add_row(
            str(idx),
            str(item.get("metodo_pago", "general")).upper(),
            doc_sec,
            f"{item.get('score', 0.0):.4f}",
            extracto,
        )
    console.print(tabla)


def comando_cron(thread_id: str) -> None:
    """Ejecuta el barrido real de lotes próximos a caducar y stock crítico en PostgreSQL."""
    ejecutar_turno(
        input_text=(
            "Ejecuta el barrido programado real sobre PostgreSQL: revisa lotes próximos a caducar "
            "(v_por_caducar) y alertas de stock crítico (v_stock_bajo). Si detectas alertas reales, "
            "encadena al publicista para proponer campaña de rescate."
        ),
        thread_id=thread_id,
        event_source="cron",
    )


def comando_estado(thread_id: str) -> None:
    """Inspecciona el OrchestratorState real y las estadísticas vivas de PostgreSQL."""
    snap = get_graph_state(thread_id)
    vals = snap.get("values") or {}
    next_nodes = snap.get("next") or []

    t_state = Table(title=f"OrchestratorState Real (thread={thread_id[:8]}...)", border_style="cyan")
    t_state.add_column("Campo", style="bold cyan", no_wrap=True)
    t_state.add_column("Valor Actual", style="white")

    t_state.add_row("event_source", str(vals.get("event_source", "N/A")))
    t_state.add_row("next_agent", str(vals.get("next_agent", "N/A")))
    t_state.add_row("next_nodes (checkpointer)", ", ".join(next_nodes) if next_nodes else "Ninguno (libre)")
    t_state.add_row("iteration_count", str(vals.get("iteration_count", 0)))
    t_state.add_row("total_messages", str(len(vals.get("messages", []))))

    db_ev = vals.get("db_evidence")
    t_state.add_row("db_evidence", (str(db_ev)[:300] + ("..." if db_ev and len(str(db_ev)) > 300 else "")) if db_ev else "Sin evidencia aún")

    rep = vals.get("strategic_report")
    t_state.add_row(
        "strategic_report",
        f"Generado ({len(rep)} secciones): {str(rep.get('identificacion_sector', ''))[:120]}" if isinstance(rep, dict) else "Ninguno",
    )

    pa = vals.get("promo_assets")
    t_state.add_row(
        "promo_assets",
        f"Producto={pa.get('producto_promocionado')} | CTA={pa.get('cta')}" if isinstance(pa, dict) else "Ninguno",
    )

    pend = vals.get("pending_approval")
    t_state.add_row(
        "pending_approval",
        f"{pend.get('action_type')} ({pend.get('status')})" if isinstance(pend, dict) else "Ninguna",
    )
    console.print(t_state)

    db_info = verify_db_connection()
    if db_info.get("connected"):
        console.print(
            f"[dim]PostgreSQL en vivo ({db_info['database']}): "
            f"{db_info['productos_activos']} productos | {db_info['lotes_por_caducar']} por caducar | "
            f"{db_info['alertas_stock_bajo']} stock bajo | {db_info['ventas_registradas']} ventas "
            f"(${db_info['ingresos_acumulados']:,.2f} MXN)[/dim]"
        )


# ---------------------------------------------------------------------------
# Bucle Principal del CLI Interactivo
# ---------------------------------------------------------------------------

def main() -> None:
    session_thread_id = str(uuid.uuid4())
    mostrar_panel_inicio()

    try:
        while True:
            try:
                linea = Prompt.ask("\n[bold cyan]Tiendita-IA[/bold cyan]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Interrupción detectada. Cerrando sesión...[/yellow]")
                break

            if not linea:
                continue

            # Parseo seguro respetando rutas con espacios entre comillas
            try:
                tokens = shlex.split(linea)
            except ValueError:
                tokens = linea.split()

            cmd = tokens[0].lower()
            args = tokens[1:]

            if cmd in ("/salir", "/exit", "exit", "quit"):
                console.print("[green]Cerrando conexiones y saliendo de Tiendita IA...[/green]")
                break
            elif cmd in ("/ayuda", "/help"):
                mostrar_ayuda()
            elif cmd == "/cerebro":
                comando_cerebro_directo(args)
            elif cmd == "/cerebros":
                comando_asistente_cerebros()
            elif cmd == "/reset-cerebros":
                reset_brains_to_nvidia_default()
                console.print("[bold green]✓ Todos los agentes restaurados al perfil exclusivo 100% NVIDIA NIM.[/bold green]")
                mostrar_tabla_cerebros()
            elif cmd == "/imagen":
                comando_imagen(args, session_thread_id)
            elif cmd == "/pago":
                comando_pago(args, session_thread_id)
            elif cmd == "/rag":
                comando_rag(args)
            elif cmd == "/cron":
                comando_cron(session_thread_id)
            elif cmd == "/estado":
                comando_estado(session_thread_id)
            else:
                # Texto libre -> event_source="chat" contra PostgreSQL + Tavily/RAG reales
                ejecutar_turno(
                    input_text=linea,
                    thread_id=session_thread_id,
                    event_source="chat",
                )
    finally:
        cerradas = close_db_pool()
        console.print(f"[dim]Pool de PostgreSQL cerrado limpiamente ({cerradas} conexiones liberadas). ¡Hasta luego![/dim]")


if __name__ == "__main__":
    main()
