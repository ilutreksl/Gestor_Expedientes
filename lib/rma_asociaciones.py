"""
Módulo para gestionar las asociaciones entre expedientes RMA.
Permite asociar múltiples expedientes entre sí y consultar estas relaciones.
"""

from lib.logger_config import get_logger

logger = get_logger()


def obtener_asociaciones(rma_id, conn):
    """
    Obtiene todos los expedientes asociados a un RMA específico.
    
    Args:
        rma_id: ID del RMA
        conn: Conexión a la base de datos
        
    Returns:
        list: Lista de diccionarios con información de los RMAs asociados
    """
    try:
        cursor = conn.cursor()
        
        # Obtener asociaciones (bidireccional: buscar donde sea rma_id o rma_asociado_id)
        cursor.execute("""
            SELECT DISTINCT
                CASE 
                    WHEN a.rma_id = ? THEN a.rma_asociado_id
                    ELSE a.rma_id
                END as rma_asociado_id,
                a.motivo,
                a.fecha_asociacion,
                a.usuario,
                a.id as asociacion_id,
                r.codigo_rma,
                r.cliente,
                r.estado
            FROM rma_asociaciones a
            INNER JOIN rma_maestro r ON (
                (a.rma_id = ? AND r.id = a.rma_asociado_id) OR
                (a.rma_asociado_id = ? AND r.id = a.rma_id)
            )
            WHERE a.rma_id = ? OR a.rma_asociado_id = ?
            ORDER BY a.fecha_asociacion DESC
        """, (rma_id, rma_id, rma_id, rma_id, rma_id))
        
        resultados = cursor.fetchall()
        
        asociaciones = []
        for row in resultados:
            asociaciones.append({
                'rma_id': row[0],
                'motivo': row[1] or '',
                'fecha_asociacion': row[2],
                'usuario': row[3] or 'Desconocido',
                'asociacion_id': row[4],
                'codigo_rma': row[5],
                'nombre_cliente': row[6],
                'estado_expediente': row[7]
            })
        
        logger.info(f"Se obtuvieron {len(asociaciones)} asociaciones para RMA ID {rma_id}")
        return asociaciones
        
    except Exception as e:
        logger.error(f"Error al obtener asociaciones para RMA ID {rma_id}: {e}")
        return []


