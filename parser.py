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
        'keywords': ['interés simple', 'interes simple'],
        'peso': 5,
    },
    'interes_compuesto': {
        'nombre': 'Interés Compuesto',
        'keywords': [
            'interés compuesto', 'interes compuesto',
            'capitalización', 'capitalizacion', 'capitaliza',
        ],
        'peso': 5,
    },
    'runway': {
        'nombre': 'Runway / Supervivencia',
        'keywords': [
            'runway', 'supervivencia', 'burn rate', 'gasto mensual', 'saldo inicial',
            'cuánto tiempo', 'cuanto tiempo', 'cuántos meses', 'cuantos meses',
            'sobrevivir', 'aguantar', 'quedarse sin dinero', 'quedarse sin caja',
        ],
        'peso': 3,
    },
    'capital_trabajo': {
        'nombre': 'Capital de Trabajo',
        'keywords': [
            'capital de trabajo', 'ciclo de caja', 'ciclo operativo',
            'días de cobro', 'dias de cobro', 'días de inventario', 'dias de inventario',
            'días de pago', 'dias de pago', 'ciclo de conversión', 'ciclo de conversion',
        ],
        'peso': 4,
    },
    'credito': {
        'nombre': 'Crédito / Préstamo',
        'keywords': [
            'préstamo', 'prestamo', 'crédito', 'credito', 'cuota mensual',
            'amortización', 'amortizacion', 'financiamiento', 'hipoteca',
            'tabla de amortización', 'sistema francés', 'sistema frances',
        ],
        'peso': 3,
    },
    'convertible': {
        'nombre': 'Nota Convertible',
        'keywords': [
            'nota convertible', 'convertible', 'valuation cap', 'dilución del fundador',
            'dilucion del fundador', 'ronda de inversión', 'ronda serie',
            'descuento de conversión', 'descuento de conversion',
        ],
        'peso': 4,
    },
    'valor_terminal': {
        'nombre': 'Valor Terminal',
        'keywords': [
            'valor terminal', 'valor residual', 'perpetuidad', 'gordon',
            'múltiplo de salida', 'multiplo de salida', 'exit multiple',
            'tasa de crecimiento perpetuo',
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
      'inversión es', 'inversion es', 'cuesta', 'vale'], 'inversion', None),

    # Tasa de descuento / interés (porcentaje) — poner primero y con frases largas
    (['tasa de descuento del', 'tasa de descuento de', 'tasa de descuento es',
      'tasa de descuento', 'tasa de interés del', 'tasa de interés de',
      'tasa de interes del', 'tasa de interes de', 'tasa de interés es', 'tasa de interes es',
      'tasa anual de', 'tasa anual del', 'tasa anual es', 'costo de capital de', 'costo de capital es',
      'wacc de', 'wacc es', 'tasa de rendimiento', 'tasa del', 'tasa de'], 'tasa', 'pct'),

    # Flujos de caja — incluye formas verbales
    (['flujo de caja de', 'flujos de caja de', 'flujo anual de', 'flujos anuales de',
      'flujo neto de', 'flujos netos de', 'ingreso anual de', 'ingresos anuales de',
      'beneficio anual de', 'genera', 'generará', 'generamos', 'recibirá por año',
      'recibo', 'recibiré', 'recibimos', 'recibe', 'recibir',
      'retorno anual de', 'flujo periódico de', 'flujo periodico de',
      'gana', 'ganaremos', 'produce', 'producirá',
      'flujos de', 'flujo de'], 'flujo', None),

    # Períodos / años
    (['durante', 'por un plazo de', 'en un plazo de', 'plazo de',
      'horizonte de', 'en un período de', 'en un periodo de',
      'durante un período de', 'durante un periodo de',
      'anuales por', 'mensuales por'], 'periodos', None),

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
      'tiene en caja', 'saldo de'], 'saldo', None),

    # Runway: gasto mensual
    (['gasto mensual de', 'gastos mensuales de', 'costo mensual de',
      'burn rate de', 'egresos mensuales de', 'erogación mensual de'], 'gasto_mensual', None),

    # Runway: ingreso mensual
    (['ingreso mensual de', 'ingresos mensuales de',
      'ingreso mensual proyectado', 'ingresos mensuales proyectados',
      'ingresos mensuales estimados', 'ingreso mensual estimado',
      'ingresos proyectados de', 'ingreso proyectado de',
      'ingresos proyectados', 'ingreso proyectado',
      'ingresos mensuales', 'ingreso mensual',
      'recibe mensualmente', 'cobra mensualmente',
      'vende mensualmente'], 'ingreso_mensual', None),

    # Runway: tasa de caída
    (['tasa de caída', 'tasa de caida', 'caída mensual de', 'caida mensual de',
      'decrecimiento mensual de'], 'tasa_caida', 'pct'),

    # Crédito: cuotas
    (['número de cuotas', 'numero de cuotas', 'cantidad de cuotas',
      'en cuotas', 'en meses', 'plazo en meses', 'plazo de cuotas',
      'cuotas mensuales de'], 'num_cuotas', None),

    # Capital de trabajo: días de cobro
    (['días de cobro', 'dias de cobro', 'plazo de cobro de',
      'días en cobrar', 'dias en cobrar', 'período de cobro de',
      'periodo de cobro de'], 'dias_cobro', None),

    # Capital de trabajo: días de inventario
    (['días de inventario', 'dias de inventario', 'rotación de inventario de',
      'días en inventario', 'dias en inventario'], 'dias_inventario', None),

    # Capital de trabajo: días de pago
    (['días de pago', 'dias de pago', 'plazo de pago de',
      'días para pagar', 'dias para pagar', 'crédito de proveedores de',
      'credito de proveedores de'], 'dias_pago', None),

    # Capital de trabajo: costo diario
    (['costo diario de', 'egresos diarios de', 'costo promedio diario de',
      'gasto diario de'], 'costo_diario', None),

    # Nota convertible
    (['valuation cap de', 'valuation cap es', 'cap de valoración de',
      'cap de valoracion de', 'cap de', 'límite de valoración de',
      'limite de valoracion de'], 'valuation_cap', None),
    (['valoración pre-money de', 'valoracion pre-money de',
      'valoración pre de', 'valoracion pre de',
      'pre-money de', 'valoración de la empresa de',
      'valoracion de la empresa de'], 'valoracion_pre', None),
    (['descuento de conversión de', 'descuento de conversion de',
      'con un descuento de', 'descuento de conversión', 'descuento de conversion'], 'descuento_pct', None),

    # Valor terminal
    (['tasa de crecimiento de', 'tasa de crecimiento es',
      'tasa g de', 'crecimiento perpetuo de'], 'tasa_crecimiento', 'pct'),
    (['múltiplo de', 'multiplo de', 'exit multiple de',
      'múltiplo de salida de', 'multiplo de salida de'], 'multiplo', None),
    (['flujo del último año', 'flujo final de', 'flujo del año n de',
      'fcf final de', 'flujo del último período de'], 'flujo_final', None),

    # Ingresos / costos genéricos (para sensibilidad)
    (['ingresos de', 'ingreso de', 'ventas de'], 'ingresos', None),
    (['costos de', 'costo de', 'gastos de', 'gasto de'], 'costos', None),
]

