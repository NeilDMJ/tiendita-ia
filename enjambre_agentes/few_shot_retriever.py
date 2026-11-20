"""
few_shot_retriever.py — Inyección dinámica de ejemplos Few-Shot (NeMo Retriever + Data Flywheel).

Pipeline de recuperación en 2 pasos sobre PostgreSQL/pgvector (`ejemplos_few_shot`):
  1. Top-10 por similitud coseno (`embedding <=> query_vec`) filtrado por `rol_agente`,
     con `nvidia/nv-embedqa-e5-v5` (`input_type="query"` / `"passage"`).
  2. Reranking de esos candidatos con `nvidia/nv-rerankqa-mistral-4b-v3` -> Top-3.

Data Flywheel hacia NeMo Customizer:
  - `record_hitl_feedback(...)`: guarda cada interacción HITL aprobada/editada.
  - `export_sft_dataset_jsonl(...)`: exporta los registros verificados en formato
    conversacional (`{"messages": [system, user, assistant]}`) para un SFT Customization Job.

Sin `DATABASE_URL` o sin endpoint NeMo alcanzable, degrada sin error al dataset del asistente
y al banco semilla en memoria (comportamiento determinista previo).

Banco semilla en memoria para los roles:
   - `orquestador`: Enrutamiento simple y multi-intención coordinada.
   - `ocr`: Clasificación de tickets (`inversion_inventario` vs `gasto_operativo`).
   - `investigador`: Reporte comercial de 9 secciones obligatorias.
   - `publicista`: Prompt de video vertical 9:16 (5s) + copy persuasivo + CTA.
   - `tutor_ui`: Guía de pago en máximo 2 oraciones accionables referenciando la UI.
"""
from __future__ import annotations

import os
import json
import asyncio
import hashlib
import logging
from contextlib import closing
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Literal, Sequence

from pydantic import BaseModel, Field

from models import (
    NemoServiceError,
    get_nemo_embeddings_client,
    get_nemo_reranker_client,
    nemo_is_configured,
    run_sync,
)

logger = logging.getLogger(__name__)

_PKG_DIR = Path(__file__).resolve().parent


# ─────────────────────────────────────────────────────────────────────────────
# 1. BANCO DE EJEMPLOS SEMILLA DETERMINISTAS (FALLBACK INMEDIATO)
# ─────────────────────────────────────────────────────────────────────────────

