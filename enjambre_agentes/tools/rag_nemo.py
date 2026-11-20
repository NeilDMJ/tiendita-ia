"""
Arquitectura RAG Dual Especializada en Pagos Digitales de México (CoDi, SPEI, DiMo)
y Conocimiento Comercial para Tiendita IA.

Fuentes indexadas:
  - `data/Embeddings/datos/conocimiento.jsonl` (934 fragmentos oficiales Banxico: CoDi, SPEI, DiMo, CEP)
  - `data/Embeddings/datos/embeddings.npz` (vectores precalculados 4096-dim `nvidia/nemotron-3.5-embed-8b`)
  - `data/Embeddings/datos/guias.json` (flujos paso a paso por pantalla y advertencias de seguridad)
  - Políticas base de la tiendita y reportes estratégicos históricos (`data/reportes/`)

Motores de almacenamiento y búsqueda:
  1. `FAISS` persistente en `data/vectorstores/faiss/` (índice coseno activo + respaldo de vectores 4096-dim).
  2. `PostgreSQL (pgvector)` en tablas `documento` y `fragmento` (`vector(1024)`) sincronizado automáticamente.
  3. Reranking con `nvidia/nv-rerankqa-mistral-4b-v3` cuando `NVIDIA_API_KEY` esté activa y autorizada,
     con respaldo automático por similitud coseno en `FAISS` / `pgvector`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from langchain_core.documents import Document
from langchain_core.tools import tool

from config.keys import NVIDIA_API_KEY
from schemas.reports import StrategicReport

# ---------------------------------------------------------------------------
# Rutas locales y estado singleton
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMBEDDINGS_DATOS_DIR = DATA_DIR / "Embeddings" / "datos"
CONOCIMIENTO_JSONL_PATH = EMBEDDINGS_DATOS_DIR / "conocimiento.jsonl"
EMBEDDINGS_NPZ_PATH = EMBEDDINGS_DATOS_DIR / "embeddings.npz"
GUIAS_JSON_PATH = EMBEDDINGS_DATOS_DIR / "guias.json"

REPORTES_DIR = DATA_DIR / "reportes"
FAISS_DIR = DATA_DIR / "vectorstores" / "faiss"
FAISS_PRECOMPUTED_PATH = FAISS_DIR / "pagos_precomputed_4096.faiss"
FAISS_PRECOMPUTED_META_PATH = FAISS_DIR / "pagos_precomputed_meta.json"
FAISS_MANIFEST_PATH = FAISS_DIR / "manifest_pagos.json"

REPORTES_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)

_FAISS_INDEX_VERSION = "pagos_digitales_v2"
_PGVECTOR_DIM = 1024

_faiss_store = None
_embeddings_singleton = None
_guias_cache: Optional[Dict[str, Any]] = None
_reranker_unavailable = False
_pgvector_synced_session = False

# Políticas comerciales base de Tiendita IA
_DOCUMENTOS_BASE = [
    Document(
        page_content=(
            "Política de Caducidad y Mermas: Todo producto con fecha de vencimiento menor a 5 días "
            "debe colocarse en canasta de remate rápido con 20% a 30% de descuento. Si faltan 48 horas "
            "o menos, el descuento puede elevarse al 50% con aprobación de gerencia."
        ),
        metadata={
            "chunk_id": "base#caducidades",
            "doc": "politicas_tiendita",
            "titulo": "Política de Caducidad y Mermas",
            "seccion": "Caducidades",
            "categoria": "politicas",
            "tema": "caducidades",
            "fuente_tipo": "politica_base",
            "metodo_pago": "general",
            "metodos_pago": [],
            "pantalla": "",
            "codigos_error": [],
        },
    ),
    Document(
        page_content=(
            "Comisión por Pagos Digitales en Tiendita IA: En cobros con CoDi, DiMo o SPEI no hay "
            "comisión al cliente; en terminal con tarjeta, la tiendita absorbe el costo operativo del 3.5% "
            "como gasto de operación para maximizar el ticket promedio."
        ),
        metadata={
            "chunk_id": "base#pagos_digitales",
            "doc": "politicas_tiendita",
            "titulo": "Política de Pagos Digitales en Mostrador",
            "seccion": "Pagos Digitales",
            "categoria": "finanzas",
            "tema": "pagos_digitales",
            "fuente_tipo": "politica_base",
            "metodo_pago": "general",
            "metodos_pago": ["codi", "spei", "dimo"],
            "pantalla": "seleccion_pago",
            "codigos_error": [],
        },
    ),
    Document(
        page_content=(
            "Estrategia de Upselling en Caja: Al vender leche o pan, sugerir siempre café soluble, "
            "atún o mermelada. Si el cliente lleva refresco, sugerir botanas o cacahuates de alta rotación."
        ),
        metadata={
            "chunk_id": "base#upselling",
            "doc": "politicas_tiendita",
            "titulo": "Estrategia de Upselling en Caja",
            "seccion": "Ventas",
            "categoria": "ventas",
            "tema": "upselling",
            "fuente_tipo": "politica_base",
            "metodo_pago": "general",
            "metodos_pago": [],
            "pantalla": "",
            "codigos_error": [],
        },
    ),
    Document(
        page_content=(
            "Clasificación Contable: Inversión en Inventario incluye exclusivamente productos comprados "
            "para venta directa. Gasto Operativo incluye luz, internet, bolsas de plástico, rollos de ticket, "
            "limpieza y reparaciones."
        ),
        metadata={
            "chunk_id": "base#contabilidad",
            "doc": "politicas_tiendita",
            "titulo": "Clasificación Contable",
            "seccion": "Contabilidad",
            "categoria": "contabilidad",
            "tema": "clasificacion",
            "fuente_tipo": "politica_base",
            "metodo_pago": "general",
            "metodos_pago": [],
            "pantalla": "",
            "codigos_error": [],
        },
    ),
]


# ---------------------------------------------------------------------------
# Extracción de metadatos estructurados para CoDi / SPEI / DiMo
# ---------------------------------------------------------------------------

def _inferir_metodos_pago(texto: str, doc: str = "", seccion: str = "") -> Tuple[str, List[str]]:
    """Detecta los métodos de pago digital (codi, spei, dimo) cubiertos por un fragmento."""
    blob = f"{doc} {seccion} {texto}".lower()
    encontrados: List[str] = []

    if re.search(r"\bcodi\b|cobro digital|c[oó]digo qr|mensaje de cobro", blob):
        encontrados.append("codi")
    if re.search(r"\bdimo\b|dinero m[oó]vil|n[uú]mero de tel[eé]fono celular|10 d[ií]gitos", blob):
        encontrados.append("dimo")
    if re.search(r"\bspei\b|\bclabe\b|\bcep\b|clave de rastreo|transferencia electr[oó]nica|interbancari", blob):
        encontrados.append("spei")

    # Determinar método primario priorizando el documento origen
    doc_l = doc.lower()
    if "codi" in doc_l:
        primario = "codi"
    elif "dimo" in doc_l:
        primario = "dimo"
    elif "spei" in doc_l:
        primario = "spei"
    elif encontrados:
        primario = encontrados[0]
    else:
        primario = "general"

    if primario != "general" and primario not in encontrados:
        encontrados.insert(0, primario)

    return primario, encontrados


def _inferir_pantalla_y_errores(texto: str, seccion: str = "") -> Tuple[str, List[str]]:
    """Extrae etapa/pantalla operativa y códigos/tipos de error documentados en el fragmento."""
    blob = f"{seccion} {texto}".lower()

    pantalla = ""
    reglas_pantalla = [
        ("cobro_qr", r"c[oó]digo qr|escanear|nfc|mensaje de cobro"),
        ("transferir", r"clabe|destinatario|n[uú]mero celular|cuenta nueva|transferir"),
        ("monto_concepto", r"monto|l[ií]mite|comisi[oó]n|8,?000|concepto de pago"),
        ("confirmacion", r"confirmar|autoriza|nip|token|firma|factor de autenticaci[oó]n"),
        ("comprobante", r"\bcep\b|comprobante electr[oó]nico|clave de rastreo|movimientos"),
        ("rechazo_error", r"rechaz|devoluci[oó]n|retenid|error|fall[oa]|no se acredit|reclamaci[oó]n"),
    ]
    for nombre_pantalla, patron in reglas_pantalla:
        if re.search(patron, blob):
            pantalla = nombre_pantalla
            break

    errores: List[str] = []
    reglas_error = [
        ("formato_invalido", r"formato.*no es v[aá]lido|formato inv[aá]lido"),
        ("firma_invalida", r"firma.*no es v[aá]lida|firma electr[oó]nica"),
        ("saldo_insuficiente", r"saldo insuficiente|fondos insuficientes"),
        ("cuenta_invalida", r"cuenta.*inv[aá]lida|clabe.*incorrecta|no existe la cuenta"),
        ("limite_excedido", r"l[ií]mite.*monto|8,?000|exced|tope"),
        ("rechazo_pago", r"se rechaza|rechazad[oa]|devoluci[oó]n"),
        ("cep_no_encontrado", r"cep|clave de rastreo|no.*localiz|comprobante"),
        ("timeout_retencion", r"retenid|demora|tiempo m[aá]ximo|segundos|latencia"),
    ]
    for codigo, patron in reglas_error:
        if re.search(patron, blob):
            errores.append(codigo)

    return pantalla, errores


def _cargar_guias_json() -> Dict[str, Any]:
    """Carga y cachea `data/Embeddings/datos/guias.json`."""
    global _guias_cache
    if _guias_cache is not None:
        return _guias_cache
    if GUIAS_JSON_PATH.exists():
        try:
            with open(GUIAS_JSON_PATH, "r", encoding="utf-8") as f:
                _guias_cache = json.load(f)
                return _guias_cache
        except Exception:
            pass
    _guias_cache = {}
    return _guias_cache


def obtener_advertencias_pago(tipo_operacion: str = "cobro") -> List[str]:
    """Devuelve las advertencias de seguridad oficiales de `guias.json`."""
    guias = _cargar_guias_json()
    adv_dict = guias.get("advertencias", {})
    salida: List[str] = []
    if adv_dict.get("_claves"):
        salida.append(adv_dict["_claves"])
    for item in adv_dict.get(tipo_operacion, []):
        if item not in salida:
            salida.append(item)
    return salida


def _construir_documentos_pagos() -> List[Document]:
    """
    Lee `conocimiento.jsonl` y `guias.json` de `data/Embeddings/datos/` y los convierte en
    `Document` enriquecidos con metadatos de `metodo_pago` (codi/spei/dimo), `pantalla` y `codigos_error`.
    """
    docs: List[Document] = list(_DOCUMENTOS_BASE)

    # 1. Guías paso a paso y advertencias desde guias.json
    guias = _cargar_guias_json()
    if guias:
        for clave, contenido in guias.get("verificadas", {}).items():
            pasos = contenido.get("pasos", [])
            banco, _, flujo = clave.partition(":")
            for idx, paso in enumerate(pasos, 1):
                pant = paso.get("pantalla", "")
                txt = paso.get("texto", "")
                docs.append(
                    Document(
                        page_content=(
                            f"Guía paso a paso ({banco} - {flujo}, paso {idx}, pantalla '{pant}'): {txt}"
                        ),
                        metadata={
                            "chunk_id": f"guias#verificada#{clave}#{idx}",
                            "doc": "guias.json",
                            "titulo": f"Guía {banco} ({flujo})",
                            "seccion": pant or f"Paso {idx}",
                            "categoria": "pagos_digitales",
                            "tema": "guia_ui",
                            "fuente_tipo": "guias_json",
                            "metodo_pago": "spei",
                            "metodos_pago": ["spei", "dimo", "codi"],
                            "pantalla": pant.lower(),
                            "paso": idx,
                            "codigos_error": [],
                        },
                    )
                )

        for flujo, pasos in guias.get("genericas", {}).items():
            metodos = ["codi", "spei", "dimo"] if flujo in ("cobro", "transferencia") else ["spei"]
            resumen_pasos = " ".join(f"Paso {i}: {p.get('texto', '')}" for i, p in enumerate(pasos, 1))
            docs.append(
                Document(
                    page_content=f"Guía genérica de {flujo} en app bancaria: {resumen_pasos}",
                    metadata={
                        "chunk_id": f"guias#generica#{flujo}",
                        "doc": "guias.json",
                        "titulo": f"Guía genérica: {flujo}",
                        "seccion": flujo,
                        "categoria": "pagos_digitales",
                        "tema": "guia_ui",
                        "fuente_tipo": "guias_json",
                        "metodo_pago": "codi" if flujo == "cobro" else "spei",
                        "metodos_pago": metodos,
                        "pantalla": flujo,
                        "codigos_error": [],
                    },
                )
            )
            for idx, paso in enumerate(pasos, 1):
                docs.append(
                    Document(
                        page_content=f"Guía genérica ({flujo}, paso {idx}): {paso.get('texto', '')}",
                        metadata={
                            "chunk_id": f"guias#generica#{flujo}#{idx}",
                            "doc": "guias.json",
                            "titulo": f"Guía genérica: {flujo}",
                            "seccion": f"Paso {idx}",
                            "categoria": "pagos_digitales",
                            "tema": "guia_ui",
                            "fuente_tipo": "guias_json",
                            "metodo_pago": "codi" if flujo == "cobro" else "spei",
                            "metodos_pago": metodos,
                            "pantalla": flujo,
                            "paso": idx,
                            "codigos_error": [],
                        },
                    )
                )

        for clave_adv, val_adv in guias.get("advertencias", {}).items():
            textos = [val_adv] if isinstance(val_adv, str) else list(val_adv or [])
            for idx, t in enumerate(textos, 1):
                docs.append(
                    Document(
                        page_content=f"Advertencia de seguridad ({clave_adv}): {t}",
                        metadata={
                            "chunk_id": f"guias#advertencia#{clave_adv}#{idx}",
                            "doc": "guias.json",
                            "titulo": f"Advertencia de seguridad: {clave_adv}",
                            "seccion": "seguridad",
                            "categoria": "pagos_digitales",
                            "tema": "seguridad_pagos",
                            "fuente_tipo": "guias_json",
                            "metodo_pago": "general",
                            "metodos_pago": ["codi", "spei", "dimo"],
                            "pantalla": "confirmacion",
                            "codigos_error": ["seguridad", "nip", "verificacion_deposito"],
                        },
                    )
                )

    # 2. Corpus oficial Banxico (conocimiento.jsonl)
    if CONOCIMIENTO_JSONL_PATH.exists():
        with open(CONOCIMIENTO_JSONL_PATH, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    reg = json.loads(linea)
                except Exception:
                    continue
                texto = (reg.get("texto") or "").strip()
                if not texto:
                    continue
                doc_name = reg.get("doc", "")
                titulo = reg.get("titulo", "")
                seccion = reg.get("seccion", "")
                primario, metodos = _inferir_metodos_pago(texto, doc_name, seccion)
                pantalla, errores = _inferir_pantalla_y_errores(texto, seccion)

                encabezado = f"{titulo}" + (f" — {seccion}" if seccion else "")
                docs.append(
                    Document(
                        page_content=f"[{encabezado}]\n{texto}",
                        metadata={
                            "chunk_id": reg.get("id", ""),
                            "doc": doc_name,
                            "titulo": titulo,
                            "seccion": seccion,
                            "fuente": reg.get("fuente", ""),
                            "relevancia_base": reg.get("relevancia", "media"),
                            "categoria": "pagos_digitales",
                            "tema": primario,
                            "fuente_tipo": "conocimiento_jsonl",
                            "metodo_pago": primario,
                            "metodos_pago": metodos,
                            "pantalla": pantalla,
                            "codigos_error": errores,
                        },
                    )
                )

    return docs


def _guardar_faiss_precalculado_npz() -> Dict[str, Any]:
    """
    Carga los vectores precalculados de `data/Embeddings/datos/embeddings.npz` (4096-dim)
    en un índice FAISS `IndexFlatIP` y los persiste en `data/vectorstores/faiss/`.
    """
    if not EMBEDDINGS_NPZ_PATH.exists():
        return {"loaded": False, "reason": "embeddings.npz no encontrado"}

    try:
        import faiss

        npz = np.load(EMBEDDINGS_NPZ_PATH, allow_pickle=True)
        vectores = npz["v"].astype(np.float32)
        ids = [str(x) for x in npz["ids"].tolist()]
        modelo_origen = str(npz["modelo"].item()) if "modelo" in npz else "unknown"

        faiss.normalize_L2(vectores)
        index = faiss.IndexFlatIP(vectores.shape[1])
        index.add(vectores)
        faiss.write_index(index, str(FAISS_PRECOMPUTED_PATH))

        with open(FAISS_PRECOMPUTED_META_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "modelo_origen": modelo_origen,
                    "dimension": int(vectores.shape[1]),
                    "total_vectores": int(vectores.shape[0]),
                    "ids": ids,
                },
                f,
                ensure_ascii=False,
            )
        return {
            "loaded": True,
            "modelo_origen": modelo_origen,
            "dimension": int(vectores.shape[1]),
            "total_vectores": int(vectores.shape[0]),
        }
    except Exception as exc:
        return {"loaded": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# Embeddings locales normalizados (384 -> 1024 exacto para pgvector) + Reranker
# ---------------------------------------------------------------------------

def _get_active_embeddings():
    """
    Obtiene el modelo de embeddings local normalizado (`all-MiniLM-L6-v2`) para consultas
    rápidas con similitud coseno en FAISS y proyección exacta a `vector(1024)` en pgvector.
    """
    global _embeddings_singleton
    if _embeddings_singleton is not None:
        return _embeddings_singleton

    from langchain_huggingface import HuggingFaceEmbeddings
    _embeddings_singleton = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embeddings_singleton


def _pad_to_pgvector_dim(vec: List[float], target_dim: int = _PGVECTOR_DIM) -> List[float]:
    """
    Extiende con ceros (o trunca re-normalizando) un vector L2-normalizado a `target_dim=1024`.
    Para vectores unitarios de 384 dims, el zero-padding preserva exactamente la similitud coseno
    (`1 - (u <=> v)`) dentro del índice HNSW de PostgreSQL `pgvector`.
    """
    arr = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm > 0:
        arr = arr / norm
    if len(arr) == target_dim:
        return arr.tolist()
    if len(arr) < target_dim:
        padded = np.zeros(target_dim, dtype=np.float32)
        padded[: len(arr)] = arr
        return padded.tolist()
    sliced = arr[:target_dim]
    s_norm = float(np.linalg.norm(sliced))
    if s_norm > 0:
        sliced = sliced / s_norm
    return sliced.tolist()


def _get_nemo_reranker():
    """Obtiene el modelo reranker `nvidia/nv-rerankqa-mistral-4b-v3` si está disponible y autorizado."""
    global _reranker_unavailable
    if _reranker_unavailable:
        return None
    if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIARerank
            return NVIDIARerank(model="nvidia/nv-rerankqa-mistral-4b-v3", nvidia_api_key=NVIDIA_API_KEY)
        except Exception:
            _reranker_unavailable = True
    return None


def _get_faiss_vectorstore(force_rebuild: bool = False):
    """
    Carga o construye el almacén vectorial FAISS en `data/vectorstores/faiss/` con todo el
    conocimiento de pagos digitales (`conocimiento.jsonl`, `embeddings.npz`, `guias.json`).
    """
    global _faiss_store
    if _faiss_store is not None and not force_rebuild:
        return _faiss_store

    from langchain_community.vectorstores import FAISS
    from langchain_community.vectorstores.utils import DistanceStrategy

    embeddings = _get_active_embeddings()
    index_file = FAISS_DIR / "index.faiss"

    manifest_ok = False
    if not force_rebuild and index_file.exists() and FAISS_MANIFEST_PATH.exists():
        try:
            manifest = json.loads(FAISS_MANIFEST_PATH.read_text(encoding="utf-8"))
            if manifest.get("version") == _FAISS_INDEX_VERSION and manifest.get("total_docs", 0) >= 900:
                manifest_ok = True
        except Exception:
            manifest_ok = False

    if manifest_ok:
        try:
            _faiss_store = FAISS.load_local(
                str(FAISS_DIR),
                embeddings,
                allow_dangerous_deserialization=True,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
            return _faiss_store
        except Exception:
            pass

    # Construir índice completo desde data/Embeddings/datos/
    npz_info = _guardar_faiss_precalculado_npz()
    documentos = _construir_documentos_pagos()
    _faiss_store = FAISS.from_documents(
        documentos,
        embeddings,
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
    )
    try:
        _faiss_store.save_local(str(FAISS_DIR))
        FAISS_MANIFEST_PATH.write_text(
            json.dumps(
                {
                    "version": _FAISS_INDEX_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "total_docs": len(documentos),
                    "precomputed_npz": npz_info,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    return _faiss_store


def sincronizar_pgvector(forzar: bool = False) -> Dict[str, Any]:
    """
    Sincroniza los documentos y fragmentos de CoDi, SPEI y DiMo hacia las tablas
    `documento` y `fragmento` (`vector(1024)`) en PostgreSQL (`tiendita-db`) si está disponible.
    """
    global _pgvector_synced_session
    try:
        from tools.db_client import _get_connection

        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM fragmento")
                existentes = int(cur.fetchone()[0])
                if existentes >= 900 and not forzar:
                    _pgvector_synced_session = True
                    return {"synced": True, "status": "already_synced", "fragmentos": existentes}

                if forzar:
                    cur.execute("DELETE FROM documento")

                docs = _construir_documentos_pagos()
                embeddings = _get_active_embeddings()
                textos = [d.page_content for d in docs]
                vectores_raw = embeddings.embed_documents(textos)

                # Agrupar documentos padre por nombre de archivo
                doc_ids: Dict[str, str] = {}
                for d in docs:
                    doc_key = d.metadata.get("doc") or "general"
                    if doc_key not in doc_ids:
                        cur.execute(
                            "INSERT INTO documento (titulo, fuente) VALUES (%s, %s) RETURNING id",
                            (d.metadata.get("titulo") or doc_key, d.metadata.get("fuente") or doc_key),
                        )
                        doc_ids[doc_key] = str(cur.fetchone()[0])

                # Inserción por lotes en tabla fragmento
                batch_rows = []
                for d, v_raw in zip(docs, vectores_raw):
                    doc_key = d.metadata.get("doc") or "general"
                    v_1024 = _pad_to_pgvector_dim(v_raw, _PGVECTOR_DIM)
                    vec_literal = "[" + ",".join(f"{x:.6f}" for x in v_1024) + "]"
                    meta_tag = json.dumps(
                        {
                            "chunk_id": d.metadata.get("chunk_id", ""),
                            "metodo_pago": d.metadata.get("metodo_pago", "general"),
                            "metodos_pago": d.metadata.get("metodos_pago", []),
                            "pantalla": d.metadata.get("pantalla", ""),
                            "seccion": d.metadata.get("seccion", ""),
                            "doc": doc_key,
                            "fuente_tipo": d.metadata.get("fuente_tipo", ""),
                        },
                        ensure_ascii=False,
                    )
                    texto_almacenado = f"{meta_tag}\n{d.page_content}"
                    batch_rows.append((doc_ids[doc_key], texto_almacenado, vec_literal))

                cur.executemany(
                    "INSERT INTO fragmento (documento_id, texto, embedding) VALUES (%s, %s, %s::vector)",
                    batch_rows,
                )
            conn.commit()

        _pgvector_synced_session = True
        return {
            "synced": True,
            "status": "synchronized",
            "documentos": len(doc_ids),
            "fragmentos": len(batch_rows),
        }
    except Exception as exc:
        return {"synced": False, "status": "unavailable", "error": str(exc)}


def _buscar_en_pgvector(consulta: str, top_k: int = 8) -> List[Tuple[Document, float]]:
    """Ejecuta búsqueda coseno directa en PostgreSQL `pgvector` si `fragmento` está poblada."""
    try:
        from tools.db_client import _get_connection

        embeddings = _get_active_embeddings()
        q_vec = _pad_to_pgvector_dim(embeddings.embed_query(consulta), _PGVECTOR_DIM)
        vec_literal = "[" + ",".join(f"{x:.6f}" for x in q_vec) + "]"

        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT f.texto, d.titulo, d.fuente, (1 - (f.embedding <=> %s::vector)) AS score
                      FROM fragmento f
                      JOIN documento d ON d.id = f.documento_id
                     ORDER BY f.embedding <=> %s::vector
                     LIMIT %s
                    """,
                    (vec_literal, vec_literal, top_k),
                )
                filas = cur.fetchall()

        resultados: List[Tuple[Document, float]] = []
        for texto_full, titulo, fuente, score in filas:
            meta: Dict[str, Any] = {"titulo": titulo, "fuente": fuente}
            cuerpo = texto_full
            if texto_full.startswith("{") and "\n" in texto_full:
                primera, resto = texto_full.split("\n", 1)
                try:
                    meta.update(json.loads(primera))
                    cuerpo = resto
                except Exception:
                    pass
            resultados.append((Document(page_content=cuerpo, metadata=meta), float(score)))
        return resultados
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Búsqueda Especializada en Pagos Digitales (CoDi, SPEI, DiMo)
# ---------------------------------------------------------------------------

