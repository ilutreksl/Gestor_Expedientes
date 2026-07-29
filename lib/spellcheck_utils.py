"""
lib/spellcheck_utils.py
Corrector ortográfico multi-idioma para RichTextEditor.

Usa 'pyspellchecker' (diccionario por frecuencia de palabras, sin dependencias
nativas que instalar en cada equipo). Para español, el diccionario básico que
trae pyspellchecker es muy limitado (no reconoce muchas formas verbales
conjugadas de uso corriente, p.ej. "tiene") y generaba demasiados falsos
positivos, así que se complementa con un diccionario mucho más amplio
(~143.000 palabras) generado a partir de 'wordfreq' (frecuencias de palabras
extraídas de corpus reales) y bundleado en Diccionarios/es_palabras_frecuentes.txt
— no requiere 'wordfreq' en tiempo de ejecución, solo se usó para generar ese
fichero una vez, podando además a propósito las formas sin tilde que en el
corpus real son claramente menos frecuentes que su versión acentuada (para
que errores de tilde comunes, p.ej. "informacion", sí se marquen).

El idioma activo se controla con `set_idioma_ortografia()` (lo llama la app
al iniciar sesión y al guardar los Ajustes de Usuario, según
user_settings["idioma_ortografia"]).

Las palabras que el usuario marque como correctas (nombres de producto,
siglas, marcas...) se guardan en
Diccionarios/diccionario_personalizado_ortografia.json y se respetan entre
sesiones, para todos los idiomas y para todos los usuarios que compartan esa
carpeta (OneDrive).
"""
import json
import re
from pathlib import Path

from lib.logger_config import get_logger

logger = get_logger()

try:
    from spellchecker import SpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False

# Palabras: letras (incluye acentos/ñ) y apóstrofes internos; ignora números y símbolos.
PATRON_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*")

_DICCIONARIOS_DIR = Path(__file__).parent.parent / "Diccionarios"
_DICCIONARIO_PERSONALIZADO_PATH = _DICCIONARIOS_DIR / "diccionario_personalizado_ortografia.json"

# Idiomas que trae pyspellchecker de fábrica. El nombre mostrado es el que
# aparece en el desplegable de Ajustes de Usuario.
IDIOMAS_DISPONIBLES = {
    "es": "Español",
    "en": "Inglés",
    "fr": "Francés",
    "pt": "Portugués",
    "de": "Alemán",
    "it": "Italiano",
    "nl": "Neerlandés",
    "ru": "Ruso",
    "ar": "Árabe",
    "eu": "Euskera",
    "fa": "Persa",
    "lv": "Letón",
}
IDIOMA_POR_DEFECTO = "es"

# Diccionario ampliado propio: solo existe (de momento) para español.
_DICCIONARIOS_AMPLIADOS = {
    "es": _DICCIONARIOS_DIR / "es_palabras_frecuentes.txt",
}

_idioma_actual = IDIOMA_POR_DEFECTO
_spellchecker_cache = {}  # idioma -> SpellChecker


def set_idioma_ortografia(codigo: str):
    """Cambia el idioma activo del corrector.

    Los editores que se abran a partir de este momento revisarán en el nuevo
    idioma. No es necesario reiniciar la aplicación.
    """
    global _idioma_actual
    codigo = (codigo or "").strip().lower()
    if codigo not in IDIOMAS_DISPONIBLES:
        logger.warning(f"Idioma de ortografía '{codigo}' no reconocido; se usa '{IDIOMA_POR_DEFECTO}'.")
        codigo = IDIOMA_POR_DEFECTO
    if codigo != _idioma_actual:
        logger.info(f"Idioma del corrector ortográfico cambiado a '{codigo}' ({IDIOMAS_DISPONIBLES[codigo]}).")
    _idioma_actual = codigo


def get_idioma_ortografia() -> str:
    """Código del idioma activo actualmente (p.ej. 'es')."""
    return _idioma_actual


def _cargar_palabras_personalizadas() -> set:
    if not _DICCIONARIO_PERSONALIZADO_PATH.exists():
        return set()
    try:
        with open(_DICCIONARIO_PERSONALIZADO_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("palabras", []))
    except Exception as e:
        logger.warning(f"No se pudo cargar el diccionario personalizado de ortografía: {e}")
        return set()


