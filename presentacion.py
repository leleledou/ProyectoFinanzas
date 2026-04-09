# ═══════════════════════════════════════════════════════════════
# presentacion.py — Módulo de Presentación Visual
# Formatos, cajas y display de resultados financieros
# ═══════════════════════════════════════════════════════════════

import sys
import io

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                   errors='replace')

ANCHO = 64


# ─── Primitivas visuales ─────────────────────────────────────

def encabezado(titulo: str):
    print(f"\n  {'═' * ANCHO}")
    print(f"  {titulo.center(ANCHO)}")
    print(f"  {'═' * ANCHO}\n")


def seccion(titulo: str):
    texto = f" {titulo} "
    pad = ANCHO - len(texto)
    izq = pad // 2
    der = pad - izq
    print(f"\n  {'─' * izq}{texto}{'─' * der}\n")


def separador():
    print(f"  {'─' * ANCHO}")


def caja(titulo: str, lineas: list):
    w = ANCHO - 2
    print(f"  ┌{'─' * w}┐")
    print(f"  │ {titulo:<{w - 1}}│")
    print(f"  ├{'─' * w}┤")
    for ln in lineas:
        s = str(ln)
        # Si la línea es muy larga, truncar
        if len(s) > w - 2:
            s = s[:w - 5] + '...'
        print(f"  │ {s:<{w - 1}}│")
    print(f"  └{'─' * w}┘\n")


def caja_criterio(titulo: str, lineas: list):
    w = ANCHO - 2
    print(f"\n  ╔{'═' * w}╗")
    print(f"  ║ {titulo:<{w - 1}}║")
    print(f"  ╠{'═' * w}╣")
    for ln in lineas:
        s = str(ln)
        # Wrap long lines preserving leading spaces
        indent = len(s) - len(s.lstrip(' '))
        indent_str = ' ' * indent
        max_w = w - 2
        while len(s) > max_w:
            corte = s[:max_w].rfind(' ')
            if corte <= indent:
                corte = max_w
            print(f"  ║ {s[:corte]:<{w - 1}}║")
            s = indent_str + s[corte:].lstrip(' ')
        print(f"  ║ {s:<{w - 1}}║")
    print(f"  ╚{'═' * w}╝\n")


def fmt_moneda(v: float) -> str:
    return f"${v:>14,.2f}"


def fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


def barra(valor: float, max_val: float, ancho: int = 20) -> str:
    if max_val <= 0:
        return '░' * ancho
    prop = min(max(valor / max_val, 0), 1)
    lleno = int(prop * ancho)
    return '█' * lleno + '░' * (ancho - lleno)


# ─── Display: VAN / TIR ──────────────────────────────────────

def mostrar_van_tir(res: dict):
    van = res.get('van')
    tir = res.get('tir')
    tasa = res.get('tasa', 0)
    inv = res.get('inversion', 0)
    flujos = res.get('flujos', [])
    payback = res.get('payback')
    ir = res.get('indice_rentabilidad')
    periodos = res.get('periodos', 0)

    estado = "VIABLE" if van and van > 0 else "NO VIABLE"

    lineas = [f"Inversión inicial:      {fmt_moneda(inv)}"]

    if len(flujos) <= 6:
        for i, f in enumerate(flujos, 1):
            lineas.append(f"  Flujo período {i}:      {fmt_moneda(f)}")
    else:
        lineas.append(f"  Flujo por período:    {fmt_moneda(flujos[0])}")
        lineas.append(f"  Períodos:             {periodos}")

    lineas.append(f"Tasa de descuento:      {fmt_pct(tasa)}")
    lineas.append("")
    if van is not None:
        lineas.append(f"VAN:                   {fmt_moneda(van)}")
    if tir is not None:
        lineas.append(f"TIR:                   {fmt_pct(tir)}")
    elif van is not None:
        lineas.append("TIR:                   No calculable (flujos no cambian de signo)")
    if payback is not None:
        lineas.append(f"Período de recupero:   {payback:.1f} períodos")
    elif van is not None:
        lineas.append("Período de recupero:   No se recupera en el horizonte")
    if ir is not None:
        lineas.append(f"Índice de rentab.:     {ir:.3f}")
    lineas.append("")
    lineas.append(f"Estado:                {estado}")

    caja("RESULTADOS — VAN / TIR", lineas)


# ─── Display: Interés Simple / Compuesto ─────────────────────

