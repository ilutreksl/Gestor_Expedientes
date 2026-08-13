"""
Módulo para gestionar el texto de ayuda de la ventana "Añadir Trazabilidad".
El texto se guarda en la tabla config_trazabilidad de Turso (fila única, id=1)
y es editable solo por el usuario admin desde el panel de administración.
"""

from lib.logger_config import get_logger

logger = get_logger()

# NOTA: connect_db se importa de forma diferida (dentro de cada método) en vez
# de al nivel de módulo, porque lib/app_core.py importa esta clase — un import
# a nivel de módulo aquí crearía un ciclo de importación circular con app_core.

TEXTO_AYUDA_DEFECTO = (
    "Adjunta el correo, foto o documento relacionado con esta incidencia y "
    "añade un comentario si lo necesitas. El sistema lo clasificará "
    "automáticamente: los correos (.eml/.msg) se asocian en la pestaña "
    "Asociados y el resto de archivos en Adjuntos."
)


class TrazabilidadManager:
    """Clase para gestionar la configuración de la ventana de Trazabilidad."""

    def __init__(self):
        self._asegurar_fila_existe()

    def _asegurar_fila_existe(self):
        """Crea la fila de configuración en Turso con el texto por defecto si no existe."""
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM config_trazabilidad WHERE id = 1")
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO config_trazabilidad (id, texto_ayuda) VALUES (1, ?)",
                    (TEXTO_AYUDA_DEFECTO,)
                )
                conn.commit()
                logger.info("Fila de configuración de trazabilidad creada en Turso con el texto por defecto")
            conn.close()
        except Exception as e:
            logger.error(f"Error al asegurar la fila de configuración de trazabilidad: {e}")

    def cargar_texto_ayuda(self):
        """
        Carga el texto de ayuda desde Turso.

        Returns:
            str: Texto de ayuda configurado (o el texto por defecto si algo falla).
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT texto_ayuda FROM config_trazabilidad WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                return TEXTO_AYUDA_DEFECTO
            return row[0]
        except Exception as e:
            logger.error(f"Error al cargar el texto de ayuda de trazabilidad: {e}")
            return TEXTO_AYUDA_DEFECTO

    def guardar_texto_ayuda(self, texto):
        """
        Guarda el texto de ayuda en Turso.

        Args:
            texto (str): Nuevo texto de ayuda.

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE config_trazabilidad SET texto_ayuda = ? WHERE id = 1",
                (texto,)
            )
            conn.commit()
            conn.close()
            logger.info("Texto de ayuda de trazabilidad actualizado")
            return True, "Texto de ayuda guardado correctamente."
        except Exception as e:
            logger.error(f"Error al guardar el texto de ayuda de trazabilidad: {e}")
            return False, f"Error al guardar: {e}"
