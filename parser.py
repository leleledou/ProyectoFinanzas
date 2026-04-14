# ═══════════════════════════════════════════════════════════════
# parser.py — Análisis de Texto en Lenguaje Natural
# Detecta tipo de análisis, extrae variables y sensibilidad
# ═══════════════════════════════════════════════════════════════

import re
from typing import Any, Dict, List, Optional, Tuple

# ─── Tipos de análisis con sus palabras clave ────────────────
TIPOS = {
    'van_tir': {
        'nombre': 'VAN / TIR',
        'keywords': [
            'van', 'valor actual neto', 'npv', 'tir', 'tasa interna de retorno', 'irr',
            'flujo de caja', 'flujos de caja', 'flujo anual', 'flujos anuales',
            'proyecto de inversión', 'proyecto de inversion', 'viabilidad del proyecto',
            'inversión inicial', 'inversion inicial', 'período de recuperación',
            'periodo de recuperacion', 'payback', 'índice de rentabilidad',
        ],
        'peso': 1,
    },
    'interes_simple': {
        'nombre': 'Interés Simple',
        'keywords': ['interés simple', 'interes simple',
                     'simple anual', 'tasa simple'],
        'peso': 5,
    },
    'interes_compuesto': {
        'nombre': 'Interés Compuesto',
        'keywords': [
            'interés compuesto', 'interes compuesto',
            'capitalización', 'capitalizacion', 'capitaliza',
            'compuesto',
        ],
        'peso': 7,
    },
    'runway': {
        'nombre': 'Runway / Supervivencia',
        'keywords': [
            'runway', 'supervivencia', 'burn rate', 'gasto mensual', 'saldo inicial',
            'cuánto tiempo', 'cuanto tiempo', 'cuántos meses', 'cuantos meses',
            'sobrevivir', 'aguantar', 'quedarse sin dinero', 'quedarse sin caja',
            'meses de vida', 'meses le quedan', 'meses de operación',
            'caja disponible', 'efectivo disponible',
        ],
        'peso': 3,
    },
    'capital_trabajo': {
        'nombre': 'Capital de Trabajo',
        'keywords': [
            'capital de trabajo', 'ciclo de caja', 'ciclo operativo',
            'días de cobro', 'dias de cobro', 'días de inventario', 'dias de inventario',
            'días de pago', 'dias de pago', 'ciclo de conversión', 'ciclo de conversion',
            'ciclo de efectivo', 'ciclo de conversión de efectivo',
            'rotación de inventario', 'rotacion de inventario',
            'plazo de cobro', 'plazo de pago',
            'cobra en', 'paga en', 'inventario de',
            'cobro', 'inventario', 'proveedores',
        ],
        'peso': 4,
    },
    'credito': {
        'nombre': 'Crédito / Préstamo',
        'keywords': [
            'préstamo', 'prestamo', 'crédito', 'credito', 'cuota mensual',
            'amortización', 'amortizacion', 'financiamiento', 'hipoteca',
            'tabla de amortización', 'sistema francés', 'sistema frances',
            'línea de crédito', 'linea de credito', 'cuotas mensuales',
            'pago mensual', 'pagos mensuales',
            'revolving', 'línea revolving', 'linea revolving',
        ],
        'peso': 3,
    },
    'convertible': {
        'nombre': 'Nota Convertible',
        'keywords': [
            'nota convertible', 'convertible note', 'valuation cap',
            'dilución del fundador', 'dilucion del fundador',
            'ronda de inversión', 'ronda serie', 'safe',
            'descuento de conversión', 'descuento de conversion',
            'cap de valoración', 'cap de valoracion',
            'pre-money', 'post-money', 'pre money', 'post money',
        ],
        'peso': 4,
    },
    'valor_terminal': {
        'nombre': 'Valor Terminal',
        'keywords': [
            'valor terminal', 'valor residual', 'perpetuidad', 'gordon',
            'múltiplo de salida', 'multiplo de salida', 'exit multiple',
            'tasa de crecimiento perpetuo', 'valor de salida',
            'múltiplo ebitda', 'multiplo ebitda', 'enterprise value',
        ],
        'peso': 4,
    },
}

