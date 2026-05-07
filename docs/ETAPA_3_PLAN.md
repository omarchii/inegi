# Etapa 3 — Baseline: FLAN-T5-base + Qwen2.5-1.5B-Instruct (vanilla)

> Lee este archivo antes de tocar código. Es el plan aprobado para la Etapa 3.

## Estado del proyecto al iniciar

- **Etapa 1: ✅ COMPLETA** — pipeline pandas + intent + Streamlit con datos reales.
- **Etapa 2: ✅ COMPLETA** — dataset de entrenamiento generado (`training_data/`).
- **Etapa 3: 🔜 PENDIENTE** — notebook de baseline, sin fine-tuning todavía.
- Etapas 4-5: pendientes.

## Objetivo

Evaluar qué tan bien responden **FLAN-T5-base** y **Qwen2.5-1.5B-Instruct** (sin fine-tuning) a las preguntas del test set, usando el prompt construido por `construir_prompt()`. Esto establece el **baseline** con el que se comparará el modelo fine-tuneado de Etapa 4.

## Archivos que produce esta etapa

```
notebooks/
└── 03_baseline_flan_qwen.ipynb

reports/
└── etapa3_baseline_resultados.md   (resumen de métricas)
```

## Hardware objetivo

- **Local (Windows):** i7, RTX 3060 Ti, 32 GB RAM.
  - FLAN-T5-base corre sin problemas en CPU o GPU de 8 GB.
  - Qwen2.5-1.5B-Instruct corre en GPU de 8 GB con `device_map="auto"` y dtype bfloat16.
- **Colab:** alternativa si local no alcanza.
- El notebook debe funcionar en ambos entornos con mínimos cambios.

## Modelos a evaluar

| Modelo | HF ID | Tamaño | Tipo |
|---|---|---|---|
| FLAN-T5-base | `google/flan-t5-base` | ~250 MB | Seq2Seq |
| Qwen2.5-1.5B-Instruct | `Qwen/Qwen2.5-1.5B-Instruct` | ~3 GB | CausalLM (chat) |

## Datos de entrada

- `training_data/test_questions.json` — 42 ejemplos con campos `intent`, `input`, `output`.
  - `input` = prompt completo construido por `construir_prompt()`.
  - `output` = respuesta ideal de referencia (gold standard).

## Estructura del notebook (celdas)

### Celda 1 — Instalación de dependencias
```bash
pip install transformers torch accelerate sentencepiece rouge-score nltk
```
> **Nota:** estas dependencias NO van a `requirements.txt` del proyecto principal hasta Etapa 5.

### Celda 2 — Imports y configuración
```python
import torch, json, re
from pathlib import Path
from transformers import (
    T5ForConditionalGeneration, T5Tokenizer,
    AutoModelForCausalLM, AutoTokenizer,
)
from rouge_score import rouge_scorer
import nltk
nltk.download('punkt', quiet=True)
```

### Celda 3 — Cargar test set
```python
test = json.loads(Path('training_data/test_questions.json').read_text())
# 42 ejemplos: [{intent, input, output}, ...]
```

### Celda 4 — Función de inferencia FLAN-T5-base
```python
def inferir_flan(model, tokenizer, prompt: str, max_new_tokens=512) -> str:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(out[0], skip_special_tokens=True)
```

### Celda 5 — Función de inferencia Qwen2.5-1.5B-Instruct
```python
def inferir_qwen(model, tokenizer, prompt: str, max_new_tokens=512) -> str:
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
```

### Celda 6 — Métricas
```python
def calcular_metricas(predicciones: list[str], referencias: list[str]) -> dict:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=False)
    r1, r2, rl = [], [], []
    for pred, ref in zip(predicciones, referencias):
        s = scorer.score(ref, pred)
        r1.append(s['rouge1'].fmeasure)
        r2.append(s['rouge2'].fmeasure)
        rl.append(s['rougeL'].fmeasure)
    return {
        'rouge1': round(sum(r1)/len(r1), 4),
        'rouge2': round(sum(r2)/len(r2), 4),
        'rougeL': round(sum(rl)/len(rl), 4),
    }
```

