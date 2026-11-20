"""Utilidades compartidas: huellas de archivos y datos del entorno para los registros (entregable C)."""
import hashlib
import os
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# Plan B para entornos con cuDNN roto (DLI con dos cuDNN instalados): SIN_CUDNN=1 python train.py ...
# Entrena igual en GPU, solo sin cuDNN (más lento). Queda registrado en entorno()["cudnn"].
if os.environ.get("SIN_CUDNN"):
    import torch

    torch.backends.cudnn.enabled = False
ARTEFACTOS = AQUI / "artefactos"


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def entorno() -> dict:
    info = {"python": platform.python_version(), "so": platform.platform()}
    try:
        import torch

        info["torch"] = torch.__version__
        info["cudnn"] = torch.backends.cudnn.version() if torch.backends.cudnn.enabled else "desactivado (SIN_CUDNN)"
        info["cuda"] = torch.version.cuda
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except ImportError:
        pass
    try:
        import ultralytics

        info["ultralytics"] = ultralytics.__version__
    except ImportError:
        pass
    try:
        import tensorrt

        info["tensorrt"] = tensorrt.__version__
    except ImportError:
        pass
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def guardar_json(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str))
    print(f"Guardado: {ruta}")