# ─── Patrones de contexto → variable ─────────────────────────
# Cada entrada: ([keywords_antes_del_número], nombre_variable, transformar)
# transformar: None=valor directo, 'pct'=÷100, 'neg'=negativo
CONTEXTO_MAP: List[Tuple[List[str], str, Optional[str]]] = [
    # Inversión inicial — incluye formas verbales
    (['inversión inicial', 'inversion inicial', 'costo inicial', 'desembolso inicial',
      'capital inicial', 'monto de la inversión', 'monto de la inversion',
      'inversión de', 'inversion de', 'invertir en', 'costo del proyecto',
      'precio del proyecto', 'invierto', 'invertimos', 'invertiré', 'se invierte',
      'inversión es', 'inversion es', 'cuesta', 'vale',
      'invierte', 'invirtió', 'invirtio'], 'inversion', None),

    # Tasa de descuento / interés (porcentaje) — poner primero y con frases largas
    (['tasa de descuento del', 'tasa de descuento de', 'tasa de descuento es',
      'tasa de descuento', 'tasa de interés del', 'tasa de interés de',
      'tasa de interes del', 'tasa de interes de', 'tasa de interés es', 'tasa de interes es',
      'tasa anual de', 'tasa anual del', 'tasa anual es', 'costo de capital de', 'costo de capital es',
      'wacc de', 'wacc es', 'tasa de rendimiento', 'tasa del', 'tasa de',
      'costo de oportunidad de', 'costo de oportunidad del',
      'rendimiento esperado de'], 'tasa', 'pct'),

    # Flujos de caja — incluye formas verbales
    (['flujo de caja de', 'flujos de caja de', 'flujo anual de', 'flujos anuales de',
      'flujo neto de', 'flujos netos de', 'ingreso anual de', 'ingresos anuales de',
      'beneficio anual de', 'genera', 'generará', 'generamos', 'recibirá por año',
      'recibo', 'recibiré', 'recibimos', 'recibe', 'recibir',
      'retorno anual de', 'flujo periódico de', 'flujo periodico de',
      'gana', 'ganaremos', 'produce', 'producirá',
      'flujos de', 'flujo de', 'cash flow de',
      'flujo año', 'flujo del año'], 'flujo', None),

    # Períodos / años
    (['durante', 'por un plazo de', 'en un plazo de', 'plazo de',
      'horizonte de', 'en un período de', 'en un periodo de',
      'durante un período de', 'durante un periodo de',
      'anuales por', 'mensuales por', 'a lo largo de',
      'horizonte de evaluación de', 'horizonte de evaluacion de'], 'periodos', None),

    # Capital (interés simple/compuesto)
    (['capital de', 'depositar', 'depósito de', 'deposito de',
      'suma de', 'ahorra', 'monto de', 'capital inicial de',
      'monto del préstamo de', 'monto del prestamo de'], 'capital', None),

    # Capitalizaciones por año
    (['capitaliza', 'capitalización', 'veces al año', 'veces por año',
      'capitalizaciones al año', 'capitalizaciones por año'], 'capitalizaciones', None),

    # Runway: saldo
    (['saldo inicial de', 'saldo de caja de', 'caja disponible de',
      'cuenta con', 'tiene disponible', 'capital disponible de',
      'tiene en caja', 'saldo de', 'efectivo de',
      'efectivo disponible de', 'cash de',
      'caja inicial'], 'saldo', None),

    # Runway: gasto mensual
    (['gasto mensual de', 'gastos mensuales de', 'costo mensual de',
      'burn rate de', 'egresos mensuales de', 'erogación mensual de',
      'gasta mensualmente', 'costo operativo mensual de',
      'costos fijos mensuales de',
      'burn mensual'], 'gasto_mensual', None),

    # Runway: ingreso mensual
    (['ingreso mensual de', 'ingresos mensuales de',
      'ingreso mensual proyectado', 'ingresos mensuales proyectados',
      'ingresos mensuales estimados', 'ingreso mensual estimado',
      'ingresos proyectados de', 'ingreso proyectado de',
      'ingresos proyectados', 'ingreso proyectado',
      'ingresos mensuales', 'ingreso mensual',
      'recibe mensualmente', 'cobra mensualmente',
      'vende mensualmente', 'factura mensualmente',
      'venta mensual de', 'ventas mensuales de'], 'ingreso_mensual', None),

    # Runway: tasa de caída
    (['tasa de caída', 'tasa de caida', 'caída mensual de', 'caida mensual de',
      'decrecimiento mensual de', 'caen un', 'bajan un',
      'disminuyen un', 'decrecen un'], 'tasa_caida', 'pct'),

    # Crédito: monto del préstamo
    (['monto del préstamo', 'monto del prestamo', 'monto del crédito',
      'monto del credito', 'préstamo de', 'prestamo de',
      'crédito de', 'credito de', 'financiamiento de',
      'línea de crédito de', 'linea de credito de'], 'monto', None),

    # Crédito: cuotas
    (['número de cuotas', 'numero de cuotas', 'cantidad de cuotas',
      'en cuotas', 'en meses', 'plazo en meses', 'plazo de cuotas',
      'cuotas mensuales de', 'pagos mensuales de',
      'plazo de'], 'num_cuotas', None),

    # Capital de trabajo: días de cobro
    (['días de cobro', 'dias de cobro', 'plazo de cobro de',
      'días en cobrar', 'dias en cobrar', 'período de cobro de',
      'periodo de cobro de', 'cobra en', 'demora en cobrar',
      'tarda en cobrar', 'ciclo de cobro de',
      'cobro de', 'cobro en', 'cobrar en'], 'dias_cobro', None),

    # Capital de trabajo: días de inventario
    (['días de inventario', 'dias de inventario', 'rotación de inventario de',
      'días en inventario', 'dias en inventario',
      'inventario de', 'inventario', 'almacena durante'], 'dias_inventario', None),

    # Capital de trabajo: días de pago
    (['días de pago', 'dias de pago', 'plazo de pago de',
      'días para pagar', 'dias para pagar', 'crédito de proveedores de',
      'credito de proveedores de', 'paga a proveedores en',
      'paga proveedores en', 'paga en', 'proveedores en',
      'plazo con proveedores de',
      'proveedores pagan'], 'dias_pago', None),

    # Capital de trabajo: costo diario
    (['costo diario de', 'costo diario', 'egresos diarios de',
      'costo promedio diario de', 'costo promedio diario',
      'gasto diario de', 'gasto diario',
      'operación diaria de'], 'costo_diario', None),

    # Nota convertible
    (['valuation cap de', 'valuation cap es', 'cap de valoración de',
      'cap de valoracion de', 'cap de', 'límite de valoración de',
      'limite de valoracion de', 'valuation cap',
      'valoración cap', 'valoracion cap'], 'valuation_cap', None),
    (['valoración pre-money de', 'valoracion pre-money de',
      'valoración pre de', 'valoracion pre de',
      'pre-money de', 'valoración de la empresa de',
      'valoracion de la empresa de', 'pre-money es',
      'valoración pre-money', 'valoracion pre-money',
      'valoración de la ronda', 'valoracion de la ronda'], 'valoracion_pre', None),
    (['descuento de conversión de', 'descuento de conversion de',
      'con un descuento de', 'descuento de conversión', 'descuento de conversion',
      'descuento del', 'descuento de'], 'descuento_pct', 'pct'),

    # Valor terminal
    (['tasa de crecimiento de', 'tasa de crecimiento es',
      'tasa de crecimiento perpetuo de', 'tasa de crecimiento perpetuo',
      'tasa de crecimiento', 'crecimiento perpetuo de',
      'crecimiento de', 'crecimiento del', 'crecimiento',
      'tasa g de', 'crece al',
      'g =', 'g='], 'tasa_crecimiento', 'pct'),
    (['múltiplo de salida de', 'multiplo de salida de',
      'múltiplo de', 'multiplo de', 'exit multiple de',
      'múltiplo ebitda de', 'multiplo ebitda de',
      'múltiplo de salida', 'multiplo de salida'], 'multiplo', None),
    (['flujo del último año', 'flujo final de', 'flujo del año n de',
      'fcf final de', 'flujo del último período de',
      'último flujo de', 'ultimo flujo de',
      'ebitda del último año', 'ebitda final de',
      'flujo del último año de', 'flujo terminal de'], 'flujo_final', None),

    # Ingresos / costos genéricos (para sensibilidad)
    (['ingresos de', 'ingreso de', 'ventas de',
      'revenue de', 'facturación de', 'facturacion de'], 'ingresos', None),
    (['costos de', 'costo de', 'gastos de', 'gasto de',
      'costos operativos de', 'costos fijos de'], 'costos', None),
]

# ─── Palabras clave de sensibilidad ──────────────────────────
KEYWORDS_SENSIBILIDAD = [
    'sensibilidad', 'sensible', 'sensible a', 'análisis de sensibilidad',
    'analisis de sensibilidad', 'varía', 'varia', 'variando', 'variar',
    'si cambia', 'si aumenta', 'si disminuye', 'si baja', 'si sube',
    'qué pasa si', 'que pasa si', 'escenario pesimista', 'escenario optimista',
    'escenarios', 'impacto de', 'efecto de',
    'qué pasaría', 'que pasaria', 'evaluar con', 'evalúa con',
    'comparar con', 'simular con', 'rango de', 'entre valores de',
]

