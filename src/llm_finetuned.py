"""Carga del modelo Qwen2.5-1.5B-Instruct + adapter LoRA fine-tuneado y
generación de respuestas para la app Streamlit.

Auto-detecta el mejor backend disponible:
- CUDA (Windows + RTX 3060 Ti) → 4-bit si bitsandbytes está instalado, fp16 si no.
- MPS (Mac Apple Silicon) → fp16.
- CPU → fp32 (lento, fallback).

Mismo `do_sample=False, max_new_tokens=512` que la evaluación de Etapa 4.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


_BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
_ADAPTER_DIR = Path(__file__).resolve().parent.parent / "models" / "qwen_lora_inegi"
_MAX_NEW_TOKENS = 512


def _detectar_backend() -> tuple[str, dict[str, Any]]:
    """Devuelve (nombre_backend, kwargs_para_from_pretrained)."""
    if torch.cuda.is_available():
        try:
            from transformers import BitsAndBytesConfig
            import bitsandbytes  # noqa: F401  — solo para detectar disponibilidad
            bnb = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            return "cuda-4bit", {
                "quantization_config": bnb,
                "device_map": "auto",
            }
        except (ImportError, RuntimeError):
            return "cuda-fp16", {
                "torch_dtype": torch.float16,
                "device_map": "auto",
            }
    if torch.backends.mps.is_available():
        return "mps", {"torch_dtype": torch.float16}
    return "cpu", {"torch_dtype": torch.float32}


def cargar_modelo() -> tuple[Any, Any, str]:
    """Carga el modelo base + adapter LoRA. Pesado: cachea la primera llamada.

    Returns:
        (model, tokenizer, backend_name)
    """
    if not _ADAPTER_DIR.exists():
        raise FileNotFoundError(
            f"Adapter LoRA no encontrado en {_ADAPTER_DIR}. "
            f"Descárgalo de Drive o re-ejecuta Etapa 4."
        )

    backend, model_kwargs = _detectar_backend()

    tokenizer = AutoTokenizer.from_pretrained(_BASE_MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        _BASE_MODEL_ID,
        trust_remote_code=True,
        **model_kwargs,
    )

    if backend in {"mps", "cpu"}:
        model = model.to(backend if backend == "mps" else "cpu")

    model = PeftModel.from_pretrained(model, str(_ADAPTER_DIR))
    model.eval()
    return model, tokenizer, backend


def generar_respuesta(
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_new_tokens: int = _MAX_NEW_TOKENS,
) -> str:
    """Genera la respuesta del modelo dado el prompt completo.

    Mismo setup que la evaluación: chat template de Qwen, do_sample=False,
    decoding determinista para reproducibilidad.
    """
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(
        out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True,
    )


__all__ = ["cargar_modelo", "generar_respuesta"]