SEED_FEW_SHOTS: Dict[str, List[Dict[str, Any]]] = {
    "orquestador": [
        {
            "escenario": "Enrutamiento simple por escaneo POS",
            "entrada": {
                "event_source": "vision_api",
                "vision_payload": {
                    "endpoint": "/pos-checkout",
                    "items": [{"sku": "COCA-600", "nombre": "Coca Cola 600ml", "cantidad": 2}],
                    "confianza_global": 0.98
                }
            },
            "decision": {
                "next_step": "vendedor",
                "reasoning": "El evento proviene de la cámara del punto de venta (/pos-checkout). Se delega al Vendedor para armar el carrito, validar inventario y preparar cobro.",
                "instructions_for_agent": "Armar carrito de compra, comprobar existencias de COCA-600 y sugerir cross-selling."
            }
        },
        {
            "escenario": "Enrutamiento multi-intención (Caducidad -> Análisis -> Campaña)",
            "entrada": {
                "event_source": "chat",
                "query": "Revisa los productos próximos a caducar, analiza el margen de ganancia de los que tengan stock alto y prepárame una campaña de descuento para sacarlos rápido."
            },
            "decision": {
                "next_step": "control",
                "reasoning": "La solicitud requiere una cadena de 3 especialistas. Primero el Agente de Control debe consultar lotes_inventario por caducar; posteriormente el Analista evaluará márgenes y finalmente el Publicista generará los activos.",
                "instructions_for_agent": "Consultar lotes próximos a vencer (query_expiring_products) y reportar SKUs críticos al estado."
            }
        }
    ],

    "ocr": [
        {
            "tipo_ticket": "Factura de Proveedor de Mercancía",
            "proveedor": "Distribuidora de Lácteos y Abarrotes del Centro S.A. de C.V.",
            "items": [
                {"descripcion": "Leche Entera 1L (Caja 12 pzas)", "cantidad": 5, "precio_unitario": 280.00, "subtotal": 1400.00},
                {"descripcion": "Huevo Blanco 18 pzas", "cantidad": 10, "precio_unitario": 55.00, "subtotal": 550.00}
            ],
            "total": 1950.00,
            "clasificacion": "inversion_inventario",
            "justificacion": "Los bienes adquiridos corresponden a mercancía para reventa en tienda (lácteos y huevo). Incrementan el inventario realizable."
        },
        {
            "tipo_ticket": "Recibo de Servicios / Mantenimiento",
            "proveedor": "CFE Suministrador de Servicios Básicos",
            "items": [
                {"descripcion": "Consumo Energía Eléctrica Tarifa PDBT Local Comercial", "cantidad": 1, "precio_unitario": 1280.00, "subtotal": 1280.00}
            ],
            "total": 1280.00,
            "clasificacion": "gasto_operativo",
            "justificacion": "Corresponde a suministro de energía para la operación continua de refrigeradores y luces del local. No genera existencias vendibles."
        }
    ],

    "investigador": [
        {
            "sector": "Comercio Minorista de Proximidad (Tiendita de Abarrotes Tradicional)",
            "strategic_report": {
                "identificacion_sector": "Sector retail de proximidad (canal tradicional de abarrotes y misceláneas en México/LATAM), enfocado en compras de conveniencia diaria y reposición inmediata.",
                "mercado_tendencias": "Crecimiento del 18% en métodos de cobro digital (SPEI, QR, tarjetas sin contacto). Alta preferencia por presentaciones unitarias y marcas de valor ante presiones inflacionarias.",
                "clientes": "Familias locales, amas de casa y trabajadores de paso con frecuencia de visita de 3 a 5 veces por semana y ticket promedio de $65 a $110 MXN.",
                "problemas": "Merma por caducidad en lácteos y perecederos (6.5% del volumen), desabasto imprevisto en fines de semana y falta de visibilidad en márgenes reales por producto.",
                "soluciones": "Automatización de alertas de caducidad a 72 horas, cross-selling dinámico en mostrador (snacks + bebidas frías) e integración de pagos SPEI con confirmación auditiva.",
                "hipotesis": "Ofrecer un descuento dinámico del 15% en lotes a 3 días de expirar reduce la merma en un 70% e incrementa el flujo de caja sin canibalizar margen operativo.",
                "objetivos": "Reducir la pérdida por caducidad a menos del 1.5% mensual y aumentar el ticket promedio a $95 MXN mediante combos estratégicos.",
                "impacto": "Aumento estimado del margen neto global de 4.2 puntos porcentuales y recuperación de $3,500 MXN mensuales en inventario que antes se descartaba.",
                "hallazgos": "Los clientes aceptan compras de oportunidad con descuento visible en caja; el 82% de las ventas de impulso ocurren entre las 17:00 y las 20:30 hrs."
            }
        }
    ],

    "publicista": [
        {
            "producto": "Leche Entera Lala 1L",
            "motivo": "Lote con 3 días restantes antes de caducidad",
            "descuento": "20%",
            "promo_assets": {
                "video_prompt": "Cinematic vertical 9:16 commercial, 5 seconds. Extreme close-up of a glass bottle of fresh whole milk with chilled condensation drops catching soft morning sunlight. Rich creamy milk pouring smoothly into a glass on a clean rustic wooden countertop, warm morning bakery ambience, hyperrealistic, vibrant colors, 4k 60fps commercial look.",
                "copy_promocional": "¡Aprovecha hoy 20% de descuento en Leche Lala 1L! Frescura garantizada para el desayuno familiar. Solo por hoy o hasta agotar existencias en Tiendita IA.",
                "call_to_action": "Toca aquí para apartar tus litros en la app o pídelos directo por WhatsApp.",
                "video_url": "https://cdn.tiendita.ia/promos/leche_lala_descuento_916.mp4"
            }
        }
    ],

    "control": [
        {
            "usuario": "Sube la Coca a $22",
            "asistente": {
                "tool": "actualizar_precio",
                "args": {"nombre": "Coca-Cola 600 ml", "precio": 22.0},
                "respuesta": "Listo, el precio de Coca-Cola 600 ml se actualizó a $22.00. Confirma para guardar el cambio."
            },
            "categoria": "precio"
        },
        {
            "usuario": "¿Cuánto me queda de leche?",
            "asistente": {
                "tool": "consultar_inventario",
                "args": {"nombre": "Leche Lala 1 L"},
                "respuesta": "Tienes 14 piezas de Leche Lala 1 L en existencia (mínimo recomendado: 6)."
            },
            "categoria": "consulta_producto"
        },
        {
            "usuario": "Dame de alta Mazapán a $5, tengo 24 piezas",
            "asistente": {
                "tool": "crear_producto",
                "args": {"nombre": "Mazapán", "precio": 5.0, "stock": 24},
                "respuesta": "Producto 'Mazapán' registrado con precio $5.00 y stock inicial de 24 piezas. Confirma para guardar."
            },
            "categoria": "crear_completo"
        },
        {
            "usuario": "Llegaron 10 de Bimbo",
            "asistente": {
                "tool": "ajustar_stock",
                "args": {"nombre": "Pan Bimbo Blanco", "cantidad": 10, "tipo": "entrada"},
                "respuesta": "Se registraron 10 piezas de entrada de Pan Bimbo Blanco. Stock actualizado."
            },
            "categoria": "stock"
        }
    ],

    "tutor_ui": [
        {
            "ui_state": {
                "pantalla": "PagoSPEI",
                "paso_actual": "ingreso_clabe",
                "campos_vacios": ["clabe_interbancaria"],
                "error_visible": "La cuenta CLABE debe contener exactamente 18 dígitos numéricos.",
                "intentos": 2
            },
            "asistencia_recomendada": "Verifica que tu cuenta CLABE tenga exactamente 18 dígitos sin espacios ni guiones. Pégala en el campo 'CLABE Interbancaria' y pulsa el botón verde 'Verificar y Continuar'."
        },
        {
            "ui_state": {
                "pantalla": "CheckoutTarjeta",
                "paso_actual": "cvv_invalido",
                "campos_vacios": ["cvv"],
                "error_visible": "Código CVV incompleto.",
                "intentos": 1
            },
            "asistencia_recomendada": "Ingresa el código de seguridad de 3 dígitos ubicado al reverso de tu tarjeta en el campo 'CVV'. Al completarlo, el botón 'Pagar con Tarjeta' se activará para finalizar tu compra."
        }
    ]
}


