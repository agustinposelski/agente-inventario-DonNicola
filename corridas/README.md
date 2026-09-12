# Corridas reales

Este directorio contiene las evidencias de ejecución del agente. Cada corrida registra entrada, fecha, salida y resultado observado.

| Corrida | Fecha | Entrada | Salida / evidencia |
|---|---|---|---|
| [Carga #18](corrida_02.md) | 07/09/2026 02:39 UTC | Cinco fotografías manuscritas ([1](entrada_corrida_02_01.jpeg), [2](entrada_corrida_02_02.jpeg), [3](entrada_corrida_02_03.jpeg), [4](entrada_corrida_02_04.jpeg), [5](entrada_corrida_02_05.jpeg)) | 51 productos; detectó el problema `nan` |
| [Carga #19](corrida_03.md) | 07/09/2026 03:00 UTC | [Una fotografía](entrada_corrida_03.jpg) | 10 productos; validación posterior sin `nan` |
| [Análisis de precios](corrida_precios_01.md) | Corrida real documentada | Selección de un balde de albañil | Tres fuentes y precio de referencia; [captura](evidencia_precios_01.png) |

## Iteraciones documentadas

- [Corrección del error `nan`](iteracion_tecnica_nan.md): problema, hipótesis, corrección y validación.
- [Evidencia de consumo de OpenAI](evidencia_consumo_2026-09-07.png): captura del panel de Usage del 7/09/2026.

Las corridas de inventario tienen revisión humana antes de persistir cambios. La corrida de precios también se confirma manualmente antes de tomar el valor de referencia.
