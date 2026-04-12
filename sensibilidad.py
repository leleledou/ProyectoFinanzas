# ═══════════════════════════════════════════════════════════════
# sensibilidad.py — Análisis de Sensibilidad
# Varía una variable y observa el impacto en el resultado clave
# Soporta variaciones porcentuales Y escenarios discretos
# ═══════════════════════════════════════════════════════════════

from typing import Any, Dict, List, Optional
from calculo import (
    calcular_van, calcular_tir, calcular_runway,
    calcular_dilucion_convertible,
    calcular_valor_terminal_perpetuidad, calcular_valor_terminal_multiplo,
    calcular_ciclo_caja,
)


def analizar(tipo: str, variables: Dict[str, Any],
             config: Dict) -> Optional[Dict]:
    """
    Ejecuta análisis de sensibilidad según el tipo y la configuración.

    config debe tener:
        variable: str — variable a variar
        variaciones_pct: list[float] | None — porcentajes de variación
        valores_discretos: list[float] | None — valores explícitos
        flujo_anio: int | None — año específico del flujo a variar

    Retorna dict con resultados de sensibilidad.
    """
    var_sensible = config.get('variable', 'flujos')
    variaciones = config.get('variaciones_pct', [-30, -20, -10, 0, 10, 20, 30])
    valores_discretos = config.get('valores_discretos')
    flujo_anio = config.get('flujo_anio')

    # Si hay valores discretos, usar el handler discreto
    if valores_discretos:
        return _analizar_discreto(tipo, variables, var_sensible,
                                   valores_discretos, flujo_anio)

    handlers = {
        'van_tir': _sens_van_tir,
        'runway': _sens_runway,
        'interes_simple': _sens_interes,
        'interes_compuesto': _sens_interes,
        'credito': _sens_credito,
        'valor_terminal': _sens_valor_terminal,
        'capital_trabajo': _sens_capital_trabajo,
        'convertible': _sens_convertible,
    }

    handler = handlers.get(tipo)
    if handler is None:
        return None

    try:
        filas = handler(variables, var_sensible, variaciones, flujo_anio)
        if not filas:
            return None
        return {
            'variable': var_sensible,
            'variaciones': filas,
            'tipo': tipo,
            'es_discreto': False,
        }
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════
# SENSIBILIDAD DISCRETA — valores explícitos, no porcentuales
# ════════════════════════════════════════════════════════════════

def _analizar_discreto(tipo: str, variables: Dict, var_sensible: str,
                        valores: List[float],
                        flujo_anio: Optional[int]) -> Optional[Dict]:
    """
    Ejecuta sensibilidad con valores discretos explícitos.
    Ejemplo: cap=[1.5M, 2M, 2.5M] o tasa=[0.12, 0.18, 0.24]
    """
    handlers = {
        'van_tir': _disc_van_tir,
        'valor_terminal': _disc_valor_terminal,
        'convertible': _disc_convertible,
        'credito': _disc_credito,
        'capital_trabajo': _disc_capital_trabajo,
        'runway': _disc_runway,
    }

    handler = handlers.get(tipo)
    if handler is None:
        return None

    try:
        filas = handler(variables, var_sensible, valores, flujo_anio)
        if not filas:
            return None
        return {
            'variable': var_sensible,
            'variaciones': filas,
            'tipo': tipo,
            'es_discreto': True,
            'valores_discretos': valores,
        }
    except Exception:
        return None


# ─── Discreto: VAN/TIR ─────────────────────────────────────

