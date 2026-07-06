"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.

Este mixin construye, en el hueco libre de la columna de estadísticas, el
listado compacto de tareas asignadas al usuario y un calendario mensual con
las tareas marcadas por día.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
import calendar as calendar_std
from lib import tareas_notificaciones
from lib.logger_config import get_logger

logger = get_logger()

DIAS_SEMANA_CORTOS = ["L", "M", "X", "J", "V", "S", "D"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
            "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# Colores explícitos para el punto de prioridad de cada tarea (no depender del
# renderizado de emojis, que en algunos sistemas se muestra en blanco y negro).
PRIORIDAD_COLORES = {
    "Alta": "#e74c3c",
    "Normal": "#f39c12",
    "Baja": "#27ae60",
}


class TareasDashboardMixin:
    def crear_widget_tareas_dashboard(self, parent):
        """Construye, según los ajustes de usuario, el listado de tareas y/o el
        calendario mensual bajo las estadísticas del dashboard."""
        logger.debug("Construyendo widget de tareas/calendario del dashboard")
        try:
            hoy = datetime.date.today()
            self._calendario_mes = hoy.month
            self._calendario_anio = hoy.year
            self._dia_filtro_tareas = None

            mostrar_tareas = self.user_settings.get("mostrar_tareas_dashboard", True)
            mostrar_calendario = self.user_settings.get("mostrar_calendario_dashboard", True)

            if mostrar_calendario:
                self.calendario_dashboard_frame = ctk.CTkFrame(parent, height=178, fg_color=("gray95", "gray17"))
                self.calendario_dashboard_frame.pack(side="bottom", fill="x", padx=5, pady=(2, 5))
                self.calendario_dashboard_frame.pack_propagate(False)
                self._construir_calendario_dashboard()
            else:
                self.calendario_dashboard_frame = None

            if mostrar_tareas:
                self.tareas_dashboard_frame = ctk.CTkFrame(parent, fg_color="transparent")
                self.tareas_dashboard_frame.pack(side="top", fill="both", expand=True, padx=5, pady=(2, 0))

                ctk.CTkLabel(self.tareas_dashboard_frame, text="✅ Mis Tareas",
                             font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(2, 2))

                self.tareas_dashboard_scroll = ctk.CTkScrollableFrame(self.tareas_dashboard_frame, fg_color="transparent")
                self.tareas_dashboard_scroll.pack(fill="both", expand=True)

                self._cargar_tareas_dashboard()
            else:
                self.tareas_dashboard_frame = None

            logger.debug("Widget de tareas/calendario del dashboard construido correctamente")
        except Exception as e:
            logger.error(f"Error al construir widget de tareas/calendario del dashboard: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Listado de tareas
    # ------------------------------------------------------------------
    def _cargar_tareas_dashboard(self):
        """Recarga el listado de tareas del dashboard aplicando los filtros de
        ajustes (todas/prioritarias) y el filtro de día del calendario si hay uno activo."""
        try:
            if not hasattr(self, "tareas_dashboard_scroll") or not self.tareas_dashboard_scroll.winfo_exists():
                return

            for widget in self.tareas_dashboard_scroll.winfo_children():
                widget.destroy()

            mostrar_todas = self.user_settings.get("mostrar_todas_tareas_dashboard", True)
            solo_prioritarias = self.user_settings.get("mostrar_prioritarias_dashboard", False)

            tareas = tareas_notificaciones.obtener_tareas_dashboard(
                self.conectar_db, self.username, mostrar_todas, solo_prioritarias
            )

            if self._dia_filtro_tareas:
                tareas = [t for t in tareas
                          if self._parsear_fecha_tarea(t.get('fecha_vencimiento')) == self._dia_filtro_tareas]

            logger.debug(f"Dashboard: {len(tareas)} tareas mostradas (filtro día={self._dia_filtro_tareas})")

            if not tareas:
                ctk.CTkLabel(self.tareas_dashboard_scroll, text="Sin tareas pendientes",
                             font=ctk.CTkFont(size=9), text_color="gray").pack(pady=10)
                return

            for tarea in tareas:
                self._crear_fila_tarea_dashboard(tarea)
        except Exception as e:
            logger.error(f"Error al cargar tareas del dashboard: {e}", exc_info=True)

    def _crear_fila_tarea_dashboard(self, tarea):
        """Crea una fila compacta (2 líneas) para una tarea, con botones de acción solo-icono."""
        fila = ctk.CTkFrame(self.tareas_dashboard_scroll, fg_color=("white", "gray25"), corner_radius=6)
        fila.pack(fill="x", pady=2, padx=1)

        prioridad = tarea.get('prioridad') or 'Normal'
        color_prioridad = PRIORIDAD_COLORES.get(prioridad, PRIORIDAD_COLORES['Normal'])

        titulo_texto = tarea['titulo']
        if len(titulo_texto) > 26:
            titulo_texto = titulo_texto[:26] + "…"

        codigo_rma = tarea.get('codigo_rma')
        texto_tooltip_expediente = f"Expediente: {codigo_rma}" if codigo_rma else "Sin expediente asociado"

        linea1 = ctk.CTkFrame(fila, fg_color="transparent")
        linea1.pack(fill="x", padx=4, pady=(3, 0))

        lbl_punto = ctk.CTkLabel(linea1, text="●", font=ctk.CTkFont(size=12, weight="bold"),
                                  text_color=color_prioridad, width=12)
        lbl_punto.pack(side="left")

        lbl_titulo = ctk.CTkLabel(linea1, text=titulo_texto, font=ctk.CTkFont(size=9, weight="bold"), anchor="w")
        lbl_titulo.pack(side="left", fill="x", expand=True)

        linea2 = ctk.CTkFrame(fila, fg_color="transparent")
        linea2.pack(fill="x", padx=4, pady=(0, 3))

        fecha_v = tarea.get('fecha_vencimiento')
        fecha_texto = ""
        if fecha_v:
            try:
                fecha_texto = datetime.datetime.strptime(fecha_v, "%Y-%m-%d").strftime("%d/%m")
            except ValueError:
                fecha_texto = fecha_v
        lbl_fecha = ctk.CTkLabel(linea2, text=fecha_texto, font=ctk.CTkFont(size=8), text_color="gray")
        lbl_fecha.pack(side="left")

        # Tooltip con el expediente asociado en cualquier punto de la fila que no sea un botón
        for widget_fila in (fila, linea1, lbl_punto, lbl_titulo, linea2, lbl_fecha):
            Tooltip(widget_fila, texto_tooltip_expediente)

        botones = ctk.CTkFrame(linea2, fg_color="transparent")
        botones.pack(side="right")

        btn_completar = ctk.CTkButton(botones, text="✓", width=20, height=18, font=ctk.CTkFont(size=10),
                                      fg_color=("#27ae60", "#2ecc71"), hover_color=("#229954", "#27ae60"),
                                      command=lambda t=tarea: self._completar_tarea_dashboard(t))
        btn_completar.pack(side="left", padx=1)
        Tooltip(btn_completar, "Completar tarea")

        btn_editar = ctk.CTkButton(botones, text="✏", width=20, height=18, font=ctk.CTkFont(size=10),
                                   command=lambda t=tarea: self._abrir_dialogo_editar_tarea_dashboard(t))
        btn_editar.pack(side="left", padx=1)
        Tooltip(btn_editar, "Editar tarea")

        btn_eliminar = ctk.CTkButton(botones, text="🗑", width=20, height=18, font=ctk.CTkFont(size=10),
                                     fg_color=("#c0392b", "#e74c3c"), hover_color=("#a93226", "#c0392b"),
                                     command=lambda t=tarea: self._eliminar_tarea_dashboard(t))
        btn_eliminar.pack(side="left", padx=1)
        Tooltip(btn_eliminar, "Eliminar tarea")

        if tarea.get('codigo_rma'):
            btn_abrir = ctk.CTkButton(botones, text="📂", width=20, height=18, font=ctk.CTkFont(size=10),
                                      command=lambda c=tarea['codigo_rma']: self._abrir_expediente_dashboard(c))
            btn_abrir.pack(side="left", padx=1)
            Tooltip(btn_abrir, f"Abrir expediente {tarea['codigo_rma']}")

    def _refrescar_tareas_dashboard(self):
        """Recarga listado y calendario, y el badge de tareas si existe."""
        self._cargar_tareas_dashboard()
        self._construir_calendario_dashboard()
        if hasattr(self, 'badge_tareas'):
            try:
                self.badge_tareas.actualizar_contador()
            except Exception:
                pass

    def _completar_tarea_dashboard(self, tarea):
        if not messagebox.askyesno("Completar tarea",
                                    f"¿Marcar como completada la tarea:\n\n'{tarea['titulo']}'?"):
            return
        try:
            exito = tareas_notificaciones.completar_tarea_con_historial(self.conectar_db, tarea['id'], self.username)
            if exito:
                self._refrescar_tareas_dashboard()
            else:
                messagebox.showerror("Error", "No se pudo completar la tarea")
        except Exception as e:
            logger.error(f"Error al completar tarea {tarea.get('id')} desde dashboard: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al completar la tarea:\n{e}")

    def _eliminar_tarea_dashboard(self, tarea):
        if not messagebox.askyesno("Eliminar tarea",
                                    f"¿Eliminar la tarea:\n\n'{tarea['titulo']}'?\n\nEsta acción no se puede deshacer."):
            return
        try:
            exito = tareas_notificaciones.eliminar_tarea_con_historial(self.conectar_db, tarea['id'], self.username)
            if exito:
                self._refrescar_tareas_dashboard()
            else:
                messagebox.showerror("Error", "No se pudo eliminar la tarea")
        except Exception as e:
            logger.error(f"Error al eliminar tarea {tarea.get('id')} desde dashboard: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al eliminar la tarea:\n{e}")

    def _abrir_expediente_dashboard(self, codigo_rma):
        logger.debug(f"Dashboard: abriendo expediente {codigo_rma}")
        try:
            self.abrir_expediente_desde_panel(codigo_rma)
        except Exception as e:
            logger.error(f"Error al abrir expediente {codigo_rma} desde dashboard: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir el expediente:\n{e}")

    def _abrir_dialogo_editar_tarea_dashboard(self, tarea):
        """Diálogo compacto de edición de tarea, reutilizado desde el widget del dashboard."""
        logger.debug(f"Abriendo diálogo de edición de tarea {tarea['id']} desde dashboard")
        dlg = ctk.CTkToplevel(self)
        dlg.title("Editar tarea")
        dlg.geometry("420x580")
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"ID: {tarea['id']} - RMA: {tarea.get('codigo_rma') or 'N/A'}").pack(pady=5)

        ctk.CTkLabel(dlg, text="Título:").pack(pady=(10, 0))
        titulo_entry = ctk.CTkEntry(dlg)
        titulo_entry.insert(0, tarea['titulo'])
        titulo_entry.pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10, 0))
        desc_text = tk.Text(dlg, height=5)
        desc_text.insert('1.0', tarea.get('descripcion') or '')
        desc_text.pack(padx=10, pady=5, fill='both', expand=True)

        ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5, 0))
        fecha_entry = ctk.CTkEntry(dlg)
        fecha_entry.insert(0, tarea.get('fecha_vencimiento') or '')
        fecha_entry.pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Estado:").pack(pady=(5, 0))
        estado_var = ctk.StringVar(value=tarea.get('estado', 'Pendiente'))
        ctk.CTkOptionMenu(dlg, values=["Pendiente", "En Progreso", "Completado"],
                          variable=estado_var).pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Prioridad:").pack(pady=(5, 0))
        prioridad_var = ctk.StringVar(value=tarea.get('prioridad', 'Normal'))
        ctk.CTkOptionMenu(dlg, values=["Alta", "Normal", "Baja"],
                          variable=prioridad_var).pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Asignar a:").pack(pady=(5, 0))
        usuarios_disponibles = ["No asignado"]
        try:
            conn_temp, cur_temp = self.conectar_db()
            cur_temp.execute("SELECT nombre_usuario FROM usuarios ORDER BY nombre_usuario")
            usuarios_disponibles.extend([row[0] for row in cur_temp.fetchall()])
            conn_temp.close()
        except Exception as e:
            logger.error(f"Error al obtener usuarios para diálogo de edición de tarea: {e}", exc_info=True)

        asignado_actual = tarea.get('asignado_a') or "No asignado"
        asignado_var = ctk.StringVar(value=asignado_actual)
        ctk.CTkOptionMenu(dlg, values=usuarios_disponibles, variable=asignado_var).pack(padx=10, pady=5, fill='x')

        def guardar_edicion():
            nuevo_titulo = titulo_entry.get().strip()
            if not nuevo_titulo:
                messagebox.showerror("Error", "El título es obligatorio.", parent=dlg)
                return
            nueva_desc = desc_text.get('1.0', 'end').strip()
            nueva_fecha = fecha_entry.get().strip() or None
            nuevo_asignado = asignado_var.get()
            if nuevo_asignado == "No asignado":
                nuevo_asignado = None
            try:
                exito = tareas_notificaciones.editar_tarea_con_historial(
                    self.conectar_db, tarea['id'], self.username,
                    nuevo_titulo, nueva_desc, nueva_fecha, estado_var.get(), nuevo_asignado, prioridad_var.get()
                )
                if exito:
                    dlg.destroy()
                    self._refrescar_tareas_dashboard()
                    messagebox.showinfo("Éxito", "Tarea actualizada correctamente")
                else:
                    messagebox.showerror("Error", "No se pudo actualizar la tarea", parent=dlg)
            except Exception as e:
                logger.error(f"Error al editar tarea {tarea.get('id')} desde dashboard: {e}", exc_info=True)
                messagebox.showerror("Error", f"No se pudo actualizar la tarea:\n{e}", parent=dlg)

        ctk.CTkButton(dlg, text="Guardar", command=guardar_edicion).pack(pady=10)

    def _abrir_dialogo_crear_tarea_dashboard(self):
        """Diálogo para crear una tarea nueva desde el calendario del dashboard,
        con opción de asociarla a un expediente existente."""
        logger.debug("Abriendo diálogo de creación de tarea desde el calendario del dashboard")
        fecha_inicial = self._dia_filtro_tareas or datetime.date.today()

        dlg = ctk.CTkToplevel(self)
        dlg.title("Crear tarea")
        dlg.geometry("460x700")
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Título:").pack(pady=(10, 0))
        titulo_entry = ctk.CTkEntry(dlg)
        titulo_entry.pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10, 0))
        desc_text = tk.Text(dlg, height=4)
        desc_text.pack(padx=10, pady=5, fill='both', expand=True)

        ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5, 0))
        fecha_entry = ctk.CTkEntry(dlg)
        fecha_entry.insert(0, fecha_inicial.isoformat())
        fecha_entry.pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Prioridad:").pack(pady=(5, 0))
        prioridad_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(dlg, values=["Alta", "Normal", "Baja"],
                          variable=prioridad_var).pack(padx=10, pady=5, fill='x')

        ctk.CTkLabel(dlg, text="Asignar a:").pack(pady=(5, 0))
        usuarios_disponibles = ["No asignado"]
        try:
            conn_temp, cur_temp = self.conectar_db()
            cur_temp.execute("SELECT nombre_usuario FROM usuarios ORDER BY nombre_usuario")
            usuarios_disponibles.extend([row[0] for row in cur_temp.fetchall()])
            conn_temp.close()
        except Exception as e:
            logger.error(f"Error al obtener usuarios para diálogo de creación de tarea: {e}", exc_info=True)

        asignado_var = ctk.StringVar(value="No asignado")
        ctk.CTkOptionMenu(dlg, values=usuarios_disponibles, variable=asignado_var).pack(padx=10, pady=5, fill='x')

        # Selector de expediente (opcional): buscar por código RMA o cliente
        ctk.CTkLabel(dlg, text="Expediente asociado (opcional):").pack(pady=(5, 0))
        expediente_seleccionado = {"codigo_rma": None, "texto": None}

        lbl_expediente_actual = ctk.CTkLabel(dlg, text="Sin expediente asociado", text_color="gray",
                                              font=ctk.CTkFont(size=10))
        lbl_expediente_actual.pack(padx=10, pady=(0, 2), fill='x')

        expediente_entry = ctk.CTkEntry(dlg, placeholder_text="Escriba código RMA o cliente para buscar...")
        expediente_entry.pack(padx=10, pady=(0, 2), fill='x')

        expediente_resultados = ctk.CTkScrollableFrame(dlg, height=90)
        expediente_resultados.pack(padx=10, pady=(0, 5), fill='x')

        def buscar_expedientes(_event=None):
            termino = expediente_entry.get().strip()
            for widget in expediente_resultados.winfo_children():
                widget.destroy()
            if len(termino) < 2:
                return
            try:
                conn_temp, cur_temp = self.conectar_db()
                cur_temp.execute(
                    "SELECT codigo_rma, cliente FROM rma_maestro "
                    "WHERE codigo_rma LIKE ? OR cliente LIKE ? "
                    "ORDER BY fecha_emision DESC LIMIT 20",
                    (f"%{termino}%", f"%{termino}%")
                )
                resultados = cur_temp.fetchall()
                conn_temp.close()
            except Exception as e:
                logger.error(f"Error buscando expedientes para nueva tarea: {e}", exc_info=True)
                return

            if not resultados:
                ctk.CTkLabel(expediente_resultados, text="Sin resultados", text_color="gray",
                             font=ctk.CTkFont(size=9)).pack(pady=5)
                return

            for codigo_rma, cliente in resultados:
                def seleccionar(codigo=codigo_rma, cli=cliente):
                    expediente_seleccionado["codigo_rma"] = codigo
                    expediente_seleccionado["texto"] = f"{codigo} - {cli}"
                    lbl_expediente_actual.configure(text=f"Expediente: {codigo} - {cli}", text_color=("black", "white"))
                    expediente_entry.delete(0, "end")
                    for w in expediente_resultados.winfo_children():
                        w.destroy()

                fila = ctk.CTkButton(expediente_resultados, text=f"{codigo_rma} - {cliente}",
                                      font=ctk.CTkFont(size=9), anchor="w",
                                      fg_color="transparent", text_color=("black", "white"),
                                      hover_color=("gray80", "gray30"), command=seleccionar)
                fila.pack(fill="x", pady=1)

        expediente_entry.bind("<KeyRelease>", buscar_expedientes)

        def quitar_expediente():
            expediente_seleccionado["codigo_rma"] = None
            expediente_seleccionado["texto"] = None
            lbl_expediente_actual.configure(text="Sin expediente asociado", text_color="gray")

        ctk.CTkButton(dlg, text="Quitar expediente asociado", height=20, font=ctk.CTkFont(size=9),
                      fg_color="transparent", text_color="gray", hover_color=("gray80", "gray30"),
                      command=quitar_expediente).pack(padx=10, pady=(0, 5), fill='x')

        def confirmar_crear():
            titulo = titulo_entry.get().strip()
            if not titulo:
                messagebox.showerror("Error", "El título es obligatorio.", parent=dlg)
                return
            descripcion = desc_text.get("1.0", "end").strip()
            fecha_v = fecha_entry.get().strip() or None
            if fecha_v:
                try:
                    datetime.datetime.strptime(fecha_v, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD", parent=dlg)
                    return
            asignado_a = asignado_var.get()
            if asignado_a == "No asignado":
                asignado_a = None
            codigo_rma = expediente_seleccionado["codigo_rma"]

            try:
                conn, cur = self.conectar_db()
                cur.execute(
                    "INSERT INTO tareas (codigo_rma, titulo, descripcion, fecha_vencimiento, estado, "
                    "creado_por, creado_en, asignado_a, prioridad, notificado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                    (codigo_rma, titulo, descripcion, fecha_v, 'Pendiente', self.username,
                     datetime.datetime.now().isoformat(), asignado_a, prioridad_var.get())
                )
                if codigo_rma:
                    cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
                    rma_row = cur.fetchone()
                    if rma_row:
                        cur.execute("""
                            INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                            VALUES (?, ?, ?, ?)
                        """, (rma_row[0], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             self.username, f"Nueva tarea creada desde el calendario: {titulo}"))
                conn.commit()
                conn.close()
                dlg.destroy()
                self._refrescar_tareas_dashboard()
                messagebox.showinfo("Éxito", "✅ Tarea creada correctamente")
            except Exception as e:
                logger.error(f"Error al crear tarea desde el calendario del dashboard: {e}", exc_info=True)
                messagebox.showerror("Error", f"No se pudo crear la tarea:\n{e}", parent=dlg)

        ctk.CTkButton(dlg, text="Crear", command=confirmar_crear).pack(pady=10)

    # ------------------------------------------------------------------
    # Calendario mensual
    # ------------------------------------------------------------------
    @staticmethod
    def _parsear_fecha_tarea(fecha_vencimiento):
        """Convierte fecha_vencimiento (texto libre, p.ej. 'YYYY-MM-DD' o con hora
        u otros separadores) en un datetime.date, o None si no se puede interpretar.
        Se usa para comparar con el día seleccionado en el calendario sin depender
        de que el formato guardado sea exactamente igual byte a byte."""
        if not fecha_vencimiento:
            return None
        try:
            solo_fecha = fecha_vencimiento.strip().split(" ")[0].split("T")[0]
            partes = solo_fecha.replace("/", "-").split("-")
            if len(partes) != 3:
                return None
            anio, mes, dia = (int(p) for p in partes)
            return datetime.date(anio, mes, dia)
        except (ValueError, TypeError):
            return None

    def _construir_calendario_dashboard(self):
        """Reconstruye el mini-calendario mensual marcando los días con tareas pendientes."""
        try:
            if not hasattr(self, "calendario_dashboard_frame") or self.calendario_dashboard_frame is None:
                return
            if not self.calendario_dashboard_frame.winfo_exists():
                return

            for widget in self.calendario_dashboard_frame.winfo_children():
                widget.destroy()

            mostrar_todas = self.user_settings.get("mostrar_todas_tareas_dashboard", True)
            solo_prioritarias = self.user_settings.get("mostrar_prioritarias_dashboard", False)

            conteo_dias = tareas_notificaciones.obtener_conteo_tareas_por_dia(
                self.conectar_db, self.username, self._calendario_anio, self._calendario_mes,
                mostrar_todas, solo_prioritarias
            )

            header = ctk.CTkFrame(self.calendario_dashboard_frame, fg_color="transparent")
            header.pack(fill="x", pady=(2, 2))

            btn_nueva_tarea = ctk.CTkButton(header, text="+", width=22, height=18, font=ctk.CTkFont(size=10, weight="bold"),
                                             fg_color=("#27ae60", "#2ecc71"), hover_color=("#229954", "#27ae60"),
                                             command=lambda: self._abrir_dialogo_crear_tarea_dashboard())
            btn_nueva_tarea.pack(side="left", padx=2)
            Tooltip(btn_nueva_tarea, "Crear tarea nueva")

            ctk.CTkButton(header, text="◀", width=22, height=18, font=ctk.CTkFont(size=10),
                          command=lambda: self._cambiar_mes_calendario(-1)).pack(side="left", padx=2)

            mes_texto = f"{MESES_ES[self._calendario_mes - 1][:3]} {self._calendario_anio}"
            ctk.CTkLabel(header, text=mes_texto, font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", expand=True)

            ctk.CTkButton(header, text="▶", width=22, height=18, font=ctk.CTkFont(size=10),
                          command=lambda: self._cambiar_mes_calendario(1)).pack(side="right", padx=2)

            dias_frame = ctk.CTkFrame(self.calendario_dashboard_frame, fg_color="transparent")
            dias_frame.pack(fill="both", expand=True, padx=2)
            for col in range(7):
                dias_frame.grid_columnconfigure(col, weight=1, uniform="dia")

            for col, letra in enumerate(DIAS_SEMANA_CORTOS):
                ctk.CTkLabel(dias_frame, text=letra, font=ctk.CTkFont(size=8),
                             text_color="gray").grid(row=0, column=col, sticky="nsew")

            cal = calendar_std.Calendar(firstweekday=0)
            semanas = cal.monthdayscalendar(self._calendario_anio, self._calendario_mes)
            hoy = datetime.date.today()

            for fila_idx, semana in enumerate(semanas, start=1):
                for col, dia in enumerate(semana):
                    if dia == 0:
                        ctk.CTkLabel(dias_frame, text="").grid(row=fila_idx, column=col, sticky="nsew")
                        continue

                    info = conteo_dias.get(dia)
                    es_hoy = (dia == hoy.day and self._calendario_mes == hoy.month
                              and self._calendario_anio == hoy.year)
                    es_filtro = (self._dia_filtro_tareas is not None
                                 and self._dia_filtro_tareas == datetime.date(self._calendario_anio, self._calendario_mes, dia))

                    if es_filtro:
                        color_fondo = ("#3498db", "#2980b9")
                        color_texto = "white"
                    elif info and info.get("tiene_alta"):
                        color_fondo = ("#f5b7b1", "#7b241c")
                        color_texto = ("black", "white")
                    elif info:
                        color_fondo = ("#fdebd0", "#7d6608")
                        color_texto = ("black", "white")
                    elif es_hoy:
                        color_fondo = ("#d5f5e3", "#1e8449")
                        color_texto = ("black", "white")
                    else:
                        color_fondo = "transparent"
                        color_texto = ("black", "white")

                    btn_dia = ctk.CTkButton(dias_frame, text=str(dia), width=22, height=18,
                                            font=ctk.CTkFont(size=8), fg_color=color_fondo, text_color=color_texto,
                                            hover_color=("#aed6f1", "#1f618d"),
                                            command=lambda d=dia: self._on_click_dia_calendario(d))
                    btn_dia.grid(row=fila_idx, column=col, sticky="nsew", padx=1, pady=1)
        except Exception as e:
            logger.error(f"Error al construir calendario del dashboard: {e}", exc_info=True)

    def _cambiar_mes_calendario(self, delta):
        mes = self._calendario_mes + delta
        anio = self._calendario_anio
        if mes < 1:
            mes = 12
            anio -= 1
        elif mes > 12:
            mes = 1
            anio += 1
        self._calendario_mes = mes
        self._calendario_anio = anio

        if self._dia_filtro_tareas and (self._dia_filtro_tareas.month != mes or self._dia_filtro_tareas.year != anio):
            self._dia_filtro_tareas = None

        logger.debug(f"Calendario dashboard: navegando a {mes}/{anio}")
        self._construir_calendario_dashboard()
        self._cargar_tareas_dashboard()

    def _on_click_dia_calendario(self, dia):
        nueva_fecha = datetime.date(self._calendario_anio, self._calendario_mes, dia)
        if self._dia_filtro_tareas == nueva_fecha:
            self._dia_filtro_tareas = None
            logger.info(f"Usuario {self.username} quitó el filtro de día del calendario del dashboard")
        else:
            self._dia_filtro_tareas = nueva_fecha
            logger.info(f"Usuario {self.username} filtró tareas del dashboard por día {nueva_fecha.isoformat()}")
        self._construir_calendario_dashboard()
        self._cargar_tareas_dashboard()
