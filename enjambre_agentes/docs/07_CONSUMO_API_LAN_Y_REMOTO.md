# 07 · Consumo de la API REST y WebSockets (Red Wi-Fi/LAN, Apps Móviles e Internet)

Guía práctica paso a paso para levantar el servidor de **Tiendita IA** en una PC host y consumir todos sus métodos desde **otra PC en la misma red Wi-Fi (LAN)**, una **app móvil** o **Internet** mediante túneles `ssh` nativos.

---

## 1. Paso a Paso: Levantar el Servidor en la PC Host

### Paso 1 — Arrancar el servidor (detecta tu IP Wi-Fi automáticamente)
En la PC donde vive `enjambre_agentes` (con `tiendita-db` activo):

```bash
cd /home/m4r10/Documents/tiendita-ia/enjambre_agentes

# Modo Red Local (Wi-Fi / LAN):
uv run python main.py --serve

# O con puerto personalizado:
uv run python main.py --serve --port 8000

# O exponiendo además a Internet sin instalar ngrok (túnel SSH nativo):
uv run python main.py --serve --tunnel               # localhost.run
uv run python main.py --serve --tunnel pinggy        # puerto 443 si el 22 está bloqueado
uv run python main.py --serve --tunnel vps           # usa SSH_VPS_TARGET de .env
```

Al arrancar, verás un panel `rich` con la IP local real detectada (ejemplo: `192.168.1.64`):
- **REST LAN:** `http://192.168.1.64:8000`
- **WebSocket LAN:** `ws://192.168.1.64:8000/ws/orchestrate`
- **Swagger interactivo:** `http://192.168.1.64:8000/docs`

### Paso 2 — Abrir el puerto en el firewall de Linux (si otra PC no conecta)
Si la otra PC en el mismo Wi-Fi no recibe respuesta, abre el puerto `8000` en la PC host:

```bash
# En Fedora / RHEL / Rocky (firewalld):
sudo firewall-cmd --add-port=8000/tcp --permanent && sudo firewall-cmd --reload

# En Ubuntu / Debian (ufw):
sudo ufw allow 8000/tcp
```

### Paso 3 — Autenticación opcional (`TIENDITA_API_KEY`)
En [.env](../.env):
- Si `TIENDITA_API_KEY=` está **vacía**, cualquier equipo en la LAN puede conectar sin header (ideal para pruebas rápidas).
- Si defines `TIENDITA_API_KEY=mi_clave_secreta`:
  - **REST:** enviar header `X-API-Key: mi_clave_secreta` (excepto `/health` y `/docs`, que son públicos).
  - **WebSocket:** conectar con `?api_key=mi_clave_secreta` o header `X-API-Key`.

---

## 2. Verificar Conectividad desde Otra PC en el Mismo Wi-Fi

Reemplaza `<IP_HOST>` por la IP mostrada en el panel (ej. `192.168.1.64`):

```bash
# 1. Prueba rápida desde navegador o curl (sin API key)
curl http://<IP_HOST>:8000/health

# 2. Abrir documentación interactiva Swagger desde el navegador de la otra PC:
# http://<IP_HOST>:8000/docs

# 3. Usar el cliente de prueba incluido (si la otra PC tiene el repo):
uv run python -m scripts.test_client --url http://<IP_HOST>:8000 --mode all
```

---

## 3. Catálogo Completo de Métodos y Ejemplos JSON

> Si tienes `TIENDITA_API_KEY` configurada, añade `-H "X-API-Key: <TU_CLAVE>"` a todos los comandos `curl` (excepto `/health`).

### A. Salud, Modelos y Herramientas MCP

```bash
# Estado del servidor y conexión en vivo a PostgreSQL
curl http://<IP_HOST>:8000/health

# Modelos disponibles por proveedor + estado de proveedores + cerebros activos
curl http://<IP_HOST>:8000/models

# Manifiesto MCP JSON de las 24 herramientas comerciales
curl http://<IP_HOST>:8000/tools/mcp
```

---

### B. Gestión de Cerebros por Subagente en Vivo (`/brains`)

```bash
# 1. Ver qué proveedor y modelo tiene cada uno de los 7 agentes
curl http://<IP_HOST>:8000/brains

# 2. Cambiar el cerebro de un subagente en runtime (sin reiniciar el servidor)
curl -X PUT http://<IP_HOST>:8000/brains/vendedor \
  -H "Content-Type: application/json" \
  -d '{"provider": "Gemini", "model_name": "gemini-flash-lite-latest"}'

# 3. Restaurar los 7 agentes a 100% NVIDIA NIM
curl -X POST http://<IP_HOST>:8000/brains/reset
```

---

### C. Orquestación Multiagente, Streaming SSE, HITL y Estado

#### 1. Consulta síncrona (`POST /orchestrate`)
```bash
curl -X POST http://<IP_HOST>:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "¿Cuáles son los 3 productos más vendidos?",
    "event_source": "chat"
  }'
```
Respuesta JSON típica:
```json
{
  "status": "completed",
  "thread_id": "f720b429-...",
  "next_agent": "analista",
  "reply": "[ANALISTA]: Los 3 productos más vendidos son...",
  "requires_approval": false,
  "pending_approval": null,
  "db_evidence": "...",
  "iteration_count": 2
}
```
> **Continuidad de sesión:** Guarda `thread_id` en tu app y envíalo en los siguientes turnos para mantener el historial conversacional.

