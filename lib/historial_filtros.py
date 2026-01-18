"""
Módulo para gestionar filtros y búsqueda en el historial de expedientes.
Proporciona funcionalidades para filtrar por usuario, fecha y tipo de cambio.
"""

import logging
from datetime import datetime

logger = logging.getLogger("GestorExpedientes")


def obtener_historial_filtrado(rma_id, texto_busqueda=None, usuario_filtro=None, 
                                fecha_desde=None, fecha_hasta=None, solo_comentarios_manuales=False,
                                connect_db_func=None):
    """
    Obtiene el historial de un expediente aplicando filtros.
    
    Args:
        rma_id: ID del expediente
        texto_busqueda: Texto a buscar en la descripción
        usuario_filtro: Filtrar por usuario específico
        fecha_desde: Fecha desde (formato DD/MM/YYYY)
        fecha_hasta: Fecha hasta (formato DD/MM/YYYY)
        solo_comentarios_manuales: Si True, solo muestra comentarios manuales
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        list: Lista de tuplas (fecha_cambio, usuario, descripcion_cambio)
    """
    try:
        conn, cursor = connect_db_func()
        if not conn:
            logger.error(f"No se pudo conectar a la BD para obtener historial de RMA {rma_id}")
            return []
        
        # Construir query SQL con filtros
        query = """
            SELECT fecha_cambio, usuario, descripcion_cambio 
            FROM rma_historial 
            WHERE rma_id = ?
        """
        params = [rma_id]
        
        # Filtro de búsqueda de texto
        if texto_busqueda and texto_busqueda.strip():
            query += " AND LOWER(descripcion_cambio) LIKE ?"
            params.append(f"%{texto_busqueda.lower()}%")
        
        # Filtro de usuario
        if usuario_filtro and usuario_filtro != "Todos":
            query += " AND usuario = ?"
            params.append(usuario_filtro)
        
        # Filtro de fechas
        if fecha_desde:
            try:
                # Convertir DD/MM/YYYY a formato comparable
                fecha_desde_obj = datetime.strptime(fecha_desde, '%d/%m/%Y')
                fecha_desde_sql = fecha_desde_obj.strftime('%Y-%m-%d')
                query += " AND DATE(fecha_cambio) >= ?"
                params.append(fecha_desde_sql)
            except ValueError:
                logger.warning(f"Formato de fecha inválido para fecha_desde: {fecha_desde}")
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%d/%m/%Y')
                fecha_hasta_sql = fecha_hasta_obj.strftime('%Y-%m-%d')
                query += " AND DATE(fecha_cambio) <= ?"
                params.append(fecha_hasta_sql)
            except ValueError:
                logger.warning(f"Formato de fecha inválido para fecha_hasta: {fecha_hasta}")
        
        # Filtro de solo comentarios manuales
        if solo_comentarios_manuales:
            # Los comentarios manuales empiezan con "COMENTARIO MANUAL:"
            query += " AND descripcion_cambio LIKE 'COMENTARIO MANUAL:%'"
        
        query += " ORDER BY id DESC"
        
        cursor.execute(query, tuple(params))
        registros = cursor.fetchall()
        conn.close()
        
        logger.debug(f"Historial filtrado de RMA {rma_id}: {len(registros)} registros")
        return registros
        
    except Exception as e:
        logger.error(f"Error obteniendo historial filtrado de RMA {rma_id}: {e}", exc_info=True)
        return []


def obtener_usuarios_historial(rma_id, connect_db_func=None):
    """
    Obtiene la lista de usuarios únicos que han modificado un expediente.
    
    Args:
        rma_id: ID del expediente
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        list: Lista de nombres de usuario
    """
    try:
        conn, cursor = connect_db_func()
        if not conn:
            logger.error(f"No se pudo conectar a la BD para obtener usuarios de RMA {rma_id}")
            return []
        
        cursor.execute("""
            SELECT DISTINCT usuario 
            FROM rma_historial 
            WHERE rma_id = ? AND usuario IS NOT NULL
            ORDER BY usuario
        """, (rma_id,))
        
        usuarios = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        
        logger.debug(f"Usuarios en historial de RMA {rma_id}: {len(usuarios)}")
        return usuarios
        
    except Exception as e:
        logger.error(f"Error obteniendo usuarios de historial de RMA {rma_id}: {e}", exc_info=True)
        return []


def validar_formato_fecha(fecha_str):
    """
    Valida que una fecha tenga el formato DD/MM/YYYY.
    
    Args:
        fecha_str: String con la fecha
        
    Returns:
        tuple: (bool, str) - (válido, mensaje de error si aplica)
    """
    if not fecha_str or not fecha_str.strip():
        return True, ""  # Fecha vacía es válida (sin filtro)
    
    try:
        datetime.strptime(fecha_str.strip(), '%d/%m/%Y')
        return True, ""
    except ValueError:
        return False, "Formato debe ser DD/MM/YYYY"


def contar_comentarios_manuales(rma_id, connect_db_func=None):
    """
    Cuenta cuántos comentarios manuales hay en el historial.
    
    Args:
        rma_id: ID del expediente
        connect_db_func: Función para conectar a la base de datos
        
    Returns:
        int: Número de comentarios manuales
    """
    try:
        conn, cursor = connect_db_func()
        if not conn:
            return 0
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM rma_historial 
            WHERE rma_id = ? 
              AND descripcion_cambio LIKE 'COMENTARIO MANUAL:%'
        """, (rma_id,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        return int(resultado[0]) if resultado else 0
        
    except Exception as e:
        logger.error(f"Error contando comentarios manuales de RMA {rma_id}: {e}", exc_info=True)
        return 0
