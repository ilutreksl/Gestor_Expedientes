"""Utilidades para búsqueda y localización de albaranes PDF."""

import os
import re
import glob as glob_module


def extraer_nombre_pdf_desde_albaran(numero_albaran, fmt_usuario, fmt_pdf):
    """
    Extrae las partes variables del número de albarán y construye el nombre del archivo PDF.

    Tokens en fmt_usuario: {Y} (año), {N} (número correlativo)
    Tokens en fmt_pdf:     {Y}, {N}, {N0} (número sin ceros a la izquierda)
    Se permite * en fmt_pdf como comodín para glob.

    Ejemplos:
        numero_albaran='AL26/0007', fmt_usuario='AL{Y}/{N}', fmt_pdf='Albarán 1-AL{Y}-{N0}*.pdf'
        → devuelve 'Albarán 1-AL26-7*.pdf'

        numero_albaran='ALB-2024001', fmt_usuario='ALB-{N}', fmt_pdf='{N}.pdf'
        → devuelve '2024001.pdf'

    Args:
        numero_albaran: Número tal como lo escribe el usuario (ej: 'AL26/0007')
        fmt_usuario: Patrón con tokens {Y}/{N} (ej: 'AL{Y}/{N}')
        fmt_pdf: Patrón del nombre de archivo PDF (ej: 'Albarán 1-AL{Y}-{N0}*.pdf')

    Returns:
        str: Nombre del archivo PDF esperado (puede contener * como comodín glob)

    Raises:
        ValueError: Si los patrones no tienen tokens o el número no coincide
    """
    if not fmt_usuario:
        fmt_usuario = "{N}"
    if not fmt_pdf:
        fmt_pdf = "{N}.pdf"

    # Buscar todos los tokens en fmt_usuario (en orden de aparición)
    tokens_usuario = re.findall(r'\{[A-Za-z0-9]+\}', fmt_usuario)
    if not tokens_usuario:
        raise ValueError(
            "El patrón del número de albarán debe contener al menos un token ({N} o {Y})"
        )

    # Construir regex desde fmt_usuario sustituyendo cada token por un grupo de captura.
    # El último token usa captura codiciosa (.+) para consumir hasta el final;
    # los anteriores usan lazy (.+?) para no "tragarse" los separadores literales.
    regex_str = re.escape(fmt_usuario)
    nombres_token = []
    for i, token in enumerate(tokens_usuario):
        nombre = token[1:-1]  # quitar { y }
        nombres_token.append(nombre)
        escaped = re.escape(token)
        grupo = r'(.+)' if i == len(tokens_usuario) - 1 else r'(.+?)'
        regex_str = regex_str.replace(escaped, grupo, 1)
    regex_str += '$'

    match = re.match(regex_str, numero_albaran, re.IGNORECASE)
    if not match:
        raise ValueError(
            f"El número '{numero_albaran}' no coincide con el patrón '{fmt_usuario}'"
        )

    valores = {nombre: match.group(i + 1) for i, nombre in enumerate(nombres_token)}

    # Construir el nombre del PDF reemplazando tokens conocidos
    nombre_pdf = fmt_pdf
    for nombre, valor in valores.items():
        nombre_pdf = nombre_pdf.replace(f'{{{nombre}}}', valor)

    # {N0}: número sin ceros a la izquierda (derivado de {N})
    if '{N0}' in nombre_pdf:
        if 'N' not in valores:
            raise ValueError(
                "Se usa {N0} en el formato PDF pero no hay {N} en el formato de usuario"
            )
        n_sin_ceros = valores['N'].lstrip('0') or '0'
        nombre_pdf = nombre_pdf.replace('{N0}', n_sin_ceros)

    # Comprobar que no quedan tokens sin resolver
    restantes = re.findall(r'\{[A-Za-z0-9]+\}', nombre_pdf)
    if restantes:
        raise ValueError(
            f"Tokens sin resolver en el formato PDF: {', '.join(restantes)}"
        )

    return nombre_pdf


def buscar_pdf_en_carpeta(carpeta, nombre_archivo):
    """
    Busca un archivo en una carpeta de forma recursiva e insensible a mayúsculas.
    Soporta comodines (* y ?) en nombre_archivo para búsqueda glob.

    Args:
        carpeta: Ruta de la carpeta donde buscar
        nombre_archivo: Nombre del archivo a buscar (puede contener * o ?)

    Returns:
        str|None: Ruta completa del archivo encontrado, o None si no existe
    """
    tiene_comodin = '*' in nombre_archivo or '?' in nombre_archivo

    # Búsqueda con glob (maneja comodines; en Windows es insensible a mayúsculas)
    patron = os.path.join(carpeta, "**", nombre_archivo)
    resultados = glob_module.glob(patron, recursive=True)
    if resultados:
        return resultados[0]

    # Fallback para nombres exactos en sistemas sensibles a mayúsculas (Linux)
    if not tiene_comodin:
        nombre_lower = nombre_archivo.lower()
        for raiz, _, archivos in os.walk(carpeta):
            for archivo in archivos:
                if archivo.lower() == nombre_lower:
                    return os.path.join(raiz, archivo)

    return None
