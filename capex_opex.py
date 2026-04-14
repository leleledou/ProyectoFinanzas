# ═══════════════════════════════════════════════════════════════
# capex_opex.py — Capa adicional de interpretación CAPEX / OPEX
# No modifica la lógica existente. Solo añade criterio complementario.
# ═══════════════════════════════════════════════════════════════

import re
from typing import Dict, List, Optional


FRASES_CAPEX = [
    'dinero disponible', 'capital inicial', 'caja inicial',
    'monto con el que se inicia', 'monto con el que inicia',
    'recursos del proyecto', 'inversión realizada', 'inversion realizada',
    'inversión inicial', 'inversion inicial', 'capital disponible',
    'fondos iniciales', 'fondos disponibles', 'desembolso inicial',
]

FRASES_OPEX = [
    'gastos mensuales', 'gasto mensual', 'costos fijos', 'costo fijo',
    'egresos', 'burn rate', 'pagos recurrentes', 'pago recurrente',
    'costos operativos', 'costo operativo', 'gastos operativos',
    'gasto operativo', 'pagos mensuales', 'salidas mensuales',
]


def interpretar(texto: str) -> Optional[Dict]:
    """
    Analiza el texto buscando CAPEX y OPEX. Devuelve un dict con los
    valores detectados, las frases disparadoras y el fragmento de texto
    original que permitió la detección. Retorna None si no hay nada.

    Estructura:
        {
          'variables': [
            {'tipo': 'CAPEX', 'etiqueta': 'inversión inicial',
             'monto': 150000.0, 'frase_clave': 'capital inicial',
             'fragmento': 'cuento con un capital inicial de $150,000 para...'},
            {'tipo': 'OPEX', ...},
          ],
          'criterios': [str, ...],
        }
    """
    if not texto:
        return None

    texto_original = texto
    texto_l = texto.lower()

    capex = _buscar(texto_original, texto_l, FRASES_CAPEX)
    opex = _buscar(texto_original, texto_l, FRASES_OPEX)

    variables = []
    if capex:
        capex['tipo'] = 'CAPEX'
        capex['etiqueta'] = 'Inversión inicial'
        variables.append(capex)
    if opex:
        opex['tipo'] = 'OPEX'
        opex['etiqueta'] = 'Costos operativos'
        variables.append(opex)

    if not variables:
        return None

    info_legacy = {
        'capex': capex['monto'] if capex else None,
        'opex': opex['monto'] if opex else None,
        'frase_capex': capex['frase_clave'] if capex else None,
        'frase_opex': opex['frase_clave'] if opex else None,
    }

    return {
        'variables': variables,
        'criterios': generar_criterio(info_legacy),
    }


def _buscar(texto_original: str, texto_l: str, frases: List[str]) -> Optional[Dict]:
    """
    Busca la primera frase disparadora y devuelve
    {'frase_clave', 'fragmento', 'monto'} o None.
    """
    mejor_idx = -1
    mejor_frase = None
    for f in frases:
        idx = texto_l.find(f)
        if idx >= 0 and (mejor_idx < 0 or idx < mejor_idx):
            mejor_idx = idx
            mejor_frase = f

    if mejor_idx < 0:
        return None

    post_ini = mejor_idx + len(mejor_frase)
    post_fin = post_ini + 100
    ventana_post = texto_l[post_ini:post_fin]
    monto = _extraer_monto(ventana_post)

    if monto is None:
        pre_ini = max(0, mejor_idx - 60)
        ventana_pre = texto_l[pre_ini:mejor_idx]
        monto = _extraer_monto(ventana_pre)

    frag_ini = max(0, mejor_idx - 20)
    frag_fin = mejor_idx + len(mejor_frase) + 80
    fragmento = texto_original[frag_ini:frag_fin].strip()

    return {
        'frase_clave': mejor_frase,
        'fragmento': fragmento,
        'monto': monto,
    }


_NUM_RE = re.compile(
    r'\$?\s*(\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,](\d+))?'
    r'(?:(k|m)\b|\s+(mil|millones|millon|millón)\b)?',
    re.IGNORECASE,
)


