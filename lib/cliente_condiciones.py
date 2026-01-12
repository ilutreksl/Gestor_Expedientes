"""
Módulo para gestionar las condiciones comerciales de los clientes.
Incluye funciones para cargar y guardar descuentos y campos de reserva.
"""

from lib.logger_config import get_logger

logger = get_logger()


def cargar_condiciones_cliente(cliente_id, conn):
    """
    Carga las condiciones comerciales de un cliente.
    
    Args:
        cliente_id: ID del cliente
        conn: Conexión a la base de datos
        
    Returns:
        dict con las claves: descuento, campo_reserva_1, campo_reserva_2
        Si no existe el cliente, retorna valores por defecto (0.0, "", "")
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT descuento, campo_reserva_1, campo_reserva_2
            FROM clientes
            WHERE cliente_id = ?
        """, (cliente_id,))
        
        resultado = cursor.fetchone()
        
        if resultado:
            logger.info(f"Condiciones cargadas para cliente ID {cliente_id}")
            return {
                'descuento': resultado[0] if resultado[0] is not None else 0.0,
                'campo_reserva_1': resultado[1] if resultado[1] is not None else "",
                'campo_reserva_2': resultado[2] if resultado[2] is not None else ""
            }
        else:
            logger.warning(f"Cliente ID {cliente_id} no encontrado, retornando valores por defecto")
            return {
                'descuento': 0.0,
                'campo_reserva_1': "",
                'campo_reserva_2': ""
            }
            
    except Exception as e:
        logger.error(f"Error al cargar condiciones del cliente {cliente_id}: {e}")
        # Retornar valores por defecto en caso de error
        return {
            'descuento': 0.0,
            'campo_reserva_1': "",
            'campo_reserva_2': ""
        }


def guardar_condiciones_cliente(cliente_id, descuento, campo_reserva_1, campo_reserva_2, conn):
    """
    Guarda las condiciones comerciales de un cliente.
    
    Args:
        cliente_id: ID del cliente
        descuento: Descuento aplicable (número decimal, ej: 10.5 para 10.5%)
        campo_reserva_1: Texto del primer campo de reserva
        campo_reserva_2: Texto del segundo campo de reserva
        conn: Conexión a la base de datos
        
    Returns:
        bool: True si se guardó correctamente, False en caso de error
    """
    try:
        cursor = conn.cursor()
        
        # Validar descuento
        try:
            descuento_float = float(descuento) if descuento else 0.0
        except (ValueError, TypeError):
            logger.error(f"Descuento inválido: {descuento}. Usando 0.0")
            descuento_float = 0.0
        
        # Asegurar que los campos de reserva sean strings
        campo_reserva_1 = str(campo_reserva_1) if campo_reserva_1 else ""
        campo_reserva_2 = str(campo_reserva_2) if campo_reserva_2 else ""
        
        cursor.execute("""
            UPDATE clientes
            SET descuento = ?,
                campo_reserva_1 = ?,
                campo_reserva_2 = ?
            WHERE cliente_id = ?
        """, (descuento_float, campo_reserva_1, campo_reserva_2, cliente_id))
        
        conn.commit()
        
        logger.info(
            f"Condiciones guardadas para cliente ID {cliente_id}: "
            f"descuento={descuento_float}%, reserva_1='{campo_reserva_1}', reserva_2='{campo_reserva_2}'"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error al guardar condiciones del cliente {cliente_id}: {e}")
        return False


def validar_descuento(descuento_str):
    """
    Valida que el descuento sea un número válido.
    
    Args:
        descuento_str: String con el descuento a validar
        
    Returns:
        tuple: (es_valido: bool, valor_float: float, mensaje_error: str)
    """
    try:
        if not descuento_str or descuento_str.strip() == "":
            return True, 0.0, ""
        
        valor = float(descuento_str)
        
        if valor < 0:
            return False, 0.0, "El descuento no puede ser negativo"
        
        if valor > 100:
            return False, 0.0, "El descuento no puede ser mayor a 100%"
        
        return True, valor, ""
        
    except ValueError:
        return False, 0.0, "El descuento debe ser un número válido"
