# ═══════════════════════════════════════════════════════════════
# calculo.py — Módulo de Cálculos Financieros
# Funciones matemáticas puras para análisis financiero
# Sin dependencias externas
# ═══════════════════════════════════════════════════════════════


# ─── Indicadores Financieros Clásicos ─────────────────────────

def calcular_van(inversion_inicial, flujos_netos, tasa_descuento):
    """
    Valor Actual Neto (VAN / NPV).
    VAN = -I₀ + Σ(Fₜ / (1 + r)^t)
    """
    van = -inversion_inicial
    for t, flujo in enumerate(flujos_netos, 1):
        van += flujo / (1 + tasa_descuento) ** t
    return van


def calcular_tir(inversion_inicial, flujos_netos, precision=0.00001, max_iter=50000):
    """
    Tasa Interna de Retorno (TIR / IRR) por método de bisección.
    La TIR es la tasa que hace VAN = 0.
    """
    def van_a_tasa(r):
        if r <= -1:
            return float('inf')
        resultado = -inversion_inicial
        for t, flujo in enumerate(flujos_netos, 1):
            resultado += flujo / (1 + r) ** t
        return resultado

    lo, hi = -0.50, 10.0
    van_lo = van_a_tasa(lo)
    van_hi = van_a_tasa(hi)

    if van_lo * van_hi > 0:
        hi = 100.0
        van_hi = van_a_tasa(hi)
        if van_lo * van_hi > 0:
            return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        van_mid = van_a_tasa(mid)
        if abs(van_mid) < precision or abs(hi - lo) < precision:
            return mid
        if van_lo * van_mid < 0:
            hi = mid
        else:
            lo = mid
            van_lo = van_mid

    return (lo + hi) / 2


def calcular_periodo_recuperacion(inversion_inicial, flujos_netos):
    """Período de Recuperación (Payback Period)."""
    acumulado = 0
    for t, flujo in enumerate(flujos_netos):
        acumulado += flujo
        if acumulado >= inversion_inicial:
            if flujo != 0:
                excedente = acumulado - inversion_inicial
                return round(t + 1 - (excedente / flujo), 2)
            return t + 1
    return None


def calcular_indice_rentabilidad(inversion_inicial, van):
    """
    Índice de Rentabilidad (IR).
    IR > 1: rentable | IR < 1: no rentable
    """
    if inversion_inicial == 0:
        return float('inf')
    return (van + inversion_inicial) / inversion_inicial


def calcular_valor_presente(flujo, tasa, periodo):
    """Valor presente de un flujo futuro individual."""
    if tasa <= -1:
        return float('inf')
    return flujo / (1 + tasa) ** periodo


# ─── Caso 1: Bootstrapping / Runway ──────────────────────────

def calcular_runway(saldo_inicial, gasto_mensual, ingreso_mensual_inicial,
                    tasa_caida_ingreso=0.0, meses_max=120):
    """
    Calcula meses de supervivencia (runway) con ingresos que pueden caer.
    Retorna: (lista_saldos, lista_ingresos, mes_quiebre o None)
    """
    saldos = [saldo_inicial]
    ingresos_mes = [ingreso_mensual_inicial]
    ingreso = ingreso_mensual_inicial

    for mes in range(1, meses_max + 1):
        if mes > 1:
            ingreso = ingreso * (1 - tasa_caida_ingreso)
        nuevo_saldo = saldos[-1] + ingreso - gasto_mensual
        saldos.append(round(nuevo_saldo, 2))
        ingresos_mes.append(round(ingreso, 2))
        if nuevo_saldo <= 0:
            return saldos, ingresos_mes, mes

    return saldos, ingresos_mes, None


# ─── Caso 3: Nota Convertible ────────────────────────────────