# Variables que pueden ser sensibles con sus nombres canónicos
# Orden importa: las más específicas primero para evitar falsos positivos
VARIABLE_SENSIBILIDAD = {
    'ingreso_mensual': ['ingreso mensual', 'ingresos mensuales', 'venta mensual',
                        'ingresos reales', 'ingresos_mensuales', 'ingresos mensuales'],
    'tasa_caida': ['tasa de caída', 'tasa de caida', 'caída de ingresos'],
    'valuation_cap': ['valuation cap', 'cap de valoración', 'cap de valoracion',
                      'valoración cap', 'valoracion cap', 'cap'],
    'multiplo': ['múltiplo de salida', 'multiplo de salida', 'exit multiple',
                 'multiple salida', 'multiple_salida',
                 'múltiplo', 'multiplo', 'multiple'],
    'descuento_pct': ['descuento de conversión', 'descuento de conversion', 'descuento'],
    'dias_cobro': ['días de cobro', 'dias de cobro', 'dias cobro',
                   'cobro', 'plazo de cobro'],
    'flujos': ['flujo de caja', 'flujos de caja', 'flujo', 'flujos'],
    'ingresos': ['ingresos', 'ingreso', 'ventas', 'revenue'],
    'costos': ['costo', 'costos', 'gasto', 'gastos', 'egresos'],
    'tasa': ['tasa de descuento', 'tasa descuento', 'tasa de interés',
             'tasa de interes', 'wacc', 'tasa'],
    'inversion': ['inversión', 'inversion', 'capital inicial'],
}

# Variables que se refieren a flujos de un año específico
# Patrón: flujo_año3, flujo_a3, etc.
PATRON_FLUJO_ANIO = re.compile(
    r'(?:flujo|f)\s*(?:del?\s*)?(?:año|a)\s*(\d+)',
    re.IGNORECASE
)


# ════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
# CAPA DE NORMALIZACIÓN DE MONEDAS (preprocesamiento)
# ════════════════════════════════════════════════════════════════

_BOL_TOKENS = (
    r'moneda\s+boliviana',
    r'bolivianos?',
    r'BOB',
    r'Bs\.?',
)
_USD_TOKENS = (
    r'd[óo]lares?',
    r'US\$',
    r'USD',
)

_RE_BOL_ANTES = re.compile(
    r'(?<![A-Za-z0-9])(?:' + '|'.join(_BOL_TOKENS) + r')\s*(-?\s*[\d][\d.,]*)',
    re.IGNORECASE)
_RE_BOL_DESPUES = re.compile(
    r'(-?\s*[\d][\d.,]*)\s*(?:' + '|'.join(_BOL_TOKENS) + r')(?![A-Za-z0-9])',
    re.IGNORECASE)
_RE_USD_ANTES = re.compile(
    r'(?<![A-Za-z0-9])(?:' + '|'.join(_USD_TOKENS) + r')\s*(-?\s*[\d][\d.,]*)',
    re.IGNORECASE)
_RE_USD_DESPUES = re.compile(
    r'(-?\s*[\d][\d.,]*)\s*(?:' + '|'.join(_USD_TOKENS) + r')(?![A-Za-z0-9])',
    re.IGNORECASE)


def _normalizar_monedas(texto: str) -> Tuple[str, Optional[str]]:
    """
    Capa previa al análisis: reconoce variantes de bolivianos y dólares
    y las normaliza a un formato que el extractor numérico ya maneja.

    - Bs / Bs. / BOB / bolivianos / moneda boliviana → se marcan con 'Bs '
      antepuesto al número (sin alterar el valor).
    - USD / US$ / dólares / dolares / dólar / dolar → se convierten a '$'
      antepuesto al número, para aprovechar la detección existente.

    Retorna (texto_normalizado, moneda_dominante) donde moneda_dominante
    es '$', 'Bs' o None si no se detectó.
    """
    if not texto:
        return texto, None

    cuenta_bol = 0
    cuenta_usd = 0

    def _sub_bol(m):
        nonlocal cuenta_bol
        cuenta_bol += 1
        num = m.group(1).replace(' ', '')
        return f' Bs {num} '

    def _sub_usd(m):
        nonlocal cuenta_usd
        cuenta_usd += 1
        num = m.group(1).replace(' ', '')
        return f' ${num} '

    # Dólares primero (US$ contiene $ que podría confundirse luego)
    out = _RE_USD_ANTES.sub(_sub_usd, texto)
    out = _RE_USD_DESPUES.sub(_sub_usd, out)
    out = _RE_BOL_ANTES.sub(_sub_bol, out)
    out = _RE_BOL_DESPUES.sub(_sub_bol, out)

    # Colapsar espacios múltiples generados por las sustituciones
    out = re.sub(r'[ \t]{2,}', ' ', out)

    if cuenta_bol == 0 and cuenta_usd == 0:
        return out, None

    # Si aparecen ambas, gana la más frecuente; empate → no se fuerza una sola
    if cuenta_bol > cuenta_usd:
        moneda = 'Bs'
    elif cuenta_usd > cuenta_bol:
        moneda = '$'
    else:
        moneda = '$' if cuenta_usd else 'Bs'
    return out, moneda


# ════════════════════════════════════════════════════════════════
# CAPA DE INTERPRETACIÓN SEMÁNTICA (preprocesamiento)
# ════════════════════════════════════════════════════════════════
# Reescribe frases en lenguaje natural a formas canónicas que el
# parser existente sabe mapear. No altera la lógica ni las fórmulas.

