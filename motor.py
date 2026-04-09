# ═══════════════════════════════════════════════════════════════
# motor.py — Orquestador de Cálculos Financieros
# Llama a calculo.py según el tipo y las variables disponibles
# ═══════════════════════════════════════════════════════════════

from typing import Any, Dict, List, Optional
from calculo import (
    calcular_van, calcular_tir, calcular_periodo_recuperacion,
    calcular_indice_rentabilidad, calcular_interes_simple,
    calcular_interes_compuesto, calcular_runway,
    calcular_ciclo_caja, calcular_capital_trabajo_necesario,
    calcular_cuota_prestamo, generar_tabla_amortizacion,
    calcular_dilucion_convertible,
    calcular_valor_terminal_perpetuidad, calcular_valor_terminal_multiplo,
)


def calcular(tipo: str, variables: Dict[str, Any],
             calculos_posibles: List[str]) -> Dict[str, Any]:
    """
    Ejecuta los cálculos posibles para el tipo de análisis dado.
    Retorna dict con los resultados.
    """
    handlers = {
        'van_tir': _calcular_van_tir,
        'interes_simple': _calcular_interes_simple,
        'interes_compuesto': _calcular_interes_compuesto,
        'runway': _calcular_runway,
        'capital_trabajo': _calcular_capital_trabajo,
        'credito': _calcular_credito,
        'convertible': _calcular_convertible,
        'valor_terminal': _calcular_valor_terminal,
    }
    handler = handlers.get(tipo)
    if handler is None:
        return {'error': f'Tipo de análisis no soportado: {tipo}'}

    try:
        return handler(variables, calculos_posibles)
    except Exception as e:
        return {'error': str(e), 'tipo': tipo}


# ─── VAN / TIR ───────────────────────────────────────────────

def _calcular_van_tir(v: Dict, posibles: List[str]) -> Dict:
    res = {}
    inv = v.get('inversion', 0)
    flujos = v.get('flujos', [])
    tasa = v.get('tasa', 0)

    if 'van' in posibles:
        res['van'] = calcular_van(inv, flujos, tasa)
        res['tasa'] = tasa

    if 'tir' in posibles:
        res['tir'] = calcular_tir(inv, flujos)

    if 'payback' in posibles:
        res['payback'] = calcular_periodo_recuperacion(inv, flujos)

    if 'indice_rentabilidad' in posibles and 'van' in res:
        res['indice_rentabilidad'] = calcular_indice_rentabilidad(inv, res['van'])

    res['inversion'] = inv
    res['flujos'] = flujos
    res['periodos'] = len(flujos)
    return res


# ─── Interés Simple ──────────────────────────────────────────

def _calcular_interes_simple(v: Dict, posibles: List[str]) -> Dict:
    capital = v.get('capital', 0)
    tasa = v.get('tasa', 0)
    periodos = v.get('periodos', 0)

    monto, interes = calcular_interes_simple(capital, tasa, periodos)
    return {
        'capital': capital,
        'tasa': tasa,
        'periodos': periodos,
        'monto_final': monto,
        'interes_total': interes,
        'tasa_efectiva_total': interes / capital if capital else 0,
    }


# ─── Interés Compuesto ───────────────────────────────────────

def _calcular_interes_compuesto(v: Dict, posibles: List[str]) -> Dict:
    capital = v.get('capital', 0)
    tasa = v.get('tasa', 0)
    periodos = v.get('periodos', 0)
    caps = int(v.get('capitalizaciones', 1))

    monto, interes = calcular_interes_compuesto(capital, tasa, periodos, caps)

    # Comparar con simple para mostrar diferencia
    monto_s, interes_s = calcular_interes_simple(capital, tasa, periodos)

    return {
        'capital': capital,
        'tasa': tasa,
        'periodos': periodos,
        'capitalizaciones': caps,
        'monto_final': monto,
        'interes_total': interes,
        'tasa_efectiva_total': interes / capital if capital else 0,
        'diferencia_vs_simple': interes - interes_s,
        'monto_simple_ref': monto_s,
    }


# ─── Runway ──────────────────────────────────────────────────

