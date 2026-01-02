"""
Módulo de Gestión de Backups en Backblaze B2
Proporciona funciones para listar, descargar, mover y eliminar backups
"""

import os
import requests
import base64
from datetime import datetime
from pathlib import Path
import subprocess
import sys

class BackupManagerB2:
    """Clase para gestionar backups en Backblaze B2"""
    
    def __init__(self):
        self.b2_key_id = os.getenv("B2_KEY_ID")
        self.b2_application_key = os.getenv("B2_APPLICATION_KEY")
        self.b2_bucket_name = os.getenv("B2_BUCKET_NAME", "gestion-expedientes-app-b2")
        self.auth_data = None
        self.bucket_id = None
        
    def autenticar(self):
        """Autentica con Backblaze B2 y obtiene token de autorización"""
        try:
            if not self.b2_key_id or not self.b2_application_key:
                return False, "Credenciales de B2 no configuradas"
            
            # Crear credenciales en base64
            id_and_key = f"{self.b2_key_id}:{self.b2_application_key}"
            basic_auth = base64.b64encode(id_and_key.encode()).decode()
            
            headers = {"Authorization": f"Basic {basic_auth}"}
            response = requests.get("https://api.backblazeb2.com/b2api/v2/b2_authorize_account", 
                                    headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_data = {
                    'authorizationToken': data['authorizationToken'],
                    'apiUrl': data['apiUrl'],
                    'downloadUrl': data['downloadUrl'],
                    'accountId': data['accountId']
                }
                return True, "Autenticación exitosa"
            else:
                return False, f"Error de autenticación: {response.text}"
        except Exception as e:
            return False, f"Error al autenticar: {e}"
    
    def obtener_bucket_id(self):
        """Obtiene el ID del bucket"""
        try:
            if not self.auth_data:
                return False, "No autenticado"
            
            headers = {"Authorization": self.auth_data['authorizationToken']}
            payload = {"accountId": self.auth_data['accountId'], "bucketName": self.b2_bucket_name}
            
            response = requests.post(
                f"{self.auth_data['apiUrl']}/b2api/v2/b2_list_buckets",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                buckets = data.get('buckets', [])
                for bucket in buckets:
                    if bucket['bucketName'] == self.b2_bucket_name:
                        self.bucket_id = bucket['bucketId']
                        return True, "Bucket encontrado"
                return False, "Bucket no encontrado"
            else:
                return False, f"Error al buscar bucket: {response.text}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def listar_archivos(self, prefix=""):
        """Lista todos los archivos en el bucket con un prefijo opcional"""
        try:
            if not self.auth_data or not self.bucket_id:
                return None, "No autenticado o bucket no encontrado"
            
            headers = {"Authorization": self.auth_data['authorizationToken']}
            archivos = []
            next_file_name = None
            
            while True:
                payload = {
                    "bucketId": self.bucket_id,
                    "maxFileCount": 1000
                }
                
                if prefix:
                    payload["prefix"] = prefix
                
                if next_file_name:
                    payload["startFileName"] = next_file_name
                
                response = requests.post(
                    f"{self.auth_data['apiUrl']}/b2api/v2/b2_list_file_names",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code != 200:
                    return None, f"Error al listar archivos: {response.text}"
                
                data = response.json()
                files = data.get('files', [])
                
                for file in files:
                    archivos.append({
                        'fileName': file['fileName'],
                        'fileId': file['fileId'],
                        'contentLength': file['contentLength'],
                        'uploadTimestamp': file['uploadTimestamp'],
                        'contentType': file.get('contentType', 'application/octet-stream')
                    })
                
                next_file_name = data.get('nextFileName')
                if not next_file_name:
                    break
            
            return archivos, "OK"
        except Exception as e:
            return None, f"Error: {e}"
    
    def descargar_archivo(self, file_id, file_name, destino_local):
        """Descarga un archivo de B2 al sistema local"""
        try:
            if not self.auth_data:
                return False, "No autenticado"
            
            headers = {"Authorization": self.auth_data['authorizationToken']}
            
            # Obtener URL de descarga
            download_url = f"{self.auth_data['downloadUrl']}/file/{self.b2_bucket_name}/{file_name}"
            
            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                with open(destino_local, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True, "Archivo descargado correctamente"
            else:
                return False, f"Error al descargar: {response.text}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def eliminar_archivo(self, file_id, file_name):
        """Elimina un archivo de B2"""
        try:
            if not self.auth_data:
                return False, "No autenticado"
            
            headers = {"Authorization": self.auth_data['authorizationToken']}
            payload = {
                "fileId": file_id,
                "fileName": file_name
            }
            
            response = requests.post(
                f"{self.auth_data['apiUrl']}/b2api/v2/b2_delete_file_version",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return True, "Archivo eliminado"
            else:
                return False, f"Error al eliminar: {response.text}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def mover_a_archivo(self, file_id, file_name):
        """Mueve un archivo a la carpeta Archivo/"""
        try:
            if not self.auth_data or not self.bucket_id:
                return False, "No autenticado"
            
            # B2 no tiene "mover", se debe copiar y luego eliminar
            # 1. Copiar el archivo con nuevo nombre
            nuevo_nombre = f"Archivo/{file_name}" if not file_name.startswith("Archivo/") else file_name
            
            headers = {"Authorization": self.auth_data['authorizationToken']}
            
            # Copiar archivo
            payload = {
                "sourceFileId": file_id,
                "fileName": nuevo_nombre
            }
            
            response = requests.post(
                f"{self.auth_data['apiUrl']}/b2api/v2/b2_copy_file",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                return False, f"Error al copiar archivo: {response.text}"
            
            # 2. Eliminar el archivo original si no estaba ya en Archivo/
            if not file_name.startswith("Archivo/"):
                success, msg = self.eliminar_archivo(file_id, file_name)
                if not success:
                    return False, f"Archivo copiado pero no se pudo eliminar el original: {msg}"
            
            return True, "Archivo movido a Archivo/"
        except Exception as e:
            return False, f"Error: {e}"
    
    def ejecutar_backup(self):
        """Ejecuta el script de backup de Turso"""
        try:
            script_path = Path(__file__).parent.parent / "scripts" / "backup_turso.py"
            
            if not script_path.exists():
                return False, f"Script de backup no encontrado: {script_path}"
            
            # Ejecutar el script de Python
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            if result.returncode == 0:
                return True, "Backup creado exitosamente"
            else:
                return False, f"Error al crear backup: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Timeout: El backup tardó más de 5 minutos"
        except Exception as e:
            return False, f"Error al ejecutar backup: {e}"
    
    def formatear_tamaño(self, bytes):
        """Convierte bytes a formato legible (KB, MB, GB)"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} PB"
    
    def formatear_fecha(self, timestamp_ms):
        """Convierte timestamp de milisegundos a fecha legible"""
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Fecha desconocida"