def _normalizar_metodo_pago(metodo_pago: Optional[str]) -> Optional[str]:
    if not metodo_pago:
        return None
    m = metodo_pago.strip().lower()
    if m in ("codi", "qr", "cobro_digital"):
        return "codi"
    if m in ("spei", "transferencia", "clabe", "cep"):
        return "spei"
    if m in ("dimo", "dinero_movil", "celular"):
        return "dimo"
    return m


def buscar_guia_pago(
    metodo_pago: Optional[str],
    pantalla: Optional[str],
    consulta: str,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Recupera y rankea los pasos exactos, reglas, límites y solución de errores de
    **CoDi, SPEI o DiMo** desde `data/vectorstores/faiss/` (y `pgvector` si está sincronizado).

    Aplica reranking con `nvidia/nv-rerankqa-mistral-4b-v3` cuando `NVIDIA_API_KEY` esté activa
    y autorizada, o similitud coseno en `FAISS` como respaldo automático.
    """
    global _reranker_unavailable

    metodo_norm = _normalizar_metodo_pago(metodo_pago)
    pantalla_norm = pantalla.strip().lower() if pantalla else None

    partes_query = []
    if metodo_norm:
        etiquetas = {
            "codi": "CoDi cobro digital código QR",
            "spei": "SPEI transferencia electrónica CLABE CEP",
            "dimo": "DiMo dinero móvil número celular",
        }
        partes_query.append(etiquetas.get(metodo_norm, metodo_norm))
    if pantalla_norm:
        partes_query.append(f"pantalla {pantalla_norm}")
    if consulta:
        partes_query.append(consulta.strip())
    query_enriquecida = " ".join(partes_query).strip() or "pagos digitales CoDi SPEI DiMo"

    vs = _get_faiss_vectorstore()
    fetch_k = max(top_k * 8, 24)
    pares_faiss = vs.similarity_search_with_score(query_enriquecida, k=fetch_k)
    motor = "faiss_cosine"

    # Filtrar y puntuar por método de pago, pantalla y calidad de guía
    candidatos_puntuados: List[Tuple[Document, float]] = []
    for doc, raw_score in pares_faiss:
        meta = doc.metadata or {}
        score_coseno = max(0.0, min(1.0, float(raw_score)))
        metodos_doc = [m.lower() for m in (meta.get("metodos_pago") or [])]
        metodo_doc = str(meta.get("metodo_pago", "general")).lower()

        if metodo_norm in ("codi", "spei", "dimo"):
            coincide_metodo = (metodo_doc == metodo_norm) or (metodo_norm in metodos_doc)
            if not coincide_metodo:
                continue
            if metodo_doc == metodo_norm:
                score_coseno = min(1.0, score_coseno + 0.06)

        if pantalla_norm:
            pant_doc = str(meta.get("pantalla", "")).lower()
            sec_doc = str(meta.get("seccion", "")).lower()
            if pantalla_norm in pant_doc or pantalla_norm in sec_doc or pant_doc and pant_doc in pantalla_norm:
                score_coseno = min(1.0, score_coseno + 0.08)

        # Dar ligera prioridad a guías paso a paso cuando se solicita asistencia de pantalla
        if pantalla_norm and meta.get("fuente_tipo") == "guias_json":
            score_coseno = min(1.0, score_coseno + 0.05)

        candidatos_puntuados.append((doc, score_coseno))

    # Si el filtro estricto dejó menos de top_k, completar con los mejores resultados sin filtro
    if len(candidatos_puntuados) < top_k:
        ids_ya = {d.metadata.get("chunk_id") for d, _ in candidatos_puntuados}
        for doc, raw_score in pares_faiss:
            cid = doc.metadata.get("chunk_id")
            if cid not in ids_ya:
                candidatos_puntuados.append((doc, max(0.0, min(1.0, float(raw_score)))))
                ids_ya.add(cid)
            if len(candidatos_puntuados) >= max(top_k * 2, 6):
                break

    candidatos_puntuados.sort(key=lambda par: par[1], reverse=True)
    top_candidatos = candidatos_puntuados[: max(top_k * 2, 6)]

    # Reranking con NVIDIA NeMo (`nvidia/nv-rerankqa-mistral-4b-v3`) si está disponible
    reranker = _get_nemo_reranker()
    if reranker and len(top_candidatos) > 1:
        try:
            docs_only = [d for d, _ in top_candidatos]
            ranked = reranker.compress_documents(documents=docs_only, query=query_enriquecida)
            if ranked:
                top_candidatos = [
                    (d, float(d.metadata.get("relevance_score", 0.5)))
                    for d in ranked[:top_k]
                ]
                motor = "faiss+nemo_rerank"
        except Exception:
            _reranker_unavailable = True

    resultados: List[Dict[str, Any]] = []
    for doc, score in top_candidatos[:top_k]:
        meta = doc.metadata or {}
        resultados.append({
            "id": meta.get("chunk_id", ""),
            "doc": meta.get("doc", ""),
            "titulo": meta.get("titulo", ""),
            "seccion": meta.get("seccion", ""),
            "fuente_tipo": meta.get("fuente_tipo", ""),
            "metodo_pago": meta.get("metodo_pago", "general"),
            "metodos_pago": meta.get("metodos_pago", []),
            "pantalla": meta.get("pantalla", ""),
            "codigos_error": meta.get("codigos_error", []),
            "score": round(float(score), 4),
            "motor": motor,
            "texto": doc.page_content.strip(),
        })

    return resultados


def buscar_rag_pagos(
    consulta: str,
    top_k: int = 5,
    metodo_pago: Optional[str] = None,
    preferir_pgvector: bool = False,
) -> Dict[str, Any]:
    """
    Consulta unificada para el comando `/rag <consulta>` del CLI:
    recupera documentos de CoDi, SPEI o DiMo con puntuación de relevancia desde
    `data/vectorstores/faiss/` o `pgvector` y reporta el estado de ambos índices.
    """
    pg_sync = sincronizar_pgvector(forzar=False)
    resultados_pg: List[Dict[str, Any]] = []

    if preferir_pgvector and pg_sync.get("synced"):
        pares_pg = _buscar_en_pgvector(consulta, top_k=top_k)
        for doc, score in pares_pg:
            meta = doc.metadata or {}
            resultados_pg.append({
                "id": meta.get("chunk_id", ""),
                "doc": meta.get("doc", ""),
                "titulo": meta.get("titulo", ""),
                "seccion": meta.get("seccion", ""),
                "fuente_tipo": meta.get("fuente_tipo", ""),
                "metodo_pago": meta.get("metodo_pago", "general"),
                "pantalla": meta.get("pantalla", ""),
                "score": round(float(score), 4),
                "motor": "pgvector_cosine",
                "texto": doc.page_content.strip(),
            })

    resultados = resultados_pg or buscar_guia_pago(
        metodo_pago=metodo_pago,
        pantalla=None,
        consulta=consulta,
        top_k=top_k,
    )

    return {
        "consulta": consulta,
        "metodo_filtrado": metodo_pago,
        "motor_usado": resultados[0]["motor"] if resultados else "faiss_cosine",
        "faiss_dir": str(FAISS_DIR),
        "pgvector": pg_sync,
        "total": len(resultados),
        "resultados": resultados,
    }


# ---------------------------------------------------------------------------
# Indexación de Reportes Históricos y Herramientas @tool existentes
# ---------------------------------------------------------------------------

def index_strategic_report(report: StrategicReport | Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Persiste un reporte estratégico en disco (JSON y Markdown) y lo indexa vectorialmente
    en FAISS para consultas históricas inmediatas.
    """
    report_data = report if isinstance(report, dict) else report.model_dump()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = report_data.get("identificacion_sector", "reporte")[:30].replace(" ", "_").replace("/", "-")
    base_name = f"{timestamp}_{slug}"

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

    texto_indexacion = (
        f"REPORTE ESTRATÉGICO [{timestamp}]: {report_data.get('identificacion_sector', '')}. "
        f"Tendencias: {report_data.get('mercado_tendencias', '')}. Clientes: {report_data.get('clientes', '')}. "
        f"Problemas: {report_data.get('problemas', '')}. Soluciones: {report_data.get('soluciones', '')}. "
        f"Hipótesis: {report_data.get('hipotesis', '')}. Objetivos: {report_data.get('objetivos', '')}. "
        f"Impacto: {report_data.get('impacto', '')}. Hallazgos: {report_data.get('hallazgos', '')}."
    )
    meta = dict(metadata or {})
    meta.update({
        "chunk_id": f"reporte#{timestamp}",
        "doc": json_path.name,
        "titulo": f"Reporte Estratégico {timestamp}",
        "seccion": "estrategia",
        "timestamp": timestamp,
        "tipo": "strategic_report",
        "fuente_tipo": "strategic_report",
        "metodo_pago": "general",
        "metodos_pago": [],
        "archivo_json": str(json_path),
        "archivo_md": str(md_path),
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
    docs = vs.similarity_search(query, k=max(top_k * 4, 12))
    return [d for d in docs if d.metadata.get("tipo") == "strategic_report"][:top_k]


@tool
def consultar_conocimiento_comercial(consulta: str, categoria: Optional[str] = None) -> str:
    """
    Consulta la base de conocimientos comerciales y guías oficiales de pagos digitales (CoDi, SPEI, DiMo)
    usando la Arquitectura RAG Dual (FAISS + pgvector + NeMo Rerank si está disponible).
    """
    resultados = buscar_guia_pago(
        metodo_pago=categoria if categoria in ("codi", "spei", "dimo") else None,
        pantalla=None,
        consulta=consulta,
        top_k=3,
    )
    salida = []
    for r in resultados:
        etiqueta = f"{r['metodo_pago'].upper()} | {r['doc']} | score={r['score']:.3f}"
        salida.append(f"[{etiqueta}]: {r['texto']}")
    return "\n\n".join(salida) if salida else "Sin conocimiento específico registrado para esta consulta."


@tool
def indexar_documento_comercial(texto: str, categoria: str, tema: str) -> str:
    """
    Registra dinámicamente una nueva regla, política o dato en el almacén vectorial RAG Dual.
    """
    doc = Document(
        page_content=texto,
        metadata={
            "chunk_id": f"regla#{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "doc": "reglas_dinamicas",
            "titulo": tema,
            "seccion": categoria,
            "categoria": categoria.lower(),
            "tema": tema.lower(),
            "fuente_tipo": "regla_dinamica",
            "metodo_pago": tema.lower() if tema.lower() in ("codi", "spei", "dimo") else "general",
            "metodos_pago": [tema.lower()] if tema.lower() in ("codi", "spei", "dimo") else [],
        },
    )
    vs = _get_faiss_vectorstore()
    vs.add_documents([doc])
    try:
        vs.save_local(str(FAISS_DIR))
    except Exception:
        pass
    return f"Documento indexado con éxito en categoría '{categoria}', tema '{tema}'."
