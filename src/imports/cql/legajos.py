import os
import re
import shutil
import pandas as pd

from sqlalchemy.orm import Session

# Importamos los modelos y la conexión tal como en la API
from src.database import get_db, Credito, Transferencia
from src.database.models import DocumentoLegajo, EstadoCredito

def mapear_legajos_a_clave_externa(cql_data) -> pd.DataFrame:
    """
    Lee los archivos PDF en legajos_path, extrae el ID del nombre del archivo,
    y lo cruza con el índice de df_inventario para obtener la Clave Externa.
    """
    legajos_path = cql_data.legajos_path
    df_inventario = cql_data.df_inventario[["Clave Externa"]].copy()
    
    resultados = []
    
    # Verificamos que la carpeta exista
    if not os.path.exists(legajos_path):
        print(f"La ruta no existe: {legajos_path}")
        return pd.DataFrame()

    # Recorremos todos los archivos en la carpeta
    for filename in os.listdir(legajos_path):
        if filename.lower().endswith('.pdf'):
            # Verificamos si es el formato exportado por el sistema: "Legajo Nro. {id_interno} - ..."
            match_legajo_nro = re.match(r'^Legajo Nro\.?\s+(\d+)\s+-', filename, re.IGNORECASE)
            if match_legajo_nro:
                id_vendedor = match_legajo_nro.group(1)
                resultados.append({
                    "archivo_pdf": filename,
                    "ruta_completa": os.path.join(legajos_path, filename),
                    "id_inventario": id_vendedor,
                    "clave_externa": id_vendedor
                })
                continue

            # Dividimos el nombre por el guion para extraer la primera parte
            partes = filename.split('-')
            if len(partes) > 0:
                id_str = partes[0].strip()
                
                try:
                    # Convertimos a entero para quitar ceros a la izquierda (ej. "012998" -> 12998)
                    # Esto asume que el índice de tu df_inventario es de tipo int.
                    id_num = int(id_str)
                    
                    # Buscamos si el ID existe en el índice del DataFrame
                    if id_num in df_inventario.index:
                        clave_externa = df_inventario.loc[id_num, "Clave Externa"]
                        resultados.append({
                            "archivo_pdf": filename,
                            "ruta_completa": os.path.join(legajos_path, filename),
                            "id_inventario": id_num,
                            "clave_externa": clave_externa
                        })
                    else:
                        # Por si el índice del DataFrame está como string (ej. "12998" o "012998")
                        if id_str in df_inventario.index:
                            clave_externa = df_inventario.loc[id_str, "Clave Externa"]
                            resultados.append({
                                "archivo_pdf": filename,
                                "ruta_completa": os.path.join(legajos_path, filename),
                                "id_inventario": id_str,
                                "clave_externa": clave_externa
                            })
                        elif str(id_num) in df_inventario.index:
                            clave_externa = df_inventario.loc[str(id_num), "Clave Externa"]
                            resultados.append({
                                "archivo_pdf": filename,
                                "ruta_completa": os.path.join(legajos_path, filename),
                                "id_inventario": str(id_num),
                                "clave_externa": clave_externa
                            })
                except ValueError:
                    # Si la primera parte no es un número, lo ignoramos o lo notificamos
                    pass
                    
    # Convertimos la lista de resultados a un DataFrame para que sea fácil de trabajar
    return pd.DataFrame(resultados)


