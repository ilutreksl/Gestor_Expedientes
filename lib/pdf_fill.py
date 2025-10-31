"""Funciones para rellenar plantillas PDF (AcroForm) a partir de datos en SQLite.

Usa pypdf (pip install pypdf) para listar y rellenar campos de formulario.
Esta implementación rellena los campos existentes y deja el PDF con los campos
actualizados (no aplanados). La función principal devuelve la ruta del archivo
generado.
"""
from __future__ import annotations
import sqlite3
import os
from typing import Dict, List, Optional

try:
    from pypdf import PdfReader, PdfWriter
except Exception as e:
    raise ImportError("pypdf no está instalado. Instálalo con: pip install pypdf") from e
from pypdf.generic import NameObject, BooleanObject

# Intento importar pdfrw para un método alternativo de rellenado más robusto
try:
    from pdfrw import PdfReader as PR_PdfReader, PdfWriter as PR_PdfWriter, PdfDict, PdfName
except Exception:
    PR_PdfReader = None
    PR_PdfWriter = None
    PdfDict = None
    PdfName = None
# Intento importar reportlab para generar apariencias (/AP)
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import landscape
    REPORTLAB_AVAILABLE = True
except Exception:
    rl_canvas = None
    REPORTLAB_AVAILABLE = False


def _normalize(name: str) -> str:
    """Normaliza nombres eliminando no-alfa-numéricos y pasando a minúsculas."""
    import re
    return re.sub(r'[^0-9a-z]', '', name.lower()) if name else ''


def get_pdf_field_names(template_path: str) -> List[str]:
    """Devuelve la lista de nombres de campos de formulario (AcroForm) en la plantilla."""
    reader = PdfReader(template_path)
    try:
        fields = reader.get_fields() or {}
        return list(fields.keys())
    except Exception:
        # Fallback: intentar get_form_text_fields si está disponible
        try:
            f = reader.get_form_text_fields() or {}
            return list(f.keys())
        except Exception:
            return []


