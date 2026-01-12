"""
Módulo para gestionar los tipos de cliente del sistema.
Permite cargar, guardar, añadir y eliminar tipos de cliente desde un archivo JSON.
"""

import json
import os
from lib.logger_config import get_logger

logger = get_logger()

# Ruta al archivo JSON de tipos de cliente
TIPOS_CLIENTE_FILE = os.path.join("Diccionarios", "tipos_cliente.json")


def cargar_tipos_cliente():
    """
    Carga los tipos de cliente desde el archivo JSON.
    
    Returns:
        list: Lista de tipos de cliente. Si no existe el archivo, retorna valores por defecto.
    """
    try:
        if os.path.exists(TIPOS_CLIENTE_FILE):
            with open(TIPOS_CLIENTE_FILE, 'r', encoding='utf-8') as f:
                tipos = json.load(f)
                logger.info(f"Tipos de cliente cargados: {len(tipos)} tipos")
                return tipos
        else:
            logger.warning(f"Archivo {TIPOS_CLIENTE_FILE} no encontrado, usando valores por defecto")
            # Crear archivo con valores por defecto
            tipos_default = ["Normal", "Distribuidor", "VIP"]
            guardar_tipos_cliente(tipos_default)
            return tipos_default
            
    except Exception as e:
        logger.error(f"Error al cargar tipos de cliente: {e}")
        # Retornar valores por defecto en caso de error
        return ["Normal", "Distribuidor", "VIP"]


def guardar_tipos_cliente(tipos):
    """
    Guarda la lista de tipos de cliente en el archivo JSON.
    
    Args:
        tipos: Lista de tipos de cliente a guardar
        
    Returns:
        bool: True si se guardó correctamente, False en caso de error
    """
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(TIPOS_CLIENTE_FILE), exist_ok=True)
        
        # Guardar en archivo JSON con formato legible
        with open(TIPOS_CLIENTE_FILE, 'w', encoding='utf-8') as f:
            json.dump(tipos, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Tipos de cliente guardados correctamente: {len(tipos)} tipos")
        return True
        
    except Exception as e:
        logger.error(f"Error al guardar tipos de cliente: {e}")
        return False


def anadir_tipo_cliente(nuevo_tipo):
    """
    Añade un nuevo tipo de cliente a la lista.
    
    Args:
        nuevo_tipo: Nombre del nuevo tipo de cliente
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validar que no esté vacío
        if not nuevo_tipo or not nuevo_tipo.strip():
            logger.warning("Intento de añadir tipo de cliente vacío")
            return False, "El tipo de cliente no puede estar vacío"
        
        nuevo_tipo = nuevo_tipo.strip()
        
        # Cargar tipos existentes
        tipos = cargar_tipos_cliente()
        
        # Verificar que no exista ya (case-insensitive)
        if any(tipo.lower() == nuevo_tipo.lower() for tipo in tipos):
            logger.warning(f"Intento de añadir tipo duplicado: {nuevo_tipo}")
            return False, f"El tipo '{nuevo_tipo}' ya existe"
        
        # Añadir el nuevo tipo
        tipos.append(nuevo_tipo)
        
        # Guardar
        if guardar_tipos_cliente(tipos):
            logger.info(f"Tipo de cliente añadido: {nuevo_tipo}")
            return True, f"Tipo '{nuevo_tipo}' añadido correctamente"
        else:
            return False, "Error al guardar los cambios"
            
    except Exception as e:
        logger.error(f"Error al añadir tipo de cliente: {e}")
        return False, f"Error: {str(e)}"


def eliminar_tipo_cliente(tipo_a_eliminar):
    """
    Elimina un tipo de cliente de la lista.
    
    Args:
        tipo_a_eliminar: Nombre del tipo de cliente a eliminar
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Cargar tipos existentes
        tipos = cargar_tipos_cliente()
        
        # Verificar que exista
        if tipo_a_eliminar not in tipos:
            logger.warning(f"Intento de eliminar tipo inexistente: {tipo_a_eliminar}")
            return False, f"El tipo '{tipo_a_eliminar}' no existe"
        
        # No permitir eliminar si es el último
        if len(tipos) <= 1:
            logger.warning("Intento de eliminar el último tipo de cliente")
            return False, "No se puede eliminar el último tipo de cliente"
        
        # Eliminar el tipo
        tipos.remove(tipo_a_eliminar)
        
        # Guardar
        if guardar_tipos_cliente(tipos):
            logger.info(f"Tipo de cliente eliminado: {tipo_a_eliminar}")
            return True, f"Tipo '{tipo_a_eliminar}' eliminado correctamente"
        else:
            return False, "Error al guardar los cambios"
            
    except Exception as e:
        logger.error(f"Error al eliminar tipo de cliente: {e}")
        return False, f"Error: {str(e)}"


def editar_tipo_cliente(tipo_antiguo, tipo_nuevo):
    """
    Edita un tipo de cliente existente.
    
    Args:
        tipo_antiguo: Nombre actual del tipo de cliente
        tipo_nuevo: Nuevo nombre para el tipo de cliente
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validar que el nuevo nombre no esté vacío
        if not tipo_nuevo or not tipo_nuevo.strip():
            logger.warning("Intento de editar tipo de cliente con nombre vacío")
            return False, "El nuevo nombre no puede estar vacío"
        
        tipo_nuevo = tipo_nuevo.strip()
        
        # Cargar tipos existentes
        tipos = cargar_tipos_cliente()
        
        # Verificar que el tipo antiguo exista
        if tipo_antiguo not in tipos:
            logger.warning(f"Intento de editar tipo inexistente: {tipo_antiguo}")
            return False, f"El tipo '{tipo_antiguo}' no existe"
        
        # Verificar que el nuevo nombre no exista ya (excepto si es el mismo)
        if tipo_antiguo.lower() != tipo_nuevo.lower():
            if any(tipo.lower() == tipo_nuevo.lower() for tipo in tipos):
                logger.warning(f"Intento de renombrar a tipo duplicado: {tipo_nuevo}")
                return False, f"El tipo '{tipo_nuevo}' ya existe"
        
        # Reemplazar el tipo
        index = tipos.index(tipo_antiguo)
        tipos[index] = tipo_nuevo
        
        # Guardar
        if guardar_tipos_cliente(tipos):
            logger.info(f"Tipo de cliente editado: '{tipo_antiguo}' -> '{tipo_nuevo}'")
            return True, f"Tipo renombrado de '{tipo_antiguo}' a '{tipo_nuevo}'"
        else:
            return False, "Error al guardar los cambios"
            
    except Exception as e:
        logger.error(f"Error al editar tipo de cliente: {e}")
        return False, f"Error: {str(e)}"
