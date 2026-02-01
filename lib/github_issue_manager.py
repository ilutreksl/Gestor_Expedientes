"""
Módulo para gestionar reportes de issues en GitHub.
Incluye funcionalidades para adjuntar logs e imágenes.
"""

import os
import datetime
import base64
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import requests
from PIL import Image
import io
from lib.logger_config import get_logger

# Importar configuración de Backblaze B2
try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
    from b2sdk.exception import B2Error
    import os as os_mod
    B2_DISPONIBLE = True
except ImportError:
    B2_DISPONIBLE = False

logger = get_logger()

# Registrar disponibilidad de Backblaze B2
if not B2_DISPONIBLE:
    logger.warning("Backblaze B2 no disponible para adjuntar imágenes")


def renderizar_markdown_simple(textbox, contenido_md):
    """
    Renderiza markdown básico en un CTkTextbox.
    Convierte markdown a texto formateado simple.
    
    Args:
        textbox: Widget CTkTextbox donde renderizar
        contenido_md: Contenido markdown a renderizar
    """
    try:
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        
        lineas = contenido_md.split('\n')
        
        for linea in lineas:
            linea_original = linea
            linea_stripped = linea.strip()
            
            # Saltar líneas vacías
            if not linea_stripped:
                textbox.insert("end", "\n")
                continue
            
            # Headers nivel 1 (# )
            if linea_stripped.startswith('# '):
                texto = linea_stripped[2:].upper()
                textbox.insert("end", f"\n{'='*60}\n{texto}\n{'='*60}\n\n")
            
            # Headers nivel 2 (## )
            elif linea_stripped.startswith('## '):
                texto = linea_stripped[3:].upper()
                textbox.insert("end", f"\n{texto}\n{'-'*len(texto)}\n\n")
            
            # Headers nivel 3 (### )
            elif linea_stripped.startswith('### '):
                texto = linea_stripped[4:]
                # Procesar negritas en headers nivel 3
                if '**' in texto:
                    texto = texto.replace('**', '')
                textbox.insert("end", f"\n▸ {texto}\n\n")
            
            # Separadores (---)
            elif linea_stripped.startswith('---'):
                textbox.insert("end", f"\n{'─'*60}\n\n")
            
            # Listas con viñeta (- o *)
            elif linea_stripped.startswith('- ') or linea_stripped.startswith('* '):
                texto = linea_stripped[2:]
                textbox.insert("end", f"  • {texto}\n")
            
            # Listas numeradas
            elif len(linea_stripped) > 2 and linea_stripped[0].isdigit() and linea_stripped[1] == '.':
                textbox.insert("end", f"  {linea_stripped}\n")
            
            # Línea con negritas **texto**
            else:
                texto = linea_stripped
                # Procesar negritas: **texto** -> TEXTO
                if '**' in texto:
                    import re
                    # Reemplazar **texto** por TEXTO (en mayúsculas)
                    texto = re.sub(r'\*\*([^*]+)\*\*', lambda m: m.group(1).upper(), texto)
                
                textbox.insert("end", f"{texto}\n")
        
        textbox.configure(state="disabled")
        
    except Exception as e:
        # Si falla, mostrar texto plano
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", contenido_md)
        textbox.configure(state="disabled")


def subir_imagen_b2(ruta_imagen, username):
    """
    Sube una imagen a Backblaze B2 con calidad media y retorna el enlace público.
    
    Args:
        ruta_imagen: Ruta local de la imagen
        username: Usuario que sube la imagen
        
    Returns:
        str: URL pública de B2 o None si falla
    """
    if not B2_DISPONIBLE:
        logger.error("Backblaze B2 no está disponible")
        return None
    
    try:
        # Obtener credenciales de B2 desde variables de entorno
        b2_key_id = os_mod.getenv("B2_KEY_ID")
        b2_application_key = os_mod.getenv("B2_APPLICATION_KEY")
        b2_bucket_name = os_mod.getenv("B2_BUCKET_NAME", "gestion-expedientes-app-b2")
        
        if not b2_key_id or not b2_application_key:
            logger.error("Credenciales de B2 no configuradas")
            return None
        
        # Inicializar cliente B2
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", b2_key_id, b2_application_key)
        
        # Obtener bucket
        bucket = b2_api.get_bucket_by_name(b2_bucket_name)
        
        # Reducir calidad de imagen
        img = Image.open(ruta_imagen)
        
        # Convertir RGBA a RGB si es necesario
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            img = rgb_img
        
        # Redimensionar si es muy grande (max 1920px en cualquier dimensión)
        max_size = 1920
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Guardar en archivo temporal
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            img.save(tmp_file, format='JPEG', quality=70, optimize=True)
            temp_path = tmp_file.name
        
        # Generar nombre único con timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = os_mod.path.splitext(os_mod.path.basename(ruta_imagen))[0]
        nombre_archivo = f"{timestamp}_{username}_{nombre_base}.jpg"
        
        # Ruta en B2
        b2_path = f"Images_Report/{nombre_archivo}"
        
        # Subir archivo
        bucket.upload_local_file(
            local_file=temp_path,
            file_name=b2_path
        )
        logger.info(f"Imagen subida a Backblaze B2: {b2_path}")
        
        # Limpiar archivo temporal
        os_mod.remove(temp_path)
        
        # Construir URL pública de B2
        # Formato: https://f{bucket_id}.backblazeb2.com/file/{bucket_name}/{file_name}
        download_url = bucket.get_download_url(b2_path)
        logger.info(f"Enlace público generado: {download_url}")
        
        return download_url
        
    except B2Error as e:
        logger.error(f"Error B2 al subir imagen: {e}")
        return None
    except Exception as e:
        logger.error(f"Error al subir imagen a Backblaze B2: {e}")
        return None