def _disc_van_tir(variables: Dict, var_sensible: str,
                   valores: List[float],
                   flujo_anio: Optional[int]) -> List[Dict]:
    inv = variables.get('inversion', 0)
    flujos_base = variables.get('flujos', [])
    tasa_presente = variables.get('tasa') is not None
    tasa_base = variables.get('tasa', 0.10)

    if not flujos_base:
        return []

    # Si no hay tasa provista y no la estamos variando, no podemos calcular VAN
    puede_van = tasa_presente or var_sensible == 'tasa'

    filas = []
    for val in valores:
        if var_sensible in ('flujos', 'ingresos') and flujo_anio:
            # Variar solo el flujo de un año específico
            flujos_mod = flujos_base[:]
            idx = flujo_anio - 1
            if 0 <= idx < len(flujos_mod):
                flujos_mod[idx] = val
            tasa_mod = tasa_base
            inv_mod = inv
        elif var_sensible in ('flujos', 'ingresos'):
            flujos_mod = [val] * len(flujos_base)
            tasa_mod = tasa_base
            inv_mod = inv
        elif var_sensible == 'tasa':
            flujos_mod = flujos_base
            tasa_mod = val
            inv_mod = inv
        elif var_sensible == 'inversion':
            flujos_mod = flujos_base
            tasa_mod = tasa_base
            inv_mod = val
        else:
            flujos_mod = flujos_base
            tasa_mod = tasa_base
            inv_mod = inv

        van = calcular_van(inv_mod, flujos_mod, tasa_mod) if puede_van else None
        tir = calcular_tir(inv_mod, flujos_mod)

        filas.append({
            'valor_discreto': val,
            'van': van,
            'tir': tir,
            'viable': van is not None and van > 0,
        })

    return filas


# ─── Discreto: Valor Terminal ───────────────────────────────

def _disc_valor_terminal(variables: Dict, var_sensible: str,
                          valores: List[float],
                          flujo_anio: Optional[int]) -> List[Dict]:
    flujo_f = variables.get('flujo_final', 0)
    g_base = variables.get('tasa_crecimiento', 0)
    r_base = variables.get('tasa', 0)

    filas = []
    for val in valores:
        if var_sensible == 'multiplo':
            vt = calcular_valor_terminal_multiplo(flujo_f, val)
            filas.append({
                'valor_discreto': val,
                'valor_terminal': vt,
                'metodo': f'{val}x',
                'viable': True,
            })
        elif var_sensible == 'tasa_crecimiento':
            g = val
            if r_base > g:
                vt = calcular_valor_terminal_perpetuidad(flujo_f, g, r_base)
            else:
                vt = None
            filas.append({
                'valor_discreto': val,
                'valor_terminal': vt,
                'viable': vt is not None,
            })
        elif var_sensible == 'tasa':
            r = val
            if r > g_base:
                vt = calcular_valor_terminal_perpetuidad(flujo_f, g_base, r)
            else:
                vt = None
            filas.append({
                'valor_discreto': val,
                'valor_terminal': vt,
                'viable': vt is not None,
            })

    return filas


# ─── Discreto: Convertible ─────────────────────────────────

def _disc_convertible(variables: Dict, var_sensible: str,
                       valores: List[float],
                       flujo_anio: Optional[int]) -> List[Dict]:
    inv = variables.get('inversion', 0)
    cap_base = variables.get('valuation_cap', 0)
    val_pre_base = variables.get('valoracion_pre', cap_base)  # default a cap
    desc_base = variables.get('descuento_pct', 0)
    desc_pct_val = desc_base * 100 if desc_base < 1 else desc_base

    filas = []
    for val in valores:
        if var_sensible == 'valuation_cap':
            res = calcular_dilucion_convertible(inv, val, val_pre_base, desc_pct_val)
            label = f'Cap ${val:,.0f}'
        elif var_sensible == 'descuento_pct':
            desc_v = val * 100 if val < 1 else val
            res = calcular_dilucion_convertible(inv, cap_base, val_pre_base, desc_v)
            label = f'Desc {desc_v:.0f}%'
        else:
            continue

        filas.append({
            'valor_discreto': val,
            'label': label,
            'dilucion_pct': res['dilucion_pct'],
            'ownership_fundador': res['ownership_fundador'],
            'valoracion_efectiva': res['valoracion_efectiva'],
            'metodo': res['metodo_conversion'],
            'viable': True,
        })

    return filas


# ─── Discreto: Crédito ─────────────────────────────────────

