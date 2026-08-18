import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import math
from datetime import date
import os
import re
import shutil
from src.database.models.clientes import Cliente, SexoEnum, EstadoClienteEnum, Provincia, Empleador
from src.database.models.creditos import Credito, Cuota, TipoCredito, EstadoCredito, EstadoCuota, DocumentoLegajo, Transferencia
from src.database.models.socios import SocioComercial, TasaYComision
from sqlalchemy import func
from src.logic.creditos.amortization import AmortizationEngine
from src.config import get_company_data
def map_sexo(sexo_str: str) -> SexoEnum:
    if pd.isna(sexo_str):
        return None
    s = str(sexo_str).strip().upper()
    if s.startswith('M'):
        return SexoEnum.MASCULINO
    elif s.startswith('F'):
        return SexoEnum.FEMENINO
    else:
        return SexoEnum.OTRO

def map_estado(estado_str: str) -> EstadoClienteEnum:
    if pd.isna(estado_str):
        return None
    s = str(estado_str).strip().upper()
    if 'ACTIVO' in s:
        return EstadoClienteEnum.ACTIVO
    elif 'INACTIVO' in s:
        return EstadoClienteEnum.INACTIVO
    elif 'INCOBRABLE' in s:
        return EstadoClienteEnum.INCOBRABLE
    elif 'MOROSO' in s:
        return EstadoClienteEnum.MOROSO
    return EstadoClienteEnum.ACTIVO

def get_or_create_provincia(session: Session, nombre_provincia: str):
    if pd.isna(nombre_provincia) or not str(nombre_provincia).strip():
        return None
    nombre = str(nombre_provincia).strip().upper()
    provincia = session.query(Provincia).filter_by(nombre=nombre).first()
    if not provincia:
        provincia = Provincia(nombre=nombre)
        session.add(provincia)
        session.commit()
    return provincia.id

def import_clients_from_dataframe(df: pd.DataFrame, session: Session):
    """
    Importa clientes desde un DataFrame de Pandas a la base de datos.
    Se asume que las columnas coinciden con el esquema especificado.
    """
    nuevos_clientes = 0
    actualizados = 0
    errores = []

    for index, row in df.iterrows():
        try:
            # Obtener CUIL como string, removiendo decimales si los hay y rellenando si es necesario
            if pd.isna(row.get('C.U.I.L.')):
                errores.append(f"Fila {index}: CUIL faltante")
                continue
            cuil_val = str(int(row['C.U.I.L.'])) if not pd.isna(row['C.U.I.L.']) else None
            
            # Obtener DNI
            dni_val = str(int(row['D.N.I.'])) if not pd.isna(row['D.N.I.']) else None

            # Buscar si el cliente ya existe
            cliente = session.query(Cliente).filter_by(cuil=cuil_val).first()
            es_nuevo = False
            if not cliente:
                cliente = Cliente(cuil=cuil_val)
                es_nuevo = True

            cliente.documento = dni_val
            cliente.apellido = str(row['APELLIDO']).strip() if not pd.isna(row.get('APELLIDO')) else ""
            cliente.nombre = str(row['NOMBRE']).strip() if not pd.isna(row.get('NOMBRE')) else ""
            
            if not pd.isna(row.get('FECHA NACIMIENTO')):
                cliente.fecha_nacimiento = row['FECHA NACIMIENTO'].date()
            
            cliente.sexo = map_sexo(row.get('SEXO'))
            cliente.estado_civil = str(row['ESTADO CIVIL']).strip() if not pd.isna(row.get('ESTADO CIVIL')) else None
            cliente.nacionalidad = str(row['NACIONALIDAD']).strip() if not pd.isna(row.get('NACIONALIDAD')) else None
            
            cliente.legajo = str(int(row['LEGAJO'])) if not pd.isna(row.get('LEGAJO')) else None
            cliente.estado = map_estado(row.get('ESTADO'))
            
            if not pd.isna(row.get('FECHA ESTADO')):
                cliente.fecha_estado = row['FECHA ESTADO'].date()
                
            cliente.cbu = str(int(row['CBU'])).zfill(22) if not pd.isna(row.get('CBU')) else None
            
            cliente.telefono = str(row['TELÉFONO']).strip() if not pd.isna(row.get('TELÉFONO')) else None
            cliente.telefono_2 = str(row['CELULAR']).strip() if not pd.isna(row.get('CELULAR')) else None
            cliente.mail = str(row['E-MAIL']).strip() if not pd.isna(row.get('E-MAIL')) else None
            
            cliente.calle = str(row['CALLE']).strip() if not pd.isna(row.get('CALLE')) else None
            cliente.calle_nro = int(row['CALLE NÚMERO']) if not pd.isna(row.get('CALLE NÚMERO')) else None
            cliente.piso = str(row['PISO']).strip() if not pd.isna(row.get('PISO')) else None
            cliente.depto = str(row['DEPTO.']).strip() if not pd.isna(row.get('DEPTO.')) else None
            cliente.localidad = str(row['LOCALIDAD']).strip() if not pd.isna(row.get('LOCALIDAD')) else None
            cliente.id_codigo_postal = str(int(row['CÓDIGO POSTAL'])) if not pd.isna(row.get('CÓDIGO POSTAL')) else None
            
            # Provincia lookup
            provincia_id = get_or_create_provincia(session, row.get('PROVINCIA'))
            cliente.id_provincia = provincia_id

            if es_nuevo:
                session.add(cliente)
                nuevos_clientes += 1
            else:
                actualizados += 1
                
            session.commit()
            
        except Exception as e:
            session.rollback()
            errores.append(f"Error procesando fila {index} (CUIL {row.get('C.U.I.L.')}): {str(e)}")

    return {
        "nuevos": nuevos_clientes,
        "actualizados": actualizados,
        "errores": errores
    }

