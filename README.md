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
