# Servicio de visión

Expone a la app el clasificador de productos entrenado en NVIDIA DLI (`vision/artefactos/v1/best.onnx`).
Corre de forma independiente en el puerto **`8001`** (`VISION_PORT`, configurable) para no interferir con la API del enjambre de agentes (`8000`).
*(Si en algún momento deseas volver a montarlo en el mismo puerto `8000` junto al enjambre, define `MOUNT_VISION_IN_API=1` en `enjambre_agentes/.env`).*

## Levantar (puerto 8001)

```bash
cd back
../enjambre_agentes/.venv/bin/python -m vision.server

# O con uvicorn directo / otro puerto:
VISION_PORT=8001 ../enjambre_agentes/.venv/bin/uvicorn vision:app --host 0.0.0.0 --port 8001
```

- Documentación interactiva: `http://localhost:8001/docs` → sección **Visión**.
- Desde el celular (misma red Wi-Fi): usar `http://<IP-de-la-laptop>:8001` para `/vision/*` (y `http://<IP-de-la-laptop>:8000` para el enjambre).
  La IP se ve con `ip -4 addr` (Linux). Si el celular no conecta, revisar el firewall del puerto `8001`.

## Endpoints

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| POST | `/vision/pos-checkout` | multipart `imagen` | `{imagen_id, items[], clase_modelo}` |
| POST | `/vision/catalog-scan` | multipart `imagen` | `{items[], categoria, caducidad_ocr}` |
| POST | `/vision/receipt-ocr` | multipart `imagen` | **simulación** (`simulacion: true`) |
| GET | `/vision/salud` | — | clases, umbral, catálogo y SHA-256 de `best.onnx` / `best.pt` |

Cada ítem: `sku, nombre, cantidad (1), precio_unitario, confianza, requiere_confirmacion, alternativas[]`
(contrato en `front/src/api/esquemas.ts`).

- **Un producto por foto**: el modelo clasifica, no detecta; `cantidad` = 1 y no hay `caja`.
- **`fondo`** (no hay producto) → `items: []`.
- **Confianza < 0.6** (`VISION_UMBRAL`) → el ítem llega con `requiere_confirmacion: true` y alternativas;
  la pantalla de revisión le pide al tendero confirmar o corregir.
- **Errores**: foto ilegible o vacía → `422`; más de 15 MB → `413`; modelo ausente → `503` en `/salud`.
- **Privacidad**: la foto se procesa en memoria y no se guarda.

## Modelo

- `best.onnx` con onnxruntime (CPU, ~8 ms por foto con HTTP; usa CUDA si está `onnxruntime-gpu`).
  El `.engine` de TensorRT solo corre en la T4 del DLI; su benchmark está en `vision/artefactos/v1/benchmark.json`.
- Otro modelo: `VISION_MODELO=/ruta/best.onnx`. Las clases se leen de los metadatos del ONNX.
- Clase → producto: `catalogo_vision.json`. Los mismos SKU y la columna `clase_vision` están en `back/datos/catalogo.csv` (semilla de Postgres que usan los agentes).
- Verificado: las 801 fotos de test (sesión s2) por `/vision/pos-checkout` dan **95.26 %**, igual que
  `eval.py` en el DLI (mismo preprocesamiento que Ultralytics).
