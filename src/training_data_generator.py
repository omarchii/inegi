"""Generador del dataset de entrenamiento — Etapa 2.

Lógica completamente determinística (sin APIs ni modelos).
Todos los números se extraen de los DataFrames calculados por src/analytics.py.

Uso rápido:
    from src.training_data_generator import generar_y_guardar_todo
    generar_y_guardar_todo()
"""
from __future__ import annotations

import json
import re
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics import (
    accidentes_por_municipio,
    accidentes_por_tipo,
    comparar_accidentes_estados,
    estacionalidad_ventas_nacional,
    ranking_accidentes,
    relacion_ventas_accidentes_nacional,
    tendencia_accidentes,
    tendencia_parque_vehicular_nacional,
    tendencia_ventas_nacional,
)
from .response_generator import construir_prompt
from .utils import ENTIDADES_CANONICAS, PROCESSED_DIR, TRAINING_DATA_DIR

# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------
_MESES: dict[int, str] = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

_TIPO_LABEL: dict[str, str] = {
    "total": "vehículos (autos y camiones)",
    "auto": "autos",
    "camion": "camiones",
}


def _fmt(n: Any) -> str:
    """Entero con separadores de miles."""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def _pct(v: Any) -> str:
    """Cambio porcentual con signo. Devuelve N/D si NaN."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/D"
    return f"{float(v):+.1f}%"


def _pick_template(templates: list[str], slots: dict) -> str:
    """Devuelve un template aleatorio cuyos placeholders {x} estén en slots."""
    valid = [
        t for t in templates
        if all(k in slots for k in re.findall(r"\{(\w+)\}", t))
    ]
    return random.choice(valid if valid else templates)


# ---------------------------------------------------------------------------
# Plantillas de preguntas (≥7 por intent)
# ---------------------------------------------------------------------------
TEMPLATES_PREGUNTA: dict[str, list[str]] = {
    "ranking_accidentes": [
        "¿Qué estados tuvieron más accidentes de tránsito en {anio}?",
        "Dame el top {top_n} de entidades con más accidentes viales en {anio}.",
        "Ranking de accidentes por entidad para {anio}.",
        "¿Cuáles fueron los {top_n} estados con mayor número de accidentes en {anio}?",
        "Muéstrame las entidades con más accidentes de tráfico en {anio}.",
        "¿En qué estados ocurrieron más accidentes de tránsito durante {anio}?",
        "Lista las {top_n} entidades con el mayor registro de accidentes en {anio}.",
        "¿Qué entidades lideraron el conteo de accidentes en {anio}?",
        "¿Cuál fue el top {top_n} de estados más accidentados en {anio}?",
    ],
    "tendencia_accidentes": [
        "¿Cómo ha evolucionado el número de accidentes en {estado} a lo largo del tiempo?",
        "Muéstrame la tendencia de accidentes viales en {estado}.",
        "¿Cuántos accidentes ha habido en {estado} por año?",
        "¿Ha aumentado o disminuido la accidentalidad en {estado}?",
        "Dame la serie histórica de accidentes para {estado}.",
        "¿Cuál es la evolución anual de siniestros en {estado}?",
        "Análisis de tendencia de accidentes en {estado}.",
        "¿Cómo varían los accidentes anuales en {estado}?",
        "Evolución histórica de accidentes viales en {estado}.",
    ],
    "comparacion_accidentes": [
        "¿Cuál de los dos estados, {estado_1} o {estado_2}, tiene más accidentes?",
        "Compara los accidentes viales entre {estado_1} y {estado_2}.",
        "¿Cómo se compara la accidentalidad de {estado_1} frente a {estado_2}?",
        "Diferencia de accidentes entre {estado_1} y {estado_2} por año.",
        "¿Qué estado registra más accidentes: {estado_1} o {estado_2}?",
        "Historial comparativo de accidentes: {estado_1} vs {estado_2}.",
        "¿Cuál es la brecha de accidentalidad entre {estado_1} y {estado_2}?",
        "Comparación anual de siniestros: {estado_1} contra {estado_2}.",
    ],
    "accidentes_por_municipio": [
        "¿Qué municipios de {estado} tienen más accidentes viales?",
        "Dame los {top_n} municipios más peligrosos de {estado}.",
        "Top {top_n} municipios con más accidentes en {estado} en {anio}.",
        "¿Qué municipios de {estado} registraron más accidentes en {anio}?",
        "¿Cuáles son los municipios más accidentados de {estado}?",
        "Municipios de {estado} con mayor número de accidentes en {anio}.",
        "Ranking de municipios por accidentes en {estado}.",
        "¿Dónde ocurren más accidentes dentro de {estado}?",
    ],
    "accidentes_por_tipo": [
        "¿Qué tipos de accidente son más frecuentes en {estado}?",
        "Distribución de accidentes por tipo en {estado} durante {anio}.",
        "¿Cuáles son los tipos de accidente más comunes en México?",
        "¿Qué categorías de accidente predominan en {estado}?",
        "Distribución por tipo de accidente a nivel nacional en {anio}.",
        "¿Qué tipos de siniestro ocurren más en {estado} en {anio}?",
        "¿Qué tipo de accidente es más frecuente a nivel nacional?",
        "Análisis por tipo de accidente en {estado}.",
    ],
    "tendencia_ventas_nacional": [
        "¿Cómo han evolucionado las ventas de vehículos en México?",
        "Dame la tendencia de ventas de {tipo} a nivel nacional.",
        "¿Cómo han variado las ventas anuales de vehículos en el país?",
        "Serie histórica de ventas nacionales de {tipo}.",
        "¿Cuántos vehículos tipo {tipo} se han vendido en México por año?",
        "Tendencia de ventas vehiculares nacionales ({tipo}).",
        "¿Cómo han cambiado las ventas de autos en México a lo largo del tiempo?",
        "Evolución anual de ventas de vehículos en México.",
        "¿Cuántos vehículos se han vendido en México a lo largo de los años?",
        "¿En qué año se vendieron más vehículos en México?",
    ],
    "estacionalidad_ventas_nacional": [
        "¿En qué mes se venden más vehículos en México en {anio}?",
        "Ventas mensuales de {tipo} en México durante {anio}.",
        "¿Cuál es el patrón estacional de ventas de vehículos en {anio}?",
        "¿En qué meses del {anio} cayeron las ventas de {tipo}?",
        "Distribución mensual de ventas vehiculares nacionales en {anio}.",
        "¿Cómo se distribuyen las ventas de vehículos a lo largo del año {anio}?",
        "Estacionalidad de ventas de {tipo} en el mercado nacional ({anio}).",
    ],
    "tendencia_parque_nacional": [
        "¿Cómo ha crecido el parque vehicular en México?",
        "Dame la evolución del parque vehicular registrado en México.",
        "¿Cuántos vehículos circulan en México por año?",
        "Tendencia del parque vehicular nacional registrado.",
        "¿Ha aumentado el número de autos en circulación en México?",
        "¿Cuál es la trayectoria del parque vehicular en el país?",
        "Evolución anual del parque vehicular en circulación en México.",
        "¿Cómo ha variado el total de vehículos registrados en México?",
        "Serie histórica del parque vehicular nacional.",
        "¿Cuál es la tendencia del parque vehicular a nivel nacional?",
        "¿Ha crecido el parque vehicular en México a lo largo de los años?",
        "Muéstrame cuántos vehículos hay registrados en México año a año.",
        "¿Cuántos vehículos estaban en circulación en México en los últimos años?",
        "Análisis del parque vehicular registrado en México.",
        "¿Qué tan rápido ha crecido el parque vehicular en México?",
        "Dame los datos históricos del parque vehicular nacional.",
        "¿Cuál es el tamaño del parque vehicular en México?",
        "Evolución histórica del número de vehículos en circulación en México.",
        "¿Cómo se ha expandido el parque vehicular registrado en el país?",
        "Serie anual del parque vehicular en circulación a nivel nacional.",
    ],
    "relacion_ventas_accidentes_nacional": [
        "¿Existe relación entre las ventas de vehículos y los accidentes en México "
        "entre {anio_inicio} y {anio_fin}?",
        "¿Cómo se correlacionan las ventas de {tipo} con los accidentes viales "
        "entre {anio_inicio} y {anio_fin}?",
        "Relación entre ventas de vehículos y accidentes nacionales "
        "({anio_inicio}-{anio_fin}).",
        "¿A más ventas de autos, más accidentes? Analiza el periodo "
        "{anio_inicio}-{anio_fin}.",
        "Correlación entre ventas de {tipo} y accidentes de tránsito "
        "({anio_inicio}-{anio_fin}).",
        "¿Las ventas vehiculares explican los accidentes entre {anio_inicio} "
        "y {anio_fin}?",
        "Asociación entre ventas de {tipo} y accidentes nacionales "
        "de {anio_inicio} a {anio_fin}.",
    ],
    "resumen_estado": [
        "Dame un resumen de accidentalidad en {estado}.",
        "¿Cómo está {estado} en términos de accidentes viales?",
        "Resumen ejecutivo de movilidad y accidentalidad para {estado}.",
        "¿Cuál es el panorama de accidentes en {estado}?",
        "Análisis de accidentalidad en {estado}.",
        "Dame el perfil de accidentalidad del estado de {estado}.",
        "¿Qué tan alto es el nivel de accidentes en {estado}?",
        "Resumen de la situación vial en {estado}.",
        "¿Cómo ha evolucionado la accidentalidad en {estado}?",
    ],
}


# ---------------------------------------------------------------------------
# Redactores por intent — producen las 4 secciones obligatorias
# ---------------------------------------------------------------------------

def _redactar_ranking_accidentes(df: pd.DataFrame, slots: dict) -> str:
    anio = slots.get("anio")
    n = len(df)

    primer = df.iloc[0]
    e1, t1 = primer["entidad"], primer["total_accidentes"]
    segundo_txt = ""
    if n > 1:
        e2, t2 = df.iloc[1]["entidad"], df.iloc[1]["total_accidentes"]
        segundo_txt = f", seguida por {e2} con {_fmt(t2)}"

    resumen = (
        f"En {anio}, {e1} encabezó el ranking de accidentes viales "
        f"con {_fmt(t1)} incidentes registrados{segundo_txt}."
    )

    bullets = "\n".join(
        f"- {int(r['rank'])}.° {r['entidad']}: {_fmt(r['total_accidentes'])} accidentes"
        for _, r in df.iterrows()
    )

    total_top = int(df["total_accidentes"].sum())
    interpretacion = (
        f"Las {n} entidades del ranking concentran {_fmt(total_top)} accidentes en {anio}. "
        "Las zonas metropolitanas de alta densidad poblacional y tráfico vehicular tienden "
        "a acumular más incidentes. El volumen absoluto no refleja la tasa de accidentalidad "
        "por habitante ni por vehículo en circulación."
    )

    aviso_2022 = (
        "\n- A partir de 2022 se registra un cambio en la cobertura del ATUS que puede "
        "inflar las cifras; las comparaciones con años anteriores requieren cautela."
        if anio and anio >= 2022 else ""
    )
    limitaciones = (
        "- Los datos ATUS cubren zonas urbanas y suburbanas; los incidentes en carreteras "
        f"rurales y federales pueden estar subrepresentados.{aviso_2022}"
        "\n- El ranking refleja volumen absoluto, no tasas por población ni parque vehicular."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_tendencia_accidentes(df: pd.DataFrame, slots: dict) -> str:
    estado = slots.get("estado", str(df.iloc[0]["entidad"]))
    primer_anio = int(df["anio"].min())
    ultimo_anio = int(df["anio"].max())
    primer_val = int(df[df["anio"] == primer_anio]["total_accidentes"].iloc[0])
    ultimo_val = int(df[df["anio"] == ultimo_anio]["total_accidentes"].iloc[0])
    cambio_total = ((ultimo_val - primer_val) / primer_val * 100) if primer_val else 0.0

    idx_max = df["total_accidentes"].idxmax()
    anio_pico = int(df.loc[idx_max, "anio"])
    val_pico = int(df.loc[idx_max, "total_accidentes"])

    tendencia_str = (
        "al alza" if cambio_total > 5 else ("a la baja" if cambio_total < -5 else "relativamente estable")
    )
    resumen = (
        f"{estado} muestra una tendencia {tendencia_str} en accidentes viales entre {primer_anio} "
        f"y {ultimo_anio}, pasando de {_fmt(primer_val)} a {_fmt(ultimo_val)} "
        f"incidentes ({_pct(cambio_total)} en el período). El año pico fue {anio_pico} "
        f"con {_fmt(val_pico)} accidentes."
    )

    key_anios = sorted({primer_anio, anio_pico, ultimo_anio})
    bullets = "\n".join(
        f"- {int(r['anio'])}: {_fmt(r['total_accidentes'])} accidentes"
        + (f" ({_pct(r['cambio_pct'])} vs año anterior)" if not pd.isna(r["cambio_pct"]) else "")
        for _, r in df[df["anio"].isin(key_anios)].sort_values("anio").iterrows()
    )

    nota_pico = ""
    if anio_pico >= 2022:
        nota_pico = (
            f" El pico en {anio_pico} puede estar relacionado con el cambio metodológico "
            "en la cobertura del ATUS a partir de 2022."
        )
    interpretacion = (
        f"La evolución de {primer_anio} a {ultimo_anio} refleja cambios en la densidad vehicular, "
        f"infraestructura vial y condiciones de movilidad en {estado}.{nota_pico}"
    )

    limitaciones = (
        "- La serie histórica 1997-2024 incluye un salto metodológico en 2022: muchas entidades "
        "duplicaron o triplicaron sus cifras, probablemente por ampliación de la cobertura "
        "de reporte. Las comparaciones entre períodos pre y post 2022 deben interpretarse "
        "con cautela."
        "\n- Los datos ATUS corresponden a zonas urbanas y suburbanas; la cobertura rural "
        "es limitada."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_comparacion_accidentes(df: pd.DataFrame, slots: dict) -> str:
    e1 = slots.get("estado_1")
    e2 = slots.get("estado_2")

    # Columnas de estados son las que no son anio ni diferencia
    cols_estados = [c for c in df.columns if c not in ("anio", "diferencia")]
    if e1 not in cols_estados or e2 not in cols_estados:
        e1, e2 = cols_estados[0], cols_estados[1]

    primer_anio = int(df["anio"].min())
    ultimo_anio = int(df["anio"].max())
    total_e1 = int(df[e1].sum())
    total_e2 = int(df[e2].sum())
    lider = e1 if total_e1 >= total_e2 else e2
    rezagado = e2 if lider == e1 else e1
    t_lider = max(total_e1, total_e2)
    t_rezag = min(total_e1, total_e2)

    ult = df[df["anio"] == ultimo_anio].iloc[0]
    v1_ult, v2_ult = int(ult[e1]), int(ult[e2])

    resumen = (
        f"En el período {primer_anio}-{ultimo_anio}, {lider} acumuló más accidentes "
        f"({_fmt(t_lider)}) que {rezagado} ({_fmt(t_rezag)}). "
        f"En {ultimo_anio}: {e1} registró {_fmt(v1_ult)} y {e2} {_fmt(v2_ult)} accidentes."
    )

    all_bullets = [
        f"- {int(r['anio'])}: {e1} {_fmt(r[e1])} vs {e2} {_fmt(r[e2])} "
        f"(dif. {e1}: {'+' if r['diferencia'] >= 0 else ''}{_fmt(r['diferencia'])})"
        for _, r in df.sort_values("anio").iterrows()
    ]
    # Mostrar máximo 8 filas para no inflar el output
    if len(all_bullets) > 8:
        step = len(all_bullets) // 7
        sel = all_bullets[::step][:7]
        sel.append(all_bullets[-1])
    else:
        sel = all_bullets
    bullets = "\n".join(sel)

    interpretacion = (
        f"Las diferencias entre {e1} y {e2} reflejan distintos volúmenes de tráfico, "
        "densidad urbana y cobertura del ATUS. El estado con mayor número absoluto de "
        "accidentes no implica necesariamente un mayor riesgo por habitante o por "
        "kilómetro recorrido."
    )

    limitaciones = (
        "- La serie incluye un salto metodológico en 2022 que puede haber alterado la "
        "cobertura de reporte en algunas entidades, afectando la comparabilidad temporal."
        "\n- Los datos cubren zonas urbanas y suburbanas; la cobertura rural es limitada."
        "\n- No se incluye normalización por población ni parque vehicular de cada entidad."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_accidentes_por_municipio(df: pd.DataFrame, slots: dict) -> str:
    estado = slots.get("estado", str(df.iloc[0]["entidad"]))
    anio = slots.get("anio")

    primer = df.iloc[0]
    mun_1 = primer["municipio"]
    t_1 = primer["total_accidentes"]

    periodo = (
        f" en {anio}" if anio else
        (f" ({df.iloc[0]['rango_anios']})" if "rango_anios" in df.columns else "")
    )
    resumen = (
        f"{mun_1} es el municipio de {estado} con más accidentes viales registrados{periodo}, "
        f"con {_fmt(t_1)} incidentes."
    )

    bullets = "\n".join(
        f"- {int(r['rank'])}.° {r['municipio']}: {_fmt(r['total_accidentes'])} accidentes"
        for _, r in df.iterrows()
    )

    interpretacion = (
        f"La concentración de accidentes en los municipios de mayor tráfico de {estado} "
        "sugiere que las zonas urbanas y los corredores de alta circulación son los focos "
        "principales de siniestros. La inversión en infraestructura vial y señalización "
        "en estos municipios tendría mayor impacto relativo."
    )

    aviso_2022 = (
        "\n- Desde 2022, el ATUS amplió su cobertura de reporte; las cifras pueden no "
        "ser directamente comparables con años anteriores."
        if anio and anio >= 2022 else ""
    )
    limitaciones = (
        f"- Los datos corresponden a accidentes en zonas urbanas y suburbanas de {estado}; "
        f"incidentes en carreteras o zonas rurales pueden estar subrepresentados.{aviso_2022}"
        "\n- El total refleja el período disponible; no todos los años tienen la misma cobertura."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_accidentes_por_tipo(df: pd.DataFrame, slots: dict) -> str:
    estado = slots.get("estado")
    anio = slots.get("anio")

    if estado and anio:
        ctx = f" en {estado} durante {anio}"
    elif estado:
        ctx = f" en {estado}"
    elif anio:
        ctx = f" a nivel nacional en {anio}"
    else:
        ctx = " a nivel nacional"

    primer = df.iloc[0]
    tipo_1, t1, p1 = primer["tipo_accidente"], primer["total_accidentes"], primer["porcentaje"]

    resumen = (
        f"El tipo de accidente más frecuente{ctx} es «{tipo_1}» "
        f"con {_fmt(t1)} incidentes ({p1:.1f}% del total)."
    )
    if len(df) > 1:
        seg = df.iloc[1]
        resumen += f" Le sigue «{seg['tipo_accidente']}» con {_fmt(seg['total_accidentes'])} ({seg['porcentaje']:.1f}%)."

    bullets = "\n".join(
        f"- {int(r['rank'])}.° {r['tipo_accidente']}: "
        f"{_fmt(r['total_accidentes'])} ({r['porcentaje']:.1f}%)"
        for _, r in df.iterrows()
    )

    interpretacion = (
        "La distribución por tipo de accidente indica los siniestros que más afectan la vía "
        "pública. Las categorías dominantes suelen relacionarse con velocidad excesiva, "
        "distracciones al volante y condiciones de la infraestructura vial. Esta información "
        "es útil para priorizar campañas de prevención y políticas de seguridad vial."
    )

    aviso_2022 = (
        "\n- A partir de 2022, la cobertura del ATUS se amplió en varias entidades, lo que "
        "puede haber modificado la distribución por tipo de accidente."
        if anio and anio >= 2022 else ""
    )
    limitaciones = (
        f"- Los datos cubren zonas urbanas y suburbanas{ctx}; no incluye la totalidad de "
        f"siniestros en carreteras rurales o federales.{aviso_2022}"
        "\n- La clasificación TIPACCID del INEGI puede agrupar subcategorías de distinta naturaleza."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_tendencia_ventas_nacional(df: pd.DataFrame, slots: dict) -> str:
    tipo = slots.get("tipo", "total")
    label = _TIPO_LABEL.get(tipo, tipo)

    primer_anio = int(df["anio"].min())
    ultimo_anio = int(df["anio"].max())
    primer_val = int(df[df["anio"] == primer_anio]["total_ventas"].iloc[0])
    ultimo_val = int(df[df["anio"] == ultimo_anio]["total_ventas"].iloc[0])
    cambio_total = ((ultimo_val - primer_val) / primer_val * 100) if primer_val else 0.0

    idx_max = df["total_ventas"].idxmax()
    anio_max = int(df.loc[idx_max, "anio"])
    val_max = int(df.loc[idx_max, "total_ventas"])

    resumen = (
        f"Las ventas nacionales de {label} pasaron de {_fmt(primer_val)} unidades en "
        f"{primer_anio} a {_fmt(ultimo_val)} en {ultimo_anio} ({_pct(cambio_total)} en el "
        f"período). El máximo histórico fue {anio_max} con {_fmt(val_max)} unidades."
    )

    bullets = "\n".join(
        f"- {int(r['anio'])}: {_fmt(r['total_ventas'])} unidades"
        + (f" ({_pct(r['cambio_pct'])} vs año anterior)" if not pd.isna(r["cambio_pct"]) else "")
        for _, r in df.sort_values("anio").iterrows()
    )

    nota_covid = ""
    if 2020 in df["anio"].values:
        v2020 = int(df[df["anio"] == 2020]["total_ventas"].iloc[0])
        if v2020 < val_max * 0.85:
            nota_covid = (
                f" La caída de 2020 ({_fmt(v2020)} unidades) coincide con el impacto "
                "de la pandemia de COVID-19 sobre la cadena de producción y distribución automotriz."
            )
    interpretacion = (
        f"La tendencia de ventas de {label} refleja los ciclos de la economía mexicana, "
        f"la disponibilidad de crédito automotriz y los cambios en la demanda.{nota_covid}"
    )

    limitaciones = (
        "- Los datos VMRC son nacionales; no permiten desglose por entidad federativa."
        "\n- Las ventas registradas corresponden a unidades nuevas; no incluye el mercado de seminuevos."
        "\n- Los datos de 2025 y 2026 son preliminares y han sido excluidos de este análisis."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_estacionalidad_ventas_nacional(df: pd.DataFrame, slots: dict) -> str:
    anio = slots.get("anio", int(df["anio"].iloc[0]))
    tipo = slots.get("tipo", "total")
    label = _TIPO_LABEL.get(tipo, tipo)

    idx_max = df["total_ventas"].idxmax()
    idx_min = df["total_ventas"].idxmin()
    mes_max = int(df.loc[idx_max, "mes"])
    val_max = int(df.loc[idx_max, "total_ventas"])
    mes_min = int(df.loc[idx_min, "mes"])
    val_min = int(df.loc[idx_min, "total_ventas"])

    resumen = (
        f"En {anio}, el mes con más ventas de {label} fue {_MESES[mes_max]} "
        f"({_fmt(val_max)} unidades); {_MESES[mes_min]} registró el mínimo "
        f"({_fmt(val_min)} unidades)."
    )

    bullets = "\n".join(
        f"- {_MESES[int(r['mes'])].capitalize()}: {_fmt(r['total_ventas'])} unidades"
        for _, r in df.sort_values("mes").iterrows()
    )

    interpretacion = (
        f"El patrón mensual de ventas en {anio} muestra variaciones asociadas a campañas "
        "comerciales (fin de año, bono anual), temporadas de alto tráfico y la disponibilidad "
        "de inventario en distribuidoras."
    )

    limitaciones = (
        "- Los datos VMRC son nacionales; no permiten desglose por entidad federativa."
        "\n- Las ventas corresponden a unidades nuevas registradas; no incluye el mercado de seminuevos."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_tendencia_parque_nacional(df: pd.DataFrame, slots: dict) -> str:
    primer_anio = int(df["anio"].min())
    ultimo_anio = int(df["anio"].max())
    primer_val = int(df[df["anio"] == primer_anio]["total_parque_cierre"].iloc[0])
    ultimo_val = int(df[df["anio"] == ultimo_anio]["total_parque_cierre"].iloc[0])
    cambio_total = ((ultimo_val - primer_val) / primer_val * 100) if primer_val else 0.0

    resumen = (
        f"El parque vehicular nacional registrado pasó de {_fmt(primer_val)} unidades en "
        f"{primer_anio} a {_fmt(ultimo_val)} en {ultimo_anio}, un crecimiento de "
        f"{_pct(cambio_total)} en el período."
    )

    all_bullets = [
        f"- {int(r['anio'])}: {_fmt(r['total_parque_cierre'])} vehículos"
        + (f" ({_pct(r['cambio_pct'])} vs año anterior)" if not pd.isna(r["cambio_pct"]) else "")
        for _, r in df.sort_values("anio").iterrows()
    ]
    if len(all_bullets) > 15:
        step = len(all_bullets) // 10
        sel = all_bullets[::step][:10]
        sel.append(all_bullets[-1])
        bullets = "\n".join(sel)
    else:
        bullets = "\n".join(all_bullets)

    interpretacion = (
        "El crecimiento sostenido del parque vehicular refleja la motorización progresiva "
        "de la población mexicana, impulsada por el acceso al crédito automotriz y el "
        "incremento del ingreso familiar. Este aumento es un factor estructural relevante "
        "al analizar la accidentalidad vial."
    )

    limitaciones = (
        "- El parque vehicular registrado puede diferir del parque activo real; vehículos "
        "sin verificación o en rezago administrativo pueden estar incluidos."
        "\n- Los datos son nacionales; no permiten desglose por entidad federativa."
        "\n- Los datos de 2025 y 2026 son preliminares y han sido excluidos de este análisis."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_relacion_ventas_accidentes_nacional(df: pd.DataFrame, slots: dict) -> str:
    anio_inicio = slots.get("anio_inicio")
    anio_fin = slots.get("anio_fin")
    tipo = slots.get("tipo", "total")
    label = _TIPO_LABEL.get(tipo, tipo)

    corr = df["correlacion_pearson"].iloc[0]
    corr_str = f"{corr:.3f}" if not pd.isna(corr) else "N/D"

    if pd.isna(corr):
        desc_corr = "No se pudo calcular la correlación (datos insuficientes)."
    elif abs(corr) < 0.2:
        desc_corr = (
            f"La correlación de Pearson es {corr_str}: asociación prácticamente nula entre "
            f"ventas de {label} y accidentes en el período analizado."
        )
    elif abs(corr) < 0.5:
        signo = "positiva" if corr > 0 else "negativa"
        desc_corr = (
            f"La correlación de Pearson es {corr_str}: asociación {signo} moderada entre "
            f"ventas de {label} y accidentes, sin implicar causalidad."
        )
    else:
        signo = "positiva" if corr > 0 else "negativa"
        desc_corr = (
            f"La correlación de Pearson es {corr_str}: asociación {signo} considerable entre "
            f"ventas de {label} y accidentes, aunque sin implicar causalidad directa."
        )

    resumen = (
        f"Para el período {anio_inicio}-{anio_fin}, la correlación de Pearson entre ventas "
        f"nacionales de {label} y accidentes viales es {corr_str}. "
        "Esta cifra estadística no implica causalidad."
    )

    sub = df.dropna(subset=["total_ventas", "total_accidentes"])
    lines = [
        f"- {int(r['anio'])}: ventas {_fmt(r['total_ventas'])} unidades | "
        f"accidentes {_fmt(r['total_accidentes'])}"
        for _, r in sub.sort_values("anio").iterrows()
    ]
    lines.append(f"- Correlación de Pearson ({anio_inicio}-{anio_fin}): {corr_str}")
    bullets = "\n".join(lines)

    interpretacion = (
        f"{desc_corr} "
        "La relación entre ventas vehiculares y accidentes está mediada por múltiples factores: "
        "tamaño del parque vehicular, infraestructura vial, comportamiento del conductor, "
        "políticas de seguridad vial y cobertura del sistema ATUS. "
        "La correlación no implica causalidad."
    )

    limitaciones = (
        "- Los datos VMRC son nacionales; no es posible el desglose a nivel estatal."
        "\n- Los accidentes ATUS se agregan a nivel nacional para este cruce; se pierde "
        "la variabilidad regional."
        "\n- La correlación de Pearson asume relación lineal; relaciones no lineales no se capturan."
        "\n- Factores confusores (demografía, cobertura ATUS, pandemia 2020) no están controlados."
        "\n- Correlación no implica causalidad: no se puede afirmar que las ventas vehiculares "
        "causen los accidentes."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


def _redactar_resumen_estado(
    df_tend: pd.DataFrame,
    df_tipos: pd.DataFrame,
    slots: dict,
) -> str:
    estado = slots.get("estado", str(df_tend.iloc[0]["entidad"]))
    primer_anio = int(df_tend["anio"].min())
    ultimo_anio = int(df_tend["anio"].max())
    total_acum = int(df_tend["total_accidentes"].sum())
    ultimo_val = int(df_tend[df_tend["anio"] == ultimo_anio]["total_accidentes"].iloc[0])

    idx_max = df_tend["total_accidentes"].idxmax()
    anio_pico = int(df_tend.loc[idx_max, "anio"])
    val_pico = int(df_tend.loc[idx_max, "total_accidentes"])

    tipo_top = df_tipos.iloc[0]["tipo_accidente"]
    p_top = float(df_tipos.iloc[0]["porcentaje"])

    resumen = (
        f"{estado} acumuló {_fmt(total_acum)} accidentes entre {primer_anio} y {ultimo_anio}. "
        f"El año con mayor incidencia fue {anio_pico} ({_fmt(val_pico)}). "
        f"En {ultimo_anio} se registraron {_fmt(ultimo_val)} accidentes. "
        f"El tipo de accidente más frecuente es «{tipo_top}» ({p_top:.1f}% del total)."
    )

    trend_lines = [
        f"- {int(r['anio'])}: {_fmt(r['total_accidentes'])} accidentes"
        for _, r in df_tend.sort_values("anio").iterrows()
    ]
    if len(trend_lines) > 12:
        trend_lines = trend_lines[:6] + ["..."] + trend_lines[-4:]
    type_lines = [
        f"- {r['tipo_accidente']}: {_fmt(r['total_accidentes'])} ({r['porcentaje']:.1f}%)"
        for _, r in df_tipos.head(5).iterrows()
    ]
    bullets = (
        "Tendencia anual:\n" + "\n".join(trend_lines)
        + "\n\nDistribución por tipo (top 5):\n" + "\n".join(type_lines)
    )

    interpretacion = (
        f"La evolución de accidentes en {estado} refleja cambios en la densidad vehicular, "
        "cobertura de reporte y condiciones de infraestructura vial. "
        f"La concentración del {p_top:.1f}% en «{tipo_top}» sugiere un área prioritaria "
        "de intervención para política pública de seguridad vial."
    )

    limitaciones = (
        "- La serie histórica incluye un salto metodológico en 2022 (probable cambio en "
        "cobertura de reporte): las comparaciones largas deben interpretarse con cautela."
        "\n- Los datos ATUS cubren zonas urbanas y suburbanas; la cobertura rural es limitada."
        "\n- El resumen no incluye tasas por habitante ni por vehículo en circulación."
    )

    return (
        f"1. Resumen\n{resumen}\n\n"
        f"2. Datos principales\n{bullets}\n\n"
        f"3. Interpretación\n{interpretacion}\n\n"
        f"4. Limitaciones\n{limitaciones}"
    )


# ---------------------------------------------------------------------------
# Despachador público
# ---------------------------------------------------------------------------

def redactar_respuesta_ideal(
    intent: str,
    df: pd.DataFrame | dict,
    slots: dict,
) -> str:
    """Despacha al redactor correcto según el intent.

    Para 'resumen_estado', df debe ser un dict {'tendencia': df1, 'tipos': df2}.
    Para el resto, df es un DataFrame normal devuelto por analytics.py.
    """
    dispatch = {
        "ranking_accidentes": _redactar_ranking_accidentes,
        "tendencia_accidentes": _redactar_tendencia_accidentes,
        "comparacion_accidentes": _redactar_comparacion_accidentes,
        "accidentes_por_municipio": _redactar_accidentes_por_municipio,
        "accidentes_por_tipo": _redactar_accidentes_por_tipo,
        "tendencia_ventas_nacional": _redactar_tendencia_ventas_nacional,
        "estacionalidad_ventas_nacional": _redactar_estacionalidad_ventas_nacional,
        "tendencia_parque_nacional": _redactar_tendencia_parque_nacional,
        "relacion_ventas_accidentes_nacional": _redactar_relacion_ventas_accidentes_nacional,
    }
    if intent == "resumen_estado":
        if not isinstance(df, dict):
            raise TypeError("Para resumen_estado, df debe ser dict {'tendencia':..., 'tipos':...}")
        return _redactar_resumen_estado(df["tendencia"], df["tipos"], slots)

    fn = dispatch.get(intent)
    if fn is None:
        raise ValueError(f"Intent no reconocido: '{intent}'")
    return fn(df, slots)


# ---------------------------------------------------------------------------
# Generadores de corpus por intent
# ---------------------------------------------------------------------------

def _hacer_ejemplo(
    intent: str,
    pregunta: str,
    df_prompt: pd.DataFrame,
    df_output: pd.DataFrame | dict,
    slots: dict,
) -> dict:
    """Arma la tripleta {intent, input, output}."""
    prompt = construir_prompt(pregunta, intent, df_prompt, {"slots": slots})
    output = redactar_respuesta_ideal(intent, df_output, slots)
    return {"intent": intent, "input": prompt, "output": output}


def _corpus_ranking_accidentes(df_atus_anual: pd.DataFrame) -> list[dict]:
    items = []
    anios = list(range(2005, 2025))
    top_ns = [3, 5, 10]
    for anio in anios:
        for top_n in top_ns:
            try:
                df_r = ranking_accidentes(df_atus_anual, anio, top_n)
                slots = {"anio": anio, "top_n": top_n}
                tpl = _pick_template(TEMPLATES_PREGUNTA["ranking_accidentes"], slots)
                items.append(_hacer_ejemplo("ranking_accidentes", tpl.format(**slots), df_r, df_r, slots))
            except Exception:
                continue
    random.shuffle(items)
    return items[:50]


def _corpus_tendencia_accidentes(df_atus_anual: pd.DataFrame) -> list[dict]:
    items = []
    templates = TEMPLATES_PREGUNTA["tendencia_accidentes"]
    for estado in ENTIDADES_CANONICAS:
        try:
            df_r = tendencia_accidentes(df_atus_anual, estado)
            slots = {"estado": estado}
            # Dos variantes de pregunta por estado para enriquecer el léxico
            tpls_usados = random.sample(templates, min(2, len(templates)))
            for tpl in tpls_usados:
                items.append(_hacer_ejemplo("tendencia_accidentes", tpl.format(**slots), df_r, df_r, slots))
        except Exception:
            continue
    random.shuffle(items)
    return items[:50]


def _corpus_comparacion_accidentes(df_atus_anual: pd.DataFrame) -> list[dict]:
    entidades = list(ENTIDADES_CANONICAS)
    todos_pares = [(e1, e2) for i, e1 in enumerate(entidades) for e2 in entidades[i + 1:]]
    pares = random.sample(todos_pares, min(50, len(todos_pares)))
    items = []
    for e1, e2 in pares:
        try:
            df_r = comparar_accidentes_estados(df_atus_anual, e1, e2)
            slots = {"estado_1": e1, "estado_2": e2}
            tpl = _pick_template(TEMPLATES_PREGUNTA["comparacion_accidentes"], slots)
            items.append(_hacer_ejemplo("comparacion_accidentes", tpl.format(**slots), df_r, df_r, slots))
        except Exception:
            continue
    return items[:50]


def _corpus_accidentes_por_municipio(
    df_atus_detalle: pd.DataFrame, df_atus_anual: pd.DataFrame
) -> list[dict]:
    entidades = list(ENTIDADES_CANONICAS)
    anios_rec = [a for a in sorted(df_atus_anual["anio"].unique()) if a >= 2010]
    items, seen = [], set()
    intentos = 0
    while len(items) < 50 and intentos < 300:
        intentos += 1
        estado = random.choice(entidades)
        anio = random.choice(anios_rec) if random.random() < 0.5 else None
        top_n = random.choice([5, 10])
        key = (estado, anio, top_n)
        if key in seen:
            continue
        seen.add(key)
        try:
            df_r = accidentes_por_municipio(df_atus_detalle, estado, anio, top_n)
            if df_r.empty:
                continue
            slots: dict = {"estado": estado, "top_n": top_n}
            if anio is not None:
                slots["anio"] = anio
            tpl = _pick_template(TEMPLATES_PREGUNTA["accidentes_por_municipio"], slots)
            items.append(_hacer_ejemplo("accidentes_por_municipio", tpl.format(**slots), df_r, df_r, slots))
        except Exception:
            continue
    return items


def _corpus_accidentes_por_tipo(df_atus_detalle: pd.DataFrame) -> list[dict]:
    entidades = list(ENTIDADES_CANONICAS)
    anios_rec = sorted(
        a for a in df_atus_detalle["anio"].unique() if a >= 2010
    )
    variantes = ["nacional_sin_anio", "nacional_con_anio", "estatal_sin_anio", "estatal_con_anio"]
    items, seen = [], set()
    intentos = 0
    while len(items) < 50 and intentos < 300:
        intentos += 1
        variante = random.choice(variantes)
        estado = random.choice(entidades) if "estatal" in variante else None
        anio = random.choice(anios_rec) if "con_anio" in variante else None
        key = (estado, anio)
        if key in seen:
            continue
        seen.add(key)
        try:
            df_r = accidentes_por_tipo(df_atus_detalle, estado=estado, anio=anio)
            if df_r.empty:
                continue
            slots: dict = {}
            if estado:
                slots["estado"] = estado
            if anio:
                slots["anio"] = anio
            tpl = _pick_template(TEMPLATES_PREGUNTA["accidentes_por_tipo"], slots)
            items.append(_hacer_ejemplo("accidentes_por_tipo", tpl.format(**slots), df_r, df_r, slots))
        except Exception:
            continue
    return items


def _corpus_tendencia_ventas_nacional(vmrc_ventas: pd.DataFrame) -> list[dict]:
    tipos = ["total", "auto", "camion"]
    templates = TEMPLATES_PREGUNTA["tendencia_ventas_nacional"]
    items = []
    for tipo in tipos:
        slots = {"tipo": tipo}
        try:
            df_r = tendencia_ventas_nacional(vmrc_ventas, tipo)
            if df_r.empty:
                continue
            for tpl in templates:
                keys = re.findall(r"\{(\w+)\}", tpl)
                if not all(k in slots for k in keys):
                    continue
                items.append(_hacer_ejemplo(
                    "tendencia_ventas_nacional", tpl.format(**slots), df_r, df_r, slots
                ))
        except Exception:
            continue
    return items[:30]


def _corpus_estacionalidad_ventas_nacional(vmrc_ventas: pd.DataFrame) -> list[dict]:
    anios = list(range(2015, 2025))
    tipos = ["total", "auto", "camion"]
    items = []
    for anio in anios:
        for tipo in tipos:
            slots = {"anio": anio, "tipo": tipo}
            try:
                df_r = estacionalidad_ventas_nacional(vmrc_ventas, anio, tipo)
                if df_r.empty:
                    continue
                tpl = _pick_template(TEMPLATES_PREGUNTA["estacionalidad_ventas_nacional"], slots)
                items.append(_hacer_ejemplo(
                    "estacionalidad_ventas_nacional", tpl.format(**slots), df_r, df_r, slots
                ))
            except Exception:
                continue
    return items[:30]


def _corpus_tendencia_parque_nacional(vmrc_parque: pd.DataFrame) -> list[dict]:
    items = []
    try:
        df_r = tendencia_parque_vehicular_nacional(vmrc_parque)
        if df_r.empty:
            return items
        slots: dict = {}
        for tpl in TEMPLATES_PREGUNTA["tendencia_parque_nacional"]:
            if re.findall(r"\{(\w+)\}", tpl):
                continue  # saltar templates con placeholders que no tenemos
            items.append(_hacer_ejemplo(
                "tendencia_parque_nacional", tpl, df_r, df_r, slots
            ))
    except Exception:
        pass
    return items[:20]


def _corpus_relacion_ventas_accidentes_nacional(
    df_atus_anual: pd.DataFrame, vmrc_ventas: pd.DataFrame
) -> list[dict]:
    rangos = [
        (2015, 2024), (2015, 2020), (2015, 2019),
        (2016, 2024), (2017, 2024), (2018, 2024),
        (2019, 2024), (2015, 2022), (2016, 2023),
        (2017, 2023), (2015, 2018), (2016, 2019),
        (2017, 2020), (2018, 2021), (2019, 2022),
    ]
    tipos = ["total", "auto", "camion"]
    items = []
    for ai, af in rangos:
        for tipo in tipos:
            slots = {"anio_inicio": ai, "anio_fin": af, "tipo": tipo}
            try:
                df_r = relacion_ventas_accidentes_nacional(df_atus_anual, vmrc_ventas, ai, af, tipo)
                if df_r.empty:
                    continue
                tpl = _pick_template(TEMPLATES_PREGUNTA["relacion_ventas_accidentes_nacional"], slots)
                items.append(_hacer_ejemplo(
                    "relacion_ventas_accidentes_nacional", tpl.format(**slots), df_r, df_r, slots
                ))
            except Exception:
                continue
    return items[:50]


def _corpus_resumen_estado(
    df_atus_anual: pd.DataFrame, df_atus_detalle: pd.DataFrame
) -> list[dict]:
    entidades = list(ENTIDADES_CANONICAS)
    items = []

    for estado in entidades:
        try:
            df_tend = tendencia_accidentes(df_atus_anual, estado)
            df_tipos = accidentes_por_tipo(df_atus_detalle, estado)
            slots = {"estado": estado}
            tpl = _pick_template(TEMPLATES_PREGUNTA["resumen_estado"], slots)
            prompt = construir_prompt(tpl.format(**slots), "resumen_estado", df_tend, {"slots": slots})
            output = redactar_respuesta_ideal("resumen_estado", {"tendencia": df_tend, "tipos": df_tipos}, slots)
            items.append({"intent": "resumen_estado", "input": prompt, "output": output})
        except Exception:
            continue

    # Relleno hasta 50 con plantillas alternativas
    extras = 50 - len(items)
    pool = random.sample(entidades, min(extras, len(entidades)))
    for estado in pool:
        try:
            df_tend = tendencia_accidentes(df_atus_anual, estado)
            df_tipos = accidentes_por_tipo(df_atus_detalle, estado)
            slots = {"estado": estado}
            tpl = random.choice(TEMPLATES_PREGUNTA["resumen_estado"])
            prompt = construir_prompt(tpl.format(**slots), "resumen_estado", df_tend, {"slots": slots})
            output = redactar_respuesta_ideal("resumen_estado", {"tendencia": df_tend, "tipos": df_tipos}, slots)
            items.append({"intent": "resumen_estado", "input": prompt, "output": output})
        except Exception:
            continue

    return items[:50]


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------

def generar_corpus(
    df_atus_anual: pd.DataFrame,
    df_atus_detalle: pd.DataFrame,
    df_vmrc_ventas: pd.DataFrame,
    df_vmrc_parque: pd.DataFrame,
    seed: int = 42,
) -> list[dict]:
    """Genera el corpus completo con seed fija para reproducibilidad."""
    random.seed(seed)

    # Excluir preliminares 2025/2026
    vmrc_ventas = df_vmrc_ventas[df_vmrc_ventas["anio"] <= 2024].copy()
    vmrc_parque = df_vmrc_parque[df_vmrc_parque["anio"] <= 2024].copy()

    corpus: list[dict] = []
    corpus.extend(_corpus_ranking_accidentes(df_atus_anual))
    corpus.extend(_corpus_tendencia_accidentes(df_atus_anual))
    corpus.extend(_corpus_comparacion_accidentes(df_atus_anual))
    corpus.extend(_corpus_accidentes_por_municipio(df_atus_detalle, df_atus_anual))
    corpus.extend(_corpus_accidentes_por_tipo(df_atus_detalle))
    corpus.extend(_corpus_tendencia_ventas_nacional(vmrc_ventas))
    corpus.extend(_corpus_estacionalidad_ventas_nacional(vmrc_ventas))
    corpus.extend(_corpus_tendencia_parque_nacional(vmrc_parque))
    corpus.extend(_corpus_relacion_ventas_accidentes_nacional(df_atus_anual, vmrc_ventas))
    corpus.extend(_corpus_resumen_estado(df_atus_anual, df_atus_detalle))

    return corpus


# ---------------------------------------------------------------------------
# Split estratificado
# ---------------------------------------------------------------------------

def split_estratificado(
    corpus: list[dict],
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split estratificado por intent; cada intent aparece en los 3 splits."""
    random.seed(seed)
    by_intent: dict[str, list[dict]] = defaultdict(list)
    for item in corpus:
        by_intent[item["intent"]].append(item)

    train, val, test = [], [], []
    for intent_items in by_intent.values():
        random.shuffle(intent_items)
        n = len(intent_items)
        n_test = max(1, round(n * ratios[2]))
        n_val = max(1, round(n * ratios[1]))
        n_train = n - n_val - n_test
        if n_train < 1:
            n_train = 1
            n_val = max(0, (n - n_train) // 2)
            n_test = n - n_train - n_val
        train.extend(intent_items[:n_train])
        val.extend(intent_items[n_train : n_train + n_val])
        test.extend(intent_items[n_train + n_val :])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def guardar_jsonl(items: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  Guardado: {path}  ({len(items)} ejemplos)")


def guardar_test_json(items: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Guardado: {path}  ({len(items)} preguntas de prueba)")


# ---------------------------------------------------------------------------
# Punto de entrada conveniente
# ---------------------------------------------------------------------------

def generar_y_guardar_todo(seed: int = 42) -> dict[str, int]:
    """Carga los procesados, genera corpus y guarda los 3 archivos.

    Retorna dict con conteos por split.
    """
    from collections import Counter

    atus_anual = pd.read_csv(PROCESSED_DIR / "atus_anual.csv")
    atus_detalle = pd.read_csv(PROCESSED_DIR / "atus_detalle.csv")
    vmrc_ventas = pd.read_csv(PROCESSED_DIR / "vmrc_ventas_mensual.csv")
    vmrc_parque = pd.read_csv(PROCESSED_DIR / "vmrc_parque_mensual.csv")

    print("Generando corpus...")
    corpus = generar_corpus(atus_anual, atus_detalle, vmrc_ventas, vmrc_parque, seed=seed)
    print(f"Total: {len(corpus)} ejemplos\n")

    counts = Counter(item["intent"] for item in corpus)
    print("Conteo por intent:")
    for intent, n in sorted(counts.items()):
        print(f"  {intent}: {n}")

    train, val, test = split_estratificado(corpus, seed=seed)
    print(f"\nSplit → train={len(train)}  val={len(val)}  test={len(test)}")

    guardar_jsonl(train, TRAINING_DATA_DIR / "train.jsonl")
    guardar_jsonl(val, TRAINING_DATA_DIR / "validation.jsonl")
    guardar_test_json(test, TRAINING_DATA_DIR / "test_questions.json")

    return {"train": len(train), "val": len(val), "test": len(test)}


__all__ = [
    "TEMPLATES_PREGUNTA",
    "redactar_respuesta_ideal",
    "generar_corpus",
    "split_estratificado",
    "guardar_jsonl",
    "guardar_test_json",
    "generar_y_guardar_todo",
]
