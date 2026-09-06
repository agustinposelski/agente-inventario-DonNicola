import base64
import os
import re
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


def guardar_lote(tabla: pd.DataFrame) -> None:
    db = cliente_supabase()
    ahora = datetime.now(timezone.utc).isoformat()

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
            db.table("inventario").update(datos).eq("id", registro["id"]).execute()
        else:
            datos["cantidad"] = cantidad_nueva
            datos["observaciones"] = str(fila["Observaciones"]).strip()
            db.table("inventario").insert(datos).execute()


def cargar_inventario() -> pd.DataFrame:
    db = cliente_supabase()
    respuesta = (
        db.table("inventario")
        .select(
            "producto,categoria,medida,variante,cantidad,unidad,"
            "observaciones,actualizado_en"
        )
        .order("producto")
        .execute()
    )
    columnas = {
        "producto": "Producto",
        "categoria": "Categoría",
        "medida": "Medida",
        "variante": "Variante",
        "cantidad": "Cantidad",
        "unidad": "Unidad",
        "observaciones": "Observaciones",
        "actualizado_en": "Última actualización",
    }
    return pd.DataFrame(respuesta.data).rename(columns=columnas)


st.set_page_config(page_title="Inventario Don Nicola", page_icon="🧰", layout="wide")
st.title("🧰 Inventario Don Nicola")

if not autenticar():
    st.stop()

tab_carga, tab_inventario = st.tabs(["Cargar imágenes", "Inventario acumulado"])

with tab_carga:
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
                    guardar_lote(editada)
                    del st.session_state["lote"]
                    st.success("Lote incorporado correctamente.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo guardar el lote: {error}")

with tab_inventario:
    try:
        inventario = cargar_inventario()
        st.dataframe(inventario, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar inventario en CSV",
            data=inventario.to_csv(index=False).encode("utf-8-sig"),
            file_name="inventario_don_nicola.csv",
            mime="text/csv",
        )
    except Exception as error:
        st.info(f"El inventario online todavía no está configurado: {error}")