def _build_field_values_from_db(db_path: str, codigo_rma: str) -> Dict[str, str]:
    """Recupera datos del RMA en la BD y devuelve un dict columna->valor (strings).

    Sólo extrae campos del maestro rma_maestro relevantes para plantillas comunes.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"BD no encontrada: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"No se encontró RMA con código {codigo_rma}")

    # Convertir a dict simple con claves en minúsculas
    data = {k.lower(): ('' if v is None else str(v)) for k, v in dict(row).items()}

    # Mapear nombres alternativos para plantillas (por si el PDF usa campos diferentes)
    aliases = {}
    # Ejemplos: cliente -> cliente, codigo_rma -> codigo_rma, etc.
    for key in list(data.keys()):
        aliases[_normalize(key)] = data[key]

    return aliases


def fill_pdf(template_path: str, output_path: str, field_values: Dict[str, str]) -> None:
    """Rellena un PDF con los pares field_name->value.

    - field_values keys deben corresponder a nombres exactos de campos en el PDF.
    - No aplana el PDF.
    """
    # Preferir pdfrw si está disponible: suele manejar mejor las apariciones de formulario
    if PR_PdfReader is not None:
        # pdfrw approach: set annotation /V and /AP may be left to viewer; set NeedAppearances
        trailer = PR_PdfReader(template_path)
        if not trailer:
            raise ValueError("No se pudo leer la plantilla PDF con pdfrw")

        for page in trailer.pages:
            annotations = page.Annots
            if annotations:
                for annot in annotations:
                    if annot.Subtype == PdfName('Widget') and annot.T:
                        name = str(annot.T)[1:-1] if str(annot.T).startswith('(') else str(annot.T)
                        # Buscar valor por nombre exacto
                        if name in field_values:
                            val = field_values[name]
                        else:
                            # intentar normalizado
                            norm = _normalize(name)
                            # buscar matching por normalized key
                            found = None
                            for k,v in field_values.items():
                                if _normalize(k) == norm:
                                    found = v; break
                            val = found if found is not None else None

                        if val is not None:
                            # Establecer /V y /DV
                            try:
                                annot.update(PdfDict(V='{}'.format(val)))
                                annot.update(PdfDict(DV='{}'.format(val)))
                            except Exception:
                                try:
                                    annot.V = '{}'.format(val)
                                except Exception:
                                    pass
                            # Intentar crear apariencia visible (/AP) si reportlab está disponible
                            try:
                                if REPORTLAB_AVAILABLE:
                                    # Obtener rect y crear appearance con ese tamaño
                                    r = annot.Rect
                                    if r and len(r) >= 4:
                                        try:
                                            # Coordenadas: [llx, lly, urx, ury]
                                            llx, lly, urx, ury = [float(x) for x in r]
                                            width = abs(urx - llx)
                                            height = abs(ury - lly)
                                        except Exception:
                                            width = 200
                                            height = 20
                                    else:
                                        width = 200; height = 20

                                    # Crear pequeño PDF con reportlab que contiene el texto
                                    import tempfile
                                    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                                    tmpf.close()
                                    c = rl_canvas.Canvas(tmpf.name, pagesize=(width, height))
                                    # Ajustar tamaño de fuente según espacio
                                    font_size = 10
                                    try:
                                        c.setFont('Helvetica', font_size)
                                    except Exception:
                                        pass
                                    # Dibujar texto con un pequeño margen
                                    text_x = 2
                                    text_y = height - font_size - 2
                                    c.drawString(text_x, max(0, text_y), str(val))
                                    c.save()

                                    # Leer el PDF generado y extraer XObject
                                    ap_trailer = PR_PdfReader(tmpf.name)
                                    try:
                                        ap_page = ap_trailer.pages[0]
                                        xobj = ap_page.Resources.XObject
                                        if xobj:
                                            # Establecer annot.AP = << /N xobj >>
                                            annot.AP = PdfDict(N=xobj)
                                    except Exception:
                                        pass
                                    finally:
                                        try:
                                            os.unlink(tmpf.name)
                                        except Exception:
                                            pass
                            except Exception:
                                pass

        # Forzar NeedAppearances
        try:
            if trailer.Root is not None:
                if trailer.Root.AcroForm is None:
                    trailer.Root.AcroForm = PdfDict(NeedAppearances=PdfName('true'))
                else:
                    trailer.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName('true')))
        except Exception:
            pass

        PR_PdfWriter().write(output_path, trailer)
        return

    # Fallback a pypdf si pdfrw no está presente
    reader = PdfReader(template_path)
    writer = PdfWriter()

    # Copiar páginas
    for p in reader.pages:
        writer.add_page(p)

    # Rellenar: actualizamos cada página con los valores proporcionados
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, field_values)
        except Exception:
            # Algunas versiones de pypdf requieren pasar la página original del reader;
            # intentamos de todos modos continuar.
            pass

    # Intentar forzar NeedAppearances para mejorar la visualización en algunos visores
    try:
        root = reader.trailer.get("/Root")
        if root and "/AcroForm" in root:
            acro = root["/AcroForm"]
            # Adjuntar el AcroForm original al writer y forzar NeedAppearances
            writer._root_object.update({NameObject("/AcroForm"): acro})
            try:
                writer._root_object[NameObject("/AcroForm")][NameObject("/NeedAppearances")] = BooleanObject(True)
            except Exception:
                # Ignorar si no se puede establecer
                pass
    except Exception:
        pass

    with open(output_path, "wb") as f:
        writer.write(f)


def fill_pdf_for_rma(db_path: str, codigo_rma: str, template_path: str, output_path: str, mapping: Optional[Dict[str, str]] = None,
                     flatten: bool = False, exclude_from_flatten: Optional[List[str]] = None,
                     force_empty_fields: Optional[List[str]] = None,
                     skip_fields: Optional[List[str]] = None) -> str:
    """Construye valores desde la BD y rellena la plantilla, guardando en output_path.

    mapping: opcional dict donde la clave es el nombre del campo PDF (o su forma normalizada)
    y el valor puede ser:
      - 'db:columna_bd' para tomar el valor de la columna en rma_maestro
      - 'val:Texto literal' para un valor fijo
      - 'expr:{col1} - {col2}' para formatear usando columnas del RMA (llaves)

    Devuelve la ruta del archivo generado.
    """
    # 1) Obtener campos normalizados desde la BD
    db_values = _build_field_values_from_db(db_path, codigo_rma)

    # 2) Obtener campos del PDF
    pdf_fields = get_pdf_field_names(template_path)
    mapped_values: Dict[str, str] = {}

    # Normalizar mapping keys for lookup
    norm_mapping: Dict[str, str] = {}
    if mapping:
        for k, v in mapping.items():
            norm_k = _normalize(k)
            norm_mapping[norm_k] = v
            # Also store exact key for direct match
            norm_mapping[k] = v

    # Normalizar skip list
    skip_norm = set(_normalize(x) for x in (skip_fields or []))

    for pf in pdf_fields:
        # Si el campo está en la lista de skip, no lo sobreescribimos (preservar valor de plantilla)
        if skip_fields:
            if pf in skip_fields or _normalize(pf) in skip_norm:
                continue
        pf_norm = _normalize(pf)

        value_to_set: Optional[str] = None

        # A) Si existe mapping explícito para este campo (por nombre exacto o normalizado)
        if mapping:
            if pf in mapping:
                mapval = mapping[pf]
            elif pf_norm in norm_mapping:
                mapval = norm_mapping[pf_norm]
            else:
                mapval = None

            if mapval:
                # Interpretar mapval
                if mapval.startswith('db:'):
                    col = mapval.split(':', 1)[1].strip()
                    val = db_values.get(_normalize(col), '')
                    value_to_set = val
                elif mapval.startswith('val:'):
                    value_to_set = mapval.split(':', 1)[1]
                elif mapval.startswith('expr:'):
                    expr = mapval.split(':', 1)[1]
                    # Reemplazar {col} por su valor
                    try:
                        fmt = expr
                        for dbk, dbv in db_values.items():
                            fmt = fmt.replace('{' + dbk + '}', dbv)
                        value_to_set = fmt
                    except Exception:
                        value_to_set = ''

        # B) Si no hay mapping, intentar mapeo automático por normalización (compatibilidad retro)
        if value_to_set is None:
            if pf_norm in db_values:
                value_to_set = db_values[pf_norm]
            else:
                # Intentar heurística: buscar substring
                for dbk, dbv in db_values.items():
                    if dbk in pf_norm or pf_norm in dbk:
                        value_to_set = dbv
                        break

        if value_to_set is not None:
            mapped_values[pf] = value_to_set

    # 3) Si no hay campos detectados, lanzar excepción para evitar generar PDFs vacíos
    if not mapped_values:
        raise ValueError("No se detectaron coincidencias entre campos del PDF y las fuentes (DB o mapping). Revise el mapeo o los nombres de campos en la plantilla.")

    # 4) Asegurar carpeta destino
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # 5) Rellenar
    # Si se solicita aplanado, rellenamos primero en un archivo temporal y luego aplanamos
    if flatten:
        import tempfile
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmpf.close()
        try:
            fill_pdf(template_path, tmpf.name, mapped_values)
            # Aplanar manteniendo los campos excluidos (si los hay)
            exclude = exclude_from_flatten or []
            flatten_pdf(tmpf.name, output_path, exclude_fields=exclude)
        finally:
            try:
                os.unlink(tmpf.name)
            except Exception:
                pass
    else:
        fill_pdf(template_path, output_path, mapped_values)

    return output_path


def flatten_pdf(input_pdf: str, output_pdf: str, exclude_fields: Optional[List[str]] = None) -> str:
    """Aplana un PDF con campos rellenados: superpone los valores como contenido
    y elimina los campos del formulario, devolviendo la ruta del PDF aplanado.

    exclude_fields: lista de nombres de campos (tal como aparecen en la plantilla) que
    se deben conservar como campos editables (no aplanar).

    Requiere pdfrw y reportlab.
    """
    if PR_PdfReader is None or PR_PdfWriter is None:
        raise ImportError("pdfrw no está disponible; instala pdfrw para aplanar PDFs")
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab no está disponible; instala reportlab para aplanar PDFs")

    trailer = PR_PdfReader(input_pdf)
    if trailer is None:
        raise ValueError("No se pudo leer el PDF de entrada para aplanar")

    import tempfile
    from pdfrw import PageMerge

    # Normalizar lista de exclusión para comparaciones (tolerar mayúsculas/acentos/espacios)
    exclude_norm = set(_normalize(x) for x in (exclude_fields or []))

    for page_number, page in enumerate(trailer.pages):
        annots = page.Annots
        if not annots:
            continue

        # Obtener tamaño de página
        try:
            media = page.MediaBox
            llx = float(media[0]); lly = float(media[1]); urx = float(media[2]); ury = float(media[3])
            page_w = abs(urx - llx); page_h = abs(ury - lly)
        except Exception:
            page_w, page_h = 595, 842  # A4 fallback

        # Crear overlay para la página
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmpf.close()
        try:
            c = rl_canvas.Canvas(tmpf.name, pagesize=(page_w, page_h))
            # Para cada anotación, escribir el valor en la posición del rect
            kept_annots = []
            for annot in annots:
                try:
                    name = annot.T
                    val = annot.V
                    if not name:
                        kept_annots.append(annot)
                        continue
                    name_s = str(name)[1:-1] if str(name).startswith('(') else str(name)
                    name_norm = _normalize(name_s)

                    # Si el campo está en la lista de exclusión, lo mantenemos sin aplanar
                    if name_norm in exclude_norm or name_s in (exclude_fields or []):
                        kept_annots.append(annot)
                        continue

                    if not val:
                        # Sin valor para aplanar
                        continue
                    val_s = str(val)[1:-1] if str(val).startswith('(') else str(val)

                    # rect
                    r = annot.Rect
                    if r and len(r) >= 4:
                        try:
                            rx0, ry0, rx1, ry1 = [float(x) for x in r]
                        except Exception:
                            continue
                        x = rx0 - llx
                        y = ry0 - lly
                    else:
                        x, y = 10, page_h - 20

                    # Ajustar tamaño de fuente simple
                    font_size = 10
                    try:
                        c.setFont('Helvetica', font_size)
                    except Exception:
                        pass
                    # reportlab origin is lower-left; ya estamos usando coordenadas en puntos
                    c.drawString(x + 1, y + 1, val_s)
                except Exception:
                    try:
                        kept_annots.append(annot)
                    except Exception:
                        pass
                    continue
            c.save()

            # Merge overlay onto page
            overlay = PR_PdfReader(tmpf.name)
            if overlay and overlay.pages:
                overlay_page = overlay.pages[0]
                PageMerge(page).add(overlay_page).render()

            # Sustituir la lista de anotaciones por sólo las que queremos conservar
            try:
                if kept_annots:
                    page.Annots = kept_annots
                else:
                    if hasattr(page, 'Annots'):
                        del page.Annots
            except Exception:
                pass
        finally:
            try:
                os.unlink(tmpf.name)
            except Exception:
                pass

    # Después de procesar páginas, filtrar también el listado global de campos en AcroForm
    try:
        acro = trailer.Root.AcroForm
        if acro and hasattr(acro, 'Fields') and acro.Fields:
            new_fields = []
            for f in acro.Fields:
                try:
                    t = f.T
                    if not t:
                        continue
                    t_s = str(t)[1:-1] if str(t).startswith('(') else str(t)
                    if _normalize(t_s) in exclude_norm or t_s in (exclude_fields or []):
                        new_fields.append(f)
                except Exception:
                    # Si no podemos decidir, conservamos
                    new_fields.append(f)
            # Reasignar
            trailer.Root.AcroForm.Fields = new_fields
    except Exception:
        pass

    PR_PdfWriter().write(output_pdf, trailer)
    return output_pdf
