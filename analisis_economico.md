# Análisis económico

## Alcance analizado

El costo principal del agente proviene de:

1. Interpretar las fotografías del inventario con la API de OpenAI.
2. Generar la salida estructurada.
3. Consultar y comparar precios online.
4. Mantener el almacenamiento en Supabase.

La revisión humana y la descarga del CSV no agregan costo de modelo significativo.

## Datos observados del proyecto

Se realizaron tres corridas reales:

- Carga #18: cinco imágenes y 51 productos.
- Carga #19: una imagen y 10 productos.
- Análisis de precios: un producto con tres fuentes comparadas.

La cuenta de OpenAI fue cargada inicialmente con **USD 5**. El consumo exacto debe verificarse en el panel de uso, porque depende de la cantidad y resolución de las imágenes, los tokens enviados y la respuesta generada.

## Fórmula de costo

Para cada corrida:

`Costo = (tokens de entrada / 1.000.000 × tarifa de entrada) + (tokens de salida / 1.000.000 × tarifa de salida)`

Para el análisis de precios también debe sumarse el costo de las consultas adicionales realizadas por el agente.

No se debe presentar una cifra fija como exacta sin consultar la tarifa vigente del modelo y el consumo real de la cuenta.

## Escenario de planificación

Para administrar el saldo disponible se adopta un límite interno de **USD 0,10 por semana** para el uso del agente.

| Concepto | Supuesto |
|---|---:|
| Cargas de inventario | 1 por semana |
| Análisis de precios | 1 por semana |
| Presupuesto semanal máximo | USD 0,10 |
| Presupuesto mensual aproximado | USD 0,43 |
| Presupuesto anual aproximado | USD 5,20 |

Con un saldo de USD 5, este escenario cubre aproximadamente un año si el consumo real se mantiene cercano al límite previsto. Si el costo observado supera ese límite, se debe reducir la resolución o cantidad de imágenes, espaciar las consultas de precios o elegir un modelo más económico.

## Modelo y optimización

Se utiliza GPT-5.6 Terra porque prioriza la lectura de manuscritos, la clasificación y la salida estructurada.

La optimización recomendada es:

1. Medir el costo real de diez corridas.
2. Probar un modelo más pequeño con las mismas imágenes.
3. Comparar errores de producto, medida, cantidad y categoría.
4. Cambiar de modelo solo si la calidad sigue siendo aceptable.

La decisión no debe basarse únicamente en el precio: un error de inventario puede ser más costoso que una diferencia pequeña en el costo de la API.

## Almacenamiento

Supabase se utiliza en el plan gratuito para esta primera versión personal. Debe monitorearse el almacenamiento de fotografías y el volumen de consultas. Si el historial crece demasiado, se puede conservar una miniatura o aplicar una política de archivo.

## Conclusión

El proyecto es económicamente viable para un uso personal y semanal, siempre que se controle el consumo real. El próximo control recomendado es registrar el costo de diez corridas y actualizar esta documentación con datos observados, reemplazando los supuestos de planificación por valores reales.