# ────────────────────────────────────────────────────────────────────────────────
# 2. CONSTANTES, PROMPTS DE SISTEMA Y MODELO DE REGISTRO
# ────────────────────────────────────────────────────────────────────────────────

SCHEMA_SQL_PATH = _PKG_DIR / "sql" / "001_ejemplos_few_shot.sql"
DEFAULT_SFT_PATH = "datasets/nemo_sft_train.jsonl"
RETRIEVAL_TOP_K = 10   # candidatos por similitud coseno (paso 1)
RERANK_TOP_N = 3       # ejemplos finales tras reranking (paso 2)
_INDEX_TEXT_MAX_CHARS = 1500

_ROLE_ALIASES = {"supervisor": "orquestador", "tutor": "tutor_ui"}

# Prompt de sistema por rol: es el `system` de cada registro del dataset SFT. Debe coincidir con el
# prompt base con el que se invoque el adaptador LoRA resultante (NEMO_MODEL_<ROL>).
ROLE_SYSTEM_PROMPTS: Dict[str, str] = {
    "orquestador": (
        "Eres el Supervisor de un ecosistema multiagente para una tiendita de barrio. Recibes un JSON "
        "con event_source, query y/o vision_payload. Responde ÚNICAMENTE con JSON "
        '{"next_step": "<agente>", "reasoning": "<motivo>", "instructions_for_agent": "<instrucciones>"} '
        "eligiendo entre control, vendedor, analista, investigador, publicista, tutor_ui o FIN."
    ),
    "control": (
        "Eres el Agente de Control de inventario de una tiendita. Responde ÚNICAMENTE en JSON "
        '{"tool": "<nombre o null>", "args": {...}, "respuesta": "<texto breve en español>"}. '
        "Nunca inventes precios ni existencias; toda mutación requiere confirmación humana."
    ),
    "vendedor": (
        "Eres el Agente Vendedor del punto de venta de una tiendita. Arma el carrito solo con productos, "
        "precios y existencias de la base de datos, sin revelar costos de proveedor. Responde en JSON "
        "con la acción y el payload de la venta; toda venta requiere confirmación humana."
    ),
    "publicista": (
        "Eres el Agente Publicista de una tiendita. Responde ÚNICAMENTE en JSON con video_prompt "
        "(inglés, vertical 9:16, 5 segundos), copy_promocional (español) y call_to_action."
    ),
    "tutor_ui": (
        "Eres el Tutor de pagos de la app móvil de una tiendita. Dado el ui_state, responde en MÁXIMO 2 "
        "oraciones accionables que nombren solo botones o campos visibles en pantalla."
    ),
    "ocr": (
        "Eres el Agente de OCR financiero de una tiendita. Clasifica el ticket como inversion_inventario "
        "o gasto_operativo y responde ÚNICAMENTE en JSON con clasificacion y justificacion."
    ),
    "investigador": (
        "Eres el Agente Investigador de mercado de una tiendita. Responde ÚNICAMENTE en JSON con las 9 claves: "
        "identificacion_sector, mercado_tendencias, clientes, problemas, soluciones, hipotesis, objetivos, "
        "impacto, hallazgos."
    ),
}
_GENERIC_SYSTEM_PROMPT = "Eres un agente especializado de una tiendita de barrio. Responde únicamente en JSON."


