# Etapa 4 — Resultados Fine-tuning (QLoRA)

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
| Qwen2.5-1.5B-Instruct (LoRA) | 0.7055 | 0.635 | 0.6753 | 0.7976 | 159.5 | 1.0 |

## Predicciones completas

Ver `reports/finetune_results.csv`.

## Comparación con baselines

Ver `reports/etapa4_comparacion_modelos.md` para la tabla unificada
(FLAN vanilla · Qwen vanilla · Qwen-LoRA) y ejemplos cualitativos.
