"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

# Claves de filtro que representan un criterio de texto/valor (excluye "tipos")
_CLAVES_FILTRO = ("estado", "fecha_desde", "fecha_hasta", "cliente", "documento",
                   "proveedor", "estado_producto", "referencia")


class BusquedaMixin:
    # ------------------------------------------------------------------
    # Historial de búsquedas
    # ------------------------------------------------------------------
    def cargar_historial_busquedas(self):
        """Carga el historial de búsquedas del usuario desde configuración."""
        if not hasattr(self, 'historial_busquedas'):
            self.historial_busquedas = self.user_settings.get("historial_busquedas", [])
        return self.historial_busquedas[:10]  # Máximo 10 búsquedas recientes

    def guardar_busqueda_en_historial(self, termino, filtros=None):
        """Guarda una nueva búsqueda en el historial."""
        filtros = filtros or {}
        tiene_criterio = bool(termino and termino.strip()) or any(filtros.get(k) for k in _CLAVES_FILTRO)
        if not tiene_criterio:
            return

        entrada = {
            "termino": (termino or "").strip(),
            "filtros": filtros,
            "fecha": datetime.datetime.now().isoformat()
        }

        if not hasattr(self, 'historial_busquedas'):
            self.historial_busquedas = self.user_settings.get("historial_busquedas", [])

        clave = entrada["termino"]
        self.historial_busquedas = [h for h in self.historial_busquedas if h.get("termino") != clave]
        self.historial_busquedas.insert(0, entrada)
        self.historial_busquedas = self.historial_busquedas[:10]

        self.user_settings["historial_busquedas"] = self.historial_busquedas
        save_user_settings(self.user_settings, self.username)

    def limpiar_historial_busquedas(self):
        """Limpia todo el historial de búsquedas."""
        self.historial_busquedas = []
        self.user_settings["historial_busquedas"] = []
        save_user_settings(self.user_settings, self.username)

    def limpiar_historial_busquedas_ui(self):
        """Limpia el historial desde la interfaz (el desplegable se reconstruye al abrirse)."""
        self.limpiar_historial_busquedas()

    def mostrar_historial_dropdown(self):
        """Muestra un menú desplegable con las últimas búsquedas realizadas."""
        historial = self.cargar_historial_busquedas()
        menu = tk.Menu(self, tearoff=0)

        if not historial:
            menu.add_command(label="Sin búsquedas recientes", state="disabled")
        else:
            for entrada in historial:
                texto = (entrada.get("termino") or "").strip()
                filtros = entrada.get("filtros") or {}
                if not texto:
                    activos = [k for k in _CLAVES_FILTRO if filtros.get(k)]
                    texto = f"(filtros: {', '.join(activos)})" if activos else "(sin criterios)"
                if len(texto) > 45:
                    texto = texto[:42] + "..."
                menu.add_command(label=f"🕘 {texto}", command=lambda e=entrada: self.usar_busqueda_historial(e))
            menu.add_separator()
            menu.add_command(label="🗑️ Limpiar historial", command=self.limpiar_historial_busquedas_ui)

        try:
            x = self.btn_historial.winfo_rootx()
            y = self.btn_historial.winfo_rooty() + self.btn_historial.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def usar_busqueda_historial(self, entrada):
        """Aplica una búsqueda del historial (término y filtros guardados)."""
        self.entry_busqueda_global.delete(0, 'end')
        self.entry_busqueda_global.insert(0, entrada.get("termino", ""))

        filtros = entrada.get("filtros") or {}
        if filtros:
            if not self.filtros_expandido.get():
                self.toggle_filtros_avanzados()

            self.filtro_estado.set(filtros.get("estado") or "Todos")
            self.filtro_fecha_desde.delete(0, 'end')
            self.filtro_fecha_desde.insert(0, filtros.get("fecha_desde", ""))
            self.filtro_fecha_hasta.delete(0, 'end')
            self.filtro_fecha_hasta.insert(0, filtros.get("fecha_hasta", ""))
            self.filtro_cliente.delete(0, 'end')
            self.filtro_cliente.insert(0, filtros.get("cliente", ""))
            self.filtro_documento.delete(0, 'end')
            self.filtro_documento.insert(0, filtros.get("documento", ""))
            self.filtro_proveedor.delete(0, 'end')
            self.filtro_proveedor.insert(0, filtros.get("proveedor", ""))
            self.filtro_estado_producto.set(filtros.get("estado_producto") or "Todos")
            self.filtro_referencia.delete(0, 'end')
            self.filtro_referencia.insert(0, filtros.get("referencia", ""))

            tipos = filtros.get("tipos", ["expedientes", "productos", "tareas", "historial"])
            self.chk_incluir_expedientes.set("expedientes" in tipos)
            self.chk_incluir_productos.set("productos" in tipos)
            self.chk_incluir_tareas.set("tareas" in tipos)
            self.chk_incluir_historial.set("historial" in tipos)

        self.ejecutar_busqueda()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def mostrar_busqueda_global(self):
        """Muestra la interfaz de búsqueda global: barra de búsqueda compacta,
        filtros plegables y resultados en formato de listado (no en tarjetas)."""
        self.limpiar_contenido()

        # --- Cabecera ---
        header_frame = ctk.CTkFrame(self.content_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(header_frame, text="🔍 Búsqueda Global",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(header_frame, text="← Volver a Lista", command=self.mostrar_lista_rma,
                      width=150, height=30).pack(side="right", padx=10, pady=10)

        # --- Barra de búsqueda (una sola fila, ancho completo) ---
        toolbar = ctk.CTkFrame(self.content_frame)
        toolbar.pack(fill="x", padx=10, pady=(0, 5))

        self.entry_busqueda_global = ctk.CTkEntry(
            toolbar, placeholder_text="Buscar por código, cliente, referencia, motivo...",
            height=35, font=ctk.CTkFont(size=13))
        self.entry_busqueda_global.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        self.entry_busqueda_global.bind("<Return>", lambda e: self.ejecutar_busqueda())

        ctk.CTkButton(toolbar, text="🔍 Buscar", command=self.ejecutar_busqueda,
                      width=100, height=35).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(toolbar, text="🗑️ Limpiar", command=self.limpiar_busqueda_global,
                      width=90, height=35).pack(side="left", padx=5, pady=10)

        self.filtros_expandido = ctk.BooleanVar(value=False)
        self.btn_toggle_filtros = ctk.CTkButton(toolbar, text="🔽 Filtros",
                                                  command=self.toggle_filtros_avanzados,
                                                  width=100, height=35)
        self.btn_toggle_filtros.pack(side="left", padx=5, pady=10)

        self.btn_historial = ctk.CTkButton(toolbar, text="🕘 Historial",
                                            command=self.mostrar_historial_dropdown,
                                            width=100, height=35)
        self.btn_historial.pack(side="left", padx=(5, 10), pady=10)

        # --- Panel de filtros (plegable, en su propio contenedor para no
        # desordenar el resto de widgets al mostrarse/ocultarse) ---
        self.filtros_wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.filtros_wrapper.pack(fill="x", padx=10, pady=0)

        self.filtros_content = ctk.CTkFrame(self.filtros_wrapper)
        # No se empaqueta todavía: permanece oculto hasta pulsar "Filtros"

        self.crear_controles_filtros()

        # --- Ayuda ---
        ayuda_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ayuda_frame.pack(fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(ayuda_frame,
                     text="⌨️ Ctrl+F para abrir esta búsqueda   ·   Haz clic en un resultado para abrir su expediente en una ventana aparte",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")

        # --- Resultados (listado simple, ocupa todo el espacio restante) ---
        self.resultados_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.resultados_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.mostrar_mensaje_busqueda("👆 Introduce un término de búsqueda o aplica filtros para comenzar")
        self.entry_busqueda_global.focus()

    def crear_controles_filtros(self):
        """Crea los controles del panel de filtros avanzados, en una rejilla compacta."""
        for w in self.filtros_content.winfo_children():
            w.destroy()

        # Estados reales de expediente, obtenidos de la base de datos (evita listas inventadas)
        estados_db = ["Todos"]
        conn = None
        try:
            conn, cursor = self.master.conectar_db()
            if conn:
                cursor.execute("""SELECT DISTINCT estado FROM rma_maestro
                                   WHERE estado IS NOT NULL AND estado != '' ORDER BY estado""")
                estados_db += [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            print(f"Error al cargar estados para filtro de búsqueda: {e}")
        finally:
            if conn:
                conn.close()

        estados_producto = ["Todos"] + list(self.OPCIONES.get("Estado_Producto", []) or [])

        for col in range(4):
            self.filtros_content.grid_columnconfigure(col, weight=1)

        pad = {"padx": 10, "pady": 6}

        ctk.CTkLabel(self.filtros_content, text="Estado expediente:").grid(row=0, column=0, sticky="w", **pad)
        self.filtro_estado = ctk.CTkOptionMenu(self.filtros_content, values=estados_db)
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=0, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Proveedor:").grid(row=0, column=2, sticky="w", **pad)
        self.filtro_proveedor = ctk.CTkEntry(self.filtros_content, placeholder_text="Nombre del proveedor")
        self.filtro_proveedor.grid(row=0, column=3, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Fecha emisión desde:").grid(row=1, column=0, sticky="w", **pad)
        self.filtro_fecha_desde = ctk.CTkEntry(self.filtros_content, placeholder_text="YYYY-MM-DD")
        self.filtro_fecha_desde.grid(row=1, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Fecha emisión hasta:").grid(row=1, column=2, sticky="w", **pad)
        self.filtro_fecha_hasta = ctk.CTkEntry(self.filtros_content, placeholder_text="YYYY-MM-DD")
        self.filtro_fecha_hasta.grid(row=1, column=3, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Cliente:").grid(row=2, column=0, sticky="w", **pad)
        self.filtro_cliente = ctk.CTkEntry(self.filtros_content, placeholder_text="Nombre del cliente")
        self.filtro_cliente.grid(row=2, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Documento cliente:").grid(row=2, column=2, sticky="w", **pad)
        self.filtro_documento = ctk.CTkEntry(self.filtros_content, placeholder_text="Nº de documento")
        self.filtro_documento.grid(row=2, column=3, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Estado del producto:").grid(row=3, column=0, sticky="w", **pad)
        self.filtro_estado_producto = ctk.CTkOptionMenu(self.filtros_content, values=estados_producto)
        self.filtro_estado_producto.set("Todos")
        self.filtro_estado_producto.grid(row=3, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self.filtros_content, text="Referencia artículo:").grid(row=3, column=2, sticky="w", **pad)
        self.filtro_referencia = ctk.CTkEntry(self.filtros_content, placeholder_text="Referencia del artículo")
        self.filtro_referencia.grid(row=3, column=3, sticky="ew", **pad)

        tipos_frame = ctk.CTkFrame(self.filtros_content, fg_color="transparent")
        tipos_frame.grid(row=4, column=0, columnspan=4, sticky="w", padx=10, pady=(2, 6))
        ctk.CTkLabel(tipos_frame, text="Incluir en resultados:").pack(side="left", padx=(0, 10))
        self.chk_incluir_expedientes = ctk.BooleanVar(value=True)
        self.chk_incluir_productos = ctk.BooleanVar(value=True)
        self.chk_incluir_tareas = ctk.BooleanVar(value=True)
        self.chk_incluir_historial = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tipos_frame, text="Expedientes", variable=self.chk_incluir_expedientes).pack(side="left", padx=6)
        ctk.CTkCheckBox(tipos_frame, text="Productos", variable=self.chk_incluir_productos).pack(side="left", padx=6)
        ctk.CTkCheckBox(tipos_frame, text="Tareas", variable=self.chk_incluir_tareas).pack(side="left", padx=6)
        ctk.CTkCheckBox(tipos_frame, text="Historial", variable=self.chk_incluir_historial).pack(side="left", padx=6)

        botones_filtros = ctk.CTkFrame(self.filtros_content, fg_color="transparent")
        botones_filtros.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkButton(botones_filtros, text="🔍 Aplicar filtros", command=self.ejecutar_busqueda,
                      height=30).pack(side="left", padx=(0, 5))
        ctk.CTkButton(botones_filtros, text="🧹 Limpiar filtros", command=self.limpiar_filtros,
                      height=30).pack(side="left")

    def toggle_filtros_avanzados(self):
        """Muestra u oculta el panel de filtros avanzados."""
        if self.filtros_expandido.get():
            self.filtros_content.pack_forget()
            self.btn_toggle_filtros.configure(text="🔽 Filtros")
            self.filtros_expandido.set(False)
        else:
            self.filtros_content.pack(fill="x", pady=(0, 5))
            self.btn_toggle_filtros.configure(text="🔼 Filtros")
            self.filtros_expandido.set(True)

    def limpiar_filtros(self):
        """Limpia todos los filtros avanzados (sin lanzar la búsqueda)."""
        self.filtro_estado.set("Todos")
        self.filtro_fecha_desde.delete(0, 'end')
        self.filtro_fecha_hasta.delete(0, 'end')
        self.filtro_cliente.delete(0, 'end')
        self.filtro_documento.delete(0, 'end')
        self.filtro_proveedor.delete(0, 'end')
        self.filtro_estado_producto.set("Todos")
        self.filtro_referencia.delete(0, 'end')
        self.chk_incluir_expedientes.set(True)
        self.chk_incluir_productos.set(True)
        self.chk_incluir_tareas.set(True)
        self.chk_incluir_historial.set(True)

    def validar_fecha(self, fecha_str):
        """Valida formato de fecha YYYY-MM-DD."""
        try:
            datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def limpiar_busqueda_global(self):
        """Limpia el campo de búsqueda y los resultados."""
        self.entry_busqueda_global.delete(0, 'end')
        self.mostrar_mensaje_busqueda("👆 Introduce un término de búsqueda o aplica filtros para comenzar")
        self.entry_busqueda_global.focus()

    def mostrar_mensaje_busqueda(self, mensaje):
        """Muestra un mensaje centrado en el área de resultados."""
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.resultados_frame, text=mensaje,
                     font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)

    # ------------------------------------------------------------------
    # Ejecución de la búsqueda
    # ------------------------------------------------------------------
    def recopilar_filtros(self):
        """Lee el estado actual de los controles de filtro y devuelve un dict plano."""
        tipos = []
        if self.chk_incluir_expedientes.get():
            tipos.append("expedientes")
        if self.chk_incluir_productos.get():
            tipos.append("productos")
        if self.chk_incluir_tareas.get():
            tipos.append("tareas")
        if self.chk_incluir_historial.get():
            tipos.append("historial")

        return {
            "estado": "" if self.filtro_estado.get() == "Todos" else self.filtro_estado.get(),
            "fecha_desde": self.filtro_fecha_desde.get().strip(),
            "fecha_hasta": self.filtro_fecha_hasta.get().strip(),
            "cliente": self.filtro_cliente.get().strip(),
            "documento": self.filtro_documento.get().strip(),
            "proveedor": self.filtro_proveedor.get().strip(),
            "estado_producto": "" if self.filtro_estado_producto.get() == "Todos" else self.filtro_estado_producto.get(),
            "referencia": self.filtro_referencia.get().strip(),
            "tipos": tipos,
        }

    def ejecutar_busqueda(self):
        """Ejecuta la búsqueda combinando el texto libre y los filtros activos."""
        termino = self.entry_busqueda_global.get().strip()
        filtros = self.recopilar_filtros()

        if filtros["fecha_desde"] and not self.validar_fecha(filtros["fecha_desde"]):
            messagebox.showerror("Error", "Formato de fecha inválido en 'desde' (YYYY-MM-DD)")
            return
        if filtros["fecha_hasta"] and not self.validar_fecha(filtros["fecha_hasta"]):
            messagebox.showerror("Error", "Formato de fecha inválido en 'hasta' (YYYY-MM-DD)")
            return

        if not filtros["tipos"]:
            self.mostrar_mensaje_busqueda("⚠️ Selecciona al menos un tipo de resultado a incluir")
            return

        hay_filtros_activos = any(filtros.get(k) for k in _CLAVES_FILTRO)
        if not termino and not hay_filtros_activos:
            self.mostrar_mensaje_busqueda("👆 Introduce un término de búsqueda o aplica filtros para comenzar")
            return
        if termino and len(termino) < 2:
            self.mostrar_mensaje_busqueda("⚠️ El término de búsqueda debe tener al menos 2 caracteres")
            return

        self.mostrar_mensaje_busqueda("🔄 Buscando...")
        self.update()

        try:
            self.guardar_busqueda_en_historial(termino, filtros)
            resultados = self.buscar_global(termino, filtros)
            self.mostrar_resultados(resultados, termino, filtros)
        except Exception as e:
            print(f"Error en búsqueda global: {e}")
            self.mostrar_mensaje_busqueda(f"❌ Error en la búsqueda: {e}")

    def buscar_global(self, termino, filtros):
        """Consulta las tablas seleccionadas aplicando texto libre y filtros."""
        resultados = {"expedientes": [], "productos": [], "historial": [], "tareas": []}

        conn, cursor = self.master.conectar_db()
        if not conn:
            return resultados

        try:
            if "expedientes" in filtros["tipos"]:
                resultados["expedientes"] = self._buscar_expedientes(cursor, termino, filtros)
            if "productos" in filtros["tipos"]:
                resultados["productos"] = self._buscar_productos(cursor, termino, filtros)
            if "historial" in filtros["tipos"]:
                try:
                    resultados["historial"] = self._buscar_historial(cursor, termino, filtros)
                except Exception as e:
                    print(f"Búsqueda en historial omitida: {e}")
            if "tareas" in filtros["tipos"]:
                try:
                    resultados["tareas"] = self._buscar_tareas(cursor, termino, filtros)
                except Exception as e:
                    print(f"Búsqueda en tareas omitida: {e}")
            return resultados
        finally:
            conn.close()

    def _buscar_expedientes(self, cursor, termino, filtros):
        """Busca en rma_maestro. El texto libre recorre todas las columnas de texto."""
        cursor.execute("PRAGMA table_info(rma_maestro)")
        columnas = [c[1] for c in cursor.fetchall()]

        where, params = [], []

        if termino:
            campos_texto = [c for c in columnas if c.lower() != 'id']
            if campos_texto:
                where.append("(" + " OR ".join(f"{c} LIKE ?" for c in campos_texto) + ")")
                params.extend([f"%{termino}%"] * len(campos_texto))

        if filtros["estado"]:
            where.append("estado = ?")
            params.append(filtros["estado"])
        if filtros["fecha_desde"]:
            where.append("fecha_emision >= ?")
            params.append(filtros["fecha_desde"])
        if filtros["fecha_hasta"]:
            where.append("fecha_emision <= ?")
            params.append(filtros["fecha_hasta"])
        if filtros["cliente"]:
            where.append("cliente LIKE ?")
            params.append(f"%{filtros['cliente']}%")
        if filtros["documento"]:
            where.append("numero_documento_cliente LIKE ?")
            params.append(f"%{filtros['documento']}%")
        if filtros["proveedor"]:
            where.append("rma_proveedor LIKE ?")
            params.append(f"%{filtros['proveedor']}%")

        sql = "SELECT id, codigo_rma, cliente, numero_documento_cliente, estado, fecha_emision, rma_proveedor FROM rma_maestro"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY fecha_emision DESC LIMIT 100"

        cursor.execute(sql, params)
        return cursor.fetchall()

    def _buscar_productos(self, cursor, termino, filtros):
        """Busca en rma_detalles (join con rma_maestro para mostrar contexto)."""
        cursor.execute("PRAGMA table_info(rma_detalles)")
        columnas = [c[1] for c in cursor.fetchall()]
        excluir = {'id', 'rma_id', 'cantidad_segun_documento', 'cantidad_entregada',
                   'precio_unitario', 'precio_final', 'depreciacion', 'porcentaje_depreciacion'}

        where, params = [], []

        if termino:
            campos_texto = [f"d.{c}" for c in columnas if c.lower() not in excluir]
            if campos_texto:
                where.append("(" + " OR ".join(f"{c} LIKE ?" for c in campos_texto) + ")")
                params.extend([f"%{termino}%"] * len(campos_texto))

        if filtros["estado_producto"]:
            where.append("d.estado_producto = ?")
            params.append(filtros["estado_producto"])
        if filtros["referencia"]:
            where.append("d.referencia_articulo LIKE ?")
            params.append(f"%{filtros['referencia']}%")
        if filtros["estado"]:
            where.append("m.estado = ?")
            params.append(filtros["estado"])
        if filtros["fecha_desde"]:
            where.append("m.fecha_emision >= ?")
            params.append(filtros["fecha_desde"])
        if filtros["fecha_hasta"]:
            where.append("m.fecha_emision <= ?")
            params.append(filtros["fecha_hasta"])
        if filtros["cliente"]:
            where.append("m.cliente LIKE ?")
            params.append(f"%{filtros['cliente']}%")
        if filtros["documento"]:
            where.append("m.numero_documento_cliente LIKE ?")
            params.append(f"%{filtros['documento']}%")
        if filtros["proveedor"]:
            where.append("m.rma_proveedor LIKE ?")
            params.append(f"%{filtros['proveedor']}%")

        sql = """SELECT d.id, d.rma_id, d.referencia_articulo, d.cantidad_segun_documento,
                        d.cantidad_entregada, d.estado_producto, m.codigo_rma, m.cliente
                 FROM rma_detalles d JOIN rma_maestro m ON d.rma_id = m.id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.fecha_emision DESC LIMIT 100"

        cursor.execute(sql, params)
        return cursor.fetchall()

    def _buscar_historial(self, cursor, termino, filtros):
        """Busca en rma_historial (cambios de estado / comentarios)."""
        where, params = [], []

        if termino:
            where.append("(h.descripcion_cambio LIKE ? OR h.usuario LIKE ? OR m.codigo_rma LIKE ?)")
            params.extend([f"%{termino}%"] * 3)
        if filtros["estado"]:
            where.append("m.estado = ?")
            params.append(filtros["estado"])
        if filtros["fecha_desde"]:
            where.append("date(h.fecha_cambio) >= ?")
            params.append(filtros["fecha_desde"])
        if filtros["fecha_hasta"]:
            where.append("date(h.fecha_cambio) <= ?")
            params.append(filtros["fecha_hasta"])
        if filtros["cliente"]:
            where.append("m.cliente LIKE ?")
            params.append(f"%{filtros['cliente']}%")

        sql = """SELECT h.rma_id, h.fecha_cambio, h.descripcion_cambio, h.usuario, m.codigo_rma, m.cliente
                 FROM rma_historial h JOIN rma_maestro m ON h.rma_id = m.id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY h.fecha_cambio DESC LIMIT 100"

        cursor.execute(sql, params)
        return cursor.fetchall()

    def _buscar_tareas(self, cursor, termino, filtros):
        """Busca en tareas (asociadas o no a un expediente)."""
        where, params = [], []

        if termino:
            where.append("(t.titulo LIKE ? OR t.descripcion LIKE ? OR t.estado LIKE ? OR t.creado_por LIKE ? OR t.codigo_rma LIKE ?)")
            params.extend([f"%{termino}%"] * 5)
        if filtros["fecha_desde"]:
            where.append("date(t.fecha_vencimiento) >= ?")
            params.append(filtros["fecha_desde"])
        if filtros["fecha_hasta"]:
            where.append("date(t.fecha_vencimiento) <= ?")
            params.append(filtros["fecha_hasta"])
        if filtros["cliente"]:
            where.append("m.cliente LIKE ?")
            params.append(f"%{filtros['cliente']}%")
        if filtros["estado"]:
            where.append("m.estado = ?")
            params.append(filtros["estado"])

        sql = """SELECT t.id, t.codigo_rma, t.titulo, t.descripcion, t.estado, t.fecha_vencimiento,
                        t.creado_por, m.id as rma_id, m.cliente
                 FROM tareas t LEFT JOIN rma_maestro m ON t.codigo_rma = m.codigo_rma"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY t.fecha_vencimiento IS NULL, t.fecha_vencimiento DESC LIMIT 100"

        cursor.execute(sql, params)
        return cursor.fetchall()

    # ------------------------------------------------------------------
    # Presentación de resultados: listado compacto, no tarjetas
    # ------------------------------------------------------------------
    def mostrar_resultados(self, resultados, termino, filtros):
        """Dibuja los resultados agrupados por tipo, en filas finas y clicables."""
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()

        total = sum(len(v) for v in resultados.values())

        resumen_frame = ctk.CTkFrame(self.resultados_frame, fg_color="transparent")
        resumen_frame.pack(fill="x", padx=6, pady=(6, 4))

        criterios = []
        if termino:
            criterios.append(f"'{termino}'")
        activos = [k for k in _CLAVES_FILTRO if filtros.get(k)]
        if activos:
            criterios.append(f"{len(activos)} filtro(s)")
        texto_criterios = " · ".join(criterios) if criterios else "todos los registros"

        ctk.CTkLabel(resumen_frame, text=f"📊 {total} resultado(s) para {texto_criterios}",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        if total == 0:
            ctk.CTkLabel(self.resultados_frame,
                         text="❌ No se encontraron resultados con los criterios especificados",
                         font=ctk.CTkFont(size=13), text_color="orange").pack(pady=30)
            return

        if resultados["expedientes"]:
            self._render_seccion(f"📋 Expedientes ({len(resultados['expedientes'])})",
                                  resultados["expedientes"], self._fila_expediente)
        if resultados["productos"]:
            self._render_seccion(f"📦 Productos ({len(resultados['productos'])})",
                                  resultados["productos"], self._fila_producto)
        if resultados["tareas"]:
            self._render_seccion(f"✅ Tareas ({len(resultados['tareas'])})",
                                  resultados["tareas"], self._fila_tarea)
        if resultados["historial"]:
            self._render_seccion(f"📜 Historial ({len(resultados['historial'])})",
                                  resultados["historial"], self._fila_historial)

    def _render_seccion(self, titulo, filas, builder):
        seccion = ctk.CTkFrame(self.resultados_frame, fg_color="transparent")
        seccion.pack(fill="x", padx=4, pady=(4, 8))

        ctk.CTkLabel(seccion, text=titulo, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=6, pady=(2, 4))

        lista_frame = ctk.CTkFrame(seccion)
        lista_frame.pack(fill="x", padx=4)

        for fila in filas:
            builder(lista_frame, fila)

    def _crear_fila(self, parent, icono, col1, col1_width, col2, estado_text, estado_color, fecha_text, on_click):
        """Renderiza una fila compacta y clicable de resultado (estilo tabla, no tarjeta)."""
        if col2 and len(col2) > 90:
            col2 = col2[:87] + "..."

        fila = ctk.CTkFrame(parent, fg_color="transparent")
        fila.pack(fill="x", padx=2, pady=1)

        lbl_icono = ctk.CTkLabel(fila, text=icono, width=22, font=ctk.CTkFont(size=13))
        lbl_icono.pack(side="left", padx=(6, 2), pady=4)

        lbl_col1 = ctk.CTkLabel(fila, text=str(col1), width=col1_width, anchor="w",
                                 font=ctk.CTkFont(size=12, weight="bold"))
        lbl_col1.pack(side="left", padx=4, pady=4)

        lbl_fecha = ctk.CTkLabel(fila, text=str(fecha_text or ""), width=95, anchor="e",
                                  font=ctk.CTkFont(size=11), text_color="gray")
        lbl_fecha.pack(side="right", padx=(4, 10), pady=4)

        lbl_estado = ctk.CTkLabel(fila, text=str(estado_text or ""), width=140, anchor="w",
                                   font=ctk.CTkFont(size=11), text_color=estado_color)
        lbl_estado.pack(side="right", padx=4, pady=4)

        lbl_col2 = ctk.CTkLabel(fila, text=str(col2 or ""), anchor="w",
                                 font=ctk.CTkFont(size=11), text_color="gray")
        lbl_col2.pack(side="left", padx=4, pady=4, fill="x", expand=True)

        ctk.CTkFrame(parent, height=1, fg_color=("gray85", "gray25")).pack(fill="x", padx=6)

        if on_click is None:
            return

        widgets = [fila, lbl_icono, lbl_col1, lbl_col2, lbl_estado, lbl_fecha]

        def _on_enter(e):
            try:
                modo = ctk.get_appearance_mode()
                hover_color = "#EAF2FB" if modo == "Light" else "#2C3E50"
            except Exception:
                hover_color = "#EAF2FB"
            for w in widgets:
                try:
                    w.configure(fg_color=hover_color)
                except Exception:
                    pass

        def _on_leave(e):
            for w in widgets:
                try:
                    w.configure(fg_color="transparent")
                except Exception:
                    pass

        def _on_click(e):
            on_click()

        for w in widgets:
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)
            w.bind("<Button-1>", _on_click)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

    def _fila_expediente(self, parent, exp):
        exp_id, codigo_rma, cliente, num_doc, estado, fecha, proveedor = exp
        color = self.get_color_por_estado(estado) if estado else "#7f8c8d"
        detalle = cliente or "Sin cliente"
        if num_doc:
            detalle += f" · Doc: {num_doc}"
        if proveedor:
            detalle += f" · Prov: {proveedor}"
        self._crear_fila(parent, icono="📋",
                          col1=codigo_rma or "Sin código", col1_width=110,
                          col2=detalle,
                          estado_text=estado or "Sin estado", estado_color=color,
                          fecha_text=fecha,
                          on_click=lambda: self._abrir_editor_rma(rma_id=exp_id))

    def _fila_producto(self, parent, prod):
        prod_id, rma_id, referencia, cant_doc, cant_ent, estado_prod, codigo_rma, cliente = prod
        detalle = f"RMA {codigo_rma or '?'} · {cliente or 'Sin cliente'} · Cant: {cant_ent or 0}/{cant_doc or 0}"
        self._crear_fila(parent, icono="📦",
                          col1=referencia or "Sin referencia", col1_width=140,
                          col2=detalle,
                          estado_text=estado_prod or "Sin estado", estado_color="#7f8c8d",
                          fecha_text="",
                          on_click=lambda: self._abrir_editor_rma(rma_id=rma_id))

    def _fila_tarea(self, parent, tarea):
        tarea_id, codigo_rma, titulo, descripcion, estado, fecha_venc, creado_por, rma_id, cliente = tarea
        color = {"Pendiente": "orange", "En Progreso": "#3498db",
                 "Completada": "#27ae60", "Cancelada": "#e74c3c"}.get(estado or "", "#7f8c8d")
        titulo_corto = (titulo or "Sin título")
        if len(titulo_corto) > 40:
            titulo_corto = titulo_corto[:37] + "..."
        detalle = " · ".join(p for p in [codigo_rma, cliente] if p) or "Tarea sin expediente"
        self._crear_fila(parent, icono="✅",
                          col1=titulo_corto, col1_width=220,
                          col2=detalle,
                          estado_text=estado or "Sin estado", estado_color=color,
                          fecha_text=fecha_venc,
                          on_click=(lambda: self._abrir_editor_rma(rma_id=rma_id)) if rma_id else None)

    def _fila_historial(self, parent, hist):
        rma_id, fecha_cambio, descripcion, usuario, codigo_rma, cliente = hist
        desc_corta = descripcion or "Sin descripción"
        if len(desc_corta) > 70:
            desc_corta = desc_corta[:67] + "..."
        self._crear_fila(parent, icono="📜",
                          col1=codigo_rma or "Sin código", col1_width=110,
                          col2=desc_corta,
                          estado_text=usuario or "Sin usuario", estado_color="#3498db",
                          fecha_text=fecha_cambio,
                          on_click=lambda: self._abrir_editor_rma(rma_id=rma_id))
