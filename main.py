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

from parser import analizar_texto
from validador import validar, resumir_faltantes
from motor import calcular
from presentacion import (
    encabezado, seccion, caja_criterio, mostrar_resultados,
    mostrar_sensibilidad, mostrar_datos_faltantes,
    mostrar_variables_detectadas,
)
from criterio import generar
from sensibilidad import analizar as analizar_sensibilidad


def procesar_problema(texto: str):
    """Procesa un problema financiero descrito en texto libre."""

    # 1. Analizar el texto
    analisis = analizar_texto(texto)
    tipo = analisis['tipo']
    tipo_nombre = analisis['tipo_nombre']
    variables = analisis['variables']
    config_sens = analisis['sensibilidad']

    encabezado(f"ANÁLISIS: {tipo_nombre.upper()}")

    # 2. Mostrar variables detectadas
    mostrar_variables_detectadas(variables)

    # 3. Validar qué se puede calcular
    validacion = validar(variables, tipo)
    faltantes = validacion['faltantes']
    calculos_posibles = validacion['calculos_posibles']

    # 4. Mostrar datos faltantes si los hay
    if faltantes:
        faltantes_legibles = resumir_faltantes(faltantes)
        mostrar_datos_faltantes(faltantes_legibles, validacion['calculos_imposibles'])

    # 5. Calcular si es posible
    resultados = {}
    if validacion['puede_calcular']:
        seccion("RESULTADOS")
        resultados = calcular(tipo, variables, calculos_posibles)

        if 'error' in resultados:
            print(f"  Error en el cálculo: {resultados['error']}\n")
        else:
            mostrar_resultados(tipo, resultados)

    # 6. Análisis de sensibilidad
    sens_resultado = None
    if config_sens and validacion['puede_calcular'] and 'error' not in resultados:
        sens_resultado = analizar_sensibilidad(tipo, variables, config_sens)
        if sens_resultado:
            mostrar_sensibilidad(sens_resultado, tipo)

    # 7. Criterio de decisión
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