def mostrar_ventana_info_issue(ventana_principal, callback_continuar):
    """
    Muestra ventana informativa antes de reportar issue.
    
    Args:
        ventana_principal: Referencia a la ventana principal de la aplicación
        callback_continuar: Función a llamar cuando el usuario acepta continuar
    """
    # Leer el contenido del archivo Mensaje_Issue.md
    mensaje_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Diccionarios", "Mensaje_Issue.md")
    try:
        with open(mensaje_path, 'r', encoding='utf-8') as f:
            mensaje_content = f.read()
        logger.info("Ventana informativa de issue mostrada correctamente")
    except Exception as e:
        logger.error(f"Error al leer Mensaje_Issue.md: {e}")
        mensaje_content = "Error al cargar el mensaje informativo. ¿Desea continuar?"
    
    # Crear ventana informativa
    ventana_info = ctk.CTkToplevel(ventana_principal)
    ventana_info.title("Información - Reportar Issue")
    ventana_info.geometry("700x650")
    ventana_info.resizable(False, False)
    ventana_info.grab_set()
    
    # Área de texto con scroll para el mensaje (sin doble scroll)
    texto_mensaje = ctk.CTkTextbox(ventana_info, wrap="word", font=ctk.CTkFont(size=12))
    texto_mensaje.pack(fill="both", expand=True, padx=20, pady=(20, 10))
    
    # Renderizar markdown
    renderizar_markdown_simple(texto_mensaje, mensaje_content)
    
    # Botón de aceptar
    def aceptar_y_continuar():
        ventana_info.destroy()
        callback_continuar()
    
    btn_frame = ctk.CTkFrame(ventana_info, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    btn_aceptar = ctk.CTkButton(
        btn_frame,
        text="Aceptar",
        command=aceptar_y_continuar,
        width=120,
        height=40,
        font=ctk.CTkFont(size=14, weight="bold")
    )
    btn_aceptar.pack(side="right")
    
    btn_cancelar = ctk.CTkButton(
        btn_frame,
        text="❌ Cancelar",
        command=ventana_info.destroy,
        width=120,
        height=40,
        fg_color="#8B0000",
        hover_color="#A52A2A"
    )
    btn_cancelar.pack(side="right", padx=(0, 10))


def obtener_log_mas_reciente(username=None):
    """
    Obtiene el contenido del archivo de log más reciente del usuario.
    
    Args:
        username: Nombre del usuario para buscar su log específico
        
    Returns:
        tuple: (contenido_log, nombre_archivo) o None si no se encuentra
    """
    try:
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(logs_dir):
            logger.warning("Directorio de logs no encontrado")
            return None
        
        # Buscar logs del usuario específico si se proporciona username
        if username:
            archivos_log = [f for f in os.listdir(logs_dir) if f.endswith(f'_{username}.log')]
        else:
            archivos_log = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        
        if not archivos_log:
            logger.warning(f"No se encontraron archivos de log{' para el usuario ' + username if username else ''}")
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        archivos_log.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
        archivo_mas_reciente = os.path.join(logs_dir, archivos_log[0])
        
        # Leer contenido del log (limitar a últimas 100 líneas para evitar issues muy largos)
        with open(archivo_mas_reciente, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            # Tomar últimas 100 líneas o todas si hay menos
            lineas_limitadas = lineas[-100:] if len(lineas) > 100 else lineas
            logger.info(f"Log más reciente obtenido: {archivos_log[0]} ({len(lineas_limitadas)} líneas)")
            return ''.join(lineas_limitadas), archivos_log[0]
    except Exception as e:
        logger.error(f"Error al obtener log más reciente: {e}")
        return None


def seleccionar_imagenes():
    """
    Abre un diálogo para seleccionar imágenes.
    
    Returns:
        list: Lista de rutas de archivos seleccionados
    """
    try:
        archivos = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Todos los archivos", "*.*")
            ]
        )
        if archivos:
            logger.info(f"{len(archivos)} imagen(es) seleccionada(s) para adjuntar")
        return list(archivos)
    except Exception as e:
        logger.error(f"Error al seleccionar imágenes: {e}")
        return []


