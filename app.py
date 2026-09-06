import base64
import hashlib
import os
import re
import statistics
import unicodedata
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from openai import OpenAI
from pydantic import BaseModel
from supabase import Client, create_client


MODEL = "gpt-5.6-terra"
CATEGORIES = [
    "Electricidad",
    "Sanitarios",
    "Pintura",
    "Herramientas",
    "Seguridad",
    "Jardín",
    "Gas",
    "Construcción",
    "Ferretería general",
    "Otros",
]
COLUMNS = [
    "Producto",
    "Categoría",
    "Medida",
    "Variante",
    "Cantidad",
    "Unidad",
    "Observaciones",
    "Requiere revisión",
]

SYSTEM_PROMPT = """
Sos el agente de inventario de la ferretería Don Nicola.
Analizá todas las imágenes recibidas como un único lote semanal.

Extraé una fila por cada producto y completá: producto, categoría, medida,
variante, cantidad, unidad y observaciones.

Categorías permitidas:
- Electricidad
- Sanitarios
- Pintura
- Herramientas
- Seguridad
- Jardín
- Gas
- Construcción
- Ferretería general
- Otros

Reglas:
- Clasificá cada producto en la categoría más específica de la lista.
- Clasificá los repuestos y accesorios de calefón como "Sanitarios", aunque el artefacto funcione con gas o electricidad.
- No inventes texto ni cantidades.
- Si se anota una cantidad de artículos individuales y no se menciona caja,
  paquete, rollo u otra presentación, usá "unidad".
- Si un dato realmente no se distingue, usá null para cantidad o
  "Revisión manual" para texto, explicá la duda en observaciones y marcá
  requiere_revision=true.
- No marques revisión solo porque la nota omite la palabra "unidad" cuando
  claramente se están contando artículos individuales.
- Separá productos con distinta medida, variante o unidad.
- Unificá duplicados claros dentro del mismo lote sumando sus cantidades.
- Conservá marcas y modelos cuando sean visibles.
- Si una imagen no contiene inventario, no generes filas ficticias.
""".strip()


class FuentePrecio(BaseModel):
    comercio: str
    precio: float
    url: str


class ResultadoPrecio(BaseModel):
    producto_buscado: str
    fuentes: list[FuentePrecio]
    confianza: str
    observaciones: str


class ProductoExtraido(BaseModel):
    producto: str
    categoria: str
    medida: str
    variante: str
    cantidad: float | None
    unidad: str
    observaciones: str
    requiere_revision: bool


class LoteInventario(BaseModel):
    productos: list[ProductoExtraido]


def secreto(nombre: str) -> str | None:
    try:
        return st.secrets[nombre]
    except (KeyError, FileNotFoundError):
        return os.getenv(nombre)


def autenticar() -> bool:
    if st.session_state.get("autenticado"):
        return True

    st.subheader("Acceso personal")
    clave = st.text_input("Contraseña", type="password")
    if st.button("Ingresar", type="primary"):
        clave_configurada = secreto("APP_PASSWORD")
        if clave_configurada and clave == clave_configurada:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta o no configurada.")
    return False


def cliente_supabase() -> Client:
    url = secreto("SUPABASE_URL")
    key = secreto("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("Falta configurar Supabase.")
    return create_client(url, key)


def formatear_ars(valor: object) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    numero = f"{float(valor):,.2f}"
    numero = numero.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {numero}"


def normalizar(texto: object) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto or ""))
    limpio = limpio.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"\s+", " ", limpio)


def clave_producto(fila: pd.Series) -> str:
    campos = [fila["Producto"], fila["Medida"], fila["Variante"], fila["Unidad"]]
    return "|".join(normalizar(valor) for valor in campos)


def imagen_data_url(archivo) -> str:
    mime = archivo.type or "image/jpeg"
    contenido = base64.b64encode(archivo.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{contenido}"


def huella_archivos(archivos) -> str:
    huellas = sorted(hashlib.sha256(archivo.getvalue()).hexdigest() for archivo in archivos)
    combinado = "|".join(huellas).encode("utf-8")
    return hashlib.sha256(combinado).hexdigest()


def guardar_fotos_carga(db: Client, carga_id: int, archivos) -> list[dict]:
    imagenes = []
    bucket = db.storage.from_("inventario-fotos")
    for indice, archivo in enumerate(archivos, start=1):
        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", archivo.name or "")
        if not nombre:
            nombre = f"imagen_{indice}.jpg"
        ruta = f"{carga_id}/{indice}_{nombre}"
        bucket.upload(
            path=ruta,
            file=archivo.getvalue(),
            file_options={
                "content-type": archivo.type or "image/jpeg",
                "upsert": "false",
            },
        )
        imagenes.append(
            {
                "ruta": ruta,
                "nombre": archivo.name or nombre,
                "tipo": archivo.type or "image/jpeg",
            }
        )
    return imagenes


def descargar_foto(ruta: str) -> bytes:
    return cliente_supabase().storage.from_("inventario-fotos").download(ruta)


def interpretar_imagenes(archivos) -> pd.DataFrame:
    api_key = secreto("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY.")

    contenido = [
        {
            "type": "input_text",
            "text": "Interpretá estas imágenes y devolvé el lote de inventario.",
        }
    ]
    for archivo in archivos:
        contenido.append(
            {
                "type": "input_image",
                "image_url": imagen_data_url(archivo),
                "detail": "original",
            }
        )

    client = OpenAI(api_key=api_key)
    respuesta = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": contenido},
        ],
        text_format=LoteInventario,
        store=False,
    )
    lote = respuesta.output_parsed
    if lote is None:
        raise RuntimeError("El modelo no devolvió un inventario válido.")

    filas = []
    for item in lote.productos:
        categoria = item.categoria if item.categoria in CATEGORIES else "Otros"
        filas.append(
            {
                "Producto": item.producto,
                "Categoría": categoria,
                "Medida": item.medida,
                "Variante": item.variante,
                "Cantidad": item.cantidad,
                "Unidad": item.unidad,
                "Observaciones": item.observaciones,
                "Requiere revisión": item.requiere_revision,
            }
        )
    return pd.DataFrame(filas, columns=COLUMNS)


