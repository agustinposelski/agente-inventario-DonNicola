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

## Revisión de precios del stock

La revisión de precios se ejecuta sobre los productos del inventario que se seleccionan para analizar. Por eso, su costo no es fijo: aumenta según:

- Cantidad de productos enviados a buscar.
- Cantidad de fuentes consultadas por producto.
- Cantidad de variantes o medidas que deban distinguirse.
- Tokens utilizados para resumir y comparar los resultados.

Una corrida de precios de 20 productos no tiene el mismo costo que una corrida de un solo producto. La estimación debe calcularse así:

`Costo de precios = cantidad de productos × costo promedio de búsqueda por producto`

En la corrida documentada se analizó un balde de albañil con tres fuentes: Neomat, Ferretería Comara y Mercado Libre Argentina — Providentec. Para el uso habitual, se recomienda analizar únicamente los productos que necesitan actualización de precio y no repetir la consulta completa innecesariamente.

## Escenario de planificación

Para administrar el saldo disponible se adopta un límite interno de **USD 0,10 por semana** para el uso del agente.

| Concepto | Supuesto |
|---|---:|
| Cargas de inventario | 1 por semana |
| Revisión de precios del stock | 1 por semana, sobre productos seleccionados |
| Presupuesto semanal máximo | USD 0,10 |
| Presupuesto mensual aproximado | USD 0,43 |
| Presupuesto anual aproximado | USD 5,20 |

Con un saldo de USD 5, este escenario cubre aproximadamente un año si el consumo real se mantiene cercano al límite previsto. Si el costo observado supera ese límite, se debe reducir la cantidad de productos analizados por semana, espaciar las consultas de precios, reducir la resolución de las imágenes o elegir un modelo más económico.

## Modelo y optimización

Se utiliza GPT-5.6 Terra porque prioriza la lectura de manuscritos, la clasificación y la salida estructurada.

La optimización recomendada es:

1. Medir el costo real de diez corridas de inventario y de diez consultas de precios.
2. Separar el costo promedio de interpretar imágenes del costo promedio de buscar precios.
3. Probar un modelo más pequeño con las mismas entradas.
4. Comparar errores de producto, medida, cantidad, categoría y precio.
5. Cambiar de modelo solo si la calidad sigue siendo aceptable.

La decisión no debe basarse únicamente en el precio: un error de inventario o de precio puede ser más costoso que una diferencia pequeña en el costo de la API.

## Almacenamiento

Supabase se utiliza en el plan gratuito para esta primera versión personal. Debe monitorearse el almacenamiento de fotografías y el volumen de consultas. Si el historial crece demasiado, se puede conservar una miniatura o aplicar una política de archivo.

## Conclusión

El proyecto es económicamente viable para un uso personal y semanal, siempre que se controle el consumo real. El próximo control recomendado es registrar por separado el costo de diez corridas de inventario y diez revisiones de precios, y actualizar esta documentación con datos observados, reemplazando los supuestos de planificación por valores reales.
