"""
Módulo para consultar el uso de almacenamiento de los servicios en la nube
Obtiene información de Backblaze B2 y Turso
"""

import os
import logging

logger = logging.getLogger(__name__)


def obtener_uso_dropbox(dropbox_client=None):
    """
    Obtiene el uso de almacenamiento de Dropbox.
    
    Args:
        dropbox_client: Cliente de Dropbox ya autenticado (opcional)
    
    Returns:
        dict: {
            'usado_mb': float,
            'total_mb': float,
            'tipo_cuenta': str,
            'error': str (si hay error)
        }
    """
    try:
        # Si no se pasa cliente, intentar crear uno
        if dropbox_client is None:
            try:
                from dropbox_config import DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET
                import dropbox
                
                if not DROPBOX_REFRESH_TOKEN or not DROPBOX_APP_KEY or not DROPBOX_APP_SECRET:
                    logger.warning("Credenciales de Dropbox no configuradas")
                    return {'error': 'No configurado'}
                
                dropbox_client = dropbox.Dropbox(
                    app_key=DROPBOX_APP_KEY,
                    app_secret=DROPBOX_APP_SECRET,
                    oauth2_refresh_token=DROPBOX_REFRESH_TOKEN
                )
            except Exception as e:
                logger.warning(f"No se pudo crear cliente Dropbox: {e}")
                return {'error': 'No disponible'}
        
        # Obtener información de espacio
        space_usage = dropbox_client.users_get_space_usage()
        
        # Calcular usado y total en MB
        usado_bytes = space_usage.used
        total_bytes = space_usage.allocation.get_individual().allocated
        
        usado_mb = usado_bytes / (1024 * 1024)
        total_mb = total_bytes / (1024 * 1024)
        total_gb = total_mb / 1024
        
        # Obtener tipo de cuenta
        account_info = dropbox_client.users_get_current_account()
        account_type = account_info.account_type
        
        # Mapear tipos de cuenta
        tipo_cuenta_map = {
            'basic': 'FREE',
            'pro': 'PRO',
            'business': 'BUSINESS'
        }
        tipo_cuenta = tipo_cuenta_map.get(account_type._tag, account_type._tag.upper())
        
        return {
            'usado_mb': usado_mb,
            'total_mb': total_mb,
            'tipo_cuenta': tipo_cuenta,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo uso de Dropbox: {e}")
        return {'error': str(e)}

'''
# Función obtener_uso_dropbox() eliminada
# Ya no usamos Dropbox, solo Backblaze B2
'''

def obtener_uso_backblaze():
    """
    Obtiene el uso de almacenamiento de Backblaze B2.
    
    Returns:
        dict: {
            'usado_mb': float,
            'total_mb': float,
            'tipo_cuenta': str,
            'error': str (si hay error)
        }
    """
    try:
        import requests
        import base64
        
        b2_key_id = os.getenv("B2_KEY_ID")
        b2_application_key = os.getenv("B2_APPLICATION_KEY")
        
        if not b2_key_id or not b2_application_key:
            logger.warning("Credenciales de Backblaze B2 no configuradas")
            return {'error': 'No configurado'}
        
        # Autenticar con B2
        id_and_key = f"{b2_key_id}:{b2_application_key}"
        basic_auth = base64.b64encode(id_and_key.encode()).decode()
        headers = {"Authorization": f"Basic {basic_auth}"}
        
        response = requests.get("https://api.backblazeb2.com/b2api/v2/b2_authorize_account", 
                                headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Error autenticación B2: {response.status_code}")
            return {'error': 'Error de autenticación'}
        
        auth_data = response.json()
        auth_token = auth_data['authorizationToken']
        api_url = auth_data['apiUrl']
        
        # Obtener información del bucket
        bucket_name = os.getenv("B2_BUCKET_NAME", "gestion-expedientes-app-b2")
        
        headers = {"Authorization": auth_token}
        payload = {
            "accountId": auth_data['accountId'],
            "bucketName": bucket_name
        }
        
        response = requests.post(
            f"{api_url}/b2api/v2/b2_list_buckets",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Error listando buckets B2: {response.status_code}")
            return {'error': 'Error al obtener bucket'}
        
        data = response.json()
        buckets = data.get('buckets', [])
        
        # Buscar nuestro bucket
        bucket_info = None
        for bucket in buckets:
            if bucket['bucketName'] == bucket_name:
                bucket_info = bucket
                break
        
        if not bucket_info:
            logger.warning(f"Bucket {bucket_name} no encontrado")
            return {'error': 'Bucket no encontrado'}
        
        # Nota: B2 no proporciona límite total de la cuenta de forma directa
        # Solo podemos obtener el tamaño usado del bucket
        # Para cuentas gratuitas es 10GB, para pagadas es ilimitado
        
        # Calcular tamaño total del bucket (sumando todos los archivos)
        bucket_id = bucket_info['bucketId']
        archivos_payload = {
            "bucketId": bucket_id,
            "maxFileCount": 10000  # Máximo permitido por llamada
        }
        
        response = requests.post(
            f"{api_url}/b2api/v2/b2_list_file_versions",
            headers=headers,
            json=archivos_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Error listando archivos B2: {response.status_code}")
            return {'error': 'Error al listar archivos'}
        
        files_data = response.json()
        files = files_data.get('files', [])
        
        # Sumar tamaño de todos los archivos
        total_usado_bytes = sum(f.get('contentLength', 0) for f in files)
        usado_mb = total_usado_bytes / (1024 * 1024)
        
        # Límite de cuenta FREE: 10GB
        # Para cuentas de pago no hay límite (usaremos un valor alto para mostrar)
        total_gb = 10  # Valor por defecto para cuenta FREE
        total_mb = total_gb * 1024
        
        # Determinar tipo de cuenta (B2 no lo proporciona directamente)
        # Si están usando más de 10GB, asumimos cuenta de pago
        if usado_mb > (10 * 1024):
            tipo_cuenta = "PAID"
            total_gb = 0  # Ilimitado
            total_mb = 0
        else:
            tipo_cuenta = "FREE"
        
        logger.info(f"Backblaze B2: {usado_mb:.1f}MB / {total_gb}GB ({tipo_cuenta})")
        
        return {
            'usado_mb': usado_mb,
            'total_mb': total_mb if total_mb > 0 else None,  # None = ilimitado
            'tipo_cuenta': tipo_cuenta,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo uso de Backblaze B2: {e}")
        return {'error': str(e)}


def obtener_uso_turso():
    """
    Obtiene el uso de almacenamiento de Turso usando PRAGMA queries.
    Calcula el tamaño multiplicando page_count * page_size.
    
    Returns:
        dict: {
            'usado_mb': float,
            'total_mb': float,
            'tipo_cuenta': str,
            'error': str (si hay error)
        }
    """
    try:
        import requests
        
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")
        
        if not turso_url or not turso_token:
            logger.warning("Turso no configurado")
            return {'error': 'No configurado'}
        
        # Convertir URL a formato HTTPS para la API
        api_url = turso_url.replace("libsql://", "https://").replace("wss://", "https://")
        
        # Obtener page_count y page_size en una sola petición
        # Turso espera formato con "statements" en lugar de "requests"
        request_payload = {
            "statements": [
                "PRAGMA page_count",
                "PRAGMA page_size"
            ]
        }
        
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {turso_token}",
                "Content-Type": "application/json"
            },
            json=request_payload,
            timeout=5
        )
        
        if response.status_code != 200:
            logger.error(f"Error consultando Turso: {response.status_code} - {response.text}")
            return {
                'usado_mb': None,
                'total_mb': 5 * 1024,  # 5GB para plan FREE
                'tipo_cuenta': 'FREE',
                'error': None
            }
        
        data = response.json()
        
        # La respuesta de Turso tiene estructura: [{"results": {...}}, ...]
        if not isinstance(data, list) or len(data) < 2:
            logger.error(f"Respuesta inesperada de Turso")
            return {
                'usado_mb': None,
                'total_mb': 5 * 1024,
                'tipo_cuenta': 'FREE',
                'error': None
            }
        
        # page_count - primer resultado
        page_count_data = data[0]
        
        if isinstance(page_count_data, dict) and "results" in page_count_data:
            results = page_count_data["results"]
            rows = results.get("rows", [])
            if rows and len(rows) > 0 and len(rows[0]) > 0:
                page_count = int(rows[0][0])
            else:
                page_count = 0
        else:
            page_count = 0
        
        # page_size - segundo resultado
        page_size_data = data[1]
        
        if isinstance(page_size_data, dict) and "results" in page_size_data:
            results = page_size_data["results"]
            rows = results.get("rows", [])
            if rows and len(rows) > 0 and len(rows[0]) > 0:
                page_size = int(rows[0][0])
            else:
                page_size = 0
        else:
            page_size = 0
        
        if page_count == 0 or page_size == 0:
            logger.warning(f"Valores inválidos: page_count={page_count}, page_size={page_size}")
            return {
                'usado_mb': None,
                'total_mb': 5 * 1024,
                'tipo_cuenta': 'FREE',
                'error': None
            }
        
        # Calcular tamaño total en bytes
        size_bytes = page_count * page_size
        usado_mb = size_bytes / (1024 * 1024)
        
        logger.info(f"Turso: {usado_mb:.2f}MB usado (page_count={page_count}, page_size={page_size})")
        
        return {
            'usado_mb': usado_mb,
            'total_mb': 5 * 1024,  # 5GB para plan FREE
            'tipo_cuenta': 'FREE',
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo uso de Turso: {e}")
        return {
            'usado_mb': None,
            'total_mb': 5 * 1024,
            'tipo_cuenta': 'FREE',
            'error': None
        }


def obtener_todos_los_usos():
    """
    Obtiene el uso de almacenamiento de todos los servicios.
    
    Returns:
        dict: {
            'backblaze': dict,
            'turso': dict
        }
    """
    logger.info("Consultando uso de almacenamiento de todos los servicios...")
    
    resultado = {
        'backblaze': obtener_uso_backblaze(),
        'turso': obtener_uso_turso()
    }
    
    logger.info("Consulta de almacenamiento completada")
    return resultado