_SEMANTIC_REWRITES: List[Tuple[re.Pattern, str]] = [
    # Tasa de descuento → tasa (evita colisión con "descuento del" de convertibles)
    (re.compile(r'\btasa\s+de\s+descuento\b', re.IGNORECASE), 'tasa'),
    (re.compile(r'\btasa\s+referencial\b', re.IGNORECASE), 'tasa'),
    (re.compile(r'\btasa\s+de\s+referencia\b', re.IGNORECASE), 'tasa'),
    (re.compile(r'\binter[eé]s\s+anual\b', re.IGNORECASE), 'tasa anual'),
    (re.compile(r'\binter[eé]s\s+del\b', re.IGNORECASE), 'tasa del'),
    # "a 11%" entre flujos anuales → "con tasa del 11%"
    (re.compile(r'\b(a|al)\s+(\d+(?:[.,]\d+)?\s*%)', re.IGNORECASE),
     r'con tasa del \2'),
    # Recursos / dinero
    (re.compile(r'\brecursos\s+del\s+proyecto\b', re.IGNORECASE), 'inversión'),
    (re.compile(r'\brecursos\s+de\s+arranque\b', re.IGNORECASE), 'inversión inicial'),
    (re.compile(r'\bdinero\s+disponible\b', re.IGNORECASE), 'saldo'),
    # Sinónimos de flujos (listas de varios valores anuales)
    (re.compile(r'\bingresos?\s+por\s+a[ñn]o\b', re.IGNORECASE), 'flujos anuales'),
    (re.compile(r'\bingresos?\s+anuales?\s+de\b', re.IGNORECASE), 'flujos anuales de'),
    (re.compile(r'\bretornos?\s+esperados?\s*:?', re.IGNORECASE), 'flujos:'),
    (re.compile(r'\bretornos?\s+de\b', re.IGNORECASE), 'flujos de'),
    (re.compile(r'\bretornos?\b', re.IGNORECASE), 'flujos'),
    (re.compile(r'\bmontos?\s+por\s+per[ií]odo\b', re.IGNORECASE), 'flujos'),
    (re.compile(r'\bentradas?\s+anuales?\b', re.IGNORECASE), 'flujos anuales'),
    (re.compile(r'\bgenerando\s+ingresos?\s+de\b', re.IGNORECASE), 'flujos de'),
    (re.compile(r'\bgenera\s+flujos?\s+de\b', re.IGNORECASE), 'flujos de'),
    # Costos operativos / OPEX
    (re.compile(r'\bcostos?\s+operativos?\s+mensuales?\b', re.IGNORECASE),
     'gasto mensual'),
    (re.compile(r'\bpagos?\s+recurrentes?\b', re.IGNORECASE), 'gasto mensual'),
    # Sensibilidad explícita: "variaciones de 8%, 15% y 20%" / "sensibilidad de ..."
    (re.compile(r'\b(?:an[aá]lisis\s+de\s+)?sensibilidad\s+'
                r'(?:con\s+)?(?:variaciones?\s+de\s+)?', re.IGNORECASE),
     'escenarios de '),
    (re.compile(r'\bvariando\s+la\s+tasa\s+en\b', re.IGNORECASE),
     'escenarios de tasa'),
    (re.compile(r'\bvariaciones?\s+de\b', re.IGNORECASE), 'escenarios de'),
    # "tasa cambia de X% a Y%" → escenarios discretos
    (re.compile(r'\btasa\s+cambia\s+de\s+(\d+(?:[.,]\d+)?)\s*%\s+a\s+'
                r'(\d+(?:[.,]\d+)?)\s*%', re.IGNORECASE),
     r'tasa del \1% escenarios de tasa \1%, \2%'),
    # Escenarios de cambio de plazo (aumentar / ampliar / extender)
    (re.compile(r'\b(?:si\s+)?(?:se\s+)?(?:le\s+)?'
                r'(?:aumentamos?|aumenta|ampl[ií]a|extiende|alarga|suma|sumamos|'
                r'incrementamos?|incrementa)\s+'
                r'(?:el\s+plazo\s+(?:en\s+|de\s+)?)?'
                r'(\d+)\s*(meses?|a[ñn]os?)(?:\s+adicionales?)?(?:\s+mas)?',
                re.IGNORECASE),
     r'escenario plazo mas \1 xmeses'),
    (re.compile(r'\b(?:si\s+)?(?:se\s+)?(?:le\s+)?'
                r'(?:disminuimos?|disminuye|reducimos?|reduce|restamos?|resta|'
                r'acortamos?|acorta|recorta)\s+'
                r'(?:el\s+plazo\s+(?:en\s+|de\s+)?)?'
                r'(\d+)\s*(meses?|a[ñn]os?)(?:\s+menos)?',
                re.IGNORECASE),
     r'escenario plazo menos \1 xmeses'),
    # "cuánto vas a devolver" → indica interés simple de monto final
    (re.compile(r'\bcu[aá]nto\s+(?:vas\s+a|voy\s+a|debes?)\s+devolver\b',
                re.IGNORECASE),
     'calcular monto final de interés simple'),
]


def _enriquecer_semantica(texto: str) -> str:
    """Reescribe sinónimos y expresiones naturales a formas canónicas."""
    if not texto:
        return texto
    out = texto
    # Pases contextuales: resolver ambigüedades léxicas antes de las reescrituras.
    out = _resolver_saldo_vs_capital(out)
    out = _resolver_capital_vs_inversion(out)
    for patron, repl in _SEMANTIC_REWRITES:
        out = patron.sub(repl, out)
    # Colapsar espacios extra generados por las sustituciones
    out = re.sub(r'[ \t]{2,}', ' ', out)
    return out


_RE_CAP_INIT = re.compile(
    r'\b(capital\s+inicial|monto\s+inicial|monto\s+de|monto|capital)\s+de\b',
    re.IGNORECASE)
_HINTS_INVERSION = (
    'flujo', 'flujos', 'ingresos de', 'retorno', 'retornos', 'van', 'tir',
    'generando', 'genera flujos', 'proyecto', 'año 1', 'año 2', 'anio 1',
    'primer año', 'primer anio', 'rentabilidad del proyecto', 'inversión inicial',
    'inversion inicial',
)
_HINTS_CAPITAL = (
    'interés simple', 'interes simple', 'interés compuesto', 'interes compuesto',
    'monto final', 'valor acumulado', 'se invierte a una tasa',
    'cuánto vas a devolver', 'cuanto vas a devolver',
    'capital de', 'se dispone de un capital', 'se cuenta con',
)


_RE_CUENTA_CON = re.compile(
    r'\bse\s+cuenta\s+con\b', re.IGNORECASE)
_HINTS_INTERES = (
    'interés simple', 'interes simple', 'interés compuesto', 'interes compuesto',
    'monto final', 'valor acumulado', 'valor final',
)


def _resolver_saldo_vs_capital(texto: str) -> str:
    """'Se cuenta con N' puede ser saldo (runway) o capital (interés). Si el
    enunciado menciona interés/monto final, preferir capital."""
    low = texto.lower()
    if any(h in low for h in _HINTS_INTERES):
        return _RE_CUENTA_CON.sub('se dispone de un capital de', texto)
    return texto


def _resolver_capital_vs_inversion(texto: str) -> str:
    """
    Decide si 'capital inicial/monto inicial/monto de' en el enunciado debe
    leerse como inversión (proyecto con flujos) o como capital (interés simple
    o compuesto). Reescribe hacia la forma canónica que el CONTEXTO_MAP maneja.
    """
    low = texto.lower()
    score_inv = sum(1 for h in _HINTS_INVERSION if h in low)
    score_cap = sum(1 for h in _HINTS_CAPITAL if h in low)
    if score_inv == score_cap:
        return texto

    destino = 'inversión de' if score_inv > score_cap else 'capital de'

    def _rep(m):
        # Conserva la palabra "inicial" si la venía para reforzar el mapeo
        grp = m.group(1).lower()
        if 'inicial' in grp and destino.startswith('inversión'):
            return 'inversión inicial de'
        if 'inicial' in grp and destino.startswith('capital'):
            return 'capital de'
        return destino

    return _RE_CAP_INIT.sub(_rep, texto)


def analizar_texto(texto: str) -> Dict[str, Any]:
    """
    Analiza el texto en lenguaje natural y retorna un diccionario con:
      - tipo: str (clave del tipo de análisis)
      - tipo_nombre: str (nombre legible)
      - variables: dict {nombre: valor}
      - sensibilidad: dict | None
      - moneda: str ('$' o 'Bs') detectada en el texto
      - texto_original: str
    """
    texto_norm, moneda = _normalizar_monedas(texto)
    texto_norm = _enriquecer_semantica(texto_norm)
    texto_l = texto_norm.lower()

    tipo, tipo_nombre = _detectar_tipo(texto_l)
    variables = _extraer_variables(texto_l, tipo)
    sensibilidad = _detectar_sensibilidad(texto_l, tipo, variables)

    return {
        'tipo': tipo,
        'tipo_nombre': tipo_nombre,
        'variables': variables,
        'sensibilidad': sensibilidad,
        'moneda': moneda or '$',
        'texto_original': texto,
    }


