#!/usr/bin/env python3
"""Fusiona el adaptador LoRA local, lo convierte a GGUF Q8_0 y lo registra en Ollama.

Uso:
    .venv/bin/python scripts/export_lora_ollama.py --gguf-converter /ruta/a/llama.cpp/convert_hf_to_gguf.py
    .venv/bin/python scripts/export_lora_ollama.py --skip-merge --model-name tiendita-lora-v1
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ADAPTER_DIR = ROOT / "data" / "loras" / "tiendita_lora_v1"
DEFAULT_MERGED_DIR = ROOT / "data" / "loras" / "tiendita_lora_v1_merged"
BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

QWEN_MODELFILE_TEMPLATE = '''FROM ./{gguf_filename}

TEMPLATE """{{{{- if .Messages }}}}
{{{{- if or .System .Tools }}}}<|im_start|>system
{{{{- if .System }}}}
{{{{ .System }}}}
{{{{- end }}}}
{{{{- if .Tools }}}}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{{{- range .Tools }}}}
{{"type": "function", "function": {{{{ .Function }}}}}}
{{{{- end }}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>
{{{{- end }}}}<|im_end|>
{{{{ end }}}}
{{{{- range $i, $_ := .Messages }}}}
{{{{- $last := eq (len (slice $.Messages $i)) 1 -}}}}
{{{{- if eq .Role "user" }}}}<|im_start|>user
{{{{ .Content }}}}<|im_end|>
{{{{ else if eq .Role "assistant" }}}}<|im_start|>assistant
{{{{ if .Content }}}}{{{{ .Content }}}}
{{{{- else if .ToolCalls }}}}<tool_call>
{{{{ range .ToolCalls }}}}{{"name": "{{{{ .Function.Name }}}}", "arguments": {{{{ .Function.Arguments }}}}}}
{{{{ end }}}}</tool_call>
{{{{- end }}}}{{{{ if not $last }}}}<|im_end|>
{{{{ end }}}}
{{{{- else if eq .Role "tool" }}}}<|im_start|>user
<tool_response>
{{{{ .Content }}}}
</tool_response><|im_end|>
{{{{ end }}}}
{{{{- if and (ne .Role "assistant") $last }}}}<|im_start|>assistant
{{{{ end }}}}
{{{{- end }}}}
{{{{- else }}}}
{{{{- if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ end }}}}{{{{ .Response }}}}{{{{ if .Response }}}}<|im_end|>{{{{ end }}}}"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

SYSTEM """Eres el asistente de Tiendita IA para tiendas de abarrotes en México. Responde en español claro, directo y en máximo 2 oraciones accionables para dudas de pagos digitales (CoDi, SPEI, DiMo) u operación diaria. Nunca solicites NIP, contraseñas ni CVV."""
'''


def merge_adapter(adapter_dir: Path, merged_dir: Path) -> None:
    """Fusiona los pesos LoRA en el modelo base y guarda los safetensors listos para GGUF."""
    t0 = time.perf_counter()
    print(f"[1/3] Cargando modelo base {BASE_MODEL_ID}...")
    try:
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            dtype=torch.bfloat16,
            device_map="cpu",
            local_files_only=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir))
    except Exception:
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            dtype=torch.bfloat16,
            device_map="cpu",
        )
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)

    print(f"[2/3] Aplicando adaptador LoRA ({adapter_dir}) con merge_and_unload()...")
    merged_model = PeftModel.from_pretrained(base_model, str(adapter_dir)).merge_and_unload()

    if merged_dir.exists():
        shutil.rmtree(merged_dir)
    merged_dir.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(str(merged_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_dir))
    print(f"      Modelo fusionado guardado en {merged_dir} ({time.perf_counter() - t0:.1f}s)")


def convert_to_gguf(merged_dir: Path, gguf_path: Path, converter: Path, outtype: str) -> None:
    """Convierte el directorio safetensors fusionado a GGUF usando llama.cpp."""
    env = os.environ.copy()
    gguf_py = converter.parent / "gguf-py"
    if gguf_py.exists():
        env["PYTHONPATH"] = f"{gguf_py}:{env.get('PYTHONPATH', '')}".rstrip(":")

    cmd = [
        sys.executable,
        str(converter),
        str(merged_dir),
        "--outfile",
        str(gguf_path),
        "--outtype",
        outtype,
    ]
    subprocess.run(cmd, env=env, check=True)


def register_in_ollama(model_name: str, adapter_dir: Path, gguf_filename: str) -> None:
    """Genera el Modelfile y registra el GGUF en el servidor local de Ollama."""
    modelfile_path = adapter_dir / "Modelfile"
    modelfile_path.write_text(
        QWEN_MODELFILE_TEMPLATE.format(gguf_filename=gguf_filename),
        encoding="utf-8",
    )
    print(f"[3/3] Registrando '{model_name}' en Ollama desde {modelfile_path}...")
    subprocess.run(
        ["ollama", "create", model_name, "-f", str(modelfile_path)],
        cwd=str(adapter_dir),
        check=True,
    )
    print(f"OK: Modelo '{model_name}' registrado en Ollama.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta y registra el LoRA de Tiendita IA en Ollama (GGUF).")
    parser.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    parser.add_argument("--merged-dir", type=Path, default=DEFAULT_MERGED_DIR)
    parser.add_argument("--model-name", default="tiendita-lora-v1")
    parser.add_argument("--outtype", default="q8_0", help="Tipo de salida GGUF (q8_0, f16, bf16)")
    parser.add_argument("--gguf-converter", type=Path, default=None, help="Ruta a llama.cpp/convert_hf_to_gguf.py")
    parser.add_argument("--skip-merge", action="store_true", help="Registrar GGUF existente sin volver a fusionar")
    args = parser.parse_args()

    gguf_filename = f"{args.model_name}-{args.outtype}.gguf"
    gguf_path = args.adapter_dir / gguf_filename

    if not args.skip_merge:
        merge_adapter(args.adapter_dir, args.merged_dir)
        if args.gguf_converter is None:
            raise SystemExit("Pasa --gguf-converter /ruta/a/llama.cpp/convert_hf_to_gguf.py para generar el GGUF.")
        convert_to_gguf(args.merged_dir, gguf_path, args.gguf_converter, args.outtype)
        if args.merged_dir.exists():
            shutil.rmtree(args.merged_dir)

    if not gguf_path.exists():
        raise SystemExit(f"No se encontró el archivo GGUF esperado: {gguf_path}")

    register_in_ollama(args.model_name, args.adapter_dir, gguf_filename)


if __name__ == "__main__":
    main()
