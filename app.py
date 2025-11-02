import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import Toplevel
import sqlite3
import os
try:
    # Carga variables de entorno desde .env si existe (opcional)
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass
import bcrypt
import sys
import os 
import datetime
import webbrowser
import docx
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
from PIL import Image, ImageTk
#from tkcalendar import Calendar
from CTkDatePicker import CTkDatePicker

import tkinter as tk

import pandas as pd
import locale
import shutil # Para copiar archivos
import tkinter.filedialog as filedialog # Para el diálogo de selección de archivos
import subprocess # Para abrir archivos en diferentes OS
# Notificaciones nativas (Windows)
try:
    from win10toast import ToastNotifier
except Exception:
    ToastNotifier = None

# Módulo para rellenado de PDFs
try:
    from lib.pdf_fill import fill_pdf_for_rma, get_pdf_field_names
except Exception:
    # Si no está instalado/ disponible aún, seguiremos sin la funcionalidad
    fill_pdf_for_rma = None
    get_pdf_field_names = None

# Definición de las variables globales de la base de datos
DB_NAME = "rma_app.db"
# Mensaje de advertencia sobre la limitación de SQLite en red compartida
ADVERTENCIA_MULTIUSUARIO = "⚠️ ADVERTENCIA: Esta app usa SQLite, NO es segura para múltiples usuarios escribiendo a la vez en red compartida. ¡Riesgo de corrupción de datos si escriben a la vez!"

APP_VERSION = "v0.0.56"
DB_FILENAME = "rma_app.db"

# Session global para Turso (reutiliza conexiones HTTP)
_turso_session = None

# Caché simple para consultas frecuentes (estados, etc.)
_query_cache = {}
_cache_timeout = 300  # 5 minutos

def _get_turso_session():
    """Obtiene o crea una sesión HTTP persistente para Turso"""
    global _turso_session
    if _turso_session is None:
        import requests
        _turso_session = requests.Session()
        _turso_session.headers.update({
            "Content-Type": "application/json"
        })
    return _turso_session

def _get_cached_query(cache_key, query_func, ttl=None):
    """Sistema de caché para queries frecuentes (estados, usuarios, etc.)"""
    import time
    global _query_cache
    
    if ttl is None:
        ttl = _cache_timeout
    
    now = time.time()
    
    # Verificar si existe en caché y no ha expirado
    if cache_key in _query_cache:
        cached_data, timestamp = _query_cache[cache_key]
        if now - timestamp < ttl:
            return cached_data
    
    # Si no está en caché o expiró, ejecutar query y guardar
    result = query_func()
    _query_cache[cache_key] = (result, now)
    return result

