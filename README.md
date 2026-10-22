# INEGI AI Assistant

Asistente analítico sobre datos abiertos de INEGI:
- **ATUS** — Accidentes de tránsito en zonas urbanas y suburbanas (1997–2024).
- **VMRC** — Ventas y parque vehicular (datos **nacionales**).

> **Principio del proyecto:** el LLM **no inventa cifras**. Todo número viene de pandas. El modelo solo redacta.

## Alcance (Camino A)

Los archivos VMRC descargados son a nivel **nacional**, no estatal. Por eso el alcance del proyecto es:

- ATUS: análisis por **entidad / municipio / año / tipo de accidente**.
- VMRC: análisis solo a nivel **nacional** (ventas auto/camion, parque vehicular, estacionalidad mensual).
- Cruce ATUS × VMRC: solo a nivel **nacional**.
- Año tope canónico: **2024**. Las cifras preliminares 2025/2026 se etiquetan y se excluyen del análisis principal (se pueden incluir desde la sidebar de la app).

## Estado actual — Etapa 1

- [x] Estructura del repo y andamiaje
- [x] Carga + limpieza al esquema canónico (28 archivos ATUS + 4 VMRC)
- [x] 10 funciones de análisis (`src/analytics.py`)
- [x] Detección de intención por reglas (10 intents)
- [x] Generador de prompt ejecutivo
- [x] App Streamlit (tabla + gráfica + prompt)
- [x] Smoke test con datos reales
- [ ] Etapa 2: generación de dataset de entrenamiento
- [ ] Etapa 3: baseline FLAN-T5 / Qwen2.5
- [ ] Etapa 4: fine-tuning con LoRA
- [ ] Etapa 5: integración del modelo a la app

## Stack

- Python · pandas · Streamlit · Plotly
- Próximas etapas: Hugging Face + LoRA/QLoRA, Qwen2.5-1.5B-Instruct, FLAN-T5-base.

## Instalación

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Datos

Los archivos crudos se colocan en `data/raw/` con esta estructura (tal como vienen de INEGI):

```
data/raw/
├── conjunto_de_datos_atus_anual_csv/
│   ├── conjunto_de_datos/atus_anual_1997.csv … atus_anual_2024.csv
│   ├── catalogos/tc_entidad.csv (y otros)
│   └── diccionario_de_datos/, metadatos/
└── conjunto_de_datos_vmrc_mensual_csv/
    ├── conjunto_de_datos/
    │   ├── vmrc_vehiculos_mensual_tr_cifra_1991_2026.csv
    │   ├── vmrc_venta_veh_mensual_tr_cifra_2015_2026.csv
    │   ├── vmrc_venta_cam_mensual_tr_cifra_2015_2026.csv
    │   └── vmrc_produccion_mensual_tr_cifra_2015_2026.csv
    └── diccionario_de_datos/, metadatos/
```

### Generar procesados

```bash
python -c "from src.data_processing import construir_procesados; construir_procesados()"
```

O abre `notebooks/01_data_exploration.ipynb` y corre todas las celdas.

Esto produce:

```
data/processed/
├── atus_anual.csv         # entidad, anio, total_accidentes  (32×28 ≈ 896 filas)
├── atus_detalle.csv       # entidad, id_entidad, municipio, anio, tipo_accidente, total_accidentes
├── vmrc_ventas_mensual.csv# anio, mes, tipo, total_ventas, estatus, preliminar
└── vmrc_parque_mensual.csv# anio, mes, total_parque, estatus, preliminar
```

## Correr la app

```bash
streamlit run app/streamlit_app.py
```

## Estructura

```
inegi-ai-assistant/
├── app/streamlit_app.py
├── data/{raw,processed}/
├── notebooks/01_data_exploration.ipynb
├── src/
│   ├── data_processing.py     # carga + limpieza + esquema canónico
│   ├── analytics.py           # 10 funciones de análisis
│   ├── intent_detection.py    # detección por reglas
│   ├── response_generator.py  # construcción de prompt
│   └── utils.py               # rutas + normalización entidades
├── training_data/, reports/
├── requirements.txt
└── README.md
```

## Funciones disponibles (analytics.py)

**ATUS (por entidad):**
- `ranking_accidentes(df, anio, top_n)`
- `tendencia_accidentes(df, estado)`
- `comparar_accidentes_estados(df, e1, e2)`
- `accidentes_por_municipio(df_detalle, estado, anio?, top_n)`
- `accidentes_por_tipo(df_detalle, estado?, anio?, top_n)`

**VMRC (nacional):**
- `tendencia_ventas_nacional(df, tipo='total'|'auto'|'camion')`
- `estacionalidad_ventas_nacional(df, anio, tipo)`
- `tendencia_parque_vehicular_nacional(df)`

**Cruce nacional:**
- `relacion_ventas_accidentes_nacional(df_atus, df_vmrc, anio_inicio, anio_fin, tipo)`

## Ejemplos de preguntas

- ¿Qué estados tuvieron más accidentes en 2023?
- ¿Cómo cambiaron los accidentes en Yucatán de 2010 a 2023?
- Compara Yucatán y Quintana Roo en accidentes.
- Top 5 municipios con más accidentes en Jalisco en 2022.
- Distribución por tipo de accidente en 2023.
- Tendencia de ventas de automóviles en México (nacional).
- Ventas mensuales de vehículos en 2023 (nacional).
- Tendencia del parque vehicular nacional.
- ¿Hay relación entre ventas de vehículos y accidentes a nivel nacional entre 2015 y 2023?
- Dame un resumen ejecutivo de movilidad para Yucatán.

## Notas / hallazgos durante exploración

- **Bug en CSV crudo de ATUS:** la columna `ANIO` aparece corrupta (=1) en 23 de 28 archivos. El año real se toma del nombre del archivo (`atus_anual_YYYY.csv`).
- **Espacio en columna VMRC:** `AUTO_DE_LUJO ` viene con espacio al final; se normaliza.
- **Salto en accidentes 2022:** muchas entidades muestran un salto fuerte entre 2021 y 2022 (ej. Yucatán: 2,378 → 9,015). Posible cambio metodológico de cobertura por parte de INEGI; documentar como limitación al interpretar tendencias largas.
- **Correlación ventas-accidentes nacional (2015–2023): -0.033** ≈ cero. Refuerza el principio de no afirmar causalidad.

## Reglas de generación (codificadas en el prompt)

1. Responder en español.
2. Usar solo los datos calculados — no inventar cifras.
3. No afirmar causalidad cuando solo hay correlación.
4. Estructura ejecutiva: Resumen · Datos · Interpretación · Limitaciones.
