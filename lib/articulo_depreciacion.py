"""
Módulo para gestionar la depreciación de artículos en RMAs.
Incluye funciones para validar porcentajes y calcular valores depreciados.
"""

from lib.logger_config import get_logger

logger = get_logger()


def validar_porcentaje_depreciacion(porcentaje_str):
    """
    Valida que el porcentaje de depreciación sea un número válido.
    
    Args:
        porcentaje_str: String con el porcentaje a validar
        
    Returns:
        tuple: (es_valido: bool, valor_float: float, mensaje_error: str)
    """
    try:
        if not porcentaje_str or porcentaje_str.strip() == "":
            return True, 0.0, ""
        
        # Permitir coma decimal
        valor_str = porcentaje_str.replace(',', '.')
        valor = float(valor_str)
        
        if valor < 0:
            return False, 0.0, "El porcentaje no puede ser negativo"
        
        if valor > 100:
            return False, 0.0, "El porcentaje no puede ser mayor a 100%"
        
        return True, valor, ""
        
    except ValueError:
        return False, 0.0, "El porcentaje debe ser un número válido"


def calcular_valor_depreciado(precio_original, porcentaje_depreciacion):
    """
    Calcula el valor de un artículo después de aplicar la depreciación.
    
    Args:
        precio_original: Precio original del artículo
        porcentaje_depreciacion: Porcentaje de depreciación a aplicar (0-100)
        
    Returns:
        float: Valor depreciado del artículo
    """
    try:
        precio = float(precio_original)
        porcentaje = float(porcentaje_depreciacion)
        
        if porcentaje <= 0:
            return precio
        
        if porcentaje >= 100:
            return 0.0
        
        valor_depreciado = precio * (1 - porcentaje / 100)
        logger.info(f"Valor depreciado calculado: {precio}€ - {porcentaje}% = {valor_depreciado}€")
        
        return valor_depreciado
        
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculando valor depreciado: {e}")
        return float(precio_original) if precio_original else 0.0


def aplicar_depreciacion_articulo(articulo_data, depreciacion, porcentaje):
    """
    Aplica la depreciación a un artículo y retorna los datos actualizados.
    
    Args:
        articulo_data: Diccionario con los datos del artículo
        depreciacion: Boolean indicando si tiene depreciación
        porcentaje: Porcentaje de depreciación a aplicar
        
    Returns:
        dict: Datos del artículo actualizados con depreciación
    """
    articulo = articulo_data.copy()
    articulo['depreciacion'] = 1 if depreciacion else 0
    articulo['porcentaje_depreciacion'] = float(porcentaje) if depreciacion else 0.0
    
    logger.info(
        f"Depreciación aplicada a artículo {articulo.get('referencia_articulo', 'N/A')}: "
        f"activa={depreciacion}, porcentaje={porcentaje}%"
    )
    
    return articulo


def obtener_estadisticas_depreciacion(conn, rma_id=None):
    """
    Obtiene estadísticas sobre artículos con depreciación.
    
    Args:
        conn: Conexión a la base de datos
        rma_id: ID del RMA (opcional, si se quiere filtrar por RMA específico)
        
    Returns:
        dict: Estadísticas de depreciación
    """
    try:
        cursor = conn.cursor()
        
        if rma_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_articulos,
                    SUM(CASE WHEN depreciacion = 1 THEN 1 ELSE 0 END) as con_depreciacion,
                    AVG(CASE WHEN depreciacion = 1 THEN porcentaje_depreciacion ELSE 0 END) as porcentaje_promedio
                FROM rma_detalles
                WHERE rma_id = ?
            """, (rma_id,))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_articulos,
                    SUM(CASE WHEN depreciacion = 1 THEN 1 ELSE 0 END) as con_depreciacion,
                    AVG(CASE WHEN depreciacion = 1 THEN porcentaje_depreciacion ELSE 0 END) as porcentaje_promedio
                FROM rma_detalles
            """)
        
        resultado = cursor.fetchone()
        
        if resultado:
            stats = {
                'total_articulos': resultado[0] or 0,
                'con_depreciacion': resultado[1] or 0,
                'porcentaje_promedio': resultado[2] or 0.0
            }
            logger.info(f"Estadísticas de depreciación obtenidas: {stats}")
            return stats
        
        return {'total_articulos': 0, 'con_depreciacion': 0, 'porcentaje_promedio': 0.0}
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de depreciación: {e}")
        return {'total_articulos': 0, 'con_depreciacion': 0, 'porcentaje_promedio': 0.0}