# ════════════════════════════════════════════════════════════════
# DETECCIÓN DE TIPO
# ════════════════════════════════════════════════════════════════

def _detectar_tipo(texto_l: str) -> Tuple[str, str]:
    """Retorna (clave_tipo, nombre_tipo) con mayor puntaje de keywords."""
    puntajes: Dict[str, int] = {}

    for tipo_key, info in TIPOS.items():
        score = 0
        peso = info.get('peso', 1)
        for kw in info['keywords']:
            if kw in texto_l:
                # Keywords más largos (más específicos) valen más
                bonus = len(kw.split()) - 1  # frases de múltiples palabras valen más
                score += peso + bonus
        puntajes[tipo_key] = score

    mejor = max(puntajes, key=lambda k: puntajes[k])

    # Si el mejor puntaje es 0, usar heurísticas adicionales antes de default
    if puntajes[mejor] == 0:
        mejor = _detectar_tipo_por_heuristica(texto_l)

    return mejor, TIPOS[mejor]['nombre']


def _detectar_tipo_por_heuristica(texto_l: str) -> str:
    """Detecta el tipo cuando no hay keywords explícitos, usando patrones."""
    # Buscar patrones numéricos que sugieran el tipo
    tiene_cuotas = bool(re.search(r'\d+\s*cuotas?', texto_l))
    tiene_dias = bool(re.search(r'\d+\s*d[ií]as?', texto_l) or
                      re.search(r'd[ií]as?\s*de\s*(cobro|pago|inventario)', texto_l) or
                      re.search(r'cobr[ao].*\d+\s*d[ií]as?', texto_l) or
                      re.search(r'inventario.*\d+\s*d[ií]as?', texto_l))
    tiene_flujos_periodo = bool(re.search(r'(?:año|a)\s*\d+\s*[=:]', texto_l))
    tiene_cap = 'cap' in texto_l or 'convertible' in texto_l
    tiene_multiplo = bool(re.search(r'\d+\s*[xX]', texto_l))
    tiene_runway = bool(re.search(r'(saldo|caja|efectivo).{0,30}(gasto|burn|egreso)', texto_l))

    if tiene_cuotas:
        return 'credito'
    if tiene_dias:
        return 'capital_trabajo'
    if tiene_cap:
        return 'convertible'
    if tiene_runway:
        return 'runway'
    if tiene_multiplo and not tiene_flujos_periodo:
        return 'valor_terminal'
    return 'van_tir'  # default final


# ════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE NÚMEROS CON CONTEXTO
# ════════════════════════════════════════════════════════════════

def _encontrar_numeros(texto_l: str) -> List[Dict[str, Any]]:
    """
    Encuentra todos los números en el texto con su contexto.
    Soporta: 150k, 1.5M, 4x, -50000, $100,000, 12%, etc.
    """
    patron = re.compile(
        r'(?<!\w)'                                      # no precedido por letra/dígito
        r'(-\s*)?'                                       # (1) signo negativo opcional
        r'(\$\s*)?'                                      # (2) signo $ opcional
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?'           # (3) número con separadores
        r'|\d+(?:[.,]\d+)?)'                             # o número simple
        r'\s*'
        r'(mil(?:lones?)?|millones?'                     # (4) unidad/sufijo
        r'|meses?|períodos?|periodos?|cuotas?|años?|anios?'
        r'|d[ií]as?'
        r'|[kK]|[mM]{1,2}'
        r'|%|[xX])?'
        r'(?!\w)',
        re.IGNORECASE
    )

    resultados = []
    for m in patron.finditer(texto_l):
        signo_neg = bool(m.group(1))
        tiene_peso = bool(m.group(2))
        raw_num = m.group(3)
        unidad_raw = (m.group(4) or '').strip()
        unidad = unidad_raw.lower()

        valor = _parsear_numero(raw_num)
        if valor is None:
            continue

        # Aplicar multiplicador de unidad/sufijo
        es_multiplo = False
        if unidad.startswith('millon') or unidad in ('m', 'mm'):
            valor *= 1_000_000
        elif unidad == 'mil' or unidad == 'k':
            valor *= 1_000
        elif unidad == 'x':
            es_multiplo = True

        # Aplicar signo negativo
        if signo_neg:
            valor = -valor

        # Determinar si es porcentaje
        es_pct = unidad == '%'
        resto = texto_l[m.end():m.end() + 15]
        if 'por ciento' in resto or 'porciento' in resto:
            es_pct = True

        # Contexto: 90 caracteres antes, 40 caracteres después
        inicio = m.start()
        ctx_inicio = max(0, inicio - 90)
        contexto_antes = texto_l[ctx_inicio:inicio].strip()
        fin = m.end()
        ctx_fin = min(len(texto_l), fin + 40)
        contexto_despues = texto_l[fin:ctx_fin].strip()

        unidades_tiempo = ('años', 'año', 'anios', 'anio',
                           'meses', 'mes',
                           'períodos', 'periodos', 'período', 'periodo')
        unidades_cuota = ('cuotas', 'cuota')
        unidades_dias = ('días', 'dias', 'día', 'dia')

        resultados.append({
            'valor': valor,
            'es_pct': es_pct,
            'es_multiplo': es_multiplo,
            'unidad_tiempo': unidad in unidades_tiempo,
            'unidad_dias': unidad in unidades_dias,
            'unidad_cuota': unidad in unidades_cuota,
            'tiene_peso': tiene_peso,
            'contexto_antes': contexto_antes,
            'contexto_despues': contexto_despues,
            'pos': inicio,
            'raw': m.group(0),
            'unidad': unidad,
        })

    return resultados


def _parsear_numero(s: str) -> Optional[float]:
    """Convierte string a float manejando formatos ES (1.000,50) y EN (1,000.50)."""
    s = s.strip()
    if not s:
        return None

    tiene_coma = ',' in s
    tiene_punto = '.' in s

    if tiene_coma and tiene_punto:
        ultimo_coma = s.rfind(',')
        ultimo_punto = s.rfind('.')
        if ultimo_punto > ultimo_coma:
            # EN: 1,000.50
            s = s.replace(',', '')
        else:
            # ES: 1.000,50
            s = s.replace('.', '').replace(',', '.')
    elif tiene_coma:
        partes = s.split(',')
        if len(partes) == 2 and len(partes[1]) <= 2:
            s = s.replace(',', '.')    # decimal
        else:
            s = s.replace(',', '')     # miles
    elif tiene_punto:
        partes = s.split('.')
        if len(partes) == 2 and len(partes[1]) == 3:
            s = s.replace('.', '')     # miles estilo ES
        # else: decimal normal

    try:
        return float(s)
    except ValueError:
        return None


