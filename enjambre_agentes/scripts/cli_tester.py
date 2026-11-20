#!/usr/bin/env python3
"""
CLI Interactivo de Tiendita IA.
Comandos interactivos:
  /modelo      -> Selector dinámico de modelos conectados a listar_modelos_disponibles()
  /test        -> Selector interactivo del banco de pruebas tests/test_cases.json
  /pos         -> Simulación de mostrador de caja con visión
  /ticket      -> Simulación de auditoría de comprobante con clasificación contable
  /pago        -> Prueba de asistencia del Tutor UI en pantalla (máximo 2 oraciones)
  /cron        -> Detonador de revisión de caducidades y video promocional 9:16
  /investigar  -> Generación de reporte estratégico comercial de 9 secciones
  /reportes    -> Listado de reportes históricos indexados en disco/RAG
  /estado      -> Visualización del estado del inventario y ventas
  /salir       -> Finalizar sesión
Soporta confirmación Human-in-the-Loop [s/n/e] (Sí / No / Editar).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

# Asegurar path del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.models import listar_modelos_disponibles, cargar_config_agentes
from agents.graph import run_orchestration, resume_orchestration
from tools.db_client import _MOCK_INVENTORY, _MOCK_SALES

console = Console()
TEST_CASES_PATH = Path(__file__).resolve().parent.parent / "tests" / "test_cases.json"
REPORTES_DIR = Path(__file__).resolve().parent.parent / "data" / "reportes"


def mostrar_banner():
    console.print(
        Panel.fit(
            "[bold cyan]TIENDITA IA: Ecosistema Comercial Multimodal[/bold cyan]\n"
            "[green]NVIDIA NIM / NeMo + LangGraph + PostgreSQL Vectorial + Dual RAG[/green]\n"
            "[dim]Comandos: /modelo, /test, /pos, /ticket, /pago, /cron, /investigar, /reportes, /estado, /salir[/dim]",
            border_style="cyan"
        )
    )


def comando_seleccionar_modelo():
    console.print("\n[bold yellow]Consultando modelos disponibles en vivo...[/bold yellow]")
    modelos = listar_modelos_disponibles()

    tabla = Table(title="Modelos Disponibles por Proveedor", border_style="yellow")
    tabla.add_column("Proveedor", style="cyan", no_wrap=True)
    tabla.add_column("Modelos Activos", style="white")

    for prov, mods in modelos.items():
        tabla.add_row(prov, ", ".join(mods[:4]) + ("..." if len(mods) > 4 else ""))
    console.print(tabla)

    opcion = Prompt.ask("¿Deseas consultar la configuración actual de agentes?", choices=["s", "n"], default="n")
    if opcion == "s":
        cfg = cargar_config_agentes().get("modelos", {})
        t_agentes = Table(title="Asignación Actual de Modelos por Agente", border_style="green")
        t_agentes.add_column("Agente", style="cyan")
        t_agentes.add_column("Proveedor", style="magenta")
        t_agentes.add_column("Modelo Configurado", style="white")
        for ag, datos in cfg.items():
            t_agentes.add_row(ag, datos.get("proveedor", "NVIDIA"), datos.get("modelo", "Default"))
        console.print(t_agentes)


def manejar_hitl(pending_approval: dict, thread_id: str):
    """Manejo interactivo de confirmación humana [s/n/e] ante acciones sensibles."""
    console.print("\n[bold magenta]====================================================[/bold magenta]")
    console.print("[bold red][!_!] ALERTA HUMAN-IN-THE-LOOP (HITL) REQUERIDA[/bold red]")
    console.print(f"[bold]Acción:[/bold] {pending_approval.get('action_type')}")
    console.print(f"[bold]Descripción:[/bold] {pending_approval.get('description')}")
    console.print(f"[bold]Motivo:[/bold] {pending_approval.get('reason')}")
    console.print(f"[dim]Datos propuestos: {json.dumps(pending_approval.get('proposed_data'), ensure_ascii=False)}[/dim]")
    console.print("[bold magenta]====================================================[/bold magenta]")

    decision = Prompt.ask(
        "¿Deseas autorizar esta acción? [s = Aprobar / n = Rechazar / e = Editar]",
        choices=["s", "n", "e"],
        default="s"
    )

    if decision == "s":
        resume_orchestration(thread_id=thread_id, approved=True, notes="Aprobado por operador en CLI.")
        console.print("[bold green](^_^)/ Acción APROBADA exitosamente y registrada para NeMo Customizer.[/bold green]")
    elif decision == "n":
        motivo = Prompt.ask("Indica el motivo del rechazo")
        resume_orchestration(thread_id=thread_id, approved=False, notes=motivo)
        console.print("[bold yellow](¬_¬) Acción RECHAZADA por el operador.[/bold yellow]")
    else:
        edicion = Prompt.ask("Ingresa los datos o instrucción corregida")
        resume_orchestration(thread_id=thread_id, approved=True, correction=edicion, notes="Aprobado con edición.")
        console.print("[bold green](^_^)/ Acción APROBADA con correcciones.[/bold green]")


def ejecutar_caso(input_text: str, event_source: str = "chat", vision_payload: dict = None, ui_state: dict = None):
    thread_id = str(uuid.uuid4())
    console.print(f"\n[bold cyan](・_・)? Ejecutando orquestación [Evento: {event_source}]...[/bold cyan]")

    res = run_orchestration(
        input_text=input_text,
        thread_id=thread_id,
        event_source=event_source,
        vision_payload=vision_payload,
        ui_state=ui_state
    )

    mensajes = res.get("messages", [])
    for m in mensajes:
        contenido = m.content if hasattr(m, "content") else str(m)
        console.print(Panel(contenido, title=f"Respuesta ({res.get('next_agent', 'Orquestador')})", border_style="green"))

    # Mostrar reporte estratégico si se generó
    if res.get("strategic_report"):
        rep = res["strategic_report"]
        t_rep = Table(title="Reporte Estratégico (9 Secciones Obligatorias)", border_style="blue")
        t_rep.add_column("Sección", style="cyan", no_wrap=True)
        t_rep.add_column("Contenido", style="white")
        for k, v in rep.items():
            t_rep.add_row(k.replace("_", " ").title(), str(v))
        console.print(t_rep)

    # Mostrar activos promocionales si se generaron
    if res.get("promo_assets"):
        pa = res["promo_assets"]
        console.print(Panel(
            f"[bold]Copy:[/bold] {pa.get('copy_text')}\n[bold]CTA:[/bold] {pa.get('cta')}\n[bold]Video 9:16:[/bold] {json.dumps(pa.get('video_prompt'), indent=2, ensure_ascii=False)}",
            title="Activos Promocionales (Publicista)",
            border_style="magenta"
        ))

    pending = res.get("pending_approval")
    if pending and pending.get("requires_human") and pending.get("status") == "pending":
        manejar_hitl(pending, thread_id)


def comando_banco_pruebas():
    if not TEST_CASES_PATH.exists():
        console.print("[red]No se encontró tests/test_cases.json[/red]")
        return

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        casos = json.load(f)

    console.print(f"\n[bold green]Banco de Pruebas: {len(casos)} escenarios disponibles.[/bold green]")
    for i, c in enumerate(casos, 1):
        console.print(f"[cyan]{i}. [{c['id']}][/cyan] {c['nombre']} - [dim]{c['descripcion']}[/dim]")

    elegido = Prompt.ask("Selecciona el número de caso a ejecutar (o 'todos')", default="1")
    if elegido == "todos":
        for c in casos:
            console.print(f"\n[bold yellow]>>> Ejecutando {c['id']}: {c['nombre']}[/bold yellow]")
            ejecutar_caso(c["input_text"], c["event_source"], c.get("vision_payload"), c.get("ui_state"))
    else:
        try:
            idx = int(elegido) - 1
            c = casos[idx]
            ejecutar_caso(c["input_text"], c["event_source"], c.get("vision_payload"), c.get("ui_state"))
        except Exception as e:
            console.print(f"[red]Opción inválida: {e}[/red]")


def comando_listar_reportes():
    archivos = sorted(list(REPORTES_DIR.glob("*.json")), reverse=True)
    if not archivos:
        console.print("[yellow]Aún no se han guardado reportes estratégicos en data/reportes/.[/yellow]")
        return

    tabla = Table(title="Reportes Estratégicos Históricos Indexados", border_style="cyan")
    tabla.add_column("Archivo", style="white")
    tabla.add_column("Sector Identificado", style="green")

    for a in archivos[:10]:
        try:
            with open(a, "r", encoding="utf-8") as f:
                d = json.load(f)
                tabla.add_row(a.name, d.get("identificacion_sector", "N/A")[:70])
        except Exception:
            pass
    console.print(tabla)


def main():
    mostrar_banner()
    while True:
        try:
            linea = Prompt.ask("\n[bold cyan]Tiendita-IA>[/bold cyan]").strip()
            if not linea:
                continue
            if linea in ("/salir", "exit", "quit"):
                console.print("[green]Sesión finalizada. ¡Hasta luego![/green]")
                break
            elif linea == "/modelo":
                comando_seleccionar_modelo()
            elif linea == "/test":
                comando_banco_pruebas()
            elif linea == "/pos":
                ejecutar_caso(
                    input_text="Cobro de 2 leches Lala y 1 pan Bimbo en mostrador con tarjeta.",
                    event_source="pos-checkout",
                    vision_payload={"endpoint": "/pos-checkout", "image_b64": "MOCK_B64"}
                )
            elif linea == "/ticket":
                ejecutar_caso(
                    input_text="Comprobante de compra por $1,450 en abarrotes para reventa.",
                    event_source="receipt-ocr",
                    vision_payload={"endpoint": "/receipt-ocr", "image_b64": "MOCK_B64"}
                )
            elif linea == "/pago":
                ejecutar_caso(
                    input_text="Error al insertar la tarjeta en la terminal.",
                    event_source="chat",
                    ui_state={"screen": "ingreso_nip", "step": 2, "payment_method": "tarjeta", "error_code": "CHIP_DEFECTUOSO"}
                )
            elif linea == "/cron":
                ejecutar_caso(
                    input_text="Vigilar caducidades del día y generar activos de video 9:16 si hay riesgo.",
                    event_source="cron"
                )
            elif linea == "/investigar":
                tema = Prompt.ask("Ingresa el tema o giro comercial para el estudio estratégico", default="Expansión de catálogo en abarrotes de barrio")
                ejecutar_caso(input_text=tema, event_source="chat")
            elif linea == "/reportes":
                comando_listar_reportes()
            elif linea == "/estado":
                console.print(f"[bold]Productos en Inventario:[/bold] {len(_MOCK_INVENTORY)}")
                console.print(f"[bold]Ventas Registradas:[/bold] {len(_MOCK_SALES)}")
            else:
                ejecutar_caso(input_text=linea, event_source="chat")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[green]Salida forzada por usuario.[/green]")
            break


if __name__ == "__main__":
    main()
