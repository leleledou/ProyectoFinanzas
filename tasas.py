# ═══════════════════════════════════════════════════════════════
# tasas.py — Análisis y Conversión de Tasas de Interés
# Detecta tasas en texto libre, convierte nominal→efectiva,
# recomienda la más conveniente según contexto
# ═══════════════════════════════════════════════════════════════

import re
from typing import Any, Dict, List, Optional


# ─── Mapeo de capitalización ───────────────────────────────────

CAPITALIZACIONES = {
    'mensual': 12,
    'bimestral': 6,
    'trimestral': 4,
    'cuatrimestral': 3,
    'semestral': 2,
    'anual': 1,
}


def analizar_tasas(texto: str) -> Optional[Dict[str, Any]]:
    """
    Analiza texto libre buscando tasas de interés.
    Retorna dict con tasas detectadas, conversiones y recomendación,
    o None si no se detectan tasas relevantes para este análisis.
    """
    texto_l = texto.lower()
    tasas = _extraer_tasas(texto_l)
    if not tasas:
        return None

    contexto = _detectar_contexto(texto_l)

    # Convertir nominales a efectivas
    for t in tasas:
        if t['tipo_tasa'] == 'nominal' and t['capitalizacion_n'] > 1:
            t['tasa_efectiva'] = _nominal_a_efectiva(
                t['valor'], t['capitalizacion_n'])
        else:
            t['tasa_efectiva'] = t['valor']

    # Recomendación
    recomendacion = _recomendar(tasas, contexto)

    return {
        'tasas': tasas,
        'contexto': contexto,
        'recomendacion': recomendacion,
    }


def _extraer_tasas(texto_l: str) -> List[Dict[str, Any]]:
    """Extrae todas las tasas porcentuales del texto con su tipo y capitalización."""
    # Patrón: captura valor%, contexto alrededor
    patron = re.compile(
        r'(?:(?:tasa|interés|interes|rendimiento|costo)\s+)?'
        r'(?:(?:nominal|efectiva?)\s+)?'
        r'(?:(?:anual|mensual|semestral|trimestral|bimestral)\s+)?'
        r'(?:del?\s+)?'
        r'(\d+(?:[.,]\d+)?)\s*%'
    )

    tasas = []
    for m in patron.finditer(texto_l):
        valor_str = m.group(1).replace(',', '.')
        valor = float(valor_str) / 100  # convertir a decimal

        inicio = max(0, m.start() - 40)
        ctx_antes = texto_l[inicio:m.start()]
        ctx_despues = texto_l[m.end():min(len(texto_l), m.end() + 40)]
        ctx_completo = ctx_antes + ' ' + m.group(0) + ' ' + ctx_despues

        # Para tipo, usar contexto corto (evita contaminación de otra tasa)
        ctx_tipo = ctx_antes[-30:] + ' ' + m.group(0) + ' ' + ctx_despues[:20]
        tipo_tasa = _detectar_tipo_tasa(ctx_tipo)
        # Para capitalización, usar solo contexto posterior (evita bleed de otra tasa)
        ctx_cap = m.group(0) + ' ' + ctx_despues
        capitalizacion_n, capitalizacion_nombre = _detectar_capitalizacion(ctx_cap)

        # Si es nominal sin capitalización explícita, no se puede convertir bien
        # Asumir capitalización mensual por defecto para nominales
        if tipo_tasa == 'nominal' and capitalizacion_n == 1:
            capitalizacion_n = 12
            capitalizacion_nombre = 'mensual'

        tasas.append({
            'valor': valor,
            'valor_pct': float(valor_str),
            'tipo_tasa': tipo_tasa,
            'capitalizacion_n': capitalizacion_n,
            'capitalizacion_nombre': capitalizacion_nombre,
            'tasa_efectiva': None,  # se calcula después
            'texto_original': m.group(0).strip(),
        })

    return tasas