def mostrar_interes(res: dict, tipo: str):
    titulo = "RESULTADOS — INTERÉS COMPUESTO" if tipo == 'interes_compuesto' else "RESULTADOS — INTERÉS SIMPLE"
    caps = res.get('capitalizaciones', 1)

    lineas = [
        f"Capital inicial:       {fmt_moneda(res['capital'])}",
        f"Tasa anual:            {fmt_pct(res['tasa'])}",
        f"Plazo:                 {res['periodos']:.0f} años",
    ]
    if tipo == 'interes_compuesto' and caps > 1:
        lineas.append(f"Capitalizaciones/año:  {caps}")

    lineas += [
        "",
        f"Monto final:           {fmt_moneda(res['monto_final'])}",
        f"Interés total:         {fmt_moneda(res['interes_total'])}",
        f"Rendimiento total:     {fmt_pct(res.get('tasa_efectiva_total', 0))}",
    ]

    if tipo == 'interes_compuesto' and 'diferencia_vs_simple' in res:
        diff = res['diferencia_vs_simple']
        lineas.append(f"Diferencia vs. simple: {fmt_moneda(diff)}")

    caja(titulo, lineas)


# ─── Display: Runway ─────────────────────────────────────────

def mostrar_runway(res: dict):
    mes_q = res.get('mes_quiebre')
    flujo_neto = res.get('flujo_neto_mensual', 0)

    if mes_q:
        estado = f"Quiebre en el mes {mes_q}"
    else:
        estado = "Sostenible > 120 meses"

    lineas = [
        f"Saldo inicial:         {fmt_moneda(res['saldo'])}",
        f"Gasto mensual:         {fmt_moneda(res['gasto_mensual'])}",
        f"Ingreso mensual:       {fmt_moneda(res.get('ingreso_mensual', 0))}",
        f"Flujo neto mensual:    {fmt_moneda(flujo_neto)}",
    ]
    if res.get('tasa_caida', 0) > 0:
        lineas.append(f"Tasa caída ingresos:   {fmt_pct(res['tasa_caida'])}/mes")
    lineas += ["", f"Resultado:             {estado}"]

    caja("RESULTADOS — RUNWAY / SUPERVIVENCIA", lineas)


# ─── Display: Capital de Trabajo ─────────────────────────────

def mostrar_capital_trabajo(res: dict):
    ciclo = res.get('ciclo_caja', 0)
    cap_nec = res.get('capital_necesario')

    lineas = [
        f"Días de cobro:         {res.get('dias_cobro', 0):.0f} días",
        f"Días de inventario:    {res.get('dias_inventario', 0):.0f} días",
        f"Días de pago:          {res.get('dias_pago', 0):.0f} días",
        "",
        f"Ciclo de caja:         {ciclo:.0f} días",
        f"Interpretación:        {'Favorable' if ciclo < 30 else 'Moderado' if ciclo < 60 else 'Desfavorable'}",
    ]
    if cap_nec is not None:
        lineas.append(f"Capital de trabajo:    {fmt_moneda(cap_nec)}")

    caja("RESULTADOS — CAPITAL DE TRABAJO", lineas)


# ─── Display: Crédito ────────────────────────────────────────

def mostrar_credito(res: dict):
    tabla = res.get('tabla_amortizacion', [])

    lineas = [
        f"Monto del préstamo:    {fmt_moneda(res['monto'])}",
        f"Tasa anual:            {fmt_pct(res['tasa_anual'])}",
        f"Tasa por período:      {fmt_pct(res['tasa_periodo'])}",
        f"Número de cuotas:      {res['num_cuotas']}",
        "",
        f"Cuota ({res['periodo_label']}): {fmt_moneda(res['cuota'])}",
        f"Total a pagar:         {fmt_moneda(res['total_pagado'])}",
        f"Total intereses:       {fmt_moneda(res['total_intereses'])}",
    ]
    caja("RESULTADOS — CRÉDITO / PRÉSTAMO", lineas)

    # Mostrar primeras y últimas filas de amortización
    if tabla:
        seccion("Tabla de Amortización (primeras y últimas filas)")
        print(f"    {'Per':>4}  {'Cuota':>12}  {'Interés':>12}  {'Capital':>12}  {'Saldo':>14}")
        print(f"    {'─'*4}  {'─'*12}  {'─'*12}  {'─'*12}  {'─'*14}")
        filas_mostrar = tabla[:3] + (['...'] if len(tabla) > 6 else []) + tabla[-3:] if len(tabla) > 6 else tabla
        for fila in filas_mostrar:
            if fila == '...':
                print(f"    {'...':>55}")
                continue
            print(f"    {fila['periodo']:>4}  "
                  f"${fila['cuota']:>11,.2f}  "
                  f"${fila['interes']:>11,.2f}  "
                  f"${fila['capital']:>11,.2f}  "
                  f"${fila['saldo']:>13,.2f}")
        print()