def get_or_create_empleador(session: Session, razon_social: str):
    if pd.isna(razon_social) or not str(razon_social).strip():
        return None
    nombre = str(razon_social).strip().upper()
    empleador = session.query(Empleador).filter_by(razon_social=nombre).first()
    if not empleador:
        empleador = Empleador(razon_social=nombre)
        session.add(empleador)
        session.commit()
    return empleador.id

def update_clients_from_crts_dataframe(df: pd.DataFrame, session: Session):
    """
    Actualiza datos de los clientes (como CBU y Empleador) a partir del DataFrame de créditos.
    Busca a los clientes por su DNI.
    """
    actualizados = 0
    no_encontrados = 0
    errores = []

    for index, row in df.iterrows():
        try:
            if pd.isna(row.get('DNI')):
                continue
            
            dni_val = str(int(row['DNI']))
            
            # Buscar el cliente por DNI
            cliente = session.query(Cliente).filter_by(documento=dni_val).first()
            if not cliente:
                no_encontrados += 1
                continue
            
            modificado = False
            
            # Actualizar CBU si está presente en el excel y es válido
            if not pd.isna(row.get('CBU')):
                nuevo_cbu = str(int(row['CBU'])).zfill(22)
                if cliente.cbu != nuevo_cbu:
                    cliente.cbu = nuevo_cbu
                    modificado = True
            
            # Actualizar Organismo (Empleador) si está presente
            if not pd.isna(row.get('Organismo')):
                empleador_id = get_or_create_empleador(session, row.get('Organismo'))
                if empleador_id and cliente.empleador_id != empleador_id:
                    cliente.empleador_id = empleador_id
                    modificado = True
            
            if modificado:
                actualizados += 1
                
            session.commit()
            
        except Exception as e:
            session.rollback()
            errores.append(f"Error procesando fila con DNI {row.get('DNI')}: {str(e)}")

    return {
        "actualizados": actualizados,
        "no_encontrados": no_encontrados,
        "errores": errores
    }

