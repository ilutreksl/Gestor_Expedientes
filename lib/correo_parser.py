"""Extracción de asunto/remitente/fecha/cuerpo de archivos de correo (.eml y .msg).

No requiere conexión a Office 365 ni a ningún servidor de correo: parsea
directamente el archivo exportado por el usuario desde su cliente de correo.

El recorte de firma (busca marcadores habituales como "--", "Saludos,",
"Enviado desde mi iPhone", etc.) y la división en hilo (dividir_hilo, busca
marcadores de respuesta/reenvío citado tipo "El... escribió:" o bloques
De:/Enviado:/Para:/Asunto:) son heurísticos y no son 100% fiables, por lo que
el cuerpo extraído debe revisarse/editarse antes de guardarlo definitivamente.
"""
import os
import re
import email
import email.utils
import email.policy
import html as html_module

logger = None
try:
    from lib.logger_config import get_logger
    logger = get_logger()
except Exception:
    pass

EXTENSIONES_SOPORTADAS = ('.eml', '.msg')

_MARCADORES_FIRMA = [
    r'^--\s*$',
    r'^_{5,}$',
    r'^-{5,}$',
    r'^\s*(saludos|un saludo|atentamente|cordialmente|reciba un cordial saludo)\s*,?\s*$',
    r'^\s*(best regards|kind regards|regards|sincerely|thanks|thank you)\s*,?\s*$',
    r'^enviado desde mi (iphone|ipad|android|dispositivo)',
    r'^sent from my (iphone|ipad|android|device)',
    r'^get outlook for',
]
_MARCADORES_FIRMA_RE = [re.compile(p, re.IGNORECASE) for p in _MARCADORES_FIRMA]


# --- División de un cuerpo en los mensajes individuales de un hilo -------
#
# Un .eml/.msg no guarda varios correos por separado: el correo más reciente
# lleva pegados los anteriores como texto citado, precedido de un marcador
# típico de cliente de correo. Estos patrones cubren los formatos más
# habituales (Gmail/Outlook, español e inglés); es heurístico y, si no
# reconoce el formato, simplemente no divide el texto.

_PATRON_EL_ESCRIBIO = re.compile(
    r'^[\s>]*(?:El\s+(?P<fecha1>.+),\s*(?P<remitente1>.+?)\s+escribió\s*:'
    r'|On\s+(?P<fecha2>.+),\s*(?P<remitente2>.+?)\s+wrote\s*:)\s*$',
    re.IGNORECASE
)
_PATRON_SEPARADOR_ORIGINAL = re.compile(
    r'^[\s>]*-{2,}\s*(mensaje original|original message|forwarded message|mensaje reenviado)\s*-{2,}\s*$',
    re.IGNORECASE
)
_PATRON_DE = re.compile(r'^[\s>]*(?:De|From)\s*:\s*(?P<valor>.+)$', re.IGNORECASE)
_PATRON_ENVIADO = re.compile(r'^[\s>]*(?:Enviado|Sent|Fecha|Date)\s*:\s*(?P<valor>.+)$', re.IGNORECASE)
_PATRON_PARA = re.compile(r'^[\s>]*(?:Para|To)\s*:\s*(?P<valor>.+)$', re.IGNORECASE)
_PATRON_ASUNTO = re.compile(r'^[\s>]*(?:Asunto|Subject)\s*:\s*(?P<valor>.+)$', re.IGNORECASE)


def _quitar_prefijo_cita(texto: str) -> str:
    """Quita el prefijo '>' de citado clásico de texto plano, línea a línea."""
    lineas = [re.sub(r'^\s*>+\s?', '', l) for l in texto.splitlines()]
    return '\n'.join(lineas).strip()


def _detectar_bloque_metadatos(lineas, inicio) -> tuple:
    """Busca un bloque De:/Enviado:/Para:/Asunto: a partir de `inicio`.

    Devuelve (num_lineas_consumidas, remitente, fecha). Si no encuentra nada,
    devuelve (0, None, None).
    """
    remitente = None
    fecha = None
    vistos = set()
    j = inicio
    limite = min(len(lineas), inicio + 6)
    while j < limite:
        linea = lineas[j]
        if not linea.strip():
            j += 1
            continue
        m_de = _PATRON_DE.match(linea)
        m_env = _PATRON_ENVIADO.match(linea)
        m_para = _PATRON_PARA.match(linea)
        m_asu = _PATRON_ASUNTO.match(linea)
        if m_de and 'de' not in vistos:
            remitente = m_de.group('valor').strip()
            vistos.add('de')
        elif m_env and 'enviado' not in vistos:
            fecha = m_env.group('valor').strip()
            vistos.add('enviado')
        elif m_para and 'para' not in vistos:
            vistos.add('para')
        elif m_asu and 'asunto' not in vistos:
            vistos.add('asunto')
        else:
            break
        j += 1

    consumidas = j - inicio
    return (consumidas, remitente, fecha) if vistos else (0, None, None)


