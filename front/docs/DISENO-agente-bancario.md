# Diseño del agente guía bancario (Hackathon NVIDIA)

> Estado: documento de diseño. No incluye código. Los nombres de modelos y servicios de NVIDIA deben contrastarse con la documentación vigente (build.nvidia.com, docs.nvidia.com) antes de implementar.

## 0. Contexto y restricciones

La app del tendero suma un agente que **guía paso a paso** al usuario en operaciones de cualquier app bancaria (transferencias, pago de servicios, saldo, revisión de cobros).

- Las apps bancarias bloquean overlays y capturas de pantalla → el agente vive en un **chat independiente dentro de nuestra app**; el usuario alterna entre ambas apps.
- El agente **nunca accede** a la app del banco ni a datos reales de la cuenta.
- Privacidad primero: lo que salga del dispositivo debe estar anonimizado.
- Debe funcionar en móvil (Expo) y aprovechar herramientas NVIDIA.

Piezas ya existentes en el front que se reutilizan:

| Pieza | Archivo |
|---|---|
| Pantalla del asistente (placeholder) | `front/src/app/(tabs)/asistente.tsx` |
| Cliente de API (`enviarMensaje`) | `front/src/api/asistente.ts` |
| Esquemas zod (`MensajeAsistente`, `EstadoPantalla`) | `front/src/api/esquemas.ts` |
| Mock del asistente (`mockRespuestaAsistente`) | `front/src/api/mocks/index.ts` |
| Cliente HTTP, timeout, `ErrorApi`, flag `USAR_MOCKS` | `front/src/api/cliente.ts` |
| Sistema de diseño (flat, texto ≥ 16 px, sin jerga de IA) | `front/docs/diseno/00-sistema.md` |

## 1. Arquitectura propuesta

```
App Expo (chat) ──HTTPS──► Backend FastAPI propio ──► NIM (build.nvidia.com / servidor del concurso)
   │                          │  1. Anonimizador (regex + NER)
   │                          │  2. Guardrails (NeMo Guardrails)
   │                          │  3. RAG sobre guías verificadas (NeMo Retriever / embeddings NIM)
   │                          └─ 4. Validación de salida (esquema JSON)
   └─ Caché local SQLite (guías, historial sin datos sensibles)
```

### Modelo de razonamiento
- **Prototipo:** LLM instruct servido por **NIM** (API compatible con OpenAI) en build.nvidia.com, p. ej. familia Llama 3.x Instruct o Nemotron. Si el concurso proporciona servidor, se apunta ese endpoint cambiando solo la URL base: el resto no cambia.
- **Producción:** modelo 8B (o menor) cuantizado con **TensorRT-LLM**, desplegado como NIM en servidor propio; opción on-device para dispositivos de gama alta con un modelo pequeño. Así ningún texto del usuario sale a terceros.

### Voz (opcional, segunda fase)
- **NVIDIA Riva** ASR/TTS en español como servicio (gRPC/HTTP) detrás del backend.
- En el prototipo: omitir voz o usar STT/TTS del dispositivo. Requiere dependencia nueva (`expo-audio`, instalar con `npx expo install`; hoy `app.json` tiene `recordAudioAndroid:false`, habría que habilitar el permiso de micrófono).

### Integración móvil
- `asistente.tsx` renderiza burbujas planas; envía el texto con `enviarMensaje` → `/asistente/mensaje`.
- El backend responde con JSON estructurado (§2) y la app lo pinta como lista de pasos numerados + advertencias + botones de respuesta rápida.
- Se mantiene el patrón `USAR_MOCKS` para trabajar sin backend.

### Prototipo vs. producción

| Componente | Hackathon (prototipo) | Producción |
|---|---|---|
| LLM | NIM hospedado, prompt + few-shot | NIM propio / TensorRT-LLM, LoRA |
| Guías | 3–5 bancos × 4 operaciones, curadas a mano | Pipeline de verificación continua |
| RAG | Búsqueda por banco+operación (casi exacta) | NeMo Retriever + reranking |
| Guardrails | Reglas básicas de alcance en prompt + filtro | NeMo Guardrails con rieles completos |
| Anonimización | Regex (tarjeta, CLABE, montos, teléfono) | NER + auditoría + pruebas de fuga |
| Voz | Omitida o STT del dispositivo | Riva ASR/TTS |
| Telemetría | Ninguna con contenido | Métricas agregadas sin texto |

## 2. Cómo entiende los flujos sin datos reales

### Base de conocimiento de guías
El modelo **no inventa** pasos: los toma de guías curadas por banco y operación.

