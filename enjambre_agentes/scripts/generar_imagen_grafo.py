#!/usr/bin/env python3
"""
Genera la imagen de alta resolución (`docs/diagrama_agentes_tiendita_ia.png`) del
enjambre multiagente de Tiendita IA con:
  - Descripción funcional clara dentro de cada uno de los 7 agentes
  - Aristas etiquetadas con acciones, HITL, compound_chain y conexiones a BD/RAG/NIM
  - Panel inferior de "Cómo Interactúan los Agentes (Flujos Operativos Paso a Paso)"
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
PNG_OUT = DOCS_DIR / "diagrama_agentes_tiendita_ia.png"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Paleta de alto contraste (tema oscuro moderno de presentación)
C_BG = "#0b1220"
C_BAND = "#111a2e"
C_BAND_BORDER = "#24324d"
C_CARD = "#162138"
C_CARD_DARK = "#0f172a"
C_TEXT = "#f1f5f9"
C_MUTED = "#94a3b8"
C_PRIMARY = "#38bdf8"    # Cyan / Orquestación
C_NVIDIA = "#76b900"     # Verde NVIDIA (120B)
C_NANO = "#22d3ee"       # Cyan claro (Nano 8B)
C_WARN = "#f59e0b"       # Ámbar (HITL)
C_SUCCESS = "#10b981"    # Esmeralda (END / Solo Lectura)
C_PURPLE = "#a78bfa"     # RAG
C_PINK = "#f472b6"       # Vision
C_ORANGE = "#fb923c"     # Web / Tavily
C_BLUE = "#60a5fa"       # PostgreSQL


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _bezier_points(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    steps: int = 56,
) -> List[Tuple[float, float]]:
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        pts.append((x, y))
    return pts


def _draw_arrow_curve(
    draw: ImageDraw.ImageDraw,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    color: str,
    width: int = 4,
    dashed: bool = False,
    arrow_size: float = 16.0,
) -> None:
    pts = _bezier_points(p0, p1, p2, p3, steps=56)
    if dashed:
        for i in range(0, len(pts) - 2, 2):
            draw.line([pts[i], pts[i + 1]], fill=color, width=width)
    else:
        draw.line(pts, fill=color, width=width, joint="curve")

    end_x, end_y = pts[-1]
    prev_x, prev_y = pts[-3]
    angle = math.atan2(end_y - prev_y, end_x - prev_x)
    left = (
        end_x - arrow_size * math.cos(angle - math.pi / 6),
        end_y - arrow_size * math.sin(angle - math.pi / 6),
    )
    right = (
        end_x - arrow_size * math.cos(angle + math.pi / 6),
        end_y - arrow_size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([(end_x, end_y), left, right], fill=color)


def _draw_pill_label(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fg: str,
    border: str,
    bg: str = C_CARD_DARK,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px, py = 12, 6
    rect = [cx - tw / 2 - px, cy - th / 2 - py, cx + tw / 2 + px, cy + th / 2 + py]
    draw.rounded_rectangle(rect, radius=12, fill=bg, outline=border, width=2)
    draw.text((cx - tw / 2, cy - th / 2 - 2), text, font=font, fill=fg)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw / 2, y), text, font=font, fill=fill)


def generar_png() -> None:
    # Lienzo 2800x2460 (2x supersampled -> 2100x1845 ultra-nítido)
    W, H = 2800, 2460
    img = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    f_title = _font(FONT_BOLD, 38)
    f_sub = _font(FONT_REG, 21)
    f_band = _font(FONT_BOLD, 17)
    f_node_t = _font(FONT_BOLD, 24)
    f_node_m = _font(FONT_MONO, 16)
    f_node_b = _font(FONT_REG, 17)
    f_node_tag = _font(FONT_BOLD, 15)
    f_edge = _font(FONT_BOLD, 15)
    f_legend = _font(FONT_REG, 18)
    f_flow_t = _font(FONT_BOLD, 19)
    f_flow_b = _font(FONT_REG, 17)

    # Encabezado superior
    draw.text((64, 34), "TIENDITA IA — Funciones e Interacción del Enjambre Multiagente", font=f_title, fill=C_TEXT)
    draw.text(
        (64, 88),
        "1 Supervisor + 6 Especialistas (100% NVIDIA NIM Default) · LangGraph · PostgreSQL · RAG CoDi/SPEI/DiMo · HITL",
        font=f_sub,
        fill=C_MUTED,
    )

    # Leyenda superior derecha
    legend_items = [
        (C_NVIDIA, "Nemotron-3 Super 120B"),
        (C_NANO, "Nemotron Nano 8B (LoRA)"),
        (C_WARN, "Pausa HITL (approval_gate)"),
        (C_SUCCESS, "Salida Directa / COMMIT"),
    ]
    lx = 1860
    for idx, (col, lbl) in enumerate(legend_items):
        row_x = lx + (idx % 2) * 445
        row_y = 36 + (idx // 2) * 38
        draw.ellipse([row_x, row_y + 4, row_x + 18, row_y + 22], fill=col)
        draw.text((row_x + 28, row_y), lbl, font=f_legend, fill=C_TEXT)

    # 6 Bandas de capas (5 arquitectura + 1 flujos de interacción)
    bands = [
        (48, 144, 2752, 304, "CAPA 1 · CANALES DE ENTRADA (REST JSON · SSE · WEBSOCKET /ws/orchestrate · CLI · CÁMARA · CRON)"),
        (48, 326, 2752, 620, "CAPA 2 · ORQUESTACIÓN CENTRAL (SUPERVISOR MAESTRO POR RAZONAMIENTO PURO · SIN PALABRAS CLAVE)"),
        (48, 642, 2752, 1132, "CAPA 3 · 6 AGENTES ESPECIALISTAS — FUNCIONES EXACTAS, MODELO NVIDIA Y PERMISOS"),
        (48, 1154, 2752, 1478, "CAPA 4 · CONTROL HUMANO (HITL approval_gate) Y SALIDA CONSOLIDADA (END)"),
        (48, 1500, 2752, 1872, "CAPA 5 · HERRAMIENTAS (@tool), MEMORIA MULTICAPA, POSTGRESQL Y STACK NVIDIA"),
        (48, 1894, 2752, 2418, "CAPA 6 · CÓMO INTERACTÚAN LOS AGENTES ENTRE SÍ (5 FLUJOS OPERATIVOS PASO A PASO)"),
    ]
    for x1, y1, x2, y2, title in bands:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=22, fill=C_BAND, outline=C_BAND_BORDER, width=2)
        draw.text((x1 + 26, y1 + 14), title, font=f_band, fill=C_MUTED)

    # Coordenadas clave
    sup_cx, sup_cy, sup_r = 1400, 484, 108
    spec_y1, spec_y2 = 724, 1102
    spec_w = 412
    spec_gap = 36
    spec_x0 = 76

    specs = [
        (
            "control", "Control", "Nemotron Nano 8B",
            [
                "• Escanea anaqueles (/catalog-scan)",
                "• OCR tickets: inventario vs gasto",
                "• Alta de SKU y ajustes de stock",
                "• Detecta lotes por caducar / bajos",
            ],
            "Lectura + Escritura HITL", C_NANO, C_WARN,
        ),
        (
            "vendedor", "Vendedor POS", "Nemotron Nano 8B",
            [
                "• Detecta artículos en caja POS",
                "• Carrito, cotización y cobro real",
                "• Upselling con v_coocurrencia",
                "• Valida límites CoDi/SPEI/DiMo",
            ],
            "Máscara Costo + HITL", C_NANO, C_WARN,
        ),
        (
            "analista", "Analista", "Nemotron-3 Super 120B",
            [
                "• Flujo de caja (v_flujo_caja)",
                "• Márgenes por SKU (auditoría)",
                "• Rotación y top más vendidos",
                "• Resumen ventas y ticket medio",
            ],
            "100% Solo Lectura", C_NVIDIA, C_SUCCESS,
        ),
        (
            "investigador", "Investigador", "Nemotron-3 Super 120B",
            [
                "• Consulta reportes previos (FAISS)",
                "• Busca tendencias web (Tavily)",
                "• Extrae páginas (BeautifulSoup)",
                "• Genera reporte de 9 secciones",
            ],
            "Guarda e Indexa en FAISS", C_NVIDIA, C_PRIMARY,
        ),
        (
            "publicista", "Publicista", "Nemotron Nano 8B",
            [
                "• Lee lotes críticos (v_por_caducar)",
                "• Crea copys para WhatsApp/tienda",
                "• Redacta CTA y remates (20% desc)",
                "• Genera prompt Video 9:16 (5 s)",
            ],
            "Aprobación HITL Obligatoria", C_NANO, C_WARN,
        ),
        (
            "tutor_ui", "Tutor UI", "Nemotron Nano 8B",
            [
                "• Lee ui_state (pantalla/paso/error)",
                "• Consulta RAG Banxico + guias.json",
                "• Resuelve fallos CoDi/SPEI/DiMo",
                "• Nunca solicita NIP, token ni CVV",
            ],
            "Estricto: Máx. 2 oraciones", C_NANO, C_SUCCESS,
        ),
    ]

    spec_centers = {}
    for i, item in enumerate(specs):
        x1 = spec_x0 + i * (spec_w + spec_gap)
        cx = x1 + spec_w / 2
        spec_centers[item[0]] = (cx, spec_y1, spec_y2, x1, x1 + spec_w)

    hitl_x1, hitl_y1, hitl_x2, hitl_y2 = 590, 1236, 1360, 1438
    hitl_cx, hitl_cy = (hitl_x1 + hitl_x2) / 2, (hitl_y1 + hitl_y2) / 2
    end_cx, end_cy, end_r = 2110, 1338, 96

    # Subsistemas Capa 5
    sub_y1, sub_y2 = 1572, 1838
    sub_w = 496
    sub_gap = 42
    sub_x0 = 76
    subs = [
        ("postgres", "PostgreSQL (tiendita-db)", "v_inventario · v_por_caducar", "v_margen · registrar_venta()", "Pool Thread-Safe + pgvector", C_BLUE),
        ("vision", "NVIDIA NIM Vision (VL)", "nemotron-3.5-super-vl-120b", "Catálogo · POS · OCR Ticket", "Imágenes Reales Base64", C_PINK),
        ("rag", "RAG Dual CoDi/SPEI/DiMo", "FAISS (969 frags) + pgvector", "Banxico + guias.json + Rerank", "embeddings.npz (4096-dim)", C_PURPLE),
        ("web", "Tavily Web + Reportes", "search_web_tavily + Scraping", "data/reportes/*.json & .md", "Memoria Estratégica Histórica", C_ORANGE),
        ("nemo", "NeMo Guardrails + SFT", "rails.co (Colang) + guards.py", "nemo_customizer_train.jsonl", "LoRA + Circuit Breaker 90s", C_NVIDIA),
    ]
    sub_centers = {}
    for i, s in enumerate(subs):
        x1 = sub_x0 + i * (sub_w + sub_gap)
        sub_centers[s[0]] = (x1 + sub_w / 2, sub_y1, sub_y2, x1, x1 + sub_w)

    # ==================== ARISTAS (DEBAJO DE NODOS) ====================

    # 1. Entrada -> Supervisor
    _draw_arrow_curve(draw, (1400, 286), (1400, 320), (1400, 344), (1400, sup_cy - sup_r - 4), C_PRIMARY, width=5)
    _draw_pill_label(draw, 1400, 330, "event_source + JSON / Imagen / ui_state", f_edge, C_PRIMARY, C_PRIMARY)

    # 2. Supervisor -> 6 Especialistas
    edge_specs = [
        ("control", C_NANO, "inventario / OCR / cron", (615, 604)),
        ("vendedor", C_NANO, "cobro POS / upsell", (965, 690)),
        ("analista", C_NVIDIA, "flujo / márgenes / top", (1235, 690)),
        ("investigador", C_NVIDIA, "mercado / 9 secciones", (1585, 690)),
        ("publicista", C_NANO, "campaña / video 9:16", (1880, 690)),
        ("tutor_ui", C_NANO, "ui_state CoDi/SPEI/DiMo", (2210, 604)),
    ]
    for role, col, lbl, lbl_pos in edge_specs:
        cx, y1, _, _, _ = spec_centers[role]
        dx = cx - sup_cx
        start_x = sup_cx + max(-sup_r * 0.92, min(sup_r * 0.92, dx * 0.14))
        start_y = sup_cy + math.sqrt(max(1.0, sup_r**2 - (start_x - sup_cx) ** 2))
        _draw_arrow_curve(
            draw,
            (start_x, start_y),
            (start_x + dx * 0.25, start_y + 70),
            (cx, y1 - 80),
            (cx, y1 - 4),
            col,
            width=4,
        )
        _draw_pill_label(draw, lbl_pos[0], lbl_pos[1], lbl, f_edge, C_TEXT, col)

    # 3. Retorno compound_chain (Control -> Supervisor)
    ctrl_cx = spec_centers["control"][0]
    _draw_arrow_curve(
        draw,
        (ctrl_cx + 80, spec_y1),
        (ctrl_cx + 150, 486),
        (sup_cx - 320, 466),
        (sup_cx - sup_r - 6, 484),
        C_PRIMARY,
        width=4,
        dashed=True,
    )
    _draw_pill_label(draw, 810, 478, "compound_chain (ej. control → publicista)", f_edge, C_PRIMARY, C_PRIMARY)

    # 4. Aristas hacia HITL
    _draw_arrow_curve(draw, (spec_centers["control"][0], spec_y2), (spec_centers["control"][0], 1310), (480, 1326), (hitl_x1 - 4, 1326), C_WARN, width=4)
    _draw_pill_label(draw, 415, 1280, "alta / gasto crítico", f_edge, C_WARN, C_WARN)

    _draw_arrow_curve(draw, (spec_centers["vendedor"][0], spec_y2), (spec_centers["vendedor"][0], 1192), (850, 1192), (850, hitl_y1 - 4), C_WARN, width=4)
    _draw_pill_label(draw, 930, 1205, "descuento especial", f_edge, C_WARN, C_WARN)

    _draw_arrow_curve(draw, (spec_centers["publicista"][0] - 80, spec_y2), (1760, 1200), (1500, 1278), (hitl_x2 + 4, 1288), C_WARN, width=4)
    _draw_pill_label(draw, 1565, 1242, "aprobar campaña 9:16", f_edge, C_WARN, C_WARN)

    # 5. Salidas directas hacia END
    _draw_arrow_curve(draw, (spec_centers["analista"][0], spec_y2), (spec_centers["analista"][0], 1190), (1950, 1212), (end_cx - end_r + 12, end_cy - 58), C_SUCCESS, width=4)
    _draw_arrow_curve(draw, (spec_centers["investigador"][0], spec_y2), (spec_centers["investigador"][0], 1175), (2040, 1185), (end_cx - 24, end_cy - end_r - 2), C_SUCCESS, width=4)
    _draw_arrow_curve(draw, (spec_centers["tutor_ui"][0], spec_y2), (spec_centers["tutor_ui"][0], 1264), (2350, 1338), (end_cx + end_r + 4, end_cy), C_SUCCESS, width=4)
    _draw_pill_label(draw, 2450, 1250, "guía ≤ 2 oraciones", f_edge, C_SUCCESS, C_SUCCESS)

    # 6. HITL -> END
    _draw_arrow_curve(draw, (hitl_x2, hitl_cy + 16), (1600, hitl_cy + 16), (1810, end_cy + 16), (end_cx - end_r - 4, end_cy + 16), C_SUCCESS, width=5)
    _draw_pill_label(draw, 1685, hitl_cy + 48, "resume_orchestration() → COMMIT / Cancelar", f_edge, C_SUCCESS, C_SUCCESS)

    # 7. Conexiones a Capa 5
    pg_cx = sub_centers["postgres"][0]
    vis_cx = sub_centers["vision"][0]
    rag_cx = sub_centers["rag"][0]
    web_cx = sub_centers["web"][0]
    nemo_cx = sub_centers["nemo"][0]

    _draw_arrow_curve(draw, (spec_centers["control"][0] - 90, spec_y2), (180, 1370), (240, 1495), (pg_cx - 80, sub_y1 - 4), C_BLUE, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["vendedor"][0] - 80, spec_y2), (560, 1400), (350, 1495), (pg_cx, sub_y1 - 4), C_BLUE, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (hitl_cx - 120, hitl_y2), (650, 1505), (470, 1525), (pg_cx + 110, sub_y1 - 4), C_WARN, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["control"][0] + 60, spec_y2), (420, 1350), (760, 1505), (vis_cx - 40, sub_y1 - 4), C_PINK, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["vendedor"][0], spec_y2), (760, 1430), (850, 1505), (vis_cx + 40, sub_y1 - 4), C_PINK, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["tutor_ui"][0] - 60, spec_y2), (2280, 1475), (1560, 1495), (rag_cx + 90, sub_y1 - 4), C_PURPLE, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["vendedor"][0] + 100, spec_y2), (1080, 1465), (1320, 1510), (rag_cx - 90, sub_y1 - 4), C_PURPLE, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (spec_centers["investigador"][0], spec_y2), (1680, 1450), (1890, 1510), (web_cx, sub_y1 - 4), C_ORANGE, width=3, dashed=True, arrow_size=12)
    _draw_arrow_curve(draw, (hitl_cx + 160, hitl_y2), (1480, 1495), (2260, 1505), (nemo_cx - 40, sub_y1 - 4), C_NVIDIA, width=3, dashed=True, arrow_size=12)

    # ==================== NODOS ENCIMA DE ARISTAS ====================

    # Capa 1: Cliente
    draw.rounded_rectangle([850, 190, 1950, 286], radius=48, fill=C_CARD, outline=C_PRIMARY, width=4)
    _draw_centered_text(draw, 1400, 204, "Cliente · App Móvil · CLI Rich · Cámara · Cron", f_node_t, C_TEXT)
    _draw_centered_text(draw, 1400, 244, "REST JSON (/orchestrate, /pago, /imagen, /cron)  ·  SSE  ·  WebSocket (/ws/orchestrate)", f_node_b, C_MUTED)

    # Capa 2: Supervisor (CÍRCULO) + Tarjeta de funciones del Supervisor a la derecha
    draw.ellipse([sup_cx - sup_r, sup_cy - sup_r, sup_cx + sup_r, sup_cy + sup_r], fill=C_CARD, outline=C_NVIDIA, width=6)
    _draw_centered_text(draw, sup_cx, sup_cy - 54, "Supervisor", _font(FONT_BOLD, 30), C_TEXT)
    _draw_centered_text(draw, sup_cx, sup_cy - 12, "Nemotron 120B", f_node_m, C_MUTED)
    _draw_centered_text(draw, sup_cx, sup_cy + 18, "Razonamiento Puro", _font(FONT_BOLD, 17), C_NVIDIA)
    _draw_centered_text(draw, sup_cx, sup_cy + 46, "iter ≤ 6", f_node_m, C_PRIMARY)

    # Ficha lateral de funciones del Supervisor (para que los 7 agentes tengan descripción clara)
    sup_box = [1600, 386, 2680, 560]
    draw.rounded_rectangle(sup_box, radius=16, fill=C_CARD_DARK, outline=C_NVIDIA, width=2)
    draw.line([(sup_cx + sup_r, 472), (1600, 472)], fill=C_NVIDIA, width=2)
    draw.text((1626, 400), "Funciones del Supervisor Maestro (Director de Orquesta):", font=_font(FONT_BOLD, 19), fill=C_NVIDIA)
    sup_bullets = [
        "• Analiza intención semántica + event_source + imagen/ui_state (sin palabras clave).",
        "• Emite salida estructurada SupervisorDecision eligiendo el especialista exacto.",
        "• Encadena varios agentes con compound_chain (ej. Control → Publicista) sin duplicados.",
        "• Rescate silencioso (.with_fallbacks() + Circuit Breaker 90s) y límite iter ≤ 6.",
    ]
    for idx, line in enumerate(sup_bullets):
        draw.text((1626, 434 + idx * 30), line, font=f_node_b, fill=C_TEXT)

    # Capa 3: 6 Especialistas con sus 4 funciones detalladas
    for role, title, model, bullets, tag, col_border, col_tag in specs:
        cx, y1, y2, x1, x2 = spec_centers[role]
        draw.rounded_rectangle([x1, y1, x2, y2], radius=22, fill=C_CARD, outline=col_border, width=4)
        draw.rounded_rectangle([x1 + 18, y1 + 18, x1 + 36, y1 + 36], radius=9, fill=col_border)
        _draw_centered_text(draw, cx + 8, y1 + 18, title, f_node_t, C_TEXT)
        _draw_centered_text(draw, cx, y1 + 58, model, f_node_m, C_MUTED)
        draw.line([(x1 + 22, y1 + 92), (x2 - 22, y1 + 92)], fill=C_BAND_BORDER, width=2)

        for b_idx, b_txt in enumerate(bullets):
            draw.text((x1 + 22, y1 + 110 + b_idx * 44), b_txt, font=f_node_b, fill=C_TEXT)

        _draw_pill_label(draw, cx, y2 - 36, tag, f_node_tag, col_tag, col_tag, bg=C_CARD_DARK)

    # Capa 4: HITL + END
    draw.rounded_rectangle([hitl_x1, hitl_y1, hitl_x2, hitl_y2], radius=22, fill=C_CARD, outline=C_WARN, width=5)
    _draw_centered_text(draw, hitl_cx, hitl_y1 + 22, "approval_gate (HITL Interrupt)", _font(FONT_BOLD, 25), C_WARN)
    _draw_centered_text(draw, hitl_cx, hitl_y1 + 66, "Pausa en CLI / REST / WebSocket: [s] Aprobar · [n] Rechazar · [e] Editar", f_node_b, C_TEXT)
    _draw_centered_text(draw, hitl_cx, hitl_y1 + 102, "Si Aprueba → COMMIT real en PostgreSQL + Feedback SFT (NeMo Customizer)", f_node_m, C_MUTED)
    _draw_centered_text(draw, hitl_cx, hitl_y1 + 136, "Si Rechaza → Cancelación limpia (0 escrituras en BD)", f_node_m, C_MUTED)

    draw.ellipse([end_cx - end_r, end_cy - end_r, end_cx + end_r, end_cy + end_r], fill=C_CARD, outline=C_SUCCESS, width=6)
    _draw_centered_text(draw, end_cx, end_cy - 34, "END", _font(FONT_BOLD, 34), C_SUCCESS)
    _draw_centered_text(draw, end_cx, end_cy + 14, "Respuesta JSON", f_node_m, C_TEXT)
    _draw_centered_text(draw, end_cx, end_cy + 40, "~3.5s directo", f_node_m, C_MUTED)

    # Capa 5: Subsistemas
    for key, title, l1, l2, tag, col in subs:
        cx, y1, y2, x1, x2 = sub_centers[key]
        draw.rounded_rectangle([x1, y1, x2, y2], radius=18, fill=C_CARD, outline=col, width=3)
        _draw_centered_text(draw, cx, y1 + 22, title, _font(FONT_BOLD, 22), C_TEXT)
        draw.line([(x1 + 22, y1 + 62), (x2 - 22, y1 + 62)], fill=C_BAND_BORDER, width=2)
        _draw_centered_text(draw, cx, y1 + 80, l1, f_node_m, C_MUTED)
        _draw_centered_text(draw, cx, y1 + 114, l2, f_node_m, C_MUTED)
        _draw_pill_label(draw, cx, y2 - 44, tag, f_node_tag, col, col, bg=C_CARD_DARK)

    # ==================== CAPA 6: CÓMO INTERACTÚAN ENTRE SÍ (5 FLUJOS) ====================
    flows_cards = [
        (
            "1. Flujo Compuesto + HITL (/cron)",
            C_WARN,
            "Supervisor → Control → Supervisor (compound_chain) → Publicista → approval_gate → END",
            "Control detecta lotes próximos a caducar en v_por_caducar y devuelve el control al Supervisor; éste despacha a Publicista para redactar copy + video 9:16 y pausar en HITL hasta que el dueño apruebe el COMMIT en tabla promocion.",
        ),
        (
            "2. Cobro en Mostrador POS + CoDi / SPEI / DiMo",
            C_NANO,
            "Supervisor → Vendedor POS ↔ (PostgreSQL + RAG Pagos) → [HITL si hay descuento] → END",
            "Vendedor cotiza con buscar_productos(), sugiere venta cruzada desde v_coocurrencia, valida límites sin comisión de CoDi/SPEI/DiMo en el RAG, protege el costo unitario y ejecuta la venta atómica vía registrar_venta().",
        ),
        (
            "3. Asistencia de Pagos Digitales en Pantalla (/pago)",
            C_PURPLE,
            "Supervisor (ui_copilot) → Tutor UI ↔ RAG Banxico (FAISS / pgvector) → NeMo Guardrails → END",
            "Tutor UI recibe método (codi/spei/dimo), pantalla, paso y error; consulta guias.json y conocimiento.jsonl y responde en máximo 2 oraciones accionables sin pedir NIP ni contraseñas.",
        ),
        (
            "4. Visión Artificial Multimodal (/imagen · /catalog-scan · /receipt-ocr)",
            C_PINK,
            "Supervisor (vision_api) → Control o Vendedor ↔ NVIDIA NIM Vision VL + PostgreSQL → [HITL] → END",
            "El archivo Base64 real pasa por el buffer de NIM Vision (nemotron-3.5-super-vl-120b). Control clasifica tickets (inversion_inventario vs gasto_operativo) o da de alta SKUs con confirmación HITL; Vendedor cotiza artículos en caja.",
        ),
        (
            "5. Auditoría Financiera Rápida & Estrategia Comercial",
            C_NVIDIA,
            "Analista: Supervisor → Analista ↔ PostgreSQL (Solo Lectura) → END   |   Investigador: Supervisor → Investigador ↔ (FAISS + Tavily Web) → END",
            "Analista responde en ~3.5s sin volver al Supervisor (flujo de caja, márgenes y top ventas). Investigador consulta reportes previos, investiga en la web, genera StrategicReport de 9 secciones y lo reindexa en FAISS.",
        ),
    ]

    fy = 1948
    card_h = 84
    card_gap = 12
    for title, col, route_line, desc in flows_cards:
        draw.rounded_rectangle([76, fy, 2724, fy + card_h], radius=14, fill=C_CARD, outline=col, width=2)
        # Barra lateral izquierda de acento
        draw.rounded_rectangle([76, fy, 92, fy + card_h], radius=6, fill=col)
        draw.text((112, fy + 10), title, font=f_flow_t, fill=col)
        # Ruta en monospace alineada a la derecha del título
        t_bbox = draw.textbbox((0, 0), title, font=f_flow_t)
        route_x = 112 + (t_bbox[2] - t_bbox[0]) + 28
        draw.text((route_x, fy + 13), f"Ruta: {route_line}", font=_font(FONT_MONO, 15), fill=C_PRIMARY)
        draw.text((112, fy + 46), desc, font=f_flow_b, fill=C_TEXT)
        fy += card_h + card_gap

    # Downsample suave a 2100x1845 con LANCZOS
    final = img.resize((2100, 1845), Image.Resampling.LANCZOS)
    final.save(PNG_OUT, format="PNG", optimize=True)
    print(f"PNG actualizado: {PNG_OUT} ({PNG_OUT.stat().st_size:,} bytes, {final.size[0]}x{final.size[1]})")


if __name__ == "__main__":
    generar_png()
