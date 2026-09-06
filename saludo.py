import re
import csv
from pathlib import Path


COLUMNAS = [
    "Producto",
    "Medida",
    "Tipo",
    "Categoría",
    "Cantidad",
    "Unidad",
    "Precio sugerido",
]


CATEGORIAS_POR_PALABRA = {
    # Electricidad e iluminación
    "caño corrugado": "Electricidad e iluminación",
    "reflector": "Electricidad e iluminación",
    "sensor de movimiento": "Electricidad e iluminación",
    "unidad magnética": "Electricidad e iluminación",
    "unidad magneticas": "Electricidad e iluminación",
    "cable de estufa": "Electricidad e iluminación",
    "cables de estufas": "Electricidad e iluminación",
    "cinta aisladora": "Electricidad e iluminación",
    # Gas y calefacción
    "resistencia calefon": "Gas y calefacción",
    "calentador de mate": "Gas y calefacción",
    "calendatdr de mate": "Gas y calefacción",
    "magiclick": "Gas y calefacción",
    "maglickik": "Gas y calefacción",
    "termocupla": "Gas y calefacción",
    "enchufe calefon": "Gas y calefacción",
    "ducha de calefon": "Gas y calefacción",
    "regulador": "Gas y calefacción",
    "regulardor": "Gas y calefacción",
    "flexible de gas": "Gas y calefacción",
    # Sanitarios y plomería
    "extractor": "Sanitarios y plomería",
    "pegamento pvc": "Sanitarios y plomería",
    "cañamo": "Sanitarios y plomería",
    # Pintura
    "pincel": "Pintura",
    "pinceleta": "Pintura",
    "rodillo": "Pintura",
    # Seguridad industrial
    "porta martillo": "Seguridad industrial",
    "faja de seguridad": "Seguridad industrial",
    "auricular de casco": "Seguridad industrial",
    "zapato de seguridad": "Seguridad industrial",
    # Herramientas y accesorios
    "cabo de": "Herramientas y accesorios",
    "sierra circular": "Herramientas y accesorios",
    "piedra de banco": "Herramientas y accesorios",
    "arco cerrucho": "Herramientas y accesorios",
    "puntas biassoni": "Herramientas y accesorios",
    "corta hierro": "Herramientas y accesorios",
    "corta guierro": "Herramientas y accesorios",
    "grifa": "Herramientas y accesorios",
    "grinfa": "Herramientas y accesorios",
    "escuadra": "Herramientas y accesorios",
    # Construcción y albañilería
    "tanza de albañil": "Construcción y albañilería",
    "balde de albañil": "Construcción y albañilería",
    "baldes de albañil": "Construcción y albañilería",
    "precinto": "Construcción y albañilería",
    # Adhesivos, lubricantes y consumibles
    "polvo epoxi": "Adhesivos, lubricantes y consumibles",
    "grasa grafitada": "Adhesivos, lubricantes y consumibles",
    "glicerina": "Adhesivos, lubricantes y consumibles",
    "vela para soldar": "Adhesivos, lubricantes y consumibles",
    # Varios
    "pico de pelota": "Varios",
    # Reglas generales que deben evaluarse al final
    "tanza": "Productos de Jardinería",
    "enchufe": "Electricidad e iluminación",
}


def cargar_catalogo_local():
    """Lee las categorías que el local puede ampliar sin editar el programa."""
    archivo_catalogo = Path(__file__).with_name("catalogo_productos.csv")
    if not archivo_catalogo.exists():
        return []

    with archivo_catalogo.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=";")
        filas = list(lector)

    return sorted(filas, key=lambda fila: len(fila["Palabra clave"]), reverse=True)


CATALOGO_LOCAL = cargar_catalogo_local()


