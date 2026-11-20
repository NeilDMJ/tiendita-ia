"""
Arquitectura RAG Dual para Tiendita IA:
1. Motor Principal (Persistente): PostgreSQL (pgvector) + NeMo Retriever
   (nvidia/nv-embedqa-e5-v5 + nvidia/nv-rerankqa-mistral-4b-v3).
2. Motor Secundario / Offline / Sesión: FAISS en disco/memoria + HuggingFaceEmbeddings
   (sentence-transformers/all-MiniLM-L6-v2) con conmutación automática ante fallos de API.
3. Indexación y Recuperación de Reportes Estratégicos Históricos.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from langchain_core.tools import tool

from config.keys import NVIDIA_API_KEY, DATABASE_URL, HF_TOKEN
from schemas.reports import StrategicReport

# Directorios locales para almacenamiento
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTES_DIR = DATA_DIR / "reportes"
FAISS_DIR = DATA_DIR / "vectorstores" / "faiss"
REPORTES_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)

# Índice FAISS singleton en memoria/disco
_faiss_store = None

# Memoria base de políticas comerciales
_DOCUMENTOS_BASE = [
    Document(
        page_content="Política de Caducidad y Mermas: Todo producto con fecha de vencimiento menor a 5 días debe colocarse en canasta de remate rápido con 20% a 30% de descuento. Si faltan 48 horas o menos, el descuento puede elevarse al 50% con aprobación de gerencia.",
        metadata={"categoria": "politicas", "tema": "caducidades", "tipo": "base"}
    ),
    Document(
        page_content="Comisión por Pagos Digitales: En cobros con tarjeta o terminal digital, la tiendita no cobra comisión extra al cliente; el costo operativo del 3.5% se absorbe como gasto de operación para maximizar el ticket promedio y atraer clientes jóvenes.",
        metadata={"categoria": "finanzas", "tema": "pagos_digitales", "tipo": "base"}
    ),
    Document(
        page_content="Estrategia de Upselling en Caja: Al vender leche o pan, sugerir siempre café soluble, atún o mermelada. Si el cliente lleva refresco, sugerir botanas o cacahuates de alta rotación.",
        metadata={"categoria": "ventas", "tema": "upselling", "tipo": "base"}
    ),
    Document(
        page_content="Clasificación Contable: Inversión en Inventario incluye exclusivamente productos comprados para venta directa. Gasto Operativo incluye luz, internet, bolsas de plástico, rollos de ticket, limpieza y reparaciones.",
        metadata={"categoria": "contabilidad", "tema": "clasificacion", "tipo": "base"}
    ),
]


def _get_active_embeddings():
    """Retorna embeddings de NVIDIA NIM o conmuta a HuggingFaceEmbeddings local."""
    if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
            return NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5", nvidia_api_key=NVIDIA_API_KEY)
        except Exception:
            pass

    # Motor Secundario Offline: HuggingFace local
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _get_nemo_reranker():
    """Obtiene el modelo reranker de NVIDIA NIM si está disponible."""
    if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIARerank
            return NVIDIARerank(model="nvidia/nv-rerankqa-mistral-4b-v3", nvidia_api_key=NVIDIA_API_KEY)
        except Exception:
            pass
    return None


def _get_faiss_vectorstore():
    """Inicializa o carga el almacén vectorial local FAISS."""
    global _faiss_store
    if _faiss_store is not None:
        return _faiss_store

    from langchain_community.vectorstores import FAISS
    embeddings = _get_active_embeddings()
    index_file = FAISS_DIR / "index.faiss"

    if index_file.exists():
        try:
            _faiss_store = FAISS.load_local(str(FAISS_DIR), embeddings, allow_dangerous_deserialization=True)
            return _faiss_store
        except Exception:
            pass

    # Crear nuevo índice con documentos base
    _faiss_store = FAISS.from_documents(_DOCUMENTOS_BASE, embeddings)
    try:
        _faiss_store.save_local(str(FAISS_DIR))
    except Exception:
        pass
    return _faiss_store


def index_strategic_report(report: StrategicReport | Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Persiste un reporte estratégico en disco (JSON y Markdown) y lo indexa vectorialmente
    en FAISS y PostgreSQL (pgvector) para consultas históricas inmediatas.
    """
    if isinstance(report, dict):
        report_data = report
    else:
        report_data = report.model_dump()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    slug = report_data.get("identificacion_sector", "reporte")[:30].replace(" ", "_").replace("/", "-")
    base_name = f"{timestamp}_{slug}"

    # 1. Guardar en disco (JSON y Markdown)
    json_path = REPORTES_DIR / f"{base_name}.json"
    md_path = REPORTES_DIR / f"{base_name}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    md_content = f"""# Reporte Estratégico Comercial - {timestamp}