### Celda 7 — Cargar FLAN-T5-base y evaluar
- Cargar modelo con `T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")`.
- Correr inferencia sobre los 42 ejemplos del test set.
- Calcular métricas ROUGE.

### Celda 8 — Cargar Qwen2.5-1.5B-Instruct y evaluar
- Cargar con `AutoModelForCausalLM.from_pretrained(..., torch_dtype=torch.bfloat16, device_map="auto")`.
- Correr inferencia sobre los 42 ejemplos.
- Calcular métricas ROUGE.

### Celda 9 — Tabla comparativa baseline
```
| Modelo                   | ROUGE-1 | ROUGE-2 | ROUGE-L |
|--------------------------|---------|---------|---------|
| FLAN-T5-base (vanilla)   |  X.XXX  |  X.XXX  |  X.XXX  |
| Qwen2.5-1.5B (vanilla)   |  X.XXX  |  X.XXX  |  X.XXX  |
```

### Celda 10 — Ejemplos cualitativos (3 ejemplos)
- Para cada modelo: mostrar `intent`, `pregunta`, `respuesta_generada`, `respuesta_gold`.
- Revisión visual de coherencia.

### Celda 11 — Guardar resultados
- Guardar `reports/etapa3_baseline_resultados.md` con la tabla de métricas y notas.

## Métricas objetivo

- ROUGE no es la métrica ideal para textos largos en español, pero sirve como proxy rápido.
- El objetivo **no es un número específico** — es tener una línea base documentada para comparar contra el modelo fine-tuneado de Etapa 4.
- Qwen2.5-1.5B-Instruct vanilla debería superar a FLAN-T5-base por arquitectura y tamaño.

## Reglas para esta etapa

1. **Sin fine-tuning.** Los modelos se cargan con pesos pre-entrenados, sin ajuste.
2. **El prompt viene de `construir_prompt()`** — no inventar formato nuevo.
3. **ROUGE en español** — no usar stemmers en inglés; `use_stemmer=False`.
4. **Guardar predicciones en JSON** para no tener que re-inferir en Etapa 4.
5. **Si la GPU local no alcanza para Qwen**, usar Colab (T4 free es suficiente).

## Criterio de éxito de Etapa 3

- [ ] `notebooks/03_baseline_flan_qwen.ipynb` ejecutado de inicio a fin sin errores.
- [ ] Métricas ROUGE calculadas para ambos modelos sobre los 42 ejemplos del test set.
- [ ] Tabla comparativa visible en el notebook.
- [ ] `reports/etapa3_baseline_resultados.md` guardado con métricas y observaciones.
- [ ] Al menos 3 ejemplos cualitativos revisados por intent.

## Prompt de retomar (para copiar al inicio de la sesión)

```
Estoy retomando el proyecto INEGI AI Assistant en /Users/omarchi/Developer/inegi.

Antes de proponer nada, lee en este orden:
1. CLAUDE.md (contexto general, decisiones, esquemas canónicos).
2. docs/ETAPA_3_PLAN.md (plan completo de la Etapa 3).

Resumen rápido:
- Etapas 1 y 2 están COMPLETAS y validadas.
- Etapa 2 produjo training_data/train.jsonl (341), validation.jsonl (42), test_questions.json (42).
- Etapa 3 es el baseline: evaluar FLAN-T5-base y Qwen2.5-1.5B-Instruct vanilla (sin fine-tuning)
  sobre el test set con métricas ROUGE.

Tu tarea es implementar notebooks/03_baseline_flan_qwen.ipynb según docs/ETAPA_3_PLAN.md.
El notebook debe:
1. Cargar test_questions.json (42 ejemplos, campo 'input' = prompt, 'output' = gold).
2. Inferir con FLAN-T5-base y Qwen2.5-1.5B-Instruct (sin fine-tuning).
3. Calcular ROUGE-1, ROUGE-2, ROUGE-L para cada modelo.
4. Mostrar tabla comparativa + 3 ejemplos cualitativos.
5. Guardar reports/etapa3_baseline_resultados.md.

Hardware local: Windows, i7, RTX 3060 Ti, 32 GB RAM.
Alternativa: Google Colab si la GPU no alcanza.

Procede con un plan corto antes de implementar.
```