def _calcular_runway(v: Dict, posibles: List[str]) -> Dict:
    saldo = v.get('saldo', 0)
    gasto = v.get('gasto_mensual', 0)
    ingreso = v.get('ingreso_mensual', 0)
    tasa_caida = v.get('tasa_caida', 0)

    saldos, ingresos, mes_q = calcular_runway(saldo, gasto, ingreso, tasa_caida)

    return {
        'saldo': saldo,
        'gasto_mensual': gasto,
        'ingreso_mensual': ingreso,
        'tasa_caida': tasa_caida,
        'mes_quiebre': mes_q,
        'saldos': saldos,
        'ingresos': ingresos,
        'flujo_neto_mensual': ingreso - gasto,
    }


# ─── Capital de Trabajo ──────────────────────────────────────

def _calcular_capital_trabajo(v: Dict, posibles: List[str]) -> Dict:
    dc = v.get('dias_cobro', 0)
    di = v.get('dias_inventario', 0)
    dp = v.get('dias_pago', 0)
    cd = v.get('costo_diario', 0)

    ciclo = calcular_ciclo_caja(dc, di, dp)
    cap_necesario = calcular_capital_trabajo_necesario(cd, ciclo) if cd else None

    return {
        'dias_cobro': dc,
        'dias_inventario': di,
        'dias_pago': dp,
        'costo_diario': cd,
        'ciclo_caja': ciclo,
        'capital_necesario': cap_necesario,
    }


# ─── Crédito ─────────────────────────────────────────────────

def _calcular_credito(v: Dict, posibles: List[str]) -> Dict:
    monto = v.get('monto', 0)
    tasa_anual = v.get('tasa', 0)
    num_cuotas = int(v.get('num_cuotas', 0))

    # Determinar si la tasa es mensual o anual
    # Si num_cuotas > 12, asumimos cuotas mensuales → tasa mensual
    if num_cuotas > 12:
        tasa_periodo = tasa_anual / 12
        periodo_label = 'mensual'
    else:
        tasa_periodo = tasa_anual
        periodo_label = 'por período'

    cuota = calcular_cuota_prestamo(monto, tasa_periodo, num_cuotas)
    tabla, total_int = generar_tabla_amortizacion(monto, tasa_periodo, num_cuotas)

    return {
        'monto': monto,
        'tasa_anual': tasa_anual,
        'tasa_periodo': tasa_periodo,
        'periodo_label': periodo_label,
        'num_cuotas': num_cuotas,
        'cuota': cuota,
        'total_intereses': total_int,
        'total_pagado': cuota * num_cuotas,
        'tabla_amortizacion': tabla,
    }


# ─── Nota Convertible ────────────────────────────────────────

def _calcular_convertible(v: Dict, posibles: List[str]) -> Dict:
    inv = v.get('inversion', 0)
    cap = v.get('valuation_cap', 0)
    val_pre = v.get('valoracion_pre', 0)
    desc_pct = v.get('descuento_pct', 0)

    # descuento_pct ya viene como fracción (ej: 0.20)
    desc_pct_val = desc_pct * 100 if desc_pct < 1 else desc_pct

    resultado = calcular_dilucion_convertible(inv, cap, val_pre, desc_pct_val)
    resultado.update({
        'inversion': inv,
        'valuation_cap': cap,
        'valoracion_pre': val_pre,
        'descuento_pct': desc_pct_val,
    })
    return resultado


# ─── Valor Terminal ──────────────────────────────────────────

def _calcular_valor_terminal(v: Dict, posibles: List[str]) -> Dict:
    flujo_f = v.get('flujo_final', 0)
    g = v.get('tasa_crecimiento', 0)
    r = v.get('tasa', 0)
    multiplo = v.get('multiplo')

    res = {
        'flujo_final': flujo_f,
        'tasa_crecimiento': g,
        'tasa_descuento': r,
    }

    if 'vt_perpetuidad' in posibles:
        if r > g:
            res['vt_perpetuidad'] = calcular_valor_terminal_perpetuidad(flujo_f, g, r)
        else:
            res['vt_perpetuidad'] = None
            res['error_perpetuidad'] = 'La tasa de descuento debe ser mayor que la tasa de crecimiento'

    if 'vt_multiplo' in posibles and multiplo:
        res['vt_multiplo'] = calcular_valor_terminal_multiplo(flujo_f, multiplo)
        res['multiplo'] = multiplo

    return res
