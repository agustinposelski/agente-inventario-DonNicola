# Agente de inventario — Ferretería Don Nicola

Aplicación personal para transformar fotografías de anotaciones semanales en un inventario organizado, acumulativo y revisable.

**Aplicación desplegada:** https://agente-inventario-donnicola.streamlit.app/

## Objetivo

Reducir la transcripción manual del inventario de la ferretería. El usuario carga fotografías del cuaderno, el agente interpreta los productos y propone una tabla que luego se revisa y confirma.

## Funcionamiento

1. Cargar una o varias imágenes.
2. GPT-5.6 Terra interpreta el lote completo.
3. Revisar y corregir la tabla.
4. Confirmar la carga.
5. Guardar el lote de forma transaccional: si falla una operación, no se aplican cambios parciales.
6. Sumar cantidades al inventario online.
7. Consultar el inventario acumulado y descargarlo como CSV.
7. Seleccionar productos para consultar precios online y calcular un precio de referencia.

El inventario es acumulativo. Un producto se considera repetido cuando coinciden producto, medida, variante y unidad.

## Salida estructurada

Cada producto se organiza con estos campos:

- Producto
- Categoría
- Medida
- Variante
- Cantidad
- Unidad
- Observaciones
- Requiere revisión

Si un dato no se distingue, el agente no lo inventa: lo marca como no especificado o para revisión manual.

## Análisis de precios

La aplicación permite:

- Consultar precios online.
- Comparar varias fuentes.
- Mostrar rango y confianza.
- Calcular un precio de referencia intermedio.
- Editar manualmente el precio cuando la búsqueda no sea suficiente.
- Reflejar el precio confirmado en el inventario acumulado.

## Herramientas y tecnología

- Interfaz: Streamlit.
- Modelo: OpenAI Responses API con GPT-5.6 Terra.
- Almacenamiento: Supabase.
- Persistencia: función SQL transaccional para evitar actualizaciones parciales.
- Repositorio: GitHub.
- Despliegue: Streamlit Cloud.
- Acceso: contraseña personal.

## Prompts del agente

El contrato está separado en archivos y es utilizado por la aplicación:

- [prompts/system_prompt.md](prompts/system_prompt.md): rol, objetivo, categorías, reglas de evidencia, salida y supervisión.
- [prompts/user_prompt.md](prompts/user_prompt.md): instrucción para interpretar el lote semanal de imágenes.

## Supervisión humana

- **L0:** el agente propone la lectura y clasificación.
- **L1:** una persona revisa y corrige los campos.
- **L2:** una persona confirma antes de guardar.
- **L3:** una persona puede editar producto, categoría, medida, unidad y precio.
- **L4:** la persona conserva la responsabilidad final sobre el inventario.

## Corridas reales

Las evidencias están en [corridas/](corridas/):

- [corrida_02.md](corridas/corrida_02.md): cinco imágenes y 51 productos; permitió detectar el error nan.
- [corrida_03.md](corridas/corrida_03.md): una imagen y diez productos; resultado corregido.
- [corrida_precios_01.md](corridas/corrida_precios_01.md): búsqueda de precio para un balde de albañil con tres fuentes.
- [evidencia_precios_01.png](corridas/evidencia_precios_01.png): captura de la consulta de precios.

## Documentación del proyecto

- [DECISIONES.md](DECISIONES.md): decisiones funcionales, técnicas y correcciones.
- [analisis_economico.md](analisis_economico.md): costos, supuestos y proyección.
- [gobierno_riesgos.md](gobierno_riesgos.md): permisos, riesgos, claves y responsabilidades.

## Seguridad

Las claves de OpenAI y Supabase se configuran como secretos del despliegue. No deben guardarse en el código, prompts, README, capturas ni commits públicos.

Las fotografías originales se conservan en el historial protegido de la aplicación y no forman parte del repositorio público.