def calcular_dilucion_convertible(inversion, valuation_cap, valoracion_pre_ronda,
                                   descuento_pct):
    """
    Dilución del fundador en nota convertible.
    Convierte al menor entre: cap o valoración×(1-descuento).
    """
    val_con_descuento = valoracion_pre_ronda * (1 - descuento_pct / 100)
    val_efectiva = min(valuation_cap, val_con_descuento)
    metodo = "Cap" if valuation_cap <= val_con_descuento else "Descuento"

    if val_efectiva <= 0:
        return {'valoracion_efectiva': 0, 'dilucion_pct': 100,
                'ownership_fundador': 0, 'valoracion_post': inversion,
                'metodo_conversion': metodo}

    dilucion = (inversion / (val_efectiva + inversion)) * 100
    return {
        'valoracion_efectiva': val_efectiva,
        'dilucion_pct': dilucion,
        'ownership_fundador': 100 - dilucion,
        'valoracion_post': val_efectiva + inversion,
        'metodo_conversion': metodo
    }


# ─── Caso 4: Ciclo de Caja ───────────────────────────────────

def calcular_ciclo_caja(dias_cobro, dias_inventario, dias_pago):
    """Ciclo de Conversión de Efectivo = DCC + DCI - DCP"""
    return dias_cobro + dias_inventario - dias_pago


def calcular_capital_trabajo_necesario(costo_diario, ciclo_caja):
    """Capital de trabajo = Costo diario × Ciclo de caja"""
    return costo_diario * max(ciclo_caja, 0)


# ─── Caso 6: Valor Terminal ──────────────────────────────────

def calcular_valor_terminal_perpetuidad(flujo_ultimo, tasa_crecimiento, tasa_descuento):
    """Valor Terminal por Perpetuidad Creciente (Gordon). VT = FCF×(1+g)/(r-g)"""
    if tasa_descuento <= tasa_crecimiento:
        return float('inf')
    return flujo_ultimo * (1 + tasa_crecimiento) / (tasa_descuento - tasa_crecimiento)


def calcular_valor_terminal_multiplo(metrica_final, multiplo):
    """Valor Terminal por Múltiplos. VT = Métrica × Múltiplo"""
    return metrica_final * multiplo


# ─── Caso 8: Interés Simple vs Compuesto ─────────────────────

def calcular_interes_simple(capital, tasa_anual, periodos_anios):
    """I. Simple: M = C×(1 + r×t). Retorna (monto, interes)"""
    interes = capital * tasa_anual * periodos_anios
    return capital + interes, interes


def calcular_interes_compuesto(capital, tasa_anual, periodos_anios,
                                capitalizaciones=1):
    """I. Compuesto: M = C×(1+r/n)^(n×t). Retorna (monto, interes)"""
    n = capitalizaciones
    monto = capital * (1 + tasa_anual / n) ** (n * periodos_anios)
    return monto, monto - capital


# ─── Caso 5: Crédito ─────────────────────────────────────────

def calcular_cuota_prestamo(monto, tasa_periodo, num_cuotas):
    """Cuota con sistema francés."""
    if tasa_periodo == 0:
        return monto / num_cuotas if num_cuotas > 0 else 0
    factor = (1 + tasa_periodo) ** num_cuotas
    return monto * (tasa_periodo * factor) / (factor - 1)


def generar_tabla_amortizacion(monto, tasa_periodo, num_cuotas):
    """Tabla de amortización. Retorna (tabla[], total_intereses)"""
    cuota = calcular_cuota_prestamo(monto, tasa_periodo, num_cuotas)
    tabla = []
    saldo = monto
    total_int = 0
    for i in range(1, num_cuotas + 1):
        interes_p = saldo * tasa_periodo
        capital_p = cuota - interes_p
        saldo -= capital_p
        total_int += interes_p
        tabla.append({'periodo': i, 'cuota': round(cuota, 2),
                      'interes': round(interes_p, 2),
                      'capital': round(capital_p, 2),
                      'saldo': round(max(0, saldo), 2)})
    return tabla, round(total_int, 2)
