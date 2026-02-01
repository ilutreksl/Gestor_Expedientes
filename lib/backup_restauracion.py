"""
Módulo para restaurar backups de base de datos desde archivos .db o .sql
"""
import os
import sqlite3
import shutil
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validar_archivo_backup(ruta_archivo):
    """
    Valida que el archivo de backup sea válido (.db o .sql)
    
    Args:
        ruta_archivo: Ruta del archivo a validar
    
    Returns:
        tuple: (es_valido: bool, tipo_archivo: str, mensaje_error: str)
    """
    if not os.path.exists(ruta_archivo):
        return False, None, "El archivo no existe"
    
    extension = os.path.splitext(ruta_archivo)[1].lower()
    
    if extension not in ['.db', '.sql']:
        return False, None, "El archivo debe ser .db o .sql"
    
    # Validar que el archivo no esté vacío
    if os.path.getsize(ruta_archivo) == 0:
        return False, None, "El archivo está vacío"
    
    # Si es .db, validar que sea una base de datos SQLite válida
    if extension == '.db':
        try:
            conn = sqlite3.connect(ruta_archivo)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = cursor.fetchall()
            conn.close()
            
            if not tablas:
                return False, None, "El archivo .db no contiene tablas"
            
            logger.info(f"Archivo .db validado: {len(tablas)} tablas encontradas")
            return True, 'db', None
            
        except sqlite3.Error as e:
            return False, None, f"El archivo .db no es válido: {str(e)}"
    
    # Si es .sql, validar que contenga comandos SQL
    elif extension == '.sql':
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar que contenga comandos SQL básicos
            comandos_sql = ['CREATE', 'INSERT', 'UPDATE', 'DELETE', 'DROP']
            if not any(cmd in contenido.upper() for cmd in comandos_sql):
                return False, None, "El archivo .sql no contiene comandos SQL válidos"
            
            logger.info(f"Archivo .sql validado: {len(contenido)} caracteres")
            return True, 'sql', None
            
        except Exception as e:
            return False, None, f"Error al leer el archivo .sql: {str(e)}"
    
    return False, None, "Tipo de archivo desconocido"


def crear_backup_actual(ruta_db_actual):
    """
    Crea un backup de seguridad de la base de datos actual antes de restaurar
    
    Args:
        ruta_db_actual: Ruta de la base de datos actual
    
    Returns:
        tuple: (exito: bool, ruta_backup: str, mensaje_error: str)
    """
    try:
        # Crear directorio de backups de emergencia si no existe
        directorio_backup = os.path.join(os.path.dirname(ruta_db_actual), "backups_emergencia")
        os.makedirs(directorio_backup, exist_ok=True)
        
        # Nombre del backup con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"backup_antes_restauracion_{timestamp}.db"
        ruta_backup = os.path.join(directorio_backup, nombre_backup)
        
        # Copiar base de datos actual
        shutil.copy2(ruta_db_actual, ruta_backup)
        
        logger.info(f"Backup de seguridad creado en: {ruta_backup}")
        return True, ruta_backup, None
        
    except Exception as e:
        logger.error(f"Error al crear backup de seguridad: {str(e)}")
        return False, None, f"Error al crear backup de seguridad: {str(e)}"