def _encontrar_fronteras(lineas) -> list:
    """Localiza, dentro de una lista de líneas, los puntos donde empieza cada
    mensaje citado/reenviado anterior (marcador "El... escribió:"/"On... wrote:",
    separador "-----Mensaje original-----" o bloque De:/Enviado:/Para:/Asunto:).

    Devuelve una lista de tuplas (indice_inicio, num_lineas_marcador, remitente, fecha).
    """
    n = len(lineas)
    fronteras = []

    i = 0
    while i < n:
        linea = lineas[i]

        m = _PATRON_EL_ESCRIBIO.match(linea)
        if m:
            remitente = (m.group('remitente1') or m.group('remitente2') or '').strip()
            fecha = (m.group('fecha1') or m.group('fecha2') or '').strip()
            fronteras.append((i, 1, remitente, _normalizar_fecha(fecha)))
            i += 1
            continue

        num_separador = 1 if _PATRON_SEPARADOR_ORIGINAL.match(linea) else 0
        consumidas_meta, remitente_meta, fecha_meta = _detectar_bloque_metadatos(lineas, i + num_separador)

        if num_separador or consumidas_meta:
            total = num_separador + consumidas_meta
            fronteras.append((i, total, remitente_meta or '', _normalizar_fecha(fecha_meta) if fecha_meta else ''))
            i += max(total, 1)
            continue

        i += 1

    return fronteras


def _recortar_firma(texto: str) -> str:
    """Recorta heurísticamente la firma del mensaje actual (saludo final, "--",
    "Enviado desde mi iPhone", etc.).

    Solo busca dentro del texto del propio mensaje: si el cuerpo contiene un
    hilo citado (ver dividir_hilo), ese hilo se deja intacto a partir de su
    marcador para poder reconstruirlo después, en vez de tratarlo como firma.
    """
    if not texto:
        return texto

    lineas = texto.splitlines()
    n = len(lineas)
    if n < 2:
        return texto.rstrip()

    fronteras = _encontrar_fronteras(lineas)
    limite = fronteras[0][0] if fronteras else n

    for i in range(0, limite):
        linea = lineas[i].strip()
        if not linea:
            continue
        for patron in _MARCADORES_FIRMA_RE:
            if patron.match(linea):
                inicio_recortado = '\n'.join(lineas[:i]).rstrip()
                resto_hilo = '\n'.join(lineas[limite:]).rstrip()
                if inicio_recortado and resto_hilo:
                    return f"{inicio_recortado}\n\n{resto_hilo}"
                return inicio_recortado if inicio_recortado else (resto_hilo if resto_hilo else texto.rstrip())

    return texto.rstrip()


def dividir_hilo(texto: str) -> list:
    """Divide el cuerpo de un correo en los mensajes individuales de un hilo.

    Devuelve una lista de dicts {'remitente', 'fecha', 'texto'} en el mismo
    orden en que aparecen en el archivo (normalmente el más reciente primero,
    seguido de las respuestas/reenvíos anteriores citados). El primer elemento
    corresponde siempre al propio correo (su remitente/fecha ya se conocen por
    las cabeceras del archivo, no por el texto, así que se devuelven vacíos).

    Si no se detecta ningún marcador de cita/reenvío reconocible, devuelve una
    lista con un único mensaje (el texto completo, sin dividir).
    """
    if not texto or not texto.strip():
        return []

    lineas = texto.splitlines()
    n = len(lineas)
    fronteras = _encontrar_fronteras(lineas)

    if not fronteras:
        # Sin marcadores reconocibles: intentar solo el caso simple de cita
        # clásica con '>' al principio de línea (respuesta simple sin cabecera).
        for idx, linea in enumerate(lineas):
            if linea.lstrip().startswith('>'):
                texto_actual = '\n'.join(lineas[:idx]).strip()
                texto_citado = _quitar_prefijo_cita('\n'.join(lineas[idx:]))
                mensajes = []
                if texto_actual:
                    mensajes.append({'remitente': '', 'fecha': '', 'texto': texto_actual})
                if texto_citado:
                    mensajes.append({'remitente': '', 'fecha': '', 'texto': texto_citado})
                return mensajes if mensajes else [{'remitente': '', 'fecha': '', 'texto': texto.strip()}]
        return [{'remitente': '', 'fecha': '', 'texto': texto.strip()}]

    mensajes = []
    primer_fin = fronteras[0][0]
    texto_primero = '\n'.join(lineas[:primer_fin]).strip()
    mensajes.append({'remitente': '', 'fecha': '', 'texto': texto_primero})

    for idx, (inicio, num_marcador, remitente, fecha) in enumerate(fronteras):
        inicio_contenido = inicio + num_marcador
        fin_contenido = fronteras[idx + 1][0] if idx + 1 < len(fronteras) else n
        texto_segmento = _quitar_prefijo_cita('\n'.join(lineas[inicio_contenido:fin_contenido]))
        mensajes.append({'remitente': remitente, 'fecha': fecha, 'texto': texto_segmento})

    # Descartar segmentos vacíos (p.ej. una cabecera sin texto real detrás)
    return [m for m in mensajes if m['texto']]