```yaml
banco: BBVA
operacion: transferencia_spei
version_app: "verificar"          # versión de la app contra la que se validó
verificado_en: "AAAA-MM-DD"       # fecha de la última verificación manual
pasos:
  - pantalla: Inicio
    elemento: "Transferir"        # texto del botón tal como aparece (por verificar)
    accion: Tocar
    aviso: null
  - pantalla: Transferir
    elemento: "A otra cuenta"
    accion: Elegir destinatario o agregar uno nuevo
    aviso: "Verifica el nombre del beneficiario antes de seguir."
```

### Flujo de una consulta
1. El usuario escribe (o dicta) su petición.
2. **Anonimizador local/backend** sustituye datos sensibles por placeholders.
3. Se detectan `banco` y `operacion` (clasificación del LLM con salida estructurada).
4. **RAG:** se recupera la guía exacta. Si no existe, se marca como "guía genérica sin verificar".
5. El LLM redacta con tono conversacional **solo a partir de los pasos recuperados**.
6. Validación de esquema; si falla, un reintento y luego respuesta segura de respaldo.

### Salida estructurada (zod en el front)
```json
{
  "intencion": "transferencia",
  "banco": "BBVA",
  "pasos": [{ "n": 1, "texto": "…", "pantalla": "Inicio" }],
  "advertencias": ["…"],
  "guia_verificada": true,
  "necesita_aclaracion": false,
  "respuestas_rapidas": []
}
```

### Anonimización (si se usa API alojada)
- Antes de enviar a NIM se eliminan o enmascaran: números de tarjeta, CLABE, números de cuenta, montos, nombres propios, teléfonos, correos → `[TARJETA]`, `[CLABE]`, `[MONTO]`, etc.
- El modelo no necesita cifras para guiar: los pasos no dependen del monto ni del beneficiario.
- Se guarda el texto original solo en el dispositivo; el backend no registra el contenido de los mensajes.
- Si el anonimizador detecta algo que no puede enmascarar con seguridad, **bloquea el envío** y pide al usuario reformular.

## 3. Diseño de la experiencia conversacional

### Tono
- Cercano, claro y breve; español de México, tuteo.
- Pasos numerados cortos (una acción por paso), sin jerga técnica ni de IA (conforme a `00-sistema.md`).
- Siempre indica **en qué pantalla** debe estar el usuario en cada paso.

### Confirmaciones de seguridad
- Aviso fijo al iniciar cualquier operación: *"No compartas aquí tu NIP, token, CVV ni contraseñas. Yo nunca te los pediré."*
- Antes de cada paso irreversible: *"Revisa en tu app del banco el nombre del beneficiario y el monto antes de confirmar."*
- Aviso anti-fraude: el banco nunca pide claves por mensaje o llamada.
- El agente nunca confirma que una operación "ya se hizo": no tiene forma de saberlo.

### Fuera de alcance
- Asesoría de inversión, crédito o fiscal; soporte técnico del banco; consulta de datos reales de la cuenta; cualquier tema ajeno a la banca.
- Respuesta tipo: *"Eso no lo puedo resolver desde aquí. Para eso lo mejor es contactar a tu banco por sus canales oficiales. ¿Te ayudo con alguna operación paso a paso?"*
- Implementación: rieles de NeMo Guardrails (tema permitido/bloqueado) + prompt de sistema.

### Desambiguación
- Si falta banco u operación, **una sola** pregunta con botones de respuesta rápida (p. ej. BBVA · Banorte · Santander · Otro).
- Si el banco no está en la base: guía genérica claramente marcada ("pasos generales, pueden variar en tu app").

### Estados de la pantalla
Vacío (sugerencias de ejemplo), cargando, error (`ErrorApi.mensaje`), sin conexión (guías en caché) y éxito, como exige `PLAN-frontend.md`.

## 4. Datos y ajuste fino

### Estrategia por fases
1. **Hackathon:** sin fine-tuning. Prompt de sistema + few-shot + RAG sobre guías. Es lo viable en el tiempo disponible.
2. **Después:** dataset sintético (generado con un modelo Nemotron/Llama y curado con **NeMo Curator**), ~500–2000 diálogos en JSONL, y **LoRA** con **NeMo Customizer** sobre un modelo ~8B para tono, formato y rechazo de fuera de alcance. Las guías siguen en RAG (no se "memorizan" en pesos, porque cambian).

### Formato de ejemplo (JSONL)
```json
{"messages":[
 {"role":"system","content":"Eres un guía bancario. Solo usas las guías proporcionadas. Nunca pides NIP, token ni CVV."},
 {"role":"user","content":"Quiero realizar una transferencia. Utilizo BBVA, ¿cómo lo hago?"},
 {"role":"assistant","content":"…respuesta de abajo…"}
]}
```

