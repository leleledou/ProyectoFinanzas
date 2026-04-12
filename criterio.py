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

    # Veredicto principal
    if van is None:
        lineas.append("No se pudo calcular el VAN con los datos disponibles (falta tasa de descuento).")
    elif van > 0:
        lineas.append(f"El proyecto ES VIABLE: genera un Valor Actual Neto positivo de ${van:,.2f}.")
        lineas.append("  Esto significa que el proyecto crea valor por encima del costo de capital.")
    else:
        lineas.append(f"El proyecto NO ES VIABLE: el VAN es negativo (${van:,.2f}).")
        lineas.append("  El proyecto destruiría valor respecto a simplemente invertir a la tasa de descuento.")

    # TIR vs tasa
    if tir is not None:
        if tasa and tasa > 0:
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
            lineas.append(f"La TIR del proyecto es {tir*100:.2f}%.")
            lineas.append("  Sin tasa de descuento explícita, compare este rendimiento con su costo de capital.")
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

    tasa_simp_ref = res.get('tasa_simple_ref')
    if tasa_simp_ref and abs(tasa_simp_ref - tasa) > 0.001:
        # Comparación explícita: tasas diferentes para simple y compuesto
        monto_s = res.get('monto_simple_ref', 0)
        interes_s = res.get('interes_simple_ref', 0)
        lineas.append(f"Comparación de ofertas a {periodos:.0f} años:")
        lineas.append(f"  Interés SIMPLE al {tasa_simp_ref*100:.2f}% anual:")
        lineas.append(f"    Monto final: ${monto_s:,.2f} | Interés: ${interes_s:,.2f}")
        lineas.append(f"  Interés COMPUESTO al {tasa*100:.2f}% anual:")
        lineas.append(f"    Monto final: ${monto_f:,.2f} | Interés: ${interes:,.2f}")
        diff = monto_s - monto_f
        if diff > 0:
            lineas.append(f"  El interés simple paga ${diff:,.2f} MÁS. Conviene la oferta simple.")
        else:
            lineas.append(f"  El interés compuesto paga ${abs(diff):,.2f} MÁS. Conviene el compuesto.")
    else:
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
    es_discreto = sens.get('es_discreto', False)
    if not filas:
        return []

    if es_discreto:
        return _criterio_sens_discreto(tipo, sens)

    lineas = [f"Análisis de sensibilidad sobre '{var}':"]

    if tipo == 'van_tir':
        filas_con_van = [f for f in filas if f.get('van') is not None]
        if not filas_con_van:
            tirs = [f.get('tir') for f in filas if f.get('tir') is not None]
            if tirs:
                lineas.append(f"  TIR varía entre {min(tirs)*100:.2f}% y {max(tirs)*100:.2f}%.")
                lineas.append("  (Sin tasa de descuento provista, no se calcula VAN por escenario.)")
            return lineas

        filas = filas_con_van
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

    elif tipo == 'convertible':
        dils = [f['dilucion_pct'] for f in filas]
        min_dil = min(dils)
        max_dil = max(dils)
        lineas.append(f"  La dilución varía entre {min_dil:.2f}% y {max_dil:.2f}%.")
        owns = [f['ownership_fundador'] for f in filas]
        min_own = min(owns)
        if min_own < 65:
            lineas.append(f"  ALERTA: en el peor escenario, el fundador retiene solo {min_own:.2f}%.")
        else:
            lineas.append(f"  En todos los escenarios, el fundador retiene al menos {min_own:.2f}%.")

    elif tipo == 'capital_trabajo':
        ciclos = [f['ciclo_caja'] for f in filas]
        min_c = min(ciclos)
        max_c = max(ciclos)
        lineas.append(f"  El ciclo de caja varía entre {min_c:.0f} y {max_c:.0f} días.")
        desfav = [f for f in filas if f['ciclo_caja'] >= 60]
        if desfav:
            lineas.append(f"  En {len(desfav)} de {len(filas)} escenarios el ciclo es desfavorable (≥60 días).")

    elif tipo == 'valor_terminal':
        vts = [f['valor_terminal'] for f in filas if f.get('valor_terminal') is not None]
        if vts:
            lineas.append(f"  El valor terminal oscila entre ${min(vts):,.0f} y ${max(vts):,.0f}.")
            ratio = max(vts) / min(vts) if min(vts) > 0 else float('inf')
            if ratio > 3:
                lineas.append("  Alta sensibilidad: el rango es muy amplio. Validar supuestos cuidadosamente.")

    return lineas