# ─── Display: Nota Convertible ───────────────────────────────

def mostrar_convertible(res: dict):
    lineas = [
        f"Inversión nota:        {fmt_moneda(res['inversion'])}",
        f"Valuation cap:         {fmt_moneda(res['valuation_cap'])}",
        f"Valoración pre-money:  {fmt_moneda(res['valoracion_pre'])}",
        f"Descuento:             {res['descuento_pct']:.1f}%",
        "",
        f"Valoración efectiva:   {fmt_moneda(res['valoracion_efectiva'])}",
        f"Método conversión:     {res.get('metodo_conversion', 'N/A')}",
        f"Dilución fundador:     {res['dilucion_pct']:.2f}%",
        f"Participación fundad.: {res['ownership_fundador']:.2f}%",
        f"Valoración post-money: {fmt_moneda(res['valoracion_post'])}",
    ]
    caja("RESULTADOS — NOTA CONVERTIBLE", lineas)


# ─── Display: Valor Terminal ─────────────────────────────────

def mostrar_valor_terminal(res: dict):
    lineas = [
        f"Flujo del último año:  {fmt_moneda(res['flujo_final'])}",
        f"Tasa de crecimiento:   {fmt_pct(res.get('tasa_crecimiento', 0))}",
        f"Tasa de descuento:     {fmt_pct(res.get('tasa_descuento', 0))}",
        "",
    ]
    vt_p = res.get('vt_perpetuidad')
    if vt_p is not None:
        lineas.append(f"Valor Terminal (Gordon): {fmt_moneda(vt_p)}")
    elif 'error_perpetuidad' in res:
        lineas.append(f"Perpetuidad: {res['error_perpetuidad']}")

    vt_m = res.get('vt_multiplo')
    if vt_m is not None:
        lineas.append(f"Valor Terminal (múlt.):  {fmt_moneda(vt_m)}")
        lineas.append(f"Múltiplo aplicado:       {res.get('multiplo', 'N/A')}x")

    caja("RESULTADOS — VALOR TERMINAL", lineas)


# ─── Display genérico ────────────────────────────────────────

def mostrar_resultados(tipo: str, res: dict):
    """Despacha al display correcto según el tipo."""
    if tipo == 'van_tir':
        mostrar_van_tir(res)
    elif tipo == 'interes_simple':
        mostrar_interes(res, 'interes_simple')
    elif tipo == 'interes_compuesto':
        mostrar_interes(res, 'interes_compuesto')
    elif tipo == 'runway':
        mostrar_runway(res)
    elif tipo == 'capital_trabajo':
        mostrar_capital_trabajo(res)
    elif tipo == 'credito':
        mostrar_credito(res)
    elif tipo == 'convertible':
        mostrar_convertible(res)
    elif tipo == 'valor_terminal':
        mostrar_valor_terminal(res)


# ─── Display: Sensibilidad ───────────────────────────────────

def mostrar_sensibilidad(sens: dict, tipo: str):
    if not sens or not sens.get('variaciones'):
        return

    var = sens['variable']
    filas = sens['variaciones']
    seccion(f"Análisis de Sensibilidad — Variable: {var}")

    # Determinar la métrica principal a mostrar
    if tipo == 'van_tir':
        _mostrar_sens_van(filas)
    elif tipo == 'runway':
        _mostrar_sens_runway(filas)
    elif tipo in ('interes_simple', 'interes_compuesto'):
        _mostrar_sens_interes(filas)
    elif tipo == 'credito':
        _mostrar_sens_credito(filas)
    elif tipo == 'valor_terminal':
        _mostrar_sens_vt(filas)


def _mostrar_sens_van(filas: list):
    vans = [f['van'] for f in filas if f.get('van') is not None]
    max_abs = max(abs(v) for v in vans) if vans else 1
    if max_abs == 0:
        max_abs = 1

    print(f"    {'Variación':>9}  {'Barra':20}  {'VAN':>16}  {'TIR':>8}  Estado")
    print(f"    {'─'*9}  {'─'*20}  {'─'*16}  {'─'*8}  {'─'*10}")
    for f in filas:
        van = f.get('van', 0) or 0
        tir = f.get('tir')
        pct = f['variacion_pct']
        sgn = '+' if pct >= 0 else ''
        b = barra(max(van, 0), max_abs, 18)
        viable = "VIABLE" if f.get('viable') else "NO VIABLE"
        tir_s = fmt_pct(tir) if tir else '  N/A  '
        print(f"    {sgn}{pct:>7.0f}%  {b}  {fmt_moneda(van)}  {tir_s:>8}  {viable}")
    print()


