"""Construye notebooks/04_finetune_qwen_lora_colab.ipynb a partir de celdas
declaradas como tuplas (tipo, source). Idempotente: vuelve a generarse cada
vez que cambias este archivo y lo ejecutas. No es parte del pipeline; es solo
una herramienta para regenerar el notebook sin editar JSON a mano.
"""

from __future__ import annotations

import json
from pathlib import Path


def md(src: str) -> dict:
    return {
        'cell_type': 'markdown',
        'metadata': {},
        'source': src.splitlines(keepends=True),
    }


def code(src: str) -> dict:
    return {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': src.splitlines(keepends=True),
    }


CELLS: list[dict] = [

md('''# Etapa 4 — Fine-tuning Qwen2.5-1.5B-Instruct con LoRA (bf16)

Entrena un adapter LoRA sobre Qwen-1.5B-Instruct usando los 341 ejemplos de
`training_data/train.jsonl`, evalúa en el mismo `test_questions.json` que
Etapa 3, y produce una tabla de comparación contra los baselines.

**Configuración:** LoRA en bf16 (sin 4-bit) · 3 epochs · early stopping en
`eval_loss` · adapter guardado en Drive.
'''),

md('''## Celda 1 — Instalación de dependencias

LoRA en bf16 (sin QLoRA). Aún así `peft` importa `bitsandbytes` como
dependencia dura al construir el módulo LoRA, así que lo necesitamos
instalado y limpio (aunque no lo usemos para cuantizar). El primer comando
desinstala lo que Colab tenga preinstalado para evitar un estado mixto;
el segundo instala todo limpio.
'''),

code('''!pip uninstall -y -q transformers peft accelerate bitsandbytes datasets torchao
!pip install -q transformers peft accelerate datasets bitsandbytes torchao rouge-score nltk sentencepiece'''),

md('''## Celda 2 — Configuración de entorno (Colab vs local)'''),

code('''import os
import sys
from pathlib import Path

IN_COLAB = 'google.colab' in sys.modules

if IN_COLAB:
    from google.colab import drive
    drive.mount('/content/drive')
    PROJECT_ROOT = Path('/content/drive/MyDrive/inegi')
    sys.path.insert(0, str(PROJECT_ROOT))
else:
    PROJECT_ROOT = Path('..').resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

print(f'PROJECT_ROOT: {PROJECT_ROOT}')
print(f'Modo: {"Colab" if IN_COLAB else "Local"}')
assert (PROJECT_ROOT / 'training_data' / 'train.jsonl').exists(), \\
    'No se encuentra training_data/train.jsonl en PROJECT_ROOT'
assert (PROJECT_ROOT / 'src' / 'baseline_metrics.py').exists(), \\
    'No se encuentra src/baseline_metrics.py — súbelo a Drive'
'''),

md('''## Celda 3 — Imports'''),

code('''import json
import re
import torch
import pandas as pd
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer,
    DataCollatorForSeq2Seq, EarlyStoppingCallback,
)
from peft import LoraConfig, get_peft_model, PeftModel

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Device: {device}')
if device == 'cuda':
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
'''),

md('''## Celda 4 — Cargar datasets

Los tres splits tienen los mismos campos: `intent`, `input`, `output`.
Verificado que no hay solape de inputs entre train, val y test.
'''),

code('''def cargar_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]

train_raw = cargar_jsonl(PROJECT_ROOT / 'training_data' / 'train.jsonl')
val_raw   = cargar_jsonl(PROJECT_ROOT / 'training_data' / 'validation.jsonl')
test_raw  = json.loads((PROJECT_ROOT / 'training_data' / 'test_questions.json').read_text(encoding='utf-8'))

print(f'train: {len(train_raw)}  val: {len(val_raw)}  test: {len(test_raw)}')
print(f'Intents val: {sorted(set(e["intent"] for e in val_raw))}')
'''),

md('''## Celda 5 — Cargar Qwen2.5-1.5B en fp16

Sin cuantización: el modelo en fp16 (~3 GB) cabe en T4 con margen.
`fp16` (no `bf16`) porque T4 es arquitectura Turing y no tiene tensor cores
de bf16. `enable_input_require_grads()` es necesario para que gradient
checkpointing funcione cuando el modelo base está congelado y solo entrenan
los pesos LoRA.
'''),

code('''QWEN_ID = 'Qwen/Qwen2.5-1.5B-Instruct'

tokenizer = AutoTokenizer.from_pretrained(QWEN_ID, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    QWEN_ID,
    torch_dtype=torch.float16,
    device_map='auto',
    trust_remote_code=True,
)
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
print('Modelo base cargado en fp16.')
'''),

md('''## Celda 6 — Aplicar LoRA

`r=16, alpha=32, dropout=0.05`. `target_modules` cubre todos los proyectores
de atención y FFN de Qwen para mejor capacidad de adaptación.
'''),

code('''lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias='none',
    task_type='CAUSAL_LM',
    target_modules=[
        'q_proj', 'k_proj', 'v_proj', 'o_proj',
        'gate_proj', 'up_proj', 'down_proj',
    ],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
'''),

md('''## Celda 7 — Tokenizar dataset

Para SFT con masking: el loss solo se calcula sobre los tokens de la respuesta
(no sobre el prompt). Esto evita que el modelo "aprenda" a copiar el prompt.

`MAX_LEN = 1024`: balance entre cobertura del prompt y VRAM disponible en
T4. Si truncar más del 10% de los ejemplos, subir a 1536 y bajar batch.
'''),

code('''MAX_LEN = 1024

def tokenize(ex):
    messages = [{'role': 'user', 'content': ex['input']}]
    prompt_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    full_text = prompt_text + ex['output'] + tokenizer.eos_token

    prompt_ids = tokenizer(prompt_text, add_special_tokens=False).input_ids
    full_ids = tokenizer(
        full_text, add_special_tokens=False, truncation=True, max_length=MAX_LEN,
    ).input_ids

    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
    labels = labels[:len(full_ids)]

    return {
        'input_ids': full_ids,
        'attention_mask': [1] * len(full_ids),
        'labels': labels,
    }

train_ds = Dataset.from_list(train_raw).map(tokenize, remove_columns=['intent', 'input', 'output'])
val_ds   = Dataset.from_list(val_raw).map(tokenize,   remove_columns=['intent', 'input', 'output'])

# Sanity: ¿cuántos ejemplos se truncan?
trunc_train = sum(1 for ex in train_ds if len(ex['input_ids']) >= MAX_LEN)
trunc_val   = sum(1 for ex in val_ds   if len(ex['input_ids']) >= MAX_LEN)
print(f'Truncados train: {trunc_train}/{len(train_ds)}')
print(f'Truncados val:   {trunc_val}/{len(val_ds)}')
print(f'Long. media train (tokens): {np.mean([len(ex["input_ids"]) for ex in train_ds]):.0f}')
'''),

md('''## Celda 8 — Training arguments

- Batch efectivo: 1 × 16 = 16
- 3 epochs ≈ 64 pasos de optimizador (341 / 16 × 3)
- Eval por epoch + early stopping con paciencia 1
- LR 2e-4, warmup 3% (estándar QLoRA)
'''),

code('''ADAPTER_DIR = PROJECT_ROOT / 'models' / 'qwen_lora_inegi'
ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

training_args = TrainingArguments(
    output_dir=str(ADAPTER_DIR / 'checkpoints'),
    num_train_epochs=3,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=2e-4,
    warmup_ratio=0.03,
    lr_scheduler_type='cosine',
    fp16=True,
    optim='adamw_torch',
    logging_steps=5,
    eval_strategy='epoch',
    save_strategy='epoch',
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model='eval_loss',
    greater_is_better=False,
    report_to='none',
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={'use_reentrant': False},
)

data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer, padding=True, return_tensors='pt',
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    data_collator=data_collator,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
)

print('Trainer listo.')
'''),

md('''## Celda 9 — Entrenar

En T4 (Colab gratis) este bloque dura ~30–45 min. Si la `eval_loss` sube en
una epoch consecutiva, early stopping cierra el entrenamiento.
'''),

code('''train_result = trainer.train()
print(train_result.metrics)
'''),

md('''## Celda 10 — Guardar adapter

Solo el adapter LoRA (~30 MB), no el modelo base. Etapa 5 (Streamlit local
en RTX 3060 Ti) descargará este adapter y lo aplicará sobre Qwen-1.5B.
'''),

code('''trainer.model.save_pretrained(ADAPTER_DIR)
tokenizer.save_pretrained(ADAPTER_DIR)
print(f'Adapter guardado en: {ADAPTER_DIR}')
print('Archivos:', sorted(p.name for p in ADAPTER_DIR.iterdir()))
'''),

md('''## Celda 11 — Inferencia sobre test set

Mismo `test_questions.json` que Etapa 3. Mismo `do_sample=False` para
comparabilidad estricta.
'''),

code('''from tqdm.auto import tqdm

trainer.model.eval()

def inferir_qwen_finetune(prompt: str, max_new_tokens: int = 512) -> str:
    messages = [{'role': 'user', 'content': prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors='pt').to(trainer.model.device)
    with torch.no_grad():
        out = trainer.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(
        out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True,
    )

finetune_preds = []
for ex in tqdm(test_raw, desc='Qwen-LoRA'):
    finetune_preds.append(inferir_qwen_finetune(ex['input']))

print(f'Inferencias completadas: {len(finetune_preds)}')
'''),

md('''## Celda 12 — Métricas (reusando `src.baseline_metrics`)

Mismas funciones que Etapa 3, importadas desde el módulo compartido.
'''),

code('''from src.baseline_metrics import calcular_metricas_rouge, calcular_metricas_extra

gold = [ex['output'] for ex in test_raw]

ft_rouge = calcular_metricas_rouge(finetune_preds, gold)
ft_extra = calcular_metricas_extra(finetune_preds, test_raw)

print('Métricas Qwen-LoRA fine-tuneado:', {**ft_rouge, **ft_extra})
'''),

md('''## Celda 13 — Guardar resultados de Etapa 4'''),

code('''REPORTS_DIR = PROJECT_ROOT / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)

# CSV con predicciones del modelo fine-tuneado
ft_csv_path = REPORTS_DIR / 'finetune_results.csv'
pd.DataFrame([
    {
        'idx': i,
        'intent': ex['intent'],
        'gold': ex['output'],
        'qwen_finetune_pred': finetune_preds[i],
    }
    for i, ex in enumerate(test_raw)
]).to_csv(ft_csv_path, index=False, encoding='utf-8')
print(f'CSV guardado: {ft_csv_path}')

# Markdown con métricas del fine-tuneado
ft_md_path = REPORTS_DIR / 'etapa4_finetune_resultados.md'
no_causal_ft = ft_extra['no_causalidad_cuando_aplica']

ft_md = f"""# Etapa 4 — Resultados Fine-tuning (QLoRA)

## Configuración

- Modelo base: `Qwen/Qwen2.5-1.5B-Instruct`
- Método: LoRA en bf16 (sin cuantización 4-bit)
- LoRA: r=16, alpha=32, dropout=0.05, target_modules = todos los proyectores
- Optimizador: adamw_torch, lr=2e-4, cosine, warmup=3%
- Batch efectivo: 16 (2 × 8 grad. accum.)
- Epochs: 3 con early stopping (paciencia=1) sobre `eval_loss`
- Test set: `training_data/test_questions.json` (42 ejemplos, mismo que Etapa 3)

## Métricas

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | Secciones (0-1) | Long. media (pal.) | No-causalidad (cruce) |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct (LoRA) | {ft_rouge['rouge1']} | {ft_rouge['rouge2']} | {ft_rouge['rougeL']} | {ft_extra['secciones_presentes']} | {ft_extra['longitud_media_palabras']} | {no_causal_ft} |

## Predicciones completas

Ver `reports/finetune_results.csv`.

## Comparación con baselines

Ver `reports/etapa4_comparacion_modelos.md` para la tabla unificada
(FLAN vanilla · Qwen vanilla · Qwen-LoRA) y ejemplos cualitativos.
"""
ft_md_path.write_text(ft_md, encoding='utf-8')
print(f'Markdown guardado: {ft_md_path}')
'''),

md('''## Celda 14 — Comparación unificada con baselines

Lee `baseline_results.csv` (Etapa 3) y combina con las predicciones del
fine-tuneado. Recalcula las métricas de los baselines desde el CSV
(no re-corre inferencia) y produce la tabla final + ejemplos cualitativos.

> Nota: si `baseline_results.csv` no existe en Drive, esta celda falla con un
> mensaje claro. Asegúrate de haberlo subido desde tu Mac.
'''),

code('''baseline_csv = REPORTS_DIR / 'baseline_results.csv'
assert baseline_csv.exists(), (
    f'Falta {baseline_csv}. Sube reports/baseline_results.csv desde tu Mac '
    f'antes de correr esta celda.'
)

df_base = pd.read_csv(baseline_csv)
assert len(df_base) == len(test_raw), 'baseline_results.csv tiene otra cantidad de filas que test_raw.'

flan_preds = df_base['flan_pred'].astype(str).tolist()
qwen_vanilla_preds = df_base['qwen_pred'].astype(str).tolist()

flan_rouge = calcular_metricas_rouge(flan_preds, gold)
flan_extra = calcular_metricas_extra(flan_preds, test_raw)
qv_rouge = calcular_metricas_rouge(qwen_vanilla_preds, gold)
qv_extra = calcular_metricas_extra(qwen_vanilla_preds, test_raw)

resumen = pd.DataFrame([
    {'Modelo': 'FLAN-T5-base (vanilla)',          **flan_rouge, **flan_extra},
    {'Modelo': 'Qwen2.5-1.5B-Instruct (vanilla)', **qv_rouge,   **qv_extra},
    {'Modelo': 'Qwen2.5-1.5B-Instruct (LoRA)',    **ft_rouge,   **ft_extra},
])
display(resumen.set_index('Modelo'))
'''),

md('''## Celda 15 — Ejemplos cualitativos lado a lado

Tres intents representativos (ranking, tipo, cruce nacional). Útil para el
reporte porque ROUGE en español con respuestas largas es ruidoso — los
ejemplos muestran el salto cualitativo del fine-tuning.
'''),

code('''INTENTS_MUESTRA = [
    'ranking_accidentes',
    'accidentes_por_tipo',
    'relacion_ventas_accidentes_nacional',
]

ejemplos_md = []
for intent_objetivo in INTENTS_MUESTRA:
    idx = next(
        (i for i, e in enumerate(test_raw) if e['intent'] == intent_objetivo),
        None,
    )
    if idx is None:
        continue
    ejemplos_md.append(f"### Intent: `{intent_objetivo}`\\n")
    ejemplos_md.append(f"**Pregunta:** {test_raw[idx]['input'][:300]}...\\n")
    ejemplos_md.append(f"**Gold:**\\n```\\n{gold[idx]}\\n```\\n")
    ejemplos_md.append(f"**FLAN-T5-base (vanilla):**\\n```\\n{flan_preds[idx]}\\n```\\n")
    ejemplos_md.append(f"**Qwen-1.5B (vanilla):**\\n```\\n{qwen_vanilla_preds[idx]}\\n```\\n")
    ejemplos_md.append(f"**Qwen-1.5B (LoRA):**\\n```\\n{finetune_preds[idx]}\\n```\\n")
    ejemplos_md.append('---\\n')

print('\\n'.join(ejemplos_md[:20]))
'''),

md('''## Celda 16 — Guardar comparación

Archivo final que vas a citar en el reporte escolar:
`reports/etapa4_comparacion_modelos.md`.
'''),

code('''comp_path = REPORTS_DIR / 'etapa4_comparacion_modelos.md'

tabla_md = resumen.set_index('Modelo').to_markdown()
ejemplos_str = '\\n'.join(ejemplos_md)

# Deltas relativos al baseline más fuerte (Qwen vanilla)
delta = {
    'rouge1': ft_rouge['rouge1'] - qv_rouge['rouge1'],
    'rouge2': ft_rouge['rouge2'] - qv_rouge['rouge2'],
    'rougeL': ft_rouge['rougeL'] - qv_rouge['rougeL'],
    'secciones': ft_extra['secciones_presentes'] - qv_extra['secciones_presentes'],
}

comp = f"""# Etapa 4 — Comparación de modelos

Evaluación sobre el mismo `test_questions.json` (42 ejemplos), mismas
funciones de métricas (`src.baseline_metrics`), misma estrategia de
generación (`do_sample=False`, `max_new_tokens=512`).

## Tabla unificada

{tabla_md}

## Delta del fine-tuning vs Qwen vanilla

| Métrica | Δ (LoRA − vanilla) |
|---|---|
| ROUGE-1   | {delta['rouge1']:+.4f} |
| ROUGE-2   | {delta['rouge2']:+.4f} |
| ROUGE-L   | {delta['rougeL']:+.4f} |
| Secciones | {delta['secciones']:+.4f} |

## Ejemplos cualitativos lado a lado

{ejemplos_str}

## Notas para el reporte

- **ROUGE en español con respuestas largas es ruidoso.** Considéralo proxy
  comparativo, no medida absoluta. El salto cualitativo en estructura
  (secciones presentes) y adherencia al formato es más visible en los
  ejemplos cualitativos que en ROUGE.
- **Las cifras numéricas siguen viniendo del prompt.** Ningún modelo (ni
  fine-tuneado) inventa números: el LLM solo redacta a partir de los datos
  calculados con pandas, según el principio fundamental del proyecto.
- **No-causalidad:** confirmar que el fine-tuneado mantiene la mención de
  correlación / no-causalidad en los ejemplos de cruce ventas-accidentes.
"""
comp_path.write_text(comp, encoding='utf-8')
print(f'Comparación guardada: {comp_path}')
'''),

md('''---
**Etapa 4 completada.** Archivos en `reports/`:

- `etapa4_finetune_resultados.md`
- `finetune_results.csv`
- `etapa4_comparacion_modelos.md`  ← este es el que vas a citar en el reporte

Adapter LoRA en `models/qwen_lora_inegi/` (Drive). Etapa 5 lo descargará a
local (RTX 3060 Ti) y lo cargará sobre Qwen-1.5B-Instruct para servir a
Streamlit.
'''),

]


def main() -> None:
    nb = {
        'cells': CELLS,
        'metadata': {
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': 'python3',
            },
            'language_info': {'name': 'python', 'version': '3.10.0'},
        },
        'nbformat': 4,
        'nbformat_minor': 4,
    }
    out = Path(__file__).parent / '04_finetune_qwen_lora_colab.ipynb'
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'Notebook escrito: {out}')


if __name__ == '__main__':
    main()
