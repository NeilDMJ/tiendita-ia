"""API del catálogo. Los servicios de IA son MOCK hasta tener los modelos entrenados
(declarar como simulados en la ficha). Variables: VISION_URL, LLM_URL."""
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from . import agents, db, tools

app = FastAPI(title="Tiendita IA - catálogo")
db.init()

VISION_URL = os.getenv("VISION_URL")  # p.ej. http://servidor:8001/detect
LLM_URL = os.getenv("LLM_URL")        # p.ej. http://servidor:8000/v1 (NIM/vLLM)


async def detectar(imagen: bytes) -> list[dict]:
    if not VISION_URL:  # MOCK
        return [{"clase": "desconocido", "confianza": 0.0, "simulado": True}]
    raise NotImplementedError("llamar al servicio de visión (TensorRT)")


# El SYSTEM_PROMPT del catálogo y la llamada al LLM viven ahora en backend/agents/control.py
# y backend/agents/base.py (el orquestador usa el mismo modelo para todos los agentes).


@app.post("/vision/detect")
async def vision_detect(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "imagen vacía")
    try:
        return {"detecciones": await detectar(data)}
    except Exception as e:
        raise HTTPException(502, f"servicio de visión no disponible: {e}")


class Mensaje(BaseModel):
    texto: str
    sesion_id: str = "default"


@app.post("/chat")
async def chat(m: Mensaje):
    """Un solo chat: el orquestador elige al agente. Las lecturas se ejecutan; las escrituras
    devuelven una PROPUESTA (requiere_confirmacion) y no se ejecutan hasta /confirmar."""
    try:
        return await agents.atender(m.texto, m.sesion_id)
    except Exception as e:
        raise HTTPException(502, f"asistente no disponible: {e}")


class Accion(BaseModel):
    tool: str
    args: dict
    agente: str | None = None  # informativo (etiqueta); el dueño de la tool lo da el registro
    sesion_id: str = "default"


@app.post("/confirmar")
def confirmar(a: Accion):
    try:
        return agents.confirmar(a.tool, a.args, a.sesion_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:  # p.ej. nombre duplicado
        raise HTTPException(409, str(e))


@app.get("/alertas")
def alertas():
    """Avisos proactivos de los agentes (stock bajo, por caducar, pagos sin conciliar)."""
    return agents.alertas()


@app.get("/carrito/{sesion_id}")
def carrito(sesion_id: str):
    return agents.sesion(sesion_id)


@app.get("/productos")
def productos():
    return tools.ejecutar("consultar_inventario", {})["productos"]
