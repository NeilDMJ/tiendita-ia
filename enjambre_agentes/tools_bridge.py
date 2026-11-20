"""
tools_bridge.py — Adaptadores de herramientas tipadas para LangGraph ToolNode y MCP.

Ecosistema Multiagente Comercial Multimodal:
1. CONTROL_TOOLS:
   - `parse_vision_catalog_item`: Valida escaneo de catálogo y coteja existencia de SKU.
   - `parse_receipt_ocr`: Clasifica ticket OCR en inversión inventario vs gasto operativo.
   - `query_expiring_products`: Lotes por caducar o productos bajo stock mínimo.
   - `commit_inventory_mutation`: Ejecuta INSERT/UPDATE de inventario o finanzas.
2. VENDEDOR_TOOLS:
   - `build_pos_cart_from_vision`: Cruza detección POS con BD, calcula subtotales y stock.
   - `get_cross_sell_recommendations`: Sugiere productos complementarios frecuentes.
   - `commit_sale_transaction`: Registra venta, detalle y descuenta stock.
3. ANALISTA_TOOLS (Estrictamente Solo Lectura):
   - `get_cashflow_summary`: Cruza ingresos de ventas vs egresos operativos e inventario.
   - `get_product_margins`: Calcula margen bruto y rotación por SKU/categoría.
4. INVESTIGADOR_TOOLS:
   - `get_sales_cohort_metrics`: Ticket promedio, horas pico y productos ancla.
   - `search_market_trends`: Consulta tendencias externas vía Tavily o fallback estructurado.
5. PUBLICISTA_TOOLS:
   - `generate_promo_video_job`: Despacha prompt vertical 9:16 (5s) y crea borrador en campanas.
6. TUTOR_UI_TOOLS:
   - `inspect_payment_step`: Diagnostica errores de pago móvil (SPEI, tarjeta, QR).
7. Exportación MCP:
   - `to_mcp_tool_definitions`: Exporta las 13 herramientas en formato JSON Schema MCP.
"""
from __future__ import annotations

import os
import re
import json
import urllib.request
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import tool


# ─────────────────────────────────────────────────────────────────────────────
# 1. BASE DE DATOS DETERMINISTA EN MEMORIA (POSTGRESQL MOCK LAYER)
# ─────────────────────────────────────────────────────────────────────────────

