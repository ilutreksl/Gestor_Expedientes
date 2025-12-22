"""
Script de Backup Automático de Turso Database
Exporta la base de datos a formato .db y .sql y envía por email
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
from email.mime.base import MIMEBase
from email import encoders

# Configuración
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", "carlos@ilutrek.es")

def log(mensaje):
    """Imprime mensaje con timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}")

def obtener_tablas_turso():
    """Obtiene la lista de tablas de la base de datos"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "requests": [{"type": "execute", "stmt": {"sql": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name", "args": []}}]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                rows = results[0].get("response", {}).get("result", {}).get("rows", [])
                tablas = [row.get("values", [])[0] for row in rows if row.get("values")]
                return tablas
        
        return []
    except Exception as e:
        log(f"❌ Error al obtener tablas: {e}")
        return []

def contar_registros(tabla):
    """Cuenta registros de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "requests": [{"type": "execute", "stmt": {"sql": f"SELECT COUNT(*) FROM {tabla}", "args": []}}]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                rows = results[0].get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    return rows[0].get("values", [])[0]
        
        return 0
    except:
        return 0

def obtener_schema_tabla(tabla):
    """Obtiene el schema CREATE TABLE de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "requests": [{"type": "execute", "stmt": {"sql": f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tabla}'", "args": []}}]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                rows = results[0].get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    return rows[0].get("values", [])[0]
        
        return None
    except Exception as e:
        log(f"❌ Error al obtener schema de {tabla}: {e}")
        return None

def obtener_datos_tabla(tabla):
    """Obtiene todos los datos de una tabla"""
    try:
        headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}"}
        payload = {
            "requests": [{"type": "execute", "stmt": {"sql": f"SELECT * FROM {tabla}", "args": []}}]
        }
        
        response = requests.post(TURSO_DATABASE_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                result = results[0].get("response", {}).get("result", {})
                columns = [col.get("name") for col in result.get("cols", [])]
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
                valores = row.get("values", [])
                cursor.execute(insert_sql, valores)
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
                        valores = row.get("values", [])
                        valores_sql = []
                        for v in valores:
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

def enviar_email(db_path, sql_path, estadisticas, errores=None):
    """Envía email con los backups adjuntos"""
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

📁 ARCHIVOS ADJUNTOS:
  • {db_path.name if db_path else 'No disponible'}
  • {sql_path.name if sql_path else 'No disponible'}
"""
        
        if errores:
            cuerpo += f"\n⚠️ ERRORES ENCONTRADOS:\n{errores}\n"
        
        cuerpo += f"""
{'='*50}
Este es un mensaje automático generado por GitHub Actions.
Sistema de Gestión de Expedientes RMA - ILUTREK S.L.
"""
        
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        # Adjuntar archivos
        for archivo_path in [db_path, sql_path]:
            if archivo_path and archivo_path.exists():
                with open(archivo_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={archivo_path.name}')
                    msg.attach(part)
                    log(f"📎 Adjuntado: {archivo_path.name}")
        
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
    
    # Verificar variables de entorno
    if not all([TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, EMAIL_USER, EMAIL_PASSWORD]):
        log("❌ ERROR: Faltan variables de entorno requeridas")
        sys.exit(1)
    
    try:
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
            'size_sql': f"{sql_path.stat().st_size / 1024:.2f} KB" if sql_path and sql_path.exists() else "0 KB"
        }
        
        if not db_path:
            errores.append("- No se pudo crear el backup .db")
        if not sql_path:
            errores.append("- No se pudo crear el backup .sql")
        
        # Enviar email
        log("\n" + "="*60)
        log("📧 Enviando backup por email")
        log("="*60)
        
        errores_texto = "\n".join(errores) if errores else None
        email_ok = enviar_email(db_path, sql_path, estadisticas, errores_texto)
        
        # Limpiar archivos temporales
        if db_path and db_path.exists():
            db_path.unlink()
            log(f"🗑️  Eliminado archivo temporal: {db_path}")
        if sql_path and sql_path.exists():
            sql_path.unlink()
            log(f"🗑️  Eliminado archivo temporal: {sql_path}")
        
        log("\n" + "="*60)
        if email_ok and not errores:
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