def _detectar_tipo_tasa(ctx: str) -> str:
    """Determina si la tasa es nominal o efectiva según proximidad al %."""
    # Buscar la posición más cercana al número (más a la derecha antes del %)
    pos_nominal = -1
    for p in [r'nominal', r'tna\b', r'tasa\s+nominal']:
        for m in re.finditer(p, ctx):
            pos_nominal = max(pos_nominal, m.start())

    pos_efectiva = -1
    for p in [r'efectiva?', r'tea\b', r'tasa\s+efectiva']:
        for m in re.finditer(p, ctx):
            pos_efectiva = max(pos_efectiva, m.start())

    if pos_nominal < 0 and pos_efectiva < 0:
        return 'efectiva'  # default
    if pos_nominal >= 0 and pos_efectiva >= 0:
        # Usar la más cercana al número (mayor posición = más cerca)
        return 'nominal' if pos_nominal > pos_efectiva else 'efectiva'
    return 'nominal' if pos_nominal >= 0 else 'efectiva'


def _detectar_capitalizacion(ctx: str) -> tuple:
    """Detecta la frecuencia de capitalización en el contexto."""
    for nombre, n in CAPITALIZACIONES.items():
        if nombre in ctx:
            return n, nombre
    # Buscar también "capitaliza N veces"
    m = re.search(r'capitaliza\w*\s+(\d+)\s+veces', ctx)
    if m:
        n = int(m.group(1))
        # Buscar nombre inverso
        for nombre, val in CAPITALIZACIONES.items():
            if val == n:
                return n, nombre
        return n, f'{n} veces/año'
    return 1, 'anual'


def _detectar_contexto(texto_l: str) -> str:
    """Detecta si el contexto es de inversión o financiamiento."""
    kw_inversion = [
        'inversión', 'inversion', 'invertir', 'invierto', 'rendimiento',
        'ahorro', 'deposito', 'depósito', 'plazo fijo', 'cdt',
        'fondo', 'ganancia', 'rentabilidad',
    ]
    kw_financiamiento = [
        'préstamo', 'prestamo', 'crédito', 'credito', 'financiamiento',
        'deuda', 'cuota', 'pagar', 'hipoteca', 'amortización', 'amortizacion',
    ]

    score_inv = sum(1 for kw in kw_inversion if kw in texto_l)
    score_fin = sum(1 for kw in kw_financiamiento if kw in texto_l)

    if score_fin > score_inv:
        return 'financiamiento'
    if score_inv > score_fin:
        return 'inversion'
    return 'general'


def _nominal_a_efectiva(tasa_nominal: float, capitalizaciones: int) -> float:
    """Convierte tasa nominal anual a tasa efectiva anual."""
    return (1 + tasa_nominal / capitalizaciones) ** capitalizaciones - 1


def _recomendar(tasas: List[Dict], contexto: str) -> Optional[Dict[str, Any]]:
    """Recomienda la tasa más conveniente según el contexto."""
    if len(tasas) < 2:
        return None

    efectivas = [(i, t['tasa_efectiva']) for i, t in enumerate(tasas)]

    if contexto == 'inversion':
        mejor_idx, mejor_val = max(efectivas, key=lambda x: x[1])
        criterio = 'mayor tasa efectiva (inversión)'
    elif contexto == 'financiamiento':
        mejor_idx, mejor_val = min(efectivas, key=lambda x: x[1])
        criterio = 'menor tasa efectiva (financiamiento)'
    else:
        # General: mostrar ambas opciones
        max_idx, max_val = max(efectivas, key=lambda x: x[1])
        min_idx, min_val = min(efectivas, key=lambda x: x[1])
        return {
            'mejor_inversion': tasas[max_idx]['texto_original'],
            'mejor_financiamiento': tasas[min_idx]['texto_original'],
            'criterio': 'depende del contexto',
            'mejor_idx': None,
        }

    return {
        'mejor_idx': mejor_idx,
        'mejor_tasa': tasas[mejor_idx]['texto_original'],
        'tasa_efectiva': mejor_val,
        'criterio': criterio,
    }