### Caso de referencia
**Usuario:** "Quiero realizar una transferencia. Utilizo BBVA, ¿cómo lo hago?"

**Agente:**
> ¡Claro! Te guío paso a paso. Abre tu app de BBVA e inicia sesión como lo haces normalmente. *(Recuerda: aquí nunca me compartas tu NIP ni tu token.)*
>
> 1. En la **pantalla principal**, busca la opción **Transferir** (o "Enviar dinero") y tócala.
> 2. Elige a **quién** le vas a enviar: un contacto guardado o **agregar una cuenta nueva**.
> 3. Si es nueva, captura la CLABE, tarjeta o número de celular del destinatario **directamente en tu app**.
> 4. Escribe el **monto** y un **concepto** (por ejemplo, "pago de mercancía").
> 5. Revisa la pantalla de resumen: **nombre del beneficiario, monto y cuenta**.
> 6. Si todo está bien, toca **Confirmar** y autoriza con tu método de seguridad (huella, token o NIP).
> 7. Guarda el comprobante que muestra la app.
>
> Cuando llegues a algún paso y tu pantalla se vea distinta, dime qué opciones ves y lo ajustamos. ¿Ya estás en la pantalla principal?

> Nota: los nombres exactos de botones (“Transferir”, “Enviar dinero”) deben **verificarse manualmente** en la versión vigente de la app de BBVA y registrarse con `version_app` y `verificado_en` antes de mostrarse como guía verificada.

### Ejemplos adicionales a incluir en el dataset
- Pago de servicio (luz/agua/teléfono) en otro banco.
- Consulta de saldo y de movimientos.
- Revisión de si un cobro/depósito llegó.
- Banco desconocido → guía genérica marcada.
- El usuario pega su número de tarjeta → el agente rechaza, pide no compartirlo y continúa sin él.
- Pregunta fuera de alcance (inversiones, soporte) → redirección.
- "Mi pantalla no coincide" → pide describir lo que ve.

### Evaluación
- Pasos correctos frente a la guía de referencia (revisión manual + comparación automática).
- **Fuga de datos sensibles = 0** en un conjunto de pruebas adversariales.
- Rechazo correcto de fuera de alcance y de peticiones de claves.
- Latencia de respuesta en móvil (objetivo orientativo: < 3 s al primer token).

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| **Privacidad:** datos sensibles enviados a una API externa | Anonimización previa y bloqueo si no se puede enmascarar; sin logs de contenido; consentimiento visible; camino a modelo propio (NIM local / TensorRT-LLM) |
| **Alucinación de pasos** inexistentes en la app | RAG obligatorio sobre guías verificadas; el modelo solo parafrasea; "no lo sé" permitido; guía genérica marcada; evaluación periódica |
| **Cambios de interfaz del banco** | Versionado y fecha de verificación por guía; botón "esto no coincide" que reporta y pide describir la pantalla; revisión manual periódica |
| **Fraude / suplantación** (alguien usa el chat para pedir claves) | El agente jamás solicita credenciales; avisos fijos; rieles que bloquean peticiones de claves |
| **Fiabilidad sin conexión** | Guías y respuestas frecuentes en caché SQLite; aviso de modo sin conexión (`AvisoConexion` ya existe) |
| **Latencia y costo de API** | Modelo pequeño, caché por banco/operación, respuestas cortas |
| **Responsabilidad:** el usuario cree que el agente ejecuta la operación | Mensajes claros: el agente solo guía; nunca confirma que algo se realizó |

## 6. Plan del hackathon

1. **Base:** backend FastAPI mínimo con `/asistente/mensaje`, conexión a NIM y flag de mocks.
2. **Guías:** redactar y verificar a mano 3–5 bancos × (transferencia, pago de servicio, saldo, revisión de cobros).
3. **Seguridad:** anonimizador por regex y rieles básicos de alcance.
4. **Front:** pantalla de chat con pasos numerados, advertencias y respuestas rápidas.
5. **Demo:** caso BBVA de punta a punta + intento de fuga de datos + pregunta fuera de alcance.
6. **Si hay tiempo:** voz con Riva, evaluación automática, LoRA.

## 7. Puntos de integración en el front (para una fase posterior)

- `front/src/app/(tabs)/asistente.tsx`: pantalla de chat.
- `front/src/api/asistente.ts`: llamada al nuevo endpoint y rama de mock.
- `front/src/api/esquemas.ts`: esquema zod de la salida estructurada (§2).
- `front/src/api/mocks/index.ts`: mock que reproduzca el caso BBVA.
- `back/`: hoy vacío; alojaría FastAPI, anonimizador, RAG y guardrails.
