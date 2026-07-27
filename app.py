from lib.app_core import *  # noqa: F401,F403 - helpers/constantes compartidos
import lib.app_core as app_core
from lib.ui_mixins.busqueda_mixin import BusquedaMixin
from lib.ui_mixins.dashboard_mixin import DashboardMixin
from lib.ui_mixins.tareas_dashboard_mixin import TareasDashboardMixin
from lib.ui_mixins.rma_listado_mixin import RmaListadoMixin
from lib.ui_mixins.rma_editor_mixin import RmaEditorMixin
from lib.ui_mixins.backups_mixin import BackupsMixin
from lib.ui_mixins.adjuntos_mixin import AdjuntosMixin
from lib.ui_mixins.informes_mixin import InformesMixin
from lib.ui_mixins.admin_mixin import AdminMixin
from lib.ui_mixins.articulos_mixin import ArticulosMixin
from lib.ui_mixins.recepciones_mixin import RecepcionesMixin
from lib.ui_mixins.email_mixin import EmailMixin
from lib.ui_mixins.clientes_mixin import ClientesMixin

#try:
#    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
#except locale.Error:
#    try:
#        locale.setlocale(locale.LC_ALL, 'es_ES')
#    except locale.Error:
#        print("Advertencia: No se pudo configurar el locale para moneda.")

# ----------------------------------------------------------------------
# 1. CLASE DE LA VENTANA DE LOGIN
# ----------------------------------------------------------------------

