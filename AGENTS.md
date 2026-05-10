# AGENTS.md — Contexto para futuras sesiones de Codex

## Qué es este proyecto

Proyecto escolar de IA generativa. Asistente analítico que responde preguntas en lenguaje natural sobre dos datasets de INEGI:

- **ATUS** — Accidentes de tránsito en zonas urbanas y suburbanas (1997–2024).
- **VMRC** — Ventas y parque vehicular (datos NACIONALES).

## Principio fundamental (NO violar)

El LLM **no calcula y no inventa cifras**. Toda métrica numérica se calcula con pandas; el modelo generativo solo redacta a partir de los datos que recibe en el prompt.

## Alcance — Camino A

Los archivos VMRC descargados son **nacionales mensuales**, no estatales. Por eso:

- ATUS: por **entidad / municipio / año / tipo de accidente**.
- VMRC: solo a nivel **nacional**.
- Cruce ATUS × VMRC: solo a nivel **nacional**.
- Año tope canónico: **2024**. Preliminares 2025/2026 etiquetadas, excluidas del análisis principal.
- VMRC: ventas combinadas (auto + camion) por defecto, separables por `tipo='auto'|'camion'`.

## Esquemas canónicos

```
ATUS detalle (data/processed/atus_detalle.csv):
    entidad, id_entidad, municipio, anio, tipo_accidente, total_accidentes

ATUS anual (data/processed/atus_anual.csv):
    entidad, anio, total_accidentes

VMRC ventas mensual (data/processed/vmrc_ventas_mensual.csv):
    anio, mes, tipo ('auto'|'camion'), total_ventas, estatus, preliminar

VMRC parque mensual (data/processed/vmrc_parque_mensual.csv):
    anio, mes, total_parque, estatus, preliminar
```

## Funciones (src/analytics.py)

ATUS: `ranking_accidentes`, `tendencia_accidentes`, `comparar_accidentes_estados`, `accidentes_por_municipio`, `accidentes_por_tipo`.
VMRC nacional: `tendencia_ventas_nacional`, `estacionalidad_ventas_nacional`, `tendencia_parque_vehicular_nacional`.
Cruce nacional: `relacion_ventas_accidentes_nacional`.

## Intents (src/intent_detection.py)

`ranking_accidentes`, `tendencia_accidentes`, `comparacion_accidentes`, `accidentes_por_municipio`, `accidentes_por_tipo`, `tendencia_ventas_nacional`, `estacionalidad_ventas_nacional`, `tendencia_parque_nacional`, `relacion_ventas_accidentes_nacional`, `resumen_estado`, `pregunta_no_soportada`.

Slots: `estado`, `estado_1`, `estado_2`, `municipio`, `anio`, `anio_inicio`, `anio_fin`, `top_n`, `tipo` (auto|camion|total).

## Hallazgos / cosas que NO se deben olvidar

- **Bug ANIO=1 en ATUS crudo:** 23 de 28 archivos. El año se toma del nombre del archivo (`_anio_desde_nombre`). NO leer el año de la columna.
- **Espacio en columna VMRC:** `AUTO_DE_LUJO ` (con espacio); se limpia con `.strip().upper()` en headers.
- **Tabs/espacios en IDs:** `ID_ENTIDAD`, `ID_MUNICIPIO`, `ID_MES` traen `\t` y espacios; se limpian con `.str.strip().str.zfill(N)`.
- **Catálogo de entidades:** `ID_ENTIDAD` (01–32) → nombre, vía `tc_entidad.csv` y luego `normalizar_entidad`.
- **Salto metodológico ATUS 2022:** muchas entidades duplicaron o triplicaron sus accidentes entre 2021 y 2022. Probable cambio de cobertura. Mencionar como limitación cuando se hagan tendencias largas.
- **Correlación ventas-accidentes nacional 2015–2023 ≈ -0.033** (prácticamente nula). Buen ejemplo en el reporte para mostrar que los datos no soportan causalidad.
- **Códigos numéricos en `tipo_accidente` — RESUELTO:** los archivos ATUS 1997–2021 guardaban TIPACCID como código numérico (0–9). Se agregó `TIPACCID_MAPA` en `data_processing.py` y se aplica en `clean_atus()`. Mapeo: 0=Certificado cero, 1=Colisión con vehículo automotor, 2=Colisión con peatón (atropellamiento), 3=Colisión con animal, 4=Colisión con objeto fijo, 5=Volcadura, 6=Caída de pasajero, 7=Salida del camino, 8=Incendio, 9=Colisión con ferrocarril. `atus_detalle.csv` y training_data regenerados.