def validar_lote(tabla: pd.DataFrame) -> list[str]:
    errores = []
    for indice, fila in tabla.iterrows():
        numero = indice + 1
        if bool(fila["Requiere revisión"]):
            errores.append(f"Fila {numero}: todavía requiere revisión manual.")
        if not str(fila["Producto"]).strip():
            errores.append(f"Fila {numero}: falta el producto.")
        if str(fila["Categoría"]).strip() not in CATEGORIES:
            errores.append(f"Fila {numero}: seleccioná una categoría válida.")
        try:
            cantidad = float(fila["Cantidad"])
            if cantidad <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errores.append(f"Fila {numero}: la cantidad debe ser mayor que cero.")
    return errores


def combinar_observaciones(anterior: str | None, nueva: str | None) -> str:
    partes = [str(x).strip() for x in (anterior, nueva) if str(x or "").strip()]
    return " | ".join(dict.fromkeys(partes))


def guardar_lote(tabla: pd.DataFrame, huella: str, archivos) -> None:
    db = cliente_supabase()
    ahora = datetime.now(timezone.utc).isoformat()

    duplicada = (
        db.table("cargas_inventario")
        .select("id")
        .eq("huella", huella)
        .eq("estado", "activa")
        .limit(1)
        .execute()
    )
    if duplicada.data:
        raise ValueError(
            "Este mismo grupo de imágenes ya fue confirmado anteriormente."
        )

    carga = (
        db.table("cargas_inventario")
        .insert({"huella": huella, "estado": "activa"})
        .execute()
    )
    carga_id = int(carga.data[0]["id"])

    try:
        imagenes = guardar_fotos_carga(db, carga_id, archivos)
        (
            db.table("cargas_inventario")
            .update({"imagenes": imagenes})
            .eq("id", carga_id)
            .execute()
        )

        for _, fila in tabla.iterrows():
            clave = clave_producto(fila)
            actual = (
                db.table("inventario")
                .select("id,cantidad,observaciones")
                .eq("clave", clave)
                .limit(1)
                .execute()
            )
            cantidad_nueva = float(fila["Cantidad"])
            datos = {
                "clave": clave,
                "producto": str(fila["Producto"]).strip(),
                "categoria": str(fila["Categoría"]).strip(),
                "medida": str(fila["Medida"]).strip(),
                "variante": str(fila["Variante"]).strip(),
                "unidad": str(fila["Unidad"]).strip(),
                "actualizado_en": ahora,
            }

            if actual.data:
                registro = actual.data[0]
                datos["cantidad"] = float(registro["cantidad"]) + cantidad_nueva
                datos["observaciones"] = combinar_observaciones(
                    registro.get("observaciones"), fila["Observaciones"]
                )
                (
                    db.table("inventario")
                    .update(datos)
                    .eq("id", registro["id"])
                    .execute()
                )
            else:
                datos["cantidad"] = cantidad_nueva
                datos["observaciones"] = str(fila["Observaciones"]).strip()
                db.table("inventario").insert(datos).execute()

            movimiento = {
                "carga_id": carga_id,
                "clave": clave,
                "producto": datos["producto"],
                "categoria": datos["categoria"],
                "medida": datos["medida"],
                "variante": datos["variante"],
                "cantidad_agregada": cantidad_nueva,
                "unidad": datos["unidad"],
                "observaciones": str(fila["Observaciones"]).strip(),
            }
            db.table("movimientos_inventario").insert(movimiento).execute()
    except Exception:
        (
            db.table("cargas_inventario")
            .update({"estado": "error"})
            .eq("id", carga_id)
            .execute()
        )
        raise


