# Etapa 3 — Resultados Baseline

## Configuración

- Test set: `training_data/test_questions.json` (42 ejemplos)
- Modelos evaluados sin fine-tuning (pesos pre-entrenados).
- ROUGE calculado con `use_stemmer=False` (español).

## Tabla de métricas

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | Secciones (0-1) | Long. media (pal.) | No-causalidad (cruce) |
|---|---|---|---|---|---|---|
| FLAN-T5-base (vanilla) | 0.1746 | 0.0341 | 0.0872 | 0.0298 | 123.7 | 1.0 |
| Qwen2.5-1.5B-Instruct (vanilla) | 0.3828 | 0.12 | 0.2296 | 0.9524 | 160.9 | 1.0 |

## Notas

- **Secciones (0-1):** fracción de las 4 secciones esperadas (Resumen, Datos principales, Interpretación, Limitaciones) presentes en la respuesta.
- **No-causalidad (cruce):** fracción de ejemplos de `relacion_ventas_accidentes_nacional` donde la respuesta menciona no-causalidad/correlación.
- ROUGE subestima la calidad de respuestas largas y en español; usar como proxy comparativo, no como métrica absoluta.
- Qwen2.5-1.5B-Instruct (vanilla) debería superar a FLAN-T5-base por arquitectura y tamaño.
- Estos resultados son el baseline contra el que se comparará el modelo fine-tuneado de Etapa 4.

## Predicciones completas

Ver `reports/baseline_results.csv`.