class FeedbackRecord(BaseModel):
    """Par entrada/salida verificado de un agente (fila de `ejemplos_few_shot`)."""
    rol_agente: str
    entrada: Dict[str, Any]
    salida: Dict[str, Any]
    origen: Literal["seed", "assistant_dataset", "hitl_aprobado", "hitl_editado"] = "hitl_aprobado"

    def texto_indexado(self) -> str:
        """Texto que se embebe: la entrada del ejemplo, que es lo que se compara con la consulta."""
        return json.dumps(self.entrada, ensure_ascii=False, sort_keys=True)[:_INDEX_TEXT_MAX_CHARS]

    def huella(self) -> str:
        canonical = json.dumps(
            [self.rol_agente, self.entrada, self.salida], ensure_ascii=False, sort_keys=True, default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_role(role: str) -> str:
    key = role.lower().strip()
    return _ROLE_ALIASES.get(key, key)


def _vec_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{v:.7g}" for v in vec) + "]"


def _seed_to_pair(role: str, shot: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Normaliza un ejemplo semilla (formas heterogéneas por rol) a un par (entrada, salida)."""
    pick = lambda keys: {k: shot[k] for k in keys if k in shot}  # noqa: E731
    if role == "orquestador":
        return shot.get("entrada", {}), shot.get("decision", {})
    if role == "ocr":
        return pick(("tipo_ticket", "proveedor", "items", "total")), pick(("clasificacion", "justificacion"))
    if role == "investigador":
        return {"sector": shot.get("sector")}, shot.get("strategic_report", {})
    if role == "publicista":
        return pick(("producto", "motivo", "descuento")), shot.get("promo_assets", {})
    if role == "control":
        return {"usuario": shot.get("usuario")}, shot.get("asistente", {})
    if role == "tutor_ui":
        return shot.get("ui_state", {}), {"asistencia_recomendada": shot.get("asistencia_recomendada")}
    return {}, shot


# ────────────────────────────────────────────────────────────────────────────────
# 3. FEW-SHOT RETRIEVER: PGVECTOR + RERANKING + FALLBACKS DETERMINISTAS
# ────────────────────────────────────────────────────────────────────────────────

class FewShotRetriever:
    """
    Recuperador de ejemplos Few-Shot. Orden de preferencia por llamada:
    1. NeMo Retriever sobre pgvector (requiere DATABASE_URL + endpoint NeMo alcanzable + `query`).
    2. Dataset del asistente de catálogo (rol `control`).
    3. Últimos ejemplos verificados en PostgreSQL (si hay DATABASE_URL).
    4. Banco semilla determinista en memoria (`SEED_FEW_SHOTS`).

    `embedder` / `reranker` pueden inyectarse (pruebas); por defecto se crean con
    `get_nemo_embeddings_client()` / `get_nemo_reranker_client()`.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        embedder: Optional[Any] = None,
        reranker: Optional[Any] = None,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._embedder = embedder
        self._reranker = reranker
        self._seed_store = SEED_FEW_SHOTS
        self._assistant_data = self._load_assistant_dataset()

    # ── clientes NeMo (perezosos) ──

    @property
    def embedder(self) -> Any:
        if self._embedder is None:
            self._embedder = get_nemo_embeddings_client()
        return self._embedder

    @property
    def reranker(self) -> Any:
        if self._reranker is None:
            self._reranker = get_nemo_reranker_client()
        return self._reranker

    def _nemo_available(self) -> bool:
        if os.getenv("NEMO_RETRIEVER_ENABLED", "true").lower() == "false":
            return False
        return self._embedder is not None or nemo_is_configured()

    def _semantic_ready(self) -> bool:
        return bool(self.db_url) and self._nemo_available()

    def _connect(self) -> Any:
        import psycopg2
        return psycopg2.connect(self.db_url)

    # ── dataset del asistente de catálogo ──

    def _load_assistant_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        """Carga e indexa por categoría el dataset sintetizado (data/train.jsonl)."""
        dataset_by_cat: Dict[str, List[Dict[str, Any]]] = {}
        posibles_rutas = [
            _PKG_DIR / "data" / "train.jsonl",
            _PKG_DIR.parent / "assistant" / "data" / "train.jsonl",
            Path("assistant") / "data" / "train.jsonl",
        ]
        for ruta in posibles_rutas:
            if not ruta.exists():
                continue
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        cat = row.get("categoria", "general")
                        msgs = row.get("messages", [])
                        if len(msgs) >= 3:
                            usuario = msgs[1].get("content", "")
                            resp_raw = msgs[2].get("content", "{}")
                            try:
                                resp_dict = json.loads(resp_raw)
                            except Exception:
                                resp_dict = {"respuesta": resp_raw}
                            if not isinstance(resp_dict, dict):
                                resp_dict = {"respuesta": resp_raw}
                            dataset_by_cat.setdefault(cat, []).append(
                                {"usuario": usuario, "asistente": resp_dict, "categoria": cat}
                            )
                break
            except Exception as exc:
                logger.warning("No se pudo leer %s: %s", ruta, exc)
        return dataset_by_cat

    # ── recuperación semántica (paso 1: pgvector, paso 2: reranking) ──

    def _fetch_candidates(self, role: str, query_vec: Sequence[float], top_k: int) -> List[Dict[str, Any]]:
        literal = _vec_literal(query_vec)
        with closing(self._connect()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, entrada_json, salida_json, texto_indexado,
                       1 - (embedding <=> %s::vector) AS similitud
                FROM ejemplos_few_shot
                WHERE rol_agente = %s AND verificado AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (literal, role, literal, top_k),
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "entrada": r[1], "salida": r[2], "texto_indexado": r[3], "similitud": float(r[4])}
            for r in rows
        ]

    async def asemantic_search(
        self,
        role: str,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
        top_n: int = RERANK_TOP_N,
    ) -> List[Dict[str, Any]]:
        """Top-`top_k` por coseno filtrado por rol -> reranking -> Top-`top_n`."""
        role_key = _normalize_role(role)
        query_vec = await self.embedder.aembed_query(query)
        candidates = await asyncio.to_thread(self._fetch_candidates, role_key, query_vec, top_k)
        if not candidates:
            return []

        try:
            hits = await self.reranker.arerank(query, [c["texto_indexado"] for c in candidates], top_n=top_n)
            ordered = [candidates[h.index] for h in hits]
        except NemoServiceError as exc:
            logger.warning("Reranker no disponible (%s); se usa el orden por similitud coseno.", exc)
            ordered = candidates[:top_n]
        return [{"entrada": c["entrada"], "salida": c["salida"]} for c in ordered]

    def get_few_shots(
        self, role: str, query: Optional[str] = None, limit: int = RERANK_TOP_N
    ) -> List[Dict[str, Any]]:
        """Recupera los ejemplos más relevantes para el rol indicado (ver orden en la clase)."""
        role_key = _normalize_role(role)

        # 1. NeMo Retriever: pgvector + reranking
        if query and query.strip() and self._semantic_ready():
            try:
                found = run_sync(self.asemantic_search(role_key, query, RETRIEVAL_TOP_K, limit))
                if found:
                    return found
            except Exception as exc:  # red, BD o contrato: nunca debe romper el grafo
                logger.warning("Recuperación semántica falló (%s); usando fallbacks deterministas.", exc)

        # 2. Dataset del asistente de catálogo / control
        if role_key in ["control", "asistente_catalogo", "catalogo"] and self._assistant_data:
            q_clean = (query or "").lower()
            categoria_preferida = None
            if any(k in q_clean for k in ["precio", "cuesta", "sube"]):
                categoria_preferida = "precio"
            elif any(k in q_clean for k in ["stock", "llegaron", "quedan", "merma", "echaron"]):
                categoria_preferida = "stock"
            elif any(k in q_clean for k in ["cuanto hay", "cuánto hay", "qué vendo", "inventario", "tengo"]):
                categoria_preferida = "consulta_producto"
            elif any(k in q_clean for k in ["alta", "nuevo", "registra", "agrega"]):
                categoria_preferida = "crear_completo"

            if categoria_preferida and categoria_preferida in self._assistant_data:
                return self._assistant_data[categoria_preferida][:limit]

            mezcla = []
            for c in ["precio", "stock", "consulta_producto", "crear_completo"]:
                if c in self._assistant_data and self._assistant_data[c]:
                    mezcla.append(self._assistant_data[c][0])
            if mezcla:
                return mezcla[:limit]

        # 3. Últimos ejemplos verificados en PostgreSQL (sin consulta semántica)
        if self.db_url:
            try:
                with closing(self._connect()) as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT entrada_json, salida_json FROM ejemplos_few_shot "
                        "WHERE rol_agente = %s AND verificado ORDER BY id DESC LIMIT %s",
                        (role_key, limit),
                    )
                    rows = cur.fetchall()
                if rows:
                    return [{"entrada": r[0], "salida": r[1]} for r in rows]
            except Exception as exc:
                logger.debug("Consulta directa a ejemplos_few_shot falló: %s", exc)

        # 4. Banco semilla determinista en memoria
        return self._seed_store.get(role_key, [])[:limit]

    def format_few_shots_for_prompt(self, role: str, query: Optional[str] = None) -> str:
        """Formatea los ejemplos en una sección de prompt lista para inyectar en el LLM."""
        shots = self.get_few_shots(role=role, query=query, limit=RERANK_TOP_N)
        if not shots:
            return ""

        lines = [f"### EJEMPLOS DE REFERENCIA DE ALTA CALIDAD (FEW-SHOT - ROL: {role.upper()}):"]
        for idx, shot in enumerate(shots, 1):
            lines.append(f"\n--- Ejemplo {idx} ---")
            lines.append(json.dumps(shot, ensure_ascii=False, indent=2))
        lines.append("--- FIN DE EJEMPLOS ---\n")
        return "\n".join(lines)

    # ── esquema, indexación y mantenimiento de embeddings ──

    def ensure_schema(self) -> None:
        """Aplica `sql/001_ejemplos_few_shot.sql` (extensión pgvector, tabla e índices)."""
        if not self.db_url:
            raise RuntimeError("DATABASE_URL no está configurada.")
        with closing(self._connect()) as conn, conn, conn.cursor() as cur:
            cur.execute(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))

    _INSERT_SQL = (
        "INSERT INTO ejemplos_few_shot "
        "(rol_agente, entrada_json, salida_json, texto_indexado, embedding, origen, verificado, huella) "
        "VALUES (%s, %s::jsonb, %s::jsonb, %s, %s::vector, %s, TRUE, %s) "
        "ON CONFLICT (huella) DO NOTHING"
    )

    def _insert_records(self, records: Sequence[FeedbackRecord], vectors: Sequence[Optional[Sequence[float]]]) -> int:
        inserted = 0
        with closing(self._connect()) as conn, conn, conn.cursor() as cur:
            for rec, vec in zip(records, vectors):
                cur.execute(
                    self._INSERT_SQL,
                    (
                        rec.rol_agente,
                        json.dumps(rec.entrada, ensure_ascii=False, default=str),
                        json.dumps(rec.salida, ensure_ascii=False, default=str),
                        rec.texto_indexado(),
                        _vec_literal(vec) if vec else None,
                        rec.origen,
                        rec.huella(),
                    ),
                )
                inserted += cur.rowcount
        return inserted

    def seed_database(self, include_assistant: bool = True) -> int:
        """Indexa el banco semilla (y el dataset del asistente) con embeddings `passage`. Idempotente."""
        self.ensure_schema()
        records: List[FeedbackRecord] = []
        for role, shots in self._seed_store.items():
            for shot in shots:
                entrada, salida = _seed_to_pair(role, shot)
                records.append(FeedbackRecord(rol_agente=role, entrada=entrada, salida=salida, origen="seed"))
        if include_assistant:
            for items in self._assistant_data.values():
                for it in items:
                    records.append(FeedbackRecord(
                        rol_agente="control",
                        entrada={"usuario": it["usuario"]},
                        salida=it["asistente"],
                        origen="assistant_dataset",
                    ))
        vectors = run_sync(self.embedder.aembed_documents([r.texto_indexado() for r in records]))
        return self._insert_records(records, vectors)

    def backfill_embeddings(self, batch_size: int = 32) -> int:
        """Calcula embeddings para filas guardadas sin vector (p. ej. NeMo caído durante el HITL)."""
        updated = 0
        while True:
            with closing(self._connect()) as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id, texto_indexado FROM ejemplos_few_shot "
                    "WHERE embedding IS NULL ORDER BY id LIMIT %s",
                    (batch_size,),
                )
                rows = cur.fetchall()
            if not rows:
                return updated
            vectors = run_sync(self.embedder.aembed_documents([r[1] for r in rows]))
            with closing(self._connect()) as conn, conn, conn.cursor() as cur:
                for (row_id, _), vec in zip(rows, vectors):
                    cur.execute(
                        "UPDATE ejemplos_few_shot SET embedding = %s::vector WHERE id = %s",
                        (_vec_literal(vec), row_id),
                    )
            updated += len(rows)

    # ── Data Flywheel: HITL -> PostgreSQL -> dataset SFT para NeMo Customizer ──

    @staticmethod
    def _buffer_path() -> Path:
        return Path(os.getenv("NEMO_FLYWHEEL_BUFFER", str(_PKG_DIR / "datasets" / "hitl_feedback.jsonl")))

    def record_hitl_feedback(
        self,
        rol_agente: str,
        entrada_json: Dict[str, Any],
        salida_aprobada_json: Dict[str, Any],
        *,
        editado: bool = False,
    ) -> bool:
        """
        Guarda una interacción HITL aprobada (`editado=False`) o corregida por el operador
        (`editado=True`, `edited_payload`) como ejemplo verificado.

        Con DATABASE_URL se inserta en `ejemplos_few_shot` (con embedding si NeMo responde; si no,
        queda sin vector y `backfill_embeddings()` lo completa). Si no hay BD o falla, se anexa a un
        buffer JSONL local para no perder el registro. Nunca lanza excepción al flujo HITL.
        """
        try:
            rec = FeedbackRecord(
                rol_agente=_normalize_role(rol_agente),
                entrada=entrada_json,
                salida=salida_aprobada_json,
                origen="hitl_editado" if editado else "hitl_aprobado",
            )
        except Exception as exc:
            logger.warning("Feedback HITL descartado por formato inválido: %s", exc)
            return False

        if self.db_url:
            try:
                vec: Optional[Sequence[float]] = None
                if self._nemo_available():
                    try:
                        vec = run_sync(self.embedder.aembed_documents([rec.texto_indexado()]))[0]
                    except Exception as exc:
                        logger.warning("Embedding no disponible; se guarda sin vector (%s).", exc)
                self.ensure_schema()
                self._insert_records([rec], [vec])
                return True
            except Exception as exc:
                logger.warning("No se pudo guardar en PostgreSQL (%s); se usa el buffer local.", exc)

        try:
            path = self._buffer_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec.model_dump(), ensure_ascii=False, default=str) + "\n")
            return True
        except OSError as exc:
            logger.warning("No se pudo escribir el buffer de feedback: %s", exc)
            return False

    def _iter_verified_records(
        self, roles: Optional[Sequence[str]], solo_hitl: bool
    ) -> Iterator[FeedbackRecord]:
        wanted = {_normalize_role(r) for r in roles} if roles else None

        def accept(rec: FeedbackRecord) -> bool:
            if wanted is not None and rec.rol_agente not in wanted:
                return False
            return not solo_hitl or rec.origen.startswith("hitl_")

        if self.db_url:
            try:
                with closing(self._connect()) as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT rol_agente, entrada_json, salida_json, origen "
                        "FROM ejemplos_few_shot WHERE verificado ORDER BY id"
                    )
                    rows = cur.fetchall()
                for r in rows:
                    rec = FeedbackRecord(rol_agente=r[0], entrada=r[1], salida=r[2], origen=r[3])
                    if accept(rec):
                        yield rec
            except Exception as exc:
                logger.warning("No se pudo leer ejemplos_few_shot (%s); se exporta solo el buffer local.", exc)

        path = self._buffer_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = FeedbackRecord.model_validate_json(line)
                    except Exception:
                        continue
                    if accept(rec):
                        yield rec

    def iter_sft_records(
        self, roles: Optional[Sequence[str]] = None, solo_hitl: bool = False
    ) -> Iterator[Dict[str, Any]]:
        """Registros verificados en formato conversacional de NeMo Customizer (deduplicados)."""
        seen: set[str] = set()
        for rec in self._iter_verified_records(roles, solo_hitl):
            fingerprint = rec.huella()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            yield {
                "messages": [
                    {"role": "system", "content": ROLE_SYSTEM_PROMPTS.get(rec.rol_agente, _GENERIC_SYSTEM_PROMPT)},
                    {"role": "user", "content": json.dumps(rec.entrada, ensure_ascii=False, default=str)},
                    {"role": "assistant", "content": json.dumps(rec.salida, ensure_ascii=False, default=str)},
                ]
            }

    def export_sft_dataset_jsonl(
        self,
        output_path: str = DEFAULT_SFT_PATH,
        *,
        roles: Optional[Sequence[str]] = None,
        solo_hitl: bool = False,
    ) -> int:
        """Escribe el dataset SFT (una línea JSON por registro) y devuelve cuántos registros exportó."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(out, "w", encoding="utf-8") as f:
            for record in self.iter_sft_records(roles=roles, solo_hitl=solo_hitl):
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        return count


# ────────────────────────────────────────────────────────────────────────────────
# 4. FUNCIONES DE MÓDULO (INSTANCIA COMPARTIDA)
# ────────────────────────────────────────────────────────────────────────────────

_default_retriever: Optional[FewShotRetriever] = None


def get_default_retriever() -> FewShotRetriever:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = FewShotRetriever()
    return _default_retriever


def record_hitl_feedback(
    rol_agente: str,
    entrada_json: Dict[str, Any],
    salida_aprobada_json: Dict[str, Any],
    *,
    editado: bool = False,
) -> bool:
    """Guarda una interacción HITL aprobada/corregida (ver `FewShotRetriever.record_hitl_feedback`)."""
    return get_default_retriever().record_hitl_feedback(
        rol_agente, entrada_json, salida_aprobada_json, editado=editado
    )


def export_sft_dataset_jsonl(
    output_path: str = DEFAULT_SFT_PATH,
    *,
    roles: Optional[Sequence[str]] = None,
    solo_hitl: bool = False,
) -> int:
    """Exporta el dataset SFT para NeMo Customizer (ver `FewShotRetriever.export_sft_dataset_jsonl`)."""
    return get_default_retriever().export_sft_dataset_jsonl(output_path, roles=roles, solo_hitl=solo_hitl)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mantenimiento de ejemplos few-shot (pgvector + NeMo Retriever).")
    parser.add_argument(
        "comando",
        choices=["init-db", "seed", "backfill"],
        help="init-db: crea extensión/tabla/índices | seed: indexa semillas y dataset del asistente | "
             "backfill: calcula embeddings pendientes",
    )
    args = parser.parse_args()
    retr = FewShotRetriever()
    if args.comando == "init-db":
        retr.ensure_schema()
        print("Esquema ejemplos_few_shot listo.")
    elif args.comando == "seed":
        print(f"Ejemplos insertados: {retr.seed_database()}")
    else:
        print(f"Embeddings completados: {retr.backfill_embeddings()}")
