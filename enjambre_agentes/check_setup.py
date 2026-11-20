#!/usr/bin/env python3
"""
check_setup.py — Script de verificación rápida del entorno y dependencias.

Valida:
1. Versión de Python (>= 3.11)
2. Importación exitosa de todos los módulos core
3. Disponibilidad de al menos un proveedor LLM configurado
4. Estructura del grafo compilado
5. Exportación MCP de herramientas
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Colores ANSI para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check(condition: bool, message: str) -> bool:
    """Imprime resultado de un chequeo."""
    if condition:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        print(f"{RED}✗{RESET} {message}")
        return False


def main():
    print(f"\n{BOLD}═══ Verificación de Entorno: Enjambre Agentes ═══{RESET}\n")
    
    all_ok = True
    
    # 1. Versión de Python
    py_version = sys.version_info
    all_ok &= check(
        py_version >= (3, 11),
        f"Python >= 3.11 (detectado: {py_version.major}.{py_version.minor}.{py_version.micro})"
    )
    
    # 2. Importaciones core
    try:
        from state import OrchestratorState
        all_ok &= check(True, "Módulo 'state.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'state.py' falló: {e}")
    
    try:
        from models import get_llm, get_available_models
        all_ok &= check(True, "Módulo 'models.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'models.py' falló: {e}")
    
    try:
        from guards import enforce_db_grounding, validate_strategic_report
        all_ok &= check(True, "Módulo 'guards.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'guards.py' falló: {e}")
    
    try:
        from few_shot_retriever import FewShotRetriever
        all_ok &= check(True, "Módulo 'few_shot_retriever.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'few_shot_retriever.py' falló: {e}")
    
    try:
        from tools_bridge import to_mcp_tool_definitions
        all_ok &= check(True, "Módulo 'tools_bridge.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'tools_bridge.py' falló: {e}")
    
    try:
        from graph import build_orchestrator, orchestrator_graph
        all_ok &= check(True, "Módulo 'graph.py' importado correctamente")
    except Exception as e:
        all_ok &= check(False, f"Módulo 'graph.py' falló: {e}")
    
    # 3. Configuración de proveedores LLM
    print(f"\n{BOLD}── Proveedores LLM Configurados ──{RESET}")
    providers_ok = False
    
    if os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY"):
        check(True, "NVIDIA NIM configurado")
        providers_ok = True
    else:
        check(False, "NVIDIA NIM no configurado (NVIDIA_API_KEY)")
    
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        check(True, "Google Gemini configurado")
        providers_ok = True
    else:
        check(False, "Google Gemini no configurado (GEMINI_API_KEY)")
    
    if os.getenv("GROQ_API_KEY"):
        check(True, "Groq Cloud configurado")
        providers_ok = True
    else:
        check(False, "Groq Cloud no configurado (GROQ_API_KEY)")
    
    if os.getenv("COHERE_API_KEY") or os.getenv("CO_API_KEY"):
        check(True, "Cohere configurado")
        providers_ok = True
    else:
        check(False, "Cohere no configurado (COHERE_API_KEY)")
    
    # Ollama no requiere API key
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    check(True, f"Ollama Local disponible en: {ollama_host}")
    
    if not providers_ok:
        print(f"\n{YELLOW}⚠ Advertencia: No se detectó ningún proveedor LLM configurado.{RESET}")
        print(f"{YELLOW}  Configura al menos uno en el archivo .env (copia de .env.example){RESET}")
        all_ok = False
    
    # 4. Estructura del grafo
    print(f"\n{BOLD}── Estructura del Grafo ──{RESET}")
    try:
        from graph import orchestrator_graph
        nodes = list(orchestrator_graph.nodes.keys())
        expected_nodes = {
            "supervisor", "control", "vendedor", "analista", 
            "investigador", "publicista", "tutor_ui", "aprobacion_hitl"
        }
        all_ok &= check(
            expected_nodes.issubset(set(nodes)),
            f"Grafo compilado con 8 nodos: {', '.join(expected_nodes)}"
        )
    except Exception as e:
        all_ok &= check(False, f"Error al compilar grafo: {e}")
    
    # 5. Exportación MCP
    print(f"\n{BOLD}── Herramientas MCP ──{RESET}")
    try:
        from tools_bridge import to_mcp_tool_definitions
        mcp_tools = to_mcp_tool_definitions()
        all_ok &= check(
            len(mcp_tools) >= 17,
            f"Exportadas {len(mcp_tools)} herramientas en formato MCP JSON Schema"
        )
    except Exception as e:
        all_ok &= check(False, f"Error en exportación MCP: {e}")
    
    # Resumen final
    print(f"\n{BOLD}═══════════════════════════════════════════════════{RESET}")
    if all_ok:
        print(f"{GREEN}{BOLD}✓ Todos los chequeos pasaron. El entorno está listo.{RESET}\n")
        print(f"Siguiente paso: Ejecutar la API o CLI:")
        print(f"  • CLI:  {BOLD}uv run python cli_tester.py{RESET}")
        print(f"  • API:  {BOLD}uv run uvicorn api:app --reload{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}✗ Algunos chequeos fallaron. Revisa los errores arriba.{RESET}\n")
        print(f"Consulta el README.md para instrucciones de instalación.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
