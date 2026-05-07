# Cómo retomar el proyecto en una nueva sesión

## Estado actual

| Etapa | Estado |
|---|---|
| Etapa 1 — Pipeline pandas + Streamlit | ✅ Completa |
| Etapa 2 — Dataset de entrenamiento | ✅ Completa |
| Etapa 3 — Baseline FLAN-T5 + Qwen vanilla | 🔜 Siguiente |
| Etapa 4 — Fine-tuning LoRA/QLoRA en Colab | ⏳ Pendiente |
| Etapa 5 — Integración modelo fine-tuneado | ⏳ Pendiente |

---

## ▶️ Para iniciar Etapa 3 — pega esto al inicio de la sesión

```
Estoy retomando el proyecto INEGI AI Assistant en /Users/omarchi/Developer/inegi.

Antes de proponer nada, lee en este orden:
1. CLAUDE.md (contexto general, decisiones, esquemas canónicos).
2. docs/ETAPA_3_PLAN.md (plan completo de la Etapa 3).

Resumen rápido:
- Etapas 1 y 2 están COMPLETAS y validadas.
- Etapa 2 produjo training_data/train.jsonl (341), validation.jsonl (42),
  test_questions.json (42). Cada ejemplo: {intent, input, output}.
- Etapa 3 es el baseline: evaluar FLAN-T5-base y Qwen2.5-1.5B-Instruct vanilla
  (sin fine-tuning) sobre el test set con métricas ROUGE.

Tu tarea es implementar notebooks/03_baseline_flan_qwen.ipynb según
docs/ETAPA_3_PLAN.md. El notebook debe:
1. Cargar test_questions.json (42 ejemplos).
2. Inferir con FLAN-T5-base y Qwen2.5-1.5B-Instruct (sin fine-tuning).
3. Calcular ROUGE-1, ROUGE-2, ROUGE-L para cada modelo.
4. Mostrar tabla comparativa + 3 ejemplos cualitativos por modelo.
5. Guardar reports/etapa3_baseline_resultados.md.

Hardware local: Windows, i7, RTX 3060 Ti, 32 GB RAM.
Alternativa: Google Colab si la GPU local no alcanza para Qwen.

Procede con un plan corto antes de implementar.
```

---

## Antes de iniciar la nueva sesión, en tu terminal

```bash
cd /Users/omarchi/Developer/inegi
source .venv/bin/activate

# verificar que los 3 archivos de training data existen
ls -lh training_data/

# si faltan, regenerar (tarda ~30 s)
python -c "from src.training_data_generator import generar_y_guardar_todo; generar_y_guardar_todo()"
```

---

## Archivos clave por etapa

| Archivo | Relevante para |
|---|---|
| `CLAUDE.md` | Siempre — contexto global, esquemas, hallazgos |
| `docs/ETAPA_2_PLAN.md` | Referencia histórica — Etapa 2 cerrada |
| `docs/ETAPA_3_PLAN.md` | Plan activo — leer antes de Etapa 3 |
| `src/training_data_generator.py` | Generador del corpus (Etapa 2) |
| `training_data/test_questions.json` | Input para el baseline (Etapa 3) |
| `src/response_generator.py` | `construir_prompt()` — arma el input |
| `src/analytics.py` | Las 10 funciones que devuelven DataFrames |
