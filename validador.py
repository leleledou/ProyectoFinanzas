# ═══════════════════════════════════════════════════════════════
# validador.py — Validación de Variables Extraídas
# Determina qué datos hay, qué faltan y qué se puede calcular
# ═══════════════════════════════════════════════════════════════

from typing import Any, Dict, List, Tuple

# ─── Variables requeridas por tipo de análisis ───────────────
REQUERIDAS = {
    'van_tir': {
        'obligatorias': ['inversion', 'flujos', 'tasa'],
        'opcionales': ['periodos'],
        'calculos': {
            'van': ['inversion', 'flujos', 'tasa'],
            'tir': ['inversion', 'flujos'],
            'payback': ['inversion', 'flujos'],
            'indice_rentabilidad': ['inversion', 'flujos', 'tasa'],
        },
    },
    'interes_simple': {
        'obligatorias': ['capital', 'tasa', 'periodos'],
        'opcionales': [],
        'calculos': {
            'monto_final': ['capital', 'tasa', 'periodos'],
            'interes': ['capital', 'tasa', 'periodos'],
        },
    },
    'interes_compuesto': {
        'obligatorias': ['capital', 'tasa', 'periodos'],
        'opcionales': ['capitalizaciones'],
        'calculos': {
            'monto_final': ['capital', 'tasa', 'periodos'],
            'interes': ['capital', 'tasa', 'periodos'],
        },
    },
    'runway': {
        'obligatorias': ['saldo', 'gasto_mensual'],
        'opcionales': ['ingreso_mensual', 'tasa_caida'],
        'calculos': {
            'meses_supervivencia': ['saldo', 'gasto_mensual'],
        },
    },
    'capital_trabajo': {
        'obligatorias': ['dias_cobro', 'dias_inventario', 'dias_pago'],
        'opcionales': ['costo_diario'],
        'calculos': {
            'ciclo_caja': ['dias_cobro', 'dias_inventario', 'dias_pago'],
            'capital_necesario': ['dias_cobro', 'dias_inventario', 'dias_pago', 'costo_diario'],
        },
    },
    'credito': {
        'obligatorias': ['monto', 'tasa', 'num_cuotas'],
        'opcionales': [],
        'calculos': {
            'cuota': ['monto', 'tasa', 'num_cuotas'],
            'amortizacion': ['monto', 'tasa', 'num_cuotas'],
        },
    },
    'convertible': {
        'obligatorias': ['inversion', 'valuation_cap', 'descuento_pct'],
        'opcionales': ['valoracion_pre'],
        'calculos': {
            'dilucion': ['inversion', 'valuation_cap', 'descuento_pct'],
        },
    },
    'valor_terminal': {
        'obligatorias': ['flujo_final', 'tasa_crecimiento', 'tasa'],
        'opcionales': ['multiplo'],
        'calculos': {
            'vt_perpetuidad': ['flujo_final', 'tasa_crecimiento', 'tasa'],
            'vt_multiplo': ['flujo_final', 'multiplo'],
        },
    },
}

# ─── Nombres legibles de variables ───────────────────────────
NOMBRES_LEGIBLES = {
    'inversion': 'inversión inicial',
    'flujos': 'flujos de caja',
    'tasa': 'tasa de descuento',
    'periodos': 'número de períodos',
    'capital': 'capital inicial',
    'capitalizaciones': 'capitalizaciones por año',
    'saldo': 'saldo inicial',
    'gasto_mensual': 'gasto mensual',
    'ingreso_mensual': 'ingreso mensual',
    'tasa_caida': 'tasa de caída de ingresos',
    'monto': 'monto del préstamo',
    'num_cuotas': 'número de cuotas',
    'dias_cobro': 'días de cobro',
    'dias_inventario': 'días de inventario',
    'dias_pago': 'días de pago a proveedores',
    'costo_diario': 'costo diario de operación',
    'valuation_cap': 'valuation cap',
    'valoracion_pre': 'valoración pre-money',
    'descuento_pct': 'porcentaje de descuento',
    'flujo_final': 'flujo del último período',
    'tasa_crecimiento': 'tasa de crecimiento perpetuo',
    'multiplo': 'múltiplo de salida',
    'ingresos': 'ingresos base',
    'costos': 'costos base',
    'ingreso_mensual': 'ingreso mensual',
    'meses': 'meses',
}


def validar(variables: Dict[str, Any], tipo: str) -> Dict:
    """
    Valida las variables extraídas para el tipo de análisis dado.

    Retorna:
        presentes: list de variables encontradas
        faltantes: list de variables obligatorias que faltan
        calculos_posibles: list de cálculos que se pueden hacer
        calculos_imposibles: list de cálculos que no se pueden hacer
        puede_calcular: bool — hay al menos un cálculo posible
    """
    config = REQUERIDAS.get(tipo, {})
    obligatorias = config.get('obligatorias', [])
    calculos = config.get('calculos', {})

    presentes = [v for v in obligatorias if _variable_presente(v, variables)]
    faltantes = [v for v in obligatorias if not _variable_presente(v, variables)]

    calculos_posibles = []
    calculos_imposibles = []
    for calculo, reqs in calculos.items():
        if all(_variable_presente(r, variables) for r in reqs):
            calculos_posibles.append(calculo)
        else:
            faltantes_calc = [r for r in reqs if not _variable_presente(r, variables)]
            calculos_imposibles.append((calculo, faltantes_calc))

    return {
        'presentes': presentes,
        'faltantes': faltantes,
        'calculos_posibles': calculos_posibles,
        'calculos_imposibles': calculos_imposibles,
        'puede_calcular': len(calculos_posibles) > 0,
    }


def _variable_presente(nombre: str, variables: Dict) -> bool:
    """Verifica si una variable está presente y tiene valor válido."""
    if nombre not in variables:
        return False
    val = variables[nombre]
    if val is None:
        return False
    if isinstance(val, list) and len(val) == 0:
        return False
    return True


def nombre_legible(var: str) -> str:
    """Retorna el nombre legible de una variable."""
    return NOMBRES_LEGIBLES.get(var, var.replace('_', ' '))


def resumir_faltantes(faltantes: List[str]) -> List[str]:
    """Genera mensajes de qué datos faltan."""
    return [f"- {nombre_legible(v)}" for v in faltantes]