# ─── Palabras clave de sensibilidad ──────────────────────────
KEYWORDS_SENSIBILIDAD = [
    'sensibilidad', 'sensible', 'sensible a', 'análisis de sensibilidad',
    'analisis de sensibilidad', 'varía', 'varia', 'variando', 'variar',
    'si cambia', 'si aumenta', 'si disminuye', 'si baja', 'si sube',
    'qué pasa si', 'que pasa si', 'escenario pesimista', 'escenario optimista',
    'escenarios', 'impacto de', 'efecto de',
]

# Variables que pueden ser sensibles con sus nombres canónicos
VARIABLE_SENSIBILIDAD = {
    'ingresos': ['ingreso', 'ingresos', 'ventas', 'flujos', 'flujo de caja'],
    'costos': ['costo', 'costos', 'gasto', 'gastos', 'egresos'],
    'tasa': ['tasa', 'tasa de descuento', 'tasa de interés', 'tasa de interes', 'wacc'],
    'inversion': ['inversión', 'inversion', 'capital inicial'],
    'tasa_caida': ['tasa de caída', 'tasa de caida', 'caída de ingresos'],
}


# ════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ════════════════════════════════════════════════════════════════

def analizar_texto(texto: str) -> Dict[str, Any]:
    """
    Analiza el texto en lenguaje natural y retorna un diccionario con:
      - tipo: str (clave del tipo de análisis)
      - tipo_nombre: str (nombre legible)
      - variables: dict {nombre: valor}
      - sensibilidad: dict | None
      - texto_original: str
    """
    texto_l = texto.lower()

    tipo, tipo_nombre = _detectar_tipo(texto_l)
    variables = _extraer_variables(texto_l, tipo)
    sensibilidad = _detectar_sensibilidad(texto_l, tipo, variables)

    return {
        'tipo': tipo,
        'tipo_nombre': tipo_nombre,
        'variables': variables,
        'sensibilidad': sensibilidad,
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
                score += peso
        puntajes[tipo_key] = score

    mejor = max(puntajes, key=lambda k: puntajes[k])
    if puntajes[mejor] == 0:
        mejor = 'van_tir'  # default

    return mejor, TIPOS[mejor]['nombre']


# ════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE NÚMEROS CON CONTEXTO
# ════════════════════════════════════════════════════════════════

def _encontrar_numeros(texto_l: str) -> List[Dict[str, Any]]:
    """
    Encuentra todos los números en el texto con su contexto.
    Retorna lista de dicts con: valor, contexto_antes, es_pct, unidad, pos_inicio
    """
    # Patrón: número con separadores opcionales de miles/decimales
    patron = re.compile(
        r'(?<!\w)'                                  # no precedido por letra
        r'(\$\s*)?'                                  # signo $ opcional
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?'       # número con separadores
        r'|\d+(?:[.,]\d+)?)'                         # o número simple
        r'\s*'
        r'(mil(?:lones?)?|%|años?|meses?|períodos?|periodos?|cuotas?)?'
        r'(?!\w)',
        re.IGNORECASE
    )

    resultados = []
    for m in patron.finditer(texto_l):
        raw_num = m.group(2)
        unidad = (m.group(3) or '').strip().lower()
        tiene_peso = bool(m.group(1))

        valor = _parsear_numero(raw_num)
        if valor is None:
            continue

        # Aplicar multiplicador de unidad
        if unidad.startswith('millon'):
            valor *= 1_000_000
        elif unidad == 'mil':
            valor *= 1_000

        # Determinar si es porcentaje
        es_pct = unidad == '%'
        # También detectar "por ciento" justo después
        resto = texto_l[m.end():m.end() + 15]
        if 'por ciento' in resto or 'porciento' in resto:
            es_pct = True

        # Contexto: 90 caracteres antes
        inicio = m.start()
        ctx_inicio = max(0, inicio - 90)
        contexto_antes = texto_l[ctx_inicio:inicio].strip()

        unidades_tiempo = ('años', 'año', 'meses', 'mes',
                           'períodos', 'periodos', 'período', 'periodo')
        unidades_cuota = ('cuotas', 'cuota')

        resultados.append({
            'valor': valor,
            'es_pct': es_pct,
            'unidad_tiempo': unidad in unidades_tiempo,
            'unidad_cuota': unidad in unidades_cuota,
            'tiene_peso': tiene_peso,
            'contexto_antes': contexto_antes,
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

    # Encontrar el keyword más cercano al número (mayor posición en ctx)
    mejor_pos = -1
    mejor_var = None

    for keywords, var_name, _ in CONTEXTO_MAP:
        for kw in keywords:
            pos = ctx.rfind(kw)   # rfind = última aparición = más cercana al número
            if pos > mejor_pos:
                mejor_pos = pos
                mejor_var = var_name

    # Heurísticas por unidad: si el número tiene unidad de tiempo/cuota,
    # priorizar eso a menos que el contexto inmediato sea muy específico
    if num['unidad_cuota']:
        return 'num_cuotas'

    if num['unidad_tiempo']:
        # Solo usar el match de contexto si es muy cercano al número (últimos 20 chars)
        ctx_cercano = ctx[-20:] if len(ctx) > 20 else ctx
        for keywords, var_name, _ in CONTEXTO_MAP:
            if var_name == 'periodos':
                continue
            for kw in keywords:
                if kw in ctx_cercano:
                    return var_name
        return 'periodos'

    if mejor_var is not None:
        return mejor_var

    if num['es_pct'] and tipo in ('van_tir', 'credito', 'valor_terminal',
                                   'interes_simple', 'interes_compuesto'):
        return 'tasa'

    # Números monetarios sin contexto → asignación posicional posterior
    valor = num['valor']
    if num['tiene_peso'] or (valor >= 100 and not num['es_pct']):
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
            if 'valoracion_pre' not in variables and montos_sin_ctx:
                variables['valoracion_pre'] = montos_sin_ctx[0]

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

    return variables


def _extraer_flujos_por_periodo(texto_l: str) -> Optional[List[float]]:
    """
    Detecta patrones como 'año 1: $X, año 2: $Y' o 'período 1: X'.
    Retorna lista ordenada de flujos o None si no encuentra el patrón.
    """
    patron = re.compile(
        r'(?:año|periodo|período|mes)\s+(\d+)\s*[:\-]\s*\$?\s*([\d.,]+)'
        r'(?:\s*(?:mil(?:lones?)?)?)',
        re.IGNORECASE
    )
    matches = patron.findall(texto_l)
    if len(matches) < 2:
        return None

    try:
        pares = sorted([(int(p), _parsear_numero(v)) for p, v in matches])
        return [v for _, v in pares if v is not None]
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════
# DETECCIÓN DE SENSIBILIDAD
# ════════════════════════════════════════════════════════════════

def _detectar_sensibilidad(texto_l: str, tipo: str,
                            variables: Dict) -> Optional[Dict]:
    """
    Detecta si se solicita análisis de sensibilidad.
    Retorna dict con variable_sensible, variaciones, o None.
    """
    # Verificar si hay keywords de sensibilidad
    hay_kw = any(kw in texto_l for kw in KEYWORDS_SENSIBILIDAD)

    # Para VAN/TIR, siempre hacer sensibilidad sobre flujos por defecto
    hacer_sens = hay_kw or tipo == 'van_tir'
    if not hacer_sens:
        return None

    # Detectar variable sensible mencionada explícitamente
    var_sensible = _detectar_variable_sensible(texto_l, tipo, variables)

    # Detectar variaciones porcentuales mencionadas
    variaciones = _detectar_variaciones(texto_l)
    if not variaciones:
        variaciones = [-30, -20, -10, 0, 10, 20, 30]  # default

    return {
        'variable': var_sensible,
        'variaciones_pct': variaciones,
        'explicita': hay_kw,
    }


def _detectar_variable_sensible(texto_l: str, tipo: str,
                                  variables: Dict) -> str:
    """Identifica qué variable se quiere variar."""
    for var_canon, aliases in VARIABLE_SENSIBILIDAD.items():
        for alias in aliases:
            # Buscar "sensibilidad a X" o "si X cambia" etc.
            patrones_ctx = [
                f'sensibilidad a {alias}', f'sensibilidad de {alias}',
                f'sensible a {alias}', f'si {alias}', f'variar {alias}',
                f'variando {alias}', f'impacto de {alias}',
            ]
            for p in patrones_ctx:
                if p in texto_l:
                    return var_canon

    # Default por tipo
    defaults = {
        'van_tir': 'flujos',
        'runway': 'tasa_caida',
        'credito': 'tasa',
        'interes_simple': 'tasa',
        'interes_compuesto': 'tasa',
        'valor_terminal': 'tasa_crecimiento',
        'capital_trabajo': 'dias_cobro',
        'convertible': 'descuento_pct',
    }
    return defaults.get(tipo, 'flujos')


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