def guardar_categoria_en_catalogo(palabra_clave, categoria):
    """Agrega o actualiza una categoría elegida desde la aplicación."""
    global CATALOGO_LOCAL
    palabra_clave = palabra_clave.strip()
    archivo_catalogo = Path(__file__).with_name("catalogo_productos.csv")
    filas = [fila.copy() for fila in CATALOGO_LOCAL]

    for fila in filas:
        if fila["Palabra clave"].lower() == palabra_clave.lower():
            fila["Categoría"] = categoria
            break
    else:
        filas.append({"Palabra clave": palabra_clave, "Categoría": categoria})

    filas = sorted(filas, key=lambda fila: fila["Palabra clave"].lower())
    with archivo_catalogo.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=["Palabra clave", "Categoría"], delimiter=";")
        escritor.writeheader()
        escritor.writerows(filas)

    CATALOGO_LOCAL = sorted(filas, key=lambda fila: len(fila["Palabra clave"]), reverse=True)


def clasificar_producto(producto):
    """Asigna una categoría conocida o deja el producto pendiente de clasificar."""
    producto_normalizado = producto.lower()
    for fila in CATALOGO_LOCAL:
        if fila["Palabra clave"].lower() in producto_normalizado:
            return fila["Categoría"]
    for palabra, categoria in CATEGORIAS_POR_PALABRA.items():
        if palabra in producto_normalizado:
            return categoria
    return "Sin categoría"


def encontrar_medida(texto):
    """Busca medidas como 3 mm, 20 W, 3/4 o 'de 30'."""
    patron = r"(?:\d+(?:\s+\d+/\d+)?\s*(?:mm|cm|m|w|pulgadas?|[\"'])|\bde\s+\d+\b|\d+/\d+)"
    resultado = re.search(patron, texto, re.IGNORECASE)
    if resultado is None:
        return ""
    return resultado.group(0).strip()


def interpretar_anotacion(anotacion):
    """Convierte una anotación informal en una fila ordenada."""
    coincidencia_lista_medidas = re.search(
        r"^(.*?)\s+(\d+\s*x\s*\d+(?:\s*,\s*\d+\s*x\s*\d+)+)\s*$",
        anotacion,
        re.IGNORECASE,
    )

    if coincidencia_lista_medidas:
        producto = coincidencia_lista_medidas.group(1).strip()
        medidas = re.findall(r"\d+\s*x\s*\d+", coincidencia_lista_medidas.group(2))
        return [
            {
                "Producto": producto,
                "Medida": medida.replace(" ", ""),
                "Tipo": "Sin tipo",
                "Categoría": clasificar_producto(producto),
                "Cantidad": 1,
                "Unidad": "unidad",
                "Precio sugerido": "Sin precio",
            }
            for medida in medidas
        ]

    coincidencia_variantes = re.search(
        r"^(.*?)\s*\(?\s*(\d+)\s+([a-záéíóúñ]+)\s+y\s+(\d+)\s+([a-záéíóúñ]+)\s*\)?\s*$",
        anotacion,
        re.IGNORECASE,
    )
    if coincidencia_variantes:
        producto = coincidencia_variantes.group(1).strip()
        filas = []
        for cantidad, variante in (
            (coincidencia_variantes.group(2), coincidencia_variantes.group(3)),
            (coincidencia_variantes.group(4), coincidencia_variantes.group(5)),
        ):
            filas.append(
                {
                    "Producto": producto,
                    "Medida": "Sin medida",
                    "Tipo": variante,
                    "Categoría": clasificar_producto(producto),
                    "Cantidad": int(cantidad),
                    "Unidad": "unidad",
                    "Precio sugerido": "Sin precio",
                }
            )
        return filas

    coincidencia_cantidad_parentesis = re.search(
        r"\((\d+)(?:\s+([a-záéíóúñ]+))?\)\s*$",
        anotacion,
        re.IGNORECASE,
    )
    coincidencia_cantidad_final = re.search(
        r"(?:\s*-\s*|\s+)(\d+)\s+([a-záéíóúñ]+)\s*$",
        anotacion,
        re.IGNORECASE,
    )

    if coincidencia_cantidad_parentesis:
        cantidad = int(coincidencia_cantidad_parentesis.group(1))
        unidad = coincidencia_cantidad_parentesis.group(2) or "unidad"
        anotacion_sin_cantidad = anotacion[:coincidencia_cantidad_parentesis.start()].strip()
    elif coincidencia_cantidad_final:
        cantidad = int(coincidencia_cantidad_final.group(1))
        unidad = coincidencia_cantidad_final.group(2)
        anotacion_sin_cantidad = anotacion[:coincidencia_cantidad_final.start()].strip()
    else:
        cantidad = 1
        unidad = "unidad"
        anotacion_sin_cantidad = anotacion

    partes = [parte.strip() for parte in anotacion_sin_cantidad.split("-") if parte.strip()]
    coincidencia = re.search(
        r"(?:\d+(?:\s+\d+/\d+)?\s*(?:mm|cm|m|w|pulgadas?|[\"'])|\bde\s+\d+\b|\d+/\d+)",
        anotacion_sin_cantidad,
        re.IGNORECASE,
    )
    raw_medida = coincidencia.group(0).strip() if coincidencia else ""
    medida = re.sub(r"\s*pulgadas?\s*$", '"', raw_medida, flags=re.IGNORECASE)
    medida = re.sub(r"^de\s+", "", medida, flags=re.IGNORECASE)
    medida = re.sub(r"\s*w$", " W", medida, flags=re.IGNORECASE)

    producto = partes[0] if partes else anotacion.strip()
    texto_despues_de_medida = ""
    if coincidencia and partes and raw_medida in partes[0]:
        posicion_medida = partes[0].find(raw_medida)
        producto = partes[0][:posicion_medida].strip()
        texto_despues_de_medida = partes[0][posicion_medida + len(raw_medida):].strip()

    variantes = [variante for variante in partes[1:] if variante not in (raw_medida, medida)]
    if texto_despues_de_medida and len(partes) == 1:
        variantes.append(texto_despues_de_medida)
    tipo = " - ".join(variantes)

    return {
        "Producto": producto,
        "Medida": medida or "Sin medida",
        "Tipo": tipo or "Sin tipo",
        "Categoría": clasificar_producto(producto),
        "Cantidad": cantidad,
        "Unidad": unidad,
        "Precio sugerido": "Sin precio",
    }


