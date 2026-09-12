# Gobierno, permisos y riesgos

## Propósito

Este documento define cómo se controla el agente de inventario de Ferretería Don Nicola, qué riesgos existen y qué intervención humana es obligatoria antes de considerar válida una salida.

## Responsables

| Rol | Responsabilidad |
|---|---|
| Propietario y usuario del inventario | Carga fotografías, revisa resultados, confirma lotes y corrige datos. |
| Responsable final | La misma persona propietaria del inventario firma la confirmación final. |
| Administrador técnico | Configura secretos, despliegue, Supabase y cambios de código. En esta versión también es el propietario del proyecto. |
| Proveedor de servicios | OpenAI procesa la solicitud del modelo y Supabase almacena los datos según la configuración de las cuentas. |

No se permite que una salida del modelo se convierta automáticamente en un registro definitivo sin confirmación humana.

## Permisos

### Aplicación

- Acceso protegido mediante contraseña.
- Uso inicial personal, sin cuentas de terceros.
- Solo el usuario autorizado debe cargar imágenes, confirmar lotes y editar el inventario.

### GitHub

- El repositorio es público para fines académicos.
- El código puede ser visible, pero nunca deben publicarse claves, tokens, contraseñas ni datos privados.
- Los cambios de código deben revisarse antes de desplegarse.

### OpenAI y Supabase

- Las claves se guardan como secretos del despliegue.
- No se escriben en app.py, README, prompts ni capturas.
- El acceso a Supabase debe limitarse a las operaciones necesarias para leer y actualizar el inventario.
- Si se agregan más usuarios, se debe incorporar autenticación individual y políticas de acceso por usuario.

## Datos tratados

El sistema procesa:

- Fotografías de anotaciones manuscritas.
- Productos, cantidades, medidas, categorías y unidades.
- Precios de referencia y fuentes online.
- Fecha de cada carga.

Las fotografías pueden contener información del negocio. Por eso no deben compartirse fuera del propósito del inventario ni incluirse públicamente en GitHub.

## Riesgos y controles

| Riesgo | Consecuencia | Control |
|---|---|---|
| Lectura incorrecta de una palabra | Producto mal identificado | Revisión humana y posibilidad de editar el nombre. |
| Cantidad ilegible | Stock incorrecto | Marcar revisión manual; no inventar cantidades. |
| Medida o unidad confundida | Se mezclan productos distintos | Mantener producto, medida, variante y unidad como clave de coincidencia. |
| Categoría incorrecta | Inventario desordenado | Permitir editar la categoría antes o después de guardar. |
| Valores vacíos o nan | Fallo de guardado o salida confusa | Normalizar valores nulos y validar números antes de persistir. |
| Precio online desactualizado | Precio de referencia incorrecto | Mostrar fuentes, fecha, rango y permitir modificar manualmente la mediana. |
| Fuente online no comparable | Comparación engañosa | Registrar observaciones y excluir variantes no equivalentes. |
| Duplicación de una carga | Stock inflado | Revisar el historial antes de confirmar y conservar fecha/lote. |
| Clave expuesta | Uso no autorizado y costo inesperado | Secretos fuera del repositorio y rotación inmediata ante sospecha. |
| Caída de OpenAI o Supabase | El proceso no termina | Mostrar error; la función SQL transaccional revierte cambios del lote y permite reintentar con revisión. |
| Imagen privada compartida públicamente | Exposición de información | Mantener las fotos en el almacenamiento protegido y no subirlas al repositorio. |

## Supervisión humana L0–L4

- **L0 — Propuesta:** el agente interpreta las imágenes y propone campos estructurados.
- **L1 — Revisión:** la persona revisa producto, categoría, medida, variante, cantidad, unidad y observaciones.
- **L2 — Confirmación:** la persona presiona confirmar antes de sumar el lote al inventario.
- **L3 — Corrección posterior:** la persona puede editar nombre, categoría, medida, unidad y precio de referencia.
- **L4 — Responsabilidad:** la persona propietaria decide qué dato queda válido y responde por el inventario final.

El sistema no publica productos ni toma decisiones comerciales irreversibles sin una acción explícita del usuario.

## Procedimiento ante errores

1. No confirmar el lote si hay datos dudosos.
2. Corregir el registro o marcarlo como “Revisión manual”.
3. Si el lote ya fue guardado, editar el producto desde el inventario o corregirlo en el historial.
4. Si hubo duplicación, detener nuevas cargas y revisar el lote afectado.
5. Si se sospecha exposición de una clave, revocarla y generar una nueva.
6. Documentar el incidente en DECISIONES.md si modifica el funcionamiento del agente.

## Criterio de aceptación

Una corrida se considera válida cuando:

- La entrada está conservada.
- La salida estructurada fue revisada.
- Los datos inciertos fueron corregidos o marcados.
- La persona confirmó explícitamente el lote.
- La fecha y el resultado pueden reconstruirse desde el historial.
