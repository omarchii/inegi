"""Carga y limpieza de datasets INEGI (ATUS y VMRC).

ALCANCE (Camino A — solo datos disponibles)
==========================================
- ATUS: análisis por entidad, municipio, año y tipo de accidente.
- VMRC: análisis únicamente a nivel NACIONAL (los archivos descargados
  no traen desglose por entidad federativa).
- Cruce ATUS × VMRC: solo nacional.
- Año tope canónico: 2024 (para empatar con ATUS y evitar mezclar
  cifras preliminares 2025/2026).

ESQUEMAS CANÓNICOS
==================
ATUS detalle (data/processed/atus_detalle.csv):
    entidad           str   (canónico, ej. "Yucatán")
    id_entidad        str   ("01"-"32")
    municipio         str   (clave 3 dígitos como string, ej. "001")
    anio              int
    tipo_accidente    str   (categórico ATUS: TIPACCID)
    total_accidentes  int

ATUS anual (data/processed/atus_anual.csv):
    entidad           str
    anio              int
    total_accidentes  int

VMRC ventas mensual (data/processed/vmrc_ventas_mensual.csv):
    anio          int
    mes           int       (1-12)
    tipo          str       ("auto" | "camion")
    total_ventas  int
    estatus       str       ("Cifras Definitivas" | "Cifras Preliminares")
    preliminar    bool      (True si anio > AÑO_TOPE_CANONICO)

VMRC parque vehicular mensual (data/processed/vmrc_parque_mensual.csv):
    anio          int
    mes           int
    total_parque  int       (suma público + particular de auto, cam_pas, cyc_carga)
    estatus       str
    preliminar    bool
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .utils import (
    PROCESSED_DIR,
    RAW_DIR,
    asegurar_directorios,
    normalizar_entidad,
)

# -----------------------------------------------------------------------------
# Constantes y rutas
# -----------------------------------------------------------------------------
ANIO_TOPE_CANONICO: int = 2024  # análisis principal hasta este año

# Mapeo de códigos numéricos TIPACCID (usados en archivos 1997–2021) a etiquetas
# legibles equivalentes a las usadas en los archivos 2022+.
# Código 0 = "Certificado cero" (confirmado: 32 registros/año, uno por entidad).
# Códigos 1-9 derivan del diccionario oficial ATUS 1997-2024.
# Codes 10-12 (motocicleta, ciclista, otro) no aparecen como numérico en la data.
TIPACCID_MAPA: dict[str, str] = {
    "0": "Certificado cero",
    "1": "Colisión con vehículo automotor",
    "2": "Colisión con peatón (atropellamiento)",
    "3": "Colisión con animal",
    "4": "Colisión con objeto fijo",
    "5": "Volcadura",
    "6": "Caída de pasajero",
    "7": "Salida del camino",
    "8": "Incendio",
    "9": "Colisión con ferrocarril",
}

# ATUS
ATUS_DIR: Path = RAW_DIR / "conjunto_de_datos_atus_anual_csv"
ATUS_DATA_DIR: Path = ATUS_DIR / "conjunto_de_datos"
ATUS_TC_ENTIDAD: Path = ATUS_DIR / "catalogos" / "tc_entidad.csv"

# VMRC
VMRC_DIR: Path = RAW_DIR / "conjunto_de_datos_vmrc_mensual_csv"
VMRC_DATA_DIR: Path = VMRC_DIR / "conjunto_de_datos"
VMRC_VENTA_AUTO: Path = (
    VMRC_DATA_DIR / "vmrc_venta_veh_mensual_tr_cifra_2015_2026.csv"
)
VMRC_VENTA_CAMION: Path = (
    VMRC_DATA_DIR / "vmrc_venta_cam_mensual_tr_cifra_2015_2026.csv"
)
VMRC_VEHICULOS: Path = (
    VMRC_DATA_DIR / "vmrc_vehiculos_mensual_tr_cifra_1991_2026.csv"
)
VMRC_PRODUCCION: Path = (
    VMRC_DATA_DIR / "vmrc_produccion_mensual_tr_cifra_2015_2026.csv"
)

# Procesados
ATUS_DETALLE_PATH: Path = PROCESSED_DIR / "atus_detalle.csv"
ATUS_ANUAL_PATH: Path = PROCESSED_DIR / "atus_anual.csv"
VMRC_VENTAS_PATH: Path = PROCESSED_DIR / "vmrc_ventas_mensual.csv"
VMRC_PARQUE_PATH: Path = PROCESSED_DIR / "vmrc_parque_mensual.csv"


# -----------------------------------------------------------------------------
# Helpers de I/O
# -----------------------------------------------------------------------------
def _read_csv_robusto(path: Path, **kwargs) -> pd.DataFrame:
    """Lee un CSV probando encodings comunes en datasets INEGI."""
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {path}. "
            f"Verifica que esté colocado en la carpeta correcta."
        )
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {path} con encodings utf-8/latin-1/cp1252.")


def _strip_str_cols(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """Quita whitespace/tabs en columnas string. Los CSV de INEGI a veces
    traen tabs antes de los IDs ('\\t01' en ID_ENTIDAD)."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df


