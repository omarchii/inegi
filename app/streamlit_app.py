"""App Streamlit del INEGI AI Assistant — Etapa 1 (Camino A).

Alcance:
- ATUS por entidad/municipio/tipo de accidente.
- VMRC solo a nivel NACIONAL (ventas auto/camion y parque vehicular).
- Cruce ATUS × VMRC: solo NACIONAL.
- Año tope canónico: 2024 (preliminares 2025/2026 excluidos por defecto).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import analytics
from src.data_processing import (
    ANIO_TOPE_CANONICO,
    ATUS_ANUAL_PATH,
    ATUS_DETALLE_PATH,
    VMRC_PARQUE_PATH,
    VMRC_VENTAS_PATH,
    load_atus_anual,
    load_atus_detalle,
    load_vmrc_parque,
    load_vmrc_ventas,
)
from src.intent_detection import Intent, detectar_intencion
from src.response_generator import construir_prompt


@st.cache_resource(show_spinner="Cargando modelo Qwen-1.5B + adapter LoRA…")
def _cargar_llm():
    """Carga única del modelo fine-tuneado. Cacheado para toda la sesión."""
    from src.llm_finetuned import cargar_modelo
    return cargar_modelo()

# -----------------------------------------------------------------------------
# Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Vialytics MX",
    page_icon="🚦",
    layout="wide",
)

st.title("Vialytics MX")
st.subheader("Analizador Inteligente de Seguridad Vial")
st.markdown(
    "Aplicación de análisis basada en datos abiertos de INEGI. "
    "Permite consultar información sobre accidentes de tránsito, parque vehicular "
    "y ventas nacionales mediante preguntas en lenguaje natural."
)

st.info(
    "**Alcance del análisis** — "
    "ATUS permite análisis por entidad y municipio. "
    "VMRC, con los archivos disponibles, se analiza a nivel nacional. "
    "Por esta razón, la aplicación no estima ventas por estado "
    "ni inventa desgloses que no existen en los datos.",
    icon="ℹ️",
)

with st.sidebar:
    st.header("Configuración")
    incluir_preliminar = st.checkbox(
        f"Incluir cifras preliminares (> {ANIO_TOPE_CANONICO})",
        value=False,
        help="Por defecto el análisis se recorta a 2024 para empatar con ATUS.",
    )
    usar_llm = st.checkbox(
        "Generar respuesta con IA (Qwen-1.5B fine-tuneado)",
        value=True,
        help=(
            "Si está activado, la app genera una respuesta en lenguaje natural "
            "con el modelo fine-tuneado de Etapa 4. Primera carga: 1–2 min."
        ),
    )


# -----------------------------------------------------------------------------
# Carga de datos (cached)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _cargar_datos(incluir_preliminar: bool):
    err: list[str] = []
    atus_anual = atus_detalle = vmrc_ventas = vmrc_parque = None
    try:
        atus_anual = load_atus_anual()
    except FileNotFoundError:
        err.append(f"No se encontró {ATUS_ANUAL_PATH}")
    try:
        atus_detalle = load_atus_detalle()
    except FileNotFoundError:
        err.append(f"No se encontró {ATUS_DETALLE_PATH}")
    try:
        vmrc_ventas = load_vmrc_ventas(incluir_preliminar=incluir_preliminar)
    except FileNotFoundError:
        err.append(f"No se encontró {VMRC_VENTAS_PATH}")
    try:
        vmrc_parque = load_vmrc_parque(incluir_preliminar=incluir_preliminar)
    except FileNotFoundError:
        err.append(f"No se encontró {VMRC_PARQUE_PATH}")
    return atus_anual, atus_detalle, vmrc_ventas, vmrc_parque, err


atus_anual, atus_detalle, vmrc_ventas, vmrc_parque, errores = _cargar_datos(
    incluir_preliminar
)

with st.sidebar:
    st.header("Estado de datos")
    if atus_anual is not None:
        st.success(f"ATUS: {len(atus_anual):,} filas anuales")
        st.caption(
            f"Años {atus_anual['anio'].min()}–{atus_anual['anio'].max()} · "
            f"{atus_anual['entidad'].nunique()} entidades"
        )
    else:
        st.error("ATUS no disponible")
    if vmrc_ventas is not None:
        st.success(f"VMRC ventas: {len(vmrc_ventas):,} filas")
        st.caption(
            f"Años {vmrc_ventas['anio'].min()}–{vmrc_ventas['anio'].max()} · "
            f"tipos: {sorted(vmrc_ventas['tipo'].unique())}"
        )
    else:
        st.error("VMRC ventas no disponible")
    if vmrc_parque is not None:
        st.success(f"VMRC parque: {len(vmrc_parque):,} filas")
    else:
        st.error("VMRC parque no disponible")
    if errores:
        for e in errores:
            st.warning(e)
        st.info(
            "Genera los CSV procesados con `python -m src.data_processing` "
            "o el notebook `notebooks/01_data_exploration.ipynb`."
        )


# -----------------------------------------------------------------------------
# Input
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Consulta los datos")
ejemplos = [
    "¿Qué estados tuvieron más accidentes en 2023?",
    "¿Cómo cambiaron los accidentes en Yucatán de 2010 a 2023?",
    "¿Qué municipios de Yucatán tuvieron más accidentes en 2023?",
    "¿Qué tipos de accidente fueron más frecuentes en Yucatán en 2023?",
    "¿Cómo evolucionaron las ventas nacionales de autos de 2015 a 2024?",
    "¿Cómo ha cambiado el parque vehicular nacional con los años?",
    "¿Hay relación entre ventas nacionales y accidentes nacionales de 2015 a 2023?",
]
ejemplo = st.selectbox("Ejemplos (opcional)", options=[""] + ejemplos, index=0)
pregunta = st.text_input(
    "Tu pregunta:",
    value=ejemplo,
    placeholder="Escribe una pregunta sobre accidentes (por estado/municipio) "
    "o ventas/parque vehicular nacional...",
)
ejecutar = st.button("Analizar", type="primary", disabled=not pregunta.strip())


# -----------------------------------------------------------------------------
# Dispatcher intent -> analytics
# -----------------------------------------------------------------------------
def _dispatch(intent: Intent) -> tuple[pd.DataFrame | None, str | None]:
    s = intent.slots
    name = intent.name
    tipo = s.get("tipo", "total")

    def _need(df, etiqueta: str):
        if df is None:
            raise RuntimeError(f"Dataset {etiqueta} no disponible.")
        return df

    try:
        if name == "ranking_accidentes":
            df_atus = _need(atus_anual, "ATUS")
            anio = s.get("anio")
            if anio is None:
                anio = int(df_atus["anio"].max())
                s["anio"] = anio  # para que el prompt y el título lo vean
                s["anio_default"] = True
            return analytics.ranking_accidentes(
                df_atus, anio=int(anio),
                top_n=int(s.get("top_n", 5)),
            ), None

        if name == "tendencia_accidentes":
            estado = s.get("estado")
            if not estado:
                return None, "Falta el estado."
            return analytics.tendencia_accidentes(
                _need(atus_anual, "ATUS"), estado=estado
            ), None

        if name == "comparacion_accidentes":
            e1, e2 = s.get("estado_1"), s.get("estado_2")
            if not (e1 and e2):
                return None, "Faltan dos estados para comparar."
            return analytics.comparar_accidentes_estados(
                _need(atus_anual, "ATUS"), e1, e2
            ), None

        if name == "accidentes_por_municipio":
            estado = s.get("estado")
            if not estado:
                return None, "Falta el estado."
            return analytics.accidentes_por_municipio(
                _need(atus_detalle, "ATUS detalle"),
                estado=estado, anio=s.get("anio"),
                top_n=int(s.get("top_n", 10)),
            ), None

        if name == "accidentes_por_tipo":
            return analytics.accidentes_por_tipo(
                _need(atus_detalle, "ATUS detalle"),
                estado=s.get("estado"), anio=s.get("anio"),
                top_n=int(s.get("top_n", 10)),
            ), None

        if name == "tendencia_ventas_nacional":
            return analytics.tendencia_ventas_nacional(
                _need(vmrc_ventas, "VMRC ventas"), tipo=tipo,
            ), None

        if name == "estacionalidad_ventas_nacional":
            df_v = _need(vmrc_ventas, "VMRC ventas")
            anio = s.get("anio")
            if anio is None:
                anio = int(df_v["anio"].max())
                s["anio"] = anio
                s["anio_default"] = True
            return analytics.estacionalidad_ventas_nacional(
                df_v, anio=int(anio), tipo=tipo,
            ), None

        if name == "tendencia_parque_nacional":
            return analytics.tendencia_parque_vehicular_nacional(
                _need(vmrc_parque, "VMRC parque"),
            ), None

        if name == "relacion_ventas_accidentes_nacional":
            ai, af = s.get("anio_inicio"), s.get("anio_fin")
            if ai is None or af is None:
                # rango común disponible.
                a = _need(atus_anual, "ATUS")
                v = _need(vmrc_ventas, "VMRC ventas")
                comunes = sorted(set(a["anio"]) & set(v["anio"]))
                if not comunes:
                    return None, "No hay años en común entre ATUS y VMRC."
                ai, af = comunes[0], comunes[-1]
            return analytics.relacion_ventas_accidentes_nacional(
                _need(atus_anual, "ATUS"),
                _need(vmrc_ventas, "VMRC ventas"),
                anio_inicio=int(ai), anio_fin=int(af), tipo=tipo,
            ), None

        if name == "resumen_estado":
            estado = s.get("estado")
            if not estado:
                return None, "Falta el estado."
            partes = []
            if atus_anual is not None:
                try:
                    t_acc = analytics.tendencia_accidentes(
                        atus_anual, estado
                    ).rename(columns={"total_accidentes": "valor"})
                    t_acc["serie"] = "accidentes"
                    partes.append(t_acc[["entidad", "anio", "serie", "valor"]])
                except ValueError:
                    pass
            if not partes:
                return None, f"No hay datos para {estado}."
            return pd.concat(partes, ignore_index=True), None

        return None, "Pregunta no soportada."
    except (ValueError, KeyError, RuntimeError) as e:
        return None, str(e)


# -----------------------------------------------------------------------------
# Gráficas
# -----------------------------------------------------------------------------
def _graficar(intent_name: str, df: pd.DataFrame, slots: dict[str, Any]):
    if df is None or df.empty:
        return None
    tipo = slots.get("tipo", "total")

    if intent_name == "ranking_accidentes":
        return px.bar(
            df, x="entidad", y="total_accidentes",
            title=f"Top accidentes — {slots.get('anio')}",
        )
    if intent_name == "tendencia_accidentes":
        return px.line(
            df, x="anio", y="total_accidentes", markers=True,
            title=f"Tendencia accidentes — {slots.get('estado')}",
        )
    if intent_name == "comparacion_accidentes":
        e1, e2 = slots.get("estado_1"), slots.get("estado_2")
        if e1 in df.columns and e2 in df.columns:
            largo = df.melt(
                id_vars="anio", value_vars=[e1, e2],
                var_name="entidad", value_name="valor",
            )
            return px.line(
                largo, x="anio", y="valor", color="entidad", markers=True,
                title=f"{e1} vs {e2}",
            )
    if intent_name == "accidentes_por_municipio":
        return px.bar(
            df, x="municipio", y="total_accidentes",
            title=f"Top municipios — {slots.get('estado')}"
            + (f" ({slots.get('anio')})" if slots.get("anio") else ""),
        )
    if intent_name == "accidentes_por_tipo":
        return px.bar(
            df, x="tipo_accidente", y="total_accidentes",
            title="Distribución por tipo de accidente",
        )
    if intent_name == "tendencia_ventas_nacional":
        return px.line(
            df, x="anio", y="total_ventas", markers=True,
            title=f"Ventas nacionales ({tipo}) — anuales",
        )
    if intent_name == "estacionalidad_ventas_nacional":
        return px.bar(
            df, x="mes", y="total_ventas",
            title=f"Estacionalidad ventas {tipo} — {slots.get('anio')}",
        )
    if intent_name == "tendencia_parque_nacional":
        return px.line(
            df, x="anio", y="total_parque_cierre", markers=True,
            title="Parque vehicular nacional (cierre anual)",
        )
    if intent_name == "relacion_ventas_accidentes_nacional":
        cols = [c for c in ("total_ventas", "total_accidentes") if c in df.columns]
        if cols:
            largo = df.melt(
                id_vars="anio", value_vars=cols,
                var_name="serie", value_name="valor",
            )
            return px.line(
                largo, x="anio", y="valor", color="serie", markers=True,
                title=f"Ventas ({tipo}) vs accidentes — Nacional",
            )
    if intent_name == "resumen_estado":
        return px.line(
            df, x="anio", y="valor", color="serie", markers=True,
            title=f"Resumen — {slots.get('estado')}",
        )
    return None


# -----------------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------------
if ejecutar and pregunta.strip():
    intent = detectar_intencion(pregunta)

    with st.expander("Intención detectada", expanded=False):
        st.json(
            {
                "intent": intent.name,
                "slots": intent.slots,
                "confianza": intent.confianza,
            }
        )

    if intent.name == "pregunta_no_soportada":
        st.error(
            "No pude entender la pregunta. Intenta mencionar un tema "
            "(accidentes / ventas / parque), una entidad (para accidentes) "
            "y/o un año."
        )
    else:
        if intent.slots.get("entidad_ignorada_vmrc"):
            st.warning(
                f"VMRC (ventas / parque) solo está disponible a nivel "
                f"**nacional**. Ignoré la entidad "
                f"«{intent.slots['entidad_ignorada_vmrc']}» y respondo con "
                f"datos nacionales.",
                icon="⚠️",
            )
        df_res, err = _dispatch(intent)
        if intent.slots.get("anio_default"):
            st.info(
                f"No mencionaste un año, así que usé el más reciente "
                f"disponible: **{intent.slots['anio']}**.",
                icon="📅",
            )
        if err:
            st.error(err)
        elif df_res is None or df_res.empty:
            st.warning("La consulta no devolvió datos.")
        else:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader("Resultados calculados")
                st.dataframe(df_res, use_container_width=True)
            with c2:
                st.subheader("Visualización")
                fig = _graficar(intent.name, df_res, intent.slots)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sin gráfica para esta intención.")

            prompt = construir_prompt(
                pregunta_usuario=pregunta,
                intent=intent.name,
                dataframe_resultado=df_res,
                contexto={"slots": intent.slots},
            )
            st.subheader("Prompt enviado al modelo")
            with st.expander("Ver prompt completo", expanded=False):
                st.code(prompt, language="markdown")

            if usar_llm:
                try:
                    model, tokenizer, backend = _cargar_llm()
                except Exception as e:
                    st.error(
                        f"No se pudo cargar el modelo fine-tuneado: {e}\n\n"
                        f"Desactiva el toggle 'Generar respuesta con IA' en la "
                        f"barra lateral para usar la app sin LLM."
                    )
                else:
                    from src.llm_finetuned import generar_respuesta
                    st.subheader("Respuesta generada")
                    st.caption(f"Backend: `{backend}` · Modelo: Qwen-1.5B + LoRA")
                    with st.spinner("Generando respuesta…"):
                        respuesta = generar_respuesta(model, tokenizer, prompt)
                    st.markdown(respuesta)