def restaurar_desde_db(ruta_backup_db, ruta_db_destino):
    """
    Restaura una base de datos desde un archivo .db
    
    Args:
        ruta_backup_db: Ruta del archivo .db de backup
        ruta_db_destino: Ruta donde restaurar la base de datos
    
    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    try:
        logger.info(f"Iniciando restauración desde archivo .db: {ruta_backup_db}")
        
        # Cerrar cualquier conexión existente (esto debe hacerse desde fuera)
        # Simplemente copiamos el archivo
        shutil.copy2(ruta_backup_db, ruta_db_destino)
        
        # Verificar que la restauración fue exitosa
        conn = sqlite3.connect(ruta_db_destino)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        conn.close()
        
        logger.info(f"Base de datos restaurada exitosamente: {len(tablas)} tablas")
        return True, f"Base de datos restaurada correctamente ({len(tablas)} tablas)"
        
    except Exception as e:
        logger.error(f"Error al restaurar desde .db: {str(e)}")
        return False, f"Error al restaurar: {str(e)}"


def restaurar_desde_sql(ruta_backup_sql, ruta_db_destino):
    """
    Restaura una base de datos desde un archivo .sql
    
    Args:
        ruta_backup_sql: Ruta del archivo .sql de backup
        ruta_db_destino: Ruta donde restaurar la base de datos
    
    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    try:
        logger.info(f"Iniciando restauración desde archivo .sql: {ruta_backup_sql}")
        
        # Leer el archivo SQL
        with open(ruta_backup_sql, 'r', encoding='utf-8') as f:
            script_sql = f.read()
        
        # Eliminar la base de datos actual si existe
        if os.path.exists(ruta_db_destino):
            os.remove(ruta_db_destino)
            logger.info("Base de datos actual eliminada")
        
        # Crear nueva base de datos y ejecutar el script
        conn = sqlite3.connect(ruta_db_destino)
        cursor = conn.cursor()
        
        # Ejecutar el script SQL
        cursor.executescript(script_sql)
        conn.commit()
        
        # Verificar que la restauración fue exitosa
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        
        # Contar registros en tablas principales
        total_registros = 0
        if any('rma_maestro' in str(tabla) for tabla in tablas):
            cursor.execute("SELECT COUNT(*) FROM rma_maestro")
            total_registros = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"Base de datos restaurada desde SQL: {len(tablas)} tablas, {total_registros} registros en rma_maestro")
        return True, f"Base de datos restaurada correctamente ({len(tablas)} tablas, {total_registros} expedientes)"
        
    except Exception as e:
        logger.error(f"Error al restaurar desde .sql: {str(e)}")
        return False, f"Error al restaurar: {str(e)}"