# -----------------------------------------------------------------------------
# ATUS
# -----------------------------------------------------------------------------
def _cargar_tc_entidad() -> dict[str, str]:
    """Devuelve dict {ID_ENTIDAD ('01'-'32'): nombre_canonico}."""
    tc = _read_csv_robusto(ATUS_TC_ENTIDAD)
    tc = _strip_str_cols(tc, ["ID_ENTIDAD", "NOM_ENTIDAD"])
    # Asegurar 2 dígitos en el ID.
    tc["ID_ENTIDAD"] = tc["ID_ENTIDAD"].str.zfill(2)
    tc["entidad_canonica"] = tc["NOM_ENTIDAD"].map(normalizar_entidad)
    return dict(zip(tc["ID_ENTIDAD"], tc["entidad_canonica"]))


def listar_archivos_atus() -> list[Path]:
    """Lista los CSV anuales de ATUS encontrados en data/raw/."""
    if not ATUS_DATA_DIR.exists():
        raise FileNotFoundError(
            f"No existe el directorio de datos ATUS: {ATUS_DATA_DIR}"
        )
    return sorted(ATUS_DATA_DIR.glob("atus_anual_*.csv"))


def _anio_desde_nombre(path: Path) -> int:
    """Extrae el año del nombre del archivo `atus_anual_<YYYY>.csv`."""
    import re

    m = re.search(r"atus_anual_(\d{4})\.csv$", path.name)
    if not m:
        raise ValueError(f"No pude extraer año del nombre: {path.name}")
    return int(m.group(1))


def load_atus_raw() -> pd.DataFrame:
    """Carga y concatena todos los CSV anuales de ATUS.

    NOTA: la columna ANIO de los CSV crudos es inconsistente entre años
    (en la mayoría de archivos viene como 1 en vez del año real). Por eso
    usamos el AÑO DEL NOMBRE DEL ARCHIVO como fuente de verdad y lo
    inyectamos como columna `ANIO`.
    """
    archivos = listar_archivos_atus()
    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron archivos atus_anual_*.csv en {ATUS_DATA_DIR}"
        )

    cols_uso = {"ID_ENTIDAD", "ID_MUNICIPIO", "TIPACCID"}
    partes: list[pd.DataFrame] = []
    for p in archivos:
        anio = _anio_desde_nombre(p)
        df = _read_csv_robusto(
            p, usecols=lambda c: c.strip().upper() in cols_uso
        )
        df.columns = [c.strip().upper() for c in df.columns]
        df = _strip_str_cols(df, ["ID_ENTIDAD", "ID_MUNICIPIO", "TIPACCID"])
        df["ANIO"] = anio
        partes.append(df)

    return pd.concat(partes, ignore_index=True)