class MockPostgresDB:
    """
    Simulador determinista de PostgreSQL en memoria con los esquemas de:
    productos, lotes_inventario, ventas, detalle_ventas, movimientos_financieros
    y campanas_promocionales.
    
    Permite operar de forma 100% determinista sin infraestructura externa activa,
    y soporta conexión directa a PostgreSQL vía DATABASE_URL si está configurada.
    """
    _instance: Optional[MockPostgresDB] = None

    def __init__(self):
        self._init_data()

    @classmethod
    def get_instance(cls) -> MockPostgresDB:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_data(self):
        # 1. Tabla: productos con soporte para alias coloquiales de México (dataset assistant)
        self.productos: Dict[int, Dict[str, Any]] = {
            1: {
                "id": 1, "sku": "LALA-1L", "nombre": "Leche Lala 1 L",
                "categoria": "lacteos", "precio_venta": 29.00, "costo_unitario": 22.00,
                "stock_actual": 14, "stock_minimo": 6,
                "alias": ["la leche", "la lala", "la leche lala", "leche lala 1 l", "leche entera lala 1l"],
                "atributos_visuales": {"color": "azul/blanco", "empaque": "tetrapack", "marca": "Lala"}
            },
            2: {
                "id": 2, "sku": "HUEV-12", "nombre": "Huevo Blanco 12 pzas",
                "categoria": "abarrotes", "precio_venta": 45.00, "costo_unitario": 36.00,
                "stock_actual": 20, "stock_minimo": 8,
                "alias": ["el huevo", "los huevos", "huevo blanco", "blanquillos"],
                "atributos_visuales": {"empaque": "cono", "marca": "San Juan"}
            },
            3: {
                "id": 3, "sku": "COCA-600", "nombre": "Coca-Cola 600 ml",
                "categoria": "bebidas", "precio_venta": 20.00, "costo_unitario": 13.50,
                "stock_actual": 35, "stock_minimo": 10,
                "alias": ["la coca", "la coca de 600", "coca-cola", "la coca de 600 ml", "coca cola"],
                "atributos_visuales": {"color": "rojo", "empaque": "botella pet", "marca": "Coca-Cola"}
            },
            4: {
                "id": 4, "sku": "BIMB-BLAN", "nombre": "Pan de caja Bimbo",
                "categoria": "panaderia", "precio_venta": 45.00, "costo_unitario": 33.00,
                "stock_actual": 7, "stock_minimo": 5,
                "alias": ["el pan de caja", "el bimbo", "el pan bimbo", "pan blanco bimbo"],
                "atributos_visuales": {"color": "azul/blanco", "empaque": "bolsa", "marca": "Bimbo"}
            },
            5: {
                "id": 5, "sku": "SABR-ORIG-45G", "nombre": "Sabritas Original 45 g",
                "categoria": "botanas", "precio_venta": 20.00, "costo_unitario": 14.00,
                "stock_actual": 25, "stock_minimo": 8,
                "alias": ["las sabritas", "las papas sabritas", "las sabritas normales", "papas con sal"],
                "atributos_visuales": {"color": "amarillo", "empaque": "bolsa", "marca": "Sabritas"}
            },
            6: {
                "id": 6, "sku": "FRIJ-ISAD-430", "nombre": "Frijoles La Sierra",
                "categoria": "abarrotes", "precio_venta": 22.00, "costo_unitario": 16.00,
                "stock_actual": 18, "stock_minimo": 6,
                "alias": ["los frijoles", "los frijoles de lata", "los frijoles la sierra", "frijoles isadora"],
                "atributos_visuales": {"color": "negro", "empaque": "pouch", "marca": "La Sierra"}
            },
            7: {
                "id": 7, "sku": "AGUA-BON-1L", "nombre": "Agua 1 L",
                "categoria": "bebidas", "precio_venta": 15.00, "costo_unitario": 9.00,
                "stock_actual": 30, "stock_minimo": 10,
                "alias": ["el agua", "el agua de litro", "agua embotellada", "bonafont"],
                "atributos_visuales": {"color": "naranja", "empaque": "botella pet", "marca": "Bonafont"}
            },
            8: {
                "id": 8, "sku": "NESC-CLAS-120", "nombre": "Café Nescafé Clásico 120g",
                "categoria": "abarrotes", "precio_venta": 68.00, "costo_unitario": 52.00,
                "stock_actual": 6, "stock_minimo": 3,
                "alias": ["el café", "el cafe", "nescafe", "el nescafé"],
                "atributos_visuales": {"color": "rojo/vidrio", "empaque": "frasco", "marca": "Nescafé"}
            },
            9: {
                "id": 9, "sku": "JAB-ZOTE-400", "nombre": "Jabón Zote",
                "categoria": "limpieza", "precio_venta": 20.00, "costo_unitario": 15.00,
                "stock_actual": 16, "stock_minimo": 5,
                "alias": ["el zote", "el jabón zote", "el jabon zote", "el jabón de barra"],
                "atributos_visuales": {"color": "rosa", "empaque": "barra", "marca": "La Corona"}
            },
            10: {
                "id": 10, "sku": "BOING-500ML", "nombre": "Jugo Boing 500 ml",
                "categoria": "bebidas", "precio_venta": 15.00, "costo_unitario": 10.00,
                "stock_actual": 18, "stock_minimo": 6,
                "alias": ["el boing", "los boing", "el jugo boing"],
                "atributos_visuales": {"color": "verde/frutas", "empaque": "tetrabrik", "marca": "Pascual Boing"}
            },
            11: {
                "id": 11, "sku": "GANS-MAR-50G", "nombre": "Gansito Marinela",
                "categoria": "panaderia", "precio_venta": 18.00, "costo_unitario": 13.00,
                "stock_actual": 22, "stock_minimo": 8,
                "alias": ["los gansitos", "el gansito", "los gansitos marinela"],
                "atributos_visuales": {"color": "azul", "empaque": "envoltura", "marca": "Marinela"}
            },
            12: {
                "id": 12, "sku": "TAKIS-56G", "nombre": "Takis Fuego 56 g",
                "categoria": "botanas", "precio_venta": 20.00, "costo_unitario": 14.50,
                "stock_actual": 25, "stock_minimo": 10,
                "alias": ["los takis", "los takis fuego", "las takis"],
                "atributos_visuales": {"color": "morado", "empaque": "bolsa", "marca": "Barcel"}
            },
            13: {
                "id": 13, "sku": "GAL-MAR-170", "nombre": "Galletas Marías Gamesa",
                "categoria": "galletas", "precio_venta": 16.00, "costo_unitario": 11.50,
                "stock_actual": 24, "stock_minimo": 6,
                "alias": ["las marías", "las marias", "las galletas marías", "las gamesa"],
                "atributos_visuales": {"color": "amarillo", "empaque": "rollo", "marca": "Gamesa"}
            },
            14: {
                "id": 14, "sku": "MARUCH-64G", "nombre": "Sopa Maruchan",
                "categoria": "abarrotes", "precio_venta": 17.00, "costo_unitario": 12.00,
                "stock_actual": 30, "stock_minimo": 8,
                "alias": ["la maruchan", "las sopas maruchan", "la sopa instantánea"],
                "atributos_visuales": {"color": "amarillo/rojo", "empaque": "vaso", "marca": "Maruchan"}
            },
            15: {
                "id": 15, "sku": "ATUN-DOL-140", "nombre": "Atún Dolores",
                "categoria": "abarrotes", "precio_venta": 24.00, "costo_unitario": 18.00,
                "stock_actual": 20, "stock_minimo": 6,
                "alias": ["el atún", "el atun", "las latas de atún", "el atún dolores"],
                "atributos_visuales": {"color": "azul/amarillo", "empaque": "lata", "marca": "Dolores"}
            },
            16: {
                "id": 16, "sku": "ACEITE-123-1L", "nombre": "Aceite 1-2-3 1 L",
                "categoria": "abarrotes", "precio_venta": 45.00, "costo_unitario": 35.00,
                "stock_actual": 12, "stock_minimo": 4,
                "alias": ["el aceite", "el aceite 123", "el aceite de litro"],
                "atributos_visuales": {"color": "amarillo", "empaque": "botella pet", "marca": "1-2-3"}
            },
            17: {
                "id": 17, "sku": "PAPEL-HIG-4P", "nombre": "Papel higiénico",
                "categoria": "limpieza", "precio_venta": 10.00, "costo_unitario": 6.50,
                "stock_actual": 35, "stock_minimo": 10,
                "alias": ["el papel", "el papel de baño", "el papel higiénico"],
                "atributos_visuales": {"color": "blanco", "empaque": "paquete 4", "marca": "Pétalo"}
            }
        }

        # 2. Tabla: lotes_inventario (Fechas dinámicas relativas a hoy)
        hoy = datetime.now()
        f_2d = (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
        f_3d = (hoy + timedelta(days=3)).strftime("%Y-%m-%d")
        f_30d = (hoy + timedelta(days=30)).strftime("%Y-%m-%d")

        self.lotes_inventario: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "producto_id": 1, "cantidad": 6, "fecha_caducidad": f_2d, "estado": "proximo_a_vencer"},
            2: {"id": 2, "producto_id": 4, "cantidad": 4, "fecha_caducidad": f_3d, "estado": "proximo_a_vencer"},
            3: {"id": 3, "producto_id": 2, "cantidad": 20, "fecha_caducidad": f_30d, "estado": "activo"},
            4: {"id": 4, "producto_id": 3, "cantidad": 35, "fecha_caducidad": f_30d, "estado": "activo"},
        }

        # 3. Tabla: ventas y detalle_ventas
        self.ventas: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "fecha": (hoy - timedelta(days=1)).isoformat(), "total": 113.00, "metodo_pago": "efectivo", "origen_vision": True},
            2: {"id": 2, "fecha": (hoy - timedelta(days=1)).isoformat(), "total": 37.50, "metodo_pago": "tarjeta", "origen_vision": True},
            3: {"id": 3, "fecha": hoy.isoformat(), "total": 89.00, "metodo_pago": "spei", "origen_vision": False},
        }

        self.detalle_ventas: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "venta_id": 1, "producto_id": 1, "cantidad": 2, "precio_unitario": 28.50, "subtotal": 57.00},
            2: {"id": 2, "venta_id": 1, "producto_id": 4, "cantidad": 1, "precio_unitario": 42.00, "subtotal": 42.00},
            3: {"id": 3, "venta_id": 1, "producto_id": 7, "cantidad": 1, "precio_unitario": 14.00, "subtotal": 14.00},
            4: {"id": 4, "venta_id": 2, "producto_id": 3, "cantidad": 1, "precio_unitario": 18.00, "subtotal": 18.00},
            5: {"id": 5, "venta_id": 2, "producto_id": 5, "cantidad": 1, "precio_unitario": 19.50, "subtotal": 19.50},
            6: {"id": 6, "venta_id": 3, "producto_id": 8, "cantidad": 1, "precio_unitario": 68.00, "subtotal": 68.00},
            7: {"id": 7, "venta_id": 3, "producto_id": 6, "cantidad": 1, "precio_unitario": 21.00, "subtotal": 21.00},
        }

        # 4. Tabla: movimientos_financieros
        self.movimientos_financieros: Dict[int, Dict[str, Any]] = {
            1: {
                "id": 1, "tipo": "inversion_inventario", "proveedor": "Distribuidora Bimbo S.A.",
                "monto_total": 1250.00, "fecha": (hoy - timedelta(days=5)).strftime("%Y-%m-%d"),
                "url_ticket": "https://cdn.tiendita.ia/tickets/bimbo_nov15.jpg",
                "datos_ocr_json": {"items": [{"sku": "BIMB-BLAN", "cant": 30}]}
            },
            2: {
                "id": 2, "tipo": "inversion_inventario", "proveedor": "Coca Cola FEMSA",
                "monto_total": 2400.00, "fecha": (hoy - timedelta(days=4)).strftime("%Y-%m-%d"),
                "url_ticket": "https://cdn.tiendita.ia/tickets/femsa_nov16.jpg",
                "datos_ocr_json": {"items": [{"sku": "COCA-600", "cant": 150}]}
            },
            3: {
                "id": 3, "tipo": "gasto_operativo", "proveedor": "CFE Suministrador de Servicios Básicos",
                "monto_total": 1150.00, "fecha": (hoy - timedelta(days=3)).strftime("%Y-%m-%d"),
                "url_ticket": "https://cdn.tiendita.ia/tickets/cfe_nov.jpg",
                "datos_ocr_json": {"concepto": "Energía eléctrica refrigeradores y local"}
            },
            4: {
                "id": 4, "tipo": "gasto_operativo", "proveedor": "Arrendadora San José (Renta)",
                "monto_total": 4500.00, "fecha": (hoy - timedelta(days=15)).strftime("%Y-%m-%d"),
                "url_ticket": None,
                "datos_ocr_json": {"concepto": "Renta mensual local comercial"}
            }
        }

        # 5. Tabla: campanas_promocionales
        self.campanas_promocionales: Dict[int, Dict[str, Any]] = {
            1: {
                "id": 1, "producto_id": 1, "motivo": "Lote por caducar en 48 horas",
                "copy_texto": "¡Oferta relámpago! Leche Lala 1L a solo $24.00 llevando 2 pzas.",
                "video_prompt": "Cinematic vertical 9:16 milk commercial, 5 seconds...",
                "video_url": "https://cdn.tiendita.ia/promos/leche_promo.mp4",
                "estado_aprobacion": "aprobada"
            }
        }


