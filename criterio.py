# ═══════════════════════════════════════════════════════════════
# criterio.py — Generador de Criterio / Conclusión Final
# Interpreta los resultados como lo haría una persona experta
# ═══════════════════════════════════════════════════════════════

from typing import Any, Dict, List, Optional


def generar(tipo: str, resultados: Dict, variables: Dict,
            faltantes: List[str], sensibilidad: Optional[Dict]) -> List[str]:
    """
    Genera una lista de conclusiones en lenguaje natural.
    Siempre retorna al menos un punto, incluso si faltan datos.
    """
    handlers = {
        'van_tir': _criterio_van_tir,
        'interes_simple': _criterio_interes,
        'interes_compuesto': _criterio_interes,
        'runway': _criterio_runway,
        'capital_trabajo': _criterio_capital_trabajo,
        'credito': _criterio_credito,
        'convertible': _criterio_convertible,
        'valor_terminal': _criterio_valor_terminal,
    }

    lineas: List[str] = []

    handler = handlers.get(tipo)
    if handler and resultados and 'error' not in resultados:
        lineas = handler(resultados, variables, sensibilidad)
    else:
        lineas.append("No fue posible realizar el cálculo completo.")

    # Agregar limitaciones por datos faltantes
    if faltantes:
        lineas.append("")
        lineas.append("Limitaciones del análisis:")
        for f in faltantes:
            lineas.append(f"  {f}")
        lineas.append("  Se recomienda proporcionar estos datos para un análisis completo.")

    # Agregar conclusión de sensibilidad si existe
    if sensibilidad and sensibilidad.get('variaciones'):
        sens_lines = _criterio_sensibilidad(tipo, sensibilidad)
        if sens_lines:
            lineas.append("")
            lineas.extend(sens_lines)

    return lineas


# ─── VAN / TIR ───────────────────────────────────────────────

def _criterio_van_tir(res: Dict, variables: Dict,
                       sens: Optional[Dict]) -> List[str]:
    van = res.get('van')
    tir = res.get('tir')
    tasa = res.get('tasa', 0)
    payback = res.get('payback')
    ir = res.get('indice_rentabilidad')
    periodos = res.get('periodos', 0)
    lineas = []

    if van is None:
        lineas.append("No se pudo calcular el VAN con los datos disponibles.")
        return lineas

    # Veredicto principal
    if van > 0:
        lineas.append(f"El proyecto ES VIABLE: genera un Valor Actual Neto positivo de ${van:,.2f}.")
        lineas.append("  Esto significa que el proyecto crea valor por encima del costo de capital.")
    else:
        lineas.append(f"El proyecto NO ES VIABLE: el VAN es negativo (${van:,.2f}).")
        lineas.append("  El proyecto destruiría valor respecto a simplemente invertir a la tasa de descuento.")

    # TIR vs tasa
    if tir is not None:
        if tir > tasa:
            margen = (tir - tasa) * 100
            lineas.append(f"La TIR ({tir*100:.2f}%) supera la tasa de descuento ({tasa*100:.2f}%) en {margen:.1f} puntos.")
            if margen > 10:
                lineas.append("  El margen de seguridad es amplio, lo que indica baja sensibilidad al riesgo.")
            else:
                lineas.append("  El margen de seguridad es ajustado; pequeños cambios podrían afectar la viabilidad.")
        else:
            lineas.append(f"La TIR ({tir*100:.2f}%) está por debajo de la tasa requerida ({tasa*100:.2f}%).")
            lineas.append("  El rendimiento del proyecto no compensa el riesgo asumido.")
    else:
        lineas.append("La TIR no pudo calcularse (posiblemente los flujos no cambian de signo).")

    # Payback
    if payback is not None:
        if payback <= periodos * 0.5:
            lineas.append(f"El período de recupero es de {payback:.1f} períodos: se recupera en la primera mitad del horizonte.")
        elif payback <= periodos:
            lineas.append(f"El período de recupero es de {payback:.1f} períodos, dentro del horizonte de inversión.")
        else:
            lineas.append(f"El período de recupero ({payback:.1f}) supera el horizonte de evaluación: el capital no se recupera.")
    else:
        lineas.append("El capital invertido no se recupera dentro del horizonte analizado.")

    # Índice de rentabilidad
    if ir is not None:
        if ir > 1:
            lineas.append(f"Por cada peso invertido, se obtienen ${ir:.2f} de valor presente (IR = {ir:.3f}).")
        else:
            lineas.append(f"El índice de rentabilidad ({ir:.3f}) es menor a 1: el proyecto no genera valor suficiente.")

    return lineas


