#!/usr/bin/env python3
"""
Genera la representación gráfica en formato Mermaid del Grafo LangGraph de Tiendita IA.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.graph import tiendita_graph


def generar():
    salida_md = Path(__file__).resolve().parent.parent / "ARCHITECTURE_GRAPH.md"
    mermaid_code = tiendita_graph.get_graph().draw_mermaid()
    
    contenido = f"""# Arquitectura del Grafo LangGraph - Tiendita IA

```mermaid
{mermaid_code}
```
"""
    with open(salida_md, "w", encoding="utf-8") as f:
        f.write(contenido)
        
    print(f"Diagrama Mermaid generado exitosamente en: {salida_md}")


if __name__ == "__main__":
    generar()