def _html_a_texto(html_contenido: str) -> str:
    """Conversión mínima de HTML a texto plano (sin dependencias externas)."""
    texto = re.sub(r'(?is)<(script|style).*?>.*?</\1>', '', html_contenido)
    texto = re.sub(r'(?i)<br\s*/?>', '\n', texto)
    texto = re.sub(r'(?i)</p>', '\n\n', texto)
    texto = re.sub(r'(?is)<[^>]+>', '', texto)
    texto = html_module.unescape(texto)
    # Colapsar líneas en blanco excesivas
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


def _normalizar_fecha(valor) -> str:
    if not valor:
        return ''
    if isinstance(valor, str):
        try:
            dt = email.utils.parsedate_to_datetime(valor)
            if dt is not None:
                return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            pass
        return valor.strip()
    try:
        return valor.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(valor)


def parsear_eml(filepath: str) -> dict:
    """Extrae asunto/remitente/fecha/cuerpo de un archivo .eml (formato MIME estándar)."""
    with open(filepath, 'rb') as f:
        mensaje = email.message_from_binary_file(f, policy=email.policy.default)

    asunto = str(mensaje.get('subject', '') or '')
    remitente = str(mensaje.get('from', '') or '')
    fecha = _normalizar_fecha(mensaje.get('date', ''))

    cuerpo_texto = None
    cuerpo_html = None

    if mensaje.is_multipart():
        for parte in mensaje.walk():
            if parte.is_attachment():
                continue
            tipo = parte.get_content_type()
            if tipo == 'text/plain' and cuerpo_texto is None:
                cuerpo_texto = parte.get_content()
            elif tipo == 'text/html' and cuerpo_html is None:
                cuerpo_html = parte.get_content()
    else:
        tipo = mensaje.get_content_type()
        if tipo == 'text/plain':
            cuerpo_texto = mensaje.get_content()
        elif tipo == 'text/html':
            cuerpo_html = mensaje.get_content()

    if cuerpo_texto is not None:
        cuerpo_bruto = cuerpo_texto
    elif cuerpo_html is not None:
        cuerpo_bruto = _html_a_texto(cuerpo_html)
    else:
        cuerpo_bruto = ''

    return {
        'asunto': asunto.strip(),
        'remitente': remitente.strip(),
        'fecha': fecha,
        'cuerpo_completo': cuerpo_bruto.strip(),
        'cuerpo_sin_firma': _recortar_firma(cuerpo_bruto),
    }


def parsear_msg(filepath: str) -> dict:
    """Extrae asunto/remitente/fecha/cuerpo de un archivo .msg (formato nativo de Outlook).

    Requiere la librería 'extract-msg' (pip install extract-msg).
    """
    try:
        import extract_msg
    except ImportError as e:
        raise ImportError(
            "Falta la librería 'extract-msg' para leer archivos .msg de Outlook.\n"
            "Instálala con: pip install extract-msg"
        ) from e

    mensaje = extract_msg.Message(filepath)
    try:
        asunto = mensaje.subject or ''
        remitente = mensaje.sender or ''
        fecha = _normalizar_fecha(mensaje.date)

        cuerpo_bruto = mensaje.body or ''
        if not cuerpo_bruto.strip():
            html_body = getattr(mensaje, 'htmlBody', None)
            if html_body:
                if isinstance(html_body, bytes):
                    html_body = html_body.decode('utf-8', errors='ignore')
                cuerpo_bruto = _html_a_texto(html_body)

        return {
            'asunto': asunto.strip(),
            'remitente': remitente.strip(),
            'fecha': fecha,
            'cuerpo_completo': cuerpo_bruto.strip(),
            'cuerpo_sin_firma': _recortar_firma(cuerpo_bruto),
        }
    finally:
        try:
            mensaje.close()
        except Exception:
            pass


def parsear_correo_archivo(filepath: str) -> dict:
    """Despacha al parser adecuado según la extensión del archivo (.eml o .msg)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.eml':
        return parsear_eml(filepath)
    elif ext == '.msg':
        return parsear_msg(filepath)
    else:
        raise ValueError(f"Formato de correo no soportado: '{ext}'. Solo se admiten .eml y .msg")