def actualizar_stock(tabla: pd.DataFrame) -> None:
    db = cliente_supabase()
    ahora = datetime.now(timezone.utc).isoformat()
    for _, fila in tabla.iterrows():
        cantidad = float(fila["Cantidad"])
        if cantidad < 0:
            raise ValueError("La cantidad no puede ser negativa.")
        categoria = str(fila["Categoría"]).strip()
        if categoria not in CATEGORIES:
            raise ValueError("Seleccioná una categoría válida.")
        (
            db.table("inventario")
            .update(
                {
                    "cantidad": cantidad,
                    "categoria": categoria,
                    "actualizado_en": ahora,
                }
            )
            .eq("id", int(fila["ID"]))
            .execute()
        )


def eliminar_productos(ids: list[int]) -> None:
    db = cliente_supabase()
    for identificador in ids:
        db.table("inventario").delete().eq("id", int(identificador)).execute()


def buscar_precio_online(fila: pd.Series) -> ResultadoPrecio:
    api_key = secreto("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY.")

    descripcion = " · ".join(
        str(fila[campo]).strip()
        for campo in ["Producto", "Medida", "Variante"]
        if str(fila.get(campo, "")).strip()
    )
    pedido = f"""
Buscá precios de venta actuales en Argentina para este producto nuevo:
{descripcion}
Categoría: {fila.get("Categoría", "")}

Requisitos:
- Buscá en Mercado Libre Argentina y comercios argentinos confiables.
- Compará solamente productos equivalentes en medida, potencia, variante,
  marca y presentación cuando esos datos estén disponibles.
- Usá precios finales publicados en pesos argentinos y excluí envío,
  cuotas, productos usados y publicaciones sin stock.
- Devolvé entre 2 y 5 fuentes directas cuando existan.
- Cada fuente debe incluir comercio, precio numérico en ARS y URL directa.
- Si no hay coincidencias comparables, devolvé una lista vacía.
- Confianza debe ser Alta, Media o Baja.
""".strip()

    client = OpenAI(api_key=api_key)
    respuesta = client.responses.parse(
        model=MODEL,
        tools=[{"type": "web_search"}],
        tool_choice="required",
        input=pedido,
        text_format=ResultadoPrecio,
        store=False,
    )
    resultado = respuesta.output_parsed
    if resultado is None:
        raise RuntimeError("La búsqueda no devolvió un resultado válido.")
    return resultado


def guardar_resultado_precio(
    producto_id: int,
    resultado: ResultadoPrecio,
) -> dict:
    fuentes = [
        {
            "comercio": fuente.comercio.strip(),
            "precio": float(fuente.precio),
            "url": fuente.url.strip(),
        }
        for fuente in resultado.fuentes
        if float(fuente.precio) > 0 and fuente.url.strip()
    ]
    if not fuentes:
        raise ValueError("No se encontraron publicaciones comparables.")

    valores = [fuente["precio"] for fuente in fuentes]
    confianza = resultado.confianza.strip().capitalize()
    if confianza not in ["Alta", "Media", "Baja"]:
        confianza = "Baja"
    if len(fuentes) == 1:
        confianza = "Baja"

    datos = {
        "precio_min": min(valores),
        "precio_referencia": statistics.median(valores),
        "precio_max": max(valores),
        "moneda": "ARS",
        "fuentes_precio": fuentes,
        "precio_confianza": confianza,
        "precio_actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    (
        cliente_supabase()
        .table("inventario")
        .update(datos)
        .eq("id", int(producto_id))
        .execute()
    )
    datos["fuentes"] = fuentes
    datos["observaciones"] = resultado.observaciones
    return datos


def parsear_precio_manual(valor: object) -> float:
    texto = str(valor or "").strip().replace("$", "").replace(" ", "")
    if not texto:
        raise ValueError("Ingresá un precio.")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") == 1 and len(texto.split(".")[-1]) == 3:
        texto = texto.replace(".", "")
    precio = float(texto)
    if precio <= 0:
        raise ValueError("El precio manual debe ser mayor que cero.")
    return precio


def guardar_precios_manuales(tabla: pd.DataFrame) -> int:
    db = cliente_supabase()
    ahora = datetime.now(timezone.utc).isoformat()
    actualizados = 0
    for _, fila in tabla.iterrows():
        valor = fila.get("Nueva mediana manual", "")
        if not str(valor or "").strip():
            continue
        precio = parsear_precio_manual(valor)
        (
            db.table("inventario")
            .update(
                {
                    "precio_referencia": precio,
                    "moneda": "ARS",
                    "precio_confianza": "Manual",
                    "precio_actualizado_en": ahora,
                }
            )
            .eq("id", int(fila["ID"]))
            .execute()
        )
        actualizados += 1
    return actualizados