#### 2. Streaming SSE en vivo (`POST /orchestrate/stream`)
```bash
curl -N -X POST http://<IP_HOST>:8000/orchestrate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "¿Cuánto cuesta la Coca-Cola 600 ml?",
    "thread_id": "mi-sesion-movil-1"
  }'
```

#### 3. Reanudación Human-in-the-Loop (`POST /orchestrate/resume`)
Cuando cualquier endpoint devuelva `"requires_approval": true`:
```bash
curl -X POST http://<IP_HOST>:8000/orchestrate/resume \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "<THREAD_ID_PAUSADO>",
    "approved": true,
    "correction": null,
    "notes": "Confirmado desde app móvil"
  }'
```
- `approved: true` → ejecuta el `COMMIT` real en PostgreSQL y registra la muestra para NeMo Customizer.
- `approved: false` → cancela la operación sin modificar la base de datos.

#### 4. Inspeccionar estado de sesión (`GET /state/{thread_id}`)
```bash
curl http://<IP_HOST>:8000/state/<THREAD_ID>
```

---

### D. Pagos Digitales México (CoDi / SPEI / DiMo) y RAG

#### 1. Copiloto de pantalla Tutor UI (`POST /pago` o `POST /ui-copilot`)
Responde en **máximo 2 oraciones accionables** respaldadas por el índice oficial de Banxico (`guias.json` + `conocimiento.jsonl`):
```bash
curl -X POST http://<IP_HOST>:8000/pago \
  -H "Content-Type: application/json" \
  -d '{
    "metodo_pago": "codi",
    "pantalla": "cobro_qr",
    "paso": 2,
    "error_code": "LIMITE_EXCEDIDO"
  }'
```

#### 2. Búsqueda directa en el RAG (`POST /rag/search` y `GET /rag/search`)
```bash
# Variante POST (JSON)
curl -X POST http://<IP_HOST>:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "límite de monto máximo sin comisión CoDi",
    "metodo_pago": "codi",
    "top_k": 3
  }'

# Variante GET rápida
curl "http://<IP_HOST>:8000/rag/search?q=cuando+se+rechaza+SPEI&metodo=spei&top_k=3"
```

---

### E. Visión Multimodal, Cron y Reportes Estratégicos

#### 1. Enviar imagen real desde cámara o disco (`POST /imagen`)
`mode` acepta `"catalog"`, `"pos"` o `"ticket"`:
```bash
IMG_B64=$(base64 -w 0 ./mi_foto.jpg)
curl -X POST http://<IP_HOST>:8000/imagen \
  -H "Content-Type: application/json" \
  -d "{
    \"image_b64\": \"$IMG_B64\",
    \"mode\": \"ticket\",
    \"mime_type\": \"image/jpeg\",
    \"filename\": \"mi_foto.jpg\"
  }"
```
También siguen disponibles los atajos especializados `POST /catalog-scan`, `POST /pos-checkout` y `POST /receipt-ocr`.

#### 2. Barrido de caducidades y stock crítico (`POST /cron`)
```bash
curl -X POST http://<IP_HOST>:8000/cron \
  -H "Content-Type: application/json" \
  -d '{"days_ahead": 7}'
```

#### 3. Reportes estratégicos históricos (`GET /reports/history` y `GET /reports/{report_id}`)
```bash
curl http://<IP_HOST>:8000/reports/history
curl http://<IP_HOST>:8000/reports/<REPORT_ID>
```

---

## 4. WebSocket Bidireccional en Tiempo Real (`ws://<IP_HOST>:8000/ws/orchestrate`)

Ideal para **apps móviles y frontends web**: transmite cada nodo en vivo y permite resolver pausas **HITL** dentro del mismo socket sin reconectar.

### Ejemplo en Python (desde otra PC)
```python
import asyncio, json, websockets

async def main():
    url = "ws://192.168.1.64:8000/ws/orchestrate"  # añade ?api_key=... si TIENDITA_API_KEY está activa
    async with websockets.connect(url) as ws:
        hello = json.loads(await ws.recv())
        print("Conectado:", hello)

        # Enviar instrucción (event_source: chat | vision_api | ui_copilot | cron_trigger)
        await ws.send(json.dumps({
            "message": "",
            "event_source": "cron_trigger",
            "thread_id": hello["thread_id"],
        }))

        while True:
            ev = json.loads(await ws.recv())
            if ev["type"] == "node_update":
                print("Nodo:", ev["node"])
            elif ev["type"] == "hitl_required":
                print("Aprobación requerida:", ev["approval"])
                # Responder en el MISMO socket: "approve" o "reject"
                await ws.send(json.dumps({"action": "approve", "notes": "Aprobado desde cliente remoto"}))
            elif ev["type"] in ("hitl_resolved", "completed"):
                print("Respuesta final:", ev["result"]["reply"])
                break

asyncio.run(main())
```

### Ejemplo en JavaScript / React Native / Web
```javascript
const ws = new WebSocket("ws://192.168.1.64:8000/ws/orchestrate");

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "connected") {
    ws.send(JSON.stringify({
      message: "¿Cuáles son los 3 productos más vendidos?",
      event_source: "chat",
      thread_id: msg.thread_id
    }));
  } else if (msg.type === "node_update") {
    console.log("Avance nodo:", msg.node);
  } else if (msg.type === "hitl_required") {
    // Mostrar confirmación al usuario y enviar en el mismo socket:
    ws.send(JSON.stringify({ action: "approve", notes: "Confirmado en móvil" }));
  } else if (msg.type === "completed" || msg.type === "hitl_resolved") {
    console.log("Respuesta:", msg.result.reply);
  }
};
```
