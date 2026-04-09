# ═══════════════════════════════════════════════════════════════
# sensibilidad.py — Análisis de Sensibilidad
# Varía una variable y observa el impacto en el resultado clave
# ═══════════════════════════════════════════════════════════════

from typing import Any, Dict, List, Optional
from calculo import calcular_van, calcular_tir, calcular_runway


def analizar(tipo: str, variables: Dict[str, Any],
             config: Dict) -> Optional[Dict]:
    """
    Ejecuta análisis de sensibilidad según el tipo y la configuración.

    config debe tener:
        variable: str — variable a variar
        variaciones_pct: list[float] — porcentajes de variación

    Retorna dict con resultados de sensibilidad.
    """
    var_sensible = config.get('variable', 'flujos')
    variaciones = config.get('variaciones_pct', [-30, -20, -10, 0, 10, 20, 30])

    handlers = {
        'van_tir': _sens_van_tir,
        'runway': _sens_runway,
        'interes_simple': _sens_interes,
        'interes_compuesto': _sens_interes,
        'credito': _sens_credito,
        'valor_terminal': _sens_valor_terminal,
    }

    handler = handlers.get(tipo)
    if handler is None:
        return None

    try:
        filas = handler(variables, var_sensible, variaciones)
        if not filas:
            return None
        return {
            'variable': var_sensible,
            'variaciones': filas,
            'tipo': tipo,
        }
    except Exception:
        return None


# ─── VAN / TIR ───────────────────────────────────────────────

def _sens_van_tir(variables: Dict, var_sensible: str,
                  variaciones: List[float]) -> List[Dict]:
    inv = variables.get('inversion', 0)
    flujos_base = variables.get('flujos', [])
    tasa_base = variables.get('tasa', 0.10)

    if not flujos_base:
        return []

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'flujos' or var_sensible == 'ingresos':
            flujos_mod = [f * factor for f in flujos_base]
            tasa_mod = tasa_base
        elif var_sensible == 'tasa':
            flujos_mod = flujos_base
            tasa_mod = max(tasa_base * factor, 0.001)
        elif var_sensible == 'inversion':
            flujos_mod = flujos_base
            tasa_mod = tasa_base
            inv = variables.get('inversion', 0) * factor
        elif var_sensible == 'costos':
            # Reduce los flujos (aumenta costos = reduce flujo neto)
            flujos_mod = [f * (1 - (factor - 1)) for f in flujos_base]
            tasa_mod = tasa_base
        else:
            flujos_mod = [f * factor for f in flujos_base]
            tasa_mod = tasa_base

        van = calcular_van(inv if var_sensible == 'inversion' else
                           variables.get('inversion', 0),
                           flujos_mod, tasa_mod)
        tir = calcular_tir(variables.get('inversion', 0), flujos_mod)

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'van': van,
            'tir': tir,
            'viable': van > 0,
        })

    return filas


# ─── Runway ──────────────────────────────────────────────────

def _sens_runway(variables: Dict, var_sensible: str,
                 variaciones: List[float]) -> List[Dict]:
    saldo = variables.get('saldo', 0)
    gasto = variables.get('gasto_mensual', 0)
    ingreso_base = variables.get('ingreso_mensual', 0)
    tasa_caida_base = variables.get('tasa_caida', 0)

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'tasa_caida':
            # Para tasa de caída, las variaciones son valores absolutos
            tasa = max(0, tasa_caida_base * factor)
            ingreso = ingreso_base
        elif var_sensible == 'ingresos':
            tasa = tasa_caida_base
            ingreso = ingreso_base * factor
        else:
            tasa = max(0, tasa_caida_base * factor)
            ingreso = ingreso_base

        _, _, mes_q = calcular_runway(saldo, gasto, ingreso, tasa)
        meses = mes_q if mes_q else '>120'

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'meses': mes_q,
            'meses_display': f'{mes_q} meses' if mes_q else '>120 meses (sostenible)',
            'viable': mes_q is None,
        })

    return filas


# ─── Interés ─────────────────────────────────────────────────

def _sens_interes(variables: Dict, var_sensible: str,
                  variaciones: List[float]) -> List[Dict]:
    from calculo import calcular_interes_compuesto, calcular_interes_simple

    capital = variables.get('capital', 0)
    tasa_base = variables.get('tasa', 0)
    periodos = variables.get('periodos', 0)
    caps = int(variables.get('capitalizaciones', 1))

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'tasa':
            tasa_mod = max(tasa_base * factor, 0.001)
            cap_mod = capital
        else:
            tasa_mod = tasa_base
            cap_mod = capital * factor

        if caps > 1:
            monto, interes = calcular_interes_compuesto(cap_mod, tasa_mod, periodos, caps)
        else:
            monto, interes = calcular_interes_simple(cap_mod, tasa_mod, periodos)

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'monto_final': monto,
            'interes': interes,
            'viable': True,
        })

    return filas


# ─── Crédito ─────────────────────────────────────────────────

def _sens_credito(variables: Dict, var_sensible: str,
                  variaciones: List[float]) -> List[Dict]:
    from calculo import calcular_cuota_prestamo

    monto = variables.get('monto', 0)
    tasa_anual_base = variables.get('tasa', 0)
    num_cuotas = int(variables.get('num_cuotas', 0))
    tasa_periodo = tasa_anual_base / 12 if num_cuotas > 12 else tasa_anual_base

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'tasa':
            tasa_mod = max(tasa_periodo * factor, 0.0001)
            monto_mod = monto
        else:
            tasa_mod = tasa_periodo
            monto_mod = monto * factor

        cuota = calcular_cuota_prestamo(monto_mod, tasa_mod, num_cuotas)
        total = cuota * num_cuotas

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'cuota': cuota,
            'total_pagado': total,
            'viable': True,
        })

    return filas


# ─── Valor Terminal ──────────────────────────────────────────

def _sens_valor_terminal(variables: Dict, var_sensible: str,
                          variaciones: List[float]) -> List[Dict]:
    from calculo import calcular_valor_terminal_perpetuidad

    flujo_f = variables.get('flujo_final', 0)
    g_base = variables.get('tasa_crecimiento', 0)
    r_base = variables.get('tasa', 0)

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'tasa_crecimiento':
            g_mod = max(g_base * factor, 0)
            r_mod = r_base
        elif var_sensible == 'tasa':
            g_mod = g_base
            r_mod = max(r_base * factor, g_base + 0.001)
        else:
            g_mod = g_base
            r_mod = r_base

        if r_mod > g_mod:
            vt = calcular_valor_terminal_perpetuidad(flujo_f, g_mod, r_mod)
        else:
            vt = None

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'valor_terminal': vt,
            'viable': vt is not None,
        })

    return filas
