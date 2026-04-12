# ═══════════════════════════════════════════════════════════════
# main.py — Simulador Financiero: Herramienta de Toma de Decisiones
# Punto de entrada principal — recibe texto libre y produce análisis
# ═══════════════════════════════════════════════════════════════

import sys
import io

# Configurar UTF-8 para caracteres especiales en Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                   errors='replace')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8',
                                  errors='replace')

from parser import analizar_texto, TIPOS
from validador import validar, resumir_faltantes, nombre_legible
from motor import calcular
from presentacion import (
    encabezado, seccion, caja_criterio, mostrar_resultados,
    mostrar_sensibilidad, mostrar_datos_faltantes,
    mostrar_variables_detectadas, fmt_moneda, fmt_pct,
)
from criterio import generar
from sensibilidad import analizar as analizar_sensibilidad

# Variables que se muestran como porcentaje en la confirmación
_VARS_PCT_CONFIRM = {'tasa', 'tasa_crecimiento', 'tasa_caida', 'descuento_pct'}
_VARS_ENTERAS_CONFIRM = {'periodos', 'num_cuotas', 'capitalizaciones',
                          'dias_cobro', 'dias_inventario', 'dias_pago'}


def _confirmar_analisis(tipo, tipo_nombre, variables, config_sens):
    """
    Muestra lo detectado y permite al usuario confirmar, cancelar o corregir el tipo.
    Retorna (confirmado, tipo, tipo_nombre, variables).
    """
    print(f"\n  {'─' * 50}")
    print(f"  VERIFICACIÓN ANTES DE CALCULAR")
    print(f"  {'─' * 50}")
    print(f"  Tipo detectado:      {tipo_nombre}")
    print(f"  {'─' * 50}")

    if variables:
        print(f"  Datos detectados:")
        for k, v in variables.items():
            if k == 'flujos' and isinstance(v, list):
                if len(v) <= 8:
                    flujos_str = ', '.join(f'${f:,.0f}' for f in v)
                    print(f"    Flujos ({len(v)}p):    [{flujos_str}]")
                else:
                    print(f"    Flujos:            {len(v)} períodos (${v[0]:,.0f} ... ${v[-1]:,.0f})")
            elif k in _VARS_PCT_CONFIRM and isinstance(v, (int, float)):
                print(f"    {nombre_legible(k):20s} {v*100:.2f}%")
            elif k in _VARS_ENTERAS_CONFIRM and isinstance(v, (int, float)):
                print(f"    {nombre_legible(k):20s} {int(v)}")
            elif isinstance(v, (int, float)):
                print(f"    {nombre_legible(k):20s} ${v:,.2f}")
            else:
                print(f"    {nombre_legible(k):20s} {v}")
    else:
        print(f"  No se detectaron datos numéricos.")

    if config_sens:
        var_s = config_sens.get('variable', 'N/A')
        print(f"  {'─' * 50}")
        print(f"  Variable sensible:   {var_s}")
        flujo_anio = config_sens.get('flujo_anio')
        if flujo_anio:
            print(f"  Flujo específico:    año {flujo_anio}")
        vals_disc = config_sens.get('valores_discretos')
        if vals_disc:
            disc_str = ', '.join(f'{v:,.2f}' if v < 1 else f'${v:,.0f}' for v in vals_disc[:8])
            print(f"  Escenarios discretos: [{disc_str}]")
        elif config_sens.get('variaciones_pct'):
            vars_str = ', '.join(f'{v:+d}%' for v in config_sens['variaciones_pct'])
            print(f"  Variaciones:         [{vars_str}]")

    print(f"  {'─' * 50}")

    # Mostrar opciones de tipo disponibles para cambio rápido
    tipos_cortos = {str(i+1): k for i, k in enumerate(TIPOS.keys())}

    try:
        resp = input("  ¿Confirmar? (Enter=sí / n=cancelar / t=cambiar tipo): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False, tipo, tipo_nombre, variables

    if resp == 'n':
        return False, tipo, tipo_nombre, variables

    if resp == 't':
        print("  Tipos disponibles:")
        for num, key in tipos_cortos.items():
            marca = " ←" if key == tipo else ""
            print(f"    {num}. {TIPOS[key]['nombre']}{marca}")
        try:
            sel = input("  Seleccione número: ").strip()
        except (EOFError, KeyboardInterrupt):
            return False, tipo, tipo_nombre, variables
        if sel in tipos_cortos:
            tipo = tipos_cortos[sel]
            tipo_nombre = TIPOS[tipo]['nombre']
            print(f"  → Tipo cambiado a: {tipo_nombre}")

    return True, tipo, tipo_nombre, variables


def procesar_problema(texto: str):
    """Procesa un problema financiero descrito en texto libre."""

    # 1. Analizar el texto
    analisis = analizar_texto(texto)
    tipo = analisis['tipo']
    tipo_nombre = analisis['tipo_nombre']
    variables = analisis['variables']
    config_sens = analisis['sensibilidad']

    # 2. VERIFICACIÓN — mostrar lo detectado y pedir confirmación
    confirmado, tipo, tipo_nombre, variables = _confirmar_analisis(
        tipo, tipo_nombre, variables, config_sens)
    if not confirmado:
        print("  Cancelado. Ingrese el problema de nuevo.\n")
        return

    encabezado(f"ANÁLISIS: {tipo_nombre.upper()}")

    # 3. Mostrar variables detectadas
    mostrar_variables_detectadas(variables)

    # 4. Validar qué se puede calcular
    validacion = validar(variables, tipo)
    faltantes = validacion['faltantes']
    calculos_posibles = validacion['calculos_posibles']

    # 5. Mostrar datos faltantes si los hay
    if faltantes:
        faltantes_legibles = resumir_faltantes(faltantes)
        mostrar_datos_faltantes(faltantes_legibles, validacion['calculos_imposibles'])

    # 6. Calcular si es posible
    resultados = {}
    if validacion['puede_calcular']:
        seccion("RESULTADOS")
        resultados = calcular(tipo, variables, calculos_posibles)

        if 'error' in resultados:
            print(f"  Error en el cálculo: {resultados['error']}\n")
        else:
            mostrar_resultados(tipo, resultados)

    # 7. Análisis de sensibilidad
    sens_resultado = None
    if config_sens and validacion['puede_calcular'] and 'error' not in resultados:
        sens_resultado = analizar_sensibilidad(tipo, variables, config_sens)
        if sens_resultado:
            mostrar_sensibilidad(sens_resultado, tipo)

    # 8. Criterio de decisión
    seccion("CRITERIO DE DECISIÓN")
    faltantes_legibles = resumir_faltantes(faltantes) if faltantes else []
    lineas_criterio = generar(tipo, resultados, variables,
                              faltantes_legibles, sens_resultado)
    caja_criterio(f"CRITERIO — {tipo_nombre.upper()}", lineas_criterio)


def main():
    encabezado("SIMULADOR FINANCIERO — HERRAMIENTA DE TOMA DE DECISIONES")
    print("  Escriba su problema financiero en texto libre.")
    print("  Ejemplos:")
    print("    - Invierto $100,000 con flujos de $30,000 anuales por 5 años, tasa del 12%")
    print("    - Préstamo de $50,000 al 18% anual en 36 cuotas")
    print("    - Tengo un saldo de $200,000 con gasto mensual de $15,000")
    print()
    print("  Escriba 'salir' para terminar.\n")

    while True:
        try:
            texto = input("  >>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  ¡Hasta pronto!\n")
            break

        if not texto:
            continue

        if texto.lower() in ('salir', 'exit', 'quit', 'q'):
            print("\n  ═══════════════════════════════════════════════════")
            print("  Gracias por usar el Simulador Financiero.")
            print("  Herramienta de apoyo para la toma de decisiones.")
            print("  ═══════════════════════════════════════════════════\n")
            break

        try:
            procesar_problema(texto)
        except Exception as e:
            print(f"\n  Error procesando el problema: {e}\n")

        print()


if __name__ == "__main__":
    main()