def _disc_credito(variables: Dict, var_sensible: str,
                   valores: List[float],
                   flujo_anio: Optional[int]) -> List[Dict]:
    from calculo import calcular_cuota_prestamo

    monto = variables.get('monto', 0)
    tasa_anual = variables.get('tasa', 0)
    num_cuotas = int(variables.get('num_cuotas', 0))
    tasa_periodo = tasa_anual / 12 if num_cuotas > 12 else tasa_anual

    filas = []
    for val in valores:
        if var_sensible == 'tasa':
            tp = val / 12 if num_cuotas > 12 else val
            cuota = calcular_cuota_prestamo(monto, tp, num_cuotas)
        elif var_sensible == 'monto':
            cuota = calcular_cuota_prestamo(val, tasa_periodo, num_cuotas)
        else:
            cuota = calcular_cuota_prestamo(monto, tasa_periodo, num_cuotas)

        total = cuota * num_cuotas

        filas.append({
            'valor_discreto': val,
            'cuota': cuota,
            'total_pagado': total,
            'viable': True,
        })

    return filas


# ─── Discreto: Capital de trabajo ───────────────────────────

def _disc_capital_trabajo(variables: Dict, var_sensible: str,
                           valores: List[float],
                           flujo_anio: Optional[int]) -> List[Dict]:
    dc = variables.get('dias_cobro', 0)
    di = variables.get('dias_inventario', 0)
    dp = variables.get('dias_pago', 0)
    cd = variables.get('costo_diario', 0)

    filas = []
    for val in valores:
        if var_sensible == 'dias_cobro':
            ciclo = calcular_ciclo_caja(val, di, dp)
        elif var_sensible == 'dias_inventario':
            ciclo = calcular_ciclo_caja(dc, val, dp)
        elif var_sensible == 'dias_pago':
            ciclo = calcular_ciclo_caja(dc, di, val)
        else:
            ciclo = calcular_ciclo_caja(dc, di, dp)

        cap = cd * max(ciclo, 0) if cd else None
        filas.append({
            'valor_discreto': val,
            'ciclo_caja': ciclo,
            'capital_necesario': cap,
            'viable': ciclo < 60,
        })

    return filas


# ─── Discreto: Runway ──────────────────────────────────────

def _disc_runway(variables: Dict, var_sensible: str,
                  valores: List[float],
                  flujo_anio: Optional[int]) -> List[Dict]:
    saldo = variables.get('saldo', 0)
    gasto = variables.get('gasto_mensual', 0)
    ingreso = variables.get('ingreso_mensual', 0)
    tasa_caida = variables.get('tasa_caida', 0)

    filas = []
    for val in valores:
        if var_sensible == 'ingreso_mensual':
            _, _, mes_q = calcular_runway(saldo, gasto, val, tasa_caida)
        elif var_sensible == 'gasto_mensual':
            _, _, mes_q = calcular_runway(saldo, val, ingreso, tasa_caida)
        elif var_sensible == 'tasa_caida':
            _, _, mes_q = calcular_runway(saldo, gasto, ingreso, val)
        else:
            _, _, mes_q = calcular_runway(saldo, gasto, ingreso, tasa_caida)

        filas.append({
            'valor_discreto': val,
            'meses': mes_q,
            'meses_display': f'{mes_q} meses' if mes_q else '>120 meses (sostenible)',
            'viable': mes_q is None,
        })

    return filas


# ════════════════════════════════════════════════════════════════
# SENSIBILIDAD PORCENTUAL — lógica original extendida
# ════════════════════════════════════════════════════════════════

# ─── VAN / TIR ───────────────────────────────────────────────

def _sens_van_tir(variables: Dict, var_sensible: str,
                  variaciones: List[float],
                  flujo_anio: Optional[int] = None) -> List[Dict]:
    inv = variables.get('inversion', 0)
    flujos_base = variables.get('flujos', [])
    tasa_presente = variables.get('tasa') is not None
    tasa_base = variables.get('tasa', 0.10)

    if not flujos_base:
        return []

    puede_van = tasa_presente or var_sensible == 'tasa'

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible in ('flujos', 'ingresos'):
            if flujo_anio and 0 < flujo_anio <= len(flujos_base):
                # Variar solo el flujo de un año específico
                flujos_mod = flujos_base[:]
                flujos_mod[flujo_anio - 1] = flujos_base[flujo_anio - 1] * factor
            else:
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
            flujos_mod = [f * (1 - (factor - 1)) for f in flujos_base]
            tasa_mod = tasa_base
        else:
            flujos_mod = [f * factor for f in flujos_base]
            tasa_mod = tasa_base

        inv_para_van = inv if var_sensible == 'inversion' else variables.get('inversion', 0)
        van = calcular_van(inv_para_van, flujos_mod, tasa_mod) if puede_van else None
        tir = calcular_tir(variables.get('inversion', 0), flujos_mod)

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'van': van,
            'tir': tir,
            'viable': van is not None and van > 0,
        })

    return filas