def _crear_spellchecker(idioma: str):
    sc = SpellChecker(language=idioma)

    ruta_ampliado = _DICCIONARIOS_AMPLIADOS.get(idioma)
    if ruta_ampliado and ruta_ampliado.exists():
        # Se suma (no sustituye) al diccionario básico de pyspellchecker:
        # load_text_file solo incrementa frecuencias/añade palabras.
        sc.word_frequency.load_text_file(str(ruta_ampliado), encoding='utf-8')
    elif ruta_ampliado:
        logger.warning(
            f"No se encontró el diccionario ampliado de ortografía en {ruta_ampliado}; "
            f"se usará solo el básico de pyspellchecker para '{idioma}'.")

    palabras_custom = _cargar_palabras_personalizadas()
    if palabras_custom:
        sc.word_frequency.load_words(palabras_custom)

    return sc


def get_spellchecker(idioma: str | None = None):
    """Devuelve la instancia del corrector para `idioma` (o el idioma activo
    si no se indica). Se crea una sola vez por idioma y se reutiliza.

    Devuelve None si pyspellchecker no está instalado o si falla la carga
    del diccionario.
    """
    if not SPELLCHECKER_AVAILABLE:
        return None

    idioma = (idioma or _idioma_actual)
    if idioma not in _spellchecker_cache:
        try:
            _spellchecker_cache[idioma] = _crear_spellchecker(idioma)
            logger.info(f"Corrector ortográfico ({idioma}) inicializado correctamente.")
        except Exception as e:
            logger.error(f"No se pudo inicializar el corrector ortográfico ({idioma}): {e}")
            _spellchecker_cache[idioma] = None
    return _spellchecker_cache[idioma]


def añadir_palabra_personalizada(palabra: str):
    """Añade una palabra al diccionario personalizado (persistente, común a
    todos los idiomas) y la incorpora a todos los correctores ya cargados en
    memoria."""
    palabra = (palabra or "").strip()
    if not palabra:
        return
    palabras = _cargar_palabras_personalizadas()
    if palabra.lower() in {p.lower() for p in palabras}:
        return
    palabras.add(palabra)
    try:
        _DICCIONARIO_PERSONALIZADO_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_DICCIONARIO_PERSONALIZADO_PATH, 'w', encoding='utf-8') as f:
            json.dump({"palabras": sorted(palabras)}, f, indent=2, ensure_ascii=False)
        logger.info(f"Palabra añadida al diccionario personalizado de ortografía: '{palabra}'")
    except Exception as e:
        logger.error(f"No se pudo guardar la palabra '{palabra}' en el diccionario personalizado: {e}")

    for sc in _spellchecker_cache.values():
        if sc is not None:
            sc.word_frequency.load_words([palabra])


def detectar_palabras_incorrectas(texto: str):
    """Analiza `texto` y devuelve una lista de tuplas (inicio, fin, palabra)
    con las posiciones (offsets de carácter) de las palabras no reconocidas,
    según el idioma activo. Devuelve [] si el corrector no está disponible.
    """
    sc = get_spellchecker()
    if sc is None or not texto:
        return []

    coincidencias = list(PATRON_PALABRA.finditer(texto))
    if not coincidencias:
        return []

    palabras = [m.group(0) for m in coincidencias]
    # SpellChecker compara en minúsculas internamente; unknown() es la forma
    # rápida de filtrar el conjunto (evita mirar candidates() palabra a palabra).
    desconocidas = sc.unknown(palabras)
    if not desconocidas:
        return []

    desconocidas_lower = {p.lower() for p in desconocidas}
    resultado = []
    for m in coincidencias:
        palabra = m.group(0)
        # Ignorar palabras muy cortas (iniciales, unidades, etc.) para reducir ruido.
        if len(palabra) < 3:
            continue
        if palabra.lower() in desconocidas_lower:
            resultado.append((m.start(), m.end(), palabra))
    return resultado


def obtener_sugerencias(palabra: str, maximo: int = 5):
    """Devuelve hasta `maximo` sugerencias de corrección para `palabra`, con la
    más probable primero (p.ej. para una palabra sin tilde, la corrección de
    pyspellchecker prioriza la misma palabra con la tilde correcta)."""
    sc = get_spellchecker()
    if sc is None:
        return []
    try:
        candidatas = sc.candidates(palabra) or set()
    except Exception:
        return []
    candidatas.discard(palabra.lower())
    if not candidatas:
        return []

    mejor = sc.correction(palabra)
    ordenadas = sorted(candidatas, key=lambda c: sc[c], reverse=True)
    if mejor and mejor in ordenadas:
        ordenadas.remove(mejor)
        ordenadas.insert(0, mejor)
    return ordenadas[:maximo]
