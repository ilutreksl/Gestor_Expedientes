"""
Script de Backup Automático de Turso Database
Exporta la base de datos a formato .db y .sql y sube a Backblaze B2
"""

import os
import sys
import json
import requests
import sqlite3
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import base64

# Cargar variables de entorno desde .env si existe (para pruebas locales)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:  # No sobrescribir si ya existe
                    os.environ[key] = value

# Configuración
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", "carlos@ilutrek.es")

# Backblaze B2
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "gestion-expedientes-app-b2")
MAX_BACKUPS = 30  # Número máximo de backups antes de mover a archivo

# Convertir URL de Turso de libsql:// a https://
if TURSO_DATABASE_URL.startswith("libsql://"):
    TURSO_DATABASE_URL = TURSO_DATABASE_URL.replace("libsql://", "https://")
elif not TURSO_DATABASE_URL.startswith("http"):
    # Si no tiene protocolo, agregar https://
    TURSO_DATABASE_URL = f"https://{TURSO_DATABASE_URL}"

def log(mensaje):
    """Imprime mensaje con timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}")

def autenticar_b2():
    """Autentica con Backblaze B2 y obtiene token de autorización"""
    try:
        log("🔐 Autenticando con Backblaze B2...")
        
        # Crear credenciales en base64
        id_and_key = f"{B2_KEY_ID}:{B2_APPLICATION_KEY}"
        basic_auth = base64.b64encode(id_and_key.encode()).decode()
        
        headers = {"Authorization": f"Basic {basic_auth}"}
        response = requests.get("https://api.backblazeb2.com/b2api/v2/b2_authorize_account", headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            log("✅ Autenticación exitosa con B2")
            return {
                'authorizationToken': data['authorizationToken'],
                'apiUrl': data['apiUrl'],
                'downloadUrl': data['downloadUrl']
            }
        else:
            log(f"❌ Error de autenticación B2: {response.text}")
            return None
    except Exception as e:
        log(f"❌ Error al autenticar con B2: {e}")
        return None

def obtener_bucket_id(auth_data):
    """Obtiene el ID del bucket"""
    try:
        headers = {"Authorization": auth_data['authorizationToken']}
        payload = {"accountId": B2_KEY_ID.split(':')[0] if ':' in B2_KEY_ID else B2_KEY_ID[:24], "bucketName": B2_BUCKET_NAME}
        
        response = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_list_buckets",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            buckets = data.get('buckets', [])
            for bucket in buckets:
                if bucket['bucketName'] == B2_BUCKET_NAME:
                    return bucket['bucketId']
            log(f"❌ Bucket '{B2_BUCKET_NAME}' no encontrado")
            return None
        else:
            log(f"❌ Error al listar buckets: {response.text}")
            return None
    except Exception as e:
        log(f"❌ Error al obtener bucket ID: {e}")
        return None

def listar_archivos_b2(auth_data, bucket_id, prefix=""):
    """Lista archivos en el bucket"""
    try:
        headers = {"Authorization": auth_data['authorizationToken']}
        payload = {
            "bucketId": bucket_id,
            "prefix": prefix,
            "maxFileCount": 10000
        }
        
        response = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_list_file_names",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('files', [])
        else:
            log(f"⚠️ Error al listar archivos: {response.text}")
            return []
    except Exception as e:
        log(f"⚠️ Error al listar archivos: {e}")
        return []

def subir_archivo_b2(auth_data, bucket_id, archivo_path, nombre_remoto):
    """Sube un archivo a Backblaze B2"""
    try:
        # Obtener URL de subida
        headers = {"Authorization": auth_data['authorizationToken']}
        payload = {"bucketId": bucket_id}
        
        response = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_get_upload_url",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            log(f"❌ Error al obtener URL de subida: {response.text}")
            return False
        
        upload_data = response.json()
        upload_url = upload_data['uploadUrl']
        upload_token = upload_data['authorizationToken']
        
        # Leer archivo y calcular SHA1
        with open(archivo_path, 'rb') as f:
            file_data = f.read()
        
        sha1 = hashlib.sha1(file_data).hexdigest()
        
        # Subir archivo
        upload_headers = {
            "Authorization": upload_token,
            "X-Bz-File-Name": nombre_remoto,
            "Content-Type": "application/octet-stream",
            "X-Bz-Content-Sha1": sha1
        }
        
        response = requests.post(upload_url, headers=upload_headers, data=file_data, timeout=300)
        
        if response.status_code == 200:
            log(f"✅ Archivo subido: {nombre_remoto}")
            return True
        else:
            log(f"❌ Error al subir archivo: {response.text}")
            return False
            
    except Exception as e:
        log(f"❌ Error al subir archivo: {e}")
        return False

def mover_archivo_b2(auth_data, bucket_id, nombre_actual, nombre_nuevo):
    """Mueve/renombra un archivo en B2"""
    try:
        headers = {"Authorization": auth_data['authorizationToken']}
        
        # Primero obtener el fileId del archivo actual
        archivos = listar_archivos_b2(auth_data, bucket_id, nombre_actual)
        file_id = None
        
        for archivo in archivos:
            if archivo['fileName'] == nombre_actual:
                file_id = archivo['fileId']
                break
        
        if not file_id:
            log(f"⚠️ Archivo no encontrado para mover: {nombre_actual}")
            return False
        
        # Copiar archivo a nueva ubicación
        payload = {
            "sourceFileId": file_id,
            "fileName": nombre_nuevo
        }
        
        response = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_copy_file",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            log(f"⚠️ Error al copiar archivo: {response.text}")
            return False
        
        # Eliminar archivo original
        delete_payload = {
            "fileId": file_id,
            "fileName": nombre_actual
        }
        
        response = requests.post(
            f"{auth_data['apiUrl']}/b2api/v2/b2_delete_file_version",
            headers=headers,
            json=delete_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            log(f"✅ Archivo movido: {nombre_actual} → {nombre_nuevo}")
            return True
        else:
            log(f"⚠️ Error al eliminar archivo original: {response.text}")
            return False
            
    except Exception as e:
        log(f"❌ Error al mover archivo: {e}")
        return False

def gestionar_rotacion_backups(auth_data, bucket_id):
    """Gestiona la rotación de backups: mantiene 30 y mueve antiguos a Archivo"""
    try:
        log("🔄 Verificando rotación de backups...")
        
        # Listar backups actuales (no en carpeta Archivo)
        todos_archivos = listar_archivos_b2(auth_data, bucket_id)
        backups = [f for f in todos_archivos if f['fileName'].startswith('backup_turso_') and not f['fileName'].startswith('Archivo/')]
        
        # Ordenar por nombre (que incluye fecha) - más antiguos primero
        backups_db = sorted([f for f in backups if f['fileName'].endswith('.db')], key=lambda x: x['fileName'])
        backups_sql = sorted([f for f in backups if f['fileName'].endswith('.sql')], key=lambda x: x['fileName'])
        
        archivos_movidos = 0
        
        # Si hay más de 30 backups .db, mover los antiguos
        while len(backups_db) > MAX_BACKUPS:
            backup_antiguo = backups_db.pop(0)
            nombre_actual = backup_antiguo['fileName']
            nombre_nuevo = f"Archivo/{nombre_actual}"
            
            if mover_archivo_b2(auth_data, bucket_id, nombre_actual, nombre_nuevo):
                archivos_movidos += 1
        
        # Si hay más de 30 backups .sql, mover los antiguos
        while len(backups_sql) > MAX_BACKUPS:
            backup_antiguo = backups_sql.pop(0)
            nombre_actual = backup_antiguo['fileName']
            nombre_nuevo = f"Archivo/{nombre_actual}"
            
            if mover_archivo_b2(auth_data, bucket_id, nombre_actual, nombre_nuevo):
                archivos_movidos += 1
        
        if archivos_movidos > 0:
            log(f"📁 {archivos_movidos} archivos movidos a carpeta Archivo")
        else:
            log(f"✅ Rotación OK: {len(backups_db)} backups .db y {len(backups_sql)} backups .sql")
        
        return True
        
    except Exception as e:
        log(f"❌ Error en rotación de backups: {e}")
        return False

def obtener_tablas_turso():
    """Obtiene la lista de tablas de la base de datos"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "statements": ["SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"]
        }
        
        log(f"Conectando a: {TURSO_DATABASE_URL}")
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            log(f"❌ Status code: {response.status_code}")
            log(f"❌ Error response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            # La respuesta es directamente una lista de resultados
            if isinstance(data, list) and len(data) > 0:
                rows = data[0].get("results", {}).get("rows", [])
                tablas = [row[0] for row in rows if row]
                return tablas
        
        return []
    except Exception as e:
        log(f"❌ Error al obtener tablas: {e}")
        import traceback
        traceback.print_exc()
        return []

def contar_registros(tabla):
    """Cuenta registros de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "statements": [f"SELECT COUNT(*) FROM {tabla}"]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                rows = data[0].get("results", {}).get("rows", [])
                if rows:
                    return rows[0][0]
        
        return 0
    except:
        return 0

def obtener_schema_tabla(tabla):
    """Obtiene el schema CREATE TABLE de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "statements": [f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tabla}'"]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                rows = data[0].get("results", {}).get("rows", [])
                if rows:
                    return rows[0][0]
        
        return None
    except Exception as e:
        log(f"❌ Error al obtener schema de {tabla}: {e}")
        return None

def obtener_datos_tabla(tabla):
    """Obtiene todos los datos de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "statements": [f"SELECT * FROM {tabla}"]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                result = data[0].get("results", {})
                columns = result.get("columns", [])
                rows = result.get("rows", [])
                return columns, rows
        
        return None, None
    except Exception as e:
        log(f"❌ Error al obtener datos de {tabla}: {e}")
        return None, None

def crear_backup_db(tablas):
    """Crea archivo .db con todos los datos"""
    fecha = datetime.now().strftime("%Y-%m-%d")
    db_path = Path(f"backup_turso_{fecha}.db")
    
    try:
        # Crear base de datos SQLite local
        if db_path.exists():
            db_path.unlink()
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        total_registros = 0
        
        for tabla in tablas:
            log(f"📦 Exportando tabla: {tabla}")
            
            # Obtener schema
            schema = obtener_schema_tabla(tabla)
            if not schema:
                log(f"⚠️  No se pudo obtener schema de {tabla}")
                continue
            
            # Crear tabla
            cursor.execute(schema)
            
            # Obtener datos
            columns, rows = obtener_datos_tabla(tabla)
            if not columns or not rows:
                log(f"ℹ️  Tabla {tabla} vacía o sin datos")
                continue
            
            # Insertar datos
            placeholders = ','.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO {tabla} ({','.join(columns)}) VALUES ({placeholders})"
            
            for row in rows:
                cursor.execute(insert_sql, row)
                total_registros += 1
            
            log(f"✅ {tabla}: {len(rows)} registros")
        
        conn.commit()
        conn.close()
        
        log(f"✅ Backup .db creado: {db_path} ({total_registros} registros totales)")
        return db_path, total_registros
        
    except Exception as e:
        log(f"❌ Error al crear backup .db: {e}")
        return None, 0

def crear_backup_sql(tablas):
    """Crea archivo .sql con DDL y datos"""
    fecha = datetime.now().strftime("%Y-%m-%d")
    sql_path = Path(f"backup_turso_{fecha}.sql")
    
    try:
        with open(sql_path, 'w', encoding='utf-8') as f:
            f.write(f"-- Backup Turso Database\n")
            f.write(f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Base de datos: Gestor RMA\n\n")
            
            total_registros = 0
            
            for tabla in tablas:
                log(f"📝 Exportando a SQL: {tabla}")
                
                # Schema
                schema = obtener_schema_tabla(tabla)
                if schema:
                    f.write(f"\n-- Tabla: {tabla}\n")
                    f.write(f"DROP TABLE IF EXISTS {tabla};\n")
                    f.write(f"{schema};\n\n")
                
                # Datos
                columns, rows = obtener_datos_tabla(tabla)
                if columns and rows:
                    for row in rows:
                        valores_sql = []
                        for v in row:
                            if v is None:
                                valores_sql.append("NULL")
                            elif isinstance(v, str):
                                valores_sql.append(f"'{v.replace(chr(39), chr(39)+chr(39))}'")
                            else:
                                valores_sql.append(str(v))
                        
                        insert = f"INSERT INTO {tabla} ({','.join(columns)}) VALUES ({','.join(valores_sql)});\n"
                        f.write(insert)
                        total_registros += 1
                    
                    f.write("\n")
                    log(f"✅ {tabla}: {len(rows)} registros")
        
        log(f"✅ Backup .sql creado: {sql_path} ({total_registros} registros totales)")
        return sql_path, total_registros
        
    except Exception as e:
        log(f"❌ Error al crear backup .sql: {e}")
        return None, 0

def enviar_email(estadisticas, errores=None, b2_urls=None):
    """Envía email con estadísticas del backup (sin adjuntos)"""
    try:
        log("📧 Preparando email...")
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"{'✅ Backup Exitoso' if not errores else '⚠️ Backup con Errores'} - Turso DB - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Cuerpo del email
        estado = "ÉXITO" if not errores else "COMPLETADO CON ERRORES"
        cuerpo = f"""
Backup Automático de Base de Datos Turso
{'='*50}

Estado: {estado}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 ESTADÍSTICAS:
  • Tablas exportadas: {estadisticas.get('tablas', 0)}
  • Total de registros: {estadisticas.get('registros', 0)}
  • Tamaño backup .db: {estadisticas.get('size_db', '0 KB')}
  • Tamaño backup .sql: {estadisticas.get('size_sql', '0 KB')}

☁️ BACKBLAZE B2:
  • Bucket: {B2_BUCKET_NAME}
  • Archivos subidos: {estadisticas.get('archivos_subidos', 0)}
"""
        
        if b2_urls:
            cuerpo += f"  • Archivos en B2:\n"
            for url in b2_urls:
                cuerpo += f"    - {url}\n"
        
        if errores:
            cuerpo += f"\n⚠️ ERRORES ENCONTRADOS:\n{errores}\n"
        
        cuerpo += f"""
{'='*50}
Este es un mensaje automático generado por GitHub Actions.
Sistema de Gestión de Expedientes RMA - ILUTREK S.L.
"""
        
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        # Enviar
        log(f"📤 Enviando email a {EMAIL_TO}...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        log("✅ Email enviado correctamente")
        return True
        
    except Exception as e:
        log(f"❌ Error al enviar email: {e}")
        return False

def main():
    """Función principal"""
    log("="*60)
    log("🚀 Iniciando Backup Automático de Turso Database")
    log("="*60)
    
    errores = []
    b2_urls = []
    
    # Verificar variables de entorno
    if not all([TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, EMAIL_USER, EMAIL_PASSWORD, B2_KEY_ID, B2_APPLICATION_KEY]):
        log("❌ ERROR: Faltan variables de entorno requeridas")
        sys.exit(1)
    
    try:
        # Autenticar con B2
        auth_data = autenticar_b2()
        if not auth_data:
            log("❌ No se pudo autenticar con Backblaze B2")
            sys.exit(1)
        
        # Obtener bucket ID
        bucket_id = obtener_bucket_id(auth_data)
        if not bucket_id:
            log("❌ No se pudo obtener el ID del bucket")
            sys.exit(1)
        
        log(f"✅ Bucket encontrado: {B2_BUCKET_NAME} (ID: {bucket_id})")
        
        # Obtener tablas
        log("📋 Obteniendo lista de tablas...")
        tablas = obtener_tablas_turso()
        
        if not tablas:
            log("❌ No se encontraron tablas")
            sys.exit(1)
        
        log(f"✅ Encontradas {len(tablas)} tablas: {', '.join(tablas)}")
        
        # Crear backups
        log("\n" + "="*60)
        log("📦 Creando backup en formato .db")
        log("="*60)
        db_path, registros_db = crear_backup_db(tablas)
        
        log("\n" + "="*60)
        log("📝 Creando backup en formato .sql")
        log("="*60)
        sql_path, registros_sql = crear_backup_sql(tablas)
        
        # Estadísticas
        estadisticas = {
            'tablas': len(tablas),
            'registros': registros_db or registros_sql,
            'size_db': f"{db_path.stat().st_size / 1024:.2f} KB" if db_path and db_path.exists() else "0 KB",
            'size_sql': f"{sql_path.stat().st_size / 1024:.2f} KB" if sql_path and sql_path.exists() else "0 KB",
            'archivos_subidos': 0
        }
        
        if not db_path:
            errores.append("- No se pudo crear el backup .db")
        if not sql_path:
            errores.append("- No se pudo crear el backup .sql")
        
        # Subir archivos a B2
        log("\n" + "="*60)
        log("☁️ Subiendo backups a Backblaze B2")
        log("="*60)
        
        archivos_subidos = 0
        
        if db_path and db_path.exists():
            if subir_archivo_b2(auth_data, bucket_id, db_path, db_path.name):
                archivos_subidos += 1
                b2_urls.append(db_path.name)
            else:
                errores.append(f"- Error al subir {db_path.name}")
        
        if sql_path and sql_path.exists():
            if subir_archivo_b2(auth_data, bucket_id, sql_path, sql_path.name):
                archivos_subidos += 1
                b2_urls.append(sql_path.name)
            else:
                errores.append(f"- Error al subir {sql_path.name}")
        
        estadisticas['archivos_subidos'] = archivos_subidos
        
        # Gestionar rotación de backups
        log("\n" + "="*60)
        log("🔄 Gestionando rotación de backups")
        log("="*60)
        gestionar_rotacion_backups(auth_data, bucket_id)
        
        # Enviar email con estadísticas
        log("\n" + "="*60)
        log("📧 Enviando notificación por email")
        log("="*60)
        
        errores_texto = "\n".join(errores) if errores else None
        email_ok = enviar_email(estadisticas, errores_texto, b2_urls)
        
        # Limpiar archivos temporales
        if db_path and db_path.exists():
            db_path.unlink()
            log(f"🗑️  Eliminado archivo temporal: {db_path}")
        if sql_path and sql_path.exists():
            sql_path.unlink()
            log(f"🗑️  Eliminado archivo temporal: {sql_path}")
        
        log("\n" + "="*60)
        if email_ok and not errores and archivos_subidos == 2:
            log("✅ Backup completado exitosamente")
            log("="*60)
            sys.exit(0)
        else:
            log("⚠️  Backup completado con errores")
            log("="*60)
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
