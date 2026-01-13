"""
Módulo para estadísticas de artículos con filtros por resultado de expediente y estado de artículo
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog, Toplevel, Listbox, Scrollbar, MULTIPLE, END
import pandas as pd
from lib.logger_config import get_logger

logger = get_logger()


def mostrar_estadisticas_articulos(ventana_principal):
    """
    Muestra estadísticas de artículos con filtros y cálculo de suma total en euros.
    
    Args:
        ventana_principal: Instancia de VentanaPrincipal con acceso a main_stats_frame y master
    """
    # Limpiar el frame principal
    ventana_principal.limpiar_marco_stats()
    
    # Título
    ctk.CTkLabel(
        ventana_principal.main_stats_frame, 
        text="📦 ESTADÍSTICAS DE ARTÍCULOS", 
        font=ctk.CTkFont(size=18, weight="bold")
    ).pack(pady=20)
    
    # Obtener conexión a la base de datos
    conn, cursor = ventana_principal.master.conectar_db()
    if not conn:
        ctk.CTkLabel(
            ventana_principal.main_stats_frame, 
            text="Error al conectar con la base de datos.", 
            text_color="red"
        ).pack(pady=20)
        return
    
    cursor = conn.cursor()
    
    # Obtener valores únicos para los filtros
    try:
        # Estados de artículos únicos
        cursor.execute("""
            SELECT DISTINCT estado_producto 
            FROM rma_detalles 
            WHERE estado_producto IS NOT NULL AND estado_producto != ''
            ORDER BY estado_producto ASC
        """)
        estados_articulos = ["Todos"] + [fila[0] for fila in cursor.fetchall()]
        
        # Resultados de expedientes únicos
        cursor.execute("""
            SELECT DISTINCT resultado_expediente 
            FROM rma_maestro 
            WHERE resultado_expediente IS NOT NULL AND resultado_expediente != ''
            ORDER BY resultado_expediente ASC
        """)
        resultados_expedientes = ["Todos"] + [fila[0] for fila in cursor.fetchall()]
        
    except Exception as e:
        print(f"Error al obtener valores de filtros: {e}")
        estados_articulos = ["Todos"]
        resultados_expedientes = ["Todos"]
    
    # Frame de filtros
    filtros_frame = ctk.CTkFrame(ventana_principal.main_stats_frame)
    filtros_frame.pack(fill="x", padx=20, pady=10)
    
    # Variable para almacenar estados seleccionados
    estados_seleccionados = []
    
    # Fila 1: Filtros de resultado y estado
    ctk.CTkLabel(filtros_frame, text="Resultado del Expediente:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    filtro_resultado = ctk.CTkOptionMenu(filtros_frame, values=resultados_expedientes)
    filtro_resultado.set("Todos")
    filtro_resultado.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    
    # Selector múltiple de estados con botón
    ctk.CTkLabel(filtros_frame, text="Estado del Artículo:").grid(row=0, column=2, padx=10, pady=5, sticky="w")
    
    btn_seleccionar_estados = ctk.CTkButton(
        filtros_frame,
        text="Seleccionar Estados (Todos)",
        command=lambda: abrir_selector_estados(estados_articulos, estados_seleccionados, btn_seleccionar_estados, cargar_datos_wrapper),
        fg_color="#6b7280",
        hover_color="#4b5563"
    )
    btn_seleccionar_estados.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
    
    # Fila 2: Filtros de fecha y ordenación
    ctk.CTkLabel(filtros_frame, text="Fecha Desde:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    entry_fecha_desde = ctk.CTkEntry(filtros_frame, placeholder_text="DD/MM/AAAA")
    entry_fecha_desde.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    
    ctk.CTkLabel(filtros_frame, text="Fecha Hasta:").grid(row=1, column=2, padx=10, pady=5, sticky="w")
    entry_fecha_hasta = ctk.CTkEntry(filtros_frame, placeholder_text="DD/MM/AAAA")
    entry_fecha_hasta.grid(row=1, column=3, padx=10, pady=5, sticky="ew")
    
    ctk.CTkLabel(filtros_frame, text="Ordenar por:").grid(row=1, column=4, padx=10, pady=5, sticky="w")
    filtro_orden = ctk.CTkOptionMenu(filtros_frame, values=["Referencia", "Cantidad Total ↓", "Cantidad Total ↑", "Coste Total ↓", "Coste Total ↑"])
    filtro_orden.set("Cantidad Total ↓")
    filtro_orden.grid(row=1, column=5, padx=10, pady=5, sticky="ew")
    
    filtros_frame.grid_columnconfigure(1, weight=1)
    filtros_frame.grid_columnconfigure(3, weight=1)
    filtros_frame.grid_columnconfigure(5, weight=1)
    
    # Frame para resultados
    resultados_container = ctk.CTkFrame(ventana_principal.main_stats_frame)
    resultados_container.pack(fill="both", expand=True, padx=20, pady=10)
    
    # Label para suma total
    total_frame = ctk.CTkFrame(ventana_principal.main_stats_frame)
    total_frame.pack(fill="x", padx=20, pady=10)
    
    lbl_total = ctk.CTkLabel(
        total_frame, 
        text="TOTAL: 0.00 €", 
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#22c55e"
    )
    lbl_total.pack(pady=10)
    
    def cargar_datos():
        """Carga los datos según los filtros aplicados."""
        from datetime import datetime
        
        # Limpiar resultados anteriores
        for widget in resultados_container.winfo_children():
            widget.destroy()
        
        # Construir query según filtros - AGRUPADO por referencia y estado
        resultado_seleccionado = filtro_resultado.get()
        fecha_desde = entry_fecha_desde.get().strip()
        fecha_hasta = entry_fecha_hasta.get().strip()
        orden_seleccionado = filtro_orden.get()
        
        query = """
            SELECT 
                d.referencia_articulo,
                d.estado_producto,
                SUM(d.cantidad_entregada) as cantidad_total,
                AVG(COALESCE(d.precio_final, d.precio_unitario)) as precio_promedio,
                COUNT(DISTINCT m.codigo_rma) as num_expedientes,
                m.resultado_expediente
            FROM rma_detalles d
            INNER JOIN rma_maestro m ON d.rma_id = m.id
            WHERE 1=1
        """
        
        params = []
        
        if resultado_seleccionado != "Todos":
            query += " AND m.resultado_expediente = ?"
            params.append(resultado_seleccionado)
        
        # Filtro múltiple de estados
        if estados_seleccionados and "Todos" not in estados_seleccionados:
            placeholders = ",".join(["?" for _ in estados_seleccionados])
            query += f" AND d.estado_producto IN ({placeholders})"
            params.extend(estados_seleccionados)
        
        # Filtros de fecha (usando fecha_emision como referencia)
        if fecha_desde:
            try:
                fecha_obj = datetime.strptime(fecha_desde, "%d/%m/%Y")
                fecha_sql = fecha_obj.strftime("%Y-%m-%d")
                query += " AND m.fecha_emision >= ?"
                params.append(fecha_sql)
            except ValueError:
                messagebox.showwarning("Fecha inválida", "El formato de 'Fecha Desde' debe ser DD/MM/AAAA")
                return
        
        if fecha_hasta:
            try:
                fecha_obj = datetime.strptime(fecha_hasta, "%d/%m/%Y")
                fecha_sql = fecha_obj.strftime("%Y-%m-%d")
                query += " AND m.fecha_emision <= ?"
                params.append(fecha_sql)
            except ValueError:
                messagebox.showwarning("Fecha inválida", "El formato de 'Fecha Hasta' debe ser DD/MM/AAAA")
                return
        
        query += " GROUP BY d.referencia_articulo, d.estado_producto, m.resultado_expediente"
        
        # Aplicar ordenación
        if orden_seleccionado == "Referencia":
            query += " ORDER BY d.referencia_articulo ASC"
        elif orden_seleccionado == "Cantidad Total ↓":
            query += " ORDER BY cantidad_total DESC, d.referencia_articulo ASC"
        elif orden_seleccionado == "Cantidad Total ↑":
            query += " ORDER BY cantidad_total ASC, d.referencia_articulo ASC"
        elif orden_seleccionado == "Coste Total ↓":
            query += " ORDER BY (cantidad_total * precio_promedio) DESC, d.referencia_articulo ASC"
        elif orden_seleccionado == "Coste Total ↑":
            query += " ORDER BY (cantidad_total * precio_promedio) ASC, d.referencia_articulo ASC"
        
        try:
            cursor.execute(query, tuple(params))
            registros = cursor.fetchall()
            
            if not registros:
                ctk.CTkLabel(
                    resultados_container, 
                    text="No se encontraron artículos con los filtros aplicados.", 
                    text_color="gray"
                ).pack(pady=20)
                lbl_total.configure(text="TOTAL: 0.00 €")
                return
            
            # Frame scrollable para la tabla
            scroll_frame = ctk.CTkScrollableFrame(resultados_container)
            scroll_frame.pack(fill="both", expand=True)
            
            # Encabezados actualizados con indicador de ordenación
            header_font = ctk.CTkFont(weight="bold", size=12)
            headers_base = ["REFERENCIA", "ESTADO ARTÍCULO", "CANT. TOTAL", "PRECIO UNIT.", "COSTE TOTAL", "Nº EXPED.", "RESULTADO"]
            
            # Añadir indicador de ordenación
            headers = []
            for i, header in enumerate(headers_base):
                if i == 2:  # CANT. TOTAL
                    if orden_seleccionado == "Cantidad Total ↓":
                        headers.append(f"{header} ▼")
                    elif orden_seleccionado == "Cantidad Total ↑":
                        headers.append(f"{header} ▲")
                    else:
                        headers.append(header)
                elif i == 4:  # COSTE TOTAL
                    if orden_seleccionado == "Coste Total ↓":
                        headers.append(f"{header} ▼")
                    elif orden_seleccionado == "Coste Total ↑":
                        headers.append(f"{header} ▲")
                    else:
                        headers.append(header)
                elif i == 0:  # REFERENCIA
                    if orden_seleccionado == "Referencia":
                        headers.append(f"{header} ▲")
                    else:
                        headers.append(header)
                else:
                    headers.append(header)
            
            for col, header in enumerate(headers):
                lbl = ctk.CTkLabel(scroll_frame, text=header, font=header_font)
                lbl.grid(row=0, column=col, padx=10, pady=10, sticky="w")
            
            # Calcular suma total
            suma_total = 0.0
            
            # Datos agrupados
            for i, reg in enumerate(registros, start=1):
                referencia, estado_art, cantidad_total, precio_promedio, num_expedientes, resultado_exp = reg
                
                # Normalizar valores
                try:
                    cantidad_float = float(cantidad_total) if cantidad_total else 0.0
                    precio_float = float(precio_promedio) if precio_promedio else 0.0
                    total_float = cantidad_float * precio_float
                    suma_total += total_float
                except (ValueError, TypeError):
                    cantidad_float = 0.0
                    precio_float = 0.0
                    total_float = 0.0
                
                # Columnas
                ctk.CTkLabel(scroll_frame, text=str(referencia) if referencia else "N/A").grid(
                    row=i, column=0, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=str(estado_art) if estado_art else "N/A").grid(
                    row=i, column=1, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=f"{cantidad_float:.0f}", 
                           font=ctk.CTkFont(weight="bold")).grid(
                    row=i, column=2, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=f"{precio_float:.2f} €").grid(
                    row=i, column=3, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=f"{total_float:.2f} €", 
                           text_color="#2563eb", font=ctk.CTkFont(weight="bold")).grid(
                    row=i, column=4, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=str(int(num_expedientes))).grid(
                    row=i, column=5, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(scroll_frame, text=str(resultado_exp) if resultado_exp else "N/A").grid(
                    row=i, column=6, padx=10, pady=5, sticky="w")
            
            # Actualizar total
            lbl_total.configure(text=f"TOTAL: {suma_total:,.2f} €")
            
            # Guardar registros para exportación
            cargar_datos.ultimos_registros = registros
            
        except Exception as e:
            print(f"Error al cargar datos de artículos: {e}")
            messagebox.showerror("Error", f"Error al cargar los datos: {e}")
            cargar_datos.ultimos_registros = []
    
    # Inicializar variable para almacenar registros
    cargar_datos.ultimos_registros = []
    
    # Wrapper para poder llamar cargar_datos antes de definirla
    def cargar_datos_wrapper():
        cargar_datos()
    
    def exportar_a_excel():
        """Exporta los resultados actuales a Excel con formato."""
        if not cargar_datos.ultimos_registros:
            messagebox.showwarning("Sin datos", "No hay datos para exportar. Primero aplique los filtros.")
            return
        
        try:
            # Preparar datos para DataFrame
            datos_export = []
            for reg in cargar_datos.ultimos_registros:
                referencia, estado_art, cantidad_total, precio_promedio, num_expedientes, resultado_exp = reg
                
                try:
                    cantidad_float = float(cantidad_total) if cantidad_total else 0.0
                    precio_float = float(precio_promedio) if precio_promedio else 0.0
                    total_float = cantidad_float * precio_float
                except (ValueError, TypeError):
                    cantidad_float = 0.0
                    precio_float = 0.0
                    total_float = 0.0
                
                datos_export.append({
                    'Referencia': str(referencia) if referencia else "N/A",
                    'Estado del Artículo': str(estado_art) if estado_art else "N/A",
                    'Cantidad Total': cantidad_float,
                    'Precio Unitario (€)': precio_float,
                    'Coste Total (€)': total_float,
                    'Nº Expedientes': int(num_expedientes),
                    'Resultado Expediente': str(resultado_exp) if resultado_exp else "N/A"
                })
            
            # Crear DataFrame
            df = pd.DataFrame(datos_export)
            
            # Solicitar ruta de guardado
            archivo = filedialog.asksaveasfilename(
                title="Guardar estadísticas de artículos",
                defaultextension=".xlsx",
                filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
                initialfile="estadisticas_articulos.xlsx"
            )
            
            if not archivo:
                return
            
            # Exportar a Excel con formato
            with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Estadísticas')
                
                # Obtener el workbook y la hoja
                workbook = writer.book
                worksheet = writer.sheets['Estadísticas']
                
                # Ajustar ancho de columnas automáticamente
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Aplicar formato a los encabezados
                from openpyxl.styles import Font, PatternFill, Alignment
                
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            
            messagebox.showinfo("Éxito", f"Los datos se han exportado correctamente a:\n{archivo}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar a Excel:\n{e}")
            print(f"Error en exportación: {e}")
    
    # Botones en la segunda fila
    btn_limpiar = ctk.CTkButton(
        filtros_frame, 
        text="🗑️ Limpiar Fechas", 
        command=lambda: (entry_fecha_desde.delete(0, 'end'), entry_fecha_hasta.delete(0, 'end'), cargar_datos()),
        fg_color="#6b7280",
        hover_color="#4b5563",
        width=120
    )
    btn_limpiar.grid(row=2, column=0, padx=10, pady=10)
    
    # Botón de aplicar filtros
    btn_aplicar = ctk.CTkButton(
        filtros_frame, 
        text="🔍 Aplicar Filtros", 
        command=cargar_datos,
        fg_color="#3b82f6",
        hover_color="#2563eb",
        width=140
    )
    btn_aplicar.grid(row=2, column=1, padx=10, pady=10)
    
    # Botón de comparativa con ventas
    btn_comparativa = ctk.CTkButton(
        filtros_frame, 
        text="📊 Comparativa con Ventas", 
        command=lambda: abrir_ventana_comparativa(ventana_principal),
        fg_color="#8b5cf6",
        hover_color="#7c3aed",
        width=180
    )
    btn_comparativa.grid(row=2, column=2, columnspan=2, padx=10, pady=10)
    
    # Botón de exportar a Excel
    btn_exportar = ctk.CTkButton(
        filtros_frame,
        text="💾 Exportar a Excel",
        command=exportar_a_excel,
        fg_color="#22c55e",
        hover_color="#16a34a",
        width=140
    )
    btn_exportar.grid(row=2, column=4, columnspan=2, padx=10, pady=10)
    
    # Cargar datos iniciales
    cargar_datos()
    
    conn.close()


def abrir_selector_estados(estados_disponibles, estados_seleccionados, boton, callback_actualizar):
    """Abre una ventana para seleccionar múltiples estados."""
    
    # Crear ventana modal
    ventana_selector = Toplevel()
    ventana_selector.title("Seleccionar Estados de Artículo")
    ventana_selector.geometry("500x400")
    ventana_selector.transient()
    ventana_selector.grab_set()
    
    # Centrar ventana
    ventana_selector.update_idletasks()
    x = (ventana_selector.winfo_screenwidth() - 500) // 2
    y = (ventana_selector.winfo_screenheight() - 400) // 2
    ventana_selector.geometry(f"500x400+{x}+{y}")
    
    # Frame principal
    frame_principal = ctk.CTkFrame(ventana_selector)
    frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(
        frame_principal,
        text="Seleccione los estados a filtrar (múltiple):",
        font=ctk.CTkFont(size=12, weight="bold")
    ).pack(pady=10)
    
    # Frame con scrollbar para la lista
    frame_lista = ctk.CTkFrame(frame_principal)
    frame_lista.pack(fill="both", expand=True, padx=10, pady=10)
    
    scrollbar = Scrollbar(frame_lista)
    scrollbar.pack(side="right", fill="y")
    
    listbox = Listbox(frame_lista, selectmode=MULTIPLE, yscrollcommand=scrollbar.set, height=15)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)
    
    # Añadir items a la lista
    for estado in estados_disponibles:
        listbox.insert(END, estado)
        # Seleccionar si ya estaba seleccionado previamente
        if estado in estados_seleccionados or (not estados_seleccionados and estado == "Todos"):
            listbox.selection_set(estados_disponibles.index(estado))
    
    # Frame de botones
    frame_botones = ctk.CTkFrame(frame_principal)
    frame_botones.pack(fill="x", pady=10)
    
    def seleccionar_todos():
        listbox.selection_set(0, END)
    
    def deseleccionar_todos():
        listbox.selection_clear(0, END)
    
    def aplicar_seleccion():
        # Obtener elementos seleccionados
        indices = listbox.curselection()
        estados_seleccionados.clear()
        
        if not indices:
            # Si no hay selección, seleccionar "Todos"
            estados_seleccionados.append("Todos")
        else:
            for i in indices:
                estados_seleccionados.append(listbox.get(i))
        
        # Actualizar texto del botón
        if "Todos" in estados_seleccionados or not estados_seleccionados:
            boton.configure(text="Seleccionar Estados (Todos)")
        elif len(estados_seleccionados) == 1:
            # Truncar si es muy largo
            texto = estados_seleccionados[0]
            if len(texto) > 25:
                texto = texto[:22] + "..."
            boton.configure(text=f"Estados: {texto}")
        else:
            boton.configure(text=f"Estados seleccionados: {len(estados_seleccionados)}")
        
        # Actualizar datos
        callback_actualizar()
        
        # Cerrar ventana
        ventana_selector.destroy()
    
    ctk.CTkButton(
        frame_botones,
        text="✓ Seleccionar Todos",
        command=seleccionar_todos,
        fg_color="#3b82f6",
        width=140
    ).pack(side="left", padx=5)
    
    ctk.CTkButton(
        frame_botones,
        text="✗ Deseleccionar Todos",
        command=deseleccionar_todos,
        fg_color="#6b7280",
        width=140
    ).pack(side="left", padx=5)
    
    ctk.CTkButton(
        frame_botones,
        text="Aplicar",
        command=aplicar_seleccion,
        fg_color="#22c55e",
        width=100
    ).pack(side="right", padx=5)
    
    ctk.CTkButton(
        frame_botones,
        text="Cancelar",
        command=ventana_selector.destroy,
        fg_color="#ef4444",
        width=100
    ).pack(side="right", padx=5)


def abrir_ventana_comparativa(ventana_principal):
    """Abre la ventana de comparativa con ventas."""
    from lib.comparativa_ventas import VentanaComparativaVentas
    VentanaComparativaVentas(ventana_principal)