def clean_atus(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Limpia ATUS y devuelve (detalle, anual).

    - detalle: agregado a (entidad, id_entidad, municipio, anio, tipo_accidente).
    - anual:   agregado a (entidad, anio).

    Filtra a años 1997-ANIO_TOPE_CANONICO y a IDs de entidad válidos (01-32).
    """
    requeridas = {"ID_ENTIDAD", "ID_MUNICIPIO", "ANIO", "TIPACCID"}
    faltantes = requeridas - set(df_raw.columns)
    if faltantes:
        raise KeyError(f"ATUS: columnas faltantes {faltantes}")

    df = df_raw.copy()
    df["ID_ENTIDAD"] = df["ID_ENTIDAD"].astype(str).str.strip().str.zfill(2)
    df["ID_MUNICIPIO"] = df["ID_MUNICIPIO"].astype(str).str.strip().str.zfill(3)
    df["ANIO"] = pd.to_numeric(df["ANIO"], errors="coerce").astype("Int64")
    df["TIPACCID"] = df["TIPACCID"].astype(str).str.strip()
    # Normalizar códigos numéricos (archivos 1997–2021) a etiquetas legibles.
    df["TIPACCID"] = df["TIPACCID"].replace(TIPACCID_MAPA)

    # Filtros de calidad.
    df = df.dropna(subset=["ANIO"])
    df = df[df["ANIO"].between(1997, ANIO_TOPE_CANONICO)]
    df["ANIO"] = df["ANIO"].astype(int)
    # IDs de entidad válidos (01-32).
    df = df[df["ID_ENTIDAD"].str.fullmatch(r"0[1-9]|[12]\d|3[0-2]")]

    # Mapear a entidad canónica.
    mapa = _cargar_tc_entidad()
    df["entidad"] = df["ID_ENTIDAD"].map(mapa)
    df = df.dropna(subset=["entidad"])

    # Detalle agregado.
    detalle = (
        df.groupby(
            ["entidad", "ID_ENTIDAD", "ID_MUNICIPIO", "ANIO", "TIPACCID"],
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "ID_ENTIDAD": "id_entidad",
                "ID_MUNICIPIO": "municipio",
                "ANIO": "anio",
                "TIPACCID": "tipo_accidente",
                "size": "total_accidentes",
            }
        )
    )
    detalle = detalle[
        [
            "entidad",
            "id_entidad",
            "municipio",
            "anio",
            "tipo_accidente",
            "total_accidentes",
        ]
    ]
    detalle["total_accidentes"] = detalle["total_accidentes"].astype(int)

    # Anual agregado.
    anual = (
        detalle.groupby(["entidad", "anio"], as_index=False)["total_accidentes"]
        .sum()
        .sort_values(["entidad", "anio"])
        .reset_index(drop=True)
    )

    return detalle, anual


# -----------------------------------------------------------------------------
# VMRC — ventas (autos + camiones)
# -----------------------------------------------------------------------------
def _limpiar_vmrc_base(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas comunes a todos los archivos VMRC."""
    df = df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    df = _strip_str_cols(df, ["ID_MES", "COBERTURA", "ESTATUS", "PROD_EST"])
    df["ANIO"] = pd.to_numeric(df["ANIO"], errors="coerce").astype("Int64")
    df["ID_MES"] = pd.to_numeric(df["ID_MES"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["ANIO", "ID_MES"])
    df["ANIO"] = df["ANIO"].astype(int)
    df["ID_MES"] = df["ID_MES"].astype(int)
    df = df[df["ID_MES"].between(1, 12)]
    return df


def load_vmrc_venta_auto() -> pd.DataFrame:
    """Ventas mensuales nacionales de automóviles, en formato canónico
    (anio, mes, tipo, total_ventas, estatus, preliminar)."""
    df = _read_csv_robusto(VMRC_VENTA_AUTO)
    df = _limpiar_vmrc_base(df)

    # Columnas de venta (sumamos todos los segmentos para el total nacional).
    # Nota: una columna viene como 'AUTO_DE_LUJO ' con espacio al final.
    cols_venta = [
        c
        for c in df.columns
        if c
        in {
            "AUTO_SUBCOMPACTO",
            "AUTO_COMPACTO",
            "AUTO_DE_LUJO",
            "AUTO_DEPORTIVO",
            "AUTO_IMPORTADO",
        }
    ]
    if not cols_venta:
        raise KeyError(
            f"VMRC venta_auto: no se reconocieron columnas de venta. "
            f"Columnas presentes: {list(df.columns)}"
        )
    for c in cols_venta:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["total_ventas"] = df[cols_venta].sum(axis=1).astype(int)

    out = df[["ANIO", "ID_MES", "total_ventas", "ESTATUS"]].rename(
        columns={"ANIO": "anio", "ID_MES": "mes", "ESTATUS": "estatus"}
    )
    out["tipo"] = "auto"
    out["preliminar"] = out["anio"] > ANIO_TOPE_CANONICO
    return out[["anio", "mes", "tipo", "total_ventas", "estatus", "preliminar"]]


def load_vmrc_venta_camion() -> pd.DataFrame:
    """Ventas mensuales nacionales de camiones (canonical)."""
    df = _read_csv_robusto(VMRC_VENTA_CAMION)
    df = _limpiar_vmrc_base(df)

    # Todas las columnas que sean conteos numéricos de ventas.
    no_metricas = {"PROD_EST", "COBERTURA", "ANIO", "ID_MES", "ESTATUS"}
    cols_venta = [c for c in df.columns if c not in no_metricas]
    for c in cols_venta:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["total_ventas"] = df[cols_venta].sum(axis=1).astype(int)

    out = df[["ANIO", "ID_MES", "total_ventas", "ESTATUS"]].rename(
        columns={"ANIO": "anio", "ID_MES": "mes", "ESTATUS": "estatus"}
    )
    out["tipo"] = "camion"
    out["preliminar"] = out["anio"] > ANIO_TOPE_CANONICO
    return out[["anio", "mes", "tipo", "total_ventas", "estatus", "preliminar"]]


def clean_vmrc_ventas() -> pd.DataFrame:
    """Combina ventas de autos + camiones en un solo DataFrame canónico."""
    auto = load_vmrc_venta_auto()
    cam = load_vmrc_venta_camion()
    out = pd.concat([auto, cam], ignore_index=True)
    return out.sort_values(["anio", "mes", "tipo"]).reset_index(drop=True)


# -----------------------------------------------------------------------------
# VMRC — parque vehicular
# -----------------------------------------------------------------------------
def load_vmrc_vehiculos() -> pd.DataFrame:
    """Parque vehicular nacional mensual (canonical)."""
    df = _read_csv_robusto(VMRC_VEHICULOS)
    df = _limpiar_vmrc_base(df)

    cols_parque = [
        c
        for c in df.columns
        if c
        in {
            "AUTO_PUBLICO",
            "AUTO_PARTICULAR",
            "CAM_PAS_PUBLICO",
            "CAM_PAS_PARTICULAR",
            "CYC_CARGA_PUBLICO",
            "CYC_CARGA_PARTICULAR",
        }
    ]
    for c in cols_parque:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["total_parque"] = df[cols_parque].sum(axis=1).astype(int)

    out = df[["ANIO", "ID_MES", "total_parque", "ESTATUS"]].rename(
        columns={"ANIO": "anio", "ID_MES": "mes", "ESTATUS": "estatus"}
    )
    out["preliminar"] = out["anio"] > ANIO_TOPE_CANONICO
    return out[["anio", "mes", "total_parque", "estatus", "preliminar"]].sort_values(
        ["anio", "mes"]
    ).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Persistencia + loaders de procesados
# -----------------------------------------------------------------------------
def guardar_procesado(df: pd.DataFrame, path: Path) -> None:
    asegurar_directorios([path.parent])
    df.to_csv(path, index=False, encoding="utf-8")


def construir_procesados() -> dict[str, Path]:
    """Lee todos los crudos, limpia y escribe los CSV procesados.

    Returns:
        Dict con las rutas de los archivos generados.
    """
    asegurar_directorios([PROCESSED_DIR])

    print("[ATUS] Cargando archivos crudos...")
    atus_raw = load_atus_raw()
    print(f"[ATUS] Filas crudas: {len(atus_raw):,}")

    print("[ATUS] Limpiando...")
    atus_detalle, atus_anual = clean_atus(atus_raw)
    guardar_procesado(atus_detalle, ATUS_DETALLE_PATH)
    guardar_procesado(atus_anual, ATUS_ANUAL_PATH)
    print(f"[ATUS] Detalle -> {ATUS_DETALLE_PATH} ({len(atus_detalle):,} filas)")
    print(f"[ATUS] Anual   -> {ATUS_ANUAL_PATH} ({len(atus_anual):,} filas)")

    print("[VMRC] Procesando ventas (autos + camiones)...")
    vmrc_ventas = clean_vmrc_ventas()
    guardar_procesado(vmrc_ventas, VMRC_VENTAS_PATH)
    print(f"[VMRC] Ventas -> {VMRC_VENTAS_PATH} ({len(vmrc_ventas):,} filas)")

    print("[VMRC] Procesando parque vehicular...")
    vmrc_parque = load_vmrc_vehiculos()
    guardar_procesado(vmrc_parque, VMRC_PARQUE_PATH)
    print(f"[VMRC] Parque -> {VMRC_PARQUE_PATH} ({len(vmrc_parque):,} filas)")

    return {
        "atus_detalle": ATUS_DETALLE_PATH,
        "atus_anual": ATUS_ANUAL_PATH,
        "vmrc_ventas": VMRC_VENTAS_PATH,
        "vmrc_parque": VMRC_PARQUE_PATH,
    }


# -----------------------------------------------------------------------------
# Loaders de procesados (para la app y analytics)
# -----------------------------------------------------------------------------
def load_atus_anual(path: Path | str = ATUS_ANUAL_PATH) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8")


def load_atus_detalle(path: Path | str = ATUS_DETALLE_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8", dtype={"id_entidad": str, "municipio": str})
    return df


def load_vmrc_ventas(
    path: Path | str = VMRC_VENTAS_PATH, incluir_preliminar: bool = False
) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    if not incluir_preliminar:
        df = df[~df["preliminar"]]
    return df.reset_index(drop=True)


def load_vmrc_parque(
    path: Path | str = VMRC_PARQUE_PATH, incluir_preliminar: bool = False
) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    if not incluir_preliminar:
        df = df[~df["preliminar"]]
    return df.reset_index(drop=True)