def import_credits_from_dataframe(df: pd.DataFrame, session: Session, map_socios: dict = None):
    """
    Importa créditos y sus respectivas cuotas a partir de un DataFrame de créditos.
    Las cuotas se calculan utilizando AmortizationEngine.
    """
    nuevos_creditos = 0
    creditos_existentes = 0
    errores = []
    nuevos_ids_externos = set()

    amuf_socio = session.query(SocioComercial).filter(SocioComercial.razon_social.ilike('%AMUF%')).first()
    amuf_socio_id = amuf_socio.id if amuf_socio else None

    for index, row in df.iterrows():
        try:
            if pd.isna(row.get('DNI')) or pd.isna(row.get('ID Externo')):
                continue
            
            dni_val = str(int(row['DNI']))
            id_ext = str(row['ID Externo']).strip()
            
            # Buscar el cliente para obtener su CUIL
            cliente = session.query(Cliente).filter_by(documento=dni_val).first()
            if not cliente:
                errores.append(f"DNI {dni_val} (Fila {index}): Cliente no encontrado.")
                continue
            
            # Verificar si el crédito ya existe
            credito = session.query(Credito).filter_by(id_externo=id_ext).first()
            if credito:
                creditos_existentes += 1
                continue
            
            plazo = int(row['Plazo']) if not pd.isna(row.get('Plazo')) else 1
            capital = round(float(row['Capital']), 2) if not pd.isna(row.get('Capital')) else 0.0
            
            tasa = round(float(row['Tasa']), 6) if not pd.isna(row.get('Tasa')) else 0.0
            # Si la tasa viene en formato porcentaje (ej: 150 en lugar de 1.50)
            if tasa > 2:
                tasa = tasa / 100.0
                
            emision = row['Emisión'].date() if not pd.isna(row.get('Emisión')) else date.today()
            
            # Obtener socio originador
            linea_val = str(row.get('Línea', row.get('Linea', ''))).strip()
            socio_id = amuf_socio_id
            if map_socios and linea_val and linea_val != 'nan':
                socio_id = map_socios.get(linea_val, amuf_socio_id)
            
            # Buscar comision_id
            comision_id = None
            if socio_id:
                comision = session.query(TasaYComision).filter(
                    TasaYComision.socio_originador_id == socio_id,
                    TasaYComision.plazo == plazo,
                    func.round(TasaYComision.tna_c_iva, 4) == round(tasa, 4),
                    TasaYComision.fecha <= emision
                ).order_by(TasaYComision.fecha.desc()).first()
                if comision:
                    comision_id = comision.id
                else:
                    errores.append(f"DNI {dni_val} (ID Externo {id_ext}): No se encontró una Tasa y Comisión activa para socio originador ID {socio_id}, plazo {plazo}, tasa {tasa} y fecha de emisión {emision}.")
                    continue
            else:
                errores.append(f"DNI {dni_val} (ID Externo {id_ext}): No se puede asignar comisión porque el socio originador es nulo.")
                continue

            # Crear crédito
            credito = Credito(
                id_externo=id_ext,
                cliente_cuil=cliente.cuil,
                capital=capital,
                tna_c_iva=tasa,
                plazo=plazo,
                fecha_emision=emision,
                estado=EstadoCredito.APROBADO,
                tipo_credito=TipoCredito.FRANCES,
                dia_vencimiento=28,
                socio_originador_id=socio_id,
                comision_id=comision_id
            )
            session.add(credito)
            session.flush() # Para obtener el ID del crédito generado
            
            # Generar cuotas usando AmortizationEngine
            cuotas = AmortizationEngine.generate_french_schedule(
                credito_id=credito.id,
                capital=capital,
                tna_c_iva=tasa,
                plazo=plazo,
                fecha_emision=emision,
                dia_vencimiento=28
            )
            
            session.add_all(cuotas)
            
            nuevos_creditos += 1
            nuevos_ids_externos.add(id_ext)
            session.commit()
            
        except Exception as e:
            session.rollback()
            errores.append(f"Error procesando fila {index} (ID Externo {row.get('ID Externo')}): {str(e)}")

    return {
        "nuevos_creditos": nuevos_creditos,
        "creditos_existentes": creditos_existentes,
        "errores": errores,
        "nuevos_ids_externos": nuevos_ids_externos
    }

