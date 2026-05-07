"""Métricas compartidas para Etapas 3 (baseline) y 4 (fine-tune).

Mantener estas funciones aquí garantiza que las cifras que se comparan en el
reporte final se calculan exactamente igual en ambos notebooks.
"""

from __future__ import annotations

import re


_SECCIONES = [
    r'resumen',
    r'datos\s+principales',
    r'interpretaci[oó]n',
    r'limitaciones',
]

_NUM_PATRON = re.compile(r'\b\d{4,}\b')

_NO_CAUSAL = re.compile(
    r'correlaci[oó]n|asociaci[oó]n|no\s+impl[ií]ca\s+causalidad|coincidencia\s+temporal',
    re.IGNORECASE,
)


def _tiene_secciones(texto: str) -> float:
    texto_lower = texto.lower()
    encontradas = sum(1 for s in _SECCIONES if re.search(s, texto_lower))
    return encontradas / len(_SECCIONES)


def _menciona_no_causalidad(texto: str, intent: str) -> bool | None:
    if intent != 'relacion_ventas_accidentes_nacional':
        return None
    return bool(_NO_CAUSAL.search(texto))


def calcular_metricas_rouge(
    predicciones: list[str], referencias: list[str]
) -> dict:
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(
        ['rouge1', 'rouge2', 'rougeL'], use_stemmer=False
    )
    r1, r2, rl = [], [], []
    for pred, ref in zip(predicciones, referencias):
        s = scorer.score(ref, pred)
        r1.append(s['rouge1'].fmeasure)
        r2.append(s['rouge2'].fmeasure)
        rl.append(s['rougeL'].fmeasure)
    return {
        'rouge1': round(sum(r1) / len(r1), 4),
        'rouge2': round(sum(r2) / len(r2), 4),
        'rougeL': round(sum(rl) / len(rl), 4),
    }


def calcular_metricas_extra(
    predicciones: list[str], ejemplos: list[dict]
) -> dict:
    frac_secciones = [_tiene_secciones(p) for p in predicciones]
    longitudes = [len(p.split()) for p in predicciones]
    no_causal_results = [
        _menciona_no_causalidad(p, e['intent'])
        for p, e in zip(predicciones, ejemplos)
    ]
    no_causal_vals = [v for v in no_causal_results if v is not None]
    return {
        'secciones_presentes': round(sum(frac_secciones) / len(frac_secciones), 4),
        'longitud_media_palabras': round(sum(longitudes) / len(longitudes), 1),
        'no_causalidad_cuando_aplica': (
            round(sum(no_causal_vals) / len(no_causal_vals), 4)
            if no_causal_vals else None
        ),
    }
