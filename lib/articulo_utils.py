"""
Utilidades para gestión de artículos
"""
import customtkinter as ctk
from tkinter import messagebox, Toplevel, Listbox, Scrollbar, MULTIPLE, END
import tkinter as tk
from datetime import datetime


class VentanaEstadosArticulo(ctk.CTkToplevel):
    """Ventana para mostrar estados de un artículo con filtros y exportación"""
    
    def __init__(self, parent, referencia, connect_db_func):
        super().__init__(parent)
        
        self.parent_window = parent
        self.referencia = referencia
        self.connect_db = connect_db_func
        self.estados_seleccionados = []
        self.datos_actuales = []
        self.suma_cantidad = 0
        self.suma_total = 0.0
        
        # Configurar ventana
        self.title(f"Estados por Artículo - {referencia}")
        self.geometry("900x700")
        self.resizable(True, True)
        self.minsize(700, 500)
        
        # Aparecer al frente
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        self.after(500, lambda: self.attributes('-topmost', False))
        
        self.crear_interfaz()
        self.cargar_datos()
    
    def crear_interfaz(self):
        """Crea la interfaz de la ventana"""
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=12, pady=12)
        
        # ========== HEADER ==========
        header = ctk.CTkFrame(main)
        header.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            header,
            text=f"Estados para: {self.referencia}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        # Botón de imprimir
        btn_imprimir = ctk.CTkButton(
            header,
            text="🖨️",
            command=lambda: self.imprimir_resultados(),
            width=40,
            height=40,
            font=ctk.CTkFont(size=20),
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        btn_imprimir.grid(row=0, column=1, padx=5, sticky="e")
        
        header.grid_columnconfigure(0, weight=1)
        
        # ========== FILTROS ==========
        filtros_frame = ctk.CTkFrame(main)
        filtros_frame.pack(fill="x", pady=(0, 10))
        
        # Fecha desde
        ctk.CTkLabel(filtros_frame, text="Fecha Desde:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_fecha_desde = ctk.CTkEntry(filtros_frame, placeholder_text="DD/MM/YYYY", width=120)
        self.entry_fecha_desde.grid(row=0, column=1, padx=5, pady=5)
        
        # Fecha hasta
        ctk.CTkLabel(filtros_frame, text="Fecha Hasta:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_fecha_hasta = ctk.CTkEntry(filtros_frame, placeholder_text="DD/MM/YYYY", width=120)
        self.entry_fecha_hasta.grid(row=0, column=3, padx=5, pady=5)
        
        # Selector de estados
        ctk.CTkLabel(filtros_frame, text="Estados:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.btn_seleccionar_estados = ctk.CTkButton(
            filtros_frame,
            text="Seleccionar (Todos)",
            command=self.abrir_selector_estados,
            width=150
        )
        self.btn_seleccionar_estados.grid(row=0, column=5, padx=5, pady=5)
        
        # Botón aplicar filtros
        btn_filtrar = ctk.CTkButton(
            filtros_frame,
            text="🔍 Aplicar Filtros",
            command=self.cargar_datos,
            width=120
        )
        btn_filtrar.grid(row=0, column=6, padx=10, pady=5)
        
        # ========== LISTA DE RESULTADOS ==========
        self.list_frame = ctk.CTkScrollableFrame(main, height=400)
        self.list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # ========== RESUMEN ==========
        self.resumen_frame = ctk.CTkFrame(main)
        self.resumen_frame.pack(fill="x")
    
    def obtener_estados_disponibles(self):
        """Obtiene todos los estados únicos del artículo"""
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT COALESCE(estado_producto, 'Sin estado') as estado
                FROM rma_detalles
                WHERE referencia_articulo = ?
                ORDER BY estado
            """, (self.referencia,))
            estados = [row[0] for row in cur.fetchall()]
            conn.close()
            return estados
        except Exception as e:
            print(f"Error obteniendo estados: {e}")
            return []
    
    def abrir_selector_estados(self):
        """Abre ventana para seleccionar múltiples estados"""
        estados_disponibles = self.obtener_estados_disponibles()
        
        ventana = Toplevel(self)
        ventana.title("Seleccionar Estados")
        ventana.geometry("400x400")
        ventana.transient(self)
        ventana.grab_set()
        
        # Centrar
        ventana.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 200
        ventana.geometry(f"400x400+{x}+{y}")
        
        tk.Label(ventana, text="Seleccione los estados (Ctrl+Click para múltiple):", font=("Arial", 10, "bold")).pack(pady=10)
        
        frame_lista = tk.Frame(ventana)
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(frame_lista)
        scrollbar.pack(side="right", fill="y")
        
        listbox = Listbox(frame_lista, selectmode=MULTIPLE, yscrollcommand=scrollbar.set, font=("Arial", 10))
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Agregar estados
        for estado in estados_disponibles:
            listbox.insert(END, estado)
        
        # Marcar estados previamente seleccionados
        for i, estado in enumerate(estados_disponibles):
            if estado in self.estados_seleccionados:
                listbox.selection_set(i)
        
        def aplicar_seleccion():
            indices = listbox.curselection()
            self.estados_seleccionados = [listbox.get(i) for i in indices]
            
            if self.estados_seleccionados:
                texto = f"Seleccionar ({len(self.estados_seleccionados)})"
            else:
                texto = "Seleccionar (Todos)"
            
            self.btn_seleccionar_estados.configure(text=texto)
            ventana.destroy()
            self.cargar_datos()
        
        btn_frame = tk.Frame(ventana)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Aplicar", command=aplicar_seleccion, width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=ventana.destroy, width=12).pack(side="left", padx=5)
    
    def cargar_datos(self):
        """Carga los datos con filtros aplicados"""
        # Limpiar lista actual
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        # Limpiar resumen
        for widget in self.resumen_frame.winfo_children():
            widget.destroy()
        
        # Construir query con filtros
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            
            # Query base
            sql = """
                SELECT COALESCE(rd.estado_producto, 'Sin estado') as estado,
                       SUM(COALESCE(rd.cantidad_entregada, 0)) as total_cantidad,
                       SUM(COALESCE(rd.cantidad_entregada, 0) * COALESCE(rd.precio_final, rd.precio_unitario, 0)) as total_euros
                FROM rma_detalles rd
                LEFT JOIN rma_maestro rm ON rd.rma_id = rm.id
                WHERE rd.referencia_articulo = ?
            """
            params = [self.referencia]
            
            # Filtro de fecha desde
            fecha_desde = self.entry_fecha_desde.get().strip()
            if fecha_desde:
                try:
                    # Validar formato
                    datetime.strptime(fecha_desde, '%d/%m/%Y')
                    sql += " AND rm.fecha_emision >= ?"
                    # Convertir a formato SQLite (YYYY-MM-DD)
                    fecha_obj = datetime.strptime(fecha_desde, '%d/%m/%Y')
                    params.append(fecha_obj.strftime('%Y-%m-%d'))
                except ValueError:
                    messagebox.showwarning("Fecha inválida", "El formato de 'Fecha Desde' debe ser DD/MM/YYYY")
                    return
            
            # Filtro de fecha hasta
            fecha_hasta = self.entry_fecha_hasta.get().strip()
            if fecha_hasta:
                try:
                    datetime.strptime(fecha_hasta, '%d/%m/%Y')
                    sql += " AND rm.fecha_emision <= ?"
                    fecha_obj = datetime.strptime(fecha_hasta, '%d/%m/%Y')
                    params.append(fecha_obj.strftime('%Y-%m-%d'))
                except ValueError:
                    messagebox.showwarning("Fecha inválida", "El formato de 'Fecha Hasta' debe ser DD/MM/YYYY")
                    return
            
            # Filtro de estados
            if self.estados_seleccionados:
                placeholders = ','.join('?' * len(self.estados_seleccionados))
                sql += f" AND COALESCE(rd.estado_producto, 'Sin estado') IN ({placeholders})"
                params.extend(self.estados_seleccionados)
            
            sql += " GROUP BY rd.estado_producto ORDER BY total_cantidad DESC"
            
            cur.execute(sql, params)
            filas = cur.fetchall()
            conn.close()
            
            self.mostrar_resultados(filas)
            
        except Exception as e:
            print(f"Error cargando datos: {e}")
            messagebox.showerror("Error BD", f"No se pudieron cargar los datos:\n{e}")
    
    def mostrar_resultados(self, filas):
        """Muestra los resultados en la lista"""
        # Cabecera
        head = ctk.CTkFrame(self.list_frame)
        head.pack(fill="x", padx=5, pady=(0, 6))
        head.grid_columnconfigure(0, weight=3, minsize=250)
        head.grid_columnconfigure(1, weight=1, minsize=150)
        head.grid_columnconfigure(2, weight=1, minsize=150)
        
        hf = ctk.CTkFont(weight="bold", size=13)
        ctk.CTkLabel(head, text="ESTADO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkLabel(head, text="CANTIDAD TOTAL", font=hf).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkLabel(head, text="TOTAL (€)", font=hf).grid(row=0, column=2, padx=5, sticky="w")
        
        # Importar función para doble clic
        try:
            from lib.estados_articulo import mostrar_expedientes_por_articulo_y_estado
        except Exception:
            mostrar_expedientes_por_articulo_y_estado = None
        
        # Filas de datos
        suma_cant = 0
        suma_euros = 0.0
        
        for fila in filas:
            estado = fila[0] if fila[0] else '-'
            total_cantidad = int(fila[1]) if fila[1] else 0
            total_euros = float(fila[2]) if fila[2] else 0.0
            
            rf = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            rf.pack(fill="x", padx=5, pady=2)
            rf.grid_columnconfigure(0, weight=3, minsize=250)
            rf.grid_columnconfigure(1, weight=1, minsize=150)
            rf.grid_columnconfigure(2, weight=1, minsize=150)
            
            lbl_e = ctk.CTkLabel(rf, text=estado, anchor="w")
            lbl_e.grid(row=0, column=0, padx=5, sticky="w")
            
            # Doble clic para ver expedientes
            if mostrar_expedientes_por_articulo_y_estado:
                lbl_e.configure(cursor="hand2")
                lbl_e.bind("<Double-Button-1>", lambda e, est=estado: mostrar_expedientes_por_articulo_y_estado(self.parent_window, self.referencia, est))
                rf.bind("<Double-Button-1>", lambda e, est=estado: mostrar_expedientes_por_articulo_y_estado(self.parent_window, self.referencia, est))
            
            ctk.CTkLabel(rf, text=str(total_cantidad), anchor="w").grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(rf, text=f"{total_euros:.2f} €", anchor="w").grid(row=0, column=2, padx=5, sticky="w")
            
            suma_cant += total_cantidad
            suma_euros += total_euros
        
        # Fila resumen
        resumen = ctk.CTkFrame(self.resumen_frame, fg_color="#EFEFEF")
        resumen.pack(fill="x", padx=5, pady=5)
        resumen.grid_columnconfigure(0, weight=3, minsize=250)
        resumen.grid_columnconfigure(1, weight=1, minsize=150)
        resumen.grid_columnconfigure(2, weight=1, minsize=150)
        
        rf = ctk.CTkFont(weight="bold", size=14)
        ctk.CTkLabel(resumen, text="TOTAL", font=rf).grid(row=0, column=0, padx=5, pady=8, sticky="w")
        ctk.CTkLabel(resumen, text=str(suma_cant), font=rf).grid(row=0, column=1, padx=5, pady=8, sticky="w")
        ctk.CTkLabel(resumen, text=f"{suma_euros:.2f} €", font=rf).grid(row=0, column=2, padx=5, pady=8, sticky="w")
        
        # Guardar datos para impresión
        self.datos_actuales = filas
        self.suma_cantidad = suma_cant
        self.suma_total = suma_euros
    
    def imprimir_resultados(self):
        """Genera vista previa e imprime los resultados"""
        try:
            if not self.datos_actuales:
                messagebox.showinfo("Sin datos", "No hay datos para imprimir.\nAsegúrese de que el artículo tiene estados registrados.")
                return
            
            generar_vista_previa_impresion(
                self,
                self.referencia,
                self.datos_actuales,
                self.suma_cantidad,
                self.suma_total,
                self.entry_fecha_desde.get(),
                self.entry_fecha_hasta.get()
            )
        except Exception as e:
            print(f"Error al imprimir: {e}")
            messagebox.showerror("Error de Impresión", f"No se pudo generar la vista previa:\n{str(e)}")


def generar_vista_previa_impresion(parent, referencia, datos, suma_cant, suma_total, fecha_desde, fecha_hasta):
    """Genera una vista previa HTML profesional para imprimir"""
    try:
        import webbrowser
        import tempfile
        import os
        from datetime import datetime
        
        # Generar HTML profesional
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Estados de Artículo - {referencia}</title>
        <style>
            @media print {{
                @page {{ margin: 2cm; }}
                body {{ margin: 0; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 20px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #2196F3;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2196F3;
                margin: 0;
                font-size: 28px;
            }}
            .header h2 {{
                color: #666;
                margin: 10px 0 0 0;
                font-size: 20px;
                font-weight: normal;
            }}
            .info-section {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .info-section p {{
                margin: 5px 0;
                color: #555;
            }}
            .info-section strong {{
                color: #333;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #2196F3;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .total-row {{
                background-color: #e3f2fd;
                font-weight: bold;
                font-size: 16px;
            }}
            .total-row td {{
                padding: 15px 12px;
                border-top: 2px solid #2196F3;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #777;
                font-size: 12px;
            }}
            .no-print {{
                text-align: center;
                margin-top: 20px;
            }}
            .btn-print {{
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
            }}
            .btn-print:hover {{
                background-color: #1976D2;
            }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📦 Estados de Artículo</h1>
                <h2>Referencia: {referencia}</h2>
            </div>
            
            <div class="info-section">
                <p><strong>Fecha de generación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        """
        
        # Agregar información del período filtrado
        if fecha_desde or fecha_hasta:
            html_content += "<p><strong>Período filtrado:</strong> "
            if fecha_desde and fecha_hasta:
                html_content += f"Desde {fecha_desde} hasta {fecha_hasta}"
            elif fecha_desde:
                html_content += f"Desde {fecha_desde} en adelante"
            else:
                html_content += f"Hasta {fecha_hasta}"
            html_content += "</p>"
        else:
            html_content += "<p><strong>Período:</strong> Todos los registros históricos (sin filtro de fecha)</p>"
        
        html_content += """
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Estado</th>
                        <th style="text-align: right;">Cantidad Total</th>
                        <th style="text-align: right;">Total (€)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for fila in datos:
            estado = fila[0] if fila[0] else '-'
            cantidad = int(fila[1]) if fila[1] else 0
            total = float(fila[2]) if fila[2] else 0.0
            
            html_content += f"""
                        <tr>
                            <td>{estado}</td>
                            <td style="text-align: right;">{cantidad}</td>
                            <td style="text-align: right;">{total:.2f} €</td>
                        </tr>
            """
        
        html_content += f"""
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td style="text-align: right;"><strong>{suma_cant}</strong></td>
                        <td style="text-align: right;"><strong>{suma_total:.2f} €</strong></td>
                    </tr>
                </tfoot>
            </table>
            
            <div class="footer">
                <p>Documento generado automáticamente por el Sistema de Gestión de Expedientes</p>
            </div>
        </div>
        
        <div class="no-print">
            <button class="btn-print" onclick="window.print()">🖨️ Imprimir</button>
            <button class="btn-print" onclick="window.close()" style="background-color: #757575;">❌ Cerrar</button>
        </div>
    </body>
    </html>
        """
        
        # Guardar en archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
            f.write(html_content)
            temp_file = f.name
        
        # Abrir en navegador por defecto (no en editor de código)
        import sys
        if sys.platform == 'win32':
            # En Windows, usar el navegador por defecto
            os.startfile(temp_file)
        else:
            # En otros sistemas, usar webbrowser
            webbrowser.open('file://' + os.path.realpath(temp_file))
        
    except Exception as e:
        print(f"Error generando vista previa: {e}")
        import traceback
        traceback.print_exc()
        raise


def mostrar_selector_referencias(articulos_data, parent_window, callback):
    """
    Muestra un diálogo para seleccionar un artículo de la lista en memoria
    
    Args:
        articulos_data: Lista de artículos en memoria
        parent_window: Ventana padre
        callback: Función a llamar con la referencia del artículo seleccionado
    """
    ventana = ctk.CTkToplevel(parent_window)
    ventana.title("Seleccionar Artículo")
    ventana.geometry("600x400")
    ventana.transient(parent_window)
    ventana.grab_set()
    
    # Centrar ventana
    ventana.update_idletasks()
    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (600 // 2)
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (400 // 2)
    ventana.geometry(f"600x400+{x}+{y}")
    
    # Título
    ctk.CTkLabel(
        ventana, 
        text="Seleccione el artículo que desea ver:",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=10)
    
    # Frame con scroll para la lista
    frame_lista = ctk.CTkScrollableFrame(ventana, width=550, height=250)
    frame_lista.pack(padx=10, pady=5, fill="both", expand=True)
    
    # Crear botones para cada artículo
    for articulo in articulos_data:
        referencia = articulo.get('referencia_articulo', 'N/A')
        estado = articulo.get('estado_producto', 'N/A')
        cantidad = articulo.get('cantidad_entregada', 0)
        precio = articulo.get('precio_unitario', 0.0)
        
        try:
            texto = f"{referencia} - {estado} (Cant: {cantidad}, €{float(precio):.2f})"
        except:
            texto = f"{referencia} - {estado} (Cant: {cantidad})"
        
        btn = ctk.CTkButton(
            frame_lista,
            text=texto,
            width=520,
            height=40,
            anchor="w",
            command=lambda ref=referencia: seleccionar_y_cerrar(ref)
        )
        btn.pack(pady=2, padx=5)
    
    def seleccionar_y_cerrar(referencia):
        ventana.destroy()
        callback(referencia)
    
    # Botón cancelar
    ctk.CTkButton(
        ventana,
        text="Cancelar",
        command=ventana.destroy,
        width=100
    ).pack(pady=10)


# ==================== FUNCIONES DE CÁLCULO DE PRECIOS ====================

from lib.logger_config import get_logger

logger = get_logger()


def obtener_descuento_cliente(cliente_nombre, conn):
    """
    Obtiene el descuento configurado para un cliente desde sus condiciones.
    
    Args:
        cliente_nombre: Nombre del cliente
        conn: Conexión a la base de datos
        
    Returns:
        float: Porcentaje de descuento (0-100), o 0.0 si no tiene
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT descuento
            FROM clientes
            WHERE nombre = ?
        """, (cliente_nombre,))
        
        resultado = cursor.fetchone()
        
        if resultado and resultado[0] is not None:
            descuento = float(resultado[0])
            logger.info(f"Descuento obtenido para cliente '{cliente_nombre}': {descuento}%")
            return descuento
        
        logger.info(f"Cliente '{cliente_nombre}' no tiene descuento configurado")
        return 0.0
        
    except Exception as e:
        logger.error(f"Error obteniendo descuento del cliente '{cliente_nombre}': {e}")
        return 0.0


def validar_cliente_sin_descuento(cliente_nombre, conn):
    """
    Verifica si un cliente tiene descuento configurado.
    
    Args:
        cliente_nombre: Nombre del cliente
        conn: Conexión a la base de datos
        
    Returns:
        tuple: (tiene_descuento: bool, descuento: float)
    """
    descuento = obtener_descuento_cliente(cliente_nombre, conn)
    tiene_descuento = descuento > 0
    
    if not tiene_descuento:
        logger.warning(f"Cliente '{cliente_nombre}' sin descuento configurado")
    
    return tiene_descuento, descuento


def calcular_precio_final(precio_unitario, descuento_cliente=0.0, tiene_depreciacion=False, porcentaje_depreciacion=0.0):
    """
    Calcula el precio final aplicando descuento del cliente y depreciación.
    Orden: Precio → Descuento Cliente → Depreciación
    
    Args:
        precio_unitario: Precio original del artículo
        descuento_cliente: Porcentaje de descuento del cliente (0-100)
        tiene_depreciacion: Si el artículo tiene depreciación
        porcentaje_depreciacion: Porcentaje de depreciación (0-100)
        
    Returns:
        float: Precio final calculado
    """
    try:
        precio = float(precio_unitario)
        
        # Paso 1: Aplicar descuento del cliente
        if descuento_cliente > 0:
            precio = precio * (1 - descuento_cliente / 100)
            logger.info(f"Precio después de descuento {descuento_cliente}%: {precio:.2f}€")
        
        # Paso 2: Aplicar depreciación
        if tiene_depreciacion and porcentaje_depreciacion > 0:
            precio = precio * (1 - porcentaje_depreciacion / 100)
            logger.info(f"Precio después de depreciación {porcentaje_depreciacion}%: {precio:.2f}€")
        
        logger.info(f"Precio final calculado: {precio:.2f}€ (Original: {precio_unitario}€, Desc: {descuento_cliente}%, Deprec: {porcentaje_depreciacion}%)")
        
        return round(precio, 2)
        
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculando precio final: {e}")
        return float(precio_unitario) if precio_unitario else 0.0


def calcular_precio_total_articulo(precio_final, cantidad_entregada):
    """
    Calcula el precio total de un artículo (precio final × cantidad).
    
    Args:
        precio_final: Precio final unitario con descuentos aplicados
        cantidad_entregada: Cantidad de unidades entregadas
        
    Returns:
        float: Precio total del artículo
    """
    try:
        precio = float(precio_final)
        cantidad = float(cantidad_entregada)
        total = precio * cantidad
        
        logger.info(f"Precio total: {precio:.2f}€ × {cantidad} = {total:.2f}€")
        
        return round(total, 2)
        
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculando precio total: {e}")
        return 0.0