class LoginApp(ctk.CTk):
    """Clase principal de la aplicación, encargada del login."""
    def __init__(self):
        super().__init__()
        
        # Configuraciones básicas de la ventana
        self.title("Gestión RMA - Login")
        
        # Centrar la ventana en la pantalla
        window_width = 400
        window_height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        
        self.resizable(False, False)
        
        # Agregar icono personalizado de ILUTREK
        try:
            self.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            pass  # Si no se puede cargar el icono, continuar sin él
        
        ctk.set_appearance_mode("light") 
        ctk.set_default_color_theme("themes/BH_rime.json")

        self.crear_widgets_login()

    def crear_widgets_login(self):
        """Diseña y coloca los elementos de la ventana de login."""
        
        login_frame = ctk.CTkFrame(self, 
                                   width=400, 
                                   height=300, 
                                   corner_radius=10,
                                   #fg_color=("gray95", "gray10")
                                   )
        login_frame.pack(pady=20, padx=40, fill="both", expand=True)

        ctk.CTkLabel(login_frame, text="Iniciar Sesión", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))

        self.username_entry = ctk.CTkEntry(login_frame, placeholder_text="Nombre de Usuario")
        self.username_entry.pack(pady=12, padx=10)
        # Permitir login con ENTER desde el campo de usuario
        self.username_entry.bind("<Return>", lambda event: self.verificar_login())

        self.password_entry = ctk.CTkEntry(login_frame, placeholder_text="Contraseña", show="*")
        self.password_entry.pack(pady=12, padx=10)
        # Permitir login con ENTER desde el campo de contraseña
        self.password_entry.bind("<Return>", lambda event: self.verificar_login())

        login_button = ctk.CTkButton(login_frame, 
                                  text="Iniciar Sesión", 
                                  command=self.verificar_login,
                                  # AJUSTE CLAVE: Color de fondo y hover a tonos de gris
                                  #fg_color="gray50",     # Fondo del botón: Gris medio
                                  #hover_color="gray40",   # Color al pasar el ratón: Gris oscuro
                                  #text_color="white"
                                  )     # Color del texto (blanco para contraste)
        login_button.pack(pady=12, padx=10)
        
        self.error_label = ctk.CTkLabel(login_frame, text="", text_color="red")
        self.error_label.pack(pady=5)

    def conectar_db(self):
        """Intenta conectar a la base de datos."""
        try:
            # Añadimos un timeout de 5 segundos. Si hay variables de entorno de Turso,
            # se conectará a Turso; en caso contrario, a SQLite local.
            conn = connect_db(timeout=5)
            cursor = conn.cursor()
            return conn, cursor
        except sqlite3.Error as e:
            self.error_label.configure(text=f"Error de DB: {e}", text_color="red")
            print(f"Error de base de datos: {e}")
            return None, None

    def cargar_tema_usuario(self, username):
        """Carga y aplica el tema personalizado del usuario antes de crear la ventana principal."""
        try:
            user_settings = load_user_settings(username)
            
            # Aplicar tema personalizado si está configurado
            tema_usuario = user_settings.get("theme", "themes/BH_rime.json")
            
            # Validar que el tema existe y es válido
            if tema_usuario and tema_usuario != "System":
                if os.path.exists(tema_usuario):
                    try:
                        ctk.set_default_color_theme(tema_usuario)
                    except Exception as e:
                        # Si falla, usar tema por defecto
                        ctk.set_default_color_theme("themes/BH_rime.json")
                else:
                    ctk.set_default_color_theme("themes/BH_rime.json")
            else:
                ctk.set_default_color_theme("themes/BH_rime.json")
            
            # Aplicar modo de apariencia personalizado
            modo_usuario = user_settings.get("appearance_mode", "light")
            # BH_rime siempre debe usar modo claro
            if tema_usuario == "themes/BH_rime.json":
                modo_usuario = "light"
            try:
                ctk.set_appearance_mode(modo_usuario)
            except Exception as e:
                ctk.set_appearance_mode("light")
                
        except Exception as e:
            # Aplicar valores por defecto
            ctk.set_default_color_theme("themes/BH_rime.json")
            ctk.set_appearance_mode("light")

    def verificar_login(self):
        """Comprueba las credenciales del usuario."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.configure(text="Rellena todos los campos.")
            return

        conn, cursor = self.conectar_db()
    
        # Manejar el caso de que la conexión haya fallado
        if conn is None:
            messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos.")
            return
        # -----------------------
        if not conn:
            return

        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash, rol FROM usuarios WHERE nombre_usuario = ?", (username,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            password_hash, rol = resultado
            try:
                if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                    self.error_label.configure(text=f"✅ Acceso concedido", text_color="green")
                    self.abrir_ventana_principal(username, rol)
                else:
                    self.error_label.configure(text="Usuario o contraseña incorrectos.")
            except Exception as e:
                 self.error_label.configure(text="Error de seguridad en credenciales.")
                 print(f"Error bcrypt: {e}")
        else:
            self.error_label.configure(text="Usuario o contraseña incorrectos.")

    def abrir_ventana_principal(self, username, rol):
        """Abre la ventana principal de la aplicación."""
        
        # IMPORTANTE: Cargar y aplicar tema del usuario ANTES de crear la ventana principal
        self.cargar_tema_usuario(username)
        
        self.withdraw() # Ocultamos la ventana de login
        # Mostrar un splash/transición entre login y la ventana principal
        try:
            splash = tk.Toplevel(self)
            splash.overrideredirect(True)
            splash.configure(bg="white")
            sw = splash.winfo_screenwidth()
            sh = splash.winfo_screenheight()
            w, h = 380, 120
            x = (sw - w) // 2
            y = (sh - h) // 2
            splash.geometry(f"{w}x{h}+{x}+{y}")

            frame = tk.Frame(splash, bg="white")
            frame.pack(fill="both", expand=True)
            tk.Label(frame, text="Cargando Gestor RMA...", font=("Segoe UI", 11, "bold"), bg="white").pack(pady=(16, 6))
            status_label = tk.Label(frame, text="Preparando la interfaz...", font=("Segoe UI", 9), bg="white")
            status_label.pack(pady=(0, 8))
            try:
                progress = ttk.Progressbar(frame, mode="indeterminate", length=320)
                progress.pack(pady=(0, 6))
                progress.start(10)
            except Exception:
                progress = None

            # Forzar dibujado del splash antes de crear la ventana principal
            try:
                splash.update()
            except Exception:
                pass
        except Exception:
            splash = None
            status_label = None
            progress = None

        try:
            if not hasattr(self, 'ventana_principal') or not self.ventana_principal.winfo_exists():
                # Instanciar la ventana principal (esto puede tardar si carga muchos datos)
                # Actualizar label de estado antes de la carga (si es posible)
                try:
                    if status_label:
                        status_label.config(text="Cargando datos y recursos...")
                        splash.update()
                except Exception:
                    pass

                self.ventana_principal = VentanaPrincipal(self, username, rol)

        finally:
            # Cerrar el splash y detener la barra si existen
            try:
                if progress:
                    progress.stop()
            except Exception:
                pass
            try:
                if splash:
                    splash.destroy()
            except Exception:
                pass

        print(ADVERTENCIA_MULTIUSUARIO)

# ----------------------------------------------------------------------
# 2. CLASE DE LA VENTANA PRINCIPAL DE LA APLICACIÓN
# ----------------------------------------------------------------------

class VentanaPrincipal(ctk.CTkToplevel, BusquedaMixin, DashboardMixin, TareasDashboardMixin, RmaListadoMixin, RmaEditorMixin, BackupsMixin, AdjuntosMixin, InformesMixin, AdminMixin, ArticulosMixin, RecepcionesMixin, EmailMixin, ClientesMixin):
    """Ventana principal que gestiona el listado, creación y edición de RMAs."""
    
    # Opciones predefinidas para desplegables
    # Inicializar el gestor de estados
    estados_manager = EstadosArticuloManager()
    # Inicializar el gestor de personas
    personas_manager = PersonasManager()
    # Inicializar el gestor de personas de recepción
    personas_recepcion_manager = PersonasRecepcionManager()
    
    # Inicializar el gestor de resultado expediente
    resultado_expediente_manager = ResultadoExpedienteManager()
    
    OPCIONES = {
        "Autorizacion": ["SI", "NO"],
        "Autorizado_Por": personas_manager.cargar_personas(),  # Cargar desde JSON
        "Gestionado_Por": personas_manager.cargar_personas(),  # Cargar desde JSON
        "Recepcionado_Por": personas_recepcion_manager.cargar_personas(),  # Cargar desde JSON
        "Resultado_Expediente": resultado_expediente_manager.cargar_resultados(),  # Cargar desde JSON
        "Resolucion_Provisional": ["", "REPOSICION", "ABONAR", "NO ABONAR"],
        "Estado_Producto": estados_manager.cargar_estados(),  # Cargar desde JSON
        "Tipo_Cliente": cargar_tipos_cliente()  # Cargar desde JSON
    }
    
    def get_color_por_estado(self, estado):
        """Obtiene el color del dashboard para un estado específico, manteniendo coherencia visual"""
        # Mapeo de colores del dashboard para coherencia visual
        colores_dashboard = {
            'Completado': "#27ae60",
            'Pendiente de Autorización': "#e74c3c", 
            'Pendiente de Autorizacion': "#e74c3c",  # Variación sin tilde
            'Recibido': "#3498db",
            'En Trámite': "#f39c12",
            'En Tramite': "#f39c12",  # Variación sin tilde
            'En Proceso': "#f39c12",  # Variación alternativa
            'Procesando': "#f39c12",  # Variación alternativa
            'Autorizado': "#9b59b6"
        }
        return colores_dashboard.get(estado, "#7f8c8d")  # Color gris por defecto

    def __init__(self, master, username, rol):
        super().__init__(master)
        self.master = master
        self.username = username
        self.rol = rol
        
        # Configurar usuario en el sistema de logging
        set_current_user(username)
        logger.info(f"Usuario '{username}' con rol '{rol}' ha iniciado sesión")
        
        # Configuración para compatibilidad de esquema de BD
        self._usar_tipo_almacenamiento = True  # Por defecto asumimos que funciona

        # Inicializar referencias de iconos por defecto para evitar AttributeError
        # Icon placeholders (se asignarán en crear_diseno)
        self.icon_list = None
        self.icon_articles = None
        self.icon_stats = None
        self.icon_tasks = None
        self.icon_reports = None
        self.icon_info = None
        self.icon_edit = None
        self.icon_user = None
        self.icon_papel = None
        self.icon_mas = None
        self.icon_ventas_compras = None
        
        # Variables de paginación para lista principal
        self.pagina_actual_lista = 0
        self.elementos_por_pagina_lista = 25
        
        # Cargar ajustes de usuario (ya aplicados en LoginApp, solo necesitamos cargarlos aquí)
        try:
            self.user_settings = load_user_settings(self.username)
            
            # Verificar estado de firma en B2 si está habilitado
            if usar_b2():
                tiene_firma_guardada = self.user_settings.get("tiene_firma", False)
                firma_existe = verificar_firma_usuario_existe(self.username, get_b2_client)
                
                # Si hay desincronización, corregir
                if tiene_firma_guardada != firma_existe:
                    self.user_settings["tiene_firma"] = firma_existe
                    save_user_settings(self.user_settings, self.username)
                    if firma_existe:
                        logger.info(f"Firma detectada en B2 para usuario {self.username}")
                    else:
                        logger.info(f"No se detectó firma en B2 para usuario {self.username}")
        except Exception as e:
            logger.error(f"Error al cargar ajustes de usuario: {e}")
            self.user_settings = {}
            
        # Crear tablas necesarias si no existen
        try:
            self.crear_tabla_rma_orders()
            self.crear_tabla_adjuntos()
            self.crear_tabla_correos_asociados()
            self.crear_tabla_tareas()
            
            # Actualizar estructura de tabla tareas (añadir columnas asignado_a y prioridad)
            tareas_notificaciones.actualizar_tabla_tareas(self.master.conectar_db)
        except Exception as e:
            logger.error(f"Error al crear/actualizar tablas: {e}")

        # Migrar columnas de rma_maestro y rma_detalles
        try:
            self.verificar_columna_motivo()
        except Exception as e:
            logger.error(f"Error en migración de columnas: {e}")

        # Migrar columna fecha_entregado_contabilidad (Turso-safe)
        try:
            self._migrar_columna_contabilidad_rma_maestro()
        except Exception as e:
            logger.error(f"Error en migración columna contabilidad: {e}")

        # Migrar columnas resolucion_provisional / obs_res_provisional (Turso-safe)
        try:
            self._migrar_columnas_resolucion_provisional()
        except Exception as e:
            logger.error(f"Error en migración columnas resolución provisional: {e}")

        # Exponer a nivel de módulo para que Tooltip y otros lean la preferencia
        try:
            app_core.USER_SETTINGS = self.user_settings
        except Exception:
            pass
        
        # ----------------------------------------------------
        # 🛠️ AJUSTE DE PESO PARA EXPANDIR EL ÁREA DE TRABAJO 🛠️
        # ----------------------------------------------------
        # Configurar la expansión horizontal y vertical de la ventana principal
        
        # Columna 0 (Sidebar): Peso 0 (No se expande)
        self.master.grid_columnconfigure(0, weight=0) 
        
        # Columna 1 (Content Frame): Peso 1 (Ocupa todo el ancho restante)
        self.master.grid_columnconfigure(1, weight=1) 
        
        # Fila 0: Peso 1 (Ocupa toda la altura)
        self.master.grid_rowconfigure(0, weight=1)
        
        self.protocol("WM_DELETE_WINDOW", self.cerrar_app)
        # Título de la ventana principal
        try:
            self.title("Gestión RMA - Expedientes")
            # Agregar icono personalizado de ILUTREK
            self.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            # CTkToplevel puede usar wm_title alternativamente
            try:
                self.wm_title("Gestión RMA - Expedientes")
                self.iconbitmap("Icono_Ilutrek.ico")
            except Exception:
                pass  # Si no se puede cargar, continuar sin icono
            except Exception:
                pass
        
        self.crear_diseno()
        
        # Establecer tamaño inicial y centrar la ventana en la pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Tamaño de la ventana (80% de la pantalla o 1400x700, lo que sea mayor)
        window_width = max(1400, int(screen_width * 0.8))
        window_height = max(700, int(screen_height * 0.8))
        
        # Calcular posición central
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Aplicar geometría completa (tamaño + posición)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Establecer tamaño mínimo para acomodar el dashboard
        self.minsize(1400, 700)
        
        # Configurar atajos de teclado globales
        self.bind_all("<Control-f>", lambda e: self.mostrar_busqueda_global())
        self.bind_all("<Control-F>", lambda e: self.mostrar_busqueda_global())
        self.bind_all("<Control-n>", lambda e: self._abrir_editor_rma())
        self.bind_all("<Control-N>", lambda e: self._abrir_editor_rma())
        # Refrescar listado con F5 (como en muchas aplicaciones)
        try:
            self.bind_all("<F5>", lambda e: self.aplicar_filtros_rma())
        except Exception:
            # Failsafe: no bloquear si bind falla en algún entorno
            pass
        
        # Iniciar comprobación periódica de tareas (notificaciones para el creador)
        try:
            self.programar_chequeo_tareas()
        except Exception:
            pass
        
        # Inicializar gestor de avisos
        try:
            root_path = os.path.dirname(os.path.abspath(__file__))
            self.avisos_manager = AvisosManager(root_path)
            # Mostrar aviso si está activo (con un pequeño delay para que la ventana principal se renderice primero)
            self.after(500, lambda: self.avisos_manager.mostrar_aviso_popup(self))
        except Exception as e:
            print(f"Error al inicializar avisos: {e}")

    def verificar_columna_motivo(self):
        """
        Verifica si la columna 'motivo' existe en rma_maestro y la añade si no.
        Esto es una migración simple para SQLite.
        NOTA: Solo funciona con SQLite local. Turso debe tener la estructura completa desde el dump.
        """
        # Si estamos usando Turso, saltar esta verificación (ALTER TABLE no funciona bien)
        if os.getenv("TURSO_DATABASE_URL"):
            print("ℹ️ Usando Turso - verificación de columnas omitida (usar dump SQL completo)")
            return
        
        conn, cursor = self.master.conectar_db()
        if not conn: return

        try:
            # Obtenemos las columnas actuales de la tabla rma_maestro
            cursor.execute("PRAGMA table_info('rma_maestro')")
            cols = [row[1] for row in cursor.fetchall()]

            # Columnas que queremos asegurar que existen (nombre en DB, tipo y default opcional)
            columnas_necesarias = {
                'motivo': "TEXT",
                'rma_proveedor': "TEXT DEFAULT ''",
                'modelo': "TEXT DEFAULT ''",
                'n_serie': "TEXT DEFAULT ''",
                'ref_proveedor': "TEXT DEFAULT ''",
                'obs_tecnica': "TEXT DEFAULT ''"
            }

            for col_name, col_def in columnas_necesarias.items():
                if col_name not in cols:
                    try:
                        cursor.execute(f"ALTER TABLE rma_maestro ADD COLUMN {col_name} {col_def}")
                    except Exception as e:
                        print(f"Error al añadir columna '{col_name}': {e}")

            conn.commit()

        except Exception as e:
            print(f"Error comprobando/añadiendo columnas en rma_maestro: {e}")
        finally:
            conn.close()

        # Migración de columnas en rma_detalles (se ejecuta siempre, también en Turso)
        self._migrar_columnas_rma_detalles()

    def _migrar_columnas_rma_detalles(self):
        """
        Añade las columnas numero_albaran y numero_order a rma_detalles si no existen.
        Se ejecuta tanto en SQLite local como en Turso (ALTER TABLE ADD COLUMN es seguro en ambos).
        """
        try:
            result = self.master.conectar_db()
            if isinstance(result, tuple):
                conn, cursor = result
            else:
                conn = result
                cursor = conn.cursor() if conn else None

            if not conn or not cursor:
                return

            columnas_necesarias = {
                'numero_albaran': "TEXT DEFAULT ''",
                'numero_order': "TEXT DEFAULT ''",
            }

            try:
                cursor.execute("PRAGMA table_info('rma_detalles')")
                cols_actuales = [row[1] for row in cursor.fetchall()]
            except Exception:
                # Turso no soporta PRAGMA — intentar ADD COLUMN directamente (falla silenciosamente si ya existe)
                cols_actuales = []

            for col_name, col_def in columnas_necesarias.items():
                if col_name not in cols_actuales:
                    try:
                        cursor.execute(f"ALTER TABLE rma_detalles ADD COLUMN {col_name} {col_def}")
                        conn.commit()
                        print(f"✅ Columna '{col_name}' añadida a rma_detalles")
                    except Exception as e:
                        # Si ya existe la columna, el error es esperado y se ignora
                        err_str = str(e).lower()
                        if "duplicate" not in err_str and "already exists" not in err_str:
                            print(f"Info al añadir '{col_name}' en rma_detalles: {e}")

            conn.close()
        except Exception as e:
            print(f"Error en migración rma_detalles: {e}")

    def _migrar_columna_contabilidad_rma_maestro(self):
        """Añade la columna fecha_entregado_contabilidad a rma_maestro si no existe.
        Funciona tanto en SQLite local como en Turso (ALTER TABLE ADD COLUMN es seguro en ambos)."""
        try:
            result = self.master.conectar_db()
            if isinstance(result, tuple):
                conn, cursor = result
            else:
                conn = result
                cursor = conn.cursor() if conn else None

            if not conn or not cursor:
                return

            columnas_necesarias = {
                'fecha_entregado_contabilidad': "TEXT DEFAULT NULL",
            }

            try:
                cursor.execute("PRAGMA table_info('rma_maestro')")
                cols_actuales = [row[1] for row in cursor.fetchall()]
            except Exception:
                # Turso no soporta PRAGMA — intentar ADD COLUMN directamente
                cols_actuales = []

            for col_name, col_def in columnas_necesarias.items():
                if col_name not in cols_actuales:
                    try:
                        cursor.execute(f"ALTER TABLE rma_maestro ADD COLUMN {col_name} {col_def}")
                        conn.commit()
                        logger.info(f"Columna '{col_name}' añadida a rma_maestro")
                    except Exception as e:
                        err_str = str(e).lower()
                        if "duplicate" not in err_str and "already exists" not in err_str:
                            logger.warning(f"Info al añadir '{col_name}' en rma_maestro: {e}")

            conn.close()
        except Exception as e:
            logger.error(f"Error en migración columna contabilidad rma_maestro: {e}")

    def _migrar_columnas_resolucion_provisional(self):
        """Añade las columnas resolucion_provisional y obs_res_provisional a rma_maestro si no existen.
        Funciona tanto en SQLite local como en Turso (ALTER TABLE ADD COLUMN es seguro en ambos)."""
        try:
            result = self.master.conectar_db()
            if isinstance(result, tuple):
                conn, cursor = result
            else:
                conn = result
                cursor = conn.cursor() if conn else None

            if not conn or not cursor:
                return

            columnas_necesarias = {
                'resolucion_provisional': "TEXT DEFAULT ''",
                'obs_res_provisional': "TEXT DEFAULT ''",
            }

            try:
                cursor.execute("PRAGMA table_info('rma_maestro')")
                cols_actuales = [row[1] for row in cursor.fetchall()]
            except Exception:
                # Turso no soporta PRAGMA — intentar ADD COLUMN directamente
                cols_actuales = []

            for col_name, col_def in columnas_necesarias.items():
                if col_name not in cols_actuales:
                    try:
                        cursor.execute(f"ALTER TABLE rma_maestro ADD COLUMN {col_name} {col_def}")
                        conn.commit()
                        logger.info(f"Columna '{col_name}' añadida a rma_maestro")
                    except Exception as e:
                        err_str = str(e).lower()
                        if "duplicate" not in err_str and "already exists" not in err_str:
                            logger.warning(f"Info al añadir '{col_name}' en rma_maestro: {e}")

            conn.close()
        except Exception as e:
            logger.error(f"Error en migración columnas resolución provisional rma_maestro: {e}")

    def cerrar_app(self):
        """Maneja el cierre de la ventana principal y de toda la app."""
        from lib.confirmacion_cierre import confirmar_cierre_aplicacion
        
        if confirmar_cierre_aplicacion(self):
            self.master.destroy()

    def limpiar_contenido(self):
        """Limpia todos los widgets del marco de contenido principal."""
        try:
            if self.content_frame and self.content_frame.winfo_exists():
                for widget in self.content_frame.winfo_children():
                    try:
                        widget.destroy()
                    except:
                        pass
        except Exception as e:
            print(f"Error al limpiar contenido: {e}")

    def crear_diseno(self):
        """Define la estructura principal con un panel lateral y un área de contenido."""
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Panel Lateral de Navegación (Columna 0) ---
        self.sidebar_frame = ctk.CTkFrame(self,
                                          width=100,
                                          corner_radius=0,
                                          #fg_color="gray90"
                                          )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        ruta_logo = os.path.join(os.path.dirname(__file__), "Icono_Ilutrek.png")
        self.logo_image = ctk.CTkImage(light_image=Image.open(ruta_logo),
                                           dark_image=Image.open(ruta_logo),
                                           size=(100, 100)) # Ajusta este tamaño (width, height)
            
        # 💡 PASO 2: COLOCAR LA IMAGEN EN LA FILA 0
        # Usamos un CTkLabel para contener la imagen.
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, 
                                       text="", 
                                       image=self.logo_image)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        # Cargar iconos (outline 24x24) para botones icon-only
        ruta_icons = os.path.join(os.path.dirname(__file__), "icons")
        # Mantener referencias para evitar GC (ImageTk objects must be referenced)
        self._icon_refs = {}
        
        # Obtener tamaño de iconos desde configuración
        icon_size = self.user_settings.get("icon_size", 24)

        def _ensure_icon_png(fname, shape="rect", fg=(43,108,176,255)):
            """Asegura que exista un PNG válido en icons/fname. Si no existe o está corrupto,
            genera uno simple y lo guarda en disco.
            """
            path = os.path.join(ruta_icons, fname)
            try:
                if os.path.exists(path):
                    # Intentar abrir con PIL para verificar integridad
                    Image.open(path).verify()
                    return True
            except Exception:
                # Archivo corrupto o no imagen válida -> reescribir
                pass

            # Crear carpeta si no existe
            try:
                os.makedirs(ruta_icons, exist_ok=True)
            except Exception:
                pass

            # Generar imagen sencilla usando el tamaño configurado
            try:
                img = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                margin = icon_size // 6
                if shape == "list":
                    y1, y2, y3 = icon_size // 3, icon_size // 2, (icon_size * 2) // 3
                    draw.line([margin, y1, icon_size - margin, y1], fill=fg, width=2)
                    draw.line([margin, y2, icon_size - margin, y2], fill=fg, width=2)
                    draw.line([margin, y3, icon_size - margin, y3], fill=fg, width=2)
                elif shape == "dot":
                    draw.ellipse([margin, margin, icon_size - margin, icon_size - margin], outline=fg, width=2)
                elif shape == "pencil":
                    draw.line([margin, icon_size - margin, icon_size - margin, margin], fill=fg, width=2)
                    tip_size = icon_size // 6
                    draw.polygon([(icon_size - margin, margin),(icon_size - margin + tip_size, margin + tip_size),(icon_size - margin - tip_size, margin + tip_size)], fill=fg)
                else:
                    draw.rectangle([margin, margin, icon_size - margin, icon_size - margin], outline=fg, width=2)

                img.save(path, format="PNG")
                return True
            except Exception:
                return False

        def _load_icon(fname):
            path = os.path.join(ruta_icons, fname)
            if not os.path.exists(path):
                return None
            try:
                # Prefer CTkImage (works well with customtkinter)
                img = ctk.CTkImage(light_image=Image.open(path), dark_image=Image.open(path), size=(icon_size, icon_size))
                self._icon_refs[fname] = img
                return img
            except Exception:
                try:
                    # Fallback to ImageTk.PhotoImage if CTkImage fails
                    pil = Image.open(path).resize((icon_size, icon_size), Image.LANCZOS)
                    tkimg = ImageTk.PhotoImage(pil)
                    self._icon_refs[fname] = tkimg
                    return tkimg
                except Exception:
                    return None

        def _make_placeholder_icon(key=None, shape="rect", fg="#2b6cb0", bg=None):
            """Genera un icono simple con PIL y lo convierte a PhotoImage/CTkImage.
            shape: 'rect', 'dot', 'pencil' (simple), 'list'
            """
            try:
                img = Image.new("RGBA", (icon_size, icon_size), bg if bg is not None else (0, 0, 0, 0))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                margin = icon_size // 6
                if shape == "rect":
                    draw.rectangle([margin, margin, icon_size - margin, icon_size - margin], outline=fg, width=2)
                elif shape == "dot":
                    draw.ellipse([margin, margin, icon_size - margin, icon_size - margin], outline=fg, width=2)
                elif shape == "list":
                    # three horizontal lines
                    y1, y2, y3 = icon_size // 3, icon_size // 2, (icon_size * 2) // 3
                    draw.line([margin, y1, icon_size - margin, y1], fill=fg, width=2)
                    draw.line([margin, y2, icon_size - margin, y2], fill=fg, width=2)
                    draw.line([margin, y3, icon_size - margin, y3], fill=fg, width=2)
                elif shape == "pencil":
                    # simple pencil: diagonal line + tip
                    draw.line([margin, icon_size - margin, icon_size - margin, margin], fill=fg, width=2)
                    tip_size = icon_size // 6
                    draw.polygon([(icon_size - margin, margin),(icon_size - margin + tip_size, margin + tip_size),(icon_size - margin - tip_size, margin + tip_size)], fill=fg)
                else:
                    draw.rectangle([margin, margin, icon_size - margin, icon_size - margin], outline=fg, width=2)

                # Try CTkImage first
                try:
                    ctki = ctk.CTkImage(light_image=img, dark_image=img, size=(icon_size, icon_size))
                    keyname = f"gen-{key or shape}"
                    self._icon_refs[keyname] = ctki
                    return ctki
                except Exception:
                    tkimg = ImageTk.PhotoImage(img)
                    keyname = f"gen-{key or shape}"
                    self._icon_refs[keyname] = tkimg
                    return tkimg
            except Exception:
                return None

        # Asegurar que existan ficheros PNG válidos en disco (sobrescribe corruptos)
        _ensure_icon_png("ic_list_outline_24.png", shape="list")
        _ensure_icon_png("ic_articles_outline_24.png", shape="rect")
        _ensure_icon_png("ic_stats_outline_24.png", shape="dot")
        _ensure_icon_png("ic_tasks_outline_24.png", shape="rect")
        _ensure_icon_png("ic_reports_outline_24.png", shape="rect")
        _ensure_icon_png("boton-de-informacion.png", shape="dot")
        _ensure_icon_png("ic_edit_outline_24.png", shape="pencil")
        # Additional user-provided icons
        _ensure_icon_png("user.png", shape="rect")
        _ensure_icon_png("papel.png", shape="rect")
        _ensure_icon_png("mas.png", shape="rect")
        _ensure_icon_png("settings.png", shape="rect")

        # Cargar iconos (preferir CTkImage, fallback a ImageTk)
        self.icon_list = _load_icon("ic_list_outline_24.png") or _make_placeholder_icon("list", shape="list")
        self.icon_articles = _load_icon("ic_articles_outline_24.png") or _make_placeholder_icon("articles", shape="rect")
        self.icon_stats = _load_icon("ic_stats_outline_24.png") or _make_placeholder_icon("stats", shape="dot")
        self.icon_tasks = _load_icon("ic_tasks_outline_24.png") or _make_placeholder_icon("tasks", shape="rect")
        self.icon_reports = _load_icon("ic_reports_outline_24.png") or _make_placeholder_icon("reports", shape="rect")
        self.icon_info = _load_icon("boton-de-informacion.png") or _make_placeholder_icon("info", shape="dot")
        self.icon_edit = _load_icon("ic_edit_outline_24.png") or _make_placeholder_icon("edit", shape="pencil")
        # Load additional icons (user, papel, mas)
        self.icon_user = _load_icon("user.png")
        self.icon_papel = _load_icon("papel.png")
        self.icon_mas = _load_icon("mas.png")
        self.icon_settings = _load_icon("settings.png")
        self.icon_busqueda = _load_icon("busqueda.png")
        self.icon_bd = _load_icon("bd.png")
        self.icon_report = _load_icon("report.png")
        self.icon_ventas_compras = _load_icon("ventas_compras.png") or _make_placeholder_icon("ventas_compras", shape="rect")
        
        # ... (Botones btn_lista, btn_buscar, btn_reportar en filas 1, 2, 3) ...

        # Fila alta: Espacio vacío para empujar los elementos inferiores.
        # Reservamos una fila alta para 'push' y colocamos la info de usuario en filas finales.
        self.sidebar_frame.grid_rowconfigure(20, weight=1) # <--- Espaciador principal.

        # Fila alta: Espacio vacío para empujar los elementos inferiores.
        self.sidebar_frame.grid_rowconfigure(50, weight=1)  # Uso fila 50 para tener espacio para más botones

        # Información de Usuario y Rol (al final)
        self.lbl_usuario_rol = ctk.CTkLabel(self.sidebar_frame, text=f"Usuario: {self.username} ({self.rol})", font=ctk.CTkFont(size=12))
        self.lbl_usuario_rol.grid(row=51, column=0, padx=20, pady=(10, 5), sticky="s")

        # Versión de la App
        ctk.CTkLabel(self.sidebar_frame, text=f"Versión: {APP_VERSION}", font=ctk.CTkFont(size=10, slant="italic")).grid(row=52, column=0, padx=20, pady=(0, 2), sticky="s")

        # Copyright
        año_actual = datetime.datetime.now().year
        ctk.CTkLabel(self.sidebar_frame, text=f"© {año_actual} ILUTREK, S.L.", font=ctk.CTkFont(size=10, weight="bold")).grid(row=53, column=0, padx=20, pady=(2, 10), sticky="s")
        
        ctk.CTkLabel(self.sidebar_frame, text="MENÚ", font=ctk.CTkFont(family="Verdana", size=20, weight="bold")).grid(row=1, column=0, padx=20, pady=(20, 10))

        # Usamos índices de fila secuenciales para evitar solapamientos.
        fila = 2

        # Botón Búsqueda Global - busca en todos los campos
        sidebar_bg = self.sidebar_frame.cget("fg_color") if hasattr(self.sidebar_frame, 'cget') else None
        self.btn_busqueda_global = ctk.CTkButton(self.sidebar_frame,
                                               text="",
                                               image=self.icon_busqueda,
                                               width=44,
                                               height=44,
                                               fg_color=sidebar_bg,
                                               hover_color=sidebar_bg,
                                               command=self.mostrar_busqueda_global)
        self.btn_busqueda_global.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_busqueda_global, "Búsqueda Global - Buscar en todos los campos")
        fila += 1

        # Botón de gestión de usuarios (solo visible para administradores)
        if str(self.rol).strip().lower() in ("admin", "administrador"):
            sidebar_bg = self.sidebar_frame.cget("fg_color") if hasattr(self.sidebar_frame, 'cget') else None
            self.btn_usuarios = ctk.CTkButton(self.sidebar_frame,
                                             text="",
                                             image=(self.icon_user or self.icon_tasks),
                                             width=44,
                                             height=44,
                                             fg_color=sidebar_bg if sidebar_bg is not None else None,
                                             hover_color=sidebar_bg if sidebar_bg is not None else None,
                                             command=self.mostrar_gestion_usuarios)
            self.btn_usuarios.grid(row=fila, column=0, padx=12, pady=6)
            Tooltip(self.btn_usuarios, "Gestión de usuarios")
            fila += 1
            
        sidebar_bg = self.sidebar_frame.cget("fg_color") if hasattr(self.sidebar_frame, 'cget') else None

        self.btn_lista = ctk.CTkButton(self.sidebar_frame,
                                       text="",
                                       image=self.icon_list,
                                       width=44,
                                       height=44,
                                       fg_color=sidebar_bg,
                                       hover_color=sidebar_bg,
                                       command=self.mostrar_lista_rma)
        self.btn_lista.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_lista, "Listado de expedientes")
        fila += 1

        # Botón Artículos: abre ventana con listado de artículos y conteo de expedientes asociados
        self.btn_articulos = ctk.CTkButton(self.sidebar_frame,
                                           text="",
                                           image=self.icon_articles,
                                           width=44,
                                           height=44,
                                           fg_color=sidebar_bg,
                                           hover_color=sidebar_bg,
                                           command=self.mostrar_articulos_window)
        self.btn_articulos.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_articulos, "Artículos")
        fila += 1

        # Botón Ventas/Compras a3ERP: importación y comparativa con incidencias
        self.btn_ventas_compras = ctk.CTkButton(self.sidebar_frame,
                                           text="",
                                           image=self.icon_ventas_compras,
                                           width=44,
                                           height=44,
                                           fg_color=sidebar_bg,
                                           hover_color=sidebar_bg,
                                           command=self.mostrar_ventas_compras_a3erp)
        self.btn_ventas_compras.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_ventas_compras, "Ventas y Compras (a3ERP)")
        fila += 1

        self.btn_estadisticas = ctk.CTkButton(self.sidebar_frame,
                                              text="",
                                              image=self.icon_stats,
                                              width=44,
                                              height=44,
                                              fg_color=sidebar_bg,
                                              hover_color=sidebar_bg,
                                              command=self.mostrar_ventana_estadisticas)
        self.btn_estadisticas.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_estadisticas, "Filtrar / Estadísticas")
        fila += 1

        # Botón de Tareas (lista y creación de tareas por expediente) con badge
        # Crear frame contenedor para el botón + badge
        self.frame_tareas = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.frame_tareas.grid(row=fila, column=0, padx=20, pady=6)
        
        self.btn_tareas = ctk.CTkButton(self.frame_tareas,
                                        text="",
                                        image=self.icon_tasks,
                                        width=44,
                                        height=44,
                                        fg_color=sidebar_bg,
                                        hover_color=sidebar_bg,
                                        command=self.mostrar_gestion_tareas)
        self.btn_tareas.grid(row=0, column=0)
        
        # Badge mejorado con auto-actualización y panel
        self.badge_tareas = TareasBadge(
            parent=self.frame_tareas,
            connect_db_func=self.conectar_db,
            username=self.username,
            on_click_callback=self.abrir_panel_tareas
        )
        self.badge_tareas.grid(row=0, column=0, sticky="ne", padx=(30, 0), pady=(0, 0))
        
        # Iniciar auto-actualización del badge cada 5 minutos
        self.badge_tareas.programar_actualizacion()
        
        Tooltip(self.btn_tareas, "Tareas")
        fila += 1

        # Botón de Gestión de Clientes
        self.btn_clientes = ctk.CTkButton(self.sidebar_frame,
                                        text="",
                                        image=self.icon_user,  # Usar icono de usuario para clientes
                                        width=44,
                                        height=44,
                                        fg_color=sidebar_bg,
                                        hover_color=sidebar_bg,
                                        command=self.mostrar_clientes)
        self.btn_clientes.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_clientes, "Gestión de Clientes")
        fila += 1

        # Botón Gestión RMP (Proveedores -> Expedientes)
        self.btn_gestion_rmp = ctk.CTkButton(self.sidebar_frame,
                                             text="",
                                             image=(self.icon_papel or self.icon_reports),
                                             width=44,
                                             height=44,
                                             fg_color=sidebar_bg,
                                             hover_color=sidebar_bg,
                                             command=self.mostrar_gestion_rmp)
        self.btn_gestion_rmp.grid(row=fila, column=0, padx=12, pady=6)
        Tooltip(self.btn_gestion_rmp, "Gestión RMP")
        fila += 1

        # Mostrar botón de Backup solo para administradores y Dpto. Tecnico
        rol_norm = str(self.rol).strip().lower()
        if rol_norm in ("admin", "administrador", "dpto. tecnico", "dpto tecnico", "dpto técnico"):
            self.btn_buscar = ctk.CTkButton(self.sidebar_frame,
                                           text="",
                                           image=self.icon_bd,
                                           width=44,
                                           height=44,
                                           fg_color=sidebar_bg,
                                           hover_color=sidebar_bg,
                                           command=self.mostrar_gestor_backups)
            self.btn_buscar.grid(row=fila, column=0, padx=20, pady=6)
            Tooltip(self.btn_buscar, "Gestor de Backups en Backblaze B2")
            fila += 1

        self.btn_reportar = ctk.CTkButton(self.sidebar_frame,
                                          text="",
                                          image=self.icon_report,
                                          width=44,
                                          height=44,
                                          fg_color=sidebar_bg,
                                          hover_color=sidebar_bg,
                                          command=lambda: github_issue_manager.mostrar_ventana_info_issue(self, lambda: github_issue_manager.mostrar_formulario_github(self)))
        self.btn_reportar.grid(row=fila, column=0, padx=20, pady=6)
        Tooltip(self.btn_reportar, "Reportar un problema / abrir GitHub")
        
        # Botón Ajustes - abre diálogo de preferencias del usuario
        try:
            fila += 1
            self.btn_ajustes = ctk.CTkButton(self.sidebar_frame,
                                             text="",
                                             image=(self.icon_settings or self.icon_info),
                                             width=44,
                                             height=44,
                                             fg_color=sidebar_bg if sidebar_bg is not None else None,
                                             hover_color=sidebar_bg if sidebar_bg is not None else None,
                                             command=self.mostrar_ajustes)
            self.btn_ajustes.grid(row=fila, column=0, padx=20, pady=6)
            Tooltip(self.btn_ajustes, "Ajustes")
        except Exception:
            pass
        
        # Botón de menú Admin (solo para administradores) - AL FINAL
        if str(self.rol).strip().lower() in ("admin", "administrador"):
            fila += 1
            self.btn_admin_menu = ctk.CTkButton(self.sidebar_frame,
                                               text="⚙️ Admin",
                                               width=100,
                                               height=35,
                                               font=ctk.CTkFont(size=12, weight="bold"),
                                               command=self.mostrar_menu_admin)
            self.btn_admin_menu.grid(row=fila, column=0, padx=12, pady=8)
            Tooltip(self.btn_admin_menu, "Funciones de Administración")
        
        # --- Contenido Principal (Columna 1) ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent") # 'transparent' para que herede el fondo 'Light' (blanco)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Establecer tamaño mínimo de ventana para acomodar el dashboard
        self.minsize(1400, 700)
        
        self.mostrar_lista_rma()

    def verificar_tareas_pendientes_expediente(self, rma_id):
        """Verifica si un expediente específico tiene tareas pendientes."""
        try:
            conn, cursor = self.conectar_db()
            if not conn:
                return 0, []
            
            # Primero obtenemos el código RMA del expediente
            cursor.execute("SELECT codigo_rma FROM rma_maestro WHERE id = ?", (rma_id,))
            resultado_rma = cursor.fetchone()
            if not resultado_rma:
                conn.close()
                return 0, []
            
            codigo_rma = resultado_rma[0]
            
            # Ahora buscamos tareas pendientes usando el código RMA
            cursor.execute("""
                SELECT COUNT(*), GROUP_CONCAT(titulo || ' (' || estado || ')') as tareas_pendientes
                FROM tareas 
                WHERE codigo_rma = ? 
                AND estado NOT IN ('Completado', 'Completada', 'Finalizada')
                AND estado IS NOT NULL
            """, (codigo_rma,))
            
            resultado = cursor.fetchone()
            count = int(resultado[0]) if resultado[0] else 0
            tareas_pendientes = resultado[1].split(',') if resultado[1] else []
            
            conn.close()
            return count, tareas_pendientes
        except Exception as e:
            print(f"Error al verificar tareas pendientes del expediente: {e}")
            return 0, []

    def conectar_db(self):
        """Intenta conectar a la base de datos (método heredado de master)."""
        return self.master.conectar_db()

    def obtener_temas_disponibles(self):
        """Obtiene la lista de temas disponibles desde la carpeta themes/"""
        import glob
        import os
        try:
            temas = []
            # Buscar archivos .json en la carpeta themes
            archivos_tema = glob.glob("themes/*.json")
            for archivo in archivos_tema:
                # Normalizar la ruta y extraer solo el nombre del archivo sin la extensión
                nombre_archivo = os.path.basename(archivo)
                nombre_tema = os.path.splitext(nombre_archivo)[0]
                # Convertir nombres a formato más amigable
                if nombre_tema.lower() == "bh_rime":
                    display = "BH Rime (Predeterminado)"
                else:
                    # Reemplazar guiones/underscores por espacios y title case
                    display = nombre_tema.replace('_', ' ').replace('-', ' ').title()
                temas.append(display)

            # Asegurar que BH Rime esté primero
            temas_ordenados = []
            if any(t.startswith("BH Rime") for t in temas):
                # encontrar la primera que contenga 'BH Rime'
                for t in temas:
                    if t.startswith("BH Rime"):
                        temas_ordenados.append(t)
                        temas.remove(t)
                        break
            temas_ordenados.extend(sorted(temas))

            return temas_ordenados if temas_ordenados else ["BH Rime (Predeterminado)"]
        except Exception:
            return ["BH Rime (Predeterminado)", "Rime", "Metal", "Pink", "Red"]

    def tema_display_a_archivo(self, tema_display):
        """Convierte el nombre mostrado del tema al nombre del archivo"""
        # Limpiar el nombre de entrada por si tiene rutas o caracteres extraños
        tema_limpio = tema_display.replace("Themes\\", "").replace("Themes/", "").replace("themes\\", "").replace("themes/", "").strip()

        # Mapeo rápido para nombres comunes
        mapping = {
            "BH Rime (Predeterminado)": "BH_rime.json",
            "Rime": "rime.json",
            "Metal": "metal.json",
            "Pink": "pink.json",
            "Red": "red.json"
        }
        if tema_limpio in mapping:
            return mapping[tema_limpio]

        # Intentar buscar un archivo en themes/ que coincida con el display
        import glob, os
        posibles = glob.glob("themes/*.json")
        # Normalizar display para comparar
        display_norm = tema_limpio.lower().replace(' ', '').replace('_', '').replace('-', '')
        for p in posibles:
            base = os.path.splitext(os.path.basename(p))[0]
            if base.lower() == tema_limpio.lower().replace(' ', '_') or base.lower() == tema_limpio.lower():
                return os.path.basename(p)
            if base.lower().replace('_', '').replace('-', '') == display_norm:
                return os.path.basename(p)

        # Intentar construir nombres probables
        cand1 = f"{tema_limpio}.json"
        cand2 = f"{tema_limpio.replace(' ', '_')}.json"
        if os.path.exists(os.path.join('themes', cand1)):
            return cand1
        if os.path.exists(os.path.join('themes', cand2)):
            return cand2

        # Fallback: BH_rime
        return 'BH_rime.json'

    def archivo_a_tema_display(self, archivo_tema):
        """Convierte el nombre del archivo al nombre mostrado"""
        import os
        if not archivo_tema:
            return "BH Rime (Predeterminado)"
        # Si viene con path, extraer basename
        archivo = os.path.basename(archivo_tema)
        name = os.path.splitext(archivo)[0]
        if name.lower() == 'bh_rime':
            return 'BH Rime (Predeterminado)'
        # Normalizar: underscore/dash -> space, title case
        display = name.replace('_', ' ').replace('-', ' ').title()
        return display

    def mostrar_ajustes(self):
        """Abre la ventana de ajustes del usuario."""
        try:
            from lib.settings_window import SettingsWindow
            logger.info(f"Abriendo ventana de ajustes para usuario: {self.username}")
            SettingsWindow(self, self)
        except Exception as e:
            logger.error(f"Error abriendo ventana de ajustes: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir la ventana de ajustes:\n{e}")

    def mostrar_ventas_compras_a3erp(self):
        """Abre la ventana de importación y comparativa de ventas/compras de a3ERP."""
        try:
            if hasattr(self, 'ventas_compras_window') and self.ventas_compras_window.winfo_exists():
                self.ventas_compras_window.focus()
                return
            from lib.ventas_compras_a3erp import VentanaVentasComprasA3ERP
            self.ventas_compras_window = VentanaVentasComprasA3ERP(self)
        except Exception as e:
            logger.error(f"Error abriendo ventana de ventas/compras a3ERP: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir la ventana de ventas/compras:\n{e}")

    def mostrar_manual_usuario(self):
        """Abre una ventana con el contenido del manual de usuario organizado por secciones."""
        import os
        import re
        
        try:
            # Ruta al archivo del manual
            ruta_manual = os.path.join(os.path.dirname(__file__), "Guias", "MANUAL_USUARIO.md")
            
            if not os.path.exists(ruta_manual):
                messagebox.showwarning("Manual no encontrado", 
                                      f"No se encontró el archivo del manual en:\n{ruta_manual}")
                logger.warning(f"Manual de usuario no encontrado en: {ruta_manual}")
                return
            
            # Leer el contenido del manual
            with open(ruta_manual, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
            
            # Parsear secciones del markdown (headers que empiezan con ##)
            secciones = []
            contenido_secciones = {}
            seccion_actual = None
            contenido_actual = []
            
            for linea in lineas:
                # Detectar headers de nivel 2 (## Titulo)
                match = re.match(r'^##\s+(.+)$', linea.strip())
                if match:
                    # Guardar sección anterior si existe
                    if seccion_actual:
                        contenido_secciones[seccion_actual] = ''.join(contenido_actual)
                    
                    # Nueva sección
                    titulo_seccion = match.group(1)
                    # Limpiar emojis y caracteres especiales para el key
                    key_seccion = re.sub(r'[^\w\s-]', '', titulo_seccion).strip()
                    secciones.append((titulo_seccion, key_seccion))
                    seccion_actual = key_seccion
                    contenido_actual = [linea]
                else:
                    if seccion_actual:
                        contenido_actual.append(linea)
            
            # Guardar última sección
            if seccion_actual:
                contenido_secciones[seccion_actual] = ''.join(contenido_actual)
            
            # Crear ventana para mostrar el manual
            ventana_manual = ctk.CTkToplevel(self)
            ventana_manual.title("📖 Manual de Usuario - Gestor de Expedientes")
            ventana_manual.geometry("1200x750")
            
            # Hacer que la ventana esté siempre al frente
            ventana_manual.transient(self)
            ventana_manual.lift()
            ventana_manual.focus_force()
            ventana_manual.attributes('-topmost', True)
            # Después de un momento, quitar el topmost para que pueda moverse normalmente
            ventana_manual.after(100, lambda: ventana_manual.attributes('-topmost', False))
            
            # Agregar icono
            try:
                ventana_manual.iconbitmap("Icono_Ilutrek.ico")
            except Exception:
                pass
            
            # Frame principal con grid para dividir en dos columnas
            frame_principal = ctk.CTkFrame(ventana_manual)
            frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
            frame_principal.grid_columnconfigure(1, weight=1)
            frame_principal.grid_rowconfigure(1, weight=1)
            
            # Título superior
            titulo_label = ctk.CTkLabel(frame_principal, 
                                       text="📖 Manual de Usuario - Gestor de Expedientes RMA",
                                       font=ctk.CTkFont(size=18, weight="bold"))
            titulo_label.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="ew")
            
            # ===== PANEL IZQUIERDO: ÍNDICE DE SECCIONES =====
            indice_frame = ctk.CTkScrollableFrame(frame_principal, 
                                                  label_text="📑 Índice de Secciones",
                                                  width=280)
            indice_frame.grid(row=1, column=0, padx=(5, 5), pady=5, sticky="nsew")
            
            # ===== PANEL DERECHO: CONTENIDO =====
            contenido_container = ctk.CTkFrame(frame_principal)
            contenido_container.grid(row=1, column=1, padx=(5, 5), pady=5, sticky="nsew")
            contenido_container.grid_rowconfigure(0, weight=1)
            contenido_container.grid_columnconfigure(0, weight=1)
            
            # Frame scrollable para el contenido
            contenido_frame = ctk.CTkScrollableFrame(contenido_container, 
                                                     label_text="Contenido")
            contenido_frame.grid(row=0, column=0, sticky="nsew")
            
            # Label para mostrar el contenido de la sección actual
            contenido_label = ctk.CTkLabel(contenido_frame,
                                          text="",
                                          font=ctk.CTkFont(size=11, family="Segoe UI"),
                                          justify="left",
                                          anchor="nw",
                                          wraplength=750)
            contenido_label.pack(fill="both", expand=True, padx=15, pady=15)
            
            # Función para mostrar una sección
            def mostrar_seccion(titulo_seccion, key_seccion, btn_clickeado=None):
                """Muestra el contenido de una sección específica."""
                contenido = contenido_secciones.get(key_seccion, "Sección no encontrada")
                contenido_label.configure(text=contenido)
                contenido_frame.configure(label_text=f"📄 {titulo_seccion}")
                
                # Resetear colores de todos los botones del índice
                for widget in indice_frame.winfo_children():
                    if isinstance(widget, ctk.CTkButton):
                        widget.configure(fg_color="#1f538d", hover_color="#14375e")
                
                # Destacar el botón clickeado
                if btn_clickeado:
                    btn_clickeado.configure(fg_color="#14375e", hover_color="#0d2943")
                
                logger.debug(f"Manual: mostrando sección '{titulo_seccion}'")
            
            # Crear botones para cada sección en el índice
            primer_boton = None
            for i, (titulo, key) in enumerate(secciones):
                # Truncar títulos muy largos para el botón
                titulo_boton = titulo if len(titulo) <= 35 else titulo[:32] + "..."
                
                btn = ctk.CTkButton(indice_frame,
                                   text=f"{i+1}. {titulo_boton}",
                                   font=ctk.CTkFont(size=11),
                                   anchor="w",
                                   height=32,
                                   fg_color="#1f538d",
                                   hover_color="#14375e")
                btn.pack(fill="x", padx=5, pady=3)
                
                # Configurar comando con lambda que captura el botón
                btn.configure(command=lambda t=titulo, k=key, b=btn: mostrar_seccion(t, k, b))
                Tooltip(btn, titulo)  # Tooltip con el título completo
                
                if i == 0:
                    primer_boton = btn
            
            # Frame de botones inferior
            botones_frame = ctk.CTkFrame(frame_principal, fg_color="transparent")
            botones_frame.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="ew")
            
            def cerrar_manual():
                ventana_manual.destroy()
                logger.info("Manual de usuario cerrado")
            
            def abrir_archivo():
                """Abre el archivo del manual con el programa predeterminado."""
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(ruta_manual)
                    elif os.name == 'posix':  # macOS/Linux
                        import subprocess
                        subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', ruta_manual])
                    logger.info(f"Manual de usuario abierto: {ruta_manual}")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
                    logger.error(f"Error abriendo archivo del manual: {e}")
            
            # Botones
            btn_abrir = ctk.CTkButton(botones_frame, 
                                     text="📄 Abrir archivo original",
                                     command=abrir_archivo,
                                     width=180)
            btn_abrir.pack(side="left", padx=5)
            Tooltip(btn_abrir, "Abre el archivo Markdown del manual con tu editor predeterminado")
            
            btn_cerrar = ctk.CTkButton(botones_frame,
                                      text="Cerrar",
                                      command=cerrar_manual,
                                      width=100)
            btn_cerrar.pack(side="right", padx=5)
            Tooltip(btn_cerrar, "Cierra esta ventana")
            
            # Mostrar la primera sección por defecto
            if primer_boton and secciones:
                mostrar_seccion(secciones[0][0], secciones[0][1], primer_boton)
            
            logger.info(f"Manual de usuario mostrado con {len(secciones)} secciones")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir el manual de usuario:\n{e}")
            logger.error(f"Error mostrando manual de usuario: {e}", exc_info=True)

    def crear_campo(self, parent, fila, label_text, campo_bd, valor_defecto="", deshabilitado=False, tipo="entry", opciones=None):
        """Función auxiliar para crear etiquetas y campos de entrada/desplegables en el formulario."""
        ctk.CTkLabel(parent, text=label_text).grid(row=fila, column=0, padx=10, pady=5, sticky="w")

        
        widget = None
        
        if tipo == "entry":
            # 1. Crear el Entry en estado normal (por defecto)
            widget = ctk.CTkEntry(parent, width=300, state="normal") 
            
            # 2. Insertar el valor (solo se puede en estado normal)
            if valor_defecto:
                widget.insert(0, valor_defecto)
                
            # 3. Deshabilitar si se indica
            if deshabilitado:
                widget.configure(state="disabled")

        elif tipo == "optionmenu":
            widget = ctk.CTkOptionMenu(parent, 
                                       values=opciones, 
                                       width=300,
                                       #fg_color="gray80",        # Color del botón principal
                                       #button_color="gray70",    # Color del botón de flecha
                                       #button_hover_color="gray60", # Color al pasar el ratón por el botón de flecha
                                       #text_color="black"
                                       )
            if valor_defecto in opciones:
                widget.set(valor_defecto)
            elif opciones:
                widget.set(opciones[0])
            # Nota: CTkOptionMenu no tiene estado 'disabled' de forma nativa como el Entry, 
            # pero no es necesario para los campos que estamos usando ahora.
        elif tipo == "date":
            # 📅 Campo de selección de fecha
            widget = CTkDatePicker(parent, width=300)
            # Aplicar el formato de fecha según la preferencia del usuario (solo visual)
            try:
                pref = getattr(self, 'user_settings', {}).get('date_format', 'YYYY-MM-DD')
                fmt_map = {
                    'YYYY-MM-DD': '%Y-%m-%d',
                    'DD/MM/YYYY': '%d/%m/%Y',
                    'MM/DD/YYYY': '%m/%d/%Y'
                }
                widget_fmt = fmt_map.get(pref, '%Y-%m-%d')
                widget.set_date_format(widget_fmt)
            except Exception:
                # Fallback seguro
                try:
                    widget.set_date_format('%Y-%m-%d')
                except Exception:
                    pass

            # Si hay valor por defecto, establecerlo
            if valor_defecto:
                try:
                    from datetime import datetime
                    fecha = datetime.strptime(valor_defecto, "%Y-%m-%d")
                    widget.set_date(fecha)
                except ValueError:
                    pass  # Ignorar si el formato no es válido

            if deshabilitado:
                widget.configure(state="disabled")

            
        if widget:
            widget.grid(row=fila, column=1, padx=10, pady=5, sticky="ew")
            # Guardamos la referencia para acceder a los datos después
            setattr(self, f"entry_{campo_bd}", widget)

    def crear_tabla_rma_orders(self):
        """Crea la tabla de órdenes/partidas RMA si no existe."""
        try:
            conn, cursor = self.master.conectar_db()
            if not conn:
                return
                
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rma_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rma_id INTEGER NOT NULL,
                    num_order TEXT,
                    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Tabla rma_orders creada o verificada correctamente")
        except Exception as e:
            logger.error(f"Error al crear tabla rma_orders: {e}")

    def crear_tabla_correos_asociados(self):
        """Crea la tabla rma_correos_asociados si no existe."""
        conn, cursor = self.master.conectar_db()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rma_correos_asociados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rma_id INTEGER NOT NULL,
                    asunto TEXT,
                    remitente TEXT,
                    fecha_correo TEXT,
                    cuerpo TEXT,
                    nombre_archivo_original TEXT,
                    ruta_relativa_adjunto TEXT,
                    tipo_almacenamiento TEXT DEFAULT 'local',
                    fecha_importacion TEXT,
                    usuario_importacion TEXT,
                    FOREIGN KEY (rma_id) REFERENCES rma_maestro (id)
                )
            """)
            conn.commit()
            logger.info("Tabla rma_correos_asociados creada o verificada correctamente")
        except Exception as e:
            logger.error(f"Error al crear tabla rma_correos_asociados: {e}")
        finally:
            conn.close()

    def crear_tabla_adjuntos(self):
        """Crea la tabla rma_adjuntos si no existe."""
        conn, cursor = self.master.conectar_db()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rma_adjuntos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rma_id INTEGER NOT NULL,
                    nombre_archivo TEXT NOT NULL,
                    ruta_relativa TEXT NOT NULL,
                    fecha_subida TEXT,
                    usuario_subida TEXT,
                    tipo_almacenamiento TEXT DEFAULT 'local',
                    FOREIGN KEY (rma_id) REFERENCES rma_maestro (id)
                )
            """)
            
            # Verificar si podemos usar la nueva columna
            self._verificar_columna_tipo_almacenamiento(cursor)
            
            conn.commit()
            if getattr(self, '_usar_tipo_almacenamiento', False):
                print("✓ Sistema de adjuntos configurado con esquema nuevo (Backblaze B2/Local tracking)")
            else:
                print("✓ Sistema de adjuntos configurado con esquema clásico (compatible)")
        except sqlite3.Error as e:
            print(f"Error al crear la tabla 'rma_adjuntos': {e}")
        finally:
            conn.close()

    def _verificar_columna_tipo_almacenamiento(self, cursor):
        """Verifica si la columna tipo_almacenamiento existe y funciona."""
        try:
            # Intentar hacer un SELECT con la columna
            cursor.execute("SELECT tipo_almacenamiento FROM rma_adjuntos LIMIT 1")
            self._usar_tipo_almacenamiento = True
            print("✓ Esquema nuevo detectado - usando columna tipo_almacenamiento")
        except Exception as e:
            error_str = str(e).lower()
            if ("no column named tipo_almacenamiento" in error_str or 
                "table rma_adjuntos has no column named tipo_almacenamiento" in error_str or
                "no such table" in error_str or
                "no such column: tipo_almacenamiento" in error_str):
                self._usar_tipo_almacenamiento = False
                print("✓ Esquema clásico detectado - usando compatibilidad con BD existente")
            else:
                # Si es otro error, usar esquema compatible por seguridad
                self._usar_tipo_almacenamiento = False
                print(f"✓ Usando esquema compatible por seguridad: {e}")

    def crear_tabla_tareas(self):
        """Crea la tabla 'tareas' si no existe. Asociada a RMA por código o libre."""
        conn, cursor = self.master.conectar_db()
        if not conn:
            return
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tareas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_rma TEXT,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    fecha_vencimiento TEXT,
                    estado TEXT DEFAULT 'Pendiente',
                    creado_por TEXT,
                    creado_en TEXT,
                    notificado INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            print("Tabla 'tareas' verificada/creada.")
        except sqlite3.Error as e:
            print(f"Error al crear la tabla 'tareas': {e}")
        finally:
            conn.close()

    def comprobar_tareas_vencidas(self):
        """Comprueba tareas vencidas para el usuario actual y muestra notificaciones."""
        try:
            # Obtener ruta del icono de la app
            icono = None
            try:
                icono_path = os.path.join(os.path.dirname(__file__), "Icono_Ilutrek.ico")
                if os.path.exists(icono_path):
                    icono = icono_path
            except Exception:
                pass
            
            # Usar el módulo de tareas_notificaciones
            tareas_notificaciones.comprobar_y_notificar_tareas(
                connect_db_func=self.conectar_db,
                usuario=self.username,
                mostrar_messagebox_func=lambda title, msg: messagebox.showinfo(title, msg),
                icono=icono,
                habilitar_sonido=self.user_settings.get("notificaciones_sonoras", True),
                dias_anticipacion=self.user_settings.get("dias_anticipacion_vencimiento", 7),
                volumen=self.user_settings.get("volumen_notificaciones", 50)
            )
            
            # Chequear expedientes sin gestionar
            dias_sin_gestionar = self.user_settings.get("dias_notificar_sin_gestionar", 30)
            if dias_sin_gestionar > 0:
                expedientes = tareas_notificaciones.obtener_expedientes_sin_gestionar(
                    connect_db_func=self.conectar_db,
                    dias_sin_gestionar=dias_sin_gestionar
                )
                
                if expedientes:
                    mensaje_lines = [f"⚠️ {len(expedientes)} expediente(s) sin gestionar por más de {dias_sin_gestionar} días:"]
                    for exp in expedientes[:5]:  # Mostrar máximo 5
                        dias = exp.get('dias_sin_gestionar', '?')
                        mensaje_lines.append(f"  • {exp['codigo_rma']} - {exp['cliente']} ({dias} días)")
                    
                    if len(expedientes) > 5:
                        mensaje_lines.append(f"  ... y {len(expedientes) - 5} más")
                    
                    mensaje_completo = "\n".join(mensaje_lines)
                    
                    tareas_notificaciones.enviar_notificacion_nativa(
                        titulo="📋 Expedientes Pendientes",
                        mensaje=mensaje_completo,
                        icono=icono,
                        timeout=15,
                        reproducir_sonido=self.user_settings.get("notificaciones_sonoras", True),
                        volumen=self.user_settings.get("volumen_notificaciones", 50)
                    )
                    
        except Exception as e:
            logger.error(f"Error en comprobar_tareas_vencidas: {e}", exc_info=True)

    def programar_chequeo_tareas(self, intervalo_ms=3_600_000):
        """Programa la comprobación periódica de tareas vencidas (por defecto cada 60 minutos)."""
        try:
            # Llamar a la comprobación
            self.comprobar_tareas_vencidas()
            # Reprogramar
            self.after(intervalo_ms, lambda: self.programar_chequeo_tareas(intervalo_ms))
        except Exception as e:
            logger.error(f"Error programando chequeo tareas: {e}", exc_info=True)

if __name__ == "__main__":
    # Solo verificar base de datos local si no estamos usando Turso
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not (turso_url and turso_token):
        # Solo validar archivo local si no hay configuración de Turso
        if not os.path.exists(DB_NAME):
            print("🚨 Error Crítico: No se encuentra el archivo de base de datos 'rma_app.db'.")
            print("Asegúrate de ejecutar primero 'python db_setup.py'.")
            sys.exit(1)
    else:
        print("🌩️ Usando base de datos Turso cloud")
    
    # Mostrar un splash/spinner de arranque y ejecutar optimize_database en background
    try:
        print("🔧 Iniciando: splash de arranque y optimización en segundo plano...")

        # Nota: no aplicamos aquí el tema del usuario para evitar recargas visuales.
        # Los ajustes de tema se mantienen desactivados por ahora porque los colores
        # están fijados en el theme y la aplicación provocaba una doble renderización.

        # Crear ventana splash simple (tkinter, sin bordes)
        splash = tk.Tk()
        splash.overrideredirect(True)
        splash.configure(bg="white")
        w, h = 420, 140
        sw = splash.winfo_screenwidth()
        sh = splash.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(splash, bg="white")
        frame.pack(fill="both", expand=True)

        label = tk.Label(frame, text="Iniciando Gestor RMA - Expedientes", font=("Segoe UI", 12, "bold"), bg="white")
        label.pack(pady=(20, 6))

        sub = tk.Label(frame, text="Preparando la aplicación...", font=("Segoe UI", 10), bg="white", wraplength=380, justify="left")
        sub.pack(pady=(0, 10))

        try:
            pb = ttk.Progressbar(frame, mode="indeterminate", length=340)
            pb.pack(pady=(0, 12))
            pb.start(12)
        except Exception:
            pb = None

        # Verificar tipo de BD
        import time
        if turso_url and turso_token:
            try:
                sub.config(text="🌩️ Usando base de datos Turso cloud")
                splash.update()
            except Exception:
                pass
            time.sleep(0.3)
        else:
            try:
                sub.config(text="💾 Usando base de datos local SQLite")
                splash.update()
            except Exception:
                pass
            time.sleep(0.3)
        
        # Verificar conexión a Backblaze B2
        try:
            sub.config(text="Verificando conexión a Backblaze B2...")
            splash.update()
        except Exception:
            pass
        
        # La verificación de B2 se hará cuando se use por primera vez
        # mediante la función usar_b2() que cachea la conexión
        
        try:
            sub.config(text="Configuración de almacenamiento lista")
            splash.update()
        except Exception:
            pass
        time.sleep(0.3)
        
        # Iniciar optimización en un hilo daemon
        t = threading.Thread(target=optimize_database, daemon=True)
        t.start()

        # Mostrar mensajes por etapas mientras la optimización corre
        try:
            while t.is_alive():
                # Mostrar etapa de optimización
                try:
                    sub.config(text="🔧 Optimizando la base de datos...")
                except Exception:
                    pass
                try:
                    splash.update()
                except Exception:
                    pass
                time.sleep(0.05)

            # Una vez terminado, indicar carga de la interfaz
            try:
                sub.config(text="✨ Cargando interfaz...")
                splash.update()
            except Exception:
                pass

            # Pequeña pausa para que el usuario vea el estado final
            time.sleep(0.25)

        except KeyboardInterrupt:
            # Permitir salir con Ctrl-C si se interrumpe
            pass

        # Cerramos el splash ANTES de crear la ventana principal para evitar conflictos
        try:
            if pb:
                pb.stop()
        except Exception:
            pass
        try:
            splash.destroy()
        except Exception:
            pass

        # Crear la aplicación principal (ahora que la optimización ha finalizado)
        app = LoginApp()
        app.mainloop()

    except Exception:
        # Si algo falla en el splash, fallback al comportamiento previo
        print("🔧 Optimizando base de datos en segundo plano...")
        t = threading.Thread(target=optimize_database, daemon=True)
        t.start()
        app = LoginApp()
        app.mainloop()