def mapear_comprobantes_a_clave_externa(cql_data) -> pd.DataFrame:
    """
    Lee los comprobantes de transferencias, extrae el ID numérico del inicio del archivo,
    captura la información de transferencia (ej: "1 de 3", "02") y cruza con df_inventario.
    """
    comprobantes_path = cql_data.comprobantes_path
    df_inventario = cql_data.df_inventario[["Clave Externa"]].copy()
    
    resultados = []
    
    if not os.path.exists(comprobantes_path):
        print(f"La ruta no existe: {comprobantes_path}")
        return pd.DataFrame()

    # PATRONES REGEX
    # 1. ^(\d+) -> Busca al inicio (^) del string uno o más dígitos (\d+)
    patron_id = re.compile(r'^(\d+)')
    
    # 2. [-\s]+(\d+(?:\s*de\s*\d+)?)\.pdf$ -> Busca antes del ".pdf" al final del texto ($) 
    #    cualquier guion o espacio seguido de números, y opcionalmente un " de X"
    patron_transferencia = re.compile(r'[-\s]+(\d+(?:\s*de\s*\d+)?)\.pdf$', re.IGNORECASE)

    for filename in os.listdir(comprobantes_path):
        if filename.lower().endswith('.pdf'):
            
            # Buscar el ID al principio del nombre
            match_id = patron_id.search(filename)
            
            if match_id:
                # El grupo 1 es el número capturado (ej. "010945" o "4422")
                id_str = match_id.group(1)
                
                # Intentar extraer también el detalle de la transferencia (1, 02, 1 de 3)
                match_trans = patron_transferencia.search(filename)
                info_transferencia = match_trans.group(1) if match_trans else "1" # Por defecto "1" si no dice nada
                
                try:
                    # Convertimos a entero para cruzar numéricamente
                    id_num = int(id_str)
                    
                    # Variables que guardaremos
                    archivo_info = {
                        "archivo_pdf": filename,
                        "ruta_completa": os.path.join(comprobantes_path, filename),
                        "info_transferencia": info_transferencia
                    }
                    
                    # Verificamos cruce con el índice
                    if id_num in df_inventario.index:
                        clave_externa = df_inventario.loc[id_num, "Clave Externa"]
                        archivo_info["id_inventario"] = id_num
                        archivo_info["clave_externa"] = clave_externa
                        resultados.append(archivo_info)
                        
                    # Alternativas por si tu índice fuera de tipo string
                    elif id_str in df_inventario.index:
                        clave_externa = df_inventario.loc[id_str, "Clave Externa"]
                        archivo_info["id_inventario"] = id_str
                        archivo_info["clave_externa"] = clave_externa
                        resultados.append(archivo_info)
                        
                    elif str(id_num) in df_inventario.index:
                        clave_externa = df_inventario.loc[str(id_num), "Clave Externa"]
                        archivo_info["id_inventario"] = str(id_num)
                        archivo_info["clave_externa"] = clave_externa
                        resultados.append(archivo_info)
                        
                except ValueError:
                    pass
            else:
                # Si el archivo no comienza con números, lo ignoramos o podrías loggearlo
                print(f"No se detectó un ID válido al inicio del archivo: {filename}")
                    
    return pd.DataFrame(resultados)


