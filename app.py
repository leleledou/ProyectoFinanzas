# ═══════════════════════════════════════════════════════════════
# app.py — Interfaz Streamlit para el Simulador Financiero
# Solo interfaz visual — NO modifica la lógica existente
# Ejecutar con: streamlit run app.py
# ═══════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
from parser import analizar_texto, TIPOS
from validador import validar, resumir_faltantes, nombre_legible
from motor import calcular
from criterio import generar
from capex_opex import interpretar as interpretar_capex_opex
from sensibilidad import analizar as analizar_sensibilidad
from tasas import analizar_tasas

# ─── Configuración de página ────────────────────────────────

st.set_page_config(
    page_title="Simulador Financiero",
    page_icon="📊",
    layout="wide",
)

# ─── CSS personalizado ──────────────────────────────────────

st.markdown("""
<style>
    .criterio-box {
        background-color: rgba(128, 128, 128, 0.15);
        border-left: 5px solid #1f77b4;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .criterio-line {
        margin: 0.25rem 0;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.3);
        padding: 0.8rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Helpers de formato ─────────────────────────────────────

_VARS_PCT = {'tasa', 'tasa_crecimiento', 'tasa_caida', 'descuento_pct'}
_VARS_ENTERAS = {'periodos', 'num_cuotas', 'capitalizaciones',
                 'dias_cobro', 'dias_inventario', 'dias_pago'}


_MONEDA_SIMBOLO = '$'


def set_moneda(simbolo):
    global _MONEDA_SIMBOLO
    _MONEDA_SIMBOLO = simbolo or '$'


def fmt_moneda(v):
    return f"{_MONEDA_SIMBOLO}{v:,.2f}"


def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


# ═══════════════════════════════════════════════════════════════
# Funciones de display (definidas ANTES de usarlas)
# ═══════════════════════════════════════════════════════════════

def _mostrar_resultados_st(tipo, res):
    dispatch = {
        'van_tir': _mostrar_van_tir_st,
        'interes_simple': lambda r: _mostrar_interes_st(r, 'interes_simple'),
        'interes_compuesto': lambda r: _mostrar_interes_st(r, 'interes_compuesto'),
        'runway': _mostrar_runway_st,
        'capital_trabajo': _mostrar_capital_trabajo_st,
        'credito': _mostrar_credito_st,
        'convertible': _mostrar_convertible_st,
        'valor_terminal': _mostrar_valor_terminal_st,
    }
    handler = dispatch.get(tipo)
    if handler:
        handler(res)


def _mostrar_van_tir_st(res):
    van = res.get('van')
    tir = res.get('tir')
    tasa = res.get('tasa', 0)
    inv = res.get('inversion', 0)
    payback = res.get('payback')
    ir = res.get('indice_rentabilidad')

    viable = van is not None and van > 0

    if viable:
        st.success("PROYECTO VIABLE — VAN positivo")
    else:
        st.error("PROYECTO NO VIABLE — VAN negativo o no calculable")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Inversión Inicial", fmt_moneda(inv))
        if van is not None:
            delta_van = f"{'Genera' if van > 0 else 'Destruye'} valor"
            st.metric("VAN", fmt_moneda(van), delta=delta_van,
                      delta_color="normal" if van > 0 else "inverse")
    with c2:
        st.metric("Tasa de Descuento", fmt_pct(tasa))
        if tir is not None:
            delta_tir = f"{'>' if tir > tasa else '<'} tasa descuento" if tasa else None
            st.metric("TIR", fmt_pct(tir), delta=delta_tir,
                      delta_color="normal" if tir > tasa else "inverse")
        else:
            st.metric("TIR", "No calculable")
    with c3:
        if payback is not None:
            st.metric("Período de Recupero", f"{payback:.1f} períodos")
        else:
            st.metric("Período de Recupero", "No se recupera")
        if ir is not None:
            st.metric("Índice de Rentabilidad", f"{ir:.3f}")

    flujos = res.get('flujos', [])
    if flujos and len(flujos) <= 12:
        with st.expander("Detalle de flujos"):
            for i, f in enumerate(flujos, 1):
                st.markdown(f"- **Período {i}:** {fmt_moneda(f)}")


def _mostrar_interes_st(res, tipo):
    capital = res.get('capital', 0)
    monto_f = res.get('monto_final', 0)
    interes = res.get('interes_total', 0)
    tasa = res.get('tasa', 0)
    periodos = res.get('periodos', 0)
    rendimiento = res.get('tasa_efectiva_total', 0)

    tasa_simp_ref = res.get('tasa_simple_ref')

    if tipo == 'interes_compuesto' and tasa_simp_ref and abs(tasa_simp_ref - tasa) > 0.001:
        monto_s = res.get('monto_simple_ref', 0)
        interes_s = res.get('interes_simple_ref', 0)

        st.info(f"Comparación de ofertas a {periodos:.0f} años")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### Interés Simple ({fmt_pct(tasa_simp_ref)})")
            st.metric("Monto Final", fmt_moneda(monto_s))
            st.metric("Interés Total", fmt_moneda(interes_s))
        with col2:
            st.markdown(f"#### Interés Compuesto ({fmt_pct(tasa)})")
            st.metric("Monto Final", fmt_moneda(monto_f))
            st.metric("Interés Total", fmt_moneda(interes))

        diff = monto_s - monto_f
        if diff > 0:
            st.success(f"El interés simple paga {fmt_moneda(diff)} MÁS. Conviene la oferta simple.")
        else:
            st.success(f"El interés compuesto paga {fmt_moneda(abs(diff))} MÁS. Conviene el compuesto.")
        return

    titulo = "Interés Compuesto" if tipo == 'interes_compuesto' else "Interés Simple"
    st.info(f"Resultados — {titulo}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Capital Inicial", fmt_moneda(capital))
        st.metric("Tasa Anual", fmt_pct(tasa))
    with c2:
        st.metric("Plazo", f"{periodos:.0f} años")
        if tipo == 'interes_compuesto':
            caps = res.get('capitalizaciones', 1)
            if caps > 1:
                st.metric("Capitalizaciones/año", str(caps))
    with c3:
        st.metric("Monto Final", fmt_moneda(monto_f))
        st.metric("Interés Total", fmt_moneda(interes))
        st.metric("Rendimiento Total", fmt_pct(rendimiento))

    if tipo == 'interes_compuesto' and 'diferencia_vs_simple' in res:
        diff = res['diferencia_vs_simple']
        if diff > 0:
            st.caption(f"Diferencia vs. interés simple: +{fmt_moneda(diff)}")


def _mostrar_runway_st(res):
    mes_q = res.get('mes_quiebre')
    flujo_neto = res.get('flujo_neto_mensual', 0)
    saldo = res.get('saldo', 0)
    gasto = res.get('gasto_mensual', 0)
    ingreso = res.get('ingreso_mensual', 0)

    if mes_q is None:
        st.success("Sostenible — Más de 120 meses de operación")
    elif mes_q <= 3:
        st.error(f"CRÍTICO — Quiebre en el mes {mes_q}")
    elif mes_q <= 6:
        st.error(f"URGENTE — Quiebre en el mes {mes_q}")
    elif mes_q <= 12:
        st.warning(f"ATENCIÓN — Quiebre en el mes {mes_q}")
    else:
        st.info(f"Quiebre en el mes {mes_q}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Saldo Inicial", fmt_moneda(saldo))
    with c2:
        st.metric("Gasto Mensual", fmt_moneda(gasto))
    with c3:
        st.metric("Ingreso Mensual", fmt_moneda(ingreso))

    c4, c5 = st.columns(2)
    with c4:
        delta_color = "normal" if flujo_neto >= 0 else "inverse"
        st.metric("Flujo Neto Mensual", fmt_moneda(flujo_neto),
                  delta="Positivo" if flujo_neto >= 0 else "Negativo",
                  delta_color=delta_color)
    with c5:
        if mes_q:
            st.metric("Meses de Runway", str(mes_q))
        else:
            st.metric("Meses de Runway", "> 120")

    if res.get('tasa_caida', 0) > 0:
        st.caption(f"Tasa de caída de ingresos: {fmt_pct(res['tasa_caida'])}/mes")

    saldos = res.get('saldos', [])
    if saldos and len(saldos) > 1:
        df = pd.DataFrame({
            'Mes': list(range(len(saldos))),
            'Saldo': saldos,
        })
        st.line_chart(df.set_index('Mes'), y='Saldo', use_container_width=True)


def _mostrar_capital_trabajo_st(res):
    ciclo = res.get('ciclo_caja', 0)
    cap_nec = res.get('capital_necesario')

    if ciclo < 0:
        st.success("Ciclo FAVORABLE — La empresa cobra antes de pagar")
    elif ciclo < 30:
        st.success(f"Ciclo ACEPTABLE — {ciclo:.0f} días")
    elif ciclo < 60:
        st.warning(f"Ciclo MODERADO — {ciclo:.0f} días")
    else:
        st.error(f"Ciclo DESFAVORABLE — {ciclo:.0f} días")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Días de Cobro", f"{res.get('dias_cobro', 0):.0f}")
    with c2:
        st.metric("Días de Inventario", f"{res.get('dias_inventario', 0):.0f}")
    with c3:
        st.metric("Días de Pago", f"{res.get('dias_pago', 0):.0f}")

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Ciclo de Caja", f"{ciclo:.0f} días")
    with c5:
        if cap_nec is not None:
            st.metric("Capital de Trabajo Necesario", fmt_moneda(cap_nec))


def _mostrar_credito_st(res):
    monto = res.get('monto', 0)
    cuota = res.get('cuota', 0)
    total_pagado = res.get('total_pagado', 0)
    total_int = res.get('total_intereses', 0)
    num_cuotas = res.get('num_cuotas', 0)
    periodo_label = res.get('periodo_label', 'período')

    sobrecosto = (total_int / monto * 100) if monto else 0

    if sobrecosto > 50:
        st.warning(f"Costo financiero ELEVADO ({sobrecosto:.1f}% del monto)")
    elif sobrecosto > 25:
        st.info(f"Costo financiero moderado ({sobrecosto:.1f}% del monto)")
    else:
        st.success(f"Costo financiero razonable ({sobrecosto:.1f}% del monto)")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Monto del Préstamo", fmt_moneda(monto))
        st.metric("Tasa Anual", fmt_pct(res.get('tasa_anual', 0)))
    with c2:
        st.metric(f"Cuota ({periodo_label})", fmt_moneda(cuota))
        st.metric("Número de Cuotas", str(num_cuotas))
    with c3:
        st.metric("Total a Pagar", fmt_moneda(total_pagado))
        st.metric("Total Intereses", fmt_moneda(total_int))

    tabla = res.get('tabla_amortizacion', [])
    if tabla:
        with st.expander("Tabla de Amortización"):
            df = pd.DataFrame(tabla)
            df.columns = [c.capitalize() for c in df.columns]
            st.dataframe(
                df.style.format({
                    'Cuota': '${:,.2f}',
                    'Interes': '${:,.2f}',
                    'Capital': '${:,.2f}',
                    'Saldo': '${:,.2f}',
                }),
                use_container_width=True,
                hide_index=True,
            )


def _mostrar_convertible_st(res):
    dilucion = res.get('dilucion_pct', 0)
    ownership = res.get('ownership_fundador', 0)

    if dilucion < 10:
        st.success(f"Dilución BAJA ({dilucion:.2f}%)")
    elif dilucion < 20:
        st.info(f"Dilución MODERADA ({dilucion:.2f}%)")
    else:
        st.warning(f"Dilución SIGNIFICATIVA ({dilucion:.2f}%)")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Inversión Nota", fmt_moneda(res.get('inversion', 0)))
        st.metric("Valuation Cap", fmt_moneda(res.get('valuation_cap', 0)))
    with c2:
        st.metric("Valoración Pre-money", fmt_moneda(res.get('valoracion_pre', 0)))
        st.metric("Descuento", f"{res.get('descuento_pct', 0):.1f}%")
    with c3:
        st.metric("Valoración Efectiva", fmt_moneda(res.get('valoracion_efectiva', 0)))
        st.metric("Método Conversión", res.get('metodo_conversion', 'N/A'))

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Dilución Fundador", f"{dilucion:.2f}%")
    with c5:
        st.metric("Participación Fundador", f"{ownership:.2f}%")


def _mostrar_valor_terminal_st(res):
    vt_p = res.get('vt_perpetuidad')
    vt_m = res.get('vt_multiplo')

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Flujo del Último Año", fmt_moneda(res.get('flujo_final', 0)))
    with c2:
        st.metric("Tasa de Crecimiento", fmt_pct(res.get('tasa_crecimiento', 0)))
    with c3:
        st.metric("Tasa de Descuento", fmt_pct(res.get('tasa_descuento', 0)))

    c4, c5 = st.columns(2)
    with c4:
        if vt_p is not None:
            st.metric("V.T. Perpetuidad (Gordon)", fmt_moneda(vt_p))
        elif 'error_perpetuidad' in res:
            st.error(f"Perpetuidad: {res['error_perpetuidad']}")
    with c5:
        if vt_m is not None:
            st.metric("V.T. Múltiplo", fmt_moneda(vt_m))
            st.caption(f"Múltiplo aplicado: {res.get('multiplo', 'N/A')}x")


# ─── Funciones de sensibilidad ──────────────────────────────

def _label_variacion(fila, es_discreto):
    if es_discreto:
        val = fila['valor_discreto']
        if abs(val) >= 1000:
            return fmt_moneda(val)
        elif val < 1:
            return f"{val*100:.2f}%"
        else:
            return f"{val:,.2f}"
    else:
        pct = fila['variacion_pct']
        return f"{pct:+.0f}%"


def _mostrar_sensibilidad_st(sens, tipo):
    if not sens or not sens.get('variaciones'):
        return

    var = sens['variable']
    filas = sens['variaciones']
    es_discreto = sens.get('es_discreto', False)

    etiqueta = "discreta" if es_discreto else "porcentual"
    st.markdown(f"**Variable analizada:** `{var}` (sensibilidad {etiqueta})")

    if tipo == 'van_tir':
        _sens_van_tir_st(filas, es_discreto)
    elif tipo == 'runway':
        _sens_runway_st(filas, es_discreto)
    elif tipo in ('interes_simple', 'interes_compuesto'):
        _sens_interes_st(filas, es_discreto)
    elif tipo == 'credito':
        _sens_credito_st(filas, es_discreto)
    elif tipo == 'valor_terminal':
        _sens_vt_st(filas, es_discreto)
    elif tipo == 'capital_trabajo':
        _sens_ct_st(filas, es_discreto)
    elif tipo == 'convertible':
        _sens_conv_st(filas, es_discreto)


def _sens_van_tir_st(filas, es_discreto):
    rows = []
    for f in filas:
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'VAN': f.get('van'),
            'TIR': fmt_pct(f.get('tir')) if f.get('tir') is not None else 'N/A',
            'Estado': 'Viable' if f.get('viable') else 'No viable',
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    vans = [f.get('van') for f in filas if f.get('van') is not None]
    if vans:
        labels = [_label_variacion(f, es_discreto) for f in filas if f.get('van') is not None]
        chart_df = pd.DataFrame({'Escenario': labels, 'VAN': vans})
        st.bar_chart(chart_df.set_index('Escenario'), y='VAN', use_container_width=True)


def _sens_runway_st(filas, es_discreto):
    rows = []
    for f in filas:
        meses = f.get('meses') or 120
        display = f.get('meses_display', str(meses))
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'Meses': meses,
            'Resultado': display,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame({
        'Escenario': [r['Escenario'] for r in rows],
        'Meses': [r['Meses'] for r in rows],
    })
    st.bar_chart(chart_df.set_index('Escenario'), y='Meses', use_container_width=True)


def _sens_interes_st(filas, es_discreto):
    rows = []
    for f in filas:
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'Monto Final': f['monto_final'],
            'Interés': f['interes'],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({
        'Monto Final': '${:,.2f}',
        'Interés': '${:,.2f}',
    }), use_container_width=True, hide_index=True)


def _sens_credito_st(filas, es_discreto):
    rows = []
    for f in filas:
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'Cuota': f['cuota'],
            'Total Pagado': f['total_pagado'],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({
        'Cuota': '${:,.2f}',
        'Total Pagado': '${:,.2f}',
    }), use_container_width=True, hide_index=True)


def _sens_vt_st(filas, es_discreto):
    rows = []
    for f in filas:
        vt = f.get('valor_terminal')
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'Valor Terminal': vt if vt is not None else 0,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({
        'Valor Terminal': '${:,.2f}',
    }), use_container_width=True, hide_index=True)


def _sens_ct_st(filas, es_discreto):
    rows = []
    for f in filas:
        cap = f.get('capital_necesario')
        rows.append({
            'Escenario': _label_variacion(f, es_discreto),
            'Ciclo Caja (días)': f['ciclo_caja'],
            'Capital Necesario': fmt_moneda(cap) if cap is not None else 'N/A',
            'Estado': 'Favorable' if f['ciclo_caja'] < 30 else 'Moderado' if f['ciclo_caja'] < 60 else 'Desfavorable',
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _sens_conv_st(filas, es_discreto):
    rows = []
    for f in filas:
        rows.append({
            'Escenario': f.get('label', _label_variacion(f, es_discreto)),
            'Dilución (%)': f'{f["dilucion_pct"]:.2f}',
            'Fundador (%)': f'{f["ownership_fundador"]:.2f}',
            'Val. Efectiva': fmt_moneda(f['valoracion_efectiva']),
            'Método': f.get('metodo', ''),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ─── Display de análisis de tasas ───────────────────────────

def _mostrar_tasas_st(info_tasas):
    """Muestra los resultados del análisis de tasas de interés."""
    if not info_tasas:
        return

    tasas = info_tasas['tasas']
    contexto = info_tasas['contexto']
    recomendacion = info_tasas.get('recomendacion')

    st.markdown("### Análisis de Tasas de Interés")

    for i, t in enumerate(tasas):
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(f"Tasa {i+1} — Tipo", t['tipo_tasa'].capitalize())
            with c2:
                st.metric("Tasa Original", f"{t['valor_pct']:.2f}%")
            with c3:
                tea = t['tasa_efectiva']
                if tea is not None:
                    st.metric("Tasa Efectiva Anual", f"{tea * 100:.4f}%")
            if t['tipo_tasa'] == 'nominal':
                st.caption(
                    f"Capitalización: {t['capitalizacion_nombre']} "
                    f"({t['capitalizacion_n']} veces/año)"
                )

    if recomendacion:
        ctx_label = {
            'inversion': 'Inversión',
            'financiamiento': 'Financiamiento',
            'general': 'General',
        }.get(contexto, contexto)

        if recomendacion.get('mejor_idx') is not None:
            st.success(
                f"**Recomendación ({ctx_label}):** "
                f"Conviene la tasa {recomendacion['mejor_tasa']} "
                f"(efectiva: {recomendacion['tasa_efectiva'] * 100:.4f}%) — "
                f"{recomendacion['criterio']}"
            )
        else:
            st.info(
                f"**Para inversión** conviene: {recomendacion['mejor_inversion']}  \n"
                f"**Para financiamiento** conviene: {recomendacion['mejor_financiamiento']}"
            )


# ─── Display de criterio ────────────────────────────────────

def _mostrar_criterio_st(lineas):
    if not lineas:
        return

    html_lines = []
    for linea in lineas:
        if not linea.strip():
            html_lines.append('<br>')
            continue

        text = linea

        if any(kw in text.upper() for kw in ['NO VIABLE', 'NO ES VIABLE', 'DESFAVORABLE', 'NEGATIVO']):
            text = f'&#10060; {text}'
        elif any(kw in text.upper() for kw in ['VIABLE', 'FAVORABLE', 'SOSTENIBLE', 'ACEPTABLE']):
            text = f'&#9989; {text}'

        if any(kw in text.upper() for kw in ['CRÍTICA', 'CRITICA', 'URGENTE', 'ALERTA']):
            text = f'&#128680; {text}'
        if any(kw in text.upper() for kw in ['MODERADO', 'AJUSTADO', 'LIMITADO']):
            text = f'&#9888;&#65039; {text}'

        if text.startswith('  '):
            html_lines.append(f'<div class="criterio-line" style="padding-left:1.5rem;">{text.strip()}</div>')
        else:
            html_lines.append(f'<div class="criterio-line"><strong>{text}</strong></div>')

    content = '\n'.join(html_lines)
    st.markdown(f'<div class="criterio-box">{content}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# INTERFAZ PRINCIPAL
# ═══════════════════════════════════════════════════════════════

st.markdown("# Simulador Financiero")
st.markdown("### Herramienta de Análisis y Toma de Decisiones")
st.markdown("---")

# ─── Sidebar ────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Tipos de análisis")
    for key, info in TIPOS.items():
        st.markdown(f"- **{info['nombre']}**")
    st.markdown("---")
    st.markdown(
        "El sistema detecta automáticamente el tipo de análisis "
        "a partir de su texto."
    )
    override = st.selectbox(
        "Forzar tipo de análisis (opcional):",
        ["Automático"] + [info['nombre'] for info in TIPOS.values()],
        index=0,
    )

# ─── Entrada de texto ───────────────────────────────────────

texto = st.text_area(
    "Describa su problema financiero en texto libre:",
    height=120,
    placeholder=(
        "Ejemplo: Invierto $100,000 con flujos de $30,000 anuales por 5 años, "
        "tasa del 12%\n\n"
        "Ejemplo: Startup con caja inicial 150000, burn mensual 20000\n\n"
        "Ejemplo: Préstamo de $50,000 al 18% anual en 36 cuotas"
    ),
)

# ─── Botón Analizar ─────────────────────────────────────────

analizar_btn = st.button("Analizar", type="primary", use_container_width=True)

if analizar_btn and texto.strip():
    try:
        analisis = analizar_texto(texto)
    except Exception as e:
        st.error(f"Error al analizar el texto: {e}")
        st.stop()

    set_moneda(analisis.get('moneda', '$'))

    tipo = analisis['tipo']
    tipo_nombre = analisis['tipo_nombre']
    variables = analisis['variables']
    config_sens = analisis['sensibilidad']

    if override != "Automático":
        for key, info in TIPOS.items():
            if info['nombre'] == override:
                tipo = key
                tipo_nombre = info['nombre']
                break

    st.markdown("---")
    st.markdown(f"## Análisis: {tipo_nombre}")

    # Variables detectadas
    if variables:
        with st.expander("Variables detectadas en el texto", expanded=True):
            cols = st.columns(min(len(variables), 3))
            col_idx = 0
            for k, v in variables.items():
                with cols[col_idx % len(cols)]:
                    label = nombre_legible(k)
                    if k == 'flujos' and isinstance(v, list):
                        st.metric(label="Flujos de caja", value=f"{len(v)} períodos")
                        if len(v) <= 8:
                            for i, fl in enumerate(v, 1):
                                st.caption(f"Período {i}: {fmt_moneda(fl)}")
                        else:
                            st.caption(f"Desde {fmt_moneda(v[0])} hasta {fmt_moneda(v[-1])}")
                    elif k in _VARS_PCT and isinstance(v, (int, float)):
                        st.metric(label=label.capitalize(), value=fmt_pct(v))
                    elif k in _VARS_ENTERAS and isinstance(v, (int, float)):
                        st.metric(label=label.capitalize(), value=str(int(v)))
                    elif isinstance(v, (int, float)):
                        st.metric(label=label.capitalize(), value=fmt_moneda(v))
                    else:
                        st.metric(label=label.capitalize(), value=str(v))
                col_idx += 1
    else:
        st.warning("No se detectaron variables numéricas en el texto.")
        st.stop()

    # Validación
    validacion = validar(variables, tipo)
    faltantes = validacion['faltantes']
    calculos_posibles = validacion['calculos_posibles']

    if faltantes:
        faltantes_legibles = resumir_faltantes(faltantes)
        with st.expander("Datos faltantes", expanded=True):
            st.warning("No se encontraron los siguientes datos en el texto:")
            for f in faltantes_legibles:
                st.markdown(f"  {f}")
            if validacion['calculos_imposibles']:
                st.markdown("**Cálculos que no se pueden realizar:**")
                for calc, reqs in validacion['calculos_imposibles']:
                    st.markdown(f"- {calc.upper().replace('_', ' ')}")

    # Resultados
    resultados = {}
    if validacion['puede_calcular']:
        resultados = calcular(tipo, variables, calculos_posibles)

        if 'error' in resultados:
            st.error(f"Error en el cálculo: {resultados['error']}")
        else:
            st.markdown("### Resultados")
            _mostrar_resultados_st(tipo, resultados)
    else:
        st.error(
            "No se pudieron detectar suficientes datos para realizar cálculos. "
            "Intente reformular su problema con más detalle."
        )

    # Sensibilidad
    sens_resultado = None
    if config_sens and validacion['puede_calcular'] and 'error' not in resultados:
        sens_resultado = analizar_sensibilidad(tipo, variables, config_sens)
        if sens_resultado:
            st.markdown("### Análisis de Sensibilidad")
            _mostrar_sensibilidad_st(sens_resultado, tipo)

    # Análisis de tasas de interés
    info_tasas = analizar_tasas(texto)
    if info_tasas:
        st.markdown("---")
        _mostrar_tasas_st(info_tasas)

    # Criterio de decisión
    st.markdown("---")
    st.markdown("### Criterio de Decisión")
    faltantes_legibles = resumir_faltantes(faltantes) if faltantes else []
    lineas_criterio = generar(tipo, resultados, variables,
                              faltantes_legibles, sens_resultado)
    _mostrar_criterio_st(lineas_criterio)

    # Capa adicional: interpretación CAPEX / OPEX (no intrusiva)
    info_co = interpretar_capex_opex(texto)
    if info_co:
        st.markdown("---")
        st.markdown("### Interpretación Complementaria — CAPEX / OPEX")
        cols = st.columns(len(info_co['variables']))
        for col, var in zip(cols, info_co['variables']):
            with col:
                monto_txt = (f"${var['monto']:,.2f}"
                             if var['monto'] is not None
                             else "— sin monto detectado —")
                st.markdown(f"**{var['tipo']} · {var['etiqueta']}**")
                st.markdown(f"#### {monto_txt}")
                st.caption(f"Frase clave: *\"{var['frase_clave']}\"*")
                st.markdown(
                    f"<div style='font-size:0.85rem;opacity:0.8;'>"
                    f"Fragmento: \"{var['fragmento']}\"</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("#### Criterio CAPEX / OPEX")
        _mostrar_criterio_st(info_co['criterios'])

elif analizar_btn and not texto.strip():
    st.warning("Por favor, ingrese un problema financiero para analizar.")