# ─── Interés Simple / Compuesto ──────────────────────────────

def _criterio_interes(res: Dict, variables: Dict,
                       sens: Optional[Dict]) -> List[str]:
    capital = res.get('capital', 0)
    monto_f = res.get('monto_final', 0)
    interes = res.get('interes_total', 0)
    tasa = res.get('tasa', 0)
    periodos = res.get('periodos', 0)
    rendimiento = res.get('tasa_efectiva_total', 0)
    diferencia = res.get('diferencia_vs_simple')
    lineas = []

    lineas.append(f"Un capital de ${capital:,.2f} al {tasa*100:.2f}% anual durante {periodos:.0f} años")
    lineas.append(f"  crece hasta ${monto_f:,.2f}, generando ${interes:,.2f} de intereses.")
    lineas.append(f"  El rendimiento total sobre el capital es del {rendimiento*100:.2f}%.")

    if diferencia and diferencia > 0:
        lineas.append(f"Al capitalizar, se generan ${diferencia:,.2f} adicionales respecto al interés simple.")
        lineas.append("  Esto ilustra el efecto del interés compuesto en horizontes largos.")

    if periodos >= 10:
        lineas.append(f"Con {periodos:.0f} años, el efecto del tiempo es significativo: ")
        lineas.append(f"  el capital se multiplica {monto_f/capital:.2f}x.")

    return lineas


# ─── Runway ──────────────────────────────────────────────────

def _criterio_runway(res: Dict, variables: Dict,
                      sens: Optional[Dict]) -> List[str]:
    mes_q = res.get('mes_quiebre')
    flujo_neto = res.get('flujo_neto_mensual', 0)
    saldo = res.get('saldo', 0)
    gasto = res.get('gasto_mensual', 0)
    ingreso = res.get('ingreso_mensual', 0)
    tasa_caida = res.get('tasa_caida', 0)
    lineas = []

    if mes_q is None:
        lineas.append("La empresa es financieramente sostenible en el horizonte analizado (>120 meses).")
        if flujo_neto >= 0:
            lineas.append(f"  El flujo neto mensual es positivo (${flujo_neto:,.2f}): ingresos cubren gastos.")
        else:
            lineas.append("  Los ingresos son menores a los gastos, pero el saldo inicial es suficiente.")
    else:
        lineas.append(f"La empresa quedará sin liquidez en el mes {mes_q}.")
        if mes_q <= 3:
            lineas.append("  SITUACIÓN CRÍTICA: el runway es menor a 3 meses. Se requiere acción inmediata.")
        elif mes_q <= 6:
            lineas.append("  SITUACIÓN URGENTE: menos de 6 meses. Se debe buscar financiamiento o reducir costos.")
        elif mes_q <= 12:
            lineas.append("  Hay tiempo limitado. Se recomienda buscar ingresos o capital adicional.")
        else:
            lineas.append("  El horizonte es razonable para buscar alternativas estratégicas.")

    if flujo_neto < 0:
        deficit = abs(flujo_neto)
        lineas.append(f"El déficit mensual es de ${deficit:,.2f}. Para ser sostenible, debe reducirse a cero.")

    if tasa_caida > 0:
        lineas.append(f"Con una caída de ingresos del {tasa_caida*100:.1f}% mensual, el deterioro se acelera con el tiempo.")

    return lineas


# ─── Capital de Trabajo ──────────────────────────────────────

