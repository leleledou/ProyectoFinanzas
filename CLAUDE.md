# CLAUDE.md

Este archivo orienta a Claude Code (claude.ai/code) cuando trabaja en este repositorio.

## Ejecutar la aplicación

```bash
python main.py
```

Sin pasos de compilación ni dependencias externas — solo biblioteca estándar de Python.

## Arquitectura

El sistema recibe un problema financiero escrito en texto libre, lo analiza, calcula y produce una salida estructurada con una sección **CRITERIO** redactada en lenguaje natural. Ocho módulos, cada uno con una única responsabilidad:

```
main.py          Punto de entrada. Loop de input → llama a procesar_problema()
parser.py        Análisis NLP del texto: detecta tipo de análisis, extrae variables numéricas, detecta configuración de sensibilidad
validador.py     Determina qué variables requeridas están presentes/ausentes y qué cálculos son posibles
motor.py         Orquesta las llamadas a calculo.py según el tipo y las variables disponibles
calculo.py       Funciones matemáticas puras (VAN, TIR, amortización, runway, etc.) — sin efectos secundarios
sensibilidad.py  Varía una variable en un rango porcentual y devuelve resultados por escenario
presentacion.py  Todo el display en consola: cajas, barras, tablas, formato de moneda y porcentajes
criterio.py      Genera las conclusiones en lenguaje humano a partir de los resultados
```

## Diseño del parser (módulo más complejo)

`parser.py` usa procesamiento de lenguaje natural basado en reglas:

1. **Detección de tipo** (`_detectar_tipo`): puntúa cada tipo de análisis contando coincidencias de palabras clave, ponderadas por especificidad (`peso`).
2. **Extracción de números** (`_encontrar_numeros`): regex encuentra todos los números con su contexto (90 chars antes), detecta signo `$`, unidad `%`, unidades de tiempo (`años`, `cuotas`, etc.).
3. **Mapeo a variables** (`_identificar_variable`): usa el keyword **más a la derecha** (más cercano al número) dentro de los últimos 50 chars de contexto — esto evita que el contexto de un número anterior contamine el siguiente.
4. **Fallback posicional** en `_extraer_variables`: los valores monetarios sin contexto se asignan por posición según el tipo (primer valor grande → `inversion`, el siguiente → `flujos` para VAN/TIR; primero → `monto` para crédito, etc.).
5. **Detección de sensibilidad** (`_detectar_sensibilidad`): busca palabras clave de sensibilidad; por defecto aplica sensibilidad sobre flujos en VAN/TIR.

### Invariante clave del parser
Las entradas de `CONTEXTO_MAP` se buscan con `rfind` (última aparición = más cercana al número). La **proximidad** tiene prioridad sobre el orden en la lista.

## Tipos de análisis y variables requeridas

| Clave de tipo | Variables requeridas |
|---|---|
| `van_tir` | `inversion`, `flujos`, `tasa` |
| `interes_simple` | `capital`, `tasa`, `periodos` |
| `interes_compuesto` | `capital`, `tasa`, `periodos` |
| `runway` | `saldo`, `gasto_mensual` |
| `capital_trabajo` | `dias_cobro`, `dias_inventario`, `dias_pago` |
| `credito` | `monto`, `tasa`, `num_cuotas` |
| `convertible` | `inversion`, `valuation_cap`, `valoracion_pre`, `descuento_pct` |
| `valor_terminal` | `flujo_final`, `tasa_crecimiento`, `tasa` |

## Comportamientos importantes

- `calcular_tir` devuelve `None` cuando no puede encontrar la TIR — todos los llamadores deben manejar `None`.
- Las tasas se almacenan como decimales (`0.12` = 12%). El parser divide entre 100 cuando aparece el símbolo `%` o cuando el contexto (`tasa de`, `tasa del`, etc.) implica porcentaje y el valor es > 1.
- `num_cuotas` se detecta mediante la unidad de tiempo `cuotas` en el regex, distinta de `periodos` (años/meses).
- La sección CRITERIO siempre se genera, incluso con datos incompletos — en ese caso indica qué falta y por qué limita el análisis.