# ════════════════════════════════════════════════════════════════
# MAPEO DE NÚMEROS A VARIABLES
# ════════════════════════════════════════════════════════════════

def _identificar_variable(num: Dict, tipo: str) -> Optional[str]:
    """
    Asigna un nombre de variable al número según su contexto.
    Usa el keyword más cercano (más a la derecha) al número.
    """
    ctx_full = num['contexto_antes']
    # Usar últimas 50 chars para contexto inmediato
    ctx = ctx_full[-50:] if len(ctx_full) > 50 else ctx_full

    # Si es múltiplo (4x, 6x), asignar como multiplo
    if num.get('es_multiplo'):
        return 'multiplo'

    # Encontrar el keyword más cercano al número (mayor posición en ctx)
    # Si dos keywords empatan en posición, preferir el más largo (más específico)
    mejor_pos = -1
    mejor_var = None
    mejor_len = 0

    for keywords, var_name, _ in CONTEXTO_MAP:
        for kw in keywords:
            pos = ctx.rfind(kw)   # rfind = última aparición = más cercana al número
            if pos > mejor_pos or (pos == mejor_pos and pos >= 0 and len(kw) > mejor_len):
                mejor_pos = pos
                mejor_var = var_name
                mejor_len = len(kw)

    # Heurísticas por unidad: si el número tiene unidad de tiempo/cuota/días
    if num['unidad_cuota']:
        return 'num_cuotas'

    # Números con unidad "días" → solo relevantes para capital_trabajo
    if num.get('unidad_dias'):
        if tipo == 'capital_trabajo':
            # Primero buscar en contexto completo solo para dias_*
            for keywords, var_name, _ in CONTEXTO_MAP:
                if not var_name.startswith('dias_'):
                    continue
                for kw in keywords:
                    if kw in ctx:
                        return var_name
            # Buscar en contexto posterior
            after_ctx = num.get('contexto_despues', '')
            if any(kw in after_ctx for kw in ['crédito', 'credito', 'cobro', 'cobrar', 'cliente']):
                return 'dias_cobro'
            if any(kw in after_ctx for kw in ['proveedor', 'pago', 'pagar']):
                return 'dias_pago'
            if any(kw in after_ctx for kw in ['inventario', 'almacen', 'stock']):
                return 'dias_inventario'
            # Default para capital_trabajo con días: usar posición
            return 'dias_cobro'
        # Para otros tipos, "X días" no es una variable estándar → ignorar
        return None

    if num['unidad_tiempo']:
        # Solo usar el match de contexto si es muy cercano al número (últimos 12 chars)
        # Esto evita que "flujos de 400k por 5 años" asigne el 5 a flujo
        ctx_cercano = ctx[-12:] if len(ctx) > 12 else ctx
        for keywords, var_name, _ in CONTEXTO_MAP:
            if var_name == 'periodos':
                continue
            for kw in keywords:
                if kw in ctx_cercano:
                    return var_name
        return 'periodos'

    # Si el número es porcentaje, priorizar variables de tipo porcentaje
    # No permitir que un % se asigne a una variable monetaria
    _VARS_MONETARIAS = {'inversion', 'flujo', 'capital', 'saldo', 'gasto_mensual',
                        'ingreso_mensual', 'monto', 'valuation_cap', 'valoracion_pre',
                        'flujo_final', 'ingresos', 'costos', 'costo_diario',
                        '_monto_sin_contexto'}
    _VARS_PCT = {'tasa', 'descuento_pct', 'tasa_crecimiento', 'tasa_caida'}

    if num['es_pct']:
        # Si el contexto encontró una variable de porcentaje, usarla
        if mejor_var in _VARS_PCT:
            return mejor_var
        # Si no, asignar como tasa para los tipos que lo esperan
        if tipo in ('van_tir', 'credito', 'valor_terminal',
                    'interes_simple', 'interes_compuesto'):
            return 'tasa'
        if tipo == 'convertible':
            return 'descuento_pct'
        return mejor_var

    if mejor_var is not None:
        return mejor_var

    # Números monetarios sin contexto → asignación posicional posterior
    valor = num['valor']
    if num['tiene_peso'] or (abs(valor) >= 100 and not num['es_pct']):
        return '_monto_sin_contexto'

    return None


def _get_transform(var_name: str) -> Optional[str]:
    """Retorna la transformación para una variable."""
    for keywords, name, transform in CONTEXTO_MAP:
        if name == var_name:
            return transform
    return None


