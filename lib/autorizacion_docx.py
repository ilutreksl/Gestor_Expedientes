"""
Módulo para generar documentos de autorización en DOCX.
Rellena la plantilla de autorización con datos del expediente.
"""

import os
import logging
from datetime import datetime
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False
    # Intentar con win32com como alternativa (solo Windows)
    try:
        import win32com.client
        WIN32COM_AVAILABLE = True
    except ImportError:
        WIN32COM_AVAILABLE = False

logger = logging.getLogger(__name__)


def generar_autorizacion_docx(
    plantilla_path,
    ruta_destino,
    codigo_rma,
    cliente=None,
    persona_de_contacto=None,
    email_de_contacto=None,
    fecha_emision=None,
    motivo=None,
    observaciones=None,
    fecha_autorizacion=None,
    usar_cuno=False,
    cuno_path=None,
    ruta_firma=None
):
    """
    Genera un documento de autorización en formato DOCX usando python-docx.
    
    Args:
        plantilla_path: Ruta a la plantilla DOCX
        ruta_destino: Ruta donde guardar el documento generado
        codigo_rma: Código del RMA
        cliente: Nombre del cliente
        persona_de_contacto: Persona de contacto
        email_de_contacto: Email de contacto
        fecha_emision: Fecha de emisión del RMA
        motivo: Motivo del RMA
        observaciones: Observaciones adicionales
        fecha_autorizacion: Fecha de autorización
        usar_cuno: Si se debe incluir el cuño
        cuno_path: Ruta al archivo del cuño
        ruta_firma: Ruta al archivo de la firma
    
    Returns:
        bool: True si se generó correctamente, False en caso contrario
    """
    try:
        logger.info(f"Generando documento de autorización para {codigo_rma}")
        
        # Validar que existe la plantilla
        if not os.path.exists(plantilla_path):
            logger.error(f"No se encuentra la plantilla: {plantilla_path}")
            return False
        
        # Si ruta_destino termina en .pdf, cambiarla temporalmente a .docx
        # para el procesamiento DOCX → PDF
        ruta_pdf_final = None
        if ruta_destino.lower().endswith('.pdf'):
            ruta_pdf_final = ruta_destino
            ruta_destino = ruta_destino[:-4] + '.docx'  # Cambiar .pdf por .docx
            logger.info(f"Ruta ajustada para procesamiento: {ruta_destino}")
        
        # Cargar la plantilla
        document = docx.Document(plantilla_path)
        
        # Función auxiliar para convertir fecha a dd/mm/yyyy
        def formato_fecha(fecha_str):
            if not fecha_str:
                return ''
            try:
                # Intentar parsear varios formatos
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        dt = datetime.strptime(fecha_str, fmt)
                        return dt.strftime('%d/%m/%Y')
                    except ValueError:
                        continue
                # Si no se pudo parsear, devolver el original
                return str(fecha_str)
            except:
                return str(fecha_str)
        
        # Preparar el mapeo de marcadores a valores
        mapeo = {
            '[[CODIGO_RMA]]': str(codigo_rma or ''),
            '[[CLIENTE]]': str(cliente or ''),
            '[[PERSONA_CONTACTO]]': str(persona_de_contacto or ''),
            '[[EMAIL_CONTACTO]]': str(email_de_contacto or ''),
            '[[FECHA_EMISION]]': formato_fecha(fecha_emision),
            '[[MOTIVO]]': str(motivo or ''),
            '[[OBSERVACIONES]]': str(observaciones or ''),
            '[[FECHA_AUTORIZACION]]': formato_fecha(fecha_autorizacion or datetime.now().strftime('%Y-%m-%d'))
        }
        
        logger.info(f"Campos a rellenar: {len(mapeo)}")
        for clave, valor in mapeo.items():
            if valor:
                logger.info(f"  {clave} = '{valor}'")
        
        # Función auxiliar para reemplazar texto preservando formato
        def reemplazar_texto_preservando_formato(document, mapeo):
            """Reemplaza texto manteniendo el formato original"""
            
            def reemplazar_en_parrafo(paragraph):
                """Reemplaza marcadores en un párrafo, manejando marcadores divididos en múltiples runs"""
                # Construir el texto completo del párrafo
                texto_completo = ''.join(run.text for run in paragraph.runs)
                
                # Verificar si hay algún marcador en este párrafo
                tiene_marcador = any(clave in texto_completo for clave in mapeo.keys())
                
                if not tiene_marcador:
                    return
                
                # Si hay marcadores, procesar run por run
                for run in paragraph.runs:
                    texto_modificado = run.text
                    for clave, valor in mapeo.items():
                        if clave in texto_modificado:
                            texto_modificado = texto_modificado.replace(clave, valor)
                    run.text = texto_modificado
                
                # Manejo especial: si un marcador está dividido en múltiples runs
                # Reconstruir el párrafo combinando runs
                texto_completo = ''.join(run.text for run in paragraph.runs)
                for clave, valor in mapeo.items():
                    if clave in texto_completo and not any(clave in run.text for run in paragraph.runs):
                        # El marcador está dividido entre runs
                        # Limpiar todos los runs y poner el texto en el primero
                        texto_reemplazado = texto_completo.replace(clave, valor)
                        if paragraph.runs:
                            paragraph.runs[0].text = texto_reemplazado
                            # Eliminar el texto de los demás runs
                            for run in paragraph.runs[1:]:
                                run.text = ''
                        break
            
            # Reemplazar en párrafos
            for paragraph in document.paragraphs:
                reemplazar_en_parrafo(paragraph)
            
            # Reemplazar en tablas
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            reemplazar_en_parrafo(paragraph)
        
        # Aplicar reemplazos
        reemplazar_texto_preservando_formato(document, mapeo)
        logger.info("Texto reemplazado en el documento")
        
        # Añadir imágenes si están disponibles
        # Usar posicionamiento absoluto para que no desplacen el texto
        firma_agregada = False
        cuno_agregado = False
        
        # Buscar párrafo con marcador [[FIRMAS]] o [[IMAGENES]]
        parrafo_firmas = None
        for paragraph in document.paragraphs:
            texto = paragraph.text
            if '[[FIRMAS]]' in texto or '[[IMAGENES]]' in texto:
                parrafo_firmas = paragraph
                # Limpiar el marcador pero mantener el párrafo
                for run in paragraph.runs:
                    run.text = run.text.replace('[[FIRMAS]]', '').replace('[[IMAGENES]]', '')
                break
        
        # Si no encontramos el marcador, usar el último párrafo
        if parrafo_firmas is None and ((usar_cuno and cuno_path and os.path.exists(cuno_path)) or (ruta_firma and os.path.exists(ruta_firma))):
            parrafo_firmas = document.add_paragraph()
        
        # Si hay imágenes para añadir
        if parrafo_firmas and ((usar_cuno and cuno_path and os.path.exists(cuno_path)) or (ruta_firma and os.path.exists(ruta_firma))):
            # Añadir un run vacío para poder insertar las imágenes flotantes
            run_contenedor = parrafo_firmas.add_run()
            
            # Posiciones absolutas desde la esquina inferior derecha de la página
            # En EMUs (English Metric Units): 914400 EMU = 1 pulgada
            margen_derecha = 914400 * 1.0  # 1 pulgada desde la derecha
            y_inicial = 914400 * 2.5  # Posición Y inicial (desde arriba)
            
            # Añadir cuño si se solicita
            if usar_cuno and cuno_path and os.path.exists(cuno_path):
                try:
                    # Añadir imagen como inline primero
                    picture = run_contenedor.add_picture(cuno_path, width=Inches(1.5))
                    
                    # Obtener el elemento inline de la imagen
                    inline = picture._inline
                    
                    # Convertir a anchor (flotante) y posicionar
                    from docx.oxml import parse_xml
                    
                    # Eliminar el inline
                    parent = inline.getparent()
                    anchor_xml = f'''
                    <wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                               xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
                               distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="251658240"
                               behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
                        <wp:simplePos x="0" y="0"/>
                        <wp:positionH relativeFrom="page">
                            <wp:align>right</wp:align>
                        </wp:positionH>
                        <wp:positionV relativeFrom="page">
                            <wp:posOffset>{int(y_inicial)}</wp:posOffset>
                        </wp:positionV>
                        <wp:extent cx="{inline.extent.cx}" cy="{inline.extent.cy}"/>
                        <wp:effectExtent l="0" t="0" r="0" b="0"/>
                        <wp:wrapNone/>
                        <wp:docPr id="{inline.docPr.id}" name="{inline.docPr.name}"/>
                        {inline.graphic.xml}
                    </wp:anchor>
                    '''
                    anchor = parse_xml(anchor_xml)
                    parent.replace(inline, anchor)
                    
                    cuno_agregado = True
                    logger.info(f"Cuño añadido al documento (flotante)")
                except Exception as e:
                    logger.error(f"Error al añadir cuño: {e}")
            
            # Añadir firma si se proporciona
            if ruta_firma and os.path.exists(ruta_firma):
                try:
                    # Calcular posición Y para la firma (debajo del cuño)
                    y_firma = y_inicial + (914400 * 0.8)  # 0.8 pulgadas más abajo
                    
                    # Añadir imagen como inline primero
                    picture = run_contenedor.add_picture(ruta_firma, width=Inches(1.5))
                    
                    # Obtener el elemento inline de la imagen
                    inline = picture._inline
                    
                    # Convertir a anchor (flotante) y posicionar
                    from docx.oxml import parse_xml
                    
                    # Eliminar el inline
                    parent = inline.getparent()
                    anchor_xml = f'''
                    <wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                               xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
                               distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="251658241"
                               behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
                        <wp:simplePos x="0" y="0"/>
                        <wp:positionH relativeFrom="page">
                            <wp:align>right</wp:align>
                        </wp:positionH>
                        <wp:positionV relativeFrom="page">
                            <wp:posOffset>{int(y_firma)}</wp:posOffset>
                        </wp:positionV>
                        <wp:extent cx="{inline.extent.cx}" cy="{inline.extent.cy}"/>
                        <wp:effectExtent l="0" t="0" r="0" b="0"/>
                        <wp:wrapNone/>
                        <wp:docPr id="{inline.docPr.id}" name="{inline.docPr.name}"/>
                        {inline.graphic.xml}
                    </wp:anchor>
                    '''
                    anchor = parse_xml(anchor_xml)
                    parent.replace(inline, anchor)
                    
                    firma_agregada = True
                    logger.info(f"Firma añadida al documento (flotante)")
                except Exception as e:
                    logger.error(f"Error al añadir firma: {e}")
        
        # Guardar el documento DOCX temporalmente
        document.save(ruta_destino)
        logger.info(f"Documento DOCX generado: {ruta_destino}")
        
        # Si se especificó PDF como destino final, convertir
        if ruta_pdf_final:
            ruta_pdf = ruta_pdf_final
        else:
            # Si no se especificó, asumir que queremos PDF
            ruta_pdf = ruta_destino.replace('.docx', '.pdf')
        
        # Convertir a PDF
        try:
            if DOCX2PDF_AVAILABLE:
                # Método 1: docx2pdf (más simple)
                docx2pdf_convert(ruta_destino, ruta_pdf)
                logger.info(f"Convertido a PDF con docx2pdf: {ruta_pdf}")
            elif WIN32COM_AVAILABLE:
                # Método 2: win32com (solo Windows, requiere Word instalado)
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = False
                doc = word.Documents.Open(os.path.abspath(ruta_destino))
                doc.SaveAs(os.path.abspath(ruta_pdf), FileFormat=17)  # 17 = wdFormatPDF
                doc.Close()
                word.Quit()
                logger.info(f"Convertido a PDF con win32com: {ruta_pdf}")
            else:
                logger.warning("No hay herramienta de conversión a PDF disponible. Se guardará como DOCX.")
                # No hacer nada, mantener el DOCX
                return True
            
            # Eliminar el DOCX temporal
            try:
                os.remove(ruta_destino)
                logger.info(f"DOCX temporal eliminado")
            except Exception as e:
                logger.warning(f"No se pudo eliminar DOCX temporal: {e}")
            
            logger.info(f"Documento de autorización PDF generado: {ruta_pdf}")
            return True
            
        except Exception as e:
            logger.error(f"Error al convertir a PDF: {e}", exc_info=True)
            # Si falla la conversión, mantener el DOCX
            logger.warning("Se mantendrá el archivo DOCX")
            return True
        
    except Exception as e:
        logger.error(f"Error al generar documento de autorización: {e}", exc_info=True)
        return False