def convertir_imagen_a_base64(ruta_imagen):
    """
    Convierte una imagen a base64 para incluirla en el issue de GitHub.
    
    Args:
        ruta_imagen: Ruta al archivo de imagen
        
    Returns:
        str: Imagen en formato base64 o None si hay error
    """
    try:
        with open(ruta_imagen, 'rb') as f:
            imagen_base64 = base64.b64encode(f.read()).decode('utf-8')
        logger.info(f"Imagen convertida a base64: {os.path.basename(ruta_imagen)}")
        return imagen_base64
    except Exception as e:
        logger.error(f"Error al convertir imagen a base64 {ruta_imagen}: {e}")
        return None


def crear_issue_github(titulo, cuerpo, tipo, token):
    """
    Crea un issue en el repositorio de GitHub.
    
    Args:
        titulo: Título del issue
        cuerpo: Contenido del issue
        tipo: Tipo de issue (Bug o Sugerencia)
        token: Token de autenticación de GitHub
        
    Returns:
        int: Número del issue creado o None si hay error
    """
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
        logger.info(f"Issue #{issue_number} creado exitosamente en GitHub - Tipo: {tipo}")
        return issue_number
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al crear issue en GitHub (RequestException): {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear issue en GitHub: {e}")
        raise


def mostrar_formulario_github(ventana_principal):
    """
    Muestra un formulario para crear un issue en GitHub con opción de adjuntar logs e imágenes.
    
    Args:
        ventana_principal: Referencia a la ventana principal de la aplicación
    """
    # Importar APP_VERSION desde el módulo principal
    try:
        from app import APP_VERSION
    except:
        APP_VERSION = "desconocida"
    
    # Crear una nueva ventana modal con tamaño fijo (no maximizable)
    ventana_issue = ctk.CTkToplevel(ventana_principal)
    ventana_issue.title("Crear Issue en GitHub")
    ventana_issue.geometry("550x780")  # Altura aumentada para incluir botón de imágenes
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
    nombre_entry.insert(0, ventana_principal.username)
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
    ctk.CTkRadioButton(tipo_frame, text="Bug", variable=tipo_var, value="Bug", command=lambda: actualizar_checkbox_log()).pack(side="left", padx=12)
    ctk.CTkRadioButton(tipo_frame, text="Sugerencia", variable=tipo_var, value="Sugerencia", command=lambda: actualizar_checkbox_log()).pack(side="left", padx=12)

    # Checkbox para adjuntar log (visible solo si es Bug)
    adjuntar_log_var = tk.BooleanVar(value=False)
    checkbox_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    checkbox_frame.pack(fill="x", padx=5, pady=(0,8))
    
    checkbox_log = ctk.CTkCheckBox(
        checkbox_frame,
        text="📎 Adjuntar archivo de log más reciente",
        variable=adjuntar_log_var,
        font=ctk.CTkFont(size=11)
    )
    
    def actualizar_checkbox_log():
        if tipo_var.get() == "Bug":
            checkbox_log.pack(anchor="w", padx=5)
        else:
            checkbox_log.pack_forget()
            adjuntar_log_var.set(False)
    
    # Inicializar visibilidad del checkbox
    actualizar_checkbox_log()

    # Campo de descripción
    ctk.CTkLabel(content_frame, text="Descripción:").pack(anchor="w", padx=5, pady=(4,2))
    desc_text = ctk.CTkTextbox(content_frame, height=160)
    desc_text.pack(fill="both", expand=True, padx=5, pady=(0,8))

    # Botón para adjuntar imágenes
    imagenes_seleccionadas = []
    
    def adjuntar_imagenes():
        nuevas_imagenes = seleccionar_imagenes()
        if nuevas_imagenes:
            imagenes_seleccionadas.extend(nuevas_imagenes)
            actualizar_lista_imagenes()
    
    def actualizar_lista_imagenes():
        if imagenes_seleccionadas:
            nombres = [os.path.basename(img) for img in imagenes_seleccionadas]
            label_imagenes.configure(text=f"📷 {len(imagenes_seleccionadas)} imagen(es): {', '.join(nombres[:3])}{'...' if len(nombres) > 3 else ''}")
        else:
            label_imagenes.configure(text="")
    
    btn_imagenes = ctk.CTkButton(
        content_frame,
        text="🖼️ Adjuntar Imágenes",
        command=adjuntar_imagenes,
        width=150,
        height=32
    )
    btn_imagenes.pack(anchor="w", padx=5, pady=(0,4))
    
    label_imagenes = ctk.CTkLabel(content_frame, text="", font=ctk.CTkFont(size=10), text_color="gray")
    label_imagenes.pack(anchor="w", padx=5, pady=(0,8))

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
            logger.warning("Intento de enviar issue con campos incompletos")
            return

        titulo = f"[{tipo}] Reporte de {nombre}"
        cuerpo = (
            f"Reporte creado por: {nombre}\n"
            f"Fecha: {fecha}\n"
            f"Tipo: {tipo}\n"
            f"Rol del usuario: {ventana_principal.rol}\n"
            f"Versión de la App: {APP_VERSION}\n\n"
            f"Descripción:\n{descripcion}\n"
        )
        
        # Adjuntar log si está marcado y es un Bug
        if adjuntar_log_var.get() and tipo == "Bug":
            resultado_log = obtener_log_mas_reciente(username=ventana_principal.username)
            if resultado_log:
                contenido_log, nombre_log = resultado_log
                cuerpo += f"\n\n---\n\n### 📋 Log adjunto: `{nombre_log}`\n\n"
                cuerpo += "```log\n"
                cuerpo += contenido_log
                cuerpo += "\n```\n"
            else:
                cuerpo += "\n\n⚠️ No se pudo adjuntar el archivo de log (no encontrado o error al leer).\n"
        
        # Adjuntar imágenes si hay
        if imagenes_seleccionadas:
            cuerpo += "\n\n---\n\n### 🖼️ Imágenes adjuntas:\n\n"
            
            # Mostrar progreso
            ventana_issue.update()
            
            imagenes_subidas = 0
            for idx, ruta_imagen in enumerate(imagenes_seleccionadas, 1):
                try:
                    nombre_archivo = os.path.basename(ruta_imagen)
                    
                    # Subir imagen a Backblaze B2
                    if B2_DISPONIBLE:
                        logger.info(f"Subiendo imagen {idx}/{len(imagenes_seleccionadas)} a Backblaze B2...")
                        url_b2 = subir_imagen_b2(ruta_imagen, ventana_principal.username)
                        
                        if url_b2:
                            # Incluir imagen directamente en el issue (se mostrará inline)
                            cuerpo += f"**Imagen {idx}: {nombre_archivo}**\n\n"
                            cuerpo += f"![{nombre_archivo}]({url_b2})\n\n"
                            imagenes_subidas += 1
                            logger.info(f"Imagen {idx} subida correctamente")
                        else:
                            cuerpo += f"{idx}. ⚠️ **{nombre_archivo}** - Error al subir a Backblaze B2\n"
                            logger.warning(f"No se pudo subir imagen: {nombre_archivo}")
                    else:
                        # Si Backblaze B2 no está disponible, solo mencionar la imagen
                        tamaño = os.path.getsize(ruta_imagen)
                        cuerpo += f"{idx}. **{nombre_archivo}** ({tamaño / 1024:.2f} KB)\n"
                        
                except Exception as e:
                    logger.error(f"Error al procesar imagen {ruta_imagen}: {e}")
                    cuerpo += f"{idx}. ⚠️ **Error al procesar imagen**\n"
            
            if not DROPBOX_DISPONIBLE:
                cuerpo += "\n*Nota: Dropbox no disponible. Las imágenes deben adjuntarse manualmente.*\n"
            elif imagenes_subidas > 0:
                cuerpo += f"\n*{imagenes_subidas} imagen(es) subida(s) a Dropbox correctamente.*\n"

        token = os.getenv('GITHUB_TOKEN')
        if not token:
            messagebox.showerror("Error", "No se encontró el token de GitHub. Contacte al administrador del sistema.")
            logger.error("Token de GitHub no encontrado en variables de entorno")
            return

        try:
            issue_number = crear_issue_github(titulo, cuerpo, tipo, token)
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