def _extraer_variables(texto_l: str, tipo: str) -> Dict[str, Any]:
    """Extrae y mapea todas las variables del texto."""
    numeros = _encontrar_numeros(texto_l)
    variables: Dict[str, Any] = {}
    flujos_lista: List[float] = []
    montos_sin_ctx: List[float] = []

    # Detectar flujos explícitos por año: "año 1: X, año 2: Y, ..."
    # o "A1=25k, A2=35k, A3=45k"
    flujos_explicitos = _extraer_flujos_por_periodo(texto_l)
    if flujos_explicitos:
        variables['flujos'] = flujos_explicitos

    for num in numeros:
        var_name = _identificar_variable(num, tipo)
        if var_name is None:
            continue

        valor = num['valor']

        # Aplicar transformación de porcentaje si corresponde
        if not num['es_pct']:
            # Verificar si el contexto sugiere que es porcentaje
            transform = _get_transform(var_name)
            if transform == 'pct' and valor > 1:
                valor = valor / 100
        else:
            # Ya es porcentaje (tiene %)
            if var_name in ('tasa', 'descuento_pct', 'tasa_crecimiento', 'tasa_caida'):
                valor = valor / 100

        if var_name == 'flujo':
            flujos_lista.append(valor)
        elif var_name == '_monto_sin_contexto':
            montos_sin_ctx.append(valor)
        elif var_name not in variables:
            variables[var_name] = valor

    # Construir lista de flujos si no se extrajeron explícitamente
    if 'flujos' not in variables and flujos_lista:
        periodos = int(variables.get('periodos', len(flujos_lista)))
        if len(flujos_lista) == 1 and periodos > 1:
            variables['flujos'] = [flujos_lista[0]] * periodos
        else:
            variables['flujos'] = flujos_lista

    # Resolver montos sin contexto según el tipo
    # ── Asignación posicional de montos sin contexto explícito ──
    if montos_sin_ctx:
        if tipo == 'van_tir':
            # Primer monto grande = inversión, resto = flujos (si no hay flujos ya)
            if 'inversion' not in variables:
                variables['inversion'] = montos_sin_ctx[0]
                montos_sin_ctx = montos_sin_ctx[1:]
            if 'flujos' not in variables and montos_sin_ctx and not flujos_lista:
                periodos = int(variables.get('periodos', len(montos_sin_ctx)))
                if len(montos_sin_ctx) == 1 and periodos > 1:
                    variables['flujos'] = [montos_sin_ctx[0]] * periodos
                else:
                    variables['flujos'] = montos_sin_ctx[:]

        elif tipo == 'credito':
            if 'monto' not in variables:
                variables['monto'] = montos_sin_ctx[0]

        elif tipo in ('interes_simple', 'interes_compuesto'):
            if 'capital' not in variables:
                variables['capital'] = montos_sin_ctx[0]

        elif tipo == 'runway':
            if 'saldo' not in variables:
                variables['saldo'] = montos_sin_ctx[0]
                montos_sin_ctx = montos_sin_ctx[1:]
            if 'gasto_mensual' not in variables and montos_sin_ctx:
                variables['gasto_mensual'] = montos_sin_ctx[0]

        elif tipo == 'convertible':
            if 'inversion' not in variables:
                variables['inversion'] = montos_sin_ctx[0]
                montos_sin_ctx = montos_sin_ctx[1:]
            if 'valuation_cap' not in variables and montos_sin_ctx:
                variables['valuation_cap'] = montos_sin_ctx[0]
                montos_sin_ctx = montos_sin_ctx[1:]
            # No asignar valoracion_pre por posición — se contamina con valores
            # de sensibilidad. Si falta, motor.py lo defaultea a valuation_cap.

        elif tipo == 'valor_terminal':
            if 'flujo_final' not in variables:
                variables['flujo_final'] = montos_sin_ctx[0]

    # Si hay flujos_lista y aún no se asignaron, usarlos
    if 'flujos' not in variables and flujos_lista:
        periodos = int(variables.get('periodos', len(flujos_lista)))
        if len(flujos_lista) == 1 and periodos > 1:
            variables['flujos'] = [flujos_lista[0]] * periodos
        else:
            variables['flujos'] = flujos_lista

    # Promover 'ingresos' genérico a 'ingreso_mensual' en contexto runway
    if tipo == 'runway' and 'ingreso_mensual' not in variables and 'ingresos' in variables:
        variables['ingreso_mensual'] = variables.pop('ingresos')

    # Normalizar tasa: si es > 1 y no es porcentaje explícito, es probable %
    if 'tasa' in variables and variables['tasa'] > 1:
        variables['tasa'] = variables['tasa'] / 100

    # Normalizar descuento_pct: si ya vino como decimal (0.20) dejarlo como está
    # Si vino como entero (20) ya fue dividido por 100 en la extracción

    # Para interés: convertir meses a años si periodos viene de "X meses"
    if tipo in ('interes_simple', 'interes_compuesto') and 'periodos' in variables:
        if re.search(r'\b\d+\s*meses?\b', texto_l) and variables['periodos'] >= 12:
            variables['periodos'] = variables['periodos'] / 12

    # Para interés compuesto: detectar tasas separadas de simple y compuesto
    if tipo == 'interes_compuesto':
        m_comp = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:anual\s+)?compuesto', texto_l)
        if m_comp:
            variables['tasa'] = float(m_comp.group(1)) / 100
        m_simp = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:anual\s+)?simple', texto_l)
        if m_simp:
            variables['tasa_simple_ref'] = float(m_simp.group(1)) / 100

    return variables


def _extraer_flujos_por_periodo(texto_l: str) -> Optional[List[float]]:
    """
    Detecta patrones de flujos etiquetados por período:
    - 'año 1: $25k, año 2: $35k'
    - 'A1=25k, A2=35k, A3=45k'
    - 'F1=25000, F2=30000'
    - 'período 1: 25000, período 2: 30000'
    """
    # Patrón ampliado: soporta año/periodo/A/F + número + separador + valor con sufijo
    # (?<!\w) evita que "a" dentro de palabras como "oferta" coincida
    patron = re.compile(
        r'(?<!\w)(?:año|periodo|período|mes|a|f)\s*(\d+)\s*[:\-=]\s*'
        r'(-?\s*\$?\s*[\d.,]+)\s*([kKmM]{1,2}|mil(?:lones?)?)?',
        re.IGNORECASE
    )
    matches = patron.findall(texto_l)
    if len(matches) < 2:
        return None

    try:
        pares = []
        for periodo_str, valor_str, sufijo in matches:
            valor = _parsear_numero(valor_str.replace('$', '').replace(' ', ''))
            if valor is None:
                continue
            sufijo_l = sufijo.lower().strip()
            if sufijo_l == 'k':
                valor *= 1_000
            elif sufijo_l in ('m', 'mm') or sufijo_l.startswith('millon'):
                valor *= 1_000_000
            elif sufijo_l == 'mil':
                valor *= 1_000
            # Manejar signo negativo en el valor
            if valor_str.strip().startswith('-'):
                valor = -abs(valor)
            pares.append((int(periodo_str), valor))
        pares.sort()
        if pares:
            return [v for _, v in pares]
    except Exception:
        pass

    return None


# ════════════════════════════════════════════════════════════════
# DETECCIÓN DE SENSIBILIDAD
# ════════════════════════════════════════════════════════════════

def _detectar_sensibilidad(texto_l: str, tipo: str,
                            variables: Dict) -> Optional[Dict]:
    """
    Detecta si se solicita análisis de sensibilidad.
    Retorna dict con variable_sensible, variaciones porcentuales o discretas.
    """
    # Verificar si hay keywords de sensibilidad
    hay_kw = any(kw in texto_l for kw in KEYWORDS_SENSIBILIDAD)

    # Para VAN/TIR, siempre hacer sensibilidad sobre flujos por defecto
    hacer_sens = hay_kw or tipo == 'van_tir'
    if not hacer_sens:
        return None

    # Detectar variable sensible mencionada explícitamente
    var_sensible = _detectar_variable_sensible(texto_l, tipo, variables)

    # Detectar si se pide sensibilidad sobre un flujo de año específico
    flujo_anio = _detectar_flujo_anio_sensible(texto_l.replace('_', ' '))

    # Intentar detectar escenarios discretos primero
    valores_discretos = _detectar_escenarios_discretos(texto_l)

    # Si hay valores discretos, usarlos
    if valores_discretos:
        return {
            'variable': var_sensible,
            'variaciones_pct': None,
            'valores_discretos': valores_discretos,
            'flujo_anio': flujo_anio,
            'explicita': hay_kw,
        }

    # Si no, usar variaciones porcentuales
    variaciones = _detectar_variaciones(texto_l)
    if not variaciones:
        variaciones = [-30, -20, -10, 0, 10, 20, 30]  # default

    return {
        'variable': var_sensible,
        'variaciones_pct': variaciones,
        'valores_discretos': None,
        'flujo_anio': flujo_anio,
        'explicita': hay_kw,
    }


