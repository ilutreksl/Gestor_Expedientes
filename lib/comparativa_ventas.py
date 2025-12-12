"""
Módulo para comparativa de incidencias vs ventas mediante importación de Excel
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd


class VentanaComparativaVentas(ctk.CTkToplevel):
    """Ventana para importar Excel de ventas y comparar con incidencias."""
    
    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)
        
        self.ventana_principal = ventana_principal
        self.datos_ventas = None  # DataFrame con datos importados
        self.datos_comparativa = None  # Resultado de la comparativa
        
        # Configuración de la ventana
        self.title("Comparativa Ventas vs Incidencias")
        self.geometry("1200x700")
        
        # Centrar ventana
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 700) // 2
        self.geometry(f"1200x700+{x}+{y}")
        
        self._crear_interfaz()
    
    def _crear_interfaz(self):
        """Crea la interfaz de la ventana."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            main_frame, 
            text="📊 COMPARATIVA: VENTAS vs INCIDENCIAS", 
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=10)
        
        # Instrucciones
        instrucciones_frame = ctk.CTkFrame(main_frame, fg_color="#f0f0f0")
        instrucciones_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            instrucciones_frame,
            text="ℹ️ Instrucciones:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2c3e50"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            instrucciones_frame,
            text="1. El archivo Excel debe tener 2 columnas SIN encabezados: [Referencia, Cantidad Vendida]\n"
                 "2. Se compararán solo las referencias que existan en ambas fuentes (BD e Excel)\n"
                 "3. Solo se cuentan incidencias con estados problemáticos:\n"
                 "   • NO FUNCIONA • REPOSICIÓN FALLO • FALLO SOLDADURA • FALLO MÓDULO\n"
                 "4. Se calculará el porcentaje: (Incidencias Problemáticas / Ventas) × 100",
            font=ctk.CTkFont(size=11),
            text_color="#2c3e50",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Botones de acción
        botones_frame = ctk.CTkFrame(main_frame)
        botones_frame.pack(fill="x", pady=10)
        
        self.btn_importar = ctk.CTkButton(
            botones_frame,
            text="📁 Importar Excel de Ventas",
            command=self._importar_excel,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            width=200
        )
        self.btn_importar.pack(side="left", padx=5)
        
        self.btn_calcular = ctk.CTkButton(
            botones_frame,
            text="🔄 Calcular Comparativa",
            command=self._calcular_comparativa,
            fg_color="#22c55e",
            hover_color="#16a34a",
            width=200,
            state="disabled"
        )
        self.btn_calcular.pack(side="left", padx=5)
        
        self.btn_exportar = ctk.CTkButton(
            botones_frame,
            text="💾 Exportar Resultados",
            command=self._exportar_resultados,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            width=200,
            state="disabled"
        )
        self.btn_exportar.pack(side="left", padx=5)
        
        # Label de estado
        self.lbl_estado = ctk.CTkLabel(
            main_frame,
            text="📂 No se ha importado ningún archivo",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.lbl_estado.pack(pady=10)
        
        # Frame para resultados
        self.resultados_frame = ctk.CTkScrollableFrame(main_frame)
        self.resultados_frame.pack(fill="both", expand=True, pady=10)
    
    def _importar_excel(self):
        """Importa el archivo Excel con datos de ventas."""
        try:
            # Abrir diálogo para seleccionar archivo
            archivo = filedialog.askopenfilename(
                title="Seleccionar archivo Excel",
                filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")]
            )
            
            if not archivo:
                return
            
            # Leer Excel sin encabezados
            df = pd.read_excel(archivo, header=None, names=['referencia', 'cantidad_vendida'])
            
            # Validar que tenga al menos 2 columnas
            if df.shape[1] < 2:
                messagebox.showerror("Error", "El archivo debe tener al menos 2 columnas: Referencia y Cantidad")
                return
            
            # Convertir referencia a string y limpiar
            df['referencia'] = df['referencia'].astype(str).str.strip()
            
            # Convertir cantidad a numérico
            df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce').fillna(0)
            
            # Eliminar filas sin referencia válida
            df = df[df['referencia'] != '']
            df = df[df['referencia'] != 'nan']
            
            if df.empty:
                messagebox.showwarning("Advertencia", "No se encontraron datos válidos en el archivo")
                return
            
            # Guardar datos
            self.datos_ventas = df
            
            # Actualizar estado
            self.lbl_estado.configure(
                text=f"✅ Archivo importado: {df.shape[0]} referencias cargadas",
                text_color="#22c55e"
            )
            
            # Habilitar botón de calcular
            self.btn_calcular.configure(state="normal")
            
            # Mostrar preview de datos importados
            self._mostrar_preview_ventas()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al importar el archivo:\n{e}")
            print(f"Error importando Excel: {e}")
    
    def _mostrar_preview_ventas(self):
        """Muestra un preview de los datos de ventas importados."""
        # Limpiar frame de resultados
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.resultados_frame,
            text="📋 PREVIEW DE DATOS IMPORTADOS",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        # Tabla de preview (primeras 20 filas)
        preview_df = self.datos_ventas.head(20)
        
        # Encabezados
        header_frame = ctk.CTkFrame(self.resultados_frame)
        header_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(header_frame, text="REFERENCIA", font=ctk.CTkFont(weight="bold"), width=400).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="CANTIDAD VENDIDA", font=ctk.CTkFont(weight="bold"), width=200).pack(side="left", padx=10)
        
        # Datos
        for _, row in preview_df.iterrows():
            row_frame = ctk.CTkFrame(self.resultados_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row_frame, text=str(row['referencia']), width=400).pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=f"{row['cantidad_vendida']:.0f}", width=200).pack(side="left", padx=10)
        
        if len(self.datos_ventas) > 20:
            ctk.CTkLabel(
                self.resultados_frame,
                text=f"... y {len(self.datos_ventas) - 20} referencias más",
                text_color="gray"
            ).pack(pady=5)
    
    def _calcular_comparativa(self):
        """Calcula la comparativa entre ventas e incidencias."""
        if self.datos_ventas is None:
            messagebox.showwarning("Advertencia", "Primero debe importar un archivo Excel")
            return
        
        try:
            # Obtener datos de incidencias de la BD
            conn, cursor = self.ventana_principal.master.conectar_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            
            cursor = conn.cursor()
            
            # Estados problemáticos a considerar para la comparativa
            estados_problematicos = [
                "NO FUNCIONA, ABONAR",
                "NO FUNCIONA ; NO ABONAR",
                "REPOSICION FALLO PRODUCTO",
                "REPOSICION ; ABONAR",
                "FALLO SOLDADURA ; ABONAR",
                "FALLO SOLDADURA ; NO ABONAR",
                "FALLO MODULO ; ABONAR"
            ]
            
            # Crear placeholders para la consulta SQL
            placeholders = ','.join(['?' for _ in estados_problematicos])
            
            # Query para obtener cantidad de incidencias por referencia (solo estados problemáticos)
            cursor.execute(f"""
                SELECT 
                    referencia_articulo,
                    COUNT(*) as num_incidencias,
                    SUM(cantidad_entregada) as cantidad_total_incidencias
                FROM rma_detalles
                WHERE referencia_articulo IS NOT NULL 
                AND referencia_articulo != ''
                AND estado_producto IN ({placeholders})
                GROUP BY referencia_articulo
            """, estados_problematicos)
            
            incidencias_data = cursor.fetchall()
            conn.close()
            
            # Crear DataFrame de incidencias
            df_incidencias = pd.DataFrame(incidencias_data, columns=['referencia', 'num_incidencias', 'cantidad_incidencias'])
            df_incidencias['referencia'] = df_incidencias['referencia'].astype(str).str.strip()
            
            # Hacer merge (inner join) - solo referencias que existan en ambas fuentes
            df_comparativa = pd.merge(
                self.datos_ventas,
                df_incidencias,
                on='referencia',
                how='inner'
            )
            
            if df_comparativa.empty:
                messagebox.showwarning(
                    "Sin coincidencias",
                    "No se encontraron referencias comunes entre las ventas y las incidencias.\n"
                    "Verifique que las referencias en el Excel coincidan con las de la base de datos."
                )
                return
            
            # Calcular porcentaje: (Incidencias / Ventas) × 100
            df_comparativa['porcentaje_incidencia'] = (
                df_comparativa['cantidad_incidencias'] / df_comparativa['cantidad_vendida'] * 100
            ).round(2)
            
            # Ordenar por porcentaje descendente
            df_comparativa = df_comparativa.sort_values('porcentaje_incidencia', ascending=False)
            
            # Guardar resultados
            self.datos_comparativa = df_comparativa
            
            # Mostrar resultados
            self._mostrar_resultados_comparativa()
            
            # Habilitar botón de exportar
            self.btn_exportar.configure(state="normal")
            
            # Actualizar estado
            self.lbl_estado.configure(
                text=f"✅ Comparativa calculada: {len(df_comparativa)} referencias coincidentes",
                text_color="#22c55e"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al calcular la comparativa:\n{e}")
            print(f"Error en comparativa: {e}")
    
    def _mostrar_resultados_comparativa(self):
        """Muestra los resultados de la comparativa en una tabla."""
        # Limpiar frame de resultados
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.resultados_frame,
            text="📊 RESULTADOS DE LA COMPARATIVA",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        # Nota informativa sobre estados incluidos
        nota_frame = ctk.CTkFrame(self.resultados_frame, fg_color="#e3f2fd")
        nota_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            nota_frame,
            text="ℹ️ Solo se cuentan incidencias con estados problemáticos (NO FUNCIONA, REPOSICIÓN FALLO, FALLO SOLDADURA/MÓDULO)",
            font=ctk.CTkFont(size=10),
            text_color="#1976d2",
            wraplength=700
        ).pack(padx=10, pady=5)
        
        # Resumen estadístico
        resumen_frame = ctk.CTkFrame(self.resultados_frame, fg_color="#f0f0f0")
        resumen_frame.pack(fill="x", pady=10)
        
        total_refs = len(self.datos_comparativa)
        promedio_porcentaje = self.datos_comparativa['porcentaje_incidencia'].mean()
        max_porcentaje = self.datos_comparativa['porcentaje_incidencia'].max()
        
        ctk.CTkLabel(
            resumen_frame,
            text=f"📈 Referencias analizadas: {total_refs} | "
                 f"Promedio incidencia: {promedio_porcentaje:.2f}% | "
                 f"Máximo: {max_porcentaje:.2f}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2c3e50"
        ).pack(pady=10)
        
        # Encabezados de tabla
        header_frame = ctk.CTkFrame(self.resultados_frame)
        header_frame.pack(fill="x", pady=5)
        
        headers = [
            ("REFERENCIA", 250),
            ("CANT. VENDIDA", 120),
            ("INCIDENCIAS", 120),
            ("CANT. INCIDENCIAS", 150),
            ("% INCIDENCIA", 120)
        ]
        
        for header, width in headers:
            ctk.CTkLabel(
                header_frame, 
                text=header, 
                font=ctk.CTkFont(weight="bold"), 
                width=width
            ).pack(side="left", padx=5)
        
        # Datos
        for _, row in self.datos_comparativa.iterrows():
            row_frame = ctk.CTkFrame(self.resultados_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            # Determinar color según porcentaje
            porcentaje = row['porcentaje_incidencia']
            if porcentaje < 1:
                color_porcentaje = "#22c55e"  # Verde
            elif porcentaje < 3:
                color_porcentaje = "#eab308"  # Amarillo
            elif porcentaje < 5:
                color_porcentaje = "#f97316"  # Naranja
            else:
                color_porcentaje = "#ef4444"  # Rojo
            
            ctk.CTkLabel(row_frame, text=str(row['referencia']), width=250).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=f"{row['cantidad_vendida']:.0f}", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=f"{int(row['num_incidencias'])}", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=f"{row['cantidad_incidencias']:.0f}", width=150).pack(side="left", padx=5)
            ctk.CTkLabel(
                row_frame, 
                text=f"{porcentaje:.2f}%", 
                width=120,
                text_color=color_porcentaje,
                font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=5)
        
        # Leyenda de colores
        leyenda_frame = ctk.CTkFrame(self.resultados_frame, fg_color="#f0f0f0")
        leyenda_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(leyenda_frame, text="Leyenda: ", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(leyenda_frame, text="🟢 <1%", text_color="#22c55e").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda_frame, text="🟡 1-3%", text_color="#eab308").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda_frame, text="🟠 3-5%", text_color="#f97316").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda_frame, text="🔴 >5%", text_color="#ef4444").pack(side="left", padx=5)
    
    def _exportar_resultados(self):
        """Exporta los resultados de la comparativa a Excel."""
        if self.datos_comparativa is None:
            messagebox.showwarning("Advertencia", "Primero debe calcular la comparativa")
            return
        
        try:
            # Abrir diálogo para guardar archivo
            archivo = filedialog.asksaveasfilename(
                title="Guardar resultados",
                defaultextension=".xlsx",
                filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
                initialfile="comparativa_ventas_incidencias.xlsx"
            )
            
            if not archivo:
                return
            
            # Preparar DataFrame para exportar con nombres de columnas en español
            df_exportar = self.datos_comparativa.copy()
            df_exportar.columns = [
                'Referencia', 
                'Cantidad Vendida', 
                'Número de Incidencias', 
                'Cantidad en Incidencias',
                'Porcentaje de Incidencia (%)'
            ]
            
            # Exportar a Excel
            df_exportar.to_excel(archivo, index=False, sheet_name='Comparativa')
            
            messagebox.showinfo(
                "Exportación exitosa",
                f"Los resultados se han exportado correctamente a:\n{archivo}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar los resultados:\n{e}")
            print(f"Error exportando: {e}")
