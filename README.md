# Agente de inventario Don Nicola

Aplicación personal para transformar fotografías de anotaciones semanales en un inventario organizado y acumulativo.

## Flujo

1. Cargar una o varias imágenes.
2. GPT-5.6 Terra interpreta el lote completo.
3. Revisar y corregir la tabla antes de confirmarla.
4. Sumar las cantidades al inventario online.
5. Consultar el inventario acumulado y descargarlo como CSV.

## Columnas

- Producto
- Medida
- Variante
- Cantidad
- Unidad
- Observaciones

Un producto se considera repetido cuando coinciden producto, medida, variante y unidad. Si un dato no se distingue, el agente lo marca para revisión manual en lugar de inventarlo.

## Tecnología

- Interfaz: Streamlit
- Interpretación de imágenes: OpenAI Responses API con gpt-5.6-terra
- Almacenamiento: Supabase
- Acceso inicial: contraseña personal

## Estado

Primera versión creada. Falta configurar las claves privadas, crear la tabla de Supabase y publicar la aplicación.

## Seguridad

Las claves se configuran como secretos de la aplicación. Nunca deben guardarse dentro del repositorio.

## Contrato del agente

El contrato está documentado y es utilizado por la aplicación:

- `prompts/system_prompt.md`: rol, objetivo, categorías permitidas, reglas de evidencia, contrato de salida y supervisión humana.
- `prompts/user_prompt.md`: instrucción para interpretar el lote semanal de imágenes.

La aplicación carga estos archivos al iniciar. Si no estuvieran disponibles, conserva un texto de respaldo para evitar que la interfaz falle.

## Supervisión humana L0-L4

- **L0:** el agente propone la lectura y clasificación.
- **L1:** una persona revisa y corrige los campos.
- **L2:** una persona confirma antes de guardar el lote.
- **L3:** una persona puede editar producto, categoría, medida, unidad y precio.
- **L4:** la persona conserva la responsabilidad final sobre el inventario.
