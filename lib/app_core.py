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
import re

# Cargar variables de entorno
load_dotenv()
from PIL import Image, ImageTk
#from tkcalendar import Calendar
from CTkDatePicker import CTkDatePicker
from lib.changelog_window import mostrar_ventana_cambios
from lib.rma_utils import obtener_ultima_actividad, calcular_tiempos_expediente, obtener_color_tiempo, obtener_promedio_cliente
from lib.video_utils import comprimir_video_inteligente
from lib.avisos_manager import AvisosManager
from lib.backup_manager import BackupManagerB2
from lib.estados_manager import EstadosArticuloManager
from lib.personas_manager import PersonasManager
from lib.personas_recepcion_manager import PersonasRecepcionManager
from lib.resultado_expediente_manager import ResultadoExpedienteManager
from lib.tipos_cliente_manager import cargar_tipos_cliente
from lib import github_issue_manager
from lib import rma_asociaciones
from lib import rma_correos_asociados
from lib import correo_parser
from lib import tareas_notificaciones
from lib.tareas_panel import TareasBadge, PanelTareas
from lib.rich_text_editor import RichTextEditor

# Sistema de logging
from lib.logger_config import setup_logging, set_current_user, get_logger

# Gestor de firmas de usuario
from lib.firma_manager import (
    subir_firma_usuario_b2,
    descargar_firma_usuario_b2,
    eliminar_firma_usuario_b2,
    verificar_firma_usuario_existe
)

import tkinter as tk
from tkinter import ttk

# Inicializar sistema de logging (captura todos los prints y errores)
logger = setup_logging()
logger.info("Aplicación iniciada")

# Monkey patch para prevenir errores en ventanas destruidas
# Guardamos referencias a los métodos originales
_original_tk_after = tk.Misc.after
_original_toplevel_destroy = Toplevel.destroy

# Diccionario global para rastrear IDs de callbacks por ventana
_window_after_ids = {}

def _safe_after(self, ms, func=None, *args):
    """Wrapper seguro para after() que registra los IDs"""
    # Si func es None, es un sleep, no lo trackeamos
    if func is None:
        return _original_tk_after(self, ms)
    
    # Función wrapper que verifica si la ventana existe antes de ejecutar
    def safe_func(*func_args):
        try:
            # Verificar si el widget todavía existe
            if self.winfo_exists():
                return func(*func_args)
        except:
            pass  # Ventana ya destruida, ignorar silenciosamente
    
    # Programar el callback con la función segura
    after_id = _original_tk_after(self, ms, safe_func, *args)
    
    # Registrar el ID si es una ventana Toplevel
    if isinstance(self, (Toplevel, ctk.CTkToplevel)):
        window_id = id(self)
        if window_id not in _window_after_ids:
            _window_after_ids[window_id] = []
        _window_after_ids[window_id].append(after_id)
    
    return after_id

def _safe_destroy(self):
    """Wrapper seguro para destroy() que cancela todos los callbacks"""
    window_id = id(self)
    
    # Cancelar todos los callbacks programados para esta ventana
    if window_id in _window_after_ids:
        for after_id in _window_after_ids[window_id][:]:
            try:
                self.after_cancel(after_id)
            except:
                pass
        del _window_after_ids[window_id]
    
    # Liberar grab si existe
    try:
        self.grab_release()
    except:
        pass
    
    # Llamar al destroy original
    try:
        _original_toplevel_destroy(self)
    except:
        pass

# Aplicar los monkey patches
tk.Misc.after = _safe_after
Toplevel.destroy = _safe_destroy
ctk.CTkToplevel.destroy = _safe_destroy
import threading
import tempfile

# Importaciones para Backblaze B2
try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
    from b2sdk.v2.exception import B2Error, NonExistentBucket
    B2_DISPONIBLE = True
except ImportError:
    print("ADVERTENCIA: b2sdk no está instalado. Instala con: pip install b2sdk")
    B2_DISPONIBLE = False

# Cargar credenciales de B2 desde variables de entorno
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "gestion-expedientes-app-b2")
B2_ROOT_FOLDER = "Adjuntos_RMA"  # Prefijo en bucket para adjuntos de RMA