def mostrar_tabla(filas):
    """Muestra las filas con las columnas alineadas."""
    anchos = {columna: max(len(columna), *(len(str(fila[columna])) for fila in filas)) for columna in COLUMNAS}
    encabezado = " | ".join(columna.ljust(anchos[columna]) for columna in COLUMNAS)
    separador = "-+-".join("-" * anchos[columna] for columna in COLUMNAS)
    print("\n" + encabezado)
    print(separador)
    for fila in filas:
        print(" | ".join(str(fila[columna]).ljust(anchos[columna]) for columna in COLUMNAS))


def guardar_csv(filas):
    filas_para_csv = []
    for fila in filas:
        fila_csv = fila.copy()
        if fila_csv["Medida"] != "Sin medida":
            fila_csv["Medida"] = f'="{fila_csv["Medida"]}"'
        filas_para_csv.append(fila_csv)
    with open("inventario_organizado.csv", "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(filas_para_csv)


def es_comando_de_ejecucion(texto):
    """Evita guardar como producto las líneas que muestra la terminal."""
    texto_normalizado = texto.lower().replace("/", "\\")
    return (
        "python.exe" in texto_normalizado
        or "python " in texto_normalizado
        or "saludo.py" in texto_normalizado
        or texto_normalizado.startswith("c:\\users\\")
    )


def main():
    print("Escribí una anotación por línea.")
    print("Cuando termines, presioná Enter en una línea vacía.\n")
    filas = []
    while True:
        anotacion = input("> ").strip()
        if not anotacion:
            break
        if es_comando_de_ejecucion(anotacion):
            print("Esa línea es un comando de la terminal y no se guardó.")
            continue
        resultado = interpretar_anotacion(anotacion)
        if isinstance(resultado, list):
            filas.extend(resultado)
        else:
            filas.append(resultado)
    guardar_csv(filas)
    if filas:
        mostrar_tabla(filas)
        print("\nInventario guardado en inventario_organizado.csv")
    else:
        print("No se ingresaron productos. Se creó un CSV vacío con los encabezados.")


if __name__ == "__main__":
    main()
