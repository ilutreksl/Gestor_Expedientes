"""
Utilidades para el manejo de datos de RMA
"""
from lib.logger_config import get_logger
logger = get_logger()

def obtener_ultima_actividad(fecha_emision, fecha_autorizacion, fecha_recepcion, fecha_proceso, fecha_gestion):
    """
    Determina cuál es la última fecha registrada entre las fechas de actividad del expediente.
    
    Args:
        fecha_emision (str): Fecha de emisión del expediente
        fecha_autorizacion (str): Fecha de autorización
        fecha_recepcion (str): Fecha de recepción
        fecha_proceso (str): Fecha de proceso
        fecha_gestion (str): Fecha de gestión (cierre)
    
    Returns:
        str: Cadena formateada con el prefijo correspondiente y la fecha (ej: "E-2024-12-10")
             Devuelve cadena vacía si no hay ninguna fecha registrada.
    """
    from datetime import datetime
    
    # Orden de prioridad en caso de empate (de mayor a menor prioridad en el flujo del proceso)
    # C (cierre) > P (proceso) > R (recepción) > A (autorización) > E (emisión)
    prioridad = {'C': 5, 'P': 4, 'R': 3, 'A': 2, 'E': 1}
    
    # Diccionario con las fechas y sus prefijos correspondientes
    fechas_actividad = {
        'E': fecha_emision,
        'A': fecha_autorizacion,
        'R': fecha_recepcion,
        'P': fecha_proceso,
        'C': fecha_gestion
    }
    
    # Filtrar solo las fechas válidas (no None, no vacías)
    fechas_validas = {}
    for prefijo, fecha_str in fechas_actividad.items():
        # Convertir None a cadena vacía para manejo consistente
        if fecha_str is None:
            continue
        
        fecha_str = str(fecha_str).strip()
        if not fecha_str or fecha_str.lower() == 'none':
            continue
            
        try:
            # Intentar parsear la fecha para validarla y poder compararla
            # Asumimos formato YYYY-MM-DD o similar
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            fechas_validas[prefijo] = (fecha_obj, fecha_str)
        except ValueError:
            # Si no es formato YYYY-MM-DD, intentar otros formatos comunes
            for formato in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%y', '%d-%m-%y']:
                try:
                    fecha_obj = datetime.strptime(fecha_str, formato)
                    fechas_validas[prefijo] = (fecha_obj, fecha_str)
                    break
                except ValueError:
                    continue
    
    # Si no hay fechas válidas, devolver vacío
    if not fechas_validas:
        return ""
    
    # Encontrar la fecha más reciente, usando prioridad en caso de empate
    # La clave de ordenamiento es: (fecha, prioridad del prefijo)
    prefijo_max = max(fechas_validas.items(), key=lambda x: (x[1][0], prioridad[x[0]]))[0]
    fecha_max_str = fechas_validas[prefijo_max][1]
    
    # Devolver con el formato: PREFIJO-FECHA
    return f"{prefijo_max}-{fecha_max_str}"


def calcular_tiempos_expediente(fecha_emision, fecha_autorizacion, fecha_recepcion, fecha_proceso, fecha_gestion):
    """
    Calcula los tiempos transcurridos entre cada fase del expediente.
    
    Args:
        fecha_emision (str): Fecha de emisión del expediente
        fecha_autorizacion (str): Fecha de autorización
        fecha_recepcion (str): Fecha de recepción
        fecha_proceso (str): Fecha de proceso
        fecha_gestion (str): Fecha de gestión (cierre)
    
    Returns:
        dict: Diccionario con los tiempos calculados:
            - 'dias_total': Días totales desde emisión hasta hoy o hasta cierre
            - 'dias_e_a': Días entre emisión y autorización
            - 'dias_a_r': Días entre autorización y recepción
            - 'dias_r_p': Días entre recepción y proceso
            - 'dias_p_c': Días entre proceso y cierre
            - 'cerrado': Boolean indicando si el expediente está cerrado
    """
    from datetime import datetime
    
    def parsear_fecha(fecha_str):
        """Intenta parsear una fecha en varios formatos."""
        if not fecha_str or fecha_str is None:
            return None
        
        fecha_str = str(fecha_str).strip()
        if not fecha_str or fecha_str.lower() == 'none':
            return None
        
        for formato in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%y', '%d-%m-%y']:
            try:
                return datetime.strptime(fecha_str, formato)
            except ValueError:
                continue
        return None
    
    # Parsear todas las fechas
    f_emision = parsear_fecha(fecha_emision)
    f_autorizacion = parsear_fecha(fecha_autorizacion)
    f_recepcion = parsear_fecha(fecha_recepcion)
    f_proceso = parsear_fecha(fecha_proceso)
    f_gestion = parsear_fecha(fecha_gestion)
    
    resultado = {
        'dias_total': None,
        'dias_e_a': None,
        'dias_a_r': None,
        'dias_r_p': None,
        'dias_p_c': None,
        'cerrado': f_gestion is not None
    }
    
    # Calcular días totales
    if f_emision:
        fecha_fin = f_gestion if f_gestion else datetime.now()
        resultado['dias_total'] = (fecha_fin - f_emision).days
    
    # Calcular tiempos entre fases
    if f_emision and f_autorizacion:
        resultado['dias_e_a'] = (f_autorizacion - f_emision).days
    
    if f_autorizacion and f_recepcion:
        resultado['dias_a_r'] = (f_recepcion - f_autorizacion).days
    
    if f_recepcion and f_proceso:
        resultado['dias_r_p'] = (f_proceso - f_recepcion).days
    
    if f_proceso and f_gestion:
        resultado['dias_p_c'] = (f_gestion - f_proceso).days
    
    return resultado


