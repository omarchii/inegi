"""Utilidades transversales del proyecto.

Centraliza:
- Rutas del proyecto (basadas en pathlib, no hardcodeadas).
- Normalización de nombres de entidades federativas.
- Helpers de validación.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from unidecode import unidecode

# Raíz del proyecto = carpeta padre de src/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
TRAINING_DATA_DIR: Path = PROJECT_ROOT / "training_data"

# Catálogo canónico de entidades federativas (32 estados).
# Lo usamos para normalizar variaciones que vienen en los CSV de INEGI.
ENTIDADES_CANONICAS: tuple[str, ...] = (
    "Aguascalientes",
    "Baja California",
    "Baja California Sur",
    "Campeche",
    "Chiapas",
    "Chihuahua",
    "Ciudad de México",
    "Coahuila",
    "Colima",
    "Durango",
    "Guanajuato",
    "Guerrero",
    "Hidalgo",
    "Jalisco",
    "México",
    "Michoacán",
    "Morelos",
    "Nayarit",
    "Nuevo León",
    "Oaxaca",
    "Puebla",
    "Querétaro",
    "Quintana Roo",
    "San Luis Potosí",
    "Sinaloa",
    "Sonora",
    "Tabasco",
    "Tamaulipas",
    "Tlaxcala",
    "Veracruz",
    "Yucatán",
    "Zacatecas",
)

# Aliases comunes que aparecen en datasets de INEGI.
_ALIAS_ENTIDAD: dict[str, str] = {
    "distrito federal": "Ciudad de México",
    "df": "Ciudad de México",
    "cdmx": "Ciudad de México",
    "ciudad de mexico": "Ciudad de México",
    "estado de mexico": "México",
    "edomex": "México",
    "mexico": "México",
    "coahuila de zaragoza": "Coahuila",
    "michoacan de ocampo": "Michoacán",
    "veracruz de ignacio de la llave": "Veracruz",
    "nuevo leon": "Nuevo León",
    "queretaro": "Querétaro",
    "san luis potosi": "San Luis Potosí",
    "yucatan": "Yucatán",
}


def _slug(s: str) -> str:
    """Quita acentos, baja a minúsculas y compacta espacios."""
    return " ".join(unidecode(s).lower().split())


def normalizar_entidad(nombre: str) -> str:
    """Normaliza el nombre de una entidad federativa al catálogo canónico.

    Args:
        nombre: Nombre como viene en el dataset o como lo escribió el usuario.

    Returns:
        Nombre canónico (con acentos correctos). Si no se reconoce,
        regresa el input original con strip().
    """
    if not isinstance(nombre, str):
        return str(nombre)

    bruto = nombre.strip()
    slug = _slug(bruto)

    # Match directo en aliases.
    if slug in _ALIAS_ENTIDAD:
        return _ALIAS_ENTIDAD[slug]

    # Match contra catálogo canónico (comparando slugs).
    for canonica in ENTIDADES_CANONICAS:
        if _slug(canonica) == slug:
            return canonica

    # No reconocido — devolvemos limpio para que el caller decida.
    return bruto


def validar_entidad(nombre: str) -> bool:
    """True si el nombre normaliza a una entidad del catálogo canónico."""
    return normalizar_entidad(nombre) in ENTIDADES_CANONICAS


def asegurar_directorios(dirs: Iterable[Path]) -> None:
    """Crea directorios si no existen (idempotente)."""
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