def _criterio_capital_trabajo(res: Dict, variables: Dict,
                               sens: Optional[Dict]) -> List[str]:
    ciclo = res.get('ciclo_caja', 0)
    cap_nec = res.get('capital_necesario')
    dc = res.get('dias_cobro', 0)
    dp = res.get('dias_pago', 0)
    di = res.get('dias_inventario', 0)
    lineas = []

    lineas.append(f"El ciclo de caja de la empresa es de {ciclo:.0f} días.")

    if ciclo < 0:
        lineas.append("  FAVORABLE: la empresa cobra antes de pagar a proveedores. Genera liquidez natural.")
    elif ciclo < 30:
        lineas.append("  ACEPTABLE: el ciclo es corto, el capital de trabajo necesario es bajo.")
    elif ciclo < 60:
        lineas.append("  MODERADO: se requiere capital de trabajo para financiar el ciclo operativo.")
    else:
        lineas.append("  DESFAVORABLE: ciclo largo. La empresa financia a sus clientes con capital propio.")

    if dp > dc:
        dias_ventaja = dp - dc
        lineas.append(f"  Los proveedores dan {dias_ventaja:.0f} días más de los que tarda en cobrar: favorable.")
    elif dc > dp:
        dias_gap = dc - dp
        lineas.append(f"  Cobra {dias_gap:.0f} días después de tener que pagar: genera necesidad de capital.")

    if di > 0:
        lineas.append(f"  Los {di:.0f} días de inventario representan el costo de almacenaje en el ciclo.")

    if cap_nec is not None:
        lineas.append(f"Se necesitan ${cap_nec:,.2f} de capital de trabajo para financiar un ciclo completo.")

    return lineas


# ─── Crédito ─────────────────────────────────────────────────

def _criterio_credito(res: Dict, variables: Dict,
                       sens: Optional[Dict]) -> List[str]:
    monto = res.get('monto', 0)
    cuota = res.get('cuota', 0)
    total = res.get('total_pagado', 0)
    total_int = res.get('total_intereses', 0)
    tasa_anual = res.get('tasa_anual', 0)
    num_cuotas = res.get('num_cuotas', 0)
    periodo_label = res.get('periodo_label', 'período')
    lineas = []

    sobrecosto = (total_int / monto * 100) if monto else 0

    lineas.append(f"Por un préstamo de ${monto:,.2f}, la cuota {periodo_label} es de ${cuota:,.2f}.")
    lineas.append(f"Al finalizar las {num_cuotas} cuotas, se habrá pagado ${total:,.2f} en total.")
    lineas.append(f"Los intereses representan ${total_int:,.2f} ({sobrecosto:.1f}% del monto original).")

    if sobrecosto > 50:
        lineas.append("  El costo financiero es elevado. Se recomienda evaluar alternativas de menor tasa.")
    elif sobrecosto > 25:
        lineas.append("  El costo financiero es moderado, consistente con tasas de mercado típicas.")
    else:
        lineas.append("  El costo financiero es razonable.")

    lineas.append(f"La tasa anual del {tasa_anual*100:.2f}% implica una tasa {periodo_label} de {res['tasa_periodo']*100:.4f}%.")

    return lineas


# ─── Nota Convertible ────────────────────────────────────────

def _criterio_convertible(res: Dict, variables: Dict,
                           sens: Optional[Dict]) -> List[str]:
    dilucion = res.get('dilucion_pct', 0)
    ownership = res.get('ownership_fundador', 0)
    metodo = res.get('metodo_conversion', '')
    val_efectiva = res.get('valoracion_efectiva', 0)
    val_cap = res.get('valuation_cap', 0)
    val_pre = res.get('valoracion_pre', 0)
    lineas = []

    lineas.append(f"La nota convierte usando el método '{metodo}' (el más favorable para el inversor).")
    lineas.append(f"  Valoración efectiva de conversión: ${val_efectiva:,.2f}.")

    if dilucion < 10:
        lineas.append(f"La dilución del {dilucion:.2f}% es baja: el fundador retiene {ownership:.2f}% de la empresa.")
    elif dilucion < 20:
        lineas.append(f"La dilución del {dilucion:.2f}% es moderada. El fundador conserva {ownership:.2f}%.")
    else:
        lineas.append(f"La dilución del {dilucion:.2f}% es significativa. El fundador retiene {ownership:.2f}%.")

    if metodo == 'Cap' and val_cap < val_pre:
        diff = val_pre - val_cap
        lineas.append(f"  El cap está ${diff:,.2f} por debajo de la valoración actual: protege al inversor.")
    elif metodo == 'Descuento':
        lineas.append("  El descuento resultó más favorable que el cap: el inversor obtiene una rebaja adicional.")

    return lineas


# ─── Valor Terminal ──────────────────────────────────────────