def import_transfers_from_dataframe(df_transf: pd.DataFrame, df_crts: pd.DataFrame, session: Session, nuevos_ids_externos: set = None):
    """
    Importa transferencias desde un DataFrame (df_transf).
    Mapea el 'ID Quota' de df_transf a la columna 'Crédito' de df_crts 
    para obtener el 'ID Externo' correspondiente en la base de datos.
    Si se proporciona nuevos_ids_externos, omite los créditos que no estén en ese set.
    """
    importadas = 0
    errores = []

    for index, row in df_transf.iterrows():
        try:
            id_quota = row.get('ID Quota')
            if pd.isna(id_quota):
                errores.append(f"Fila {index}: 'ID Quota' faltante")
                continue
                
            # Limpiar ID por posibles ceros a la izquierda (ej: 013848)
            try:
                quota_id_clean = str(int(id_quota))
            except ValueError:
                quota_id_clean = str(id_quota).strip()

            credito_id_externo = None
            
            # Buscar coincidencia
            if str(id_quota) in df_crts["Crédito"].astype(str).values:
                credito_id_externo = str(df_crts[df_crts["Crédito"].astype(str) == str(id_quota)]["ID Externo"].values[0]).strip()
            elif quota_id_clean in df_crts["Crédito"].astype(str).values:
                credito_id_externo = str(df_crts[df_crts["Crédito"].astype(str) == quota_id_clean]["ID Externo"].values[0]).strip()
                
            if not credito_id_externo:
                errores.append(f"Fila {index}: No se pudo determinar el ID Externo en df_crts para ID Quota '{id_quota}'")
                continue

            if nuevos_ids_externos is not None and credito_id_externo not in nuevos_ids_externos:
                continue

            credito = session.query(Credito).filter(Credito.id_externo == credito_id_externo).first()
            if not credito:
                errores.append(f"Fila {index}: Crédito con ID Externo '{credito_id_externo}' no encontrado en BD")
                continue
                
            # Parse fields
            cbu = str(int(row["CBU/CVU"])).zfill(22) if not pd.isna(row.get("CBU/CVU")) else ""
            cuit = str(int(row["CUIT/CUIL"])) if not pd.isna(row.get("CUIT/CUIL")) else ""
            monto = float(row["Monto"]) if not pd.isna(row.get("Monto")) else 0.0
            razon_social = str(row["Razon Social"]).strip() if not pd.isna(row.get("Razon Social")) else ""

            transferencia = Transferencia(
                cbu=cbu,
                monto=monto,
                cuit=cuit,
                credito_id=credito.id,
                razon_social=razon_social
            )
            session.add(transferencia)
            session.commit()
            importadas += 1

        except Exception as e:
            session.rollback()
            errores.append(f"Fila {index}: Error al procesar - {str(e)}")

    return {
        "importadas": importadas,
        "errores": errores
    }

def process_quota_documents(file_paths: list, df_crts: pd.DataFrame, session: Session, upload_dir: str, nuevos_ids_externos: set = None):
    """
    Procesa documentos masivos (transferencias y legajos) provenientes del sistema Quota de Estudio CFL.
    Extrae un ID del nombre del archivo, busca en df_crts para obtener el valor de la columna "Crédito",
    y asocia el documento al Credito/Transferencia correspondiente en la BD.
    Si se proporciona nuevos_ids_externos, omite los documentos de los créditos que no estén en ese set.
    """
    procesados = []
    errores = []

    os.makedirs(upload_dir, exist_ok=True)
    target_cols = ["ID Externo", "Crédito"]
    missing_cols = [col for col in target_cols if col not in df_crts.columns]
    if missing_cols:
        raise ValueError(f"Faltan las columnas requeridas en df_crts: {missing_cols}")

    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            name_without_ext, ext = os.path.splitext(filename)
            
            # 1. Match Transferencia -> ID.NUM.ext
            transfer_match = re.search(r"^(\d+)\.(\d+)$", name_without_ext)
            # 2. Match Legajo -> ID - LINEA - NOMBRE COMPLETO.ext
            legajo_match = re.search(r"^(\d+)\s*-\s*", name_without_ext)

            quota_id = None
            transf_index = None
            is_legajo = False

            if transfer_match:
                quota_id = transfer_match.group(1)
                transf_index = int(transfer_match.group(2))
            elif legajo_match:
                quota_id = legajo_match.group(1)
                is_legajo = True
            else:
                errores.append({"archivo": filename, "error": "Formato de nombre no reconocido"})
                continue
            credito_id_externo = None
            
            # Quitar ceros a la izquierda para comparar correctamente (ej: 013848 -> 13848)
            try:
                quota_id_clean = str(int(quota_id))
            except ValueError:
                quota_id_clean = str(quota_id).strip()
                
            # Primero probamos buscar exactamente el ID del archivo, luego la versión sin ceros
            if quota_id in df_crts["Crédito"].astype(str).values:
                credito_id_externo = str(df_crts[df_crts["Crédito"].astype(str) == quota_id]["ID Externo"].values[0]).strip()
            elif quota_id_clean in df_crts["Crédito"].astype(str).values:
                credito_id_externo = str(df_crts[df_crts["Crédito"].astype(str) == quota_id_clean]["ID Externo"].values[0]).strip()
            
            if not credito_id_externo:
                errores.append({"archivo": filename, "error": f"No se pudo determinar el ID Externo en df_crts para ID archivo {quota_id}"})
                continue
            
            if nuevos_ids_externos is not None and credito_id_externo not in nuevos_ids_externos:
                continue

            # Buscar el crédito en la BD
            credito = session.query(Credito).filter(Credito.id_externo == credito_id_externo).first()
            if not credito:
                errores.append({"archivo": filename, "error": f"Crédito '{credito_id_externo}' no encontrado en BD"})
                continue

            transferencia = None
            if transfer_match:
                # Buscar la transferencia correspondiente
                transferencias = session.query(Transferencia).filter(Transferencia.credito_id == credito.id).order_by(Transferencia.id).all()
                if 1 <= transf_index <= len(transferencias):
                    transferencia = transferencias[transf_index - 1]
                else:
                    errores.append({"archivo": filename, "error": f"Transferencia índice {transf_index} no válida para crédito ID Externo {credito_id_externo}"})
                    continue

            # Copiar archivo físicamente
            dest_path = os.path.join(upload_dir, filename)
            shutil.copy2(file_path, dest_path)

            # Crear Documento
            doc = DocumentoLegajo(
                nombre_archivo=filename,
                ruta_archivo=dest_path,
                tipo_archivo="application/pdf" if ext.lower() == ".pdf" else "application/octet-stream",
                credito_id=credito.id,
                transferencia_id=transferencia.id if transferencia else None
            )
            session.add(doc)
            session.commit()

            procesados.append(filename)

        except Exception as e:
            session.rollback()
            errores.append({"archivo": file_path, "error": str(e)})

    return {
        "procesados": procesados,
        "errores": errores
    }

