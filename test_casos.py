"""Test script for the 8 exam cases."""
import json
from parser import analizar_texto

CASOS = [
    # Caso 1: Runway
    "Startup de desarrollo de software en Santa Cruz. Caja inicial Bs. 150,000. Burn mensual fijo Bs. 45,000 (salarios + oficina). Ingresos mensuales proyectados Bs. 30,000. Variable sensible: ingresos reales (caída por retrasos de clientes). Rango: 60%, 80%, 100%, 120% de ingresos base",

    # Caso 2: VAN/TIR
    "Compra de servidor para app de delivery. Costo inicial Bs. 80,000. Flujos anuales: A1=25k, A2=35k, A3=45k. Vida útil 3 años. Variable sensible: tasa descuento (costo de capital en Bolivia). Rango: 12%, 18%, 24%, 30%",

    # Caso 3: Convertible
    "Inversión de Bs. 200,000 vía nota convertible. Valoración cap Bs. 2,000,000. Descuento 20%. Variables sensibles: cap (Bs. 1.5M, 2M, 2.5M), descuento (15%, 20%, 25%)",

    # Caso 4: Capital de trabajo
    "E-commerce de repuestos electrónicos Santa Cruz. Ventas mensuales Bs. 120,000 (60 días crédito clientes). Proveedores pagan 30 días. Variable sensible: dias_cobro_clientes (45, 60, 75, 90 días)",

    # Caso 5: Crédito
    "Taller mecánico 4x4. Necesita Bs. 300,000 para inventario. Línea revolving Banco FIE 18% anual. Variable sensible: ingresos_mensuales (80k, 95k, 110k, 125k)",

    # Caso 6: Valor terminal
    "App delivery Santa Cruz proyecta venderse en 5 años. Inversión hoy Bs. 500,000. Variable sensible: multiple_salida (4x, 6x, 8x, 10x)",

    # Caso 7: VAN/TIR con flujo año 3
    "Consultoría software expande a La Paz. Inversión Bs. 180,000. Flujos: A1=50k, A2=80k, A3=110k. Variable sensible: flujo_año3 (90k, 110k, 130k, 150k)",

    # Caso 8: Interés simple vs compuesto
    "Plataforma ideame.com, Bs. 100,000 a 24 meses. Oferta 1: 15% simple anual. Oferta 2: 11% compuesto.",
]

ESPERADO = [
    {"tipo": "runway", "vars": {"saldo": 150000, "gasto_mensual": 45000, "ingreso_mensual": 30000}, "sens_var": "ingreso_mensual"},
    {"tipo": "van_tir", "vars": {"inversion": 80000, "flujos": [25000, 35000, 45000]}, "sens_var": "tasa"},
    {"tipo": "convertible", "vars": {"inversion": 200000, "valuation_cap": 2000000, "descuento_pct": 0.20}, "sens_var": "valuation_cap"},
    {"tipo": "capital_trabajo", "vars": {"dias_cobro": 60, "dias_pago": 30}, "sens_var": "dias_cobro"},
    {"tipo": "credito", "vars": {"monto": 300000, "tasa": 0.18}, "sens_var": "ingreso_mensual"},
    {"tipo": "valor_terminal", "vars": {"flujo_final": 500000, "multiplo": 4.0}, "sens_var": "multiplo"},
    {"tipo": "van_tir", "vars": {"inversion": 180000, "flujos": [50000, 80000, 110000]}, "sens_var": "flujos"},
    {"tipo": "interes_compuesto", "vars": {"capital": 100000, "tasa": 0.11, "periodos": 2}, "sens_var": None},
]

for i, (texto, esp) in enumerate(zip(CASOS, ESPERADO), 1):
    print(f"\n{'='*70}")
    print(f"CASO {i}")
    print(f"{'='*70}")
    res = analizar_texto(texto)

    # Check tipo
    tipo_ok = res['tipo'] == esp['tipo']
    print(f"Tipo detectado: {res['tipo']} (esperado: {esp['tipo']}) {'OK' if tipo_ok else 'FALLO'}")

    # Check variables
    print(f"Variables detectadas: {res['variables']}")
    for k, v in esp['vars'].items():
        actual = res['variables'].get(k)
        if actual is None:
            print(f"  {k}: FALTANTE (esperado: {v})")
        elif isinstance(v, list):
            ok = actual == v
            print(f"  {k}: {actual} (esperado: {v}) {'OK' if ok else 'FALLO'}")
        elif isinstance(v, float):
            ok = abs(actual - v) < 0.001
            print(f"  {k}: {actual} (esperado: {v}) {'OK' if ok else 'FALLO'}")
        else:
            ok = actual == v
            print(f"  {k}: {actual} (esperado: {v}) {'OK' if ok else 'FALLO'}")

    # Check extra variables that shouldn't be there
    for k in res['variables']:
        if k not in esp['vars']:
            print(f"  {k}: {res['variables'][k]} (no esperado)")

    # Check sensitivity
    sens = res['sensibilidad']
    if sens:
        sens_var = sens.get('variable', 'N/A')
        if esp['sens_var'] is None:
            print(f"Var sensible: {sens_var} (esperado: ninguna) INFO")
        else:
            sens_ok = sens_var == esp['sens_var']
            print(f"Var sensible: {sens_var} (esperado: {esp['sens_var']}) {'OK' if sens_ok else 'FALLO'}")
        if sens.get('valores_discretos'):
            print(f"  Valores discretos: {sens['valores_discretos']}")
        if sens.get('variaciones_pct'):
            print(f"  Variaciones %: {sens['variaciones_pct']}")
        flujo_anio = sens.get('flujo_anio')
        if flujo_anio:
            print(f"  Flujo año específico: {flujo_anio}")
    else:
        if esp['sens_var'] is None:
            print(f"Sensibilidad: NO DETECTADA (esperado: ninguna) OK")
        else:
            print(f"Sensibilidad: NO DETECTADA (esperado: {esp['sens_var']}) FALLO")