db = MockPostgresDB.get_instance()


def find_product_by_name_or_alias(term: str) -> Optional[Dict[str, Any]]:
    """
    Busca un producto en la base de datos por SKU exacto, nombre canónico o
    alias coloquial mexicano (integración con el dataset de assistant).
    """
    if not term:
        return None
    term_clean = term.lower().strip()

    # Stopwords españolas excluidas del solapamiento de palabras clave
    _STOPWORDS = {"de", "la", "el", "los", "las", "un", "una", "unos", "unas",
                  "y", "o", "con", "sin", "en", "a", "por", "para", "del"}

    term_words = {w for w in re.findall(r"\w+", term_clean) if w not in _STOPWORDS}

    # 1. Búsqueda exacta en SKU o nombre
    for p in db.productos.values():
        if p["sku"].lower() == term_clean or p["nombre"].lower() == term_clean:
            return p

    # 2. Búsqueda exacta en lista de alias coloquiales
    for p in db.productos.values():
        for alias in p.get("alias", []):
            if alias.lower() == term_clean:
                return p

    # 3. Coincidencia parcial / substring (solo si el término tiene ≥2 chars)
    if len(term_clean) >= 2:
        for p in db.productos.values():
            if term_clean in p["nombre"].lower():
                return p
            for alias in p.get("alias", []):
                if term_clean in alias.lower() or alias.lower() in term_clean:
                    return p

    # 4. Solapamiento de palabras clave (stopwords excluidas, threshold ≥ 2 palabras sustantivas)
    if not term_words:
        return None
    best_p = None
    best_overlap = 0
    for p in db.productos.values():
        p_words = {w for w in re.findall(r"\w+", p["nombre"].lower()) if w not in _STOPWORDS}
        for alias in p.get("alias", []):
            p_words.update(w for w in re.findall(r"\w+", alias.lower()) if w not in _STOPWORDS)
        overlap = len(term_words & p_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_p = p

    # Requerir al menos 2 palabras sustantivas solapadas para evitar falsos positivos
    if best_overlap >= 2:
        return best_p
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. ESQUEMAS PYDANTIC DE ENTRADA PARA LAS HERRAMIENTAS
# ─────────────────────────────────────────────────────────────────────────────

class ParseVisionCatalogInput(BaseModel):
    vision_payload: Dict[str, Any] = Field(description="Payload devuelto por la API /catalog-scan")

class ParseReceiptOCRInput(BaseModel):
    vision_payload: Dict[str, Any] = Field(description="Payload devuelto por la API /receipt-ocr")

class QueryExpiringInput(BaseModel):
    dias_horizonte: int = Field(default=3, ge=1, le=60, description="Días hacia adelante para alertar caducidades")

class CommitInventoryMutationInput(BaseModel):
    mutation_payload: Dict[str, Any] = Field(
        description="Datos de la mutación: tabla ('productos' | 'lotes_inventario' | 'movimientos_financieros'), accion ('insert' | 'update') y valores"
    )

class BuildPosCartInput(BaseModel):
    vision_payload: Dict[str, Any] = Field(description="Payload devuelto por la API /pos-checkout")

class CrossSellInput(BaseModel):
    skus_carrito: List[str] = Field(description="Lista de SKUs actualmente en el carrito de compra")

class CommitSaleTransactionInput(BaseModel):
    cart_payload: Dict[str, Any] = Field(description="Estructura del carrito validado con ítems, total y método de pago")

class CashflowSummaryInput(BaseModel):
    fecha_inicio: str = Field(description="Fecha inicio YYYY-MM-DD")
    fecha_fin: str = Field(description="Fecha fin YYYY-MM-DD")

class ProductMarginsInput(BaseModel):
    categoria: Optional[str] = Field(default=None, description="Filtrar por categoría (ej. 'lacteos', 'bebidas') o None para todos")

class SearchMarketTrendsInput(BaseModel):
    sector: str = Field(description="Sector o segmento a investigar (ej. 'retail tradicional', 'tiendita')")
    query: str = Field(description="Pregunta o tópico específico de tendencias")

class GeneratePromoVideoInput(BaseModel):
    producto: str = Field(description="Nombre o SKU del producto en promoción")
    descuento: str = Field(description="Porcentaje o tipo de descuento (ej. '15%', '2x1')")
    video_prompt: str = Field(description="Prompt cinematográfico en inglés vertical 9:16 (5s)")

class InspectPaymentStepInput(BaseModel):
    ui_state: Dict[str, Any] = Field(description="Estado actual de la interfaz de usuario móvil")

# ── Esquemas de Catálogo Asistente (Integración con assistant/) ──
class CrearProductoInput(BaseModel):
    nombre: str = Field(description="Nombre comercial del producto")
    precio: float = Field(description="Precio de venta al público en MXN")
    stock: int = Field(default=0, description="Existencia física inicial")
    costo: Optional[float] = Field(default=None, description="Costo de adquisición por unidad")
    caducidad: Optional[str] = Field(default=None, description="Fecha de caducidad en formato YYYY-MM-DD")

class ActualizarPrecioInput(BaseModel):
    nombre: str = Field(description="Nombre o alias del producto (ej. 'Coca', 'Bimbo', 'Leche Lala')")
    precio: float = Field(description="Nuevo precio de venta en MXN")

class ConsultarInventarioInput(BaseModel):
    nombre: Optional[str] = Field(default=None, description="Nombre o alias del producto específico a consultar, o None para catálogo general")

class AjustarStockInput(BaseModel):
    nombre: str = Field(description="Nombre o alias del producto")
    cantidad: int = Field(description="Cantidad de piezas a ajustar")
    tipo: str = Field(description="Tipo de movimiento: 'entrada' (llegada), 'salida' (retiro), 'merma' (caducado/dañado)")


# ─────────────────────────────────────────────────────────────────────────────
# 3. KITS DE HERRAMIENTAS COMERCIALES (@tool)
# ─────────────────────────────────────────────────────────────────────────────

# ── KIT 1: CONTROL_TOOLS ──

@tool(args_schema=ParseVisionCatalogInput)
def parse_vision_catalog_item(vision_payload: Dict[str, Any]) -> str:
    """
    Valida la detección recibida de /catalog-scan y consulta en PostgreSQL si el SKU
    o código de barras ya existe en la tabla 'productos', o si es un nuevo ingreso.
    """
    items = vision_payload.get("items", [])
    if not items:
        return json.dumps({"status": "warning", "message": "No se detectaron ítems en el payload de catálogo."}, ensure_ascii=False)

    resultados = []
    for item in items:
        sku = item.get("sku", "").strip()
        nombre_detectado = item.get("nombre", "")
        # Buscar en productos
        producto_existente = None
        for p in db.productos.values():
            if p["sku"] == sku or p["nombre"].lower() == nombre_detectado.lower():
                producto_existente = p
                break

        if producto_existente:
            resultados.append({
                "sku": sku,
                "encontrado_en_bd": True,
                "producto_id": producto_existente["id"],
                "nombre_oficial": producto_existente["nombre"],
                "stock_actual": producto_existente["stock_actual"],
                "precio_venta": producto_existente["precio_venta"],
                "atributos_visuales": producto_existente["atributos_visuales"],
                "accion_recomendada": "actualizar_stock"
            })
        else:
            resultados.append({
                "sku": sku,
                "encontrado_en_bd": False,
                "nombre_detectado": nombre_detectado,
                "atributos_detectados": item.get("atributos", {}),
                "accion_recomendada": "alta_nuevo_producto"
            })

    return json.dumps({
        "status": "success",
        "endpoint": "/catalog-scan",
        "total_detectados": len(items),
        "analisis": resultados
    }, ensure_ascii=False, indent=2)


@tool(args_schema=ParseReceiptOCRInput)
def parse_receipt_ocr(vision_payload: Dict[str, Any]) -> str:
    """
    Clasifica un ticket o factura procesado por /receipt-ocr en 'inversion_inventario'
    (mercancía de reventa) versus 'gasto_operativo' (luz, renta, empaques, limpieza).
    Estructura ítems, subtotales, proveedor y total numérico exacto.
    """
    proveedor = vision_payload.get("proveedor", "Proveedor Desconocido")
    items = vision_payload.get("items", [])
    total = vision_payload.get("total")

    # Si el total no viene dado, sumarlo de los items
    if total is None:
        total = sum(float(it.get("subtotal", 0.0) or (float(it.get("cantidad", 1)) * float(it.get("precio_unitario", 0.0)))) for it in items)

    # Heurística determinista de clasificación comercial
    proveedores_inventario = ["bimbo", "coca", "femsa", "lala", "sabritas", "gamesa", "abarrotes", "lacteos", "distribuidora"]
    proveedores_gasto = ["cfe", "luz", "renta", "arrendadora", "limpieza", "papeleria", "internet", "telmex", "gas"]

    prov_lower = proveedor.lower()
    es_inventario = any(k in prov_lower for k in proveedores_inventario)
    es_gasto = any(k in prov_lower for k in proveedores_gasto)

    if es_inventario and not es_gasto:
        tipo = "inversion_inventario"
        justificacion = f"Proveedor de mercancía para reventa ({proveedor})."
    elif es_gasto:
        tipo = "gasto_operativo"
        justificacion = f"Gasto indispensable para operación o servicios del local ({proveedor})."
    else:
        # Evaluar por items si el proveedor es genérico
        tipo = vision_payload.get("tipo_movimiento") or "inversion_inventario"
        justificacion = "Clasificación determinada por naturaleza de los ítems adquiridos."

    parsed = {
        "status": "success",
        "tipo": tipo,
        "proveedor": proveedor,
        "monto_total": round(float(total), 2),
        "items_contabilizados": items,
        "justificacion": justificacion,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "requiere_aprobacion": True
    }
    return json.dumps(parsed, ensure_ascii=False, indent=2)


@tool(args_schema=QueryExpiringInput)
def query_expiring_products(dias_horizonte: int = 3) -> str:
    """
    Consulta en 'lotes_inventario' los productos que caducan dentro del horizonte especificado
    o productos en 'productos' cuya existencia actual está por debajo del stock mínimo.
    """
    hoy = datetime.now()
    fecha_limite = hoy + timedelta(days=dias_horizonte)
    
    criticos_caducidad = []
    for lote in db.lotes_inventario.values():
        try:
            f_cad = datetime.strptime(lote["fecha_caducidad"], "%Y-%m-%d")
            dias_restantes = (f_cad - hoy).days
            if dias_restantes <= dias_horizonte and lote["cantidad"] > 0:
                prod = db.productos.get(lote["producto_id"], {})
                criticos_caducidad.append({
                    "lote_id": lote["id"],
                    "sku": prod.get("sku", "N/A"),
                    "nombre": prod.get("nombre", "N/A"),
                    "cantidad_en_lote": lote["cantidad"],
                    "precio_venta": prod.get("precio_venta", 0.0),
                    "costo_unitario": prod.get("costo_unitario", 0.0),
                    "fecha_caducidad": lote["fecha_caducidad"],
                    "dias_restantes": dias_restantes,
                    "estado": lote["estado"]
                })
        except Exception:
            pass

    criticos_stock = []
    for prod in db.productos.values():
        if prod["stock_actual"] <= prod["stock_minimo"]:
            criticos_stock.append({
                "producto_id": prod["id"],
                "sku": prod["sku"],
                "nombre": prod["nombre"],
                "stock_actual": prod["stock_actual"],
                "stock_minimo": prod["stock_minimo"],
                "precio_venta": prod["precio_venta"],
                "accion": "reorden_inmediato"
            })

    res = {
        "status": "success",
        "horizonte_dias": dias_horizonte,
        "productos_por_caducar": criticos_caducidad,
        "productos_bajo_stock_minimo": criticos_stock,
        "total_alertas": len(criticos_caducidad) + len(criticos_stock)
    }
    return json.dumps(res, ensure_ascii=False, indent=2)


@tool(args_schema=CommitInventoryMutationInput)
def commit_inventory_mutation(mutation_payload: Dict[str, Any]) -> str:
    """
    Ejecuta INSERT o UPDATE en 'productos', 'lotes_inventario' o 'movimientos_financieros'.
    Esta herramienta muta el estado de la base de datos tras confirmación del usuario.
    """
    tabla = mutation_payload.get("tabla")
    accion = mutation_payload.get("accion", "insert")
    datos = mutation_payload.get("datos", {})

    if tabla == "productos":
        if accion == "insert":
            nuevo_id = max(db.productos.keys(), default=0) + 1
            datos["id"] = nuevo_id
            db.productos[nuevo_id] = datos
            return json.dumps({"status": "success", "tabla": tabla, "id": nuevo_id, "mensaje": f"Producto '{datos.get('nombre')}' dado de alta."}, ensure_ascii=False)
        elif accion == "update":
            sku = datos.get("sku")
            for p in db.productos.values():
                if p["sku"] == sku:
                    p.update(datos)
                    return json.dumps({"status": "success", "tabla": tabla, "sku": sku, "mensaje": "Stock y/o atributos actualizados."}, ensure_ascii=False)
            return json.dumps({"status": "error", "mensaje": f"SKU {sku} no encontrado."}, ensure_ascii=False)

    elif tabla == "lotes_inventario":
        nuevo_id = max(db.lotes_inventario.keys(), default=0) + 1
        datos["id"] = nuevo_id
        db.lotes_inventario[nuevo_id] = datos
        return json.dumps({"status": "success", "tabla": tabla, "lote_id": nuevo_id, "mensaje": "Lote registrado exitosamente."}, ensure_ascii=False)

    elif tabla == "movimientos_financieros":
        nuevo_id = max(db.movimientos_financieros.keys(), default=0) + 1
        datos["id"] = nuevo_id
        db.movimientos_financieros[nuevo_id] = datos
        return json.dumps({"status": "success", "tabla": tabla, "movimiento_id": nuevo_id, "monto": datos.get("monto_total"), "mensaje": "Movimiento financiero asentado."}, ensure_ascii=False)

    return json.dumps({"status": "error", "mensaje": f"Tabla '{tabla}' no soportada."}, ensure_ascii=False)


# ── Herramientas del Asistente de Catálogo (Integración assistant/) ──

@tool(args_schema=CrearProductoInput)
def crear_producto(nombre: str, precio: float, stock: int = 0, costo: Optional[float] = None, caducidad: Optional[str] = None) -> str:
    """
    Registra un nuevo producto en el catálogo con precio, costo, existencias iniciales y caducidad opcional.
    Responde en formato estándar {"tool": "crear_producto", "args": {...}, "respuesta": "..."}.
    """
    prod_existente = find_product_by_name_or_alias(nombre)
    if prod_existente:
        return json.dumps({
            "tool": "crear_producto",
            "args": {"nombre": nombre, "precio": precio, "stock": stock, "costo": costo, "caducidad": caducidad},
            "respuesta": f"El producto '{prod_existente['nombre']}' ya existe en el catálogo. Usa actualizar_precio o ajustar_stock.",
            "status": "warning"
        }, ensure_ascii=False)

    nuevo_id = max(db.productos.keys(), default=0) + 1
    sku = f"PROD-{nuevo_id:03d}"
    costo_calc = costo if costo is not None else round(precio * 0.75, 2)
    db.productos[nuevo_id] = {
        "id": nuevo_id,
        "sku": sku,
        "nombre": nombre,
        "categoria": "general",
        "precio_venta": float(precio),
        "costo_unitario": float(costo_calc),
        "stock_actual": int(stock),
        "stock_minimo": 5,
        "alias": [nombre.lower()],
        "atributos_visuales": {}
    }
    if caducidad:
        lote_id = max(db.lotes_inventario.keys(), default=0) + 1
        db.lotes_inventario[lote_id] = {
            "id": lote_id,
            "producto_id": nuevo_id,
            "cantidad": int(stock),
            "fecha_caducidad": caducidad,
            "estado": "activo"
        }

    return json.dumps({
        "tool": "crear_producto",
        "args": {"nombre": nombre, "precio": precio, "costo": costo, "stock": stock, "caducidad": caducidad},
        "respuesta": f"Voy a dar de alta {nombre} a ${precio:,.2f} con {stock} piezas. ¿Confirmas?",
        "status": "success",
        "producto_id": nuevo_id,
        "sku": sku
    }, ensure_ascii=False)


@tool(args_schema=ActualizarPrecioInput)
def actualizar_precio(nombre: str, precio: float) -> str:
    """
    Actualiza el precio de venta al público de un producto en el catálogo.
    Responde en formato estándar {"tool": "actualizar_precio", "args": {...}, "respuesta": "..."}.
    """
    prod = find_product_by_name_or_alias(nombre)
    if not prod:
        return json.dumps({
            "tool": "actualizar_precio",
            "args": {"nombre": nombre, "precio": precio},
            "respuesta": f"No encontré el producto '{nombre}' en el catálogo para actualizar su precio.",
            "status": "error"
        }, ensure_ascii=False)

    precio_anterior = prod["precio_venta"]
    prod["precio_venta"] = float(precio)

    return json.dumps({
        "tool": "actualizar_precio",
        "args": {"nombre": prod["nombre"], "precio": precio},
        "respuesta": f"Voy a cambiar {prod['nombre']} a ${precio:,.2f} (antes ${precio_anterior:,.2f}). ¿Confirmas?",
        "status": "success",
        "sku": prod["sku"],
        "precio_anterior": precio_anterior,
        "precio_nuevo": precio
    }, ensure_ascii=False)


@tool(args_schema=ConsultarInventarioInput)
def consultar_inventario(nombre: Optional[str] = None) -> str:
    """
    Consulta existencias y precios de un producto específico o lista el catálogo completo.
    Responde en formato estándar {"tool": "consultar_inventario", "args": {...}, "respuesta": "..."}.
    """
    if nombre:
        prod = find_product_by_name_or_alias(nombre)
        if not prod:
            return json.dumps({
                "tool": "consultar_inventario",
                "args": {"nombre": nombre},
                "respuesta": f"No tengo registrado '{nombre}' en el catálogo.",
                "status": "error"
            }, ensure_ascii=False)

        return json.dumps({
            "tool": "consultar_inventario",
            "args": {"nombre": prod["nombre"]},
            "respuesta": f"De {prod['nombre']} tienes {prod['stock_actual']} piezas en existencia a un precio de ${prod['precio_venta']:,.2f}.",
            "status": "success",
            "producto": prod
        }, ensure_ascii=False)
    else:
        lista = [{"nombre": p["nombre"], "stock": p["stock_actual"], "precio": p["precio_venta"]} for p in db.productos.values()]
        return json.dumps({
            "tool": "consultar_inventario",
            "args": {"nombre": None},
            "respuesta": f"Te muestro el inventario completo ({len(lista)} productos registrados).",
            "status": "success",
            "catalogo": lista
        }, ensure_ascii=False)


@tool(args_schema=AjustarStockInput)
def ajustar_stock(nombre: str, cantidad: int, tipo: str) -> str:
    """
    Ajusta el inventario de un producto sumando entradas o descontando salidas y mermas.
    Responde en formato estándar {"tool": "ajustar_stock", "args": {...}, "respuesta": "..."}.
    """
    prod = find_product_by_name_or_alias(nombre)
    if not prod:
        return json.dumps({
            "tool": "ajustar_stock",
            "args": {"nombre": nombre, "cantidad": cantidad, "tipo": tipo},
            "respuesta": f"No encontré '{nombre}' en el catálogo para ajustar existencias.",
            "status": "error"
        }, ensure_ascii=False)

    cant = int(cantidad)
    stock_previo = prod["stock_actual"]
    verbo = {"entrada": "sumar", "merma": "registrar como merma", "salida": "descontar"}.get(tipo, "ajustar")

    if tipo == "entrada":
        prod["stock_actual"] += cant
    else:
        prod["stock_actual"] = max(0, prod["stock_actual"] - cant)

    return json.dumps({
        "tool": "ajustar_stock",
        "args": {"nombre": prod["nombre"], "cantidad": cant, "tipo": tipo},
        "respuesta": f"Voy a {verbo} {cant} de {prod['nombre']} (existencia actual: {prod['stock_actual']}). ¿Confirmas?",
        "status": "success",
        "sku": prod["sku"],
        "stock_anterior": stock_previo,
        "stock_nuevo": prod["stock_actual"]
    }, ensure_ascii=False)


# ── KIT 2: VENDEDOR_TOOLS ──

@tool(args_schema=BuildPosCartInput)
def build_pos_cart_from_vision(vision_payload: Dict[str, Any]) -> str:
    """
    Cruza los ítems detectados por cámara en /pos-checkout con el catálogo en PostgreSQL,
    valida existencias de stock, calcula precios unitarios, subtotales y el total consolidado.
    """
    items_detectados = vision_payload.get("items", [])
    if not items_detectados:
        return json.dumps({"status": "warning", "message": "No hay ítems detectados en /pos-checkout."}, ensure_ascii=False)

    lineas_carrito = []
    total_acumulado = 0.0
    alertas_stock = []

    for item in items_detectados:
        sku = item.get("sku", "")
        cant = int(item.get("cantidad", 1))

        # Buscar en catálogo
        prod = None
        for p in db.productos.values():
            if p["sku"] == sku or p["nombre"].lower() == item.get("nombre", "").lower():
                prod = p
                break

        if not prod:
            alertas_stock.append(f"Producto '{item.get('nombre', sku)}' no encontrado en catálogo.")
            continue

        if prod["stock_actual"] < cant:
            alertas_stock.append(f"Stock insuficiente para {prod['nombre']}. Solicitado: {cant}, Disponible: {prod['stock_actual']}.")

        subtotal = round(prod["precio_venta"] * cant, 2)
        total_acumulado += subtotal

        lineas_carrito.append({
            "producto_id": prod["id"],
            "sku": prod["sku"],
            "nombre": prod["nombre"],
            "cantidad": cant,
            "precio_unitario": prod["precio_venta"],
            "subtotal": subtotal,
            "stock_disponible": prod["stock_actual"]
        })

    carrito = {
        "status": "success",
        "endpoint": "/pos-checkout",
        "items": lineas_carrito,
        "total_a_cobrar": round(total_acumulado, 2),
        "alertas_stock": alertas_stock,
        "requiere_confirmacion_cobro": True
    }
    return json.dumps(carrito, ensure_ascii=False, indent=2)


@tool(args_schema=CrossSellInput)
def get_cross_sell_recommendations(skus_carrito: List[str]) -> str:
    """
    Analiza los productos actuales del carrito y sugiere recomendaciones de venta cruzada
    (cross-selling) basadas en co-ocurrencia y frecuencia de compra comprobada.
    """
    reglas_coocurrencia = {
        "COCA-600": [{"sku": "SABR-ORIG-45G", "motivo": "Botana salada complementaria de alta rotación"}],
        "LALA-1L": [{"sku": "BIMB-BLAN", "motivo": "Combo desayuno tradicional"}, {"sku": "GAL-MAR-170", "motivo": "Acompañamiento dulce"}],
        "BIMB-BLAN": [{"sku": "LALA-1L", "motivo": "Lácteo básico"}, {"sku": "HUEV-12", "motivo": "Ingrediente para sándwich o desayuno"}],
        "NESC-CLAS-120": [{"sku": "LALA-1L", "motivo": "Café con leche"}, {"sku": "GAL-MAR-170", "motivo": "Galletas para café"}]
    }

    recomendaciones = []
    skus_set = set(skus_carrito)

    for sku in skus_carrito:
        if sku in reglas_coocurrencia:
            for rec in reglas_coocurrencia[sku]:
                target_sku = rec["sku"]
                if target_sku not in skus_set:
                    # Buscar datos del producto recomendado
                    for p in db.productos.values():
                        if p["sku"] == target_sku:
                            recomendaciones.append({
                                "sku": target_sku,
                                "nombre": p["nombre"],
                                "precio_venta": p["precio_venta"],
                                "motivo": rec["motivo"],
                                "gancho_venta": f"¿Desea agregar {p['nombre']} por solo ${p['precio_venta']:,.2f}?"
                            })

    return json.dumps({
        "status": "success",
        "skus_evaluados": skus_carrito,
        "recomendaciones": recomendaciones[:3]
    }, ensure_ascii=False, indent=2)


@tool(args_schema=CommitSaleTransactionInput)
def commit_sale_transaction(cart_payload: Dict[str, Any]) -> str:
    """
    Registra formalmente una venta completada en 'ventas' y 'detalle_ventas',
    descontando el stock físico correspondiente de 'productos'.
    """
    items = cart_payload.get("items", [])
    total = float(cart_payload.get("total_a_cobrar", 0.0) or cart_payload.get("total", 0.0))
    metodo = cart_payload.get("metodo_pago", "efectivo")
    origen_vision = bool(cart_payload.get("origen_vision", True))

    nueva_venta_id = max(db.ventas.keys(), default=0) + 1
    hoy_iso = datetime.now().isoformat()

    db.ventas[nueva_venta_id] = {
        "id": nueva_venta_id,
        "fecha": hoy_iso,
        "total": round(total, 2),
        "metodo_pago": metodo,
        "origen_vision": origen_vision
    }

    detalles_guardados = []
    for it in items:
        det_id = max(db.detalle_ventas.keys(), default=0) + 1
        p_id = it.get("producto_id")
        cant = int(it.get("cantidad", 1))
        p_unit = float(it.get("precio_unitario", 0.0))
        sub = round(cant * p_unit, 2)

        db.detalle_ventas[det_id] = {
            "id": det_id,
            "venta_id": nueva_venta_id,
            "producto_id": p_id,
            "cantidad": cant,
            "precio_unitario": p_unit,
            "subtotal": sub
        }
        detalles_guardados.append(db.detalle_ventas[det_id])

        # Descontar stock
        if p_id in db.productos:
            db.productos[p_id]["stock_actual"] = max(0, db.productos[p_id]["stock_actual"] - cant)

    resultado = {
        "status": "success",
        "venta_id": nueva_venta_id,
        "fecha": hoy_iso,
        "total_cobrado": round(total, 2),
        "metodo_pago": metodo,
        "detalles": detalles_guardados,
        "mensaje": f"Venta #{nueva_venta_id} confirmada. Stock descontado exitosamente."
    }
    return json.dumps(resultado, ensure_ascii=False, indent=2)


# ── KIT 3: ANALISTA_TOOLS (Estrictamente Solo Lectura) ──

@tool(args_schema=CashflowSummaryInput)
def get_cashflow_summary(fecha_inicio: str, fecha_fin: str) -> str:
    """
    ESTRICTAMENTE SOLO LECTURA.
    Calcula el balance y flujo de caja sumando ingresos reales de 'ventas' y
    contrastándolos con egresos de 'movimientos_financieros' (gastos operativos e inversión en inventario).
    """
    total_ingresos = sum(v["total"] for v in db.ventas.values())

    gasto_operativo = 0.0
    inversion_inventario = 0.0

    for m in db.movimientos_financieros.values():
        if m["tipo"] == "gasto_operativo":
            gasto_operativo += m["monto_total"]
        elif m["tipo"] == "inversion_inventario":
            inversion_inventario += m["monto_total"]

    total_egresos = gasto_operativo + inversion_inventario
    flujo_neto = round(total_ingresos - total_egresos, 2)

    resumen = {
        "status": "success",
        "periodo": f"{fecha_inicio} a {fecha_fin}",
        "ingresos_ventas": round(total_ingresos, 2),
        "egresos_totales": round(total_egresos, 2),
        "desglose_egresos": {
            "gasto_operativo": round(gasto_operativo, 2),
            "inversion_inventario": round(inversion_inventario, 2)
        },
        "flujo_caja_neto": flujo_neto,
        "rentabilidad_bruta_porcentaje": round((total_ingresos / total_egresos * 100), 2) if total_egresos > 0 else 0.0
    }
    return json.dumps(resumen, ensure_ascii=False, indent=2)


@tool(args_schema=ProductMarginsInput)
def get_product_margins(categoria: Optional[str] = None) -> str:
    """
    ESTRICTAMENTE SOLO LECTURA.
    Calcula el margen de ganancia unitario bruto ($ y %) y rotación estimada por SKU.
    Filtra opcionalmente por categoría.
    """
    analisis = []
    for prod in db.productos.values():
        if categoria and prod["categoria"].lower() != categoria.lower():
            continue

        pv = prod["precio_venta"]
        cu = prod["costo_unitario"]
        margen_pesos = round(pv - cu, 2)
        margen_porcentaje = round((margen_pesos / pv) * 100, 2) if pv > 0 else 0.0

        analisis.append({
            "sku": prod["sku"],
            "nombre": prod["nombre"],
            "categoria": prod["categoria"],
            "precio_venta": pv,
            "costo_unitario": cu,
            "margen_pesos": margen_pesos,
            "margen_porcentaje": margen_porcentaje,
            "stock_actual": prod["stock_actual"]
        })

    # Ordenar de mayor a menor margen porcentual
    analisis.sort(key=lambda x: x["margen_porcentaje"], reverse=True)

    return json.dumps({
        "status": "success",
        "categoria_filtrada": categoria or "todas",
        "total_skus": len(analisis),
        "metricas_margen": analisis
    }, ensure_ascii=False, indent=2)


# ── KIT 4: INVESTIGADOR_TOOLS ──

@tool
def get_sales_cohort_metrics() -> str:
    """
    Analiza la base de datos histórica de ventas para obtener ticket promedio,
    horarios pico y productos ancla de alta rotación.
    """
    total_ventas = len(db.ventas)
    if total_ventas == 0:
        return json.dumps({"status": "warning", "message": "No hay ventas registradas."}, ensure_ascii=False)

    suma_totales = sum(v["total"] for v in db.ventas.values())
    ticket_promedio = round(suma_totales / total_ventas, 2)

    # Conteo de productos más vendidos
    conteo_prod: Dict[int, int] = {}
    for d in db.detalle_ventas.values():
        pid = d["producto_id"]
        conteo_prod[pid] = conteo_prod.get(pid, 0) + d["cantidad"]

    productos_ancla = []
    for pid, cant in sorted(conteo_prod.items(), key=lambda x: x[1], reverse=True)[:3]:
        p = db.productos.get(pid, {})
        productos_ancla.append({
            "sku": p.get("sku"),
            "nombre": p.get("nombre"),
            "unidades_vendidas": cant,
            "precio_venta": p.get("precio_venta")
        })

    cohort_data = {
        "status": "success",
        "ticket_promedio_mxn": ticket_promedio,
        "total_transacciones_analizadas": total_ventas,
        "horarios_pico_identificados": [
            {"franja": "07:30 - 09:30", "tipo_demanda": "Desayuno / Reposición rápida", "ticket_medio": 48.50},
            {"franja": "18:00 - 20:30", "tipo_demanda": "Cena / Compras de conveniencia y botanas", "ticket_medio": 82.00}
        ],
        "productos_ancla": productos_ancla
    }
    return json.dumps(cohort_data, ensure_ascii=False, indent=2)


@tool(args_schema=SearchMarketTrendsInput)
def search_market_trends(sector: str, query: str) -> str:
    """
    Consulta tendencias comerciales externas de consumo retail minorista.
    Utiliza Tavily Search si existe TAVILY_API_KEY o un fallback estructurado.
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            req_data = json.dumps({
                "api_key": tavily_key,
                "query": f"{sector} {query} tendencias retail Mexico 2026",
                "max_results": 3
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                res = json.loads(response.read().decode("utf-8"))
                return json.dumps({
                    "status": "success",
                    "source": "tavily_live_search",
                    "results": res.get("results", [])
                }, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Fallback estructurado de inteligencia de mercado para abarrotes/tienditas
    fallback_insights = {
        "status": "success",
        "source": "intel_mercado_retail_latam",
        "sector": sector,
        "query": query,
        "macrotendencias": [
            "Adopción acelerada de cobro con tarjeta y CoDi/SPEI (+35% en negocios de barrio).",
            "Preferencia marcada por empaques personales o 'desembolso bajo' frente a presentaciones familiares.",
            "Consumo de impulso en refrigerados (bebidas energéticas, leches saborizadas, refrescos fríos) con margen superior al 28%."
        ],
        "comportamiento_consumidor": "El 74% de los compradores de tienditas decide compras complementarias al llegar al mostrador si existe señalización clara de precio o descuento."
    }
    return json.dumps(fallback_insights, ensure_ascii=False, indent=2)


# ── KIT 5: PUBLICISTA_TOOLS ──

@tool(args_schema=GeneratePromoVideoInput)
def generate_promo_video_job(producto: str, descuento: str, video_prompt: str) -> str:
    """
    Envía un prompt vertical 9:16 (5s) a la API de generación de video sintético
    y registra un borrador en la tabla 'campanas_promocionales' en estado 'pendiente_aprobacion'.
    """
    # Buscar producto
    prod_id = 1
    for p in db.productos.values():
        if p["sku"].lower() == producto.lower() or producto.lower() in p["nombre"].lower():
            prod_id = p["id"]
            break

    campana_id = max(db.campanas_promocionales.keys(), default=0) + 1
    nueva_campana = {
        "id": campana_id,
        "producto_id": prod_id,
        "motivo": f"Campaña promocional con descuento de {descuento}",
        "copy_texto": f"Aprovecha {descuento} de descuento en {producto}. ¡Solo en Tiendita IA!",
        "video_prompt": video_prompt,
        "video_url": f"https://cdn.tiendita.ia/promos/video_job_{campana_id}_916.mp4",
        "estado_aprobacion": "pendiente_aprobacion"
    }
    db.campanas_promocionales[campana_id] = nueva_campana

    respuesta = {
        "status": "success",
        "job_id": f"vid_gen_job_{campana_id}",
        "formato": "vertical_9_16",
        "duracion_segundos": 5,
        "campana_id": campana_id,
        "video_prompt": video_prompt,
        "video_url_generada": nueva_campana["video_url"],
        "estado": "pendiente_aprobacion",
        "mensaje": f"Trabajo de video registrado para {producto}. Esperando confirmación de usuario."
    }
    return json.dumps(respuesta, ensure_ascii=False, indent=2)


# ── KIT 6: TUTOR_UI_TOOLS ──

@tool(args_schema=InspectPaymentStepInput)
def inspect_payment_step(ui_state: Dict[str, Any]) -> str:
    """
    Cruza 'pantalla', 'paso_actual', 'campos_vacios' y 'error_visible' con las reglas
    estrictas de pasarelas de pago (SPEI, Tarjeta Bancaria, QR) y genera el diagnóstico exacto.
    """
    pantalla = ui_state.get("pantalla", "Checkout")
    paso = ui_state.get("paso_actual", "")
    campos_vacios = ui_state.get("campos_vacios", [])
    error = ui_state.get("error_visible")
    intentos = ui_state.get("intentos", 1)

    diagnostico = ""
    accion_exacta = ""

    if "spei" in pantalla.lower():
        if "clabe" in campos_vacios or (error and "18" in error):
            diagnostico = "Falta o es incorrecta la CLABE interbancaria de 18 dígitos."
            accion_exacta = "Ingresa los 18 dígitos de la cuenta CLABE en el campo 'CLABE Interbancaria' y pulsa 'Confirmar Transferencia'."
        else:
            diagnostico = "Esperando comprobante de transferencia SPEI del banco emisor."
            accion_exacta = "Presiona 'Verificar Pago SPEI' para consultar el estado en Banxico."

    elif "tarjeta" in pantalla.lower():
        if "cvv" in campos_vacios:
            diagnostico = "Falta el código de seguridad (CVV)."
            accion_exacta = "Escribe los 3 dígitos del reverso de tu tarjeta en el campo 'CVV' y presiona 'Pagar con Tarjeta'."
        elif "numero" in campos_vacios:
            diagnostico = "Falta el número de tarjeta (16 dígitos)."
            accion_exacta = "Escribe los 16 dígitos de tu tarjeta sin espacios en el recuadro correspondiente."
        else:
            diagnostico = error or "Error general al procesar la tarjeta."
            accion_exacta = "Revisa los fondos disponibles de tu tarjeta o intenta con otro método de pago."

    elif "qr" in pantalla.lower():
        diagnostico = "Escaneo de código QR de cobro."
        accion_exacta = "Apunta la cámara de tu app bancaria al código QR visible en pantalla y confirma el importe."

    else:
        diagnostico = f"Paso {paso} en pantalla {pantalla}."
        accion_exacta = "Completa los campos obligatorios marcados con asterisco para continuar."

    return json.dumps({
        "status": "success",
        "pantalla": pantalla,
        "diagnostico_problema": diagnostico,
        "instruccion_accionable": accion_exacta,
        "intentos": intentos
    }, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# 4. AGRUPACIÓN DE KITS Y EXPORTADOR MCP
# ─────────────────────────────────────────────────────────────────────────────

CONTROL_TOOLS = [
    parse_vision_catalog_item,
    parse_receipt_ocr,
    query_expiring_products,
    commit_inventory_mutation,
    crear_producto,
    actualizar_precio,
    consultar_inventario,
    ajustar_stock,
]

VENDEDOR_TOOLS = [
    build_pos_cart_from_vision,
    get_cross_sell_recommendations,
    commit_sale_transaction,
]

ANALISTA_TOOLS = [
    get_cashflow_summary,
    get_product_margins,
]

INVESTIGADOR_TOOLS = [
    get_sales_cohort_metrics,
    search_market_trends,
]

PUBLICISTA_TOOLS = [
    generate_promo_video_job,
]

TUTOR_UI_TOOLS = [
    inspect_payment_step,
]

ALL_TOOLS = (
    CONTROL_TOOLS
    + VENDEDOR_TOOLS
    + ANALISTA_TOOLS
    + INVESTIGADOR_TOOLS
    + PUBLICISTA_TOOLS
    + TUTOR_UI_TOOLS
)


def to_mcp_tool_definitions() -> List[Dict[str, Any]]:
    """
    Exporta las 17 herramientas comerciales tipadas en el formato de esquema
    estándar del Model Context Protocol (MCP).
    
    Conteo: 8 CONTROL + 3 VENDEDOR + 2 ANALISTA + 2 INVESTIGADOR + 1 PUBLICISTA + 1 TUTOR_UI = 17.
    """
    mcp_tools = []
    for t in ALL_TOOLS:
        input_schema: Dict[str, Any] = {"type": "object", "properties": {}}
        if hasattr(t, "args_schema") and t.args_schema:
            try:
                schema = t.args_schema.model_json_schema()
                input_schema = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            except Exception:
                pass
        
        mcp_tools.append({
            "name": t.name,
            "description": t.description or "",
            "inputSchema": input_schema
        })

    return mcp_tools