# Variables globales para cache de cliente de B2
_b2_api_cache = None
_b2_bucket_cache = None
_last_b2_check = 0

# ================================
# FUNCIONES DE COMPRESIÓN DE IMÁGENES
# ================================

def es_imagen(filepath):
    """Detecta si un archivo es una imagen basándose en la extensión."""
    extensiones_imagen = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.heic', '.heif'}
    ext = os.path.splitext(filepath)[1].lower()
    return ext in extensiones_imagen

def es_video(filepath):
    """Detecta si un archivo es un video basándose en la extensión."""
    extensiones_video = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'}
    ext = os.path.splitext(filepath)[1].lower()
    return ext in extensiones_video

def comprimir_imagen_inteligente(filepath_original, callback_progreso=None):
    """
    Comprime una imagen siguiendo la estrategia inteligente (Opción 1):
    - Si > 2MB: Redimensionar a 1920x1080 máx, calidad 85%
    - Si > 500KB: Solo recomprimir con calidad 90%
    - Si < 500KB: No modificar
    
    Returns: (filepath_comprimido, tamaño_original_mb, tamaño_final_mb) o (None, 0, 0) si hay error
    """
    try:
        from PIL import Image
        import tempfile
        
        if callback_progreso:
            callback_progreso("🔍 Analizando imagen...")
        
        # Obtener tamaño original
        tamaño_original = os.path.getsize(filepath_original)
        tamaño_original_mb = tamaño_original / (1024 * 1024)
        
        # Si es muy pequeña, no comprimir
        if tamaño_original < 500 * 1024:  # 500KB
            if callback_progreso:
                callback_progreso(f"✅ Imagen pequeña ({tamaño_original_mb:.1f}MB), no necesita compresión")
            return filepath_original, tamaño_original_mb, tamaño_original_mb
        
        if callback_progreso:
            callback_progreso(f"📏 Imagen {tamaño_original_mb:.1f}MB - iniciando compresión...")
        
        # Abrir imagen
        with Image.open(filepath_original) as img:
            # Convertir HEIC/HEIF a RGB si es necesario
            if img.format in ['HEIC', 'HEIF'] or img.mode in ['RGBA', 'LA']:
                if callback_progreso:
                    callback_progreso("🔄 Convirtiendo formato...")
                # Crear fondo blanco para transparencias
                if img.mode in ['RGBA', 'LA']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Determinar parámetros de compresión según tamaño
            if tamaño_original > 2 * 1024 * 1024:  # > 2MB
                # Redimensionar y comprimir agresivamente
                max_width, max_height = 1920, 1080
                calidad = 85
                if callback_progreso:
                    callback_progreso("🎯 Redimensionando a Full HD y comprimiendo...")
            else:
                # Solo recomprimir
                max_width, max_height = img.size
                calidad = 90
                if callback_progreso:
                    callback_progreso("🔧 Recomprimiendo con calidad optimizada...")
            
            # Redimensionar manteniendo aspecto si es necesario
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                if callback_progreso:
                    callback_progreso(f"📐 Redimensionado a {img.width}x{img.height}")
            
            # Crear archivo temporal comprimido
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            
            # Guardar imagen comprimida
            if callback_progreso:
                callback_progreso("💾 Guardando imagen optimizada...")
                
            img.save(temp_path, 'JPEG', quality=calidad, optimize=True, progressive=True)
        
        # Verificar resultado
        tamaño_final = os.path.getsize(temp_path)
        tamaño_final_mb = tamaño_final / (1024 * 1024)
        reduccion = ((tamaño_original - tamaño_final) / tamaño_original) * 100
        
        if callback_progreso:
            callback_progreso(f"✅ Compresión completada: {tamaño_original_mb:.1f}MB → {tamaño_final_mb:.1f}MB ({reduccion:.1f}% reducción)")
        
        return temp_path, tamaño_original_mb, tamaño_final_mb
        
    except Exception as e:
        if callback_progreso:
            callback_progreso(f"❌ Error en compresión: {e}")
        print(f"Error comprimiendo imagen {filepath_original}: {e}")
        return None, 0, 0


