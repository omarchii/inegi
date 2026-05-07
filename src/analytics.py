"""Funciones de análisis sobre los datasets ATUS y VMRC.

ALCANCE (Camino A — sin desglose estatal de VMRC)
=================================================
- ATUS: por entidad, municipio, año y tipo de accidente.
- VMRC: solo a nivel NACIONAL.
- Cruce ATUS × VMRC: solo nacional.

Esquemas esperados (ver data_processing.py):
    ATUS detalle: ['entidad','id_entidad','municipio','anio',
                   'tipo_accidente','total_accidentes']
    ATUS anual:   ['entidad','anio','total_accidentes']
    VMRC ventas:  ['anio','mes','tipo','total_ventas','estatus','preliminar']
    VMRC parque:  ['anio','mes','total_parque','estatus','preliminar']

Todas las funciones devuelven DataFrames.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from .utils import normalizar_entidad

TipoVehiculo = Literal["total", "auto", "camion"]

# -----------------------------------------------------------------------------
# Validadores
# -----------------------------------------------------------------------------
_COLS_ATUS_ANUAL = {"entidad", "anio", "total_accidentes"}
_COLS_ATUS_DETALLE = {
    "entidad",
    "municipio",
    "anio",
    "tipo_accidente",
    "total_accidentes",
}
_COLS_VMRC_VENTAS = {"anio", "mes", "tipo", "total_ventas"}
_COLS_VMRC_PARQUE = {"anio", "mes", "total_parque"}


def _check(df: pd.DataFrame, requeridas: set[str], nombre: str) -> None:
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise KeyError(
            f"DataFrame {nombre} no tiene columnas requeridas: {faltantes}. "
            f"Presentes: {list(df.columns)}"
        )


def _check_anio(df: pd.DataFrame, anio: int) -> None:
    if anio not in set(df["anio"].unique()):
        disp = sorted(df["anio"].unique().tolist())
        raise ValueError(f"Año {anio} no disponible. Años: {disp}")


def _check_estado(df: pd.DataFrame, estado_norm: str) -> None:
    if estado_norm not in set(df["entidad"].unique()):
        raise ValueError(
            f"Entidad '{estado_norm}' no encontrada en los datos."
        )


def _filtrar_tipo_ventas(df: pd.DataFrame, tipo: TipoVehiculo) -> pd.DataFrame:
    """Filtra el df de ventas por tipo. 'total' = auto + camion."""
    if tipo == "total":
        return df
    if tipo not in ("auto", "camion"):
        raise ValueError("tipo debe ser 'total', 'auto' o 'camion'.")
    return df[df["tipo"] == tipo]


# =============================================================================
# ATUS — funciones a nivel entidad
# =============================================================================
def ranking_accidentes(
    df_atus_anual: pd.DataFrame, anio: int, top_n: int = 5
) -> pd.DataFrame:
    """Top-N entidades con más accidentes en un año.

    Returns: ['entidad','anio','total_accidentes','rank']
    """
    _check(df_atus_anual, _COLS_ATUS_ANUAL, "ATUS anual")
    _check_anio(df_atus_anual, anio)
    if top_n <= 0:
        raise ValueError("top_n debe ser positivo.")

    sub = (
        df_atus_anual[df_atus_anual["anio"] == anio]
        .groupby("entidad", as_index=False)["total_accidentes"]
        .sum()
        .sort_values("total_accidentes", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    sub.insert(1, "anio", anio)
    sub["rank"] = range(1, len(sub) + 1)
    return sub


def tendencia_accidentes(
    df_atus_anual: pd.DataFrame, estado: str
) -> pd.DataFrame:
    """Serie anual de accidentes para una entidad.

    Returns: ['entidad','anio','total_accidentes','cambio_pct']
    """
    _check(df_atus_anual, _COLS_ATUS_ANUAL, "ATUS anual")
    e = normalizar_entidad(estado)
    _check_estado(df_atus_anual, e)

    sub = (
        df_atus_anual[df_atus_anual["entidad"] == e]
        .groupby(["entidad", "anio"], as_index=False)["total_accidentes"]
        .sum()
        .sort_values("anio")
        .reset_index(drop=True)
    )
    sub["cambio_pct"] = (sub["total_accidentes"].pct_change() * 100).round(2)
    return sub


def comparar_accidentes_estados(
    df_atus_anual: pd.DataFrame, estado_1: str, estado_2: str
) -> pd.DataFrame:
    """Compara accidentes año a año entre dos entidades.

    Returns: ['anio', '<estado_1>', '<estado_2>', 'diferencia']
    """
    _check(df_atus_anual, _COLS_ATUS_ANUAL, "ATUS anual")
    e1, e2 = normalizar_entidad(estado_1), normalizar_entidad(estado_2)
    _check_estado(df_atus_anual, e1)
    _check_estado(df_atus_anual, e2)
    if e1 == e2:
        raise ValueError("Los dos estados deben ser distintos.")

    sub = df_atus_anual[df_atus_anual["entidad"].isin([e1, e2])]
    pivot = (
        sub.groupby(["anio", "entidad"], as_index=False)["total_accidentes"]
        .sum()
        .pivot(index="anio", columns="entidad", values="total_accidentes")
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    pivot = pivot[["anio", e1, e2]]
    pivot["diferencia"] = pivot[e1] - pivot[e2]
    return pivot.sort_values("anio").reset_index(drop=True)


def accidentes_por_municipio(
    df_atus_detalle: pd.DataFrame,
    estado: str,
    anio: int | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Top municipios con más accidentes en una entidad.

    Si `anio` es None, agrega sobre todos los años disponibles.

    Returns: ['entidad','municipio','anio'(o 'rango_anios'),'total_accidentes','rank']
    """
    _check(df_atus_detalle, _COLS_ATUS_DETALLE, "ATUS detalle")
    e = normalizar_entidad(estado)
    _check_estado(df_atus_detalle, e)
    if top_n <= 0:
        raise ValueError("top_n debe ser positivo.")

    sub = df_atus_detalle[df_atus_detalle["entidad"] == e]
    if anio is not None:
        _check_anio(sub, anio)
        sub = sub[sub["anio"] == anio]
        agrupado = (
            sub.groupby(["entidad", "municipio"], as_index=False)["total_accidentes"]
            .sum()
            .sort_values("total_accidentes", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
        agrupado.insert(2, "anio", anio)
    else:
        anio_min, anio_max = int(sub["anio"].min()), int(sub["anio"].max())
        agrupado = (
            sub.groupby(["entidad", "municipio"], as_index=False)["total_accidentes"]
            .sum()
            .sort_values("total_accidentes", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
        agrupado.insert(2, "rango_anios", f"{anio_min}-{anio_max}")

    agrupado["rank"] = range(1, len(agrupado) + 1)
    return agrupado


def accidentes_por_tipo(
    df_atus_detalle: pd.DataFrame,
    estado: str | None = None,
    anio: int | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Distribución de accidentes por tipo (TIPACCID).

    Filtros opcionales por entidad y año.
    Returns: ['tipo_accidente','total_accidentes','porcentaje','rank',
              ('entidad','anio') si se filtraron]
    """
    _check(df_atus_detalle, _COLS_ATUS_DETALLE, "ATUS detalle")

    sub = df_atus_detalle
    extras: dict[str, str | int] = {}
    if estado is not None:
        e = normalizar_entidad(estado)
        _check_estado(sub, e)
        sub = sub[sub["entidad"] == e]
        extras["entidad"] = e
    if anio is not None:
        _check_anio(sub, anio)
        sub = sub[sub["anio"] == anio]
        extras["anio"] = anio

    out = (
        sub.groupby("tipo_accidente", as_index=False)["total_accidentes"]
        .sum()
        .sort_values("total_accidentes", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    total = out["total_accidentes"].sum()
    out["porcentaje"] = (out["total_accidentes"] / total * 100).round(2) if total else 0
    out["rank"] = range(1, len(out) + 1)

    # Insertar columnas de contexto (si aplica) al inicio.
    for k, v in extras.items():
        out.insert(0, k, v)
    return out


# =============================================================================
# VMRC — funciones a nivel NACIONAL
# =============================================================================
def tendencia_ventas_nacional(
    df_vmrc_ventas: pd.DataFrame, tipo: TipoVehiculo = "total"
) -> pd.DataFrame:
    """Serie anual nacional de ventas (suma de los 12 meses).

    Args:
        df_vmrc_ventas: DataFrame con esquema VMRC ventas.
        tipo: 'total' (auto+camion), 'auto' o 'camion'.

    Returns: ['anio','tipo','total_ventas','cambio_pct']
    """
    _check(df_vmrc_ventas, _COLS_VMRC_VENTAS, "VMRC ventas")
    sub = _filtrar_tipo_ventas(df_vmrc_ventas, tipo)

    out = (
        sub.groupby("anio", as_index=False)["total_ventas"]
        .sum()
        .sort_values("anio")
        .reset_index(drop=True)
    )
    out["tipo"] = tipo
    out["cambio_pct"] = (out["total_ventas"].pct_change() * 100).round(2)
    return out[["anio", "tipo", "total_ventas", "cambio_pct"]]


def estacionalidad_ventas_nacional(
    df_vmrc_ventas: pd.DataFrame, anio: int, tipo: TipoVehiculo = "total"
) -> pd.DataFrame:
    """Ventas mensuales (Ene-Dic) de un año específico, a nivel nacional.

    Returns: ['anio','mes','tipo','total_ventas']
    """
    _check(df_vmrc_ventas, _COLS_VMRC_VENTAS, "VMRC ventas")
    _check_anio(df_vmrc_ventas, anio)
    sub = _filtrar_tipo_ventas(df_vmrc_ventas, tipo)
    sub = sub[sub["anio"] == anio]

    out = (
        sub.groupby(["anio", "mes"], as_index=False)["total_ventas"]
        .sum()
        .sort_values("mes")
        .reset_index(drop=True)
    )
    out["tipo"] = tipo
    return out[["anio", "mes", "tipo", "total_ventas"]]


def tendencia_parque_vehicular_nacional(
    df_vmrc_parque: pd.DataFrame,
) -> pd.DataFrame:
    """Serie anual nacional del parque vehicular registrado en circulación.

    Returns: ['anio','total_parque_anio_max','cambio_pct']

    Nota: para parque vehicular tomamos el valor de DICIEMBRE de cada año
    (último mes disponible) como referencia del cierre anual; si diciembre
    no existe, se toma el último mes disponible.
    """
    _check(df_vmrc_parque, _COLS_VMRC_PARQUE, "VMRC parque")

    # Para cada año, tomar el mes máximo disponible (idealmente 12).
    idx = df_vmrc_parque.groupby("anio")["mes"].idxmax()
    cierre = df_vmrc_parque.loc[idx, ["anio", "mes", "total_parque"]].rename(
        columns={"total_parque": "total_parque_cierre"}
    )
    cierre = cierre.sort_values("anio").reset_index(drop=True)
    cierre["cambio_pct"] = (cierre["total_parque_cierre"].pct_change() * 100).round(2)
    return cierre


# =============================================================================
# Cruce ATUS × VMRC — solo NACIONAL
# =============================================================================
def relacion_ventas_accidentes_nacional(
    df_atus_anual: pd.DataFrame,
    df_vmrc_ventas: pd.DataFrame,
    anio_inicio: int,
    anio_fin: int,
    tipo: TipoVehiculo = "total",
) -> pd.DataFrame:
    """Relación nacional entre ventas y accidentes por año.

    NOTA: NO implica causalidad. La interpretación debe declararlo así.
    El response_generator ya incluye ese aviso en el prompt.

    Returns:
        ['anio','total_ventas','total_accidentes','correlacion_pearson']
        donde 'correlacion_pearson' se replica en todas las filas.
    """
    _check(df_atus_anual, _COLS_ATUS_ANUAL, "ATUS anual")
    _check(df_vmrc_ventas, _COLS_VMRC_VENTAS, "VMRC ventas")
    if anio_inicio > anio_fin:
        raise ValueError("anio_inicio debe ser <= anio_fin.")

    # ATUS nacional = suma de todas las entidades por año.
    atus_nac = (
        df_atus_anual[df_atus_anual["anio"].between(anio_inicio, anio_fin)]
        .groupby("anio", as_index=False)["total_accidentes"]
        .sum()
    )

    ventas = _filtrar_tipo_ventas(df_vmrc_ventas, tipo)
    ventas_nac = (
        ventas[ventas["anio"].between(anio_inicio, anio_fin)]
        .groupby("anio", as_index=False)["total_ventas"]
        .sum()
    )

    if atus_nac.empty and ventas_nac.empty:
        raise ValueError(
            f"No hay datos en {anio_inicio}-{anio_fin} ni en ATUS ni en VMRC."
        )

    merged = pd.merge(ventas_nac, atus_nac, on="anio", how="outer").sort_values(
        "anio"
    )

    sub_corr = merged.dropna(subset=["total_ventas", "total_accidentes"])
    if len(sub_corr) >= 3:
        corr = round(
            float(sub_corr["total_ventas"].corr(sub_corr["total_accidentes"])), 3
        )
    else:
        corr = float("nan")

    merged["correlacion_pearson"] = corr
    merged["tipo_vmrc"] = tipo
    return merged.reset_index(drop=True)