def obtener_color_tiempo(dias):
    """
    Devuelve un color según los días transcurridos.
    
    Args:
        dias (int): Número de días
    
    Returns:
        str: Color en formato hex o nombre de color
    """
    if dias is None:
        return "gray"
    elif dias < 10:
        return "#22c55e"  # Verde
    elif dias < 20:
        return "#eab308"  # Amarillo
    elif dias < 30:
        return "#f97316"  # Naranja
    else:
        return "#ef4444"  # Rojo


def obtener_promedio_cliente(cliente, conn):
    """
    Calcula el promedio de días de tramitación para un cliente específico.
    
    Args:
        cliente (str): Nombre del cliente
        conn: Conexión a la base de datos
    
    Returns:
        dict: Diccionario con promedios:
            - 'promedio_total': Promedio de días totales
            - 'total_expedientes': Número de expedientes del cliente
            - 'promedio_e_a': Promedio días emisión a autorización
            - 'promedio_a_r': Promedio días autorización a recepción
            - 'promedio_r_p': Promedio días recepción a proceso
            - 'promedio_p_c': Promedio días proceso a cierre
    """
    from datetime import datetime
    
    cursor = conn.cursor()
    
    # Obtener todos los expedientes cerrados del cliente
    cursor.execute("""
        SELECT fecha_emision, fecha_autorizacion, fecha_recepcion, 
               fecha_proceso, fecha_gestion
        FROM rma_maestro
        WHERE cliente = ? AND fecha_gestion IS NOT NULL AND fecha_gestion != ''
    """, (cliente,))
    
    expedientes = cursor.fetchall()
    
    if not expedientes:
        return {
            'promedio_total': None,
            'total_expedientes': 0,
            'promedio_e_a': None,
            'promedio_a_r': None,
            'promedio_r_p': None,
            'promedio_p_c': None
        }
    
    # Calcular tiempos para cada expediente
    tiempos_totales = []
    tiempos_e_a = []
    tiempos_a_r = []
    tiempos_r_p = []
    tiempos_p_c = []
    
    for exp in expedientes:
        tiempos = calcular_tiempos_expediente(*exp)
        
        if tiempos['dias_total'] is not None:
            tiempos_totales.append(tiempos['dias_total'])
        if tiempos['dias_e_a'] is not None:
            tiempos_e_a.append(tiempos['dias_e_a'])
        if tiempos['dias_a_r'] is not None:
            tiempos_a_r.append(tiempos['dias_a_r'])
        if tiempos['dias_r_p'] is not None:
            tiempos_r_p.append(tiempos['dias_r_p'])
        if tiempos['dias_p_c'] is not None:
            tiempos_p_c.append(tiempos['dias_p_c'])
    
    def promedio(lista):
        return sum(lista) / len(lista) if lista else None
    
    return {
        'promedio_total': promedio(tiempos_totales),
        'total_expedientes': len(expedientes),
        'promedio_e_a': promedio(tiempos_e_a),
        'promedio_a_r': promedio(tiempos_a_r),
        'promedio_r_p': promedio(tiempos_r_p),
        'promedio_p_c': promedio(tiempos_p_c)
    }