def _mostrar_sens_runway(filas: list):
    max_meses = max((f['meses'] or 120) for f in filas)
    print(f"    {'Variación':>9}  {'Barra':20}  Resultado")
    print(f"    {'─'*9}  {'─'*20}  {'─'*30}")
    for f in filas:
        meses = f.get('meses') or 120
        pct = f['variacion_pct']
        sgn = '+' if pct >= 0 else ''
        b = barra(meses, max(max_meses, 1), 18)
        display = f.get('meses_display', str(meses))
        print(f"    {sgn}{pct:>7.0f}%  {b}  {display}")
    print()


def _mostrar_sens_interes(filas: list):
    montos = [f['monto_final'] for f in filas]
    max_m = max(montos) if montos else 1
    print(f"    {'Variación':>9}  {'Barra':20}  {'Monto Final':>16}  {'Interés':>16}")
    print(f"    {'─'*9}  {'─'*20}  {'─'*16}  {'─'*16}")
    for f in filas:
        pct = f['variacion_pct']
        sgn = '+' if pct >= 0 else ''
        b = barra(f['monto_final'], max_m, 18)
        print(f"    {sgn}{pct:>7.0f}%  {b}  {fmt_moneda(f['monto_final'])}  {fmt_moneda(f['interes'])}")
    print()


def _mostrar_sens_credito(filas: list):
    cuotas = [f['cuota'] for f in filas]
    max_c = max(cuotas) if cuotas else 1
    print(f"    {'Variación':>9}  {'Barra':20}  {'Cuota':>16}  {'Total Pagado':>16}")
    print(f"    {'─'*9}  {'─'*20}  {'─'*16}  {'─'*16}")
    for f in filas:
        pct = f['variacion_pct']
        sgn = '+' if pct >= 0 else ''
        b = barra(f['cuota'], max_c, 18)
        print(f"    {sgn}{pct:>7.0f}%  {b}  {fmt_moneda(f['cuota'])}  {fmt_moneda(f['total_pagado'])}")
    print()


def _mostrar_sens_vt(filas: list):
    vts = [f['valor_terminal'] for f in filas if f.get('valor_terminal') is not None]
    max_vt = max(vts) if vts else 1
    print(f"    {'Variación':>9}  {'Barra':20}  {'Valor Terminal':>16}")
    print(f"    {'─'*9}  {'─'*20}  {'─'*16}")
    for f in filas:
        pct = f['variacion_pct']
        sgn = '+' if pct >= 0 else ''
        vt = f.get('valor_terminal')
        if vt is not None:
            b = barra(vt, max_vt, 18)
            vt_s = fmt_moneda(vt)
        else:
            b = '░' * 18
            vt_s = '       N/A'
        print(f"    {sgn}{pct:>7.0f}%  {b}  {vt_s}")
    print()


# ─── Display: datos faltantes ────────────────────────────────

def mostrar_datos_faltantes(faltantes: list, calculos_imposibles: list):
    if not faltantes:
        return
    lineas = ["Los siguientes datos no se encontraron en el texto:", ""]
    for f in faltantes:
        lineas.append(f"  {f}")
    if calculos_imposibles:
        lineas.append("")
        lineas.append("Por eso no se pudo calcular:")
        for calc, reqs in calculos_imposibles:
            lineas.append(f"  - {calc.upper().replace('_', ' ')}")
    caja("DATOS FALTANTES", lineas)


_VARS_ENTERAS = {'periodos', 'num_cuotas', 'capitalizaciones',
                  'dias_cobro', 'dias_inventario', 'dias_pago'}
_VARS_PCT = {'tasa', 'tasa_crecimiento', 'tasa_caida', 'descuento_pct'}


def mostrar_variables_detectadas(variables: dict):
    if not variables:
        return
    from validador import nombre_legible
    lineas = []
    for k, v in variables.items():
        if k == 'flujos' and isinstance(v, list):
            lineas.append(f"  Flujos detectados: {len(v)} período(s)")
            if len(v) <= 5:
                for i, f in enumerate(v, 1):
                    lineas.append(f"    Período {i}: ${f:,.2f}")
        elif k in _VARS_PCT and isinstance(v, float):
            lineas.append(f"  {nombre_legible(k)}: {v*100:.2f}%")
        elif k in _VARS_ENTERAS and isinstance(v, float):
            lineas.append(f"  {nombre_legible(k)}: {int(v)}")
        elif isinstance(v, (int, float)):
            lineas.append(f"  {nombre_legible(k)}: ${v:,.2f}")
        else:
            lineas.append(f"  {nombre_legible(k)}: {v}")
    if lineas:
        caja("DATOS DETECTADOS EN EL TEXTO", lineas)
