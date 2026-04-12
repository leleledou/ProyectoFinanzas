"""Full integration test - runs each case through the complete pipeline."""
import sys
import io

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

from parser import analizar_texto
from validador import validar, resumir_faltantes
from motor import calcular
from sensibilidad import analizar as analizar_sensibilidad
from criterio import generar

CASOS = [
    ("CASO 1: Runway", "Startup de desarrollo de software en Santa Cruz. Caja inicial Bs. 150,000. Burn mensual fijo Bs. 45,000 (salarios + oficina). Ingresos mensuales proyectados Bs. 30,000. Variable sensible: ingresos reales (caída por retrasos de clientes). Rango: 60%, 80%, 100%, 120% de ingresos base"),
    ("CASO 2: VAN/TIR", "Compra de servidor para app de delivery. Costo inicial Bs. 80,000. Flujos anuales: A1=25k, A2=35k, A3=45k. Vida útil 3 años. Variable sensible: tasa descuento (costo de capital en Bolivia). Rango: 12%, 18%, 24%, 30%"),
    ("CASO 3: Convertible", "Inversión de Bs. 200,000 vía nota convertible. Valoración cap Bs. 2,000,000. Descuento 20%. Variables sensibles: cap (Bs. 1.5M, 2M, 2.5M), descuento (15%, 20%, 25%)"),
    ("CASO 4: Capital Trabajo", "E-commerce de repuestos electrónicos Santa Cruz. Ventas mensuales Bs. 120,000 (60 días crédito clientes). Proveedores pagan 30 días. Variable sensible: dias_cobro_clientes (45, 60, 75, 90 días)"),
    ("CASO 5: Crédito", "Taller mecánico 4x4. Necesita Bs. 300,000 para inventario. Línea revolving Banco FIE 18% anual. Variable sensible: ingresos_mensuales (80k, 95k, 110k, 125k)"),
    ("CASO 6: Valor Terminal", "App delivery Santa Cruz proyecta venderse en 5 años. Inversión hoy Bs. 500,000. Variable sensible: multiple_salida (4x, 6x, 8x, 10x)"),
    ("CASO 7: VAN/TIR flujo año3", "Consultoría software expande a La Paz. Inversión Bs. 180,000. Flujos: A1=50k, A2=80k, A3=110k. Variable sensible: flujo_año3 (90k, 110k, 130k, 150k)"),
    ("CASO 8: Interés simple vs compuesto", "Plataforma ideame.com, Bs. 100,000 a 24 meses. Oferta 1: 15% simple anual. Oferta 2: 11% compuesto."),
]

for nombre, texto in CASOS:
    print(f"\n{'='*70}")
    print(f"  {nombre}")
    print(f"{'='*70}")

    analisis = analizar_texto(texto)
    tipo = analisis['tipo']
    variables = analisis['variables']
    config_sens = analisis['sensibilidad']

    print(f"  Tipo: {analisis['tipo_nombre']}")
    print(f"  Variables: {variables}")

    validacion = validar(variables, tipo)
    faltantes = validacion['faltantes']
    calculos_posibles = validacion['calculos_posibles']

    if faltantes:
        print(f"  Faltantes: {faltantes}")
    print(f"  Puede calcular: {validacion['puede_calcular']}")
    print(f"  Calculos posibles: {calculos_posibles}")

    resultados = {}
    if validacion['puede_calcular']:
        resultados = calcular(tipo, variables, calculos_posibles)
        if 'error' in resultados:
            print(f"  ERROR: {resultados['error']}")
        else:
            # Show key results
            for k, v in resultados.items():
                if k in ('tabla_amortizacion', 'saldos', 'ingresos'):
                    continue
                if isinstance(v, float):
                    print(f"  {k}: {v:,.4f}")
                else:
                    print(f"  {k}: {v}")

    # Sensibilidad
    sens_resultado = None
    if config_sens and validacion['puede_calcular'] and 'error' not in resultados:
        sens_resultado = analizar_sensibilidad(tipo, variables, config_sens)
        if sens_resultado:
            print(f"  Sensibilidad: {len(sens_resultado.get('variaciones', []))} escenarios")
            for f in sens_resultado.get('variaciones', [])[:4]:
                print(f"    {f}")
        else:
            print(f"  Sensibilidad: FALLO (retornó None)")

    # Criterio
    faltantes_leg = resumir_faltantes(faltantes) if faltantes else []
    criterio_lines = generar(tipo, resultados, variables, faltantes_leg, sens_resultado)
    print(f"  --- CRITERIO ---")
    for ln in criterio_lines:
        print(f"  {ln}")