class Tooltip:
    """Simple tooltip for tkinter widgets. Shows a small Toplevel on hover."""
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._id = None
        self._tipwindow = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None):
        self._unschedule()
        try:
            if not USER_SETTINGS.get("show_tooltips", True):
                return
        except Exception:
            pass
        self._id = self.widget.after(self.delay, self._show)

    def _unschedule(self):
        if self._id:
            try:
                self.widget.after_cancel(self._id)
            except Exception:
                pass
            self._id = None

    def _show(self):
        if self._tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack(ipadx=4, ipady=2)

    def _hide(self, event=None):
        self._unschedule()
        tw = self._tipwindow
        self._tipwindow = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️ Pandas no está disponible. La exportación a Excel estará deshabilitada.")

import locale
import shutil # Para copiar archivos
import tkinter.filedialog as filedialog # Para el diálogo de selección de archivos
import subprocess # Para abrir archivos en diferentes OS
# Módulo para rellenado de PDFs
try:
    from lib.pdf_fill import fill_pdf_for_rma, get_pdf_field_names, fill_pdf
except Exception:
    # Si no está instalado/ disponible aún, seguiremos sin la funcionalidad
    fill_pdf_for_rma = None
    get_pdf_field_names = None
    fill_pdf = None

# Definición de las variables globales de la base de datos
DB_NAME = "rma_app.db"
# Mensaje de advertencia sobre la limitación de SQLite en red compartida
ADVERTENCIA_MULTIUSUARIO = "⚠️ ADVERTENCIA: Esta app usa SQLite, NO es segura para múltiples usuarios escribiendo a la vez en red compartida. ¡Riesgo de corrupción de datos si escriben a la vez!"

APP_VERSION = "v1.2.20"
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


