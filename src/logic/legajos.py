import os
import logging
from typing import Dict, List, Any
# pyrefly: ignore [missing-import]
from docx import Document
# pyrefly: ignore [missing-import]
from docx2pdf import convert

# Configuración básica de logging para monitoreo de batch processing
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def _replace_in_paragraphs(paragraphs: List[Any], data: Dict[str, Any]) -> None:
    """
    Función auxiliar para reemplazar texto a nivel de párrafo.
    Resuelve el problema de los marcadores divididos en múltiples 'runs'
    y preserva el formato original del texto (negritas, cursivas, etc.).
    """
    for paragraph in paragraphs:
        p_text = paragraph.text
        # Verificación rápida
        if not any(f"{{{{ {k} }}}}" in p_text or f"{{{{{k}}}}}" in p_text for k in data):
            continue

        # Lista de listas de caracteres para cada run
        run_chars = [list(run.text) for run in paragraph.runs]
        
        for key, value in data.items():
            for placeholder in (f"{{{{ {key} }}}}", f"{{{{{key}}}}}"):
                while True:
                    current_text = "".join("".join(chars) for chars in run_chars)
                    start_idx = current_text.find(placeholder)
                    if start_idx == -1:
                        break
                        
                    # Encontrar en qué run empieza el marcador
                    curr_len = 0
                    run_start = 0
                    char_start = 0
                    for r_idx, chars in enumerate(run_chars):
                        if curr_len <= start_idx < curr_len + len(chars):
                            run_start = r_idx
                            char_start = start_idx - curr_len
                            break
                        curr_len += len(chars)
                        
                    chars_to_remove = len(placeholder)
                    removable_in_start = len(run_chars[run_start]) - char_start
                    
                    if chars_to_remove <= removable_in_start:
                        # El marcador completo está en este run
                        run_chars[run_start][char_start:char_start+chars_to_remove] = list(str(value))
                    else:
                        # El marcador abarca varios runs
                        run_chars[run_start] = run_chars[run_start][:char_start] + list(str(value))
                        chars_to_remove -= removable_in_start
                        
                        r_idx = run_start + 1
                        while chars_to_remove > 0 and r_idx < len(run_chars):
                            removable_in_current = len(run_chars[r_idx])
                            if chars_to_remove >= removable_in_current:
                                run_chars[r_idx] = []
                                chars_to_remove -= removable_in_current
                            else:
                                run_chars[r_idx] = run_chars[r_idx][chars_to_remove:]
                                chars_to_remove = 0
                            r_idx += 1

        # Volcar los caracteres de nuevo a los runs
        for run, chars in zip(paragraph.runs, run_chars):
            run.text = "".join(chars)

def replace_placeholders_in_doc(doc: Document, data: Dict[str, Any]) -> None:
    """
    Reemplaza los marcadores de posición {{ variable }} en un documento Word.

    Itera sobre los párrafos principales y el contenido de todas las tablas,
    delegando el reemplazo a nivel de 'run' para intentar mantener 
    la tipografía y formato original.

    Args:
        doc (Document): Objeto Document de python-docx ya instanciado.
        data (Dict[str, Any]): Diccionario con las claves a buscar y sus valores de reemplazo.

    Raises:
        TypeError: Si los tipos de datos en el diccionario no son convertibles a string.
    """
    # 1. Reemplazo en párrafos del cuerpo principal
    _replace_in_paragraphs(doc.paragraphs, data)

    # 2. Reemplazo recursivo en celdas de todas las tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, data)

def process_document(template_path: str, output_pdf: str, data: Dict[str, Any]) -> None:
    """
    Carga una plantilla, reemplaza las variables estipuladas y
    lo exporta automáticamente a formato .pdf sin guardar el .docx modificado en disco de forma permanente.

    Args:
        template_path (str): Ruta absoluta o relativa al archivo .docx de origen.
        output_pdf (str): Ruta donde se exportará el archivo PDF final.
        data (Dict[str, Any]): Estructura de datos para reemplazar en el documento.

    Raises:
        FileNotFoundError: Si el archivo de la plantilla no existe en la ruta dada.
        RuntimeError: Ante cualquier falla inesperada del motor de conversión docx2pdf.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"No se encontró la plantilla en: {template_path}")

    import tempfile
    
    # Fase 1: Procesamiento del .docx
    try:
        doc = Document(template_path)
        replace_placeholders_in_doc(doc, data)
        
        # Crear un archivo docx temporal
        temp_docx_fd, temp_docx_path = tempfile.mkstemp(suffix=".docx")
        os.close(temp_docx_fd)
        doc.save(temp_docx_path)
    except Exception as e:
        raise RuntimeError(f"Error interno modificando el documento .docx: {e}")

    # Fase 2: Conversión a PDF mediante COM/Word nativo (Windows)
    try:
        # docx2pdf opera de manera óptima con rutas absolutas
        abs_docx = os.path.abspath(temp_docx_path)
        abs_pdf = os.path.abspath(output_pdf)
        convert(abs_docx, abs_pdf)
    except Exception as e:
        raise RuntimeError(f"Error durante la conversión COM a PDF: {e}")
    finally:
        # Limpiar el archivo temporal
        if os.path.exists(temp_docx_path):
            try:
                os.remove(temp_docx_path)
            except OSError:
                pass

def batch_process_documents(template_path: str, output_dir: str, data_list: List[Dict[str, Any]]) -> None:
    """
    Procesa un lote completo de documentos a partir de un iterable de diccionarios, 
    gestionando las excepciones a nivel de iteración para no interrumpir el pipeline.

    Args:
        template_path (str): Ruta a la plantilla de Word original.
        output_dir (str): Directorio de salida para los archivos generados.
        data_list (List[Dict[str, Any]]): Lista de diccionarios (cada registro del DataFrame o JSON).
    
    Raises:
        ValueError: Si la lista de datos proporcionada está vacía.
    """
    if not data_list:
        raise ValueError("El lote de datos a procesar está vacío.")
    
    os.makedirs(output_dir, exist_ok=True)

    for idx, data in enumerate(data_list):
        # Utiliza una clave única si existe, de lo contrario un índice secuencial
        doc_name = str(data.get('id', f"documento_{idx}"))
        out_pdf = os.path.join(output_dir, f"{doc_name}.pdf")
        
        try:
            process_document(template_path, out_pdf, data)
            logging.info(f"Éxito: {doc_name}.pdf generado.")
        except Exception as e:
            logging.error(f"Fallo en {doc_name}: {e}")