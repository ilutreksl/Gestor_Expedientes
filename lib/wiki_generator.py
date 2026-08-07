"""Genera la wiki local de ayuda (Guias/wiki/index.html) a partir de los .md de Guias/.

Combina la plantilla, el CSS, marked.js (vendorizado) y el contenido crudo de
MANUAL_USUARIO.md y FUNCIONES_APLICACION.md en un único HTML autocontenido,
que se abre con el navegador por defecto del sistema. Se regenera automáticamente
cuando las fuentes son más recientes que el HTML ya generado.
"""
import os
import json
import datetime

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(_LIB_DIR)
_ASSETS_DIR = os.path.join(_LIB_DIR, "wiki_assets")
_GUIAS_DIR = os.path.join(_BASE_DIR, "Guias")
_OUTPUT_DIR = os.path.join(_GUIAS_DIR, "wiki")
_OUTPUT_PATH = os.path.join(_OUTPUT_DIR, "index.html")

_MANUAL_MD_PATH = os.path.join(_GUIAS_DIR, "MANUAL_USUARIO.md")
_FUNCIONES_MD_PATH = os.path.join(_GUIAS_DIR, "FUNCIONES_APLICACION.md")

_TEMPLATE_PATH = os.path.join(_ASSETS_DIR, "template.html")
_STYLE_PATH = os.path.join(_ASSETS_DIR, "style.css")
_APP_JS_PATH = os.path.join(_ASSETS_DIR, "app.js")
_MARKED_JS_PATH = os.path.join(_ASSETS_DIR, "marked.min.js")

_SOURCE_PATHS = [
    _MANUAL_MD_PATH,
    _FUNCIONES_MD_PATH,
    _TEMPLATE_PATH,
    _STYLE_PATH,
    _APP_JS_PATH,
    _MARKED_JS_PATH,
]


def _leer(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def _necesita_regenerar():
    if not os.path.exists(_OUTPUT_PATH):
        return True
    salida_mtime = os.path.getmtime(_OUTPUT_PATH)
    for ruta in _SOURCE_PATHS:
        if os.path.exists(ruta) and os.path.getmtime(ruta) > salida_mtime:
            return True
    return False


def _generar():
    template = _leer(_TEMPLATE_PATH)
    css = _leer(_STYLE_PATH)
    marked_js = _leer(_MARKED_JS_PATH)
    app_js = _leer(_APP_JS_PATH)
    manual_md = _leer(_MANUAL_MD_PATH)
    funciones_md = _leer(_FUNCIONES_MD_PATH)

    docs = {
        "manual": {"title": "Manual de Usuario", "md": manual_md},
        "funciones": {"title": "Referencia Técnica", "md": funciones_md},
    }
    # Evita que un "</script>" dentro del markdown cierre el <script> que lo embebe.
    docs_json = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")

    generado_en = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    html = template
    html = html.replace("__WIKI_CSS__", css)
    html = html.replace("__WIKI_MARKED_JS__", marked_js)
    html = html.replace("__WIKI_APP_JS__", app_js)
    html = html.replace("__WIKI_DOCS_JSON__", docs_json)
    html = html.replace("__WIKI_GENERATED_AT__", generado_en)

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    return _OUTPUT_PATH


def asegurar_wiki_generada():
    """Genera Guias/wiki/index.html si falta o si las fuentes son más recientes.

    Devuelve la ruta absoluta al index.html listo para abrir.
    """
    if _necesita_regenerar():
        return _generar()
    return _OUTPUT_PATH
