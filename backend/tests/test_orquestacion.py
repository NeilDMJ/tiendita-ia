"""Flujo del orquestador en modo mock (sin LLM): ruteo, venta + pago, validaciones."""
import asyncio
from datetime import date, timedelta

import pytest

from backend import agents, db, tools
from backend.agents import orquestador


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.delenv("LLM_URL", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    db.init()
    orquestador.SESIONES.clear()
    pronto = (date.today() + timedelta(days=3)).isoformat()
    for n, pr, co, st, cad in [("Coca-Cola 600 ml", 20, 15, 10, None), ("Gansito Marinela", 18, 12, 3, pronto),
                               ("Pan de caja Bimbo", 45, 30, 4, None)]:
        tools.ejecutar("crear_producto", {"nombre": n, "precio": pr, "costo": co, "stock": st,
                                          "caducidad": cad, "clase_vision": None})


def chat(texto, sid="s"):
    return asyncio.run(agents.atender(texto, sid))


@pytest.mark.parametrize("texto,agente", [
    ("¿cuántos Gansitos me quedan?", "control"), ("cóbrame 2 Cocas", "vendedor"),
    ("¿cómo me fue hoy?", "analista"), ("arma una promo del pan", "publicista"),
    ("precio de referencia de la Coca", "investigador"), ("sube la Coca a $22", "control"),
])
def test_ruteo(texto, agente):
    assert chat(texto)["agente"] == agente


def test_venta_digital_completa():
    r = chat("cóbrame 2 Cocas y 1 Gansito")
    assert r["tool"] == "agregar_al_carrito" and "Total: $58" in r["respuesta"]
    r = chat("transferencia")
    assert r["requiere_confirmacion"] and r["tool"] == "registrar_venta"
    assert tools.ejecutar("consultar_inventario", {"nombre": "Coca"})["productos"][0]["stock"] == 10  # aún no escribe
    r = chat("sí")
    assert r["resultado"]["venta_id"] == 1 and r["resultado"]["estado_pago"] == "pendiente"
    assert tools.ejecutar("consultar_inventario", {"nombre": "Coca"})["productos"][0]["stock"] == 8
    r = chat("ya llegó, referencia 99887")
    assert r["agente"] == "vendedor" and r["requiere_confirmacion"]
    assert chat("sí")["resultado"]["estado"] == "recibido"
    assert "1 pagos recibidos" in chat("cierre de caja")["respuesta"]
    assert chat("concilia los pagos")["requiere_confirmacion"]
    assert chat("sí")["resultado"]["conciliados"] == 1
    assert "Ventas (hoy): 1" in chat("¿cómo me fue hoy?")["respuesta"]


def test_pide_metodo_y_stock_insuficiente():
    chat("cóbrame 1 Coca")
    r = chat("cobrar")
    assert r["faltantes"] == ["falta metodo_pago"] and not r["requiere_confirmacion"]
    assert "Solo te quedan" in chat("agrega 50 cocas")["respuesta"]


def test_cancelar_no_escribe():
    chat("cóbrame 1 Coca")
    chat("efectivo")
    assert chat("no")["respuesta"].startswith("Cancelado")
    assert tools.ejecutar("consultar_inventario", {"nombre": "Coca"})["productos"][0]["stock"] == 10


def test_negativos_422():
    with pytest.raises(ValueError):
        agents.confirmar("registrar_venta", {"items": [{"nombre": "Coca", "cantidad": 99}], "metodo_pago": "efectivo"})
    with pytest.raises(ValueError):
        agents.confirmar("registrar_venta", {"items": [{"nombre": "Coca", "cantidad": 1}], "metodo_pago": "bitcoin"})
    with pytest.raises(ValueError):
        agents.confirmar("borrar_todo", {})
    assert tools.ejecutar("consultar_inventario", {"nombre": "Coca"})["productos"][0]["stock"] == 10


def test_promocion_delega_en_control_y_alertas():
    r = chat("arma una promo")
    assert r["tool"] == "generar_promocion" and "Gansito" in r["respuesta"] and r["delegaciones"] == ["control"]
    assert any(a["tipo"] == "stock_bajo" for a in agents.alertas())


def test_reporte_marca_fuentes():
    chat("cóbrame 2 Cocas")
    chat("efectivo"); chat("sí")
    r = chat("hazme un reporte")
    assert r["tool"] == "generar_reporte" and "[externa]" in r["respuesta"] and "[bd]" in r["respuesta"]
    assert chat("gasté $50 en bolsas")["requiere_confirmacion"]
