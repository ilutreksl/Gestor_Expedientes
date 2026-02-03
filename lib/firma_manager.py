"""
Gestor de firmas de usuario en Backblaze B2.

Este módulo gestiona la carga, descarga y eliminación de firmas digitales
de los usuarios en el almacenamiento B2.
"""

import os
from lib.logger_config import get_logger

logger = get_logger()


def subir_firma_usuario_b2(username, ruta_imagen_local, get_b2_client_func):
    """
    Sube la firma de un usuario a B2 en la carpeta Firmas/.
    
    Args:
        username (str): Nombre del usuario
        ruta_imagen_local (str): Ruta local del archivo PNG
        get_b2_client_func: Función para obtener el cliente B2
        
    Returns:
        tuple: (exito, mensaje) - (True, nombre_archivo) si éxito, (False, error) si falla
    """
    try:
        logger.info(f"Iniciando subida de firma para usuario: {username}")
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            error_msg = "No se pudo conectar con Backblaze B2"
            logger.error(f"Subida de firma fallida: {error_msg}")
            return False, error_msg
        
        # Validar que el archivo existe
        if not os.path.exists(ruta_imagen_local):
            error_msg = f"El archivo no existe: {ruta_imagen_local}"
            logger.error(f"Subida de firma fallida: {error_msg}")
            return False, error_msg
        
        # Validar que es PNG
        if not ruta_imagen_local.lower().endswith('.png'):
            error_msg = "Solo se aceptan archivos PNG"
            logger.warning(f"Intento de subir archivo no PNG: {ruta_imagen_local}")
            return False, error_msg
        
        # Nombre del archivo en B2
        nombre_archivo = f"firma_{username}.png"
        ruta_b2 = f"Firmas/{nombre_archivo}"
        
        logger.debug(f"Subiendo firma a B2: {ruta_b2}")
        
        # Subir archivo
        bucket.upload_local_file(
            local_file=ruta_imagen_local,
            file_name=ruta_b2
        )
        
        logger.info(f"Firma subida correctamente para usuario '{username}' -> {ruta_b2}")
        return True, nombre_archivo
        
    except Exception as e:
        error_msg = f"Error al subir firma para {username}: {e}"
        logger.error(error_msg, exc_info=True)
        return False, str(e)


def descargar_firma_usuario_b2(username, ruta_destino, get_b2_client_func):
    """
    Descarga la firma de un usuario desde B2.
    
    Args:
        username (str): Nombre del usuario
        ruta_destino (str): Ruta local donde guardar la firma
        get_b2_client_func: Función para obtener el cliente B2
        
    Returns:
        bool: True si éxito, False si falla
    """
    try:
        logger.info(f"Iniciando descarga de firma para usuario: {username}")
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            logger.error("Descarga de firma fallida: No se pudo conectar con B2")
            return False
        
        # Nombre del archivo en B2
        nombre_archivo = f"firma_{username}.png"
        ruta_b2 = f"Firmas/{nombre_archivo}"
        
        logger.debug(f"Descargando firma desde B2: {ruta_b2} -> {ruta_destino}")
        
        # Descargar archivo
        bucket.download_file_by_name(
            file_name=ruta_b2,
            local_file=ruta_destino
        )
        
        # Verificar que se descargó
        if os.path.exists(ruta_destino):
            tamanio = os.path.getsize(ruta_destino)
            logger.info(f"Firma descargada correctamente para usuario '{username}' ({tamanio} bytes)")
            return True
        else:
            logger.error(f"El archivo descargado no existe: {ruta_destino}")
            return False
        
    except Exception as e:
        error_msg = f"Error al descargar firma para {username}: {e}"
        logger.error(error_msg, exc_info=True)
        return False


def eliminar_firma_usuario_b2(username, get_b2_client_func):
    """
    Elimina la firma de un usuario de B2.
    
    Args:
        username (str): Nombre del usuario
        get_b2_client_func: Función para obtener el cliente B2
        
    Returns:
        bool: True si éxito, False si falla
    """
    try:
        logger.info(f"Iniciando eliminación de firma para usuario: {username}")
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            logger.error("Eliminación de firma fallida: No se pudo conectar con B2")
            return False
        
        # Nombre del archivo en B2
        nombre_archivo = f"firma_{username}.png"
        ruta_b2 = f"Firmas/{nombre_archivo}"
        
        logger.debug(f"Eliminando firma de B2: {ruta_b2}")
        
        # Buscar y eliminar archivo
        try:
            file_version = bucket.get_file_info_by_name(ruta_b2)
            if file_version:
                b2_api.delete_file_version(file_version.id_, ruta_b2)
                logger.info(f"Firma eliminada correctamente para usuario '{username}'")
                return True
            else:
                logger.warning(f"No se encontró firma para usuario '{username}' en B2")
                return False
        except Exception as e:
            # Si el archivo no existe, no es un error crítico
            error_str = str(e).lower()
            if "not_found" in error_str or "does not exist" in error_str or "not present" in error_str or "filenotpresent" in error_str:
                logger.warning(f"No se encontró firma para usuario '{username}': {e}")
                return True  # Retornar True porque el objetivo (que no exista) se cumplió
            else:
                raise
        
    except Exception as e:
        error_msg = f"Error al eliminar firma para {username}: {e}"
        logger.error(error_msg, exc_info=True)
        return False


def verificar_firma_usuario_existe(username, get_b2_client_func):
    """
    Verifica si existe una firma para el usuario en B2.
    
    Args:
        username (str): Nombre del usuario
        get_b2_client_func: Función para obtener el cliente B2
        
    Returns:
        bool: True si existe, False si no
    """
    try:
        logger.debug(f"Verificando existencia de firma para usuario: {username}")
        
        b2_api, bucket = get_b2_client_func()
        if not b2_api or not bucket:
            logger.debug("Verificación de firma: No hay conexión B2")
            return False
        
        # Nombre del archivo en B2
        nombre_archivo = f"firma_{username}.png"
        ruta_b2 = f"Firmas/{nombre_archivo}"
        
        # Intentar obtener info del archivo
        try:
            file_info = bucket.get_file_info_by_name(ruta_b2)
            existe = file_info is not None
            logger.debug(f"Firma para usuario '{username}': {'EXISTE' if existe else 'NO EXISTE'}")
            return existe
        except Exception as e:
            # Si el archivo no existe, retornar False
            if "not_found" in str(e).lower() or "does not exist" in str(e).lower():
                logger.debug(f"Firma no encontrada para usuario '{username}'")
                return False
            else:
                logger.warning(f"Error al verificar firma para {username}: {e}")
                return False
        
    except Exception as e:
        logger.error(f"Error inesperado al verificar firma para {username}: {e}", exc_info=True)
        return False
