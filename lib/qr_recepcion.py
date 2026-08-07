"""
Generación de QR firmados para el flujo de recepción de paquetes por escaneo.
La URL codificada en el QR incluye una firma HMAC del código de RMA, para que
el Worker de Cloudflare pueda verificar que el QR fue generado por esta
aplicación y no por un tercero que se invente un código de RMA.
"""

import os
import hmac
import hashlib
import tempfile

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

from lib.logger_config import get_logger

logger = get_logger()

_WORKER_URL_ENV = "QR_RECEPCION_WORKER_URL"
_HMAC_SECRET_ENV = "QR_RECEPCION_HMAC_SECRET"

MENSAJE_QRCODE_NO_INSTALADO = (
    "Este ordenador no tiene instalada la librería 'qrcode', necesaria para incluir "
    "el código QR de recepción en el documento de Autorización.\n\n"
    "El documento se generará SIN el QR.\n\n"
    "Avisa a un administrador para que instale la librería con:\n"
    "pip install qrcode[pil]"
)


def qrcode_disponible() -> bool:
    """Indica si la librería qrcode está instalada en este ordenador."""
    return QRCODE_AVAILABLE


def _obtener_secreto() -> str:
    secreto = os.getenv(_HMAC_SECRET_ENV)
    if not secreto:
        raise RuntimeError(
            f"Falta la variable de entorno {_HMAC_SECRET_ENV} — necesaria para firmar "
            "los QR de recepción. Debe coincidir con el secreto HMAC_SECRET configurado "
            "en el Worker de Cloudflare."
        )
    return secreto


def _firmar_codigo_rma(codigo_rma: str) -> str:
    """Firma HMAC-SHA256 del código de RMA, truncada a 32 caracteres hex (128 bits)."""
    secreto = _obtener_secreto()
    firma = hmac.new(secreto.encode("utf-8"), codigo_rma.encode("utf-8"), hashlib.sha256)
    return firma.hexdigest()[:32]


def generar_url_recepcion(codigo_rma: str) -> str:
    """Construye la URL firmada que se codifica en el QR de recepción."""
    worker_url = os.getenv(_WORKER_URL_ENV)
    if not worker_url:
        raise RuntimeError(
            f"Falta la variable de entorno {_WORKER_URL_ENV} — URL del Worker de recepción por QR."
        )
    firma = _firmar_codigo_rma(codigo_rma)
    return f"{worker_url.rstrip('/')}/r?c={codigo_rma}&s={firma}"


def generar_imagen_qr(codigo_rma: str, ruta_destino: str | None = None) -> str:
    """
    Genera la imagen PNG del QR de recepción para el código de RMA dado.
    Si no se indica ruta_destino, se crea un archivo temporal.
    Devuelve la ruta del archivo PNG generado.
    """
    if not QRCODE_AVAILABLE:
        raise RuntimeError(MENSAJE_QRCODE_NO_INSTALADO)

    url = generar_url_recepcion(codigo_rma)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white")

    if not ruta_destino:
        fd, ruta_destino = tempfile.mkstemp(suffix=".png", prefix=f"qr_{codigo_rma}_")
        os.close(fd)

    imagen.save(ruta_destino)
    logger.info(f"QR de recepción generado para {codigo_rma}: {ruta_destino}")
    return ruta_destino
