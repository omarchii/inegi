"""Generación de prompts para el modelo generativo.

Este módulo NO llama a ningún modelo. Solo arma un prompt ejecutivo
listo para enviar a un LLM (FLAN-T5 baseline o Qwen2.5 fine-tuneado).

El prompt incluye:
- Reglas estrictas (responder en español, no inventar cifras, no causalidad).
- Datos en formato compacto (texto, no JSON crudo, para que cualquier
  modelo pequeño lo entienda).
- Estructura ejecutiva esperada en la salida.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

# -----------------------------------------------------------------------------
# Reglas del sistema (constantes — el modelo debe respetarlas siempre)
# -----------------------------------------------------------------------------
REGLAS_SISTEMA = """Eres un asistente analítico de datos de movilidad en México.
Reglas estrictas que debes seguir SIEMPRE:
1. Responde únicamente en español claro y profesional.
2. Usa SOLO los datos numéricos que se te proporcionan en este prompt.
   No inventes cifras, porcentajes, estados ni años.
3. Si comparas ventas de vehículos con accidentes, NO afirmes causalidad.
   Habla de correlación, asociación o coincidencia temporal, y menciona
   explícitamente que correlación no implica causalidad.
4. Si los datos son insuficientes (pocos años, valores faltantes), dilo.
5. Mantén un tono ejecutivo: claro, breve, accionable.
""".strip()

ESTRUCTURA_RESPUESTA = """Estructura tu respuesta exactamente en estas 4 secciones:
1. Resumen (1-2 frases con la conclusión principal).
2. Datos principales (los números clave en bullets).
3. Interpretación (qué sugieren los datos, sin afirmar causalidad indebida).
4. Limitaciones (qué NO se puede concluir con estos datos).
""".strip()


# -----------------------------------------------------------------------------
# Helpers de formato
# -----------------------------------------------------------------------------
def _df_a_texto(df: pd.DataFrame, max_filas: int = 40) -> str:
    """Convierte un DataFrame a texto tabular legible para el modelo.

    Trunca a max_filas para no inflar el contexto. Usa to_string()
    porque es más legible que CSV/JSON para modelos pequeños.
    """
    if df is None or df.empty:
        return "(sin datos)"
    if len(df) > max_filas:
        cabeza = df.head(max_filas).to_string(index=False)
        return f"{cabeza}\n... ({len(df) - max_filas} filas adicionales omitidas)"
    return df.to_string(index=False)


def _describir_intent(intent_name: str, slots: dict[str, Any]) -> str:
    """Texto humano que describe qué se calculó."""
    e = slots.get("estado")
    e1 = slots.get("estado_1")
    e2 = slots.get("estado_2")
    a = slots.get("anio")
    ai = slots.get("anio_inicio")
    af = slots.get("anio_fin")
    n = slots.get("top_n", 5)

    tipo = slots.get("tipo", "total")
    municipio = slots.get("municipio")

    descripciones = {
        "ranking_accidentes": f"Top-{n} entidades con más accidentes en {a}.",
        "tendencia_accidentes": f"Tendencia anual de accidentes en {e}.",
        "comparacion_accidentes": f"Comparación de accidentes entre {e1} y {e2}.",
        "accidentes_por_municipio": (
            f"Top-{n} municipios con más accidentes en {e}"
            + (f" ({a})." if a else " (todos los años disponibles).")
        ),
        "accidentes_por_tipo": (
            "Distribución de accidentes por tipo (TIPACCID)"
            + (f" en {e}" if e else "")
            + (f" para {a}." if a else " (agregado).")
        ),
        "tendencia_ventas_nacional": (
            f"Tendencia anual NACIONAL de ventas de vehículos (tipo: {tipo})."
        ),
        "estacionalidad_ventas_nacional": (
            f"Ventas mensuales NACIONALES en {a} (tipo: {tipo})."
        ),
        "tendencia_parque_nacional": (
            "Evolución anual del parque vehicular registrado en circulación "
            "(nacional, cierre anual)."
        ),
        "relacion_ventas_accidentes_nacional": (
            f"Relación temporal NACIONAL entre ventas (tipo: {tipo}) y "
            f"accidentes ({ai}-{af}). Incluye correlación de Pearson como "
            "referencia (no implica causalidad)."
        ),
        "resumen_estado": f"Resumen ejecutivo de movilidad para {e}.",
    }
    return descripciones.get(intent_name, f"Análisis ({intent_name}).")


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------
def construir_prompt(
    pregunta_usuario: str,
    intent: str,
    dataframe_resultado: pd.DataFrame,
    contexto: dict[str, Any] | None = None,
) -> str:
    """Construye el prompt para enviar al modelo generativo.

    Args:
        pregunta_usuario: la pregunta original tal cual.
        intent: nombre de la intención detectada.
        dataframe_resultado: DataFrame ya calculado por analytics.
        contexto: dict opcional con slots y metadata extra
            (estado, anio, anio_inicio, anio_fin, top_n, fuentes, etc.).

    Returns:
        Prompt como string listo para enviar al modelo.
    """
    contexto = contexto or {}
    slots = contexto.get("slots", {})

    descripcion = _describir_intent(intent, slots)
    datos_txt = _df_a_texto(dataframe_resultado)

    fuentes = contexto.get(
        "fuentes",
        "INEGI - ATUS (Accidentes de Tránsito en Zonas Urbanas y Suburbanas) "
        "y/o VMRC (Registro Administrativo de Vehículos).",
    )

    aviso_causalidad = ""
    if intent == "relacion_ventas_accidentes_nacional":
        aviso_causalidad = (
            "\nIMPORTANTE: aunque los datos pueden mostrar correlación, "
            "muchos otros factores (población, infraestructura vial, "
            "políticas públicas, parque vehicular total, cobertura de "
            "reporte de ATUS) influyen en los accidentes. Además, las "
            "ventas VMRC son a nivel NACIONAL y los accidentes ATUS se "
            "agregan a nivel nacional para este cruce — no inferir "
            "comportamiento por entidad. NO afirmes causalidad."
        )

    prompt = f"""{REGLAS_SISTEMA}

Fuente de datos: {fuentes}

Tarea: {descripcion}{aviso_causalidad}

Pregunta del usuario:
\"\"\"
{pregunta_usuario.strip()}
\"\"\"

Datos calculados (estos son los ÚNICOS números válidos):
{datos_txt}

{ESTRUCTURA_RESPUESTA}

Respuesta:"""
    return prompt


__all__ = ["construir_prompt", "REGLAS_SISTEMA", "ESTRUCTURA_RESPUESTA"]