def importar_documentos_masivamente(cql_data):
    df_legajos = mapear_legajos_a_clave_externa(cql_data)
    df_comprobantes = mapear_comprobantes_a_clave_externa(cql_data)
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    UPLOAD_DIR_ABS = os.path.join(project_root, "data", "uploads", "legajos")
    os.makedirs(UPLOAD_DIR_ABS, exist_ok=True)
    
    # Obtenemos la sesión de base de datos
    db: Session = next(get_db())
    
    procesados = 0
    errores = []
    
    try:
        # ==========================================
        # 1. IMPORTAR LEGAJOS (DNI, RECIBOS, ETC)
        # ==========================================
        print("   ➡️ Importando Legajos Generales...")
        for index, row in df_legajos.iterrows():
            clave_externa = str(row['clave_externa'])
            
            # Buscar el crédito por su id_externo
            credito = db.query(Credito).filter(Credito.id_externo == clave_externa).first()
            
            if not credito:
                errores.append(f"Legajo {row['archivo_pdf']}: Crédito no encontrado (ID Externo: {clave_externa})")
                continue
                
            # Copiar el archivo físico
            nuevo_nombre = f"{credito.id}_{row['archivo_pdf']}"
            file_path_abs = os.path.join(UPLOAD_DIR_ABS, nuevo_nombre)
            shutil.copy2(row['ruta_completa'], file_path_abs)
            
            # Insertar o actualizar registro en Base de Datos
            doc_existente = db.query(DocumentoLegajo).filter(
                DocumentoLegajo.credito_id == credito.id,
                DocumentoLegajo.nombre_archivo == row['archivo_pdf']
            ).first()

            if doc_existente:
                doc_existente.ruta_archivo = file_path_abs
                doc_existente.tipo_archivo = "application/pdf"
                doc_existente.transferencia_id = None
            else:
                doc = DocumentoLegajo(
                    credito_id=credito.id,
                    nombre_archivo=row['archivo_pdf'],
                    ruta_archivo=file_path_abs,
                    tipo_archivo="application/pdf",
                    transferencia_id=None
                )
                db.add(doc)
            procesados += 1
            
        # Guardamos avance
        db.commit()
        
        # ==========================================
        # 2. IMPORTAR COMPROBANTES DE TRANSFERENCIA
        # ==========================================
        print("   ➡️ Importando Comprobantes de Transferencia...")
        for index, row in df_comprobantes.iterrows():
            clave_externa = str(row['clave_externa'])
            credito = db.query(Credito).filter(Credito.id_externo == clave_externa).first()
            
            if not credito:
                errores.append(f"Comprobante {row['archivo_pdf']}: Crédito no encontrado (ID Externo: {clave_externa})")
                continue
            
            # Extraer el índice numérico de la transferencia (ej: "1 de 3" -> 1, "02" -> 2)
            transf_info = str(row['info_transferencia'])
            match_num = re.search(r'\d+', transf_info)
            transf_index = int(match_num.group()) if match_num else 1
            
            # Buscar las transferencias del crédito para vincular el ID correcto
            transferencias = db.query(Transferencia).filter(Transferencia.credito_id == credito.id).order_by(Transferencia.id).all()
            
            transferencia_id = None
            if transferencias:
                if 1 <= transf_index <= len(transferencias):
                    transferencia_id = transferencias[transf_index - 1].id
                else:
                    errores.append(f"ADVERTENCIA: Índice {transf_index} fuera de rango en {row['archivo_pdf']}. Se asignará a la primera transferencia.")
                    transferencia_id = transferencias[0].id
            
            # Copiar archivo
            nuevo_nombre = f"{credito.id}_{row['archivo_pdf']}"
            file_path_abs = os.path.join(UPLOAD_DIR_ABS, nuevo_nombre)
            shutil.copy2(row['ruta_completa'], file_path_abs)
            
            # Insertar o actualizar en BD
            doc_existente = db.query(DocumentoLegajo).filter(
                DocumentoLegajo.credito_id == credito.id,
                DocumentoLegajo.nombre_archivo == row['archivo_pdf']
            ).first()

            if doc_existente:
                doc_existente.ruta_archivo = file_path_abs
                doc_existente.tipo_archivo = "application/pdf"
                doc_existente.transferencia_id = transferencia_id
            else:
                doc_transf = DocumentoLegajo(
                    credito_id=credito.id,
                    nombre_archivo=row['archivo_pdf'],
                    ruta_archivo=file_path_abs,
                    tipo_archivo="application/pdf",
                    transferencia_id=transferencia_id
                )
                db.add(doc_transf)
            
            # Forzamos flush para evaluar los estados en tiempo real
            db.flush()
            
            # ----------------------------------------------------
            # LOGICA DE LA APP: Cambiar estado a ACTIVO si cumple
            # ----------------------------------------------------
            if credito.estado in (EstadoCredito.APROBADO, EstadoCredito.FIRMADO, "APROBADO", "FIRMADO", "EstadoCredito.APROBADO", "EstadoCredito.FIRMADO"):
                transf_todas = db.query(Transferencia).filter(Transferencia.credito_id == credito.id).all()
                if transf_todas:
                    todas_con_comprobante = True
                    for t in transf_todas:
                        doc_count = db.query(DocumentoLegajo).filter(DocumentoLegajo.transferencia_id == t.id).count()
                        if doc_count == 0:
                            todas_con_comprobante = False
                            break
                    
                    if todas_con_comprobante:
                        db.query(Credito).filter(Credito.id == credito.id).update({"estado": EstadoCredito.ACTIVO.name})
            
            procesados += 1
            
        # Commit Final
        db.commit()
        print(f"✅ Se importaron {procesados} archivos exitosamente.")
        
        if errores:
            print("\nDetalle de errores o advertencias (mostrando primeros 15):")
            for e in errores[:15]:
                print(f" - {e}")
            if len(errores) > 15:
                print(f"...y {len(errores) - 15} avisos más.")
                
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR CRÍTICO] Se ha hecho un rollback. Detalle del error: {e}")
    finally:
        db.close()
