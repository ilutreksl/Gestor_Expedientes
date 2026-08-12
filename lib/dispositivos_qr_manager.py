"""
Gestión de dispositivos y PINs para el flujo de recepción de paquetes por QR.

Los PINs se generan y cancelan desde aquí (app de escritorio), pero se
consumen/validan desde el Worker de Cloudflare, que es quien realmente
registra un dispositivo nuevo y controla los intentos fallidos. Esta clase
solo gestiona el lado de administración: generar, listar y revocar.

La tabla config_recepcion_qr es una fila única (id = 1) compartida con
PersonasRecepcionManager (que solo toca la columna personas_recepcion); aquí
se gestionan el resto de columnas: mensaje_incidencias, pin_max_intentos,
pin_caducidad_minutos.
"""

import secrets
from datetime import datetime, timedelta

from lib.logger_config import get_logger

logger = get_logger()


class DispositivosQRManager:
    """Gestiona PINs y dispositivos registrados para la recepción por QR"""

    def generar_pin(self, creado_por):
        """
        Genera un PIN de un solo uso, con la caducidad configurada.

        Args:
            creado_por (str): usuario admin que genera el PIN

        Returns:
            tuple: (pin: str | None, error: str | None)
        """
        from lib.app_core import connect_db
        try:
            config = self.obtener_config()
            minutos = config.get("pin_caducidad_minutos", 15)

            pin = f"{secrets.randbelow(1_000_000):06d}"
            ahora = datetime.now()
            caducidad = ahora + timedelta(minutes=minutos)

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pins_qr (pin, estado, creado_por, fecha_creacion, fecha_caducidad, intentos_fallidos) "
                "VALUES (?, 'pendiente', ?, ?, ?, 0)",
                (pin, creado_por, ahora.isoformat(), caducidad.isoformat())
            )
            conn.commit()
            conn.close()

            logger.info(f"PIN generado por {creado_por}, caduca {caducidad.isoformat()}")
            return pin, None
        except Exception as e:
            logger.error(f"Error al generar PIN: {e}")
            return None, str(e)

    def cancelar_pin(self, pin_id):
        """Cancela un PIN pendiente antes de que se use (estado -> caducado)"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pins_qr SET estado = 'caducado' WHERE id = ? AND estado = 'pendiente'",
                (pin_id,)
            )
            conn.commit()
            conn.close()
            logger.info(f"PIN id={pin_id} cancelado")
            return True, "PIN cancelado"
        except Exception as e:
            logger.error(f"Error al cancelar PIN id={pin_id}: {e}")
            return False, str(e)

    def listar_pins_pendientes(self):
        """Devuelve los PINs con estado 'pendiente', más recientes primero"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, pin, creado_por, fecha_creacion, fecha_caducidad, intentos_fallidos "
                "FROM pins_qr WHERE estado = 'pendiente' ORDER BY fecha_creacion DESC"
            )
            filas = cursor.fetchall()
            conn.close()
            columnas = ["id", "pin", "creado_por", "fecha_creacion", "fecha_caducidad", "intentos_fallidos"]
            return [dict(zip(columnas, fila)) for fila in filas]
        except Exception as e:
            logger.error(f"Error al listar PINs pendientes: {e}")
            return []

    def listar_dispositivos(self, incluir_revocados=False):
        """Devuelve los dispositivos registrados, más recientes primero"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            sql = (
                "SELECT id, tipo, nombre_persona, fecha_registro, revocado, fecha_revocado, puede_editar "
                "FROM dispositivos_qr"
            )
            if not incluir_revocados:
                sql += " WHERE revocado = 0"
            sql += " ORDER BY fecha_registro DESC"
            cursor.execute(sql)
            filas = cursor.fetchall()
            conn.close()
            columnas = ["id", "tipo", "nombre_persona", "fecha_registro", "revocado", "fecha_revocado", "puede_editar"]
            return [dict(zip(columnas, fila)) for fila in filas]
        except Exception as e:
            logger.error(f"Error al listar dispositivos: {e}")
            return []

    def revocar_dispositivo(self, dispositivo_id):
        """Revoca un dispositivo registrado; deberá volver a pedir PIN para usarse"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dispositivos_qr SET revocado = 1, fecha_revocado = ? WHERE id = ?",
                (datetime.now().isoformat(), dispositivo_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"Dispositivo id={dispositivo_id} revocado")
            return True, "Dispositivo revocado"
        except Exception as e:
            logger.error(f"Error al revocar dispositivo id={dispositivo_id}: {e}")
            return False, str(e)

    def set_puede_editar(self, dispositivo_id, valor):
        """Concede o retira permiso de edición desde el móvil a un dispositivo"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dispositivos_qr SET puede_editar = ? WHERE id = ?",
                (1 if valor else 0, dispositivo_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"Dispositivo id={dispositivo_id} puede_editar={'sí' if valor else 'no'}")
            return True, "Permiso actualizado"
        except Exception as e:
            logger.error(f"Error al actualizar permiso de edición del dispositivo id={dispositivo_id}: {e}")
            return False, str(e)

    def obtener_config(self):
        """Devuelve mensaje_incidencias, pin_max_intentos y pin_caducidad_minutos"""
        from lib.app_core import connect_db
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mensaje_incidencias, pin_max_intentos, pin_caducidad_minutos "
                "FROM config_recepcion_qr WHERE id = 1"
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return {"mensaje_incidencias": "", "pin_max_intentos": 5, "pin_caducidad_minutos": 15}
            return {
                "mensaje_incidencias": row[0] or "",
                "pin_max_intentos": row[1] if row[1] is not None else 5,
                "pin_caducidad_minutos": row[2] if row[2] is not None else 15,
            }
        except Exception as e:
            logger.error(f"Error al obtener configuración de recepción QR: {e}")
            return {"mensaje_incidencias": "", "pin_max_intentos": 5, "pin_caducidad_minutos": 15}

    def actualizar_config(self, mensaje_incidencias=None, pin_max_intentos=None, pin_caducidad_minutos=None):
        """Actualiza uno o varios campos de configuración (los que sean distintos de None)"""
        from lib.app_core import connect_db
        try:
            campos = []
            valores = []
            if mensaje_incidencias is not None:
                campos.append("mensaje_incidencias = ?")
                valores.append(mensaje_incidencias)
            if pin_max_intentos is not None:
                campos.append("pin_max_intentos = ?")
                valores.append(pin_max_intentos)
            if pin_caducidad_minutos is not None:
                campos.append("pin_caducidad_minutos = ?")
                valores.append(pin_caducidad_minutos)

            if not campos:
                return True, "Nada que actualizar"

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE config_recepcion_qr SET {', '.join(campos)} WHERE id = 1", tuple(valores))
            conn.commit()
            conn.close()
            logger.info("Configuración de recepción QR actualizada")
            return True, "Configuración guardada"
        except Exception as e:
            logger.error(f"Error al actualizar configuración de recepción QR: {e}")
            return False, str(e)
