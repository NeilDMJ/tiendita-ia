# Servicio de visión

Expone a la app el clasificador de productos entrenado en NVIDIA DLI (`vision/artefactos/v1/best.onnx`).
Se monta dentro de la API de agentes (`enjambre_agentes/api.py`), así la app usa un solo `EXPO_PUBLIC_API_URL`.

## Levantar

```bash
cd enjambre_agentes
uv run uvicorn api:app --host 0.0.0.0 --port 8000
```

- Documentación interactiva: `http://localhost:8000/docs` → sección **Visión**.
- Desde el celular (misma red Wi-Fi): en `front/.env`
  ```
  EXPO_PUBLIC_API_URL=http://<IP-de-la-laptop>:8000
  EXPO_PUBLIC_USE_MOCKS=0
  ```
  La IP se ve con `ip -4 addr` (Linux). Si el celular no conecta, revisar el firewall del puerto 8000.

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
