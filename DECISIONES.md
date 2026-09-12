# Decisiones del proyecto

## Objetivo

Construir un agente para Ferretería Don Nicola que convierta fotografías de anotaciones manuscritas en un inventario acumulativo, revisable y organizado.

## Decisiones funcionales

### 1. Se descartó el Excel como entrada principal

El proyecto comenzó con un archivo Excel, pero se decidió trabajar directamente con fotografías del cuaderno de inventario.

**Motivo:** las fotos representan el proceso real de trabajo y evitan transcribir manualmente las anotaciones.

### 2. Se permiten varias imágenes por carga

Todas las imágenes subidas en una misma operación se interpretan como un único lote semanal.

**Motivo:** una página puede no alcanzar para registrar todo el inventario.

### 3. El inventario es acumulativo

Cuando el mismo producto aparece nuevamente, se suma la cantidad existente.

La coincidencia se determina por:

- Producto
- Medida
- Variante
- Unidad

### 4. Se incorporó revisión humana

El agente propone los datos, pero la persona puede corregirlos antes de confirmar.

También se permite editar posteriormente:

- Producto
- Categoría
- Medida
- Unidad
- Precio de referencia

**Motivo:** la escritura manuscrita puede ser ambigua y una clasificación o precio incorrecto afecta el inventario.

### 5. Se definieron categorías comerciales

Se utilizan categorías como Electricidad, Sanitarios, Pinturería, Herramientas, Seguridad, Jardinería, Gas, Construcción, Ferretería general, Bulonería y Otros.

Criterios particulares:

- Resistencias y accesorios de calefón: Sanitarios.
- Bisagras y manijas para muebles: Ferretería general, salvo evidencia específica.
- Si la clasificación no es confiable: revisión manual.

### 6. Se agregó historial de cargas

Cada carga conserva la fecha, los productos interpretados y las fotografías originales.

**Motivo:** permitir reconstruir el origen de una decisión y revisar errores posteriores.

### 7. Se agregó análisis de precios online

El sistema consulta fuentes online y calcula un precio de referencia intermedio a partir de los valores encontrados.

También permite modificar manualmente la mediana o precio de referencia cuando no hay resultados adecuados.

### 8. Se priorizó el inventario acumulado

El inventario acumulado es la vista principal. El precio de referencia confirmado en el análisis de precios se refleja allí.

### 9. Se eligió almacenamiento online

Se utiliza Supabase para guardar el inventario, las cargas y los precios.

**Motivo:** conservar la información entre semanas y acceder desde la aplicación desplegada.

## Decisiones técnicas

### 10. Modelo de IA

Se utiliza GPT-5.6 Terra por su equilibrio entre interpretación de imágenes, salida estructurada y costo.

### 11. Salida estructurada

La interpretación utiliza campos definidos:

- Producto
- Categoría
- Medida
- Variante
- Cantidad
- Unidad
- Observaciones
- Requiere revisión

Los valores inciertos no se inventan: se informa “No especificada”, “Revisión manual” o una observación equivalente.

### 12. Seguridad

Las claves de OpenAI y Supabase se configuran como secretos del despliegue y no se guardan en el repositorio público.

### 13. Corrección de valores vacíos

Se normalizaron valores nulos y no finitos para evitar que aparezca `nan` en pantalla o que falle el guardado JSON.

Esta decisión surgió al revisar la carga #18 y se verificó en la carga #19.

### 14. Guardado transaccional

Se reemplazó el guardado fila por fila por una función SQL transaccional llamada aplicar_lote_atomico.

**Motivo:** si falla una inserción o actualización, la base revierte todo el lote y evita un inventario parcialmente actualizado.

La integración se verificó con una nueva carga confirmada correctamente desde la aplicación.

## Supervisión humana

El flujo definido es:

1. El agente interpreta.
2. La persona revisa y corrige.
3. La persona confirma.
4. El sistema guarda y suma al inventario.
5. La persona conserva la responsabilidad final.

## Corridas reales documentadas

Se registraron tres evidencias:

- Carga #18: cinco imágenes y detección del problema `nan`.
- Carga #19: una imagen, diez productos y resultado corregido.
- Análisis de precios: balde de albañil, tres fuentes y precio de referencia.

## Pendientes de entrega

- Completar el análisis económico del uso del modelo.
- Revisar la documentación final del README.
- Validar que todos los secretos permanezcan fuera del repositorio.