def _detectar_variable_sensible(texto_l: str, tipo: str,
                                  variables: Dict) -> str:
    """Identifica qué variable se quiere variar."""
    # Normalizar underscores → espacios para coincidencia
    texto_norm = texto_l.replace('_', ' ')

    for var_canon, aliases in VARIABLE_SENSIBILIDAD.items():
        for alias in aliases:
            alias_norm = alias.replace('_', ' ')
            # Buscar "sensibilidad a X", "escenarios de X", "si X cambia" etc.
            patrones_ctx = [
                f'sensibilidad a {alias_norm}', f'sensibilidad de {alias_norm}',
                f'sensibilidad del {alias_norm}', f'sensibilidad en {alias_norm}',
                f'sensible a {alias_norm}', f'sensible: {alias_norm}',
                f'sensibles: {alias_norm}',
                f'variable sensible: {alias_norm}',
                f'si {alias_norm}', f'variar {alias_norm}',
                f'variando {alias_norm}', f'impacto de {alias_norm}',
                f'impacto del {alias_norm}', f'efecto de {alias_norm}',
                f'efecto del {alias_norm}',
                f'escenarios de {alias_norm}', f'escenarios del {alias_norm}',
                f'valores de {alias_norm}', f'valores del {alias_norm}',
                f'con {alias_norm} de', f'evaluar {alias_norm}',
            ]
            for p in patrones_ctx:
                if p in texto_norm:
                    # Remap genérico a tipo-específico
                    if var_canon == 'ingresos' and tipo == 'runway':
                        return 'ingreso_mensual'
                    return var_canon

    # Detectar referencia a flujo de año específico
    if PATRON_FLUJO_ANIO.search(texto_norm):
        return 'flujos'

    # Default por tipo
    defaults = {
        'van_tir': 'flujos',
        'runway': 'ingreso_mensual',
        'credito': 'tasa',
        'interes_simple': 'tasa',
        'interes_compuesto': 'tasa',
        'valor_terminal': 'tasa_crecimiento',
        'capital_trabajo': 'dias_cobro',
        'convertible': 'descuento_pct',
    }
    return defaults.get(tipo, 'flujos')


def _detectar_flujo_anio_sensible(texto_l: str) -> Optional[int]:
    """
    Detecta si se quiere variar un flujo de un año específico.
    Ej: 'sensibilidad del flujo del año 3' → retorna 3
    """
    m = PATRON_FLUJO_ANIO.search(texto_l)
    if m:
        return int(m.group(1))
    return None


def _son_factores_pct(valores: List[float]) -> bool:
    """Detecta si una lista de valores son factores porcentuales (ej: 0.6, 0.8, 1.0, 1.2)."""
    if not valores:
        return False
    # Son factores si todos están entre 0.1 y 2.0 y contienen 1.0
    todos_en_rango = all(0.1 <= v <= 2.0 for v in valores)
    contiene_uno = any(abs(v - 1.0) < 0.001 for v in valores)
    return todos_en_rango and contiene_uno


def _detectar_escenarios_discretos(texto_l: str) -> Optional[List[float]]:
    """
    Detecta listas de valores discretos para sensibilidad.
    Busca patrones como:
    - 'escenarios de 90k, 110k, 130k, 150k'
    - '(90000, 110000, 130000, 150000)'
    - 'valores: 12%, 18%, 24%, 30%'
    - 'con cap de 1.5M, 2M, 2.5M'
    - 'múltiplos de 4x, 6x, 8x, 10x'
    """
    # Buscar listas entre paréntesis
    for m in re.finditer(r'\(([^)]+)\)', texto_l):
        valores = _parsear_lista_valores(m.group(1))
        if valores and len(valores) >= 3:
            if not _son_factores_pct(valores):
                return valores

    # Buscar después de keywords de escenarios
    patrones_kw = [
        r'(?:escenarios?|valores?|opciones?|niveles?|rango)\s*(?:de|:)\s*(.+?)(?:\.|;|$)',
        r'(?:con|entre)\s+(?:cap|múltiplo|multiplo|tasa|descuento)\s*(?:de|:)?\s*(.+?)(?:\.|;|$)',
    ]

    for pat in patrones_kw:
        for m in re.finditer(pat, texto_l, re.IGNORECASE):
            valores = _parsear_lista_valores(m.group(1))
            if valores and len(valores) >= 3:
                if not _son_factores_pct(valores):
                    return valores

    # Buscar listas de múltiplos: "4x, 6x, 8x, 10x"
    mult_pattern = re.findall(r'(\d+(?:\.\d+)?)\s*[xX]', texto_l)
    if len(mult_pattern) >= 3:
        return [float(v) for v in mult_pattern]

    return None


def _parsear_lista_valores(texto: str) -> Optional[List[float]]:
    """
    Parsea una cadena con valores separados por comas.
    Soporta sufijos k, M, %, x.
    Retorna lista de valores float o None.
    """
    # Encontrar todos los números con posibles sufijos
    patron = re.compile(
        r'(-?\s*\$?\s*[\d.,]+)\s*([kKmM]{1,2}|mil(?:lones?)?|%|[xX])?'
    )
    matches = patron.findall(texto)
    if len(matches) < 2:
        return None

    valores = []
    es_pct = False
    for val_str, sufijo in matches:
        val = _parsear_numero(val_str.replace('$', '').replace(' ', ''))
        if val is None:
            continue
        sufijo_l = sufijo.lower().strip()
        if sufijo_l == 'k':
            val *= 1_000
        elif sufijo_l in ('m', 'mm') or sufijo_l.startswith('millon'):
            val *= 1_000_000
        elif sufijo_l == 'mil':
            val *= 1_000
        elif sufijo_l == '%':
            es_pct = True
        # x suffix: mantener valor como está (es un múltiplo)
        valores.append(val)

    if not valores:
        return None
    if es_pct:
        valores = [v / 100 for v in valores]
    return valores


def _detectar_variaciones(texto_l: str) -> Optional[List[float]]:
    """
    Extrae variaciones porcentuales mencionadas explícitamente.
    Ejemplo: "60%, 80%, 100%, 120%, 140%" → [-40, -20, 0, 20, 40] relativo a 100%
    O: "varía entre -30% y +30%"
    """
    # Patrón: rango "entre X% y Y%"
    rango_pat = re.compile(
        r'entre\s+([+-]?\d+)\s*%\s+y\s+([+-]?\d+)\s*%', re.IGNORECASE)
    m = rango_pat.search(texto_l)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        paso = max(1, abs(hi - lo) // 6)
        return list(range(lo, hi + 1, paso))

    # Patrón: lista de porcentajes como factores (60%, 80%, 100%, 120%)
    lista_pat = re.compile(r'(\d+)\s*%(?:\s*[,y]\s*(\d+)\s*%)+')
    m = lista_pat.search(texto_l)
    if m:
        todos = re.findall(r'(\d+)\s*%', texto_l[m.start():m.end() + 20])
        vals = [int(v) for v in todos]
        # Interpretar como factores relativos al 100%
        if 100 in vals:
            return [v - 100 for v in vals]

    # Patrón: variaciones explícitas como "+10%, +20%" o "-10%, -20%"
    var_pat = re.compile(r'([+-]\d+)\s*%')
    matches = var_pat.findall(texto_l)
    if len(matches) >= 2:
        variaciones = sorted(set(int(v) for v in matches))
        if 0 not in variaciones:
            variaciones = sorted(variaciones + [0])
        return variaciones

    return None