def restaurar_en_turso(ruta_archivo_backup):
    """
    Restaura un backup directamente en Turso (BD principal)
    
    Args:
        ruta_archivo_backup: Ruta del archivo de backup (.db o .sql)
    
    Returns:
        tuple: (exito: bool, mensaje: str, total_comandos: int)
    """
    try:
        # Verificar si Turso está configurado
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")
        
        if not turso_url or not turso_token:
            logger.warning("Turso no configurado")
            return False, "Turso no está configurado (variables TURSO_DATABASE_URL y TURSO_AUTH_TOKEN no encontradas)", 0
        
        logger.info(f"Iniciando restauración en Turso desde: {ruta_archivo_backup}")
        
        # Determinar el tipo de archivo y obtener el SQL
        extension = os.path.splitext(ruta_archivo_backup)[1].lower()
        
        if extension == '.sql':
            # Leer directamente el archivo SQL
            with open(ruta_archivo_backup, 'r', encoding='utf-8') as f:
                script_sql = f.read()
            logger.info(f"Archivo SQL leído: {len(script_sql)} caracteres")
            
        elif extension == '.db':
            # Convertir .db a SQL usando sqlite3
            logger.info("Convirtiendo archivo .db a SQL...")
            conn = sqlite3.connect(ruta_archivo_backup)
            script_sql = '\n'.join(conn.iterdump())
            conn.close()
            logger.info(f"Archivo .db convertido a SQL: {len(script_sql)} caracteres")
        else:
            return False, f"Formato de archivo no soportado: {extension}", 0
        
        # Dividir el script en comandos individuales
        comandos = [cmd.strip() for cmd in script_sql.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
        
        logger.info(f"Total de comandos SQL a ejecutar en Turso: {len(comandos)}")
        
        # Importar a Turso usando requests
        import requests
        
        # Preparar batch de requests
        requests_batch = []
        for comando in comandos:
            if comando:
                # Añadir ; al final si no lo tiene
                sql_cmd = comando if comando.endswith(';') else comando + ';'
                requests_batch.append({
                    "type": "execute",
                    "stmt": {"sql": sql_cmd}
                })
        
        # Ejecutar en lotes para evitar timeouts
        batch_size = 50  # Reducido para mayor estabilidad
        total_batches = (len(requests_batch) + batch_size - 1) // batch_size
        comandos_ejecutados = 0
        
        logger.info(f"Ejecutando en {total_batches} lotes de hasta {batch_size} comandos")
        
        for i in range(0, len(requests_batch), batch_size):
            batch = requests_batch[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Ejecutando lote {batch_num}/{total_batches} ({len(batch)} comandos)")
            
            try:
                response = requests.post(
                    turso_url,
                    headers={"Authorization": f"Bearer {turso_token}"},
                    json={"requests": batch},
                    timeout=60
                )
                
                if response.status_code != 200:
                    logger.error(f"Error en lote {batch_num}: {response.status_code} - {response.text}")
                    return False, f"Error al restaurar en Turso (lote {batch_num}/{total_batches}): HTTP {response.status_code}", comandos_ejecutados
                
                # Verificar si hay errores en la respuesta
                data = response.json()
                results = data.get("results", [])
                
                for idx, result in enumerate(results):
                    if result.get("type") == "error":
                        error_msg = result.get("error", {}).get("message", "Unknown error")
                        logger.error(f"Error SQL en comando {comandos_ejecutados + idx + 1}: {error_msg}")
                        # Continuar con los demás comandos en lugar de fallar completamente
                
                comandos_ejecutados += len(batch)
                logger.info(f"Lote {batch_num} ejecutado: {comandos_ejecutados}/{len(requests_batch)} comandos completados")
                
            except requests.exceptions.Timeout:
                logger.error(f"Timeout en lote {batch_num}")
                return False, f"Timeout al restaurar en Turso (lote {batch_num}/{total_batches})", comandos_ejecutados
            except Exception as e:
                logger.error(f"Error en lote {batch_num}: {str(e)}")
                return False, f"Error en lote {batch_num}: {str(e)}", comandos_ejecutados
        
        logger.info(f"Restauración en Turso completada: {comandos_ejecutados} comandos ejecutados")
        return True, f"Base de datos restaurada en Turso ({comandos_ejecutados} comandos ejecutados)", comandos_ejecutados
        
    except Exception as e:
        logger.error(f"Error al restaurar en Turso: {str(e)}", exc_info=True)
        return False, f"Error al restaurar en Turso: {str(e)}", 0


def sincronizar_con_turso(ruta_db_local):
    """
    Sincroniza la base de datos local restaurada con Turso
    
    Args:
        ruta_db_local: Ruta de la base de datos local restaurada
    
    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    try:
        # Verificar si Turso está configurado
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")
        
        if not turso_url or not turso_token:
            logger.info("Turso no configurado, omitiendo sincronización con Turso")
            return True, "Turso no configurado (solo restauración local)"
        
        logger.info("Iniciando sincronización con Turso...")
        
        # Buscar el script de exportación SQL
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        directorio_raiz = os.path.dirname(directorio_actual)
        script_export = os.path.join(directorio_raiz, "scripts", "export_sqlite_dump.py")
        
        if not os.path.exists(script_export):
            logger.warning(f"Script de exportación no encontrado: {script_export}")
            return False, "No se encontró el script de exportación para sincronizar con Turso"
        
        # Exportar la base de datos local a SQL
        directorio_temp = os.path.join(directorio_raiz, "temp_restore")
        os.makedirs(directorio_temp, exist_ok=True)
        
        archivo_sql = os.path.join(directorio_temp, "restauracion_turso.sql")
        
        # Ejecutar script de exportación
        logger.info(f"Exportando BD local a SQL: {archivo_sql}")
        resultado = subprocess.run(
            ["python", script_export, ruta_db_local, archivo_sql],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if resultado.returncode != 0:
            logger.error(f"Error al exportar BD a SQL: {resultado.stderr}")
            return False, f"Error al exportar BD: {resultado.stderr}"
        
        # Leer el archivo SQL
        with open(archivo_sql, 'r', encoding='utf-8') as f:
            script_sql = f.read()
        
        logger.info(f"Archivo SQL generado: {len(script_sql)} caracteres")
        
        # Importar a Turso usando requests
        import requests
        import json
        
        # Dividir el script en comandos individuales
        comandos = [cmd.strip() for cmd in script_sql.split(';') if cmd.strip()]
        
        logger.info(f"Ejecutando {len(comandos)} comandos en Turso...")
        
        # Preparar batch de requests
        requests_batch = []
        for comando in comandos:
            if comando:
                requests_batch.append({
                    "type": "execute",
                    "stmt": {"sql": comando + ";"}
                })
        
        # Ejecutar en lotes de 100 comandos para evitar timeouts
        batch_size = 100
        total_batches = (len(requests_batch) + batch_size - 1) // batch_size
        
        for i in range(0, len(requests_batch), batch_size):
            batch = requests_batch[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Ejecutando lote {batch_num}/{total_batches} ({len(batch)} comandos)")
            
            response = requests.post(
                turso_url,
                headers={"Authorization": f"Bearer {turso_token}"},
                json={"requests": batch},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Error en lote {batch_num}: {response.status_code} - {response.text}")
                return False, f"Error al sincronizar con Turso (lote {batch_num}): {response.text}"
        
        # Limpiar archivos temporales
        try:
            os.remove(archivo_sql)
            os.rmdir(directorio_temp)
        except:
            pass
        
        logger.info("Sincronización con Turso completada exitosamente")
        return True, "Sincronizado con Turso correctamente"
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout al exportar BD a SQL")
        return False, "Timeout al preparar datos para Turso"
    except Exception as e:
        logger.error(f"Error al sincronizar con Turso: {str(e)}", exc_info=True)
        return False, f"Error al sincronizar con Turso: {str(e)}"


def restaurar_backup(ruta_archivo_backup, ruta_db_destino, sincronizar_turso=True):
    """
    Función principal para restaurar un backup
    PRIORIDAD: Turso es la BD principal, local es secundaria
    
    Flujo:
    1. Restaurar en Turso (BD principal) si está configurado
    2. Restaurar en local (BD secundaria) opcionalmente
    
    Args:
        ruta_archivo_backup: Ruta del archivo de backup (.db o .sql)
        ruta_db_destino: Ruta de la base de datos local de destino
        sincronizar_turso: Si True, restaura también en Turso (recomendado)
    
    Returns:
        tuple: (exito: bool, mensaje: str, ruta_backup_seguridad: str)
    """
    # Validar archivo
    es_valido, tipo_archivo, error = validar_archivo_backup(ruta_archivo_backup)
    if not es_valido:
        logger.error(f"Archivo de backup no válido: {error}")
        return False, error, None
    
    # Verificar si Turso está configurado
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    turso_configurado = bool(turso_url and turso_token)
    
    mensajes = []
    ruta_backup_seguridad = None
    
    # ========================================
    # PASO 1: RESTAURAR EN TURSO (BD PRINCIPAL)
    # ========================================
    if turso_configurado and sincronizar_turso:
        logger.info("=" * 60)
        logger.info("PASO 1: Restaurando en TURSO (Base de datos PRINCIPAL)")
        logger.info("=" * 60)
        
        exito_turso, msg_turso, comandos = restaurar_en_turso(ruta_archivo_backup)
        
        if exito_turso:
            mensajes.append(f"✅ TURSO (Principal): {msg_turso}")
            logger.info("Restauración en Turso completada exitosamente")
        else:
            logger.error(f"Error al restaurar en Turso: {msg_turso}")
            mensajes.append(f"❌ TURSO (Principal): {msg_turso}")
            # Si falla Turso (BD principal), es un error crítico
            return False, "\n".join(mensajes), None
    
    elif turso_configurado and not sincronizar_turso:
        logger.warning("Turso configurado pero sincronización deshabilitada")
        mensajes.append("⚠️ TURSO: Sincronización deshabilitada (BD principal NO restaurada)")
    
    else:
        logger.info("Turso no configurado, omitiendo restauración en Turso")
        mensajes.append("ℹ️ TURSO: No configurado (solo se restaurará local)")
    
    # ========================================
    # PASO 2: RESTAURAR EN LOCAL (BD SECUNDARIA - OPCIONAL)
    # ========================================
    logger.info("=" * 60)
    logger.info("PASO 2: Restaurando en LOCAL (Base de datos secundaria)")
    logger.info("=" * 60)
    
    try:
        # Crear backup de seguridad de la BD local si existe
        if os.path.exists(ruta_db_destino):
            exito_backup, ruta_backup_seguridad, error_backup = crear_backup_actual(ruta_db_destino)
            if not exito_backup:
                logger.warning(f"No se pudo crear backup de seguridad local: {error_backup}")
                mensajes.append(f"⚠️ LOCAL: No se pudo crear backup de seguridad")
            else:
                logger.info(f"Backup de seguridad local creado: {ruta_backup_seguridad}")
        else:
            logger.info("Base de datos local no existe, se creará nueva")
        
        # Restaurar en local
        if tipo_archivo == 'db':
            exito_local, mensaje_local = restaurar_desde_db(ruta_archivo_backup, ruta_db_destino)
        elif tipo_archivo == 'sql':
            exito_local, mensaje_local = restaurar_desde_sql(ruta_archivo_backup, ruta_db_destino)
        else:
            return False, "Tipo de archivo no soportado", ruta_backup_seguridad
        
        if exito_local:
            mensajes.append(f"✅ LOCAL (Secundaria): {mensaje_local}")
            logger.info("Restauración local completada exitosamente")
        else:
            mensajes.append(f"⚠️ LOCAL (Secundaria): {mensaje_local}")
            logger.warning(f"Error al restaurar en local: {mensaje_local}")
            # Si local falla pero Turso OK, no es crítico (Turso es principal)
            if turso_configurado:
                mensajes.append("ℹ️ La BD principal (Turso) fue restaurada correctamente")
        
    except Exception as e:
        logger.error(f"Error inesperado al restaurar en local: {str(e)}", exc_info=True)
        mensajes.append(f"❌ LOCAL: Error inesperado: {str(e)}")
        # Si local falla pero Turso OK, aún es éxito parcial
        if turso_configurado and any("✅ TURSO" in m for m in mensajes):
            mensajes.append("ℹ️ La BD principal (Turso) fue restaurada correctamente")
    
    # ========================================
    # RESULTADO FINAL
    # ========================================
    mensaje_final = "\n".join(mensajes)
    
    # Determinar si la restauración fue exitosa
    # Éxito = Turso OK (si está configurado) O local OK (si Turso no está configurado)
    if turso_configurado:
        # Si Turso está configurado, es la BD principal
        exito_final = any("✅ TURSO" in m for m in mensajes)
        if exito_final:
            logger.info("Restauración EXITOSA: BD principal (Turso) restaurada")
        else:
            logger.error("Restauración FALLIDA: BD principal (Turso) no restaurada")
    else:
        # Si Turso no está configurado, local es la BD principal
        exito_final = any("✅ LOCAL" in m for m in mensajes)
        if exito_final:
            logger.info("Restauración EXITOSA: BD local restaurada")
        else:
            logger.error("Restauración FALLIDA: BD local no restaurada")
    
    return exito_final, mensaje_final, ruta_backup_seguridad


def obtener_info_backup(ruta_archivo):
    """
    Obtiene información sobre un archivo de backup
    
    Args:
        ruta_archivo: Ruta del archivo de backup
    
    Returns:
        dict: Información del backup (tablas, registros, tamaño, etc.)
    """
    info = {
        'archivo': os.path.basename(ruta_archivo),
        'ruta': ruta_archivo,
        'tamaño': os.path.getsize(ruta_archivo),
        'fecha_modificacion': datetime.fromtimestamp(os.path.getmtime(ruta_archivo)),
        'tipo': os.path.splitext(ruta_archivo)[1],
        'tablas': [],
        'total_registros': 0,
        'es_valido': False
    }
    
    try:
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        if extension == '.db':
            conn = sqlite3.connect(ruta_archivo)
            cursor = conn.cursor()
            
            # Obtener lista de tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            info['tablas'] = [tabla[0] for tabla in cursor.fetchall()]
            
            # Contar registros en rma_maestro si existe
            if 'rma_maestro' in info['tablas']:
                cursor.execute("SELECT COUNT(*) FROM rma_maestro")
                info['total_registros'] = cursor.fetchone()[0]
            
            conn.close()
            info['es_valido'] = True
            
        elif extension == '.sql':
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar CREATE TABLE para detectar tablas
            import re
            tablas_match = re.findall(r'CREATE TABLE (?:IF NOT EXISTS )?["\']?(\w+)["\']?', contenido, re.IGNORECASE)
            info['tablas'] = list(set(tablas_match))
            
            # Intentar estimar registros contando INSERT
            inserts_match = re.findall(r'INSERT INTO ["\']?rma_maestro["\']?', contenido, re.IGNORECASE)
            info['total_registros'] = len(inserts_match)
            
            info['es_valido'] = len(info['tablas']) > 0
        
        logger.info(f"Información de backup obtenida: {info['archivo']}, {len(info['tablas'])} tablas, {info['total_registros']} registros")
        
    except Exception as e:
        logger.error(f"Error al obtener información del backup: {str(e)}")
        info['error'] = str(e)
    
    return info
