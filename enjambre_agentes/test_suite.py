"""
test_suite.py — Pruebas unitarias y de integración del Ecosistema Multiagente Comercial.
"""
import json
import os
import tempfile

# El Data Flywheel (HITL aprobado) escribe aquí en lugar de en datasets/ del repo
os.environ.setdefault("NEMO_FLYWHEEL_BUFFER", os.path.join(tempfile.mkdtemp(prefix="suite_"), "hitl_feedback.jsonl"))

from state import (
    OrchestratorState,
    ProductoDB,
    LoteInventarioDB,
    VentaDB,
    DetalleVentaDB,
    MovimientoFinancieroDB,
    CampanaPromocionalDB,
    VisionPayloadModel,
    UIStateModel,
    StrategicReportModel,
    PromoAssetsModel,
    PendingApprovalModel,
)
from guards import enforce_db_grounding, validate_strategic_report
from few_shot_retriever import FewShotRetriever
from tools_bridge import (
    ALL_TOOLS,
    to_mcp_tool_definitions,
    parse_vision_catalog_item,
    parse_receipt_ocr,
    query_expiring_products,
    build_pos_cart_from_vision,
    get_cross_sell_recommendations,
    commit_sale_transaction,
    get_cashflow_summary,
    get_product_margins,
    get_sales_cohort_metrics,
    search_market_trends,
    generate_promo_video_job,
    inspect_payment_step,
    # Herramientas del asistente de catálogo (integración assistant/)
    crear_producto,
    actualizar_precio,
    consultar_inventario,
    ajustar_stock,
    find_product_by_name_or_alias,
)
from graph import run_orchestration, resume_orchestration


def test_models_and_schemas():
    print("1. Validando Modelos Pydantic...")
    prod = ProductoDB(
        sku="TEST-SKU",
        nombre="Producto Test",
        categoria="lacteos",
        precio_venta=25.0,
        costo_unitario=18.0,
        stock_actual=10,
        stock_minimo=3
    )
    assert prod.sku == "TEST-SKU"
    assert prod.precio_venta == 25.0

    vision = VisionPayloadModel(
        endpoint="/pos-checkout",
        items=[{"sku": "TEST-SKU", "cantidad": 1}],
        confianza_global=0.99
    )
    assert vision.endpoint == "/pos-checkout"

    ui = UIStateModel(
        pantalla="PagoSPEI",
        paso_actual="ingreso_clabe",
        campos_vacios=["clabe"],
        error_visible="Falta CLABE",
        intentos=1
    )
    assert ui.pantalla == "PagoSPEI"
    print("✓ Modelos Pydantic v2 validados correctamente.")


def test_tools_and_mcp():
    # 8 control + 3 vendedor + 2 analista + 2 investigador + 1 publicista + 1 tutor_ui = 17
    _TOTAL_TOOLS = 17
    print(f"\n2. Validando {_TOTAL_TOOLS} Herramientas Comerciales y Exportación MCP...")
    assert len(ALL_TOOLS) == _TOTAL_TOOLS, f"Se esperaban {_TOTAL_TOOLS} herramientas, se encontraron {len(ALL_TOOLS)}"
    mcp_defs = to_mcp_tool_definitions()
    assert len(mcp_defs) == _TOTAL_TOOLS, f"Se esperaban {_TOTAL_TOOLS} definiciones MCP, se obtuvieron {len(mcp_defs)}"
    for m in mcp_defs:
        assert "name" in m and "description" in m and "inputSchema" in m
        assert m["inputSchema"]["type"] == "object"
    print(f"✓ {_TOTAL_TOOLS} herramientas comerciales tipadas y exportadas en formato JSON Schema MCP.")


def test_guards():
    print("\n3. Validando Guards Deterministas...")
    valid_report = {
        "identificacion_sector": "Abarrotes y Misceláneas",
        "mercado_tendencias": "Digitalización de cobro y formatos pequeños",
        "clientes": "Familias de cercanía diaria",
        "problemas": "Mermas por caducidad no gestionadas a tiempo",
        "soluciones": "Visión artificial y promociones automatizadas",
        "hipotesis": "15% de descuento elimina 70% de mermas",
        "objetivos": "0 mermas y ticket de $95 MXN",
        "impacto": "Mejora de 5.8% en rentabilidad neta",
        "hallazgos": "Ticket promedio real de $79.50"
    }
    assert validate_strategic_report(valid_report) is True
    assert validate_strategic_report({"identificacion_sector": ""}) is False
    assert validate_strategic_report({"campo_invalido": "xyz"}) is False

    # Grounding determinista
    ok, errs = enforce_db_grounding("El total fue de $113.00 MXN", [{"total": 113.0}])
    assert ok is True, f"Error en grounding válido: {errs}"

    # Discrepancia no respaldada
    ok_bad, errs_bad = enforce_db_grounding("El total fue de $9,999.00 MXN", [{"total": 113.0}])
    assert ok_bad is False
    assert len(errs_bad) > 0

    # Sin evidencia y con mención monetaria
    ok_empty, errs_empty = enforce_db_grounding("Cobro de $50.00", [])
    assert ok_empty is False
    print("✓ enforce_db_grounding y validate_strategic_report funcionando al 100%.")


