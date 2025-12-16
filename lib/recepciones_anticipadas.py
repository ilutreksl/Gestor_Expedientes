"""
Módulo para estadísticas de recepciones anticipadas.
Detecta clientes que reciben productos antes de autorizarlos.
"""

from datetime import datetime


def obtener_recepciones_anticipadas(conn):
    """
    Obtiene clientes con expedientes donde fecha_recepcion < fecha_autorizacion.
    
    Retorna lista de tuplas: (cliente, cantidad_expedientes, media_dias_adelanto)
    """
    cursor = conn.cursor()
    
    sql = """
    SELECT 
        cliente,
        COUNT(*) as cantidad,
        AVG(JULIANDAY(fecha_autorizacion) - JULIANDAY(fecha_recepcion)) as media_dias
    FROM rma_maestro
    WHERE 
        fecha_recepcion IS NOT NULL 
        AND fecha_recepcion != ''
        AND fecha_autorizacion IS NOT NULL
        AND fecha_autorizacion != ''
        AND fecha_recepcion <= fecha_autorizacion
    GROUP BY cliente
    ORDER BY cantidad DESC
    """
    
    cursor.execute(sql)
    resultados = cursor.fetchall()
    
    return resultados


def obtener_expedientes_anticipados_por_cliente(conn, cliente):
    """
    Obtiene los expedientes de un cliente específico con recepción anticipada.
    
    Retorna lista de tuplas: (id, codigo_rma, fecha_recepcion, fecha_autorizacion, dias_adelanto, estado)
    """
    cursor = conn.cursor()
    
    sql = """
    SELECT 
        id,
        codigo_rma,
        fecha_recepcion,
        fecha_autorizacion,
        JULIANDAY(fecha_autorizacion) - JULIANDAY(fecha_recepcion) as dias_adelanto,
        estado
    FROM rma_maestro
    WHERE 
        cliente = ?
        AND fecha_recepcion IS NOT NULL 
        AND fecha_recepcion != ''
        AND fecha_autorizacion IS NOT NULL
        AND fecha_autorizacion != ''
        AND fecha_recepcion <= fecha_autorizacion
    ORDER BY fecha_recepcion DESC
    """
    
    cursor.execute(sql, (cliente,))
    resultados = cursor.fetchall()
    
    return resultados


def buscar_clientes_anticipados(conn, termino_busqueda):
    """
    Busca clientes con recepciones anticipadas que coincidan con el término de búsqueda.
    
    Retorna lista de tuplas: (cliente, cantidad_expedientes, media_dias_adelanto)
    """
    cursor = conn.cursor()
    
    sql = """
    SELECT 
        cliente,
        COUNT(*) as cantidad,
        AVG(JULIANDAY(fecha_autorizacion) - JULIANDAY(fecha_recepcion)) as media_dias
    FROM rma_maestro
    WHERE 
        fecha_recepcion IS NOT NULL 
        AND fecha_recepcion != ''
        AND fecha_autorizacion IS NOT NULL
        AND fecha_autorizacion != ''
        AND fecha_recepcion <= fecha_autorizacion
        AND cliente LIKE ?
    GROUP BY cliente
    ORDER BY cantidad DESC
    """
    
    cursor.execute(sql, (f"%{termino_busqueda}%",))
    resultados = cursor.fetchall()
    
    return resultados


def ordenar_resultados(resultados, criterio='cantidad'):
    """
    Ordena los resultados según el criterio especificado.
    
    Args:
        resultados: Lista de tuplas (cliente, cantidad, media_dias)
        criterio: 'cliente', 'cantidad' o 'media_dias'
    
    Returns:
        Lista ordenada
    """
    if criterio == 'cliente':
        return sorted(resultados, key=lambda x: x[0].lower())
    elif criterio == 'cantidad':
        return sorted(resultados, key=lambda x: x[1], reverse=True)
    elif criterio == 'media_dias':
        return sorted(resultados, key=lambda x: x[2] if x[2] is not None else 0, reverse=True)
    else:
        return resultados
