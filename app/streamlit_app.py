"""App Streamlit del INEGI AI Assistant — Etapa 1 (Camino A).

Alcance:
- ATUS por entidad/municipio/tipo de accidente.
- VMRC solo a nivel NACIONAL (ventas auto/camion y parque vehicular).
- Cruce ATUS × VMRC: solo NACIONAL.
- Año tope canónico: 2024 (preliminares 2025/2026 excluidos por defecto).
"""
from __future__ import annotations

import base64
import html as html_lib
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

HERO_IMAGE_PATH = ROOT / "app" / "assets" / "vialidad_hero.jpg"


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

@st.cache_data(show_spinner=False)
def _asset_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    mime = (
        "image/jpeg"
        if path.suffix.lower() in {".jpg", ".jpeg"}
        else "image/png"
    )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _inyectar_estilos(hero_uri: str) -> None:
    if hero_uri:
        hero_background = (
            "linear-gradient(90deg, rgba(8, 13, 18, .86) 0%, "
            "rgba(8, 13, 18, .62) 42%, rgba(8, 13, 18, .18) 100%), "
            f"url('{hero_uri}')"
        )
    else:
        hero_background = "linear-gradient(120deg, #111827 0%, #374151 100%)"
    st.markdown(
        f"""
        <style>
            :root {{
                --bg: #070b12;
                --panel: #0d1420;
                --panel-2: #111b2a;
                --ink: #edf7ff;
                --muted: #8da0b8;
                --line: rgba(139, 166, 196, .22);
                --accent: #33d6c4;
                --accent-2: #7aa7ff;
                --warn: #f0b45b;
                --paper: rgba(255, 255, 255, .045);
            }}
            .stApp {{
                background:
                    radial-gradient(circle at 16% -8%, rgba(51, 214, 196, .22), transparent 34%),
                    radial-gradient(circle at 92% 0%, rgba(122, 167, 255, .18), transparent 30%),
                    linear-gradient(180deg, #070b12 0%, #0b1019 54%, #070b12 100%);
                color: var(--ink);
            }}
            .block-container {{
                max-width: 1220px;
                padding-top: 1.6rem;
                padding-bottom: 4rem;
            }}
            h1, h2, h3, p, label, span, div {{
                letter-spacing: 0;
            }}
            .stApp,
            .stApp p,
            .stApp label {{
                color: var(--ink);
            }}
            .topbar {{
                position: relative;
                min-height: 210px;
                border: 1px solid var(--line);
                border-radius: 18px;
                background-image: {hero_background};
                background-size: cover;
                background-position: center;
                box-shadow: 0 24px 70px rgba(0, 0, 0, .32);
                padding: 30px 34px;
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 24px;
                margin-bottom: 1.2rem;
                overflow: hidden;
            }}
            .topbar::after {{
                content: "";
                position: absolute;
                inset: 0;
                background:
                    linear-gradient(90deg, rgba(7, 11, 18, .92) 0%, rgba(7, 11, 18, .74) 48%, rgba(7, 11, 18, .44) 100%),
                    linear-gradient(180deg, transparent 0%, rgba(7, 11, 18, .75) 100%);
                pointer-events: none;
            }}
            .brand-copy, .signal-stack {{
                position: relative;
                z-index: 1;
            }}
            .eyebrow {{
                color: var(--accent);
                font-size: .82rem;
                font-weight: 800;
                text-transform: uppercase;
                margin-bottom: .45rem;
            }}
            .topbar h1 {{
                color: var(--ink);
                font-size: clamp(2.45rem, 6vw, 5rem);
                line-height: .9;
                margin: 0;
                font-weight: 850;
            }}
            .topbar p {{
                color: #c7d4e5;
                max-width: 680px;
                font-size: 1.05rem;
                line-height: 1.55;
                margin: .85rem 0 0;
            }}
            .signal-stack {{
                display: grid;
                gap: 10px;
                min-width: 250px;
            }}
            .signal {{
                border: 1px solid var(--line);
                border-radius: 999px;
                background: rgba(7, 11, 18, .68);
                color: #d6e5f5;
                padding: .58rem .8rem;
                font-size: .86rem;
                text-align: center;
                backdrop-filter: blur(12px);
            }}
            .scope-note {{
                border: 1px solid var(--line);
                border-left: 3px solid var(--accent);
                border-radius: 12px;
                background: rgba(13, 20, 32, .76);
                color: #b7c7d9;
                padding: .85rem 1rem;
                margin-bottom: 1rem;
            }}
            .query-separator {{
                display: none;
            }}
            .section-label {{
                color: var(--accent);
                font-size: .78rem;
                font-weight: 800;
                letter-spacing: 0;
                text-transform: uppercase;
                margin: 1.25rem 0 .55rem;
            }}
            .query-card,
            .answer-card,
            .viz-card {{
                background: linear-gradient(180deg, rgba(17, 27, 42, .92), rgba(13, 20, 32, .88));
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 1.2rem;
                box-shadow: 0 18px 52px rgba(0, 0, 0, .22);
            }}
            .query-card {{
                margin: 1rem 0 1.25rem;
            }}
            .answer-card {{
                border-color: rgba(51, 214, 196, .34);
                background:
                    linear-gradient(135deg, rgba(51, 214, 196, .10), transparent 36%),
                    linear-gradient(180deg, rgba(17, 27, 42, .96), rgba(10, 16, 26, .96));
            }}
            .answer-card p, .answer-card li {{
                font-size: 1rem;
                line-height: 1.62;
                color: #e8f2fb;
            }}
            .answer-card h1, .answer-card h2, .answer-card h3 {{
                color: var(--ink);
            }}
            .data-wrap {{
                overflow-x: auto;
                border: 1px solid var(--line);
                border-radius: 14px;
                background: rgba(8, 12, 20, .68);
            }}
            .result-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: .92rem;
                color: #dbe8f6;
            }}
            .result-table th {{
                background: rgba(51, 214, 196, .10);
                color: #eaf7ff;
                font-weight: 800;
                text-align: left;
                padding: .72rem .8rem;
                border-bottom: 1px solid var(--line);
                white-space: nowrap;
            }}
            .result-table td {{
                padding: .68rem .8rem;
                border-bottom: 1px solid rgba(139, 166, 196, .14);
                vertical-align: top;
            }}
            .result-table tr:last-child td {{
                border-bottom: 0;
            }}
            [data-testid="stWidgetLabel"] p,
            .stSelectbox label,
            .stTextInput label {{
                color: #d9e6f6 !important;
                font-weight: 800;
            }}
            [data-testid="stTextInputRootElement"],
            .stTextInput [data-baseweb="input"],
            .stTextInput input {{
                background: rgba(7, 11, 18, .88) !important;
                border: 1px solid rgba(139, 166, 196, .34) !important;
                border-radius: 12px !important;
                color: var(--ink) !important;
            }}
            .stTextInput input::placeholder {{
                color: #8da0b8 !important;
                opacity: 1 !important;
            }}
            [data-baseweb="select"] > div {{
                background: rgba(7, 11, 18, .88) !important;
                border: 1px solid rgba(139, 166, 196, .34) !important;
                border-radius: 12px !important;
                color: var(--ink) !important;
            }}
            [data-baseweb="select"] span,
            [data-baseweb="select"] svg {{
                color: var(--ink) !important;
                fill: var(--ink) !important;
            }}
            .stButton > button {{
                border-radius: 12px;
                border: 1px solid rgba(51, 214, 196, .72);
                background: linear-gradient(135deg, #33d6c4, #7aa7ff);
                color: #06101a;
                min-height: 2.75rem;
                font-weight: 850;
                box-shadow: 0 12px 30px rgba(51, 214, 196, .22);
            }}
            .stButton > button:hover {{
                border-color: #ffffff;
                color: #06101a;
                filter: brightness(1.07);
            }}
            [data-testid="stSidebar"] {{
                background: rgba(7, 11, 18, .92);
                border-right: 1px solid var(--line);
            }}
            [data-testid="stSidebar"] * {{
                color: #dcecff !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMetricValue"] {{
                color: var(--accent) !important;
            }}
            [data-testid="stMetric"] {{
                background: transparent;
            }}
            [data-testid="stDataFrame"] {{
                display: none;
            }}
            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stStatusWidget"],
            [data-testid="stDecoration"],
            #MainMenu,
            footer {{
                display: none;
            }}
            .stPlotlyChart {{
                border: 1px solid var(--line);
                border-radius: 18px;
                background: rgba(13, 20, 32, .78);
                padding: .7rem;
            }}
            .stExpander {{
                border-color: var(--line) !important;
                background: rgba(13, 20, 32, .70) !important;
                border-radius: 14px !important;
            }}
            @media (max-width: 760px) {{
                .block-container {{
                    padding-left: 1rem;
                    padding-right: 1rem;
                }}
                .topbar {{
                    min-height: auto;
                    align-items: flex-start;
                    flex-direction: column;
                    padding: 24px;
                }}
                .signal-stack {{
                    min-width: 100%;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


hero_uri = _asset_data_uri(HERO_IMAGE_PATH)
_inyectar_estilos(hero_uri)

st.markdown(
    """
    <section class="topbar">
        <div class="brand-copy">
            <div class="eyebrow">INEGI · ATUS / VMRC</div>
            <h1>Vialytics MX</h1>
            <p>
                Asistente de análisis vial para convertir preguntas en métricas
                verificadas y respuestas ejecutivas en español.
            </p>
        </div>
        <div class="signal-stack">
            <div class="signal">Pandas calcula los números</div>
            <div class="signal">La IA redacta la lectura</div>
            <div class="signal">Sin causalidad inventada</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="scope-note">
        ATUS permite análisis por entidad y municipio. VMRC se conserva a nivel
        nacional; la app no estima ventas estatales ni desgloses inexistentes.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Ajustes")
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
    st.header("Datos")
    if atus_anual is not None:
        st.metric("ATUS anual", f"{len(atus_anual):,}")
        st.caption(
            f"Años {atus_anual['anio'].min()}–{atus_anual['anio'].max()} · "
            f"{atus_anual['entidad'].nunique()} entidades"
        )
    else:
        st.error("ATUS no disponible")
    if vmrc_ventas is not None:
        st.metric("VMRC ventas", f"{len(vmrc_ventas):,}")
        st.caption(
            f"Años {vmrc_ventas['anio'].min()}–{vmrc_ventas['anio'].max()} · "
            f"tipos: {sorted(vmrc_ventas['tipo'].unique())}"
        )
    else:
        st.error("VMRC ventas no disponible")
    if vmrc_parque is not None:
        st.metric("VMRC parque", f"{len(vmrc_parque):,}")
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
st.markdown('<div class="query-separator"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="query-card">
        <div class="section-label">Pregunta al asistente</div>
        <h2 style="margin:0 0 .25rem;color:#edf7ff;">Primero la respuesta de IA</h2>
        <p style="margin:.15rem 0 0;color:#8da0b8;">
            Escribe una consulta en lenguaje natural. La app calcula con pandas,
            envía solo esos datos al modelo y muestra la evidencia al final.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
ejemplos = [
    "¿Qué estados tuvieron más accidentes en 2023?",
    "¿Cómo cambiaron los accidentes en Yucatán de 2010 a 2023?",
    "¿Qué municipios de Yucatán tuvieron más accidentes en 2023?",
    "¿Qué tipos de accidente fueron más frecuentes en Yucatán en 2023?",
    "¿Cómo evolucionaron las ventas nacionales de autos de 2015 a 2024?",
    "¿Cómo ha cambiado el parque vehicular nacional con los años?",
    "¿Hay relación entre ventas nacionales y accidentes nacionales de 2015 a 2023?",
]
ejemplo = st.selectbox("Ejemplos rápidos", options=[""] + ejemplos, index=0)
pregunta = st.text_input(
    "Tu pregunta",
    value=ejemplo,
    placeholder="Escribe una pregunta sobre accidentes (por estado/municipio) "
    "o ventas/parque vehicular nacional...",
)
ejecutar = st.button("Analizar", type="primary")


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
def _aplicar_estilo_figura(fig):
    """Aplica un tema sobrio y consistente a las gráficas."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, system-ui, sans-serif", "color": "#edf7ff"},
        title={"font": {"size": 18}, "x": 0, "xanchor": "left"},
        margin={"l": 20, "r": 20, "t": 56, "b": 36},
        legend_title_text="",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(139,166,196,.16)", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def _graficar(intent_name: str, df: pd.DataFrame, slots: dict[str, Any]):
    if df is None or df.empty:
        return None
    tipo = slots.get("tipo", "total")

    if intent_name == "ranking_accidentes":
        orden = df.sort_values("total_accidentes", ascending=True)
        fig = px.bar(
            orden, x="total_accidentes", y="entidad", orientation="h",
            title=f"Top accidentes — {slots.get('anio')}",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "tendencia_accidentes":
        fig = px.line(
            df, x="anio", y="total_accidentes", markers=True,
            title=f"Tendencia accidentes — {slots.get('estado')}",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "comparacion_accidentes":
        e1, e2 = slots.get("estado_1"), slots.get("estado_2")
        if e1 in df.columns and e2 in df.columns:
            largo = df.melt(
                id_vars="anio", value_vars=[e1, e2],
                var_name="entidad", value_name="valor",
            )
            fig = px.line(
                largo, x="anio", y="valor", color="entidad", markers=True,
                title=f"{e1} vs {e2}",
                color_discrete_sequence=["#33d6c4", "#7aa7ff"],
            )
            return _aplicar_estilo_figura(fig)
    if intent_name == "accidentes_por_municipio":
        orden = df.sort_values("total_accidentes", ascending=True)
        fig = px.bar(
            orden, x="total_accidentes", y="municipio", orientation="h",
            title=f"Top municipios — {slots.get('estado')}"
            + (f" ({slots.get('anio')})" if slots.get("anio") else ""),
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "accidentes_por_tipo":
        orden = df.sort_values("total_accidentes", ascending=True)
        fig = px.bar(
            orden, x="total_accidentes", y="tipo_accidente", orientation="h",
            title="Distribución por tipo de accidente",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "tendencia_ventas_nacional":
        fig = px.line(
            df, x="anio", y="total_ventas", markers=True,
            title=f"Ventas nacionales ({tipo}) — anuales",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "estacionalidad_ventas_nacional":
        fig = px.bar(
            df, x="mes", y="total_ventas",
            title=f"Estacionalidad ventas {tipo} — {slots.get('anio')}",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "tendencia_parque_nacional":
        fig = px.line(
            df, x="anio", y="total_parque_cierre", markers=True,
            title="Parque vehicular nacional (cierre anual)",
            color_discrete_sequence=["#33d6c4"],
        )
        return _aplicar_estilo_figura(fig)
    if intent_name == "relacion_ventas_accidentes_nacional":
        cols = [c for c in ("total_ventas", "total_accidentes") if c in df.columns]
        if cols:
            largo = df.melt(
                id_vars="anio", value_vars=cols,
                var_name="serie", value_name="valor",
            )
            fig = px.line(
                largo, x="anio", y="valor", color="serie", markers=True,
                title=f"Ventas ({tipo}) vs accidentes — Nacional",
                color_discrete_sequence=["#33d6c4", "#7aa7ff"],
            )
            return _aplicar_estilo_figura(fig)
    if intent_name == "resumen_estado":
        fig = px.line(
            df, x="anio", y="valor", color="serie", markers=True,
            title=f"Resumen — {slots.get('estado')}",
            color_discrete_sequence=["#33d6c4", "#7aa7ff"],
        )
        return _aplicar_estilo_figura(fig)
    return None


def _formatear_valor(valor: Any) -> str:
    if pd.isna(valor):
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, int):
        return f"{valor:,}"
    if isinstance(valor, float):
        if valor.is_integer():
            return f"{int(valor):,}"
        if abs(valor) < 1:
            return f"{valor:,.3f}"
        return f"{valor:,.2f}"
    return str(valor)


def _humanizar_columna(columna: str) -> str:
    reemplazos = {
        "anio": "Año",
        "mes": "Mes",
        "entidad": "Entidad",
        "municipio": "Municipio",
        "tipo": "Tipo",
        "tipo_accidente": "Tipo de accidente",
        "total_accidentes": "Accidentes",
        "total_ventas": "Ventas",
        "total_parque_cierre": "Parque vehicular",
        "correlacion_pearson": "Correlación Pearson",
        "serie": "Serie",
        "valor": "Valor",
    }
    return reemplazos.get(columna, columna.replace("_", " ").capitalize())


def _tabla_calculada_html(df: pd.DataFrame, max_filas: int = 40) -> str:
    visible = df.head(max_filas).copy()
    headers = "".join(
        f"<th>{html_lib.escape(_humanizar_columna(col))}</th>"
        for col in visible.columns
    )
    rows = []
    for _, fila in visible.iterrows():
        cells = "".join(
            f"<td>{html_lib.escape(_formatear_valor(valor))}</td>"
            for valor in fila
        )
        rows.append(f"<tr>{cells}</tr>")
    nota = ""
    if len(df) > max_filas:
        nota = (
            f"<p class='scope-note'>Se muestran {max_filas:,} de "
            f"{len(df):,} filas calculadas.</p>"
        )
    return (
        f"{nota}<div class='data-wrap'><table class='result-table'>"
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def _render_tabla_calculada(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-label">Evidencia</div>', unsafe_allow_html=True)
    with st.expander("Datos calculados por pandas", expanded=False):
        st.markdown(_tabla_calculada_html(df), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------------
if ejecutar and not pregunta.strip():
    st.warning("Escribe una pregunta antes de analizar.")

if ejecutar and pregunta.strip():
    intent = detectar_intencion(pregunta)

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
            prompt = construir_prompt(
                pregunta_usuario=pregunta,
                intent=intent.name,
                dataframe_resultado=df_res,
                contexto={"slots": intent.slots},
            )

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

                    st.markdown(
                        '<div class="section-label">Respuesta de IA</div>',
                        unsafe_allow_html=True,
                    )
                    with st.spinner("Generando respuesta…"):
                        respuesta = generar_respuesta(model, tokenizer, prompt)
                    st.markdown('<div class="answer-card">', unsafe_allow_html=True)
                    st.markdown(respuesta)
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.caption(f"Backend: `{backend}` · Modelo: Qwen-1.5B + LoRA")
            else:
                st.info(
                    "La respuesta con IA está desactivada. Abajo quedan los "
                    "datos calculados por pandas para esta consulta."
                )

            fig = _graficar(intent.name, df_res, intent.slots)
            if fig is not None:
                st.markdown(
                    '<div class="section-label">Visualización secundaria</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(fig, use_container_width=True)

            _render_tabla_calculada(df_res)

            with st.expander("Auditoría técnica", expanded=False):
                st.json(
                    {
                        "intent": intent.name,
                        "slots": intent.slots,
                        "confianza": intent.confianza,
                    }
                )
                st.code(prompt, language="markdown")
