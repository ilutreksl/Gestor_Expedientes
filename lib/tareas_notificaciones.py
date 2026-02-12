"""
Sistema de notificaciones de tareas para Gestor de Expedientes.

Este módulo maneja:
- Notificaciones de tareas vencidas/hoy
- Badge visual con contador de tareas pendientes
- Panel desplegable de tareas
- Integración con plyer para notificaciones nativas
"""

import datetime
import sqlite3
from typing import List, Dict, Tuple, Optional
from lib.logger_config import get_logger

logger = get_logger()

# Intentar importar plyer para notificaciones nativas
try:
    from plyer import notification
    PLYER_DISPONIBLE = True
    logger.info("Módulo plyer cargado correctamente para notificaciones")
except ImportError:
    PLYER_DISPONIBLE = False
    logger.warning("Módulo plyer no disponible. Notificaciones del sistema deshabilitadas.")
    notification = None


def actualizar_tabla_tareas(connect_db_func):
    """
    Añade las columnas asignado_a y prioridad a la tabla tareas si no existen.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
    """
    logger.info("Verificando/actualizando estructura de tabla tareas")
    
    try:
        # Manejar ambos casos: tupla (conn, cursor) o solo conn
        result = connect_db_func()
        if isinstance(result, tuple):
            conn, cursor = result
        else:
            conn = result
            cursor = conn.cursor() if conn else None
        
        # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return False
        
        # Verificar si la columna asignado_a existe
        cursor.execute("PRAGMA table_info(tareas)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'asignado_a' not in columnas:
            logger.info("Añadiendo columna 'asignado_a' a tabla tareas")
            cursor.execute("ALTER TABLE tareas ADD COLUMN asignado_a TEXT")
            conn.commit()
            logger.info("Columna 'asignado_a' añadida correctamente")
        
        if 'prioridad' not in columnas:
            logger.info("Añadiendo columna 'prioridad' a tabla tareas")
            cursor.execute("ALTER TABLE tareas ADD COLUMN prioridad TEXT DEFAULT 'Normal'")
            conn.commit()
            logger.info("Columna 'prioridad' añadida correctamente")
        
        conn.close()
        logger.info("Estructura de tabla tareas actualizada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar tabla tareas: {e}", exc_info=True)
        return False


def obtener_tareas_pendientes_usuario(connect_db_func, usuario: str) -> List[Dict]:
    """
    Obtiene todas las tareas pendientes asignadas a un usuario.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        usuario: Nombre del usuario
        
    Returns:
        Lista de diccionarios con información de tareas pendientes
    """
    logger.debug(f"Obteniendo tareas pendientes para usuario: {usuario}")
    
    try:
        # Manejar ambos casos: tupla (conn, cursor) o solo conn
        result = connect_db_func()
        if isinstance(result, tuple):
            conn, cursor = result
        else:
            conn = result
            cursor = conn.cursor() if conn else None
        
        # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return []
        
        # Obtener todas las tareas pendientes (asignadas o creadas por el usuario)
        cursor.execute("""
            SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, 
                   estado, prioridad, creado_por, asignado_a
            FROM tareas 
            WHERE (asignado_a = ? OR (asignado_a IS NULL AND creado_por = ?))
            AND estado NOT IN ('Completado', 'Completada', 'Finalizada')
            ORDER BY 
                CASE prioridad 
                    WHEN 'Alta' THEN 1 
                    WHEN 'Normal' THEN 2 
                    WHEN 'Baja' THEN 3 
                    ELSE 4 
                END,
                fecha_vencimiento ASC
        """, (usuario, usuario))
        
        tareas = []
        for row in cursor.fetchall():
            tarea = {
                'id': row[0],
                'codigo_rma': row[1],
                'titulo': row[2],
                'descripcion': row[3],
                'fecha_vencimiento': row[4],
                'estado': row[5],
                'prioridad': row[6] or 'Normal',
                'creado_por': row[7],
                'asignado_a': row[8]
            }
            tareas.append(tarea)
        
        conn.close()
        logger.info(f"Se encontraron {len(tareas)} tareas pendientes para {usuario}")
        return tareas
        
    except Exception as e:
        logger.error(f"Error al obtener tareas pendientes: {e}", exc_info=True)
        return []


def obtener_tareas_vencidas_hoy(connect_db_func, usuario: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Obtiene tareas vencidas y tareas para hoy de un usuario.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        usuario: Nombre del usuario
        
    Returns:
        Tupla con (tareas_vencidas, tareas_hoy)
    """
    logger.debug(f"Obteniendo tareas vencidas/hoy para usuario: {usuario}")
    
    try:
        hoy = datetime.date.today().strftime("%Y-%m-%d")
        
        # Manejar ambos casos: tupla (conn, cursor) o solo conn
        result = connect_db_func()
        if isinstance(result, tuple):
            conn, cursor = result
        else:
            conn = result
            cursor = conn.cursor() if conn else None
                # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return [], []
                # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return [], []
        
        # Tareas vencidas (fecha < hoy)
        cursor.execute("""
            SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, 
                   estado, prioridad, creado_por, asignado_a
            FROM tareas 
            WHERE (asignado_a = ? OR (asignado_a IS NULL AND creado_por = ?))
            AND estado NOT IN ('Completado', 'Completada', 'Finalizada')
            AND fecha_vencimiento IS NOT NULL
            AND fecha_vencimiento < ?
            ORDER BY fecha_vencimiento ASC
        """, (usuario, usuario, hoy))
        
        tareas_vencidas = []
        for row in cursor.fetchall():
            tarea = {
                'id': row[0],
                'codigo_rma': row[1],
                'titulo': row[2],
                'descripcion': row[3],
                'fecha_vencimiento': row[4],
                'estado': row[5],
                'prioridad': row[6] or 'Normal',
                'creado_por': row[7],
                'asignado_a': row[8]
            }
            tareas_vencidas.append(tarea)
        
        # Tareas para hoy (fecha == hoy)
        cursor.execute("""
            SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, 
                   estado, prioridad, creado_por, asignado_a
            FROM tareas 
            WHERE (asignado_a = ? OR (asignado_a IS NULL AND creado_por = ?))
            AND estado NOT IN ('Completado', 'Completada', 'Finalizada')
            AND fecha_vencimiento = ?
            ORDER BY 
                CASE prioridad 
                    WHEN 'Alta' THEN 1 
                    WHEN 'Normal' THEN 2 
                    WHEN 'Baja' THEN 3 
                    ELSE 4 
                END
        """, (usuario, usuario, hoy))
        
        tareas_hoy = []
        for row in cursor.fetchall():
            tarea = {
                'id': row[0],
                'codigo_rma': row[1],
                'titulo': row[2],
                'descripcion': row[3],
                'fecha_vencimiento': row[4],
                'estado': row[5],
                'prioridad': row[6] or 'Normal',
                'creado_por': row[7],
                'asignado_a': row[8]
            }
            tareas_hoy.append(tarea)
        
        conn.close()
        logger.info(f"Usuario {usuario}: {len(tareas_vencidas)} vencidas, {len(tareas_hoy)} para hoy")
        return tareas_vencidas, tareas_hoy
        
    except Exception as e:
        logger.error(f"Error al obtener tareas vencidas/hoy: {e}", exc_info=True)
        return [], []


def contar_tareas_pendientes(connect_db_func, usuario: str) -> int:
    """
    Cuenta el total de tareas pendientes de un usuario.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        usuario: Nombre del usuario
        
    Returns:
        Número de tareas pendientes
    """
    try:
        # Manejar ambos casos: tupla (conn, cursor) o solo conn
        result = connect_db_func()
        if isinstance(result, tuple):
            conn, cursor = result
        else:
            conn = result
            cursor = conn.cursor() if conn else None
        
        # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return 0
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM tareas 
            WHERE (asignado_a = ? OR (asignado_a IS NULL AND creado_por = ?))
            AND estado NOT IN ('Completado', 'Completada', 'Finalizada')
        """, (usuario, usuario))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        # Asegurar que retornamos un entero
        count = int(count) if count is not None else 0
        logger.debug(f"Usuario {usuario} tiene {count} tareas pendientes")
        return count
        
    except Exception as e:
        logger.error(f"Error al contar tareas pendientes: {e}", exc_info=True)
        return 0


def enviar_notificacion_nativa(titulo: str, mensaje: str, icono: Optional[str] = None, timeout: int = 10, reproducir_sonido: bool = True):
    """
    Envía una notificación nativa del sistema usando plyer.
    
    Args:
        titulo: Título de la notificación
        mensaje: Mensaje de la notificación
        icono: Ruta al icono (opcional)
        timeout: Duración en segundos
        reproducir_sonido: Si debe reproducir sonido de notificación
    """
    if not PLYER_DISPONIBLE:
        logger.debug("plyer no disponible, saltando notificación nativa")
        return False
    
    try:
        logger.info(f"Enviando notificación: {titulo}")
        notification.notify(
            title=titulo,
            message=mensaje,
            app_name='Gestor de Expedientes',
            app_icon=icono,
            timeout=timeout,
        )
        
        # Reproducir sonido si está habilitado
        if reproducir_sonido:
            try:
                import winsound
                # MB_ICONASTERISK = sonido de información de Windows
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                logger.debug("Sonido de notificación reproducido")
            except Exception as e:
                logger.debug(f"No se pudo reproducir sonido: {e}")
        
        logger.info("Notificación enviada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar notificación nativa: {e}", exc_info=True)
        return False


def comprobar_y_notificar_tareas(connect_db_func, usuario: str, mostrar_messagebox_func=None, icono: Optional[str] = None, habilitar_sonido: bool = True) -> bool:
    """
    Comprueba tareas vencidas/hoy y envía notificaciones.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        usuario: Nombre del usuario
        mostrar_messagebox_func: Función para mostrar messagebox como fallback
        icono: Ruta al icono de la app
        habilitar_sonido: Si debe reproducir sonido en las notificaciones
        
    Returns:
        True si había tareas para notificar
    """
    logger.info(f"Comprobando tareas vencidas/hoy para usuario: {usuario}")
    
    try:
        tareas_vencidas, tareas_hoy = obtener_tareas_vencidas_hoy(connect_db_func, usuario)
        
        if not tareas_vencidas and not tareas_hoy:
            logger.debug("No hay tareas vencidas ni para hoy")
            return False
        
        # Construir mensaje
        mensajes = []
        total = len(tareas_vencidas) + len(tareas_hoy)
        
        if tareas_vencidas:
            mensajes.append(f"⚠️ {len(tareas_vencidas)} tarea(s) VENCIDA(S):")
            for tarea in tareas_vencidas[:3]:  # Mostrar máximo 3
                prioridad_icon = "🔴" if tarea['prioridad'] == 'Alta' else "🟡" if tarea['prioridad'] == 'Normal' else "🟢"
                mensajes.append(f"  {prioridad_icon} {tarea['fecha_vencimiento']} - {tarea['titulo']} [{tarea['codigo_rma']}]")
            
            if len(tareas_vencidas) > 3:
                mensajes.append(f"  ... y {len(tareas_vencidas) - 3} más")
        
        if tareas_hoy:
            mensajes.append(f"\n📅 {len(tareas_hoy)} tarea(s) PARA HOY:")
            for tarea in tareas_hoy[:3]:  # Mostrar máximo 3
                prioridad_icon = "🔴" if tarea['prioridad'] == 'Alta' else "🟡" if tarea['prioridad'] == 'Normal' else "🟢"
                mensajes.append(f"  {prioridad_icon} {tarea['titulo']} [{tarea['codigo_rma']}]")
            
            if len(tareas_hoy) > 3:
                mensajes.append(f"  ... y {len(tareas_hoy) - 3} más")
        
        mensaje_completo = "\n".join(mensajes)
        
        # Intentar notificación nativa
        titulo = f"Tienes {total} tarea(s) pendiente(s)"
        exito_nativa = enviar_notificacion_nativa(
            titulo=titulo,
            mensaje=f"{len(tareas_vencidas)} vencidas, {len(tareas_hoy)} para hoy",
            icono=icono,
            timeout=10,
            reproducir_sonido=habilitar_sonido
        )
        
        # Si falla o no está disponible, usar messagebox
        if not exito_nativa and mostrar_messagebox_func:
            logger.info("Usando messagebox como fallback para notificación")
            mostrar_messagebox_func("Tareas Pendientes", mensaje_completo)
        
        return True
        
    except Exception as e:
        logger.error(f"Error al comprobar y notificar tareas: {e}", exc_info=True)
        return False


def marcar_tarea_completada(connect_db_func, tarea_id: int, usuario: str) -> bool:
    """
    Marca una tarea como completada.
    
    Args:
        connect_db_func: Función para conectar a la base de datos
        tarea_id: ID de la tarea
        usuario: Usuario que completa la tarea
        
    Returns:
        True si se actualizó correctamente
    """
    logger.info(f"Marcando tarea {tarea_id} como completada por {usuario}")
    
    try:
        # Manejar ambos casos: tupla (conn, cursor) o solo conn
        result = connect_db_func()
        if isinstance(result, tuple):
            conn, cursor = result
        else:
            conn = result
            cursor = conn.cursor() if conn else None
        
        # Verificar conexión válida
        if not conn or not cursor:
            logger.error("No se pudo conectar a la base de datos")
            return False
        
        cursor.execute("""
            UPDATE tareas 
            SET estado = 'Completado'
            WHERE id = ?
        """, (tarea_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tarea {tarea_id} marcada como completada")
        return True
        
    except Exception as e:
        logger.error(f"Error al marcar tarea como completada: {e}", exc_info=True)
        return False
