"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class RmaEditorMixin:
    def _prompt_select_autorizado_por(self, opciones):
        """Muestra un diálogo modal simple para seleccionar quien autoriza.
        Devuelve la opción seleccionada o None si se cancela.
        """
        if not opciones:
            return None

        dlg = Toplevel(self)
        dlg.title("Seleccionar Autorizado Por")
        dlg.transient(self)
        dlg.grab_set()
        # Centrar el diálogo respecto a la ventana principal
        try:
            width = 360
            height = 120
            # Forzar cálculo de medidas
            dlg.update_idletasks()
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width() or self.winfo_screenwidth()
            ph = self.winfo_height() or self.winfo_screenheight()
            x = px + max(0, (pw - width) // 2)
            y = py + max(0, (ph - height) // 2)
            dlg.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            try:
                dlg.geometry("360x120")
            except Exception:
                pass

        ctk.CTkLabel(dlg, text="Selecciona quien autoriza:", anchor="w").pack(fill='x', padx=12, pady=(12,6))
        var = tk.StringVar(value=opciones[0])
        opt = ctk.CTkOptionMenu(dlg, values=opciones)
        opt.set(opciones[0])
        opt.pack(fill='x', padx=12, pady=(0,8))

        result = {'value': None}

        def _ok():
            try:
                result['value'] = opt.get()
            except Exception:
                result['value'] = None
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btnf = ctk.CTkFrame(dlg)
        btnf.pack(fill='x', pady=(6,10), padx=12)
        ctk.CTkButton(btnf, text='OK', width=80, command=_ok).pack(side='right', padx=(6,0))
        ctk.CTkButton(btnf, text='Cancelar', width=80, command=_cancel).pack(side='right')

        self.wait_window(dlg)
        return result['value']

    def _abrir_editor_rma(self, rma_id=None):
        """Abre el editor de RMA en una ventana separada."""
        from lib.rma_editor_window import RmaEditorWindow
        
        try:
            # Restaurar el content_frame original si fue modificado por una ventana modal
            if hasattr(self, '_original_content_frame') and self._original_content_frame:
                try:
                    if self._original_content_frame.winfo_exists():
                        self.content_frame = self._original_content_frame
                except:
                    pass
            
            # Abrir directamente la nueva ventana
            # Si hay otras ventanas abiertas, no las cerramos automáticamente
            # El usuario las puede cerrar manualmente si lo desea
            RmaEditorWindow(self, rma_id)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir editor RMA: {str(e)}")

    def _mostrar_widget_tiempos(self, parent_frame, rma_id):
        """Muestra el widget de tiempos de tramitación en la ficha del expediente."""
        try:
            # Obtener datos del expediente
            conn = connect_db()
            if not conn:
                return
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fecha_emision, fecha_autorizacion, fecha_recepcion, 
                       fecha_proceso, fecha_gestion, cliente
                FROM rma_maestro
                WHERE id = ?
            """, (rma_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return
            
            fecha_emision, fecha_autorizacion, fecha_recepcion, fecha_proceso, fecha_gestion, cliente = row
            
            # Calcular tiempos del expediente
            tiempos = calcular_tiempos_expediente(
                fecha_emision, fecha_autorizacion, fecha_recepcion, 
                fecha_proceso, fecha_gestion
            )
            
            # Obtener promedio del cliente si está cerrado
            promedio_cliente = None
            if tiempos['cerrado'] and cliente:
                promedio_info = obtener_promedio_cliente(cliente, conn)
                promedio_cliente = promedio_info['promedio_total']
            
            conn.close()
            
            # Si no hay datos de tiempo, no mostrar nada
            if tiempos['dias_total'] is None:
                return
            
            # Frame para el widget de tiempos - DISEÑO VERTICAL COMPACTO
            tiempos_frame = ctk.CTkFrame(parent_frame, fg_color="#f0f0f0", corner_radius=8)
            tiempos_frame.pack(fill="x", pady=(0, 10))
            
            # Título del widget
            ctk.CTkLabel(tiempos_frame, text="📊 TIEMPOS DE TRAMITACIÓN", 
                        font=ctk.CTkFont(size=12, weight="bold"),
                        text_color="#2c3e50").pack(anchor="w", padx=10, pady=(8, 5))
            
            # Días totales
            dias_total = tiempos['dias_total']
            color_total = obtener_color_tiempo(dias_total)
            estado_texto = " (Cerrado)" if tiempos['cerrado'] else " (En curso)"
            
            total_frame = ctk.CTkFrame(tiempos_frame, fg_color="white", corner_radius=6)
            total_frame.pack(fill="x", padx=10, pady=(0, 5))
            
            ctk.CTkLabel(total_frame, text="Total:", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(4, 0))
            ctk.CTkLabel(total_frame, text=f"{dias_total} días{estado_texto}", 
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=color_total).pack(anchor="w", padx=8, pady=(0, 4))
            
            # Promedio del cliente (si está disponible)
            if promedio_cliente is not None:
                promedio_frame = ctk.CTkFrame(tiempos_frame, fg_color="white", corner_radius=6)
                promedio_frame.pack(fill="x", padx=10, pady=(0, 5))
                
                dias_prom = int(promedio_cliente)
                color_prom = obtener_color_tiempo(dias_prom)
                
                ctk.CTkLabel(promedio_frame, text=f"Promedio {cliente}:", 
                           font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(4, 0))
                ctk.CTkLabel(promedio_frame, text=f"{dias_prom} días", 
                           font=ctk.CTkFont(size=13, weight="bold"),
                           text_color=color_prom).pack(anchor="w", padx=8, pady=(0, 4))
            
            # Tiempos entre fases - DISEÑO VERTICAL
            fases_frame = ctk.CTkFrame(tiempos_frame, fg_color="white", corner_radius=6)
            fases_frame.pack(fill="x", padx=10, pady=(0, 8))
            
            ctk.CTkLabel(fases_frame, text="Fases:", font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))
            
            fases = [
                ('Emisión → Autorización', tiempos['dias_e_a']),
                ('Autorización → Recepción', tiempos['dias_a_r']),
                ('Recepción → Proceso', tiempos['dias_r_p']),
                ('Proceso → Cierre', tiempos['dias_p_c'])
            ]
            
            for nombre, dias in fases:
                if dias is not None:
                    color = obtener_color_tiempo(dias)
                    fase_item = ctk.CTkFrame(fases_frame, fg_color="transparent")
                    fase_item.pack(fill="x", padx=8, pady=1)
                    
                    ctk.CTkLabel(fase_item, text=f"{nombre}:", 
                               font=ctk.CTkFont(size=10),
                               anchor="w").pack(side="left")
                    ctk.CTkLabel(fase_item, text=f"{dias} días", 
                               font=ctk.CTkFont(size=10, weight="bold"),
                               text_color=color,
                               anchor="e").pack(side="right", padx=(5, 0))
            
            # Espacio final
            ctk.CTkLabel(fases_frame, text="").pack(pady=2)
            
        except Exception as e:
            print(f"Error al mostrar widget de tiempos: {e}")

    def mostrar_nuevo_rma(self, rma_id=None):
        """Muestra el formulario para crear (rma_id=None) o editar (rma_id=ID) un RMA."""
        self.limpiar_contenido()
        # Recordar en qué content_frame se está construyendo esta ficha (puede ser el de
        # la ventana principal o el de una RmaEditorWindow, que se intercambia temporalmente
        # en lib/rma_editor_window.py). Permite reconstruir la ficha más tarde (p.ej. justo
        # después de guardar un expediente nuevo) en el sitio correcto.
        self._content_frame_ficha_actual = self.content_frame
        self.rma_actual_id = rma_id
        self.articulos_data = [] # Lista temporal que contendrá los artículos
        
        self.datos_rma_maestro = {}
        
        if rma_id is not None:
            # Modo Edición
            self.mode = 'editar'
            # Usaremos 'current_rma_id' para ser consistentes con la función de guardar
            self.current_rma_id = rma_id
        else:
            # Modo Nuevo
            self.mode = 'nuevo'
            self.current_rma_id = None
        
        es_edicion = rma_id is not None

        # Garantizar que exista el atributo antes de llamar (evita AttributeError si la función se define más abajo)
        if not hasattr(self, 'cargar_lista_tareas_rma'):
            self.cargar_lista_tareas_rma = lambda: None
        
        # --- Cabecera ---
        # Obtener información para el título
        if es_edicion:
            # Consultar el código RMA y nombre del cliente desde la base de datos
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT codigo_rma, cliente FROM rma_maestro WHERE id = ?", (rma_id,))
            row = cur.fetchone()
            conn.close()
            
            if row:
                codigo_rma_mostrar = row[0]
                nombre_cliente = row[1] or "Sin cliente"
                titulo_texto = f"{codigo_rma_mostrar} - {nombre_cliente}"
            else:
                codigo_rma_mostrar = "DESCONOCIDO"
                titulo_texto = "EXPEDIENTE DESCONOCIDO"
        else:
            codigo_rma_mostrar = self.obtener_siguiente_rma()
            titulo_texto = "CREAR NUEVO EXPEDIENTE"
        
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # 🛠️ 1. AJUSTE DE PESO: Fila 0 (Cabecera Principal)
        self.content_frame.grid_rowconfigure(0, weight=0) # No se expande
        # --------------------------------------------------------------------------

        ctk.CTkLabel(header_frame, text=titulo_texto, font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        # Añadir advertencia de número temporal para nuevos expedientes
        if not es_edicion:
            ctk.CTkLabel(header_frame, 
                        text=f"⚠️ Número temporal: {codigo_rma_mostrar}. El número definitivo se asignará al guardar.",
                        font=ctk.CTkFont(size=12),
                        text_color="orange").grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Crear label para compatibilidad con código existente (no se muestra visualmente)
        self.lbl_codigo_rma = ctk.CTkLabel(header_frame, text=f"Nº EXPEDIENTE: {codigo_rma_mostrar}")
        
        # --------------------------------------------------------------------------
        # 2. DISEÑO DE 2 COLUMNAS: Layout principal  (Fila 1)
        # --------------------------------------------------------------------------
        # Creamos un frame contenedor para las dos columnas
        main_layout_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_layout_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Configurar pesos: columna izquierda tiene más peso
        main_layout_frame.grid_columnconfigure(0, weight=1)  # Columna izquierda (pestañas) - se expande
        main_layout_frame.grid_columnconfigure(1, weight=0)  # Columna derecha (info) - NO se expande
        main_layout_frame.grid_rowconfigure(0, weight=1)
        
        # Ajustar peso de la fila principal
        self.content_frame.grid_rowconfigure(1, weight=1)

        # ========== COLUMNA IZQUIERDA: Pestañas ==========
        left_column = ctk.CTkFrame(main_layout_frame, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_column.grid_rowconfigure(0, weight=1)  # Las pestañas se expanden
        
        # Guardar si es modo edición para usar en el guardado
        self.es_modo_edicion = es_edicion 
        
        # Vista con pestañas (Tabview) para el formulario y el historial - EN COLUMNA IZQUIERDA
        self.tabview = ctk.CTkTabview(left_column)
        self.tabview.grid(row=0, column=0, sticky="nsew", pady=(15, 10))
        
        # ========== COLUMNA DERECHA: Comentarios + Precio Total + Tiempos ==========
        right_column = ctk.CTkFrame(main_layout_frame, fg_color="transparent", width=450)
        right_column.grid(row=0, column=1, sticky="ns", padx=(5, 0))
        right_column.grid_propagate(False)  # Mantener ancho fijo
        
        # B) CAJA DE COMENTARIOS (Columna derecha, arriba)
        comentarios_frame = ctk.CTkFrame(right_column) 
        comentarios_frame.pack(fill="x", pady=(0, 10))

        # Etiqueta
        ctk.CTkLabel(comentarios_frame, text="Comentarios (Guarde al momento con el botón ➕):", 
                     text_color="black",
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 0), sticky="nw")
        
        comentario_input_frame = ctk.CTkFrame(comentarios_frame, fg_color="transparent")
        comentario_input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 5))
        
        # Textbox para comentarios
        self.textbox_comentarios = ctk.CTkTextbox(comentario_input_frame, 
                                                  height=100,
                                                  wrap="word")
        self.textbox_comentarios.grid(row=0, column=0, sticky="ew")

        # Botón de Guardar Comentario
        ctk.CTkButton(comentario_input_frame, 
                      text="➕", 
                      width=40, 
                      command=self.guardar_comentario_historial
                      ).grid(row=0, column=1, padx=(5, 0), sticky="e")
        
        # PRECIO TOTAL EXPEDIENTE (visible siempre) - EN COLUMNA DERECHA
        precio_total_frame = ctk.CTkFrame(comentarios_frame, fg_color="#e8f5e9", corner_radius=8)
        precio_total_frame.grid(row=2, column=0, padx=5, pady=(10, 5), sticky="ew")
        
        precio_content = ctk.CTkFrame(precio_total_frame, fg_color="transparent")
        precio_content.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(precio_content, text="💰 PRECIO TOTAL EXPEDIENTE:", 
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#2e7d32").pack(anchor="w")
        
        self.lbl_precio_total = ctk.CTkLabel(precio_content, text="0.00 €", 
                                             font=ctk.CTkFont(size=16, weight="bold"), 
                                             text_color="#1b5e20")
        self.lbl_precio_total.pack(anchor="w", pady=(2, 0))
        
        # Widget de tiempos de tramitación (solo en modo edición) - EN COLUMNA DERECHA
        if es_edicion:
            tiempos_container = ctk.CTkFrame(right_column)
            tiempos_container.pack(fill="x", pady=(0, 10))
            self._mostrar_widget_tiempos(tiempos_container, rma_id)
        # -----------------------------------------------------------
        general_tab = self.tabview.add("📝 General")
        estados_fechas_tab = self.tabview.add("⏱️ Estados y Fechas")
        articulos_tab = self.tabview.add("📦 Artículos")
        contabilidad_tab = self.tabview.add("💰 Contabilidad")
        # Nueva pestaña para información técnica — por si en el futuro añadimos más campos técnicos
        info_tecnica_tab = self.tabview.add("🔧 Información Técnica")
        # Determinar título de la pestaña según el modo de almacenamiento
        if usar_b2():
            adjuntos_tab = self.tabview.add("📎 Adjuntos (Backblaze B2)")
        else:
            adjuntos_tab = self.tabview.add("📎 Adjuntos (Local)")
        historial_tab = self.tabview.add("📜 Historial de Cambios")
        # Pestaña de Tareas por RMA (creación/edición desde la ficha del expediente)
        tareas_tab = self.tabview.add("🗒️ Tareas")
        # Pestaña de Asociaciones (solo en modo edición)
        if es_edicion:
            asociaciones_tab = self.tabview.add("🔗 Asociados")
        self.historial_tab = historial_tab

        # Configurar todas las pestañas con un marco scrollable (excepto Adjuntos/Historial, si es necesario)
        # Hacemos los marcos scrollable y los frames internos transparentes
        general_scroll = ctk.CTkScrollableFrame(general_tab, label_text="Datos de Identificación")
        general_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        general_frame = ctk.CTkFrame(general_scroll, fg_color="transparent")
        general_frame.pack(fill="x", padx=10, pady=10)
        general_frame.grid_columnconfigure(1, weight=1)

        estados_fechas_scroll = ctk.CTkScrollableFrame(estados_fechas_tab, label_text="Trazabilidad y Proceso")
        estados_fechas_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        estados_fechas_frame = ctk.CTkFrame(estados_fechas_scroll, fg_color="transparent")
        estados_fechas_frame.pack(fill="x", padx=10, pady=10)
        estados_fechas_frame.grid_columnconfigure(1, weight=1)
        
        contabilidad_scroll = ctk.CTkScrollableFrame(contabilidad_tab, label_text="Cierre del Expediente")
        contabilidad_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        contabilidad_frame = ctk.CTkFrame(contabilidad_scroll, fg_color="transparent")
        contabilidad_frame.pack(fill="x", padx=10, pady=10)
        contabilidad_frame.grid_columnconfigure(1, weight=1)

        # Configurar la nueva pestaña Información Técnica
        info_tecnica_scroll = ctk.CTkScrollableFrame(info_tecnica_tab, label_text="Información Técnica")
        info_tecnica_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        info_tecnica_frame = ctk.CTkFrame(info_tecnica_scroll, fg_color="transparent")
        info_tecnica_frame.pack(fill="x", padx=10, pady=10)
        info_tecnica_frame.grid_columnconfigure(1, weight=1)

        # El historial solo se muestra si estamos editando
        if es_edicion:
            self.mostrar_historial(historial_tab)
            
        # Configurar la pestaña de Tareas - siempre visible pero muestra mensaje diferente si es nuevo
        tareas_scroll = ctk.CTkScrollableFrame(tareas_tab, label_text="Tareas asociadas")
        tareas_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        tareas_frame = ctk.CTkFrame(tareas_scroll, fg_color="transparent")
        tareas_frame.pack(fill="x", padx=10, pady=10)

        # Lista de tareas para este RMA
        # Crear solo una vez el frame y el título
        self.tareas_list_frame = ctk.CTkFrame(tareas_frame)
        self.tareas_list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        tareas_frame.grid_columnconfigure(0, weight=1)
        self.tareas_title_label = ctk.CTkLabel(self.tareas_list_frame, text="Tareas asociadas", font=("Arial", 14, "bold"))
        self.tareas_title_label.pack(pady=(10, 5))
        # Si no es edición, mostramos un mensaje informativo
        if not es_edicion:
            ctk.CTkLabel(self.tareas_list_frame, text="Guarde el expediente para poder crear tareas.").pack(pady=10)
        # Siempre refrescar la lista de tareas al abrir la ficha
        self.cargar_lista_tareas_rma()

        # Función para refrescar historial tras operaciones
        def refrescar_historial():
            self.mostrar_historial(historial_tab)

        # Exponer la función para uso en otras partes
        self.refrescar_historial = refrescar_historial

        # Botón para crear nueva tarea (auto-llena código RMA y creador)
        def crear_tarea_en_rma():
            # Solo permitir si el RMA fue guardado
            if self.current_rma_id is None:
                messagebox.showwarning("Guardar primero", "Guarde el expediente antes de crear tareas.")
                return

            # Abrir un pequeño diálogo para título, descripción y fecha
            dlg = ctk.CTkToplevel(self)
            dlg.title("Crear tarea")
            dlg.geometry("500x580")
            dlg.grab_set()

            ctk.CTkLabel(dlg, text=f"RMA: {self.lbl_codigo_rma.cget('text').split(': ')[1]}").pack(pady=5)
            ctk.CTkLabel(dlg, text=f"Creador: {self.username}").pack(pady=5)

            ctk.CTkLabel(dlg, text="Título:").pack(pady=(10,0))
            titulo_entry = ctk.CTkEntry(dlg)
            titulo_entry.pack(padx=10, pady=5, fill='x')

            ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10,0))
            desc_text = tk.Text(dlg, height=4)
            desc_text.pack(padx=10, pady=5, fill='both', expand=True)

            ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5,0))
            fecha_entry = ctk.CTkEntry(dlg)
            fecha_entry.pack(padx=10, pady=5, fill='x')
            
            # Campo Asignado a
            ctk.CTkLabel(dlg, text="Asignar a:").pack(pady=(5,0))
            # Obtener lista de usuarios para asignación
            usuarios_disponibles = ["No asignado"]
            try:
                conn_temp = connect_db()
                cur_temp = conn_temp.cursor()
                cur_temp.execute("SELECT nombre_usuario FROM usuarios ORDER BY nombre_usuario")
                usuarios_disponibles.extend([row[0] for row in cur_temp.fetchall()])
                conn_temp.close()
            except:
                pass
            
            asignado_var = ctk.StringVar(value="No asignado")
            asignado_opt = ctk.CTkOptionMenu(dlg, values=usuarios_disponibles, variable=asignado_var)
            asignado_opt.pack(padx=10, pady=5, fill='x')
            
            # Campo Prioridad
            ctk.CTkLabel(dlg, text="Prioridad:").pack(pady=(5,0))
            prioridad_var = ctk.StringVar(value="Normal")
            prioridad_opt = ctk.CTkOptionMenu(dlg, values=["Alta", "Normal", "Baja"], variable=prioridad_var)
            prioridad_opt.pack(padx=10, pady=5, fill='x')

            def confirmar_crear():
                titulo = titulo_entry.get().strip()
                descripcion = desc_text.get("1.0", "end").strip()
                fecha_v = fecha_entry.get().strip() or None
                asignado_a = asignado_var.get()
                prioridad = prioridad_var.get()
                codigo_rma = self.lbl_codigo_rma.cget('text').split(': ')[1]
                
                # Si es "No asignado", guardar como NULL
                if asignado_a == "No asignado":
                    asignado_a = None
                
                if not titulo:
                    messagebox.showerror("Error", "El título es obligatorio.")
                    return
                    
                # Validar formato de fecha
                if fecha_v:
                    try:
                        fecha_obj = datetime.datetime.strptime(fecha_v, "%Y-%m-%d")
                        if fecha_obj.date() < datetime.date.today():
                            if not messagebox.askyesno("Advertencia", 
                                "La fecha de vencimiento es anterior a hoy. ¿Desea continuar?"):
                                return
                    except ValueError:
                        messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD")
                        return
                try:
                    conn = connect_db()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO tareas (codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por, creado_en, asignado_a, prioridad, notificado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                        (codigo_rma, titulo, descripcion, fecha_v, 'Pendiente', self.username, datetime.datetime.now().isoformat(), asignado_a, prioridad)
                    )
                    conn.commit()
                    
                    # Registrar en historial del RMA
                    cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
                    rma_row = cur.fetchone()
                    if rma_row:
                        rma_id = rma_row[0]
                        asignacion_texto = f" (asignada a {asignado_a})" if asignado_a else ""
                        cur.execute("""
                            INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                            VALUES (?, ?, ?, ?)
                        """, (rma_id, datetime.datetime.now().isoformat(), self.username,
                             f"Nueva tarea creada: {titulo}{asignacion_texto}"))
                        conn.commit()
                        conn.close()
                    
                    dlg.destroy()
                    # Recargar la lista e historial si corresponde
                    if hasattr(self, 'cargar_lista_tareas_rma'):
                        self.cargar_lista_tareas_rma()
                    if hasattr(self, 'refrescar_historial'):
                        self.refrescar_historial()
                    # Actualizar badge de tareas inmediatamente
                    if hasattr(self, 'badge_tareas'):
                        self.badge_tareas.actualizar_contador()
                    # Refrescar el listado/calendario de tareas del dashboard (columna derecha)
                    if hasattr(self, '_refrescar_tareas_dashboard'):
                        self._refrescar_tareas_dashboard()
                    messagebox.showinfo("Éxito", "✅ Tarea creada correctamente")
                except sqlite3.Error as e:
                    messagebox.showerror("Error BD", f"No se pudo crear la tarea: {e}")
                    if 'conn' in locals():
                        conn.close()

            ctk.CTkButton(dlg, text="Crear", command=confirmar_crear).pack(pady=10)

        # Mostrar el botón de crear solo en modo edición
        if es_edicion:
            ctk.CTkButton(tareas_frame, text="➕ Crear Tarea", command=crear_tarea_en_rma).grid(row=1, column=0, sticky="w", padx=5, pady=(5,15))

        def editar_tarea_dialog(task):
                # task is a dict with task fields
                dlg = ctk.CTkToplevel(self)
                dlg.title("Editar tarea")
                dlg.geometry("500x620")
                dlg.grab_set()

                ctk.CTkLabel(dlg, text=f"ID: {task['id']} - RMA: {task['codigo_rma']}").pack(pady=5)
                ctk.CTkLabel(dlg, text="Título:").pack(pady=(10,0))
                titulo_entry = ctk.CTkEntry(dlg)
                titulo_entry.insert(0, task['titulo'])
                titulo_entry.pack(padx=10, pady=5, fill='x')

                ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10,0))
                desc_text = tk.Text(dlg, height=5)
                desc_text.insert('1.0', task['descripcion'] or '')
                desc_text.pack(padx=10, pady=5, fill='both', expand=True)

                ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5,0))
                fecha_entry = ctk.CTkEntry(dlg)
                fecha_entry.insert(0, task.get('fecha_vencimiento') or '')
                fecha_entry.pack(padx=10, pady=5, fill='x')

                ctk.CTkLabel(dlg, text="Estado:").pack(pady=(5,0))
                estado_var = ctk.StringVar(value=task.get('estado', 'Pendiente'))
                estado_opt = ctk.CTkOptionMenu(dlg, values=["Pendiente", "En Progreso", "Completado"], variable=estado_var)
                estado_opt.pack(padx=10, pady=5, fill='x')
                
                # Campo Asignado a
                ctk.CTkLabel(dlg, text="Asignar a:").pack(pady=(5,0))
                usuarios_disponibles = ["No asignado"]
                try:
                    conn_temp = connect_db()
                    cur_temp = conn_temp.cursor()
                    cur_temp.execute("SELECT nombre_usuario FROM usuarios ORDER BY nombre_usuario")
                    usuarios_disponibles.extend([row[0] for row in cur_temp.fetchall()])
                    conn_temp.close()
                except:
                    pass
                
                asignado_actual = task.get('asignado_a') or "No asignado"
                asignado_var = ctk.StringVar(value=asignado_actual)
                asignado_opt = ctk.CTkOptionMenu(dlg, values=usuarios_disponibles, variable=asignado_var)
                asignado_opt.pack(padx=10, pady=5, fill='x')
                
                # Campo Prioridad
                ctk.CTkLabel(dlg, text="Prioridad:").pack(pady=(5,0))
                prioridad_var = ctk.StringVar(value=task.get('prioridad', 'Normal'))
                prioridad_opt = ctk.CTkOptionMenu(dlg, values=["Alta", "Normal", "Baja"], variable=prioridad_var)
                prioridad_opt.pack(padx=10, pady=5, fill='x')

                def guardar_edicion():
                    nuevo_titulo = titulo_entry.get().strip()
                    nueva_desc = desc_text.get('1.0', 'end').strip()
                    nueva_fecha = fecha_entry.get().strip() or None
                    nuevo_estado = estado_var.get()
                    nuevo_asignado = asignado_var.get()
                    nueva_prioridad = prioridad_var.get()
                    
                    # Si es "No asignado", guardar como NULL
                    if nuevo_asignado == "No asignado":
                        nuevo_asignado = None
                    
                    try:
                        conn = connect_db()
                        cur = conn.cursor()
                        cur.execute("""UPDATE tareas 
                                    SET titulo = ?, descripcion = ?, fecha_vencimiento = ?, estado = ?, asignado_a = ?, prioridad = ?
                                    WHERE id = ?""",
                                    (nuevo_titulo, nueva_desc, nueva_fecha, nuevo_estado, nuevo_asignado, nueva_prioridad, task['id']))
                        conn.commit()
                        # Registrar en historial del RMA
                        try:
                            # Obtener el ID del RMA para el historial
                            cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (task['codigo_rma'],))
                            rma_row = cur.fetchone()
                            if rma_row:
                                rma_id = rma_row[0]
                                asignacion_texto = f" (asignada a {nuevo_asignado})" if nuevo_asignado else ""
                                # Registrar el cambio en el historial
                                cur.execute("""
                                    INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                                    VALUES (?, ?, ?, ?)
                                """, (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     self.username, 
                                     f"Tarea ID {task['id']} editada - {task['titulo']} -> {nuevo_titulo} (Estado: {nuevo_estado}){asignacion_texto}")
                                )
                                conn.commit()
                        except sqlite3.Error as e:
                            print(f"Error al registrar historial de tarea: {e}")
                        conn.close()
                        dlg.destroy()
                        self.cargar_lista_tareas_rma()
                        # Actualizar badge de tareas inmediatamente
                        if hasattr(self, 'badge_tareas'):
                            self.badge_tareas.actualizar_contador()
                        # Refrescar el listado/calendario de tareas del dashboard (columna derecha)
                        if hasattr(self, '_refrescar_tareas_dashboard'):
                            self._refrescar_tareas_dashboard()
                        messagebox.showinfo("Éxito", "✅ Tarea actualizada correctamente")
                    except sqlite3.Error as e:
                        messagebox.showerror("Error BD", f"No se pudo actualizar la tarea: {e}")

                ctk.CTkButton(dlg, text="Guardar", command=guardar_edicion).pack(pady=10)

        def eliminar_tarea_rma(task_id, codigo_rma=None, titulo=None):
            if not messagebox.askyesno("Confirmar", "¿Eliminar esta tarea? Esta acción no se puede deshacer."):
                return
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM tareas WHERE id = ?", (task_id,))
                # Registrar en el historial la eliminación
                try:
                    cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
                    rma_row = cur.fetchone()
                    if rma_row and titulo:
                        rma_id = rma_row[0]
                        cur.execute("""
                            INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                            VALUES (?, ?, ?, ?)
                        """, (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             self.username,
                             f"Tarea eliminada: {titulo}")
                        )
                except Exception as e:
                    print(f"Error al registrar eliminación en historial: {e}")
                conn.commit()
                conn.close()
                if hasattr(self, 'cargar_lista_tareas_rma'):
                    self.cargar_lista_tareas_rma()
                # Actualizar badge y listado/calendario de tareas del dashboard (columna derecha)
                if hasattr(self, 'badge_tareas'):
                    self.badge_tareas.actualizar_contador()
                if hasattr(self, '_refrescar_tareas_dashboard'):
                    self._refrescar_tareas_dashboard()
                messagebox.showinfo("Eliminada", "❌ Tarea eliminada correctamente")
            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"No se pudo eliminar la tarea: {e}")

        def mostrar_tarea_row(task):
            row = ctk.CTkFrame(self.tareas_list_frame)
            row.pack(fill="x", padx=5, pady=3)
            # Determinar color según vencimiento y estado
            fecha_v = task.get('fecha_vencimiento')
            estado = task.get('estado')
            color_texto = "black"
            if estado == "Completado":
                color_texto = "green"
            elif fecha_v:
                try:
                    fecha_venc = datetime.datetime.strptime(fecha_v, "%Y-%m-%d").date()
                    hoy = datetime.date.today()
                    dias_restantes = (fecha_venc - hoy).days
                    if dias_restantes < 0:
                        color_texto = "red"  # Vencida
                    elif dias_restantes <= 3:
                        color_texto = "orange"  # Próxima a vencer
                except ValueError:
                    pass

            prioridad = task.get('prioridad') or 'Normal'
            icono_prioridad = "🔴" if prioridad == 'Alta' else "🟡" if prioridad == 'Normal' else "🟢"
            asignado_texto = f" - Asignado: {task.get('asignado_a')}" if task.get('asignado_a') else ""

            ctk.CTkLabel(row,
                        text=f"{icono_prioridad} {task['titulo']} - Vence: {fecha_v or 'Sin fecha'} - Estado: {estado}{asignado_texto}",
                        text_color=color_texto).pack(side='left', padx=5)
            ctk.CTkButton(row, text="Editar", width=60, command=lambda t=task: editar_tarea_dialog(t)).pack(side='right', padx=5)
            ctk.CTkButton(row, text="Eliminar", width=60, command=lambda t=task: eliminar_tarea_rma(t['id'], t['codigo_rma'], t['titulo'])).pack(side='right', padx=5)

        def cargar_lista_tareas_rma():
            # Limpiar solo las filas de tareas, no el título
            for w in self.tareas_list_frame.winfo_children():
                if w != self.tareas_title_label:
                    w.destroy()

            if self.current_rma_id is None:
                ctk.CTkLabel(self.tareas_list_frame, text="Guarde el expediente para ver las tareas.").pack(pady=10)
                return
            try:
                # Usar el código RMA actual de la ficha
                codigo = self.lbl_codigo_rma.cget('text').split(': ')[1].strip()
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por, asignado_a, prioridad FROM tareas WHERE codigo_rma = ? ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC", (codigo,))
                filas = cur.fetchall()
                conn.close()

                if not filas:
                    ctk.CTkLabel(self.tareas_list_frame, text="No hay tareas asociadas a este RMA.", text_color="gray").pack(pady=10)
                    return
                for tid, codigo_rma, titulo, desc, fecha_v, estado, creador, asignado_a, prioridad in filas:
                    task = {'id': tid, 'codigo_rma': codigo_rma, 'titulo': titulo, 'descripcion': desc, 'fecha_vencimiento': fecha_v, 'estado': estado, 'creado_por': creador, 'asignado_a': asignado_a, 'prioridad': prioridad}
                    mostrar_tarea_row(task)
            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"Error cargando tareas: {e}")

        # Exponer la función para recarga externa
        self.cargar_lista_tareas_rma = cargar_lista_tareas_rma
        # Cargar las tareas si estamos en edición
        if es_edicion:
            self.cargar_lista_tareas_rma()
    # Nota: No recrear tareas_scroll aquí para evitar duplicados en la pestaña de Tareas.
        
        # Configurar la pestaña de Asociaciones (solo en modo edición)
        if es_edicion:
            self.crear_tab_asociaciones(asociaciones_tab, rma_id)
            
        # -----------------------------------------------------------
        # -- 2. MOVER LLAMADAS A crear_campo A SUS NUEVOS FRAMES --
        # -----------------------------------------------------------
        
        # V A L O R E S  A U T O M Á T I C O S
        fecha_emision_valor = datetime.datetime.now().strftime("%Y-%m-%d")
        usuario_actual = self.username
        
        # A) PESTAÑA GENERAL
        # Campos de Cliente y Contacto - Cliente y Número de Documento son de solo lectura en modo edición (excepto admin)
        es_admin = self.username.lower() == "admin"
        deshabilitar_campos = es_edicion and not es_admin
        
        self.crear_campo(general_frame, 0, "Cliente:", "Cliente", deshabilitado=deshabilitar_campos)
        self.crear_campo(general_frame, 1, "Núm. Doc. Cliente:", "Numero_Documento_Cliente", deshabilitado=deshabilitar_campos)
        self.crear_campo(general_frame, 2, "Persona de Contacto:", "Persona_de_Contacto")
        self.crear_campo(general_frame, 3, "Email de Contacto:", "Email_de_Contacto")
        self.crear_campo(general_frame, 4, "Autorización:", "Autorizacion", tipo="optionmenu", opciones=self.OPCIONES["Autorizacion"], valor_defecto="NO")
        self.crear_campo(general_frame, 5, "Motivo Devolucion:", "motivo")

        # Resolución Provisional / Observ. Res. Provisional — resaltados y bloqueados
        # una vez que "Resultado Expediente" (pestaña Contabilidad) tenga valor.
        resolucion_prov_frame = ctk.CTkFrame(general_frame, fg_color="#fff8e1", corner_radius=6)
        resolucion_prov_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        resolucion_prov_frame.grid_columnconfigure(1, weight=1)

        self.crear_campo(resolucion_prov_frame, 0, "Resolución Provisional:", "Resolucion_Provisional",
                          tipo="optionmenu", opciones=self.OPCIONES["Resolucion_Provisional"], valor_defecto="")

        self.lbl_resultado_expediente_ref = ctk.CTkLabel(
            resolucion_prov_frame, text="", text_color="#6d4c00",
            font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_resultado_expediente_ref.grid(row=0, column=2, padx=(4, 10), pady=5, sticky="w")

        self.crear_campo(resolucion_prov_frame, 1, "Observ. Res. Provisional:", "Obs_Res_Provisional")

        # Fechas y Creador (Solo lectura excepto admin)
        self.crear_campo(general_frame, 8, "Fecha Emisión:", "Fecha_Emision",
                         valor_defecto=fecha_emision_valor, deshabilitado=not es_admin)
        self.crear_campo(general_frame, 9, "Creado Por:", "Creado_Por",
                         valor_defecto=usuario_actual, deshabilitado=not es_admin)


        # B) PESTAÑA ESTADOS Y FECHAS
        # Fechas de Autorización, Recepción, Proceso y Gestión
        fila_estados = 0
        # Nota: se antepone "" a las listas de personas para que el campo pueda
        # arrancar en blanco (un expediente nuevo no debe traer preseleccionada
        # la primera persona de la lista - eso obligaba a "deseleccionar").
        opciones_autorizado_por = [""] + list(self.OPCIONES["Autorizado_Por"])
        opciones_recepcionado_por = [""] + list(self.OPCIONES["Recepcionado_Por"])
        opciones_gestionado_por = [""] + list(self.OPCIONES["Gestionado_Por"])

        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Autorización:", "Fecha_Autorizacion", tipo="date"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Autorizado Por:", "Autorizado_Por", tipo="optionmenu", opciones=opciones_autorizado_por, valor_defecto=""); fila_estados += 1

        ctk.CTkLabel(estados_fechas_frame, text="--- RECEPCIÓN ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Recepción:", "Fecha_Recepcion", tipo="date"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Recepcionado Por:", "Recepcionado_Por", tipo="optionmenu", opciones=opciones_recepcionado_por, valor_defecto=""); fila_estados += 1

        ctk.CTkLabel(estados_fechas_frame, text="--- PROCESO ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Proceso:", "Fecha_Proceso", tipo="date"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Procesado Por:", "Procesado_Por"); fila_estados += 1

        ctk.CTkLabel(estados_fechas_frame, text="--- CIERRE/GESTIÓN ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Gestión:", "Fecha_Gestion", tipo="date"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Gestionado Por:", "Gestionado_Por", tipo="optionmenu", opciones=opciones_gestionado_por, valor_defecto=""); fila_estados += 1
        opciones_quincenas = ["Seleccionar..."] + self.obtener_quincenas_futuras()
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha para Factura:", "Fecha_para_factura", tipo="optionmenu", opciones=opciones_quincenas, valor_defecto="Seleccionar..."); fila_estados += 1

        
        # C) PESTAÑA INFORMACIÓN TÉCNICA (campos técnicos)

        # --- Sincronización Autorización / Fecha_Autorizacion / Autorizado_Por ---
        try:
            auth_widget = getattr(self, 'entry_Autorizacion', None)
            if auth_widget is not None:
                def _on_autorizacion_change(choice=None):
                    # No ejecutar durante la carga de datos
                    if getattr(self, '_cargando_datos', False):
                        return
                    
                    try:
                        sel = choice if choice is not None else None
                        # CTkOptionMenu may call the function with the selected value
                        if sel is None:
                            try:
                                sel = auth_widget.get()
                            except Exception:
                                sel = None

                        if sel == 'SI':
                            # Poner fecha de autorización hoy
                            hoy = datetime.datetime.now()
                            if hasattr(self, 'entry_Fecha_Autorizacion'):
                                try:
                                    if hasattr(self.entry_Fecha_Autorizacion, 'set_date'):
                                        self.entry_Fecha_Autorizacion.set_date(hoy)
                                    else:
                                        # Tratar como Entry
                                        self.entry_Fecha_Autorizacion.configure(state='normal')
                                        try:
                                            self.entry_Fecha_Autorizacion.delete(0, ctk.END)
                                        except Exception:
                                            pass
                                        try:
                                            self.entry_Fecha_Autorizacion.insert(0, hoy.strftime('%Y-%m-%d'))
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                            # Pedir autor (selector)
                            try:
                                if hasattr(self, 'entry_Autorizado_Por'):
                                    opcion = self._prompt_select_autorizado_por(self.OPCIONES.get('Autorizado_Por', []))
                                    if opcion:
                                        try:
                                            self.entry_Autorizado_Por.set(opcion)
                                        except Exception:
                                            try:
                                                self.entry_Autorizado_Por.configure(state='normal')
                                                self.entry_Autorizado_Por.delete(0, ctk.END)
                                                self.entry_Autorizado_Por.insert(0, opcion)
                                            except Exception:
                                                pass
                            except Exception:
                                pass

                        else:
                            # Si se pone 'NO', borrar fecha y dejar autor por defecto
                            if hasattr(self, 'entry_Fecha_Autorizacion'):
                                try:
                                    if hasattr(self.entry_Fecha_Autorizacion, 'set_date'):
                                        try:
                                            self.entry_Fecha_Autorizacion.set_date('')
                                        except Exception:
                                            # Intentar borrar texto
                                            try:
                                                self.entry_Fecha_Autorizacion.delete(0, ctk.END)
                                            except Exception:
                                                pass
                                    else:
                                        try:
                                            self.entry_Fecha_Autorizacion.configure(state='normal')
                                            self.entry_Fecha_Autorizacion.delete(0, ctk.END)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                            if hasattr(self, 'entry_Autorizado_Por'):
                                try:
                                    default = self.OPCIONES.get('Autorizado_Por', [None])[0]
                                    if default:
                                        try:
                                            self.entry_Autorizado_Por.set(default)
                                        except Exception:
                                            try:
                                                self.entry_Autorizado_Por.configure(state='normal')
                                                self.entry_Autorizado_Por.delete(0, ctk.END)
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                    except Exception as e:
                        print('Error manejando cambio Autorizacion:', e)

                try:
                    # Intentar configurar el callback
                    auth_widget.configure(command=_on_autorizacion_change)
                except Exception:
                    # Fallback: si no acepta configure, intentar setear manualmente (no garantizado)
                    try:
                        auth_widget.set_callback = _on_autorizacion_change
                    except Exception:
                        pass
        except Exception:
            pass
        
        # --- Sincronización INVERSA: Fecha_Autorizacion -> Autorizacion ---
        try:
            fecha_auth_widget = getattr(self, 'entry_Fecha_Autorizacion', None)
            auth_widget = getattr(self, 'entry_Autorizacion', None)
            
            if fecha_auth_widget is not None and auth_widget is not None:
                # Variable para almacenar el último valor conocido
                self._last_fecha_autorizacion = None
                
                def _verificar_fecha_autorizacion():
                    """Verifica periódicamente si cambió Fecha_Autorizacion y actualiza Autorizacion"""
                    try:
                        # Obtener la fecha del widget
                        fecha_valor = None
                        
                        # Intentar obtener el valor según el tipo de widget
                        if hasattr(fecha_auth_widget, 'get_date'):
                            try:
                                fecha_valor = fecha_auth_widget.get_date()
                            except:
                                pass
                        
                        if fecha_valor is None and hasattr(fecha_auth_widget, 'get'):
                            try:
                                fecha_valor = fecha_auth_widget.get()
                            except:
                                pass
                        
                        # Convertir a string para comparación
                        fecha_str = str(fecha_valor).strip() if fecha_valor else ""
                        
                        # Solo actualizar si cambió
                        if fecha_str != self._last_fecha_autorizacion:
                            self._last_fecha_autorizacion = fecha_str
                            
                            # Verificar si hay fecha válida
                            tiene_fecha = bool(fecha_str) and fecha_str not in ('None', 'null', '')
                            
                            # Actualizar el campo Autorizacion
                            if tiene_fecha:
                                # Hay fecha -> Autorización debe ser SI
                                try:
                                    current_auth = auth_widget.get()
                                    if current_auth != 'SI':
                                        auth_widget.set('SI')
                                except:
                                    pass
                            else:
                                # No hay fecha -> Autorización debe ser NO
                                try:
                                    current_auth = auth_widget.get()
                                    if current_auth != 'NO':
                                        auth_widget.set('NO')
                                except:
                                    pass
                        
                        # Programar siguiente verificación (cada 500ms)
                        if hasattr(self, 'content_frame') and self.content_frame.winfo_exists():
                            self.content_frame.after(500, _verificar_fecha_autorizacion)
                    except Exception as e:
                        # Si hay error, intentar reprogramar de todos modos
                        try:
                            if hasattr(self, 'content_frame') and self.content_frame.winfo_exists():
                                self.content_frame.after(500, _verificar_fecha_autorizacion)
                        except:
                            pass
                
                # Iniciar la verificación periódica
                try:
                    self.content_frame.after(500, _verificar_fecha_autorizacion)
                except Exception as e:
                    print(f'Error iniciando verificación periódica: {e}')
        except Exception as e:
            print(f'Error configurando sincronización inversa: {e}')
        # Fila 0: RMA Proveedor (label cambiado a 'RMA Proveedor')
        self.crear_campo(info_tecnica_frame, 0, "RMA Proveedor:", "Rma_Proveedor")
        # Fila 1: Modelo
        self.crear_campo(info_tecnica_frame, 1, "Modelo:", "Modelo")
        # Fila 2: N. Serie
        self.crear_campo(info_tecnica_frame, 2, "N. Serie:", "N_Serie")
        # Fila 3: Ref. Proveedor
        self.crear_campo(info_tecnica_frame, 3, "Ref. Proveedor:", "Ref_Proveedor")
        # Fila 4: Número de Orden/Partida
        self.crear_campo(info_tecnica_frame, 4, "Nº ORDER:", "Num_Order")
        # Fila 5: Observaciones Técnicas — Editor enriquecido
        ctk.CTkLabel(info_tecnica_frame, text="Observaciones Técnicas:").grid(
            row=5, column=0, padx=10, pady=5, sticky="nw"
        )
        info_tecnica_frame.grid_rowconfigure(5, weight=1)

        obs_container = tk.Frame(info_tecnica_frame)
        obs_container.grid(row=5, column=1, padx=10, pady=5, sticky="nsew")

        self.entry_Obs_Tecnica = RichTextEditor(
            obs_container,
            get_adjuntos_fn       = self._get_adjuntos_imagenes,
            get_b2_client_fn      = get_b2_client,
            b2_root_folder        = B2_ROOT_FOLDER,
            normalizar_ruta_b2_fn = normalizar_ruta_b2,
            usar_b2_fn            = usar_b2,
            height                = 16,
        )
        self.entry_Obs_Tecnica.pack(fill="both", expand=True)

        # Botón para generar la Solicitud de RMA desde la plantilla PDF
        ctk.CTkButton(
            info_tecnica_frame,
            text="Generar Solicitud de RMA",
            command=self.autorrellena_pdf
        ).grid(row=6, column=1, padx=10, pady=(8, 12), sticky="e")

        # C) PESTAÑA ARTÍCULOS (Mantener la lógica de listado y añadir artículo)
        articulos_tab.grid_columnconfigure(0, weight=1)
        articulos_frame = ctk.CTkFrame(articulos_tab) # Este marco no necesita scroll, la lista interna sí
        articulos_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        articulos_frame.grid_columnconfigure(0, weight=1)
        articulos_frame.grid_columnconfigure(1, weight=1)
        
        # Cabecera con título y botón de añadir artículo
        header_art_frame = ctk.CTkFrame(articulos_frame, fg_color="transparent")
        header_art_frame.grid(row=0, column=0, columnspan=6, pady=(10, 5), sticky="ew")
        header_art_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_art_frame, text="DETALLE DE ARTÍCULOS", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")

        self.btn_anadir_articulo = ctk.CTkButton(
            header_art_frame,
            text="➕ Añadir Artículo  [Ctrl+A]",
            width=200,
            command=self.abrir_modal_articulo
        )
        self.btn_anadir_articulo.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # Atajo de teclado Ctrl+A para abrir el modal de nuevo artículo desde la pestaña
        try:
            self.winfo_toplevel().bind_all(
                "<Control-a>",
                lambda e: self.abrir_modal_articulo() if self.tabview.get() == "📦 Artículos" else None
            )
        except Exception:
            pass

        # Variables internas necesarias para compatibilidad con funciones existentes
        self.art_auto_descuento_var = ctk.IntVar(value=1)
        self.art_depreciacion_var = ctk.IntVar(value=0)
        # Widgets ocultos (no visibles en la pestaña, usados por abrir_modal_articulo internamente)
        self.lbl_advertencia_sin_descuento = ctk.CTkLabel(articulos_frame, text="")
        self.lbl_advertencia_sin_descuento.grid_forget()

        # 5. Listado de Artículos ya añadidos (scrollable)
        articulos_frame.grid_rowconfigure(1, weight=1)
        self.articulos_list_frame = ctk.CTkScrollableFrame(articulos_frame)
        self.articulos_list_frame.grid(row=1, column=0, columnspan=6, sticky="nsew", padx=10, pady=10)
        self.actualizar_listado_articulos()

        
        # D) PESTAÑA CONTABILIDAD
        fila_cont = 0
        self.crear_campo(contabilidad_frame, fila_cont, "Resultado Expediente:", "Resultado_Expediente", tipo="optionmenu", opciones=self.OPCIONES["Resultado_Expediente"], valor_defecto=self.OPCIONES["Resultado_Expediente"][0]); fila_cont += 1
        # Campo Número Albarán con botón de búsqueda de PDF
        ctk.CTkLabel(contabilidad_frame, text="Número Albarán:").grid(
            row=fila_cont, column=0, padx=10, pady=5, sticky="w")
        self.entry_Numero_Albaran = ctk.CTkEntry(contabilidad_frame, width=300, state="normal")
        self.entry_Numero_Albaran.grid(row=fila_cont, column=1, padx=10, pady=5, sticky="ew")
        # Botón de búsqueda de PDF (visible solo si el usuario lo tiene activado en ajustes)
        self.btn_buscar_albaran = ctk.CTkButton(
            contabilidad_frame,
            text="🔍",
            width=36,
            height=28,
            font=ctk.CTkFont(size=15),
            command=self.buscar_y_adjuntar_albaran,
        )
        self.btn_buscar_albaran.grid(row=fila_cont, column=2, padx=(2, 10), pady=5, sticky="w")
        if not self.user_settings.get("busqueda_albaranes_activa", False):
            self.btn_buscar_albaran.grid_remove()
        fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Fecha Doc. Cliente:", "Fecha_Doc_Cliente"); fila_cont += 1

        # Nuevos campos de reposición y abono
        self.crear_campo(contabilidad_frame, fila_cont, "Nº Albarán Reposición:", "numero_albaran_reposicion"); fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Fecha Albarán Reposición:", "fecha_albaran_reposicion", tipo="date"); fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Nº Factura Abono:", "numero_factura_abono"); fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Fecha Factura Abono:", "fecha_factura_abono", tipo="date"); fila_cont += 1

        # --- Sincronización Resultado_Expediente -> Resolución Provisional (bloqueo + referencia) ---
        # Una vez que "Resultado Expediente" tiene valor, "Resolución Provisional" y
        # "Observ. Res. Provisional" (pestaña General) dejan de ser editables, y junto al
        # primero se muestra en texto el valor actual de "Resultado Expediente".
        def _sync_resolucion_provisional(choice=None):
            try:
                valor_resultado = self.entry_Resultado_Expediente.get()
            except Exception:
                valor_resultado = ""
            if hasattr(self, 'lbl_resultado_expediente_ref'):
                self.lbl_resultado_expediente_ref.configure(
                    text=f"Resultado Expediente: {valor_resultado}" if valor_resultado else "")
            bloquear = bool(str(valor_resultado).strip())
            for campo in ('entry_Resolucion_Provisional', 'entry_Obs_Res_Provisional'):
                widget = getattr(self, campo, None)
                if widget is not None:
                    try:
                        widget.configure(state="disabled" if bloquear else "normal")
                    except Exception:
                        pass

        self._sync_resolucion_provisional = _sync_resolucion_provisional
        try:
            self.entry_Resultado_Expediente.configure(command=_sync_resolucion_provisional)
        except Exception:
            pass
        _sync_resolucion_provisional()  # Estado inicial (cubre el modo "nuevo")

        # E) PESTAÑA ADJUNTOS
        # 1. Botón para Añadir Adjunto
        self.btn_subir_adjunto = ctk.CTkButton(
            adjuntos_tab, 
            text="➕ Subir Archivo", 
            #fg_color="gray80",        # Fondo del botón: Gris claro
            #hover_color="gray70",     # Efecto hover: Ligeramente más oscuro
            #text_color="black",
            font=ctk.CTkFont(size=14, weight="bold"),
            # CRÍTICO: Usar lambda para forzar el argumento a False
            command=lambda: self.abrir_dialogo_adjunto(modo_abrir_carpeta=False) 
        )
        self.btn_subir_adjunto.pack(pady=(10, 5), padx=10, fill='x')

        # 2b. Panel de estadísticas (cantidad + espacio total)
        self.adjuntos_stats_frame = ctk.CTkFrame(adjuntos_tab, fg_color="transparent")
        self.adjuntos_stats_frame.pack(fill='x', padx=10, pady=(0, 2))
        self.lbl_adjuntos_stats = ctk.CTkLabel(
            self.adjuntos_stats_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor='w'
        )
        self.lbl_adjuntos_stats.pack(side='left', padx=2)

        # 2. Frame para el Listado de Adjuntos
        # Usamos un ScrollableFrame para que la lista crezca
        self.adjuntos_list_frame = ctk.CTkScrollableFrame(adjuntos_tab, label_text="Archivos Adjuntos")
        self.adjuntos_list_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # Cargar los adjuntos si estamos en modo edición (la función la crearemos en el paso 4)
        if self.mode == 'editar':
            self.cargar_lista_adjuntos(self.current_rma_id)
        else:
            # En modo 'nuevo', mostramos un mensaje hasta que el RMA se guarde
            ctk.CTkLabel(self.adjuntos_list_frame, 
                         text="Guarde el expediente primero para poder adjuntar archivos.")\
                .pack(pady=20)
        

        # 4. Botón de Guardar Definitivo
        
        # 💡 CREAR UN FRAME PARA AGRUPAR LOS BOTONES DE ACCIÓN (Fila 2)
        btn_action_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_action_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        self.content_frame.grid_rowconfigure(2, weight=0)  # Los botones no se expanden
        
        # Botón de cliente (lado derecho, siempre visible)
        def abrir_ficha_cliente_desde_expediente():
            # Obtener nombre del cliente desde el campo
            if hasattr(self, 'entry_Cliente'):
                nombre_cliente = self.entry_Cliente.get().strip()
                if nombre_cliente:
                    # Buscar cliente_id por nombre
                    try:
                        conn, cursor = self.master.conectar_db()
                        if conn:
                            cursor.execute("SELECT cliente_id FROM clientes WHERE nombre = ?", (nombre_cliente,))
                            resultado = cursor.fetchone()
                            conn.close()
                            
                            if resultado:
                                self.abrir_ficha_cliente(resultado[0])
                            else:
                                messagebox.showinfo("Cliente no encontrado", 
                                                  f"El cliente '{nombre_cliente}' no está registrado en el sistema.\n\n"
                                                  "Puede usar el botón 'Migrar desde RMAs' en la ventana de clientes.")
                    except Exception as e:
                        print(f"Error buscando cliente: {e}")
                        messagebox.showerror("Error", "No se pudo buscar el cliente")
                else:
                    messagebox.showwarning("Sin cliente", "Primero debe especificar un cliente en el expediente")
        
        self.btn_ver_cliente = ctk.CTkButton(
            btn_action_frame,
            text="👤",
            command=abrir_ficha_cliente_desde_expediente,
            width=35,
            height=35,
            font=ctk.CTkFont(size=16)
        )
        self.btn_ver_cliente.pack(side="right", padx=(10, 0))
        Tooltip(self.btn_ver_cliente, "Ver ficha del cliente")
        
        # Botón de artículos (lado derecho, junto al de cliente)
        def abrir_ficha_articulo_desde_expediente():
            # Si no hay artículos en memoria, mostrar mensaje
            if not self.articulos_data:
                messagebox.showinfo("Sin artículos", 
                                  "Este expediente no tiene artículos asociados aún.\n\n"
                                  "Agregue artículos en la sección 'ARTÍCULOS' de este formulario.")
                return
            
            # Si solo hay un artículo, abrir su ficha directamente
            if len(self.articulos_data) == 1:
                referencia = self.articulos_data[0].get('referencia_articulo', '')
                if referencia:
                    self.mostrar_estados_por_articulo(referencia)
                return
            
            # Si hay múltiples artículos, mostrar selector
            from lib.articulo_utils import mostrar_selector_referencias
            
            def callback_seleccion(referencia):
                self.mostrar_estados_por_articulo(referencia)
            
            mostrar_selector_referencias(self.articulos_data, self.content_frame.winfo_toplevel(), callback_seleccion)
        
        self.btn_ver_articulo = ctk.CTkButton(
            btn_action_frame,
            text="📦",
            command=abrir_ficha_articulo_desde_expediente,
            width=35,
            height=35,
            font=ctk.CTkFont(size=16)
        )
        self.btn_ver_articulo.pack(side="right", padx=(5, 0))
        Tooltip(self.btn_ver_articulo, "Ver ficha de artículo")
        
        # 1. Botón de Generar Informe (Solo en modo edición)
        if es_edicion:
            self.btn_generar_informe = ctk.CTkButton(
                btn_action_frame, 
                text="📄 Informe (Word)", 
                command=self.generar_informe_dinamico, 
                #text_color="black",
                #fg_color="grey80", 
                #hover_color="grey70",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            self.btn_generar_informe.pack(side="left", padx=(5, 15)) # 15px de margen derecho
            self.btn_generar_reposicion = ctk.CTkButton(
                btn_action_frame, 
                text="🔄 Reposicion/Devolucion", # Texto largo para mayor claridad
                command=self.generar_reposicion_devolucion, 
                #text_color="black",
                #fg_color="grey80",
                #hover_color="grey70",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            self.btn_generar_reposicion.pack(side="left", padx=(5, 15)) # 5px izquierda, 15px derecha antes de Actualizar
            self.btn_enviar_email = ctk.CTkButton(btn_action_frame, 
                text="📧 Enviar Email",
                command=self.enviar_email_contacto,
                #text_color="black",
                #fg_color="grey80",
                #hover_color="grey70",
                font=ctk.CTkFont(size=14, weight="bold"))               
            self.btn_enviar_email.pack(side="left", padx=(5, 15))
            
            # Botón de generar autorización (solo para roles autorizados)
            if self.rol in ["administrador", "admin", "Dpto. Tecnico", "Administracion"]:
                self.btn_autorizacion = ctk.CTkButton(
                    btn_action_frame,
                    text="📋 Autorización",
                    command=lambda: self.mostrar_dialogo_autorizacion(rma_id, codigo_rma_mostrar),
                    font=ctk.CTkFont(size=14, weight="bold"),
                    fg_color="#27ae60",
                    hover_color="#229954"
                )
                self.btn_autorizacion.pack(side="left", padx=(5, 15))
                Tooltip(self.btn_autorizacion, "Generar PDF de autorización de devolución")

        # 2. Botón de Guardar
        if es_edicion:
            guardar_texto = "💾 ACTUALIZAR"
            color_boton = None  # Color por defecto
        else:
            guardar_texto = "💾 GUARDAR Y ASIGNAR NÚMERO"
            color_boton = "orange"  # Color naranja para destacar que asignará el número final
        
        self.btn_guardar_rma = ctk.CTkButton(
            btn_action_frame, 
            text=guardar_texto, 
            fg_color=color_boton,        # Color especial para nuevos expedientes
            #hover_color="gray70",     # Efecto hover: Ligeramente más oscuro
            #text_color="black",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.guardar_rma_placeholder
        )
        self.btn_guardar_rma.pack(side="left", padx=(0, 5))

        # ── Botón Reabrir (solo en modo edición; visibilidad gestionada dinámicamente) ──
        if es_edicion:
            self.btn_reabrir_expediente = ctk.CTkButton(
                btn_action_frame,
                text="🔓 Reabrir",
                fg_color="#e67e22",
                hover_color="#ca6f1e",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=self.reabrir_expediente
            )
            # No se hace .pack() aquí; lo gestiona _actualizar_botones_segun_estado()
        
        # Botón de eliminar expediente (solo para admin en modo edición)
        if es_edicion and self.username.lower() == "admin":
            self.btn_eliminar_rma = ctk.CTkButton(
                btn_action_frame,
                text="🗑️ ELIMINAR EXPEDIENTE",
                fg_color="red",
                hover_color="darkred",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda: self.eliminar_expediente(rma_id)
            )
            self.btn_eliminar_rma.pack(side="left", padx=(5, 0))
        
        # Botón de cerrar (lado derecho)
        # Detectar si estamos en una ventana modal (RmaEditorWindow)
        ventana_actual = self.content_frame.winfo_toplevel()
        es_ventana_modal = ventana_actual != self.master
        
        if es_ventana_modal:
            # Estamos en RmaEditorWindow - cerrar la ventana
            btn_cerrar = ctk.CTkButton(btn_action_frame, 
                                       text="✖️ Cerrar", 
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       command=ventana_actual.destroy)
        else:
            # Estamos en la ventana principal - volver a la lista
            btn_cerrar = ctk.CTkButton(btn_action_frame, 
                                       text="⬅️ Volver", 
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       command=self.mostrar_lista_rma)
        
        btn_cerrar.pack(side="right", padx=(10, 0))
        
        # Lógica de Edición
        if es_edicion:
            # self.lbl_codigo_rma.configure(text="Cargando datos...")
            self.cargar_datos_rma(rma_id) # Se implementará después

    def guardar_comentario_historial(self):
        """
        Guarda el contenido del Textbox de comentarios como una entrada del historial, 
        usando la estructura simple de la tabla rma_historial.
        """
        
        # 1. Validar ID del Expediente
        rma_id = self.rma_actual_id
        if rma_id is None:
            messagebox.showwarning("Aviso", "Debes guardar el expediente principal primero (botón GUARDAR RMA) para poder añadir comentarios.")
            return

        # 2. Obtener y validar el texto
        nuevo_comentario = self.textbox_comentarios.get("1.0", "end-1c").strip()
        
        if not nuevo_comentario:
            messagebox.showwarning("Aviso", "No hay texto en la caja de comentarios para guardar.")
            return
            
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # 3. Preparar los datos
            fecha_cambio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            usuario = self.username
            
            # 4. Crear la descripción completa del cambio
            # Para un historial simple, el comentario es la descripción completa
            descripcion_cambio = f"COMENTARIO MANUAL: {nuevo_comentario}"
            
            # 5. Ejecutar la inserción SQL
            cursor.execute("""
                INSERT INTO rma_historial 
                (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (rma_id, fecha_cambio, usuario, descripcion_cambio))

            # 6. Commit, Limpieza y Feedback
            conn.commit()
            conn.close()
            
            self.textbox_comentarios.delete("1.0", "end")
            
            # 7. Recargar historial (si la pestaña está visible)
            if hasattr(self, 'historial_tab') and self.historial_tab:
                # Llama a la función que recarga el listado de la pestaña historial
                self.mostrar_historial(self.historial_tab)
            
            try:
                # 1. Obtener el texto completo (ej: "Nº EXPEDIENTE: RMA25001")
                texto_label = self.lbl_codigo_rma.cget("text")
                # 2. Extraer solo el código (ej: "RMA25001")
                codigo_rma = texto_label.split(': ')[1]
            except Exception:
                # Fallback seguro en caso de que el label tenga un formato inesperado
                codigo_rma = f"ID {rma_id}"
                
            # 8. Mostrar mensaje de éxito usando la variable local 'codigo_rma'
            messagebox.showinfo("Comentario Guardado", f"El comentario ha sido guardado en el historial del RMA {codigo_rma}.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Error al guardar el comentario: {e}")

    def reabrir_expediente(self):
        """
        Muestra una ventana modal para reabrir un expediente cerrado.
        Solicita el motivo, registra en historial y limpia los campos de cierre.
        """
        if not self.rma_actual_id:
            return

        # Crear ventana modal
        ventana = ctk.CTkToplevel(self.content_frame.winfo_toplevel())
        ventana.title("Reabrir Expediente")
        ventana.geometry("480x260")
        ventana.resizable(False, False)
        ventana.grab_set()  # Modal
        ventana.focus_set()

        # Centrar la ventana respecto a la principal
        ventana.update_idletasks()
        x = ventana.winfo_toplevel().winfo_x() + (ventana.winfo_toplevel().winfo_width() // 2) - 240
        y = ventana.winfo_toplevel().winfo_y() + (ventana.winfo_toplevel().winfo_height() // 2) - 130
        ventana.geometry(f"+{x}+{y}")

        # Título e instrucción
        ctk.CTkLabel(
            ventana,
            text="🔓 Reabrir Expediente",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            ventana,
            text="Indica el motivo por el que se reabre este expediente:",
            font=ctk.CTkFont(size=13)
        ).pack(pady=(0, 8))

        # Campo de texto para el motivo
        entry_motivo = ctk.CTkTextbox(ventana, height=70, width=420)
        entry_motivo.pack(padx=20, pady=(0, 12))
        entry_motivo.focus_set()

        # Frame de botones
        btn_frame = ctk.CTkFrame(ventana, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))

        def aceptar():
            motivo = entry_motivo.get("1.0", "end-1c").strip()
            if not motivo:
                messagebox.showwarning(
                    "Motivo requerido",
                    "⚠️ Debes indicar el motivo para reabrir el expediente.",
                    parent=ventana
                )
                return

            try:
                conn = connect_db()
                cursor = conn.cursor()

                # 1. Limpiar campos de cierre en la BD
                cursor.execute("""
                    UPDATE rma_maestro
                    SET fecha_gestion = NULL,
                        gestionado_por = NULL,
                        fecha_para_factura = NULL
                    WHERE id = ?
                """, (self.rma_actual_id,))

                # 2. Registrar en historial
                descripcion_historial = f"EXPEDIENTE REABIERTO. Motivo: {motivo}"
                cursor.execute("""
                    INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                    VALUES (?, ?, ?, ?)
                """, (
                    self.rma_actual_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.username,
                    descripcion_historial
                ))

                conn.commit()
                conn.close()

            except Exception as e:
                messagebox.showerror("Error", f"Error al reabrir el expediente:\n{e}", parent=ventana)
                return

            # 3. Limpiar campos en la interfaz (sin guardar, BD ya actualizada)
            try:
                # Limpiar Fecha Gestión
                widget_fg = getattr(self, "entry_Fecha_Gestion", None)
                if widget_fg:
                    if hasattr(widget_fg, 'set_date'):
                        widget_fg.set_date(None)
                    elif hasattr(widget_fg, 'delete'):
                        widget_fg.delete(0, 'end')

                # Limpiar Gestionado Por (volver al primer valor del optionmenu)
                widget_gp = getattr(self, "entry_Gestionado_Por", None)
                if widget_gp and hasattr(widget_gp, 'set'):
                    opciones = self.OPCIONES.get("Gestionado_Por", [""])
                    widget_gp.set(opciones[0])

                # Limpiar Fecha para Factura (volver a "Seleccionar...")
                widget_fpf = getattr(self, "entry_Fecha_para_factura", None)
                if widget_fpf and hasattr(widget_fpf, 'set'):
                    widget_fpf.set("Seleccionar...")

            except Exception as e:
                print(f"Error limpiando widgets tras reapertura: {e}")

            # 4. Refrescar historial si está visible
            if hasattr(self, 'historial_tab'):
                try:
                    self.mostrar_historial(self.historial_tab)
                except Exception:
                    pass

            # 5. Actualizar botones de acción (ocultar "Reabrir", mostrar guardado normal)
            self._actualizar_botones_segun_estado()

            ventana.destroy()
            messagebox.showinfo("Expediente reabierto", "✅ El expediente ha sido reabierto correctamente.")

        ctk.CTkButton(
            btn_frame,
            text="✅ Aceptar",
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=140,
            command=aceptar
        ).pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="✖️ Cancelar",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=140,
            command=ventana.destroy
        ).pack(side="left")

    def _actualizar_botones_segun_estado(self):
        """
        Muestra u oculta el botón 'Reabrir' según si el expediente tiene Fecha Gestión.
        Llamar tras cargar datos y tras reabrir.
        """
        if not hasattr(self, 'btn_reabrir_expediente'):
            return

        try:
            widget_fg = getattr(self, "entry_Fecha_Gestion", None)
            if widget_fg:
                if hasattr(widget_fg, 'get_date'):
                    fecha = widget_fg.get_date()
                else:
                    fecha = widget_fg.get()
            else:
                fecha = ""

            esta_cerrado = bool(fecha and str(fecha).strip())

            if esta_cerrado:
                self.btn_reabrir_expediente.pack(side="left", padx=(5, 0))
            else:
                self.btn_reabrir_expediente.pack_forget()

        except Exception as e:
            print(f"Error actualizando botones según estado: {e}")

    def toggle_porcentaje_depreciacion(self):
        """Habilita o deshabilita el campo de porcentaje de depreciación según el checkbox."""
        if self.art_depreciacion_var.get() == 1:
            self.art_porcentaje_depreciacion.configure(state="normal")
        else:
            self.art_porcentaje_depreciacion.configure(state="disabled")
            self.art_porcentaje_depreciacion.delete(0, ctk.END)
            self.art_porcentaje_depreciacion.insert(0, "0")
        # Recalcular precio final si está en modo auto
        self.calcular_precio_final_tiempo_real()

    def toggle_modo_calculo_precio(self):
        """Cambia entre modo automático y manual para el cálculo del precio final."""
        if self.art_auto_descuento_var.get() == 1:  # Modo AUTO
            self.art_precio_final.configure(state="disabled")
            self.calcular_precio_final_tiempo_real()  # Calcular automáticamente
        else:  # Modo MANUAL
            self.art_precio_final.configure(state="normal")

    def calcular_precio_final_tiempo_real(self, event=None):
        """Calcula el precio final en tiempo real aplicando descuento del cliente y depreciación."""
        from lib.articulo_utils import obtener_descuento_cliente, calcular_precio_final, validar_cliente_sin_descuento
        
        # Solo calcular si está en modo auto
        if self.art_auto_descuento_var.get() != 1:
            return
        
        try:
            # Obtener precio unitario
            precio_str = self.art_precio.get().strip().replace(',', '.')
            if not precio_str:
                self.art_precio_final.configure(state="normal")
                self.art_precio_final.delete(0, ctk.END)
                self.art_precio_final.configure(state="disabled")
                return
            
            precio_unitario = float(precio_str)
            
            # Obtener nombre del cliente
            cliente_nombre = self.entry_Cliente.get().strip()
            if not cliente_nombre:
                # Si no hay cliente, precio final = precio unitario
                self.art_precio_final.configure(state="normal")
                self.art_precio_final.delete(0, ctk.END)
                self.art_precio_final.insert(0, f"{precio_unitario:.2f}")
                self.art_precio_final.configure(state="disabled")
                return
            
            # Obtener conexión a la base de datos
            conn, cursor = self.master.conectar_db()
            
            # Verificar si el cliente tiene descuento configurado
            tiene_descuento, valor_descuento = validar_cliente_sin_descuento(cliente_nombre, conn)
            
            # Obtener datos de depreciación
            tiene_depreciacion = self.art_depreciacion_var.get() == 1
            porcentaje_depreciacion = 0.0
            
            if tiene_depreciacion:
                porcentaje_str = self.art_porcentaje_depreciacion.get().strip()
                if porcentaje_str:
                    porcentaje_depreciacion = float(porcentaje_str.replace(',', '.'))
            
            # Si no tiene descuento NI depreciación, desactivar modo auto
            if not tiene_descuento and not tiene_depreciacion:
                # Desmarcar checkbox Auto
                self.art_auto_descuento_check.deselect()
                
                # Habilitar campo para entrada manual
                self.art_precio_final.configure(state="normal")
                self.art_precio_final.delete(0, ctk.END)
                self.art_precio_final.insert(0, f"{precio_unitario:.2f}")
                
                # Mostrar advertencia en label solo si es el primer artículo del expediente
                if len(self.articulos_data) == 0:
                    if hasattr(self, 'lbl_advertencia_sin_descuento'):
                        self.lbl_advertencia_sin_descuento.grid()
                
                return
            
            # Obtener descuento del cliente desde la base de datos
            descuento_cliente = obtener_descuento_cliente(cliente_nombre, conn)
            
            # Calcular precio final
            precio_final = calcular_precio_final(
                precio_unitario,
                descuento_cliente,
                tiene_depreciacion,
                porcentaje_depreciacion
            )
            
            # Actualizar campo (habilitarlo temporalmente)
            self.art_precio_final.configure(state="normal")
            self.art_precio_final.delete(0, ctk.END)
            self.art_precio_final.insert(0, f"{precio_final:.2f}")
            self.art_precio_final.configure(state="disabled")
            
        except ValueError as ve:
            # Si hay error en la conversión, limpiar el campo
            self.art_precio_final.configure(state="normal")
            self.art_precio_final.delete(0, ctk.END)
            self.art_precio_final.configure(state="disabled")
        except Exception as e:
            print(f"Error al calcular precio final: {e}")

    def anadir_articulo(self):
        """Abre el modal para añadir un nuevo artículo (wrapper de compatibilidad)."""
        self.abrir_modal_articulo(index=None)

    def limpiar_articulo(self):
        """Limpia los campos de entrada de un solo artículo."""
        self.art_ref.delete(0, ctk.END)
        self.art_cant_doc.delete(0, ctk.END)
        self.art_cant_entregada.delete(0, ctk.END)
        self.art_precio.delete(0, ctk.END)
        self.art_estado.set(self.OPCIONES["Estado_Producto"][0])
        
        # Limpiar precio final
        self.art_precio_final.configure(state="normal")
        self.art_precio_final.delete(0, ctk.END)
        if self.art_auto_descuento_var.get() == 1:
            self.art_precio_final.configure(state="disabled")
        
        # Resetear auto a activado por defecto
        self.art_auto_descuento_var.set(1)
        self.art_auto_descuento_check.select()
        self.art_precio_final.configure(state="disabled")
        
        # Ocultar advertencia de sin descuento
        if hasattr(self, 'lbl_advertencia_sin_descuento'):
            self.lbl_advertencia_sin_descuento.grid_remove()
        
        # Limpiar depreciación
        self.art_depreciacion_var.set(0)
        self.art_porcentaje_depreciacion.configure(state="normal")
        self.art_porcentaje_depreciacion.delete(0, ctk.END)
        self.art_porcentaje_depreciacion.insert(0, "0")
        self.art_porcentaje_depreciacion.configure(state="disabled")
        
        # Si estábamos en modo edición, salir de él
        try:
            if hasattr(self, 'editing_articulo_index') and self.editing_articulo_index is not None:
                self.editing_articulo_index = None
                # Restaurar el botón de añadir a su comportamiento original
                try:
                    self.btn_anadir_articulo.configure(text="➕", command=self.anadir_articulo)
                except Exception:
                    pass
        except Exception:
            pass

    def eliminar_articulo(self, index):
        """Elimina un artículo de la lista temporal y actualiza la vista."""
        if 0 <= index < len(self.articulos_data):
            self.articulos_data.pop(index)
            self.actualizar_listado_articulos()

    def editar_articulo(self, index):
        """Abre la ventana modal de edición para el artículo en la posición index."""
        if 0 <= index < len(self.articulos_data):
            self.abrir_modal_articulo(index=index)

    def actualizar_articulo(self):
        """Actualiza el artículo seleccionado con los valores actuales de los campos."""
        from lib.articulo_depreciacion import validar_porcentaje_depreciacion
        
        if not hasattr(self, 'editing_articulo_index') or self.editing_articulo_index is None:
            return
        idx = self.editing_articulo_index
        try:
            referencia = self.art_ref.get()
            cant_doc = float(self.art_cant_doc.get().replace(',', '.') or 0.0)
            cant_entregada = float(self.art_cant_entregada.get().replace(',', '.') or 0.0)
            estado = self.art_estado.get()
            precio_unitario = float(self.art_precio.get().replace(',', '.') or 0.0)
            
            # Precio final (auto o manual)
            if self.art_auto_descuento_var.get() == 1:  # Modo AUTO
                precio_final = float(self.art_precio_final.get().replace(',', '.') or precio_unitario)
            else:  # Modo MANUAL
                precio_final_str = self.art_precio_final.get().strip().replace(',', '.')
                precio_final = float(precio_final_str) if precio_final_str else precio_unitario
            
            # Depreciación
            tiene_depreciacion = self.art_depreciacion_var.get() == 1
            porcentaje_depreciacion = 0.0
            
            if tiene_depreciacion:
                porcentaje_str = self.art_porcentaje_depreciacion.get().strip()
                es_valido, porcentaje_valor, mensaje_error = validar_porcentaje_depreciacion(porcentaje_str)
                
                if not es_valido:
                    messagebox.showerror("Error", f"Porcentaje de depreciación inválido: {mensaje_error}")
                    return
                
                porcentaje_depreciacion = porcentaje_valor
                
        except ValueError:
            messagebox.showwarning("Error", "Cantidad y Precio deben ser números válidos.")
            return

        if not referencia:
            messagebox.showwarning("Error", "La referencia es obligatoria.")
            return

        # Preservar el valor de contabilizar del artículo existente
        articulo_antiguo = self.articulos_data[idx]
        contabilizar_actual = articulo_antiguo.get('contabilizar', 1)
        
        nuevo_articulo = {
            "referencia_articulo": referencia,
            "cantidad_segun_documento": cant_doc,
            "cantidad_entregada": cant_entregada,
            "estado_producto": estado,
            "precio_unitario": precio_unitario,
            "precio_final": precio_final,
            "depreciacion": 1 if tiene_depreciacion else 0,
            "porcentaje_depreciacion": porcentaje_depreciacion,
            "contabilizar": contabilizar_actual  # Preservar estado del checkbox
        }
        # Reemplazar en la lista
        try:
            self.articulos_data[idx] = nuevo_articulo
        except Exception:
            return

        # Finalizar edición
        self.editing_articulo_index = None
        try:
            self.btn_anadir_articulo.configure(text="➕", command=self.anadir_articulo)
        except Exception:
            pass

        self.actualizar_listado_articulos()
        self.limpiar_articulo()

    def _enter_articulo(self, event=None):
        """Handler para la tecla ENTER en los campos de artículo: añade o actualiza según el modo."""
        try:
            if hasattr(self, 'editing_articulo_index') and self.editing_articulo_index is not None:
                self.actualizar_articulo()
            else:
                self.anadir_articulo()
        except Exception:
            pass

    def abrir_modal_articulo(self, index=None):
        """
        Abre una ventana modal para añadir o editar un artículo.
        index: None = modo añadir nuevo; int = modo editar artículo existente.
        Atajo desde la pestaña de artículos: Ctrl+A abre este modal para nuevo artículo.
        Navegación: Tab avanza entre campos, Shift+Tab retrocede. Enter guarda.
        """
        from lib.articulo_depreciacion import validar_porcentaje_depreciacion
        from lib.articulo_utils import obtener_descuento_cliente, calcular_precio_final

        es_edicion = index is not None
        art_existente = self.articulos_data[index] if es_edicion else {}

        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar Artículo" if es_edicion else "Añadir Artículo")
        ventana.geometry("680x540")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.focus_set()

        # Centrar respecto a la ventana padre
        try:
            self.update_idletasks()
            px = self.winfo_rootx() + self.winfo_width() // 2 - 340
            py = self.winfo_rooty() + self.winfo_height() // 2 - 270
            ventana.geometry(f"680x540+{px}+{py}")
        except Exception:
            pass

        frame = ctk.CTkScrollableFrame(ventana)
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        frame.grid_columnconfigure(1, weight=1)

        titulo = "✏️ Editar Artículo" if es_edicion else "➕ Nuevo Artículo"
        ctk.CTkLabel(frame, text=titulo, font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(5, 15), sticky="w")

        def lbl(text, row):
            ctk.CTkLabel(frame, text=text, anchor="w").grid(row=row, column=0, padx=(0, 10), pady=5, sticky="w")

        # --- Campos con orden de Tab explícito ---
        lbl("Ref. Artículo *", 1)
        e_ref = ctk.CTkEntry(frame, width=350)
        e_ref.grid(row=1, column=1, pady=5, sticky="ew")
        e_ref.insert(0, art_existente.get("referencia_articulo", ""))

        lbl("Nº Albarán", 2)
        e_albaran = ctk.CTkEntry(frame, width=350)
        e_albaran.grid(row=2, column=1, pady=5, sticky="ew")
        e_albaran.insert(0, art_existente.get("numero_albaran", "") or "")

        lbl("Nº Order", 3)
        e_order = ctk.CTkEntry(frame, width=350)
        e_order.grid(row=3, column=1, pady=5, sticky="ew")
        e_order.insert(0, art_existente.get("numero_order", "") or "")

        lbl("Cant. según Documento", 4)
        e_cant_doc = ctk.CTkEntry(frame, width=150)
        e_cant_doc.grid(row=4, column=1, pady=5, sticky="w")
        e_cant_doc.insert(0, str(art_existente.get("cantidad_segun_documento", "")))

        lbl("Cant. Entregada", 5)
        e_cant_ent = ctk.CTkEntry(frame, width=150)
        e_cant_ent.grid(row=5, column=1, pady=5, sticky="w")
        e_cant_ent.insert(0, str(art_existente.get("cantidad_entregada", "")))

        lbl("Estado", 6)
        e_estado = ctk.CTkOptionMenu(frame, values=self.OPCIONES["Estado_Producto"], width=250)
        e_estado.grid(row=6, column=1, pady=5, sticky="w")
        try:
            e_estado.set(art_existente.get("estado_producto", self.OPCIONES["Estado_Producto"][0]))
        except Exception:
            pass

        lbl("Precio Unitario", 7)
        e_precio = ctk.CTkEntry(frame, width=150)
        e_precio.grid(row=7, column=1, pady=5, sticky="w")
        e_precio.insert(0, str(art_existente.get("precio_unitario", "")))

        lbl("Precio Final", 8)
        precio_final_frame = ctk.CTkFrame(frame, fg_color="transparent")
        precio_final_frame.grid(row=8, column=1, pady=5, sticky="ew")
        e_precio_final = ctk.CTkEntry(precio_final_frame, width=120)
        e_precio_final.pack(side="left", padx=(0, 8))
        e_precio_final.insert(0, str(art_existente.get("precio_final", art_existente.get("precio_unitario", ""))))

        var_auto = ctk.IntVar(value=1)
        def _toggle_auto():
            if var_auto.get() == 1:
                e_precio_final.configure(state="disabled")
            else:
                e_precio_final.configure(state="normal")
        chk_auto = ctk.CTkCheckBox(precio_final_frame, text="Auto", variable=var_auto, command=_toggle_auto)
        chk_auto.pack(side="left")
        e_precio_final.configure(state="disabled")

        def _obtener_cliente_actual():
            """Lee el nombre del cliente desde el campo real del formulario de expediente."""
            try:
                if hasattr(self, 'entry_Cliente'):
                    return self.entry_Cliente.get().strip()
            except Exception:
                pass
            return ""

        def _obtener_descuento_actual(cliente_nombre):
            """Abre una conexión real y consulta el descuento del cliente."""
            if not cliente_nombre:
                logger.info("[DESCUENTO] Sin nombre de cliente, descuento = 0")
                return 0.0
            try:
                conn_d, cursor_d = self.master.conectar_db()
                try:
                    descuento = obtener_descuento_cliente(cliente_nombre, conn_d)
                finally:
                    try:
                        conn_d.close()
                    except Exception:
                        pass
                logger.info(f"[DESCUENTO] Cliente='{cliente_nombre}' -> descuento={descuento}")
                return descuento or 0.0
            except Exception as e:
                logger.warning(f"[DESCUENTO] Error obteniendo descuento de cliente '{cliente_nombre}': {e}")
                return 0.0

        def _recalc_precio(event=None):
            if var_auto.get() != 1:
                return
            try:
                precio_u = float(e_precio.get().replace(',', '.') or 0)
                cliente_actual = _obtener_cliente_actual()
                descuento = _obtener_descuento_actual(cliente_actual)
                tiene_dep = var_dep.get() == 1
                try:
                    porc_dep = float(e_porc_dep.get().replace(',', '.') or 0)
                except Exception:
                    porc_dep = 0.0
                pf = calcular_precio_final(precio_u, descuento, tiene_dep, porc_dep)
                e_precio_final.configure(state="normal")
                e_precio_final.delete(0, "end")
                e_precio_final.insert(0, f"{pf:.2f}")
                if var_auto.get() == 1:
                    e_precio_final.configure(state="disabled")
            except Exception as e:
                logger.warning(f"Error recalculando precio final: {e}")

        e_precio.bind("<KeyRelease>", _recalc_precio)

        lbl("Depreciación", 9)
        dep_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dep_frame.grid(row=9, column=1, pady=5, sticky="w")
        var_dep = ctk.IntVar(value=art_existente.get("depreciacion", 0))
        e_porc_dep = ctk.CTkEntry(dep_frame, width=80, placeholder_text="0")
        e_porc_dep.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(dep_frame, text="% Deprec.:").pack(side="right")
        porc_actual = art_existente.get("porcentaje_depreciacion", 0.0)
        e_porc_dep.insert(0, str(porc_actual) if porc_actual else "0")

        def _toggle_dep():
            if var_dep.get() == 1:
                e_porc_dep.configure(state="normal")
            else:
                e_porc_dep.configure(state="disabled")
                e_porc_dep.delete(0, "end")
                e_porc_dep.insert(0, "0")
            _recalc_precio()

        chk_dep = ctk.CTkCheckBox(dep_frame, text="Aplicar", variable=var_dep, command=_toggle_dep)
        chk_dep.pack(side="left")
        if var_dep.get() != 1:
            e_porc_dep.configure(state="disabled")
        e_porc_dep.bind("<KeyRelease>", _recalc_precio)

        lbl_warn_dep = ctk.CTkLabel(frame, text="", text_color="red")
        lbl_warn_dep.grid(row=10, column=0, columnspan=2, sticky="w")

        # --- Botones ---
        btn_frame = ctk.CTkFrame(ventana, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        def _guardar(event=None):
            from lib.articulo_depreciacion import validar_porcentaje_depreciacion
            referencia = e_ref.get().strip().upper()
            if not referencia:
                messagebox.showwarning("Validación", "La referencia es obligatoria.", parent=ventana)
                return
            try:
                cant_doc = float(e_cant_doc.get().replace(',', '.') or 0.0)
                cant_ent = float(e_cant_ent.get().replace(',', '.') or 0.0)
                precio_u = float(e_precio.get().replace(',', '.') or 0.0)
            except ValueError:
                messagebox.showwarning("Validación", "Cantidad y Precio deben ser números.", parent=ventana)
                return

            tiene_dep = var_dep.get() == 1
            porc_dep = 0.0
            if tiene_dep:
                es_valido, porc_dep, msg_err = validar_porcentaje_depreciacion(e_porc_dep.get().strip())
                if not es_valido:
                    messagebox.showerror("Error", f"Porcentaje de depreciación inválido: {msg_err}", parent=ventana)
                    return

            if var_auto.get() == 1:
                try:
                    cliente_actual = _obtener_cliente_actual()
                    descuento = _obtener_descuento_actual(cliente_actual)
                    precio_f = calcular_precio_final(precio_u, descuento, tiene_dep, porc_dep)
                except Exception as e:
                    logger.warning(f"Error calculando precio final al guardar: {e}")
                    precio_f = precio_u
            else:
                pf_str = e_precio_final.get().strip().replace(',', '.')
                precio_f = float(pf_str) if pf_str else precio_u

            nuevo_art = {
                "referencia_articulo": referencia,
                "numero_albaran": e_albaran.get().strip(),
                "numero_order": e_order.get().strip(),
                "cantidad_segun_documento": cant_doc,
                "cantidad_entregada": cant_ent,
                "estado_producto": e_estado.get(),
                "precio_unitario": precio_u,
                "precio_final": precio_f,
                "depreciacion": 1 if tiene_dep else 0,
                "porcentaje_depreciacion": porc_dep,
                "contabilizar": self.articulos_data[index].get("contabilizar", 1) if es_edicion else 1,
            }

            if es_edicion:
                self.articulos_data[index] = nuevo_art
            else:
                self.articulos_data.append(nuevo_art)

            self.actualizar_listado_articulos()
            ventana.destroy()

        ctk.CTkButton(btn_frame, text="✔ Guardar", command=_guardar, width=120).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="gray40", hover_color="gray30",
                      command=ventana.destroy, width=100).pack(side="right")

        # --- Navegación con Tab entre campos de entrada ---
        campos_tab = [e_ref, e_albaran, e_order, e_cant_doc, e_cant_ent, e_precio, e_porc_dep]

        def _tab_siguiente(event, campo_actual):
            idx_actual = campos_tab.index(campo_actual)
            siguiente = campos_tab[(idx_actual + 1) % len(campos_tab)]
            # Saltar e_porc_dep si la depreciación está desactivada
            if siguiente is e_porc_dep and var_dep.get() != 1:
                siguiente = campos_tab[0]
            siguiente.focus_set()
            return "break"  # Evitar el Tab por defecto de Tk

        def _tab_anterior(event, campo_actual):
            idx_actual = campos_tab.index(campo_actual)
            anterior = campos_tab[(idx_actual - 1) % len(campos_tab)]
            if anterior is e_porc_dep and var_dep.get() != 1:
                anterior = campos_tab[-2]
            anterior.focus_set()
            return "break"

        for campo in campos_tab:
            campo.bind("<Tab>", lambda e, c=campo: _tab_siguiente(e, c))
            campo.bind("<Shift-Tab>", lambda e, c=campo: _tab_anterior(e, c))
            campo.bind("<Return>", _guardar)

        # --- Escape para cerrar ---
        ventana.bind("<Escape>", lambda e: ventana.destroy())

        e_ref.focus_set()

    def actualizar_listado_articulos(self):
        """Redibuja la tabla con los artículos de la lista temporal."""
        for widget in self.articulos_list_frame.winfo_children():
            widget.destroy()
        
        # Resetear selección
        self.fila_seleccionada_articulo = None
        self.frames_seleccionados_articulo = []
            
        if not self.articulos_data:
            ctk.CTkLabel(self.articulos_list_frame, text="No hay artículos asociados a este RMA.", text_color="gray").pack(pady=10)
            return
            
        # Dibujar encabezados y filas usando grid directamente en el contenedor principal
        cols = ["Ref. Artículo", "Nº Albarán", "Nº Order", "Cant. Doc.", "Cant. Entregada", "Estado", "Precio Unit.", "Precio Final", "Deprec.", "% Deprec.", "✓ Contabiliza", "Acción", ""]
        weights = [2, 1, 1, 1, 1, 2, 1, 1, 0, 1, 0, 0, 0]
        header_font = ctk.CTkFont(weight="bold", size=12)

        # Configurar columnas del contenedor para que se alineen entre filas
        for i, w in enumerate(weights):
            try:
                self.articulos_list_frame.grid_columnconfigure(i, weight=w)
            except Exception:
                pass

        # Encabezados en la fila 0
        for i, col in enumerate(cols):
            ctk.CTkLabel(self.articulos_list_frame, text=col, font=header_font).grid(row=0, column=i, padx=5, pady=5, sticky="w")

        # Filas: colocar directamente labels en la grilla del contenedor para mantener columnas alineadas
        for i, item in enumerate(self.articulos_data):
            row = i + 1
            idx = i  # Guardar índice para eventos
            
            try:
                # Crear frames para cada columna (excepto acciones) — ahora son 10 columnas de datos
                frames_fila = []
                for col in range(10):  # Columnas 0-9 (ref, albaran, order, cant_doc, cant_ent, estado, precio_u, precio_f, deprec, porc)
                    f = ctk.CTkFrame(self.articulos_list_frame, fg_color="transparent")
                    f.grid(row=row, column=col, sticky="ew", padx=0, pady=0)
                    frames_fila.append(f)
                
                # Labels dentro de los frames
                lbl_ref = ctk.CTkLabel(frames_fila[0], text=item["referencia_articulo"])
                lbl_ref.pack(anchor="w", padx=5, pady=2)

                lbl_albaran = ctk.CTkLabel(frames_fila[1], text=item.get("numero_albaran", "") or "")
                lbl_albaran.pack(anchor="w", padx=5, pady=2)

                lbl_order = ctk.CTkLabel(frames_fila[2], text=item.get("numero_order", "") or "")
                lbl_order.pack(anchor="w", padx=5, pady=2)

                lbl_cant_doc = ctk.CTkLabel(frames_fila[3], text=item["cantidad_segun_documento"])
                lbl_cant_doc.pack(anchor="w", padx=5, pady=2)
                
                lbl_cant_ent = ctk.CTkLabel(frames_fila[4], text=item["cantidad_entregada"])
                lbl_cant_ent.pack(anchor="w", padx=5, pady=2)
                
                lbl_estado = ctk.CTkLabel(frames_fila[5], text=item["estado_producto"])
                lbl_estado.pack(anchor="w", padx=5, pady=2)
                
                lbl_precio_unit = ctk.CTkLabel(frames_fila[6], text=f"{item['precio_unitario']:.2f} €")
                lbl_precio_unit.pack(anchor="w", padx=5, pady=2)
                
                precio_final = item.get("precio_final", item.get("precio_unitario", 0.0))
                lbl_precio_final = ctk.CTkLabel(frames_fila[7], text=f"{precio_final:.2f} €")
                lbl_precio_final.pack(anchor="w", padx=5, pady=2)
                
                deprec_text = "✓" if item.get("depreciacion", 0) == 1 else "-"
                lbl_deprec = ctk.CTkLabel(frames_fila[8], text=deprec_text)
                lbl_deprec.pack(anchor="w", padx=5, pady=2)
                
                porcentaje = item.get("porcentaje_depreciacion", 0.0)
                porcentaje_text = f"{porcentaje}%" if item.get("depreciacion", 0) == 1 else "-"
                lbl_porc = ctk.CTkLabel(frames_fila[9], text=porcentaje_text)
                lbl_porc.pack(anchor="w", padx=5, pady=2)

                # Checkbox de contabilizar (solo editable por Admin y Dpto. Técnico) — columna 10
                contabilizar_value = item.get("contabilizar", 1)
                
                # Convertir explícitamente a int para evitar problemas con strings
                try:
                    contabilizar_int = int(contabilizar_value)
                except (ValueError, TypeError):
                    contabilizar_int = 1
                    logger.warning(f"Valor de contabilizar inválido: {contabilizar_value} (tipo: {type(contabilizar_value).__name__}), usando 1")
                
                logger.debug(f"[RENDER] Artículo {item.get('referencia_articulo')}: contabilizar_value={contabilizar_value} -> int={contabilizar_int} -> bool={bool(contabilizar_int)}")
                
                var_contabilizar = ctk.BooleanVar(value=bool(contabilizar_int))
                
                # Determinar si el usuario puede modificar
                puede_modificar = self.rol in ["admin", "administrador", "Dpto. Tecnico"]
                
                def _toggle_contabilizar(idx_art=idx, var_chk=var_contabilizar):
                    nuevo_valor = 1 if var_chk.get() else 0
                    self.articulos_data[idx_art]['contabilizar'] = nuevo_valor
                    logger.info(f"Artículo {self.articulos_data[idx_art]['referencia_articulo']} - Contabilizar: {nuevo_valor} (checkbox: {var_chk.get()})")
                
                chk_contabilizar = ctk.CTkCheckBox(
                    self.articulos_list_frame, 
                    text="", 
                    variable=var_contabilizar,
                    command=_toggle_contabilizar,
                    width=30,
                    state="normal" if puede_modificar else "disabled"
                )
                chk_contabilizar.grid(row=row, column=10, padx=5, pady=2, sticky="w")

                # Acciones: Eliminar y Editar — columnas 11 y 12
                ctk.CTkButton(self.articulos_list_frame, text="X", width=30, fg_color="red", hover_color="darkred",
                              command=lambda idx=i: self.eliminar_articulo(idx)).grid(row=row, column=11, padx=5, pady=2, sticky="w")
                try:
                    ctk.CTkButton(self.articulos_list_frame, text="✏️", width=30,
                                  command=lambda idx=i: self.editar_articulo(idx)).grid(row=row, column=12, padx=2, pady=2, sticky="w")
                except Exception:
                    pass
                
                # Eventos de selección
                labels_fila = [lbl_ref, lbl_albaran, lbl_order, lbl_cant_doc, lbl_cant_ent, lbl_estado, lbl_precio_unit, lbl_precio_final, lbl_deprec, lbl_porc]
                
                def _seleccionar_articulo(e, frames=frames_fila, idx_art=idx):
                    if hasattr(self, 'frames_seleccionados_articulo') and self.frames_seleccionados_articulo:
                        for f in self.frames_seleccionados_articulo:
                            try:
                                f.configure(fg_color="transparent")
                            except:
                                pass
                    
                    try:
                        modo = ctk.get_appearance_mode()
                        color_sel = ("#D6EAF8" if modo == "Light" else "#2C5F8D")
                    except:
                        color_sel = "#D6EAF8"
                    
                    for f in frames:
                        try:
                            f.configure(fg_color=color_sel)
                        except:
                            pass
                    
                    self.fila_seleccionada_articulo = idx_art
                    self.frames_seleccionados_articulo = frames
                
                def _on_enter_art(e, frames=frames_fila, idx_art=idx):
                    if not hasattr(self, 'fila_seleccionada_articulo') or self.fila_seleccionada_articulo != idx_art:
                        try:
                            modo = ctk.get_appearance_mode()
                            hover_color = ("#F5F5F5" if modo == "Light" else "#2B2B2B")
                        except:
                            hover_color = "#F5F5F5"
                        for f in frames:
                            try:
                                f.configure(fg_color=hover_color)
                            except:
                                pass
                
                def _on_leave_art(e, frames=frames_fila, idx_art=idx):
                    if not hasattr(self, 'fila_seleccionada_articulo') or self.fila_seleccionada_articulo != idx_art:
                        for f in frames:
                            try:
                                f.configure(fg_color="transparent")
                            except:
                                pass
                
                # Bind a frames y labels
                for f in frames_fila:
                    f.bind("<Button-1>", _seleccionar_articulo)
                    f.bind("<Double-Button-1>", lambda e, idx_art=idx: self.editar_articulo(idx_art))
                    f.bind("<Enter>", _on_enter_art)
                    f.bind("<Leave>", _on_leave_art)
                    f.configure(cursor="hand2")
                
                for lbl in labels_fila:
                    lbl.bind("<Button-1>", _seleccionar_articulo)
                    lbl.bind("<Double-Button-1>", lambda e, idx_art=idx: self.editar_articulo(idx_art))
                    lbl.configure(cursor="hand2")
                
            except Exception:
                # Silenciar errores de renderizado individual para no romper toda la lista
                pass
            
        # --- NUEVO: Calcular y actualizar el Precio Total en la etiqueta de Contabilidad ---
        precio_total = 0.0
        
        for item in self.articulos_data:
            try:
                # Convertir cantidad_entregada a float de forma segura
                cantidad = item.get('cantidad_entregada', 0)
                if isinstance(cantidad, str):
                    # Limpiar el string y convertir a float
                    cantidad = float(cantidad.replace(',', '.')) if cantidad.strip() else 0.0
                elif cantidad is None:
                    cantidad = 0.0
                else:
                    cantidad = float(cantidad)

                # Usar precio_final en lugar de precio_unitario para el cálculo
                precio = item.get('precio_final', item.get('precio_unitario', 0.0))
                if isinstance(precio, str):
                    # Limpiar el string y convertir a float
                    precio = float(precio.replace(',', '.')) if precio.strip() else 0.0
                elif precio is None:
                    precio = 0.0
                else:
                    precio = float(precio)

                # Multiplicar de forma segura
                precio_total += cantidad * precio

            except (ValueError, TypeError) as e:
                # Si hay un error en la conversión, ignorar este artículo y continuar
                print(f"Error al calcular precio para artículo {item.get('referencia_articulo', 'N/A')}: {e}")
                continue
        
        # Esto es seguro porque lbl_precio_total se crea en mostrar_nuevo_rma
        if hasattr(self, 'lbl_precio_total'):
            self.lbl_precio_total.configure(text=f"{precio_total:.2f} €")

        # Guardar el precio total en la BD si estamos editando un expediente ya existente
        try:
            self.guardar_precio_total_expediente()
        except Exception:
            # No bloquear la UI si la actualización en BD falla aquí; el guardado final también actualizará
            pass

    def guardar_precio_total_expediente(self):
        """Recalcula el precio total desde `self.articulos_data` y lo persiste
        en `rma_maestro.precio_total_expediente` si el RMA está abierto (tiene id)."""
        # Calcular total localmente
        precio_total = 0.0
        for item in getattr(self, 'articulos_data', []):
            try:
                cantidad = item.get('cantidad_entregada', 0) or 0
                if isinstance(cantidad, str):
                    cantidad = float(cantidad.replace(',', '.')) if cantidad.strip() else 0.0
                else:
                    cantidad = float(cantidad)

                # Usar precio_final si existe, sino precio_unitario como fallback
                precio = item.get('precio_final', None)
                if precio is None or precio == '' or precio == 0:
                    precio = item.get('precio_unitario', 0.0) or 0.0

                if isinstance(precio, str):
                    precio = float(precio.replace(',', '.')) if precio.strip() else 0.0
                else:
                    precio = float(precio)

                precio_total += cantidad * precio
            except Exception:
                continue

        # Actualizar etiqueta si existe
        try:
            if hasattr(self, 'lbl_precio_total'):
                self.lbl_precio_total.configure(text=f"{precio_total:.2f} €")
        except Exception:
            pass

        # Si estamos editando un expediente ya guardado, escribir en BD
        try:
            if getattr(self, 'rma_actual_id', None) is not None:
                conn, cursor = self.master.conectar_db()
                if conn:
                    try:
                        cursor.execute("UPDATE rma_maestro SET precio_total_expediente = ? WHERE id = ?", (precio_total, self.rma_actual_id))
                        conn.commit()
                    finally:
                        conn.close()
        except Exception as e:
            print(f"Error guardando precio_total_expediente: {e}")

    def guardar_rma_placeholder(self):
        """Punto de entrada para guardar/actualizar."""
        # Validación: Si hay Fecha Gestión, debe haber Resultado Expediente
        try:
            # Obtener el widget de Fecha_Gestion
            fecha_gestion_widget = getattr(self, "entry_Fecha_Gestion", None)
            if fecha_gestion_widget:
                if hasattr(fecha_gestion_widget, 'get_date'):
                    fecha_gestion = fecha_gestion_widget.get_date()
                elif hasattr(fecha_gestion_widget, 'get'):
                    fecha_gestion = fecha_gestion_widget.get()
                else:
                    fecha_gestion = ""
            else:
                fecha_gestion = ""
            
            # Obtener el widget de Resultado_Expediente
            resultado_widget = getattr(self, "entry_Resultado_Expediente", None)
            if resultado_widget:
                if hasattr(resultado_widget, 'get'):
                    resultado_expediente = resultado_widget.get()
                else:
                    resultado_expediente = resultado_widget.cget("text")
            else:
                resultado_expediente = ""
            
            # Si hay fecha de gestión (expediente cerrado)
            if fecha_gestion and str(fecha_gestion).strip():
                # Verificar que haya resultado
                if not resultado_expediente or str(resultado_expediente).strip() == "":
                    messagebox.showwarning(
                        "Resultado Obligatorio",
                        "⚠️ No se puede cerrar un expediente sin especificar el Resultado.\n\n"
                        "Ha indicado una Fecha de Gestión, pero no ha seleccionado "
                        "un Resultado de Expediente en la pestaña Contabilidad.\n\n"
                        "Por favor, seleccione un resultado antes de guardar."
                    )
                    return  # No guardar
        except Exception as e:
            print(f"Error en validación de campos: {e}")
            # Continuar con el guardado si hay error en la validación
        
        if self.rma_actual_id is None:
            self.guardar_nuevo_rma()
        else:
            self.actualizar_rma()

    def eliminar_expediente(self, rma_id):
        """
        Elimina un expediente completo incluyendo todos sus datos relacionados.
        Solo disponible para usuario admin.
        """
        # Verificar permisos de admin
        if self.username.lower() != "admin":
            messagebox.showerror("Acceso Denegado", "Solo el administrador puede eliminar expedientes.")
            return
        
        try:
            conn = self.master.conectar_db()
            cursor = conn.cursor()
            
            # Obtener información del expediente para mostrar en la advertencia
            cursor.execute("""
                SELECT codigo_rma, cliente, numero_documento_cliente, resultado_expediente
                FROM rma_maestro 
                WHERE id = ?
            """, (rma_id,))
            info_exp = cursor.fetchone()
            
            if not info_exp:
                messagebox.showerror("Error", "No se encontró el expediente.")
                return
            
            codigo_rma, cliente, num_doc, resultado = info_exp
            
            # Contar datos relacionados
            cursor.execute("SELECT COUNT(*) FROM rma_detalles WHERE rma_id = ?", (rma_id,))
            num_articulos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rma_historial WHERE rma_id = ?", (rma_id,))
            num_historial = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tareas WHERE expediente_codigo = ?", (codigo_rma,))
            num_tareas = cursor.fetchone()[0]
            
            conn.close()
            
            # Crear ventana de advertencia personalizada
            ventana_advertencia = ctk.CTkToplevel(self)
            ventana_advertencia.title("⚠️ ADVERTENCIA - Eliminar Expediente")
            ventana_advertencia.geometry("600x450")
            ventana_advertencia.transient(self)
            ventana_advertencia.grab_set()
            
            # Frame principal
            main_frame = ctk.CTkFrame(ventana_advertencia)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título de advertencia
            lbl_titulo = ctk.CTkLabel(
                main_frame,
                text="⚠️ ADVERTENCIA: ELIMINACIÓN PERMANENTE",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="red"
            )
            lbl_titulo.pack(pady=(0, 20))
            
            # Información del expediente
            info_frame = ctk.CTkFrame(main_frame)
            info_frame.pack(fill="x", pady=10)
            
            info_texto = f"""
EXPEDIENTE A ELIMINAR:

• Código RMA: {codigo_rma}
• Cliente: {cliente}
• Número Documento: {num_doc}
• Resultado: {resultado or 'Sin resultado'}

DATOS RELACIONADOS QUE SE ELIMINARÁN:

• Artículos en RMA: {num_articulos}
• Registros de historial: {num_historial}
• Tareas asociadas: {num_tareas}

⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER ⚠️
            """
            
            lbl_info = ctk.CTkLabel(
                info_frame,
                text=info_texto,
                font=ctk.CTkFont(size=13),
                justify="left"
            )
            lbl_info.pack(padx=10, pady=10)
            
            # Campo de confirmación
            lbl_confirmar = ctk.CTkLabel(
                main_frame,
                text='Para confirmar, escriba "ELIMINAR" en el campo siguiente:',
                font=ctk.CTkFont(size=12, weight="bold")
            )
            lbl_confirmar.pack(pady=(10, 5))
            
            entry_confirmar = ctk.CTkEntry(
                main_frame,
                width=300,
                font=ctk.CTkFont(size=14)
            )
            entry_confirmar.pack(pady=5)
            
            # Frame de botones
            btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            btn_frame.pack(pady=20)
            
            def ejecutar_eliminacion():
                """Ejecuta la eliminación si la confirmación es correcta"""
                confirmacion = entry_confirmar.get().strip().upper()
                
                if confirmacion != "ELIMINAR":
                    messagebox.showwarning("Confirmación Incorrecta", 
                                         'Debe escribir exactamente "ELIMINAR" para confirmar.')
                    return
                
                try:
                    conn = self.master.conectar_db()
                    cursor = conn.cursor()
                    
                    # Eliminar en orden de dependencias
                    # 1. Detalles de artículos
                    cursor.execute("DELETE FROM rma_detalles WHERE rma_id = ?", (rma_id,))
                    
                    # 2. Historial
                    cursor.execute("DELETE FROM rma_historial WHERE rma_id = ?", (rma_id,))
                    
                    # 3. Tareas asociadas
                    cursor.execute("DELETE FROM tareas WHERE expediente_codigo = ?", (codigo_rma,))
                    
                    # 4. Finalmente el registro maestro
                    cursor.execute("DELETE FROM rma_maestro WHERE id = ?", (rma_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Expediente Eliminado", 
                                      f"El expediente {codigo_rma} y todos sus datos relacionados han sido eliminados correctamente.")
                    
                    ventana_advertencia.destroy()
                    
                    # Cerrar la ventana del expediente actual
                    if hasattr(self, 'destroy'):
                        self.destroy()
                    
                    # Refrescar la tabla principal si existe
                    if hasattr(self.master, 'actualizar_tabla_rmas'):
                        self.master.actualizar_tabla_rmas()
                        
                except Exception as e:
                    messagebox.showerror("Error", f"Error al eliminar el expediente:\n{str(e)}")
            
            btn_eliminar = ctk.CTkButton(
                btn_frame,
                text="🗑️ ELIMINAR EXPEDIENTE",
                fg_color="red",
                hover_color="darkred",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=ejecutar_eliminacion,
                width=200
            )
            btn_eliminar.pack(side="left", padx=5)
            
            btn_cancelar = ctk.CTkButton(
                btn_frame,
                text="✖ Cancelar",
                font=ctk.CTkFont(size=14),
                command=ventana_advertencia.destroy,
                width=150
            )
            btn_cancelar.pack(side="left", padx=5)
            
            # Focus en el campo de confirmación
            entry_confirmar.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar la eliminación:\n{str(e)}")

    def guardar_nuevo_rma(self):
        """Valida los campos y realiza la inserción en rma_maestro y rma_detalles."""
        
        # 0. Validar que el cliente existe en la base de datos de clientes
        # Obtener el nombre del cliente primero
        entry_cliente = getattr(self, 'entry_Cliente', None)
        if entry_cliente:
            nombre_cliente = ""
            try:
                if hasattr(entry_cliente, 'get'):
                    nombre_cliente = entry_cliente.get().strip()
                elif hasattr(entry_cliente, 'cget'):
                    nombre_cliente = entry_cliente.cget("text").strip()
            except Exception:
                nombre_cliente = ""
            
            if nombre_cliente:
                # Verificar si el cliente existe en la tabla clientes
                try:
                    conn_check, cursor_check = self.master.conectar_db()
                    if conn_check:
                        cursor_check.execute("SELECT cliente_id, activo FROM clientes WHERE nombre = ?", (nombre_cliente,))
                        resultado = cursor_check.fetchone()
                        conn_check.close()
                        
                        if not resultado:
                            # Cliente no existe - mostrar mensaje de advertencia
                            self._mostrar_dialogo_cliente_no_existe(nombre_cliente)
                            return  # Cancelar el guardado
                        elif resultado and resultado[1] == 0:
                            # Cliente existe pero está inactivo
                            messagebox.showerror(
                                "Cliente Inactivo",
                                f"El cliente '{nombre_cliente}' está inactivo y no puede ser usado para nuevos expedientes.\n\n"
                                "Por favor, contacte con el administrador para reactivarlo.",
                                icon="warning"
                            )
                            return  # Cancelar el guardado
                except Exception as e:
                    print(f"Error verificando cliente: {e}")
                    # Si hay error, permitir continuar (no bloquear por error de verificación)
        
        # 1. Recolección y Validación de campos obligatorios
        datos_maestro = {}
        campos_a_insertar = [
            'Cliente', 'Numero_Documento_Cliente', 'Persona_de_Contacto', 'Email_de_Contacto',
            'Autorizacion', 'Autorizado_Por', 'Fecha_Autorizacion', 'Fecha_Recepcion',
            'Recepcionado_Por', 'Fecha_Gestion', 'Gestionado_Por', 'Fecha_Proceso', 'Procesado_Por',
            'Fecha_para_factura', 'Numero_Albaran', 'Fecha_Doc_Cliente', 'Resultado_Expediente', 'motivo', 'Rma_Proveedor',
            'Modelo', 'N_Serie', 'Ref_Proveedor', 'Obs_Tecnica', 'Resolucion_Provisional', 'Obs_Res_Provisional',
            'numero_albaran_reposicion', 'fecha_albaran_reposicion', 'numero_factura_abono', 'fecha_factura_abono'
        ]
        
        for campo in campos_a_insertar:
            entry = getattr(self, f"entry_{campo}")
            # Obtener el valor según el tipo de widget; soportar CTkDatePicker con get_date()/get()
            try:
                if isinstance(entry, ctk.CTkTextbox):
                    valor = entry.get("1.0", "end-1c").strip()
                elif hasattr(entry, 'get_date'):
                    # CTkDatePicker exposes get_date() and also get() alias
                    valor = entry.get_date()
                elif hasattr(entry, 'get'):
                    valor = entry.get()
                else:
                    valor = entry.cget("text")
            except Exception:
                # Fallback seguro
                try:
                    if hasattr(entry, 'get_date'):
                        valor = entry.get_date()
                    else:
                        valor = entry.get()
                except Exception:
                    valor = ''
            
            # Validación de obligatorios
            if campo in ["Cliente", "Numero_Documento_Cliente", "Persona_de_Contacto", "Email_de_Contacto", "motivo"] and not valor:
                print(f"Error: El campo {campo.replace('_', ' ')} es obligatorio.")
                messagebox.showinfo("Advertencia", f"Error: El campo {campo.replace('_', ' ')} es obligatorio.")
                # Aquí deberías mostrar un mensaje de error en la interfaz
                return
            
            # Para los campos de fecha, validar y normalizar a ISO YYYY-MM-DD
            DATE_FIELDS = {'Fecha_Autorizacion', 'Fecha_Recepcion', 'Fecha_Proceso', 'Fecha_Gestion', 'Fecha_Emision', 'Fecha_Doc_Cliente', 'fecha_albaran_reposicion', 'fecha_factura_abono'}
            if campo in DATE_FIELDS:
                # Permitir valor vacío
                if valor is None or str(valor).strip() == "":
                    datos_maestro[campo.lower()] = ''
                else:
                    try:
                        datos_maestro[campo.lower()] = parse_date_to_iso(valor)
                    except ValueError as e:
                        messagebox.showerror("Fecha inválida", f"El campo {campo} debe ser una fecha válida. Valor: {valor}")
                        return
            else:
                # Campos no fecha: conversiones especiales
                if campo == 'Autorizacion':
                    try:
                        v = str(valor).strip().upper() if valor is not None else ''
                        datos_maestro[campo.lower()] = 1 if v in ('1', 'SI', 'S', 'TRUE', 'T') else 0
                    except Exception:
                        datos_maestro[campo.lower()] = 0
                elif campo == 'Email_de_Contacto':
                    datos_maestro[campo.lower()] = valor.lower() if valor else ''
                elif campo == 'Autorizado_Por':
                    datos_maestro[campo.lower()] = valor.upper() if valor else ''
                else:
                    datos_maestro[campo.lower()] = valor

        # Campos automáticos/calculados
        # NOTA: El código_rma se generará al momento del guardado para evitar condiciones de carrera
        if hasattr(self, 'es_modo_edicion') and self.es_modo_edicion:
            # En modo edición, conservamos el código existente
            datos_maestro['codigo_rma'] = self.lbl_codigo_rma.cget("text").split(": ")[1]
        else:
            # En modo nuevo, lo generaremos dentro de la transacción
            # No asignamos código_rma aquí
            pass
            
        datos_maestro['fecha_emision'] = self.entry_Fecha_Emision.get()
        datos_maestro['creado_por'] = self.entry_Creado_Por.get()

        if datos_maestro.get('resolucion_provisional'):
            logger.info(
                f"[RESOLUCION_PROVISIONAL] Nuevo expediente: 'resolucion_provisional'="
                f"'{datos_maestro.get('resolucion_provisional')}' 'obs_res_provisional'="
                f"'{datos_maestro.get('obs_res_provisional', '')}' (usuario={self.username})")

        # Definir estado inicial basado en Autorización
        # 1. INTEGRACIÓN DE LA TRAZABILIDAD
        datos_maestro['estado'] = self.determinar_estado_rma(datos_maestro)
        
        # 2. Calcular Precio Total y validar Artículos
        precio_total = 0.0
        
        for item in self.articulos_data:
            try:
                # Convertir cantidad_entregada a float de forma segura
                cantidad = item.get('cantidad_entregada', 0)
                if isinstance(cantidad, str):
                    cantidad = float(cantidad.replace(',', '.')) if cantidad.strip() else 0.0
                elif cantidad is None:
                    cantidad = 0.0
                else:
                    cantidad = float(cantidad)
                
                # Usar precio_final si existe, sino precio_unitario como fallback
                precio = item.get('precio_final', None)
                if precio is None or precio == '' or precio == 0:
                    precio = item.get('precio_unitario', 0.0)
                
                if isinstance(precio, str):
                    precio = float(precio.replace(',', '.')) if precio.strip() else 0.0
                elif precio is None:
                    precio = 0.0
                else:
                    precio = float(precio)
                
                precio_total += cantidad * precio
                
            except (ValueError, TypeError) as e:
                print(f"Error al calcular precio para artículo {item.get('referencia_articulo', 'N/A')}: {e}")
                continue
        
        datos_maestro['precio_total_expediente'] = precio_total

        # 2.5 Validación: Numero de documento del cliente no debe repetirse
        # Se permiten repeticiones para valores provisionales que contengan 'email' o 'telefonic'
        numero_doc = str(datos_maestro.get('numero_documento_cliente', '')).strip()
        if numero_doc:
            numero_doc_norm = numero_doc.lower()
            # Si el valor contiene las palabras provisionales (email/e-mail/telefonica/telefonico), no realizar la comprobación de duplicados
            if not re.search(r"\b(e-?mail|telefonica|telefonico)\b", numero_doc_norm, re.IGNORECASE):
                # Conectar a la DB para comprobar duplicados
                conn_check, cursor_check = self.master.conectar_db()
                if not conn_check:
                    return
                try:
                    cursor_check = conn_check.cursor()
                    cursor_check.execute("SELECT COUNT(*) FROM rma_maestro WHERE lower(numero_documento_cliente) = ?", (numero_doc_norm,))
                    count = cursor_check.fetchone()[0]
                    # Convertir a entero para evitar errores de comparación
                    count = int(count) if count is not None else 0
                    if count > 0:
                        conn_check.close()
                        messagebox.showwarning("Valor duplicado", f"El número de documento '{numero_doc}' ya existe en otro expediente.")
                        return
                except sqlite3.Error as e:
                    print(f"Error comprobando duplicados de numero_documento_cliente: {e}")
                    conn_check.close()
                    return
                # Cerramos la conexión de comprobación; la conexión principal se abrirá más abajo para la inserción
                conn_check.close()

        # if not self.articulos_data:
        #     print("Error: Debe añadir al menos un artículo.")
        #     return

        # Aviso: Si el número de documento contiene palabras provisionales, pedir confirmación al usuario
        try:
            if numero_doc and re.search(r"\b(e-?mail|telefonica|telefonico)\b", numero_doc, re.IGNORECASE):
                respuesta_prov = messagebox.askyesno("Valor provisional detectado",
                                                     "El campo 'Núm. Doc. Cliente' contiene un valor provisional (p.ej. 'Email' o 'Telefonica').\n¿Deseas continuar guardando el expediente con este valor?")
                if not respuesta_prov:
                    return
        except Exception:
            # Si falla mostrar el diálogo, continuar sin bloquear el guardado
            pass

        # 3. Inserción en la Base de Datos
        # ── Editor enriquecido: sobreescribir obs_tecnica con JSON completo ──
        if hasattr(self, 'entry_Obs_Tecnica') and hasattr(self.entry_Obs_Tecnica, 'get_content'):
            datos_maestro['obs_tecnica'] = self.entry_Obs_Tecnica.get_content()

        conn, cursor = self.master.conectar_db()
        if not conn: return
        cursor = conn.cursor()
        
        try:
            # Para nuevos RMA, generar el código final dentro de la transacción
            if not hasattr(self, 'es_modo_edicion') or not self.es_modo_edicion:
                codigo_rma_final = self.generar_codigo_rma_final(cursor)
                datos_maestro['codigo_rma'] = codigo_rma_final
            
            # 3a. Inserción en rma_maestro
            columnas_maestro = ', '.join(datos_maestro.keys())
            placeholders_maestro = ', '.join('?' * len(datos_maestro))
            valores_maestro = tuple(datos_maestro.values())
            
            cursor.execute(f"""
                INSERT INTO rma_maestro ({columnas_maestro}, estado) 
                VALUES ({placeholders_maestro}, ?)
            """, valores_maestro + (datos_maestro['estado'],)) # El estado se añade al final

            # Obtener el ID del RMA recién creado
            rma_id_generado = cursor.lastrowid
            
            # 3b. Inserción en rma_detalles - OPTIMIZADO con executemany
            if self.articulos_data:
                # Preparar todos los artículos para inserción batch
                primer_articulo = self.articulos_data[0].copy()
                primer_articulo['rma_id'] = rma_id_generado
                
                columnas_detalle = ', '.join(primer_articulo.keys())
                placeholders_detalle = ', '.join('?' * len(primer_articulo))
                
                # LOG: Debug de valores de contabilizar
                for i, art in enumerate(self.articulos_data):
                    logger.debug(f"Guardando artículo {i}: ref={art.get('referencia_articulo')} contabilizar={art.get('contabilizar', 'NO_FIELD')}")
                
                # Asegurar que todos los artículos tienen los campos nuevos (compatibilidad)
                campos_nuevos_defaults = {"numero_albaran": "", "numero_order": ""}
                for art in self.articulos_data:
                    for campo, defval in campos_nuevos_defaults.items():
                        if campo not in art:
                            art[campo] = defval

                # Preparar lista de valores para executemany
                valores_batch = []
                for articulo in self.articulos_data:
                    articulo_copia = articulo.copy()
                    articulo_copia['rma_id'] = rma_id_generado
                    valores_batch.append(tuple(articulo_copia.values()))
                
                # Insertar todos los artículos en una sola llamada (mucho más rápido con Turso)
                cursor.executemany(f"""
                    INSERT INTO rma_detalles ({columnas_detalle}) 
                    VALUES ({placeholders_detalle})
                """, valores_batch)

            # 3c. Inserción en rma_historial (modificar descripción si no hay artículos)
            num_articulos = len(self.articulos_data)
            descripcion = f"RMA creado. Cliente: {datos_maestro['cliente']}. Artículos: {num_articulos}. Total: {precio_total:.2f} €"
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (rma_id_generado, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, descripcion))

            # 3d. Guardar número de orden en rma_orders
            # Obtener num_order directamente del widget ya que no está en campos_a_insertar
            num_order = ''
            if hasattr(self, 'entry_Num_Order'):
                try:
                    num_order = self.entry_Num_Order.get() if hasattr(self.entry_Num_Order, 'get') else ''
                except Exception:
                    num_order = ''
            
            if num_order and str(num_order).strip():
                cursor.execute("""
                    INSERT INTO rma_orders (rma_id, num_order)
                    VALUES (?, ?)
                """, (rma_id_generado, str(num_order).strip()))

            conn.commit()
            
            # Invalidar caché de estados (puede que se haya creado un nuevo estado)
            invalidate_cache('estados_rma')
            
            # Mostrar mensaje de confirmación con número RMA final
            if not hasattr(self, 'es_modo_edicion') or not self.es_modo_edicion:
                # Es un nuevo expediente - mostrar el número final asignado
                codigo_final = datos_maestro['codigo_rma']
                messagebox.showinfo("¡Expediente Creado!",
                                    f"✅ Expediente creado exitosamente\n\n"
                                    f"📋 Número final asignado: {codigo_final}\n"
                                    f"👤 Cliente: {datos_maestro['cliente']}\n"
                                    f"💰 Total: {precio_total:.2f} €\n\n"
                                    f"Ya puede adjuntar archivos y gestionar el expediente.")
            else:
                messagebox.showinfo("Expediente Guardado", "El expediente se ha actualizado correctamente.")

            # IMPORTANTE: Actualizar ambos IDs para que el siguiente guardado use actualizar_rma()
            self.current_rma_id = rma_id_generado  # Asigna el ID al atributo de instancia
            self.rma_actual_id = rma_id_generado   # CRÍTICO: Actualizar para que guardar_rma_placeholder() use actualizar_rma()
            self.mode = 'editar'                    # Cambia la ventana a modo edición
            self.es_modo_edicion = True            # Actualizar el indicador

            # Reconstruir la ficha completa en modo edición: varios botones (Email, Informe,
            # Reposición/Devolución, Autorización, Reabrir, Eliminar) y la pestaña de Adjuntos
            # solo se crean cuando es_edicion=True, así que hay que volver a llamar a
            # mostrar_nuevo_rma() con el id ya asignado para que aparezcan sin necesidad de
            # cerrar y reabrir la ventana. Se reutiliza el content_frame en el que se
            # construyó originalmente esta ficha (ventana principal o RmaEditorWindow).
            try:
                content_frame_destino = getattr(self, '_content_frame_ficha_actual', self.content_frame)
                content_frame_original = self.content_frame
                self.content_frame = content_frame_destino
                try:
                    self.mostrar_nuevo_rma(self.rma_actual_id)
                finally:
                    self.content_frame = content_frame_original
            except Exception as e:
                logger.error(f"Error reconstruyendo la ficha tras guardar nuevo expediente: {e}")

            # NO volver al listado - mantener el expediente abierto para que puedan trabajar con él

        except sqlite3.IntegrityError as e:
            if hasattr(conn, 'rollback'):
                conn.rollback()
            print(f"Error al guardar (Integridad): {e}. Es posible que el código RMA ya exista.")
            messagebox.showerror("Error de Integridad", f"No se pudo guardar el expediente:\n{e}")
        except sqlite3.Error as e:
            if hasattr(conn, 'rollback'):
                conn.rollback()
            print(f"Error general de DB al guardar: {e}")
            messagebox.showerror("Error de Base de Datos", f"Error al guardar:\n{e}")
        finally:
            conn.close()

    def obtener_datos_actuales_maestro(self):
        """Recupera los datos del formulario MAESTRO actuales."""
        datos_maestro = {}
        # Lista de campos de la tabla rma_maestro que corresponden a entries
        campos_a_recuperar = [
            'Cliente', 'Numero_Documento_Cliente', 'Persona_de_Contacto', 'Email_de_Contacto',
            'Autorizacion', 'Autorizado_Por', 'Fecha_Autorizacion', 'Fecha_Recepcion',
            'Recepcionado_Por', 'Fecha_Gestion', 'Gestionado_Por', 'Fecha_Proceso', 'Procesado_Por',
            'Fecha_para_factura', 'Numero_Albaran', 'Fecha_Doc_Cliente', 'Resultado_Expediente',
            'Fecha_Emision', 'Creado_Por', 'motivo', 'Rma_Proveedor', 'Modelo', 'N_Serie', 'Ref_Proveedor', 'Obs_Tecnica',
            'Resolucion_Provisional', 'Obs_Res_Provisional',
            'numero_albaran_reposicion', 'fecha_albaran_reposicion', 'numero_factura_abono', 'fecha_factura_abono'
        ]

        for campo in campos_a_recuperar:
            entry_name = f"entry_{campo}"
            if hasattr(self, entry_name):
                entry = getattr(self, entry_name)
                # Intenta obtener el valor de la entrada o del optionmenu
                # Soportar CTkTextbox (requiere índices para get)
                try:
                    if isinstance(entry, ctk.CTkTextbox):
                        valor = entry.get("1.0", "end-1c").strip()
                    elif hasattr(entry, 'get_date'):
                        valor = entry.get_date()
                    elif hasattr(entry, 'get'):
                        valor = entry.get()
                    else:
                        valor = entry.cget("text")
                except Exception:
                    # Fallback
                    try:
                        if hasattr(entry, 'get_date'):
                            valor = entry.get_date()
                        else:
                            valor = entry.get()
                    except Exception:
                        valor = ''

                # Normalizar fechas si corresponde
                DATE_FIELDS = {'Fecha_Autorizacion', 'Fecha_Recepcion', 'Fecha_Proceso', 'Fecha_Gestion', 'Fecha_Emision', 'Fecha_Doc_Cliente', 'fecha_albaran_reposicion', 'fecha_factura_abono'}
                if campo in DATE_FIELDS:
                    if valor is None or str(valor).strip() == "":
                        datos_maestro[campo.lower()] = ''
                    else:
                        try:
                            datos_maestro[campo.lower()] = parse_date_to_iso(valor)
                        except ValueError:
                            # Mostrar error y abortar la recolección para forzar corrección
                            messagebox.showerror("Fecha inválida", f"El campo {campo} debe contener una fecha válida. Valor: {valor}")
                            return None
                else:
                    # Conversión especial para Autorizacion (SI/NO a 1/0)
                    if campo == 'Autorizacion':
                        try:
                            v = str(valor).strip().upper() if valor is not None else ''
                            datos_maestro['autorizacion'] = 1 if v in ('1', 'SI', 'S', 'TRUE', 'T') else 0
                        except Exception:
                            datos_maestro['autorizacion'] = 0
                    # Conversión especial para Email_de_Contacto (siempre en minúsculas)
                    elif campo == 'Email_de_Contacto':
                        datos_maestro[campo.lower()] = valor.lower() if valor else ''
                    # Conversión especial para Autorizado_Por (siempre en mayúsculas)
                    elif campo == 'Autorizado_Por':
                        datos_maestro[campo.lower()] = valor.upper() if valor else ''
                    else:
                        datos_maestro[campo.lower()] = valor
        
        datos_maestro['codigo_rma'] = self.lbl_codigo_rma.cget("text").split(": ")[1]
        
        # ── Editor enriquecido: sobreescribir obs_tecnica con JSON completo ──
        if hasattr(self, 'entry_Obs_Tecnica') and hasattr(self.entry_Obs_Tecnica, 'get_content'):
            datos_maestro['obs_tecnica'] = self.entry_Obs_Tecnica.get_content()

        # Num_Order se maneja por separado ya que está en la tabla rma_orders
        if hasattr(self, 'entry_Num_Order'):
            try:
                num_order_val = self.entry_Num_Order.get() if hasattr(self.entry_Num_Order, 'get') else ''
                datos_maestro['num_order'] = num_order_val
            except Exception:
                datos_maestro['num_order'] = ''
        
        return datos_maestro

    def autorrellena_pdf(self):
        """Autorrellena la plantilla PDF con los datos del RMA actual y la guarda en Backblaze B2.

        Busca 'Plantilla_SOLICITUD RMA.pdf' en la carpeta plantillas/. Si no existe, abre
        un diálogo para seleccionar la plantilla. Luego llama a la función de librería
        para rellenar el PDF y lo sube a Backblaze B2 como adjunto.
        """
        # Validaciones
        if not hasattr(self, 'current_rma_id') or not self.current_rma_id:
            messagebox.showwarning("Guardar primero", "Guarde el expediente antes de generar el PDF.")
            return

        # Obtener código RMA del label
        try:
            codigo_rma = self.lbl_codigo_rma.cget("text").split(": ")[1]
        except Exception:
            messagebox.showerror("Error", "No se pudo determinar el código RMA.")
            return

        # Determinar plantilla por defecto
        base_dir = os.path.dirname(os.path.abspath(__file__))
        plantilla_def = os.path.join(base_dir, 'plantillas', 'Plantilla_SOLICITUD RMA.pdf')
        if os.path.exists(plantilla_def):
            plantilla_path = plantilla_def
        else:
            # Pedir al usuario que seleccione la plantilla
            plantilla_path = filedialog.askopenfilename(
                title='Seleccionar plantilla PDF', 
                initialdir=os.path.join(base_dir, 'plantillas'), 
                filetypes=[('PDF files', '*.pdf')]
            )
            if not plantilla_path:
                return

        # Comprobar que la función de relleno esté disponible
        if fill_pdf is None:
            messagebox.showerror("Dependencia falta", "La funcionalidad de rellenado PDF no está disponible. Instala la dependencia o revisa el módulo lib.pdf_fill.")
            return

        # Obtener datos del RMA desde Turso usando la conexión de la aplicación
        try:
            conn, cursor = self.master.conectar_db()
            cursor.execute("SELECT codigo_rma, modelo, n_serie, obs_tecnica FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
            datos_rma = cursor.fetchone()
            conn.close()
            
            if not datos_rma:
                messagebox.showerror("Error", f"No se encontraron datos para el RMA {codigo_rma} en la base de datos.")
                return
            
            codigo_bd, modelo, n_serie, obs_tecnica = datos_rma
            
            # ── Si obs_tecnica es JSON del editor enriquecido, extraer texto plano ──
            if obs_tecnica and '"version"' in str(obs_tecnica):
                try:
                    import json as _json
                    _data = _json.loads(obs_tecnica)
                    obs_tecnica = " ".join(
                        seg.get("content", "")
                        for seg in _data.get("segments", [])
                        if seg.get("type") == "text"
                    ).strip()
                except Exception:
                    pass  # Si falla el parse, usar el valor tal cual
            
            # Debug: Mostrar datos obtenidos de Turso
            print(f"DEBUG PDF - Datos desde TURSO para {codigo_bd}:")
            print(f"  modelo: '{modelo}'" + (" ✓" if modelo else " [VACÍO]"))
            print(f"  n_serie: '{n_serie}'" + (" ✓" if n_serie else " [VACÍO]"))
            print(f"  obs_tecnica: '{obs_tecnica}'" + (" ✓" if obs_tecnica else " [VACÍO]"))
            
        except Exception as e:
            messagebox.showerror("Error BD", f"Error obteniendo datos de la base de datos: {e}")
            return

        # Preparar nombres de archivo
        nombre_base = f"{codigo_rma}_SOLICITUD RMA.pdf"
        
        # Si el archivo ya existe en Backblaze B2, añadimos timestamp para evitar sobrescribir
        nombre_salida = nombre_base
        if usar_b2():
            # Verificar si ya existe en Backblaze B2
            b2_api, bucket = get_b2_client()
            if b2_api and bucket:
                try:
                    ruta_check = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{codigo_rma}/{nombre_base}")
                    # Intentar listar el archivo específico
                    file_found = False
                    for file_version_info, _ in bucket.ls(ruta_check, latest_only=True):
                        file_found = True
                        break
                    
                    if file_found:
                        # El archivo existe, añadir timestamp
                        fecha_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        nombre_salida = f"{codigo_rma}_SOLICITUD RMA_{fecha_str}.pdf"
                except B2Error:
                    # El archivo no existe, podemos usar el nombre base
                    pass

        # Crear archivo temporal para el PDF generado
        temp_dir = tempfile.mkdtemp(prefix="solicitud_rma_")
        temp_pdf_path = os.path.join(temp_dir, nombre_salida)

        # Rellenar PDF con datos obtenidos de Turso
        try:
            # Campos que queremos que queden vacíos y editables
            force_empty = [
                'Cantidad afectada', 'N Pedido', 'Nº de pedido  Albarán', 'Nº de pedido Albarán',
                'N Pedido Albarán', 'Nº de pedido Albaran', 'Nº RMA'
            ]

            # Preparar valores para rellenar el PDF directamente con datos de Turso
            valores_pdf = {}
            
            # Aplicar mapping: De campos PDF a valores de BD obtenidos de Turso
            if modelo:
                valores_pdf['Modelo'] = modelo
            if n_serie: 
                valores_pdf['Número de serie'] = n_serie
            if obs_tecnica:
                valores_pdf['Ubicación de las fuentes en la instalación'] = obs_tecnica
            if codigo_rma:
                valores_pdf['Referencia para devolución'] = codigo_rma
            
            # Campos que queremos que queden vacíos y editables
            for campo_vacio in force_empty:
                valores_pdf[campo_vacio] = ''
            
            print(f"DEBUG PDF - Valores que se van a escribir en PDF:")
            for campo, valor in valores_pdf.items():
                print(f"  '{campo}' = '{valor}'")
            
            # DEBUG: Verificar campos disponibles en el PDF antes de rellenar
            try:
                from lib.pdf_fill import get_pdf_field_names
                if get_pdf_field_names:
                    campos_pdf = get_pdf_field_names(plantilla_path)
                    print(f"\nDEBUG PDF - Campos disponibles en la plantilla ({len(campos_pdf)} total):")
                    for i, campo in enumerate(campos_pdf, 1):
                        estado = "✓ MATCH" if campo in valores_pdf else "○ Sin mapear"
                        print(f"  {i:2d}. '{campo}' {estado}")
                    
                    # Verificar matching exacto
                    print(f"\nDEBUG PDF - Verificación de coincidencias:")
                    for campo_valor, valor in valores_pdf.items():
                        if campo_valor in campos_pdf:
                            print(f"  ✅ '{campo_valor}' -> EXISTE en PDF")
                        else:
                            print(f"  ❌ '{campo_valor}' -> NO EXISTE en PDF")
                            # Buscar campos similares
                            similares = [c for c in campos_pdf if campo_valor.lower() in c.lower() or c.lower() in campo_valor.lower()]
                            if similares:
                                print(f"     Similares: {similares}")
            except Exception as debug_e:
                print(f"DEBUG PDF - Error obteniendo campos PDF: {debug_e}")
            
            # Rellenar PDF usando función directa (sin consulta a BD adicional)
            print(f"\nDEBUG PDF - Ejecutando fill_pdf...")
            print(f"  Plantilla: {plantilla_path}")
            print(f"  Salida: {temp_pdf_path}")
            
            # Verificar que la plantilla existe y es accesible
            if os.path.exists(plantilla_path):
                size_plantilla = os.path.getsize(plantilla_path)
                print(f"  Plantilla existe: {size_plantilla} bytes")
            else:
                print(f"  ❌ Plantilla NO existe")
                
            fill_pdf(plantilla_path, temp_pdf_path, valores_pdf)
            
            # Verificar que el archivo de salida se generó
            if os.path.exists(temp_pdf_path):
                size_salida = os.path.getsize(temp_pdf_path)
                print(f"  ✅ PDF generado: {size_salida} bytes")
                
                # Verificar si el tamaño cambió (indicaría que se modificó)
                if abs(size_salida - size_plantilla) > 100:  # Al menos 100 bytes de diferencia
                    print(f"  ✅ PDF modificado (diferencia: {size_salida - size_plantilla} bytes)")
                else:
                    print(f"  ⚠️  PDF no modificado o cambio mínimo (diferencia: {size_salida - size_plantilla} bytes)")
            else:
                print(f"  ❌ PDF NO se generó")
                
            print(f"DEBUG PDF - fill_pdf completado")
        except Exception as e:
            # Limpiar archivo temporal
            try:
                os.remove(temp_pdf_path)
                os.rmdir(temp_dir)
            except:
                pass
            messagebox.showerror("Error Rellenado", f"Error al rellenar la plantilla: {e}")
            return

        # Decidir dónde guardar (Dropbox o local)
        if usar_b2():
            # Subir a Backblaze B2
            exito, ruta_relativa = self._subir_archivo_b2(temp_pdf_path, codigo_rma, nombre_salida)
            tipo_almacenamiento = 'backblaze'
            ubicacion_desc = "Dropbox"
        else:
            # Guardar localmente (fallback)
            exito, ruta_relativa = self._subir_archivo_local(temp_pdf_path, codigo_rma, nombre_salida)
            tipo_almacenamiento = 'local'
            ubicacion_desc = "local"
        
        # Limpiar archivo temporal
        try:
            os.remove(temp_pdf_path)
            os.rmdir(temp_dir)
        except:
            pass
        
        if not exito:
            messagebox.showerror("Error", f"No se pudo guardar la solicitud PDF en {ubicacion_desc}.")
            return

        # Registrar en la base de datos como adjunto
        try:
            conn, cursor = self.master.conectar_db()
            
            # Verificar esquema de BD antes de insertar
            self._verificar_columna_tipo_almacenamiento(cursor)
            
            # Preparar inserción con o sin tipo_almacenamiento según el esquema
            if getattr(self, '_usar_tipo_almacenamiento', False):
                cursor.execute("""
                    INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.current_rma_id,
                    nombre_salida,
                    ruta_relativa,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.username,
                    tipo_almacenamiento
                ))
            else:
                cursor.execute("""
                    INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.current_rma_id,
                    nombre_salida,
                    ruta_relativa,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.username
                ))
            
            # También registrar entrada en rma_historial con información de ubicación
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (
                self.current_rma_id,
                datetime.datetime.now().isoformat(),
                self.username,
                f"Generada Solicitud RMA: {nombre_salida} ({'☁️ Backblaze B2' if usar_b2() else '💾 Local'})"
            ))

            conn.commit()
            conn.close()
            
            # Refrescar lista de adjuntos
            try:
                self.cargar_lista_adjuntos(self.current_rma_id)
            except Exception:
                pass
            
            # Actualizar historial si está visible
            try:
                if hasattr(self, 'historial_tab'):
                    self.mostrar_historial(self.historial_tab)
            except AttributeError:
                pass
                
            # Feedback al usuario personalizado según ubicación
            if usar_b2():
                messagebox.showinfo("Éxito", f"✅ Solicitud PDF '{nombre_salida}' generada y subida a Backblaze B2 correctamente.\n\n📁 Ubicación: {ruta_relativa}")
            else:
                messagebox.showinfo("Éxito", f"✅ Solicitud PDF '{nombre_salida}' generada y guardada localmente.")
                
        except Exception as e:
            # Limpiar archivo temporal si hubo error
            try:
                os.remove(temp_pdf_path)
                os.rmdir(temp_dir)
            except:
                pass
            messagebox.showwarning("Aviso", f"PDF generado, pero no se pudo registrar en la BD: {e}")
            return

    def cargar_datos_rma(self, rma_id):
        """Carga el RMA maestro y sus detalles en el formulario."""
        # Bandera para evitar callbacks durante la carga
        self._cargando_datos = True
        
        conn, cursor = self.master.conectar_db()
        if not conn: return
        cursor = conn.cursor()
        
        try:
            # 1. Cargar RMA Maestro
            cursor.execute("SELECT * FROM rma_maestro WHERE id = ?", (rma_id,))
            columnas_maestro = [col[0] for col in cursor.description]
            datos_maestro = dict(zip(columnas_maestro, cursor.fetchone()))
            
            self.datos_rma_maestro = datos_maestro
            
            # 2. Cargar RMA Detalles (Artículos)
            # Usamos SELECT * para ser agnósticos a las columnas disponibles.
            # Así funciona aunque numero_albaran/numero_order aún no existan en la BD (Turso/legacy).
            cursor.execute(
                "SELECT * FROM rma_detalles WHERE rma_id = ?", (rma_id,)
            )
            columnas_detalle = [col[0] for col in cursor.description]
            articulos_db = [dict(zip(columnas_detalle, fila)) for fila in cursor.fetchall()]
            # Normalizar campos que puede que no existan en BDs antiguas
            for art in articulos_db:
                # contabilizar: forzar int desde cualquier tipo
                try:
                    val_cont = art.get('contabilizar', 1)
                    # NO usar "or 1" porque convierte 0 en 1
                    art['contabilizar'] = int(val_cont) if val_cont is not None else 1
                except (ValueError, TypeError):
                    art['contabilizar'] = 1
                art.setdefault('numero_albaran', '')
                art.setdefault('numero_order', '')
                if art['numero_albaran'] is None:
                    art['numero_albaran'] = ''
                if art['numero_order'] is None:
                    art['numero_order'] = ''
            
            # LOG: Debug de valores cargados desde DB
            for i, art in enumerate(articulos_db):
                cont_val = art.get('contabilizar')
                logger.debug(f"[CARGA DB] Artículo {i}: ref={art.get('referencia_articulo')} contabilizar={cont_val} (tipo: {type(cont_val).__name__})")
            
            # 3. Cargar Número de Orden desde rma_orders
            cursor.execute("SELECT num_order FROM rma_orders WHERE rma_id = ?", (rma_id,))
            orden_row = cursor.fetchone()
            if orden_row:
                datos_maestro['num_order'] = orden_row[0]
            else:
                datos_maestro['num_order'] = ''
            
            # IMPORTANTE: Recalcular precio_final si está en 0 (datos antiguos)
            try:
                from lib.articulo_utils import calcular_precio_final
                # Obtener descuento del cliente para los cálculos
                descuento_cliente = datos_maestro.get('descuento_cliente', 0.0) or 0.0
                
                for articulo in articulos_db:
                    try:
                        precio_final_actual = articulo.get('precio_final', 0) or 0
                        
                        # Si precio_final es 0, recalcularlo
                        if precio_final_actual == 0:
                            precio_unitario = articulo.get('precio_unitario', 0.0) or 0.0
                            tiene_depreciacion = articulo.get('depreciacion', 0) == 1
                            porcentaje_depreciacion = articulo.get('porcentaje_depreciacion', 0.0) or 0.0
                            
                            # Recalcular
                            precio_final_recalculado = calcular_precio_final(
                                precio_unitario,
                                descuento_cliente,
                                tiene_depreciacion,
                                porcentaje_depreciacion
                            )
                            
                            # Actualizar el diccionario
                            articulo['precio_final'] = precio_final_recalculado
                    except Exception as e:
                        # Si falla el recálculo de un artículo, continuar con los demás
                        print(f"Error recalculando precio_final para artículo: {e}")
                        # Mantener precio_unitario como fallback
                        if articulo.get('precio_final', 0) == 0:
                            articulo['precio_final'] = articulo.get('precio_unitario', 0.0)
            except Exception as e:
                print(f"Error en recálculo general de precios: {e}")
                # Continuar sin recalcular

            conn.close()

            # 3. Rellenar Formulario Maestro
            self.lbl_codigo_rma.configure(text=f"Nº EXPEDIENTE: {datos_maestro['codigo_rma']}")
            
            # >>> VERIFICACIÓN CRÍTICA DEL WIDGET MOTIVO <<<
            # Si esta línea falla, el nombre de la variable está mal.
            entry_motivo = None
            
            # Prueba 1: entry_Motivo (La que falló)
            if 'entry_Motivo' in self.__dict__:
                entry_motivo = self.entry_Motivo
            # Prueba 2: entry_motivo (Todo minúscula, la más probable)
            elif 'entry_motivo' in self.__dict__:
                entry_motivo = self.entry_motivo
            # Prueba 3: entry_motivo_ (Por si hay un guion bajo final)
            elif 'entry_motivo_' in self.__dict__:
                entry_motivo = getattr(self, "entry_motivo_", None)

            # Si encontramos el widget con el nombre correcto:
            if entry_motivo and 'motivo' in datos_maestro:
                valor_motivo = datos_maestro['motivo']
                
                if isinstance(entry_motivo, ctk.CTkEntry):
                    # 1. Borrar el placeholder
                    entry_motivo.configure(state="normal")
                    entry_motivo.delete(0, ctk.END)
                    
                    # 2. Insertar el valor
                    valor_a_insertar = str(valor_motivo) if valor_motivo is not None and str(valor_motivo).strip() != "" else ""
                    entry_motivo.insert(0, valor_a_insertar)
                    
                    # 3. Restaurar estado (si no era un campo deshabilitado, se queda en normal)
                    # NOTA: En este formulario es un campo editable, así que se queda en 'normal'
            # -----------------------------------------------
            
            # --- TRATAMIENTO ESPECIAL PARA FECHA_PARA_FACTURA ---
            # Este campo usa quincenas futuras, necesita manejo especial
            
            if hasattr(self, 'entry_Fecha_para_factura'):
                widget_fecha = self.entry_Fecha_para_factura
                
                if isinstance(widget_fecha, ctk.CTkOptionMenu):
                    # Probar con ambos nombres posibles
                    valor_fecha = datos_maestro.get('fecha_para_factura') or datos_maestro.get('Fecha_para_factura') or datos_maestro.get('Fecha_Para_factura')
                    
                    # Normalizar: si es None o la cadena 'None', tratarlo como vacío
                    if valor_fecha is None or str(valor_fecha).strip().lower() == 'none' or str(valor_fecha).strip() == '':
                        valor_fecha = None
                    
                    if valor_fecha:
                        # Hay un valor guardado
                        valores_actuales = list(widget_fecha.cget("values"))
                        valor_str = str(valor_fecha).strip()
                        
                        # Si el valor no está en las opciones (fecha antigua), añadirlo después de "Seleccionar..."
                        if valor_str and valor_str not in valores_actuales:
                            valores_actuales.insert(1, valor_str)  # Después de "Seleccionar..."
                            widget_fecha.configure(values=valores_actuales)
                        
                        # Establecer el valor guardado
                        widget_fecha.set(valor_str)
                    else:
                        # No hay valor guardado, establecer "Seleccionar..."
                        widget_fecha.set("Seleccionar...")
            
            # --- Mapeo de Columna DB a Variable de Formulario ---
            for columna, valor in datos_maestro.items():
                
                # Excluir 'id', 'precio_total_expediente', 'estado' y 'fecha_para_factura' (ya procesado arriba)
                if columna in ['id', 'precio_total_expediente', 'estado', 'fecha_para_factura']:
                    continue

                # ---------------------------------------------------------------------------------
                # 1. DETERMINAR EL NOMBRE CORRECTO DE LA VARIABLE DE LA INTERFAZ (entry_name)
                # ---------------------------------------------------------------------------------
                entry_name = None
                
                # Primero intentar con el nombre exacto del campo (como se crea en crear_campo)
                nombre_exacto = f"entry_{columna}"
                if hasattr(self, nombre_exacto):
                    entry_name = nombre_exacto
                # Caso A: Campos simples (Sin guiones bajos, como 'motivo', 'cliente', 'creado_por')
                # ESTA ES LA RUTA CRÍTICA QUE 'motivo' DEBE SEGUIR
                elif '_' not in columna:
                    # Convierte a título para hacer coincidir la convención (ej: motivo -> Motivo)
                    entry_name = f"entry_{columna.title()}" 
                
                # Caso B: Campos con guiones bajos (como 'persona_de_contacto', 'numero_documento_cliente')
                else:
                    # Aplica tu lógica compleja de transformación:
                    formato_titulo = columna.replace('_', ' ').title()
                    entry_key_name = formato_titulo.replace(' De ', ' de ')
                    entry_key_name = entry_key_name.replace(' ', '_')
                    entry_name = f"entry_{entry_key_name}"


                # ---------------------------------------------------------------------------------
                # 2. TRATAMIENTO Y RELLENO DEL WIDGET EN BASE AL NOMBRE
                # ---------------------------------------------------------------------------------
                
                # Si encontramos un nombre de variable, intentamos rellenar
                if entry_name and hasattr(self, entry_name):
                    entry = getattr(self, entry_name)
                    
                    # Tratamiento para DatePicker (si el widget expone `set_date`)
                    if hasattr(entry, 'set_date'):
                        try:
                            if valor is None or str(valor).strip() == '':
                                # Intentar limpiar el control de fecha
                                try:
                                    entry.set_date('')
                                except Exception:
                                    try:
                                        entry.configure(state='normal')
                                        entry.delete(0, ctk.END)
                                    except Exception:
                                        pass
                            else:
                                # Normalizar la fecha y establecerla
                                try:
                                    fecha_iso = parse_date_to_iso(valor)
                                    from datetime import datetime
                                    dt = datetime.strptime(fecha_iso, '%Y-%m-%d')
                                    entry.set_date(dt)
                                except Exception:
                                    try:
                                        entry.configure(state='normal')
                                        entry.delete(0, ctk.END)
                                        entry.insert(0, str(valor))
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # continuar con la siguiente columna
                        continue

                    # Tratamiento especial para OptionMenu (Autorizacion)
                    if columna == 'autorizacion' and isinstance(entry, ctk.CTkOptionMenu):
                        # Interpretar distintos posibles formatos que pueda tener el valor
                        is_si = False
                        try:
                            if isinstance(valor, (int, float)):
                                is_si = int(valor) == 1
                            elif isinstance(valor, bool):
                                is_si = bool(valor)
                            elif isinstance(valor, str):
                                vnorm = valor.strip().upper()
                                is_si = vnorm in ('1', 'SI', 'S', 'TRUE', 'T')
                        except Exception:
                            is_si = False
                        entry.set('SI' if is_si else 'NO')
                        
                    # Tratamiento para Entry
                    elif isinstance(entry, ctk.CTkEntry):
                        # Configurar Entry
                        estado_original = entry.cget("state")  
                        entry.configure(state="normal")
                        
                        # CRÍTICO: Borrar el placeholder ANTES de insertar
                        entry.delete(0, ctk.END)
                        entry.insert(0, str(valor) if valor is not None else "")

                        # Si el campo es 'numero_documento_cliente', permitir edición
                        # cuando el valor contiene 'Email' o 'Telefonica' (case-insensitive).
                        try:
                            if columna == 'numero_documento_cliente':
                                valor_str = str(valor) if valor is not None else ''
                                if re.search(r"\b(e-?mail|telefonica|telefonico)\b", valor_str, re.IGNORECASE):
                                    # Mantener en editable
                                    entry.configure(state='normal')
                                else:
                                    entry.configure(state=estado_original)
                            else:
                                entry.configure(state=estado_original)
                        except Exception:
                            entry.configure(state=estado_original)

                    # Tratamiento para DatePicker (CTkDatePicker o widgets similares)
                    elif hasattr(entry, 'set_date'):
                        try:
                            # Si el valor es nulo, limpiar
                            if valor is None:
                                entry.set_date(None)
                            else:
                                entry.set_date(valor)
                        except Exception:
                            # Fallback: escribir directamente en el sub-entry si existe
                            try:
                                if hasattr(entry, 'date_entry'):
                                    entry.date_entry.configure(state='normal')
                                    entry.date_entry.delete(0, tk.END)
                                    entry.date_entry.insert(0, str(valor) if valor is not None else '')
                            except Exception:
                                pass
                        
                    # Tratamiento para OptionMenu General
                    elif isinstance(entry, ctk.CTkOptionMenu):
                        valores_actuales = list(entry.cget("values"))
                        valor_str = str(valor) if valor is not None else ""
                        
                        # Si el valor de la BD no está en las opciones actuales, añadirlo
                        if valor_str and valor_str not in valores_actuales:
                            valores_actuales.insert(0, valor_str)  # Añadir al principio
                            entry.configure(values=valores_actuales)
                        
                        # Establecer el valor
                        if valor_str:
                            entry.set(valor_str)
                    # Tratamiento para Textbox grande (Observaciones Técnicas u otros)
                    elif isinstance(entry, ctk.CTkTextbox):
                        try:
                            entry.delete("1.0", "end")
                            entry.insert("1.0", str(valor) if valor is not None else "")
                        except Exception:
                            # algunos widgets CTkTextbox pueden tener métodos distintos; ignorar si falla
                            pass
                    # Tratamiento para RichTextEditor (editor enriquecido de Obs_Tecnica)
                    elif hasattr(entry, 'set_content'):
                        entry.set_content(valor or "")
            
            # --- NUEVO: Actualizar la etiqueta del total ---
            precio_total = datos_maestro.get('precio_total_expediente', 0.0) # Obtener el valor
            self.lbl_precio_total.configure(text=f"{precio_total:.2f} €")
            
            # --- SINCRONIZACIÓN: Si hay fecha_autorizacion, marcar Autorización como SI ---
            # (Esto se hace ANTES de desactivar la bandera para evitar callbacks)
            try:
                fecha_aut = datos_maestro.get('fecha_autorizacion')
                if fecha_aut and str(fecha_aut).strip():
                    # Hay una fecha de autorización, asegurar que Autorización esté en "SI"
                    if hasattr(self, 'entry_Autorizacion'):
                        try:
                            self.entry_Autorizacion.set('SI')
                        except Exception as e:
                            print(f"Error al sincronizar Autorización: {e}")
            except Exception as e:
                print(f"Error en sincronización de autorización: {e}")
            
            # 4. Rellenar Artículos (self.articulos_data)
            self.articulos_data = articulos_db
            self.actualizar_listado_articulos()

            # --- Aplicar bloqueo de Resolución Provisional según Resultado_Expediente cargado ---
            # CTkOptionMenu.set() no dispara el command=, así que hay que forzar la sincronización
            # ahora que "Resultado Expediente" ya tiene el valor real cargado desde la BD.
            if hasattr(self, '_sync_resolucion_provisional'):
                try:
                    self._sync_resolucion_provisional()
                except Exception as e:
                    print(f"Error al sincronizar Resolución Provisional: {e}")

        except Exception as e:
            print(f"Error al cargar datos del RMA ID {rma_id}: {e}")
        finally:
            # Desactivar bandera de carga SIEMPRE, incluso si hay error
            self._cargando_datos = False
            conn.close()
            self._actualizar_botones_segun_estado()

    def guardar_cambio_historial(self, rma_id, campo, valor_antiguo, valor_nuevo, cursor=None):
        """Registra un cambio de un campo en la tabla de historial SOLO si hay cambio real.

        Si se pasa `cursor` (de una conexión ya abierta por el llamador, p.ej.
        actualizar_rma), se reutiliza esa misma conexión/transacción en vez de
        abrir+commitear+cerrar una conexión nueva por cada campo modificado -
        evitar eso es clave porque cada conexión implica un viaje de red a Turso.
        """
        # Normalizar valores para comparación (convertir None a cadena vacía, strip)
        def normalizar_valor(val):
            if val is None:
                return ""
            return str(val).strip()

        val_antiguo_norm = normalizar_valor(valor_antiguo)
        val_nuevo_norm = normalizar_valor(valor_nuevo)

        # Si los valores son iguales después de normalizar, no registrar el cambio
        if val_antiguo_norm == val_nuevo_norm:
            return

        descripcion = f"Campo '{campo}' modificado: '{valor_antiguo}' -> '{valor_nuevo}'"
        # Si el campo modificado es 'Procesado Por' (o su variante), añadimos la nota requerida
        try:
            campo_norm = str(campo).lower().strip().replace(' ', '_')
            if campo_norm == 'procesado_por' or campo_norm == 'procesadopor':
                descripcion = descripcion + " - MATERIAL REVISADO"
        except Exception:
            # En caso de cualquier problema al normalizar, no bloqueamos el guardado del historial
            pass

        if cursor is not None:
            # Reutilizar la conexión/transacción del llamador: sin commit ni close aquí,
            # el llamador es responsable de comitear al final.
            try:
                cursor.execute("""
                    INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                    VALUES (?, ?, ?, ?)
                """, (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, descripcion))
            except sqlite3.Error as e:
                print(f"Error al registrar historial: {e}")
            return

        conn, _ = self.master.conectar_db()
        if not conn: return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, descripcion))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error al registrar historial: {e}")
        finally:
            conn.close()

    def actualizar_rma(self):
        """Compara los datos, actualiza rma_maestro y rma_detalles, y registra los cambios."""
        conn, cursor = self.master.conectar_db()
        if not conn: return

        cursor = conn.cursor()
        rma_id = self.rma_actual_id
        
        # 1. Obtener datos antiguos de la DB
        cursor.execute("SELECT * FROM rma_maestro WHERE id = ?", (rma_id,))
        columnas_maestro_db = [col[0] for col in cursor.description]
        datos_antiguos = dict(zip(columnas_maestro_db, cursor.fetchone()))
        
        # 2. Obtener datos nuevos del formulario
        datos_nuevos = self.obtener_datos_actuales_maestro()
        
        # Si la recolección devolvió None, significa que había fechas inválidas y ya se mostró un error
        if datos_nuevos is None:
            conn.close()
            return
        
        # 2.1. Validar que el cliente existe en la base de datos (solo si ha cambiado)
        cliente_antiguo = datos_antiguos.get('cliente', '')
        cliente_nuevo = datos_nuevos.get('cliente', '')
        if str(cliente_antiguo).strip() != str(cliente_nuevo).strip() and cliente_nuevo:
            # El cliente ha cambiado, verificar que existe
            try:
                cursor.execute("SELECT cliente_id FROM clientes WHERE nombre = ?", (cliente_nuevo,))
                resultado = cursor.fetchone()
                
                if not resultado:
                    # Cliente no existe - mostrar mensaje de advertencia
                    conn.close()
                    self._mostrar_dialogo_cliente_no_existe(cliente_nuevo)
                    return
            except Exception as e:
                print(f"Error verificando cliente: {e}")
                # Si hay error, permitir continuar

        # ⚠️ ADVERTENCIA ADMIN: Cambios en campos críticos
        if self.username.lower() == "admin":
            campos_criticos_modificados = []
            
            # Verificar cambios en Cliente
            cliente_antiguo = datos_antiguos.get('cliente', '')
            cliente_nuevo = datos_nuevos.get('cliente', '')
            if str(cliente_antiguo).strip() != str(cliente_nuevo).strip():
                campos_criticos_modificados.append(f"• Cliente: '{cliente_antiguo}' → '{cliente_nuevo}'")
            
            # Verificar cambios en Número de Documento
            num_doc_antiguo = datos_antiguos.get('numero_documento_cliente', '')
            num_doc_nuevo = datos_nuevos.get('numero_documento_cliente', '')
            if str(num_doc_antiguo).strip() != str(num_doc_nuevo).strip():
                campos_criticos_modificados.append(f"• Número Documento: '{num_doc_antiguo}' → '{num_doc_nuevo}'")
            
            # Verificar cambios en Fecha Emisión
            fecha_emision_antigua = datos_antiguos.get('fecha_emision', '')
            fecha_emision_nueva = datos_nuevos.get('fecha_emision', '')
            if str(fecha_emision_antigua).strip() != str(fecha_emision_nueva).strip():
                campos_criticos_modificados.append(f"• Fecha Emisión: '{fecha_emision_antigua}' → '{fecha_emision_nueva}'")
            
            # Verificar cambios en Creado Por
            creado_por_antiguo = datos_antiguos.get('creado_por', '')
            creado_por_nuevo = datos_nuevos.get('creado_por', '')
            if str(creado_por_antiguo).strip() != str(creado_por_nuevo).strip():
                campos_criticos_modificados.append(f"• Creado Por: '{creado_por_antiguo}' → '{creado_por_nuevo}'")
            
            # Si hay cambios críticos, mostrar advertencia
            if campos_criticos_modificados:
                mensaje_cambios = "\n".join(campos_criticos_modificados)
                respuesta = messagebox.askyesno(
                    "⚠️ ADVERTENCIA - Modificación de Campos Críticos",
                    f"ADMIN: Está modificando campos críticos del expediente:\n\n"
                    f"{mensaje_cambios}\n\n"
                    f"Estos cambios quedarán registrados en el historial.\n\n"
                    f"¿Confirmar modificación?"
                )
                
                if not respuesta:
                    conn.close()
                    return

        # Aviso: si el número de documento nuevo contiene valores provisionales, pedir confirmación
        try:
            num_doc_nuevo = str(datos_nuevos.get('numero_documento_cliente', '') or '').strip()
            if num_doc_nuevo and re.search(r"\b(e-?mail|telefonica|telefonico)\b", num_doc_nuevo, re.IGNORECASE):
                resp = messagebox.askyesno("Valor provisional detectado",
                                           "El campo 'Núm. Doc. Cliente' contiene un valor provisional (p.ej. 'Email' o 'Telefonica').\n¿Deseas continuar con la actualización?")
                if not resp:
                    conn.close()
                    return
        except Exception:
            pass

        # 2.1. INTEGRACIÓN DE LA TRAZABILIDAD - Calcular el nuevo estado
        estado_nuevo = self.determinar_estado_rma(datos_nuevos)
        
        # 2.2. CONFIRMACIONES INTELIGENTES: Verificar tareas pendientes antes de completar
        estado_anterior = datos_antiguos.get('estado', '')
        if estado_nuevo == 'Completado' and estado_anterior != 'Completado':
            # El expediente se está intentando completar
            count_tareas, tareas_pendientes = self.verificar_tareas_pendientes_expediente(rma_id)
            
            if count_tareas > 0:
                # Crear mensaje detallado con las tareas pendientes
                mensaje_tareas = "\n• ".join(tareas_pendientes[:5])  # Mostrar máximo 5 tareas
                if len(tareas_pendientes) > 5:
                    mensaje_tareas += f"\n• ... y {len(tareas_pendientes) - 5} tareas más"
                
                respuesta = messagebox.askyesno(
                    "⚠️ Expediente con tareas pendientes",
                    f"¿Seguro que deseas completar este expediente?\n\n"
                    f"Tiene {count_tareas} tarea(s) pendiente(s):\n\n• {mensaje_tareas}\n\n"
                    f"Se recomienda completar todas las tareas antes de cerrar el expediente.\n\n"
                    f"¿Continuar de todas formas?"
                )
                
                if not respuesta:
                    conn.close()
                    messagebox.showinfo("Operación cancelada", "El expediente no ha sido completado.")
                    return
        
        # Añadir el estado al diccionario de datos nuevos
        datos_nuevos['estado'] = estado_nuevo 
        
        # 3. Comparar y construir la consulta de actualización (UPDATE)
        campos_a_actualizar = []
        valores_a_actualizar = []
        
        def valores_son_diferentes(val1, val2):
            """Compara dos valores normalizando None y cadenas vacías."""
            # Normalizar None y cadenas vacías
            v1 = str(val1).strip() if val1 is not None else ""
            v2 = str(val2).strip() if val2 is not None else ""
            return v1 != v2
        
        # Campos que no pertenecen a rma_maestro (se manejan en otras tablas)
        campos_excluir = {'num_order'}  # num_order está en rma_orders, no en rma_maestro

        # Resolución Provisional / Observ. Res. Provisional dejan de poder modificarse
        # en cuanto Resultado_Expediente ya tiene valor (defensa server-side además del
        # bloqueo de la UI en _sync_resolucion_provisional).
        campos_bloqueados_si_resultado = {'resolucion_provisional', 'obs_res_provisional'}
        resultado_expediente_actual = str(datos_antiguos.get('resultado_expediente') or '').strip()

        for columna_db, valor_nuevo in datos_nuevos.items():
            # Saltar campos que no pertenecen a rma_maestro
            if columna_db in campos_excluir:
                continue

            if columna_db in campos_bloqueados_si_resultado and resultado_expediente_actual:
                continue  # Bloqueado: Resultado Expediente ya está cumplimentado

            valor_antiguo = datos_antiguos.get(columna_db)

            # SQLite almacena el boolean como int (1/0)
            if columna_db == 'autorizacion':
                if valor_nuevo != valor_antiguo:
                    self.guardar_cambio_historial(rma_id, "Autorización", "NO" if valor_antiguo == 0 else "SI", "NO" if valor_nuevo == 0 else "SI", cursor=cursor)
                    campos_a_actualizar.append(f"{columna_db} = ?")
                    valores_a_actualizar.append(valor_nuevo)

            # Comparación de campos normales (no boolean) usando la función de normalización
            elif valores_son_diferentes(valor_antiguo, valor_nuevo):
                # No registrar obs_tecnica en historial (puede contener JSON con imágenes)
                if columna_db != 'obs_tecnica':
                    self.guardar_cambio_historial(rma_id, columna_db.title().replace('_', ' '), str(valor_antiguo), str(valor_nuevo), cursor=cursor)
                if columna_db in campos_bloqueados_si_resultado:
                    logger.info(f"[RESOLUCION_PROVISIONAL] RMA {rma_id}: '{columna_db}' '{valor_antiguo}' -> '{valor_nuevo}' (usuario={self.username})")
                campos_a_actualizar.append(f"{columna_db} = ?")
                valores_a_actualizar.append(valor_nuevo)
        
        columna_estado_ya_anadida = 'estado' in [c.split('=')[0].strip() for c in campos_a_actualizar]

        if not columna_estado_ya_anadida:
            # Si no se incluyó en el bucle anterior (lo que indica que el estado no cambió),
            # lo incluimos ahora, usando el nuevo valor calculado.
            campos_a_actualizar.append("estado = ?")
            valores_a_actualizar.append(estado_nuevo)

        # 4. Actualizar rma_maestro si hay cambios
        updated_any = False
        if campos_a_actualizar:
            valores_a_actualizar.append(rma_id)
            set_clause = ", ".join(campos_a_actualizar)
            
            try:
                cursor.execute(f"UPDATE rma_maestro SET {set_clause} WHERE id = ?", tuple(valores_a_actualizar))
                updated_any = True
            except sqlite3.Error as e:
                print(f"Error al actualizar maestro: {e}")
                if hasattr(conn, 'rollback'):
                    conn.rollback()
                conn.close()
                return

        # 5. Actualizar rma_detalles — siempre DELETE+INSERT
        try:
            cursor.execute("SELECT COUNT(*) FROM rma_detalles WHERE rma_id = ?", (rma_id,))
            _cr = cursor.fetchone()
            articulos_antiguos_count = _cr[0] if _cr else 0

            cursor.execute("DELETE FROM rma_detalles WHERE rma_id = ?", (rma_id,))

            if self.articulos_data:
                try:
                    cursor.execute("PRAGMA table_info(rma_detalles)")
                    _cols_bd = {r[1] for r in cursor.fetchall()}
                except Exception:
                    _cols_bd = {
                        'rma_id', 'referencia_articulo', 'cantidad_segun_documento',
                        'cantidad_entregada', 'estado_producto', 'precio_unitario',
                        'precio_final', 'depreciacion', 'porcentaje_depreciacion', 'contabilizar'
                    }

                _campos_orden = [
                    'referencia_articulo', 'cantidad_segun_documento', 'cantidad_entregada',
                    'estado_producto', 'precio_unitario', 'precio_final',
                    'depreciacion', 'porcentaje_depreciacion', 'contabilizar',
                    'numero_albaran', 'numero_order'
                ]
                _cols_insert = ['rma_id'] + [c for c in _campos_orden if c in _cols_bd]
                _cols_str = ', '.join(_cols_insert)
                _ph_str   = ', '.join('?' * len(_cols_insert))
                # Defaults numéricos para campos que no pueden ser string vacío
                _num_campos = {'precio_unitario', 'precio_final', 'depreciacion',
                               'porcentaje_depreciacion', 'cantidad_segun_documento',
                               'cantidad_entregada'}

                valores_batch = []
                for articulo in self.articulos_data:
                    fila = [rma_id]
                    for col in _cols_insert[1:]:
                        val = articulo.get(col)
                        if val is None:
                            val = 1 if col == 'contabilizar' else (0 if col in _num_campos else '')
                        fila.append(val)
                    valores_batch.append(tuple(fila))

                cursor.executemany(
                    f"INSERT INTO rma_detalles ({_cols_str}) VALUES ({_ph_str})",
                    valores_batch
                )

                self.guardar_cambio_historial(
                    rma_id, "Detalle Artículos",
                    f"{articulos_antiguos_count} items",
                    f"{len(self.articulos_data)} items",
                    cursor=cursor
                )

                try:
                    precio_total_recalc = 0.0
                    for item in self.articulos_data:
                        cantidad = item.get('cantidad_entregada', 0) or 0
                        if isinstance(cantidad, str):
                            cantidad = float(cantidad.replace(',', '.')) if cantidad.strip() else 0.0
                        else:
                            cantidad = float(cantidad)
                        precio = item.get('precio_final') or item.get('precio_unitario', 0.0) or 0.0
                        if isinstance(precio, str):
                            precio = float(precio.replace(',', '.')) if precio.strip() else 0.0
                        else:
                            precio = float(precio)
                        precio_total_recalc += cantidad * precio
                    cursor.execute(
                        "UPDATE rma_maestro SET precio_total_expediente = ? WHERE id = ?",
                        (precio_total_recalc, rma_id)
                    )
                except Exception as e:
                    print(f"Error al recalcular precio_total_expediente: {e}")

            elif articulos_antiguos_count > 0:
                self.guardar_cambio_historial(
                    rma_id, "Detalle Artículos",
                    f"{articulos_antiguos_count} items", "0 items - Artículos eliminados",
                    cursor=cursor
                )

            updated_any = True

        except sqlite3.Error as e:
            print(f"Error al actualizar detalles: {e}")
            if hasattr(conn, 'rollback'):
                conn.rollback()
            conn.close()
            return

                # 6. Actualizar/Insertar en rma_orders
        try:
            num_order_nuevo = datos_nuevos.get('num_order', '')
            
            # Verificar si ya existe un registro para este RMA
            cursor.execute("SELECT num_order FROM rma_orders WHERE rma_id = ?", (rma_id,))
            orden_existente = cursor.fetchone()
            
            if orden_existente:
                # Actualizar solo si el valor cambió
                num_order_antiguo = orden_existente[0] or ''
                if str(num_order_antiguo).strip() != str(num_order_nuevo).strip():
                    if num_order_nuevo and str(num_order_nuevo).strip():
                        cursor.execute("UPDATE rma_orders SET num_order = ? WHERE rma_id = ?", (str(num_order_nuevo).strip(), rma_id))
                        self.guardar_cambio_historial(rma_id, "Número de Orden", str(num_order_antiguo), str(num_order_nuevo), cursor=cursor)
                    else:
                        # Si el nuevo valor está vacío, eliminar el registro
                        cursor.execute("DELETE FROM rma_orders WHERE rma_id = ?", (rma_id,))
                        self.guardar_cambio_historial(rma_id, "Número de Orden", str(num_order_antiguo), "(eliminado)", cursor=cursor)
                    updated_any = True
            else:
                # Insertar si no existe y hay valor
                if num_order_nuevo and str(num_order_nuevo).strip():
                    cursor.execute("INSERT INTO rma_orders (rma_id, num_order) VALUES (?, ?)", (rma_id, str(num_order_nuevo).strip()))
                    self.guardar_cambio_historial(rma_id, "Número de Orden", "(ninguno)", str(num_order_nuevo), cursor=cursor)
                    updated_any = True
        except sqlite3.Error as e:
            print(f"Error al actualizar rma_orders: {e}")
            # No hacer rollback completo, solo registrar el error
            
        # 7. Commit final e invalidar caché
        conn.commit()
        conn.close()
        
        # Invalidar caché de estados (puede que se haya actualizado el estado)
        invalidate_cache('estados_rma')

        # Mostrar un único mensaje de éxito y mantener la ficha abierta
        if updated_any:
            try:
                messagebox.showinfo("Expediente actualizado", "El expediente se ha actualizado correctamente.")
            except Exception:
                pass

    def mostrar_historial(self, parent_frame):
        """Muestra la lista de registros de cambios para el RMA actual con filtros de búsqueda."""
        from lib.historial_filtros import obtener_historial_filtrado, obtener_usuarios_historial, validar_formato_fecha
        
        # Destruye el contenido anterior
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # Frame principal contenedor
        main_frame = ctk.CTkFrame(parent_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== PANEL DE FILTROS =====
        filtros_frame = ctk.CTkFrame(main_frame)
        filtros_frame.pack(fill="x", padx=5, pady=5)
        
        # Título del panel de filtros
        ctk.CTkLabel(filtros_frame, text="🔍 Filtros de Búsqueda", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,10))
        
        # Frame para los controles de filtro
        controles_frame = ctk.CTkFrame(filtros_frame)
        controles_frame.pack(fill="x", padx=10, pady=(0,10))
        
        # Fila 1: Búsqueda de texto y usuario
        fila1_frame = ctk.CTkFrame(controles_frame)
        fila1_frame.pack(fill="x", pady=5)
        
        # Búsqueda de texto
        ctk.CTkLabel(fila1_frame, text="Buscar en descripción:").pack(side="left", padx=(5,5))
        entry_busqueda = ctk.CTkEntry(fila1_frame, width=250, placeholder_text="Escribe para buscar...")
        entry_busqueda.pack(side="left", padx=(0,20))
        Tooltip(entry_busqueda, "Busca texto en las descripciones del historial")
        
        # Filtro por usuario
        ctk.CTkLabel(fila1_frame, text="Usuario:").pack(side="left", padx=(5,5))
        usuarios = obtener_usuarios_historial(self.rma_actual_id, self.master.conectar_db)
        lista_usuarios = ["Todos"] + usuarios
        combo_usuario = ctk.CTkOptionMenu(fila1_frame, values=lista_usuarios, width=150)
        combo_usuario.set("Todos")
        combo_usuario.pack(side="left", padx=(0,5))
        Tooltip(combo_usuario, "Filtra por usuario que realizó el cambio")
        
        # Fila 2: Filtros de fecha y tipo
        fila2_frame = ctk.CTkFrame(controles_frame)
        fila2_frame.pack(fill="x", pady=5)
        
        # Fecha desde
        ctk.CTkLabel(fila2_frame, text="Desde:").pack(side="left", padx=(5,5))
        entry_fecha_desde = ctk.CTkEntry(fila2_frame, width=120, placeholder_text="DD/MM/YYYY")
        entry_fecha_desde.pack(side="left", padx=(0,10))
        Tooltip(entry_fecha_desde, "Fecha inicial (formato: DD/MM/YYYY)")
        
        # Fecha hasta
        ctk.CTkLabel(fila2_frame, text="Hasta:").pack(side="left", padx=(5,5))
        entry_fecha_hasta = ctk.CTkEntry(fila2_frame, width=120, placeholder_text="DD/MM/YYYY")
        entry_fecha_hasta.pack(side="left", padx=(0,20))
        Tooltip(entry_fecha_hasta, "Fecha final (formato: DD/MM/YYYY)")
        
        # Checkbox solo comentarios manuales
        var_solo_manuales = ctk.BooleanVar(value=False)
        check_manuales = ctk.CTkCheckBox(fila2_frame, text="Solo comentarios manuales", variable=var_solo_manuales)
        check_manuales.pack(side="left", padx=(5,5))
        Tooltip(check_manuales, "Muestra solo comentarios añadidos manualmente (no cambios automáticos)")
        
        # Frame para botones de acción
        botones_frame = ctk.CTkFrame(controles_frame)
        botones_frame.pack(fill="x", pady=5)
        
        # Frame scrollable para resultados (se crea una sola vez)
        resultados_frame = ctk.CTkScrollableFrame(main_frame, label_text="Historial de Cambios")
        resultados_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        def aplicar_filtros():
            """Aplica los filtros y actualiza la lista de historial."""
            # Validar fechas
            fecha_desde = entry_fecha_desde.get().strip()
            fecha_hasta = entry_fecha_hasta.get().strip()
            
            if fecha_desde:
                valido, mensaje = validar_formato_fecha(fecha_desde)
                if not valido:
                    messagebox.showwarning("Fecha inválida", f"Fecha desde: {mensaje}")
                    return
            
            if fecha_hasta:
                valido, mensaje = validar_formato_fecha(fecha_hasta)
                if not valido:
                    messagebox.showwarning("Fecha inválida", f"Fecha hasta: {mensaje}")
                    return
            
            # Obtener registros filtrados
            registros = obtener_historial_filtrado(
                rma_id=self.rma_actual_id,
                texto_busqueda=entry_busqueda.get(),
                usuario_filtro=combo_usuario.get(),
                fecha_desde=fecha_desde if fecha_desde else None,
                fecha_hasta=fecha_hasta if fecha_hasta else None,
                solo_comentarios_manuales=var_solo_manuales.get(),
                connect_db_func=self.master.conectar_db
            )
            
            # Mostrar resultados
            mostrar_resultados(registros)
            logger.info(f"Filtros aplicados en historial de RMA {self.rma_actual_id}: {len(registros)} registros")
        
        def limpiar_filtros():
            """Limpia todos los filtros y muestra el historial completo."""
            entry_busqueda.delete(0, 'end')
            combo_usuario.set("Todos")
            entry_fecha_desde.delete(0, 'end')
            entry_fecha_hasta.delete(0, 'end')
            var_solo_manuales.set(False)
            aplicar_filtros()
            logger.debug(f"Filtros limpiados en historial de RMA {self.rma_actual_id}")
        
        def mostrar_resultados(registros):
            """Muestra los resultados del historial en el frame de resultados."""
            # Limpiar el frame de resultados (destruir solo los hijos, no el frame)
            for widget in resultados_frame.winfo_children():
                widget.destroy()
            
            # Actualizar el label del frame
            resultados_frame.configure(label_text=f"Historial de Cambios ({len(registros)} registros)")
            
            # Encabezados
            header_font = ctk.CTkFont(weight="bold")
            resultados_frame.grid_columnconfigure(2, weight=1)  # Descripción se expande
            ctk.CTkLabel(resultados_frame, text="FECHA/HORA", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(resultados_frame, text="USUARIO", font=header_font).grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(resultados_frame, text="DESCRIPCIÓN DEL CAMBIO", font=header_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
            
            if not registros:
                ctk.CTkLabel(resultados_frame, text="No hay registros que coincidan con los filtros aplicados.", text_color="gray").grid(row=1, column=0, columnspan=3, padx=10, pady=20)
                return
            
            # Mostrar los registros
            for i, reg in enumerate(registros):
                fecha, usuario, descripcion = reg
                row = i + 1
                
                ctk.CTkLabel(resultados_frame, text=fecha).grid(row=row, column=0, padx=5, pady=2, sticky="w")
                ctk.CTkLabel(resultados_frame, text=usuario).grid(row=row, column=1, padx=5, pady=2, sticky="w")
                
                # Usamos wrap para que el texto de la descripción no se salga
                ctk.CTkLabel(resultados_frame, text=descripcion, wraplength=500, justify="left").grid(row=row, column=2, padx=5, pady=2, sticky="w")
        
        # Botones de acción
        btn_aplicar = ctk.CTkButton(botones_frame, text="🔍 Aplicar Filtros", command=aplicar_filtros)
        btn_aplicar.pack(side="left", padx=5, pady=5)
        Tooltip(btn_aplicar, "Aplica los filtros seleccionados al historial")
        
        btn_limpiar = ctk.CTkButton(botones_frame, text="🗑️ Limpiar Filtros", command=limpiar_filtros)
        btn_limpiar.pack(side="left", padx=5, pady=5)
        Tooltip(btn_limpiar, "Limpia todos los filtros y muestra el historial completo")
        
        # Cargar historial completo al inicio
        aplicar_filtros()

    def determinar_estado_rma(self, datos_maestro):
        """Calcula el estado del RMA basándose en las fechas clave."""
        
        # Obtener fechas del diccionario de datos (asegúrate que las claves son minúsculas como en la DB)
        fecha_recepcion = datos_maestro.get('fecha_recepcion')
        fecha_gestion = datos_maestro.get('fecha_gestion')
        fecha_autorizacion = datos_maestro.get('fecha_autorizacion')
        fecha_proceso = datos_maestro.get('fecha_proceso')
        fecha_emision = datos_maestro.get('fecha_emision')
        
        # 6. Estado 'Completado' (Último paso)
        if fecha_gestion:
            return "Completado"
            
        # 5. Estado 'En Trámite' (Cuando se ingresa fecha de proceso)
        elif fecha_proceso:
            return "En Trámite"
            
        # 4. Estado 'Recibido'
        elif fecha_recepcion:
            return "Recibido"
        
        # 3. Estado 'Autorizado' (Debe ir antes que fecha_emision)
        elif fecha_autorizacion:
            return "Autorizado"
            
        # 2. Estado 'Pendiente de Autorizacion' (Si solo existe la emisión)
        elif fecha_emision:
            return "Pendiente de Autorizacion"
            
        # 1. Estado por defecto
        else:
            return "Pendiente de Autorizacion"

    def mostrar_dialogo_autorizacion(self, rma_id, codigo_rma):
        """
        Muestra el diálogo para generar el PDF de autorización.
        
        Args:
            rma_id (int): ID del expediente
            codigo_rma (str): Código del expediente
        """
        from lib.autorizacion_docx import generar_autorizacion_docx
        import tkinter.filedialog as filedialog
        from datetime import datetime
        from CTkDatePicker import CTkDatePicker
        from PIL import Image
        
        # Función para validar imagen
        def validar_imagen(ruta_imagen):
            if not os.path.exists(ruta_imagen):
                return False
            try:
                with Image.open(ruta_imagen) as img:
                    img.verify()
                return True
            except Exception:
                return False
        
        # Verificar permisos
        if self.rol not in ["administrador", "admin", "Dpto. Tecnico", "Administracion"]:
            messagebox.showwarning(
                "Permiso Denegado",
                "No tiene permisos para generar autorizaciones."
            )
            return
        
        # Obtener datos del expediente
        conn, cursor = self.master.conectar_db()
        try:
            cursor.execute("""
                SELECT cliente, Persona_de_Contacto, Email_de_Contacto, 
                       fecha_emision, motivo, fecha_autorizacion, autorizado_por
                FROM rma_maestro
                WHERE id = ?
            """, (rma_id,))
            
            resultado = cursor.fetchone()
            if not resultado:
                messagebox.showerror("Error", "No se encontraron los datos del expediente.")
                return
            
            cliente, persona_de_contacto, email_de_contacto, fecha_emision, motivo, fecha_autorizacion, autorizado_por = resultado
            
            # Verificar si el expediente ya está autorizado
            if fecha_autorizacion and self.rol != "admin":
                usuario_info = f" por {autorizado_por}" if autorizado_por else ""
                messagebox.showwarning(
                    "Expediente Autorizado",
                    f"Este expediente ya fue autorizado el {fecha_autorizacion}{usuario_info}."
                )
                return
            
        except Exception as e:
            logger.error(f"Error al obtener datos del expediente: {e}")
            messagebox.showerror("Error", f"Error al obtener datos: {e}")
            return
        finally:
            conn.close()
        
        # Crear ventana de diálogo
        ventana = ctk.CTkToplevel(self.master)
        ventana.title(f"Generar Autorización - {codigo_rma}")
        ventana.geometry("650x580")
        ventana.transient(self.master)
        ventana.grab_set()
        
        # Centrar ventana
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (650 // 2)
        y = (ventana.winfo_screenheight() // 2) - (580 // 2)
        ventana.geometry(f"650x580+{x}+{y}")
        
        # Frame principal
        main_frame = ctk.CTkFrame(ventana)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            main_frame,
            text=f"📄 Autorización de Devolución",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 20))
        
        # Información del expediente
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            info_frame,
            text=f"Expediente: {codigo_rma}",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(
            info_frame,
            text=f"Cliente: {cliente or 'N/A'}",
            font=("Arial", 11)
        ).pack(anchor="w", padx=10)
        
        # Observaciones
        ctk.CTkLabel(
            main_frame,
            text="Observaciones:",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", pady=(10, 5))
        
        observaciones_text = ctk.CTkTextbox(
            main_frame,
            height=120,
            width=540
        )
        observaciones_text.pack(pady=(0, 15))
        
        # Fecha de autorización
        fecha_frame = ctk.CTkFrame(main_frame)
        fecha_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            fecha_frame,
            text="Fecha de Autorización:",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=(10, 10))
        
        # Crear el date picker
        fecha_picker = CTkDatePicker(fecha_frame, width=180)
        
        # Aplicar formato de fecha según preferencia del usuario
        try:
            pref = getattr(self, 'user_settings', {}).get('date_format', 'YYYY-MM-DD')
            fmt_map = {
                'YYYY-MM-DD': '%Y-%m-%d',
                'DD/MM/YYYY': '%d/%m/%Y',
                'MM/DD/YYYY': '%m/%d/%Y'
            }
            widget_fmt = fmt_map.get(pref, '%Y-%m-%d')
            fecha_picker.set_date_format(widget_fmt)
        except Exception:
            # Fallback seguro
            try:
                fecha_picker.set_date_format('%Y-%m-%d')
            except Exception:
                pass
        
        fecha_picker.pack(side="left", padx=5)
        
        # Establecer fecha actual
        fecha_picker.set_date(datetime.now())
        
        # Botón "Hoy"
        def establecer_hoy():
            fecha_picker.set_date(datetime.now())
        
        ctk.CTkButton(
            fecha_frame,
            text="Hoy",
            command=establecer_hoy,
            width=60
        ).pack(side="left", padx=5)
        
        # Cuño de empresa
        var_cuno = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            main_frame,
            text="Incluir cuño de la empresa",
            variable=var_cuno,
            font=("Arial", 11)
        ).pack(anchor="w", pady=(0, 10))
        
        # Firma del usuario
        var_usar_firma = ctk.BooleanVar(value=False)
        
        # Verificar si el usuario tiene firma registrada
        tiene_firma_usuario = self.user_settings.get("tiene_firma", False)
        
        if tiene_firma_usuario:
            var_usar_firma.set(True)
            ctk.CTkCheckBox(
                main_frame,
                text="Incluir mi firma",
                variable=var_usar_firma,
                font=("Arial", 11)
            ).pack(anchor="w", pady=(0, 10))
        else:
            # Mostrar mensaje de que no tiene firma configurada
            no_firma_label = ctk.CTkLabel(
                main_frame,
                text="⚠️ No tiene firma configurada. Configure su firma en Ajustes.",
                font=("Arial", 10),
                text_color="orange"
            )
            no_firma_label.pack(anchor="w", pady=(0, 10))
        
        # Botones de acción
        botones_frame = ctk.CTkFrame(main_frame)
        botones_frame.pack(fill="x", pady=(20, 0))
        
        # Barra de progreso (oculta inicialmente)
        progreso_frame = ctk.CTkFrame(main_frame)
        progreso_label = ctk.CTkLabel(progreso_frame, text="Generando documento...", font=("Arial", 10))
        progreso_bar = ctk.CTkProgressBar(progreso_frame, width=540)
        progreso_bar.set(0)
        
        def mostrar_progreso(visible=True):
            if visible:
                progreso_frame.pack(fill="x", pady=(10, 0), before=botones_frame)
                progreso_label.pack(pady=(5, 2))
                progreso_bar.pack(pady=(0, 5))
                ventana.update()
            else:
                progreso_frame.pack_forget()
        
        def actualizar_progreso(valor, texto="Generando documento..."):
            progreso_bar.set(valor)
            progreso_label.configure(text=texto)
            ventana.update()
        
        def generar_pdf():
            try:
                # Mostrar barra de progreso
                mostrar_progreso(True)
                actualizar_progreso(0.1, "Preparando datos...")
                
                # Obtener valores
                observaciones = observaciones_text.get("1.0", "end-1c").strip()
                
                # Obtener fecha del picker (devuelve string)
                try:
                    fecha_str = fecha_picker.get_date()
                    # Convertir a formato ISO usando la función global parse_date_to_iso
                    fecha_autorizacion_str = parse_date_to_iso(fecha_str)
                except Exception as e:
                    logger.error(f"Error obteniendo fecha del picker: {e}")
                    fecha_autorizacion_str = datetime.now().strftime("%Y-%m-%d")
                
                usar_cuno = var_cuno.get()
                usar_firma = var_usar_firma.get()
                
                actualizar_progreso(0.2, "Validando archivos...")
                
                # Ruta del cuño (si está habilitado)
                cuno_path = None
                if usar_cuno:
                    directorio_base = os.path.dirname(os.path.abspath(__file__))
                    cuno_path = os.path.join(directorio_base, "plantillas", "Cuño.jpg")
                    if not os.path.exists(cuno_path):
                        logger.warning(f"No se encuentra el cuño en: {cuno_path}")
                        cuno_path = None
                
                # Descargar firma del usuario desde B2 si está habilitado
                ruta_firma = None
                firma_temp_path = None
                if usar_firma and tiene_firma_usuario:
                    import tempfile
                    # Crear archivo temporal para la firma
                    firma_temp_fd, firma_temp_path = tempfile.mkstemp(suffix=".png", prefix=f"firma_{self.username}_")
                    os.close(firma_temp_fd)
                    
                    # Descargar firma desde B2
                    if descargar_firma_usuario_b2(self.username, firma_temp_path, get_b2_client):
                        ruta_firma = firma_temp_path
                        logger.info(f"Firma descargada para usuario {self.username}")
                    else:
                        logger.warning(f"No se pudo descargar firma para usuario {self.username}")
                        messagebox.showwarning(
                            "Advertencia",
                            "No se pudo descargar su firma desde el almacenamiento.\n"
                            "El documento se generará sin firma."
                        )
                
                # Nombre del archivo - Formato: RMA26001_Autorizacion.pdf (se convertirá de DOCX)
                nombre_archivo = f"{codigo_rma}_Autorizacion.pdf"
                
                actualizar_progreso(0.3, "Preparando archivos temporales...")
                
                # Generar documento en directorio temporal
                import tempfile
                temp_dir = tempfile.gettempdir()
                ruta_temporal = os.path.join(temp_dir, nombre_archivo)
                
                # Ruta de la plantilla
                plantilla_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "plantillas",
                    "Plantilla_Autorizacion.docx"
                )
                
                if not os.path.exists(plantilla_path):
                    mostrar_progreso(False)
                    messagebox.showerror("Error", f"No se encuentra la plantilla:\\n{plantilla_path}")
                    return
                
                actualizar_progreso(0.4, "Generando documento...")
                
                # Generar documento DOCX
                exito = generar_autorizacion_docx(
                    plantilla_path=plantilla_path,
                    ruta_destino=ruta_temporal,
                    codigo_rma=codigo_rma,
                    cliente=cliente or "",
                    persona_de_contacto=persona_de_contacto or "",
                    email_de_contacto=email_de_contacto or "",
                    fecha_emision=fecha_emision or "",
                    motivo=motivo or "",
                    observaciones=observaciones,
                    fecha_autorizacion=fecha_autorizacion_str,
                    usar_cuno=usar_cuno,
                    cuno_path=cuno_path,
                    ruta_firma=ruta_firma
                )
                
                # Limpiar archivo temporal de firma si se creó
                if firma_temp_path and os.path.exists(firma_temp_path):
                    try:
                        os.unlink(firma_temp_path)
                    except:
                        pass
                
                if exito:
                    actualizar_progreso(0.7, "Subiendo archivo...")
                    
                    # Subir el archivo usando el mismo sistema que otros adjuntos
                    if usar_b2():
                        exito_subida, ruta_relativa = self._subir_archivo_b2(ruta_temporal, codigo_rma, nombre_archivo, None)
                        tipo_almacenamiento = 'backblaze'
                    else:
                        exito_subida, ruta_relativa = self._subir_archivo_local(ruta_temporal, codigo_rma, nombre_archivo)
                        tipo_almacenamiento = 'local'
                    
                    # Limpiar archivo temporal
                    try:
                        os.unlink(ruta_temporal)
                    except:
                        pass
                    
                    if not exito_subida:
                        mostrar_progreso(False)
                        messagebox.showerror("Error", "No se pudo subir el documento. Revise los logs.")
                        return
                    
                    actualizar_progreso(0.9, "Registrando en base de datos...")
                    
                    # Registrar en la base de datos
                    conn, cursor = self.master.conectar_db()
                    try:
                        # Registrar el adjunto
                        if getattr(self, '_usar_tipo_almacenamiento', False):
                            # Usar esquema nuevo con tipo_almacenamiento
                            cursor.execute("""
                                INSERT INTO rma_adjuntos 
                                (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                rma_id,
                                nombre_archivo,
                                ruta_relativa,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                self.username,
                                tipo_almacenamiento
                            ))
                        else:
                            # Usar esquema antiguo sin tipo_almacenamiento
                            cursor.execute("""
                                INSERT INTO rma_adjuntos 
                                (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                rma_id,
                                nombre_archivo,
                                ruta_relativa,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                self.username
                            ))
                        
                        # Actualizar campos de autorización y estado en rma_maestro
                        cursor.execute("""
                            UPDATE rma_maestro
                            SET fecha_autorizacion = ?,
                                autorizado_por = ?,
                                estado = 'Autorizado'
                            WHERE id = ?
                        """, (fecha_autorizacion_str, self.username.upper(), rma_id))
                        
                        # Registrar en historial del expediente
                        cursor.execute("""
                            INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                            VALUES (?, ?, ?, ?)
                        """, (
                            rma_id,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            self.username,
                            f"Documento de autorización generado. Fecha de autorización: {fecha_autorizacion_str}"
                        ))
                        
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Error al registrar adjunto: {e}")
                    finally:
                        conn.close()
                    
                    actualizar_progreso(1.0, "¡Completado!")
                    
                    # Ocultar barra de progreso después de un breve momento
                    ventana.after(500, lambda: mostrar_progreso(False))
                    
                    messagebox.showinfo(
                        "Éxito",
                        f"Documento de autorización generado correctamente"
                    )
                    ventana.destroy()
                    
                    # Refrescar lista de adjuntos
                    if hasattr(self, 'cargar_lista_adjuntos'):
                        try:
                            self.cargar_lista_adjuntos(rma_id)
                        except Exception as e:
                            logger.warning(f"No se pudo refrescar lista de adjuntos: {e}")
                    
                    # Recargar los datos del expediente en la ventana actual (sin abrir nueva ventana)
                    if hasattr(self, 'cargar_datos_rma'):
                        try:
                            self.cargar_datos_rma(rma_id)
                            logger.info(f"Datos del expediente {codigo_rma} actualizados después de autorización")
                        except Exception as e:
                            logger.warning(f"No se pudieron actualizar los datos del expediente: {e}")
                else:
                    mostrar_progreso(False)
                    messagebox.showerror("Error", "No se pudo generar el documento. Revise los logs.")
                    
            except Exception as e:
                mostrar_progreso(False)
                logger.error(f"Error al generar autorización: {e}", exc_info=True)
                messagebox.showerror("Error", f"Error al generar autorización:\n{e}")
        
        ctk.CTkButton(
            botones_frame,
            text="✓ Generar PDF",
            command=generar_pdf,
            width=150,
            fg_color="#27ae60",
            hover_color="#229954"
        ).pack(side="left", padx=10, expand=True)
        
        ctk.CTkButton(
            botones_frame,
            text="✗ Cancelar",
            command=ventana.destroy,
            width=150,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=10, expand=True)

    def _verificar_existe_autorizacion(self, rma_id, codigo_rma):
        """
        Verifica si existe el archivo de autorización para el expediente.
        
        Args:
            rma_id (int): ID del expediente
            codigo_rma (str): Código del expediente
            
        Returns:
            dict o None: Diccionario con info del adjunto si existe, None si no
        """
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                return None
            
            # Buscar el archivo de autorización en rma_adjuntos
            nombre_archivo = f"{codigo_rma}_Autorizacion.pdf"
            cursor.execute("""
                SELECT ruta_relativa, tipo_almacenamiento
                FROM rma_adjuntos
                WHERE rma_id = ? AND nombre_archivo = ?
            """, (rma_id, nombre_archivo))
            
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado:
                return {
                    'ruta_relativa': resultado[0],
                    'tipo_almacenamiento': resultado[1] if len(resultado) > 1 else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Error verificando autorización: {e}")
            return None

    def _abrir_autorizacion(self, archivo_info, codigo_rma):
        """
        Descarga el archivo de autorización.
        
        Args:
            archivo_info (dict): Información del archivo (ruta_relativa, tipo_almacenamiento)
            codigo_rma (str): Código del expediente
        """
        try:
            import tkinter.filedialog as filedialog
            
            # Preguntar dónde guardar el archivo
            nombre_archivo = f"{codigo_rma}_Autorizacion.pdf"
            ruta_destino = filedialog.asksaveasfilename(
                title="Guardar Autorización",
                initialfile=nombre_archivo,
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf"), ("Todos los archivos", "*.*")]
            )
            
            if not ruta_destino:
                return  # Usuario canceló
            
            ruta_relativa = archivo_info['ruta_relativa']
            
            # Descargar según el tipo de almacenamiento
            if usar_b2():
                # Descargar desde B2
                b2_api, bucket = get_b2_client()
                if not b2_api or not bucket:
                    messagebox.showerror("Error", "No se puede conectar con Backblaze B2.")
                    return
                
                ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
                downloaded_file = bucket.download_file_by_name(ruta_b2)
                downloaded_file.save_to(ruta_destino)
                
            else:
                # Copiar desde almacenamiento local
                import shutil
                ruta_local = os.path.join("Adjuntos_RMA", ruta_relativa)
                if os.path.exists(ruta_local):
                    shutil.copy2(ruta_local, ruta_destino)
                else:
                    messagebox.showerror("Error", f"No se encuentra el archivo:\n{ruta_local}")
                    return
            
            messagebox.showinfo("Éxito", f"Archivo guardado en:\n{ruta_destino}")
            logger.info(f"Autorización descargada: {codigo_rma} -> {ruta_destino}")
            
            # Preguntar si desea abrir el archivo
            if messagebox.askyesno("Abrir archivo", "¿Desea abrir el archivo descargado?"):
                os.startfile(ruta_destino)
                
        except Exception as e:
            logger.error(f"Error descargando autorización: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo descargar el archivo de autorización:\n{e}")

    def _mostrar_dialogo_cliente_no_existe(self, nombre_cliente):
        """
        Muestra un diálogo indicando que el cliente no existe en la base de datos.
        Ofrece opciones: Cancelar o Crear Nuevo Cliente.
        
        Args:
            nombre_cliente (str): Nombre del cliente que se intentó usar
        """
        # Si es admin, permitir crear el cliente sin restricciones
        if self.username.lower() == "admin":
            # El admin puede crear el cliente, no mostrar diálogo de restricción
            return
        
        # Crear ventana de diálogo
        ventana = ctk.CTkToplevel(self)
        ventana.title("Cliente No Registrado")
        ventana.geometry("500x250")
        ventana.resizable(False, False)
        
        # Centrar ventana en la pantalla
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (500 // 2)
        y = (ventana.winfo_screenheight() // 2) - (250 // 2)
        ventana.geometry(f"500x250+{x}+{y}")
        
        # Hacer la ventana modal - se muestra por encima de la ventana actual
        ventana.transient(self)
        ventana.grab_set()
        
        # Asegurar que la ventana del expediente quede detrás del diálogo
        self.lift()
        
        # Frame principal
        main_frame = ctk.CTkFrame(ventana)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icono y título
        ctk.CTkLabel(
            main_frame,
            text="⚠️ Cliente No Encontrado",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="orange"
        ).pack(pady=(0, 15))
        
        # Mensaje
        mensaje = f"""El cliente '{nombre_cliente}' no existe en la base de datos de clientes.

Para crear un expediente, el cliente debe estar registrado previamente en la sección de Clientes."""
        
        ctk.CTkLabel(
            main_frame,
            text=mensaje,
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=450
        ).pack(pady=(0, 20))
        
        # Botones
        botones_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        botones_frame.pack(pady=10)
        
        def crear_cliente():
            """Cierra el diálogo y abre el formulario de nuevo cliente."""
            # Cerrar el diálogo
            ventana.destroy()
            # Abrir directamente el formulario de nuevo cliente
            self.nuevo_cliente()
        
        def cancelar():
            """Cierra el diálogo."""
            ventana.destroy()
        
        # Botón Crear Nuevo Cliente (recomendado)
        ctk.CTkButton(
            botones_frame,
            text="➕ Crear Nuevo Cliente",
            command=crear_cliente,
            width=180,
            fg_color="#27ae60",
            hover_color="#229954"
        ).pack(side="left", padx=10)
        
        # Botón Cancelar
        ctk.CTkButton(
            botones_frame,
            text="✗ Cancelar",
            command=cancelar,
            width=120,
            fg_color="#95a5a6",
            hover_color="#7f8c8d"
        ).pack(side="left", padx=10)

    def confirmar_cambio_estado(self, rma_id, codigo_rma, nuevo_estado):
        """
        Muestra ventana de confirmación antes de cambiar el estado del expediente.
        
        Args:
            rma_id (int): ID del expediente
            codigo_rma (str): Código del expediente
            nuevo_estado (str): Estado al que se va a cambiar
        """
        from datetime import datetime
        import customtkinter as ctk
        from CTkDatePicker import CTkDatePicker
        
        # Crear ventana de confirmación
        ventana = ctk.CTkToplevel(self)
        ventana.title("Confirmar Cambio de Estado")
        ventana.geometry("500x350")
        ventana.resizable(False, False)
        
        # Centrar la ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Frame principal
        main_frame = ctk.CTkFrame(ventana)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            main_frame,
            text=f"Cambiar Estado de {codigo_rma}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 20))
        
        # Información del cambio
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=10)
        
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        
        ctk.CTkLabel(
            info_frame,
            text=f"Nuevo Estado:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkLabel(
            info_frame,
            text=nuevo_estado
        ).grid(row=0, column=1, sticky="w", padx=5, pady=5, columnspan=2)
        
        ctk.CTkLabel(
            info_frame,
            text=f"Fecha:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        # Frame para el selector de fecha y botón Hoy
        fecha_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        fecha_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5, columnspan=2)
        
        # Selector de fecha (CTkDatePicker)
        date_picker = CTkDatePicker(fecha_frame, width=180)
        
        # Aplicar formato de fecha según preferencia del usuario
        try:
            pref = getattr(self, 'user_settings', {}).get('date_format', 'YYYY-MM-DD')
            fmt_map = {
                'YYYY-MM-DD': '%Y-%m-%d',
                'DD/MM/YYYY': '%d/%m/%Y',
                'MM/DD/YYYY': '%m/%d/%Y'
            }
            widget_fmt = fmt_map.get(pref, '%Y-%m-%d')
            date_picker.set_date_format(widget_fmt)
        except Exception:
            # Fallback seguro
            try:
                date_picker.set_date_format('%Y-%m-%d')
            except Exception:
                pass
        
        date_picker.pack(side="left", padx=(0, 5))
        
        # Botón Hoy
        def establecer_hoy():
            date_picker.set_date(datetime.now())
        
        btn_hoy = ctk.CTkButton(
            fecha_frame,
            text="Hoy",
            width=60,
            command=establecer_hoy
        )
        btn_hoy.pack(side="left")
        
        # Verificar si el usuario tiene privilegios (por ROL, no por username)
        # Los roles con privilegios son: administrador, admin, administracion y Dpto. Tecnico
        es_privilegiado = self.rol in ["administrador", "admin", "Administracion", "Dpto. Tecnico"]
        
        # Si no es privilegiado, ocultar los controles de fecha y mostrar solo texto
        if not es_privilegiado:
            # Ocultar date_picker y btn_hoy
            date_picker.pack_forget()
            btn_hoy.pack_forget()
            
            # Mostrar fecha actual como texto no editable
            ctk.CTkLabel(
                fecha_frame,
                text=datetime.now().strftime('%Y-%m-%d'),
                width=180
            ).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(
            info_frame,
            text=f"Usuario:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        # Si es privilegiado, mostrar desplegable de usuarios
        # Si no lo es, solo mostrar su nombre como texto
        if es_privilegiado:
            # Obtener lista de usuarios disponibles (excluyendo 'admin')
            usuarios_disponibles = [self.username]
            try:
                conn, cursor = self.master.conectar_db()
                if conn:
                    cursor.execute("SELECT nombre_usuario FROM usuarios WHERE nombre_usuario != 'admin' ORDER BY nombre_usuario")
                    usuarios_disponibles = [row[0] for row in cursor.fetchall()]
                    conn.close()
            except Exception as e:
                print(f"Error obteniendo usuarios: {e}")
            
            # Desplegable para el usuario
            usuario_menu = ctk.CTkOptionMenu(
                info_frame,
                values=usuarios_disponibles,
                width=180
            )
            usuario_menu.set(self.username)
            usuario_menu.grid(row=2, column=1, sticky="w", padx=5, pady=5, columnspan=2)
        else:
            # Mostrar solo el nombre del usuario actual como texto
            ctk.CTkLabel(
                info_frame,
                text=self.username,
                width=180
            ).grid(row=2, column=1, sticky="w", padx=5, pady=5, columnspan=2)
            
            # Crear un menu oculto para que ejecutar_cambio funcione
            usuario_menu = ctk.CTkOptionMenu(
                info_frame,
                values=[self.username],
                width=180
            )
            usuario_menu.set(self.username)
            # No hacer grid, solo mantenerlo en memoria
        
        # Botones
        botones_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        botones_frame.pack(side="bottom", pady=20)
        
        def ejecutar_cambio():
            from lib.rma_utils import cambiar_estado_expediente
            
            # Obtener fecha (si es privilegiado del picker, si no, fecha actual)
            if es_privilegiado:
                try:
                    fecha_obj = date_picker.get_date()
                    # parse_date_to_iso espera un string o un objeto datetime
                    if isinstance(fecha_obj, str):
                        fecha = parse_date_to_iso(fecha_obj)
                    else:
                        # Es un objeto datetime, convertir a string ISO
                        fecha = fecha_obj.strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"Error obteniendo fecha del picker: {e}")
                    fecha = datetime.now().strftime('%Y-%m-%d')
            else:
                # Usuario no privilegiado siempre usa fecha actual
                fecha = datetime.now().strftime('%Y-%m-%d')
            
            usuario = usuario_menu.get()
            
            conn, cursor = self.master.conectar_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                ventana.destroy()
                return
            
            exito = cambiar_estado_expediente(conn, rma_id, nuevo_estado, usuario, fecha)
            conn.close()
            
            if exito:
                messagebox.showinfo(
                    "Éxito",
                    f"Estado de {codigo_rma} cambiado a '{nuevo_estado}'"
                )
                ventana.destroy()
                # Recargar la lista
                self.aplicar_filtros_rma()
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo cambiar el estado del expediente"
                )
        
        ctk.CTkButton(
            botones_frame,
            text="✓ Aceptar",
            command=ejecutar_cambio,
            width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            botones_frame,
            text="✗ Cancelar",
            command=ventana.destroy,
            width=120,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=10)

    def mostrar_eliminar_rma(self):
        """Ventana simple para eliminar RMA."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("ELIMINAR RMA")
        ventana.geometry("400x300")
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        ctk.CTkLabel(ventana, text="ELIMINAR RMA", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Campo entrada
        ctk.CTkLabel(ventana, text="Código RMA:", font=ctk.CTkFont(size=14)).pack()
        entry = ctk.CTkEntry(ventana, width=200, height=30, font=ctk.CTkFont(size=14))
        entry.pack(pady=10)
        
        # Info
        info = ctk.CTkLabel(ventana, text="", font=ctk.CTkFont(size=12))
        info.pack(pady=10)
        
        # Buscar
        def buscar():
            codigo = entry.get().strip()
            if not codigo:
                info.configure(text="Escribe un código RMA", text_color="orange")
                btn_eliminar.configure(state="disabled")
                return
            
            conn, cursor = self.conectar_db()
            if conn:
                cursor.execute("SELECT cliente, fecha_emision FROM rma_maestro WHERE codigo_rma = ?", (codigo,))
                data = cursor.fetchone()
                conn.close()
                if data:
                    info.configure(text=f"Encontrado: {data[0]} - {data[1]}", text_color="green")
                    btn_eliminar.configure(state="normal")
                else:
                    info.configure(text="RMA no encontrado", text_color="red")
                    btn_eliminar.configure(state="disabled")
        
        ctk.CTkButton(ventana, text="BUSCAR", command=buscar, width=100, height=30).pack(pady=5)
        
        # Eliminar
        def eliminar():
            codigo = entry.get().strip()
            if messagebox.askyesno("Confirmar", f"¿Eliminar RMA {codigo}?"):
                try:
                    conn, cursor = self.conectar_db()
                    cursor.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo,))
                    rma_id = cursor.fetchone()[0]
                    cursor.execute("DELETE FROM rma_historial WHERE rma_id = ?", (rma_id,))
                    cursor.execute("DELETE FROM rma_detalles WHERE rma_id = ?", (rma_id,))
                    cursor.execute("DELETE FROM rma_maestro WHERE id = ?", (rma_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("OK", f"RMA {codigo} eliminado")
                    ventana.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        
        btn_eliminar = ctk.CTkButton(ventana, text="ELIMINAR", command=eliminar, 
                                    fg_color="red", width=150, height=40, state="disabled")
        btn_eliminar.pack(pady=20)
        
        ctk.CTkButton(ventana, text="CANCELAR", command=ventana.destroy, width=100).pack()

    def mostrar_generar_numero_manual(self):
        """Ventana simple para crear RMA manual."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("CREAR RMA MANUAL")
        ventana.geometry("400x250")
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        ctk.CTkLabel(ventana, text="CREAR RMA MANUAL", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Campo entrada
        ctk.CTkLabel(ventana, text="Código RMA:", font=ctk.CTkFont(size=14)).pack()
        entry = ctk.CTkEntry(ventana, width=200, height=30, font=ctk.CTkFont(size=14))
        entry.pack(pady=10)
        
        # Info
        info = ctk.CTkLabel(ventana, text="", font=ctk.CTkFont(size=12))
        info.pack(pady=10)
        
        # Validar
        def validar():
            codigo = entry.get().strip().upper()
            if not codigo:
                info.configure(text="Escribe un código RMA", text_color="orange")
                btn_crear.configure(state="disabled")
                return
            
            if not codigo.startswith("RMA25"):
                info.configure(text="Debe empezar con RMA25", text_color="red")
                btn_crear.configure(state="disabled")
                return
            
            conn, cursor = self.conectar_db()
            if conn:
                cursor.execute("SELECT COUNT(*) FROM rma_maestro WHERE codigo_rma = ?", (codigo,))
                existe = cursor.fetchone()[0] > 0
                conn.close()
                if existe:
                    info.configure(text="Ya existe ese código", text_color="red")
                    btn_crear.configure(state="disabled")
                else:
                    info.configure(text="Código válido", text_color="green")
                    btn_crear.configure(state="normal")
        
        ctk.CTkButton(ventana, text="VALIDAR", command=validar, width=100, height=30).pack(pady=5)
        
        # Crear
        def crear():
            codigo = entry.get().strip().upper()
            if messagebox.askyesno("Confirmar", f"¿Crear RMA {codigo}?"):
                try:
                    conn, cursor = self.conectar_db()
                    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        INSERT INTO rma_maestro (codigo_rma, cliente, fecha_emision, creado_por, estado, precio_total_expediente)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (codigo, "[Manual]", fecha, self.username, "Creado", 0.0))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("OK", f"RMA {codigo} creado")
                    ventana.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        
        btn_crear = ctk.CTkButton(ventana, text="CREAR", command=crear, 
                                 width=150, height=40, state="disabled")
        btn_crear.pack(pady=20)
        
        ctk.CTkButton(ventana, text="CANCELAR", command=ventana.destroy, width=100).pack()
