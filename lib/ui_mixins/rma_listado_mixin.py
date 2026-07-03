"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class RmaListadoMixin:
    def obtener_quincenas_futuras(self):
        """Genera las quincenas (Q1/Q2) para los próximos 12 meses."""
        hoy = datetime.date.today()
        quincenas = []
        for i in range(12):
            mes = hoy.month + i
            anio = hoy.year + (mes - 1) // 12
            mes = (mes - 1) % 12 + 1
            
            anio_str = str(anio)[2:]
            mes_str = str(mes).zfill(2)
            
            quincenas.append(f"Q1-{mes_str}-{anio_str}")
            quincenas.append(f"Q2-{mes_str}-{anio_str}")
        return quincenas

    def obtener_siguiente_rma(self):
        """Calcula el siguiente código RMA para mostrar como número temporal (Ej: RMA25001)."""
        conn, cursor = self.master.conectar_db()
        if not conn: return "ERROR-DB"

        cursor = conn.cursor()
        
        anio_actual_str = str(datetime.datetime.now().year)[2:]
        prefijo_busqueda = f"RMA{anio_actual_str}%" 
        
        cursor.execute("""
            SELECT codigo_rma FROM rma_maestro 
            WHERE codigo_rma LIKE ? 
            ORDER BY id DESC 
            LIMIT 1
        """, (prefijo_busqueda,))
        
        ultimo_rma = cursor.fetchone()
        siguiente_numero = 1
        
        if ultimo_rma:
            numero_str = ultimo_rma[0].replace(f"RMA{anio_actual_str}", "")
            try:
                siguiente_numero = int(numero_str) + 1
            except ValueError:
                siguiente_numero = 1
        
        codigo_numerico = str(siguiente_numero).zfill(3)
        conn.close()
        
        return f"RMA{anio_actual_str}{codigo_numerico}"

    def generar_codigo_rma_final(self, cursor):
        """
        Genera y asigna el código RMA definitivo dentro de una transacción.
        Esta función debe ejecutarse dentro de una transacción activa.
        """
        anio_actual_str = str(datetime.datetime.now().year)[2:]
        prefijo_busqueda = f"RMA{anio_actual_str}%" 
        
        # Buscar el último número asignado en la misma transacción
        cursor.execute("""
            SELECT codigo_rma FROM rma_maestro 
            WHERE codigo_rma LIKE ? 
            ORDER BY id DESC 
            LIMIT 1
        """, (prefijo_busqueda,))
        
        ultimo_rma = cursor.fetchone()
        siguiente_numero = 1
        
        if ultimo_rma:
            numero_str = ultimo_rma[0].replace(f"RMA{anio_actual_str}", "")
            try:
                siguiente_numero = int(numero_str) + 1
            except ValueError:
                siguiente_numero = 1
        
        codigo_numerico = str(siguiente_numero).zfill(3)
        return f"RMA{anio_actual_str}{codigo_numerico}"

    def mostrar_lista_rma(self):
        """Muestra el listado completo de RMAs, filtros y el dashboard de estadísticas."""
        self.limpiar_contenido()
        
        # Configurar layout principal con dos columnas
        self.content_frame.grid_columnconfigure(0, weight=3, minsize=800)  # Lista principal
        self.content_frame.grid_columnconfigure(1, weight=0, minsize=200, uniform="dashboard")  # Dashboard (ancho fijo absoluto)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # === COLUMNA IZQUIERDA: LISTA Y FILTROS ===
        lista_column = ctk.CTkFrame(self.content_frame)
        lista_column.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # Configurar expansión para la columna de lista
        lista_column.grid_rowconfigure(0, weight=0)  # Título
        lista_column.grid_rowconfigure(1, weight=0)  # Filtros  
        lista_column.grid_rowconfigure(2, weight=1)  # Listado
        lista_column.grid_rowconfigure(3, weight=0)  # Paginación
        lista_column.grid_columnconfigure(0, weight=1)

        # 1. Título y Botón Crear
        title_frame = ctk.CTkFrame(lista_column, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_frame, text="LISTADO DE EXPEDIENTES", 
                    font=ctk.CTkFont(family="Verdana", size=20, weight="bold")).grid(row=0, column=0, sticky="w")
        
        # Botón Crear Nuevo RMA
        try:
            btn_bg = None
            if hasattr(self, 'sidebar_frame') and hasattr(self.sidebar_frame, 'cget'):
                btn_bg = self.sidebar_frame.cget("fg_color")

            ctk.CTkButton(title_frame,
                          text="",
                          image=(self.icon_mas or self.icon_mas),
                          width=36,
                          height=36,
                          fg_color=(btn_bg if btn_bg is not None else None),
                          hover_color=(btn_bg if btn_bg is not None else None),
                          command=lambda: self._abrir_editor_rma(rma_id=None)).grid(row=0, column=1, padx=(20, 0), sticky="e")
            try:
                Tooltip(title_frame.winfo_children()[-1], "Crear nuevo RMA")
            except Exception:
                pass
        except Exception:
            ctk.CTkButton(title_frame,
                          text="➕ Crear Nuevo RMA",
                          command=lambda: self._abrir_editor_rma(rma_id=None)).grid(row=0, column=1, padx=(20, 0), sticky="e")

        # 2. Panel de Búsqueda y Filtros
        filtro_frame = ctk.CTkFrame(lista_column, fg_color="transparent")
        filtro_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # Búsqueda por texto
        ctk.CTkLabel(filtro_frame, text="Buscar:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.entry_busqueda = ctk.CTkEntry(filtro_frame, placeholder_text="Código RMA, Cliente o Doc.", width=250)
        self.entry_busqueda.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        # Bind para ejecutar búsqueda con Enter
        self.entry_busqueda.bind("<Return>", lambda e: self.aplicar_filtros_rma())
        
        # Filtro por Estado
        estados_posibles = self.OPCIONES.get("Estado", ["Todos"])
        if "Todos" not in estados_posibles:
            estados_posibles.insert(0, "Todos")
        if 'Exportado' not in estados_posibles:
            estados_posibles.append('Exportado')
            
        ctk.CTkLabel(filtro_frame, text="Estado:").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        self.filtro_estado = ctk.CTkOptionMenu(filtro_frame, 
                                               values=estados_posibles, 
                                               width=120)
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=0, column=3, padx=10, pady=5, sticky="w")
        
        # Filtro por Año
        ctk.CTkLabel(filtro_frame, text="Año:").grid(row=0, column=4, padx=(20, 5), pady=5, sticky="w")
        # Inicializar con el año actual, se actualizará dinámicamente en cargar_lista_rma
        año_actual = str(datetime.datetime.now().year)
        self.filtro_año = ctk.CTkOptionMenu(filtro_frame, 
                                            values=[año_actual], 
                                            width=80)
        self.filtro_año.set(año_actual)
        self.filtro_año.grid(row=0, column=5, padx=10, pady=5, sticky="w")
        
        # Botón de Aplicar Filtro
        btn_aplicar_filtro = ctk.CTkButton(filtro_frame,
                                           text="🔍 Aplicar Filtros", 
                                           command=self.aplicar_filtros_rma)
        btn_aplicar_filtro.grid(row=0, column=6, padx=(20, 0), pady=5, sticky="w")
        
        filtro_frame.grid_columnconfigure(1, weight=1)

        # 3. Listado de RMAs
        self.lista_rma_frame = ctk.CTkScrollableFrame(lista_column, 
                                                     label_text="Pulse F5 para actualizar el listado ; Pinche dos veces sobre el expediente para abrirlo.")
        self.lista_rma_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.lista_rma_frame.grid_columnconfigure(0, weight=1)
        
        # 4. Controles de Paginación
        paginacion_frame = ctk.CTkFrame(lista_column, height=40)
        paginacion_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        paginacion_frame.grid_propagate(False)
        
        self.btn_anterior_lista = ctk.CTkButton(paginacion_frame, text="◀ Anterior", width=100, 
                                               command=self.ir_pagina_anterior_lista)
        self.btn_anterior_lista.pack(side="left", padx=10, pady=5)
        
        self.lbl_pagina_lista = ctk.CTkLabel(paginacion_frame, text="Página 1 de 1")
        self.lbl_pagina_lista.pack(side="left", padx=20)
        
        self.btn_siguiente_lista = ctk.CTkButton(paginacion_frame, text="Siguiente ▶", width=100,
                                                command=self.ir_pagina_siguiente_lista)
        self.btn_siguiente_lista.pack(side="left", padx=10, pady=5)
        
        # Selector de elementos por página
        ctk.CTkLabel(paginacion_frame, text="Elementos por página:").pack(side="left", padx=(40, 5))
        self.elementos_menu_lista = ctk.CTkOptionMenu(paginacion_frame, 
                                                      values=["10", "25", "50", "100", "200"], 
                                                      width=80,
                                                      command=self.cambiar_elementos_por_pagina_lista)
        self.elementos_menu_lista.set("25")
        self.elementos_menu_lista.pack(side="left", padx=5)
        
        # === COLUMNA DERECHA: DASHBOARD ===
        dashboard_column = ctk.CTkFrame(self.content_frame, width=200, fg_color=("#f0f0f0", "#2b2b2b"))
        dashboard_column.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        dashboard_column.grid_propagate(False)  # Mantener el ancho fijo
        
        # Header del dashboard
        dashboard_header = ctk.CTkFrame(dashboard_column, fg_color="transparent")
        dashboard_header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(dashboard_header, text="📊 Estadísticas", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        # Selector de año
        año_frame = ctk.CTkFrame(dashboard_column, fg_color="transparent")
        año_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(año_frame, text="Año:", font=ctk.CTkFont(size=11)).pack(side="left")
        
        años_disponibles = [str(año) for año in range(2020, datetime.datetime.now().year + 2)]
        self.combo_año_dashboard = ctk.CTkOptionMenu(año_frame, values=años_disponibles, 
                                                    command=self.actualizar_dashboard,
                                                    width=60)
        self.combo_año_dashboard.set(str(datetime.datetime.now().year))
        self.combo_año_dashboard.pack(side="right")
        
        # Selector de período para artículos problemáticos
        periodo_frame = ctk.CTkFrame(dashboard_column, fg_color="transparent")
        periodo_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(periodo_frame, text="Período:", font=ctk.CTkFont(size=11)).pack(side="left")
        
        self.combo_periodo = ctk.CTkOptionMenu(periodo_frame, 
                                             values=["Anual", "Semestral", "Trimestral"],
                                             command=self.actualizar_dashboard,
                                             width=80)
        self.combo_periodo.set("Anual")
        self.combo_periodo.pack(side="right")
        
        # Frame para las estadísticas
        self.stats_frame = ctk.CTkFrame(dashboard_column)
        self.stats_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.stats_frame.pack_propagate(True)  # Permitir que el contenido se ajuste verticalmente

        # Cargar las estadísticas ANTES de construir el panel de tareas/calendario:
        # stats_frame debe tener ya su tamaño final para que el resto de widgets de la
        # columna se distribuyan bien (si se rellena después, algunos temas de CustomTkinter
        # no recolocan a los hermanos ya empaquetados y queda un hueco en blanco).
        self.actualizar_dashboard()  # Cargar estadísticas del dashboard

        # Panel de tareas asignadas y calendario mensual (configurable desde Ajustes de Usuario)
        self.dashboard_column = dashboard_column
        self.crear_widget_tareas_dashboard(dashboard_column)

        # Cargar datos iniciales - con filtro del año actual por defecto para optimizar rendimiento
        año_actual = str(datetime.datetime.now().year)
        self.cargar_lista_rma("", "Todos", año_actual)  # Cargar solo expedientes del año actual

    def cargar_lista_rma(self, texto_busqueda="", estado_filtro="Todos", año_filtro=None):
        """
        Carga los estados únicos de la DB para el filtro, y luego carga los RMA 
        desde la DB aplicando los filtros (texto, estado, año).
        """
        
        # Si no se especifica año, usar el año actual por defecto
        if año_filtro is None:
            año_filtro = str(datetime.datetime.now().year)
        
        # Limpiar el frame (siempre)
        for widget in self.lista_rma_frame.winfo_children():
            widget.destroy()
        
        # Resetear selección
        self.fila_seleccionada_rma = None
        self.frames_seleccionados_rma = []

        conn, cursor = self.master.conectar_db()
        if not conn: 
            ctk.CTkLabel(self.lista_rma_frame, text="Error de conexión a la base de datos.").grid(row=0, column=0, padx=10, pady=10)
            return
        cursor = conn.cursor()
        
        try:
            # 1. OBTENER ESTADOS ÚNICOS PARA EL FILTRO - CON CACHÉ
            # Solo hacemos esto si el filtro_estado ya existe (es decir, en mostrar_lista_rma ya se creó la interfaz)
            if hasattr(self, 'filtro_estado'):
                try:
                    # Usar caché para estados (se actualiza cada 5 minutos o al invalidar)
                    def query_estados():
                        cursor.execute("SELECT DISTINCT estado FROM rma_maestro WHERE estado IS NOT NULL AND estado != '' ORDER BY estado ASC")
                        return [fila[0] for fila in cursor.fetchall()]
                    
                    estados_db = _get_cached_query('estados_rma', query_estados)
                    
                    # Crear la lista final de opciones: "Todos" + estados únicos de la DB
                    estados_posibles = ["Todos"] + estados_db
                    
                    # Actualizar el OptionMenu (sin cambiar la selección actual si es válida)
                    seleccion_actual = self.filtro_estado.get()
                    self.filtro_estado.configure(values=estados_posibles)
                    
                    # Mantener la selección actual si todavía existe, si no, poner "Todos"
                    if seleccion_actual in estados_posibles:
                        self.filtro_estado.set(seleccion_actual)
                    else:
                        self.filtro_estado.set("Todos")
                except Exception as e:
                    print(f"Error al cargar estados para filtro: {e}")
                    # Continuar con valores por defecto
                    if hasattr(self, 'filtro_estado'):
                        self.filtro_estado.configure(values=["Todos"])
                        self.filtro_estado.set("Todos")
            
            # 1.5. OBTENER AÑOS DISPONIBLES PARA EL FILTRO - CON CACHÉ
            if hasattr(self, 'filtro_año'):
                try:
                    # Usar caché para años (se actualiza cada 5 minutos o al invalidar)
                    def query_años():
                        cursor.execute("""
                            SELECT DISTINCT SUBSTR(codigo_rma, 4, 2) as año_corto 
                            FROM rma_maestro 
                            WHERE codigo_rma LIKE 'RMA%' 
                            ORDER BY año_corto DESC
                        """)
                        años_cortos = [fila[0] for fila in cursor.fetchall()]
                        # Convertir años cortos (25, 24, 23...) a años completos (2025, 2024, 2023...)
                        años_completos = []
                        for año_corto in años_cortos:
                            try:
                                año_int = int(año_corto)
                                # Asumimos que años 00-30 son 2000-2030, y 31-99 son 1931-1999
                                if año_int <= 30:
                                    año_completo = 2000 + año_int
                                else:
                                    año_completo = 1900 + año_int
                                años_completos.append(str(año_completo))
                            except ValueError:
                                continue
                        return años_completos if años_completos else [str(datetime.datetime.now().year)]
                    
                    años_db = _get_cached_query('años_rma', query_años)
                    
                    # Actualizar el OptionMenu de años (sin cambiar la selección actual si es válida)
                    seleccion_actual_año = self.filtro_año.get()
                    self.filtro_año.configure(values=años_db)
                    
                    # Mantener la selección actual si todavía existe, si no, poner el año actual
                    if seleccion_actual_año in años_db:
                        self.filtro_año.set(seleccion_actual_año)
                    else:
                        # Si no existe la selección actual, usar el año actual o el más reciente
                        año_actual = str(datetime.datetime.now().year)
                        if año_actual in años_db:
                            self.filtro_año.set(año_actual)
                        elif años_db:
                            self.filtro_año.set(años_db[0])  # El más reciente
                        else:
                            self.filtro_año.set(año_actual)
                            
                except Exception as e:
                    print(f"Error al cargar años para filtro: {e}")
                    # Continuar con valores por defecto
                    año_actual = str(datetime.datetime.now().year)
                    if hasattr(self, 'filtro_año'):
                        self.filtro_año.configure(values=[año_actual])
                        self.filtro_año.set(año_actual)
                    
                # 2. CARGAR LOS REGISTROS APLICANDO LOS FILTROS
                # (Aquí mantenemos tu lógica SQL que ya estaba funcionando)
            
                sql = (
                    "SELECT m.id, m.codigo_rma, m.cliente, m.numero_documento_cliente, "
                    "m.fecha_emision, m.estado, m.fecha_autorizacion, m.fecha_recepcion, "
                    "m.fecha_proceso, m.fecha_gestion, m.numero_albaran_reposicion, "
                    "m.numero_factura_abono, m.fecha_para_factura, "
                    "COALESCE(m.fecha_entregado_contabilidad, '') AS fecha_entregado_contabilidad, "
                    "(SELECT MIN(t.fecha_vencimiento) FROM tareas t "
                    " WHERE t.codigo_rma = m.codigo_rma "
                    " AND t.estado NOT IN ('Completada', 'Cancelada') "
                    " AND t.fecha_vencimiento IS NOT NULL AND t.fecha_vencimiento != '') "
                    "AS proxima_tarea_vencimiento, "
                    "(SELECT t2.titulo FROM tareas t2 "
                    " WHERE t2.codigo_rma = m.codigo_rma "
                    " AND t2.estado NOT IN ('Completada', 'Cancelada') "
                    " AND t2.fecha_vencimiento IS NOT NULL AND t2.fecha_vencimiento != '' "
                    " ORDER BY t2.fecha_vencimiento ASC LIMIT 1) "
                    "AS proxima_tarea_titulo "
                    "FROM rma_maestro m WHERE 1=1"
                )
                params = []
            
                # Aplicar filtro de ESTADO
                estado_filtro_actual = self.filtro_estado.get() # Usamos el valor que se ha configurado
                if estado_filtro_actual and estado_filtro_actual != "Todos":
                    sql += " AND estado = ?"
                    params.append(estado_filtro_actual)
            
                # Aplicar filtro de AÑO (solo si NO hay búsqueda de texto)
                if not texto_busqueda:
                    año_filtro_actual = self.filtro_año.get() if hasattr(self, 'filtro_año') else año_filtro
                    if año_filtro_actual:
                        # Extraer los últimos 2 dígitos del año para el formato RMA (ej: 2025 -> "25")
                        try:
                            año_corto = str(año_filtro_actual)[-2:]
                            sql += " AND codigo_rma LIKE ?"
                            params.append(f"RMA{año_corto}%")
                        except Exception as e:
                            print(f"Error aplicando filtro de año: {e}")
                
                # Aplicar filtro de BÚSQUEDA por texto
                if texto_busqueda:
                    busqueda_like = f"%{texto_busqueda}%"
                    sql += " AND (codigo_rma LIKE ? OR cliente LIKE ? OR numero_documento_cliente LIKE ?)"
                    params.append(busqueda_like)
                    params.append(busqueda_like)
                    params.append(busqueda_like) 

                # Ordenar y Ejecutar
                sql += " ORDER BY id DESC"
                try:
                    cursor.execute(sql, tuple(params))
                    registros_todos = cursor.fetchall()
                    
                    # Aplicar paginación
                    total_registros = len(registros_todos)
                    inicio = self.pagina_actual_lista * self.elementos_por_pagina_lista
                    fin = min(inicio + self.elementos_por_pagina_lista, total_registros)
                    registros = registros_todos[inicio:fin]
                    
                    # Calcular total de páginas
                    total_paginas = (total_registros + self.elementos_por_pagina_lista - 1) // self.elementos_por_pagina_lista
                    if total_paginas == 0:
                        total_paginas = 1
                    
                    # Actualizar indicador de página
                    if hasattr(self, 'lbl_pagina_lista'):
                        self.lbl_pagina_lista.configure(
                            text=f"Página {self.pagina_actual_lista + 1} de {total_paginas} ({total_registros} registros)"
                        )
                    
                    # Habilitar/deshabilitar botones de navegación
                    if hasattr(self, 'btn_anterior_lista'):
                        if self.pagina_actual_lista > 0:
                            self.btn_anterior_lista.configure(state="normal")
                        else:
                            self.btn_anterior_lista.configure(state="disabled")
                    
                    if hasattr(self, 'btn_siguiente_lista'):
                        if self.pagina_actual_lista < total_paginas - 1:
                            self.btn_siguiente_lista.configure(state="normal")
                        else:
                            self.btn_siguiente_lista.configure(state="disabled")
                    
                except Exception as e:
                    print(f"Error ejecutando query principal: {e}")
                    print(f"SQL: {sql}")
                    print(f"Params: {params}")
                    raise
            
                # Obtener asociaciones en una sola consulta optimizada (bidireccional)
                asociaciones_dict = {}
                try:
                    cursor.execute("""
                        SELECT a.rma_id as rma_principal, r.codigo_rma
                        FROM rma_asociaciones a
                        INNER JOIN rma_maestro r ON r.id = a.rma_asociado_id
                        UNION
                        SELECT a.rma_asociado_id as rma_principal, r.codigo_rma
                        FROM rma_asociaciones a
                        INNER JOIN rma_maestro r ON r.id = a.rma_id
                    """)
                    
                    for row in cursor.fetchall():
                        rma_principal_id = row[0]
                        codigo_asociado = row[1]
                        if rma_principal_id not in asociaciones_dict:
                            asociaciones_dict[rma_principal_id] = []
                        asociaciones_dict[rma_principal_id].append(codigo_asociado)
                except Exception as e:
                    print(f"Error cargando asociaciones: {e}")
                    asociaciones_dict = {}
                
                conn.close()

                # 3. Dibujar la tabla de resultados (Encabezados y Registros)
            
                # ... (código para dibujar encabezados y la tabla de registros, sigue igual) ...
            
                # Encabezados
                header_font = ctk.CTkFont(weight="bold")
                # Configurar anchos de columnas para mejor distribución
                self.lista_rma_frame.grid_columnconfigure(0, weight=0, minsize=100)  # CÓDIGO RMA
                self.lista_rma_frame.grid_columnconfigure(1, weight=0)               # ICONOS (sin minsize)
                self.lista_rma_frame.grid_columnconfigure(2, weight=2, minsize=150)  # CLIENTE (reducido -26px para 4 iconos)
                self.lista_rma_frame.grid_columnconfigure(3, weight=1, minsize=150)  # DOCUMENTO
                self.lista_rma_frame.grid_columnconfigure(4, weight=0, minsize=130)  # ÚLTIMA ACTIVIDAD
                self.lista_rma_frame.grid_columnconfigure(5, weight=1, minsize=180)  # ESTADO (ampliado)
                self.lista_rma_frame.grid_columnconfigure(6, weight=0, minsize=110)  # FECHA EMISIÓN
            
                ctk.CTkLabel(self.lista_rma_frame, text="CÓDIGO RMA", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
                # Columna 1 sin encabezado (para el icono de asociación)
                ctk.CTkLabel(self.lista_rma_frame, text="CLIENTE", font=header_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(self.lista_rma_frame, text="DOCUMENTO DE CLIENTE", font=header_font).grid(row=0, column=3, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(self.lista_rma_frame, text="ÚLTIMA ACTIVIDAD", font=header_font).grid(row=0, column=4, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(self.lista_rma_frame, text="ESTADO", font=header_font).grid(row=0, column=5, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(self.lista_rma_frame, text="FECHA EMISIÓN", font=header_font).grid(row=0, column=6, padx=5, pady=5, sticky="w")
                # Eliminada columna 'ACCIONES' para usar doble clic en la fila
                if not registros:
                    ctk.CTkLabel(self.lista_rma_frame, text="No se encontraron expedientes con los filtros aplicados.", text_color="gray").grid(row=1, column=0, columnspan=7, padx=10, pady=20)
                    return

                # Registros (filas) - usar fondo por defecto del tema (sin cebra)
                colors = ("#FFFFFF", "#F3F4F6")  # variable no usada para cebra pero mantenida por compatibilidad
                # Determinar color de fondo para botones (para hacer 'transparent-like')
                btn_bg = None
                if hasattr(self, 'sidebar_frame') and hasattr(self.sidebar_frame, 'cget'):
                    btn_bg = self.sidebar_frame.cget("fg_color")

                # Altura de fila según compact_mode
                row_height = 22 if getattr(self, 'user_settings', {}).get('compact_mode', True) else 32

                for i, reg in enumerate(registros):
                    rma_id, codigo_rma, cliente, numero_documento_cliente, fecha_emision, estado, fecha_autorizacion, fecha_recepcion, fecha_proceso, fecha_gestion, numero_albaran_reposicion, numero_factura_abono, fecha_para_factura, fecha_entregado_contabilidad, proxima_tarea_vencimiento, proxima_tarea_titulo = reg
                    row = i + 1

                    # Calcular la última actividad usando la función auxiliar
                    ultima_actividad = obtener_ultima_actividad(
                        fecha_emision, 
                        fecha_autorizacion, 
                        fecha_recepcion, 
                        fecha_proceso, 
                        fecha_gestion
                    )

                    # Mapeo de color según estado (coherente con dashboard)
                    color = self.get_color_por_estado(estado)

                    # Usar fondo por defecto del tema en lugar de cebra
                    bg = "transparent"
                    # Crear un frame por columna para alinear exactamente con los encabezados
                    # Reducimos la altura de cada fila usando height pequeño para que sean más finas.
                    # Height reducido para filas compactas
                    # Hacer que la columna de 'ACCIONES' tenga un fondo fijo (sin cebra)
                    actions_bg = None
                    try:
                        if hasattr(self, 'lista_rma_frame') and hasattr(self.lista_rma_frame, 'cget'):
                            actions_bg = self.lista_rma_frame.cget('fg_color')
                    except Exception:
                        actions_bg = None
                    if actions_bg is None:
                        actions_bg = colors[0]

                    f0 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)
                    f1 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height, width=72)
                    f2 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)
                    f3 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)
                    f4 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)
                    f5 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)
                    f6 = ctk.CTkFrame(self.lista_rma_frame, fg_color="transparent", height=row_height)

                    # Colocar cada columna en la grilla principal para que se alinee con encabezados
                    f0.grid(row=row, column=0, sticky="nsew", padx=0, pady=0)
                    f1.grid(row=row, column=1, sticky="ns", padx=0, pady=0)  # Sin expandir horizontalmente
                    f1.grid_propagate(False)  # Evitar que el frame se expanda
                    f2.grid(row=row, column=2, sticky="nsew", padx=0, pady=0)
                    f3.grid(row=row, column=3, sticky="nsew", padx=0, pady=0)
                    f4.grid(row=row, column=4, sticky="nsew", padx=0, pady=0)
                    f5.grid(row=row, column=5, sticky="nsew", padx=0, pady=0)
                    f6.grid(row=row, column=6, sticky="nsew", padx=0, pady=0)

                    # Contenido de cada columna con padding muy reducido para filas más finas
                    # Crear labels y mantener referencias para enlazar eventos (doble click)
                    lbl0 = ctk.CTkLabel(f0, text=codigo_rma)
                    lbl0.pack(anchor="w", padx=4, pady=0)
                    
                    # Columna de iconos: asociaciones y contabilidad
                    lbl1 = None
                    # Icono de asociación
                    if rma_id in asociaciones_dict:
                        codigos_asociados = asociaciones_dict[rma_id]
                        lbl1 = ctk.CTkLabel(f1, text="🔗", cursor="hand2")
                        lbl1.pack(side="left", anchor="center", padx=0, pady=0)
                        tooltip_text = "Asociado a: " + ", ".join(codigos_asociados)
                        Tooltip(lbl1, tooltip_text)
                        lbl1.bind("<Button-1>", lambda e, rid=rma_id: self.mostrar_ventana_asociaciones(rid))
                    # Icono de contabilidad si hay albarán repos. o factura abono
                    tiene_albaran = numero_albaran_reposicion and str(numero_albaran_reposicion).strip()
                    tiene_factura_abono = numero_factura_abono and str(numero_factura_abono).strip()
                    if tiene_albaran or tiene_factura_abono:
                        partes_tooltip = []
                        if tiene_albaran:
                            partes_tooltip.append(f"Alb. Repos.: {str(numero_albaran_reposicion).strip()}")
                        if tiene_factura_abono:
                            partes_tooltip.append(f"Fra. Abono: {str(numero_factura_abono).strip()}")
                        if fecha_para_factura and str(fecha_para_factura).strip():
                            partes_tooltip.append(f"Fecha factura: {str(fecha_para_factura).strip()}")
                        lbl1_cont = ctk.CTkLabel(f1, text="💶")
                        lbl1_cont.pack(side="left", anchor="center", padx=0, pady=0)
                        Tooltip(lbl1_cont, "\n".join(partes_tooltip))
                    # Icono de entregado a contabilidad (quincena marcada)
                    if fecha_entregado_contabilidad and str(fecha_entregado_contabilidad).strip():
                        lbl1_ctb = ctk.CTkLabel(f1, text="📬")
                        lbl1_ctb.pack(side="left", anchor="center", padx=0, pady=0)
                        Tooltip(lbl1_ctb, f"Entregado a Contabilidad: {str(fecha_entregado_contabilidad).strip()}")
                    # Icono de tarea pendiente con vencimiento
                    if proxima_tarea_vencimiento:
                        lbl1_tarea = ctk.CTkLabel(f1, text="⏰")
                        lbl1_tarea.pack(side="left", anchor="center", padx=0, pady=0)
                        titulo_tarea = proxima_tarea_titulo or "Tarea pendiente"
                        Tooltip(lbl1_tarea, f"{titulo_tarea}\nVence: {proxima_tarea_vencimiento}")
                    
                    lbl2 = ctk.CTkLabel(f2, text=cliente)
                    lbl2.pack(anchor="w", padx=4, pady=0)
                    lbl3 = ctk.CTkLabel(f3, text=numero_documento_cliente)
                    lbl3.pack(anchor="w", padx=4, pady=0)
                    lbl4 = ctk.CTkLabel(f4, text=ultima_actividad)
                    lbl4.pack(anchor="w", padx=4, pady=0)
                    lbl5 = ctk.CTkLabel(f5, text=estado, text_color=color)
                    lbl5.pack(anchor="w", padx=4, pady=0)
                    lbl6 = ctk.CTkLabel(f6, text=fecha_emision)
                    lbl6.pack(anchor="w", padx=4, pady=0)
                    # En lugar de botón de editar, abrimos el editor con doble clic en cualquier columna de la fila

                    # Hover efectos para toda la fila: aplicar a cada columna
                    cols = [f0, f1, f2, f3, f4, f5, f6]
                    # Guardar el color original por columna para restaurarlo correctamente
                    originals = ["transparent", "transparent", "transparent", "transparent", "transparent", "transparent", "transparent"]

                    # Función para seleccionar fila con clic simple
                    def _seleccionar_fila(e, cols=cols, row_id=rma_id):
                        # Deseleccionar fila anterior
                        if hasattr(self, 'frames_seleccionados_rma') and self.frames_seleccionados_rma:
                            for frame_anterior in self.frames_seleccionados_rma:
                                try:
                                    frame_anterior.configure(fg_color="transparent")
                                except Exception:
                                    pass
                        
                        # Obtener color de selección del tema
                        try:
                            modo = ctk.get_appearance_mode()
                            color_seleccion = ("#D6EAF8" if modo == "Light" else "#2C5F8D")
                        except Exception:
                            color_seleccion = "#D6EAF8"
                        
                        # Seleccionar nueva fila
                        for rf in cols:
                            try:
                                # El frame del icono mantiene su tamaño fijo
                                if rf == cols[1]:  # f1 (icono)
                                    rf.configure(fg_color=color_seleccion)
                                else:
                                    rf.configure(fg_color=color_seleccion)
                            except Exception:
                                pass
                        
                        # Guardar referencia a la fila seleccionada
                        self.fila_seleccionada_rma = row_id
                        self.frames_seleccionados_rma = cols

                    def _on_enter(e, cols=cols):
                        # Solo aplicar hover si no está seleccionada
                        if not hasattr(self, 'fila_seleccionada_rma') or self.fila_seleccionada_rma != rma_id:
                            try:
                                modo = ctk.get_appearance_mode()
                                hover_color = ("#F5F5F5" if modo == "Light" else "#2B2B2B")
                            except Exception:
                                hover_color = "#F5F5F5"
                            for rf in cols:
                                try:
                                    rf.configure(fg_color=hover_color)
                                except Exception:
                                    pass

                    def _on_leave(e, cols=cols, originals=originals):
                        # Solo restaurar si no está seleccionada
                        if not hasattr(self, 'fila_seleccionada_rma') or self.fila_seleccionada_rma != rma_id:
                            for idx, rf in enumerate(cols):
                                try:
                                    rf.configure(fg_color=originals[idx])
                                except Exception:
                                    pass

                    # También enlazamos los labels internos para asegurar que capturan el doble click
                    inner_widgets = [lbl0, lbl2, lbl3, lbl4, lbl5, lbl6]  # No incluir lbl1 si tiene evento de asociación
                    if lbl1 is None:  # Si no hay icono de asociación, agregar el label vacío para hover
                        inner_widgets.append(lbl1)

                    for rf in cols:
                        rf.bind("<Enter>", _on_enter)
                        rf.bind("<Leave>", _on_leave)
                        rf.bind("<Button-1>", _seleccionar_fila)  # Clic simple para seleccionar
                        rf.bind("<Double-Button-1>", lambda e=None, r=rma_id: self._abrir_editor_rma(rma_id=r))  # Doble clic para abrir
                        rf.bind("<Button-3>", lambda e, rid=rma_id, cod=codigo_rma: self.mostrar_menu_contextual_expediente(e, rid, cod))  # Clic derecho
                        # Mostrar cursor 'hand2' para indicar que la fila es clicable
                        try:
                            rf.configure(cursor="hand2")
                        except Exception:
                            pass

                    # Enlazar eventos a labels (algunas platforms capturan el evento en el label)
                    for w in inner_widgets:
                        if w is not None:
                            try:
                                w.configure(cursor="hand2")
                            except Exception:
                                pass
                            try:
                                w.bind("<Button-1>", _seleccionar_fila)  # Clic simple para seleccionar
                                w.bind("<Double-Button-1>", lambda e=None, r=rma_id: self._abrir_editor_rma(rma_id=r))  # Doble clic para abrir
                                w.bind("<Button-3>", lambda e, rid=rma_id, cod=codigo_rma: self.mostrar_menu_contextual_expediente(e, rid, cod))  # Clic derecho
                            except Exception:
                                pass
            
        except Exception as e:
            print(f"Error al cargar lista de RMA: {e}")
            if conn: conn.close()
            ctk.CTkLabel(self.lista_rma_frame, text=f"Error al cargar la lista: {e}").grid(row=1, column=0, columnspan=7, padx=10, pady=20)

    def ir_pagina_anterior_lista(self):
        """Navega a la página anterior de la lista de RMA."""
        if self.pagina_actual_lista > 0:
            self.pagina_actual_lista -= 1
            texto_busqueda = self.entry_busqueda.get()
            estado_filtro = self.filtro_estado.get()
            año_filtro = self.filtro_año.get()
            self.cargar_lista_rma(texto_busqueda, estado_filtro, año_filtro)

    def ir_pagina_siguiente_lista(self):
        """Navega a la página siguiente de la lista de RMA."""
        # El límite superior se verifica en cargar_lista_rma al habilitar/deshabilitar el botón
        self.pagina_actual_lista += 1
        texto_busqueda = self.entry_busqueda.get()
        estado_filtro = self.filtro_estado.get()
        año_filtro = self.filtro_año.get()
        self.cargar_lista_rma(texto_busqueda, estado_filtro, año_filtro)

    def cambiar_elementos_por_pagina_lista(self, valor):
        """Cambia el número de elementos por página y reinicia a la primera página."""
        self.elementos_por_pagina_lista = int(valor)
        self.pagina_actual_lista = 0  # Reiniciar a la primera página
        texto_busqueda = self.entry_busqueda.get()
        estado_filtro = self.filtro_estado.get()
        año_filtro = self.filtro_año.get()
        self.cargar_lista_rma(texto_busqueda, estado_filtro, año_filtro)

    def aplicar_filtros_rma(self):
        """Lee los valores de los filtros y recarga la lista."""
        texto_busqueda = self.entry_busqueda.get()
        estado_filtro = self.filtro_estado.get()
        año_filtro = self.filtro_año.get()
        
        # Resetear a la primera página cuando se aplican nuevos filtros
        self.pagina_actual_lista = 0
        
        self.cargar_lista_rma(texto_busqueda, estado_filtro, año_filtro)

    def mostrar_menu_contextual_expediente(self, event, rma_id, codigo_rma):
        """
        Muestra el menú contextual al hacer clic derecho en un expediente.
        
        Args:
            event: Evento del clic derecho
            rma_id (int): ID del expediente
            codigo_rma (str): Código del expediente (ej: RMA25001)
        """
        from lib.rma_utils import obtener_estados_disponibles
        
        # Crear menú contextual
        menu = tk.Menu(self, tearoff=0)
        
        # Submenu para cambiar estado
        menu_estados = tk.Menu(menu, tearoff=0)
        estados = obtener_estados_disponibles()
        
        for estado in estados:
            menu_estados.add_command(
                label=estado,
                command=lambda e=estado: self.confirmar_cambio_estado(rma_id, codigo_rma, e)
            )
        
        menu.add_cascade(label="🔄 Cambiar Estado", menu=menu_estados)
        
        # Añadir opción de asociar expediente
        menu.add_separator()
        menu.add_command(
            label="🔗 Asociar Expediente",
            command=lambda: self.mostrar_dialogo_asociar_rma(rma_id)
        )
        
        # Añadir opción de generar autorización (solo para roles autorizados)
        if self.rol in ["administrador", "admin", "Dpto. Tecnico"]:
            menu.add_separator()
            menu.add_command(
                label="📄 Generar Autorización",
                command=lambda: self.mostrar_dialogo_autorizacion(rma_id, codigo_rma)
            )
        
        # Verificar si existe el archivo de autorización
        archivo_autorizacion = self._verificar_existe_autorizacion(rma_id, codigo_rma)
        if archivo_autorizacion:
            menu.add_separator()
            menu.add_command(
                label="📥 Descargar Autorización",
                command=lambda: self._abrir_autorizacion(archivo_autorizacion, codigo_rma)
            )
        
        # Mostrar el menú en la posición del cursor
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
