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
8. Seleccionar productos para consultar precios online y calcular un precio de referencia.

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

## Instalación y ejecución reproducible

Requisitos: Python 3.11 o superior, una cuenta de OpenAI, un proyecto Supabase y Git.

1. Clonar el repositorio y entrar en la carpeta:
   `git clone https://github.com/agustinposelski/agente-inventario-DonNicola.git`
   `cd agente-inventario-DonNicola`
2. Crear un entorno virtual e instalar dependencias:
   `python -m venv .venv`
   `source .venv/bin/activate` (Linux/macOS) o `.venv\\Scripts\\activate` (Windows).
   `pip install -r requirements.txt`
3. En Supabase, abrir **SQL Editor** y ejecutar [infra/supabase_schema.sql](infra/supabase_schema.sql). El script crea las tablas `inventario`, `cargas_inventario` y `movimientos_inventario`, el bucket privado `inventario-fotos` y la función transaccional `aplicar_lote_atomico`.
4. Crear `.streamlit/secrets.toml` (nunca publicarlo) con estas claves:
   `OPENAI_API_KEY = "..."\nSUPABASE_URL = "https://<proyecto>.supabase.co"\nSUPABASE_SERVICE_KEY = "..."\nAPP_PASSWORD = "..."\n`
5. Iniciar la aplicación:
   `streamlit run app.py`
6. Abrir la URL local que muestra Streamlit y cargar una imagen de prueba. Revisar la tabla, confirmar la carga y verificar el inventario acumulado.

En Streamlit Cloud, las mismas variables se configuran en **Settings → Secrets**. El archivo `.gitignore` excluye `.streamlit/secrets.toml`.

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
- [supabase_schema.sql](supabase_schema.sql): esquema SQL original.
- [infra/supabase_schema.sql](infra/supabase_schema.sql): copia incluida en el paquete reproducible.

## Seguridad

Las claves de OpenAI y Supabase se configuran como secretos del despliegue. No deben guardarse en el código, prompts, README, capturas ni commits públicos.

Las fotografías originales se conservan en el historial protegido de la aplicación y no forman parte del repositorio público.


## Ubicación física

Cada carga se asigna a una ubicación mediante un selector antes de interpretar las imágenes. Las opciones disponibles son **Pasillo**, **Galpón** y **Nonna**. La ubicación se guarda en el inventario, en el historial de movimientos y se puede modificar posteriormente desde el editor del inventario. La migración incluida en [infra/supabase_schema.sql](infra/supabase_schema.sql) asigna **Pasillo** por defecto a los productos existentes.
