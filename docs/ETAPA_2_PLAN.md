# Etapa 2 — Generación del dataset de entrenamiento

> ✅ **ETAPA COMPLETADA** — 2026-04-30.
> Este archivo es ahora registro histórico. Para continuar lee `CLAUDE.md` y `docs/ETAPA_3_PLAN.md`.

## Estado al cierre

- **Etapa 1: COMPLETA y validada.**
- **Etapa 2: COMPLETA y validada.**
  - `src/training_data_generator.py` — módulo con 10 redactores, templates, corpus generator, split, I/O.
  - `notebooks/02_generate_training_data.ipynb` — notebook de orquestación.
  - `training_data/train.jsonl` — 341 ejemplos.
  - `training_data/validation.jsonl` — 42 ejemplos.
  - `training_data/test_questions.json` — 42 preguntas de prueba.
  - 425 ejemplos totales, seed=42, split 80/10/10 estratificado por intent.
- Etapas 3-5: pendientes (baseline, fine-tuning, integración).

## Decisión tomada — Camino A determinístico

El usuario eligió **plantillas determinísticas en Python** para generar el dataset de entrenamiento. **Sin** APIs externas, **sin** transformers, **sin** torch, **sin** Colab todavía. Toda la lógica vive en código Python puro y los números vienen de `src/analytics.py`.

## Objetivo

Generar tres archivos en `training_data/`:

```
training_data/
├── train.jsonl          # 80% — entrenamiento
├── validation.jsonl     # 10% — validación durante entrenamiento
└── test_questions.json  # 10% — preguntas para evaluación humana posterior
```

Cada línea de los `.jsonl` es una tripleta:

```json
{
  "intent": "ranking_accidentes",
  "input":  "<prompt completo construido con response_generator.construir_prompt>",
  "output": "<respuesta ejecutiva ideal en 4 secciones>"
}
```

El **input** ya está resuelto: lo arma `src/response_generator.construir_prompt()`.
El **output** es lo que esta etapa va a producir: respuestas plantilla parametrizadas con los números reales calculados.

## Tamaño objetivo

- ~400 ejemplos en `train.jsonl`.
- ~50 en `validation.jsonl`.
- ~50 en `test_questions.json`.
- Distribución: ~50 ejemplos por intent (10 intents × 50 ≈ 500). Ajustable por intent según diversidad disponible.

## Pasos de implementación

### Paso 1 — Crear `src/training_data_generator.py`

Módulo con:

1. **`TEMPLATES_PREGUNTA: dict[intent, list[str]]`** — 5–10 plantillas de pregunta por intent, con placeholders `{estado}`, `{anio}`, `{anio_inicio}`, `{anio_fin}`, `{top_n}`, `{tipo}`, `{municipio}`.

   Ejemplos:
   ```python
   "ranking_accidentes": [
       "¿Qué estados tuvieron más accidentes en {anio}?",
       "Dame el top {top_n} de entidades con más accidentes en {anio}.",
       "Ranking de accidentes por entidad para {anio}.",
       ...
   ]
   ```