def parse_date_to_iso(value: str) -> str:
    """Intenta parsear una cadena de fecha en varios formatos comunes y devuelve
    la fecha normalizada en formato ISO YYYY-MM-DD.

    Lanza ValueError si no puede parsearse.
    """
    if value is None:
        raise ValueError("None provided")
    v = str(value).strip()
    if v == "":
        raise ValueError("Empty date")

    # Intentar formatos más comunes
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"]
    for fmt in formatos:
        try:
            dt = datetime.datetime.strptime(v, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    # Si ninguno encaja, intentar parseo flexible usando dateutil si está disponible
    try:
        from dateutil import parser as _parser  # type: ignore
        dt = _parser.parse(v, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        raise ValueError(f"Formato de fecha no reconocido: {value}")

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
                    request_payload = {"requests": [{"type": "execute", "stmt": {"sql": sql, "args": args}}]}

                    try:
                        response = session.post(
                            self._url,
                            headers={
                                "Authorization": f"Bearer {self._token}"
                            },
                            json=request_payload,
                            timeout=30  # Campos como obs_tecnica pueden incluir imágenes
                                        # en base64 y tardar más de 10s en subirse
                        )
                    except requests.exceptions.RequestException as e:
                        # Sin esto, un timeout/error de red se propaga como Exception
                        # genérica y el código que llama (que solo captura
                        # sqlite3.Error) no lo detecta: el guardado falla en
                        # silencio y el usuario no ve ningún aviso.
                        print(f"Error de conexión con Turso: {e}")
                        raise sqlite3.OperationalError(f"Error de conexión con Turso: {e}")

                    if response.status_code != 200:
                        print(f"Error - Response status: {response.status_code}, text: {response.text}")
                        raise sqlite3.OperationalError(f"Turso API error: {response.status_code} - {response.text}")
                    
                    data = response.json()
                    results = data.get("results", [])
                    
                    if results and len(results) > 0:
                        # Verificar si hay error en la respuesta
                        result_item = results[0]
                        if result_item.get("type") == "error":
                            error_msg = result_item.get("error", {}).get("message", "Unknown error")
                            # No imprimir errores de verificación de esquema que son normales
                            _es_error_esquema = (
                                ("tipo_almacenamiento" in sql and "SELECT" in sql) or
                                ("numero_albaran" in error_msg and "no such column" in error_msg) or
                                ("numero_order" in error_msg and "no such column" in error_msg)
                            )
                            if not _es_error_esquema:
                                print(f"SQL Error: {error_msg}")
                                print(f"Query: {sql}")
                                print(f"Params: {params}")
                            # Lanzar excepción para que pueda ser manejada por el código que llama
                            raise sqlite3.OperationalError(f"SQLite error: {error_msg}")
                        else:
                            result = result_item.get("response", {}).get("result", {})
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
                    try:
                        response = session.post(
                            self._url,
                            headers={
                                "Authorization": f"Bearer {self._token}"
                            },
                            json={"requests": requests_batch},
                            timeout=30  # Timeout mayor para batch
                        )
                    except requests.exceptions.RequestException as e:
                        print(f"Error de conexión con Turso: {e}")
                        raise sqlite3.OperationalError(f"Error de conexión con Turso: {e}")

                    if response.status_code != 200:
                        raise sqlite3.OperationalError(f"Turso API error: {response.status_code} - {response.text}")

                    # Para executemany, solo guardamos el último resultado
                    data = response.json()
                    results = data.get("results", [])
                    for result_item in results:
                        if result_item.get("type") == "error":
                            error_msg = result_item.get("error", {}).get("message", "Unknown error")
                            print(f"SQL Error (executemany): {error_msg}")
                            raise sqlite3.OperationalError(f"SQLite error: {error_msg}")
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
                    
                    # Si no hay filas directamente, intentar extraer de otros posibles formatos
                    if not rows and "values" in self._result:
                        rows = self._result.get("values", [])
                    
                    if not rows and "data" in self._result:
                        rows = self._result.get("data", [])
                    
                    # Turso puede devolver diferentes formatos
                    result_rows = []
                    for row in rows:
                        if isinstance(row, list):
                            # Caso 1: Lista de valores directos
                            if row and not isinstance(row[0], dict):
                                result_rows.append(tuple(row))
                            else:
                                # Caso 2: Lista de objetos {"type": ..., "value": ...}
                                values = []
                                for cell in row:
                                    if isinstance(cell, dict):
                                        value = cell.get("value")
                                        if value is None:
                                            value = cell.get("v")  # Otra posible key
                                        
                                        # IMPORTANTE: Convertir según el tipo para mantener tipos correctos
                                        cell_type = cell.get("type", "").lower()
                                        if value is not None:
                                            if cell_type == "integer":
                                                try:
                                                    value = int(value)
                                                except (ValueError, TypeError):
                                                    pass  # Mantener el valor original si falla
                                            elif cell_type == "real" or cell_type == "float":
                                                try:
                                                    value = float(value)
                                                except (ValueError, TypeError):
                                                    pass
                                        
                                        values.append(value)
                                    else:
                                        values.append(cell)
                                result_rows.append(tuple(values))
                        else:
                            # Caso 3: Fila como tupla directa
                            result_rows.append(tuple(row) if not isinstance(row, tuple) else row)
                    
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
    except Exception as e:
        print(f"Error al crear índices: {e}")

# --- NUEVA VARIABLE GLOBAL ---
ADJUNTOS_ROOT_DIR = "Adjuntos_RMA" # Carpeta principal para guardar todos los archivos adjuntos
# -----------------------------

# --- CONFIGURACIÓN Y FUNCIONES PARA BACKBLAZE B2 ---
def get_b2_client():
    """
    Crea y retorna un cliente de Backblaze B2 con caché.
    Retorna: (B2Api, Bucket) o (None, None) si no está configurado o hay error.
    """
    global _b2_api_cache, _b2_bucket_cache, _last_b2_check
    import time
    
    # Cache del cliente para evitar múltiples autenticaciones
    current_time = time.time()
    if _b2_api_cache and _b2_bucket_cache and (current_time - _last_b2_check < 300):  # Cache por 5 minutos
        return _b2_api_cache, _b2_bucket_cache
    
    # Verificar si b2sdk está disponible
    if not B2_DISPONIBLE:
        print("B2: SDK no disponible")
        return None, None
    
    # Verificar credenciales
    if not B2_KEY_ID or not B2_APPLICATION_KEY:
        print("B2: Credenciales no configuradas en .env")
        return None, None
    
    try:
        # Crear API de B2
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        
        # Autorizar cuenta
        b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
        
        # Obtener bucket
        bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
        
        # Guardar en cache
        _b2_api_cache = b2_api
        _b2_bucket_cache = bucket
        _last_b2_check = current_time
        
        print(f"B2: Conectado al bucket '{B2_BUCKET_NAME}'")
        return b2_api, bucket
        
    except NonExistentBucket:
        print(f"B2: Bucket '{B2_BUCKET_NAME}' no existe")
        return None, None
    except B2Error as e:
        print(f"B2: Error de autenticación: {e}")
        return None, None
    except Exception as e:
        print(f"B2: Error inesperado: {e}")
        return None, None

def usar_b2():
    """
    Determina si se debe usar Backblaze B2 o almacenamiento local.
    """
    b2_api, bucket = get_b2_client()
    return b2_api is not None and bucket is not None

def normalizar_ruta_b2(ruta):
    """
    Normaliza una ruta para B2 (sin "/" inicial, usar forward slashes).
    """
    # Eliminar "/" inicial si existe
    if ruta.startswith('/'):
        ruta = ruta[1:]
    # Reemplazar backslashes por forward slashes
    return ruta.replace('\\', '/')

# ------------------------------------------------

# --- User settings persistence (simple JSON file) ---
import json

USER_SETTINGS: dict = {}

def _get_user_settings_path() -> str:
    # Guardar en la carpeta del proyecto por simplicidad
    return os.path.join(os.getcwd(), "user_settings.json")

def load_user_settings(username: str = None) -> dict:
    defaults = {
        "date_format": "YYYY-MM-DD",
        "show_tooltips": True,
        "compact_mode": True,
        "icon_size": 24,
        "theme": "themes/BH_rime.json",
        "appearance_mode": "light",
        "tiene_firma": False,  # Campo para indicar si el usuario tiene firma en B2
        "mostrar_tareas_dashboard": True,
        "mostrar_todas_tareas_dashboard": True,
        "mostrar_prioritarias_dashboard": False,
        "mostrar_calendario_dashboard": True,
        "idioma_ortografia": "es"
    }
    path = _get_user_settings_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if not isinstance(data, dict):
                    return defaults
                # Backwards-compatible file structure:
                # { "global": {...}, "users": { "username": {...} } }
                merged = defaults.copy()
                # If old flat format (keys at root), merge them as global
                root_global = {}
                if any(k in data for k in defaults.keys()):
                    root_global.update(data)

                # Merge global overrides
                if isinstance(data.get("global"), dict):
                    root_global.update(data.get("global"))

                merged.update(root_global)

                # Merge per-user overrides if username provided
                if username and isinstance(data.get("users"), dict):
                    user_section = data.get("users", {}).get(username)
                    if isinstance(user_section, dict):
                        merged.update(user_section)

                return merged
    except Exception as e:
        print(f"Warning: no se pudieron cargar user_settings.json: {e}")
    return defaults

def save_user_settings(settings: dict, username: str = None) -> bool:
    # Do not persist attachments_dir - it's fixed by the app
    settings_to_save = settings.copy()
    settings_to_save.pop("attachments_dir", None)
    path = _get_user_settings_path()
    try:
        # Load existing file if present to preserve other users/global settings
        root = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    root = json.load(fh) or {}
            except Exception:
                root = {}

        if not isinstance(root, dict):
            root = {}

        # Ensure structure
        if "global" not in root or not isinstance(root.get("global"), dict):
            # If file was flat (legacy), migrate existing keys into global
            flat_keys = {k: v for k, v in root.items() if k not in ("users", "global")}
            root = {"global": flat_keys, "users": {}}

        if username:
            users = root.setdefault("users", {})
            users[username] = settings_to_save
        else:
            root["global"] = settings_to_save

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(root, fh, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error al guardar user_settings.json: {e}")
        try:
            # Mostrar cuadro de diálogo de error al usuario cuando falle el guardado
            messagebox.showerror("Error al guardar ajustes", f"No se pudieron guardar los ajustes: {e}")
        except Exception:
            pass
        return False