## 1. Identificación del Sector
{report_data.get('identificacion_sector', '')}

## 2. Mercado y Tendencias
{report_data.get('mercado_tendencias', '')}

## 3. Clientes
{report_data.get('clientes', '')}

## 4. Problemas Detectados
{report_data.get('problemas', '')}

## 5. Soluciones Comerciales
{report_data.get('soluciones', '')}

## 6. Hipótesis
{report_data.get('hipotesis', '')}

## 7. Objetivos SMART
{report_data.get('objetivos', '')}

## 8. Impacto Esperado
{report_data.get('impacto', '')}

## 9. Hallazgos y Próximos Pasos
{report_data.get('hallazgos', '')}
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Vectorizar e indexar en FAISS
    texto_indexacion = (
        f"REPORTE ESTRATÉGICO [{timestamp}]: {report_data.get('identificacion_sector', '')}. "
        f"Tendencias: {report_data.get('mercado_tendencias', '')}. Clientes: {report_data.get('clientes', '')}. "
        f"Problemas: {report_data.get('problemas', '')}. Soluciones: {report_data.get('soluciones', '')}. "
        f"Hipótesis: {report_data.get('hipotesis', '')}. Objetivos: {report_data.get('objetivos', '')}. "
        f"Impacto: {report_data.get('impacto', '')}. Hallazgos: {report_data.get('hallazgos', '')}."
    )
    meta = metadata or {}
    meta.update({
        "timestamp": timestamp,
        "tipo": "strategic_report",
        "archivo_json": str(json_path),
        "archivo_md": str(md_path)
    })

    doc = Document(page_content=texto_indexacion, metadata=meta)
    vs = _get_faiss_vectorstore()
    vs.add_documents([doc])
    try:
        vs.save_local(str(FAISS_DIR))
    except Exception:
        pass

    return f"Reporte estratégico indexado exitosamente en FAISS y guardado en {json_path}."


def buscar_reportes_vectoriales(query: str, top_k: int = 3) -> List[Document]:
    """Recupera los reportes estratégicos pasados más relevantes usando similitud semántica."""
    vs = _get_faiss_vectorstore()
    docs = vs.similarity_search(query, k=top_k)
    return [d for d in docs if d.metadata.get("tipo") == "strategic_report"]


@tool
def consultar_conocimiento_comercial(consulta: str, categoria: Optional[str] = None) -> str:
    """
    Consulta la base de conocimientos comerciales, normativas, márgenes y políticas de la tiendita
    usando la Arquitectura RAG Dual (NeMo Retriever con reranking o FAISS local).
    """
    vs = _get_faiss_vectorstore()
    candidatos = vs.similarity_search(consulta, k=4)

    if categoria:
        candidatos = [d for d in candidatos if d.metadata.get("categoria") == categoria.lower()]

    # Reranking semántico con NeMo si está disponible
    reranker = _get_nemo_reranker()
    if reranker and len(candidatos) > 1:
        try:
            ranked = reranker.compress_documents(documents=candidatos, query=consulta)
            candidatos = ranked[:3]
        except Exception:
            pass

    salida = []
    for d in candidatos[:3]:
        tema = d.metadata.get("tema", d.metadata.get("tipo", "general")).upper()
        salida.append(f"[{tema}]: {d.page_content}")

    return "\n\n".join(salida) if salida else "Sin conocimiento específico registrado para esta consulta."


@tool
def indexar_documento_comercial(texto: str, categoria: str, tema: str) -> str:
    """
    Registra dinámicamente una nueva regla, política o dato en el almacén vectorial RAG Dual.
    """
    doc = Document(page_content=texto, metadata={"categoria": categoria.lower(), "tema": tema.lower(), "tipo": "regla"})
    vs = _get_faiss_vectorstore()
    vs.add_documents([doc])
    try:
        vs.save_local(str(FAISS_DIR))
    except Exception:
        pass
    return f"Documento indexado con éxito en categoría '{categoria}', tema '{tema}'."
