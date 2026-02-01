"""
Módulo para gestionar adjuntos de proveedores RMP en Backblaze B2.
Proporciona funcionalidades para listar, descargar, eliminar y visualizar archivos.
"""

import logging
import os
import tempfile
import subprocess
from tkinter import filedialog, messagebox
from b2sdk.v2.exception import B2Error

logger = logging.getLogger("GestorExpedientes")


def listar_adjuntos_proveedor(proveedor_nombre, get_b2_client_func, usar_b2_func):
    """
    Lista todos los archivos de un proveedor en la carpeta RMP de Backblaze B2.
    
    Args:
        proveedor_nombre: Nombre del proveedor
        get_b2_client_func: Función para obtener cliente de B2 (retorna tupla b2_api, bucket)
        usar_b2_func: Función para verificar si B2 está habilitado
        
    Returns:
        list: Lista de diccionarios con información de archivos
              [{'nombre': str, 'path': str, 'tamaño': int, 'modificado': str}, ...]
    """
    try:
        if not usar_b2_func():
            logger.warning("Backblaze B2 no está configurado para listar adjuntos de proveedor")
            return []
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            logger.error("No se pudo obtener cliente de Backblaze B2")
            return []
        
        # Buscar archivos en RMP/ que empiecen con el nombre del proveedor
        # Limpiar nombre del proveedor para comparación
        proveedor_limpio = proveedor_nombre.strip().lower()
        
        try:
            # Listar todos los archivos en RMP/
            archivos = []
            
            for file_version_info, _ in bucket.ls(folder_to_list='RMP/', latest_only=True):
                nombre_archivo = os.path.basename(file_version_info.file_name)
                # Verificar si el nombre del archivo empieza con el nombre del proveedor
                if nombre_archivo.lower().startswith(proveedor_limpio):
                    archivo_info = {
                        'nombre': nombre_archivo,
                        'path': file_version_info.file_name,
                        'tamaño': file_version_info.size,
                        'modificado': file_version_info.upload_timestamp
                    }
                    archivos.append(archivo_info)
            
            logger.info(f"Listados {len(archivos)} adjuntos para proveedor {proveedor_nombre}")
            return archivos
            
        except B2Error as e:
            logger.error(f"Error listando archivos en B2: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Error listando adjuntos de proveedor {proveedor_nombre}: {e}", exc_info=True)
        return []


