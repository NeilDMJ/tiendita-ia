"""
few_shot_retriever.py — Inyección dinámica de ejemplos Few-Shot.

Soporta:
1. Almacenamiento y consulta en PostgreSQL con pgvector (`ejemplos_few_shot`).
2. Diccionario semilla en memoria determinista como fallback inmediato para 5 roles:
   - `orquestador`: Enrutamiento simple y multi-intención coordinada.
   - `ocr`: Clasificación de tickets (`inversion_inventario` vs `gasto_operativo`).
   - `investigador`: Reporte comercial de 9 secciones obligatorias.
   - `publicista`: Prompt de video vertical 9:16 (5s) + copy persuasivo + CTA.
   - `tutor_ui`: Guía de pago en máximo 2 oraciones accionables referenciando la UI.
"""
from __future__ import annotations

import os
import json
from typing import List, Dict, Any, Optional


from pathlib import Path


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


# ─────────────────────────────────────────────────────────────────────────────
# 2. CLASE FEW-SHOT RETRIEVER CON SOPORTE PGVECTOR + FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

class FewShotRetriever:
    """
    Recuperador dinámico de ejemplos Few-Shot con soporte para:
    1. Base de datos PostgreSQL / pgvector.
    2. Dataset de entrenamiento de assistant (assistant/data/train.jsonl).
    3. Diccionario semilla determinista en memoria (SEED_FEW_SHOTS).
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._seed_store = SEED_FEW_SHOTS
        self._assistant_data = self._load_assistant_dataset()

    def _load_assistant_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        """Carga e indexa por categoría el dataset sintetizado en assistant/data/train.jsonl."""
        dataset_by_cat: Dict[str, List[Dict[str, Any]]] = {}
        posibles_rutas = [
            Path(__file__).resolve().parent.parent / "assistant" / "data" / "train.jsonl",
            Path("assistant") / "data" / "train.jsonl",
            Path("../assistant/data/train.jsonl"),
        ]
        for ruta in posibles_rutas:
            if ruta.exists():
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
                                item = {
                                    "usuario": usuario,
                                    "asistente": resp_dict,
                                    "categoria": cat
                                }
                                dataset_by_cat.setdefault(cat, []).append(item)
                    break
                except Exception:
                    pass
        return dataset_by_cat

    def get_few_shots(self, role: str, query: Optional[str] = None, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Recupera los ejemplos más relevantes para el rol indicado.
        Si role es 'control', 'asistente_catalogo' o 'catalogo', consulta prioritariamente el dataset de assistant.
        """
        role_key = role.lower().strip()

        # Si el rol es el asistente de catálogo o control, consultar el dataset especializado
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

            # Si no hay categoría clara, tomar una mezcla representativa
            mezcla = []
            for c in ["precio", "stock", "consulta_producto", "crear_completo"]:
                if c in self._assistant_data and self._assistant_data[c]:
                    mezcla.append(self._assistant_data[c][0])
            if mezcla:
                return mezcla[:limit]

        # Intento de consulta en base de datos si existe DATABASE_URL
        if self.db_url:
            try:
                import psycopg2
                with psycopg2.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT ejemplo_json FROM ejemplos_few_shot WHERE rol = %s LIMIT %s;",
                            (role_key, limit)
                        )
                        rows = cur.fetchall()
                        if rows:
                            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]
            except Exception:
                pass

        # Fallback determinista en memoria
        examples = self._seed_store.get(role_key, [])
        return examples[:limit]

    def format_few_shots_for_prompt(self, role: str, query: Optional[str] = None) -> str:
        """
        Formatea los ejemplos en una sección de prompt lista para inyectar en LLM.
        """
        shots = self.get_few_shots(role=role, query=query, limit=2)
        if not shots:
            return ""

        lines = [f"### EJEMPLOS DE REFERENCIA DE ALTA CALIDAD (FEW-SHOT - ROL: {role.upper()}):"]
        for idx, shot in enumerate(shots, 1):
            lines.append(f"\n--- Ejemplo {idx} ---")
            lines.append(json.dumps(shot, ensure_ascii=False, indent=2))
        lines.append("--- FIN DE EJEMPLOS ---\n")
        return "\n".join(lines)