def cargar_precios() -> pd.DataFrame:
    respuesta = (
        cliente_supabase()
        .table("inventario")
        .select(
            "id,producto,categoria,medida,variante,precio_min,"
            "precio_referencia,precio_max,moneda,fuentes_precio,"
            "precio_confianza,precio_actualizado_en"
        )
        .order("producto")
        .execute()
    )
    columnas = {
        "id": "ID",
        "producto": "Producto",
        "categoria": "Categoría",
        "medida": "Medida",
        "variante": "Variante",
        "precio_min": "Precio mínimo",
        "precio_referencia": "Precio referencia",
        "precio_max": "Precio máximo",
        "moneda": "Moneda",
        "fuentes_precio": "Fuentes",
        "precio_confianza": "Confianza",
        "precio_actualizado_en": "Precio actualizado",
    }
    return pd.DataFrame(respuesta.data).rename(columns=columnas)


def cargar_historial() -> tuple[list[dict], list[dict]]:
    db = cliente_supabase()
    cargas = (
        db.table("cargas_inventario")
        .select("id,estado,creado_en,deshecho_en,imagenes")
        .order("creado_en", desc=True)
        .execute()
    )
    movimientos = (
        db.table("movimientos_inventario")
        .select(
            "carga_id,producto,categoria,medida,variante,"
            "cantidad_agregada,unidad,observaciones"
        )
        .order("producto")
        .execute()
    )
    return cargas.data, movimientos.data


