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
from lib.logger_config import get_logger

logger = get_logger()


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
    texto_mensaje.insert("1.0", mensaje_content)
    texto_mensaje.configure(state="disabled")  # Solo lectura
    
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
            for idx, ruta_imagen in enumerate(imagenes_seleccionadas, 1):
                try:
                    nombre_archivo = os.path.basename(ruta_imagen)
                    # GitHub issues soportan imágenes mediante markdown, pero necesitamos subirlas primero
                    # Por ahora, incluimos el nombre y una nota
                    cuerpo += f"{idx}. **{nombre_archivo}**\n"
                    
                    # Intentar leer y codificar imagen (limitado a 1MB por imagen)
                    tamaño = os.path.getsize(ruta_imagen)
                    if tamaño < 1024 * 1024:  # Menor a 1MB
                        # Nota: GitHub API no permite adjuntar imágenes directamente en issues via API
                        # Se incluye referencia al nombre del archivo
                        cuerpo += f"   - Tamaño: {tamaño / 1024:.2f} KB\n"
                    else:
                        cuerpo += f"   - ⚠️ Archivo muy grande ({tamaño / (1024*1024):.2f} MB), no adjuntado\n"
                        logger.warning(f"Imagen muy grande para adjuntar: {nombre_archivo}")
                except Exception as e:
                    logger.error(f"Error al procesar imagen {ruta_imagen}: {e}")
                    cuerpo += f"   - ⚠️ Error al procesar imagen\n"
            
            cuerpo += "\n*Nota: Las imágenes deben ser adjuntadas manualmente al issue después de su creación.*\n"

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
