# Iteración técnica — normalización de campos vacíos

## Problema observado

En la carga #18, algunos campos vacíos provenientes de la interpretación de las imágenes aparecieron como `nan` en la tabla y en las observaciones.

Esto afectaba la legibilidad de la salida y podía contaminar el inventario guardado.

## Hipótesis

El valor vacío estaba llegando como un valor nulo de pandas/JSON y no se convertía antes de mostrarlo o persistirlo.

## Corrección aplicada

Se incorporó una normalización previa a la presentación y al guardado:

- valores nulos de texto → cadena vacía o `No especificada`;
- observaciones vacías → cadena vacía;
- categorías no válidas → `Otros`;
- cantidades inválidas o ausentes → revisión manual;
- limpieza de valores no serializables antes de enviar el lote a Supabase.

Además, el prompt exige no inventar datos y marcar los campos dudosos para revisión humana.

## Validación real

La carga #19 se ejecutó después de la corrección:

- **Fecha:** 07/09/2026 03:00 UTC.
- **Entrada:** una fotografía.
- **Resultado:** 10 productos.
- **Resultado observado:** no aparecieron valores `nan` en la tabla visible ni en las observaciones.

La evidencia completa está en [corrida_03.md](corrida_03.md) y en [entrada_corrida_03.jpg](entrada_corrida_03.jpg).

## Conclusión

La iteración muestra un ciclo verificable de mejora:

1. detección de un error real en la carga #18;
2. formulación de una causa probable;
3. corrección de normalización;
4. nueva corrida;
5. validación visual del resultado corregido.

La revisión humana continúa siendo obligatoria antes de guardar cualquier lote.
