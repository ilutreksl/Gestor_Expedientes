"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class BusquedaMixin:
    def cargar_historial_busquedas(self):
        """Carga el historial de búsquedas del usuario desde configuración."""
        if not hasattr(self, 'historial_busquedas'):
            self.historial_busquedas = self.user_settings.get("historial_busquedas", [])
        return self.historial_busquedas[:10]  # Máximo 10 búsquedas recientes

    def guardar_busqueda_en_historial(self, termino, filtros=None):
        """Guarda una nueva búsqueda en el historial."""
        if not termino.strip():
            return
        
        # Crear entrada del historial
        entrada = {
            "termino": termino.strip(),
            "filtros": filtros or {},
            "fecha": datetime.datetime.now().isoformat()
        }
        
        # Cargar historial actual
        if not hasattr(self, 'historial_busquedas'):
            self.historial_busquedas = self.user_settings.get("historial_busquedas", [])
        
        # Remover búsqueda duplicada si existe
        self.historial_busquedas = [h for h in self.historial_busquedas 
                                   if h.get("termino") != termino.strip()]
        
        # Añadir al principio
        self.historial_busquedas.insert(0, entrada)
        
        # Mantener solo las últimas 10
        self.historial_busquedas = self.historial_busquedas[:10]
        
        # Guardar en configuración
        self.user_settings["historial_busquedas"] = self.historial_busquedas
        save_user_settings(self.user_settings, self.username)

    def limpiar_historial_busquedas(self):
        """Limpia todo el historial de búsquedas."""
        self.historial_busquedas = []
        self.user_settings["historial_busquedas"] = []
        save_user_settings(self.user_settings, self.username)

    def mostrar_busqueda_global(self):
        """Muestra la interfaz de búsqueda global avanzada con filtros múltiples e historial."""
        self.limpiar_contenido()
        
        # Header
        header_frame = ctk.CTkFrame(self.content_frame)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, 
                    text="🔍 BÚSQUEDA GLOBAL AVANZADA", 
                    font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        
        # Botón para volver
        btn_volver = ctk.CTkButton(header_frame, text="← Volver a Lista", 
                                  command=self.mostrar_lista_rma,
                                  width=150, height=30)
        btn_volver.pack(anchor="e", padx=10, pady=(0,5))
        
        # Frame principal con dos columnas
        main_frame = ctk.CTkFrame(self.content_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        main_frame.grid_columnconfigure(0, weight=2, minsize=400)  # Búsqueda principal
        main_frame.grid_columnconfigure(1, weight=1, minsize=250)  # Historial
        
        # === COLUMNA IZQUIERDA: BÚSQUEDA Y FILTROS ===
        search_column = ctk.CTkFrame(main_frame)
        search_column.grid(row=0, column=0, sticky="nsew", padx=(10,5), pady=10)
        
        # Campo de búsqueda principal
        ctk.CTkLabel(search_column, text="Buscar en todos los campos:", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        entrada_frame = ctk.CTkFrame(search_column, fg_color="transparent")
        entrada_frame.pack(fill="x", padx=10, pady=5)
        
        self.entry_busqueda_global = ctk.CTkEntry(entrada_frame, 
                                                 placeholder_text="Escribe cualquier texto para buscar...",
                                                 height=35,
                                                 font=ctk.CTkFont(size=12))
        self.entry_busqueda_global.pack(fill="x", padx=(0,10))
        
        # Botones de búsqueda
        botones_frame = ctk.CTkFrame(search_column, fg_color="transparent")
        botones_frame.pack(fill="x", padx=10, pady=5)
        
        btn_buscar = ctk.CTkButton(botones_frame, text="🔍 Buscar", 
                                  command=self.ejecutar_busqueda_global,
                                  width=100, height=35)
        btn_buscar.pack(side="left", padx=(0,5))
        
        btn_limpiar = ctk.CTkButton(botones_frame, text="🗑️ Limpiar", 
                                   command=self.limpiar_busqueda_global,
                                   width=100, height=35)
        btn_limpiar.pack(side="left", padx=5)
        
        # === FILTROS AVANZADOS ===
        filtros_frame = ctk.CTkFrame(search_column)
        filtros_frame.pack(fill="x", padx=10, pady=10)
        
        # Header de filtros con botón expandir/contraer
        filtros_header = ctk.CTkFrame(filtros_frame, fg_color="transparent")
        filtros_header.pack(fill="x", padx=10, pady=5)
        
        self.filtros_expandido = ctk.BooleanVar(value=False)
        self.btn_toggle_filtros = ctk.CTkButton(filtros_header, 
                                              text="🔽 Mostrar Filtros Avanzados",
                                              command=self.toggle_filtros_avanzados,
                                              width=200, height=30)
        self.btn_toggle_filtros.pack(side="left")
        
        # Frame de filtros (inicialmente oculto)
        self.filtros_content = ctk.CTkFrame(filtros_frame)
        # No pack inicialmente - se mostrará al expandir
        
        # Crear controles de filtros
        self.crear_controles_filtros()
        
        # Bind Enter key
        self.entry_busqueda_global.bind("<Return>", lambda e: self.ejecutar_busqueda_global())
        
        # === COLUMNA DERECHA: HISTORIAL ===
        historial_column = ctk.CTkFrame(main_frame)
        historial_column.grid(row=0, column=1, sticky="nsew", padx=(5,10), pady=10)
        
        # Header del historial
        historial_header = ctk.CTkFrame(historial_column, fg_color="transparent")
        historial_header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(historial_header, text="� Historial de Búsquedas", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        btn_limpiar_historial = ctk.CTkButton(historial_header, text="🗑️", 
                                            command=self.limpiar_historial_busquedas_ui,
                                            width=30, height=25)
        btn_limpiar_historial.pack(side="right")
        
        # Lista del historial
        self.historial_frame = ctk.CTkScrollableFrame(historial_column, height=200)
        self.historial_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.actualizar_historial_ui()
        
        # Información de ayuda
        ayuda_frame = ctk.CTkFrame(search_column, fg_color="transparent")
        ayuda_frame.pack(fill="x", padx=10, pady=5)
        
        ayuda_text = """💡 Búsqueda en: Expedientes (Código, Cliente, Estado, etc.) y Productos (Referencia, Serie, etc.)
⌨️ Atajo: Ctrl+F | 🔽 Usa filtros para búsquedas más específicas"""
        
        ctk.CTkLabel(ayuda_frame, text=ayuda_text, 
                    font=ctk.CTkFont(size=11), 
                    text_color="gray",
                    justify="left").pack(anchor="w")
        
        # Frame para resultados (span ambas columnas)
        self.resultados_frame = ctk.CTkScrollableFrame(main_frame, height=300)
        self.resultados_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(1, weight=1)

    def crear_controles_filtros(self):
        """Crea los controles de filtros avanzados."""
        # Configurar grid
        self.filtros_content.grid_columnconfigure(0, weight=1)
        self.filtros_content.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # === FILTROS PARA EXPEDIENTES ===
        exp_label = ctk.CTkLabel(self.filtros_content, text="📋 Filtros de Expedientes", 
                               font=ctk.CTkFont(size=13, weight="bold"))
        exp_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10,5))
        row += 1
        
        # Estado del expediente
        ctk.CTkLabel(self.filtros_content, text="Estado:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_estado = ctk.CTkOptionMenu(self.filtros_content, 
                                             values=["Todos", "Pendiente", "Autorizado", "Recibido", "Completado"])
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        # Rango de fechas
        ctk.CTkLabel(self.filtros_content, text="Fecha desde:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_fecha_desde = ctk.CTkEntry(self.filtros_content, placeholder_text="YYYY-MM-DD")
        self.filtro_fecha_desde.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        ctk.CTkLabel(self.filtros_content, text="Fecha hasta:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_fecha_hasta = ctk.CTkEntry(self.filtros_content, placeholder_text="YYYY-MM-DD")
        self.filtro_fecha_hasta.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        # Cliente específico
        ctk.CTkLabel(self.filtros_content, text="Cliente:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_cliente = ctk.CTkEntry(self.filtros_content, placeholder_text="Nombre del cliente")
        self.filtro_cliente.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        # === FILTROS PARA PRODUCTOS ===
        prod_label = ctk.CTkLabel(self.filtros_content, text="📦 Filtros de Productos", 
                               font=ctk.CTkFont(size=13, weight="bold"))
        prod_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15,5))
        row += 1
        
        # Estado del producto
        ctk.CTkLabel(self.filtros_content, text="Estado Producto:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_estado_producto = ctk.CTkEntry(self.filtros_content, placeholder_text="Estado del producto")
        self.filtro_estado_producto.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        # Referencia específica
        ctk.CTkLabel(self.filtros_content, text="Referencia:").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        self.filtro_referencia = ctk.CTkEntry(self.filtros_content, placeholder_text="Referencia del artículo")
        self.filtro_referencia.grid(row=row, column=1, sticky="ew", padx=10, pady=2)
        row += 1
        
        # Botones de filtros
        botones_filtros = ctk.CTkFrame(self.filtros_content, fg_color="transparent")
        botones_filtros.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        btn_aplicar_filtros = ctk.CTkButton(botones_filtros, text="🔍 Buscar con Filtros", 
                                          command=self.ejecutar_busqueda_con_filtros,
                                          height=30)
        btn_aplicar_filtros.pack(side="left", padx=(0,5))
        
        btn_limpiar_filtros = ctk.CTkButton(botones_filtros, text="🧹 Limpiar Filtros", 
                                          command=self.limpiar_filtros,
                                          height=30)
        btn_limpiar_filtros.pack(side="left")

    def toggle_filtros_avanzados(self):
        """Muestra u oculta los filtros avanzados."""
        if self.filtros_expandido.get():
            # Contraer
            self.filtros_content.pack_forget()
            self.btn_toggle_filtros.configure(text="🔽 Mostrar Filtros Avanzados")
            self.filtros_expandido.set(False)
        else:
            # Expandir
            self.filtros_content.pack(fill="x", padx=10, pady=(0,10))
            self.btn_toggle_filtros.configure(text="🔼 Ocultar Filtros Avanzados")
            self.filtros_expandido.set(True)

    def limpiar_filtros(self):
        """Limpia todos los filtros avanzados."""
        self.filtro_estado.set("Todos")
        self.filtro_fecha_desde.delete(0, 'end')
        self.filtro_fecha_hasta.delete(0, 'end')
        self.filtro_cliente.delete(0, 'end')
        self.filtro_estado_producto.delete(0, 'end')
        self.filtro_referencia.delete(0, 'end')

    def actualizar_historial_ui(self):
        """Actualiza la interfaz del historial de búsquedas."""
        # Limpiar historial actual
        for widget in self.historial_frame.winfo_children():
            widget.destroy()
        
        historial = self.cargar_historial_busquedas()
        
        if not historial:
            ctk.CTkLabel(self.historial_frame, text="Sin búsquedas recientes", 
                        text_color="gray").pack(pady=10)
            return
        
        for i, entrada in enumerate(historial):
            self.crear_entrada_historial(entrada, i)

    def crear_entrada_historial(self, entrada, index):
        """Crea una entrada visual en el historial."""
        frame = ctk.CTkFrame(self.historial_frame)
        frame.pack(fill="x", padx=5, pady=2)
        
        # Texto de la búsqueda
        texto = entrada.get("termino", "")
        if len(texto) > 25:
            texto = texto[:22] + "..."
        
        btn_entrada = ctk.CTkButton(frame, text=texto, 
                                  command=lambda: self.usar_busqueda_historial(entrada),
                                  height=25, font=ctk.CTkFont(size=11))
        btn_entrada.pack(side="left", fill="x", expand=True, padx=5, pady=2)
        
        # Fecha (opcional)
        try:
            fecha = entrada.get("fecha", "")
            if fecha:
                fecha_obj = datetime.datetime.fromisoformat(fecha.replace('Z', '+00:00'))
                fecha_str = fecha_obj.strftime("%d/%m")
                ctk.CTkLabel(frame, text=fecha_str, text_color="gray", 
                           font=ctk.CTkFont(size=9)).pack(side="right", padx=5)
        except:
            pass

    def usar_busqueda_historial(self, entrada):
        """Aplica una búsqueda del historial."""
        # Cargar término de búsqueda
        self.entry_busqueda_global.delete(0, 'end')
        self.entry_busqueda_global.insert(0, entrada.get("termino", ""))
        
        # Cargar filtros si existen
        filtros = entrada.get("filtros", {})
        if filtros and hasattr(self, 'filtro_estado'):
            # Expandir filtros si hay filtros guardados
            if not self.filtros_expandido.get():
                self.toggle_filtros_avanzados()
            
            # Aplicar filtros guardados
            self.filtro_estado.set(filtros.get("estado", "Todos"))
            self.filtro_fecha_desde.delete(0, 'end')
            self.filtro_fecha_desde.insert(0, filtros.get("fecha_desde", ""))
            self.filtro_fecha_hasta.delete(0, 'end')
            self.filtro_fecha_hasta.insert(0, filtros.get("fecha_hasta", ""))
            self.filtro_cliente.delete(0, 'end')
            self.filtro_cliente.insert(0, filtros.get("cliente", ""))
            self.filtro_estado_producto.delete(0, 'end')
            self.filtro_estado_producto.insert(0, filtros.get("estado_producto", ""))
            self.filtro_referencia.delete(0, 'end')
            self.filtro_referencia.insert(0, filtros.get("referencia", ""))
        
        # Ejecutar búsqueda
        if filtros:
            self.ejecutar_busqueda_con_filtros()
        else:
            self.ejecutar_busqueda_global()

    def limpiar_historial_busquedas_ui(self):
        """Limpia el historial desde la interfaz."""
        self.limpiar_historial_busquedas()
        self.actualizar_historial_ui()

    def ejecutar_busqueda_con_filtros(self):
        """Ejecuta búsqueda combinada con filtros avanzados."""
        termino = self.entry_busqueda_global.get().strip()
        
        # Recopilar filtros
        filtros = {
            "estado": self.filtro_estado.get() if self.filtro_estado.get() != "Todos" else "",
            "fecha_desde": self.filtro_fecha_desde.get().strip(),
            "fecha_hasta": self.filtro_fecha_hasta.get().strip(),
            "cliente": self.filtro_cliente.get().strip(),
            "estado_producto": self.filtro_estado_producto.get().strip(),
            "referencia": self.filtro_referencia.get().strip()
        }
        
        # Validar fechas
        if filtros["fecha_desde"] and not self.validar_fecha(filtros["fecha_desde"]):
            messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)")
            return
        if filtros["fecha_hasta"] and not self.validar_fecha(filtros["fecha_hasta"]):
            messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)")
            return
        
        # Guardar en historial si hay criterios de búsqueda
        if termino or any(v for v in filtros.values() if v):
            self.guardar_busqueda_en_historial(termino, filtros)
            self.actualizar_historial_ui()
        
        # Limpiar resultados previos
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        
        try:
            resultados_maestro = self.buscar_en_maestro_con_filtros(termino, filtros)
            resultados_detalles = self.buscar_en_detalles_con_filtros(termino, filtros)
            
            self.mostrar_resultados_busqueda_avanzada(resultados_maestro, resultados_detalles, termino, filtros)
            
        except Exception as e:
            messagebox.showerror("Error en la búsqueda", f"Error al ejecutar búsqueda con filtros: {str(e)}")
            print(f"Error en búsqueda con filtros: {e}")

    def buscar_en_maestro_con_filtros(self, termino, filtros):
        """Busca en rma_maestro aplicando filtros."""
        query = "SELECT * FROM rma_maestro WHERE 1=1"
        params = []
        
        # Filtro de texto general
        if termino:
            query += """ AND (
                numero_rma LIKE ? OR cliente LIKE ? OR nombre_contacto LIKE ? OR 
                email_contacto LIKE ? OR direccion_cliente LIKE ? OR 
                telefono_contacto LIKE ? OR motivo_devolucion LIKE ? OR 
                numero_seguimiento LIKE ? OR observaciones LIKE ?
            )"""
            termino_param = f"%{termino}%"
            params.extend([termino_param] * 9)
        
        # Filtros específicos
        if filtros["estado"]:
            query += " AND estado_expediente = ?"
            params.append(filtros["estado"])
        
        if filtros["fecha_desde"]:
            query += " AND fecha_emision >= ?"
            params.append(filtros["fecha_desde"])
        
        if filtros["fecha_hasta"]:
            query += " AND fecha_emision <= ?"
            params.append(filtros["fecha_hasta"])
        
        if filtros["cliente"]:
            query += " AND cliente LIKE ?"
            params.append(f"%{filtros['cliente']}%")
        
        query += " ORDER BY fecha_emision DESC LIMIT 50"
        
        conn, cursor = self.master.conectar_db()
        if not conn:
            return []
        
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            conn.close()
            raise e

    def buscar_en_detalles_con_filtros(self, termino, filtros):
        """Busca en rma_detalles aplicando filtros."""
        query = """SELECT d.id, d.rma_id, d.referencia_articulo, d.cantidad_segun_documento,
                          d.cantidad_entregada, d.estado_producto, d.precio_unitario,
                          m.codigo_rma, m.cliente, m.numero_documento_cliente 
                   FROM rma_detalles d
                   JOIN rma_maestro m ON d.rma_id = m.id
                   WHERE 1=1"""
        params = []
        
        # Filtro de texto general
        if termino:
            query += """ AND (
                m.codigo_rma LIKE ? OR d.referencia_articulo LIKE ? OR d.estado_producto LIKE ?
            )"""
            termino_param = f"%{termino}%"
            params.extend([termino_param] * 3)
        
        # Filtros específicos para productos
        if filtros["estado_producto"]:
            query += " AND d.estado_producto LIKE ?"
            params.append(f"%{filtros['estado_producto']}%")
        
        if filtros["referencia"]:
            query += " AND d.referencia_articulo LIKE ?"
            params.append(f"%{filtros['referencia']}%")
        
        # Filtros relacionados con el expediente padre
        if filtros["estado"]:
            query += " AND m.estado_expediente = ?"
            params.append(filtros["estado"])
        
        if filtros["fecha_desde"]:
            query += " AND m.fecha_emision >= ?"
            params.append(filtros["fecha_desde"])
        
        if filtros["fecha_hasta"]:
            query += " AND m.fecha_emision <= ?"
            params.append(filtros["fecha_hasta"])
        
        if filtros["cliente"]:
            query += " AND m.cliente LIKE ?"
            params.append(f"%{filtros['cliente']}%")
        
        query += " ORDER BY m.codigo_rma DESC LIMIT 50"
        
        conn, cursor = self.master.conectar_db()
        if not conn:
            return []
        
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            conn.close()
            raise e

    def mostrar_resultados_busqueda_avanzada(self, resultados_maestro, resultados_detalles, termino, filtros):
        """Muestra los resultados de la búsqueda avanzada."""
        total_resultados = len(resultados_maestro) + len(resultados_detalles)
        
        # Título de resultados
        titulo_frame = ctk.CTkFrame(self.resultados_frame, fg_color="transparent")
        titulo_frame.pack(fill="x", padx=10, pady=(10,5))
        
        filtros_activos = [k for k, v in filtros.items() if v]
        if termino or filtros_activos:
            criterios = []
            if termino:
                criterios.append(f"Texto: '{termino}'")
            if filtros_activos:
                criterios.append(f"Filtros: {', '.join(filtros_activos)}")
            criterios_text = " | ".join(criterios)
        else:
            criterios_text = "Todos los registros"
        
        ctk.CTkLabel(titulo_frame, 
                    text=f"🔍 Búsqueda Avanzada: {criterios_text}",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        ctk.CTkLabel(titulo_frame, 
                    text=f"({total_resultados} resultados)",
                    font=ctk.CTkFont(size=12), 
                    text_color="gray").pack(side="right")
        
        if total_resultados == 0:
            ctk.CTkLabel(self.resultados_frame, 
                        text="❌ No se encontraron resultados con los criterios especificados",
                        font=ctk.CTkFont(size=13),
                        text_color="orange").pack(pady=20)
            return
        
        # Resultados de expedientes
        if resultados_maestro:
            exp_frame = ctk.CTkFrame(self.resultados_frame)
            exp_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(exp_frame, 
                        text=f"📋 Expedientes ({len(resultados_maestro)} encontrados)",
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=5)
            
            for expediente in resultados_maestro:
                self.crear_resultado_expediente_avanzado(exp_frame, expediente, termino)
        
        # Resultados de productos
        if resultados_detalles:
            prod_frame = ctk.CTkFrame(self.resultados_frame)
            prod_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(prod_frame, 
                        text=f"📦 Productos ({len(resultados_detalles)} encontrados)",
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=5)
            
            for producto in resultados_detalles:
                self.crear_resultado_producto_avanzado(prod_frame, producto, termino)

    def crear_resultado_expediente_avanzado(self, parent, expediente, termino_resaltado):
        """Crea un resultado visual avanzado para expediente."""
        resultado_frame = ctk.CTkFrame(parent)
        resultado_frame.pack(fill="x", padx=10, pady=2)
        
        # Info principal
        info_frame = ctk.CTkFrame(resultado_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # RMA y estado
        header_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        
        rma_texto = f"RMA: {expediente[1]}"  # numero_rma
        ctk.CTkLabel(header_frame, text=rma_texto, 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        
        estado = expediente[8] if expediente[8] else "Sin estado"  # estado_expediente
        color_estado = self.get_color_por_estado(estado)
        ctk.CTkLabel(header_frame, text=f"🏷️ {estado}", 
                    text_color=color_estado, font=ctk.CTkFont(size=11)).pack(side="right")
        
        # Cliente y fecha
        cliente_fecha = f"👤 {expediente[2]} | 📅 {expediente[9]}"  # cliente, fecha_creacion
        ctk.CTkLabel(info_frame, text=cliente_fecha, 
                    font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
        
        # Botón para abrir
        btn_abrir = ctk.CTkButton(resultado_frame, text="📂 Abrir Expediente", 
                                 command=lambda: self.abrir_expediente_desde_busqueda(expediente[1]),
                                 height=25, width=120)
        btn_abrir.pack(side="right", padx=10, pady=5)

    def crear_resultado_producto_avanzado(self, parent, producto, termino_resaltado):
        """Crea un resultado visual avanzado para producto."""
        resultado_frame = ctk.CTkFrame(parent)
        resultado_frame.pack(fill="x", padx=10, pady=2)
        
        # Info principal
        info_frame = ctk.CTkFrame(resultado_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # Referencia y RMA
        header_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        
        ref_texto = f"📦 {producto[2]}"  # referencia_articulo (índice 2)
        ctk.CTkLabel(header_frame, text=ref_texto, 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        
        rma_texto = f"RMA: {producto[7]}"  # codigo_rma (índice 7)
        ctk.CTkLabel(header_frame, text=rma_texto, 
                    font=ctk.CTkFont(size=11), text_color="blue").pack(side="right")
        
        # Estado y cantidades
        estado_prod = producto[5] if producto[5] else "Sin estado"  # estado_producto (índice 5)
        ctk.CTkLabel(info_frame, text=f"🔧 Estado: {estado_prod}", 
                    font=ctk.CTkFont(size=10), text_color="orange").pack(anchor="w")
        
        cant_info = f"📊 Cant. Documento: {producto[3]} | Entregada: {producto[4]}"  # índices 3 y 4
        ctk.CTkLabel(info_frame, text=cant_info, 
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
        
        # Botón para abrir
        btn_abrir = ctk.CTkButton(resultado_frame, text="📂 Ver en Expediente", 
                                 command=lambda: self.abrir_expediente_desde_busqueda(producto[7]),
                                 height=25, width=120)
        btn_abrir.pack(side="right", padx=10, pady=5)

    def validar_fecha(self, fecha_str):
        """Valida formato de fecha YYYY-MM-DD."""
        try:
            datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def abrir_expediente_desde_busqueda(self, numero_rma):
        """Abre un expediente específico desde los resultados de búsqueda."""
        try:
            # Cerrar ventana de búsqueda
            if hasattr(self, 'ventana_busqueda_global') and self.ventana_busqueda_global:
                self.ventana_busqueda_global.destroy()
                self.ventana_busqueda_global = None
            
            # Cambiar al marco de expedientes
            self.mostrar_expedientes()
            
            # Buscar y mostrar el expediente específico
            self.buscar_expediente_especifico(numero_rma)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir expediente: {str(e)}")

    def buscar_expediente_especifico(self, numero_rma):
        """Busca y muestra un expediente específico."""
        try:
            # Limpiar lista actual
            for widget in self.expedientes_frame.winfo_children():
                widget.destroy()
            
            # Buscar expediente
            conn, cursor = self.master.conectar_db()
            if not conn:
                return
            
            try:
                cursor.execute("SELECT * FROM rma_maestro WHERE numero_rma = ?", (numero_rma,))
                expediente = cursor.fetchone()
                
                if expediente:
                    # Mostrar como resultado único
                    resultado_frame = ctk.CTkFrame(self.expedientes_frame)
                    resultado_frame.pack(fill="x", padx=10, pady=5)
                    
                    # Crear botón de expediente con información destacada
                    self.crear_boton_expediente(resultado_frame, expediente, destacado=True)
                    
                    # Mensaje de búsqueda exitosa
                    mensaje_frame = ctk.CTkFrame(self.expedientes_frame)
                    mensaje_frame.pack(fill="x", padx=10, pady=5)
                    ctk.CTkLabel(mensaje_frame, 
                                text=f"✅ Expediente {numero_rma} encontrado desde búsqueda",
                                font=ctk.CTkFont(size=12), 
                                text_color="green").pack(pady=10)
                else:
                    ctk.CTkLabel(self.expedientes_frame, 
                                text=f"❌ No se encontró el expediente {numero_rma}",
                                font=ctk.CTkFont(size=12), 
                                text_color="red").pack(pady=20)
                
                conn.close()
                
            except Exception as e:
                conn.close()
                raise e
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar expediente específico: {str(e)}")
            print(f"Error en buscar_expediente_especifico: {e}")
        
        # Mensaje inicial
        ctk.CTkLabel(self.resultados_frame, 
                    text="👆 Introduce un término de búsqueda arriba para comenzar",
                    font=ctk.CTkFont(size=14),
                    text_color="gray").pack(pady=50)
        
        # Focus en el campo de búsqueda
        self.entry_busqueda_global.focus()

    def ejecutar_busqueda_global(self):
        """Ejecuta la búsqueda global en todos los campos."""
        termino = self.entry_busqueda_global.get().strip()
        
        if not termino:
            self.mostrar_mensaje_busqueda("⚠️ Por favor, introduce un término de búsqueda")
            return
        
        if len(termino) < 2:
            self.mostrar_mensaje_busqueda("⚠️ El término de búsqueda debe tener al menos 2 caracteres")
            return
        
        # Limpiar resultados anteriores
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        
        # Mostrar indicador de carga
        loading_label = ctk.CTkLabel(self.resultados_frame, 
                                   text="🔄 Buscando...", 
                                   font=ctk.CTkFont(size=14))
        loading_label.pack(pady=20)
        self.update()
        
        try:
            # Guardar búsqueda en historial
            self.guardar_busqueda_en_historial(termino)
            self.actualizar_historial_ui()
            
            # Realizar búsqueda
            resultados_expedientes, resultados_productos, resultados_historial, resultados_tareas = self.buscar_en_todos_los_campos(termino)
            
            # Limpiar indicador de carga
            loading_label.destroy()
            
            # Mostrar resultados
            self.mostrar_resultados_busqueda(resultados_expedientes, resultados_productos, resultados_historial, resultados_tareas, termino)
            
        except Exception as e:
            loading_label.destroy()
            self.mostrar_mensaje_busqueda(f"❌ Error en la búsqueda: {str(e)}")

    def buscar_en_todos_los_campos(self, termino):
        """Busca el término en todos los campos de las tablas principales."""
        conn, cursor = self.master.conectar_db()
        if not conn:
            return [], []
        
        cursor = conn.cursor()
        termino_like = f"%{termino}%"
        
        try:
            # Búsqueda en rma_maestro (expedientes)
            # Obtenemos primero todas las columnas disponibles
            cursor.execute("PRAGMA table_info(rma_maestro)")
            columnas_maestro = [col[1] for col in cursor.fetchall()]
            
            # Construir query dinámicamente para todos los campos de texto
            campos_busqueda_maestro = []
            params_maestro = []
            
            for col in columnas_maestro:
                if col.lower() not in ['id']:  # Excluir campos numéricos ID
                    campos_busqueda_maestro.append(f"{col} LIKE ?")
                    params_maestro.append(termino_like)
            
            if campos_busqueda_maestro:
                sql_maestro = f"""
                SELECT id, codigo_rma, cliente, numero_documento_cliente, estado, fecha_emision,
                       rma_proveedor, motivo, fecha_gestion
                FROM rma_maestro 
                WHERE {' OR '.join(campos_busqueda_maestro)}
                ORDER BY fecha_emision DESC
                LIMIT 100
                """
                cursor.execute(sql_maestro, params_maestro)
                resultados_expedientes = cursor.fetchall()
            else:
                resultados_expedientes = []
            
            # Búsqueda en rma_detalles (productos)
            cursor.execute("PRAGMA table_info(rma_detalles)")
            columnas_detalles = [col[1] for col in cursor.fetchall()]
            
            campos_busqueda_detalles = []
            params_detalles = []
            
            for col in columnas_detalles:
                if col.lower() not in ['id', 'rma_id', 'cantidad_segun_documento', 'cantidad_entregada', 'precio_unitario']:
                    campos_busqueda_detalles.append(f"d.{col} LIKE ?")
                    params_detalles.append(termino_like)
            
            if campos_busqueda_detalles:
                sql_detalles = f"""
                SELECT DISTINCT d.id, d.rma_id, d.referencia_articulo, d.cantidad_segun_documento,
                       d.cantidad_entregada, d.estado_producto, d.precio_unitario, m.codigo_rma, m.cliente
                FROM rma_detalles d
                JOIN rma_maestro m ON d.rma_id = m.id
                WHERE {' OR '.join(campos_busqueda_detalles)}
                ORDER BY m.fecha_emision DESC
                LIMIT 100
                """
                cursor.execute(sql_detalles, params_detalles)
                resultados_productos = cursor.fetchall()
            else:
                resultados_productos = []
            
            # Búsqueda en historial (opcional si la tabla existe)
            resultados_historial = []
            try:
                sql_historial = """
                SELECT DISTINCT h.rma_id, h.fecha_cambio, h.descripcion_cambio, h.usuario, 
                       m.codigo_rma, m.cliente
                FROM rma_historial h
                JOIN rma_maestro m ON h.rma_id = m.id
                WHERE h.descripcion_cambio LIKE ? OR h.usuario LIKE ?
                ORDER BY h.fecha_cambio DESC
                LIMIT 100
                """
                cursor.execute(sql_historial, (termino_like, termino_like))
                resultados_historial = cursor.fetchall()
            except Exception:
                pass  # La tabla rma_historial puede no existir
            
            # Búsqueda en tareas
            resultados_tareas = []
            try:
                sql_tareas = """
                SELECT DISTINCT t.id, t.codigo_rma, t.titulo, t.descripcion, t.estado,
                       t.fecha_vencimiento, t.creado_por, m.id as rma_id, m.cliente
                FROM tareas t
                LEFT JOIN rma_maestro m ON t.codigo_rma = m.codigo_rma
                WHERE t.titulo LIKE ? OR t.descripcion LIKE ? OR t.estado LIKE ? OR t.creado_por LIKE ?
                ORDER BY t.fecha_vencimiento IS NULL, t.fecha_vencimiento DESC
                LIMIT 100
                """
                cursor.execute(sql_tareas, (termino_like, termino_like, termino_like, termino_like))
                resultados_tareas = cursor.fetchall()
            except Exception:
                pass  # Error en búsqueda de tareas
            
            conn.close()
            return resultados_expedientes, resultados_productos, resultados_historial, resultados_tareas
            
        except Exception as e:
            conn.close()
            raise e

    def mostrar_resultados_busqueda(self, expedientes, productos, historial, tareas, termino):
        """Muestra los resultados de la búsqueda de forma organizada."""
        total_resultados = len(expedientes) + len(productos) + len(historial) + len(tareas)
        
        if total_resultados == 0:
            self.mostrar_mensaje_busqueda(f"🔍 No se encontraron resultados para '{termino}'")
            return
        
        # Header de resultados
        header_resultados = ctk.CTkLabel(self.resultados_frame,
                                       text=f"📊 Se encontraron {total_resultados} resultados para '{termino}'",
                                       font=ctk.CTkFont(size=16, weight="bold"))
        header_resultados.pack(pady=10, anchor="w")
        
        # Mostrar expedientes
        if expedientes:
            self.mostrar_seccion_expedientes(expedientes)
        
        # Mostrar productos
        if productos:
            self.mostrar_seccion_productos(productos)
        
        # Mostrar historial
        if historial:
            self.mostrar_seccion_historial(historial)
        
        # Mostrar tareas
        if tareas:
            self.mostrar_seccion_tareas(tareas)

    def mostrar_seccion_expedientes(self, expedientes):
        """Muestra la sección de expedientes encontrados."""
        seccion_frame = ctk.CTkFrame(self.resultados_frame)
        seccion_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(seccion_frame, 
                    text=f"📋 EXPEDIENTES ENCONTRADOS ({len(expedientes)})",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        for exp in expedientes:
            exp_id, codigo_rma, cliente, num_doc, estado, fecha, rma_prov, motivo, fecha_gestion = exp
            
            item_frame = ctk.CTkFrame(seccion_frame)
            item_frame.pack(fill="x", padx=10, pady=2)
            
            # Información principal
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=10, pady=5)
            
            # Línea 1: Código RMA y fecha
            linea1 = ctk.CTkFrame(info_frame, fg_color="transparent")
            linea1.pack(fill="x")
            
            ctk.CTkLabel(linea1, text=f"📋 {codigo_rma or 'Sin código'}", 
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(linea1, text=f"📅 {fecha or 'Sin fecha'}", 
                        text_color="gray").pack(side="right")
            
            # Línea 2: Cliente y documento
            if cliente or num_doc:
                linea2 = ctk.CTkLabel(info_frame, 
                                    text=f"👤 {cliente or 'Sin cliente'} | 📄 {num_doc or 'Sin doc.'}",
                                    text_color="gray")
                linea2.pack(anchor="w")
            
            # Línea 3: Estado
            if estado:
                color_estado = self.get_color_por_estado(estado)
                ctk.CTkLabel(info_frame, text=f"🏷️ {estado}", 
                           text_color=color_estado).pack(anchor="w")
            
            # Botón para abrir expediente
            btn_abrir = ctk.CTkButton(item_frame, text="📖 Abrir Expediente", 
                                     command=lambda eid=exp_id: self._abrir_editor_rma(rma_id=eid),
                                     width=150, height=30)
            btn_abrir.pack(side="right", padx=10, pady=5)

    def mostrar_seccion_productos(self, productos):
        """Muestra la sección de productos encontrados."""
        seccion_frame = ctk.CTkFrame(self.resultados_frame)
        seccion_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(seccion_frame, 
                    text=f"📦 PRODUCTOS ENCONTRADOS ({len(productos)})",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        for prod in productos:
            prod_id, rma_id, ref_articulo, cantidad_doc, cantidad_entregada, estado_prod, precio_unit, codigo_rma, cliente = prod
            
            item_frame = ctk.CTkFrame(seccion_frame)
            item_frame.pack(fill="x", padx=10, pady=2)
            
            # Información principal
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=10, pady=5)
            
            # Línea 1: Referencia y precio
            linea1 = ctk.CTkFrame(info_frame, fg_color="transparent")
            linea1.pack(fill="x")
            
            ctk.CTkLabel(linea1, text=f"📦 {ref_articulo or 'Sin referencia'}", 
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
            if precio_unit:
                ctk.CTkLabel(linea1, text=f"💰 {precio_unit}€", 
                           text_color="blue").pack(side="right")
            
            # Línea 2: Cantidades
            if cantidad_doc or cantidad_entregada:
                ctk.CTkLabel(info_frame, text=f"� Doc: {cantidad_doc or 0} | Entregada: {cantidad_entregada or 0}", 
                           text_color="gray").pack(anchor="w")
            
            # Línea 3: Expediente asociado
            ctk.CTkLabel(info_frame, text=f"📋 Expediente: {codigo_rma} | 👤 {cliente or 'Sin cliente'}", 
                        text_color="gray").pack(anchor="w")
            
            # Línea 4: Estado del producto
            if estado_prod:
                color_estado = {"Nuevo": "green", "Usado": "orange", "Defectuoso": "red"}.get(estado_prod, "gray")
                ctk.CTkLabel(info_frame, text=f"⚪ {estado_prod}", 
                           text_color=color_estado).pack(anchor="w")
            
            # Botón para abrir expediente
            btn_abrir = ctk.CTkButton(item_frame, text="📖 Ver en Expediente", 
                                     command=lambda rid=rma_id: self._abrir_editor_rma(rma_id=rid),
                                     width=150, height=30)
            btn_abrir.pack(side="right", padx=10, pady=5)

    def mostrar_seccion_historial(self, historial):
        """Muestra la sección de historial encontrado."""
        seccion_frame = ctk.CTkFrame(self.resultados_frame)
        seccion_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(seccion_frame, 
                    text=f"📜 HISTORIAL ENCONTRADO ({len(historial)})",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        for hist in historial:
            # Columnas: rma_id, fecha_cambio, descripcion_cambio, usuario, codigo_rma, cliente
            rma_id, fecha_cambio, descripcion_cambio, usuario, codigo_rma, cliente = hist
            
            item_frame = ctk.CTkFrame(seccion_frame)
            item_frame.pack(fill="x", padx=10, pady=2)
            
            # Información principal
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=10, pady=5)
            
            # Línea 1: Fecha y usuario
            linea1 = ctk.CTkFrame(info_frame, fg_color="transparent")
            linea1.pack(fill="x")
            
            ctk.CTkLabel(linea1, text=f"📅 {fecha_cambio or 'Sin fecha'}", 
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(linea1, text=f"👨 {usuario or 'Sin usuario'}", 
                        text_color="blue").pack(side="right")
            
            # Línea 2: Descripción del cambio
            desc_text = (descripcion_cambio[:100] + "...") if descripcion_cambio and len(descripcion_cambio) > 100 else (descripcion_cambio or "Sin descripción")
            ctk.CTkLabel(info_frame, text=desc_text, text_color="gray").pack(anchor="w")
            
            # Línea 3: Expediente
            ctk.CTkLabel(info_frame, 
                        text=f"📋 {codigo_rma or 'Sin código'} | 👤 Cliente: {cliente or 'Sin cliente'}",
                        text_color="gray").pack(anchor="w")
            
            # Botón para abrir expediente
            btn_abrir = ctk.CTkButton(item_frame, text="📖 Ver Expediente", 
                                     command=lambda rid=rma_id: self._abrir_editor_rma(rma_id=rid),
                                     width=150, height=30)
            btn_abrir.pack(side="right", padx=10, pady=5)

    def mostrar_seccion_tareas(self, tareas):
        """Muestra la sección de tareas encontradas."""
        seccion_frame = ctk.CTkFrame(self.resultados_frame)
        seccion_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(seccion_frame, 
                    text=f"✅ TAREAS ENCONTRADAS ({len(tareas)})",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        for tarea in tareas:
            # Columnas: id, codigo_rma, titulo, descripcion, estado, fecha_vencimiento, creado_por, rma_id, cliente
            tarea_id, codigo_rma_tarea, titulo, descripcion, estado, fecha_vencimiento, creado_por, rma_id, cliente = tarea
            
            item_frame = ctk.CTkFrame(seccion_frame)
            item_frame.pack(fill="x", padx=10, pady=2)
            
            # Información principal
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=10, pady=5)
            
            # Línea 1: Título de la tarea
            linea1 = ctk.CTkFrame(info_frame, fg_color="transparent")
            linea1.pack(fill="x")
            
            ctk.CTkLabel(linea1, text=f"📝 {titulo or 'Sin título'}"[:60] + ("..." if titulo and len(titulo) > 60 else ""),
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            # Línea 2: Descripción
            if descripcion:
                desc_text = (descripcion[:80] + "...") if len(descripcion) > 80 else descripcion
                ctk.CTkLabel(info_frame, text=desc_text, text_color="gray").pack(anchor="w")
            
            # Línea 3: Estado y fecha de vencimiento
            color_estado = {"Pendiente": "orange", "En Progreso": "blue", "Completada": "green", "Cancelada": "red"}.get(estado or "", "gray")
            estado_text = f"🏷️ Estado: {estado or 'Sin estado'}"
            if fecha_vencimiento:
                estado_text += f" | ⏰ Vence: {fecha_vencimiento}"
            ctk.CTkLabel(info_frame, text=estado_text, text_color=color_estado).pack(anchor="w")
            
            # Línea 4: Creado por
            if creado_por:
                ctk.CTkLabel(info_frame, text=f"👨 Creado por: {creado_por}", 
                            text_color="gray").pack(anchor="w")
            
            # Línea 5: Expediente asociado
            if codigo_rma_tarea:
                ctk.CTkLabel(info_frame, text=f"📋 Expediente: {codigo_rma_tarea} | 👤 {cliente or 'Sin cliente'}", 
                            text_color="gray").pack(anchor="w")
            
            # Botón para abrir expediente
            if rma_id:
                btn_abrir = ctk.CTkButton(item_frame, text="📖 Ver Expediente", 
                                         command=lambda rid=rma_id: self._abrir_editor_rma(rma_id=rid),
                                         width=150, height=30)
                btn_abrir.pack(side="right", padx=10, pady=5)

    def mostrar_mensaje_busqueda(self, mensaje):
        """Muestra un mensaje en el área de resultados."""
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self.resultados_frame, text=mensaje, 
                    font=ctk.CTkFont(size=14),
                    text_color="gray").pack(pady=50)

    def limpiar_busqueda_global(self):
        """Limpia el campo de búsqueda y resultados."""
        self.entry_busqueda_global.delete(0, 'end')
        self.mostrar_mensaje_busqueda("👆 Introduce un término de búsqueda arriba para comenzar")
        self.entry_busqueda_global.focus()

    def test_conexion_busqueda(self):
        """Prueba rápida de la conexión para búsqueda."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                return False
            
            cursor = conn.cursor()
            # Prueba simple: obtener count de expedientes
            cursor.execute("SELECT COUNT(*) FROM rma_maestro")
            count = cursor.fetchone()[0]
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error de conexión en búsqueda: {e}")
            return False
