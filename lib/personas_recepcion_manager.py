"""
Módulo para gestionar las personas de recepción del sistema.
Permite cargar, guardar y gestionar las personas de recepción, almacenadas en
la tabla config_recepcion_qr de Turso (compartida con el Worker de recepción
por QR, para que ambos lados vean siempre la misma lista).
"""

import json
from lib.logger_config import get_logger

logger = get_logger()

# NOTA: connect_db se importa de forma diferida (dentro de cada método) en vez
# de al nivel de módulo, porque lib/app_core.py importa esta clase — un import
# a nivel de módulo aquí crearía un ciclo de importación circular con app_core.

_MENSAJE_INCIDENCIAS_DEFECTO = (
    "El nombre introducido no coincide con el personal autorizado. "
    "Por favor, contacta con el Departamento de Incidencias."
)


class PersonasRecepcionManager:
    """Clase para gestionar las personas de recepción del sistema"""

    def __init__(self, root_path=None):
        """
        Inicializa el gestor de personas de recepción.

        Args:
            root_path: Ya no se usa (las personas viven en Turso, no en un
                archivo local). Se mantiene el parámetro por compatibilidad
                con el código que instancia esta clase.
        """
        self._asegurar_fila_existe()
        logger.info("PersonasRecepcionManager inicializado")

    def _asegurar_fila_existe(self):
        """Crea la fila de configuración en Turso con valores por defecto si no existe"""
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM config_recepcion_qr WHERE id = 1")
            if cursor.fetchone() is None:
                personas_default = [
                    "RAQUEL", "SILVIA", "CARLOS", "IVAN",
                    "ANDRES", "JOSE ANTONIO", "JUANVI", "JOSE LUIS"
                ]
                cursor.execute(
                    "INSERT INTO config_recepcion_qr "
                    "(id, personas_recepcion, mensaje_incidencias, pin_max_intentos, pin_caducidad_minutos) "
                    "VALUES (1, ?, ?, 5, 15)",
                    (json.dumps(personas_default, ensure_ascii=False), _MENSAJE_INCIDENCIAS_DEFECTO)
                )
                conn.commit()
                logger.info("Fila de configuración de recepción creada en Turso con valores por defecto")
            conn.close()
        except Exception as e:
            logger.error(f"Error al asegurar la fila de configuración de recepción: {e}")

    def cargar_personas(self):
        """
        Carga las personas de recepción desde Turso.

        Returns:
            list: Lista de personas de recepción
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT personas_recepcion FROM config_recepcion_qr WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                return []
            personas = json.loads(row[0])
            logger.debug(f"Cargadas {len(personas)} personas de recepción")
            return personas
        except Exception as e:
            logger.error(f"Error al cargar personas de recepción: {e}")
            return []

    def guardar_personas(self, personas):
        """
        Guarda las personas de recepción en Turso.

        Args:
            personas (list): Lista de personas a guardar

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE config_recepcion_qr SET personas_recepcion = ? WHERE id = 1",
                (json.dumps(personas, ensure_ascii=False),)
            )
            conn.commit()
            conn.close()
            logger.info(f"Guardadas {len(personas)} personas de recepción")
            return True, "Personas de recepción guardadas correctamente"
        except Exception as e:
            logger.error(f"Error al guardar personas de recepción: {e}")
            return False, f"Error al guardar personas de recepción: {e}"

    def añadir_persona(self, nueva_persona):
        """
        Añade una nueva persona de recepción a la lista

        Args:
            nueva_persona (str): Persona a añadir

        Returns:
            tuple: (success: bool, message: str)
        """
        if not nueva_persona or not nueva_persona.strip():
            logger.warning("Intento de añadir persona de recepción vacía")
            return False, "El nombre no puede estar vacío"

        personas = self.cargar_personas()

        # Normalizar a mayúsculas para evitar duplicados
        nueva_persona_upper = nueva_persona.strip().upper()

        if nueva_persona_upper in personas:
            logger.warning(f"Intento de añadir persona de recepción duplicada: {nueva_persona_upper}")
            return False, "Esta persona ya existe"

        personas.append(nueva_persona_upper)
        success, message = self.guardar_personas(personas)

        if success:
            logger.info(f"Persona de recepción añadida: {nueva_persona_upper}")

        return success, message

    def eliminar_persona(self, persona):
        """
        Elimina una persona de recepción de la lista

        Args:
            persona (str): Persona a eliminar

        Returns:
            tuple: (success: bool, message: str)
        """
        personas = self.cargar_personas()

        if persona not in personas:
            logger.warning(f"Intento de eliminar persona de recepción inexistente: {persona}")
            return False, "La persona no existe en la lista"

        personas.remove(persona)
        success, message = self.guardar_personas(personas)

        if success:
            logger.info(f"Persona de recepción eliminada: {persona}")

        return success, message

    def editar_persona(self, persona_antigua, persona_nueva):
        """
        Edita el nombre de una persona de recepción

        Args:
            persona_antigua (str): Nombre actual
            persona_nueva (str): Nombre nuevo

        Returns:
            tuple: (success: bool, message: str)
        """
        if not persona_nueva or not persona_nueva.strip():
            logger.warning("Intento de editar persona de recepción con nombre vacío")
            return False, "El nombre no puede estar vacío"

        personas = self.cargar_personas()

        if persona_antigua not in personas:
            logger.warning(f"Intento de editar persona de recepción inexistente: {persona_antigua}")
            return False, "La persona original no existe"

        # Normalizar a mayúsculas
        persona_nueva_upper = persona_nueva.strip().upper()

        # Verificar si el nuevo nombre ya existe (y no es el mismo)
        if persona_nueva_upper in personas and persona_nueva_upper != persona_antigua:
            logger.warning(f"Intento de editar a persona de recepción duplicada: {persona_nueva_upper}")
            return False, "Ya existe una persona con ese nombre"

        # Reemplazar
        index = personas.index(persona_antigua)
        personas[index] = persona_nueva_upper

        success, message = self.guardar_personas(personas)

        if success:
            logger.info(f"Persona de recepción editada: {persona_antigua} → {persona_nueva_upper}")

        return success, message