def descargar_adjunto_proveedor(b2_path, get_b2_client_func, usar_b2_func):
    """
    Descarga un archivo de Backblaze B2 y lo guarda en la ubicación elegida por el usuario.
    
    Args:
        b2_path: Ruta del archivo en B2
        get_b2_client_func: Función para obtener cliente de B2
        usar_b2_func: Función para verificar si B2 está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje/ruta)
    """
    try:
        if not usar_b2_func():
            return False, "Backblaze B2 no está configurado"
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            return False, "No se pudo conectar a Backblaze B2"
        
        # Obtener nombre del archivo
        nombre_archivo = os.path.basename(b2_path)
        
        # Pedir ubicación de descarga
        ruta_descarga = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(nombre_archivo)[1],
            initialfile=nombre_archivo,
            title="Guardar archivo como"
        )
        
        if not ruta_descarga:
            return False, "Descarga cancelada"
        
        # Descargar archivo desde B2
        downloaded_file = bucket.download_file_by_name(b2_path)
        downloaded_file.save_to(ruta_descarga)
        
        logger.info(f"Archivo descargado: {b2_path} -> {ruta_descarga}")
        return True, ruta_descarga
        
    except B2Error as e:
        logger.error(f"Error descargando archivo {b2_path} desde B2: {e}", exc_info=True)
        return False, f"Error B2: {str(e)}"
    except Exception as e:
        logger.error(f"Error descargando archivo {b2_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def eliminar_adjunto_proveedor(b2_path, get_b2_client_func, usar_b2_func):
    """
    Elimina un archivo de Backblaze B2.
    
    Args:
        b2_path: Ruta del archivo en B2
        get_b2_client_func: Función para obtener cliente de B2
        usar_b2_func: Función para verificar si B2 está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_b2_func():
            return False, "Backblaze B2 no está configurado"
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            return False, "No se pudo conectar a Backblaze B2"
        
        # Listar archivo para obtener file_id
        file_id = None
        for file_version_info, _ in bucket.ls(b2_path, latest_only=True):
            if file_version_info.file_name == b2_path:
                file_id = file_version_info.id_
                break
        
        if not file_id:
            return False, "Archivo no encontrado en B2"
        
        # Eliminar archivo
        b2_api.delete_file_version(file_id, b2_path)
        
        logger.info(f"Archivo eliminado de Backblaze B2: {b2_path}")
        return True, "Archivo eliminado correctamente"
        
    except B2Error as e:
        logger.error(f"Error eliminando archivo {b2_path} de B2: {e}", exc_info=True)
        return False, f"Error B2: {str(e)}"
    except Exception as e:
        logger.error(f"Error eliminando archivo {b2_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def visualizar_adjunto_proveedor(b2_path, get_b2_client_func, usar_b2_func):
    """
    Descarga temporalmente y abre un archivo de Backblaze B2.
    
    Args:
        b2_path: Ruta del archivo en B2
        get_b2_client_func: Función para obtener cliente de B2
        usar_b2_func: Función para verificar si B2 está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_b2_func():
            return False, "Backblaze B2 no está configurado"
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            return False, "No se pudo conectar a Backblaze B2"
        
        # Obtener nombre y extensión del archivo
        nombre_archivo = os.path.basename(b2_path)
        _, extension = os.path.splitext(nombre_archivo)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
            tmp_path = tmp_file.name
        
        # Descargar archivo desde B2
        downloaded_file = bucket.download_file_by_name(b2_path)
        downloaded_file.save_to(tmp_path)
        
        # Abrir archivo con aplicación predeterminada
        if os.name == 'nt':  # Windows
            os.startfile(tmp_path)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.call(['open', tmp_path])
        
        logger.info(f"Archivo abierto para visualización: {b2_path}")
        return True, "Archivo abierto correctamente"
        
    except B2Error as e:
        logger.error(f"Error visualizando archivo {b2_path} desde B2: {e}", exc_info=True)
        return False, f"Error B2: {str(e)}"
    except Exception as e:
        logger.error(f"Error visualizando archivo {b2_path}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def subir_adjunto_proveedor(proveedor_nombre, get_b2_client_func, usar_b2_func):
    """
    Permite al usuario seleccionar y subir un archivo a Backblaze B2.
    
    Args:
        proveedor_nombre: Nombre del proveedor
        get_b2_client_func: Función para obtener cliente de B2
        usar_b2_func: Función para verificar si B2 está habilitado
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not usar_b2_func():
            return False, "Backblaze B2 no está configurado"
        
        # Pedir archivo local
        archivo_local = filedialog.askopenfilename(
            title="Seleccionar archivo para subir"
        )
        
        if not archivo_local:
            return False, "Selección cancelada"
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            return False, "No se pudo conectar a Backblaze B2"
        
        # Obtener nombre del archivo
        nombre_archivo = os.path.basename(archivo_local)
        
        # Construir ruta en B2
        # Formato: RMP/{nombre_proveedor}_{nombre_archivo}
        safe_proveedor = ''.join(c for c in proveedor_nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_proveedor = safe_proveedor.replace(' ', '_')
        
        b2_path = f"RMP/{safe_proveedor}_{nombre_archivo}"
        
        # Subir archivo a B2
        bucket.upload_local_file(
            local_file=archivo_local,
            file_name=b2_path
        )
        
        logger.info(f"Archivo subido a Backblaze B2: {b2_path}")
        return True, f"Archivo '{nombre_archivo}' subido correctamente"
        
    except B2Error as e:
        logger.error(f"Error subiendo archivo para proveedor {proveedor_nombre} a B2: {e}", exc_info=True)
        return False, f"Error B2: {str(e)}"
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

