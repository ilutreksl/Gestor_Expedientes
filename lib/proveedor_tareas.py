"""
Módulo para gestionar tareas de proveedores RMP.
Proporciona funcionalidades para crear, listar, actualizar y eliminar tareas asociadas a proveedores.
"""

import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger("GestorExpedientes")


def crear_tabla_tareas_proveedor(connect_db_func):
    """
    Crea la tabla tareas_proveedor si no existe.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        bool: True si se creó correctamente, False en caso de error
    """
    try:
        conn = connect_db_func()
        if not conn:
            logger.error("No se pudo conectar a la BD para crear tabla tareas_proveedor")
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tareas_proveedor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                fecha_vencimiento TEXT,
                estado TEXT DEFAULT 'Pendiente',
                creado_por TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Tabla tareas_proveedor verificada/creada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error creando tabla tareas_proveedor: {e}", exc_info=True)
        return False


def crear_tarea_proveedor(proveedor, titulo, descripcion, fecha_vencimiento, usuario, connect_db_func):
    """
    Crea una nueva tarea para un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        titulo: Título de la tarea
        descripcion: Descripción de la tarea
        fecha_vencimiento: Fecha de vencimiento (formato DD/MM/YYYY o None)
        usuario: Usuario que crea la tarea
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        if not titulo or not titulo.strip():
            return False, "El título es obligatorio"
        
        conn = connect_db_func()
        if not conn:
            logger.error("No se pudo conectar a la BD para crear tarea de proveedor")
            return False, "Error de conexión a la base de datos"
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tareas_proveedor 
            (proveedor, titulo, descripcion, fecha_vencimiento, estado, creado_por)
            VALUES (?, ?, ?, ?, 'Pendiente', ?)
        """, (proveedor, titulo.strip(), descripcion.strip() if descripcion else None, 
              fecha_vencimiento, usuario))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tarea creada para proveedor {proveedor}: '{titulo}' por {usuario}")
        return True, "Tarea creada correctamente"
        
    except Exception as e:
        logger.error(f"Error creando tarea para proveedor {proveedor}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def obtener_tareas_proveedor(proveedor, estado_filtro=None, connect_db_func=None):
    """
    Obtiene las tareas de un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        estado_filtro: Estado para filtrar ("Pendiente", "En Progreso", "Completado", None para todos)
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        list: Lista de tuplas con los datos de las tareas
    """
    try:
        conn = connect_db_func()
        if not conn:
            logger.error("No se pudo conectar a la BD para obtener tareas de proveedor")
            return []
        
        cursor = conn.cursor()
        
        if estado_filtro:
            cursor.execute("""
                SELECT id, titulo, descripcion, fecha_vencimiento, estado, creado_por, fecha_creacion
                FROM tareas_proveedor
                WHERE proveedor = ? AND estado = ?
                ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC
            """, (proveedor, estado_filtro))
        else:
            cursor.execute("""
                SELECT id, titulo, descripcion, fecha_vencimiento, estado, creado_por, fecha_creacion
                FROM tareas_proveedor
                WHERE proveedor = ?
                ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC
            """, (proveedor,))
        
        tareas = cursor.fetchall()
        conn.close()
        
        logger.debug(f"Obtenidas {len(tareas)} tareas para proveedor {proveedor}")
        return tareas
        
    except Exception as e:
        logger.error(f"Error obteniendo tareas de proveedor {proveedor}: {e}", exc_info=True)
        return []


def actualizar_estado_tarea_proveedor(tarea_id, nuevo_estado, connect_db_func):
    """
    Actualiza el estado de una tarea de proveedor.
    
    Args:
        tarea_id: ID de la tarea
        nuevo_estado: Nuevo estado ("Pendiente", "En Progreso", "Completado")
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        conn = connect_db_func()
        if not conn:
            logger.error(f"No se pudo conectar a la BD para actualizar tarea {tarea_id}")
            return False, "Error de conexión"
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tareas_proveedor
            SET estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (nuevo_estado, tarea_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tarea {tarea_id} actualizada a estado '{nuevo_estado}'")
        return True, "Estado actualizado correctamente"
        
    except Exception as e:
        logger.error(f"Error actualizando estado de tarea {tarea_id}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def eliminar_tarea_proveedor(tarea_id, connect_db_func):
    """
    Elimina una tarea de proveedor.
    
    Args:
        tarea_id: ID de la tarea
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    try:
        conn = connect_db_func()
        if not conn:
            logger.error(f"No se pudo conectar a la BD para eliminar tarea {tarea_id}")
            return False, "Error de conexión"
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tareas_proveedor WHERE id = ?", (tarea_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tarea {tarea_id} eliminada correctamente")
        return True, "Tarea eliminada correctamente"
        
    except Exception as e:
        logger.error(f"Error eliminando tarea {tarea_id}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def contar_tareas_pendientes_proveedor(proveedor, connect_db_func):
    """
    Cuenta las tareas pendientes de un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        int: Número de tareas pendientes (Pendiente + En Progreso)
    """
    try:
        conn = connect_db_func()
        if not conn:
            return 0
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM tareas_proveedor
            WHERE proveedor = ? AND estado IN ('Pendiente', 'En Progreso')
        """, (proveedor,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        return int(resultado[0]) if resultado else 0
        
    except Exception as e:
        logger.error(f"Error contando tareas pendientes de proveedor {proveedor}: {e}", exc_info=True)
        return 0