def _criterio_valor_terminal(res: Dict, variables: Dict,
                              sens: Optional[Dict]) -> List[str]:
    vt_p = res.get('vt_perpetuidad')
    vt_m = res.get('vt_multiplo')
    g = res.get('tasa_crecimiento', 0)
    r = res.get('tasa_descuento', 0)
    flujo_f = res.get('flujo_final', 0)
    lineas = []

    if vt_p is not None:
        lineas.append(f"El Valor Terminal por perpetuidad creciente (Gordon) es de ${vt_p:,.2f}.")
        lineas.append(f"  Asume que el negocio crece al {g*100:.2f}% anual de forma perpetua.")
        spread = (r - g) * 100
        lineas.append(f"  El spread entre tasa de descuento y crecimiento es de {spread:.2f} puntos.")
        if spread < 3:
            lineas.append("  Con un spread tan estrecho, el valor terminal es muy sensible a variaciones en g o r.")
        if vt_p > flujo_f * 20:
            lineas.append("  El valor terminal representa una parte muy significativa del valor total del negocio.")

    if vt_m is not None:
        multiplo = res.get('multiplo', 0)
        lineas.append(f"El Valor Terminal por múltiplo ({multiplo}x) asciende a ${vt_m:,.2f}.")
        if vt_p is not None:
            diff = abs(vt_p - vt_m) / max(vt_p, vt_m) * 100
            if diff < 10:
                lineas.append("  Ambos métodos son consistentes entre sí (diferencia < 10%). Mayor confianza.")
            else:
                mayor = "perpetuidad" if vt_p > vt_m else "múltiplo"
                lineas.append(f"  Los métodos divergen {diff:.0f}%. El método de {mayor} es más conservador.")

    if vt_p is None and vt_m is None:
        lineas.append("No fue posible calcular el valor terminal con los datos proporcionados.")

    return lineas


# ─── Criterio de Sensibilidad ─────────────────────────────────

def _criterio_sensibilidad(tipo: str, sens: Dict) -> List[str]:
    filas = sens.get('variaciones', [])
    var = sens.get('variable', '')
    if not filas:
        return []

    lineas = [f"Análisis de sensibilidad sobre '{var}':"]

    if tipo == 'van_tir':
        viables = [f for f in filas if f.get('viable')]
        no_viables = [f for f in filas if not f.get('viable')]

        if len(viables) == len(filas):
            lineas.append("  El proyecto es viable en todos los escenarios analizados.")
        elif len(no_viables) == len(filas):
            lineas.append("  El proyecto no es viable en ningún escenario. Se recomienda replantear.")
        else:
            pct_min_viable = min(f['variacion_pct'] for f in viables)
            lineas.append(f"  El proyecto es viable con variaciones de {pct_min_viable:+.0f}% o más en '{var}'.")
            if pct_min_viable >= 0:
                lineas.append("  Solo es viable si la variable no cae: margen de seguridad inexistente.")
            elif pct_min_viable >= -10:
                lineas.append("  Margen de seguridad ajustado: cualquier deterioro moderado elimina la viabilidad.")
            else:
                lineas.append(f"  Tolera una caída de hasta {abs(pct_min_viable):.0f}% en '{var}' y sigue siendo viable.")

        # Punto de equilibrio entre filas
        for i in range(len(filas) - 1):
            v1 = filas[i].get('van', 0) or 0
            v2 = filas[i + 1].get('van', 0) or 0
            if v1 * v2 < 0:
                pct1 = filas[i]['variacion_pct']
                pct2 = filas[i + 1]['variacion_pct']
                cruce = pct1 + (pct2 - pct1) * abs(v1) / (abs(v1) + abs(v2))
                lineas.append(f"  Punto crítico estimado: '{var}' debe caer más de {cruce:.1f}% para que el VAN sea negativo.")
                break

    elif tipo == 'runway':
        sostenibles = [f for f in filas if f.get('viable')]
        if sostenibles:
            lineas.append(f"  Es sostenible en {len(sostenibles)} de {len(filas)} escenarios.")
        else:
            meses_max = max((f.get('meses') or 0) for f in filas)
            lineas.append(f"  En el mejor escenario, la empresa sobrevive {meses_max} meses.")

    return lineas
