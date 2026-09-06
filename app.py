"""Primera pantalla de Ferretería Don Nicola.

Esta interfaz reutiliza el parser de saludo.py. No reemplaza el programa
original: suma una forma más cómoda de usarlo.
"""

import tkinter as tk
from tkinter import ttk
import base64
import csv
import os
from pathlib import Path
import subprocess

from saludo import COLUMNAS, guardar_categoria_en_catalogo, guardar_csv, interpretar_anotacion


CATEGORIAS_DISPONIBLES = [
    "Electricidad e iluminación",
    "Gas y calefacción",
    "Sanitarios y plomería",
    "Pintura",
    "Seguridad industrial",
    "Herramientas y accesorios",
    "Construcción y albañilería",
    "Adhesivos, lubricantes y consumibles",
    "Productos de Jardinería",
    "Varios",
]

ARCHIVO_PRECIOS = Path(__file__).with_name("precios_productos.csv")
ARCHIVO_STOCK = Path(__file__).with_name("stock_permanente.csv")
ARCHIVO_EXCEL = Path(__file__).with_name("control_inventario_don_nicola.xlsx")


class AplicacionInventario:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Ferretería Don Nicola - Inventario")
        self.ventana.geometry("1080x760")
        self.ventana.minsize(800, 500)

        self.filas = []
        self.producto_a_clasificar = tk.StringVar()
        self.categoria_elegida = tk.StringVar()
        self.producto_para_precio = tk.StringVar()
        self.costo_producto = tk.StringVar()
        self.recargo_producto = tk.StringVar(value="40")
        self.precios_guardados = self.cargar_precios()
        self.crear_interfaz()

    def crear_interfaz(self):
        contenedor = ttk.Frame(self.ventana, padding=18)
        contenedor.pack(fill="both", expand=True)

        ttk.Label(
            contenedor,
            text="Ferretería Don Nicola",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            contenedor,
            text="Pegá una anotación de inventario por línea y presioná Procesar inventario.",
        ).pack(anchor="w", pady=(0, 10))

        self.entrada = tk.Text(contenedor, height=8, font=("Segoe UI", 11), wrap="word")
        self.entrada.pack(fill="x")
        self.entrada.insert(
            "1.0",
            'Tanza 3 mm - cuadrada - 1 rollo\nCaño corrugado PVC - electricidad - 3/4 - 2 rollos',
        )

        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=10)
        ttk.Button(
            acciones,
            text="Procesar inventario",
            command=self.procesar_inventario,
        ).pack(side="left")
        ttk.Button(
            acciones,
            text="Limpiar",
            command=self.limpiar,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(acciones, text="Sumar al stock", command=self.sumar_al_stock).pack(side="left", padx=(8, 0))
        ttk.Button(acciones, text="Ver stock guardado", command=self.ver_stock_guardado).pack(side="left", padx=(8, 0))
        ttk.Button(acciones, text="Exportar a Excel", command=self.exportar_stock_a_excel).pack(side="left", padx=(8, 0))

        tabla_contenedor = ttk.Frame(contenedor)
        tabla_contenedor.pack(fill="both", expand=True)

        self.tabla = ttk.Treeview(tabla_contenedor, columns=COLUMNAS, show="headings")
        for columna in COLUMNAS:
            self.tabla.heading(columna, text=columna)
            self.tabla.column(columna, width=140, minwidth=90, stretch=True)

        barra_vertical = ttk.Scrollbar(tabla_contenedor, orient="vertical", command=self.tabla.yview)
        barra_horizontal = ttk.Scrollbar(tabla_contenedor, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=barra_vertical.set, xscrollcommand=barra_horizontal.set)

        self.tabla.grid(row=0, column=0, sticky="nsew")
        barra_vertical.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        tabla_contenedor.rowconfigure(0, weight=1)
        tabla_contenedor.columnconfigure(0, weight=1)

        self.estado = ttk.Label(contenedor, text="Todavía no se procesó ningún inventario.")
        self.estado.pack(anchor="w", pady=(10, 0))

        clasificacion = ttk.LabelFrame(contenedor, text="Clasificar producto pendiente", padding=10)
        clasificacion.pack(fill="x", pady=(10, 0))
        ttk.Label(clasificacion, text="Producto sin categoría:").grid(row=0, column=0, sticky="w")
        self.selector_producto = ttk.Combobox(
            clasificacion, textvariable=self.producto_a_clasificar, state="readonly", width=32
        )
        self.selector_producto.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Label(clasificacion, text="Categoría:").grid(row=0, column=2, sticky="w")
        self.selector_categoria = ttk.Combobox(
            clasificacion,
            textvariable=self.categoria_elegida,
            values=CATEGORIAS_DISPONIBLES,
            state="readonly",
            width=32,
        )
        self.selector_categoria.grid(row=0, column=3, padx=8, sticky="ew")
        ttk.Button(clasificacion, text="Guardar categoría", command=self.guardar_categoria).grid(
            row=0, column=4, sticky="e"
        )
        clasificacion.columnconfigure(1, weight=1)
        clasificacion.columnconfigure(3, weight=1)

        precios = ttk.LabelFrame(contenedor, text="Calcular precio de venta", padding=10)
        precios.pack(fill="x", pady=(10, 0))
        ttk.Label(precios, text="Producto:").grid(row=0, column=0, sticky="w")
        self.selector_precio = ttk.Combobox(
            precios, textvariable=self.producto_para_precio, state="readonly", width=28
        )
        self.selector_precio.grid(row=0, column=1, padx=8, sticky="ew")
        self.selector_precio.bind("<<ComboboxSelected>>", self.cargar_precio_del_producto)
        ttk.Label(precios, text="Costo ($):").grid(row=0, column=2, sticky="w")
        ttk.Entry(precios, textvariable=self.costo_producto, width=14).grid(row=0, column=3, padx=8)
        ttk.Label(precios, text="Recargo (%):").grid(row=0, column=4, sticky="w")
        ttk.Entry(precios, textvariable=self.recargo_producto, width=8).grid(row=0, column=5, padx=8)
        ttk.Button(precios, text="Calcular", command=self.calcular_precio).grid(row=0, column=6)
        ttk.Button(precios, text="Guardar precio", command=self.guardar_precio).grid(row=0, column=7, padx=(8, 0))
        self.resultado_precio = ttk.Label(precios, text="Ingresá un costo para calcular el precio sugerido.")
        self.resultado_precio.grid(row=1, column=0, columnspan=7, pady=(8, 0), sticky="w")
        precios.columnconfigure(1, weight=1)

    def procesar_inventario(self):
        anotaciones = self.entrada.get("1.0", "end").strip().splitlines()
        self.filas = []

        for anotacion in anotaciones:
            anotacion = anotacion.strip()
            if not anotacion:
                continue

            resultado = interpretar_anotacion(anotacion)
            if isinstance(resultado, list):
                self.filas.extend(resultado)
            else:
                self.filas.append(resultado)

        for fila in self.filas:
            precio = self.precios_guardados.get(fila["Producto"].lower())
            if precio:
                fila["Precio sugerido"] = f'${self.formatear_moneda(float(precio["Precio sugerido"]))}'

        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for fila in self.filas:
            self.tabla.insert("", "end", values=[fila[columna] for columna in COLUMNAS])

        guardar_csv(self.filas)
        pendientes = sorted({fila["Producto"] for fila in self.filas if fila["Categoría"] == "Sin categoría"})
        self.selector_producto["values"] = pendientes
        self.producto_a_clasificar.set(pendientes[0] if pendientes else "")
        productos = sorted({fila["Producto"] for fila in self.filas})
        self.selector_precio["values"] = productos
        self.producto_para_precio.set(productos[0] if productos else "")
        self.cargar_precio_del_producto()
        cantidad = len(self.filas)
        self.estado.config(
            text=f"Se procesaron {cantidad} producto(s). El CSV se guardó automáticamente como inventario_organizado.csv."
        )

    def limpiar(self):
        self.entrada.delete("1.0", "end")
        self.filas = []
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        self.estado.config(text="Podés escribir nuevas anotaciones.")
        self.selector_producto["values"] = []
        self.producto_a_clasificar.set("")
        self.selector_precio["values"] = []
        self.producto_para_precio.set("")
        self.costo_producto.set("")
        self.resultado_precio.config(text="Ingresá un costo para calcular el precio sugerido.")

    def guardar_categoria(self):
        producto = self.producto_a_clasificar.get()
        categoria = self.categoria_elegida.get()
        if not producto or not categoria:
            self.estado.config(text="Elegí un producto pendiente y una categoría antes de guardar.")
            return

        guardar_categoria_en_catalogo(producto, categoria)
        self.procesar_inventario()
        self.categoria_elegida.set("")
        self.estado.config(f'"{producto}" quedó guardado en el catálogo como "{categoria}".')

    def cargar_stock(self):
        if not ARCHIVO_STOCK.exists():
            return []
        with ARCHIVO_STOCK.open(encoding="utf-8-sig", newline="") as archivo:
            return list(csv.DictReader(archivo, delimiter=";"))

    @staticmethod
    def clave_stock(fila):
        return (fila["Producto"].lower(), fila["Medida"], fila["Tipo"], fila["Unidad"].lower())

    def sumar_al_stock(self):
        if not self.filas:
            self.estado.config(text="Primero procesá un inventario para poder sumarlo al stock.")
            return

        stock = self.cargar_stock()
        indice = {self.clave_stock(fila): fila for fila in stock}
        for fila_actual in self.filas:
            clave = self.clave_stock(fila_actual)
            if clave in indice:
                fila_guardada = indice[clave]
                fila_guardada["Cantidad"] = int(fila_guardada["Cantidad"]) + int(fila_actual["Cantidad"])
                if fila_actual["Precio sugerido"] != "Sin precio":
                    fila_guardada["Precio sugerido"] = fila_actual["Precio sugerido"]
            else:
                nueva_fila = {columna: fila_actual[columna] for columna in COLUMNAS}
                stock.append(nueva_fila)
                indice[clave] = nueva_fila

        stock.sort(key=lambda fila: (fila["Categoría"].lower(), fila["Producto"].lower(), fila["Medida"]))
        with ARCHIVO_STOCK.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, delimiter=";")
            escritor.writeheader()
            escritor.writerows(stock)
        self.estado.config(text=f"Se sumaron {len(self.filas)} producto(s) al stock permanente.")

    def ver_stock_guardado(self):
        stock = sorted(self.cargar_stock(), key=lambda fila: (fila["Categoría"].lower(), fila["Producto"].lower(), fila["Medida"]))
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        for fila in stock:
            self.tabla.insert("", "end", values=[fila[columna] for columna in COLUMNAS])
        self.estado.config(text=f"Stock permanente: {len(stock)} producto(s) diferentes.")

    def exportar_stock_a_excel(self):
        if not ARCHIVO_STOCK.exists():
            self.estado.config(text="Todavía no hay stock guardado para exportar a Excel.")
            return
        stock = sorted(self.cargar_stock(), key=lambda fila: (fila["Categoría"].lower(), fila["Producto"].lower(), fila["Medida"]))
        with ARCHIVO_STOCK.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, delimiter=";")
            escritor.writeheader()
            escritor.writerows(stock)
        try:
            self.crear_planilla_excel()
        except subprocess.CalledProcessError:
            self.estado.config(text="No se pudo crear el Excel. Verificá que Microsoft Excel esté instalado.")
            return
        os.startfile(ARCHIVO_EXCEL)
        self.estado.config(text="Se creó y abrió la planilla de control de inventario en Excel.")

    def crear_planilla_excel(self):
        """Crea un Excel ordenado sin instalar programas adicionales."""
        ruta_csv = str(ARCHIVO_STOCK).replace("'", "''")
        ruta_excel = str(ARCHIVO_EXCEL).replace("'", "''")
        script = f'''$ErrorActionPreference = 'Stop'
$csvPath = '{ruta_csv}'
$outputPath = '{ruta_excel}'
$verde = 5401375
$verdeClaro = 156599? 
'''
        # El color se deja escrito dentro del script para que resulte compatible con Excel de Windows.
        script = script.replace("$verdeClaro = 156599?", "$verdeClaro = 15789287") + r'''
$amarillo = 15133678
$borde = 15132390
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$libro = $excel.Workbooks.Add()

try {
    $inventario = $libro.Worksheets.Item(1)
    $inventario.Name = 'Inventario'
    $resumen = $libro.Worksheets.Add()
    $resumen.Name = 'Resumen'
    $guia = $libro.Worksheets.Add()
    $guia.Name = 'Guía rápida'

    $filas = @(Import-Csv -Path $csvPath -Delimiter ';')
    $ultimaFila = [Math]::Max(9, 8 + $filas.Count)

    $inventario.Range('A1:I1').Merge()
    $inventario.Range('A1').Value2 = 'Ferretería Don Nicola | Control de inventario'
    $inventario.Range('A1').Interior.Color = $verde
    $inventario.Range('A1').Font.Color = 16777215
    $inventario.Range('A1').Font.Bold = $true
    $inventario.Range('A1').Font.Size = 18
    $inventario.Rows.Item(1).RowHeight = 30
    $inventario.Range('A2:I2').Merge()
    $inventario.Range('A2').Value2 = 'Stock acumulativo organizado por categoría. La app genera esta planilla automáticamente.'
    $inventario.Range('A2').Font.Italic = $true
    $inventario.Range('A2').Font.Color = 6706501

    $inventario.Range('A4:B4').Merge(); $inventario.Range('D4:E4').Merge(); $inventario.Range('G4:H4').Merge()
    $inventario.Range('A5:B5').Merge(); $inventario.Range('D5:E5').Merge(); $inventario.Range('G5:H5').Merge()
    $inventario.Range('A4').Value2 = 'Productos registrados'
    $inventario.Range('D4').Value2 = 'Unidades en stock'
    $inventario.Range('G4').Value2 = 'Valor estimado'
    $inventario.Range('A5').Formula = '=COUNTA(B9:B500)'
    $inventario.Range('D5').Formula = '=SUM(E9:E500)'
    $inventario.Range('G5').Formula = '=SUM(H9:H500)'
    foreach ($rango in @('A4:B4', 'D4:E4', 'G4:H4')) {
        $inventario.Range($rango).Interior.Color = $verdeClaro
        $inventario.Range($rango).Font.Bold = $true
        $inventario.Range($rango).HorizontalAlignment = -4108
    }
    foreach ($rango in @('A5:B5', 'D5:E5', 'G5:H5')) {
        $inventario.Range($rango).Font.Bold = $true
        $inventario.Range($rango).Font.Size = 16
        $inventario.Range($rango).HorizontalAlignment = -4108
    }
    $inventario.Range('G5').NumberFormat = '$#,##0'

    $encabezados = @('Categoría', 'Producto', 'Medida', 'Tipo', 'Stock actual', 'Unidad', 'Precio sugerido', 'Valor de stock', 'Estado')
    for ($columna = 0; $columna -lt $encabezados.Count; $columna++) {
        $celda = $inventario.Cells.Item(8, $columna + 1)
        $celda.Value2 = $encabezados[$columna]
        $celda.Interior.Color = $verde
        $celda.Font.Color = 16777215
        $celda.Font.Bold = $true
        $celda.HorizontalAlignment = -4108
    }
    $inventario.Rows.Item(8).RowHeight = 26

    $filaExcel = 9
    foreach ($fila in $filas) {
        $inventario.Cells.Item($filaExcel, 1).Value2 = $fila.'Categoría'
        $inventario.Cells.Item($filaExcel, 2).Value2 = $fila.Producto
        $inventario.Cells.Item($filaExcel, 3).Value2 = $fila.Medida
        $inventario.Cells.Item($filaExcel, 4).Value2 = $fila.Tipo
        $inventario.Cells.Item($filaExcel, 5).Value2 = [int]$fila.Cantidad
        $inventario.Cells.Item($filaExcel, 6).Value2 = $fila.Unidad
        $precioTexto = [string]$fila.'Precio sugerido'
        if ($precioTexto -and $precioTexto -ne 'Sin precio') {
            $inventario.Cells.Item($filaExcel, 7).Value2 = [double](($precioTexto -replace '\$', '' -replace '\.', '' -replace ',', '.'))
        }
        $inventario.Cells.Item($filaExcel, 8).Formula = ('=E{0}*G{0}' -f $filaExcel)
        $inventario.Cells.Item($filaExcel, 9).Formula = ('=IF(E{0}=0,"Sin stock",IF(G{0}="","Sin precio","Listo"))' -f $filaExcel)
        $filaExcel++
    }

    $rangoTabla = $inventario.Range("A8:I$ultimaFila")
    $rangoTabla.Borders.LineStyle = 1
    $rangoTabla.Borders.Color = $borde
    $inventario.Range("E9:H$ultimaFila").HorizontalAlignment = -4152
    $inventario.Range("G9:H$ultimaFila").NumberFormat = '$#,##0'
    $inventario.Range("A8:I$ultimaFila").AutoFilter() | Out-Null
    $inventario.Columns.Item(1).ColumnWidth = 26
    $inventario.Columns.Item(2).ColumnWidth = 27
    $inventario.Columns.Item(3).ColumnWidth = 12
    $inventario.Columns.Item(4).ColumnWidth = 18
    $inventario.Columns.Item(5).ColumnWidth = 13
    $inventario.Columns.Item(6).ColumnWidth = 12
    $inventario.Columns.Item(7).ColumnWidth = 16
    $inventario.Columns.Item(8).ColumnWidth = 16
    $inventario.Columns.Item(9).ColumnWidth = 14
    for ($filaEstado = 9; $filaEstado -le $ultimaFila; $filaEstado++) {
        $estado = $inventario.Cells.Item($filaEstado, 9).Text
        if ($estado -eq 'Sin precio') { $inventario.Cells.Item($filaEstado, 9).Interior.Color = $amarillo }
        if ($estado -eq 'Listo') { $inventario.Cells.Item($filaEstado, 9).Interior.Color = $verdeClaro }
    }
    $inventario.Activate()
    $excel.ActiveWindow.SplitRow = 8
    $excel.ActiveWindow.FreezePanes = $true

    $resumen.Range('A1:D1').Merge()
    $resumen.Range('A1').Value2 = 'Resumen por categoría'
    $resumen.Range('A1').Interior.Color = $verde
    $resumen.Range('A1').Font.Color = 16777215
    $resumen.Range('A1').Font.Bold = $true
    $resumen.Range('A1').Font.Size = 16
    $resumen.Rows.Item(1).RowHeight = 30
    $encabezadosResumen = @('Categoría', 'Productos', 'Unidades', 'Valor estimado')
    for ($columna = 0; $columna -lt $encabezadosResumen.Count; $columna++) {
        $resumen.Cells.Item(3, $columna + 1).Value2 = $encabezadosResumen[$columna]
    }
    $resumen.Range('A3:D3').Interior.Color = $verdeClaro
    $resumen.Range('A3:D3').Font.Bold = $true
    $categorias = @($filas | ForEach-Object { $_.'Categoría' } | Where-Object { $_ } | Sort-Object -Unique)
    $filaResumen = 4
    foreach ($categoria in $categorias) {
        $resumen.Cells.Item($filaResumen, 1).Value2 = $categoria
        $resumen.Cells.Item($filaResumen, 2).Formula = ('=COUNTIF(Inventario!$A$9:$A${0},A{1})' -f $ultimaFila, $filaResumen)
        $resumen.Cells.Item($filaResumen, 3).Formula = ('=SUMIF(Inventario!$A$9:$A${0},A{1},Inventario!$E$9:$E${0})' -f $ultimaFila, $filaResumen)
        $resumen.Cells.Item($filaResumen, 4).Formula = ('=SUMIF(Inventario!$A$9:$A${0},A{1},Inventario!$H$9:$H${0})' -f $ultimaFila, $filaResumen)
        $filaResumen++
    }
    $ultimaResumen = [Math]::Max(4, $filaResumen - 1)
    $resumen.Range("A3:D$ultimaResumen").Borders.LineStyle = 1
    $resumen.Range("D4:D$ultimaResumen").NumberFormat = '$#,##0'
    $resumen.Columns.Item(1).ColumnWidth = 30
    $resumen.Columns.Item(2).ColumnWidth = 14
    $resumen.Columns.Item(3).ColumnWidth = 14
    $resumen.Columns.Item(4).ColumnWidth = 18

    $guia.Range('A1:D1').Merge()
    $guia.Range('A1').Value2 = 'Cómo leer la planilla'
    $guia.Range('A1').Interior.Color = $verde
    $guia.Range('A1').Font.Color = 16777215
    $guia.Range('A1').Font.Bold = $true
    $guia.Range('A1').Font.Size = 16
    $pasosGuia = @(
        @('1', 'Inventario', 'Muestra el stock real ordenado por categoría.', 'Precio, valor y estado se calculan solos.'),
        @('2', 'Resumen', 'Agrupa los productos por categoría.', 'Sirve para revisar rápidamente qué tenés.'),
        @('3', 'Sin precio', 'Indica productos que todavía no tienen un precio guardado.', 'Podés cargarlos desde la app.'),
        @('4', 'Próximo paso', 'Seguiremos mejorando este formato.', 'Por ejemplo: alertas de poco stock.')
    )
    for ($filaGuia = 0; $filaGuia -lt $pasosGuia.Count; $filaGuia++) {
        for ($columnaGuia = 0; $columnaGuia -lt $pasosGuia[$filaGuia].Count; $columnaGuia++) {
            $guia.Cells.Item($filaGuia + 3, $columnaGuia + 1).Value2 = $pasosGuia[$filaGuia][$columnaGuia]
        }
    }
    $guia.Range('A3:D6').Borders.LineStyle = 1
    $guia.Range('A3:A6').Interior.Color = $verdeClaro
    $guia.Range('A3:A6').Font.Bold = $true
    $guia.Columns.Item(1).ColumnWidth = 8
    $guia.Columns.Item(2).ColumnWidth = 18
    $guia.Columns.Item(3).ColumnWidth = 43
    $guia.Columns.Item(4).ColumnWidth = 42
    $guia.Range('A3:D6').WrapText = $true
    $guia.Rows('3:6').RowHeight = 34

    if (Test-Path $outputPath) { Remove-Item $outputPath -Force }
    $libro.SaveAs($outputPath, 51)
}
finally {
    $libro.Close($true)
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($guia) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($resumen) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($inventario) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($libro) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
}
'''
        comando = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", comando],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def calcular_precio(self):
        producto = self.producto_para_precio.get()
        try:
            costo = self.convertir_numero(self.costo_producto.get())
            recargo = self.convertir_numero(self.recargo_producto.get())
        except ValueError:
            self.resultado_precio.config(text="Ingresá números válidos para costo y recargo.")
            return

        if not producto or costo <= 0 or recargo < 0:
            self.resultado_precio.config(text="Elegí un producto e ingresá un costo positivo.")
            return

        precio_sugerido = round(costo * (1 + recargo / 100))
        self.resultado_precio.config(
            text=(
                f"{producto}: costo ${self.formatear_moneda(costo)} + {recargo:g}% "
                f"= precio sugerido ${self.formatear_moneda(precio_sugerido)}"
            )
        )

    def cargar_precios(self):
        if not ARCHIVO_PRECIOS.exists():
            return {}
        with ARCHIVO_PRECIOS.open(encoding="utf-8-sig", newline="") as archivo:
            lector = csv.DictReader(archivo, delimiter=";")
            return {fila["Producto"].lower(): fila for fila in lector}

    def cargar_precio_del_producto(self, evento=None):
        producto = self.producto_para_precio.get()
        precio = self.precios_guardados.get(producto.lower())
        if precio:
            self.costo_producto.set(precio["Costo"])
            self.recargo_producto.set(precio["Recargo"])
            self.calcular_precio()

    def guardar_precio(self):
        producto = self.producto_para_precio.get()
        try:
            costo = self.convertir_numero(self.costo_producto.get())
            recargo = self.convertir_numero(self.recargo_producto.get())
        except ValueError:
            self.resultado_precio.config(text="Ingresá números válidos antes de guardar.")
            return

        if not producto or costo <= 0 or recargo < 0:
            self.resultado_precio.config(text="Elegí un producto e ingresá un costo positivo.")
            return

        precio_sugerido = round(costo * (1 + recargo / 100))
        self.precios_guardados[producto.lower()] = {
            "Producto": producto,
            "Costo": f"{costo:g}",
            "Recargo": f"{recargo:g}",
            "Precio sugerido": f"{precio_sugerido:g}",
        }
        with ARCHIVO_PRECIOS.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(
                archivo,
                fieldnames=["Producto", "Costo", "Recargo", "Precio sugerido"],
                delimiter=";",
            )
            escritor.writeheader()
            escritor.writerows(sorted(self.precios_guardados.values(), key=lambda fila: fila["Producto"].lower()))
        self.resultado_precio.config(
            text=f'Precio de "{producto}" guardado: ${self.formatear_moneda(precio_sugerido)}.'
        )
        self.procesar_inventario()
        self.resultado_precio.config(
            text=f'Precio de "{producto}" guardado: ${self.formatear_moneda(precio_sugerido)}.'
        )

    @staticmethod
    def convertir_numero(texto):
        texto = texto.strip().replace("$", "").replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        return float(texto)

    @staticmethod
    def formatear_moneda(valor):
        return f"{valor:,.0f}".replace(",", ".")


if __name__ == "__main__":
    ventana = tk.Tk()
    AplicacionInventario(ventana)
    ventana.mainloop()
