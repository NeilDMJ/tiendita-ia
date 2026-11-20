# Modelo de visión — clasificador de productos

**Tarea visual (bases §7, "clasificar imágenes"):** reconocer qué producto aparece en la foto, uno a la vez, como un lector de códigos en el cobro. Clase extra `fondo` = "no hay producto".
**Modelo base:** YOLO11n-cls (Ultralytics, preentrenado en ImageNet-1k, licencia AGPL-3.0) → ajuste fino a 11 productos + fondo.
**Herramienta NVIDIA:** TensorRT (optimización FP16 para el despliegue). Entrenamiento en GPU NVIDIA del DLI (Tesla T4).

¿Por qué clasificación y no detección? El flujo de cobro escanea un producto a la vez, y la clasificación no necesita dibujar cajas: **el nombre del video es la etiqueta**. Ahorra horas de etiquetado y entrena en minutos.

## Flujo

| Paso | Dónde | Comando | Evidencia que deja |
|---|---|---|---|
| 1. Videos | celulares | ver [`GUIA_VIDEOS.md`](GUIA_VIDEOS.md) | `videos/sN/sN_<clase>.mp4` |
| 2. Extraer fotos | laptop (sin gastar GPU) | `python preparar_videos.py videos/` | `raw/<sesion>/<clase>/*.jpg` |
| 3. Revisar | laptop | abrir carpetas, borrar fotos donde no se ve el producto | — |
| 4. División | laptop o DLI | `python split.py --train s1 --test s2` | `dataset/estadisticas.json` |
| 5. Entrenamiento | DLI (T4) | `python train.py --nombre v1` | `artefactos/v1/registro.json`, `best.pt` |
| 6. Evaluación | DLI | `python eval.py --nombre v1` | `artefactos/v1/eval/` |
| 7. TensorRT | DLI | `python export_trt.py --nombre v1` | `best.engine`, `benchmark.json` |

Los pasos 4–7 están encadenados en **`entrenar_vision.ipynb`**: subirlo al JupyterLab del DLI y correr celda por celda.

## En la laptop (pasos 2–4)

```bash
pip install opencv-python pillow
cd vision
python preparar_videos.py ~/Descargas/videos     # carpeta con s1/ s2/ s3/ s4/
python split.py --train s1 --test s2              # prueba local: detecta errores antes de prender la GPU
zip -r ../raw.zip raw                              # sube raw.zip al DLI
cd .. && zip -r vision.zip vision -x 'vision/.venv/*' 'vision/raw/*' 'vision/videos/*' 'vision/dataset/*' 'vision/runs/*' 'vision/artefactos/*' '*/__pycache__/*'
```

- `preparar_videos.py` saca 1 foto cada 0.5 s, descarta las borrosas, quita metadatos (GPS) y avisa si un video salió horizontal o muy movido.
- Hay **2 sesiones** (una por iluminación). s1 entrena y s2 completa es la prueba. Val sale del último 20 % de cada video de s1, con un hueco de 2 s descartado para que no haya fotos casi iguales en train y val; queda registrado en `estadisticas.json → validacion`. Con 4 sesiones se usa `--train s1,s2 --val s3 --test s4`.
- Una sesión completa va a **un solo** conjunto (bases §7). `split.py` además busca fotos casi idénticas entre conjuntos y se detiene si las encuentra.
- Demo en vivo ("procesar una imagen nueva", bases §15): la foto se toma en el momento, en un lugar que no aparezca en ninguna sesión. El producto sí debe ser uno de los 11 entrenados.

## Entorno DLI (verificado)

Tesla T4 16 GB · driver 545.23 (CUDA ≤ 12.3) · Ubuntu 22.04 · Python 3.10 · sin torch preinstalado.
PyTorch se instala desde el índice **cu121** (`torch==2.5.1`); el de PyPI exige un driver más nuevo.

- **Descargar `artefactos_v1.zip` al terminar**: los archivos del entorno pueden perderse.
- El `.engine` solo corre en una T4 con la misma versión de TensorRT. Para servir en otra GPU, regenerarlo desde `best.onnx`; como respaldo sin GPU, `best.onnx` corre en CPU con onnxruntime (declararlo).

## Mapa a los entregables

| Bases | Archivo |
|---|---|
| §14-C Modelo base | `registro.json → modelo_base` |
| §14-C Datos y distribución | `dataset/estadisticas.json` (copia en `artefactos/v1/estadisticas_datos.json`) |
| §14-C Configuración | `registro.json → parametros`, `resultados/args.yaml` |
| §14-C Registro (fecha, duración, GPU, épocas) | `registro.json`, notebook con salidas |
| §14-C Artefacto | `best.pt` (+ `best.engine`) y su SHA-256 |
| §13 Métrica y cómo se calculó | `eval/metricas.json`, docstring de `eval.py` |
| §13 Aciertos y errores | `eval/aciertos/`, `eval/errores/` |
| §13 Comparación con modelo base | `eval/metricas.json → comparacion_modelo_base` |
| §9 Herramienta NVIDIA y su función | `benchmark.json` (PyTorch vs TensorRT) |
| §6c Relación pesos ↔ app | SHA-256 en `registro.json`; el backend debe exponerlo |
| §6d Revisión y corrección | `metricas.json → umbral_de_confianza`: bajo el umbral, la app pide confirmar |