2. **`redactar_respuesta_ideal(intent, df, slots) -> str`** — despachador que llama a una función específica por intent:
   - `_redactar_ranking_accidentes(df, slots)`
   - `_redactar_tendencia_accidentes(df, slots)`
   - `_redactar_comparacion_accidentes(df, slots)`
   - `_redactar_accidentes_por_municipio(df, slots)`
   - `_redactar_accidentes_por_tipo(df, slots)`
   - `_redactar_tendencia_ventas_nacional(df, slots)`
   - `_redactar_estacionalidad_ventas_nacional(df, slots)`
   - `_redactar_tendencia_parque_nacional(df, slots)`
   - `_redactar_relacion_ventas_accidentes_nacional(df, slots)`
   - `_redactar_resumen_estado(df, slots)`

   **Cada redactor produce las 4 secciones obligatorias:**
   1. **Resumen** — 1–2 frases con la conclusión principal, usando el dato más relevante (ej. el #1 del ranking, el cambio porcentual total, etc.).
   2. **Datos principales** — bullets con los números **literales** del DataFrame.
   3. **Interpretación** — qué sugieren los datos (correlación, no causalidad, contexto).
   4. **Limitaciones** — cubrir las que aplican: cobertura ATUS, salto metodológico 2022, VMRC nacional sin desglose estatal, no causalidad.

3. **`generar_corpus(...) -> list[dict]`** — orquesta:
   - Itera por intent.
   - Para cada intent, genera N combinaciones de slots válidos (ver sección "Combinatoria por intent" abajo).
   - Para cada combinación: ejecuta la función de `analytics.py` correspondiente, construye el prompt con `construir_prompt`, redacta la respuesta ideal y arma la tripleta.
   - Usa `random.seed(42)` para reproducibilidad.

4. **`split_estratificado(corpus, ratios=(0.8, 0.1, 0.1)) -> tuple[list, list, list]`** — split por intent (cada intent debe estar representado proporcionalmente en train/val/test).

5. **`guardar_jsonl(items, path)` y `guardar_test_json(items, path)`**.

### Paso 2 — Crear `notebooks/02_generate_training_data.ipynb`

Celdas:

1. Imports y configuración de seed.
2. Cargar `atus_anual`, `atus_detalle`, `vmrc_ventas`, `vmrc_parque` (procesados de Etapa 1).
3. Llamar `generar_corpus(atus_anual, atus_detalle, vmrc_ventas, vmrc_parque)`.
4. Mostrar conteo por intent (verificar balance).
5. `split_estratificado()` → train/val/test.
6. Guardar archivos.
7. **Sanity check: imprimir 5 ejemplos aleatorios** (intent + pregunta + primeras 200 chars de input + output completo) para revisión visual.

### Paso 3 — Validación final

1. Confirmar que los 3 archivos existen y tienen las cuentas esperadas.
2. Confirmar que ningún `output` contiene placeholders sin sustituir (`{algo}`).
3. Confirmar que cada intent aparece en train, val y test.
4. Confirmar que las respuestas con `relacion_ventas_accidentes_nacional` incluyen el aviso de no-causalidad.

## Combinatoria por intent (referencia para el generador)

| Intent | Slots variables | Cómo generar combinaciones | Aprox |
|---|---|---|---|
| `ranking_accidentes` | `anio`, `top_n` | años 2010–2024 × top_n ∈ {3,5,10} → ~45 | 50 |
| `tendencia_accidentes` | `estado` | 32 entidades canónicas | 32 |
| `comparacion_accidentes` | `estado_1`, `estado_2` | sample 50 pares aleatorios sin repetir orden | 50 |
| `accidentes_por_municipio` | `estado`, `anio?`, `top_n` | sample 50 (estado × año o solo estado) | 50 |
| `accidentes_por_tipo` | `estado?`, `anio?` | sample 50 (con/sin filtros) | 50 |
| `tendencia_ventas_nacional` | `tipo` | total, auto, camion → 3, repetir con plantillas distintas hasta ~30 | 30 |
| `estacionalidad_ventas_nacional` | `anio`, `tipo` | años 2015–2024 × {total,auto,camion} → 30 | 30 |
| `tendencia_parque_nacional` | (sin slots) | 1, repetir con ~20 plantillas distintas | 20 |
| `relacion_ventas_accidentes_nacional` | `anio_inicio`, `anio_fin`, `tipo` | rangos 2015→2024 (varios) × {total,auto,camion} | 50 |
| `resumen_estado` | `estado` | 32 entidades + variantes de plantilla | 50 |

**Total objetivo: ~500 ejemplos.** Si algún intent queda corto, se duplica con plantillas de pregunta distintas para mantener variedad léxica sin alterar números.

## Reglas duras del generador (NO romper)

1. **Cero invención de cifras.** Cada número en el `output` debe existir literalmente en el `df` calculado.
2. **No causalidad** en `relacion_ventas_accidentes_nacional` — incluir frase explícita: *"correlación no implica causalidad"*.
3. **Limitaciones ATUS** — mencionar en intents ATUS de tendencia o comparación de rangos largos (1997–2024) que **hay un salto metodológico en 2022** que afecta interpretación.
4. **VMRC nacional** — en cualquier intent VMRC, mencionar como limitación que los datos son **nacionales**, no por entidad.
5. **Cifras preliminares** — si el dataset incluyera 2025/2026 (no por defecto), etiquetar como preliminar.
6. **Español neutro y profesional** — sin coloquialismos.

## Patrón de respuesta ideal (template general)

```
1. Resumen
[Una a dos frases con la conclusión principal, usando el dato más fuerte.]

2. Datos principales
- [Dato 1 con número literal del df]
- [Dato 2 con número literal del df]
- [Dato 3 con número literal del df]

3. Interpretación
[Qué sugieren los datos. Si aplica correlación, mencionar magnitud y signo.
Si los datos muestran un cambio brusco, ofrecer contexto razonable
(ej. cobertura, parque vehicular total, eventos como pandemia).]

4. Limitaciones
- [Limitación 1]
- [Limitación 2]
- [No causalidad cuando aplique]
```

## Cómo retomar la sesión

Copia y pega esto al inicio de la nueva conversación con Claude Code:

> Estoy retomando el proyecto en `/Users/omarchi/Developer/inegi`. Lee `CLAUDE.md` y `docs/ETAPA_2_PLAN.md` para el contexto. La Etapa 1 está cerrada (pipeline + Streamlit funcionando). Procede con la Etapa 2 según el plan: implementa `src/training_data_generator.py` y `notebooks/02_generate_training_data.ipynb`, genera `train.jsonl`, `validation.jsonl` y `test_questions.json`, y muéstrame 5 ejemplos aleatorios para revisión antes de cerrar.

Y si quieres ser estricto:

> Antes de tocar código, verifica que `data/processed/atus_anual.csv`, `atus_detalle.csv`, `vmrc_ventas_mensual.csv` y `vmrc_parque_mensual.csv` existan. Si no, regéneralos con `python -m src.data_processing` (o llama a `construir_procesados()`).

## Comandos útiles para el inicio

```bash
# activar venv del proyecto
cd /Users/omarchi/Developer/inegi
source .venv/bin/activate

# verificar que los procesados existen
ls -la data/processed/

# si no existen:
python -c "from src.data_processing import construir_procesados; construir_procesados()"

# después de implementar Etapa 2:
jupyter notebook notebooks/02_generate_training_data.ipynb
# o:
python -c "from src.training_data_generator import generar_y_guardar_todo; generar_y_guardar_todo()"
```

## Lo que NO se hará en Etapa 2 (recordatorio)

- ❌ Llamar a Hugging Face, OpenAI, Anthropic ni cualquier API.
- ❌ Instalar `transformers`, `torch`, `peft`, `accelerate`, `bitsandbytes`.
- ❌ Subir a Google Colab.
- ❌ Hacer fine-tuning.

Todo eso es Etapa 3 y 4.

## Criterio de éxito de Etapa 2

- [x] `training_data/train.jsonl` existe y tiene ~400 líneas. → **341**
- [x] `training_data/validation.jsonl` existe y tiene ~50 líneas. → **42**
- [x] `training_data/test_questions.json` existe y tiene ~50 entradas. → **42**
- [x] Cada uno de los 10 intents está representado en los 3 splits.
- [x] 5 ejemplos aleatorios revisados manualmente: redacción coherente, números reales, sin placeholders, no afirma causalidad cuando aplica.
- [x] El generador es reproducible (con seed fija). → `seed=42`

## Notas post-implementación

- Los totales por intent: ranking(50) + tendencia(50) + comparación(50) + municipio(50) + tipo(50) + ventas_nac(30) + estacionalidad(30) + parque(20) + relación(45) + resumen(50) = 425.
- **Códigos numéricos en `tipo_accidente`:** algunos años ATUS almacenan TIPACCID como código numérico (`0`–`6`) en lugar de nombre legible. El generador los refleja tal cual — limitación del CSV fuente, no un bug del generador.
- Para regenerar el corpus desde cero: `python -c "from src.training_data_generator import generar_y_guardar_todo; generar_y_guardar_todo()"`