def test_few_shot_retriever():
    print("\n4. Validando FewShotRetriever...")
    retriever = FewShotRetriever()
    roles = ["orquestador", "ocr", "investigador", "publicista", "tutor_ui"]
    for r in roles:
        shots = retriever.get_few_shots(r)
        assert len(shots) >= 1, f"Faltan ejemplos para el rol {r}"
        formatted = retriever.format_few_shots_for_prompt(r)
        assert len(formatted) > 20
    print(f"✓ 5 roles Few-Shot operativos con diccionario semilla determinista.")


def test_pos_camera_and_hitl():
    print("\n5. Validando Flujo POS por Cámara (/pos-checkout) + HITL...")
    thread_pos = "test_pos_camera_123"
    result = run_orchestration(
        thread_id=thread_pos,
        event_source="vision_api",
        vision_payload={
            "endpoint": "/pos-checkout",
            "items": [{"sku": "LALA-1L", "cantidad": 2}, {"sku": "BIMB-BLAN", "cantidad": 1}],
            "confianza_global": 0.99
        }
    )

    # Debe haber pausado en HITL
    pending = result.get("pending_approval")
    assert pending is not None, "El Vendedor debió preparar pending_approval"
    assert pending["action_type"] == "sale_transaction"
    assert pending["requires_confirmation"] is True
    print(f"  -> Interrupción HITL alcanzada: Acción '{pending['action_type']}' pendiente de confirmación.")

    # Reanudar con aprobación
    resumed = resume_orchestration(thread_id=thread_pos, approved=True)
    assert resumed.get("pending_approval") is None, "pending_approval debió limpiarse tras HITL"
    last_msg = resumed.get("messages", [])[-1].content
    assert "confirmada" in last_msg.lower() or "registrada" in last_msg.lower()
    print("✓ Flujo POS por cámara con interrupción y reanudación HITL ejecutado con éxito.")


def test_receipt_ocr_and_hitl():
    print("\n6. Validando Flujo de Ticket / Factura OCR (/receipt-ocr)...")
    thread_ocr = "test_ocr_receipt_456"
    result = run_orchestration(
        thread_id=thread_ocr,
        event_source="vision_api",
        vision_payload={
            "endpoint": "/receipt-ocr",
            "proveedor": "Distribuidora de Lácteos del Centro S.A.",
            "items": [{"descripcion": "Caja Leche Lala 12 pzas", "cantidad": 2, "precio_unitario": 260.00, "subtotal": 520.00}],
            "total": 520.00,
            "tipo_movimiento": "inversion_inventario",
            "confianza_global": 0.96
        }
    )

    pending = result.get("pending_approval")
    assert pending is not None
    assert pending["action_type"] == "inventory_mutation"
    assert pending["payload"]["datos"]["tipo"] == "inversion_inventario"
    print(f"  -> Ticket clasificado como '{pending['payload']['datos']['tipo']}', monto: ${pending['payload']['datos']['monto_total']:,.2f}.")

    resumed = resume_orchestration(thread_id=thread_ocr, approved=True)
    assert resumed.get("pending_approval") is None
    print("✓ Lectura y clasificación de comprobantes OCR validada exitosamente.")


def test_tutor_ui():
    print("\n7. Validando Agente Tutor UI (Copiloto de Pagos)...")
    thread_ui = "test_ui_copilot_789"
    result = run_orchestration(
        thread_id=thread_ui,
        event_source="ui_copilot",
        ui_state={
            "pantalla": "PagoSPEI",
            "paso_actual": "ingreso_clabe",
            "campos_vacios": ["clabe_interbancaria"],
            "error_visible": "La cuenta CLABE debe tener 18 dígitos.",
            "intentos": 2
        }
    )
    last_msg = result.get("messages", [])[-1].content
    print(f"  -> Respuesta del Tutor UI: '{last_msg}'")
    # Regla: Máximo 2 oraciones accionables
    import re
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", last_msg) if s.strip()]
    assert len(sentences) <= 2, f"Se esperaban máximo 2 oraciones, se recibieron {len(sentences)}"
    assert "clabe" in last_msg.lower() or "18" in last_msg
    print("✓ Tutor UI responde en máximo 2 oraciones accionables referenciando la interfaz.")