def verify_and_update_credit_states(df_crts: pd.DataFrame, session: Session):
    """
    Recorre los créditos de df_crts. 
    Verifica si tienen su legajo adjunto para pasarlos a FIRMADO.
    Luego verifica si todas sus transferencias tienen comprobante para pasarlos a ACTIVO.
    Si falta algo en algún paso, levanta un error/aviso para ese crédito.
    """
    resultados = {
        "pasados_a_firmado": 0,
        "pasados_a_activo": 0,
        "errores": []
    }

    target_col = "ID Externo" if "ID Externo" in df_crts.columns else "Crédito"

    for index, row in df_crts.iterrows():
        try:
            # Obtener el ID Externo
            credito_id_externo = None
            if target_col in df_crts.columns:
                credito_id_externo = str(row[target_col]).strip()
            elif str(df_crts.index.name) in ["ID Externo", "Crédito", "ID"]:
                credito_id_externo = str(index).strip()
            
            if not credito_id_externo or credito_id_externo.lower() == "nan":
                continue
                
            credito = session.query(Credito).filter(Credito.id_externo == credito_id_externo).first()
            if not credito:
                resultados["errores"].append(f"Crédito ID Externo {credito_id_externo}: No encontrado en BD")
                continue
                
            # 1. Verificar si tiene legajo (DocumentoLegajo con transferencia_id == None)
            legajo = session.query(DocumentoLegajo).filter(
                DocumentoLegajo.credito_id == credito.id,
                DocumentoLegajo.transferencia_id == None
            ).first()
            
            if not legajo:
                resultados["errores"].append(f"Crédito ID Externo {credito_id_externo}: Falta Legajo adjunto")
                continue
                
            # Pasar a FIRMADO si estaba en APROBADO
            estado_actual = credito.estado.value if hasattr(credito.estado, 'value') else credito.estado
            
            if estado_actual == "APROBADO":
                credito.estado = EstadoCredito.FIRMADO
                resultados["pasados_a_firmado"] += 1
                estado_actual = "FIRMADO" # Actualizamos localmente para el siguiente paso
            
            # Solo pasamos a activo si ya está FIRMADO
            if estado_actual != "FIRMADO":
                continue
                
            # 2. Verificar transferencias
            transferencias = session.query(Transferencia).filter(Transferencia.credito_id == credito.id).all()
            if not transferencias:
                resultados["errores"].append(f"Crédito ID Externo {credito_id_externo}: No tiene transferencias cargadas")
                continue
                
            todas_con_comprobante = True
            faltantes = []
            
            for transf in transferencias:
                comprobante = session.query(DocumentoLegajo).filter(
                    DocumentoLegajo.transferencia_id == transf.id
                ).first()
                if not comprobante:
                    todas_con_comprobante = False
                    faltantes.append(str(transf.id))
                    
            if todas_con_comprobante:
                credito.estado = EstadoCredito.ACTIVO
                resultados["pasados_a_activo"] += 1
            else:
                resultados["errores"].append(f"Crédito ID Externo {credito_id_externo}: Faltan comprobantes para las transferencias ID(s): {', '.join(faltantes)}")
                
        except Exception as e:
            resultados["errores"].append(f"Error procesando crédito fila {index}: {str(e)}")

    session.commit()
    return resultados
