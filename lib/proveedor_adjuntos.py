"""
Módulo para gestionar adjuntos de proveedores RMP en Dropbox.
Proporciona funcionalidades para listar, descargar, eliminar y visualizar archivos.
"""

import logging
import os
import tempfile
import subprocess
from tkinter import filedialog, messagebox

logger = logging.getLogger("GestorExpedientes")


def listar_adjuntos_proveedor(proveedor_nombre, get_dropbox_client_func, usar_dropbox_func):
    """
    Lista todos los archivos de un proveedor en la carpeta RMP de Dropbox.
    
    Args:
        proveedor_nombre: Nombre del proveedor
        get_dropbox_client_func: Función para obtener cliente de Dropbox
        usar_dropbox_func: Función para verificar si Dropbox está habilitado
        
    Returns:
        list: Lista de diccionarios con información de archivos
              [{'nombre': str, 'path': str, 'tamaño': int, 'modificado': str}, ...]
    """
    try:
        if not usar_dropbox_func():
            logger.warning("Dropbox no está configurado para listar adjuntos de proveedor")
            return []
        
        dbx = get_dropbox_client_func()
        if not dbx:
            logger.error("No se pudo obtener cliente de Dropbox")
            return []
        
        # Buscar archivos en /RMP/ que empiecen con el nombre del proveedor
        # Limpiar nombre del proveedor para comparación
        proveedor_limpio = proveedor_nombre.strip().lower()
        
        try:
            # Listar todos los archivos en /RMP/
            resultado = dbx.files_list_folder('/RMP')
            archivos = []
            
            for entry in resultado.entries:
                # Verificar si es un archivo (no carpeta)
                if hasattr(entry, 'name'):
                    nombre_archivo = entry.name
                    # Verificar si el nombre del archivo empieza con el nombre del proveedor
                    if nombre_archivo.lower().startswith(proveedor_limpio):
                        archivo_info = {
                            'nombre': nombre_archivo,
                            'path': entry.path_display,
                            'tamaño': getattr(entry, 'size', 0),
                            'modificado': getattr(entry, 'server_modified', None)
                        }
                        archivos.append(archivo_info)
            
            logger.info(f"Listados {len(archivos)} adjuntos para proveedor {proveedor_nombre}")
            return archivos
            
        except Exception as e:
            if 'not_found' in str(e):
                logger.info(f"Carpeta /RMP no encontrada en Dropbox")
                return []
            else:
                raise
        
    except Exception as e:
        logger.error(f"Error listando adjuntos de proveedor {proveedor_nombre}: {e}", exc_info=True)
        return []


