"""
Módulo para gestionar los estados de artículos, almacenados en la
columna estados_articulo de config_recepcion_qr en Turso (compartida
con el Worker de recepción por QR, para que el móvil pueda consultarla
al editar un artículo).
"""

import json

# NOTA: connect_db se importa de forma diferida (dentro de cada método) en vez
# de al nivel de módulo, porque lib/app_core.py importa esta clase — un import
# a nivel de módulo aquí crearía un ciclo de importación circular con app_core.

_ESTADOS_DEFECTO = [
    "",
    "EN PERFECTO ESTADO ; ABONAR",
    "FUNCIONA PERFECTAMENTE ; ABONAR",
    "SOBRANTE DE OBRA ; ABONAR",
    "NO FUNCIONA, ABONAR",
    "FUNCIONA PERFECTAMENTE ; NO ABONAR",
    "NO FUNCIONA ; NO ABONAR",
    "REPOSICION FALLO PRODUCTO",
    "REPOSICION ; ABONAR",
    "MERCANCIA ENVIADA POR ERROR",
    "MALA MANIPULACION ; NO ABONAR",
    "EN PERFECTO ESTADO ; ABONAR 10% DEPRECIACION",
    "FALLO SOLDADURA ; ABONAR",
    "FALLO SOLDADURA ; NO ABONAR",
    "FALLO MODULO ; ABONAR",
    "MAL MANIPULACION ; ABONAR",
    "DANA",
    "CAMBIO DE PRODUCTO",
]


class EstadosArticuloManager:
    """Clase para gestionar los estados de artículos"""

    def __init__(self, root_path=None):
        """
        Inicializa el gestor de estados

        Args:
            root_path: Ya no se usa (los estados viven en Turso, no en un
                archivo local). Se mantiene el parámetro por compatibilidad
                con el código que instancia esta clase.
        """
        self._asegurar_fila_existe()

    def _asegurar_fila_existe(self):
        """Si la fila de configuración no tiene aún estados guardados, la siembra con los valores por defecto"""
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT estados_articulo FROM config_recepcion_qr WHERE id = 1")
            row = cursor.fetchone()
            if row is not None and not row[0]:
                cursor.execute(
                    "UPDATE config_recepcion_qr SET estados_articulo = ? WHERE id = 1",
                    (json.dumps(_ESTADOS_DEFECTO, ensure_ascii=False),)
                )
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error al asegurar los estados de artículo por defecto: {e}")

    def cargar_estados(self):
        """
        Carga los estados desde Turso

        Returns:
            list: Lista de estados
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT estados_articulo FROM config_recepcion_qr WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                return [""]
            return json.loads(row[0])
        except Exception as e:
            print(f"Error al cargar estados: {e}")
            return [""]  # Estado vacío por defecto

    def guardar_estados(self, estados):
        """
        Guarda los estados en Turso

        Args:
            estados (list): Lista de estados a guardar

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from lib.app_core import connect_db
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE config_recepcion_qr SET estados_articulo = ? WHERE id = 1",
                (json.dumps(estados, ensure_ascii=False),)
            )
            conn.commit()
            conn.close()
            return True, "Estados guardados correctamente"
        except Exception as e:
            return False, f"Error al guardar estados: {e}"

    def añadir_estado(self, nuevo_estado):
        """
        Añade un nuevo estado a la lista

        Args:
            nuevo_estado (str): Estado a añadir

        Returns:
            tuple: (success: bool, message: str)
        """
        if not nuevo_estado or not nuevo_estado.strip():
            return False, "El estado no puede estar vacío"

        estados = self.cargar_estados()

        if nuevo_estado in estados:
            return False, "Este estado ya existe"

        estados.append(nuevo_estado)
        return self.guardar_estados(estados)

    def eliminar_estado(self, estado):
        """
        Elimina un estado de la lista

        Args:
            estado (str): Estado a eliminar

        Returns:
            tuple: (success: bool, message: str)
        """
        estados = self.cargar_estados()

        if estado not in estados:
            return False, "El estado no existe"

        estados.remove(estado)
        return self.guardar_estados(estados)

    def editar_estado(self, estado_antiguo, estado_nuevo):
        """
        Edita un estado existente

        Args:
            estado_antiguo (str): Estado a modificar
            estado_nuevo (str): Nuevo valor del estado

        Returns:
            tuple: (success: bool, message: str)
        """
        if not estado_nuevo or not estado_nuevo.strip():
            return False, "El nuevo estado no puede estar vacío"

        estados = self.cargar_estados()

        if estado_antiguo not in estados:
            return False, "El estado original no existe"

        if estado_nuevo in estados and estado_nuevo != estado_antiguo:
            return False, "El nuevo estado ya existe"

        # Reemplazar el estado
        index = estados.index(estado_antiguo)
        estados[index] = estado_nuevo

        return self.guardar_estados(estados)

    def mover_estado(self, estado, direccion):
        """
        Mueve un estado arriba o abajo en la lista

        Args:
            estado (str): Estado a mover
            direccion (str): 'arriba' o 'abajo'

        Returns:
            tuple: (success: bool, message: str)
        """
        estados = self.cargar_estados()

        if estado not in estados:
            return False, "El estado no existe"

        index = estados.index(estado)

        if direccion == 'arriba':
            if index == 0:
                return False, "El estado ya está al principio"
            # Intercambiar con el anterior
            estados[index], estados[index - 1] = estados[index - 1], estados[index]
        elif direccion == 'abajo':
            if index == len(estados) - 1:
                return False, "El estado ya está al final"
            # Intercambiar con el siguiente
            estados[index], estados[index + 1] = estados[index + 1], estados[index]
        else:
            return False, "Dirección inválida"

        return self.guardar_estados(estados)