## Etapas

1. **Etapa 1 — COMPLETA Y VALIDADA:** pipeline pandas + intent + prompt + Streamlit corriendo con datos reales.
2. **Etapa 2 — COMPLETA Y VALIDADA:** dataset de entrenamiento generado con plantillas determinísticas. 425 ejemplos totales → train=341 / val=42 / test=42. Archivos en `training_data/`. Módulo en `src/training_data_generator.py`, notebook en `notebooks/02_generate_training_data.ipynb`.
3. **Etapa 3:** `03_baseline_flan_qwen.ipynb` — FLAN-T5-base + Qwen2.5-1.5B-Instruct vanilla.
4. **Etapa 4:** `04_finetune_qwen_lora_colab.ipynb` — LoRA/QLoRA en Colab.
5. **Etapa 5:** Conectar modelo fine-tuneado a `streamlit_app.py`.

## Siguiente paso al retomar

**Etapas 1 y 2 están cerradas. Fix TIPACCID aplicado (datos y training data regenerados).** La siguiente es Etapa 3.

Lee `docs/ETAPA_3_PLAN.md` antes de tocar código. Tiene el plan completo para el notebook de baseline.

## Reglas de código

- `pathlib.Path` para todas las rutas.
- Type hints donde sume.
- Funciones de analytics **devuelven DataFrames**, no imprimen.
- Errores con mensajes en español.
- Sin dependencias de fine-tuning hasta Etapa 3.

## Reglas para el LLM (en response_generator.py)

1. Responder en español.
2. Usar solo los datos del prompt.
3. No afirmar causalidad — habla de correlación / asociación.
4. Estructura ejecutiva fija: Resumen · Datos principales · Interpretación · Limitaciones.

## Hardware del usuario

- Local: Windows, i7, RTX 3060 Ti, 32 GB RAM.
- Entrenamiento: Google Colab.
- Modelos: Qwen2.5-1.5B-Instruct (fine-tune), FLAN-T5-base (baseline).

## Comandos

```bash
# activar venv del proyecto (siempre primero)
cd /Users/omarchi/Developer/inegi
source .venv/bin/activate

# instalar deps (solo la primera vez en cada máquina)
pip install -r requirements.txt

# regenerar procesados (solo si data/processed/ está vacío)
python -c "from src.data_processing import construir_procesados; construir_procesados()"

# regenerar training data (solo si training_data/ está vacío o cambió el código)
python -c "from src.training_data_generator import generar_y_guardar_todo; generar_y_guardar_todo()"

# correr la app — usar `python -m streamlit` para evitar cache de zsh
python -m streamlit run app/streamlit_app.py
```

## Notas de entorno

- El usuario en macOS tuvo problemas mezclando Anaconda base, venv PDM y el venv del proyecto. La regla: **usar siempre `python -m <comando>`** dentro del `.venv` del proyecto (`.venv/bin/python`).
- Si `which streamlit` apunta al venv pero el comando ejecuta el de Anaconda, es cache de zsh. Solución: `hash -r`.

## Notas para Codex

- El usuario prefiere planes cortos antes de implementar grandes bloques.
- No hagas fine-tuning hasta que se pida explícitamente.
- No conectes APIs de pago.
- Si algo se aparta del esquema canónico, document antes de cambiarlo.