def asociar_expedientes(rma_id, rma_asociado_id, motivo, usuario, conn):
    """
    Asocia dos expedientes RMA.
    Crea una asociación bidireccional automáticamente.
    
    Args:
        rma_id: ID del primer RMA
        rma_asociado_id: ID del segundo RMA
        motivo: Razón de la asociación
        usuario: Usuario que realiza la asociación
        conn: Conexión a la base de datos
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validaciones
        if rma_id == rma_asociado_id:
            logger.warning(f"Intento de asociar un RMA consigo mismo: {rma_id}")
            return False, "No se puede asociar un expediente consigo mismo"
        
        # Verificar que ambos RMAs existen
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM rma_maestro WHERE id = ?", (rma_id,))
        if not cursor.fetchone():
            logger.warning(f"RMA ID {rma_id} no encontrado")
            return False, f"El expediente con ID {rma_id} no existe"
        
        cursor.execute("SELECT id FROM rma_maestro WHERE id = ?", (rma_asociado_id,))
        if not cursor.fetchone():
            logger.warning(f"RMA ID {rma_asociado_id} no encontrado")
            return False, f"El expediente con ID {rma_asociado_id} no existe"
        
        # Verificar si ya existe la asociación
        cursor.execute("""
            SELECT id FROM rma_asociaciones 
            WHERE (rma_id = ? AND rma_asociado_id = ?) 
               OR (rma_id = ? AND rma_asociado_id = ?)
        """, (rma_id, rma_asociado_id, rma_asociado_id, rma_id))
        
        if cursor.fetchone():
            logger.warning(f"Intento de crear asociación duplicada: RMA {rma_id} <-> {rma_asociado_id}")
            return False, "Estos expedientes ya están asociados"
        
        # Crear la asociación (solo en una dirección, la consulta es bidireccional)
        cursor.execute("""
            INSERT INTO rma_asociaciones (rma_id, rma_asociado_id, motivo, usuario)
            VALUES (?, ?, ?, ?)
        """, (rma_id, rma_asociado_id, motivo or '', usuario))
        
        conn.commit()
        
        logger.info(f"Asociación creada exitosamente: RMA {rma_id} <-> {rma_asociado_id} por {usuario}")
        return True, "Expedientes asociados correctamente"
        
    except Exception as e:
        logger.error(f"Error al asociar expedientes {rma_id} y {rma_asociado_id}: {e}")
        return False, f"Error al crear la asociación: {str(e)}"


def desasociar_expedientes(rma_id, rma_asociado_id, conn):
    """
    Elimina la asociación entre dos expedientes.
    
    Args:
        rma_id: ID del primer RMA
        rma_asociado_id: ID del segundo RMA
        conn: Conexión a la base de datos
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        cursor = conn.cursor()
        
        # Eliminar la asociación (en cualquier dirección)
        cursor.execute("""
            DELETE FROM rma_asociaciones 
            WHERE (rma_id = ? AND rma_asociado_id = ?) 
               OR (rma_id = ? AND rma_asociado_id = ?)
        """, (rma_id, rma_asociado_id, rma_asociado_id, rma_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"No se encontró asociación entre RMA {rma_id} y {rma_asociado_id}")
            return False, "No existe asociación entre estos expedientes"
        
        conn.commit()
        
        logger.info(f"Asociación eliminada: RMA {rma_id} <-> {rma_asociado_id}")
        return True, "Asociación eliminada correctamente"
        
    except Exception as e:
        logger.error(f"Error al desasociar expedientes {rma_id} y {rma_asociado_id}: {e}")
        return False, f"Error al eliminar la asociación: {str(e)}"


def buscar_rmas_para_asociar(termino_busqueda, rma_id_excluir, conn):
    """
    Busca expedientes RMA por código o cliente para asociar.
    Excluye el RMA actual y los ya asociados.
    
    Args:
        termino_busqueda: Código RMA o nombre de cliente
        rma_id_excluir: ID del RMA actual (para excluirlo de los resultados)
        conn: Conexión a la base de datos
        
    Returns:
        list: Lista de diccionarios con RMAs encontrados
    """
    try:
        cursor = conn.cursor()
        
        # Obtener IDs de RMAs ya asociados
        cursor.execute("""
            SELECT DISTINCT
                CASE 
                    WHEN rma_id = ? THEN rma_asociado_id
                    ELSE rma_id
                END as rma_asociado_id
            FROM rma_asociaciones
            WHERE rma_id = ? OR rma_asociado_id = ?
        """, (rma_id_excluir, rma_id_excluir, rma_id_excluir))
        
        ids_asociados = [row[0] for row in cursor.fetchall()]
        ids_excluir = [rma_id_excluir] + ids_asociados
        
        # Buscar RMAs
        placeholders = ','.join(['?' for _ in ids_excluir])
        
        cursor.execute(f"""
            SELECT id, codigo_rma, cliente, estado, fecha_emision
            FROM rma_maestro
            WHERE id NOT IN ({placeholders})
              AND (codigo_rma LIKE ? OR cliente LIKE ?)
            ORDER BY fecha_emision DESC
            LIMIT 50
        """, ids_excluir + [f'%{termino_busqueda}%', f'%{termino_busqueda}%'])
        
        resultados = cursor.fetchall()
        
        rmas = []
        for row in resultados:
            rmas.append({
                'id': row[0],
                'codigo_rma': row[1],
                'nombre_cliente': row[2],  # Mantener este nombre para compatibilidad con UI
                'estado_expediente': row[3],  # Mantener este nombre para compatibilidad con UI
                'fecha_creacion': row[4]
            })
        
        logger.info(f"Búsqueda de RMAs para asociar: encontrados {len(rmas)} resultados")
        return rmas
        
    except Exception as e:
        logger.error(f"Error al buscar RMAs para asociar: {e}")
        return []


def contar_asociaciones(rma_id, conn):
    """
    Cuenta cuántos expedientes están asociados a un RMA.
    
    Args:
        rma_id: ID del RMA
        conn: Conexión a la base de datos
        
    Returns:
        int: Número de asociaciones
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT 
                CASE 
                    WHEN rma_id = ? THEN rma_asociado_id
                    ELSE rma_id
                END
            )
            FROM rma_asociaciones
            WHERE rma_id = ? OR rma_asociado_id = ?
        """, (rma_id, rma_id, rma_id))
        
        count = cursor.fetchone()[0]
        return count
        
    except Exception as e:
        logger.error(f"Error al contar asociaciones para RMA ID {rma_id}: {e}")
        return 0
