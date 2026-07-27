"""
Módulo para gestionar los correos importados (.eml/.msg) asociados a un expediente RMA.

El correo original (archivo completo) se sube al mismo almacenamiento de adjuntos
(Backblaze B2 o local) que usa el resto del expediente; aquí solo se guardan los
metadatos extraídos (asunto, remitente, fecha, cuerpo) y la referencia al archivo.
"""

from lib.logger_config import get_logger

logger = get_logger()


def obtener_correos_asociados(rma_id, conn):
    """
    Obtiene todos los correos importados asociados a un RMA, más recientes primero.

    Returns:
        list: lista de diccionarios con los datos de cada correo.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, asunto, remitente, fecha_correo, cuerpo,
                   nombre_archivo_original, ruta_relativa_adjunto, tipo_almacenamiento,
                   fecha_importacion, usuario_importacion
            FROM rma_correos_asociados
            WHERE rma_id = ?
            ORDER BY fecha_importacion DESC
        """, (rma_id,))

        resultados = cursor.fetchall()

        correos = []
        for row in resultados:
            correos.append({
                'id': row[0],
                'asunto': row[1] or '(sin asunto)',
                'remitente': row[2] or '',
                'fecha_correo': row[3] or '',
                'cuerpo': row[4] or '',
                'nombre_archivo_original': row[5] or '',
                'ruta_relativa_adjunto': row[6] or '',
                'tipo_almacenamiento': row[7] or 'local',
                'fecha_importacion': row[8] or '',
                'usuario_importacion': row[9] or 'Desconocido',
            })

        return correos

    except Exception as e:
        logger.error(f"Error al obtener correos asociados para RMA ID {rma_id}: {e}")
        return []


def insertar_correo_asociado(rma_id, datos, conn):
    """
    Inserta un correo importado asociado a un RMA.

    Args:
        rma_id: ID del RMA
        datos: dict con claves asunto, remitente, fecha_correo, cuerpo,
               nombre_archivo_original, ruta_relativa_adjunto, tipo_almacenamiento,
               fecha_importacion, usuario_importacion
        conn: Conexión a la base de datos

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rma_correos_asociados
                (rma_id, asunto, remitente, fecha_correo, cuerpo,
                 nombre_archivo_original, ruta_relativa_adjunto, tipo_almacenamiento,
                 fecha_importacion, usuario_importacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rma_id,
            datos.get('asunto', ''),
            datos.get('remitente', ''),
            datos.get('fecha_correo', ''),
            datos.get('cuerpo', ''),
            datos.get('nombre_archivo_original', ''),
            datos.get('ruta_relativa_adjunto', ''),
            datos.get('tipo_almacenamiento', 'local'),
            datos.get('fecha_importacion', ''),
            datos.get('usuario_importacion', ''),
        ))
        conn.commit()

        logger.info(f"Correo asociado importado para RMA ID {rma_id}: '{datos.get('asunto', '')}'")
        return True, "Correo importado y asociado correctamente"

    except Exception as e:
        logger.error(f"Error al insertar correo asociado para RMA ID {rma_id}: {e}")
        return False, f"Error al guardar el correo: {str(e)}"


def eliminar_correo_asociado(correo_id, conn):
    """
    Elimina un correo asociado (solo el registro en BD; el archivo original,
    si existía, se elimina aparte desde el llamador junto al resto de adjuntos).

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rma_correos_asociados WHERE id = ?", (correo_id,))

        if cursor.rowcount == 0:
            return False, "No se encontró el correo a eliminar"

        conn.commit()
        logger.info(f"Correo asociado eliminado: ID {correo_id}")
        return True, "Correo eliminado correctamente"

    except Exception as e:
        logger.error(f"Error al eliminar correo asociado ID {correo_id}: {e}")
        return False, f"Error al eliminar el correo: {str(e)}"
