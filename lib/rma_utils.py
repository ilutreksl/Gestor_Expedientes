"""
Utilidades para el manejo de datos de RMA
"""

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
