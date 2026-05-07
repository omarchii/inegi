"""Detección de intención por reglas (keywords + regex).

Alcance Camino A — VMRC solo a nivel nacional.

Intenciones soportadas:
    - ranking_accidentes              (ATUS, por entidad)
    - tendencia_accidentes            (ATUS, por entidad)
    - comparacion_accidentes          (ATUS, dos entidades)
    - accidentes_por_municipio        (ATUS, dentro de una entidad)
    - accidentes_por_tipo             (ATUS, distribución de TIPACCID)
    - tendencia_ventas_nacional       (VMRC, nacional)
    - estacionalidad_ventas_nacional  (VMRC, nacional, por mes)
    - tendencia_parque_nacional       (VMRC, parque vehicular nacional)
    - relacion_ventas_accidentes_nacional  (cruce nacional)
    - resumen_estado                  (resumen ejecutivo de una entidad)
    - pregunta_no_soportada
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from unidecode import unidecode

from .utils import ENTIDADES_CANONICAS, normalizar_entidad

INTENCIONES_VALIDAS = (
    "ranking_accidentes",
    "tendencia_accidentes",
    "comparacion_accidentes",
    "accidentes_por_municipio",
    "accidentes_por_tipo",
    "tendencia_ventas_nacional",
    "estacionalidad_ventas_nacional",
    "tendencia_parque_nacional",
    "relacion_ventas_accidentes_nacional",
    "resumen_estado",
    "pregunta_no_soportada",
)


@dataclass
class Intent:
    name: str
    slots: dict[str, Any] = field(default_factory=dict)
    confianza: float = 0.0
    pregunta_original: str = ""


# -----------------------------------------------------------------------------
# Léxicos
# -----------------------------------------------------------------------------
_KW_ACCIDENTES = (
    "accidente", "accidentes", "choque", "choques",
    "siniestro", "siniestros", "atus",
)
_KW_VENTAS = (
    "venta", "ventas", "vendio", "vendieron", "vendido",
    "vmrc",
)
# 'vehiculo'/'vehiculos' es genérico en español (auto+camion) -> NO va aquí.
_KW_AUTO = ("auto", "autos", "automovil", "automoviles", "carro", "carros")
_KW_CAMION = ("camion", "camiones", "camioneta", "camionetas", "tractocamion")
_KW_PARQUE = (
    "parque vehicular", "vehiculos en circulacion", "vehiculos registrados",
    "vehiculos de motor registrados", "circulacion",
)
_KW_RANKING = (
    "ranking", "top", "mas", "mayor", "mayores", "lider", "lideres",
    "primeros", "principales", "encabeza", "encabezo", "encabezaron",
    "lideran", "lideraron", "destacan", "destacaron",
)
_KW_TENDENCIA = (
    "tendencia", "evolucion", "evolucionaron", "cambio", "cambiaron",
    "cambiar", "historico", "a lo largo", "del tiempo", "serie", "anios",
    "ha cambiado", "han cambiado", "vario", "variaron", "comportamiento",
)
_KW_PICO_ANIO = (
    "que ano", "en que ano", "cual ano", "cual fue el ano",
    "ano pico", "ano con mas", "ano con mayor", "ano record",
    "peor ano", "mejor ano", "cuando hubo", "cuando fue",
    "ano mas alto", "ano mas bajo",
)
_KW_COMPARACION = (
    "compara", "comparar", "comparacion", "vs", "versus", "contra",
    "diferencia entre", "frente a",
)
_KW_RELACION = (
    "relacion", "relaciona", "correlacion", "asociacion", "vinculo",
    "tienen que ver", "hay relacion", "se relaciona", "ligados",
    "ligadas", "ligado", "ligada",
)
_KW_RESUMEN = (
    "resumen", "panorama", "movilidad", "perfil de", "como esta",
    "como va", "situacion de", "diagnostico",
)
_KW_MUNICIPIO = (
    "municipio", "municipios", "ciudad", "ciudades", "alcaldia", "alcaldias",
)
_KW_TIPO_ACC = (
    "tipo de accidente", "tipos de accidente", "tipo de choque",
    "clase de accidente", "clases de accidente", "categoria de accidente",
    "que tipo", "que tipos", "que clase",
)
_KW_ESTACIONAL = (
    "mes", "meses", "mensual", "mensuales", "estacional", "estacionalidad",
    "por mes", "por meses", "patron mensual", "trimestre", "trimestral",
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _slug(s: str) -> str:
    return unidecode(s).lower()


def _has(text: str, kws: tuple[str, ...]) -> bool:
    return any(kw in text for kw in kws)


def _extraer_anios(texto: str) -> list[int]:
    return [int(m) for m in re.findall(r"\b(19\d{2}|20\d{2})\b", texto)]


def _extraer_top_n(texto: str) -> int | None:
    m = re.search(r"\btop[\s\-]?(\d{1,2})\b", texto)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{1,2})\s+(estados|entidades|municipios)\b", texto)
    if m:
        return int(m.group(1))
    return None


def _extraer_entidades(texto_original: str) -> list[str]:
    """Detecta entidades canónicas mencionadas en el texto."""
    slug = _slug(texto_original)
    aliases_extra = {
        "cdmx": "Ciudad de México",
        "df": "Ciudad de México",
        "edomex": "México",
        "estado de mexico": "México",
        "distrito federal": "Ciudad de México",
    }
    encontradas: list[tuple[int, str]] = []
    for ent in ENTIDADES_CANONICAS:
        idx = slug.find(_slug(ent))
        if idx >= 0:
            encontradas.append((idx, ent))
    for alias, canonica in aliases_extra.items():
        idx = slug.find(alias)
        if idx >= 0:
            encontradas.append((idx, canonica))

    encontradas.sort(key=lambda x: x[0])
    vistas: set[str] = set()
    out: list[str] = []
    for _, ent in encontradas:
        if ent not in vistas:
            vistas.add(ent)
            out.append(ent)
    return out


def _detectar_tipo_vehiculo(texto: str) -> str:
    """Devuelve 'auto', 'camion' o 'total' según el texto."""
    es_camion = _has(texto, _KW_CAMION)
    # 'auto' debe estar como palabra; "automovil" basta.
    es_auto = _has(texto, _KW_AUTO)
    if es_auto and not es_camion:
        return "auto"
    if es_camion and not es_auto:
        return "camion"
    return "total"


# -----------------------------------------------------------------------------
# API
# -----------------------------------------------------------------------------
def detectar_intencion(pregunta: str) -> Intent:
    if not isinstance(pregunta, str) or not pregunta.strip():
        return Intent(name="pregunta_no_soportada")

    texto = _slug(pregunta)
    entidades = _extraer_entidades(pregunta)
    anios = _extraer_anios(texto)
    top_n = _extraer_top_n(texto)
    tipo = _detectar_tipo_vehiculo(texto)

    es_acc = _has(texto, _KW_ACCIDENTES)
    es_ven = _has(texto, _KW_VENTAS)
    es_parque = _has(texto, _KW_PARQUE)
    es_rank = _has(texto, _KW_RANKING)
    es_trend = _has(texto, _KW_TENDENCIA)
    es_pico_ano = _has(texto, _KW_PICO_ANIO)
    es_comp = _has(texto, _KW_COMPARACION) or len(entidades) >= 2
    es_rel = _has(texto, _KW_RELACION)
    es_resumen = _has(texto, _KW_RESUMEN)
    es_mun = _has(texto, _KW_MUNICIPIO)
    es_tipoacc = _has(texto, _KW_TIPO_ACC)
    es_mes = _has(texto, _KW_ESTACIONAL)

    slots: dict[str, Any] = {}
    if entidades:
        slots["estado"] = entidades[0]
    if len(entidades) >= 2:
        slots["estado_1"] = entidades[0]
        slots["estado_2"] = entidades[1]
    if anios:
        slots["anio"] = anios[0]
    if len(anios) >= 2:
        slots["anio_inicio"] = min(anios)
        slots["anio_fin"] = max(anios)
    if top_n is not None:
        slots["top_n"] = top_n
    if es_ven or es_parque or tipo != "total":
        slots["tipo"] = tipo
    # Marca cuando la pregunta menciona una entidad junto con ventas/parque,
    # porque VMRC es solo nacional y la app debe avisar que ignora la entidad.
    if entidades and (es_ven or es_parque):
        slots["entidad_ignorada_vmrc"] = entidades[0]

    # 1) Cruce nacional ATUS × VMRC.
    if (es_rel and es_ven and es_acc) or (es_ven and es_acc):
        return Intent(
            name="relacion_ventas_accidentes_nacional",
            slots=slots,
            confianza=0.9 if es_rel else 0.7,
            pregunta_original=pregunta,
        )

    # 2) Resumen ejecutivo de un estado (ATUS-céntrico).
    if es_resumen and entidades:
        return Intent(
            name="resumen_estado", slots=slots, confianza=0.85,
            pregunta_original=pregunta,
        )

    # 3) Tipos de accidente (distribución).
    if es_tipoacc and es_acc:
        return Intent(
            name="accidentes_por_tipo", slots=slots, confianza=0.85,
            pregunta_original=pregunta,
        )

    # 4) Municipios.
    if es_mun and es_acc and entidades:
        return Intent(
            name="accidentes_por_municipio", slots=slots, confianza=0.85,
            pregunta_original=pregunta,
        )

    # 5) Comparación de accidentes (ATUS).
    if es_comp and len(entidades) >= 2 and (es_acc or not es_ven):
        return Intent(
            name="comparacion_accidentes", slots=slots, confianza=0.8,
            pregunta_original=pregunta,
        )

    # 6) VMRC nacional.
    if es_ven or es_parque:
        if es_parque:
            return Intent(
                name="tendencia_parque_nacional", slots=slots, confianza=0.8,
                pregunta_original=pregunta,
            )
        # Estacionalidad: dispara si menciona "mes/mensual/estacional", aunque
        # no haya año (el dispatcher usa el más reciente disponible).
        if es_mes:
            return Intent(
                name="estacionalidad_ventas_nacional", slots=slots,
                confianza=0.85 if anios else 0.7,
                pregunta_original=pregunta,
            )
        return Intent(
            name="tendencia_ventas_nacional", slots=slots, confianza=0.8,
            pregunta_original=pregunta,
        )

    # 7) Tendencia de accidentes (ATUS).
    # Dispara también con preguntas tipo "qué año tuvo más accidentes en X":
    # entidad + accidentes + (tendencia explícita | búsqueda de pico de año).
    if (es_trend or es_pico_ano) and entidades and es_acc:
        return Intent(
            name="tendencia_accidentes", slots=slots, confianza=0.85,
            pregunta_original=pregunta,
        )

    # 8) Ranking de accidentes (ATUS).
    if (es_rank or top_n is not None) and es_acc:
        return Intent(
            name="ranking_accidentes", slots=slots, confianza=0.8,
            pregunta_original=pregunta,
        )

    # 9) Fallbacks suaves cuando solo se mencionó un dominio.
    if es_acc:
        if anios and not entidades:
            return Intent(
                name="ranking_accidentes", slots=slots, confianza=0.55,
                pregunta_original=pregunta,
            )
        if entidades:
            return Intent(
                name="tendencia_accidentes", slots=slots, confianza=0.55,
                pregunta_original=pregunta,
            )
        # Sin entidad ni año: ranking del año más reciente (lo resuelve _dispatch).
        return Intent(
            name="ranking_accidentes", slots=slots, confianza=0.5,
            pregunta_original=pregunta,
        )

    return Intent(
        name="pregunta_no_soportada", slots=slots, confianza=0.0,
        pregunta_original=pregunta,
    )


__all__ = [
    "Intent",
    "INTENCIONES_VALIDAS",
    "detectar_intencion",
    "normalizar_entidad",
]