def _extraer_monto(texto: str) -> Optional[float]:
    m = _NUM_RE.search(texto)
    if not m:
        return None
    entero_raw = m.group(1)
    decimal_raw = m.group(2)
    sufijo = (m.group(3) or m.group(4) or '').lower()

    entero = entero_raw.replace('.', '').replace(',', '')
    try:
        base = float(entero)
        if decimal_raw and len(decimal_raw) <= 2:
            base += float('0.' + decimal_raw)
    except ValueError:
        return None

    if sufijo in ('k', 'mil'):
        base *= 1_000
    elif sufijo in ('m', 'millon', 'millones', 'millón'):
        base *= 1_000_000

    return base


def generar_criterio(info: Dict) -> List[str]:
    """
    Construye líneas de criterio que explican:
      - qué representa la variable,
      - por qué es importante,
      - qué sucede si aumenta o disminuye,
      - y la relación entre CAPEX y OPEX cuando ambos existen.
    """
    lineas = []
    capex = info.get('capex')
    opex = info.get('opex')
    fc = info.get('frase_capex')
    fo = info.get('frase_opex')

    # ── CAPEX ───────────────────────────────────────────────
    if capex is not None or fc:
        monto_txt = f"${capex:,.2f}" if capex is not None else "(monto no numérico)"
        ref = f" (referida como \"{fc}\")" if fc else ""
        lineas.append("• Inversión inicial (CAPEX)")
        lineas.append(
            f"  Qué representa: el desembolso inicial{ref} de {monto_txt} "
            "necesario para poner en marcha el proyecto (activos, "
            "instalación, puesta en operación)."
        )
        lineas.append(
            "  Por qué es importante: define el capital en riesgo y el "
            "piso sobre el cual se medirá la rentabilidad y el periodo "
            "de recuperación."
        )
        lineas.append(
            "  Si aumenta: mayor riesgo asumido y mayor tiempo de "
            "recuperación, aunque puede aumentar la capacidad instalada "
            "del proyecto. Si disminuye: menor exposición, pero también "
            "podría limitar el alcance o la escala esperada."
        )

    # ── OPEX ────────────────────────────────────────────────
    if opex is not None or fo:
        monto_txt = f"${opex:,.2f}" if opex is not None else "(monto no numérico)"
        ref = f" (referidos como \"{fo}\")" if fo else ""
        lineas.append("• Costos operativos (OPEX)")
        lineas.append(
            f"  Qué representa: los egresos recurrentes{ref} de {monto_txt} "
            "necesarios para sostener la operación (nómina, servicios, "
            "alquileres, insumos)."
        )
        lineas.append(
            "  Por qué es importante: consumen flujo de caja período a "
            "período y determinan el runway y el punto de equilibrio."
        )
        lineas.append(
            "  Si aumenta: reduce el flujo de caja disponible, afectando "
            "la rentabilidad y la sostenibilidad del negocio. Si "
            "disminuye: libera caja y extiende la autonomía operativa."
        )

    # ── Relación CAPEX / OPEX ───────────────────────────────
    if capex and opex and opex > 0:
        meses = capex / opex
        ratio = opex / capex
        lineas.append("• Relación CAPEX / OPEX")
        lineas.append(
            f"  Con el CAPEX disponible se cubrirían aproximadamente "
            f"{meses:.1f} períodos de OPEX en ausencia de ingresos, "
            "lo que aproxima la autonomía operativa del proyecto."
        )
        if ratio > 0.5:
            lineas.append(
                "  El OPEX representa una fracción alta del CAPEX: un "
                "desequilibrio entre alta inversión inicial y altos costos "
                "operativos puede hacer inviable el proyecto en el corto "
                "plazo si no se generan ingresos rápidamente."
            )
        else:
            lineas.append(
                "  El OPEX es moderado frente al CAPEX, lo que da margen "
                "razonable para validar el modelo de negocio antes de "
                "requerir nuevas inyecciones de capital."
            )

    if not lineas:
        lineas.append(
            "No se detectaron elementos concretos de CAPEX u OPEX en el texto."
        )

    return lineas