# ─── Runway ──────────────────────────────────────────────────

def _sens_runway(variables: Dict, var_sensible: str,
                 variaciones: List[float],
                 flujo_anio: Optional[int] = None) -> List[Dict]:
    saldo = variables.get('saldo', 0)
    gasto = variables.get('gasto_mensual', 0)
    ingreso_base = variables.get('ingreso_mensual', 0)
    tasa_caida_base = variables.get('tasa_caida', 0)

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'tasa_caida':
            tasa = max(0, tasa_caida_base * factor)
            ingreso = ingreso_base
        elif var_sensible in ('ingresos', 'ingreso_mensual'):
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
                  variaciones: List[float],
                  flujo_anio: Optional[int] = None) -> List[Dict]:
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
                  variaciones: List[float],
                  flujo_anio: Optional[int] = None) -> List[Dict]:
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
                          variaciones: List[float],
                          flujo_anio: Optional[int] = None) -> List[Dict]:
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
        elif var_sensible == 'multiplo':
            multiplo_base = variables.get('multiplo', 5)
            vt = calcular_valor_terminal_multiplo(flujo_f, multiplo_base * factor)
            filas.append({
                'variacion_pct': pct,
                'factor': factor,
                'valor_terminal': vt,
                'viable': True,
            })
            continue
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


# ─── Capital de Trabajo ─────────────────────────────────────

def _sens_capital_trabajo(variables: Dict, var_sensible: str,
                           variaciones: List[float],
                           flujo_anio: Optional[int] = None) -> List[Dict]:
    dc = variables.get('dias_cobro', 0)
    di = variables.get('dias_inventario', 0)
    dp = variables.get('dias_pago', 0)
    cd = variables.get('costo_diario', 0)

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'dias_cobro':
            ciclo = calcular_ciclo_caja(dc * factor, di, dp)
        elif var_sensible == 'dias_inventario':
            ciclo = calcular_ciclo_caja(dc, di * factor, dp)
        elif var_sensible == 'dias_pago':
            ciclo = calcular_ciclo_caja(dc, di, dp * factor)
        else:
            ciclo = calcular_ciclo_caja(dc * factor, di, dp)

        cap = cd * max(ciclo, 0) if cd else None

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'ciclo_caja': ciclo,
            'capital_necesario': cap,
            'viable': ciclo < 60,
        })

    return filas


# ─── Convertible ────────────────────────────────────────────

def _sens_convertible(variables: Dict, var_sensible: str,
                       variaciones: List[float],
                       flujo_anio: Optional[int] = None) -> List[Dict]:
    inv = variables.get('inversion', 0)
    cap = variables.get('valuation_cap', 0)
    val_pre = variables.get('valoracion_pre', 0)
    desc = variables.get('descuento_pct', 0)
    desc_pct_val = desc * 100 if desc < 1 else desc

    filas = []
    for pct in variaciones:
        factor = 1 + pct / 100

        if var_sensible == 'descuento_pct':
            desc_mod = max(desc_pct_val * factor, 0)
            cap_mod = cap
        elif var_sensible == 'valuation_cap':
            desc_mod = desc_pct_val
            cap_mod = cap * factor
        else:
            desc_mod = desc_pct_val
            cap_mod = cap

        res = calcular_dilucion_convertible(inv, cap_mod, val_pre, desc_mod)

        filas.append({
            'variacion_pct': pct,
            'factor': factor,
            'dilucion_pct': res['dilucion_pct'],
            'ownership_fundador': res['ownership_fundador'],
            'valoracion_efectiva': res['valoracion_efectiva'],
            'metodo': res['metodo_conversion'],
            'viable': True,
        })

    return filas