def descargar_adjunto(ruta_relativa, usar_b2_fn, get_b2_client_fn, normalizar_ruta_b2_fn, b2_root_folder, adjuntos_root_dir):
    """
    Descarga un archivo adjunto y permite al usuario guardarlo donde quiera.
    
    Args:
        ruta_relativa (str): Ruta relativa del archivo
        usar_b2_fn (callable): Función que determina si se usa Backblaze B2
        get_b2_client_fn (callable): Función que retorna el cliente de B2 (tupla b2_api, bucket)
        normalizar_ruta_b2_fn (callable): Función para normalizar rutas de B2
        b2_root_folder (str): Carpeta raíz en B2
        adjuntos_root_dir (str): Directorio raíz de adjuntos local
    
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    import os
    from tkinter import filedialog, messagebox
    from b2sdk.v2.exception import B2Error
    
    logger.info(f"Iniciando descarga de adjunto: {ruta_relativa}")
    
    # Obtener nombre del archivo
    nombre_archivo = os.path.basename(ruta_relativa)
    
    # Preguntar al usuario dónde guardar el archivo
    ruta_destino = filedialog.asksaveasfilename(
        defaultextension=os.path.splitext(nombre_archivo)[1],
        initialfile=nombre_archivo,
        title="Guardar archivo como",
        filetypes=[("Todos los archivos", "*.*")]
    )
    
    if not ruta_destino:
        logger.info("Descarga cancelada por el usuario")
        return False
    
    try:
        if usar_b2_fn():
            # Descargar desde Backblaze B2
            logger.info(f"Descargando archivo desde Backblaze B2: {ruta_relativa}")
            b2_api, bucket = get_b2_client_fn()
            if not b2_api or not bucket:
                logger.error("No se pudo obtener el cliente de Backblaze B2")
                messagebox.showerror("Error", "No se puede conectar con Backblaze B2.")
                return False
            
            # Construir ruta en B2
            ruta_b2 = normalizar_ruta_b2_fn(f"{b2_root_folder}/{ruta_relativa}")
            
            try:
                # Descargar archivo de B2
                downloaded_file = bucket.download_file_by_name(ruta_b2)
                downloaded_file.save_to(ruta_destino)
                
                logger.info(f"Archivo descargado exitosamente desde B2 a: {ruta_destino}")
                messagebox.showinfo("Descarga completa", f"Archivo guardado en:\n{ruta_destino}")
                return True
                
            except B2Error as e:
                logger.error(f"Error descargando archivo desde B2: {e}")
                error_msg = str(e)
                if "not_found" in error_msg.lower() or "file_not_found" in error_msg.lower():
                    messagebox.showerror("Error", f"Archivo no encontrado en Backblaze B2: {ruta_relativa}")
                else:
                    messagebox.showerror("Error", f"Error descargando de Backblaze B2: {e}")
                return False
        else:
            # Copiar desde almacenamiento local
            logger.info(f"Copiando archivo desde almacenamiento local: {ruta_relativa}")
            import shutil
            
            ruta_origen = os.path.join(adjuntos_root_dir, ruta_relativa)
            
            if not os.path.exists(ruta_origen):
                logger.error(f"Archivo no encontrado en almacenamiento local: {ruta_origen}")
                messagebox.showerror("Error", f"Archivo no encontrado: {ruta_origen}")
                return False
            
            # Copiar archivo
            shutil.copy2(ruta_origen, ruta_destino)
            
            logger.info(f"Archivo copiado exitosamente a: {ruta_destino}")
            messagebox.showinfo("Descarga completa", f"Archivo guardado en:\n{ruta_destino}")
            return True
            
    except Exception as e:
        logger.error(f"Error inesperado descargando archivo: {e}")
        messagebox.showerror("Error", f"No se pudo descargar el archivo: {e}")
        return False


def obtener_estados_disponibles():
    """
    Obtiene la lista de estados disponibles para expedientes RMA.
    Excluye 'Completado' (requiere proceso completo) y 'gestion'.
    
    Returns:
        list: Lista de estados disponibles
    """
    estados = [
        "Autorizado",
        "Recibido", 
        "En Proceso"
    ]
    logger.debug(f"Estados disponibles obtenidos: {estados}")
    return estados


def cambiar_estado_expediente(conn, rma_id, nuevo_estado, usuario, fecha=None):
    """
    Cambia el estado de un expediente RMA y registra la fecha correspondiente.
    
    Args:
        conn: Conexión a la base de datos
        rma_id (int): ID del expediente RMA
        nuevo_estado (str): Nuevo estado a aplicar
        usuario (str): Usuario que realiza el cambio
        fecha (str, optional): Fecha del cambio. Si es None, usa la fecha actual.
    
    Returns:
        bool: True si el cambio fue exitoso, False en caso contrario
    """
    from datetime import datetime
    
    if fecha is None:
        fecha = datetime.now().strftime('%Y-%m-%d')
    
    try:
        cursor = conn.cursor()
        
        # Actualizar el estado
        cursor.execute("""
            UPDATE rma_maestro 
            SET estado = ?
            WHERE id = ?
        """, (nuevo_estado, rma_id))
        
        # Actualizar la fecha correspondiente según el estado
        campo_fecha = None
        if nuevo_estado == "Autorizado":
            campo_fecha = "fecha_autorizacion"
            # También actualizar quién autoriza
            cursor.execute("""
                UPDATE rma_maestro 
                SET fecha_autorizacion = ?, autorizado_por = ?
                WHERE id = ?
            """, (fecha, usuario.upper(), rma_id))
        elif nuevo_estado == "Recibido":
            campo_fecha = "fecha_recepcion"
        elif nuevo_estado == "En Proceso":
            campo_fecha = "fecha_proceso"
        elif nuevo_estado == "Completado":
            campo_fecha = "fecha_gestion"
        
        if campo_fecha and nuevo_estado != "Autorizado":
            cursor.execute(f"""
                UPDATE rma_maestro 
                SET {campo_fecha} = ?
                WHERE id = ?
            """, (fecha, rma_id))
        
        conn.commit()
        
        logger.info(f"Estado del expediente RMA ID {rma_id} cambiado a '{nuevo_estado}' por usuario '{usuario}' con fecha {fecha}")
        return True
        
    except Exception as e:
        logger.error(f"Error al cambiar estado del expediente RMA ID {rma_id}: {e}")
        if hasattr(conn, 'rollback'):
            conn.rollback()
        return False