def descargar_adjunto_proveedor(dropbox_path, get_dropbox_client_func, usar_dropbox_func):
    """
    Descarga un archivo de Dropbox y lo guarda en la ubicación elegida por el usuario.
    
    Args:
        dropbox_path: Ruta del archivo en Dropbox
        get_dropbox_client_func: Función para obtener cliente de Dropbox
        usar_dropbox_func: Función para verificar si Dropbox está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje/ruta)
    """
    try:
        if not usar_dropbox_func():
            return False, "Dropbox no está configurado"
        
        dbx = get_dropbox_client_func()
        if not dbx:
            return False, "No se pudo conectar a Dropbox"
        
        # Obtener nombre del archivo
        nombre_archivo = os.path.basename(dropbox_path)
        
        # Pedir ubicación de descarga
        ruta_descarga = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(nombre_archivo)[1],
            initialfile=nombre_archivo,
            title="Guardar archivo como"
        )
        
        if not ruta_descarga:
            return False, "Descarga cancelada"
        
        # Descargar archivo
        metadata, response = dbx.files_download(dropbox_path)
        
        with open(ruta_descarga, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Archivo descargado: {dropbox_path} -> {ruta_descarga}")
        return True, ruta_descarga
        
    except Exception as e:
        logger.error(f"Error descargando archivo {dropbox_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def eliminar_adjunto_proveedor(dropbox_path, get_dropbox_client_func, usar_dropbox_func):
    """
    Elimina un archivo de Dropbox.
    
    Args:
        dropbox_path: Ruta del archivo en Dropbox
        get_dropbox_client_func: Función para obtener cliente de Dropbox
        usar_dropbox_func: Función para verificar si Dropbox está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_dropbox_func():
            return False, "Dropbox no está configurado"
        
        dbx = get_dropbox_client_func()
        if not dbx:
            return False, "No se pudo conectar a Dropbox"
        
        # Eliminar archivo
        dbx.files_delete_v2(dropbox_path)
        
        logger.info(f"Archivo eliminado de Dropbox: {dropbox_path}")
        return True, "Archivo eliminado correctamente"
        
    except Exception as e:
        logger.error(f"Error eliminando archivo {dropbox_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def visualizar_adjunto_proveedor(dropbox_path, get_dropbox_client_func, usar_dropbox_func):
    """
    Descarga temporalmente y abre un archivo de Dropbox.
    
    Args:
        dropbox_path: Ruta del archivo en Dropbox
        get_dropbox_client_func: Función para obtener cliente de Dropbox
        usar_dropbox_func: Función para verificar si Dropbox está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_dropbox_func():
            return False, "Dropbox no está configurado"
        
        dbx = get_dropbox_client_func()
        if not dbx:
            return False, "No se pudo conectar a Dropbox"
        
        # Obtener nombre y extensión del archivo
        nombre_archivo = os.path.basename(dropbox_path)
        _, extension = os.path.splitext(nombre_archivo)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
            # Descargar archivo
            metadata, response = dbx.files_download(dropbox_path)
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        # Abrir archivo con aplicación predeterminada
        if os.name == 'nt':  # Windows
            os.startfile(tmp_path)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.call(['open', tmp_path])
        
        logger.info(f"Archivo abierto para visualización: {dropbox_path}")
        return True, "Archivo abierto correctamente"
        
    except Exception as e:
        logger.error(f"Error visualizando archivo {dropbox_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def subir_adjunto_proveedor(proveedor_nombre, get_dropbox_client_func, usar_dropbox_func):
    """
    Permite al usuario seleccionar y subir un archivo a Dropbox.
    
    Args:
        proveedor_nombre: Nombre del proveedor
        get_dropbox_client_func: Función para obtener cliente de Dropbox
        usar_dropbox_func: Función para verificar si Dropbox está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_dropbox_func():
            return False, "Dropbox no está configurado"
        
        # Pedir archivo local
        archivo_local = filedialog.askopenfilename(
            title="Seleccionar archivo para subir"
        )
        
        if not archivo_local:
            return False, "Selección cancelada"
        
        dbx = get_dropbox_client_func()
        if not dbx:
            return False, "No se pudo conectar a Dropbox"
        
        # Obtener nombre del archivo
        nombre_archivo = os.path.basename(archivo_local)
        
        # Construir ruta en Dropbox
        # Formato: /RMP/{nombre_proveedor}_{nombre_archivo}
        safe_proveedor = ''.join(c for c in proveedor_nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_proveedor = safe_proveedor.replace(' ', '_')
        
        dropbox_path = f"/RMP/{safe_proveedor}_{nombre_archivo}"
        
        # Subir archivo
        with open(archivo_local, 'rb') as f:
            import dropbox
            dbx.files_upload(
                f.read(),
                dropbox_path,
                mode=dropbox.files.WriteMode('overwrite')
            )
        
        logger.info(f"Archivo subido a Dropbox: {dropbox_path}")
        return True, f"Archivo '{nombre_archivo}' subido correctamente"
        
    except Exception as e:
        logger.error(f"Error subiendo archivo para proveedor {proveedor_nombre}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def formatear_tamaño(bytes):
    """
    Formatea el tamaño en bytes a una representación legible.
    
    Args:
        bytes: Tamaño en bytes
        
    Returns:
        str: Tamaño formateado (ej: "1.5 MB")
    """
    for unidad in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unidad}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"