def _criterio_sens_discreto(tipo: str, sens: Dict) -> List[str]:
    """Genera criterio para sensibilidad con escenarios discretos."""
    filas = sens.get('variaciones', [])
    var = sens.get('variable', '')
    lineas = [f"Sensibilidad discreta sobre '{var}':"]

    if tipo == 'van_tir':
        filas_con_van = [f for f in filas if f.get('van') is not None]
        if not filas_con_van:
            # Sin tasa: reportar solo TIRs
            tirs = [(f['valor_discreto'], f.get('tir')) for f in filas if f.get('tir') is not None]
            if tirs:
                tir_vals = [t for _, t in tirs]
                lineas.append(f"  TIR varía entre {min(tir_vals)*100:.2f}% y {max(tir_vals)*100:.2f}%.")
                mejor_val, mejor_tir = max(tirs, key=lambda x: x[1])
                peor_val, peor_tir = min(tirs, key=lambda x: x[1])
                lineas.append(f"  Mejor escenario: valor={mejor_val:,.0f} → TIR={mejor_tir*100:.2f}%")
                lineas.append(f"  Peor escenario: valor={peor_val:,.0f} → TIR={peor_tir*100:.2f}%")
                lineas.append("  (Sin tasa de descuento provista, no se calcula VAN por escenario.)")
            return lineas

        viables = [f for f in filas_con_van if f.get('viable')]
        no_viables = [f for f in filas_con_van if not f.get('viable')]
        lineas.append(f"  De {len(filas_con_van)} escenarios: {len(viables)} viables, {len(no_viables)} no viables.")

        def _fmt_val(x):
            return f"{x*100:.2f}%" if var == 'tasa' else f"{x:,.0f}"

        if viables:
            mejor = max(viables, key=lambda x: x.get('van', 0))
            lineas.append(f"  Mejor escenario: valor={_fmt_val(mejor['valor_discreto'])} → VAN=${mejor['van']:,.2f}")
        if no_viables:
            peor = min(no_viables, key=lambda x: x.get('van', 0))
            lineas.append(f"  Peor escenario: valor={_fmt_val(peor['valor_discreto'])} → VAN=${peor['van']:,.2f}")

        # Buscar punto de cruce
        filas = filas_con_van
        for i in range(len(filas) - 1):
            v1 = filas[i].get('van', 0) or 0
            v2 = filas[i + 1].get('van', 0) or 0
            if v1 * v2 < 0:
                d1 = filas[i]['valor_discreto']
                d2 = filas[i + 1]['valor_discreto']
                cruce = d1 + (d2 - d1) * abs(v1) / (abs(v1) + abs(v2))
                if var == 'tasa':
                    lineas.append(f"  Punto de equilibrio estimado: {var} ≈ {cruce*100:.2f}%")
                else:
                    lineas.append(f"  Punto de equilibrio estimado: {var} ≈ {cruce:,.0f}")
                break

    elif tipo == 'convertible':
        dils = [f['dilucion_pct'] for f in filas]
        owns = [f['ownership_fundador'] for f in filas]
        min_own = min(owns)
        max_own = max(owns)
        lineas.append(f"  Dilución varía entre {min(dils):.2f}% y {max(dils):.2f}%.")
        lineas.append(f"  Participación del fundador: {min_own:.2f}% – {max_own:.2f}%.")
        if min_own < 65:
            lineas.append(f"  ALERTA: en el escenario más dilutivo, el fundador baja de 65% ({min_own:.2f}%).")
        else:
            lineas.append(f"  El fundador mantiene al menos {min_own:.2f}% en todos los escenarios.")

    elif tipo == 'valor_terminal':
        vts = [f['valor_terminal'] for f in filas if f.get('valor_terminal') is not None]
        if vts:
            lineas.append(f"  Rango de valor terminal: ${min(vts):,.0f} – ${max(vts):,.0f}")
            if len(vts) >= 2:
                ratio = max(vts) / min(vts) if min(vts) > 0 else float('inf')
                lineas.append(f"  El valor máximo es {ratio:.1f}x el mínimo.")

    elif tipo == 'capital_trabajo':
        ciclos = [f['ciclo_caja'] for f in filas]
        lineas.append(f"  Ciclo de caja varía entre {min(ciclos):.0f} y {max(ciclos):.0f} días.")
        # Encontrar máximo tolerable (ciclo < 60)
        tolerables = [f for f in filas if f['ciclo_caja'] < 60]
        if tolerables:
            max_val = max(f['valor_discreto'] for f in tolerables)
            lineas.append(f"  Máximo tolerable de '{var}': {max_val:.0f} días (ciclo < 60 días).")

    elif tipo == 'runway':
        sostenibles = [f for f in filas if f.get('viable')]
        no_sost = [f for f in filas if not f.get('viable')]
        if sostenibles:
            lineas.append(f"  Sostenible en {len(sostenibles)} de {len(filas)} escenarios.")
        if no_sost:
            meses_list = [f.get('meses', 0) for f in no_sost if f.get('meses')]
            if meses_list:
                lineas.append(f"  En escenarios no sostenibles: {min(meses_list)}–{max(meses_list)} meses de runway.")

    elif tipo == 'credito':
        cuotas = [f['cuota'] for f in filas]
        lineas.append(f"  Cuota varía entre ${min(cuotas):,.2f} y ${max(cuotas):,.2f}.")
        totales = [f['total_pagado'] for f in filas]
        lineas.append(f"  Total pagado varía entre ${min(totales):,.2f} y ${max(totales):,.2f}.")

    return lineas
