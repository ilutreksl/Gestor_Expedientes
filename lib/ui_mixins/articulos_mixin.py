"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class ArticulosMixin:
    def mostrar_gestion_rmp(self):
        """Ventana para listar proveedores (rmp_proveedores) y permitir acciones: búsqueda, orden, editar estado y ver expedientes asociados."""
        # Evitar abrir múltiples instancias
        if hasattr(self, 'gestion_rmp_window') and getattr(self, 'gestion_rmp_window').winfo_exists():
            getattr(self, 'gestion_rmp_window').focus()
            return

        self.gestion_rmp_window = ctk.CTkToplevel(self)
        win = self.gestion_rmp_window
        win.title("Gestión RMP - Proveedores")
        win.geometry("1000x650")
        
        # Configurar para permitir minimización
        win.resizable(True, True)
        win.attributes('-topmost', False)
        win.minsize(800, 500)
        # No usar transient ni grab_set para permitir minimización completa
        win.focus_set()  # Dar foco sin bloquear
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        win.attributes('-topmost', True)   # Temporalmente al frente
        win.lift()
        win.focus_force()
        win.after(500, lambda: win.attributes('-topmost', False))  # Quitar topmost después de 500ms
        
        # Agregar icono personalizado
        try:
            win.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            pass

        main = ctk.CTkFrame(win)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(main)
        header.pack(fill="x", pady=(0,8))

        ctk.CTkLabel(header, text="Listado de RMA - Proveedores", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")

        # Búsqueda y filtro por estado
        ctk.CTkLabel(header, text="Buscar:").grid(row=1, column=0, sticky="w", pady=(8,0))
        entry_buscar = ctk.CTkEntry(header, placeholder_text="Escriba parte del numero RMA proveedor...")
        entry_buscar.grid(row=1, column=1, sticky="ew", padx=(8,0), pady=(8,0))
        # Filtro por estado
        ctk.CTkLabel(header, text="Filtrar estado:").grid(row=1, column=2, sticky="w", padx=(12,6), pady=(8,0))
        # Incluir 'Exportado' como una opción de filtro de estado
        estado_filter = ctk.CTkOptionMenu(header, values=["Todos", "En Progreso", "Enviado", "Completado", "Exportado"])
        estado_filter.set("Todos")
        estado_filter.grid(row=1, column=3, sticky="w", padx=(0,6), pady=(8,0))
        header.grid_columnconfigure(1, weight=1)

        btn_buscar = ctk.CTkButton(header, text="🔎", width=40)
        btn_buscar.grid(row=1, column=4, padx=(8,0), pady=(8,0))

        list_frame = ctk.CTkFrame(main)
        list_frame.pack(fill="both", expand=True)

        scroll = ctk.CTkScrollableFrame(list_frame)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Estado de ordenación
        sort_state = {'col': 'nombre', 'dir': 'asc'}

        # Controles de paginación para proveedores
        prov_page = {'page': 1, 'page_size': 20, 'total': 0}
        prov_pframe = ctk.CTkFrame(main)
        prov_pframe.pack(fill="x", padx=12, pady=(6,8))
        prov_prev = ctk.CTkButton(prov_pframe, text="◀ Anterior", width=100)
        prov_prev.pack(side="left", padx=(0,8))
        prov_page_lbl = ctk.CTkLabel(prov_pframe, text=f"Página {prov_page['page']}")
        prov_page_lbl.pack(side="left")
        prov_next = ctk.CTkButton(prov_pframe, text="Siguiente ▶", width=100)
        prov_next.pack(side="left", padx=8)
        prov_size_opt = ctk.CTkOptionMenu(prov_pframe, values=["10","20","50","100"], width=80)
        prov_size_opt.set(str(prov_page['page_size']))
        prov_size_opt.pack(side="right")
        ctk.CTkLabel(prov_pframe, text="Registros por página:").pack(side="right", padx=(0,8))

        # Handlers mínimos: actualizan prov_page y recargan la lista
        def _prov_prev():
            if prov_page['page'] > 1:
                prov_page['page'] -= 1
                try:
                    cargar_proveedores()
                except Exception:
                    pass

        def _prov_next():
            # no conocemos aún prov_page['total'], simplemente incrementamos y dejamos que la consulta limite
            prov_page['page'] += 1
            try:
                cargar_proveedores()
            except Exception:
                pass

        def _prov_size_changed(v):
            try:
                prov_page['page_size'] = int(v)
            except Exception:
                prov_page['page_size'] = 20
            prov_page['page'] = 1
            try:
                cargar_proveedores()
            except Exception:
                pass

        prov_prev.configure(command=_prov_prev)
        prov_next.configure(command=_prov_next)
        prov_size_opt.configure(command=_prov_size_changed)

        # Función para mostrar historial completo de un proveedor y añadir comentarios
        def mostrar_historial_proveedor(proveedor_nombre):
            try:
                vent_hist = ctk.CTkToplevel(self)
                vent_hist.title(f"Historial - {proveedor_nombre}")
                vent_hist.geometry("700x500")
                
                # Configurar para permitir minimización
                vent_hist.resizable(True, True)
                vent_hist.attributes('-topmost', False)
                vent_hist.minsize(600, 400)
                # No usar transient para permitir minimización completa
                vent_hist.focus_set()  # Dar foco sin bloquear
                
                # Forzar aparición al frente (incluso si la principal está maximizada)
                vent_hist.attributes('-topmost', True)   # Temporalmente al frente
                vent_hist.lift()
                try:
                    vent_hist.focus_force()
                except:
                    pass
                
                def quitar_topmost_vent_hist():
                    try:
                        if vent_hist.winfo_exists():
                            vent_hist.attributes('-topmost', False)
                    except:
                        pass
                
                vent_hist.after(500, quitar_topmost_vent_hist)

                cont = ctk.CTkFrame(vent_hist)
                cont.pack(fill="both", expand=True, padx=10, pady=10)

                sf = ctk.CTkScrollableFrame(cont)
                sf.pack(fill="both", expand=True)

                # Cargar historial
                try:
                    connh = connect_db()
                    curh = connh.cursor()
                    curh.execute("SELECT fecha, usuario, estado, comentario FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC", (proveedor_nombre.lower(), proveedor_nombre))
                    hist_rows = curh.fetchall()
                    connh.close()
                except Exception:
                    hist_rows = []

                
                if not hist_rows:
                    try:
                        import sqlite3 as _sqlite
                        local_db = os.path.join(os.path.dirname(__file__), DB_NAME)
                        if os.path.exists(local_db):
                            conn_local = _sqlite.connect(local_db)
                            cur_local = conn_local.cursor()
                            cur_local.execute("SELECT fecha, usuario, estado, comentario FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC", (proveedor_nombre.lower(), proveedor_nombre))
                            hist_rows = cur_local.fetchall()
                            conn_local.close()
                    except Exception:
                        hist_rows = []

                # Mostrar cada entrada
                for idx, (fecha, usuario, estado_h, comentario) in enumerate(hist_rows):
                    # Usar fondo por defecto del tema en lugar de cebra
                    rowf = ctk.CTkFrame(sf, fg_color="transparent")
                    rowf.pack(fill="x", padx=5, pady=3)
                    txt = f"{fecha} - {usuario} - {estado_h or ''}"
                    ctk.CTkLabel(rowf, text=txt, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=6, pady=(4,0))
                    if comentario:
                        ctk.CTkLabel(rowf, text=comentario, wraplength=650).pack(anchor="w", padx=6, pady=(0,6))

                # Area para añadir comentario
                ctk.CTkLabel(cont, text="Añadir comentario:").pack(anchor="w", pady=(8,2))
                comment_box = ctk.CTkTextbox(cont, height=80)
                comment_box.pack(fill="x", pady=(0,8))

                def _add_comment():
                    text = comment_box.get("0.0", "end").strip()
                    if not text:
                        messagebox.showwarning("Vacío", "Escribe un comentario antes de añadirlo.")
                        return
                    try:
                        connc = connect_db()
                        curc = connc.cursor()
                        # Asegurar la tabla existe (por si acaso)
                        curc.execute("CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                        curc.execute("INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)", (proveedor_nombre, '', text, getattr(self, 'username', 'unknown')))
                        connc.commit()
                        connc.close()
                        messagebox.showinfo("Añadido", "Comentario añadido al historial.")
                        # refrescar la ventana
                        vent_hist.destroy()
                        mostrar_historial_proveedor(proveedor_nombre)
                        # refrescar la lista principal
                        try:
                            cargar_proveedores()
                        except Exception:
                            pass
                    except Exception as e:
                        messagebox.showerror("Error BD", f"No se pudo añadir el comentario: {e}")

                ctk.CTkButton(cont, text="Añadir comentario", command=_add_comment).pack(anchor="e")
            except Exception as e:
                messagebox.showerror("Error", f"Error mostrando historial: {e}")

        def cargar_proveedores():
            """Carga la lista de proveedores EXTRAÍDOS de rma_maestro.rma_proveedor (DISTINCT)."""
            for w in scroll.winfo_children():
                w.destroy()
            filtro = entry_buscar.get().strip()
            try:
                conn = connect_db()
                cur = conn.cursor()

                # Asegurar que exista la tabla de proveedores para persistir estados
                try:
                    cur.execute("CREATE TABLE IF NOT EXISTS rma_proveedor (id INTEGER PRIMARY KEY, proveedor TEXT UNIQUE, estado TEXT, factura_abono TEXT)")
                    # Tabla de historial de proveedores: proveedor, estado, comentario, usuario, fecha
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                    )
                    conn.commit()
                    # Nota: La columna factura_abono ya está incluida en la creación de la tabla arriba
                except Exception:
                    # Si no podemos crearla en Turso u otro backend, seguimos sin persistencia
                    pass

                # Construir consulta: obtenemos proveedores distintos de rma_maestro
                # y left-join con rma_proveedor para traer el estado y factura_abono si existe.
                params = []
                search_clause = ""
                if filtro:
                    search_clause = " AND lower(rma_proveedor) LIKE ?"
                    params.append(f"%{filtro.lower()}%")

                direction = 'ASC' if sort_state.get('dir', 'asc') == 'asc' else 'DESC'

                sql = (
                    "SELECT p.proveedor, COALESCE(r.estado, '') as estado, COALESCE(r.factura_abono, '') as factura_abono "
                    "FROM (SELECT DISTINCT rma_proveedor AS proveedor FROM rma_maestro WHERE rma_proveedor IS NOT NULL AND rma_proveedor != ''"
                    + search_clause + ") p "
                    "LEFT JOIN rma_proveedor r ON lower(p.proveedor) = lower(r.proveedor) "
                )

                # Aplicar filtro por estado si no es 'Todos'
                estado_sel = None
                try:
                    estado_sel = estado_filter.get()
                except Exception:
                    estado_sel = "Todos"

                if estado_sel and estado_sel != "Todos":
                    sql += " WHERE r.estado = ?"
                    params.append(estado_sel)

                # Primero calcular total (COUNT) usando la misma subconsulta
                try:
                    count_sql = "SELECT COUNT(*) FROM (" + sql + ") as _sub"
                    cur.execute(count_sql, tuple(params))
                    raw_total = cur.fetchone()[0]
                    try:
                        total = int(raw_total) if raw_total is not None else 0
                    except Exception:
                        # Algunos adaptadores devuelven resultados como strings
                        try:
                            total = int(str(raw_total))
                        except Exception:
                            total = 0
                except Exception:
                    total = 0
                prov_page['total'] = int(total)

                # Aplicar orden y paginación (LIMIT/OFFSET)
                sql += f" ORDER BY p.proveedor {direction}"

                # Asegurar página válida
                try:
                    page_size = int(prov_page.get('page_size', 20))
                except Exception:
                    page_size = 20
                if page_size <= 0:
                    page_size = 20

                total_pages = max(1, (total + page_size - 1) // page_size)
                if prov_page['page'] > total_pages:
                    prov_page['page'] = total_pages
                if prov_page['page'] < 1:
                    prov_page['page'] = 1

                offset = (prov_page['page'] - 1) * page_size
                sql += " LIMIT ? OFFSET ?"
                params_with_limit = list(params) + [page_size, offset]

                cur.execute(sql, tuple(params_with_limit))
                rows = cur.fetchall()

                conn.close()

                # Encabezado simple
                header_row = ctk.CTkFrame(scroll)
                header_row.pack(fill="x", padx=5, pady=(0,5))
                # Ajuste de anchos: reducir PROVEEDOR a la mitad y dar espacio al HISTORIAL
                # PROVEEDOR ~180 (antes 360), ACCIONES ~260, HISTORIAL ~440 (antes 260)
                header_row.grid_columnconfigure(0, weight=1, minsize=180)
                header_row.grid_columnconfigure(1, weight=0, minsize=260)
                header_row.grid_columnconfigure(2, weight=0, minsize=440)
                # Columna extra para botón/ver historial
                header_row.grid_columnconfigure(3, weight=0, minsize=120)

                hf = ctk.CTkFont(weight="bold")
                lbl_nom = ctk.CTkLabel(header_row, text="RMP", font=hf, anchor="w", cursor="hand2")
                lbl_nom.grid(row=0, column=0, padx=5, sticky="w")
                ctk.CTkLabel(header_row, text="ACCIONES", font=hf, anchor="center").grid(row=0, column=1, padx=5)
                ctk.CTkLabel(header_row, text="HISTORIAL", font=hf, anchor="center").grid(row=0, column=2, padx=5)
                ctk.CTkLabel(header_row, text="VER", font=hf, anchor="center").grid(row=0, column=3, padx=5)

                # Alternar orden al pinchar encabezado
                def toggle_sort():
                    sort_state['dir'] = 'desc' if sort_state.get('dir', 'asc') == 'asc' else 'asc'
                    cargar_proveedores()

                lbl_nom.bind("<Button-1>", lambda e: toggle_sort())

                # Filas con estado editable (si es posible)
                colors = ("#FFFFFF", "#F3F4F6")
                # Actualizar etiqueta y estados de botones
                try:
                    total_pages = max(1, (prov_page['total'] + page_size - 1) // page_size)
                    prov_page_lbl.configure(text=f"Página {prov_page['page']} de {total_pages} ({prov_page['total']})")
                    prov_prev.configure(state="normal" if prov_page['page'] > 1 else "disabled")
                    prov_next.configure(state="normal" if prov_page['page'] < total_pages else "disabled")
                except Exception:
                    prov_page_lbl.configure(text=f"Página {prov_page.get('page',1)}")

                for idx, (prov, estado_actual, factura_actual) in enumerate(rows):
                    nombre = prov
                    # Usar fondo por defecto del tema en lugar de cebra
                    bg = "transparent"
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", padx=5, pady=2)
                    # Mantener los minsize solicitados para columnas (consistentes con header)
                    row.grid_columnconfigure(0, weight=1, minsize=180)
                    row.grid_columnconfigure(1, weight=0, minsize=260)
                    row.grid_columnconfigure(2, weight=0, minsize=440)
                    row.grid_columnconfigure(3, weight=0, minsize=120)

                    lbl_nombre = ctk.CTkLabel(row, text=nombre or "-", anchor="w", cursor="hand2")
                    lbl_nombre.grid(row=0, column=0, padx=5, sticky="w")
                    opciones_estado = ["", "En Progreso", "Enviado", "Completado", "Exportado"]
                    try:
                        opt = ctk.CTkOptionMenu(row, values=opciones_estado)
                        # Si no hay estado, dejamos en vacío (primer opción)
                        opt.set(estado_actual if estado_actual in opciones_estado else "")
                    except Exception:
                        opt = ctk.CTkEntry(row)
                        opt.insert(0, estado_actual)
                    opt.grid(row=0, column=1, padx=5, sticky="w")

                    # Última entrada de historial (mostrar último comentario/estado corto)
                    try:
                        conn_h = connect_db()
                        cur_h = conn_h.cursor()
                        cur_h.execute(
                            "SELECT estado, comentario, usuario, fecha FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC LIMIT 1",
                            (nombre.lower(), nombre)
                        )
                        last_hist = cur_h.fetchone()
                        conn_h.close()
                    except Exception:
                        last_hist = None

                    
                    if not last_hist:
                        try:
                            import sqlite3 as _sqlite
                            local_db = os.path.join(os.path.dirname(__file__), DB_NAME)
                            if os.path.exists(local_db):
                                conn_local = _sqlite.connect(local_db)
                                cur_local = conn_local.cursor()
                                cur_local.execute(
                                    "SELECT estado, comentario, usuario, fecha FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC LIMIT 1",
                                    (nombre.lower(), nombre)
                                )
                                last_hist = cur_local.fetchone()
                                conn_local.close()
                        except Exception:
                            pass

                    hist_text = ""
                    if last_hist:
                        lh_estado, lh_coment, lh_user, lh_fecha = last_hist
                        if lh_coment:
                            hist_text = f"{lh_fecha} - {lh_user}: {lh_coment}"
                        else:
                            hist_text = f"{lh_fecha} - {lh_user}: {lh_estado}"

                    # Mostrar columna de historial con acceso al historial completo
                    # Mostrar el texto completo pero permitiendo wrap para no descuadrar columnas
                    hist_lbl_text = hist_text or ""
                    hist_lbl = ctk.CTkLabel(row, text=hist_lbl_text, anchor="w", cursor="hand2", wraplength=420)
                    hist_lbl.grid(row=0, column=2, padx=5, sticky="w")
                    hist_lbl.bind("<Button-1>", lambda e, n=nombre: mostrar_historial_proveedor(n))

                    # Botón para abrir la ventana completa de historial
                    try:
                        btn_hist = ctk.CTkButton(row, text="Ver historial", width=110, command=lambda n=nombre: mostrar_historial_proveedor(n))
                        btn_hist.grid(row=0, column=3, padx=5)
                        Tooltip(btn_hist, "Ver historial completo del proveedor")
                    except Exception:
                        # Si falla la creación del botón, ignoramos para no romper el listado
                        pass

                    # Hover: usar fondo por defecto (transparent) para no añadir colores propios
                    def on_enter(e, r=row):
                        try:
                            r.configure(fg_color="transparent")
                        except Exception:
                            pass
                    def on_leave(e, r=row, original_bg=bg):
                        try:
                            r.configure(fg_color="transparent")
                        except Exception:
                            pass

                    row.bind("<Enter>", on_enter)
                    row.bind("<Leave>", on_leave)
                    lbl_nombre.bind("<Enter>", on_enter)
                    lbl_nombre.bind("<Leave>", on_leave)

                    # Click en nombre abre detalle del proveedor
                    lbl_nombre.bind("<Button-1>", lambda e, nombre=nombre, estado=estado_actual, factura=factura_actual: mostrar_expedientes_proveedor(nombre, estado, factura))

                    # Persistir cambio de estado (upsert) y anotar en historial
                    def make_state_updater(proveedor_nombre, prev_estado):
                        def updater(selected_value):
                            val = selected_value
                            # Si no hay cambio, no hacemos nada
                            try:
                                if (prev_estado is not None) and (str(val) == str(prev_estado)):
                                    return
                            except Exception:
                                pass
                            try:
                                conn3 = connect_db()
                                cur3 = conn3.cursor()
                                # Usar upsert: insertar o actualizar el estado para el proveedor
                                try:
                                    cur3.execute(
                                        "INSERT INTO rma_proveedor (proveedor, estado) VALUES (?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                                        (proveedor_nombre, val)
                                    )
                                except sqlite3.Error:
                                    # Fallback: intentar UPDATE, si no existe, INSERT
                                    cur3.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", (val, proveedor_nombre))
                                    if getattr(cur3, 'rowcount', 0) == 0:
                                        cur3.execute("INSERT INTO rma_proveedor (proveedor, estado) VALUES (?, ?)", (proveedor_nombre, val))

                                # Añadir entrada en historial de proveedor
                                try:
                                    # Asegurar tabla existe
                                    cur3.execute("CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                                except Exception:
                                    pass
                                try:
                                    usuario = getattr(self, 'username', 'unknown')
                                    # Guardar comentario explicativo del cambio de estado
                                    if prev_estado is None or prev_estado == "":
                                        comentario_text = f"Estado establecido a: {val}"
                                    else:
                                        comentario_text = f"Cambio de estado de '{prev_estado}' a '{val}'"
                                    cur3.execute("INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)", (proveedor_nombre, val, comentario_text, usuario))
                                except Exception:
                                    # Si falla en este backend, intentamos igual con conexión nueva/SQLite local (no preferido)
                                    pass

                                try:
                                    conn3.commit()
                                except Exception:
                                    pass
                                try:
                                    conn3.close()
                                except Exception:
                                    pass

                                # Refrescar la lista para mostrar el último historial
                                try:
                                    cargar_proveedores()
                                except Exception:
                                    pass
                            except Exception as e:
                                messagebox.showerror("Error BD", f"No se pudo guardar el estado: {e}")
                        return updater

                    try:
                        # CTkOptionMenu passes the selected value to the command
                        opt.configure(command=make_state_updater(nombre, estado_actual))
                    except Exception:
                        if isinstance(opt, ctk.CTkEntry):
                            opt.bind("<FocusOut>", lambda e, nombre=nombre, w=opt: make_state_updater(nombre, estado_actual)(w.get()))

            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"No se pudo cargar lista de proveedores: {e}")

        def mostrar_expedientes_proveedor(proveedor_nombre, estado_actual='', factura_actual=''):
            """Muestra la ventana de detalle del proveedor con pestañas."""
            from lib.ventana_proveedor import VentanaDetalleProveedor
            
            # Inyectar la clase Tooltip en el módulo para evitar problemas de importación circular
            import lib.ventana_proveedor as modulo_proveedor
            modulo_proveedor.Tooltip = Tooltip
            
            try:
                VentanaDetalleProveedor(
                    parent=self,
                    proveedor_nombre=proveedor_nombre,
                    estado_actual=estado_actual,
                    factura_actual=factura_actual,
                    connect_db_func=connect_db,
                    cargar_proveedores_func=cargar_proveedores,
                    usar_b2_func=usar_b2,
                    get_b2_client_func=get_b2_client
                )
            except Exception as e:
                logger.error(f"Error abriendo ventana de proveedor {proveedor_nombre}: {e}", exc_info=True)
                messagebox.showerror("Error", f"Error al abrir detalle del proveedor: {e}")
        
        def mostrar_expedientes_proveedor_OLD(proveedor_nombre, estado_actual='', factura_actual=''):
            # Ventana detallada del proveedor: info, expedientes, historial y comentarios
            vent = ctk.CTkToplevel(self)
            vent.title(f"Detalle RMP - {proveedor_nombre}")
            vent.geometry("1200x900")
            
            # Configurar para permitir minimización
            vent.resizable(True, True)
            vent.attributes('-topmost', False)
            vent.minsize(900, 600)
            # No usar transient para permitir minimización completa
            vent.focus_set()  # Dar foco sin bloquear
            
            # Forzar aparición al frente (incluso si la principal está maximizada)
            vent.attributes('-topmost', True)   # Temporalmente al frente
            vent.lift()
            try:
                vent.focus_force()
            except:
                pass
            
            def quitar_topmost_vent():
                try:
                    if vent.winfo_exists():
                        vent.attributes('-topmost', False)
                except:
                    pass
            
            vent.after(500, quitar_topmost_vent)

            cont = ctk.CTkFrame(vent)
            cont.pack(fill="both", expand=True, padx=12, pady=12)

            # ===== SECCIÓN 1: ENCABEZADO CON INFORMACIÓN DEL PROVEEDOR =====
            # Usar el color primario del tema activo en lugar de azul fijo
            header_frame = ctk.CTkFrame(cont, corner_radius=8)
            header_frame.pack(fill="x", pady=(0,10))
            header_frame.grid_columnconfigure(0, weight=1)
            header_frame.grid_columnconfigure(1, weight=1)
            header_frame.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(header_frame, text="RMP", font=ctk.CTkFont(size=11, weight="bold"), text_color="white").grid(row=0, column=0, padx=15, pady=(8,2), sticky="w")
            ctk.CTkLabel(header_frame, text=proveedor_nombre, font=ctk.CTkFont(size=14), text_color="white").grid(row=1, column=0, padx=15, pady=(0,8), sticky="w")

            ctk.CTkLabel(header_frame, text="ESTADO", font=ctk.CTkFont(size=11, weight="bold"), text_color="white").grid(row=0, column=1, padx=15, pady=(8,2), sticky="w")
            
            # Variable para rastrear el estado actual
            estado_var = {'actual': estado_actual or ''}
            
            # CTkOptionMenu para editar el estado
            opciones_estado = ["", "En Progreso", "Enviado", "Completado", "Exportado"]
            estado_menu = ctk.CTkOptionMenu(
                header_frame, 
                values=opciones_estado,
                dropdown_fg_color="white",
                dropdown_text_color="#212529"
            )
            estado_menu.set(estado_actual if estado_actual in opciones_estado else "")
            estado_menu.grid(row=1, column=1, padx=15, pady=(0,8), sticky="ew")

            ctk.CTkLabel(header_frame, text="FACTURA ABONO", font=ctk.CTkFont(size=11, weight="bold"), text_color="white").grid(row=0, column=2, padx=15, pady=(8,2), sticky="w")
            factura_entry = ctk.CTkEntry(header_frame, placeholder_text="Ej: FA2025001")
            factura_entry.insert(0, factura_actual or "")
            factura_entry.grid(row=1, column=2, padx=15, pady=(0,8), sticky="ew")

            # Función para actualizar estado
            def actualizar_estado(nuevo_estado):
                estado_anterior = estado_var['actual']
                # Si no hay cambio, no hacemos nada
                if estado_anterior == nuevo_estado:
                    return
                
                try:
                    conn_e = connect_db()
                    cur_e = conn_e.cursor()
                    # Actualizar estado en la tabla
                    try:
                        cur_e.execute(
                            "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                            (proveedor_nombre, nuevo_estado, factura_actual or '')
                        )
                    except Exception:
                        # Fallback para backends sin ON CONFLICT
                        cur_e.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", (nuevo_estado, proveedor_nombre))
                        if getattr(cur_e, 'rowcount', 0) == 0:
                            cur_e.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", (proveedor_nombre, nuevo_estado, factura_actual or ''))
                    
                    # Añadir al historial
                    usuario = getattr(self, 'username', 'unknown')
                    if estado_anterior == '' or estado_anterior is None:
                        comentario_text = f"Estado establecido a: {nuevo_estado}"
                    else:
                        comentario_text = f"Cambio de estado de '{estado_anterior}' a '{nuevo_estado}'"
                    
                    cur_e.execute(
                        "INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)",
                        (proveedor_nombre, nuevo_estado, comentario_text, usuario)
                    )
                    
                    conn_e.commit()
                    conn_e.close()
                    
                    # Actualizar variable local
                    estado_var['actual'] = nuevo_estado
                    
                    # Refrescar historial en esta ventana
                    cargar_historial()
                    
                    # Refrescar lista principal
                    try:
                        cargar_proveedores()
                    except Exception:
                        pass
                    
                    messagebox.showinfo("Actualizado", "Estado actualizado correctamente.")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo actualizar el estado: {e}")
            
            # Configurar el comando del menú de estado
            estado_menu.configure(command=actualizar_estado)

            # Botón para guardar cambios de factura_abono
            def guardar_factura():
                nueva_factura = factura_entry.get().strip()
                try:
                    conn_f = connect_db()
                    cur_f = conn_f.cursor()
                    # Actualizar factura_abono (usar el estado actual de estado_var)
                    try:
                        cur_f.execute(
                            "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET factura_abono=excluded.factura_abono",
                            (proveedor_nombre, estado_var['actual'], nueva_factura)
                        )
                    except Exception:
                        # Fallback para backends sin ON CONFLICT
                        cur_f.execute("UPDATE rma_proveedor SET factura_abono = ? WHERE proveedor = ?", (nueva_factura, proveedor_nombre))
                        if getattr(cur_f, 'rowcount', 0) == 0:
                            cur_f.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", (proveedor_nombre, estado_var['actual'], nueva_factura))
                    conn_f.commit()
                    conn_f.close()
                    messagebox.showinfo("Guardado", "Factura de abono actualizada correctamente.")
                    # Refrescar lista principal
                    try:
                        cargar_proveedores()
                    except Exception:
                        pass
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo guardar la factura: {e}")

            ctk.CTkButton(header_frame, text="💾 Guardar Factura", command=guardar_factura, width=130).grid(row=1, column=3, padx=(5,15), pady=(0,8))

            # ===== SECCIÓN 2: LISTADO DE EXPEDIENTES =====
            exp_frame = ctk.CTkFrame(cont)
            exp_frame.pack(fill="both", expand=True, pady=(0,10))

            ctk.CTkLabel(exp_frame, text="Expedientes Asociados", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=5, pady=(5,5))

            sf_exp = ctk.CTkScrollableFrame(exp_frame, height=250)
            sf_exp.pack(fill="both", expand=True, padx=5, pady=(0,5))

            # Cargar expedientes del proveedor
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, codigo_rma, cliente, numero_documento_cliente, modelo, ref_proveedor, fecha_emision, estado "
                    "FROM rma_maestro WHERE lower(Rma_Proveedor)=? OR Rma_Proveedor=? ORDER BY fecha_emision DESC",
                    (proveedor_nombre.lower(), proveedor_nombre)
                )
                filas = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Error BD", f"No se pudieron cargar expedientes: {e}")
                filas = []

            # Función para exportar a Excel
            def export_to_excel():
                try:
                    if not filas:
                        messagebox.showinfo('Exportar', 'No hay expedientes para exportar.')
                        return
                    
                    data = []
                    for r in filas:
                        (_id, codigo_rma, cliente, num_doc, modelo, ref_prov, fecha_emision, estado) = r
                        data.append({
                            'Nº Expediente': codigo_rma,
                            'Proveedor': proveedor_nombre,
                            'Cliente': cliente or '',
                            'Numero Documento Cliente': num_doc or '',
                            'Descripcion Articulo': modelo or '',
                            'Referencia': ref_prov or ''
                        })

                    df = pd.DataFrame(data)
                    base_dir = os.path.join(os.path.dirname(__file__), 'Adjuntos_RMA')
                    rmp_dir = os.path.join(base_dir, 'RMP')
                    os.makedirs(rmp_dir, exist_ok=True)

                    safe_name = ''.join(c for c in proveedor_nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_name = safe_name.replace(' ', '_')
                    file_path = os.path.join(rmp_dir, f"{safe_name}.xlsx")

                    if os.path.exists(file_path):
                        if not messagebox.askyesno('Exportar', f'El archivo {os.path.basename(file_path)} ya existe. ¿Desea sobreescribirlo?'):
                            return

                    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Expedientes')
                        workbook = writer.book
                        worksheet = writer.sheets['Expedientes']
                        from openpyxl.utils import get_column_letter
                        for i, col in enumerate(df.columns):
                            if df.empty:
                                max_len = len(str(col))
                            else:
                                col_max = df[col].astype(str).map(len).max()
                                max_len = max(int(col_max) if col_max is not None else 0, len(str(col)))
                            adjusted_width = min(max_len + 2, 60)
                            worksheet.column_dimensions[get_column_letter(i+1)].width = adjusted_width

                    messagebox.showinfo('Exportar', f'Exportado correctamente: {file_path}')

                    # Subir archivo a Backblaze B2
                    if usar_b2():
                        try:
                            # Crear ruta en Backblaze B2: RMP/{nombre_proveedor}.xlsx
                            b2_path = f"RMP/{safe_name}.xlsx"
                            
                            b2_api, bucket = get_b2_client()
                            if b2_api and bucket:
                                # Subir archivo a Backblaze B2 (sobreescribir si existe)
                                bucket.upload_local_file(
                                    local_file=file_path,
                                    file_name=b2_path
                                )
                                
                                print(f"✅ Excel RMP subido a Backblaze B2: {b2_path}")
                                # Opcional: mostrar confirmación al usuario
                                # messagebox.showinfo('Backblaze B2', f'Archivo también guardado en Backblaze B2: {b2_path}')
                            
                        except Exception as e:
                            print(f"⚠️ Error subiendo Excel RMP a Backblaze B2: {e}")
                            # No mostrar error al usuario para no interrumpir el flujo
                    else:
                        print("ℹ️ Dropbox no configurado, Excel solo guardado localmente")

                    # Añadir a historial
                    try:
                        connh = connect_db()
                        curh = connh.cursor()
                        rma_codes = [str(r[1]) for r in filas if len(r) > 1 and r[1] is not None]
                        count = len(filas)
                        codes_str = ', '.join(rma_codes)
                        if len(codes_str) > 500:
                            codes_str = codes_str[:500] + '...'
                        comentario = f'Exportado {count} expedientes a Excel: {os.path.basename(file_path)}'
                        if codes_str:
                            comentario += f' (RMAs: {codes_str})'
                        usuario = getattr(self, 'username', 'unknown')
                        curh.execute(
                            "INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)",
                            (proveedor_nombre, 'Exportado', comentario, usuario)
                        )
                        try:
                            curh.execute(
                                "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                                (proveedor_nombre, 'Exportado', factura_actual or '')
                            )
                        except Exception:
                            curh.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", ('Exportado', proveedor_nombre))
                            if getattr(curh, 'rowcount', 0) == 0:
                                curh.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", (proveedor_nombre, 'Exportado', factura_actual or ''))
                        connh.commit()
                        connh.close()
                        # Refrescar historial en esta ventana
                        cargar_historial()
                        cargar_proveedores()
                    except Exception as e:
                        print(f'Warning: error en historial: {e}')
                except Exception as e:
                    messagebox.showerror('Exportar', f'Error exportando a Excel: {e}')

            # Botón exportar
            btn_frame = ctk.CTkFrame(exp_frame)
            btn_frame.pack(fill="x", padx=5, pady=(0,5))
            ctk.CTkButton(btn_frame, text="📊 Exportar a Excel", command=export_to_excel, width=150).pack(side="right")

            # Encabezado de expedientes
            head = ctk.CTkFrame(sf_exp)
            head.pack(fill="x", padx=5, pady=(0,5))
            head.grid_columnconfigure(0, weight=1, minsize=150)
            head.grid_columnconfigure(1, weight=2, minsize=250)
            head.grid_columnconfigure(2, weight=1, minsize=120)
            head.grid_columnconfigure(3, weight=1, minsize=120)
            head.grid_columnconfigure(4, weight=0, minsize=80)

            hf = ctk.CTkFont(weight="bold")
            ctk.CTkLabel(head, text="CÓDIGO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
            ctk.CTkLabel(head, text="CLIENTE", font=hf).grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(head, text="FECHA", font=hf).grid(row=0, column=2, padx=5, sticky="w")
            ctk.CTkLabel(head, text="ESTADO", font=hf).grid(row=0, column=3, padx=5, sticky="w")
            ctk.CTkLabel(head, text="", font=hf).grid(row=0, column=4, padx=5)

            # Filas de expedientes
            colors = ("#FFFFFF", "#F7F7F7")
            for idx, r in enumerate(filas):
                try:
                    rma_id, codigo, cliente, num_doc, modelo, ref_prov, fecha, estado = r
                except Exception:
                    vals = list(r)
                    rma_id = vals[0] if len(vals) > 0 else None
                    codigo = vals[1] if len(vals) > 1 else ''
                    cliente = vals[2] if len(vals) > 2 else ''
                    fecha = vals[6] if len(vals) > 6 else ''
                    estado = vals[7] if len(vals) > 7 else ''

                # Usar fondo por defecto del tema en lugar de cebra
                bg = "transparent"
                row = ctk.CTkFrame(sf_exp, fg_color="transparent")
                row.pack(fill="x", padx=5, pady=2)
                row.grid_columnconfigure(0, weight=1, minsize=150)
                row.grid_columnconfigure(1, weight=2, minsize=250)
                row.grid_columnconfigure(2, weight=1, minsize=120)
                row.grid_columnconfigure(3, weight=1, minsize=120)
                row.grid_columnconfigure(4, weight=0, minsize=80)

                lbl_codigo = ctk.CTkLabel(row, text=codigo, anchor="w", cursor="hand2")
                lbl_codigo.grid(row=0, column=0, padx=5, sticky="w")
                lbl_cliente = ctk.CTkLabel(row, text=cliente if cliente else "-", anchor="w")
                lbl_cliente.grid(row=0, column=1, padx=5, sticky="w")
                lbl_fecha = ctk.CTkLabel(row, text=fecha if fecha else "-", anchor="w")
                lbl_fecha.grid(row=0, column=2, padx=5, sticky="w")
                lbl_estado = ctk.CTkLabel(row, text=estado if estado else "-", anchor="w")
                lbl_estado.grid(row=0, column=3, padx=5, sticky="w")

                ctk.CTkButton(row, text="Editar", width=70, command=lambda rid=rma_id: self._abrir_editor_rma(rma_id=rid)).grid(row=0, column=4, padx=5)

                # Hover
                def on_enter(e, r=row):
                    try:
                        r.configure(fg_color="transparent")
                    except Exception:
                        pass
                def on_leave(e, r=row, original_bg=bg):
                    try:
                        r.configure(fg_color="transparent")
                    except Exception:
                        pass

                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)

                # Doble clic abre editor
                row.bind("<Double-Button-1>", lambda e, rid=rma_id: self._abrir_editor_rma(rma_id=rid))
                lbl_codigo.bind("<Double-Button-1>", lambda e, rid=rma_id: self._abrir_editor_rma(rma_id=rid))

            # ===== SECCIÓN 3: HISTORIAL DEL PROVEEDOR =====
            hist_frame = ctk.CTkFrame(cont)
            hist_frame.pack(fill="both", expand=True, pady=(0,10))

            ctk.CTkLabel(hist_frame, text="Historial del Proveedor", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=5, pady=(5,5))

            sf_hist = ctk.CTkScrollableFrame(hist_frame, height=180)
            sf_hist.pack(fill="both", expand=True, padx=5, pady=(0,5))

            def cargar_historial():
                for w in sf_hist.winfo_children():
                    w.destroy()
                try:
                    conn_h = connect_db()
                    cur_h = conn_h.cursor()
                    cur_h.execute(
                        "SELECT fecha, usuario, estado, comentario FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC",
                        (proveedor_nombre.lower(), proveedor_nombre)
                    )
                    hist_rows = cur_h.fetchall()
                    conn_h.close()

                    if not hist_rows:
                        ctk.CTkLabel(sf_hist, text="No hay historial registrado.", text_color="gray").pack(anchor="w", padx=5, pady=10)
                    else:
                        for idx, (fecha, usuario, estado_h, comentario) in enumerate(hist_rows):
                            # Usar fondo por defecto del tema en lugar de filas cebra
                            rowf = ctk.CTkFrame(sf_hist, fg_color="transparent", corner_radius=6)
                            rowf.pack(fill="x", padx=3, pady=3)
                            txt = f"📅 {fecha} | 👤 {usuario}"
                            if estado_h:
                                txt += f" | 🏷️ {estado_h}"
                            ctk.CTkLabel(rowf, text=txt, font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6,2))
                            if comentario:
                                ctk.CTkLabel(rowf, text=comentario, wraplength=1100, anchor="w").pack(anchor="w", padx=8, pady=(0,6))
                except Exception as e:
                    ctk.CTkLabel(sf_hist, text=f"Error cargando historial: {e}", text_color="red").pack(anchor="w", padx=5, pady=10)

            cargar_historial()

            # ===== SECCIÓN 4: AÑADIR COMENTARIO =====
            comment_frame = ctk.CTkFrame(cont)
            comment_frame.pack(fill="x")

            ctk.CTkLabel(comment_frame, text="Añadir comentario al historial:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=(5,3))
            comment_box = ctk.CTkTextbox(comment_frame, height=60)
            comment_box.pack(fill="x", padx=5, pady=(0,5))

            def add_comment():
                text = comment_box.get("0.0", "end").strip()
                if not text:
                    messagebox.showwarning("Vacío", "Escribe un comentario antes de añadirlo.")
                    return
                try:
                    connc = connect_db()
                    curc = connc.cursor()
                    curc.execute("CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    curc.execute("INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)", 
                                (proveedor_nombre, '', text, getattr(self, 'username', 'unknown')))
                    connc.commit()
                    connc.close()
                    messagebox.showinfo("Añadido", "Comentario añadido al historial.")
                    comment_box.delete("0.0", "end")
                    cargar_historial()
                    cargar_proveedores()
                except Exception as e:
                    messagebox.showerror("Error BD", f"No se pudo añadir el comentario: {e}")

            ctk.CTkButton(comment_frame, text="💬 Añadir Comentario", command=add_comment, width=180).pack(anchor="e", padx=5, pady=(0,5))

        # Vincular búsqueda
        btn_buscar.configure(command=cargar_proveedores)
        try:
            estado_filter.configure(command=lambda v=None: cargar_proveedores())
        except Exception:
            pass
        entry_buscar.bind("<Return>", lambda e: cargar_proveedores())

        # Cargar inicialmente
        cargar_proveedores()

    def mostrar_articulos_window(self):
        """Muestra una ventana con el listado de artículos y la cantidad de expedientes relacionados."""
        # Evitar múltiples instancias
        if hasattr(self, 'articulos_window') and getattr(self, 'articulos_window').winfo_exists():
            getattr(self, 'articulos_window').focus()
            return

        self.articulos_window = ctk.CTkToplevel(self)
        win = self.articulos_window
        win.title("Artículos")
        win.geometry("800x600")
        
        # Configurar para permitir minimización
        win.resizable(True, True)
        win.attributes('-topmost', False)
        win.minsize(600, 400)
        # No usar transient ni grab_set para permitir minimización completa
        win.focus_set()  # Dar foco sin bloquear
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        win.attributes('-topmost', True)   # Temporalmente al frente
        win.lift()
        win.focus_force()
        win.after(500, lambda: win.attributes('-topmost', False))  # Quitar topmost después de 500ms

        main = ctk.CTkFrame(win)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(main)
        header.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(header, text="Listado de Artículos", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")

        # Frame para la lista con scroll (con búsqueda, paginación y carga en background)
        list_frame = ctk.CTkFrame(main)
        list_frame.pack(fill="both", expand=True)

        canvas = ctk.CTkCanvas(list_frame, borderwidth=0, highlightthickness=0)
        try:
            from tkinter import Canvas as _Canvas
            canvas = _Canvas(list_frame, borderwidth=0, highlightthickness=0)
        except Exception:
            pass

        sb = ctk.CTkScrollbar(list_frame, orientation="vertical", command=lambda *args: canvas.yview(*args))
        canvas.configure(yscrollcommand=lambda *args: sb.set(*args))
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = ctk.CTkFrame(canvas)
        try:
            window_id = canvas.create_window((0,0), window=sf, anchor="nw")
        except Exception:
            window_id = canvas.create_window((0,0), window=sf, anchor="nw")

        def on_sf_configure(event):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

        def on_canvas_config(event):
            try:
                canvas.itemconfig(window_id, width=event.width)
            except Exception:
                pass

        sf.bind("<Configure>", on_sf_configure)
        canvas.bind("<Configure>", on_canvas_config)
        
        # Habilitar scroll con rueda del mouse
        def on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except Exception:
                pass
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        # Limpiar binding cuando se cierre la ventana
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Controles de búsqueda y paginación en el header
        search_var = tk.StringVar()
        page_state = {"page": 1, "total_pages": 1}

        ctk.CTkLabel(header, text="Buscar:").grid(row=1, column=0, sticky="w", pady=(6,0))
        search_entry = ctk.CTkEntry(header, textvariable=search_var, placeholder_text="Referencia...", width=300)
        search_entry.grid(row=1, column=1, sticky="w", padx=(8,0), pady=(6,0))

        page_size_opt = ctk.CTkOptionMenu(header, values=["10","25","50","100"])
        page_size_opt.set("50")
        page_size_opt.grid(row=1, column=2, padx=(12,0), pady=(6,0))

        btn_prev = ctk.CTkButton(header, text="◀", width=40)
        btn_prev.grid(row=1, column=3, padx=(12,2), pady=(6,0))
        page_label = ctk.CTkLabel(header, text="Página 1/1")
        page_label.grid(row=1, column=4, padx=(2,6), pady=(6,0))
        btn_next = ctk.CTkButton(header, text="▶", width=40)
        btn_next.grid(row=1, column=5, padx=(2,0), pady=(6,0))

        # Progress indicator removed for cleaner UI (was showing next to pagination controls)
        # If needed in the future, re-add a subtle indicator and start/stop it when loading asynchronously.

        # Container for rows so we can clear it on reload
        rows_container = ctk.CTkFrame(sf)
        rows_container.pack(fill="both", expand=True)

        def render_rows(filas, page, total_count, page_size):
            # Clear previous rows
            for w in rows_container.winfo_children():
                w.destroy()

            hf = ctk.CTkFont(weight="bold")
            header_frame = ctk.CTkFrame(rows_container)
            header_frame.pack(fill="x", padx=5, pady=(0,4))
            header_frame.grid_columnconfigure(0, weight=3, minsize=300)
            header_frame.grid_columnconfigure(1, weight=1, minsize=80)
            ctk.CTkLabel(header_frame, text="REFERENCIA ARTÍCULO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
            ctk.CTkLabel(header_frame, text="EXPEDIENTES", font=hf).grid(row=0, column=1, padx=5, sticky="w")

            colors = ("#FFFFFF", "#F3F4F6")
            for idx, row in enumerate(filas):
                try:
                    referencia, cnt = row[0], row[1]
                except Exception:
                    vals = list(row)
                    referencia = vals[0] if len(vals) > 0 else ''
                    cnt = vals[1] if len(vals) > 1 else 0

                # Usar fondo por defecto del tema en lugar de cebra
                bg = "transparent"
                rf = ctk.CTkFrame(rows_container, fg_color="transparent")
                rf.pack(fill="x", padx=5, pady=2)
                rf.grid_columnconfigure(0, weight=3, minsize=300)
                rf.grid_columnconfigure(1, weight=1, minsize=80)

                lbl_ref = ctk.CTkLabel(rf, text=referencia or '-', anchor="w", cursor="hand2")
                lbl_ref.grid(row=0, column=0, padx=5, sticky="w")
                lbl_cnt = ctk.CTkLabel(rf, text=str(cnt), anchor="w")
                lbl_cnt.grid(row=0, column=1, padx=5, sticky="w")

                ctk.CTkButton(rf, text="Ver Expedientes", width=140, command=lambda r=referencia: self.mostrar_expedientes_por_articulo(r)).grid(row=0, column=2, padx=6)

                def on_enter(e, w=rf):
                    try:
                        w.configure(fg_color="transparent")
                    except Exception:
                        pass
                def on_leave(e, w=rf, original=bg):
                    try:
                        w.configure(fg_color="transparent")
                    except Exception:
                        pass

                rf.bind("<Enter>", on_enter)
                rf.bind("<Leave>", on_leave)
                # Doble clic ahora muestra los estados del artículo con sus totales
                lbl_ref.bind("<Double-Button-1>", lambda e, r=referencia: self.mostrar_estados_por_articulo(r))

            # Ensure numeric types for pagination calculation
            try:
                total_count = int(total_count or 0)
            except Exception:
                try:
                    total_count = int(float(total_count))
                except Exception:
                    total_count = 0
            try:
                page_size = int(page_size)
            except Exception:
                page_size = 50

            # Update page info label
            total_pages = max(1, (total_count + page_size - 1) // page_size)
            page_state["page"] = page
            page_state["total_pages"] = total_pages
            page_label.configure(text=f"Página {page}/{total_pages}")

        def load_articles_thread(page=1):
            try:
                # Progressbar removed from UI; directly schedule data rendering when ready.
                search = search_var.get().strip()
                page_size = int(page_size_opt.get())
                offset = (page - 1) * page_size

                conn = connect_db()
                cur = conn.cursor()

                # Count total
                try:
                    if search:
                        cur.execute("SELECT COUNT(DISTINCT referencia_articulo) FROM rma_detalles WHERE referencia_articulo LIKE ?", (f"%{search}%",))
                    else:
                        cur.execute("SELECT COUNT(DISTINCT referencia_articulo) FROM rma_detalles")
                    total = cur.fetchone()[0]
                    total = int(total) if total is not None else 0
                except Exception:
                    total = 0

                # Main query with limit/offset
                params = []
                where = ""
                if search:
                    where = "WHERE referencia_articulo LIKE ?"
                    params.append(f"%{search}%")

                sql = f"SELECT referencia_articulo, COUNT(DISTINCT rma_maestro.id) as expedientes_count FROM rma_detalles INNER JOIN rma_maestro ON rma_detalles.rma_id = rma_maestro.id {where} GROUP BY referencia_articulo ORDER BY expedientes_count DESC, referencia_articulo ASC LIMIT ? OFFSET ?"
                params.extend([page_size, offset])
                cur.execute(sql, tuple(params))
                filas = cur.fetchall()
                conn.close()
                # Schedule UI update (render rows directly)
                self.after(0, lambda: render_rows(filas, page, total, page_size))
            except Exception as e:
                # No progressbar to stop; show error to user
                self.after(0, lambda: messagebox.showerror("Error BD", f"No se pudieron cargar los artículos: {e}"))

        def start_load(page=1):
            threading.Thread(target=load_articles_thread, args=(page,), daemon=True).start()

        def goto_prev():
            p = max(1, page_state.get("page", 1) - 1)
            start_load(p)

        def goto_next():
            p = page_state.get("page", 1) + 1
            if page_state.get("total_pages", 1) and p > page_state.get("total_pages"):
                return
            start_load(p)

        btn_prev.configure(command=goto_prev)
        btn_next.configure(command=goto_next)
        search_entry.bind("<Return>", lambda e: start_load(1))

        # Cargar inicialmente
        start_load(1)

    def mostrar_estados_por_articulo(self, referencia):
        """Muestra una ventana con los estados que ha tenido un artículo, con suma de cantidades y total en euros por estado."""
        if not referencia:
            messagebox.showinfo("Info", "Referencia vacía.")
            return

        from lib.articulo_utils import VentanaEstadosArticulo
        VentanaEstadosArticulo(self, referencia, connect_db)

    def mostrar_expedientes_por_articulo(self, referencia):
        """Muestra una ventana con los expedientes asociados a una referencia de artículo."""
        if not referencia:
            messagebox.showinfo("Info", "Referencia vacía.")
            return

        # Evitar múltiples instancias por la misma referencia
        name = f"exp_{referencia}"
        # No strict unique naming; we just open a new window
        vent = ctk.CTkToplevel(self)
        vent.title(f"Expedientes - {referencia}")
        vent.geometry("900x600")
        
        # Configurar para permitir minimización
        vent.resizable(True, True)
        vent.attributes('-topmost', False)
        vent.minsize(700, 450)
        # No usar transient para permitir minimización completa
        try:
            vent.focus_set()  # Dar foco sin bloquear
        except:
            pass
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        vent.attributes('-topmost', True)   # Temporalmente al frente
        vent.lift()
        try:
            vent.focus_force()
        except:
            pass
        
        # Función segura para quitar topmost
        def quitar_topmost():
            try:
                if vent.winfo_exists():
                    vent.attributes('-topmost', False)
            except:
                pass
        
        vent.after(500, quitar_topmost)

        main = ctk.CTkFrame(vent)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(main)
        header.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(header, text=f"Expedientes asociados a: {referencia}", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")

        list_frame = ctk.CTkFrame(main)
        list_frame.pack(fill="both", expand=True)

        canvas = ctk.CTkCanvas(list_frame, borderwidth=0, highlightthickness=0)
        try:
            from tkinter import Canvas as _Canvas
            canvas = _Canvas(list_frame, borderwidth=0, highlightthickness=0)
        except Exception:
            pass
        sb = ctk.CTkScrollbar(list_frame, orientation="vertical", command=lambda *args: canvas.yview(*args))
        canvas.configure(yscrollcommand=lambda *args: sb.set(*args))
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        sf = ctk.CTkFrame(canvas)
        try:
            window_id = canvas.create_window((0,0), window=sf, anchor="nw")
        except Exception:
            window_id = canvas.create_window((0,0), window=sf, anchor="nw")

        def on_sf_config(event):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

        def on_canvas_cfg(event):
            try:
                canvas.itemconfig(window_id, width=event.width)
            except Exception:
                pass

        sf.bind("<Configure>", on_sf_config)
        canvas.bind("<Configure>", on_canvas_cfg)

        # Añadimos búsqueda, paginación y carga en background para la lista de expedientes
        search_var = tk.StringVar()
        page_state = {"page": 1, "total_pages": 1}

        ctk.CTkLabel(header, text="Buscar (RMA/Cliente/Doc):").grid(row=1, column=0, sticky="w", pady=(6,0))
        search_entry = ctk.CTkEntry(header, textvariable=search_var, placeholder_text="Texto a buscar...", width=350)
        search_entry.grid(row=1, column=1, sticky="w", padx=(8,0), pady=(6,0))

        page_size_opt = ctk.CTkOptionMenu(header, values=["10","25","50","100"])
        page_size_opt.set("50")
        page_size_opt.grid(row=1, column=2, padx=(12,0), pady=(6,0))

        btn_prev = ctk.CTkButton(header, text="◀", width=40)
        btn_prev.grid(row=1, column=3, padx=(12,2), pady=(6,0))
        page_label = ctk.CTkLabel(header, text="Página 1/1")
        page_label.grid(row=1, column=4, padx=(2,6), pady=(6,0))
        btn_next = ctk.CTkButton(header, text="▶", width=40)
        btn_next.grid(row=1, column=5, padx=(2,0), pady=(6,0))

        rows_container = ctk.CTkFrame(sf)
        rows_container.pack(fill="both", expand=True)

        def render_rows_expedientes(filas, page, total_count, page_size):
            for w in rows_container.winfo_children():
                w.destroy()

            head = ctk.CTkFrame(rows_container)
            head.pack(fill="x", padx=5, pady=(0,4))
            hf = ctk.CTkFont(weight="bold")
            head.grid_columnconfigure(0, weight=1, minsize=160)
            head.grid_columnconfigure(1, weight=2, minsize=300)
            head.grid_columnconfigure(2, weight=1, minsize=140)
            head.grid_columnconfigure(3, weight=1, minsize=140)
            ctk.CTkLabel(head, text="RMA", font=hf).grid(row=0, column=0, padx=5, sticky="w")
            ctk.CTkLabel(head, text="CLIENTE", font=hf).grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(head, text="DOCUMENTO", font=hf).grid(row=0, column=2, padx=5, sticky="w")
            ctk.CTkLabel(head, text="ESTADO ARTÍCULO", font=hf).grid(row=0, column=3, padx=5, sticky="w")

            colors = ("#FFFFFF", "#F3F4F6")
            for idx, r in enumerate(filas):
                try:
                    rma_id, codigo, cliente, num_doc, estado = r
                except Exception:
                    vals = list(r)
                    rma_id = vals[0] if len(vals) > 0 else None
                    codigo = vals[1] if len(vals) > 1 else ''
                    cliente = vals[2] if len(vals) > 2 else ''
                    num_doc = vals[3] if len(vals) > 3 else ''
                    estado = vals[4] if len(vals) > 4 else ''

                # Usar fondo por defecto del tema en lugar de cebra
                bg = "transparent"
                rowf = ctk.CTkFrame(rows_container, fg_color="transparent")
                rowf.pack(fill="x", padx=5, pady=2)
                rowf.grid_columnconfigure(0, weight=1, minsize=160)
                rowf.grid_columnconfigure(1, weight=2, minsize=300)
                rowf.grid_columnconfigure(2, weight=1, minsize=140)
                rowf.grid_columnconfigure(3, weight=1, minsize=140)

                lbl_codigo = ctk.CTkLabel(rowf, text=codigo or '-', anchor="w", cursor="hand2")
                lbl_codigo.grid(row=0, column=0, padx=5, sticky="w")
                lbl_cliente = ctk.CTkLabel(rowf, text=cliente or '-', anchor="w")
                lbl_cliente.grid(row=0, column=1, padx=5, sticky="w")
                lbl_doc = ctk.CTkLabel(rowf, text=num_doc or '-', anchor="w")
                lbl_doc.grid(row=0, column=2, padx=5, sticky="w")
                lbl_estado = ctk.CTkLabel(rowf, text=estado or '-', anchor="w")
                lbl_estado.grid(row=0, column=3, padx=5, sticky="w")

                acciones = ctk.CTkFrame(rowf, fg_color="transparent")
                acciones.grid(row=0, column=4, padx=5)
                ctk.CTkButton(acciones, text="Abrir", width=90, command=lambda rid=rma_id: (self._abrir_editor_rma(rma_id=rid), vent.destroy())).pack(side="left", padx=4)

                def on_ent(e, r=rowf):
                    try:
                        r.configure(fg_color="transparent")
                    except Exception:
                        pass
                def on_lve(e, r=rowf, original=bg):
                    try:
                        r.configure(fg_color=original)
                    except Exception:
                        pass

                rowf.bind("<Enter>", on_ent)
                rowf.bind("<Leave>", on_lve)
                rowf.bind("<Double-Button-1>", lambda e, rid=rma_id: (self._abrir_editor_rma(rma_id=rid), vent.destroy()))
                lbl_codigo.bind("<Double-Button-1>", lambda e, rid=rma_id: (self._abrir_editor_rma(rma_id=rid), vent.destroy()))

            # Ensure numeric types for pagination calculation
            try:
                total_count = int(total_count or 0)
            except Exception:
                try:
                    total_count = int(float(total_count))
                except Exception:
                    total_count = 0
            try:
                page_size = int(page_size)
            except Exception:
                page_size = 50

            total_pages = max(1, (total_count + page_size - 1) // page_size)
            page_state["page"] = page
            page_state["total_pages"] = total_pages
            page_label.configure(text=f"Página {page}/{total_pages}")

        def load_expedientes_thread(page=1):
            try:
                search = search_var.get().strip()
                page_size = int(page_size_opt.get())
                offset = (page - 1) * page_size

                conn = connect_db()
                cur = conn.cursor()

                # Count total
                try:
                    if search:
                        cnt_sql = "SELECT COUNT(DISTINCT T2.id) FROM rma_detalles T1 JOIN rma_maestro T2 ON T1.rma_id = T2.id WHERE T1.referencia_articulo = ? AND (T2.codigo_rma LIKE ? OR T2.cliente LIKE ? OR T2.numero_documento_cliente LIKE ?)"
                        cur.execute(cnt_sql, (referencia, f"%{search}%", f"%{search}%", f"%{search}%"))
                    else:
                        cnt_sql = "SELECT COUNT(DISTINCT T2.id) FROM rma_detalles T1 JOIN rma_maestro T2 ON T1.rma_id = T2.id WHERE T1.referencia_articulo = ?"
                        cur.execute(cnt_sql, (referencia,))
                    total = cur.fetchone()[0]
                    total = int(total) if total is not None else 0
                except Exception:
                    total = 0

                # Main query
                params = [referencia]
                where = ""
                if search:
                    where = "AND (T2.codigo_rma LIKE ? OR T2.cliente LIKE ? OR T2.numero_documento_cliente LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

                sql = f"SELECT DISTINCT T2.id, T2.codigo_rma, T2.cliente, T2.numero_documento_cliente, T1.estado_producto FROM rma_detalles T1 JOIN rma_maestro T2 ON T1.rma_id = T2.id WHERE T1.referencia_articulo = ? {where} ORDER BY T2.fecha_emision DESC LIMIT ? OFFSET ?"
                params.extend([page_size, offset])
                cur.execute(sql, tuple(params))
                filas = cur.fetchall()
                conn.close()
                self.after(0, lambda: render_rows_expedientes(filas, page, total, page_size))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error BD", f"No se pudieron cargar expedientes: {e}"))

        def start_load_expedientes(page=1):
            threading.Thread(target=load_expedientes_thread, args=(page,), daemon=True).start()

        def prev_page():
            p = max(1, page_state.get("page", 1) - 1)
            start_load_expedientes(p)

        def next_page():
            p = page_state.get("page", 1) + 1
            if page_state.get("total_pages", 1) and p > page_state.get("total_pages"):
                return
            start_load_expedientes(p)

        btn_prev.configure(command=prev_page)
        btn_next.configure(command=next_page)
        search_entry.bind("<Return>", lambda e: start_load_expedientes(1))

        # Cargar inicialmente
        start_load_expedientes(1)

    def mostrar_ventana_estadisticas(self):
        """Crea y muestra la ventana Toplevel y la estructura de navegación interna para estadísticas."""
        
        # 1. Prevenir que se abra más de una vez (si ya existe, simplemente enfocarla)
        if hasattr(self, 'stats_window') and self.stats_window.winfo_exists():
            self.stats_window.focus()
            return

        # Crear una nueva ventana modal pero independiente
        self.stats_window = ctk.CTkToplevel(self)
        self.stats_window.title("Módulo de Estadísticas")
        self.stats_window.geometry("1600x900")
        self.stats_window.minsize(800, 600)  # Tamaño mínimo para asegurar legibilidad
        
        # Configurar para permitir minimización
        self.stats_window.resizable(True, True)
        self.stats_window.attributes('-topmost', False)
        
        # Centrar la ventana en la pantalla
        screen_width = self.stats_window.winfo_screenwidth()
        screen_height = self.stats_window.winfo_screenheight()
        x = (screen_width - 1600) // 2
        y = (screen_height - 900) // 2
        self.stats_window.geometry(f"1600x900+{x}+{y}")

        # Marco principal que contendrá la navegación y el contenido
        stats_frame = ctk.CTkFrame(self.stats_window)
        stats_frame.pack(fill="both", expand=True)

        # Configurar para que los marcos se expandan correctamente
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)

        # 2. Marco de Navegación Lateral Interna (Columna 0)
        nav_frame = ctk.CTkFrame(stats_frame, width=220, corner_radius=0)
        nav_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(nav_frame, text="INFORMES", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=20, padx=10)

        # 3. Marco de Contenido Principal para la Estadística (Columna 1)
        self.main_stats_frame = ctk.CTkFrame(stats_frame)
        self.main_stats_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_stats_frame.grid_columnconfigure(0, weight=1) # Permite que el contenido se expanda
        
        # 4. Definición de las estadísticas y sus métodos (Aún no creados)
        # Se elimina la estadística 'Abonos por Cliente y Periodo' (no funcional).
        self.botones_stats = {
            "📊 Estadísticas Anuales": self.mostrar_estadisticas_anuales_menu,
            "📅 Expedientes por Quincena": self.mostrar_expedientes_quincena_menu,
            "Rentabilidad por Cliente": self.mostrar_expedientes_completados,
            "Referencia (Incidencia)": self.mostrar_articulos_incidencia,
            "👤 Incidencias por Persona": self.mostrar_incidencias_personas_menu,
            "⏱️ Tiempos de Tramitación": self.mostrar_estadisticas_tiempos,
            "📦 Artículos - Estadísticas": self.mostrar_estadisticas_articulos_menu,
            "📋 Resolución de Expedientes": self.mostrar_estadisticas_resolucion_menu,
            "⚠️ Recepciones Anticipadas": self.mostrar_recepciones_anticipadas
        }
        
        # 5. Creación de los botones del menú interno
        for text, command in self.botones_stats.items():
            ctk.CTkButton(
                nav_frame, 
                text=text, 
                anchor="w",
                command=lambda cmd=command: self.cargar_estadistica(cmd)
            ).pack(fill="x", padx=10, pady=5)

        # 6. Cargar la primera estadística por defecto
        #self.cargar_estadistica(self.mostrar_expedientes_cliente)
        self.cargar_estadistica(self.mostrar_expedientes_completados)

    def cargar_estadistica(self, func_callback):
        """
        Método central que limpia el marco principal y llama a la función 
        de la estadística seleccionada (callback).
        """
        # Limpiar el marco principal
        for widget in self.main_stats_frame.winfo_children():
            widget.destroy()
        
        # Llamar a la función que dibuja la estadística
        func_callback()

    def validar_fecha_entrada(self, fecha_ddmmyyyy):
        """Función auxiliar para validar el formato de fecha DD/MM/AAAA."""
        if not fecha_ddmmyyyy:
            return None 
        try:
            datetime.strptime(fecha_ddmmyyyy, '%d/%m/%Y')
            return fecha_ddmmyyyy 
        except ValueError:
            messagebox.showerror("Error de Formato de Fecha", 
                                 f"El formato de la fecha '{fecha_ddmmyyyy}' es incorrecto. Debe ser DD/MM/AAAA (ej: 01/01/2024).")
            return False 
        except Exception:
            return None

    def mostrar_expedientes_completados(self):
        """Wrapper que delega la creación de la estadística de rentabilidad
        al módulo externo `lib.client_rentability`.
        """
        try:
            from lib.client_rentability import mostrar_rentabilidad_clientes
            mostrar_rentabilidad_clientes(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la estadística de rentabilidad: {e}")

    def mostrar_incidencias_personas_menu(self):
        """Wrapper que delega la creación de la estadística de incidencias por persona
        al módulo externo `lib.incidencias_personas`.
        Restringido a roles: Dpto. Tecnico, Administracion, admin, Contabilidad
        """
        # Verificar permisos de rol
        roles_permitidos = ["admin", "administrador", "Dpto. Tecnico", "Administracion", "Contabilidad"]
        if self.rol not in roles_permitidos:
            messagebox.showwarning(
                "Acceso Denegado",
                f"No tiene permisos para acceder a esta estadística.\n\nRol actual: {self.rol}\nRoles permitidos: {', '.join(roles_permitidos)}"
            )
            return
        
        try:
            from lib.incidencias_personas import mostrar_incidencias_personas
            mostrar_incidencias_personas(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la estadística de incidencias: {e}")

    def mostrar_articulos_incidencia(self):
        """
        Estadística con filtros avanzados: Muestra el top de artículos según 
        múltiples 'estado_producto', rango de 'fecha_gestion' y búsqueda por 'referencia_articulo'.
        """
        
        # Lista de estados fijos proporcionada por el usuario
        self.ESTADOS_DISPONIBLES = [
            "EN PERFECTO ESTADO ; ABONAR", "FUNCIONA PERFECTAMENTE ; ABONAR", 
            "SOBRANTE DE OBRA ; ABONAR", "NO FUNCIONA, ABONAR", 
            "FUNCIONA PERFECTAMENTE ; NO ABONAR", "NO FUNCIONA ; NO ABONAR", 
            "REPOSICION FALLO PRODUCTO", "REPOSICION ; ABONAR", 
            "MERCANCIA ENVIADA POR ERROR", "MALA MANIPULACION ; NO ABONAR",
            "EN PERFECTO ESTADO ; ABONAR 10% DEPRECIACION", "FALLO SOLDADURA ; ABONAR", 
            "FALLO SOLDADURA ; NO ABONAR", "FALLO MODULO ; ABONAR", 
            "MAL MANIPULACION ; ABONAR", "DANA", "CAMBIO DE PRODUCTO"
        ]
        
        # 1. Preparación de la interfaz
        self.limpiar_marco_stats()
        if not self.main_stats_frame: return
        
        ctk.CTkLabel(self.main_stats_frame, 
                     text="ARTÍCULOS CON MÁS INCIDENCIA", 
                     font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # --- 2. Marco de Controles Principales (Filtros y Búsqueda) ---
        controles_frame = ctk.CTkFrame(self.main_stats_frame)
        controles_frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Configuración de columnas para la primera fila (Fechas)
        controles_frame.grid_columnconfigure((0, 2, 4), weight=0) # Etiquetas y Botón (fijo)
        controles_frame.grid_columnconfigure((1, 3), weight=1)    # Entries de Fecha (expandible)

        # FILTRO 1: Fecha Inicial (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Inicial (DD/MM/AAAA):").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.fecha_inicial_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 01/01/2024")
        self.fecha_inicial_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        # FILTRO 2: Fecha Final (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Final (DD/MM/AAAA):").grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.fecha_final_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 31/12/2024")
        self.fecha_final_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")
        
        # Botón para aplicar filtros - Fila 0
        ctk.CTkButton(
            controles_frame, 
            text="Aplicar Filtros", 
            command=self._cargar_datos_articulos_incidencia
        ).grid(row=0, column=4, padx=(10, 0), pady=5)
        
        # --- NUEVOS WIDGETS DE BÚSQUEDA POR REFERENCIA (Fila 1) ---
        controles_frame.grid_columnconfigure(5, weight=0) # Columna del botón Limpiar

        ctk.CTkLabel(controles_frame, text="Buscar Referencia:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.referencia_entry = ctk.CTkEntry(controles_frame, placeholder_text="Escriba parte de la referencia...")
        self.referencia_entry.grid(row=1, column=1, columnspan=3, padx=(0, 10), pady=5, sticky="ew") # Ocupa 3 columnas
        
        ctk.CTkButton(
            controles_frame, 
            text="Limpiar Búsqueda", 
            command=self._limpiar_filtro_referencia_y_recargar,
            fg_color="gray"
        ).grid(row=1, column=4, padx=(10, 0), pady=5)


        # --- 3. Marco Contenedor de Listado de Estados y Resultados ---
        content_frame = ctk.CTkFrame(self.main_stats_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        # Configuración clave de expansión: la tabla (col 1) se expande
        content_frame.grid_columnconfigure(0, weight=0, minsize=300) 
        content_frame.grid_columnconfigure(1, weight=1)             
        content_frame.grid_rowconfigure(0, weight=1)

        # --- 4. Listado de Estados con Checkboxes (Panel Izquierdo) ---
        estados_panel = ctk.CTkFrame(content_frame)
        estados_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        estados_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(estados_panel, 
                     text="ESTADOS DE INCIDENCIA", 
                     font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))
        
        scroll_frame = ctk.CTkScrollableFrame(estados_panel)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Variables para almacenar el estado de cada checkbox
        self.estado_vars = {} 
        
        # Creación dinámica de las Checkboxes
        for idx, estado in enumerate(self.ESTADOS_DISPONIBLES):
            var = ctk.StringVar(value="0") 
            chk = ctk.CTkCheckBox(
                scroll_frame, 
                text=estado, 
                variable=var,
                onvalue="1", offvalue="0"
            )
            chk.grid(row=idx, column=0, padx=5, pady=2, sticky="w")
            self.estado_vars[estado] = var

        # Checkbox para seleccionar/deseleccionar todos
        all_var = ctk.StringVar(value="0")
        def toggle_all_states():
            new_value = all_var.get()
            for var in self.estado_vars.values():
                var.set(new_value)

        ctk.CTkCheckBox(
            estados_panel, 
            text="SELECCIONAR TODOS", 
            variable=all_var,
            command=toggle_all_states,
            onvalue="1", offvalue="0",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=(5, 10))


        # --- 5. Marco donde se dibujará la tabla de resultados (Panel Derecho) ---
        self.tabla_resultados_frame = ctk.CTkFrame(content_frame)
        self.tabla_resultados_frame.grid(row=0, column=1, sticky="nsew") 

        # 6. Cargar los datos iniciales
        self._cargar_datos_articulos_incidencia()

    def _cargar_datos_articulos_incidencia(self, event=None):
        """
        Consulta la base de datos, aplica filtros de estado (múltiples), fecha,
        y búsqueda LIKE por referencia de artículo.
        """
        from datetime import datetime
        
        # 1. Obtener los valores de los filtros
        
        # 1.1. Obtener los estados seleccionados (Lista de strings)
        estados_seleccionados = [
            estado for estado, var in self.estado_vars.items() if var.get() == "1"
        ]
        
        # 1.2. Obtener filtro de Referencia
        referencia_filtro = self.referencia_entry.get().strip()

        # 1.3. Obtener y validar las fechas (DD/MM/AAAA)
        fecha_inicial_str = self.fecha_inicial_entry.get().strip()
        fecha_final_str = self.fecha_final_entry.get().strip()
        
        # Función que valida DD/MM/AAAA y devuelve el string si es válido
        def validar_fecha_entrada(fecha_ddmmyyyy):
            if not fecha_ddmmyyyy:
                return None 
            try:
                datetime.strptime(fecha_ddmmyyyy, '%d/%m/%Y')
                return fecha_ddmmyyyy 
            except ValueError:
                messagebox.showerror("Error de Formato de Fecha", 
                                     f"El formato de la fecha '{fecha_ddmmyyyy}' es incorrecto. Debe ser DD/MM/AAAA (ej: 01/01/2024).")
                return False 
            except Exception:
                return None
        
        fecha_inicial_db = validar_fecha_entrada(fecha_inicial_str)
        fecha_final_db = validar_fecha_entrada(fecha_final_str)
        
        if fecha_inicial_db is False or fecha_final_db is False:
            return

        # 2. Conexión y Limpieza del Marco
        conn, cursor = self.master.conectar_db()
        if not conn: 
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        for widget in self.tabla_resultados_frame.winfo_children():
            widget.destroy()

        # 3. Construcción dinámica de la consulta SQL y los parámetros
        
        sql_query_base = """
            SELECT 
                T2.codigo_rma, 
                T1.referencia_articulo,
                T1.estado_producto,
                T2.fecha_gestion,
                COUNT(T1.id) AS total_incidencias
            FROM 
                rma_detalles AS T1
            INNER JOIN 
                rma_maestro AS T2 ON T1.rma_id = T2.id
            WHERE 1=1 
        """
        
        condiciones = []
        parametros = []
        
        # 3.1. Filtro por Estado de Producto 
        if estados_seleccionados:
            placeholders = ', '.join('?' for _ in estados_seleccionados)
            condiciones.append(f"T1.estado_producto IN ({placeholders})")
            parametros.extend(estados_seleccionados)
            
        # 3.2. Filtro por Referencia de Artículo
        if referencia_filtro:
            condiciones.append("T1.referencia_articulo LIKE ?")
            parametros.append(f"%{referencia_filtro}%")
            
        # 3.3. Filtro por Rango de Fechas (Convierte la fecha de la DB a YYYY-MM-DD para comparación)
        if fecha_inicial_db:
            # Reorganiza: T2.fecha_gestion (DD/MM/AAAA) -> YYYY-MM-DD
            condiciones.append("SUBSTR(T2.fecha_gestion, 7, 4) || '-' || SUBSTR(T2.fecha_gestion, 4, 2) || '-' || SUBSTR(T2.fecha_gestion, 1, 2) >= ?")
            # El parámetro se convierte a YYYY-MM-DD para la comparación
            parametros.append(datetime.strptime(fecha_inicial_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        if fecha_final_db:
            condiciones.append("SUBSTR(T2.fecha_gestion, 7, 4) || '-' || SUBSTR(T2.fecha_gestion, 4, 2) || '-' || SUBSTR(T2.fecha_gestion, 1, 2) <= ?")
            parametros.append(datetime.strptime(fecha_final_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        # 4. Ensamblaje y Ejecución
        
        if condiciones:
            sql_query_base += " AND " + " AND ".join(condiciones)

        sql_query_final = sql_query_base + """
            GROUP BY 
                T2.codigo_rma, T1.referencia_articulo, T1.estado_producto, T2.fecha_gestion
            ORDER BY 
                total_incidencias DESC
            LIMIT 50; 
        """

        try:
            cursor.execute(sql_query_final, parametros)
            datos_raw = cursor.fetchall()

            # Los datos están en formato DD/MM/AAAA, no se necesita conversión de salida
            datos_formateados = list(datos_raw) 

            # 5. Dibujar la tabla
            self.mostrar_tabla_estadistica(
                datos_formateados, 
                columnas=["CÓDIGO RMA", "REFERENCIA ARTÍCULO", "ESTADO PRODUCTO", "FECHA GESTIÓN", "TOTAL INCIDENCIAS"],
                export_filename="Articulos_Incidencia_Filtrado",
                frame=self.tabla_resultados_frame, 
                formato_moneda=False 
            )

            if not datos_formateados:
                 ctk.CTkLabel(self.tabla_resultados_frame, 
                              text="No se encontraron datos con los filtros aplicados.",
                              font=ctk.CTkFont(size=14)
                 ).pack(pady=40)

        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Error SQL: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado: {e}")
        finally:
            if conn:
                conn.close()

    def _limpiar_filtro_referencia_y_recargar(self):
        """Limpia el campo de búsqueda de referencia y recarga los datos."""
        # Se asegura de que el atributo existe antes de intentar acceder a él
        if hasattr(self, 'referencia_entry'):
            self.referencia_entry.delete(0, 'end')
        # Recarga los datos para aplicar el filtro limpio (que es no filtrar)
        self._cargar_datos_articulos_incidencia()

    def mostrar_estadisticas_tiempos(self):
        """Muestra estadísticas de tiempos de tramitación por cliente."""
        self.limpiar_marco_stats()
        
        ctk.CTkLabel(self.main_stats_frame, 
                     text="⏱️ TIEMPOS DE TRAMITACIÓN POR CLIENTE", 
                     font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Obtener conexión a la base de datos
        conn, cursor = self.master.conectar_db()
        if not conn:
            ctk.CTkLabel(self.main_stats_frame, text="Error al conectar con la base de datos.", 
                        text_color="red").pack(pady=20)
            return
        
        try:
            # Obtener todos los clientes únicos con expedientes cerrados
            cursor.execute("""
                SELECT DISTINCT cliente
                FROM rma_maestro
                WHERE fecha_gestion IS NOT NULL AND fecha_gestion != ''
                AND cliente IS NOT NULL AND cliente != ''
                ORDER BY cliente ASC
            """)
            
            clientes = [fila[0] for fila in cursor.fetchall()]
            
            if not clientes:
                ctk.CTkLabel(self.main_stats_frame, 
                           text="No se encontraron expedientes cerrados para calcular estadísticas.", 
                           text_color="gray").pack(pady=20)
                conn.close()
                return
            
            # Marco scrollable para la tabla
            scroll_frame = ctk.CTkScrollableFrame(self.main_stats_frame)
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Encabezados de la tabla
            header_font = ctk.CTkFont(weight="bold", size=12)
            headers = ["CLIENTE", "EXPEDIENTES", "DÍAS PROMEDIO TOTAL", "E→A", "A→R", "R→P", "P→C"]
            
            for col, header in enumerate(headers):
                lbl = ctk.CTkLabel(scroll_frame, text=header, font=header_font)
                lbl.grid(row=0, column=col, padx=10, pady=10, sticky="w")
            
            # Calcular estadísticas para cada cliente
            for i, cliente in enumerate(clientes):
                promedio_info = obtener_promedio_cliente(cliente, conn)
                
                row = i + 1
                
                # Columna: Cliente
                ctk.CTkLabel(scroll_frame, text=cliente).grid(row=row, column=0, padx=10, pady=5, sticky="w")
                
                # Columna: Número de expedientes
                ctk.CTkLabel(scroll_frame, text=str(promedio_info['total_expedientes'])).grid(
                    row=row, column=1, padx=10, pady=5, sticky="w")
                
                # Columna: Días promedio total
                if promedio_info['promedio_total'] is not None:
                    dias_total = int(promedio_info['promedio_total'])
                    color_total = obtener_color_tiempo(dias_total)
                    ctk.CTkLabel(scroll_frame, text=f"{dias_total} días", text_color=color_total).grid(
                        row=row, column=2, padx=10, pady=5, sticky="w")
                else:
                    ctk.CTkLabel(scroll_frame, text="-", text_color="gray").grid(
                        row=row, column=2, padx=10, pady=5, sticky="w")
                
                # Columnas: Tiempos entre fases (E→A, A→R, R→P, P→C)
                fases = ['promedio_e_a', 'promedio_a_r', 'promedio_r_p', 'promedio_p_c']
                for col_idx, fase in enumerate(fases, start=3):
                    if promedio_info[fase] is not None:
                        dias = int(promedio_info[fase])
                        color = obtener_color_tiempo(dias)
                        ctk.CTkLabel(scroll_frame, text=f"{dias}d", text_color=color).grid(
                            row=row, column=col_idx, padx=10, pady=5, sticky="w")
                    else:
                        ctk.CTkLabel(scroll_frame, text="-", text_color="gray").grid(
                            row=row, column=col_idx, padx=10, pady=5, sticky="w")
            
            # Leyenda de colores
            leyenda_frame = ctk.CTkFrame(self.main_stats_frame)
            leyenda_frame.pack(pady=10)
            
            ctk.CTkLabel(leyenda_frame, text="Leyenda: ", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(leyenda_frame, text="🟢 <10 días", text_color="#22c55e").pack(side="left", padx=5)
            ctk.CTkLabel(leyenda_frame, text="🟡 10-20 días", text_color="#eab308").pack(side="left", padx=5)
            ctk.CTkLabel(leyenda_frame, text="🟠 20-30 días", text_color="#f97316").pack(side="left", padx=5)
            ctk.CTkLabel(leyenda_frame, text="🔴 >30 días", text_color="#ef4444").pack(side="left", padx=5)
            
            conn.close()
            
        except Exception as e:
            print(f"Error al generar estadísticas de tiempos: {e}")
            ctk.CTkLabel(self.main_stats_frame, 
                        text=f"Error al cargar estadísticas: {e}", 
                        text_color="red").pack(pady=20)
            if conn:
                conn.close()

    def mostrar_estadisticas_articulos_menu(self):
        """Wrapper que delega la creación de la estadística de artículos
        al módulo externo `lib.articulos_estadisticas`.
        """
        try:
            from lib.articulos_estadisticas import mostrar_estadisticas_articulos
            mostrar_estadisticas_articulos(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la estadística de artículos: {e}")

    def mostrar_estadisticas_anuales_menu(self):
        """Wrapper que delega la creación de la estadística de resumen anual
        al módulo externo `lib.anuales_estadisticas`.
        """
        try:
            from lib.anuales_estadisticas import mostrar_estadisticas_anuales
            mostrar_estadisticas_anuales(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar las estadísticas anuales: {e}")

    def mostrar_estadisticas_resolucion_menu(self):
        """Wrapper que delega la creación de la estadística de resolución de expedientes
        al módulo externo `lib.resolucion_estadisticas`.
        """
        try:
            from lib.resolucion_estadisticas import mostrar_estadisticas_resolucion
            mostrar_estadisticas_resolucion(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la estadística de resolución: {e}")

    def mostrar_expedientes_quincena_menu(self):
        """Wrapper que delega la creación de la estadística de expedientes por quincena
        al módulo externo `lib.expedientes_quincena`.
        """
        try:
            from lib.expedientes_quincena import mostrar_expedientes_quincena
            mostrar_expedientes_quincena(self.main_stats_frame, self.master.conectar_db, self.username)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la estadística de expedientes por quincena: {e}")
