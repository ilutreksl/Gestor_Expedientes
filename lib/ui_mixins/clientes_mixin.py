"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class ClientesMixin:
    def mostrar_clientes(self):
        """Muestra la gestión independiente de clientes."""
        
        # Mantener el tamaño actual de la ventana
        current_geometry = self.geometry()
        
        try:
            self.limpiar_contenido()
            
            # Asegurar que la ventana mantenga su tamaño
            self.geometry(current_geometry)
            
            # Header
            header_frame = ctk.CTkFrame(self.content_frame)
            header_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(header_frame, 
                        text="🧑‍💼 GESTIÓN DE CLIENTES", 
                        font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
            
            # Botones de acción principal
            botones_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            botones_frame.pack(fill="x", padx=10, pady=5)
            
            btn_nuevo = ctk.CTkButton(botones_frame, text="➕ Nuevo Cliente", 
                                     command=self.nuevo_cliente, 
                                     width=140, height=35)
            btn_nuevo.pack(side="left", padx=(0,10))
            Tooltip(btn_nuevo, "Crear un nuevo cliente en el sistema")
            
            btn_migrar = ctk.CTkButton(botones_frame, text="🔄 Migrar desde RMAs", 
                                      command=self.migrar_clientes_desde_rmas, 
                                      width=160, height=35)
            btn_migrar.pack(side="left", padx=(0,10))
            Tooltip(btn_migrar, "Importar clientes automáticamente desde los RMAs existentes")
            
            # Búsqueda y filtros
            busqueda_frame = ctk.CTkFrame(self.content_frame)
            busqueda_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(busqueda_frame, text="Buscar cliente:", 
                        font=ctk.CTkFont(size=12)).pack(side="left", padx=10, pady=10)
            
            self.entry_buscar_cliente = ctk.CTkEntry(busqueda_frame, 
                                                   placeholder_text="Nombre del cliente...",
                                                   width=200)
            self.entry_buscar_cliente.pack(side="left", padx=5, pady=10)
            self.entry_buscar_cliente.bind("<KeyRelease>", self.filtrar_clientes)
            Tooltip(self.entry_buscar_cliente, "Escriba para buscar clientes por nombre en tiempo real")
            
            # Filtro por tipo
            ctk.CTkLabel(busqueda_frame, text="Tipo:", 
                        font=ctk.CTkFont(size=12)).pack(side="left", padx=(20,5), pady=10)
            
            self.filtro_tipo_cliente = ctk.CTkOptionMenu(busqueda_frame, 
                                                       values=["Todos", "Regular", "Premium", "VIP"],
                                                       command=self.filtrar_clientes,
                                                       width=100)
            self.filtro_tipo_cliente.set("Todos")
            self.filtro_tipo_cliente.pack(side="left", padx=5, pady=10)
            Tooltip(self.filtro_tipo_cliente, "Filtrar clientes por tipo: Regular, Premium o VIP")
            
            # Lista de clientes con más altura para aprovechar mejor el espacio
            self.clientes_frame = ctk.CTkScrollableFrame(self.content_frame, height=500)
            self.clientes_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Cargar clientes
            self.cargar_lista_clientes()
            
        except Exception as e:
            print(f"❌ Error en mostrar_clientes: {e}")
            import traceback
            print(traceback.format_exc())

    def cargar_lista_clientes(self):
        """Carga y muestra la lista de clientes."""
        # Limpiar lista actual
        for widget in self.clientes_frame.winfo_children():
            widget.destroy()
        
        # Resetear selección
        self.fila_seleccionada_cliente = None
        self.frame_seleccionado_cliente = None
        
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                print("❌ No se pudo conectar a la base de datos")
                return
            
            # Buscar clientes con estadísticas (consulta simplificada)
            filtro_busqueda = self.entry_buscar_cliente.get().strip() if hasattr(self, 'entry_buscar_cliente') else ""
            filtro_tipo = self.filtro_tipo_cliente.get() if hasattr(self, 'filtro_tipo_cliente') else "Todos"
            
            # Consulta con estadísticas reales
            query = """
                SELECT c.cliente_id, c.nombre, c.tipo_cliente, c.activo, c.fecha_registro,
                       COALESCE(COUNT(DISTINCT r.id), 0) as total_rmas,
                       CASE 
                           WHEN COUNT(DISTINCT r.id) > 0 THEN 
                               ROUND(CAST(SUM(CASE WHEN r.resultado_expediente = 'ABONAR' THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(DISTINCT r.id), 1)
                           ELSE 0 
                       END as tasa_exito,
                       MAX(r.fecha_emision) as ultimo_rma,
                       COALESCE(COUNT(DISTINCT con.contacto_id), 0) as total_contactos
                FROM clientes c
                LEFT JOIN rma_maestro r ON c.nombre = r.cliente
                LEFT JOIN contactos_cliente con ON c.cliente_id = con.cliente_id
                WHERE 1=1
            """
            params = []
            
            if filtro_busqueda:
                query += " AND c.nombre LIKE ?"
                params.append(f"%{filtro_busqueda}%")
            
            if filtro_tipo != "Todos":
                query += " AND c.tipo_cliente = ?"
                params.append(filtro_tipo)
            
            query += " GROUP BY c.cliente_id, c.nombre, c.tipo_cliente, c.activo, c.fecha_registro ORDER BY c.nombre"
            
            cursor.execute(query, params)
            clientes = cursor.fetchall()
            
            if not clientes:
                ctk.CTkLabel(self.clientes_frame, 
                           text="📋 No se encontraron clientes. Haz clic en 'Nuevo Cliente' para agregar uno.",
                           font=ctk.CTkFont(size=13)).pack(pady=30)
                conn.close()
                return
            
            # Mostrar cada cliente
            for i, cliente in enumerate(clientes):
                self.crear_item_cliente(cliente)
            
            conn.close()
            
        except Exception as e:
            error_msg = f"❌ Error cargando clientes: {str(e)}"
            print(error_msg)
            ctk.CTkLabel(self.clientes_frame, 
                       text=error_msg,
                       font=ctk.CTkFont(size=12), 
                       text_color="red").pack(pady=20)
            import traceback
            print(traceback.format_exc())

    def crear_item_cliente(self, cliente):
        """Crea un elemento visual para un cliente en la lista con diseño compacto."""
        cliente_id, nombre, tipo, activo, fecha_reg, total_rmas, tasa_exito, ultimo_rma, total_contactos = cliente
        
        # Frame principal del cliente con altura reducida y borde sutil
        cliente_frame = ctk.CTkFrame(self.clientes_frame, height=45, border_width=1)
        cliente_frame.pack(fill="x", padx=5, pady=1)
        cliente_frame.pack_propagate(False)  # Mantener altura fija
        
        # Configurar grid para el layout horizontal
        cliente_frame.grid_columnconfigure(0, weight=1)  # Info del cliente (expandible)
        
        # Información del cliente
        info_frame = ctk.CTkFrame(cliente_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        info_frame.grid_columnconfigure(0, weight=1)
        
        # Línea superior: Nombre, estado y tipo en una sola línea
        header_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        
        # Nombre del cliente (con doble clic para abrir)
        nombre_label = ctk.CTkLabel(header_frame, text=f"🧑‍💼 {nombre}", 
                                  font=ctk.CTkFont(size=13, weight="bold"),
                                  cursor="hand2")
        nombre_label.pack(side="left")
        nombre_label.bind("<Double-Button-1>", lambda e: self.abrir_ficha_cliente(cliente_id))
        Tooltip(nombre_label, "Doble clic para abrir la ficha del cliente")
        
        # Estado a la derecha
        estado_color = "green" if activo else "red"
        estado_texto = "🟢" if activo else "🔴"
        estado_label = ctk.CTkLabel(header_frame, text=estado_texto, 
                                  font=ctk.CTkFont(size=10))
        estado_label.pack(side="right", padx=(5,0))
        
        # Línea inferior: Estadísticas compactas
        stats_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        
        # Convertir valores a números para el formateo
        try:
            total_rmas_num = int(total_rmas) if total_rmas else 0
            tasa_exito_num = float(tasa_exito) if tasa_exito else 0.0
            total_contactos_num = int(total_contactos) if total_contactos else 0
        except (ValueError, TypeError):
            total_rmas_num = 0
            tasa_exito_num = 0.0
            total_contactos_num = 0
        
        stats_text = f"📊 {total_rmas_num} RMAs • ✅ {tasa_exito_num:.1f}% • 👥 {total_contactos_num} contactos"
        if ultimo_rma:
            stats_text += f" • 📅 {ultimo_rma}"
        
        stats_label = ctk.CTkLabel(stats_frame, text=stats_text, 
                                 font=ctk.CTkFont(size=9), text_color="gray")
        stats_label.pack(side="left")
        
        # Implementar selección con clic simple
        def _seleccionar_cliente(e):
            # Deseleccionar cliente anterior
            if hasattr(self, 'frame_seleccionado_cliente') and self.frame_seleccionado_cliente:
                try:
                    self.frame_seleccionado_cliente.configure(fg_color="transparent")
                except Exception:
                    pass
            
            # Obtener color de selección
            try:
                modo = ctk.get_appearance_mode()
                color_seleccion = ("#D6EAF8" if modo == "Light" else "#2C5F8D")
            except Exception:
                color_seleccion = "#D6EAF8"
            
            # Seleccionar nuevo cliente
            cliente_frame.configure(fg_color=color_seleccion)
            
            # Guardar referencia
            self.fila_seleccionada_cliente = cliente_id
            self.frame_seleccionado_cliente = cliente_frame
        
        def _on_enter_cliente(e):
            if not hasattr(self, 'fila_seleccionada_cliente') or self.fila_seleccionada_cliente != cliente_id:
                try:
                    modo = ctk.get_appearance_mode()
                    hover_color = ("#F5F5F5" if modo == "Light" else "#2B2B2B")
                except Exception:
                    hover_color = "#F5F5F5"
                cliente_frame.configure(fg_color=hover_color)
        
        def _on_leave_cliente(e):
            if not hasattr(self, 'fila_seleccionada_cliente') or self.fila_seleccionada_cliente != cliente_id:
                cliente_frame.configure(fg_color="transparent")
        
        # Bind eventos
        cliente_frame.bind("<Button-1>", _seleccionar_cliente)
        cliente_frame.bind("<Double-Button-1>", lambda e: self.abrir_ficha_cliente(cliente_id))
        cliente_frame.bind("<Enter>", _on_enter_cliente)
        cliente_frame.bind("<Leave>", _on_leave_cliente)
        cliente_frame.configure(cursor="hand2")
        
        # Bind a labels también
        for lbl in [nombre_label, estado_label, stats_label]:
            lbl.bind("<Button-1>", _seleccionar_cliente)
            lbl.bind("<Double-Button-1>", lambda e: self.abrir_ficha_cliente(cliente_id))

    def filtrar_clientes(self, event=None):
        """Filtra la lista de clientes según los criterios de búsqueda."""
        self.cargar_lista_clientes()

    def nuevo_cliente(self):
        """Muestra el formulario para crear un nuevo cliente."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Nuevo Cliente")
        ventana.geometry("500x600")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="➕ Nuevo Cliente", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=400)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Nombre (obligatorio)
        ctk.CTkLabel(form_frame, text="Nombre del Cliente *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre completo del cliente")
        entry_nombre.pack(fill="x", pady=(0,10))
        
        # Tipo de cliente
        ctk.CTkLabel(form_frame, text="Tipo de Cliente", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        option_tipo = ctk.CTkOptionMenu(form_frame, values=self.OPCIONES["Tipo_Cliente"])
        option_tipo.set(self.OPCIONES["Tipo_Cliente"][0])
        option_tipo.pack(fill="x", pady=(0,10))
        
        # Dirección
        ctk.CTkLabel(form_frame, text="Dirección", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_direccion = ctk.CTkEntry(form_frame, placeholder_text="Dirección completa")
        entry_direccion.pack(fill="x", pady=(0,10))
        
        # Teléfono principal
        ctk.CTkLabel(form_frame, text="Teléfono Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_telefono = ctk.CTkEntry(form_frame, placeholder_text="Teléfono de contacto principal")
        entry_telefono.pack(fill="x", pady=(0,10))
        
        # Email principal
        ctk.CTkLabel(form_frame, text="Email Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_email = ctk.CTkEntry(form_frame, placeholder_text="Email de contacto principal")
        entry_email.pack(fill="x", pady=(0,10))
        
        # Notas generales
        ctk.CTkLabel(form_frame, text="Notas Generales", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        text_notas = ctk.CTkTextbox(form_frame, height=80)
        text_notas.pack(fill="x", pady=(0,10))
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        def guardar_cliente():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre del cliente es obligatorio")
                return
            
            try:
                conn, cursor = self.master.conectar_db()
                if not conn: return
                
                cursor.execute("""
                    INSERT INTO clientes (nombre, tipo_cliente, direccion, telefono_principal, 
                                        email_principal, notas_generales, descuento, campo_reserva_1, campo_reserva_2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nombre, option_tipo.get(), entry_direccion.get().strip(),
                     entry_telefono.get().strip(), entry_email.get().strip(),
                     text_notas.get("1.0", "end-1c").strip(), 0.0, "", ""))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Éxito", f"Cliente '{nombre}' creado correctamente")
                ventana.destroy()
                if hasattr(self, 'clientes_frame') and self.clientes_frame.winfo_exists():
                    self.cargar_lista_clientes()

            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    messagebox.showerror("Error", f"Ya existe un cliente con el nombre '{nombre}'")
                else:
                    messagebox.showerror("Error", f"Error al crear cliente: {str(e)}")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Guardar Cliente", 
                                  command=guardar_cliente,
                                  width=120)
        btn_guardar.pack(side="right")

    def migrar_clientes_desde_rmas(self):
        """Migra clientes existentes desde la tabla rma_maestro."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return
            
            # Contar clientes únicos en RMAs antes de migrar
            cursor.execute("""
                SELECT COUNT(DISTINCT cliente) 
                FROM rma_maestro 
                WHERE cliente IS NOT NULL AND cliente != ''
            """)
            total_clientes_en_rmas = cursor.fetchone()[0]
            
            # Contar clientes ya existentes en la tabla
            cursor.execute("SELECT COUNT(*) FROM clientes")
            clientes_antes = cursor.fetchone()[0]
            
            # Ejecutar migración
            cursor.execute("""
                INSERT OR IGNORE INTO clientes (nombre, fecha_registro, email_principal)
                SELECT DISTINCT 
                    Cliente,
                    MIN(fecha_emision) as fecha_registro,
                    Email_de_Contacto
                FROM rma_maestro 
                WHERE Cliente IS NOT NULL AND Cliente != ''
                GROUP BY Cliente
            """)
            
            # Contar después de migrar
            cursor.execute("SELECT COUNT(*) FROM clientes")
            clientes_despues = cursor.fetchone()[0]
            
            clientes_nuevos = int(clientes_despues) - int(clientes_antes)
            clientes_ya_existian = int(total_clientes_en_rmas) - clientes_nuevos
            
            # Migrar contactos - evitando duplicados
            # Primero obtener contactos únicos de RMAs que aún no existen en contactos_cliente
            cursor.execute("""
                SELECT DISTINCT
                    c.cliente_id,
                    COALESCE(rm.Persona_de_Contacto, rm.Cliente) as nombre,
                    rm.Email_de_Contacto
                FROM clientes c
                JOIN rma_maestro rm ON c.nombre = rm.Cliente
                WHERE rm.Persona_de_Contacto IS NOT NULL 
                AND rm.Persona_de_Contacto != ''
                AND NOT EXISTS (
                    SELECT 1 FROM contactos_cliente cc
                    WHERE cc.cliente_id = c.cliente_id
                    AND cc.nombre = COALESCE(rm.Persona_de_Contacto, rm.Cliente)
                )
                GROUP BY c.cliente_id, rm.Persona_de_Contacto
            """)
            
            contactos_a_migrar = cursor.fetchall()
            contactos_migrados = 0
            
            # Insertar solo los contactos que no existen
            for cliente_id, nombre, email in contactos_a_migrar:
                cursor.execute("""
                    INSERT INTO contactos_cliente (cliente_id, nombre, email, es_principal)
                    VALUES (?, ?, ?, 1)
                """, (cliente_id, nombre, email))
                contactos_migrados += 1
            
            conn.commit()
            conn.close()
            
            # Mensaje mejorado
            if clientes_nuevos > 0:
                mensaje = f"✅ Migración completada:\n\n"
                mensaje += f"• {clientes_nuevos} cliente(s) NUEVO(S) migrado(s)\n"
                if clientes_ya_existian > 0:
                    mensaje += f"• {clientes_ya_existian} cliente(s) ya existían (no duplicados)\n"
                mensaje += f"• {contactos_migrados} contacto(s) migrado(s)\n\n"
                mensaje += f"📊 Total de clientes en sistema: {clientes_despues}"
            else:
                mensaje = f"ℹ️ Migración completada:\n\n"
                mensaje += f"• Todos los clientes ({total_clientes_en_rmas}) ya estaban migrados\n"
                mensaje += f"• No se encontraron duplicados\n"
                mensaje += f"• {contactos_migrados} contacto(s) nuevos añadidos\n\n"
                mensaje += f"📊 Total de clientes en sistema: {clientes_despues}"
            
            messagebox.showinfo("Migración Completada", mensaje)
            
            self.cargar_lista_clientes()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en la migración: {str(e)}")

    def abrir_ficha_cliente(self, cliente_id):
        """Abre la ficha completa del cliente con todas sus pestañas."""
        # Obtener información del cliente
        cliente = self.obtener_cliente(cliente_id)
        if not cliente:
            messagebox.showerror("Error", "No se pudo cargar la información del cliente")
            return
        
        # Crear ventana principal
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Ficha Cliente: {cliente[1]}")  # cliente[1] es el nombre
        ventana.geometry("900x900")
        ventana.resizable(True, True)
        
        # Configurar para permitir minimización
        ventana.attributes('-topmost', False)
        ventana.minsize(700, 650)
        # No usar transient para permitir minimización completa
        ventana.focus_set()  # Dar foco sin bloquear
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        ventana.attributes('-topmost', True)   # Temporalmente al frente
        ventana.lift()
        ventana.focus_force()
        ventana.after(500, lambda: ventana.attributes('-topmost', False))  # Quitar topmost después de 500ms
        
        # Header con información básica
        header_frame = ctk.CTkFrame(ventana)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # Nombre del cliente
        nombre_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        nombre_frame.pack(fill="x")
        
        ctk.CTkLabel(nombre_frame, text=f"🧑‍💼 {cliente[1]}", 
                    font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        # Widget de estadísticas básicas
        from lib.cliente_estadisticas import calcular_estadisticas_basicas_cliente, crear_widget_estadisticas_basicas
        
        try:
            conn, cursor = self.master.conectar_db()
            if conn:
                stats = calcular_estadisticas_basicas_cliente(cliente[1], conn)
                crear_widget_estadisticas_basicas(info_frame, stats)
                conn.close()
        except Exception as e:
            print(f"Error cargando estadísticas: {e}")
        
        # Crear pestañas (sin expand para dejar espacio a los botones)
        tabview = ctk.CTkTabview(ventana, width=880, height=350)
        tabview.pack(fill="x", expand=False, padx=10, pady=5)
        
        # Pestaña 1: Información General (en modo edición)
        tab_info = tabview.add("📋 Información")
        widgets_info = self.crear_tab_informacion_cliente_editable(tab_info, cliente)
        
        # Pestaña 2: Contactos
        tab_contactos = tabview.add("👥 Contactos")
        self.crear_tab_contactos_cliente(tab_contactos, cliente_id)
        
        # Pestaña 3: Historial RMAs
        tab_rmas = tabview.add("📦 Historial RMAs")
        self.crear_tab_historial_rmas(tab_rmas, cliente_id)
        
        # Pestaña 4: Notas
        tab_notas = tabview.add("📝 Notas")
        self.crear_tab_notas_cliente(tab_notas, cliente_id)
        
        # Pestaña 5: Estadísticas
        tab_stats = tabview.add("📊 Estadísticas")
        self.crear_tab_estadisticas_cliente_completa(tab_stats, cliente_id, cliente[1])
        
        # Pestaña 6: Condiciones
        tab_condiciones = tabview.add("💰 Condiciones")
        widgets_condiciones = self.crear_tab_condiciones_cliente(tab_condiciones, cliente_id)
        
        # Botones de acción ANTES de definir funciones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Función para guardar cambios
        def guardar_cambios_cliente():
            from lib.cliente_condiciones import guardar_condiciones_cliente, validar_descuento
            
            datos = {
                'nombre': widgets_info['entry_nombre'].get().strip(),
                'tipo_cliente': widgets_info['option_tipo'].get(),
                'direccion': widgets_info['entry_direccion'].get().strip(),
                'telefono_principal': widgets_info['entry_telefono'].get().strip(),
                'email_principal': widgets_info['entry_email'].get().strip(),
                'notas_generales': widgets_info['text_notas'].get("1.0", "end-1c").strip()
            }
            
            if not datos['nombre']:
                messagebox.showerror("Error", "El nombre del cliente es obligatorio")
                return
            
            # Validar descuento antes de guardar
            descuento_str = widgets_condiciones['entry_descuento'].get().strip()
            es_valido, descuento_valor, mensaje_error = validar_descuento(descuento_str)
            
            if not es_valido:
                messagebox.showerror("Error", f"Error en Condiciones: {mensaje_error}")
                return
            
            # Actualizar datos del cliente
            if self.actualizar_cliente(cliente_id, datos):
                # Guardar condiciones comerciales
                try:
                    conn, cursor = self.master.conectar_db()
                    if conn:
                        reserva1 = widgets_condiciones['entry_reserva1'].get().strip()
                        reserva2 = widgets_condiciones['entry_reserva2'].get().strip()
                        
                        if not guardar_condiciones_cliente(cliente_id, descuento_valor, reserva1, reserva2, conn):
                            messagebox.showerror("Error", "Error al guardar las condiciones comerciales")
                            conn.close()
                            return
                        
                        conn.close()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al guardar condiciones: {str(e)}")
                    return
                
                messagebox.showinfo("Éxito", f"Cliente '{datos['nombre']}' actualizado correctamente")
                
                # Recargar estadísticas
                try:
                    conn, cursor = self.master.conectar_db()
                    if conn:
                        stats = calcular_estadisticas_basicas_cliente(datos['nombre'], conn)
                        # Actualizar widget de estadísticas
                        for widget in info_frame.winfo_children():
                            if isinstance(widget, ctk.CTkFrame) and widget != nombre_frame:
                                widget.destroy()
                        crear_widget_estadisticas_basicas(info_frame, stats)
                        conn.close()
                except Exception as e:
                    print(f"Error recargando estadísticas: {e}")
            else:
                messagebox.showerror("Error", "Error al actualizar el cliente")
        
        # Configurar botones (frame ya creado arriba)
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Guardar Cambios", 
                                 command=guardar_cambios_cliente,
                                 width=140)
        btn_guardar.pack(side="left", padx=(0,10))
        
        # Botón Desactivar (visible para todos los usuarios)
        if cliente[7] == 0:  # cliente[7] es el campo activo
            # Cliente ya inactivo - mostrar indicador
            ctk.CTkLabel(botones_frame, text="⚠️ INACTIVO", 
                        text_color="red", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5))
        else:
            # Cliente activo - mostrar botón de desactivar
            def desactivar_cliente_confirmado():
                respuesta = messagebox.askyesno(
                    "⚠️ Confirmar Desactivación",
                    f"¿Está seguro de que desea desactivar el cliente '{cliente[1]}'?\n\n"
                    "El cliente quedará inactivo y no podrá ser usado para nuevos expedientes.\n"
                    "Podrá reactivarlo más adelante desde el panel de administración.",
                    icon="warning"
                )
                if respuesta:
                    if self.eliminar_cliente(cliente_id):
                        messagebox.showinfo("Éxito", f"Cliente '{cliente[1]}' desactivado correctamente")
                        ventana.destroy()
                    else:
                        messagebox.showerror("Error", "No se pudo desactivar el cliente")
            
            btn_desactivar = ctk.CTkButton(botones_frame, text="🚫 Desactivar", 
                                           command=desactivar_cliente_confirmado,
                                           width=120,
                                           fg_color="#6c757d",
                                           hover_color="#5a6268")
            btn_desactivar.pack(side="left", padx=(0,10))
        
        # Botón Eliminar Permanentemente (solo para admin)
        if str(self.rol).strip().lower() in ("admin", "administrador"):
            def eliminar_cliente_permanente():
                respuesta = messagebox.askyesno(
                    "⚠️ ELIMINAR PERMANENTEMENTE",
                    f"¿Está seguro de que desea ELIMINAR PERMANENTEMENTE el cliente '{cliente[1]}'?\n\n"
                    "⚠️ Esta acción es IRREVERSIBLE y eliminará todos los datos del cliente de la base de datos.\n\n"
                    "Se eliminarán:\n"
                    "- Datos del cliente\n"
                    "- Contactos asociados\n"
                    "- Condiciones comerciales\n\n"
                    "Los expedientes RMAs asociados no se eliminarán pero perderán la referencia al cliente.",
                    icon="error"
                )
                if respuesta:
                    # Segunda confirmación
                    respuesta2 = messagebox.askyesno(
                        "⚠️ Confirmación Final",
                        f"¿Está COMPLETAMENTE seguro?\n\n"
                        "El cliente '{cliente[1]}' será eliminado DEFINITIVAMENTE.",
                        icon="error"
                    )
                    if respuesta2:
                        if self.eliminar_cliente_permanente(cliente_id):
                            messagebox.showinfo("Éxito", f"Cliente '{cliente[1]}' eliminado permanentemente")
                            ventana.destroy()
                        else:
                            messagebox.showerror("Error", "No se pudo eliminar el cliente")
            
            btn_eliminar = ctk.CTkButton(botones_frame, text="🗑️ Eliminar", 
                                       command=eliminar_cliente_permanente,
                                       width=120,
                                       fg_color="#dc3545",
                                       hover_color="#c82333")
            btn_eliminar.pack(side="left", padx=(0,10))
        
        btn_cerrar = ctk.CTkButton(botones_frame, text="❌ Cerrar", 
                                 command=ventana.destroy,
                                 width=100)
        btn_cerrar.pack(side="right")

    def crear_tab_informacion_cliente(self, tab_frame, cliente):
        """Crea la pestaña de información general del cliente."""
        # Frame scrollable para el formulario
        scroll_frame = ctk.CTkScrollableFrame(tab_frame, height=500)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Información básica
        ctk.CTkLabel(scroll_frame, text="📋 Información Básica", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,10))
        
        info_frame = ctk.CTkFrame(scroll_frame)
        info_frame.pack(fill="x", pady=(0,20))
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Datos del cliente
        datos = [
            ("ID Cliente:", str(cliente[0])),
            ("Nombre:", cliente[1]),
            ("Tipo:", cliente[2]),
            ("Dirección:", cliente[3] or "No especificada"),
            ("Teléfono Principal:", cliente[4] or "No especificado"),
            ("Email Principal:", cliente[5] or "No especificado"),
            ("Fecha Registro:", cliente[8].split()[0] if cliente[8] else "No disponible"),
            ("Última Actualización:", cliente[9].split()[0] if cliente[9] else "No disponible")
        ]
        
        for i, (etiqueta, valor) in enumerate(datos):
            ctk.CTkLabel(info_frame, text=etiqueta, 
                        font=ctk.CTkFont(size=12, weight="bold")).grid(
                        row=i, column=0, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(info_frame, text=valor, 
                        font=ctk.CTkFont(size=12)).grid(
                        row=i, column=1, sticky="w", padx=10, pady=5)
        
        # Notas generales
        if cliente[6]:  # cliente[6] son las notas generales
            ctk.CTkLabel(scroll_frame, text="📝 Notas Generales", 
                        font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20,10))
            
            notas_frame = ctk.CTkFrame(scroll_frame)
            notas_frame.pack(fill="x", pady=(0,10))
            
            text_notas = ctk.CTkTextbox(notas_frame, height=100)
            text_notas.pack(fill="x", padx=10, pady=10)
            text_notas.insert("1.0", cliente[6])
            text_notas.configure(state="disabled")

    def crear_tab_informacion_cliente_editable(self, tab_frame, cliente):
        """Crea la pestaña de información general del cliente en modo edición."""
        # Frame scrollable para el formulario
        scroll_frame = ctk.CTkScrollableFrame(tab_frame, height=500)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Información básica
        ctk.CTkLabel(scroll_frame, text="📋 Información Básica (Editable)", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,10))
        
        info_frame = ctk.CTkFrame(scroll_frame)
        info_frame.pack(fill="x", pady=(0,20))
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Widgets editables
        widgets = {}
        
        # ID Cliente (solo lectura)
        ctk.CTkLabel(info_frame, text="ID Cliente:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=0, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkLabel(info_frame, text=str(cliente[0]), 
                    font=ctk.CTkFont(size=12)).grid(
                    row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Nombre (editable)
        ctk.CTkLabel(info_frame, text="Nombre: *", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=1, column=0, sticky="w", padx=10, pady=5)
        widgets['entry_nombre'] = ctk.CTkEntry(info_frame)
        widgets['entry_nombre'].grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        widgets['entry_nombre'].insert(0, cliente[1])
        
        # Tipo de cliente (editable)
        ctk.CTkLabel(info_frame, text="Tipo Cliente:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=2, column=0, sticky="w", padx=10, pady=5)
        widgets['option_tipo'] = ctk.CTkOptionMenu(info_frame, 
                                                    values=self.OPCIONES["Tipo_Cliente"])
        widgets['option_tipo'].grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        widgets['option_tipo'].set(cliente[2] if cliente[2] else self.OPCIONES["Tipo_Cliente"][0])
        
        # Dirección (editable)
        ctk.CTkLabel(info_frame, text="Dirección:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=3, column=0, sticky="w", padx=10, pady=5)
        widgets['entry_direccion'] = ctk.CTkEntry(info_frame)
        widgets['entry_direccion'].grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        widgets['entry_direccion'].insert(0, cliente[3] or "")
        
        # Teléfono (editable)
        ctk.CTkLabel(info_frame, text="Teléfono Principal:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=4, column=0, sticky="w", padx=10, pady=5)
        widgets['entry_telefono'] = ctk.CTkEntry(info_frame)
        widgets['entry_telefono'].grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        widgets['entry_telefono'].insert(0, cliente[4] or "")
        
        # Email (editable)
        ctk.CTkLabel(info_frame, text="Email Principal:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=5, column=0, sticky="w", padx=10, pady=5)
        widgets['entry_email'] = ctk.CTkEntry(info_frame)
        widgets['entry_email'].grid(row=5, column=1, sticky="ew", padx=10, pady=5)
        widgets['entry_email'].insert(0, cliente[5] or "")
        
        # Fechas (solo lectura)
        ctk.CTkLabel(info_frame, text="Fecha Registro:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=6, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkLabel(info_frame, text=cliente[8].split()[0] if cliente[8] else "No disponible", 
                    font=ctk.CTkFont(size=12)).grid(
                    row=6, column=1, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(info_frame, text="Última Actualización:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=7, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkLabel(info_frame, text=cliente[9].split()[0] if cliente[9] else "No disponible", 
                    font=ctk.CTkFont(size=12)).grid(
                    row=7, column=1, sticky="w", padx=10, pady=5)
        
        # Notas generales (editable)
        ctk.CTkLabel(scroll_frame, text="📝 Notas Generales", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20,10))
        
        notas_frame = ctk.CTkFrame(scroll_frame)
        notas_frame.pack(fill="x", pady=(0,10))
        
        widgets['text_notas'] = ctk.CTkTextbox(notas_frame, height=100)
        widgets['text_notas'].pack(fill="x", padx=10, pady=10)
        if cliente[6]:
            widgets['text_notas'].insert("1.0", cliente[6])
        
        return widgets

    def crear_tab_contactos_cliente(self, tab_frame, cliente_id):
        """Crea la pestaña de contactos del cliente."""
        # Header con botón para agregar
        header_frame = ctk.CTkFrame(tab_frame)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="👥 Contactos del Cliente", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10, pady=10)
        
        btn_nuevo_contacto = ctk.CTkButton(header_frame, text="➕ Nuevo Contacto", 
                                         command=lambda: self.nuevo_contacto_cliente(cliente_id),
                                         width=120)
        btn_nuevo_contacto.pack(side="right", padx=10, pady=10)
        
        # Lista de contactos
        contactos_frame = ctk.CTkScrollableFrame(tab_frame, height=450)
        contactos_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Cargar y mostrar contactos
        contactos = self.obtener_contactos_cliente(cliente_id)
        
        if not contactos:
            ctk.CTkLabel(contactos_frame, 
                       text="📭 No hay contactos registrados para este cliente.\nHaz clic en 'Nuevo Contacto' para agregar uno.",
                       font=ctk.CTkFont(size=13)).pack(pady=50)
        else:
            for contacto in contactos:
                self.crear_item_contacto(contactos_frame, contacto, cliente_id)

    def crear_tab_historial_rmas(self, tab_frame, cliente_id):
        """Crea la pestaña de historial de RMAs."""
        from lib.cliente_utils import obtener_años_rmas_cliente, obtener_historial_rmas_cliente
        
        # Header
        header_frame = ctk.CTkFrame(tab_frame)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="📦 Historial de RMAs", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        # Frame de filtros
        filtros_frame = ctk.CTkFrame(header_frame)
        filtros_frame.pack(fill="x", padx=10, pady=5)
        
        # Búsqueda por número de RMA
        ctk.CTkLabel(filtros_frame, text="Buscar RMA:", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
        entry_buscar = ctk.CTkEntry(filtros_frame, placeholder_text="Número de RMA...", width=150)
        entry_buscar.pack(side="left", padx=5)
        
        # Filtro por año
        ctk.CTkLabel(filtros_frame, text="Año:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(20,5))
        
        # Obtener años disponibles
        años_disponibles = obtener_años_rmas_cliente(cliente_id, self.master.conectar_db)
        option_año = ctk.CTkOptionMenu(filtros_frame, values=["Todos"] + años_disponibles, width=100)
        option_año.set("Todos")
        option_año.pack(side="left", padx=5)
        
        # Lista de RMAs
        rmas_frame = ctk.CTkScrollableFrame(tab_frame, height=450)
        rmas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Función para filtrar y mostrar RMAs
        def actualizar_lista():
            for widget in rmas_frame.winfo_children():
                widget.destroy()
            
            busqueda = entry_buscar.get().strip().upper()
            año_filtro = option_año.get()
            
            rmas = obtener_historial_rmas_cliente(cliente_id, self.master.conectar_db, año_filtro if año_filtro != "Todos" else None, busqueda)
            
            if not rmas:
                ctk.CTkLabel(rmas_frame, 
                           text="📭 No se encontraron RMAs con los filtros especificados.",
                           font=ctk.CTkFont(size=13)).pack(pady=50)
            else:
                # Mostrar RMAs
                for rma in rmas:
                    numero_rma, fecha_emision, estado, motivo = rma
                    datos_rma = {
                        'info': rma,
                        'productos': []
                    }
                    self.crear_item_rma_historial(rmas_frame, numero_rma, datos_rma, cliente_id)
        
        # Botón filtrar
        btn_filtrar = ctk.CTkButton(filtros_frame, text="🔍 Filtrar", command=actualizar_lista, width=80)
        btn_filtrar.pack(side="left", padx=10)
        
        # Cargar lista inicial
        actualizar_lista()

    def crear_tab_notas_cliente(self, tab_frame, cliente_id):
        """Crea la pestaña de notas del cliente."""
        # Header con botón para agregar
        header_frame = ctk.CTkFrame(tab_frame)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="📝 Notas del Cliente", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10, pady=10)
        
        btn_nueva_nota = ctk.CTkButton(header_frame, text="➕ Nueva Nota", 
                                     command=lambda: self.nueva_nota_cliente(cliente_id),
                                     width=120)
        btn_nueva_nota.pack(side="right", padx=10, pady=10)
        
        # Lista de notas
        notas_frame = ctk.CTkScrollableFrame(tab_frame, height=450)
        notas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Cargar y mostrar notas
        notas = self.obtener_notas_cliente(cliente_id)
        
        if not notas:
            ctk.CTkLabel(notas_frame, 
                       text="📭 No hay notas registradas para este cliente.\nHaz clic en 'Nueva Nota' para agregar una.",
                       font=ctk.CTkFont(size=13)).pack(pady=50)
        else:
            for nota in notas:
                self.crear_item_nota(notas_frame, nota)

    def crear_tab_estadisticas_cliente_completa(self, tab_frame, cliente_id, nombre_cliente):
        """Crea la pestaña de estadísticas del cliente con filtros completos y exportación."""
        from lib.cliente_estadisticas import obtener_estadisticas_detalladas_cliente, exportar_estadisticas_cliente_excel
        from tkinter import filedialog
        from datetime import datetime
        
        # Header con controles
        header_frame = ctk.CTkFrame(tab_frame)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        # Título
        ctk.CTkLabel(header_frame, text="📊 Estadísticas Detalladas del Cliente", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        # Frame de filtros
        filtros_frame = ctk.CTkFrame(header_frame)
        filtros_frame.pack(fill="x", padx=10, pady=5)
        filtros_frame.grid_columnconfigure(1, weight=1)
        filtros_frame.grid_columnconfigure(3, weight=1)
        
        # Filtro de fecha desde
        ctk.CTkLabel(filtros_frame, text="Desde:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        entry_fecha_desde = ctk.CTkEntry(filtros_frame, placeholder_text="YYYY-MM-DD", width=120)
        entry_fecha_desde.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Filtro de fecha hasta
        ctk.CTkLabel(filtros_frame, text="Hasta:", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=5, pady=5, sticky="e")
        entry_fecha_hasta = ctk.CTkEntry(filtros_frame, placeholder_text="YYYY-MM-DD", width=120)
        entry_fecha_hasta.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Filtro de resultado de expediente
        ctk.CTkLabel(filtros_frame, text="Resultado:", font=ctk.CTkFont(size=11)).grid(row=0, column=4, padx=5, pady=5, sticky="e")
        filtro_estado = ctk.CTkOptionMenu(filtros_frame, 
                                         values=["Todos", "NO ABONAR", "ABONAR", "ABONAR OK", "ABONAR FALLO", "REPOSICION"],
                                         width=140)
        filtro_estado.set("Todos")
        filtro_estado.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        
        # Contenedor de resultados
        resultados_frame = ctk.CTkScrollableFrame(tab_frame, height=400)
        resultados_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Función para cargar datos
        def cargar_datos_estadisticas():
            # Limpiar resultados anteriores
            for widget in resultados_frame.winfo_children():
                widget.destroy()
            
            try:
                conn, cursor = self.master.conectar_db()
                if not conn:
                    return
                
                # Obtener filtros
                fecha_desde = entry_fecha_desde.get().strip() or None
                fecha_hasta = entry_fecha_hasta.get().strip() or None
                estado = filtro_estado.get()
                estado_filtro = None if estado == "Todos" else estado
                
                # Obtener datos
                datos = obtener_estadisticas_detalladas_cliente(
                    nombre_cliente, conn, fecha_desde, fecha_hasta, estado_filtro
                )
                
                if not datos:
                    ctk.CTkLabel(resultados_frame, 
                               text="📊 No hay datos para los filtros seleccionados.",
                               font=ctk.CTkFont(size=14)).pack(pady=50)
                    conn.close()
                    return
                
                # Calcular totales
                total_exp = len(datos)
                total_art = sum(row[4] for row in datos)
                total_coste = sum(row[5] for row in datos)
                
                # Mostrar resumen
                resumen_frame = ctk.CTkFrame(resultados_frame)
                resumen_frame.pack(fill="x", pady=(0,10))
                
                ctk.CTkLabel(resumen_frame, 
                           text=f"📦 Total: {total_exp} expedientes | 📦 {total_art} artículos | 💰 {total_coste:.2f} €",
                           font=ctk.CTkFont(size=13, weight="bold")).pack(pady=10)
                
                # Tabla de resultados
                tabla_frame = ctk.CTkFrame(resultados_frame)
                tabla_frame.pack(fill="both", expand=True)
                
                # Encabezados
                headers = ["Código RMA", "Fecha", "Estado", "Resultado", "Nº Art.", "Coste (€)"]
                header_row = ctk.CTkFrame(tabla_frame, fg_color=("#3B8ED0", "#1F6AA5"))
                header_row.pack(fill="x", padx=2, pady=2)
                
                for i, header in enumerate(headers):
                    ctk.CTkLabel(header_row, text=header, 
                               font=ctk.CTkFont(size=11, weight="bold"),
                               text_color="white").grid(row=0, column=i, padx=10, pady=5, sticky="w")
                
                # Datos
                for idx, row in enumerate(datos):
                    codigo, fecha, estado_exp, resultado, num_art, coste = row
                    
                    color_bg = ("#E8E8E8", "#2B2B2B") if idx % 2 == 0 else "transparent"
                    data_row = ctk.CTkFrame(tabla_frame, fg_color=color_bg)
                    data_row.pack(fill="x", padx=2, pady=1)
                    
                    ctk.CTkLabel(data_row, text=codigo, font=ctk.CTkFont(size=10)).grid(row=0, column=0, padx=10, pady=3, sticky="w")
                    ctk.CTkLabel(data_row, text=fecha or "", font=ctk.CTkFont(size=10)).grid(row=0, column=1, padx=10, pady=3, sticky="w")
                    ctk.CTkLabel(data_row, text=estado_exp or "", font=ctk.CTkFont(size=10)).grid(row=0, column=2, padx=10, pady=3, sticky="w")
                    ctk.CTkLabel(data_row, text=resultado or "", font=ctk.CTkFont(size=10)).grid(row=0, column=3, padx=10, pady=3, sticky="w")
                    ctk.CTkLabel(data_row, text=str(num_art), font=ctk.CTkFont(size=10)).grid(row=0, column=4, padx=10, pady=3, sticky="w")
                    ctk.CTkLabel(data_row, text=f"{coste:.2f} €", font=ctk.CTkFont(size=10)).grid(row=0, column=5, padx=10, pady=3, sticky="w")
                
                conn.close()
                
            except Exception as e:
                print(f"Error cargando estadísticas: {e}")
                messagebox.showerror("Error", f"Error al cargar estadísticas: {str(e)}")
        
        # Función para exportar a Excel
        def exportar_a_excel():
            try:
                conn, cursor = self.master.conectar_db()
                if not conn:
                    return
                
                # Obtener filtros
                fecha_desde = entry_fecha_desde.get().strip() or None
                fecha_hasta = entry_fecha_hasta.get().strip() or None
                estado = filtro_estado.get()
                estado_filtro = None if estado == "Todos" else estado
                
                # Obtener datos
                datos = obtener_estadisticas_detalladas_cliente(
                    nombre_cliente, conn, fecha_desde, fecha_hasta, estado_filtro
                )
                
                conn.close()
                
                if not datos:
                    messagebox.showinfo("Info", "No hay datos para exportar")
                    return
                
                # Solicitar ubicación de archivo
                fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"Estadisticas_{nombre_cliente.replace(' ', '_')}_{fecha_str}.xlsx"
                
                ruta = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx")],
                    initialfile=nombre_archivo
                )
                
                if ruta:
                    if exportar_estadisticas_cliente_excel(nombre_cliente, datos, ruta):
                        messagebox.showinfo("Éxito", f"Estadísticas exportadas correctamente a:\n{ruta}")
                    else:
                        messagebox.showerror("Error", "Error al exportar estadísticas")
                        
            except Exception as e:
                print(f"Error exportando: {e}")
                messagebox.showerror("Error", f"Error al exportar: {str(e)}")
        
        # Botones de acción
        botones_frame = ctk.CTkFrame(header_frame)
        botones_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(botones_frame, text="🔍 Buscar", 
                     command=cargar_datos_estadisticas,
                     width=120).pack(side="left", padx=5)
        
        ctk.CTkButton(botones_frame, text="📊 Exportar Excel", 
                     command=exportar_a_excel,
                     width=140).pack(side="left", padx=5)
        
        # Cargar datos iniciales
        cargar_datos_estadisticas()

    def crear_tab_condiciones_cliente(self, tab_frame, cliente_id):
        """Crea la pestaña de condiciones comerciales del cliente."""
        from lib.cliente_condiciones import cargar_condiciones_cliente, guardar_condiciones_cliente, validar_descuento
        
        # Frame principal
        main_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Cargar condiciones actuales
        try:
            conn, cursor = self.master.conectar_db()
            if conn:
                condiciones = cargar_condiciones_cliente(cliente_id, conn)
                conn.close()
            else:
                condiciones = {'descuento': 0.0, 'campo_reserva_1': "", 'campo_reserva_2': ""}
        except Exception as e:
            print(f"Error cargando condiciones: {e}")
            condiciones = {'descuento': 0.0, 'campo_reserva_1': "", 'campo_reserva_2': ""}
        
        # Grid layout compacto
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Campo Descuento
        ctk.CTkLabel(main_frame, text="Descuento (%):", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=8, padx=(0, 10))
        
        entry_descuento = ctk.CTkEntry(main_frame, placeholder_text="Ej: 10.5", width=150)
        entry_descuento.grid(row=0, column=1, sticky="w", pady=8)
        entry_descuento.insert(0, str(condiciones['descuento']) if condiciones['descuento'] else "0")
        
        # Campo Reserva 1
        ctk.CTkLabel(main_frame, text="Campo Reserva 1:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=8, padx=(0, 10))
        
        entry_reserva1 = ctk.CTkEntry(main_frame, placeholder_text="Información adicional", width=400)
        entry_reserva1.grid(row=1, column=1, sticky="w", pady=8)
        if condiciones['campo_reserva_1']:
            entry_reserva1.insert(0, condiciones['campo_reserva_1'])
        
        # Campo Reserva 2
        ctk.CTkLabel(main_frame, text="Campo Reserva 2:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, sticky="w", pady=8, padx=(0, 10))
        
        entry_reserva2 = ctk.CTkEntry(main_frame, placeholder_text="Información adicional", width=400)
        entry_reserva2.grid(row=2, column=1, sticky="w", pady=8)
        if condiciones['campo_reserva_2']:
            entry_reserva2.insert(0, condiciones['campo_reserva_2'])
        
        # Nota informativa
        ctk.CTkLabel(main_frame, 
                    text="ℹ️ Los cambios se guardarán con el botón 'Guardar Cambios' de la ficha",
                    font=ctk.CTkFont(size=10),
                    text_color="gray").grid(row=3, column=0, columnspan=2, sticky="w", pady=(15, 0))
        
        # Retornar widgets para posible uso externo
        return {
            'entry_descuento': entry_descuento,
            'entry_reserva1': entry_reserva1,
            'entry_reserva2': entry_reserva2
        }

    def crear_tab_asociaciones(self, tab_frame, rma_id):
        """Crea la pestaña de asociaciones de expedientes RMA."""
        # Frame principal scrollable
        scroll_frame = ctk.CTkScrollableFrame(tab_frame, label_text="Expedientes Asociados")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame para el encabezado con botón
        header_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(5, 15))
        
        ctk.CTkLabel(header_frame, 
                    text="🔗 Gestión de Asociaciones",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=5)
        
        # Botón para asociar nuevo expediente
        ctk.CTkButton(header_frame, 
                     text="➕ Asociar Expediente",
                     command=lambda: self.mostrar_dialogo_asociar_rma(rma_id),
                     width=150).pack(side="right", padx=5)
        
        # Frame para la lista de asociaciones
        self.asociaciones_list_frame = ctk.CTkFrame(scroll_frame)
        self.asociaciones_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Guardar el rma_id para refrescos
        self.asociaciones_rma_id = rma_id
        
        # Cargar asociaciones
        self.cargar_lista_asociaciones()

    def cargar_lista_asociaciones(self):
        """Carga y muestra la lista de expedientes asociados."""
        # Limpiar contenido anterior
        for widget in self.asociaciones_list_frame.winfo_children():
            widget.destroy()
        
        # Resetear selección
        self.fila_seleccionada_asoc = None
        self.frame_seleccionado_asoc = None
        
        if not hasattr(self, 'asociaciones_rma_id') or self.asociaciones_rma_id is None:
            ctk.CTkLabel(self.asociaciones_list_frame, 
                        text="No se puede cargar asociaciones",
                        text_color="red").pack(pady=20)
            return
        
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                ctk.CTkLabel(self.asociaciones_list_frame, 
                            text="Error de conexión a base de datos",
                            text_color="red").pack(pady=20)
                return
            
            # Obtener asociaciones
            asociaciones = rma_asociaciones.obtener_asociaciones(self.asociaciones_rma_id, conn)
            conn.close()
            
            if not asociaciones:
                ctk.CTkLabel(self.asociaciones_list_frame, 
                            text="No hay expedientes asociados",
                            text_color="gray",
                            font=ctk.CTkFont(size=12)).pack(pady=20)
                return
            
            # Crear encabezados de tabla
            headers_frame = ctk.CTkFrame(self.asociaciones_list_frame)
            headers_frame.pack(fill="x", padx=5, pady=(0, 5))
            
            ctk.CTkLabel(headers_frame, text="Código RMA", width=120, 
                        font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(headers_frame, text="Cliente", width=250, 
                        font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(headers_frame, text="Estado", width=120, 
                        font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(headers_frame, text="Motivo", width=200, 
                        font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(headers_frame, text="Acciones", width=150, 
                        font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            
            # Crear fila para cada asociación
            for asoc in asociaciones:
                self.crear_fila_asociacion(asoc)
                
        except Exception as e:
            logger.error(f"Error cargando asociaciones: {e}")
            ctk.CTkLabel(self.asociaciones_list_frame, 
                        text=f"Error: {str(e)}",
                        text_color="red").pack(pady=20)

    def crear_fila_asociacion(self, asoc):
        """Crea una fila visual para una asociación."""
        row_frame = ctk.CTkFrame(self.asociaciones_list_frame)
        row_frame.pack(fill="x", padx=5, pady=2)
        
        # Código RMA
        lbl_codigo = ctk.CTkLabel(row_frame, text=asoc['codigo_rma'], width=120)
        lbl_codigo.pack(side="left", padx=5, pady=5)
        
        # Cliente (truncado si es muy largo)
        cliente_texto = asoc['nombre_cliente'][:30] + "..." if len(asoc['nombre_cliente']) > 30 else asoc['nombre_cliente']
        lbl_cliente = ctk.CTkLabel(row_frame, text=cliente_texto, width=250)
        lbl_cliente.pack(side="left", padx=5, pady=5)
        
        # Estado
        lbl_estado = ctk.CTkLabel(row_frame, text=asoc['estado_expediente'], width=120)
        lbl_estado.pack(side="left", padx=5, pady=5)
        
        # Motivo (truncado si es muy largo)
        motivo_texto = asoc['motivo'][:25] + "..." if len(asoc['motivo']) > 25 else asoc['motivo'] if asoc['motivo'] else "-"
        lbl_motivo = ctk.CTkLabel(row_frame, text=motivo_texto, width=200)
        lbl_motivo.pack(side="left", padx=5, pady=5)
        
        # Botones de acciones
        acciones_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        acciones_frame.pack(side="left", padx=5, pady=5)
        
        btn_ver = ctk.CTkButton(acciones_frame, 
                     text="👁️",
                     width=40,
                     command=lambda: self.abrir_rma_asociado(asoc['rma_id']))
        btn_ver.pack(side="left", padx=2)
        
        btn_eliminar = ctk.CTkButton(acciones_frame, 
                     text="❌",
                     width=40,
                     fg_color="darkred",
                     hover_color="red",
                     command=lambda: self.desasociar_expediente(asoc['rma_id']))
        btn_eliminar.pack(side="left", padx=2)
        
        # Implementar selección con clic simple
        rma_id = asoc['rma_id']
        
        def _seleccionar_fila_asoc(e):
            # Deseleccionar fila anterior
            if hasattr(self, 'fila_seleccionada_asoc') and hasattr(self, 'frame_seleccionado_asoc'):
                try:
                    self.frame_seleccionado_asoc.configure(fg_color="transparent")
                except Exception:
                    pass
            
            # Obtener color de selección
            try:
                modo = ctk.get_appearance_mode()
                color_seleccion = ("#D6EAF8" if modo == "Light" else "#2C5F8D")
            except Exception:
                color_seleccion = "#D6EAF8"
            
            # Seleccionar nueva fila
            row_frame.configure(fg_color=color_seleccion)
            
            # Guardar referencia
            self.fila_seleccionada_asoc = rma_id
            self.frame_seleccionado_asoc = row_frame
        
        def _on_enter_asoc(e):
            if not hasattr(self, 'fila_seleccionada_asoc') or self.fila_seleccionada_asoc != rma_id:
                try:
                    modo = ctk.get_appearance_mode()
                    hover_color = ("#F5F5F5" if modo == "Light" else "#2B2B2B")
                except Exception:
                    hover_color = "#F5F5F5"
                row_frame.configure(fg_color=hover_color)
        
        def _on_leave_asoc(e):
            if not hasattr(self, 'fila_seleccionada_asoc') or self.fila_seleccionada_asoc != rma_id:
                row_frame.configure(fg_color="transparent")
        
        # Bind eventos
        row_frame.bind("<Button-1>", _seleccionar_fila_asoc)
        row_frame.bind("<Double-Button-1>", lambda e: self.abrir_rma_asociado(rma_id))
        row_frame.bind("<Enter>", _on_enter_asoc)
        row_frame.bind("<Leave>", _on_leave_asoc)
        row_frame.configure(cursor="hand2")
        
        # Bind a labels también
        for lbl in [lbl_codigo, lbl_cliente, lbl_estado, lbl_motivo]:
            lbl.bind("<Button-1>", _seleccionar_fila_asoc)
            lbl.bind("<Double-Button-1>", lambda e: self.abrir_rma_asociado(rma_id))
            lbl.configure(cursor="hand2")

    def mostrar_dialogo_asociar_rma(self, rma_id):
        """Muestra un diálogo para buscar y asociar un expediente RMA."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Asociar Expediente")
        dlg.geometry("700x500")
        dlg.grab_set()
        
        # Frame de búsqueda
        search_frame = ctk.CTkFrame(dlg)
        search_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(search_frame, 
                    text="Buscar por Código RMA o Cliente:",
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
        
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Escriba para buscar...")
        search_entry.pack(fill="x", pady=5)
        
        # Frame para resultados
        resultados_frame = ctk.CTkScrollableFrame(dlg, label_text="Resultados de Búsqueda")
        resultados_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Frame para motivo
        motivo_frame = ctk.CTkFrame(dlg)
        motivo_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(motivo_frame, 
                    text="Motivo de Asociación (opcional):",
                    font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 5))
        
        motivo_entry = ctk.CTkEntry(motivo_frame, placeholder_text="Ej: Mismo cliente, misma incidencia...")
        motivo_entry.pack(fill="x", pady=5)
        
        # Variable para almacenar el RMA seleccionado
        rma_seleccionado = {'id': None}
        
        def buscar_rmas():
            """Busca RMAs según el término ingresado."""
            termino = search_entry.get().strip()
            
            # Limpiar resultados anteriores
            for widget in resultados_frame.winfo_children():
                widget.destroy()
            
            if len(termino) < 2:
                ctk.CTkLabel(resultados_frame, 
                            text="Escriba al menos 2 caracteres para buscar",
                            text_color="gray").pack(pady=20)
                return
            
            try:
                conn, cursor = self.master.conectar_db()
                if not conn:
                    ctk.CTkLabel(resultados_frame, 
                                text="Error de conexión",
                                text_color="red").pack(pady=20)
                    return
                
                resultados = rma_asociaciones.buscar_rmas_para_asociar(termino, rma_id, conn)
                conn.close()
                
                if not resultados:
                    ctk.CTkLabel(resultados_frame, 
                                text="No se encontraron expedientes",
                                text_color="gray").pack(pady=20)
                    return
                
                # Mostrar resultados
                for rma in resultados:
                    resultado_row = ctk.CTkFrame(resultados_frame)
                    resultado_row.pack(fill="x", padx=5, pady=2)
                    
                    info_text = f"{rma['codigo_rma']} - {rma['nombre_cliente']} ({rma['estado_expediente']})"
                    ctk.CTkLabel(resultado_row, text=info_text, anchor="w").pack(side="left", padx=10, pady=8, fill="x", expand=True)
                    
                    def seleccionar(rma_data=rma):
                        rma_seleccionado['id'] = rma_data['id']
                        # Resaltar selección
                        for child in resultados_frame.winfo_children():
                            child.configure(fg_color="transparent")
                        resultado_row.configure(fg_color=("gray75", "gray25"))
                    
                    ctk.CTkButton(resultado_row, 
                                 text="Seleccionar",
                                 width=100,
                                 command=seleccionar).pack(side="right", padx=5, pady=5)
                
            except Exception as e:
                logger.error(f"Error buscando RMAs: {e}")
                ctk.CTkLabel(resultados_frame, 
                            text=f"Error: {str(e)}",
                            text_color="red").pack(pady=20)
        
        # Buscar al escribir (con delay)
        search_entry.bind('<KeyRelease>', lambda e: self.after(500, buscar_rmas))
        
        # Botones de acción
        botones_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        botones_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        def confirmar_asociacion():
            """Confirma y crea la asociación."""
            if rma_seleccionado['id'] is None:
                messagebox.showwarning("Selección Requerida", "Debe seleccionar un expediente para asociar")
                return
            
            motivo = motivo_entry.get().strip()
            
            try:
                conn, cursor = self.master.conectar_db()
                if not conn:
                    messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                    return
                
                exito, mensaje = rma_asociaciones.asociar_expedientes(
                    rma_id, 
                    rma_seleccionado['id'], 
                    motivo, 
                    self.username, 
                    conn
                )
                
                conn.close()
                
                if exito:
                    messagebox.showinfo("Éxito", mensaje)
                    dlg.destroy()
                    # Refrescar lista de asociaciones
                    if hasattr(self, 'cargar_lista_asociaciones'):
                        self.cargar_lista_asociaciones()
                else:
                    messagebox.showerror("Error", mensaje)
                    
            except Exception as e:
                logger.error(f"Error al asociar expedientes: {e}")
                messagebox.showerror("Error", f"Error inesperado: {str(e)}")
        
        ctk.CTkButton(botones_frame, 
                     text="✓ Asociar",
                     command=confirmar_asociacion).pack(side="left", padx=5)
        
        ctk.CTkButton(botones_frame, 
                     text="✗ Cancelar",
                     command=dlg.destroy).pack(side="left", padx=5)

    def abrir_rma_asociado(self, rma_id):
        """Abre un expediente asociado en una nueva ventana independiente."""
        try:
            # Guardar el content_frame actual
            content_frame_original = self.content_frame
            
            # Crear una nueva ventana independiente
            ventana_rma = ctk.CTkToplevel(self)
            ventana_rma.title(f"Expediente Asociado")
            ventana_rma.geometry("1400x900")
            
            # Crear un nuevo content_frame en la ventana nueva
            nuevo_content_frame = ctk.CTkFrame(ventana_rma)
            nuevo_content_frame.pack(fill="both", expand=True)
            nuevo_content_frame.grid_rowconfigure(0, weight=1)
            nuevo_content_frame.grid_columnconfigure(0, weight=1)
            
            # Temporalmente reemplazar el content_frame
            self.content_frame = nuevo_content_frame
            
            # Mostrar el expediente en el nuevo frame
            self.mostrar_nuevo_rma(rma_id)
            
            # Actualizar título con información del RMA
            try:
                conn, cursor = self.master.conectar_db()
                if conn:
                    cursor.execute("SELECT codigo_rma, cliente FROM rma_maestro WHERE id = ?", (rma_id,))
                    row = cursor.fetchone()
                    if row:
                        ventana_rma.title(f"Expediente Asociado - {row[0]} - {row[1]}")
                    conn.close()
            except:
                pass
            
            # Restaurar el content_frame original cuando se cierre la ventana
            def al_cerrar():
                self.content_frame = content_frame_original
                ventana_rma.destroy()
            
            ventana_rma.protocol("WM_DELETE_WINDOW", al_cerrar)
            
        except Exception as e:
            # Restaurar el content_frame original en caso de error
            self.content_frame = content_frame_original
            logger.error(f"Error abriendo RMA asociado: {e}")
            messagebox.showerror("Error", f"No se pudo abrir el expediente: {str(e)}")

    def desasociar_expediente(self, rma_asociado_id):
        """Elimina la asociación con un expediente."""
        # Confirmar acción
        if not messagebox.askyesno("Confirmar", 
                                  "¿Está seguro de que desea eliminar esta asociación?"):
            return
        
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            
            exito, mensaje = rma_asociaciones.desasociar_expedientes(
                self.asociaciones_rma_id, 
                rma_asociado_id, 
                conn
            )
            
            conn.close()
            
            if exito:
                messagebox.showinfo("Éxito", mensaje)
                # Refrescar lista
                if hasattr(self, 'cargar_lista_asociaciones'):
                    self.cargar_lista_asociaciones()
            else:
                messagebox.showerror("Error", mensaje)
                
        except Exception as e:
            logger.error(f"Error al desasociar expedientes: {e}")
            messagebox.showerror("Error", f"Error inesperado: {str(e)}")

    def mostrar_ventana_asociaciones(self, rma_id):
        """Muestra una ventana emergente con todas las asociaciones del expediente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            
            # Obtener información del RMA principal
            cursor.execute("SELECT codigo_rma, cliente FROM rma_maestro WHERE id = ?", (rma_id,))
            rma_info = cursor.fetchone()
            if not rma_info:
                conn.close()
                messagebox.showerror("Error", "No se encontró el expediente")
                return
            
            codigo_rma, nombre_cliente = rma_info
            
            # Obtener asociaciones
            asociaciones = rma_asociaciones.obtener_asociaciones(rma_id, conn)
            conn.close()
            
            if not asociaciones:
                messagebox.showinfo("Sin Asociaciones", 
                                  f"El expediente {codigo_rma} no tiene asociaciones.")
                return
            
            # Crear ventana emergente
            dlg = ctk.CTkToplevel(self)
            dlg.title(f"Asociaciones de {codigo_rma}")
            dlg.geometry("650x400")
            dlg.grab_set()
            
            # Encabezado
            header_frame = ctk.CTkFrame(dlg)
            header_frame.pack(fill="x", padx=15, pady=15)
            
            ctk.CTkLabel(header_frame, 
                        text=f"Expedientes asociados a: {codigo_rma}",
                        font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            
            ctk.CTkLabel(header_frame, 
                        text=f"Cliente: {nombre_cliente}",
                        font=ctk.CTkFont(size=11),
                        text_color="gray").pack(anchor="w", pady=(2, 0))
            
            # Frame scrollable para la lista
            lista_frame = ctk.CTkScrollableFrame(dlg, label_text=f"Total: {len(asociaciones)} asociación(es)")
            lista_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            # Configurar columnas de la grilla
            lista_frame.grid_columnconfigure(0, weight=1, minsize=120)  # Código RMA
            lista_frame.grid_columnconfigure(1, weight=2, minsize=200)  # Cliente
            lista_frame.grid_columnconfigure(2, weight=1, minsize=150)  # Estado
            lista_frame.grid_columnconfigure(3, weight=0, minsize=80)   # Botón Abrir
            
            # Encabezados
            header_font = ctk.CTkFont(weight="bold", size=11)
            ctk.CTkLabel(lista_frame, text="CÓDIGO RMA", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(lista_frame, text="CLIENTE", font=header_font).grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(lista_frame, text="ESTADO", font=header_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(lista_frame, text="", font=header_font).grid(row=0, column=3, padx=5, pady=5, sticky="w")
            
            # Listar asociaciones
            for idx, asoc in enumerate(asociaciones, start=1):
                row_frame = ctk.CTkFrame(lista_frame, fg_color="transparent")
                row_frame.grid(row=idx, column=0, columnspan=4, sticky="ew", padx=2, pady=2)
                row_frame.grid_columnconfigure(0, weight=1, minsize=120)
                row_frame.grid_columnconfigure(1, weight=2, minsize=200)
                row_frame.grid_columnconfigure(2, weight=1, minsize=150)
                row_frame.grid_columnconfigure(3, weight=0, minsize=80)
                
                # Datos
                ctk.CTkLabel(row_frame, text=asoc['codigo_rma'], anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(row_frame, text=asoc['nombre_cliente'], anchor="w").grid(row=0, column=1, padx=5, pady=5, sticky="w")
                
                # Estado con color
                color_estado = self.get_color_por_estado(asoc['estado_expediente'])
                ctk.CTkLabel(row_frame, text=asoc['estado_expediente'], 
                           text_color=color_estado, anchor="w").grid(row=0, column=2, padx=5, pady=5, sticky="w")
                
                # Botón abrir
                btn_abrir = ctk.CTkButton(row_frame, text="👁 Abrir", width=70,
                                         command=lambda aid=asoc['rma_id']: self.abrir_rma_asociado_desde_ventana(aid, dlg))
                btn_abrir.grid(row=0, column=3, padx=5, pady=2)
            
            # Botón cerrar
            ctk.CTkButton(dlg, text="Cerrar", command=dlg.destroy).pack(pady=(0, 15))
            
        except Exception as e:
            logger.error(f"Error al mostrar ventana de asociaciones: {e}")
            messagebox.showerror("Error", f"Error al cargar asociaciones: {str(e)}")

    def abrir_rma_asociado_desde_ventana(self, rma_asociado_id, ventana_padre):
        """Abre un expediente asociado en una nueva ventana independiente desde la ventana de asociaciones."""
        ventana_padre.destroy()  # Cerrar la ventana de asociaciones primero
        self.abrir_rma_asociado(rma_asociado_id)  # Luego abrir el expediente

    def cargar_estadisticas_cliente(self, cliente_id):
        """Carga las estadísticas del cliente con filtros aplicados."""
        # Limpiar contenido anterior
        for widget in self.stats_container.winfo_children():
            widget.destroy()
        
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                return
            
            # Obtener nombre del cliente
            cursor.execute("SELECT nombre FROM clientes WHERE cliente_id = ?", (cliente_id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return
            
            cliente_nombre = cliente_result[0]
            
            # Construir filtros de fecha
            filtro_año = self.filtro_año_stats.get()
            filtro_mes = self.filtro_mes_stats.get()
            
            where_fecha = ""
            params = [cliente_nombre]
            
            if filtro_año != "Todos":
                where_fecha += " AND strftime('%Y', fecha_emision) = ?"
                params.append(filtro_año)
            
            if filtro_mes != "Todos":
                mes_num = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"][
                    ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(filtro_mes)
                ]
                where_fecha += " AND strftime('%m', fecha_emision) = ?"
                params.append(mes_num)
            
            # Consulta principal: desglose por resultado_expediente
            query_resultados = f"""
                SELECT 
                    resultado_expediente,
                    COUNT(*) as cantidad,
                    SUM(COALESCE(precio_total_expediente, 0)) as total_importe,
                    AVG(COALESCE(precio_total_expediente, 0)) as importe_promedio
                FROM rma_maestro 
                WHERE cliente = ? {where_fecha}
                GROUP BY resultado_expediente
                ORDER BY cantidad DESC
            """
            
            cursor.execute(query_resultados, params)
            resultados = cursor.fetchall()
            
            if not resultados:
                ctk.CTkLabel(self.stats_container, 
                           text="📊 No hay datos para los filtros seleccionados.",
                           font=ctk.CTkFont(size=14)).pack(pady=50)
            else:
                self.mostrar_desglose_resultados(resultados)
                
                # Consulta adicional: estadísticas generales
                query_generales = f"""
                    SELECT 
                        COUNT(*) as total_expedientes,
                        SUM(COALESCE(precio_total_expediente, 0)) as importe_total,
                        AVG(COALESCE(precio_total_expediente, 0)) as importe_promedio,
                        MIN(fecha_emision) as primer_expediente,
                        MAX(fecha_emision) as ultimo_expediente
                    FROM rma_maestro 
                    WHERE cliente = ? {where_fecha}
                """
                
                cursor.execute(query_generales, params)
                generales = cursor.fetchone()
                
                if generales:
                    self.mostrar_estadisticas_generales(generales)
            
            conn.close()
            
        except Exception as e:
            print(f"Error cargando estadísticas: {e}")
            import traceback
            print(traceback.format_exc())

    def mostrar_desglose_resultados(self, resultados):
        """Muestra el desglose por tipo de resultado de expediente."""
        # Frame para desglose
        desglose_frame = ctk.CTkFrame(self.stats_container)
        desglose_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(desglose_frame, text="📋 Desglose por Resultado de Expediente", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Tabla
        tabla_frame = ctk.CTkFrame(desglose_frame)
        tabla_frame.pack(fill="x", padx=10, pady=10)
        
        # Headers
        headers = ["Resultado", "Cantidad", "Importe Total", "Importe Promedio"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(tabla_frame, text=header, 
                        font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=10, pady=5, sticky="ew")
        
        # Datos
        total_cantidad = 0
        total_importe = 0
        
        for row, (resultado, cantidad, importe_total, importe_promedio) in enumerate(resultados, 1):
            resultado_texto = resultado if resultado else "Sin Resultado"
            
            # Convertir a tipos correctos
            cantidad = int(cantidad) if cantidad is not None else 0
            importe_total = float(importe_total) if importe_total is not None else 0.0
            importe_promedio = float(importe_promedio) if importe_promedio is not None else 0.0
            
            ctk.CTkLabel(tabla_frame, text=resultado_texto).grid(row=row, column=0, padx=10, pady=2, sticky="ew")
            ctk.CTkLabel(tabla_frame, text=str(cantidad)).grid(row=row, column=1, padx=10, pady=2, sticky="ew")
            ctk.CTkLabel(tabla_frame, text=f"€{importe_total:.2f}").grid(row=row, column=2, padx=10, pady=2, sticky="ew")
            ctk.CTkLabel(tabla_frame, text=f"€{importe_promedio:.2f}").grid(row=row, column=3, padx=10, pady=2, sticky="ew")
            
            total_cantidad += cantidad
            total_importe += importe_total
        
        # Totales
        separator_frame = ctk.CTkFrame(tabla_frame, height=2)
        separator_frame.grid(row=len(resultados)+1, column=0, columnspan=4, sticky="ew", pady=5)
        
        ctk.CTkLabel(tabla_frame, text="TOTAL", 
                    font=ctk.CTkFont(weight="bold")).grid(row=len(resultados)+2, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(tabla_frame, text=str(total_cantidad), 
                    font=ctk.CTkFont(weight="bold")).grid(row=len(resultados)+2, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(tabla_frame, text=f"€{total_importe:.2f}", 
                    font=ctk.CTkFont(weight="bold")).grid(row=len(resultados)+2, column=2, padx=10, pady=5, sticky="ew")
        
        # Configurar columnas
        for col in range(4):
            tabla_frame.grid_columnconfigure(col, weight=1)

    def mostrar_estadisticas_generales(self, generales):
        """Muestra estadísticas generales del cliente."""
        total_exp, importe_total, importe_prom, primer_exp, ultimo_exp = generales
        
        # Convertir a tipos correctos
        total_exp = int(total_exp) if total_exp is not None else 0
        importe_total = float(importe_total) if importe_total is not None else 0.0
        importe_prom = float(importe_prom) if importe_prom is not None else 0.0
        
        # Frame para estadísticas generales
        generales_frame = ctk.CTkFrame(self.stats_container)
        generales_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(generales_frame, text="📈 Estadísticas Generales", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Grid para estadísticas
        stats_grid = ctk.CTkFrame(generales_frame)
        stats_grid.pack(fill="x", padx=10, pady=10)
        stats_grid.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Tarjetas de estadísticas
        self.crear_tarjeta_stat(stats_grid, "📊 Total Expedientes", str(total_exp), 0, 0)
        self.crear_tarjeta_stat(stats_grid, "💰 Importe Total", f"€{importe_total:.2f}", 0, 1)
        self.crear_tarjeta_stat(stats_grid, "📊 Importe Promedio", f"€{importe_prom:.2f}", 0, 2)
        
        if primer_exp:
            fecha_primer = str(primer_exp)[:10] if primer_exp else "N/A"
            self.crear_tarjeta_stat(stats_grid, "📅 Primer Expediente", fecha_primer, 1, 0)
        if ultimo_exp:
            fecha_ultimo = str(ultimo_exp)[:10] if ultimo_exp else "N/A"
            self.crear_tarjeta_stat(stats_grid, "📅 Último Expediente", fecha_ultimo, 1, 1)

    def crear_tarjeta_stat(self, parent, titulo, valor, row, col):
        """Crea una tarjeta de estadística."""
        tarjeta = ctk.CTkFrame(parent)
        tarjeta.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(tarjeta, text=titulo, font=ctk.CTkFont(size=11)).pack(pady=(5,0))
        ctk.CTkLabel(tarjeta, text=valor, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0,5))

    def exportar_estadisticas_excel(self, cliente_id):
        """Exporta las estadísticas del cliente a Excel."""
        try:
            # Verificar si pandas está disponible
            if not HAS_PANDAS:
                messagebox.showerror("Error", "Pandas no está instalado. Instale pandas para exportar a Excel:\npip install pandas openpyxl")
                return
            
            # Verificar si openpyxl está disponible
            try:
                import openpyxl
            except ImportError:
                messagebox.showerror("Error", "OpenPyXL no está instalado. Instale openpyxl para exportar a Excel:\npip install openpyxl")
                return
            
            conn, cursor = self.master.conectar_db()
            if not conn:
                return
            
            # Obtener nombre del cliente
            cursor.execute("SELECT nombre FROM clientes WHERE cliente_id = ?", (cliente_id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return
            
            cliente_nombre = cliente_result[0]
            
            # Construir filtros de fecha
            filtro_año = self.filtro_año_stats.get()
            filtro_mes = self.filtro_mes_stats.get()
            
            where_fecha = ""
            params = [cliente_nombre]
            
            if filtro_año != "Todos":
                where_fecha += " AND strftime('%Y', fecha_emision) = ?"
                params.append(filtro_año)
            
            if filtro_mes != "Todos":
                mes_num = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"][
                    ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(filtro_mes)
                ]
                where_fecha += " AND strftime('%m', fecha_emision) = ?"
                params.append(mes_num)
            
            # Consulta para datos detallados
            query_detalle = f"""
                SELECT 
                    codigo_rma,
                    fecha_emision,
                    resultado_expediente,
                    estado,
                    precio_total_expediente,
                    obs_tecnica
                FROM rma_maestro 
                WHERE cliente = ? {where_fecha}
                ORDER BY fecha_emision DESC
            """
            
            cursor.execute(query_detalle, params)
            datos_detalle = cursor.fetchall()
            
            # Crear DataFrame
            import pandas as pd
            df = pd.DataFrame(datos_detalle, columns=[
                'Código RMA', 'Fecha Emisión', 'Resultado Expediente', 
                'Estado', 'Precio Total', 'Observaciones Técnicas'
            ])
            
            # Crear nombre de archivo
            filtro_texto = ""
            if filtro_año != "Todos":
                filtro_texto += f"_{filtro_año}"
            if filtro_mes != "Todos":
                filtro_texto += f"_{filtro_mes}"
            
            nombre_archivo = f"Estadisticas_{cliente_nombre.replace(' ', '_')}{filtro_texto}.xlsx"
            
            # Guardar archivo con formato mejorado
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                # Escribir hoja de expedientes
                df.to_excel(writer, sheet_name='Expedientes', index=False)
                
                # Crear hoja de resumen
                query_resumen = f"""
                    SELECT 
                        resultado_expediente,
                        COUNT(*) as cantidad,
                        SUM(COALESCE(precio_total_expediente, 0)) as total_importe
                    FROM rma_maestro 
                    WHERE cliente = ? {where_fecha}
                    GROUP BY resultado_expediente
                    ORDER BY cantidad DESC
                """
                
                cursor.execute(query_resumen, params)
                datos_resumen = cursor.fetchall()
                
                df_resumen = pd.DataFrame(datos_resumen, columns=['Resultado', 'Cantidad', 'Importe Total'])
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Ajustar el ancho de las columnas automáticamente
                workbook = writer.book
                
                # Ajustar columnas de la hoja Expedientes
                worksheet_expedientes = writer.sheets['Expedientes']
                for column in worksheet_expedientes.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    # Establecer un ancho mínimo y máximo para las columnas
                    adjusted_width = min(max(max_length + 2, 10), 50)
                    worksheet_expedientes.column_dimensions[column_letter].width = adjusted_width
                
                # Ajustar columnas de la hoja Resumen
                worksheet_resumen = writer.sheets['Resumen']
                for column in worksheet_resumen.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    # Establecer un ancho mínimo y máximo para las columnas
                    adjusted_width = min(max(max_length + 2, 12), 40)
                    worksheet_resumen.column_dimensions[column_letter].width = adjusted_width
                
                # Aplicar formato a los headers (primera fila)
                from openpyxl.styles import Font, PatternFill, Alignment
                
                # Formato para headers
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                center_alignment = Alignment(horizontal="center", vertical="center")
                
                # Aplicar formato a headers de Expedientes
                for cell in worksheet_expedientes[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_alignment
                
                # Aplicar formato a headers de Resumen
                for cell in worksheet_resumen[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_alignment
                
                # Aplicar formato de moneda a las columnas de importes
                from openpyxl.styles import NamedStyle
                
                # Estilo para moneda
                currency_style = NamedStyle(name="currency_style")
                currency_style.number_format = '€#,##0.00'
                
                # Aplicar formato de moneda a la columna "Precio Total" en Expedientes (columna E)
                for row in range(2, len(df) + 2):
                    cell = worksheet_expedientes[f'E{row}']
                    cell.style = currency_style
                
                # Aplicar formato de moneda a la columna "Importe Total" en Resumen (columna C)
                for row in range(2, len(df_resumen) + 2):
                    cell = worksheet_resumen[f'C{row}']
                    cell.style = currency_style
            
            conn.close()
            
            messagebox.showinfo("Exportación Exitosa", f"Estadísticas exportadas a:\n{nombre_archivo}")
            
        except Exception as e:
            print(f"Error exportando a Excel: {e}")
            messagebox.showerror("Error", f"Error al exportar a Excel:\n{str(e)}")

    def crear_item_contacto(self, parent_frame, contacto, cliente_id):
        """Crea un elemento visual minimalista para un contacto."""
        contacto_id, nombre, cargo, email, telefono, es_principal, activo = contacto
        
        # Frame principal con borde sutil
        contacto_frame = ctk.CTkFrame(parent_frame, fg_color=("gray90", "gray20"))
        contacto_frame.pack(fill="x", padx=5, pady=3)
        
        # Contenedor principal horizontal
        main_container = ctk.CTkFrame(contacto_frame, fg_color="transparent")
        main_container.pack(fill="x", padx=10, pady=8)
        
        # Columna izquierda: Información del contacto
        info_column = ctk.CTkFrame(main_container, fg_color="transparent")
        info_column.pack(side="left", fill="x", expand=True)
        
        # Nombre
        nombre_label = ctk.CTkLabel(
            info_column, 
            text=nombre,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        nombre_label.pack(anchor="w", pady=(0, 2))
        
        # Cargo (si existe)
        if cargo:
            cargo_label = ctk.CTkLabel(
                info_column,
                text=f"💼 {cargo}",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            )
            cargo_label.pack(anchor="w", pady=(0, 2))
        
        # Email y Teléfono en una sola línea
        contact_info_parts = []
        if email:
            contact_info_parts.append(f"📧 {email}")
        if telefono:
            contact_info_parts.append(f"📞 {telefono}")
        
        if contact_info_parts:
            contact_text = " • ".join(contact_info_parts)
            contact_label = ctk.CTkLabel(
                info_column,
                text=contact_text,
                font=ctk.CTkFont(size=11),
                text_color=("gray60", "gray40")
            )
            contact_label.pack(anchor="w")
        
        # Columna derecha: Botones de acción compactos
        actions_column = ctk.CTkFrame(main_container, fg_color="transparent")
        actions_column.pack(side="right", padx=(10, 0))
        
        # Botón editar
        btn_editar = ctk.CTkButton(
            actions_column,
            text="✏️",
            command=lambda: self.editar_contacto_cliente(contacto_id, cliente_id),
            width=32,
            height=32,
            fg_color=("gray70", "gray30"),
            hover_color=("#3b82f6", "#2563eb")
        )
        btn_editar.pack(side="left", padx=2)
        Tooltip(btn_editar, "Editar contacto")
        
        # Botón eliminar
        btn_eliminar = ctk.CTkButton(
            actions_column,
            text="🗑️",
            command=lambda: self.eliminar_contacto_cliente(contacto_id, cliente_id, nombre),
            width=32,
            height=32,
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c")
        )
        btn_eliminar.pack(side="left", padx=2)
        Tooltip(btn_eliminar, "Eliminar contacto")

    def crear_item_rma_historial(self, parent_frame, numero_rma, datos, cliente_id=None):
        """Crea un elemento visual para un RMA en el historial."""
        from lib.cliente_utils import abrir_rma_por_codigo
        
        info = datos['info']  # número, fecha, estado, motivo
        productos = datos['productos']
        
        rma_frame = ctk.CTkFrame(parent_frame)
        rma_frame.pack(fill="x", padx=5, pady=5)
        
        header_frame = ctk.CTkFrame(rma_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        # Información principal del RMA
        info_principal = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_principal.pack(fill="x")
        
        label_rma = ctk.CTkLabel(info_principal, text=f"📦 RMA #{numero_rma}", 
                    font=ctk.CTkFont(size=14, weight="bold"), cursor="hand2")
        label_rma.pack(side="left")
        
        # Doble clic para abrir expediente
        def abrir_expediente(e):
            abrir_rma_por_codigo(numero_rma, self.master.conectar_db, self)
        
        label_rma.bind("<Double-Button-1>", abrir_expediente)
        Tooltip(label_rma, "Doble clic para abrir el expediente")
        
        # Estado del RMA
        estado_color = {"Abierto": "orange", "En Proceso": "blue", "Cerrado": "green", "Cancelado": "red"}.get(info[2], "gray")
        ctk.CTkLabel(info_principal, text=f"🏷️ {info[2]}", 
                    font=ctk.CTkFont(size=11), text_color=estado_color).pack(side="right")
        
        # Fecha - manejo robusto
        try:
            fecha_str = str(info[1])
            if ' ' in fecha_str:
                fecha_mostrar = fecha_str.split()[0]  # Solo la parte de la fecha
            else:
                fecha_mostrar = fecha_str  # Si no tiene espacios, usar toda la cadena
        except (IndexError, AttributeError):
            fecha_mostrar = "Sin fecha"
        
        ctk.CTkLabel(info_principal, text=f"📅 {fecha_mostrar}", 
                    font=ctk.CTkFont(size=11), text_color="gray").pack(side="right", padx=(0,10))
        
        # Motivo
        if info[3]:
            motivo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            motivo_frame.pack(fill="x", pady=(5,0))
            ctk.CTkLabel(motivo_frame, text=f"📝 Motivo: {info[3]}", 
                        font=ctk.CTkFont(size=11)).pack(side="left")
        
        # Productos (si los hay)
        if productos:
            productos_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            productos_frame.pack(fill="x", pady=(5,0))
            
            ctk.CTkLabel(productos_frame, text=f"📦 Productos ({len(productos)}):", 
                        font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            
            for producto, cantidad, precio, estado in productos[:3]:  # Mostrar máximo 3
                prod_text = f"  • {producto} (Cant: {cantidad}"
                if precio:
                    prod_text += f", €{precio}"
                if estado:
                    prod_text += f", Estado: {estado}"
                prod_text += ")"
                
                ctk.CTkLabel(productos_frame, text=prod_text, 
                            font=ctk.CTkFont(size=10)).pack(anchor="w")
            
            if len(productos) > 3:
                ctk.CTkLabel(productos_frame, text=f"  ... y {len(productos)-3} más", 
                            font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")

    def crear_item_nota(self, parent_frame, nota, parent_window=None):
        """Crea un elemento visual para una nota."""
        # Estructura correcta: nota_id, titulo, contenido, tipo, fecha, usuario, privada
        nota_id, titulo, contenido, tipo, fecha, usuario, privada = nota
        
        nota_frame = ctk.CTkFrame(parent_frame)
        nota_frame.pack(fill="x", padx=5, pady=5)
        
        header_frame = ctk.CTkFrame(nota_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        # Título y tipo
        titulo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        titulo_frame.pack(fill="x")
        
        titulo_icon = "🔒" if privada else "📝"
        ctk.CTkLabel(titulo_frame, text=f"{titulo_icon} {titulo}", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        tipo_color = {
            "General": "blue", 
            "Incidencia": "red", 
            "Comercial": "green", 
            "Técnica": "orange"
        }.get(tipo, "gray")
        ctk.CTkLabel(titulo_frame, text=f"🏷️ {tipo}", 
                    font=ctk.CTkFont(size=11), text_color=tipo_color).pack(side="right")
        
        # Fecha y usuario
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=(5,0))
        
        fecha_formateada = fecha.split(' ')[0] if fecha else "Sin fecha"
        ctk.CTkLabel(info_frame, text=f"📅 {fecha_formateada} | 👤 {usuario}", 
                    font=ctk.CTkFont(size=10), text_color="gray").pack(side="left")
        
        # Botones de acción
        botones_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        botones_frame.pack(side="right")
        
        btn_ver = ctk.CTkButton(botones_frame, text="👁️", width=30, height=25,
                               command=lambda: self.ver_nota_completa(nota))
        btn_ver.pack(side="right", padx=2)
        
        btn_editar = ctk.CTkButton(botones_frame, text="✏️", width=30, height=25,
                                  command=lambda: self.editar_nota(nota_id, parent_window))
        btn_editar.pack(side="right", padx=2)
        
        # Contenido (limitado)
        if contenido:
            contenido_preview = contenido[:200] + "..." if len(contenido) > 200 else contenido
            contenido_frame = ctk.CTkFrame(nota_frame)
            contenido_frame.pack(fill="x", padx=10, pady=(0,10))
            
            ctk.CTkLabel(contenido_frame, text=contenido_preview, 
                        font=ctk.CTkFont(size=11), 
                        wraplength=700, justify="left").pack(anchor="w", padx=10, pady=5)

    def mostrar_estadisticas_principales(self, parent_frame, stats):
        """Muestra las estadísticas principales del cliente."""
        # Nueva estructura de stats desde estadisticas_cliente:
        # [0]: cliente_id, [1]: nombre, [2]: tipo_cliente, [3]: activo,
        # [4]: total_rmas, [5]: rmas_completados, [6]: rmas_abiertos,
        # [7]: rmas_pendientes, [8]: rmas_pendientes_autorizar, [9]: rmas_recibidos,
        # [10]: rmas_en_tramite, [11]: tasa_exito, [12]: primer_rma, [13]: ultimo_rma,
        # [14]: productos_diferentes, [15]: rmas_ultimo_mes
        
        ctk.CTkLabel(parent_frame, text="📊 Estadísticas Generales", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,10))
        
        stats_frame = ctk.CTkFrame(parent_frame)
        stats_frame.pack(fill="x", pady=(0,20))
        stats_frame.grid_columnconfigure((0,1,2), weight=1)
        
        # Fila 1: RMAs totales, abiertas (NO completados), cerradas (completados)
        ctk.CTkLabel(stats_frame, text=f"📦 Total RMAs\n{stats[4] or 0}", 
                    font=ctk.CTkFont(size=14, weight="bold"), 
                    text_color="blue").grid(row=0, column=0, padx=10, pady=10)
        
        ctk.CTkLabel(stats_frame, text=f"🟡 RMAs Abiertos\n{stats[6] or 0}", 
                    font=ctk.CTkFont(size=14, weight="bold"), 
                    text_color="orange").grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(stats_frame, text=f"🟢 RMAs Cerrados\n{stats[5] or 0}", 
                    font=ctk.CTkFont(size=14, weight="bold"), 
                    text_color="green").grid(row=0, column=2, padx=10, pady=10)
        
        # Fila 2: Tasa de éxito y otros datos
        tasa_exito = stats[11] or 0  # Actualizado al índice correcto
        # Convertir a número si viene como string
        try:
            tasa_exito = float(tasa_exito)
        except (ValueError, TypeError):
            tasa_exito = 0.0
        
        color_tasa = "green" if tasa_exito >= 80 else "orange" if tasa_exito >= 60 else "red"
        
        ctk.CTkLabel(stats_frame, text=f"✅ Tasa de Éxito\n{tasa_exito:.1f}%", 
                    font=ctk.CTkFont(size=14, weight="bold"), 
                    text_color=color_tasa).grid(row=1, column=0, padx=10, pady=10)
        
        if len(stats) > 14 and stats[14]:  # productos_diferentes (índice corregido)
            ctk.CTkLabel(stats_frame, text=f"📦 Total Productos\n{stats[14]}", 
                        font=ctk.CTkFont(size=14, weight="bold"), 
                        text_color="blue").grid(row=1, column=1, padx=10, pady=10)
        
        if len(stats) > 13 and stats[13]:  # ultimo_rma (índice corregido)
            ctk.CTkLabel(stats_frame, text=f"📅 Último RMA\n{stats[13]}", 
                        font=ctk.CTkFont(size=11, weight="bold"), 
                        text_color="gray").grid(row=1, column=2, padx=10, pady=10)

    def mostrar_productos_problematicos(self, parent_frame, productos):
        """Muestra los productos más problemáticos del cliente."""
        ctk.CTkLabel(parent_frame, text="⚠️ Productos Más Problemáticos", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20,10))
        
        productos_frame = ctk.CTkFrame(parent_frame)
        productos_frame.pack(fill="x", pady=(0,10))
        
        for i, producto in enumerate(productos[:5], 1):  # Top 5
            # producto: cliente_id, producto, total_devoluciones, valor_total
            prod_frame = ctk.CTkFrame(productos_frame, fg_color="transparent")
            prod_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(prod_frame, text=f"{i}. {producto[1]}", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            
            ctk.CTkLabel(prod_frame, text=f"🔄 {producto[2]} devoluciones", 
                        font=ctk.CTkFont(size=11), text_color="red").pack(side="right")
            
            if producto[3]:  # valor_total
                ctk.CTkLabel(prod_frame, text=f"💰 €{producto[3]:.2f}", 
                            font=ctk.CTkFont(size=11), text_color="gray").pack(side="right", padx=(0,10))

    def nuevo_contacto_cliente(self, cliente_id):
        """Muestra el formulario para agregar un nuevo contacto."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Nuevo Contacto")
        ventana.geometry("400x500")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="👤 Nuevo Contacto", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=300)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Nombre (obligatorio)
        ctk.CTkLabel(form_frame, text="Nombre del Contacto *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre completo del contacto")
        entry_nombre.pack(fill="x", pady=(0,10))
        
        # Cargo
        ctk.CTkLabel(form_frame, text="Cargo", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_cargo = ctk.CTkEntry(form_frame, placeholder_text="Cargo o posición en la empresa")
        entry_cargo.pack(fill="x", pady=(0,10))
        
        # Email
        ctk.CTkLabel(form_frame, text="Email", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_email = ctk.CTkEntry(form_frame, placeholder_text="email@ejemplo.com")
        entry_email.pack(fill="x", pady=(0,10))
        
        # Teléfono
        ctk.CTkLabel(form_frame, text="Teléfono", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_telefono = ctk.CTkEntry(form_frame, placeholder_text="Número de teléfono")
        entry_telefono.pack(fill="x", pady=(0,10))
        
        # Contacto principal
        check_principal = ctk.CTkCheckBox(form_frame, text="🌟 Marcar como contacto principal")
        check_principal.pack(anchor="w", pady=10)
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        def guardar_contacto():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre del contacto es obligatorio")
                return
            
            datos = {
                'nombre': nombre,
                'cargo': entry_cargo.get().strip(),
                'email': entry_email.get().strip(),
                'telefono': entry_telefono.get().strip(),
                'es_principal': check_principal.get()
            }
            
            if self.crear_contacto_cliente(cliente_id, datos):
                messagebox.showinfo("Éxito", f"Contacto '{nombre}' creado correctamente")
                ventana.destroy()
                # Recargar la pestaña de contactos si está abierta
            else:
                messagebox.showerror("Error", "Error al crear el contacto")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Guardar Contacto", 
                                  command=guardar_contacto,
                                  width=120)
        btn_guardar.pack(side="right")

    def editar_contacto_cliente(self, contacto_id, cliente_id):
        """Permite editar un contacto existente."""
        # Obtener datos del contacto
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return
            
            cursor.execute("""
                SELECT nombre, cargo, email, telefono, es_principal
                FROM contactos_cliente 
                WHERE contacto_id = ?
            """, (contacto_id,))
            
            contacto = cursor.fetchone()
            conn.close()
            
            if not contacto:
                messagebox.showerror("Error", "No se pudo cargar el contacto")
                return
                
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando contacto: {e}")
            return
        
        # Crear ventana de edición
        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar Contacto")
        ventana.geometry("400x500")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="✏️ Editar Contacto", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=300)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Nombre (obligatorio)
        ctk.CTkLabel(form_frame, text="Nombre del Contacto *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre completo del contacto")
        entry_nombre.pack(fill="x", pady=(0,10))
        entry_nombre.insert(0, contacto[0])
        
        # Cargo
        ctk.CTkLabel(form_frame, text="Cargo", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_cargo = ctk.CTkEntry(form_frame, placeholder_text="Cargo o posición en la empresa")
        entry_cargo.pack(fill="x", pady=(0,10))
        entry_cargo.insert(0, contacto[1] or "")
        
        # Email
        ctk.CTkLabel(form_frame, text="Email", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_email = ctk.CTkEntry(form_frame, placeholder_text="email@ejemplo.com")
        entry_email.pack(fill="x", pady=(0,10))
        entry_email.insert(0, contacto[2] or "")
        
        # Teléfono
        ctk.CTkLabel(form_frame, text="Teléfono", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_telefono = ctk.CTkEntry(form_frame, placeholder_text="Número de teléfono")
        entry_telefono.pack(fill="x", pady=(0,10))
        entry_telefono.insert(0, contacto[3] or "")
        
        # Contacto principal
        check_principal = ctk.CTkCheckBox(form_frame, text="🌟 Marcar como contacto principal")
        check_principal.pack(anchor="w", pady=10)
        if contacto[4]:
            check_principal.select()
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        btn_eliminar = ctk.CTkButton(botones_frame, text="🗑️ Eliminar", 
                                   command=lambda: self.eliminar_contacto_cliente(contacto_id, ventana),
                                   width=100, fg_color="red")
        btn_eliminar.pack(side="left")
        
        def actualizar_contacto():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre del contacto es obligatorio")
                return
            
            try:
                conn, cursor = self.master.conectar_db()
                if not conn: 
                    return
                
                # Si es contacto principal, desmarcar otros
                if check_principal.get():
                    cursor.execute("""
                        UPDATE contactos_cliente 
                        SET es_principal = 0 
                        WHERE cliente_id = ? AND contacto_id != ?
                    """, (cliente_id, contacto_id))
                
                cursor.execute("""
                    UPDATE contactos_cliente 
                    SET nombre = ?, cargo = ?, email = ?, telefono = ?, es_principal = ?,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE contacto_id = ?
                """, (nombre, entry_cargo.get().strip(), entry_email.get().strip(),
                      entry_telefono.get().strip(), check_principal.get(), contacto_id))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Éxito", f"Contacto '{nombre}' actualizado correctamente")
                ventana.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al actualizar contacto: {e}")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Actualizar", 
                                  command=actualizar_contacto,
                                  width=120)
        btn_guardar.pack(side="right", padx=(10,0))

    def recargar_ficha_cliente(self, cliente_id):
        """Recarga la ficha del cliente cerrando y volviendo a abrir."""
        try:
            # Buscar y cerrar ventanas de ficha de cliente abiertas
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    title = widget.title()
                    if "Ficha Cliente:" in title:
                        widget.destroy()
                        break
            
            # Pequeña pausa para asegurar que la ventana se cierre
            self.after(100, lambda: self.abrir_ficha_cliente(cliente_id))
            
        except Exception as e:
            print(f"Error recargando ficha: {e}")
            # Si falla la recarga, al menos abrir nueva ventana
            self.abrir_ficha_cliente(cliente_id)

    def eliminar_contacto_cliente(self, contacto_id, cliente_id, nombre_contacto):
        """Elimina un contacto del cliente (eliminación física)."""
        respuesta = messagebox.askyesno(
            "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar el contacto '{nombre_contacto}'?\n\n"
            "Esta acción no se puede deshacer."
        )
        
        if not respuesta:
            return
        
        try:
            from lib.logger_config import get_logger
            logger = get_logger()
            
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return
            
            # Eliminar el contacto
            cursor.execute("""
                DELETE FROM contactos_cliente 
                WHERE contacto_id = ?
            """, (contacto_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Contacto eliminado: {nombre_contacto} (ID: {contacto_id}) del cliente ID: {cliente_id}")
            messagebox.showinfo("Éxito", f"Contacto '{nombre_contacto}' eliminado correctamente")
            
            # Recargar la ficha del cliente
            self.recargar_ficha_cliente(cliente_id)
            
        except Exception as e:
            from lib.logger_config import get_logger
            logger = get_logger()
            logger.error(f"Error al eliminar contacto {contacto_id}: {e}")
            messagebox.showerror("Error", f"Error al eliminar contacto: {e}")

    def nueva_nota_cliente(self, cliente_id, parent_window=None):
        """Muestra el formulario para agregar una nueva nota."""
        ventana = ctk.CTkToplevel(parent_window or self)
        ventana.title("Nueva Nota")
        ventana.geometry("500x600")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(parent_window or self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="📝 Nueva Nota", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=400)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Título de la nota (obligatorio)
        ctk.CTkLabel(form_frame, text="Título de la Nota *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_titulo = ctk.CTkEntry(form_frame, placeholder_text="Título descriptivo de la nota")
        entry_titulo.pack(fill="x", pady=(0,10))
        
        # Tipo (usar nombres de la base de datos)
        ctk.CTkLabel(form_frame, text="Tipo", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        option_tipo = ctk.CTkOptionMenu(form_frame, values=["General", "Incidencia", "Comercial", "Técnica"])
        option_tipo.set("General")
        option_tipo.pack(fill="x", pady=(0,10))
        
        # Contenido
        ctk.CTkLabel(form_frame, text="Contenido de la Nota *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        text_contenido = ctk.CTkTextbox(form_frame, height=200)
        text_contenido.pack(fill="x", pady=(0,10))
        
        # Usuario (opcional, se puede pre-rellenar)
        ctk.CTkLabel(form_frame, text="Usuario", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_usuario = ctk.CTkEntry(form_frame, placeholder_text="Nombre del usuario que crea la nota")
        entry_usuario.pack(fill="x", pady=(0,10))
        entry_usuario.insert(0, "Usuario")  # Valor por defecto
        
        # Checkbox para nota privada
        check_privada = ctk.CTkCheckBox(form_frame, text="Nota privada (solo visible para administradores)")
        check_privada.pack(anchor="w", pady=10)
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        def guardar_nota():
            titulo = entry_titulo.get().strip()
            contenido = text_contenido.get("1.0", "end-1c").strip()
            
            if not titulo:
                messagebox.showerror("Error", "El título de la nota es obligatorio")
                return
            
            if not contenido:
                messagebox.showerror("Error", "El contenido de la nota es obligatorio")
                return
            
            datos = {
                'titulo': titulo,
                'contenido': contenido,
                'tipo': option_tipo.get(),
                'usuario': entry_usuario.get().strip() or "Usuario",
                'privada': check_privada.get()
            }
            
            if self.crear_nota_cliente(cliente_id, datos):
                messagebox.showinfo("Éxito", f"Nota '{titulo}' creada correctamente")
                ventana.destroy()
                # Si hay ventana padre, refrescar la lista
                if hasattr(parent_window, 'title') and 'Gestión de Notas' in parent_window.title():
                    # Buscar y refrescar la lista de notas en la ventana padre
                    pass
            else:
                messagebox.showerror("Error", "Error al crear la nota")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Guardar Nota", 
                                  command=guardar_nota,
                                  width=150)
        btn_guardar.pack(side="right")

    def editar_cliente_directo(self, cliente_id, ventana_padre):
        """Permite editar la información del cliente desde la ficha."""
        # Obtener datos del cliente
        cliente = self.obtener_cliente(cliente_id)
        if not cliente:
            messagebox.showerror("Error", "No se pudo cargar la información del cliente")
            return
        
        # Crear ventana de edición
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Editar Cliente: {cliente[1]}")
        ventana.geometry("500x600")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="✏️ Editar Cliente", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=400)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Llenar formulario con datos actuales
        ctk.CTkLabel(form_frame, text="Nombre del Cliente *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre completo del cliente")
        entry_nombre.pack(fill="x", pady=(0,10))
        entry_nombre.insert(0, cliente[1])
        
        ctk.CTkLabel(form_frame, text="Tipo de Cliente", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        option_tipo = ctk.CTkOptionMenu(form_frame, values=["Regular", "Premium", "VIP"])
        option_tipo.set(cliente[2])
        option_tipo.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(form_frame, text="Dirección", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_direccion = ctk.CTkEntry(form_frame, placeholder_text="Dirección completa")
        entry_direccion.pack(fill="x", pady=(0,10))
        entry_direccion.insert(0, cliente[3] or "")
        
        ctk.CTkLabel(form_frame, text="Teléfono Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_telefono = ctk.CTkEntry(form_frame, placeholder_text="Teléfono de contacto principal")
        entry_telefono.pack(fill="x", pady=(0,10))
        entry_telefono.insert(0, cliente[4] or "")
        
        ctk.CTkLabel(form_frame, text="Email Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_email = ctk.CTkEntry(form_frame, placeholder_text="Email de contacto principal")
        entry_email.pack(fill="x", pady=(0,10))
        entry_email.insert(0, cliente[5] or "")
        
        ctk.CTkLabel(form_frame, text="Notas Generales", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        text_notas = ctk.CTkTextbox(form_frame, height=80)
        text_notas.pack(fill="x", pady=(0,10))
        text_notas.insert("1.0", cliente[6] or "")
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        def actualizar_cliente():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre del cliente es obligatorio")
                return
            
            datos = {
                'nombre': nombre,
                'tipo_cliente': option_tipo.get(),
                'direccion': entry_direccion.get().strip(),
                'telefono_principal': entry_telefono.get().strip(),
                'email_principal': entry_email.get().strip(),
                'notas_generales': text_notas.get("1.0", "end-1c").strip()
            }
            
            if self.actualizar_cliente(cliente_id, datos):
                messagebox.showinfo("Éxito", f"Cliente '{nombre}' actualizado correctamente")
                ventana.destroy()
                # Cerrar la ventana padre para que se recargue
                ventana_padre.destroy()
                # Reabrir la ficha con datos actualizados
                self.abrir_ficha_cliente(cliente_id)
            else:
                messagebox.showerror("Error", "Error al actualizar el cliente")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Actualizar Cliente", 
                                  command=actualizar_cliente,
                                  width=140)
        btn_guardar.pack(side="right")

    def editar_cliente(self, cliente_id):
        """Permite editar la información básica del cliente."""
        # Obtener datos del cliente
        cliente = self.obtener_cliente(cliente_id)
        if not cliente:
            messagebox.showerror("Error", "No se pudo cargar la información del cliente")
            return
        
        # Crear ventana de edición
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Editar Cliente: {cliente[1]}")
        ventana.geometry("500x600")
        ventana.resizable(False, False)
        
        # Centrar ventana
        ventana.transient(self)
        ventana.grab_set()
        
        # Título
        titulo_frame = ctk.CTkFrame(ventana)
        titulo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(titulo_frame, text="✏️ Editar Cliente", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Formulario
        form_frame = ctk.CTkScrollableFrame(ventana, height=400)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Llenar formulario con datos actuales
        ctk.CTkLabel(form_frame, text="Nombre del Cliente *", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre completo del cliente")
        entry_nombre.pack(fill="x", pady=(0,10))
        entry_nombre.insert(0, cliente[1])
        
        ctk.CTkLabel(form_frame, text="Tipo de Cliente", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        option_tipo = ctk.CTkOptionMenu(form_frame, values=["Regular", "Premium", "VIP"])
        option_tipo.set(cliente[2])
        option_tipo.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(form_frame, text="Dirección", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_direccion = ctk.CTkEntry(form_frame, placeholder_text="Dirección completa")
        entry_direccion.pack(fill="x", pady=(0,10))
        entry_direccion.insert(0, cliente[3] or "")
        
        ctk.CTkLabel(form_frame, text="Teléfono Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_telefono = ctk.CTkEntry(form_frame, placeholder_text="Teléfono de contacto principal")
        entry_telefono.pack(fill="x", pady=(0,10))
        entry_telefono.insert(0, cliente[4] or "")
        
        ctk.CTkLabel(form_frame, text="Email Principal", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        entry_email = ctk.CTkEntry(form_frame, placeholder_text="Email de contacto principal")
        entry_email.pack(fill="x", pady=(0,10))
        entry_email.insert(0, cliente[5] or "")
        
        ctk.CTkLabel(form_frame, text="Notas Generales", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
        text_notas = ctk.CTkTextbox(form_frame, height=80)
        text_notas.pack(fill="x", pady=(0,10))
        text_notas.insert("1.0", cliente[6] or "")
        
        # Estado del cliente
        check_activo = ctk.CTkCheckBox(form_frame, text="Cliente activo")
        check_activo.pack(anchor="w", pady=10)
        if cliente[7]:  # cliente[7] es activo
            check_activo.select()
        
        # Botones
        botones_frame = ctk.CTkFrame(ventana)
        botones_frame.pack(fill="x", padx=20, pady=20)
        
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                   command=ventana.destroy,
                                   width=100)
        btn_cancelar.pack(side="right", padx=(10,0))
        
        if cliente[7]:  # Solo mostrar eliminar si está activo
            btn_eliminar = ctk.CTkButton(botones_frame, text="🗑️ Desactivar", 
                                       command=lambda: self.confirmar_eliminar_cliente(cliente_id, ventana),
                                       width=100, fg_color="red")
            btn_eliminar.pack(side="left")
        
        def actualizar_cliente():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre del cliente es obligatorio")
                return
            
            datos = {
                'nombre': nombre,
                'tipo_cliente': option_tipo.get(),
                'direccion': entry_direccion.get().strip(),
                'telefono_principal': entry_telefono.get().strip(),
                'email_principal': entry_email.get().strip(),
                'notas_generales': text_notas.get("1.0", "end-1c").strip()
            }
            
            # Actualizar estado si cambió
            if check_activo.get() != cliente[7]:
                try:
                    conn, cursor = self.master.conectar_db()
                    if conn:
                        cursor.execute("""
                            UPDATE clientes 
                            SET activo = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                            WHERE cliente_id = ?
                        """, (check_activo.get(), cliente_id))
                        conn.commit()
                        conn.close()
                except Exception as e:
                    print(f"Error actualizando estado: {e}")
            
            if self.actualizar_cliente(cliente_id, datos):
                messagebox.showinfo("Éxito", f"Cliente '{nombre}' actualizado correctamente")
                ventana.destroy()
                self.cargar_lista_clientes()  # Recargar lista
            else:
                messagebox.showerror("Error", "Error al actualizar el cliente")
        
        btn_guardar = ctk.CTkButton(botones_frame, text="💾 Actualizar Cliente", 
                                  command=actualizar_cliente,
                                  width=140)
        btn_guardar.pack(side="right")

    def confirmar_eliminar_cliente(self, cliente_id, ventana_padre):
        """Confirma y realiza la eliminación suave del cliente."""
        if messagebox.askyesno("Confirmar Desactivación", 
                              "¿Estás seguro de que deseas desactivar este cliente?\n\nEl cliente no se eliminará, solo se marcará como inactivo."):
            if self.eliminar_cliente(cliente_id):
                messagebox.showinfo("Éxito", "Cliente desactivado correctamente")
                ventana_padre.destroy()
                self.cargar_lista_clientes()  # Recargar lista
            else:
                messagebox.showerror("Error", "Error al desactivar el cliente")

    def gestionar_notas_cliente(self, cliente_id):
        """Gestiona las notas del cliente - Abre ventana de gestión completa."""
        try:
            # Crear ventana de gestión de notas
            ventana_notas = ctk.CTkToplevel(self)
            ventana_notas.title("Gestión de Notas")
            ventana_notas.geometry("800x600")
            
            # Configurar para permitir minimización
            ventana_notas.resizable(True, True)
            ventana_notas.attributes('-topmost', False)
            ventana_notas.minsize(600, 400)
            # No usar transient para permitir minimización completa
            ventana_notas.focus_set()  # Dar foco sin bloquear
            
            # Forzar aparición al frente (incluso si la principal está maximizada)
            ventana_notas.attributes('-topmost', True)   # Temporalmente al frente
            ventana_notas.lift()
            try:
                ventana_notas.focus_force()
            except:
                pass
            
            def quitar_topmost_ventana_notas():
                try:
                    if ventana_notas.winfo_exists():
                        ventana_notas.attributes('-topmost', False)
                except:
                    pass
            
            ventana_notas.after(500, quitar_topmost_ventana_notas)
            
            # Agregar icono personalizado
            try:
                ventana_notas.iconbitmap("Icono_Ilutrek.ico")
            except Exception:
                pass
            
            # Obtener información del cliente
            cliente = self.obtener_cliente(cliente_id)
            if not cliente:
                messagebox.showerror("Error", "No se pudo obtener información del cliente")
                ventana_notas.destroy()
                return
            
            # Header
            header_frame = ctk.CTkFrame(ventana_notas)
            header_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(header_frame, text=f"📝 Notas de {cliente[1]}", 
                        font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10, pady=10)
            
            btn_nueva_nota = ctk.CTkButton(header_frame, text="➕ Nueva Nota", 
                                         command=lambda: self.nueva_nota_cliente(cliente_id, ventana_notas),
                                         width=120)
            btn_nueva_nota.pack(side="right", padx=10, pady=10)
            
            # Frame para filtros
            filtros_frame = ctk.CTkFrame(ventana_notas)
            filtros_frame.pack(fill="x", padx=10, pady=(0,10))
            
            ctk.CTkLabel(filtros_frame, text="Filtrar por tipo:").pack(side="left", padx=10, pady=10)
            
            tipo_filter = ctk.CTkComboBox(filtros_frame, values=["Todos", "General", "Incidencia", "Comercial", "Técnica"])
            tipo_filter.set("Todos")
            tipo_filter.pack(side="left", padx=10, pady=10)
            
            # Lista de notas
            notas_frame = ctk.CTkScrollableFrame(ventana_notas, height=400)
            notas_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            def cargar_notas():
                # Limpiar frame
                for widget in notas_frame.winfo_children():
                    widget.destroy()
                
                # Obtener notas
                filtro_tipo = tipo_filter.get()
                notas = self.obtener_notas_cliente(cliente_id, filtro_tipo if filtro_tipo != "Todos" else None)
                
                if not notas:
                    ctk.CTkLabel(notas_frame, 
                               text="📭 No hay notas que coincidan con el filtro.\nHaz clic en 'Nueva Nota' para agregar una.",
                               font=ctk.CTkFont(size=13)).pack(pady=50)
                else:
                    for nota in notas:
                        self.crear_item_nota(notas_frame, nota, ventana_notas)
            
            # Conectar filtro
            tipo_filter.configure(command=lambda x: cargar_notas())
            
            # Cargar notas inicial
            cargar_notas()
            
            # Botón cerrar
            btn_cerrar = ctk.CTkButton(ventana_notas, text="Cerrar", 
                                     command=ventana_notas.destroy,
                                     width=100)
            btn_cerrar.pack(pady=10)
            
        except Exception as e:
            print(f"❌ Error gestionando notas: {e}")
            messagebox.showerror("Error", f"Error al abrir gestión de notas: {e}")

    def obtener_cliente(self, cliente_id):
        """Obtiene la información completa de un cliente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return None
            
            cursor.execute("""
                SELECT cliente_id, nombre, tipo_cliente, direccion, telefono_principal,
                       email_principal, notas_generales, activo, fecha_registro, fecha_actualizacion
                FROM clientes 
                WHERE cliente_id = ?
            """, (cliente_id,))
            
            cliente = cursor.fetchone()
            conn.close()
            return cliente
            
        except Exception as e:
            print(f"Error obteniendo cliente: {e}")
            return None

    def actualizar_cliente(self, cliente_id, datos):
        """Actualiza la información de un cliente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return False
            
            cursor.execute("""
                UPDATE clientes 
                SET nombre = ?, tipo_cliente = ?, direccion = ?, telefono_principal = ?,
                    email_principal = ?, notas_generales = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE cliente_id = ?
            """, (datos['nombre'], datos['tipo_cliente'], datos['direccion'], 
                  datos['telefono_principal'], datos['email_principal'], 
                  datos['notas_generales'], cliente_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error actualizando cliente: {e}")
            return False

    def eliminar_cliente(self, cliente_id):
        """Marca un cliente como inactivo (eliminación suave)."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return False
            
            cursor.execute("""
                UPDATE clientes 
                SET activo = 0, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE cliente_id = ?
            """, (cliente_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error eliminando cliente: {e}")
            return False

    def eliminar_cliente_permanente(self, cliente_id):
        """Elimina permanentemente un cliente de la base de datos."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return False
            
            # Primero eliminar contactos asociados
            cursor.execute("DELETE FROM contactos_cliente WHERE cliente_id = ?", (cliente_id,))
            
            # Eliminar condiciones comerciales
            cursor.execute("DELETE FROM condiciones_comerciales WHERE cliente_id = ?", (cliente_id,))
            
            # Actualizar RMAs asociados para quitar referencia al cliente
            cursor.execute("""
                UPDATE rma_maestro 
                SET cliente_id = NULL 
                WHERE cliente_id = ?
            """, (cliente_id,))
            
            # Finalmente eliminar el cliente
            cursor.execute("DELETE FROM clientes WHERE cliente_id = ?", (cliente_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error eliminando cliente permanentemente: {e}")
            return False

    def obtener_contactos_cliente(self, cliente_id):
        """Obtiene todos los contactos de un cliente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return []
            
            cursor.execute("""
                SELECT contacto_id, nombre, cargo, email, telefono, es_principal, activo
                FROM contactos_cliente 
                WHERE cliente_id = ? AND activo = 1
                ORDER BY es_principal DESC, nombre
            """, (cliente_id,))
            
            contactos = cursor.fetchall()
            conn.close()
            return contactos
            
        except Exception as e:
            print(f"Error obteniendo contactos: {e}")
            return []

    def crear_contacto_cliente(self, cliente_id, datos):
        """Crea un nuevo contacto para un cliente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return False
            
            # Si es contacto principal, desmarcar otros
            if datos.get('es_principal', False):
                cursor.execute("""
                    UPDATE contactos_cliente 
                    SET es_principal = 0 
                    WHERE cliente_id = ?
                """, (cliente_id,))
            
            cursor.execute("""
                INSERT INTO contactos_cliente (cliente_id, nombre, cargo, email, telefono, es_principal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cliente_id, datos['nombre'], datos.get('cargo', ''), 
                  datos.get('email', ''), datos.get('telefono', ''), 
                  datos.get('es_principal', False)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error creando contacto: {e}")
            return False

    def obtener_notas_cliente(self, cliente_id, tipo_filtro=None):
        """Obtiene todas las notas de un cliente."""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Query base
            query = """
                SELECT nota_id, titulo, contenido, tipo, fecha, usuario, privada
                FROM notas_cliente 
                WHERE cliente_id = ?
            """
            params = [cliente_id]
            
            # Agregar filtro por tipo si se especifica
            if tipo_filtro:
                query += " AND tipo = ?"
                params.append(tipo_filtro)
            
            query += " ORDER BY fecha DESC"
            
            cursor.execute(query, params)
            notas = cursor.fetchall()
            conn.close()
            return notas
            
        except Exception as e:
            print(f"❌ Error obteniendo notas: {e}")
            return []

    def crear_nota_cliente(self, cliente_id, datos):
        """Crea una nueva nota para un cliente."""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO notas_cliente (cliente_id, usuario, tipo, titulo, contenido, privada)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cliente_id, 
                datos.get('usuario', 'Usuario'),
                datos.get('tipo', 'General'), 
                datos['titulo'], 
                datos['contenido'], 
                datos.get('privada', False)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error creando nota: {e}")
            return False

    def ver_nota_completa(self, nota):
        """Muestra la nota completa en una ventana emergente."""
        nota_id, titulo, contenido, tipo, fecha, usuario, privada = nota
        
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Nota: {titulo}")
        ventana.geometry("600x500")
        ventana.transient(self)
        
        # Header
        header_frame = ctk.CTkFrame(ventana)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        titulo_icon = "🔒" if privada else "📝"
        ctk.CTkLabel(header_frame, text=f"{titulo_icon} {titulo}", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=10, pady=10)
        
        # Info
        info_frame = ctk.CTkFrame(ventana)
        info_frame.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkLabel(info_frame, text=f"🏷️ Tipo: {tipo} | 📅 Fecha: {fecha} | 👤 Usuario: {usuario}", 
                    font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=10)
        
        # Contenido
        contenido_frame = ctk.CTkScrollableFrame(ventana, height=300)
        contenido_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(contenido_frame, text=contenido, 
                    font=ctk.CTkFont(size=12), 
                    wraplength=550, justify="left").pack(anchor="w", padx=10, pady=10)
        
        # Botón cerrar
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack(pady=10)

    def editar_nota(self, nota_id, parent_window=None):
        """Permite editar una nota existente."""
        try:
            # Obtener datos actuales de la nota
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notas_cliente WHERE nota_id = ?", (nota_id,))
            nota_actual = cursor.fetchone()
            conn.close()
            
            if not nota_actual:
                messagebox.showerror("Error", "No se pudo cargar la nota")
                return
            
            # nota_actual: nota_id, cliente_id, usuario, fecha, tipo, titulo, contenido, privada
            _, cliente_id, usuario_actual, _, tipo_actual, titulo_actual, contenido_actual, privada_actual = nota_actual
            
            ventana = ctk.CTkToplevel(parent_window or self)
            ventana.title("Editar Nota")
            ventana.geometry("500x600")
            ventana.transient(parent_window or self)
            ventana.grab_set()
            
            # Formulario similar al de nueva nota
            titulo_frame = ctk.CTkFrame(ventana)
            titulo_frame.pack(fill="x", padx=20, pady=20)
            
            ctk.CTkLabel(titulo_frame, text="📝 Editar Nota", 
                        font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
            
            form_frame = ctk.CTkScrollableFrame(ventana, height=400)
            form_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Título
            ctk.CTkLabel(form_frame, text="Título de la Nota *", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
            entry_titulo = ctk.CTkEntry(form_frame)
            entry_titulo.pack(fill="x", pady=(0,10))
            entry_titulo.insert(0, titulo_actual)
            
            # Tipo
            ctk.CTkLabel(form_frame, text="Tipo", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
            option_tipo = ctk.CTkOptionMenu(form_frame, values=["General", "Incidencia", "Comercial", "Técnica"])
            option_tipo.set(tipo_actual)
            option_tipo.pack(fill="x", pady=(0,10))
            
            # Contenido
            ctk.CTkLabel(form_frame, text="Contenido de la Nota *", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
            text_contenido = ctk.CTkTextbox(form_frame, height=200)
            text_contenido.pack(fill="x", pady=(0,10))
            text_contenido.insert("1.0", contenido_actual)
            
            # Usuario
            ctk.CTkLabel(form_frame, text="Usuario", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,2))
            entry_usuario = ctk.CTkEntry(form_frame)
            entry_usuario.pack(fill="x", pady=(0,10))
            entry_usuario.insert(0, usuario_actual)
            
            # Privada
            check_privada = ctk.CTkCheckBox(form_frame, text="Nota privada")
            check_privada.pack(anchor="w", pady=10)
            if privada_actual:
                check_privada.select()
            
            # Botones
            botones_frame = ctk.CTkFrame(ventana)
            botones_frame.pack(fill="x", padx=20, pady=20)
            
            btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                       command=ventana.destroy, width=100)
            btn_cancelar.pack(side="right", padx=(10,0))
            
            def guardar_cambios():
                titulo = entry_titulo.get().strip()
                contenido = text_contenido.get("1.0", "end-1c").strip()
                
                if not titulo or not contenido:
                    messagebox.showerror("Error", "Título y contenido son obligatorios")
                    return
                
                try:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE notas_cliente 
                        SET titulo = ?, contenido = ?, tipo = ?, usuario = ?, privada = ?
                        WHERE nota_id = ?
                    """, (titulo, contenido, option_tipo.get(), 
                          entry_usuario.get().strip(), check_privada.get(), nota_id))
                    
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Éxito", "Nota actualizada correctamente")
                    ventana.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error al actualizar nota: {e}")
            
            btn_guardar = ctk.CTkButton(botones_frame, text="💾 Guardar Cambios", 
                                      command=guardar_cambios, width=150)
            btn_guardar.pack(side="right")
            
        except Exception as e:
            print(f"❌ Error editando nota: {e}")
            messagebox.showerror("Error", f"Error al editar nota: {e}")

    def obtener_estadisticas_cliente(self, cliente_id):
        """Obtiene las estadísticas completas de un cliente."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn: 
                return None
            
            cursor.execute("""
                SELECT * FROM estadisticas_cliente 
                WHERE cliente_id = ?
            """, (cliente_id,))
            
            stats = cursor.fetchone()
            
            # También obtener productos problemáticos
            cursor.execute("""
                SELECT * FROM productos_problematicos 
                WHERE cliente_id = ?
                ORDER BY total_devoluciones DESC
                LIMIT 10
            """, (cliente_id,))
            
            productos_problematicos = cursor.fetchall()
            
            conn.close()
            
            return {
                'estadisticas': stats,
                'productos_problematicos': productos_problematicos
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return None