def deshacer_carga(carga_id: int) -> None:
    db = cliente_supabase()
    carga = (
        db.table("cargas_inventario")
        .select("id,estado")
        .eq("id", carga_id)
        .limit(1)
        .execute()
    )
    if not carga.data or carga.data[0]["estado"] != "activa":
        raise ValueError("Esta carga ya no está activa.")

    movimientos = (
        db.table("movimientos_inventario")
        .select("clave,cantidad_agregada")
        .eq("carga_id", carga_id)
        .execute()
    )

    for movimiento in movimientos.data:
        actual = (
            db.table("inventario")
            .select("id,cantidad")
            .eq("clave", movimiento["clave"])
            .limit(1)
            .execute()
        )
        if not actual.data:
            continue

        registro = actual.data[0]
        cantidad_restante = float(registro["cantidad"]) - float(
            movimiento["cantidad_agregada"]
        )
        if cantidad_restante <= 0:
            db.table("inventario").delete().eq("id", registro["id"]).execute()
        else:
            (
                db.table("inventario")
                .update(
                    {
                        "cantidad": cantidad_restante,
                        "actualizado_en": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", registro["id"])
                .execute()
            )

    (
        db.table("cargas_inventario")
        .update(
            {
                "estado": "deshecha",
                "deshecho_en": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", carga_id)
        .execute()
    )


def cargar_inventario() -> pd.DataFrame:
    db = cliente_supabase()
    respuesta = (
        db.table("inventario")
        .select(
            "id,producto,categoria,medida,variante,cantidad,unidad,"
            "observaciones,precio_referencia,actualizado_en"
        )
        .order("producto")
        .execute()
    )
    columnas = {
        "id": "ID",
        "producto": "Producto",
        "categoria": "Categoría",
        "medida": "Medida",
        "variante": "Variante",
        "cantidad": "Cantidad",
        "unidad": "Unidad",
        "observaciones": "Observaciones",
        "precio_referencia": "Precio de referencia",
        "actualizado_en": "Última actualización",
    }
    return pd.DataFrame(respuesta.data).rename(columns=columnas)


st.set_page_config(
    page_title="Ferretería Don Nicola",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --dn-ink: #263548;
        --dn-burgundy: #5B3035;
        --dn-coral: #D97771;
        --dn-yellow: #F1E45C;
        --dn-cream: #FFFDF0;
        --dn-white: #FFFFFF;
    }
    .stApp {
        background:
            radial-gradient(circle at 100% 0%, rgba(241,228,92,.27), transparent 30rem),
            linear-gradient(180deg, var(--dn-cream) 0%, #ffffff 36rem);
        color: var(--dn-ink);
    }
    [data-testid="stHeader"] { background: rgba(255,253,240,.82); }
    .block-container {
        max-width: 1500px;
        padding-top: 1.25rem;
        padding-bottom: 4rem;
    }
    .dn-hero {
        position: relative;
        min-height: 320px;
        display: flex;
        align-items: center;
        overflow: hidden;
        border: 5px solid var(--dn-ink);
        border-radius: 18px;
        padding: 2.8rem 3rem;
        margin: .4rem 0 1.6rem;
        background-image:
            linear-gradient(90deg, rgba(241,228,92,.99) 0%, rgba(241,228,92,.96) 39%, rgba(241,228,92,.48) 58%, rgba(38,53,72,.08) 76%),
            url("https://raw.githubusercontent.com/agustinposelski/agente-inventario-DonNicola/main/assets/hero-ferreteria.jpg");
        background-size: cover;
        background-position: center;
        box-shadow: 9px 9px 0 rgba(91,48,53,.22);
    }
    .dn-hero::after {
        content: "";
        position: absolute;
        inset: auto 0 0 0;
        height: 10px;
        background: var(--dn-coral);
    }
    .dn-hero-content { position: relative; z-index: 1; max-width: 760px; }
    .dn-kicker {
        display: inline-block;
        padding: .42rem .75rem;
        color: white;
        background: var(--dn-ink);
        border-radius: 4px;
        font-size: .75rem;
        font-weight: 900;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: .9rem;
    }
    .dn-hero h1 {
        color: var(--dn-coral);
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(2.25rem, 5.2vw, 4.65rem);
        font-weight: 900;
        line-height: .94;
        letter-spacing: .02em;
        text-transform: uppercase;
        -webkit-text-stroke: 2px var(--dn-ink);
        text-shadow: 3px 3px 0 rgba(255,255,255,.72);
        margin: 0;
    }
    .dn-slogan {
        display: inline-block;
        color: var(--dn-ink);
        font-size: clamp(1.05rem, 2vw, 1.45rem);
        font-weight: 900;
        font-style: italic;
        margin: 1rem 0 1.25rem;
        padding-bottom: .18rem;
        border-bottom: 4px solid var(--dn-coral);
    }
    .dn-badges { display: flex; flex-wrap: wrap; gap: .45rem; }
    .dn-badge {
        padding: .4rem .7rem;
        color: white;
        border: 2px solid var(--dn-ink);
        background: var(--dn-ink);
        border-radius: 5px;
        font-size: .77rem;
        font-weight: 800;
        letter-spacing: .02em;
        text-transform: uppercase;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: .45rem;
        background: var(--dn-yellow);
        padding: .5rem;
        border: 3px solid var(--dn-ink);
        border-radius: 12px;
        box-shadow: 5px 5px 0 rgba(91,48,53,.18);
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        height: 48px;
        padding: 0 1.15rem;
        border-radius: 7px;
        color: var(--dn-ink);
        font-weight: 800;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: white;
        background: var(--dn-ink);
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: var(--dn-coral);
    }
    .dn-section-intro {
        margin: 1.35rem 0 1rem;
        padding: 1.1rem 1.3rem;
        border: 2px solid var(--dn-ink);
        border-left: 8px solid var(--dn-coral);
        border-radius: 8px;
        background: linear-gradient(90deg, rgba(241,228,92,.42), white);
        box-shadow: 4px 4px 0 rgba(38,53,72,.08);
    }
    .dn-section-intro strong {
        display: block;
        color: var(--dn-ink);
        font-size: 1.15rem;
        margin-bottom: .15rem;
    }
    .dn-section-intro span { color: #475469; }
    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 1rem 1.1rem;
        background: white;
        border: 2px solid var(--dn-ink);
        border-top: 8px solid var(--dn-coral);
        border-radius: 9px;
        box-shadow: 5px 5px 0 rgba(241,228,92,.62);
    }
    [data-testid="stMetricValue"] { color: var(--dn-burgundy); }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        overflow: hidden;
        border: 2px solid var(--dn-ink);
        border-radius: 10px;
        box-shadow: 5px 5px 0 rgba(241,228,92,.38);
    }
    .stButton > button, .stDownloadButton > button {
        min-height: 42px;
        border: 2px solid var(--dn-ink);
        border-radius: 7px;
        font-weight: 800;
        box-shadow: 3px 3px 0 rgba(38,53,72,.12);
    }
    .stButton > button[kind="primary"] {
        background: var(--dn-coral);
        border-color: var(--dn-ink);
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--dn-burgundy);
        border-color: var(--dn-ink);
    }
    h2, h3 { color: var(--dn-ink); }
    h2 { border-bottom: 4px solid var(--dn-yellow); padding-bottom: .25rem; }
    hr { border-color: rgba(38,53,72,.18); }
    @media (max-width: 760px) {
        .block-container { padding: .75rem .8rem 3rem; }
        .dn-hero {
            min-height: 300px;
            padding: 1.7rem 1.25rem;
            background-position: 67% center;
            border-width: 3px;
        }
        .dn-hero-content { max-width: 88%; }
        .dn-hero h1 {
            font-size: clamp(2rem, 12vw, 3.25rem);
            -webkit-text-stroke: 1px var(--dn-ink);
        }
        .dn-badge { font-size: .66rem; }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            padding: 0 .65rem;
            font-size: .78rem;
        }
    }
    </style>
    <section class="dn-hero">
        <div class="dn-hero-content">
            <span class="dn-kicker">Ferretería de confianza</span>
            <h1>Ferretería<br>Don Nicola</h1>
            <p class="dn-slogan">“Nunca te abandona”</p>
            <div class="dn-badges">
                <span class="dn-badge">Pinturería</span>
                <span class="dn-badge">Electricidad</span>
                <span class="dn-badge">Bulonería</span>
                <span class="dn-badge">Sanitarios</span>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if not autenticar():
    st.stop()

tab_inventario, tab_carga, tab_precios, tab_historial = st.tabs(
    [
        "Inventario acumulado",
        "Cargar imágenes",
        "Análisis de precios",
        "Historial de cargas",
    ]
)

with tab_carga:
    st.markdown(
        '<div class="dn-section-intro"><strong>Cargar nuevo inventario</strong>'
        '<span>Subí las fotos de tus anotaciones y revisá los datos antes de sumarlos.</span></div>',
        unsafe_allow_html=True,
    )
    archivos = st.file_uploader(
        "Subí una o varias imágenes del inventario",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )
    if archivos:
        st.image(archivos, width=180)

    if st.button("Interpretar imágenes", type="primary", disabled=not archivos):
        try:
            with st.spinner("Interpretando el inventario..."):
                st.session_state["lote"] = interpretar_imagenes(archivos)
                st.session_state["huella_lote"] = huella_archivos(archivos)
        except Exception as error:
            st.error(f"No se pudo interpretar el lote: {error}")

    if "lote" in st.session_state:
        st.subheader("Revisar antes de confirmar")
        editada = st.data_editor(
            st.session_state["lote"],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_lote",
            column_config={
                "Categoría": st.column_config.SelectboxColumn(
                    "Categoría",
                    options=CATEGORIES,
                    required=True,
                ),
                "Requiere revisión": st.column_config.CheckboxColumn(
                    "Requiere revisión",
                    help="Desmarcá esta casilla después de corregir las dudas de la fila.",
                ),
            },
        )
        if st.button("Confirmar y sumar al inventario"):
            errores = validar_lote(editada)
            if errores:
                for error in errores:
                    st.warning(error)
            else:
                try:
                    guardar_lote(
                        editada,
                        st.session_state.get("huella_lote", ""),
                        archivos,
                    )
                    del st.session_state["lote"]
                    st.session_state.pop("huella_lote", None)
                    st.success("Lote incorporado correctamente.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo guardar el lote: {error}")

with tab_inventario:
    st.markdown(
        '<div class="dn-section-intro"><strong>Panel principal</strong>'
        '<span>Consultá el stock, corregí cantidades y organizá los productos por rubro.</span></div>',
        unsafe_allow_html=True,
    )
    try:
        inventario = cargar_inventario()
        if inventario.empty:
            st.info("El inventario todavía está vacío.")
        else:
            inventario["Categoría"] = inventario["Categoría"].fillna("Otros")
            extras = sorted(
                set(inventario["Categoría"].astype(str)) - set(CATEGORIES)
            )
            categorias_presentes = [
                categoria
                for categoria in CATEGORIES + extras
                if (inventario["Categoría"] == categoria).any()
            ]

            resumen_productos, resumen_categorias, resumen_precios = st.columns(3)
            resumen_productos.metric("Productos registrados", len(inventario))
            resumen_categorias.metric("Categorías activas", len(categorias_presentes))
            con_precio = int(inventario["Precio de referencia"].notna().sum())
            resumen_precios.metric("Productos con precio", con_precio)

            secciones = []
            for categoria in categorias_presentes:
                seccion = inventario[inventario["Categoría"] == categoria].copy()
                seccion = seccion.sort_values(
                    ["Producto", "Medida", "Variante"],
                    key=lambda columna: columna.astype(str).str.lower(),
                )
                secciones.append(seccion.copy())
                seccion["Precio de referencia"] = seccion[
                    "Precio de referencia"
                ].apply(formatear_ars)
                seccion["Eliminar"] = False

                st.subheader(f"{categoria} ({len(seccion)})")
                editada = st.data_editor(
                    seccion,
                    use_container_width=True,
                    hide_index=True,
                    key=f"editor_stock_{normalizar(categoria)}",
                    disabled=[
                        columna
                        for columna in seccion.columns
                        if columna not in ["Categoría", "Cantidad", "Eliminar"]
                    ],
                    column_config={
                        "ID": None,
                        "Categoría": st.column_config.SelectboxColumn(
                            "Categoría",
                            options=CATEGORIES,
                            required=True,
                            help="Cambiá la categoría y guardá para mover el producto.",
                        ),
                        "Cantidad": st.column_config.NumberColumn(
                            "Cantidad",
                            min_value=0.0,
                            required=True,
                            help="Modificá este valor para corregir el stock.",
                        ),
                        "Eliminar": st.column_config.CheckboxColumn(
                            "Eliminar",
                            help="Marcá únicamente los productos que quieras eliminar.",
                        ),
                    },
                )

                guardar, eliminar = st.columns(2)
                with guardar:
                    if st.button(
                        "Guardar cambios",
                        key=f"guardar_{normalizar(categoria)}",
                    ):
                        actualizar_stock(editada)
                        st.success(f"Productos de {categoria} actualizados.")
                        st.rerun()

                ids_eliminar = [
                    int(valor)
                    for valor in editada.loc[editada["Eliminar"], "ID"].tolist()
                ]
                with eliminar:
                    if st.button(
                        "Eliminar seleccionados",
                        key=f"eliminar_{normalizar(categoria)}",
                        disabled=not ids_eliminar,
                    ):
                        eliminar_productos(ids_eliminar)
                        st.success("Productos eliminados.")
                        st.rerun()

            inventario_ordenado = pd.concat(secciones, ignore_index=True).drop(
                columns=["ID"], errors="ignore"
            )
            st.download_button(
                "Descargar inventario en CSV",
                data=inventario_ordenado.to_csv(index=False).encode("utf-8-sig"),
                file_name="inventario_don_nicola.csv",
                mime="text/csv",
            )
    except Exception as error:
        st.info(f"No se pudo cargar o modificar el inventario: {error}")

with tab_precios:
    st.markdown(
        '<div class="dn-section-intro"><strong>Análisis de precios</strong>'
        '<span>Compará valores online y ajustá manualmente el precio de referencia.</span></div>',
        unsafe_allow_html=True,
    )
    try:
        precios = cargar_precios()
        if precios.empty:
            st.info("El inventario todavía está vacío.")
        else:
            st.caption(
                "Buscá precios online o completá manualmente la mediana. "
                "Cada búsqueda online utiliza crédito de la API."
            )

            ultimos = st.session_state.get("ultimos_precios", [])
            if ultimos:
                st.subheader("Últimos resultados online")
                for resultado in ultimos:
                    with st.expander(resultado["producto"], expanded=True):
                        st.write(
                            "Referencia: "
                            + formatear_ars(resultado["precio_referencia"])
                        )
                        st.write(
                            "Rango: "
                            + formatear_ars(resultado["precio_min"])
                            + " – "
                            + formatear_ars(resultado["precio_max"])
                        )
                        st.write(f"Confianza: {resultado['precio_confianza']}")
                        if resultado.get("observaciones"):
                            st.caption(resultado["observaciones"])
                        for fuente in resultado["fuentes"]:
                            texto_fuente = (
                                f"- [{fuente['comercio']}]"
                                f"({fuente['url']}): "
                                f"{formatear_ars(fuente['precio'])}"
                            )
                            st.markdown(texto_fuente)

            precios["Categoría"] = precios["Categoría"].fillna("Otros")
            extras = sorted(
                set(precios["Categoría"].astype(str)) - set(CATEGORIES)
            )
            categorias_precios = [
                categoria
                for categoria in CATEGORIES + extras
                if (precios["Categoría"] == categoria).any()
            ]

            for categoria in categorias_precios:
                seccion = precios[precios["Categoría"] == categoria].copy()
                seccion = seccion.sort_values(
                    ["Producto", "Medida", "Variante"],
                    key=lambda columna: columna.astype(str).str.lower(),
                )
                editor = seccion[
                    [
                        "ID",
                        "Producto",
                        "Medida",
                        "Variante",
                        "Precio mínimo",
                        "Precio referencia",
                        "Precio máximo",
                        "Confianza",
                    ]
                ].copy()
                editor["Precio mínimo"] = editor["Precio mínimo"].apply(
                    formatear_ars
                )
                editor["Precio referencia"] = editor[
                    "Precio referencia"
                ].apply(formatear_ars)
                editor["Precio máximo"] = editor["Precio máximo"].apply(
                    formatear_ars
                )
                editor["Nueva mediana manual"] = ""
                editor["Buscar online"] = False

                st.subheader(f"{categoria} ({len(editor)})")
                editada = st.data_editor(
                    editor,
                    use_container_width=True,
                    hide_index=True,
                    key=f"editor_precios_{normalizar(categoria)}",
                    disabled=[
                        "Producto",
                        "Medida",
                        "Variante",
                        "Precio mínimo",
                        "Precio referencia",
                        "Precio máximo",
                        "Confianza",
                    ],
                    column_config={
                        "ID": None,
                        "Nueva mediana manual": st.column_config.TextColumn(
                            "Nueva mediana manual",
                            help="Ejemplos: 60000 o 60.000,50",
                        ),
                        "Buscar online": st.column_config.CheckboxColumn(
                            "Buscar online"
                        ),
                    },
                )

                elegidos = editada[editada["Buscar online"]]
                nuevos_manuales = editada[
                    editada["Nueva mediana manual"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .ne("")
                ]

                buscar_col, manual_col = st.columns(2)
                with buscar_col:
                    if st.button(
                        "Buscar seleccionados",
                        key=f"buscar_precios_{normalizar(categoria)}",
                        disabled=elegidos.empty,
                    ):
                        if len(elegidos) > 5:
                            st.warning(
                                "Seleccioná como máximo 5 productos por tanda."
                            )
                        else:
                            resultados = []
                            for _, producto in elegidos.iterrows():
                                try:
                                    with st.spinner(
                                        f"Buscando {producto['Producto']}..."
                                    ):
                                        resultado = buscar_precio_online(producto)
                                        datos = guardar_resultado_precio(
                                            int(producto["ID"]),
                                            resultado,
                                        )
                                        resultados.append(
                                            {
                                                "producto": producto["Producto"],
                                                **datos,
                                            }
                                        )
                                except Exception as error:
                                    st.warning(
                                        f"{producto['Producto']}: {error}"
                                    )
                            st.session_state["ultimos_precios"] = resultados
                            st.session_state.pop(
                                f"editor_precios_{normalizar(categoria)}",
                                None,
                            )
                            if resultados:
                                st.rerun()

                with manual_col:
                    if st.button(
                        "Guardar medianas manuales",
                        key=f"guardar_manuales_{normalizar(categoria)}",
                        disabled=nuevos_manuales.empty,
                    ):
                        cantidad = guardar_precios_manuales(nuevos_manuales)
                        st.session_state.pop(
                            f"editor_precios_{normalizar(categoria)}",
                            None,
                        )
                        if cantidad:
                            st.success(
                                f"{cantidad} precio(s) manual(es) guardado(s)."
                            )
                            st.rerun()

            con_fuentes = precios[
                precios["Fuentes"].apply(
                    lambda valor: isinstance(valor, list) and bool(valor)
                )
            ]
            if not con_fuentes.empty:
                st.subheader("Fuentes guardadas")
                categorias_fuentes = [
                    categoria
                    for categoria in CATEGORIES + extras
                    if (con_fuentes["Categoría"] == categoria).any()
                ]
                for categoria in categorias_fuentes:
                    st.markdown(f"### {categoria}")
                    fuentes_categoria = con_fuentes[
                        con_fuentes["Categoría"] == categoria
                    ].sort_values(
                        ["Producto", "Medida", "Variante"],
                        key=lambda columna: columna.astype(str).str.lower(),
                    )
                    for _, fila in fuentes_categoria.iterrows():
                        partes = [
                            str(fila[campo]).strip()
                            for campo in ["Producto", "Medida", "Variante"]
                            if str(fila.get(campo, "")).strip()
                        ]
                        titulo_fuentes = " · ".join(partes)
                        with st.expander(titulo_fuentes):
                            for fuente in fila["Fuentes"]:
                                texto_fuente = (
                                    f"- [{fuente.get('comercio', 'Fuente')}]"
                                    f"({fuente.get('url', '')}): "
                                    f"{formatear_ars(fuente.get('precio', 0))}"
                                )
                                st.markdown(texto_fuente)
    except Exception as error:
        st.info(f"No se pudo cargar el análisis de precios: {error}")


with tab_historial:
    st.markdown(
        '<div class="dn-section-intro"><strong>Historial de cargas</strong>'
        '<span>Revisá cada ingreso, sus productos y las fotografías originales.</span></div>',
        unsafe_allow_html=True,
    )
    try:
        cargas, movimientos = cargar_historial()
        if not cargas:
            st.info(
                "El historial comenzará con la próxima carga que confirmes."
            )
        else:
            for carga in cargas:
                carga_id = int(carga["id"])
                detalle = [
                    movimiento
                    for movimiento in movimientos
                    if int(movimiento["carga_id"]) == carga_id
                ]
                fecha = pd.to_datetime(carga["creado_en"]).strftime(
                    "%d/%m/%Y %H:%M UTC"
                )
                estado = str(carga["estado"]).capitalize()
                titulo = (
                    f"Carga #{carga_id} · {fecha} · "
                    f"{len(detalle)} productos · {estado}"
                )

                with st.expander(titulo, expanded=False):
                    imagenes = carga.get("imagenes") or []
                    if imagenes:
                        st.caption("Fotos originales")
                        columnas_fotos = st.columns(min(3, len(imagenes)))
                        for indice, imagen in enumerate(imagenes):
                            try:
                                contenido_foto = descargar_foto(imagen["ruta"])
                                columnas_fotos[indice % len(columnas_fotos)].image(
                                    contenido_foto,
                                    caption=imagen.get("nombre", "Imagen"),
                                    width=240,
                                )
                            except Exception:
                                columnas_fotos[indice % len(columnas_fotos)].warning(
                                    "No se pudo abrir esta imagen."
                                )

                    if detalle:
                        tabla_detalle = pd.DataFrame(detalle).rename(
                            columns={
                                "producto": "Producto",
                                "categoria": "Categoría",
                                "medida": "Medida",
                                "variante": "Variante",
                                "cantidad_agregada": "Cantidad agregada",
                                "unidad": "Unidad",
                                "observaciones": "Observaciones",
                            }
                        )
                        tabla_detalle = tabla_detalle.drop(
                            columns=["carga_id"], errors="ignore"
                        )
                        st.dataframe(
                            tabla_detalle,
                            use_container_width=True,
                            hide_index=True,
                        )

                    if carga["estado"] == "activa":
                        confirmar = st.checkbox(
                            "Confirmo que quiero deshacer esta carga",
                            key=f"confirmar_deshacer_{carga_id}",
                        )
                        if st.button(
                            "Deshacer carga",
                            key=f"deshacer_{carga_id}",
                            disabled=not confirmar,
                        ):
                            deshacer_carga(carga_id)
                            st.success(
                                "Carga deshecha y cantidades descontadas."
                            )
                            st.rerun()
    except Exception as error:
        st.info(f"No se pudo cargar el historial: {error}")