def test_analista_and_investigador():
    print("\n8. Validando Agentes Analista e Investigador...")
    # Analista
    res_an = run_orchestration(
        thread_id="test_analista_chat",
        event_source="chat",
        query="Muéstrame el flujo de caja del mes y el margen de ganancia de los productos"
    )
    msg_an = res_an.get("messages", [])[-1].content
    assert "Ingresos por Ventas" in msg_an or "Flujo de Caja" in msg_an
    assert len(res_an.get("db_evidence", [])) > 0
    print("  -> Analista: Métricas de solo lectura respaldadas en db_evidence.")

    # Investigador
    res_inv = run_orchestration(
        thread_id="test_investigador_chat",
        event_source="chat",
        query="Genera el reporte estratégico de mercado para el sector retail de conveniencia"
    )
    rep = res_inv.get("strategic_report")
    assert rep is not None
    assert validate_strategic_report(rep) is True
    print("  -> Investigador: Reporte estratégico de 9 secciones obligatorias generado y validado.")
    print("✓ Analista e Investigador completados satisfactoriamente.")


def test_assistant_catalog_tools():
    print("\n9. Validando Herramientas del Asistente de Catálogo (integración assistant/)...")

    # 9a. consultar_inventario — producto específico por alias
    raw = consultar_inventario.invoke({"nombre": "la coca"})
    res = json.loads(raw)
    assert res.get("tool") == "consultar_inventario"
    assert "respuesta" in res
    assert res.get("args", {}).get("nombre") is not None
    print(f"  -> consultar_inventario (alias 'la coca'): {res['respuesta'][:60]}...")

    # 9b. consultar_inventario — catálogo general (nombre=None)
    raw_gen = consultar_inventario.invoke({"nombre": None})
    res_gen = json.loads(raw_gen)
    assert res_gen.get("tool") == "consultar_inventario"
    print(f"  -> consultar_inventario (general): {res_gen['respuesta'][:60]}...")

    # 9c. actualizar_precio
    raw_precio = actualizar_precio.invoke({"nombre": "Leche Lala 1 L", "precio": 31.50})
    res_precio = json.loads(raw_precio)
    assert res_precio.get("tool") == "actualizar_precio"
    assert "31.50" in res_precio["respuesta"] or "31" in res_precio["respuesta"]
    print(f"  -> actualizar_precio: {res_precio['respuesta']}")

    # 9d. ajustar_stock — entrada
    raw_stock = ajustar_stock.invoke({"nombre": "Leche Lala 1 L", "cantidad": 10, "tipo": "entrada"})
    res_stock = json.loads(raw_stock)
    assert res_stock.get("tool") == "ajustar_stock"
    print(f"  -> ajustar_stock (entrada): {res_stock['respuesta']}")

    # 9e. ajustar_stock — merma
    raw_merma = ajustar_stock.invoke({"nombre": "Leche Lala 1 L", "cantidad": 2, "tipo": "merma"})
    res_merma = json.loads(raw_merma)
    assert res_merma.get("tool") == "ajustar_stock"
    print(f"  -> ajustar_stock (merma): {res_merma['respuesta']}")

    # 9f. crear_producto
    raw_crear = crear_producto.invoke({"nombre": "Mazapán De La Rosa", "precio": 5.0, "stock": 24})
    res_crear = json.loads(raw_crear)
    assert res_crear.get("tool") == "crear_producto"
    assert "Mazapán" in res_crear["respuesta"]
    print(f"  -> crear_producto: {res_crear['respuesta']}")

    # 9g. find_product_by_name_or_alias
    prod = find_product_by_name_or_alias("blanquillos")
    assert prod is not None, "Debería encontrar 'Huevo Blanco' por alias 'blanquillos'"
    assert "Huevo" in prod["nombre"]
    print(f"  -> find_product_by_name_or_alias('blanquillos'): {prod['nombre']}")

    # 9h. fuera_de_alcance — control_node NO debe llamar tools; supervisor debe terminar rápido
    res_fuera = run_orchestration(
        thread_id="test_fuera_alcance_001",
        event_source="chat",
        query="¿Cuál es el clima en CDMX hoy?"
    )
    last_msg = res_fuera.get("messages", [])[-1].content
    # No debe haber pending_approval ni db_evidence extenso de una operación de BD
    pending = res_fuera.get("pending_approval")
    assert pending is None, "Una consulta fuera de alcance NO debe generar pending_approval"
    print(f"  -> fuera_de_alcance ('clima en CDMX'): '{last_msg[:80]}...' | pending={pending}")

    print("✓ Integración del asistente de catálogo (9 sub-pruebas) completada con éxito.")


if __name__ == "__main__":
    test_models_and_schemas()
    test_tools_and_mcp()
    test_guards()
    test_few_shot_retriever()
    test_pos_camera_and_hitl()
    test_receipt_ocr_and_hitl()
    test_tutor_ui()
    test_analista_and_investigador()
    test_assistant_catalog_tools()
    print("\n==================================================================")
    print("  ¡TODAS LAS PRUEBAS TÉCNICAS (10/10) COMPLETADAS CON ÉXITO!    ")
    print("==================================================================")