def invalidate_cache(pattern=None):
    """Invalida caché completo o por patrón"""
    global _query_cache
    if pattern is None:
        _query_cache.clear()
    else:
        keys_to_delete = [k for k in _query_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _query_cache[key]

# --- Conector unificado: Turso (libSQL) si hay credenciales, si no SQLite local ---
def connect_db(timeout: float | None = None):
    """Devuelve una conexión a la BD.
    - Si existen TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en el entorno, usa Turso (libSQL).
    - En caso contrario, usa SQLite local (rma_app.db).
    El API devuelto implementa DB-API 2.0 (cursor/execute/commit).
    """
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    if turso_url and turso_token:
        try:
            import requests
            import json

            class TursoCursor:
                def __init__(self, url: str, token: str, connection=None):
                    self._url = url
                    self._token = token
                    self._connection = connection
                    self._result = None
                    self.lastrowid = None
                    self.rowcount = -1
                    self._fetch_idx = 0
                    self.description = None  # DB-API 2.0: lista de tuplas con info de columnas

                def execute(self, sql: str, params: tuple | list | None = None):
                    # Convertir placeholders ? a args posicionales para Turso
                    if params:
                        # Turso espera args como lista de objetos con {type, value}
                        args = [{"type": "text", "value": str(v)} for v in params]
                    else:
                        args = []
                    
                    # Usar session persistente para mejor rendimiento
                    session = _get_turso_session()
                    
                    # Hacer request a la API REST de Turso (v2/pipeline format)
                    response = session.post(
                        self._url,
                        headers={
                            "Authorization": f"Bearer {self._token}"
                        },
                        json={"requests": [{"type": "execute", "stmt": {"sql": sql, "args": args}}]},
                        timeout=10  # Timeout de 10 segundos
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Turso API error: {response.status_code} - {response.text}")
                    
                    data = response.json()
                    results = data.get("results", [])
                    if results and len(results) > 0:
                        result = results[0].get("response", {}).get("result", {})
                        self._result = result
                    else:
                        self._result = {"rows": []}
                    
                    # Extraer metadatos
                    self.lastrowid = self._result.get("last_insert_rowid")
                    self.rowcount = self._result.get("rows_affected", -1)
                    
                    # Construir description según DB-API 2.0
                    # Formato: (name, type_code, display_size, internal_size, precision, scale, null_ok)
                    cols = self._result.get("cols", [])
                    if cols:
                        self.description = [
                            (col.get("name"), None, None, None, None, None, None)
                            for col in cols
                        ]
                    else:
                        self.description = None
                    
                    self._fetch_idx = 0
                    return self
                
                def executemany(self, sql: str, params_list: list):
                    """Ejecuta múltiples queries en un solo batch (mucho más rápido)"""
                    if not params_list:
                        return self
                    
                    # Construir batch de requests para pipeline
                    requests_batch = []
                    for params in params_list:
                        if params:
                            args = [{"type": "text", "value": str(v)} for v in params]
                        else:
                            args = []
                        requests_batch.append({
                            "type": "execute",
                            "stmt": {"sql": sql, "args": args}
                        })
                    
                    session = _get_turso_session()
                    response = session.post(
                        self._url,
                        headers={
                            "Authorization": f"Bearer {self._token}"
                        },
                        json={"requests": requests_batch},
                        timeout=30  # Timeout mayor para batch
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Turso API error: {response.status_code} - {response.text}")
                    
                    # Para executemany, solo guardamos el último resultado
                    data = response.json()
                    results = data.get("results", [])
                    if results and len(results) > 0:
                        last_result = results[-1].get("response", {}).get("result", {})
                        self._result = last_result
                        self.lastrowid = last_result.get("last_insert_rowid")
                        self.rowcount = sum(
                            r.get("response", {}).get("result", {}).get("rows_affected", 0)
                            for r in results
                        )
                    
                    return self

                def fetchall(self):
                    if not self._result:
                        return []
                    rows = self._result.get("rows", [])
                    # Turso devuelve cada fila como lista de objetos {"type": ..., "value": ...}
                    # Necesitamos extraer solo los valores
                    result_rows = []
                    for row in rows:
                        if isinstance(row, list):
                            # Extraer valores de cada celda
                            values = []
                            for cell in row:
                                if isinstance(cell, dict):
                                    values.append(cell.get("value"))
                                else:
                                    values.append(cell)
                            result_rows.append(tuple(values))
                        else:
                            result_rows.append(tuple(row))
                    return result_rows

                def fetchone(self):
                    rows = self.fetchall()
                    if self._fetch_idx < len(rows):
                        row = rows[self._fetch_idx]
                        self._fetch_idx += 1
                        return row
                    return None

            class TursoConnection:
                def __init__(self, url: str, token: str):
                    self._url = url
                    self._token = token

                def cursor(self):
                    return TursoCursor(self._url, self._token, connection=self)

                def commit(self):
                    # No-op: Turso auto-commits
                    pass

                def close(self):
                    # No cerramos la session para que se reutilice entre conexiones
                    # La session se mantendrá viva durante toda la ejecución de la app
                    pass

            # Convertir URL: libsql://xxx o wss://xxx -> https://xxx
            api_url = turso_url.replace("libsql://", "https://").replace("wss://", "https://")
            if not api_url.endswith("/"):
                api_url += "/"
            api_url += "v2/pipeline"
            
            return TursoConnection(api_url, turso_token)
        except Exception as e:
            # Si falla, caer a SQLite local con log sencillo
            print("[WARN] No se pudo conectar a Turso (libSQL HTTP). Usando SQLite local. Causa:", e)
            return sqlite3.connect(DB_NAME, timeout=timeout if timeout is not None else 5)
    # Fallback por defecto: SQLite local
    return sqlite3.connect(DB_NAME, timeout=timeout if timeout is not None else 5)

def optimize_database():
    """Crea índices en la base de datos para mejorar el rendimiento de consultas"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Índices para búsquedas frecuentes en rma_maestro
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_rma_codigo ON rma_maestro(codigo_rma)",
            "CREATE INDEX IF NOT EXISTS idx_rma_cliente ON rma_maestro(cliente)",
            "CREATE INDEX IF NOT EXISTS idx_rma_estado ON rma_maestro(estado)",
            "CREATE INDEX IF NOT EXISTS idx_rma_doc_cliente ON rma_maestro(numero_documento_cliente)",
            "CREATE INDEX IF NOT EXISTS idx_rma_fecha ON rma_maestro(fecha_emision)",
            # Índices para rma_detalles
            "CREATE INDEX IF NOT EXISTS idx_detalle_rma_id ON rma_detalles(rma_id)",
            # Índices para rma_historial
            "CREATE INDEX IF NOT EXISTS idx_historial_rma_id ON rma_historial(rma_id)",
            # Índices para rma_adjuntos
            "CREATE INDEX IF NOT EXISTS idx_adjuntos_rma_id ON rma_adjuntos(rma_id)",
        ]
        
        for idx_sql in indices:
            try:
                cursor.execute(idx_sql)
            except Exception as e:
                # Algunos índices pueden fallar en Turso, continuar
                print(f"Info: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Índices de base de datos optimizados")
    except Exception as e:
        print(f"Error al crear índices: {e}")

# --- NUEVA VARIABLE GLOBAL ---
ADJUNTOS_ROOT_DIR = "Adjuntos_RMA" # Carpeta principal para guardar todos los archivos adjuntos
# -----------------------------
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
        self.geometry("400x300")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("light") 
        ctk.set_default_color_theme("themes/rime.json")

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
            return None

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
        
        self.withdraw() # Ocultamos la ventana de login
        
        if not hasattr(self, 'ventana_principal') or not self.ventana_principal.winfo_exists():
            self.ventana_principal = VentanaPrincipal(self, username, rol)
        
        print(ADVERTENCIA_MULTIUSUARIO) 

# ----------------------------------------------------------------------
# 2. CLASE DE LA VENTANA PRINCIPAL DE LA APLICACIÓN
# ----------------------------------------------------------------------

class VentanaPrincipal(ctk.CTkToplevel):
    """Ventana principal que gestiona el listado, creación y edición de RMAs."""
    
    # Opciones predefinidas para desplegables
    OPCIONES = {
        "Autorizacion": ["SI", "NO"],
        "Autorizado_Por": ["RAQUEL", "SILVIA", "CARLOS", "IVAN", "ANDRES"],
        "Gestionado_Por": ["RAQUEL", "SILVIA", "CARLOS", "IVAN", "ANDRES"],
        "Resultado_Expediente": ["", "ABONAR", "NO ABONAR", "REPOSICION"],
        "Estado_Producto": [
            "", "EN PERFECTO ESTADO ; ABONAR", "FUNCIONA PERFECTAMENTE ; ABONAR", "SOBRANTE DE OBRA ; ABONAR", "NO FUNCIONA, ABONAR", "FUNCIONA PERFECTAMENTE ; NO ABONAR",
            "NO FUNCIONA ; NO ABONAR", "REPOSICION FALLO PRODUCTO", "REPOSICION ; ABONAR", "MERCANCIA ENVIADA POR ERROR", "MALA MANIPULACION ; NO ABONAR",
            "EN PERFECTO ESTADO ; ABONAR 10% DEPRECIACION", "FALLO SOLDADURA ; ABONAR", "FALLO SOLDADURA ; NO ABONAR", "FALLO MODULO ; ABONAR", "MAL MANIPULACION ; ABONAR",
            "DANA", "CAMBIO DE PRODUCTO"
        ]
    }
    
    def __init__(self, master, username, rol):
        super().__init__(master)
        self.master = master
        self.username = username
        self.rol = rol
        try:
            self.toaster = ToastNotifier() if ToastNotifier else None
        except Exception:
            self.toaster = None
        
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
        
        self.crear_diseno()
        # Iniciar comprobación periódica de tareas (notificaciones para el creador)
        try:
            self.programar_chequeo_tareas()
        except Exception:
            pass

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
                        print(f"✅ Columna '{col_name}' añadida a rma_maestro.")
                    except Exception as e:
                        print(f"Error al añadir columna '{col_name}': {e}")

            conn.commit()

        except Exception as e:
            print(f"Error comprobando/añadiendo columnas en rma_maestro: {e}")
        finally:
            conn.close()
    
    
    def cerrar_app(self):
        """Maneja el cierre de la ventana principal y de toda la app."""
        self.master.destroy()

    def limpiar_contenido(self):
        """Limpia todos los widgets del marco de contenido principal."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def crear_diseno(self):
        """Define la estructura principal con un panel lateral y un área de contenido."""
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Panel Lateral de Navegación (Columna 0) ---
        self.sidebar_frame = ctk.CTkFrame(self, 
                                          width=140, 
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
        #ctk.CTkLabel(self.sidebar_frame, text="MENÚ", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
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

        # Botón de gestión de usuarios (solo visible para administradores)
        if str(self.rol).strip().lower() in ("admin", "administrador"):
            self.btn_usuarios = ctk.CTkButton(self.sidebar_frame,
                                             text="👥 Gestión Usuarios",
                                             command=self.mostrar_gestion_usuarios,
                                             font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
            self.btn_usuarios.grid(row=fila, column=0, padx=20, pady=10)
            fila += 1

        self.btn_lista = ctk.CTkButton(self.sidebar_frame,
                                       text="📋 Listado",
                                       command=self.mostrar_lista_rma,
                                       font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_lista.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        # Botón Artículos: abre ventana con listado de artículos y conteo de expedientes asociados
        self.btn_articulos = ctk.CTkButton(self.sidebar_frame,
                                           text="📦 Artículos",
                                           command=self.mostrar_articulos_window,
                                           font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_articulos.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        self.btn_estadisticas = ctk.CTkButton(self.sidebar_frame,
                                              text="📊 Filtrado",
                                              command=self.mostrar_ventana_estadisticas,
                                              font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_estadisticas.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        # Botón de Tareas (lista y creación de tareas por expediente)
        self.btn_tareas = ctk.CTkButton(self.sidebar_frame,
                                        text="🗒️ Tareas",
                                        command=self.mostrar_gestion_tareas,
                                        font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_tareas.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        # Botón Gestión RMP (Proveedores -> Expedientes)
        self.btn_gestion_rmp = ctk.CTkButton(self.sidebar_frame,
                                             text="🔁 Gestión RMP",
                                             command=self.mostrar_gestion_rmp,
                                             font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_gestion_rmp.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        self.btn_buscar = ctk.CTkButton(self.sidebar_frame,
                                        text="Backup BD",
                                        command=self.crear_copia_seguridad_db,
                                        font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_buscar.grid(row=fila, column=0, padx=20, pady=10)
        fila += 1

        self.btn_reportar = ctk.CTkButton(self.sidebar_frame,
                                          text="🐞 Reportar",
                                          command=self.mostrar_formulario_github,
                                          font=ctk.CTkFont(family="Verdana", size=14, weight="bold"))
        self.btn_reportar.grid(row=fila, column=0, padx=20, pady=10)
        
        # --- Contenido Principal (Columna 1) ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent") # 'transparent' para que herede el fondo 'Light' (blanco)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.mostrar_lista_rma()
    
    
    # ----------------------------------------------------------------------
    # 3. MÉTODOS AUXILIARES Y GENERACIÓN DE CÓDIGO RMA
    # ----------------------------------------------------------------------
    
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
        """Calcula el siguiente código RMA (Ej: RMA25001)."""
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
            widget.set_date_format("%Y-%m-%d")

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
    

    # ----------------------------------------------------------------------
    # 4. LÓGICA DE LISTADO DE RMAS
    # ----------------------------------------------------------------------

    def mostrar_lista_rma(self):
        """Muestra el listado completo de RMAs, filtros y el botón de crear nuevo RMA."""
        self.limpiar_contenido()
        
        # 0. Configurar la expansión para el listado (fila 2, ahora)
        self.content_frame.grid_rowconfigure(0, weight=0) # Título
        self.content_frame.grid_rowconfigure(1, weight=0) # Filtros
        self.content_frame.grid_rowconfigure(2, weight=1) # Listado

        # 1. Título y Botón Crear (Fila 0)
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_frame, text="LISTADO", font=ctk.CTkFont(family="Verdana", size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(title_frame,
                      text="➕ Crear Nuevo RMA",
                      #fg_color="gray80",        # Fondo del botón: Gris claro
                      #hover_color="gray70",     # Efecto hover: Ligeramente más oscuro
                      #text_color="black",
                      command=lambda: self.mostrar_nuevo_rma(rma_id=None)).grid(row=0, column=1, padx=(20, 0), sticky="e")

        # ----------------------------------------------------
        # 2. NUEVO: Panel de Búsqueda y Filtros (Fila 1)
        # ----------------------------------------------------
        filtro_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        filtro_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # 2a. Búsqueda por texto (Código RMA / Cliente / Documento Cliente)
        ctk.CTkLabel(filtro_frame, text="Buscar:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.entry_busqueda = ctk.CTkEntry(filtro_frame, placeholder_text="Código RMA, Cliente o Doc.", width=250)
        self.entry_busqueda.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # 2b. Filtro por Estado
        estados_posibles = self.OPCIONES.get("Estado", ["Todos"])
        if "Todos" not in estados_posibles:
            estados_posibles.insert(0, "Todos")
        # Asegurarnos de que el estado 'Exportado' esté disponible como opción de filtro
        if 'Exportado' not in estados_posibles:
            estados_posibles.append('Exportado')
            
        ctk.CTkLabel(filtro_frame, text="Estado:").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        self.filtro_estado = ctk.CTkOptionMenu(filtro_frame, 
                                               values=estados_posibles, 
                                               width=200,
                                               #fg_color="gray80",        # Color del botón principal
                                               #button_color="gray70",    # Color del botón de flecha
                                               #button_hover_color="gray60", # Color al pasar el ratón por el botón de flecha
                                               #text_color="black"
                                               )
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=0, column=3, padx=10, pady=5, sticky="w")
        
        # 2c. Botón de Aplicar Filtro
        # Ahora el botón llama a la función que aplica los filtros
        btn_aplicar_filtro = ctk.CTkButton(filtro_frame,
                                           text="🔍 Aplicar Filtros", 
                                           command=self.aplicar_filtros_rma,
                                           #fg_color="gray80",      # Fondo del botón: Gris claro
                                           #hover_color="gray70",   # Color al pasar el ratón: Ligeramente más oscuro
                                           #text_color="black"
                                           )
        btn_aplicar_filtro.grid(row=0, column=4, padx=(20, 0), pady=5, sticky="w")
        
        # Configurar expansión para que el campo de búsqueda ocupe el espacio extra
        filtro_frame.grid_columnconfigure(1, weight=1) 
        # ----------------------------------------------------

        # 3. Listado de RMAs (Fila 2)
        # RENOMBRAR la referencia de list_scroll_frame a self.lista_rma_frame
        self.lista_rma_frame = ctk.CTkScrollableFrame(self.content_frame, label_text="Haga click en 'Editar' para ver los detalles de un expediente.")
        self.lista_rma_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.lista_rma_frame.grid_columnconfigure(0, weight=1) # Columna del listado se expande
        
        # 4. Cargar los datos iniciales
        self.cargar_lista_rma() # Llamada a la función de carga con filtros por defecto


    def cargar_lista_rma(self, texto_busqueda="", estado_filtro="Todos"):
        """
        Carga los estados únicos de la DB para el filtro, y luego carga los RMA 
        desde la DB aplicando los filtros (texto, estado).
        """
        
        # Limpiar el frame (siempre)
        for widget in self.lista_rma_frame.winfo_children():
            widget.destroy()

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
                    
            # 2. CARGAR LOS REGISTROS APLICANDO LOS FILTROS
            # (Aquí mantenemos tu lógica SQL que ya estaba funcionando)
            
            sql = "SELECT id, codigo_rma, cliente, numero_documento_cliente, fecha_emision, estado FROM rma_maestro WHERE 1=1"
            params = []
            
            # Aplicar filtro de ESTADO
            estado_filtro_actual = self.filtro_estado.get() # Usamos el valor que se ha configurado
            if estado_filtro_actual and estado_filtro_actual != "Todos":
                sql += " AND estado = ?"
                params.append(estado_filtro_actual)
                
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
                registros = cursor.fetchall()
            except Exception as e:
                print(f"Error ejecutando query principal: {e}")
                print(f"SQL: {sql}")
                print(f"Params: {params}")
                raise
            
            conn.close()

            # 3. Dibujar la tabla de resultados (Encabezados y Registros)
            
            # ... (código para dibujar encabezados y la tabla de registros, sigue igual) ...
            
            # Encabezados
            header_font = ctk.CTkFont(weight="bold")
            self.lista_rma_frame.grid_columnconfigure(1, weight=3)
            self.lista_rma_frame.grid_columnconfigure(2, weight=1) 
            ctk.CTkLabel(self.lista_rma_frame, text="CÓDIGO RMA", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(self.lista_rma_frame, text="CLIENTE", font=header_font).grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(self.lista_rma_frame, text="DOCUMENTO DE CLIENTE", font=header_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(self.lista_rma_frame, text="ESTADO", font=header_font).grid(row=0, column=3, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(self.lista_rma_frame, text="FECHA EMISIÓN", font=header_font).grid(row=0, column=4, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(self.lista_rma_frame, text="ACCIONES", font=header_font).grid(row=0, column=5, padx=5, pady=5, sticky="w") # Columna 5
            if not registros:
                ctk.CTkLabel(self.lista_rma_frame, text="No se encontraron expedientes con los filtros aplicados.", text_color="gray").grid(row=1, column=0, columnspan=5, padx=10, pady=20)
                return

            # Registros (filas cebra)
            colors = ("#FFFFFF", "#F3F4F6")
            for i, reg in enumerate(registros):
                rma_id, codigo_rma, cliente, numero_documento_cliente, fecha_emision, estado = reg
                row = i + 1

                # Mapeo de color según estado (para la etiqueta de estado)
                color = {"Pendiente de Autorizacion": "orange", "Autorizado": "blue", "Recibido": "purple", "Completado": "green"}.get(estado, "gray")

                bg = colors[i % 2]
                # Crear un frame por columna para alinear exactamente con los encabezados
                f0 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)
                f1 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)
                f2 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)
                f3 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)
                f4 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)
                f5 = ctk.CTkFrame(self.lista_rma_frame, fg_color=bg)

                # Colocar cada columna en la grilla principal para que se alinee con encabezados
                f0.grid(row=row, column=0, sticky="nsew", padx=0, pady=1)
                f1.grid(row=row, column=1, sticky="nsew", padx=0, pady=1)
                f2.grid(row=row, column=2, sticky="nsew", padx=0, pady=1)
                f3.grid(row=row, column=3, sticky="nsew", padx=0, pady=1)
                f4.grid(row=row, column=4, sticky="nsew", padx=0, pady=1)
                f5.grid(row=row, column=5, sticky="nsew", padx=0, pady=1)

                # Contenido de cada columna con padding reducido para filas más finas
                ctk.CTkLabel(f0, text=codigo_rma).pack(anchor="w", padx=4, pady=1)
                ctk.CTkLabel(f1, text=cliente).pack(anchor="w", padx=4, pady=1)
                ctk.CTkLabel(f2, text=numero_documento_cliente).pack(anchor="w", padx=4, pady=1)
                ctk.CTkLabel(f3, text=estado, text_color=color).pack(anchor="w", padx=4, pady=1)
                ctk.CTkLabel(f4, text=fecha_emision).pack(anchor="w", padx=4, pady=1)
                ctk.CTkButton(f5, text="✏️ Editar", width=80, command=lambda r=rma_id: self.mostrar_nuevo_rma(rma_id=r)).pack(anchor="w", padx=4, pady=1)

                # Hover efectos para toda la fila: aplicar a cada columna
                cols = [f0, f1, f2, f3, f4, f5]
                def _on_enter(e, cols=cols):
                    for rf in cols:
                        try:
                            rf.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                        except Exception:
                            pass
                def _on_leave(e, cols=cols, original=bg):
                    for rf in cols:
                        try:
                            rf.configure(fg_color=original)
                        except Exception:
                            pass

                for rf in cols:
                    rf.bind("<Enter>", _on_enter)
                    rf.bind("<Leave>", _on_leave)
            
        except Exception as e:
            print(f"Error al cargar lista de RMA: {e}")
            if conn: conn.close()
            ctk.CTkLabel(self.lista_rma_frame, text=f"Error al cargar la lista: {e}").grid(row=1, column=0, columnspan=5, padx=10, pady=20)

    def crear_copia_seguridad_db(self):
        """
        Crea una copia de seguridad completa de la base de datos principal
        usando el diálogo 'Guardar como' para que el usuario elija la ubicación.
        La base de datos se asume en la carpeta actual: rma_app.db.
        """
        
        # 1. Determinar la ruta de origen de la BD
        try:
            # Usamos os.getcwd() para obtener la ruta del directorio de trabajo actual
            # y os.path.join para construir la ruta completa de la base de datos.
            db_path_origen = os.path.join(os.getcwd(), DB_FILENAME)
            
            # Opcional: una verificación rápida para ver si el archivo existe
            if not os.path.exists(db_path_origen):
                messagebox.showerror(
                    "Error de Archivo", 
                    f"No se encontró la base de datos en la ruta esperada: {db_path_origen}\n"
                    "Asegúrate de que el archivo '{DB_FILENAME}' está en la misma carpeta."
                )
                return

        except Exception as e:
            messagebox.showerror("Error de Ruta", f"No se pudo determinar la ruta de la base de datos: {e}")
            return

        # 2. Generar un nombre de archivo sugerido con fecha y hora
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_sugerido = f"backup_rma_app_{fecha_actual}.db"

        # 3. Abrir el diálogo para que el usuario seleccione la ruta de destino
        path_destino = filedialog.asksaveasfilename(
            defaultextension=".db", 
            filetypes=[
                ("Base de Datos SQLite", "*.db"), 
                ("Base de Datos SQLite", "*.sqlite"),
                ("Todos los archivos", "*.*")
            ],
            initialfile=nombre_sugerido,
            title="Guardar Copia de Seguridad de la Base de Datos"
        )

        if not path_destino:
            # El usuario canceló el diálogo
            return

        # 4. Realizar la copia de seguridad
        conn_origen = None
        conn_destino = None
        # Registro de operaciones para mostrar al final
        operations_log: list[str] = []

        def show_log_window(lines: list[str], title: str = "Registro de Copia de Seguridad"):
            """Muestra una ventana Toplevel con el log de operaciones."""
            try:
                win = ctk.CTkToplevel(self)
                win.title(title)
                win.geometry("700x400")
                win.grab_set()

                frame = ctk.CTkFrame(win)
                frame.pack(fill="both", expand=True, padx=10, pady=10)

                txt = ctk.CTkTextbox(frame, wrap="word")
                txt.pack(fill="both", expand=True)
                txt.configure(state="normal")
                txt.delete("1.0", "end")
                txt.insert("1.0", "\n".join(lines))
                txt.configure(state="disabled")

                btn_close = ctk.CTkButton(win, text="Cerrar", command=win.destroy)
                btn_close.pack(pady=8)
            except Exception:
                # Fallback simple si CustomTk no funciona por alguna razón
                try:
                    messagebox.showinfo(title, "\n".join(lines))
                except Exception:
                    print("Log:\n" + "\n".join(lines))

        # Si están definidas las variables de Turso, intentamos volcar la BD remota
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")

        if turso_url and turso_token:
            try:
                operations_log.append(f"Intentando volcar Turso: {turso_url}")
                # Conectamos a la BD (esto usará la implementación Turso si las env vars están)
                remote_conn = connect_db(timeout=30)
                remote_cursor = remote_conn.cursor()

                # Obtenemos los CREATE TABLE de la BD remota (evitar tablas internas sqlite_)
                remote_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tablas = remote_cursor.fetchall()

                # Crear la BD destino local y recrear tablas
                conn_destino = sqlite3.connect(path_destino)
                dest_cur = conn_destino.cursor()

                for tabla in tablas:
                    if len(tabla) < 2:
                        continue
                    nombre, create_sql = tabla[0], tabla[1]
                    if not create_sql:
                        continue
                    try:
                        dest_cur.execute(create_sql)
                        operations_log.append(f"CREATE TABLE ejecutado para: {nombre}")
                    except Exception:
                        # Si falla crear la tabla (por compatibilidad), intentar skip
                        operations_log.append(f"Advertencia: no se pudo crear tabla {nombre} (se omite)")
                        pass

                    # Copiar los datos de la tabla en bloques para no consumir mucha memoria
                    try:
                        chunk_size = 1000

                        # Intentar obtener el total de filas para poder mostrar progreso
                        total_rows = None
                        try:
                            remote_cursor.execute(f"SELECT COUNT(*) FROM \"{nombre}\"")
                            cnt = remote_cursor.fetchone()
                            total_rows = int(cnt[0]) if cnt and cnt[0] is not None else 0
                        except Exception:
                            # Si COUNT falla por permisos o particularidades, seguiremos sin total
                            total_rows = None

                        if total_rows == 0:
                            operations_log.append(f"Tabla {nombre}: 0 filas (omitida)")
                            continue

                        offset = 0
                        copied = 0
                        insert_sql = None

                        while True:
                            # Leer por bloques usando LIMIT/OFFSET
                            remote_cursor.execute(f"SELECT * FROM \"{nombre}\" LIMIT {chunk_size} OFFSET {offset}")
                            rows = remote_cursor.fetchall()
                            if not rows:
                                break

                            # Preparar placeholders la primera vez que tengamos descripción
                            if insert_sql is None:
                                colcount = len(remote_cursor.description) if remote_cursor.description else 0
                                placeholders = ",".join(["?" for _ in range(colcount)])
                                insert_sql = f"INSERT INTO \"{nombre}\" VALUES ({placeholders})"

                            # Insertar bloque en la DB destino
                            try:
                                dest_cur.executemany(insert_sql, rows)
                                conn_destino.commit()
                                copied += len(rows)
                                offset += len(rows)
                                if total_rows is None:
                                    operations_log.append(f"Tabla {nombre}: {copied} filas copiadas (progreso por bloques)")
                                else:
                                    operations_log.append(f"Tabla {nombre}: {copied}/{total_rows} filas copiadas")
                            except Exception:
                                conn_destino.rollback()
                                operations_log.append(f"Error insertando bloque en tabla {nombre} (omitida)")
                                # Saltar a la siguiente tabla
                                break

                        if copied > 0:
                            operations_log.append(f"Tabla {nombre}: copia finalizada, {copied} filas copiadas")
                        else:
                            operations_log.append(f"Tabla {nombre}: ninguna fila copiada")
                    except Exception as e:
                        # Ignorar errores de copia de datos de tablas concretas
                        try:
                            conn_destino.rollback()
                        except Exception:
                            pass
                        operations_log.append(f"Error copiando datos de tabla {nombre} (omitida): {e}")
                        continue

                # Cerrar conexión remota si existe
                try:
                    remote_conn.close()
                except Exception:
                    pass

                operations_log.append(f"Copia de Turso completada correctamente en: {path_destino}")
                # Mostrar log detallado al usuario
                show_log_window(operations_log, title="Registro de copia (Turso)")
                return

            except Exception as e:
                # Si falla el volcado remoto, registramos y caeremos al backup local
                operations_log.append(f"Info: no se pudo volcar Turso directamente: {e}")
                try:
                    remote_conn.close()
                except Exception:
                    pass

        # Si no hay Turso o el volcado falló, intentamos el backup local tradicional
        try:
            # 4.1. Conectar a la base de datos de origen (solo lectura)
            if not os.path.exists(db_path_origen):
                raise FileNotFoundError(f"Archivo de BD local no encontrado: {db_path_origen}")

            conn_origen = sqlite3.connect(db_path_origen)
            # 4.2. Conectar a la base de datos de destino (se crea si no existe)
            conn_destino = sqlite3.connect(path_destino)

            # 4.3. Usar el método de backup integrado de SQLite
            with conn_destino:
                conn_origen.backup(conn_destino)

            operations_log.append(f"Copia local realizada correctamente en: {path_destino}")
            show_log_window(operations_log, title="Registro de copia (local)")

        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Ocurrió un error al crear la copia de seguridad: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            if conn_origen:
                conn_origen.close()
            if conn_destino:
                conn_destino.close()


    # ----------------------------------------------------------------------
    # 5. LÓGICA DE FORMULARIO (CREAR/EDITAR)
    # ----------------------------------------------------------------------

    def mostrar_nuevo_rma(self, rma_id=None):
        """Muestra el formulario para crear (rma_id=None) o editar (rma_id=ID) un RMA."""
        self.limpiar_contenido()
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
        titulo_texto = "EDITAR EXPEDIENTE" if es_edicion else "CREAR NUEVO EXPEDIENTE"
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # 🛠️ 1. AJUSTE DE PESO: Fila 0 (Cabecera Principal)
        self.content_frame.grid_rowconfigure(0, weight=0) # No se expande
        # --------------------------------------------------------------------------

        ctk.CTkLabel(header_frame, text=titulo_texto, font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        btn_volver = ctk.CTkButton(header_frame, 
                                   text="⬅️ Volver", 
                                   command=self.mostrar_lista_rma,
                                   #fg_color="gray80",        # Fondo del botón: Gris claro
                                   #hover_color="gray70",     # Efecto hover: Ligeramente más oscuro
                                   #text_color="black"
                                   )
        btn_volver.grid(row=0, column=1, padx=(20, 0), sticky="e")
        
        # --------------------------------------------------------------------------
        # 2. Fila Principal (Código RMA + Comentarios Fijos) (Fila 1)
        # --------------------------------------------------------------------------
        # Creamos un frame de control para la Fila 1
        fila1_control_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        fila1_control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Configuramos las columnas dentro de este frame: Col 0 es fija, Col 1 se expande
        fila1_control_frame.grid_columnconfigure(0, weight=0) # Fija para el código
        fila1_control_frame.grid_columnconfigure(1, weight=1) # Expansiva para los comentarios

        # A) NÚMERO DE EXPEDIENTE (Columna 0)
        if es_edicion:
            # Consultar el código RMA real desde la base de datos
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT codigo_rma FROM rma_maestro WHERE id = ?", (rma_id,))
            row = cur.fetchone()
            conn.close()
            codigo_rma_mostrar = row[0] if row else "(Desconocido)"
        else:
            codigo_rma_mostrar = self.obtener_siguiente_rma()
        self.lbl_codigo_rma = ctk.CTkLabel(fila1_control_frame, text=f"Nº EXPEDIENTE: {codigo_rma_mostrar}", 
                     font=ctk.CTkFont(size=18, weight="bold"), 
                     text_color="grey30")
        self.lbl_codigo_rma.grid(row=0, column=0, padx=10, pady=5, sticky="w") 
        
        
        # B) CAJA DE COMENTARIOS (Columna 1)
        comentarios_frame = ctk.CTkFrame(fila1_control_frame, fg_color="transparent") 
        # Cambiamos el contenedor a fila1_control_frame y lo ponemos en column=1
        comentarios_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        comentarios_frame.grid_columnconfigure(0, weight=1) 

        # Etiqueta
        ctk.CTkLabel(comentarios_frame, text="Comentarios (Guarde al momento con el botón ➕):", 
                     text_color="black",
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 0), sticky="nw")
        
        comentario_input_frame = ctk.CTkFrame(comentarios_frame, fg_color="transparent")
        comentario_input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 5))
        comentario_input_frame.grid_columnconfigure(0, weight=1) # El textbox se expande
        
        # 1. Textbox (con altura reducida) - va en la Columna 0 del nuevo frame
        self.textbox_comentarios = ctk.CTkTextbox(comentario_input_frame, 
                                                  height=40, # Altura compacta
                                                  #fg_color="gray95", 
                                                  #text_color="black",
                                                  wrap="word")
        self.textbox_comentarios.grid(row=0, column=0, sticky="ew")

        # 2. Botón de Guardar Comentario - va en la Columna 1 del nuevo frame
        ctk.CTkButton(comentario_input_frame, 
                      text="➕", 
                      width=40, 
                      #fg_color="gray70", 
                      #hover_color="gray60", 
                      #text_color="black", 
                      command=self.guardar_comentario_historial
                      ).grid(row=0, column=1, padx=(5, 0), sticky="e")
        
        # 🛠️ 2. AJUSTE DE PESO: Fila 1 (Código RMA y Status)
        self.content_frame.grid_rowconfigure(1, weight=0) # No se expande
        # --------------------------------------------------------------------------
        
       
        
        # 3. Vista con pestañas (Tabview) para el formulario y el historial
        self.tabview = ctk.CTkTabview(self.content_frame)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.content_frame.grid_rowconfigure(2, weight=1)

        # -----------------------------------------------------------
        # -- 1. PESTAÑAS PRINCIPALES DEL FORMULARIO (NUEVAS) --
        # -----------------------------------------------------------
        general_tab = self.tabview.add("📝 General")
        estados_fechas_tab = self.tabview.add("⏱️ Estados y Fechas")
        articulos_tab = self.tabview.add("📦 Artículos")
        contabilidad_tab = self.tabview.add("💰 Contabilidad")
        # Nueva pestaña para información técnica — por si en el futuro añadimos más campos técnicos
        info_tecnica_tab = self.tabview.add("🔧 Información Técnica")
        adjuntos_tab = self.tabview.add("📎 Adjuntos (Pendiente)")
        historial_tab = self.tabview.add("📜 Historial de Cambios")
        # Pestaña de Tareas por RMA (creación/edición desde la ficha del expediente)
        tareas_tab = self.tabview.add("🗒️ Tareas")
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
            dlg.geometry("400x300")
            dlg.grab_set()

            ctk.CTkLabel(dlg, text=f"RMA: {self.lbl_codigo_rma.cget('text').split(': ')[1]}").pack(pady=5)
            ctk.CTkLabel(dlg, text=f"Creador: {self.username}").pack(pady=5)

            ctk.CTkLabel(dlg, text="Título:").pack(pady=(10,0))
            titulo_entry = ctk.CTkEntry(dlg)
            titulo_entry.pack(padx=10, pady=5, fill='x')

            ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10,0))
            desc_text = tk.Text(dlg, height=5)
            desc_text.pack(padx=10, pady=5, fill='both', expand=True)

            ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5,0))
            fecha_entry = ctk.CTkEntry(dlg)
            fecha_entry.pack(padx=10, pady=5, fill='x')

            def confirmar_crear():
                titulo = titulo_entry.get().strip()
                descripcion = desc_text.get("1.0", "end").strip()
                fecha_v = fecha_entry.get().strip() or None
                codigo_rma = self.lbl_codigo_rma.cget('text').split(': ')[1]
                
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
                        "INSERT INTO tareas (codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por, creado_en, notificado) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                        (codigo_rma, titulo, descripcion, fecha_v, 'Pendiente', self.username, datetime.datetime.now().isoformat())
                    )
                    conn.commit()
                    
                    # Registrar en historial del RMA
                    cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
                    rma_row = cur.fetchone()
                    if rma_row:
                        rma_id = rma_row[0]
                        cur.execute("""
                            INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                            VALUES (?, ?, ?, ?)
                        """, (rma_id, datetime.datetime.now().isoformat(), self.username,
                             f"Nueva tarea creada: {titulo}"))
                        conn.commit()
                        conn.close()
                    
                    dlg.destroy()
                    # Recargar la lista e historial si corresponde
                    if hasattr(self, 'cargar_lista_tareas_rma'):
                        self.cargar_lista_tareas_rma()
                    if hasattr(self, 'refrescar_historial'):
                        self.refrescar_historial()
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
                dlg.geometry("420x360")
                dlg.grab_set()

                ctk.CTkLabel(dlg, text=f"ID: {task['id']} - RMA: {task['codigo_rma']}").pack(pady=5)
                ctk.CTkLabel(dlg, text="Título:").pack(pady=(10,0))
                titulo_entry = ctk.CTkEntry(dlg)
                titulo_entry.insert(0, task['titulo'])
                titulo_entry.pack(padx=10, pady=5, fill='x')

                ctk.CTkLabel(dlg, text="Descripción:").pack(pady=(10,0))
                desc_text = tk.Text(dlg, height=6)
                desc_text.insert('1.0', task['descripcion'] or '')
                desc_text.pack(padx=10, pady=5, fill='both', expand=True)

                ctk.CTkLabel(dlg, text="Fecha Vencimiento (YYYY-MM-DD):").pack(pady=(5,0))
                fecha_entry = ctk.CTkEntry(dlg)
                fecha_entry.insert(0, task.get('fecha_vencimiento') or '')
                fecha_entry.pack(padx=10, pady=5, fill='x')

                estado_var = ctk.StringVar(value=task.get('estado', 'Pendiente'))
                estado_opt = ctk.CTkOptionMenu(dlg, values=["Pendiente", "En Progreso", "Completado"], variable=estado_var)
                estado_opt.pack(pady=5)

                def guardar_edicion():
                    nuevo_titulo = titulo_entry.get().strip()
                    nueva_desc = desc_text.get('1.0', 'end').strip()
                    nueva_fecha = fecha_entry.get().strip() or None
                    nuevo_estado = estado_var.get()
                    try:
                        conn = connect_db()
                        cur = conn.cursor()
                        cur.execute("UPDATE tareas SET titulo = ?, descripcion = ?, fecha_vencimiento = ?, estado = ? WHERE id = ?",
                                    (nuevo_titulo, nueva_desc, nueva_fecha, nuevo_estado, task['id']))
                        conn.commit()
                        # Registrar en historial del RMA
                        try:
                            # Obtener el ID del RMA para el historial
                            cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (task['codigo_rma'],))
                            rma_row = cur.fetchone()
                            if rma_row:
                                rma_id = rma_row[0]
                                # Registrar el cambio en el historial
                                cur.execute("""
                                    INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                                    VALUES (?, ?, ?, ?)
                                """, (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     self.username, 
                                     f"Tarea ID {task['id']} editada - {task['titulo']} -> {nuevo_titulo} (Estado: {nuevo_estado})")
                                )
                                conn.commit()
                        except sqlite3.Error as e:
                            print(f"Error al registrar historial de tarea: {e}")
                        conn.close()
                        dlg.destroy()
                        self.cargar_lista_tareas_rma()
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

            ctk.CTkLabel(row, 
                        text=f"{task['titulo']} - Vence: {fecha_v or 'Sin fecha'} - Estado: {estado}",
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
                cur.execute("SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por FROM tareas WHERE codigo_rma = ? ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC", (codigo,))
                filas = cur.fetchall()
                conn.close()

                if not filas:
                    ctk.CTkLabel(self.tareas_list_frame, text="No hay tareas asociadas a este RMA.", text_color="gray").pack(pady=10)
                    return
                for tid, codigo_rma, titulo, desc, fecha_v, estado, creador in filas:
                    task = {'id': tid, 'codigo_rma': codigo_rma, 'titulo': titulo, 'descripcion': desc, 'fecha_vencimiento': fecha_v, 'estado': estado, 'creado_por': creador}
                    mostrar_tarea_row(task)
            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"Error cargando tareas: {e}")

        # Exponer la función para recarga externa
        self.cargar_lista_tareas_rma = cargar_lista_tareas_rma
        # Cargar las tareas si estamos en edición
        if es_edicion:
            self.cargar_lista_tareas_rma()
    # Nota: No recrear tareas_scroll aquí para evitar duplicados en la pestaña de Tareas.
            
        # -----------------------------------------------------------
        # -- 2. MOVER LLAMADAS A crear_campo A SUS NUEVOS FRAMES --
        # -----------------------------------------------------------
        
        # V A L O R E S  A U T O M Á T I C O S
        fecha_emision_valor = datetime.datetime.now().strftime("%Y-%m-%d")
        usuario_actual = self.username
        
        # A) PESTAÑA GENERAL
        # Campos de Cliente y Contacto - Cliente y Número de Documento son de solo lectura en modo edición
        self.crear_campo(general_frame, 0, "Cliente:", "Cliente", deshabilitado=es_edicion)
        self.crear_campo(general_frame, 1, "Núm. Doc. Cliente:", "Numero_Documento_Cliente", deshabilitado=es_edicion)
        self.crear_campo(general_frame, 2, "Persona de Contacto:", "Persona_de_Contacto")
        self.crear_campo(general_frame, 3, "Email de Contacto:", "Email_de_Contacto")
        self.crear_campo(general_frame, 4, "Autorización:", "Autorizacion", tipo="optionmenu", opciones=self.OPCIONES["Autorizacion"], valor_defecto="NO")
        self.crear_campo(general_frame, 5, "Motivo Devolucion:", "motivo")
        
        # Fechas y Creador (Solo lectura)
        self.crear_campo(general_frame, 6, "Fecha Emisión:", "Fecha_Emision", 
                         valor_defecto=fecha_emision_valor, deshabilitado=True)
        self.crear_campo(general_frame, 7, "Creado Por:", "Creado_Por", 
                         valor_defecto=usuario_actual, deshabilitado=True)


        # B) PESTAÑA ESTADOS Y FECHAS
        # Fechas de Autorización, Recepción, Proceso y Gestión
        fila_estados = 0
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Autorización:", "Fecha_Autorizacion"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Autorizado Por:", "Autorizado_Por", tipo="optionmenu", opciones=self.OPCIONES["Autorizado_Por"], valor_defecto=self.OPCIONES["Autorizado_Por"][0]); fila_estados += 1
        
        ctk.CTkLabel(estados_fechas_frame, text="--- RECEPCIÓN ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Recepción:", "Fecha_Recepcion"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Recepcionado Por:", "Recepcionado_Por"); fila_estados += 1
        
        ctk.CTkLabel(estados_fechas_frame, text="--- PROCESO ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Proceso:", "Fecha_Proceso"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Procesado Por:", "Procesado_Por"); fila_estados += 1
        
        ctk.CTkLabel(estados_fechas_frame, text="--- CIERRE/GESTIÓN ---", font=ctk.CTkFont(weight="bold")).grid(row=fila_estados, column=0, columnspan=2, pady=(10, 5), sticky="w"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha Gestión:", "Fecha_Gestion"); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Gestionado Por:", "Gestionado_Por", tipo="optionmenu", opciones=self.OPCIONES["Gestionado_Por"], valor_defecto=self.OPCIONES["Gestionado_Por"][0]); fila_estados += 1
        self.crear_campo(estados_fechas_frame, fila_estados, "Fecha para Factura:", "Fecha_para_factura", tipo="optionmenu", opciones=self.obtener_quincenas_futuras(), valor_defecto=self.obtener_quincenas_futuras()[0]); fila_estados += 1

        
        # C) PESTAÑA INFORMACIÓN TÉCNICA (campos técnicos)
        # Fila 0: RMA Proveedor (label cambiado a 'RMA Proveedor')
        self.crear_campo(info_tecnica_frame, 0, "RMA Proveedor:", "Rma_Proveedor")
        # Fila 1: Modelo
        self.crear_campo(info_tecnica_frame, 1, "Modelo:", "Modelo")
        # Fila 2: N. Serie
        self.crear_campo(info_tecnica_frame, 2, "N. Serie:", "N_Serie")
        # Fila 3: Ref. Proveedor
        self.crear_campo(info_tecnica_frame, 3, "Ref. Proveedor:", "Ref_Proveedor")
        # Fila 4: Observaciones Técnicas (caja de texto mayor)
        ctk.CTkLabel(info_tecnica_frame, text="Observaciones Técnicas:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_Obs_Tecnica = ctk.CTkTextbox(info_tecnica_frame, height=120, wrap="word")
        self.entry_Obs_Tecnica.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        # Botón para generar la Solicitud de RMA desde la plantilla PDF
        ctk.CTkButton(
            info_tecnica_frame,
            text="Generar Solicitud de RMA",
            command=self.autorrellena_pdf
        ).grid(row=5, column=1, padx=10, pady=(8, 12), sticky="e")

        # C) PESTAÑA ARTÍCULOS (Mantener la lógica de listado y añadir artículo)
        articulos_tab.grid_columnconfigure(0, weight=1)
        articulos_frame = ctk.CTkFrame(articulos_tab) # Este marco no necesita scroll, la lista interna sí
        articulos_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        articulos_frame.grid_columnconfigure(0, weight=1)
        articulos_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(articulos_frame, text="**DETALLE DE ARTÍCULOS**", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=6, pady=(10, 5), sticky="w")
        
        # 4. Entradas para añadir un nuevo artículo (Input Article Frame)
        input_articulo_frame = ctk.CTkFrame(articulos_frame)
        input_articulo_frame.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(5, 10))
        # ... (Mantener la definición de las entradas self.art_ref, self.art_cant_doc, etc.)
        # ... (NO TOCAR ESTA SECCIÓN, está bien como está, solo moverla)

        # Etiquetas
        ctk.CTkLabel(input_articulo_frame, text="Ref. Artículo", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(input_articulo_frame, text="Cant. Doc.", font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(input_articulo_frame, text="Cant. Entregada", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(input_articulo_frame, text="Estado", font=ctk.CTkFont(size=11)).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(input_articulo_frame, text="Precio Unitario", font=ctk.CTkFont(size=11)).grid(row=0, column=4, padx=5)
        
        # Entradas
        self.art_ref = ctk.CTkEntry(input_articulo_frame, width=150)
        self.art_ref.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        self.art_cant_doc = ctk.CTkEntry(input_articulo_frame, width=80)
        self.art_cant_doc.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.art_cant_entregada = ctk.CTkEntry(input_articulo_frame, width=80)
        self.art_cant_entregada.grid(row=1, column=2, padx=5, pady=2, sticky="ew")
        self.art_estado = ctk.CTkOptionMenu(input_articulo_frame, values=self.OPCIONES["Estado_Producto"], width=150)
        self.art_estado.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        self.art_precio = ctk.CTkEntry(input_articulo_frame, width=100)
        self.art_precio.grid(row=1, column=4, padx=5, pady=2, sticky="ew")

        # Botones de Acción de Artículos
        ctk.CTkButton(input_articulo_frame, 
                      text="➕", 
                      width=30,
                      #fg_color="gray70",        # Fondo del botón: Gris claro
                      #hover_color="gray60",     # Efecto hover: Ligeramente más oscuro
                      #text_color="black",                      
                      command=self.anadir_articulo).grid(row=1, column=5, padx=5, pady=2)
        
        # 5. Listado de Artículos ya añadidos
        self.articulos_list_frame = ctk.CTkFrame(articulos_frame)
        self.articulos_list_frame.grid(row=2, column=0, columnspan=6, sticky="ew", padx=10, pady=10)
        self.actualizar_listado_articulos()

        
        # D) PESTAÑA CONTABILIDAD
        fila_cont = 0
        self.crear_campo(contabilidad_frame, fila_cont, "Resultado Expediente:", "Resultado_Expediente", tipo="optionmenu", opciones=self.OPCIONES["Resultado_Expediente"], valor_defecto=self.OPCIONES["Resultado_Expediente"][0]); fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Número Albarán:", "Numero_Albaran"); fila_cont += 1
        self.crear_campo(contabilidad_frame, fila_cont, "Fecha Doc. Cliente:", "Fecha_Doc_Cliente"); fila_cont += 1
        
        # --- NUEVO CAMPO CALCULADO: PRECIO TOTAL ---
        ctk.CTkLabel(contabilidad_frame, text="------------------------------").grid(row=fila_cont, column=0, columnspan=2, pady=(10, 5), sticky="ew"); fila_cont += 1
        
        ctk.CTkLabel(contabilidad_frame, text="PRECIO TOTAL EXPEDIENTE:", font=ctk.CTkFont(weight="bold")).grid(row=fila_cont, column=0, padx=10, pady=5, sticky="w")
        
        # Creamos una etiqueta para mostrar el total y guardamos su referencia
        self.lbl_precio_total = ctk.CTkLabel(contabilidad_frame, text="0.00 €", font=ctk.CTkFont(size=16, weight="bold"), text_color="green")
        self.lbl_precio_total.grid(row=fila_cont, column=1, padx=10, pady=5, sticky="w")
        
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
        
        # 💡 CREAR UN FRAME PARA AGRUPAR LOS BOTONES DE ACCIÓN (Fila 3)
        btn_action_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_action_frame.grid(row=3, column=0, padx=20, pady=20, sticky="w")
        
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

        # 2. Botón de Guardar
        guardar_texto = "💾 ACTUALIZAR" if es_edicion else "💾 GUARDAR"
        guardar_button = ctk.CTkButton(
            btn_action_frame, 
            text=guardar_texto, 
            #fg_color="gray80",        # Fondo del botón: Gris claro
            #hover_color="gray70",     # Efecto hover: Ligeramente más oscuro
            #text_color="black",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.guardar_rma_placeholder
        )
        guardar_button.pack(side="left", padx=(0, 5))
        
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
    
    def anadir_articulo(self):
        """Añade una fila de artículo a la lista temporal."""
        try:
            referencia = self.art_ref.get()
            cant_doc = int(self.art_cant_doc.get() or 0)
            cant_entregada = int(self.art_cant_entregada.get() or 0)
            estado = self.art_estado.get()
            # Reemplazar comas por puntos para que float funcione
            precio_unitario = float(self.art_precio.get().replace(',', '.') or 0.0) 
        except ValueError:
            print("Error: Cantidad y Precio deben ser números.")
            return

        if not referencia:
            print("Error: La Referencia es obligatoria.")
            return

        nuevo_articulo = {
            "referencia_articulo": referencia,
            "cantidad_segun_documento": cant_doc,
            "cantidad_entregada": cant_entregada,
            "estado_producto": estado,
            "precio_unitario": precio_unitario
        }
        
        self.articulos_data.append(nuevo_articulo)
        self.actualizar_listado_articulos()
        self.limpiar_articulo()

    def limpiar_articulo(self):
        """Limpia los campos de entrada de un solo artículo."""
        self.art_ref.delete(0, ctk.END)
        self.art_cant_doc.delete(0, ctk.END)
        self.art_cant_entregada.delete(0, ctk.END)
        self.art_precio.delete(0, ctk.END)
        self.art_estado.set(self.OPCIONES["Estado_Producto"][0])

    def eliminar_articulo(self, index):
        """Elimina un artículo de la lista temporal y actualiza la vista."""
        if 0 <= index < len(self.articulos_data):
            self.articulos_data.pop(index)
            self.actualizar_listado_articulos()

    def actualizar_listado_articulos(self):
        """Redibuja la tabla con los artículos de la lista temporal."""
        for widget in self.articulos_list_frame.winfo_children():
            widget.destroy()
            
        if not self.articulos_data:
            ctk.CTkLabel(self.articulos_list_frame, text="No hay artículos asociados a este RMA.", text_color="gray").pack(pady=10)
            return
            
        header_frame = ctk.CTkFrame(self.articulos_list_frame)
        header_frame.pack(fill="x")
        cols = ["Ref. Artículo", "Cant. Doc.", "Cant. Entregada", "Estado", "Precio Unitario", "Acción"]
        weights = [2, 1, 1, 2, 1, 1]
        header_font = ctk.CTkFont(weight="bold", size=12)
        
        for i, col in enumerate(cols):
            ctk.CTkLabel(header_frame, text=col, font=header_font).grid(row=0, column=i, padx=5, pady=5, sticky="w")
            header_frame.grid_columnconfigure(i, weight=weights[i])

        for i, item in enumerate(self.articulos_data):
            row_frame = ctk.CTkFrame(self.articulos_list_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            # Configurar los mismos pesos de columna que el header
            for col_idx in range(len(weights)):
                row_frame.grid_columnconfigure(col_idx, weight=weights[col_idx])

            ctk.CTkLabel(row_frame, text=item["referencia_articulo"]).grid(row=0, column=0, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=item["cantidad_segun_documento"]).grid(row=0, column=1, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=item["cantidad_entregada"]).grid(row=0, column=2, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=item["estado_producto"]).grid(row=0, column=3, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=f"{item['precio_unitario']:.2f} €").grid(row=0, column=4, padx=5, pady=2, sticky="w")
            
            ctk.CTkButton(row_frame, text="X", width=30, fg_color="red", hover_color="darkred", 
                          command=lambda idx=i: self.eliminar_articulo(idx)).grid(row=0, column=5, padx=5, pady=2, sticky="w")
            
        # --- NUEVO: Calcular y actualizar el Precio Total en la etiqueta de Contabilidad ---
        precio_total = sum(item.get('cantidad_entregada', 0) * item.get('precio_unitario', 0.0) for item in self.articulos_data)
        
        # Esto es seguro porque lbl_precio_total se crea en mostrar_nuevo_rma
        if hasattr(self, 'lbl_precio_total'):
            self.lbl_precio_total.configure(text=f"{precio_total:.2f} €")


    def guardar_rma_placeholder(self):
        """Punto de entrada para guardar/actualizar."""
        if self.rma_actual_id is None:
            self.guardar_nuevo_rma()
        else:
            self.actualizar_rma()

    def guardar_nuevo_rma(self):
        """Valida los campos y realiza la inserción en rma_maestro y rma_detalles."""
        
        # 1. Recolección y Validación de campos obligatorios
        datos_maestro = {}
        campos_a_insertar = [
            'Cliente', 'Numero_Documento_Cliente', 'Persona_de_Contacto', 'Email_de_Contacto',
            'Autorizacion', 'Autorizado_Por', 'Fecha_Autorizacion', 'Fecha_Recepcion',
            'Recepcionado_Por', 'Fecha_Gestion', 'Gestionado_Por', 'Fecha_Proceso', 'Procesado_Por',
            'Fecha_para_factura', 'Numero_Albaran', 'Fecha_Doc_Cliente', 'Resultado_Expediente', 'motivo', 'Rma_Proveedor',
            'Modelo', 'N_Serie', 'Ref_Proveedor', 'Obs_Tecnica'
        ]
        
        for campo in campos_a_insertar:
            entry = getattr(self, f"entry_{campo}")
            # Obtener el valor según el tipo de widget
            try:
                if isinstance(entry, ctk.CTkTextbox):
                    valor = entry.get("1.0", "end-1c").strip()
                elif hasattr(entry, 'get'):
                    valor = entry.get()
                else:
                    valor = entry.cget("text")
            except Exception:
                # Fallback seguro
                try:
                    valor = entry.get()
                except Exception:
                    valor = ''
            
            # Validación de obligatorios
            if campo in ["Cliente", "Numero_Documento_Cliente", "Persona_de_Contacto", "Email_de_Contacto", "motivo"] and not valor:
                print(f"Error: El campo {campo.replace('_', ' ')} es obligatorio.")
                messagebox.showinfo("Advertencia", f"Error: El campo {campo.replace('_', ' ')} es obligatorio.")
                # Aquí deberías mostrar un mensaje de error en la interfaz
                return
            
            # Conversión especial para Autorizacion (SI/NO a 1/0)
            if campo == 'Autorizacion':
                datos_maestro[campo.lower()] = 1 if valor == "SI" else 0
            else:
                datos_maestro[campo.lower()] = valor

        # Campos automáticos/calculados
        datos_maestro['codigo_rma'] = self.lbl_codigo_rma.cget("text").split(": ")[1]
        datos_maestro['fecha_emision'] = self.entry_Fecha_Emision.get()
        datos_maestro['creado_por'] = self.entry_Creado_Por.get()
        
        # Definir estado inicial basado en Autorización
        # 1. INTEGRACIÓN DE LA TRAZABILIDAD
        datos_maestro['estado'] = self.determinar_estado_rma(datos_maestro)
        
        # 2. Calcular Precio Total y validar Artículos
        precio_total = sum(item['cantidad_entregada'] * item['precio_unitario'] for item in self.articulos_data)
        datos_maestro['precio_total_expediente'] = precio_total

        # 2.5 Validación: Numero de documento del cliente no debe repetirse
        # Se permiten repeticiones para los valores 'email' y 'telefonico'
        numero_doc = str(datos_maestro.get('numero_documento_cliente', '')).strip()
        if numero_doc:
            numero_doc_norm = numero_doc.lower()
            if numero_doc_norm not in ('email', 'telefonico'):
                # Conectar a la DB para comprobar duplicados
                conn_check, cursor_check = self.master.conectar_db()
                if not conn_check:
                    return
                try:
                    cursor_check = conn_check.cursor()
                    cursor_check.execute("SELECT COUNT(*) FROM rma_maestro WHERE lower(numero_documento_cliente) = ?", (numero_doc_norm,))
                    count = cursor_check.fetchone()[0]
                    if count and count > 0:
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

        # 3. Inserción en la Base de Datos
        conn, cursor = self.master.conectar_db()
        if not conn: return
        cursor = conn.cursor()
        
        try:
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
                print(f"✅ Detalles de {len(self.articulos_data)} artículos guardados (batch).")

            # 3c. Inserción en rma_historial (modificar descripción si no hay artículos)
            num_articulos = len(self.articulos_data)
            descripcion = f"RMA creado. Cliente: {datos_maestro['cliente']}. Artículos: {num_articulos}. Total: {precio_total:.2f} €"
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (rma_id_generado, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, descripcion))

            conn.commit()
            
            # Invalidar caché de estados (puede que se haya creado un nuevo estado)
            invalidate_cache('estados_rma')
            
            print(f"✅ RMA {datos_maestro['codigo_rma']} guardado exitosamente.")
            messagebox.showinfo("Expediente Guardado", "El expediente se ha guardado correctamente.")
            
            self.current_rma_id = rma_id_generado # Asigna el ID al atributo de instancia
            self.mode = 'editar'                   # Cambia la ventana a modo edición
            
            # Eliminamos la llamada a self.mostrar_lista_rma() para mantener la vista abierta.
            
            # Actualizar el título de la pestaña si fuera necesario
            self.tabview.set("📝 General")
            
            messagebox.showinfo("Éxito", f"RMA {datos_maestro['codigo_rma']} creado y guardado. Ahora puede adjuntar archivos.")
            
            # Volver al listado
            self.mostrar_lista_rma()

        except sqlite3.IntegrityError as e:
            conn.rollback()
            print(f"Error al guardar (Integridad): {e}. Es posible que el código RMA ya exista.")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error general de DB al guardar: {e}")
        finally:
            conn.close()

    # ----------------------------------------------------------------------
    # 6. LÓGICA DE EDICIÓN Y ACTUALIZACIÓN (CARGA Y GUARDADO DE CAMBIOS)
    # ----------------------------------------------------------------------

    def obtener_datos_actuales_maestro(self):
        """Recupera los datos del formulario MAESTRO actuales."""
        datos_maestro = {}
        # Lista de campos de la tabla rma_maestro que corresponden a entries
        campos_a_recuperar = [
            'Cliente', 'Numero_Documento_Cliente', 'Persona_de_Contacto', 'Email_de_Contacto',
            'Autorizacion', 'Autorizado_Por', 'Fecha_Autorizacion', 'Fecha_Recepcion',
            'Recepcionado_Por', 'Fecha_Gestion', 'Gestionado_Por', 'Fecha_Proceso', 'Procesado_Por',
            'Fecha_para_factura', 'Numero_Albaran', 'Fecha_Doc_Cliente', 'Resultado_Expediente',
            'Fecha_Emision', 'Creado_Por', 'motivo', 'Rma_Proveedor', 'Modelo', 'N_Serie', 'Ref_Proveedor', 'Obs_Tecnica'
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
                    elif hasattr(entry, 'get'):
                        valor = entry.get()
                    else:
                        valor = entry.cget("text")
                except Exception:
                    # Fallback
                    try:
                        valor = entry.get()
                    except Exception:
                        valor = ''
                
                # Conversión especial para Autorizacion (SI/NO a 1/0)
                if campo == 'Autorizacion':
                    datos_maestro['autorizacion'] = 1 if valor == "SI" else 0
                else:
                    datos_maestro[campo.lower()] = valor
        
        datos_maestro['codigo_rma'] = self.lbl_codigo_rma.cget("text").split(": ")[1]
        
        return datos_maestro

    def autorrellena_pdf(self):
        """Autorrellena la plantilla PDF con los datos del RMA actual y la guarda como adjunto.

        Busca primero 'Plantilla_RMA.pdf' en la carpeta plantillas/. Si no existe, abre
        un diálogo para seleccionar la plantilla. Luego llama a la función de librería
        para rellenar el PDF y registra el archivo en la tabla rma_adjuntos.
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
        plantilla_def = os.path.join(base_dir, 'plantillas', 'Plantilla_RMA.pdf')
        if os.path.exists(plantilla_def):
            plantilla_path = plantilla_def
        else:
            # Pedir al usuario que seleccione la plantilla
            plantilla_path = filedialog.askopenfilename(title='Seleccionar plantilla PDF', initialdir=os.path.join(base_dir, 'plantillas'), filetypes=[('PDF files', '*.pdf')])
            if not plantilla_path:
                return

        # Comprobar que la función de relleno esté disponible
        if fill_pdf_for_rma is None:
            messagebox.showerror("Dependencia falta", "La funcionalidad de rellenado PDF no está disponible. Instala la dependencia o revisa el módulo lib.pdf_fill.")
            return

        # Preparar rutas de salida
        carpeta_destino = self.crear_carpeta_adjuntos_rma(codigo_rma)
        # Nombre base requerido por el usuario: <CODIGO_RMA>_Solicitud_RMA.pdf
        nombre_base = f"{codigo_rma}_Solicitud_RMA.pdf"
        nombre_salida = nombre_base
        # Si el archivo ya existe, añadimos timestamp para evitar sobrescribir
        if os.path.exists(os.path.join(carpeta_destino, nombre_salida)):
            fecha_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_salida = f"{codigo_rma}_Solicitud_RMA_{fecha_str}.pdf"
        ruta_salida = os.path.join(carpeta_destino, nombre_salida)

        # Llamar a la librería para rellenar y aplanar según requisitos del usuario
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
            # Mapping explícito solicitado:
            mapping = {
                # Asignar el campo PDF "Ubicación de las fuentes en la instalación" a db:obs_tecnica
                'Ubicación de las fuentes en la instalación': 'db:obs_tecnica',
                # Serial
                'N mero de serie': 'db:n_serie',
                # Referencia para devolución -> código RMA
                'Referencia para devoluci n': 'db:codigo_rma',
                'Referencia para devolución': 'db:codigo_rma',
                # No mapear Email para preservar el valor que ya contiene la plantilla (se indica en skip_fields)
            }

            # Campos que queremos que queden editables en el PDF final
            exclude_from_flatten = [
                'Cantidad afectada', 'N Pedido', 'Nº RMA', 'N° RMA', 'N RMA', 'N� RMA',
                'N� de pedido  Albar�n', 'N� de pedido Albar�n', 'N Pedido Albarán', 'N� de pedido Albaran'
            ]

            # Forzar que ciertos campos queden vacíos y editables
            force_empty = [
                'Cantidad afectada', 'N Pedido', 'N� de pedido  Albar�n', 'N� de pedido Albar�n',
                'N Pedido Albarán', 'N� de pedido Albaran', 'Nº RMA'
            ]

            # Campos a NO sobreescribir (preservar tal como están en la plantilla)
            skip_fields = [
                'Empresa', 'Dirección de entrega', 'Persona de contactoDepartamento', 'Teléfono', 'Email',
                'Nº de pedido  Albarán', 'Nº de pedido Albarán', 'N Pedido Albarán', 'Nº de pedido Albaran'
            ]

            salida_generada = fill_pdf_for_rma(
                db_path, codigo_rma, plantilla_path, ruta_salida,
                mapping=mapping,
                flatten=True,
                exclude_from_flatten=exclude_from_flatten,
                force_empty_fields=force_empty,
                skip_fields=skip_fields
            )
        except Exception as e:
            messagebox.showerror("Error Rellenado", f"Error al rellenar la plantilla: {e}")
            return

        # Registrar en la base de datos como adjunto
        ruta_relativa = os.path.join(codigo_rma, nombre_salida)
        try:
            conn, cursor = self.master.conectar_db()
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
            # También registrar entrada en rma_historial
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (
                self.current_rma_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.username,
                f"Generada Solicitud RMA: {nombre_salida}"
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showwarning("Aviso", f"PDF generado en disco, pero no se pudo registrar en la BD: {e}")
            return

        # Refrescar lista de adjuntos
        try:
            self.cargar_lista_adjuntos(self.current_rma_id)
        except Exception:
            pass

        # Feedback al usuario
        try:
            messagebox.showinfo("Éxito", f"Solicitud generada y adjuntada: {ruta_relativa}")
        except Exception:
            # En entornos sin GUI activo, ignorar
            pass


    def cargar_datos_rma(self, rma_id):
        """Carga el RMA maestro y sus detalles en el formulario."""
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
            cursor.execute("SELECT referencia_articulo, cantidad_segun_documento, cantidad_entregada, estado_producto, precio_unitario FROM rma_detalles WHERE rma_id = ?", (rma_id,))
            columnas_detalle = [col[0] for col in cursor.description]
            articulos_db = [dict(zip(columnas_detalle, fila)) for fila in cursor.fetchall()]

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
            # --- Mapeo de Columna DB a Variable de Formulario ---
            for columna, valor in datos_maestro.items():
                
                # Excluir 'id', 'precio_total_expediente' y 'estado' que no tienen entry directo
                if columna in ['id', 'precio_total_expediente', 'estado']:
                    continue

                # ---------------------------------------------------------------------------------
                # 1. DETERMINAR EL NOMBRE CORRECTO DE LA VARIABLE DE LA INTERFAZ (entry_name)
                # ---------------------------------------------------------------------------------
                entry_name = None
                
                # Caso A: Campos simples (Sin guiones bajos, como 'motivo', 'cliente', 'creado_por')
                # ESTA ES LA RUTA CRÍTICA QUE 'motivo' DEBE SEGUIR
                if '_' not in columna:
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
                    
                    # Tratamiento especial para OptionMenu (Autorizacion)
                    if columna == 'autorizacion' and isinstance(entry, ctk.CTkOptionMenu):
                        valor_str = "SI" if valor == 1 else "NO"
                        entry.set(valor_str)
                        
                    # Tratamiento para Entry
                    elif isinstance(entry, ctk.CTkEntry):
                        # Configurar Entry
                        estado_original = entry.cget("state")  
                        entry.configure(state="normal")
                        
                        # CRÍTICO: Borrar el placeholder ANTES de insertar
                        entry.delete(0, ctk.END)
                        entry.insert(0, str(valor) if valor is not None else "")
                        
                        entry.configure(state=estado_original)
                        
                    # Tratamiento para OptionMenu General
                    elif isinstance(entry, ctk.CTkOptionMenu):
                        if str(valor) in entry.cget("values"):  
                             entry.set(str(valor))
                    # Tratamiento para Textbox grande (Observaciones Técnicas u otros)
                    elif isinstance(entry, ctk.CTkTextbox):
                        try:
                            entry.delete("1.0", "end")
                            entry.insert("1.0", str(valor) if valor is not None else "")
                        except Exception:
                            # algunos widgets CTkTextbox pueden tener métodos distintos; ignorar si falla
                            pass
            
            # --- NUEVO: Actualizar la etiqueta del total ---
            precio_total = datos_maestro.get('precio_total_expediente', 0.0) # Obtener el valor
            self.lbl_precio_total.configure(text=f"{precio_total:.2f} €")
            
            # 4. Rellenar Artículos (self.articulos_data)
            self.articulos_data = articulos_db
            self.actualizar_listado_articulos()

        except Exception as e:
            print(f"Error al cargar datos del RMA ID {rma_id}: {e}")
            conn.close()
            
    def guardar_cambio_historial(self, rma_id, campo, valor_antiguo, valor_nuevo):
        """Registra un cambio de un campo en la tabla de historial."""
        conn, cursor = self.master.conectar_db()
        if not conn: return

        cursor = conn.cursor()
        
        descripcion = f"Campo '{campo}' modificado: '{valor_antiguo}' -> '{valor_nuevo}'"
        # Si el campo modificado es 'Procesado Por' (o su variante), añadimos la nota requerida
        try:
            campo_norm = str(campo).lower().strip().replace(' ', '_')
            if campo_norm == 'procesado_por' or campo_norm == 'procesadopor':
                descripcion = descripcion + " - MATERIAL REVISADO"
        except Exception:
            # En caso de cualquier problema al normalizar, no bloqueamos el guardado del historial
            pass
        
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
        cursor.execute("SELECT * FROM rma_maestro WHERE id = ?", (rma_id,))
        columnas_maestro_db = [col[0] for col in cursor.description]
        datos_antiguos = dict(zip(columnas_maestro_db, cursor.fetchone()))
        
        # 2. Obtener datos nuevos del formulario
        datos_nuevos = self.obtener_datos_actuales_maestro()
        
        # 2.1. INTEGRACIÓN DE LA TRAZABILIDAD - Calcular el nuevo estado
        estado_nuevo = self.determinar_estado_rma(datos_nuevos)
        
        # Añadir el estado al diccionario de datos nuevos
        datos_nuevos['estado'] = estado_nuevo 
        
        # 3. Comparar y construir la consulta de actualización (UPDATE)
        campos_a_actualizar = []
        valores_a_actualizar = []
        
        for columna_db, valor_nuevo in datos_nuevos.items():
            valor_antiguo = datos_antiguos.get(columna_db)
            
            # SQLite almacena el boolean como int (1/0)
            if columna_db == 'autorizacion':
                if valor_nuevo != valor_antiguo:
                    self.guardar_cambio_historial(rma_id, "Autorización", "NO" if valor_antiguo == 0 else "SI", "NO" if valor_nuevo == 0 else "SI")
                    campos_a_actualizar.append(f"{columna_db} = ?")
                    valores_a_actualizar.append(valor_nuevo)
            
            # Comparación de campos normales (no boolean)
            elif str(valor_nuevo) != str(valor_antiguo):
                self.guardar_cambio_historial(rma_id, columna_db.title().replace('_', ' '), str(valor_antiguo), str(valor_nuevo))
                campos_a_actualizar.append(f"{columna_db} = ?")
                valores_a_actualizar.append(valor_nuevo)
        
        columna_estado_ya_anadida = 'estado' in [c.split('=')[0].strip() for c in campos_a_actualizar]

        if not columna_estado_ya_anadida:
            # Si no se incluyó en el bucle anterior (lo que indica que el estado no cambió),
            # lo incluimos ahora, usando el nuevo valor calculado.
            campos_a_actualizar.append("estado = ?")
            valores_a_actualizar.append(estado_nuevo)

        # 4. Actualizar rma_maestro si hay cambios
        if campos_a_actualizar:
            valores_a_actualizar.append(rma_id)
            set_clause = ", ".join(campos_a_actualizar)
            
            try:
                cursor.execute(f"UPDATE rma_maestro SET {set_clause} WHERE id = ?", tuple(valores_a_actualizar))
                print(f"✅ RMA {datos_nuevos['codigo_rma']} Maestro actualizado.")
                messagebox.showinfo("Expediente actualizado", "Expediente se ha actualizado.")
            except sqlite3.Error as e:
                print(f"Error al actualizar maestro: {e}")
                conn.rollback()
                conn.close()
                return

        # 5. Actualizar rma_detalles (Borrar antiguos e Insertar nuevos) - OPTIMIZADO
        try:
            # Borrar todos los detalles existentes
            cursor.execute("DELETE FROM rma_detalles WHERE rma_id = ?", (rma_id,))
            
            # Insertar los detalles de la lista temporal del formulario - BATCH
            if self.articulos_data:
                primer_articulo = self.articulos_data[0].copy()
                primer_articulo['rma_id'] = rma_id
                
                columnas_detalle = ', '.join(primer_articulo.keys())
                placeholders_detalle = ', '.join('?' * len(primer_articulo))
                
                # Preparar lista de valores para executemany
                valores_batch = []
                for articulo in self.articulos_data:
                    articulo_copia = articulo.copy()
                    articulo_copia['rma_id'] = rma_id
                    valores_batch.append(tuple(articulo_copia.values()))
                
                # Insertar todos los artículos en batch (mucho más rápido)
                cursor.executemany(f"""
                    INSERT INTO rma_detalles ({columnas_detalle}) 
                    VALUES ({placeholders_detalle})
                """, valores_batch)
                    
                self.guardar_cambio_historial(rma_id, "Detalle Artículos", "Lista Anterior", f"Lista Nueva ({len(self.articulos_data)} items)")
            
            elif not self.articulos_data and cursor.rowcount > 0: # Si borramos y no insertamos nada
                 self.guardar_cambio_historial(rma_id, "Detalle Artículos", "Lista Anterior", "Lista Nueva (0 items - Artículos eliminados)")
            
            print(f"✅ RMA {datos_nuevos['codigo_rma']} Detalles actualizados.")
            messagebox.showinfo("Expediente actualizado", "Expediente se ha actualizado.")

        except sqlite3.Error as e:
            print(f"Error al actualizar detalles: {e}")
            conn.rollback()
            conn.close()
            return
            
        # 6. Commit final, invalidar caché y retorno a la lista
        conn.commit()
        conn.close()
        
        # Invalidar caché de estados (puede que se haya actualizado el estado)
        invalidate_cache('estados_rma')
        self.mostrar_lista_rma()
    
    def mostrar_historial(self, parent_frame):
        """Muestra la lista de registros de cambios para el RMA actual."""
        
        # Destruye el 'historial_scroll_frame' anterior y todos sus hijos.
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # Marco scrollable para contener la lista de eventos
        historial_scroll_frame = ctk.CTkScrollableFrame(parent_frame, label_text="Detalle de Cambios en el Expediente")
        historial_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Encabezados
        header_font = ctk.CTkFont(weight="bold")
        historial_scroll_frame.grid_columnconfigure(2, weight=1) # Descripción se expande
        ctk.CTkLabel(historial_scroll_frame, text="FECHA/HORA", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(historial_scroll_frame, text="USUARIO", font=header_font).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(historial_scroll_frame, text="DESCRIPCIÓN DEL CAMBIO", font=header_font).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        conn, cursor = self.master.conectar_db()
        if not conn: return
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT fecha_cambio, usuario, descripcion_cambio 
                FROM rma_historial 
                WHERE rma_id = ? 
                ORDER BY id DESC
            """, (self.rma_actual_id,))
            
            registros = cursor.fetchall()
            conn.close()

            if not registros:
                ctk.CTkLabel(historial_scroll_frame, text="No hay registros de historial para este RMA.", text_color="gray").grid(row=1, column=0, columnspan=3, padx=10, pady=20)
                return
            
            # Mostrar los registros
            for i, reg in enumerate(registros):
                fecha, usuario, descripcion = reg
                row = i + 1
                
                ctk.CTkLabel(historial_scroll_frame, text=fecha).grid(row=row, column=0, padx=5, pady=2, sticky="w")
                ctk.CTkLabel(historial_scroll_frame, text=usuario).grid(row=row, column=1, padx=5, pady=2, sticky="w")
                
                # Usamos wrap para que el texto de la descripción no se salga
                ctk.CTkLabel(historial_scroll_frame, text=descripcion, wraplength=500, justify="left").grid(row=row, column=2, padx=5, pady=2, sticky="w")

        except Exception as e:
            print(f"Error al cargar historial: {e}")
            if conn: conn.close()
            ctk.CTkLabel(historial_scroll_frame, text="Error al cargar el historial.", text_color="red").grid(row=1, column=0, columnspan=3, padx=10, pady=20)


    def determinar_estado_rma(self, datos_maestro):
        """Calcula el estado del RMA basándose en las fechas clave."""
        
        # Obtener fechas del diccionario de datos (asegúrate que las claves son minúsculas como en la DB)
        fecha_recepcion = datos_maestro.get('fecha_recepcion')
        fecha_gestion = datos_maestro.get('fecha_gestion')
        fecha_autorizacion = datos_maestro.get('fecha_autorizacion')
        fecha_emision = datos_maestro.get('fecha_emision')
        
        # 5. Estado 'Completado' (Último paso)
        if fecha_gestion:
            return "Completado"
            
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
    
    def aplicar_filtros_rma(self):
        """Lee los valores de los filtros y recarga la lista."""
        texto_busqueda = self.entry_busqueda.get()
        estado_filtro = self.filtro_estado.get()
        
        self.cargar_lista_rma(texto_busqueda, estado_filtro)
    
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
                    FOREIGN KEY (rma_id) REFERENCES rma_maestro (id)
                )
            """)
            conn.commit()
            print("Tabla 'rma_adjuntos' verificada/creada.")
        except sqlite3.Error as e:
            print(f"Error al crear la tabla 'rma_adjuntos': {e}")
        finally:
            conn.close()


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
    
    def crear_carpeta_adjuntos_rma(self, codigo_rma):
        """
        Crea la carpeta específica para el RMA (Ej: Adjuntos_RMA/RMA25001) 
        si no existe.
        """
        # 1. Asegurarse de que la carpeta raíz exista (Adjuntos_RMA)
        if not os.path.exists(ADJUNTOS_ROOT_DIR):
            os.makedirs(ADJUNTOS_ROOT_DIR)
            
        # 2. Crear la carpeta específica del RMA
        ruta_rma = os.path.join(ADJUNTOS_ROOT_DIR, codigo_rma)
        os.makedirs(ruta_rma, exist_ok=True)
        return ruta_rma
    
    def abrir_dialogo_adjunto(self, modo_abrir_carpeta=False):
        """Abre el diálogo de selección de archivo y lo sube al sistema."""
        # 1. Verificar si el RMA ya está guardado (si current_rma_id tiene valor)
        if not self.current_rma_id:
            messagebox.showwarning("Advertencia", "Debe guardar el RMA al menos una vez antes de adjuntar archivos.")
            return
        
        
        # -----------------------------------------------------------------
        # LÓGICA DE OBTENCIÓN DEL CÓDIGO RMA (Igual que en tu código original)
        # -----------------------------------------------------------------
        # Obtener el texto completo de la etiqueta (Ej: "Código RMA: RMA25001")
        texto_completo = self.lbl_codigo_rma.cget("text") 
        # Extraer solo el código RMA dividiendo el texto por ": "
        codigo_rma = texto_completo.split(": ")[1] 
        
        # -----------------------------------------------------------------
        # LÓGICA DE ABRIR CARPETA (Modo Informe)
        # -----------------------------------------------------------------
        if modo_abrir_carpeta:
            # 1. Obtener la ruta de destino y crear la carpeta (usando tu método existente)
            ruta_destino_base = self.crear_carpeta_adjuntos_rma(codigo_rma)
            
            # 2. Abrir la carpeta de destino en el explorador de archivos
            try:
                if os.name == 'nt':
                    # Para Windows, usar os.startfile para abrir la carpeta
                    os.startfile(ruta_destino_base)
                elif sys.platform == 'darwin':
                    # Para macOS
                    subprocess.Popen(['open', ruta_destino_base])
                else:
                    # Para Linux (usa el comando genérico xdg-open)
                    subprocess.Popen(['xdg-open', ruta_destino_base])
                
                # ¡IMPORTANTE! Aquí termina la ejecución en modo carpeta
                return
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta de destino:\n{ruta_destino_base}\nError: {e}")
                return

        # 2. Abrir diálogo para seleccionar archivo
        filepath = filedialog.askopenfilename(
            title="Seleccionar Archivo a Adjuntar",
            filetypes=(("Todos los archivos", "*.*"), ("Documentos PDF", "*.pdf"), ("Imágenes", "*.jpg;*.png"))
        )
        
        if not filepath:
            return # El usuario canceló

        nombre_original = os.path.basename(filepath)
        # 1. Obtener el texto completo de la etiqueta (Ej: "Código RMA: RMA25001")
        texto_completo = self.lbl_codigo_rma.cget("text") 
        
        # 2. Extraer solo el código RMA dividiendo el texto por ": "
        codigo_rma = texto_completo.split(": ")[1] 
        # --------------------------

        # 3. Preparar rutas
        # Crear la ruta de destino: Adjuntos_RMA/RMA25001/nombre_archivo.ext
        ruta_destino_dir = self.crear_carpeta_adjuntos_rma(codigo_rma)
        ruta_destino_completa = os.path.join(ruta_destino_dir, nombre_original)
        
        # 4. Copiar el archivo
        try:
            # shutil.copy2 copia el archivo y preserva metadatos
            shutil.copy2(filepath, ruta_destino_completa)
        except Exception as e:
            messagebox.showerror("Error de Copia", f"No se pudo copiar el archivo. ¿Permisos?\nError: {e}")
            return
        
        # 5. Insertar registro en la base de datos
        # La ruta relativa es la que guardamos en la DB (Ej: RMA25001/nombre_archivo.ext)
        ruta_relativa = os.path.join(codigo_rma, nombre_original)
        
        conn, cursor = self.master.conectar_db()
        try:
            cursor.execute("""
                INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.current_rma_id, 
                nombre_original, 
                ruta_relativa, 
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                self.username
            ))
            conn.commit()
            messagebox.showinfo("Éxito", f"Archivo '{nombre_original}' adjuntado correctamente.")
            
            self.cargar_lista_adjuntos(self.current_rma_id) # Recargar el listado
            
            # NOTA: Llamar a self.cargar_lista_adjuntos(self.current_rma_id) aquí
            # para recargar la lista se implementará en el siguiente paso.
            # Si ya tienes una implementación básica, añádela aquí.
            
        except Exception as e:
            conn.rollback()
            # Si falla la DB, eliminar el archivo copiado para evitar inconsistencias
            if os.path.exists(ruta_destino_completa):
                os.remove(ruta_destino_completa)
            messagebox.showerror("Error DB", f"Error al guardar registro en la base de datos: {e}")
        finally:
            conn.close()
    def cargar_lista_adjuntos(self, rma_id):
        """Consulta y muestra el listado de adjuntos para un RMA específico."""
        
        # Limpiar el frame antes de cargar la nueva lista
        for widget in self.adjuntos_list_frame.winfo_children():
            widget.destroy()

        conn, cursor = self.master.conectar_db()
        cursor.execute("SELECT id, nombre_archivo, ruta_relativa FROM rma_adjuntos WHERE rma_id = ?", (rma_id,))
        adjuntos = cursor.fetchall()
        conn.close()

        if not adjuntos:
            ctk.CTkLabel(self.adjuntos_list_frame, text="No hay archivos adjuntos para este expediente.").pack(pady=10)
            return

        for i, adjunto in enumerate(adjuntos):
            adjunto_id, nombre, ruta = adjunto

            item_frame = ctk.CTkFrame(self.adjuntos_list_frame)
            item_frame.pack(fill='x', padx=5, pady=2)

            # Etiqueta del nombre del archivo
            ctk.CTkLabel(item_frame, text=nombre, width=300, anchor='w').pack(side='left', padx=5)

            # Botón Visualizar
            # El comando usa lambda para pasar la ruta del archivo
            ctk.CTkButton(
                item_frame, 
                text="👁️ Abrir", 
                width=80, 
                command=lambda r=ruta: self.abrir_adjunto(r)
            ).pack(side='right', padx=5)

            # Botón Eliminar
            # El comando usa lambda para pasar el ID del adjunto y la ruta
            ctk.CTkButton(
                item_frame, 
                text="🗑️ Eliminar", 
                width=80, 
                fg_color="red", 
                hover_color="darkred",
                command=lambda aid=adjunto_id, r=ruta: self.confirmar_eliminar_adjunto(aid, r)
            ).pack(side='right', padx=5)
            
        # Llamamos a esta función dentro de abrir_dialogo_adjunto() para que se recargue después de subir un archivo.
    def abrir_adjunto(self, ruta_relativa):
        """Abre el archivo adjunto usando el programa predeterminado del sistema operativo."""
        ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa)
        
        if not os.path.exists(ruta_completa):
            messagebox.showerror("Error", f"Archivo no encontrado: {ruta_completa}. Posiblemente haya sido movido o eliminado manualmente.")
            return

        try:
            if sys.platform == "win32":
                # Windows
                os.startfile(ruta_completa)
            elif sys.platform == "darwin":
                # macOS
                subprocess.call(['open', ruta_completa])
            else:
                # Linux (Usa xdg-open para el programa predeterminado)
                subprocess.call(['xdg-open', ruta_completa])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo. Error: {e}")
    
    def confirmar_eliminar_adjunto(self, adjunto_id, ruta_relativa):
        """Pide confirmación antes de eliminar el registro y el archivo."""
        if messagebox.askyesno("Confirmar Eliminación", "¿Está seguro de que desea eliminar este adjunto? Esta acción es irreversible y también eliminará el archivo del disco."):
            self.eliminar_adjunto(adjunto_id, ruta_relativa)

    def eliminar_adjunto(self, adjunto_id, ruta_relativa):
        """Elimina el registro de la base de datos y el archivo físico."""
        ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa)
        
        conn, cursor = self.master.conectar_db()
        try:
            # 1. Eliminar registro de la DB
            cursor.execute("DELETE FROM rma_adjuntos WHERE id = ?", (adjunto_id,))
            
            # 2. Eliminar archivo físico
            if os.path.exists(ruta_completa):
                os.remove(ruta_completa)
            
            conn.commit()
            messagebox.showinfo("Éxito", "Adjunto eliminado correctamente.")
            self.cargar_lista_adjuntos(self.current_rma_id) # Recargar el listado
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Error al eliminar el adjunto: {e}")
        finally:
            conn.close()
    
    # Dentro de la clase VentanaPrincipal

    # Dentro de la clase VentanaPrincipal

    def generar_informe_dinamico(self):
        """
        Genera un informe dinámico usando python-docx, lo guarda en la carpeta 
        de adjuntos del RMA y lo registra en la base de datos.
        """
        # 1. Validaciones y Obtención de Datos
        if not self.current_rma_id:
            messagebox.showerror("Error", "Debe cargar un RMA guardado para generar el informe.")
            return

        # Asumimos que self.datos_rma_maestro contiene los datos del RMA cargado
        # Esta variable debe llenarse cuando llamas a self.cargar_datos_rma(rma_id)
        datos = self.datos_rma_maestro 
        
        # 🚨 Verificación: Asegúrate de que los datos clave existen
        codigo_rma = datos.get('codigo_rma')
        nombre_cliente = datos.get('cliente')
        
        if not codigo_rma or not nombre_cliente:
             messagebox.showerror("Error", "Los datos del RMA no están cargados. Intente recargar el expediente.")
             return

        # 2. Rutas
        plantilla_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantillas", "Plantilla_RMA.docx")
        
        # Nombre del archivo final: Ej. RMA2024-001_Informe_20240920.docx
        fecha_str = datetime.datetime.now().strftime("%Y%m%d")
        nombre_archivo_final = f"{codigo_rma}_Informe_{fecha_str}.docx"
        
        # Ruta donde se guardará el archivo final (usando tu método existente para la carpeta)
        ruta_destino_dir = self.crear_carpeta_adjuntos_rma(codigo_rma)
        ruta_destino_completa = os.path.join(ruta_destino_dir, nombre_archivo_final)

        try:
            # 3. Cargar la plantilla y definir mapeo de marcadores
            document = docx.Document(plantilla_path)
            
            # Mapeo: [Marcador en Word]: [Valor a insertar]
            mapeo = {
                '[[CODIGO_RMA]]': codigo_rma,
                '[[CLIENTE]]': nombre_cliente,
                '[[FECHA_EMISION]]': datos.get('fecha_emision', 'N/A'),
                '[[ESTADO_ACTUAL]]': datos.get('estado', 'N/A'), # Asumo que 'estado' es parte de los datos cargados
                '[[USUARIO_CREADOR]]': datos.get('creado_por', self.username)
            }
            
            # 4. Reemplazar marcadores en párrafos
            for p in document.paragraphs:
                for clave, valor in mapeo.items():
                    if clave in p.text:
                        p.text = p.text.replace(clave, valor)
            
            # 5. Guardar el documento final
            os.makedirs(ruta_destino_dir, exist_ok=True) 
            document.save(ruta_destino_completa)
            
            # 6. Registrar en la Base de Datos
            ruta_relativa = os.path.join(codigo_rma, nombre_archivo_final)
            conn, cursor = self.master.conectar_db()
            try:
                cursor.execute("""
                    INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida) 
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.current_rma_id, 
                    nombre_archivo_final, 
                    ruta_relativa, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    self.username
                ))
                
                # Registro en el historial
                cursor.execute("""
                    INSERT INTO rma_historial (rma_id, fecha_cambio, descripcion_cambio, usuario)
                    VALUES (?, ?, ?, ?)
                """, (
                    self.current_rma_id, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    f"Generado documento de Informe: {nombre_archivo_final}", 
                    self.username
                ))
                
                conn.commit()
                self.cargar_lista_adjuntos(self.current_rma_id) # Refresca la lista de adjuntos
                try:
                    # Llamamos al método que recarga el contenido de la pestaña
                    self.mostrar_historial(self.historial_tab) 
                except AttributeError:
                    # Si la pestaña historial_tab no está definida (ej. en modo "nuevo"), ignoramos.
                    pass
                
                messagebox.showinfo("Éxito", f"Informe '{nombre_archivo_final}' generado y adjuntado correctamente.")
                
            except Exception as db_e:
                conn.rollback()
                messagebox.showerror("Error DB", f"Informe generado, pero error al registrar en DB. Revise la carpeta de adjuntos.\nError: {db_e}")
            finally:
                conn.close()

        except Exception as e:
            messagebox.showerror("Error de Generación", f"No se pudo generar el informe dinámico. Asegúrese de que la plantilla existe y python-docx está instalado.\nError: {e}")
    
    # Dentro de la clase VentanaPrincipal

    def generar_reposicion_devolucion(self):
        """
        Genera el documento de Reposición/Devolución usando la plantilla
        "Reposicion_RMA.docx", lo guarda y lo registra como adjunto.
        """
        # 1. Validaciones y Obtención de Datos
        if not self.current_rma_id:
            messagebox.showerror("Error", "Debe cargar un RMA guardado para generar el documento de Reposición/Devolución.")
            return

        # Asumimos que self.datos_rma_maestro contiene los datos del RMA cargado
        datos = self.datos_rma_maestro 
        
        # Obtener datos clave para el archivo y la ruta
        codigo_rma = datos.get('codigo_rma')
        nombre_cliente = datos.get('cliente')
        
        if not codigo_rma or not nombre_cliente:
             messagebox.showerror("Error", "No se pudieron cargar los datos clave del RMA. Intente recargar el expediente.")
             return

        # 2. Rutas y Nombres de Archivo
        # 🚨 ¡Diferencia Clave! Usamos la nueva plantilla
        nombre_plantilla = "Reposicion_RMA.docx" 
        plantilla_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantillas", nombre_plantilla)
        
        # Nombre del archivo final: Ej. RMA2024-001_Reposicion_20251016.docx
        fecha_str = datetime.datetime.now().strftime("%Y%m%d")
        nombre_archivo_final = f"{codigo_rma}_Reposicion_{fecha_str}.docx"
        
        # Ruta donde se guardará el archivo final (usando tu método existente para la carpeta)
        ruta_destino_dir = self.crear_carpeta_adjuntos_rma(codigo_rma)
        ruta_destino_completa = os.path.join(ruta_destino_dir, nombre_archivo_final)

        # 3. Verificar la Plantilla
        if not os.path.exists(plantilla_path):
            messagebox.showerror("Error", f"No se encontró la plantilla requerida en:\n{plantilla_path}")
            return
            
        try:
            # 4. Cargar la plantilla y definir mapeo de marcadores
            document = docx.Document(plantilla_path)
            
            # Mapeo: Reutilizamos el mapeo existente (si tienes nuevos campos, añádelos aquí)
            mapeo = {
                '[[CODIGO_RMA]]': codigo_rma,
                '[[CLIENTE]]': nombre_cliente,
                '[[FECHA_EMISION]]': datos.get('fecha_emision', 'N/A'),
                '[[ESTADO_ACTUAL]]': datos.get('estado', 'N/A'),
                '[[USUARIO_CREADOR]]': datos.get('creado_por', self.username)
            }
            
            # 5. Reemplazar marcadores en párrafos (Usando la lógica robusta que ya funciona)
            for p in document.paragraphs:
                for clave, valor in mapeo.items():
                    valor_a_insertar = str(valor) if valor is not None else "" 
                    if clave in p.text:
                        p.text = p.text.replace(clave, valor_a_insertar)
            
            # 6. Guardar el documento final
            os.makedirs(ruta_destino_dir, exist_ok=True) 
            document.save(ruta_destino_completa)
            
            # 7. Registrar en la Base de Datos (Misma lógica para adjuntos e historial)
            ruta_relativa = os.path.join(codigo_rma, nombre_archivo_final)
            conn, cursor = self.master.conectar_db()
            try:
                # Registro en rma_adjuntos
                cursor.execute("""
                    INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida) 
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.current_rma_id, 
                    nombre_archivo_final, 
                    ruta_relativa, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    self.username
                ))
                
                # Registro en el historial
                cursor.execute("""
                    INSERT INTO rma_historial (rma_id, fecha_cambio, descripcion_cambio, usuario)
                    VALUES (?, ?, ?, ?)
                """, (
                    self.current_rma_id, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    f"Generado documento de Reposición/Devolución: {nombre_archivo_final}", 
                    self.username
                ))
                
                conn.commit()
                self.cargar_lista_adjuntos(self.current_rma_id) # Refresca la lista de adjuntos
                try:
                    # Llamamos al método que recarga el contenido de la pestaña
                    self.mostrar_historial(self.historial_tab) 
                except AttributeError:
                    # Si la pestaña historial_tab no está definida (ej. en modo "nuevo"), ignoramos.
                    pass
                
                messagebox.showinfo("Éxito", f"Documento de Reposición/Devolución '{nombre_archivo_final}' generado y adjuntado correctamente.")
                
            except Exception as db_e:
                conn.rollback()
                messagebox.showerror("Error DB", f"Documento generado, pero error al registrar en DB/Historial. Error: {db_e}")
            finally:
                conn.close()

        except Exception as e:
            messagebox.showerror("Error de Generación", f"No se pudo generar el documento. Asegúrese de que la plantilla existe y es un archivo .docx válido.\nError: {e}")
    
    
    
    def abrir_plantilla_informe_manual_sinusoactualmente(self):
        """
        Abre la plantilla de informe de Word y la carpeta de destino de los adjuntos.
        """
        # Verificación inicial: ¿Estamos editando un RMA?
        if not self.rma_actual_id:
            messagebox.showerror("Error", "Primero debe guardar el expediente o cargar uno existente para generar un informe.")
            return

        # 1. Definir rutas
        # Obtiene la ruta absoluta de la carpeta 'plantillas'
        plantilla_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantillas")
        plantilla_path = os.path.join(plantilla_dir, "Plantilla_RMA.docx") # Asegúrate de que el nombre coincide
        
        # 2. Verificar que la plantilla existe
        if not os.path.exists(plantilla_path):
            messagebox.showerror("Error", f"No se encontró la plantilla de informe en:\n{plantilla_path}")
            return
            
        # 3. Abrir la plantilla con el programa asociado (Word)
        try:
            # os.startfile es la forma más limpia en Windows para abrir archivos
            if os.name == 'nt': 
                 os.startfile(plantilla_path)
            else:
                 # Común para macOS o Linux (puede requerir ajustes según la distribución)
                 subprocess.Popen(['xdg-open', plantilla_path]) 

            messagebox.showinfo("Instrucción", 
                "Se ha abierto la plantilla de Word.\n"
                "A continuación se abrirá la carpeta de destino. Por favor, "
                "**GUARDE el documento de Word FINAL ahí**.")
            
            # 4. Abrir la carpeta de destino para que el usuario guarde el resultado
            self.abrir_dialogo_adjunto(modo_abrir_carpeta=True)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la plantilla.\nError: {e}")
    
    def mostrar_gestion_usuarios(self):
        """Muestra la ventana de gestión de usuarios con opciones para añadir/editar usuarios."""
        # Solo admin tiene permisos para gestionar usuarios
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Error", "Solo el administrador puede gestionar usuarios.")
            return

        # Crear ventana modal
        ventana = ctk.CTkToplevel(self)
        ventana.title("Gestión de Usuarios")
        ventana.geometry("600x500")
        ventana.grab_set()

        # Frame principal
        frame = ctk.CTkFrame(ventana)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        ctk.CTkLabel(frame, text="Gestión de Usuarios", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(0, 20))

        # Frame para el formulario de nuevo usuario
        form_frame = ctk.CTkFrame(frame)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Campos del formulario
        ctk.CTkLabel(form_frame, text="Nombre de Usuario:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        entry_usuario = ctk.CTkEntry(form_frame)
        entry_usuario.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Contraseña:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        entry_password = ctk.CTkEntry(form_frame, show="*")
        entry_password.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Rol:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        # Lista de roles disponibles
        roles_disponibles = [
            "usuario",        # Usuario básico
            "admin",         # Administrador total
            "Dpto. Tecnico", # Departamento técnico
            "Administracion",# Administración
            "Contabilidad",  # Contabilidad
            "Almacen"        # Almacén
        ]
        combo_rol = ctk.CTkOptionMenu(form_frame, values=roles_disponibles)
        combo_rol.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        combo_rol.set("usuario")  # Valor por defecto

        form_frame.grid_columnconfigure(1, weight=1)

        def agregar_usuario():
            username = entry_usuario.get().strip()
            password = entry_password.get().strip()
            rol = combo_rol.get()

            if not username or not password:
                messagebox.showerror("Error", "Por favor, complete todos los campos.")
                return

            try:
                # Generar hash de la contraseña
                password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

                conn = connect_db()
                cursor = conn.cursor()

                # Verificar si el usuario ya existe
                cursor.execute("SELECT nombre_usuario FROM usuarios WHERE nombre_usuario = ?", (username,))
                if cursor.fetchone():
                    messagebox.showerror("Error", "El nombre de usuario ya existe.")
                    return

                # Insertar nuevo usuario
                cursor.execute(
                    "INSERT INTO usuarios (nombre_usuario, password_hash, rol) VALUES (?, ?, ?)",
                    (username, password_hash, rol)
                )
                conn.commit()
                messagebox.showinfo("Éxito", "Usuario creado correctamente.")
                
                # Limpiar campos
                entry_usuario.delete(0, 'end')
                entry_password.delete(0, 'end')
                combo_rol.set("usuario")
                
                # Actualizar lista de usuarios
                actualizar_lista_usuarios()

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error al crear usuario: {e}")
            finally:
                conn.close()

        # Botón para agregar usuario
        ctk.CTkButton(form_frame, text="Agregar Usuario", command=agregar_usuario).grid(row=3, column=0, columnspan=2, pady=20)

        # Frame para la lista de usuarios
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(20,10))

        # Título de la lista
        ctk.CTkLabel(list_frame, text="Usuarios Existentes", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        # Crear un frame scrollable para la lista de usuarios
        scroll_frame = ctk.CTkScrollableFrame(list_frame)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        def actualizar_lista_usuarios():
            # Limpiar lista actual
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            try:
                conn = connect_db()
                cursor = conn.cursor()
                # Asegurarnos de que la columna email exista (añadir si no)
                try:
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                    conn.commit()
                except Exception:
                    # Ignorar si ya existe o si el backend no permite ALTER (p.ej. versiones restringidas)
                    pass
                # Seleccionamos también el email si existe
                try:
                    cursor.execute("SELECT nombre_usuario, rol, COALESCE(email, '') FROM usuarios")
                except Exception:
                    # Fallback si la columna no existe por alguna razón
                    cursor.execute("SELECT nombre_usuario, rol FROM usuarios")
                usuarios = cursor.fetchall()

                for i, row in enumerate(usuarios):
                    # row can be (usuario, rol) or (usuario, rol, email)
                    usuario = row[0] if len(row) > 0 else ''
                    rol = row[1] if len(row) > 1 else ''
                    display_email = row[2] if len(row) > 2 else ''

                    row_frame = ctk.CTkFrame(scroll_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)

                    label_text = f"{usuario} ({rol})"
                    if display_email:
                        label_text += f" — {display_email}"
                    lbl = ctk.CTkLabel(row_frame, text=label_text)
                    lbl.pack(side="left", padx=5)

                    # Hacer clic en el label abre editor de usuario, excepto para admin
                    if usuario != "admin":
                        def make_editor(u=usuario):
                            return lambda e=None: editar_usuario(u)
                        try:
                            lbl.bind("<Button-1>", make_editor(usuario))
                            lbl.configure(cursor="hand2")
                        except Exception:
                            pass
                    else:
                        # Mostrar cursor normal y no permitir edición
                        try:
                            lbl.configure(cursor="")
                        except Exception:
                            pass
                    
                    if usuario != "admin":  # No permitir eliminar al usuario admin
                        def make_delete(u=usuario):
                            return lambda: eliminar_usuario(u)
                        
                        ctk.CTkButton(row_frame, text="❌", width=30, command=make_delete(usuario)).pack(side="right", padx=5)

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error al cargar usuarios: {e}")
            finally:
                conn.close()

        def editar_usuario(username):
            """Abrir dialogo para editar rol, password y email del usuario seleccionado."""
            # Proteger al usuario admin: no se puede editar
            if username == "admin":
                messagebox.showerror("Acceso denegado", "El usuario 'admin' no se puede editar ni eliminar.")
                return
            try:
                conn = connect_db()
                cur = conn.cursor()
                # Intentar obtener email si existe
                try:
                    cur.execute("SELECT nombre_usuario, rol, COALESCE(email, '') FROM usuarios WHERE nombre_usuario = ?", (username,))
                    row = cur.fetchone()
                    if row and len(row) >= 3:
                        _, rol_actual, email_actual = row
                    else:
                        cur.execute("SELECT nombre_usuario, rol FROM usuarios WHERE nombre_usuario = ?", (username,))
                        row2 = cur.fetchone()
                        rol_actual = row2[1] if row2 else ''
                        email_actual = ''
                except Exception:
                    # fallback
                    cur.execute("SELECT nombre_usuario, rol FROM usuarios WHERE nombre_usuario = ?", (username,))
                    row2 = cur.fetchone()
                    rol_actual = row2[1] if row2 else ''
                    email_actual = ''
                conn.close()
            except Exception:
                rol_actual = ''
                email_actual = ''

            # Editor modal
            ed = ctk.CTkToplevel(ventana)
            ed.title(f"Editar usuario: {username}")
            ed.geometry("420x260")
            ed.grab_set()

            f = ctk.CTkFrame(ed)
            f.pack(fill="both", expand=True, padx=12, pady=12)

            ctk.CTkLabel(f, text=f"Usuario: {username}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))

            ctk.CTkLabel(f, text="Rol:").grid(row=1, column=0, sticky="e", padx=5, pady=6)
            rol_menu = ctk.CTkOptionMenu(f, values=roles_disponibles)
            rol_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=6)
            try:
                rol_menu.set(rol_actual or "usuario")
            except Exception:
                rol_menu.set("usuario")

            ctk.CTkLabel(f, text="Nueva contraseña:").grid(row=2, column=0, sticky="e", padx=5, pady=6)
            new_pass = ctk.CTkEntry(f, show="*")
            new_pass.grid(row=2, column=1, sticky="ew", padx=5, pady=6)

            ctk.CTkLabel(f, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=6)
            email_entry = ctk.CTkEntry(f)
            email_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=6)
            try:
                email_entry.insert(0, email_actual)
            except Exception:
                pass

            f.grid_columnconfigure(1, weight=1)

            def guardar_cambios():
                nuevo_rol = rol_menu.get()
                nueva_pass = new_pass.get().strip()
                nuevo_email = email_entry.get().strip()
                try:
                    conn2 = connect_db()
                    cur2 = conn2.cursor()
                    # Si se proporcionó nueva contraseña, hashearla
                    if nueva_pass:
                        hashed = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt())
                        try:
                            cur2.execute("UPDATE usuarios SET password_hash = ? WHERE nombre_usuario = ?", (hashed, username))
                        except Exception:
                            pass
                    # Actualizar rol y email
                    try:
                        cur2.execute("UPDATE usuarios SET rol = ?, email = ? WHERE nombre_usuario = ?", (nuevo_rol, nuevo_email, username))
                    except Exception:
                        # Si UPDATE falla porque la columna email no existe, intentar crearla y reintentar
                        try:
                            cur2.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                            cur2.execute("UPDATE usuarios SET rol = ?, email = ? WHERE nombre_usuario = ?", (nuevo_rol, nuevo_email, username))
                        except Exception:
                            pass
                    conn2.commit()
                    conn2.close()
                    messagebox.showinfo("Éxito", "Usuario actualizado correctamente.")
                    ed.destroy()
                    actualizar_lista_usuarios()
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"No se pudo actualizar usuario: {e}")

            btn_frame = ctk.CTkFrame(f)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=(12,0))
            ctk.CTkButton(btn_frame, text="Guardar", command=guardar_cambios).pack(side="left", padx=6)
            ctk.CTkButton(btn_frame, text="Cancelar", command=ed.destroy).pack(side="left", padx=6)

        def eliminar_usuario(username):
            if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar al usuario {username}?"):
                try:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE nombre_usuario = ?", (username,))
                    conn.commit()
                    messagebox.showinfo("Éxito", "Usuario eliminado correctamente.")
                    actualizar_lista_usuarios()
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"Error al eliminar usuario: {e}")
                finally:
                    conn.close()

        # Cargar lista inicial de usuarios
        actualizar_lista_usuarios()
        # Cargar lista inicial de usuarios
        actualizar_lista_usuarios()

    def mostrar_gestion_tareas(self):
        """Ventana para crear y listar tareas relacionadas con expedientes."""
        # Mostrar solo el listado de tareas y filtros (la creación se hace desde la ficha del expediente)
        ventana = ctk.CTkToplevel(self)
        ventana.title("Listado de Tareas")
        ventana.geometry("700x550")
        ventana.grab_set()

        frame = ctk.CTkFrame(ventana)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(frame, text="Listado de Tareas", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0,10))

        # Filtros y lista
        controls = ctk.CTkFrame(frame)
        controls.pack(fill="x", padx=5, pady=(0,10))

        ctk.CTkLabel(controls, text="Filtrar por estado:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        filtro_estado = ctk.CTkOptionMenu(controls, values=["Todos", "Pendiente", "En Progreso", "Completado"]) 
        filtro_estado.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        filtro_estado.set("Todos")

        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        scroll = ctk.CTkScrollableFrame(list_frame)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        def abrir_expediente_por_codigo(codigo):
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo,))
                row = cur.fetchone()
                conn.close()
                if row:
                    rma_id = row[0]
                    # Abrir en panel principal
                    self.mostrar_nuevo_rma(rma_id=rma_id)
                    ventana.destroy()
                else:
                    messagebox.showwarning("No encontrado", f"No se encontró expediente con código {codigo}")
            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"Error buscando expediente: {e}")

        def actualizar_lista_tareas():
            for w in scroll.winfo_children():
                w.destroy()
            try:
                conn = connect_db()
                cur = conn.cursor()
                estado = filtro_estado.get()
                if estado == "Todos":
                    cur.execute("SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por FROM tareas ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC")
                else:
                    cur.execute("SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por FROM tareas WHERE estado = ? ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC", (estado,))
                filas = cur.fetchall()
                conn.close()

                # Encabezados de tabla con estructura en columnas
                header = ctk.CTkFrame(scroll)
                header.pack(fill="x", padx=5, pady=(0, 5))
                header.grid_columnconfigure(0, weight=2, minsize=200)  # Título
                header.grid_columnconfigure(1, weight=1, minsize=100)  # Código
                header.grid_columnconfigure(2, weight=1, minsize=120)  # Estado
                header.grid_columnconfigure(3, weight=1, minsize=120)  # Vencimiento
                header.grid_columnconfigure(4, weight=0, minsize=80)   # Acciones
                
                header_font = ctk.CTkFont(weight="bold")
                ctk.CTkLabel(header, text="TÍTULO", font=header_font, anchor="w").grid(row=0, column=0, padx=5, sticky="w")
                ctk.CTkLabel(header, text="CÓDIGO", font=header_font, anchor="w").grid(row=0, column=1, padx=5, sticky="w")
                ctk.CTkLabel(header, text="ESTADO", font=header_font, anchor="w").grid(row=0, column=2, padx=5, sticky="w")
                ctk.CTkLabel(header, text="VENCIMIENTO", font=header_font, anchor="w").grid(row=0, column=3, padx=5, sticky="w")
                ctk.CTkLabel(header, text="ACCIONES", font=header_font, anchor="center").grid(row=0, column=4, padx=5)

                # Filas de datos
                for tid, codigo, titulo, desc, fecha_v, estado_tarea, creador in filas:
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", padx=5, pady=2)
                    
                    # Configurar columnas igual que header
                    row.grid_columnconfigure(0, weight=2, minsize=200)
                    row.grid_columnconfigure(1, weight=1, minsize=100)
                    row.grid_columnconfigure(2, weight=1, minsize=120)
                    row.grid_columnconfigure(3, weight=1, minsize=120)
                    row.grid_columnconfigure(4, weight=0, minsize=80)
                    
                    # Título - clickeable
                    titulo_lbl = ctk.CTkLabel(row, text=titulo, anchor="w", cursor="hand2")
                    titulo_lbl.grid(row=0, column=0, padx=5, sticky="w")
                    
                    # Código RMA - clickeable
                    codigo_lbl = ctk.CTkLabel(row, text=codigo, anchor="w", cursor="hand2")
                    codigo_lbl.grid(row=0, column=1, padx=5, sticky="w")
                    
                    # Estado
                    estado_lbl = ctk.CTkLabel(row, text=estado_tarea, anchor="w")
                    estado_lbl.grid(row=0, column=2, padx=5, sticky="w")
                    
                    # Fecha vencimiento
                    fecha_lbl = ctk.CTkLabel(row, text=fecha_v if fecha_v else "Sin fecha", anchor="w")
                    fecha_lbl.grid(row=0, column=3, padx=5, sticky="w")
                    
                    # Efectos hover para toda la fila
                    def on_enter(e, r=row):
                        r.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                    def on_leave(e, r=row):
                        r.configure(fg_color="transparent")
                    
                    row.bind("<Enter>", on_enter)
                    row.bind("<Leave>", on_leave)
                    titulo_lbl.bind("<Enter>", on_enter)
                    titulo_lbl.bind("<Leave>", on_leave)
                    codigo_lbl.bind("<Enter>", on_enter)
                    codigo_lbl.bind("<Leave>", on_leave)
                    
                    # Click para abrir expediente
                    titulo_lbl.bind("<Button-1>", lambda e, c=codigo: abrir_expediente_por_codigo(c))
                    codigo_lbl.bind("<Button-1>", lambda e, c=codigo: abrir_expediente_por_codigo(c))
                    
                    # Botones de acción
                    acciones_frame = ctk.CTkFrame(row, fg_color="transparent")
                    acciones_frame.grid(row=0, column=4, padx=5)
                    
                    def make_done(tid=tid):
                        return lambda: marcar_completada(tid)
                    def make_delete(tid=tid):
                        return lambda: eliminar_tarea(tid)
                    
                    if estado_tarea != "Completado":
                        ctk.CTkButton(acciones_frame, text="✅", width=30, command=make_done(tid)).pack(side="left", padx=2)
                    ctk.CTkButton(acciones_frame, text="❌", width=30, command=make_delete(tid)).pack(side="left", padx=2)

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error cargando tareas: {e}")

        def marcar_completada(task_id):
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("UPDATE tareas SET estado = 'Completado', notificado = 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                actualizar_lista_tareas()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"No se pudo actualizar la tarea: {e}")

        def eliminar_tarea(task_id):
            if not messagebox.askyesno("Confirmar", "¿Eliminar esta tarea?"):
                return
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM tareas WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                actualizar_lista_tareas()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"No se pudo eliminar la tarea: {e}")

        filtro_estado.configure(command=lambda v=None: actualizar_lista_tareas())
        actualizar_lista_tareas()

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
        win.grab_set()

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
                vent_hist.grab_set()

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
                    rowf = ctk.CTkFrame(sf, fg_color="#FFFFFF" if idx % 2 == 0 else "#F7F7F7")
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
                    cur.execute("CREATE TABLE IF NOT EXISTS rma_proveedor (id INTEGER PRIMARY KEY, proveedor TEXT UNIQUE, estado TEXT)")
                    # Tabla de historial de proveedores: proveedor, estado, comentario, usuario, fecha
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                    )
                    conn.commit()
                except Exception:
                    # Si no podemos crearla en Turso u otro backend, seguimos sin persistencia
                    pass

                # Construir consulta: obtenemos proveedores distintos de rma_maestro
                # y left-join con rma_proveedor para traer el estado si existe.
                params = []
                search_clause = ""
                if filtro:
                    search_clause = " AND lower(rma_proveedor) LIKE ?"
                    params.append(f"%{filtro.lower()}%")

                direction = 'ASC' if sort_state.get('dir', 'asc') == 'asc' else 'DESC'

                sql = (
                    "SELECT p.proveedor, COALESCE(r.estado, '') as estado "
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
                lbl_nom = ctk.CTkLabel(header_row, text="PROVEEDOR", font=hf, anchor="w", cursor="hand2")
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

                for idx, (prov, estado_actual) in enumerate(rows):
                    nombre = prov
                    bg = colors[idx % 2]
                    row = ctk.CTkFrame(scroll, fg_color=bg)
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
                    except Exception:
                        # Si falla la creación del botón, ignoramos para no romper el listado
                        pass

                    # Hover
                    def on_enter(e, r=row):
                        r.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                    def on_leave(e, r=row, original_bg=bg):
                        r.configure(fg_color=original_bg)

                    row.bind("<Enter>", on_enter)
                    row.bind("<Leave>", on_leave)
                    lbl_nombre.bind("<Enter>", on_enter)
                    lbl_nombre.bind("<Leave>", on_leave)

                    # Click en nombre abre expedientes
                    lbl_nombre.bind("<Button-1>", lambda e, nombre=nombre: mostrar_expedientes_proveedor(nombre))

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

        def mostrar_expedientes_proveedor(proveedor_nombre):
            # Ventana que lista rma_maestro asociados al proveedor y permite editar (doble-clic)
            vent = ctk.CTkToplevel(self)
            vent.title(f"Expedientes - {proveedor_nombre}")
            vent.geometry("1000x650")
            vent.grab_set()

            cont = ctk.CTkFrame(vent)
            cont.pack(fill="both", expand=True, padx=10, pady=10)

            ctk.CTkLabel(cont, text=f"Expedientes asociados a: {proveedor_nombre}", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,8))

            sf = ctk.CTkScrollableFrame(cont)
            sf.pack(fill="both", expand=True)

            try:
                conn = connect_db()
                cur = conn.cursor()
                # Buscamos coincidencias por nombre (case-insensitive) o por id/string
                # Seleccionamos campos adicionales necesarios para exportar a Excel
                cur.execute(
                    "SELECT id, codigo_rma, cliente, numero_documento_cliente, modelo, ref_proveedor, fecha_emision, estado "
                    "FROM rma_maestro WHERE lower(Rma_Proveedor)=? OR Rma_Proveedor=? ORDER BY fecha_emision DESC",
                    (proveedor_nombre.lower(), proveedor_nombre)
                )
                filas = cur.fetchall()
                conn.close()

                def export_to_excel(rows, proveedor):
                    try:
                        # Construir DataFrame con la estructura solicitada
                        data = []
                        for r in rows:
                            # r: id, codigo_rma, cliente, numero_documento_cliente, modelo, ref_proveedor, fecha_emision, estado
                            (_id, codigo_rma, cliente, num_doc, modelo, ref_prov, fecha_emision, estado) = r
                            data.append({
                                'Nº Expediente': codigo_rma,
                                'Proveedor': proveedor,
                                'Cliente': cliente or '',
                                'Numero Documento Cliente': num_doc or '',
                                'Descripcion Articulo': modelo or '',
                                'Referencia': ref_prov or ''
                            })

                        if not data:
                            messagebox.showinfo('Exportar', 'No hay expedientes para exportar.')
                            return

                        df = pd.DataFrame(data)

                        # Preparar carpeta de guardado: Adjuntos_RMA/RMP
                        base_dir = os.path.join(os.path.dirname(__file__), 'Adjuntos_RMA')
                        rmp_dir = os.path.join(base_dir, 'RMP')
                        os.makedirs(rmp_dir, exist_ok=True)

                        # Nombre de archivo: proveedor.xlsx (sanitizar)
                        safe_name = ''.join(c for c in proveedor if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_name = safe_name.replace(' ', '_')
                        file_path = os.path.join(rmp_dir, f"{safe_name}.xlsx")

                        # Si ya existe, preguntar al usuario si desea sobrescribirlo (mostrar solo nombre)
                        if os.path.exists(file_path):
                            fname = os.path.basename(file_path)
                            if not messagebox.askyesno('Exportar', f'El archivo {fname} ya existe. ¿Desea sobreescribirlo?'):
                                return

                        # Guardar Excel y ajustar anchos de columna automáticamente
                        try:
                            # Usamos openpyxl a través de pandas ExcelWriter para poder ajustar columnas
                            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False, sheet_name='Expedientes')
                                workbook = writer.book
                                worksheet = writer.sheets['Expedientes']

                                # Ajustar ancho: calcular longitud máxima entre valores y encabezado
                                from openpyxl.utils import get_column_letter
                                for i, col in enumerate(df.columns):
                                    if df.empty:
                                        max_len = len(str(col))
                                    else:
                                        # map len over stringified values, ignore None
                                        col_max = df[col].astype(str).map(len).max()
                                        max_len = max(int(col_max) if col_max is not None else 0, len(str(col)))
                                    # añadir un pequeño padding y limitar a un ancho razonable
                                    adjusted_width = min(max_len + 2, 60)
                                    worksheet.column_dimensions[get_column_letter(i+1)].width = adjusted_width

                            messagebox.showinfo('Exportar', f'Exportado correctamente: {file_path}')

                            # Registrar en historial del proveedor que se exportó el listado a Excel
                            try:
                                connh = connect_db()
                                curh = connh.cursor()
                                # Conteo de expedientes y lista de códigos RMA
                                try:
                                    rma_codes = [str(r[1]) for r in rows if len(r) > 1 and r[1] is not None]
                                except Exception:
                                    rma_codes = []
                                count = len(rows)
                                codes_str = ', '.join(rma_codes)
                                # Truncar si la lista es muy larga para no crear comentarios gigantes
                                if len(codes_str) > 500:
                                    codes_str = codes_str[:500] + '...'

                                comentario = f'Exportado {count} expedientes a Excel: {os.path.basename(file_path)}'
                                if codes_str:
                                    comentario += f' (RMAs: {codes_str})'

                                usuario = getattr(self, 'username', '') if hasattr(self, 'username') else ''
                                # Insertamos comentario; marcamos estado como 'Exportado'
                                curh.execute(
                                    "INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)",
                                    (proveedor, 'Exportado', comentario, usuario)
                                )

                                # Actualizar la tabla rma_proveedor para reflejar el nuevo estado
                                try:
                                    try:
                                        curh.execute(
                                            "INSERT INTO rma_proveedor (proveedor, estado) VALUES (?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                                            (proveedor, 'Exportado')
                                        )
                                    except Exception:
                                        # Fallback a UPDATE/INSERT si el dialecto no soporta ON CONFLICT
                                        curh.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", ('Exportado', proveedor))
                                        if getattr(curh, 'rowcount', 0) == 0:
                                            curh.execute("INSERT INTO rma_proveedor (proveedor, estado) VALUES (?, ?)", (proveedor, 'Exportado'))
                                except Exception:
                                    # No bloqueamos la exportación por este error; lo registramos en consola
                                    try:
                                        print('Warning: no se pudo actualizar rma_proveedor estado a Exportado')
                                    except Exception:
                                        pass
                                connh.commit()
                                connh.close()
                                # Refrescar la lista de proveedores para que muestre el nuevo estado
                                try:
                                    cargar_proveedores()
                                except Exception:
                                    pass
                            except Exception as e:
                                # No interrumpimos la exportación por un fallo en el historial; registramos en consola
                                try:
                                    print('Warning: no se pudo escribir en rma_proveedor_hist:', e)
                                except Exception:
                                    pass
                        except Exception as e:
                            messagebox.showerror('Exportar', f'Error exportando a Excel (asegúrate de tener openpyxl): {e}')
                    except Exception as e:
                        messagebox.showerror('Exportar', f'Error exportando a Excel: {e}')

                # Encabezado
                head = ctk.CTkFrame(sf)
                head.pack(fill="x", padx=5, pady=(0,5))
                # Botón de exportar a Excel
                try:
                    ctk.CTkButton(cont, text="Exportar a Excel", command=lambda rows=filas, p=proveedor_nombre: export_to_excel(rows, p)).pack(anchor="ne")
                except Exception:
                    pass
                head.grid_columnconfigure(0, weight=1, minsize=180)
                head.grid_columnconfigure(1, weight=2, minsize=300)
                head.grid_columnconfigure(2, weight=1, minsize=140)
                head.grid_columnconfigure(3, weight=1, minsize=140)

                hf = ctk.CTkFont(weight="bold")
                ctk.CTkLabel(head, text="CÓDIGO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
                ctk.CTkLabel(head, text="CLIENTE", font=hf).grid(row=0, column=1, padx=5, sticky="w")
                ctk.CTkLabel(head, text="FECHA", font=hf).grid(row=0, column=2, padx=5, sticky="w")
                ctk.CTkLabel(head, text="ESTADO", font=hf).grid(row=0, column=3, padx=5, sticky="w")

                colors = ("#FFFFFF", "#F7F7F7")
                for idx, r in enumerate(filas):
                    # filas: id, codigo_rma, cliente, numero_documento_cliente, modelo, ref_proveedor, fecha_emision, estado
                    try:
                        rma_id, codigo, cliente, num_doc, modelo, ref_prov, fecha, estado = r
                    except Exception:
                        # Fallback si la tupla no tiene la forma esperada
                        # Intentamos mapear por posición conocida
                        vals = list(r)
                        rma_id = vals[0] if len(vals) > 0 else None
                        codigo = vals[1] if len(vals) > 1 else ''
                        cliente = vals[2] if len(vals) > 2 else ''
                        fecha = vals[3] if len(vals) > 3 else ''
                        estado = vals[4] if len(vals) > 4 else ''

                    bg = colors[idx % 2]
                    row = ctk.CTkFrame(sf, fg_color=bg)
                    row.pack(fill="x", padx=5, pady=2)
                    row.grid_columnconfigure(0, weight=1, minsize=180)
                    row.grid_columnconfigure(1, weight=2, minsize=300)
                    row.grid_columnconfigure(2, weight=1, minsize=140)
                    row.grid_columnconfigure(3, weight=1, minsize=140)
                    row.grid_columnconfigure(4, weight=0, minsize=100)

                    lbl_codigo = ctk.CTkLabel(row, text=codigo, anchor="w", cursor="hand2")
                    lbl_codigo.grid(row=0, column=0, padx=5, sticky="w")
                    lbl_cliente = ctk.CTkLabel(row, text=cliente if cliente else "-", anchor="w")
                    lbl_cliente.grid(row=0, column=1, padx=5, sticky="w")
                    lbl_fecha = ctk.CTkLabel(row, text=fecha if fecha else "-", anchor="w")
                    lbl_fecha.grid(row=0, column=2, padx=5, sticky="w")
                    lbl_estado = ctk.CTkLabel(row, text=estado if estado else "-", anchor="w")
                    lbl_estado.grid(row=0, column=3, padx=5, sticky="w")

                    acciones = ctk.CTkFrame(row, fg_color="transparent")
                    acciones.grid(row=0, column=4, padx=5)
                    # Botón Editar que abre el expediente en el panel principal
                    ctk.CTkButton(acciones, text="Editar", width=80, command=lambda rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy())).pack(side="left", padx=4)

                    # Hover
                    def on_enter(e, r=row):
                        r.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                    def on_leave(e, r=row, original_bg=bg):
                        r.configure(fg_color=original_bg)

                    row.bind("<Enter>", on_enter)
                    row.bind("<Leave>", on_leave)

                    # Doble clic también abre editor del RMA
                    row.bind("<Double-Button-1>", lambda e, rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy()))
                    lbl_codigo.bind("<Double-Button-1>", lambda e, rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy()))

            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"No se pudieron cargar expedientes: {e}")

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
        win.grab_set()

        main = ctk.CTkFrame(win)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(main)
        header.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(header, text="Listado de Artículos", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")

        # Frame para la lista con scroll
        list_frame = ctk.CTkFrame(main)
        list_frame.pack(fill="both", expand=True)

        canvas = ctk.CTkCanvas(list_frame, borderwidth=0, highlightthickness=0)
        # Use a native Frame inside a canvas for scrollable content
        try:
            # If customtkinter doesn't expose CTkCanvas in user's version, fallback to tkinter.Canvas
            from tkinter import Canvas as _Canvas
            canvas = _Canvas(list_frame, borderwidth=0, highlightthickness=0)
        except Exception:
            pass

        sb = ctk.CTkScrollbar(list_frame, orientation="vertical", command=lambda *args: canvas.yview(*args))
        canvas.configure(yscrollcommand=lambda *args: sb.set(*args))
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = ctk.CTkFrame(canvas)
        # Create window inside canvas
        # Create window inside canvas and ensure it resizes to canvas width so headers and rows align
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

        # Consultar DB: contar expedientes por referencia de artículo
        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT referencia_articulo, COUNT(DISTINCT rma_maestro.id) as expedientes_count
                FROM rma_detalles
                INNER JOIN rma_maestro ON rma_detalles.rma_id = rma_maestro.id
                WHERE referencia_articulo IS NOT NULL AND TRIM(referencia_articulo) != ''
                GROUP BY referencia_articulo
                ORDER BY expedientes_count DESC, referencia_articulo ASC
            """)
            filas = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error BD", f"No se pudieron cargar los artículos: {e}")
            return

        # Encabezado (usar grid y configurar pesos para alinear con las filas)
        header_frame = ctk.CTkFrame(sf)
        header_frame.pack(fill="x", padx=5, pady=(0,4))
        hf = ctk.CTkFont(weight="bold")
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

            bg = colors[idx % 2]
            rf = ctk.CTkFrame(sf, fg_color=bg)
            rf.pack(fill="x", padx=5, pady=2)
            rf.grid_columnconfigure(0, weight=3, minsize=300)
            rf.grid_columnconfigure(1, weight=1, minsize=80)

            lbl_ref = ctk.CTkLabel(rf, text=referencia or '-', anchor="w", cursor="hand2")
            lbl_ref.grid(row=0, column=0, padx=5, sticky="w")
            lbl_cnt = ctk.CTkLabel(rf, text=str(cnt), anchor="w")
            lbl_cnt.grid(row=0, column=1, padx=5, sticky="w")

            btn_ver = ctk.CTkButton(rf, text="Ver Expedientes", width=140, command=lambda r=referencia: self.mostrar_expedientes_por_articulo(r))
            btn_ver.grid(row=0, column=2, padx=6)

            # Hover effect
            def on_enter(e, w=rf):
                try:
                    w.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                except Exception:
                    pass
            def on_leave(e, w=rf, original=bg):
                try:
                    w.configure(fg_color=original)
                except Exception:
                    pass

            rf.bind("<Enter>", on_enter)
            rf.bind("<Leave>", on_leave)
            lbl_ref.bind("<Double-Button-1>", lambda e, r=referencia: self.mostrar_expedientes_por_articulo(r))

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
        vent.grab_set()

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

        # Consultar expedientes asociados
        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT T2.id, T2.codigo_rma, T2.cliente, T2.numero_documento_cliente, T1.estado_producto
                FROM rma_detalles T1
                JOIN rma_maestro T2 ON T1.rma_id = T2.id
                WHERE T1.referencia_articulo = ?
                ORDER BY T2.fecha_emision DESC
            """, (referencia,))
            filas = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error BD", f"No se pudieron cargar expedientes: {e}")
            return

        # Header
        head = ctk.CTkFrame(sf)
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

            bg = colors[idx % 2]
            rowf = ctk.CTkFrame(sf, fg_color=bg)
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
            ctk.CTkButton(acciones, text="Abrir", width=90, command=lambda rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy())).pack(side="left", padx=4)

            # Hover
            def on_ent(e, r=rowf):
                try:
                    r.configure(fg_color=("#E9ECEF", "#E9ECEF"))
                except Exception:
                    pass
            def on_lve(e, r=rowf, original=bg):
                try:
                    r.configure(fg_color=original)
                except Exception:
                    pass

            rowf.bind("<Enter>", on_ent)
            rowf.bind("<Leave>", on_lve)
            rowf.bind("<Double-Button-1>", lambda e, rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy()))
            lbl_codigo.bind("<Double-Button-1>", lambda e, rid=rma_id: (self.mostrar_nuevo_rma(rma_id=rid), vent.destroy()))

    def comprobar_tareas_vencidas(self):
        """Comprueba tareas vencidas para el usuario actual y muestra notificaciones (sistema si es posible)."""
        try:
            hoy = datetime.date.today().strftime("%Y-%m-%d")
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT id, codigo_rma, titulo, fecha_vencimiento FROM tareas WHERE creado_por = ? AND notificado = 0 AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento <= ?", (self.username, hoy))
            filas = cur.fetchall()
            if filas:
                mensajes = []
                ids = []
                for tid, codigo, titulo, fecha in filas:
                    mensajes.append(f"{fecha} - {titulo} [{codigo}]")
                    ids.append(tid)
                texto = "Tienes tareas vencidas o para hoy:\n" + "\n".join(mensajes)
                # Intentar notificación nativa en Windows
                try:
                    if hasattr(self, 'toaster') and self.toaster:
                        # win10toast limita longitud, mostramos un resumen
                        resumen = "; ".join(mensajes[:5])
                        self.toaster.show_toast("Tareas vencidas/hoy", resumen, duration=10, threaded=True)
                    else:
                        raise Exception("No toaster")
                except Exception:
                    # Fallback a messagebox si no hay toaster
                    messagebox.showinfo("Tareas vencidas / hoy", texto)

                # Marcar como notificado para no repetir
                for tid in ids:
                    cur.execute("UPDATE tareas SET notificado = 1 WHERE id = ?", (tid,))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error comprobando tareas vencidas: {e}")

    def programar_chequeo_tareas(self, intervalo_ms=1_800_000):
        """Programa la comprobación periódica de tareas vencidas (por defecto cada 30 minutos)."""
        try:
            # Llamamos a la comprobación
            self.comprobar_tareas_vencidas()
            # Reprogramar
            self.after(intervalo_ms, lambda: self.programar_chequeo_tareas(intervalo_ms))
        except Exception as e:
            print(f"Error programando chequeo tareas: {e}")
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
        self.botones_stats = {
            "Expedientes Completados (Rentabilidad)": self.mostrar_expedientes_completados,
            "Abonos por Cliente y Periodo": self.mostrar_abonos_cliente,
            "Referencia (Incidencia)": self.mostrar_articulos_incidencia
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
        """
        Estadística: Muestra los clientes con más expedientes COMPLETADOS, 
        el total de expedientes y la suma de su rentabilidad, con filtros de fecha y cliente.
        """
        from datetime import datetime
        
        self.limpiar_marco_stats()
        if not self.main_stats_frame: return
        
        ctk.CTkLabel(self.main_stats_frame, 
                     text="INFORME DE EXPEDIENTES RMA COMPLETADOS (POR CLIENTE)", 
                     font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)

        # --- 1. Marco de Controles y Total ---
        controles_frame = ctk.CTkFrame(self.main_stats_frame)
        controles_frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Configuración de columnas
        controles_frame.grid_columnconfigure((0, 2, 4), weight=0) # Etiquetas y Botones
        controles_frame.grid_columnconfigure((1, 3, 5), weight=1) # Entries (expandibles)

        # FILTRO 1: Fecha Inicial (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Inicial:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.fecha_inicial_exp_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 01/01/2024")
        self.fecha_inicial_exp_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        # FILTRO 2: Fecha Final (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Final:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.fecha_final_exp_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 31/12/2024")
        self.fecha_final_exp_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")
        
        # FILTRO 3: Cliente - Fila 0
        ctk.CTkLabel(controles_frame, text="Buscar Cliente:").grid(row=0, column=4, padx=(10, 5), pady=5, sticky="w")
        self.cliente_filtro_exp_entry = ctk.CTkEntry(controles_frame, placeholder_text="Escriba parte del cliente...")
        self.cliente_filtro_exp_entry.grid(row=0, column=5, padx=(0, 10), pady=5, sticky="ew")
        
        # Botón para aplicar filtros - Fila 1
        ctk.CTkButton(
            controles_frame, 
            text="Aplicar Filtros", 
            command=self._cargar_datos_expedientes_completados
        ).grid(row=1, column=0, columnspan=2, padx=(0, 5), pady=10, sticky="ew")
        
        # Etiqueta para el Total de Rentabilidad - Fila 1
        ctk.CTkLabel(controles_frame, text="Total de Rentabilidad (€):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=10, pady=10, sticky="w")
        self.lbl_total_rentabilidad = ctk.CTkLabel(controles_frame, text="0.00 €", font=ctk.CTkFont(weight="bold", size=16), text_color="#2ecc71") # Color verde para el dinero
        self.lbl_total_rentabilidad.grid(row=1, column=3, padx=(0, 10), pady=10, sticky="w")
        
        # --- 2. Marco Contenedor de Resultados ---
        self.tabla_expedientes_frame = ctk.CTkFrame(self.main_stats_frame)
        self.tabla_expedientes_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 3. Cargar los datos iniciales
        self._cargar_datos_expedientes_completados()
    
    def _cargar_datos_expedientes_completados(self):
        """
        Consulta la base de datos para obtener expedientes completados, 
        aplica filtros de fecha y cliente, y calcula el total.
        """
        from datetime import datetime
        
        # 1. Obtener los valores de los filtros
        cliente_filtro = self.cliente_filtro_exp_entry.get().strip()
        fecha_inicial_str = self.fecha_inicial_exp_entry.get().strip()
        fecha_final_str = self.fecha_final_exp_entry.get().strip()
        
        # Función auxiliar de validación de fecha (copiada de 'mostrar_articulos_incidencia')
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

        for widget in self.tabla_expedientes_frame.winfo_children():
            widget.destroy()

        # 3. Construcción dinámica de la consulta SQL y los parámetros
        
        # Seleccionamos: Cliente, Conteo de Expedientes, Suma de Precios Totales (Rentabilidad)
        sql_query_base = """
            SELECT 
                cliente, 
                COUNT(id) AS total_expedientes,
                SUM(precio_total_expediente) AS suma_total_rentabilidad
            FROM 
                rma_maestro
            WHERE 
                fecha_gestion IS NOT NULL  -- CRÍTICO: Solo expedientes COMPLETADOS
        """
        
        condiciones = []
        parametros = []
        
        # 3.1. Filtro por Cliente
        if cliente_filtro:
            condiciones.append("cliente LIKE ?")
            parametros.append(f"%{cliente_filtro}%")
            
        # 3.2. Filtro por Rango de Fechas (usando la conversión a YYYY-MM-DD para SQLite)
        if fecha_inicial_db:
            # Reorganiza: fecha_gestion (DD/MM/AAAA) -> YYYY-MM-DD
            condiciones.append("SUBSTR(fecha_gestion, 7, 4) || '-' || SUBSTR(fecha_gestion, 4, 2) || '-' || SUBSTR(fecha_gestion, 1, 2) >= ?")
            # El parámetro se convierte a YYYY-MM-DD para la comparación
            parametros.append(datetime.strptime(fecha_inicial_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        if fecha_final_db:
            condiciones.append("SUBSTR(fecha_gestion, 7, 4) || '-' || SUBSTR(fecha_gestion, 4, 2) || '-' || SUBSTR(fecha_gestion, 1, 2) <= ?")
            parametros.append(datetime.strptime(fecha_final_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        # 4. Ensamblaje y Ejecución
        
        if condiciones:
            sql_query_base += " AND " + " AND ".join(condiciones)

        sql_query_final = sql_query_base + """
            GROUP BY 
                cliente
            ORDER BY 
                total_expedientes DESC
            LIMIT 50; 
        """

        try:
            cursor.execute(sql_query_final, parametros)
            datos_raw = cursor.fetchall()
            
            # 5. Calcular la suma total del listado mostrado
            # La columna 2 de los datos (índice 2) contiene la suma total_rentabilidad de cada cliente
            suma_total_global = sum(fila[2] for fila in datos_raw if fila[2] is not None)

            # 6. Actualizar la etiqueta del total
            self.lbl_total_rentabilidad.configure(text=f"{suma_total_global:,.2f} €") 

            # 7. Dibujar la tabla
            self.mostrar_tabla_estadistica(
                datos_raw, 
                columnas=["CLIENTE", "TOTAL EXPEDIENTES", "RENTABILIDAD TOTAL (€)"],
                export_filename="Expedientes_Completados_Rentabilidad",
                frame=self.tabla_expedientes_frame, 
                formato_moneda=True # La última columna es monetaria
            )

            if not datos_raw:
                 ctk.CTkLabel(self.tabla_expedientes_frame, 
                              text="No se encontraron expedientes completados con los filtros aplicados.",
                              font=ctk.CTkFont(size=14)
                 ).pack(pady=40)

        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Error SQL: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado al cargar expedientes completados: {e}")
        finally:
            if conn:
                conn.close()

    # ==============================================================================
    # RESTO DE MÉTODOS AUXILIARES Y PLACEHOLDERS (SIN MODIFICAR, exceptuando la nueva llamada)
    # ==============================================================================

    # El método original 'mostrar_expedientes_cliente' ha sido eliminado/reemplazado.
    
    def mostrar_abonos_cliente(self):
        """
        Estadística: Muestra la suma del 'precio_total_expediente' por Cliente 
        y permite filtrar por un 'Periodo' (rango de fecha).
        """
        # 1. Preparación de la interfaz
        self.limpiar_marco_stats()
        if not self.main_stats_frame: return
        
        ctk.CTkLabel(self.main_stats_frame, 
                     text="ABONOS POR CLIENTE Y PERIODO", 
                     font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # --- 2. Marco de Controles Principales (Filtros de Fecha) ---
        controles_frame = ctk.CTkFrame(self.main_stats_frame)
        controles_frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Configuración de columnas
        controles_frame.grid_columnconfigure((0, 2), weight=0) # Etiquetas (fijas)
        controles_frame.grid_columnconfigure((1, 3), weight=1)    # Entries de Fecha (expandible)
        controles_frame.grid_columnconfigure(4, weight=0) # Botón (fijo)

        # FILTRO 1: Fecha Inicial (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Inicial (DD/MM/AAAA):").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        # Almacenamos las entries en la clase para poder acceder a ellas desde el helper
        self.abono_fecha_inicial_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 01/01/2024")
        self.abono_fecha_inicial_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        # FILTRO 2: Fecha Final (DD/MM/AAAA) - Fila 0
        ctk.CTkLabel(controles_frame, text="Fecha Final (DD/MM/AAAA):").grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.abono_fecha_final_entry = ctk.CTkEntry(controles_frame, placeholder_text="Ej: 31/12/2024")
        self.abono_fecha_final_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="ew")
        
        # Botón para aplicar filtros - Fila 0
        ctk.CTkButton(
            controles_frame, 
            text="Aplicar Filtros", 
            command=self._cargar_datos_abonos
        ).grid(row=0, column=4, padx=(10, 0), pady=5)
        
        # FILTRO 3: Resultado Expediente - Fila 1
        opciones_resultado = ["Todos"] + (self.OPCIONES.get("Resultado_Expediente", []) if hasattr(self, 'OPCIONES') else [])
        ctk.CTkLabel(controles_frame, text="Resultado Expediente:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.abono_resultado_option = ctk.CTkOptionMenu(controles_frame, values=opciones_resultado)
        self.abono_resultado_option.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.abono_resultado_option.set(opciones_resultado[0])
        
        # --- 3. Marco donde se dibujará la tabla de resultados ---
        self.abonos_tabla_resultados_frame = ctk.CTkFrame(self.main_stats_frame)
        self.abonos_tabla_resultados_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.abonos_tabla_resultados_frame.grid_columnconfigure(0, weight=1) # Permite que el contenido se expanda

        # 4. Cargar los datos iniciales (sin filtros)
        self._cargar_datos_abonos()

    def _cargar_datos_abonos(self, event=None):
        """
        Consulta la base de datos, suma 'precio_total_expediente' por cliente y 
        aplica filtros de rango de fecha.
        """
        
        # 1. Obtener y validar las fechas (DD/MM/AAAA)
        fecha_inicial_str = self.abono_fecha_inicial_entry.get().strip()
        fecha_final_str = self.abono_fecha_final_entry.get().strip()

        # Función local para validar fecha
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

        # 2. Conexión y Limpieza del Marco de Resultados
        conn, cursor = self.master.conectar_db()
        if not conn: 
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        for widget in self.abonos_tabla_resultados_frame.winfo_children():
            widget.destroy()

        # 3. Construcción dinámica de la consulta SQL y los parámetros
        
        # IMPORTANTE: Usamos SUM(precio_total_expediente) en lugar del error 'abono'
        sql_query_base = """
            SELECT 
                cliente, 
                SUM(precio_total_expediente) AS total_abono 
            FROM 
                rma_maestro
            WHERE 1=1
        """
        
        condiciones = []
        parametros = []
        
        # 3.1. Filtro por Rango de Fechas (Convierte la fecha de la DB a YYYY-MM-DD para comparación)
        if fecha_inicial_db:
            # Reorganiza: fecha_gestion (DD/MM/AAAA) -> YYYY-MM-DD
            condiciones.append("SUBSTR(fecha_gestion, 7, 4) || '-' || SUBSTR(fecha_gestion, 4, 2) || '-' || SUBSTR(fecha_gestion, 1, 2) >= ?")
            # El parámetro se convierte a YYYY-MM-DD para la comparación
            parametros.append(datetime.strptime(fecha_inicial_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        if fecha_final_db:
            condiciones.append("SUBSTR(fecha_gestion, 7, 4) || '-' || SUBSTR(fecha_gestion, 4, 2) || '-' || SUBSTR(fecha_gestion, 1, 2) <= ?")
            parametros.append(datetime.strptime(fecha_final_db, '%d/%m/%Y').strftime('%Y-%m-%d'))

        # 3.2. Filtro por Resultado de Expediente (si se seleccionó uno distinto de 'Todos')
        try:
            if hasattr(self, 'abono_resultado_option'):
                resultado_seleccionado = self.abono_resultado_option.get()
            elif hasattr(self, 'abono_resultado_optionmenu'):
                resultado_seleccionado = self.abono_resultado_optionmenu.get()
            else:
                resultado_seleccionado = None

            if resultado_seleccionado and resultado_seleccionado != 'Todos':
                # Comparación case-insensitive para mayor robustez
                condiciones.append("lower(resultado_expediente) = ?")
                parametros.append(resultado_seleccionado.strip().lower())
        except Exception:
            # Si algo falla al leer el widget, ignoramos el filtro (la consulta seguirá funcionando)
            pass

        # 4. Ensamblaje y Ejecución
        
        if condiciones:
            sql_query_base += " AND " + " AND ".join(condiciones)

        sql_query_final = sql_query_base + """
            GROUP BY 
                cliente
            ORDER BY 
                total_abono DESC; 
        """

        try:
            cursor.execute(sql_query_final, parametros)
            datos_raw = cursor.fetchall()
            
            datos_formateados = list(datos_raw)

            # 5. Dibujar la tabla
            self.mostrar_tabla_estadistica(
                datos_formateados, 
                columnas=["CLIENTE", "TOTAL ABONADO (€)"],
                export_filename="Abonos_Por_Cliente",
                frame=self.abonos_tabla_resultados_frame, 
                formato_moneda=True # Activamos el formato de moneda para esta estadística
            )

            if not datos_formateados:
                 ctk.CTkLabel(self.abonos_tabla_resultados_frame, 
                              text="No se encontraron datos con los filtros aplicados.",
                              font=ctk.CTkFont(size=14)
                 ).pack(pady=40)

        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Error SQL al cargar abonos por cliente: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado: {e}")
        finally:
            if conn:
                conn.close()

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
            

    def limpiar_marco_stats(self):
        """Método auxiliar necesario para limpiar el marco principal antes de cargar una estadística."""
        for widget in self.main_stats_frame.winfo_children():
            widget.destroy()
    
    def exportar_a_excel(self, datos, columnas, filename):
        """Exporta los datos de la estadística actual a un archivo Excel."""
        if not datos:
            messagebox.showwarning("Exportar", "No hay datos para exportar.")
            return

        # 1. Crear el DataFrame de Pandas
        df = pd.DataFrame(datos, columns=columnas)
        
        # 2. Abrir diálogo para guardar archivo
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Archivos Excel", "*.xlsx")],
            initialfile=filename
        )
        
        if path:
            try:
                # 3. Guardar en Excel (openpyxl se usa internamente por pandas)
                df.to_excel(path, index=False) # index=False evita añadir la columna de índice de pandas
                messagebox.showinfo("Exportación Exitosa", f"Datos exportados a:\n{path}")
            except Exception as e:
                messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo Excel.\nError: {e}")

    def mostrar_tabla_estadistica(self, datos, columnas, export_filename, frame, formato_moneda=False):
        """
        Dibuja un listado genérico de resultados usando un CTkScrollableFrame 
        y añade el botón de exportación.
        """
        
        if not datos:
            ctk.CTkLabel(frame, text="No se encontraron datos para esta estadística.", text_color="gray").pack(pady=20)
            return

        # Función para abrir el expediente al hacer clic en el código RMA
        def abrir_expediente(codigo_rma):
            """Abre el expediente en una nueva ventana independiente para consulta/edición.

            La ventana muestra un resumen y permite abrir el expediente en el panel principal si
            el usuario prefiere editar en la interfaz habitual.
            """
            conn, cursor = self.master.conectar_db()
            if not conn:
                return

            try:
                # Obtener datos maestro
                cursor.execute("SELECT id, codigo_rma, cliente, fecha_gestion, motivo FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
                maestro = cursor.fetchone()
                if not maestro:
                    messagebox.showerror("Error", f"No se encontró el expediente con código {codigo_rma}")
                    return

                rma_id = maestro[0]
                codigo = maestro[1]
                cliente = maestro[2]
                fecha = maestro[3]
                motivo = maestro[4]

                # Crear ventana independiente
                vent = ctk.CTkToplevel(self)
                vent.title(f"Expediente {codigo}")
                vent.geometry("900x700")
                vent.minsize(700, 500)

                # Contenedor principal
                cont = ctk.CTkFrame(vent)
                cont.pack(fill="both", expand=True, padx=12, pady=12)

                # Cabecera - campos editables
                header_frame = ctk.CTkFrame(cont)
                header_frame.pack(fill="x", pady=(0,6))

                ctk.CTkLabel(header_frame, text=f"Nº EXPEDIENTE: {codigo}", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,6))

                ctk.CTkLabel(header_frame, text="Cliente:").grid(row=1, column=0, sticky="w")
                entry_cliente = ctk.CTkEntry(header_frame)
                entry_cliente.grid(row=1, column=1, sticky="ew", padx=(8,0))
                entry_cliente.insert(0, str(cliente) if cliente is not None else "")

                ctk.CTkLabel(header_frame, text="Nº Documento:").grid(row=2, column=0, sticky="w")
                entry_num_doc = ctk.CTkEntry(header_frame)
                entry_num_doc.grid(row=2, column=1, sticky="ew", padx=(8,0))
                # intentar rellenar si existe
                try:
                    entry_num_doc.insert(0, str(maestro[3]) if maestro[3] is not None else "")
                except Exception:
                    pass

                ctk.CTkLabel(header_frame, text="Fecha Gestión:").grid(row=3, column=0, sticky="w")
                entry_fecha = ctk.CTkEntry(header_frame)
                entry_fecha.grid(row=3, column=1, sticky="ew", padx=(8,0))
                entry_fecha.insert(0, str(fecha) if fecha is not None else "")

                ctk.CTkLabel(header_frame, text="Email contacto:").grid(row=4, column=0, sticky="w")
                entry_email = ctk.CTkEntry(header_frame)
                entry_email.grid(row=4, column=1, sticky="ew", padx=(8,0))
                # maestro[6] será email si está presente
                try:
                    entry_email.insert(0, str(maestro[6]) if len(maestro) > 6 and maestro[6] is not None else "")
                except Exception:
                    pass

                header_frame.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(cont, text="Motivo:").pack(anchor="w")
                txt_motivo = ctk.CTkTextbox(cont, height=80)
                txt_motivo.pack(fill="x", pady=(0,8))
                try:
                    txt_motivo.insert("1.0", str(motivo) if motivo is not None else "")
                except Exception:
                    pass

                # Mostrar artículos relacionados (lista simple)
                ctk.CTkLabel(cont, text="Artículos asociados:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(6,4))
                art_frame = ctk.CTkScrollableFrame(cont)
                art_frame.pack(fill="both", expand=True, pady=(0,8))

                # Obtener detalles incluyendo su id para permitir edición
                cursor.execute("SELECT id, referencia_articulo, cantidad_segun_documento, cantidad_entregada, estado_producto FROM rma_detalles WHERE rma_id = ?", (rma_id,))
                detalles = cursor.fetchall()
                if detalles:
                    for d in detalles:
                        det_id = d[0]
                        ref = d[1]
                        cant_doc = d[2]
                        cant_ent = d[3]
                        estado = d[4]

                        row_fr = ctk.CTkFrame(art_frame)
                        row_fr.pack(fill="x", padx=4, pady=2)

                        lbl = ctk.CTkLabel(row_fr, text=f"{ref} — Doc: {cant_doc} — Ent: {cant_ent} — Estado: {estado}")
                        lbl.pack(side="left", anchor="w")

                        def make_editar(did, lbl_widget):
                            def editar():
                                ed_win = ctk.CTkToplevel(vent)
                                ed_win.title(f"Editar artículo {ref}")
                                ed_win.geometry("420x200")

                                ctk.CTkLabel(ed_win, text=f"Referencia: {ref}").pack(anchor="w", padx=8, pady=(8,4))
                                ctk.CTkLabel(ed_win, text="Cantidad Entregada:").pack(anchor="w", padx=8)
                                ent_cant = ctk.CTkEntry(ed_win)
                                ent_cant.pack(fill="x", padx=8, pady=(0,6))
                                ent_cant.insert(0, str(cant_ent) if cant_ent is not None else "")

                                ctk.CTkLabel(ed_win, text="Estado Producto:").pack(anchor="w", padx=8)
                                ent_estado = ctk.CTkEntry(ed_win)
                                ent_estado.pack(fill="x", padx=8, pady=(0,6))
                                ent_estado.insert(0, str(estado) if estado is not None else "")

                                def guardar_detalle():
                                    new_cant = ent_cant.get().strip()
                                    new_estado = ent_estado.get().strip()
                                    try:
                                        conn2 = connect_db()
                                        cur2 = conn2.cursor()
                                        cur2.execute("UPDATE rma_detalles SET cantidad_entregada = ?, estado_producto = ? WHERE id = ?", (new_cant, new_estado, did))
                                        conn2.commit()
                                        conn2.close()
                                        # Actualizar etiqueta
                                        lbl_widget.configure(text=f"{ref} — Doc: {cant_doc} — Ent: {new_cant} — Estado: {new_estado}")
                                        ed_win.destroy()
                                        # Refrescar los datos de la tabla
                                        refrescar_estadisticas()
                                    except sqlite3.Error as e:
                                        messagebox.showerror("Error BD", f"No se pudo actualizar el detalle: {e}")

                                ctk.CTkButton(ed_win, text="Guardar", command=guardar_detalle).pack(side="left", padx=12, pady=12)
                                ctk.CTkButton(ed_win, text="Cerrar", command=ed_win.destroy).pack(side="right", padx=12, pady=12)

                            return editar

                        btn_ed = ctk.CTkButton(row_fr, text="Editar", command=make_editar(det_id, lbl))
                        btn_ed.pack(side="right")
                else:
                    ctk.CTkLabel(art_frame, text="No hay artículos registrados.").pack(pady=8)

                # Botones en el footer de la ventana
                footer = ctk.CTkFrame(cont)
                footer.pack(fill="x", pady=(8,0))

                # Botones en el footer de la ventana
                # Función para refrescar la tabla de estadísticas
                def refrescar_estadisticas():
                    """Refresca los datos de la tabla de estadísticas."""
                    # Limpiar y recargar los datos
                    try:
                        # Re-ejecutar la carga de datos actual
                        self._cargar_datos_articulos_incidencia()
                    except Exception as e:
                        print(f"Error al refrescar estadísticas: {e}")

                def guardar_maestro():
                    new_cliente = entry_cliente.get().strip()
                    new_num_doc = entry_num_doc.get().strip()
                    new_fecha = entry_fecha.get().strip()
                    new_email = entry_email.get().strip()
                    new_motivo = txt_motivo.get("1.0", "end-1c").strip()

                    try:
                        conn2 = connect_db()
                        cur2 = conn2.cursor()
                        cur2.execute(
                            "UPDATE rma_maestro SET cliente = ?, numero_documento_cliente = ?, fecha_gestion = ?, motivo = ?, email_de_contacto = ? WHERE id = ?",
                            (new_cliente, new_num_doc, new_fecha, new_motivo, new_email, rma_id)
                        )
                        conn2.commit()
                        conn2.close()
                        messagebox.showinfo("Guardado", "Expediente actualizado correctamente.")
                        # Refrescar datos de la tabla
                        refrescar_estadisticas()
                    except sqlite3.Error as e:
                        messagebox.showerror("Error BD", f"No se pudo actualizar el expediente: {e}")

                def abrir_en_panel():
                    try:
                        self.mostrar_nuevo_rma(rma_id)
                        vent.destroy()  # Cerrar la ventana actual al abrir en panel principal
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo abrir en el panel principal: {e}")

                ctk.CTkButton(footer, text="Guardar cambios", command=guardar_maestro).pack(side="left")
                ctk.CTkButton(footer, text="✏️ Abrir en panel principal", command=abrir_en_panel).pack(side="left", padx=8)
                ctk.CTkButton(footer, text="Cerrar", command=vent.destroy).pack(side="right")

            except sqlite3.Error as e:
                messagebox.showerror("Error de Base de Datos", f"Error al consultar el expediente: {e}")
            finally:
                conn.close()

        # Mensaje informativo para el usuario
        ctk.CTkLabel(frame, text="Pulse el Nº EXPEDIENTE (primera columna) para abrirlo en una nueva ventana.", text_color="gray").pack(pady=(6,4))

        # 1. Botón de Exportar
        btn_export = ctk.CTkButton(
            frame, 
            text="💾 Exportar a Excel", 
            command=lambda: self.exportar_a_excel(datos, columnas, export_filename) # Llama al método de exportación
        )
        btn_export.pack(pady=(5, 8))

        # 2. Contenedor de la Tabla
        tabla_scroll_frame = ctk.CTkScrollableFrame(frame, label_text="Resultados")
        tabla_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # La columna 0 (típicamente el nombre del cliente/artículo) se expande
        for col_idx in range(len(columnas)):
            # Damos un peso 3 a la primera columna (Referencia Artículo)
            # y peso 1 al resto para asegurar que la Referencia se estire más.
            if col_idx == 0:
                tabla_scroll_frame.grid_columnconfigure(col_idx, weight=3) 
            else:
                tabla_scroll_frame.grid_columnconfigure(col_idx, weight=1) 
        
        # 3. Encabezados
        header_font = ctk.CTkFont(weight="bold")
        for col_idx, col_name in enumerate(columnas):
            # Alineación del encabezado
            sticky = "w" if col_idx == 0 else "e"
            ctk.CTkLabel(tabla_scroll_frame, text=col_name, font=header_font).grid(row=0, column=col_idx, padx=10, pady=5, sticky=sticky)
            
        # 4. Datos
        for row_idx, row_data in enumerate(datos):
            for col_idx, cell_value in enumerate(row_data):
                
                text_to_display = str(cell_value if cell_value is not None else "N/A")
                
                # 🚨 Aplicar formato de moneda si se especifica y estamos en la columna de valor (la última)
                if formato_moneda and col_idx == len(row_data) - 1 and cell_value is not None:
                    try:
                        # Intenta usar locale para el formato de moneda (€)
                        text_to_display = locale.currency(float(cell_value), grouping=True, symbol=True)
                    except (ValueError, TypeError, locale.Error):
                        # Fallback si no es un número o si falla el locale
                        text_to_display = f"{float(cell_value):,.2f} €"

                # Alineación del contenido
                sticky = "w" if col_idx == 0 else "e"
                
                # Crear el label como widget para poder bindear eventos
                label_widget = ctk.CTkLabel(
                    tabla_scroll_frame,
                    text=text_to_display,
                    justify="left"
                )
                label_widget.grid(row=row_idx + 1, column=col_idx, padx=10, pady=2, sticky=sticky)

                # Si es la primera columna (código RMA), hacerlo clicable
                if col_idx == 0:
                    # Cambiar cursor a mano y subrayar/colorear al hover
                    try:
                        original_color = label_widget.cget("text_color")
                    except Exception:
                        original_color = None

                    # Set cursor to hand2 if supported
                    try:
                        label_widget.configure(cursor="hand2")
                    except Exception:
                        pass

                    def on_enter(e):
                        try:
                            label_widget.configure(text_color="#1a73e8")
                        except Exception:
                            pass

                    def on_leave(e):
                        try:
                            if original_color is not None:
                                label_widget.configure(text_color=original_color)
                        except Exception:
                            pass

                    # Bind click to abrir_expediente using the displayed text (codigo)
                    label_widget.bind("<Button-1>", lambda e, code=text_to_display: abrir_expediente(code))
                    label_widget.bind("<Enter>", on_enter)
                    label_widget.bind("<Leave>", on_leave)
    
    def abrir_cliente_correo_con_mailto(self, email_acontacto, asunto, cuerpo):
        """Prepara el enlace mailto y lo abre con el cliente de correo por defecto."""
        
        # Necesitamos la librería para codificar el Asunto y el Cuerpo para la URL
        import urllib.parse
        
        # Codificar el asunto y el cuerpo (necesario para URLs mailto con espacios o caracteres especiales)
        asunto_codificado = urllib.parse.quote(asunto)
        cuerpo_codificado = urllib.parse.quote(cuerpo)
        
        # Construir el enlace mailto
        mailto_link = f"mailto:{email_acontacto}?subject={asunto_codificado}&body={cuerpo_codificado}"
        
        try:
            # Abrir el enlace usando el cliente de correo/navegador por defecto
            import webbrowser
            webbrowser.open(mailto_link)
            return True # Éxito
        except Exception as e:
            messagebox.showerror("Error de Email", "No se pudo abrir el cliente de correo por defecto. Por favor, asegúrate de que tienes un cliente de correo configurado.")
            return False # Fallo
    
    def enviar_email_contacto(self):
        """Abre el cliente de correo para enviar un email al contacto registrado en el RMA actual."""
        
        # 1. Verificar que haya un RMA actual abierto
        if not self.rma_actual_id:
            messagebox.showwarning("Advertencia", "Debe seleccionar o tener abierto un expediente RMA para enviar un email.")
            return

        conn = connect_db()
        cursor = conn.cursor()
        
        try:
            # 2. Consultar el email_contacto y el cliente del expediente actual
            cursor.execute("SELECT email_de_contacto, cliente, numero_documento_cliente, codigo_rma FROM rma_maestro WHERE id = ?", (self.rma_actual_id,))
            resultado = cursor.fetchone()
            
            if not resultado:
                messagebox.showerror("Error", f"No se encontró el expediente RMA: {self.rma_actual_id}")
                return
            
            email_acontacto, nombre_cliente, numero_documento_cliente, numero_rma = resultado
            
            # Verificar si el email_contacto está vacío o es nulo
            if not email_acontacto:
                messagebox.showwarning("Advertencia", f"El campo 'email_de_contacto' del expediente {self.rma_actual_id} está vacío.")
                return

            # 3. Definir Asunto y Cuerpo
            asunto_base = f"ENVIO DE INFORME {numero_rma}"
            
            # Texto que el cliente de correo abrirá por defecto (se puede editar)
            cuerpo_base = (
                f"Buenos dias,\n\n"
                f"Se adjunta resolución sobre el expediente abierto a su número de devolución:\n"
                f"{numero_documento_cliente}.\n"
                f"Para saber el estado de este informe, puede responder a este mismo correo.\n\n"
                f"Transcurridos 15 días del envío de este correo, se dará por cerrado el expediente, no aceptando ningún tipo de no conformidad a esta resolución.\n\n\n"
                f"Dpto. Tecnico Ilutrek."
            )

            # 4. Llamar a la función del Paso 1 para abrir el cliente de correo
            email_abierto_ok = self.abrir_cliente_correo_con_mailto(email_acontacto, asunto_base, cuerpo_base)
            
            if email_abierto_ok:
                # 5. Registrar la acción en el historial
                #accion = f"Email de contacto enviado al cliente {nombre_cliente} ({email_acontacto}). Asunto: '{asunto_base}'."
                #self.registrar_historial(accion)
                cursor.execute("""
                    INSERT INTO rma_historial (rma_id, fecha_cambio, descripcion_cambio, usuario)
                    VALUES (?, ?, ?, ?)
                """, (
                    self.rma_actual_id, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    f"Email de Resolucion enviado al cliente {nombre_cliente} ({email_acontacto}). Asunto: '{asunto_base}'.", 
                    self.username
                ))
                conn.commit()
                
                # Opcional: Mostrar una notificación al usuario
                messagebox.showinfo("Enviar Email", "Se ha abierto tu gestor de correo, por favor revisa tu borrador antes de enviarlo.")

        except sqlite3.Error as e:
            messagebox.showerror("Error de BD", f"Error al consultar la base de datos: {e}")
        finally:
            conn.close()
    
    
    
    # Nota: la implementación anterior de 'mostrar_formulario_github' era un duplicado
    # y ha sido eliminada para evitar confusión. La implementación activa está más
    # abajo en el archivo y contiene el botón de envío correctamente visible.
        
    def mostrar_formulario_github(self):
        """Muestra un formulario para crear un issue en GitHub."""
        # Crear una nueva ventana modal con tamaño fijo (no maximizable)
        ventana_issue = ctk.CTkToplevel(self)
        ventana_issue.title("Crear Issue en GitHub")
        ventana_issue.geometry("500x600")  # Altura aumentada para asegurar que todo sea visible
        ventana_issue.resizable(False, False)  # Ventana de tamaño fijo
        ventana_issue.grab_set()  # Hace la ventana modal

        # Marco con scroll para el contenido
        scroll_frame = ctk.CTkScrollableFrame(ventana_issue)
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Marco para el contenido dentro del scroll
        content_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        # Campo de nombre (autocompletado con el usuario actual)
        ctk.CTkLabel(content_frame, text="Nombre:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=(4,2))
        nombre_entry = ctk.CTkEntry(content_frame)
        nombre_entry.insert(0, self.username)
        nombre_entry.pack(fill="x", padx=5, pady=(0,12))

        # Campo de fecha (autocompletado con la fecha actual)
        ctk.CTkLabel(content_frame, text="Fecha:").pack(anchor="w", padx=5, pady=(4,2))
        fecha_entry = ctk.CTkEntry(content_frame)
        fecha_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        fecha_entry.pack(fill="x", padx=5, pady=(0,8))

        # Tipo de issue (Bug/Sugerencia)
        ctk.CTkLabel(content_frame, text="Tipo:").pack(anchor="w", padx=5, pady=(4,2))
        tipo_var = tk.StringVar(value="Sugerencia")
        tipo_frame = ctk.CTkFrame(content_frame)
        tipo_frame.pack(fill="x", padx=5, pady=(0,8))
        ctk.CTkRadioButton(tipo_frame, text="Bug", variable=tipo_var, value="Bug").pack(side="left", padx=12)
        ctk.CTkRadioButton(tipo_frame, text="Sugerencia", variable=tipo_var, value="Sugerencia").pack(side="left", padx=12)

        # Campo de descripción
        ctk.CTkLabel(content_frame, text="Descripción:").pack(anchor="w", padx=5, pady=(4,2))
        desc_text = ctk.CTkTextbox(content_frame, height=160)
        desc_text.pack(fill="both", expand=True, padx=5, pady=(0,8))

        # Footer con el botón para asegurarnos que está siempre visible
        footer = ctk.CTkFrame(ventana_issue, fg_color="transparent", height=50)
        footer.pack(side="bottom", fill="x", padx=12, pady=8)
        footer.pack_propagate(False)  # Mantiene la altura fija del footer

        # Función para enviar el issue
        def enviar_issue():
            nombre = nombre_entry.get().strip()
            fecha = fecha_entry.get().strip()
            tipo = tipo_var.get()
            descripcion = desc_text.get("1.0", "end-1c").strip()

            if not nombre or not fecha or not descripcion:
                messagebox.showerror("Error", "Por favor, complete todos los campos.")
                return

            titulo = f"[{tipo}] Reporte de {nombre}"
            cuerpo = (
                f"Reporte creado por: {nombre}\n"
                f"Fecha: {fecha}\n"
                f"Tipo: {tipo}\n"
                f"Rol del usuario: {self.rol}\n"
                f"Versión de la App: {APP_VERSION}\n\n"
                f"Descripción:\n{descripcion}\n"
            )

            token = os.getenv('GITHUB_TOKEN')
            if not token:
                messagebox.showerror("Error", "No se encontró el token de GitHub. Contacte al administrador del sistema.")
                return

            try:
                url = "https://api.github.com/repos/ilutreksl/Gestor_Expedientes/issues"
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                data = {"title": titulo, "body": cuerpo, "labels": [tipo]}

                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()

                issue_number = response.json().get('number')
                message = f"Issue creado correctamente en GitHub." if not issue_number else f"El issue #{issue_number} ha sido creado correctamente en GitHub."
                messagebox.showinfo("Éxito", message)
                ventana_issue.destroy()

            except requests.exceptions.RequestException as e:
                messagebox.showerror("Error", f"Error al crear el issue en GitHub: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al enviar el reporte: {e}")

        # Botón de enviar en el footer (posicionamiento absoluto)
        btn_enviar = ctk.CTkButton(
            footer, 
            text="✉️ Enviar Issue", 
            command=enviar_issue,
            width=120,  # Ancho fijo para el botón
            height=32   # Altura fija para el botón
        )
        btn_enviar.place(relx=0.95, rely=0.5, anchor="e")  # Posicionamiento relativo a la derecha

    def abrir_formulario_email(self):
        """Abre el cliente de correo por defecto con un enlace mailto preconfigurado."""
        
        # 🚨 ¡IMPORTANTE! Reemplaza 'tu.email@empresa.com' por la dirección correcta
        email_destino = "carlos@ilutrek.es"
        
        # Generamos un asunto útil que incluye el nombre de la aplicación y el usuario
        asunto = f"Bug/Sugerencia de {self.username} ({self.rol}) en Gestión RMA"
        
        # Creamos un cuerpo predefinido para guiar al compañero
        cuerpo = f"""
Hola,
        
Por favor, describe el problema o sugerencia a continuación:
        
----------------------------------------------------------------------
        
Tipo: [BUG / SUGERENCIA]
Página/Función: [Ej: Listado RMA / Formulario Edición]
Descripción: 
Pasos para reproducir (solo bugs):
        
----------------------------------------------------------------------
        
Información del Sistema (NO MODIFICAR):
Usuario: {self.username}
Versión de la App: {APP_VERSION}
"""
        
        # URL-encode el asunto y el cuerpo (necesario para URLs mailto)
        import urllib.parse
        asunto_codificado = urllib.parse.quote(asunto)
        cuerpo_codificado = urllib.parse.quote(cuerpo)
        
        # Construir el enlace mailto
        mailto_link = f"mailto:{email_destino}?subject={asunto_codificado}&body={cuerpo_codificado}"
        
        try:
            # Abrir el enlace usando el cliente de correo/navegador por defecto
            webbrowser.open(mailto_link)
        except Exception as e:
            # Si falla (ej. en un entorno sin navegador o cliente de correo configurado)
            print(f"Error al abrir el cliente de correo: {e}")
            messagebox.showerror("Error de Email", "No se pudo abrir el cliente de correo por defecto. Por favor, envía un email manualmente a " + email_destino)
    

# ----------------------------------------------------------------------
# 7. EJECUCIÓN DEL PROGRAMA
# ----------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        print("🚨 Error Crítico: No se encuentra el archivo de base de datos 'rma_app.db'.")
        print("Asegúrate de ejecutar primero 'python db_setup.py'.")
        sys.exit(1)
    
    # Optimizar base de datos al inicio (crear índices)
    print("🔧 Optimizando base de datos...")
    optimize_database()
    
    app = LoginApp()
    app.mainloop()