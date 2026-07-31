import logging
import os
import re
import shutil
from datetime import date, datetime
import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import (
    Cliente, Provincia, Credito, Transferencia, DocumentoLegajo,
    EstadoCredito, Relacion, TipoCredito
)
from src.logic.origination import LoanOriginator
from .parser import leer_archivo_web_carga

logger = logging.getLogger(__name__)

class ImportValidationError(Exception):
    pass

def validar_mapeos_web_carga(df_clientes: pd.DataFrame, df_creditos: pd.DataFrame, db_session: Session, socio_id_web_carga: int):
    """
    Fase Cero - Escaneo del Archivo.
    Verifica que todos los IDs foráneos presentes en el archivo existan en la tabla Relacion.
    Si falta alguno, arroja un ImportValidationError con el reporte consolidado.
    """
    map_provincias = Relacion.get_external_mapping_cache(socio_id_web_carga, "provincias", db_session)
    map_socios = Relacion.get_external_mapping_cache(socio_id_web_carga, "socios_comerciales", db_session)
    map_empleadores = Relacion.get_external_mapping_cache(socio_id_web_carga, "empleadores", db_session)
    map_comercializadores = Relacion.get_external_mapping_cache(socio_id_web_carga, "comercializadores", db_session)

    errores_faltantes = set()

    # Validar Clientes
    for _, row in df_clientes.iterrows():
        id_provincia = str(row.get("id_provincia", "")).strip()
        if id_provincia and id_provincia not in map_provincias and id_provincia != "nan":
            errores_faltantes.add(f"Provincia (Cliente): {id_provincia} - {row.get('provincia', '')}")

        id_prov_trabajo = str(row.get("id_provincia_trabajo", "")).strip()
        if id_prov_trabajo and id_prov_trabajo not in map_provincias and id_prov_trabajo != "nan":
            errores_faltantes.add(f"Provincia Trabajo (Cliente): {id_prov_trabajo} - {row.get('provincia_trabajo', '')}")

        id_organismo = str(row.get("id_organismo", "")).strip()
        if id_organismo and id_organismo not in map_empleadores and id_organismo != "nan":
            errores_faltantes.add(f"Organismo/Empleador (Cliente): {id_organismo} - {row.get('organismo', '')}")

    # Validar Créditos
    for _, row in df_creditos.iterrows():
        id_prov = str(row.get("id_provincia", "")).strip()
        if id_prov and id_prov not in map_provincias and id_prov != "nan":
            errores_faltantes.add(f"Provincia (Crédito): {id_prov} - {row.get('provincia', '')}")

        id_linea = str(row.get("id_linea", "")).strip()
        if id_linea and id_linea not in map_socios and id_linea != "nan":
            errores_faltantes.add(f"Línea/Socio Originador (Crédito): {id_linea} - {row.get('linea', '')}")

        id_comercializador = str(row.get("id_comercializador", "")).strip()
        if id_comercializador and id_comercializador not in map_comercializadores and id_comercializador != "nan":
            errores_faltantes.add(f"Comercializador/Socio (Crédito): {id_comercializador} - {row.get('comercializador', '')}")
            
        id_organismo = str(row.get("id_organismo", "")).strip()
        if id_organismo and id_organismo not in map_empleadores and id_organismo != "nan":
            errores_faltantes.add(f"Organismo/Empleador (Crédito): {id_organismo} - {row.get('organismo', '')}")

    if errores_faltantes:
        mensaje = "Faltan mapeos en la tabla Relaciones para el SISTEMA WEB CARGA:\n"
        mensaje += "\n".join([f" - {err}" for err in errores_faltantes])
        raise ImportValidationError(mensaje)

    return {
        "provincias": map_provincias,
        "socios": map_socios,
        "empleadores": map_empleadores,
        "comercializadores": map_comercializadores
    }

def importar_clientes(df_clientes: pd.DataFrame, db_session: Session, mapeos: dict):
    nuevos = 0
    actualizados = 0

    for _, row in df_clientes.iterrows():
        cuil = str(row.get("cuil", "")).strip()
        if not cuil or cuil == "nan":
            continue

        cliente = db_session.query(Cliente).filter_by(cuil=cuil).first()
        es_nuevo = False
        if not cliente:
            cliente = Cliente(cuil=cuil)
            es_nuevo = True

        nro_doc = str(row.get("nro_documento", "")).strip()
        if nro_doc and nro_doc != "nan":
            cliente.documento = nro_doc
            
        cliente.apellido = str(row.get("apellido", "")).strip()
        cliente.nombre = str(row.get("nombre", "")).strip()
        
        fecha_nac = row.get("fecha_nacimiento")
        if pd.notna(fecha_nac) and str(fecha_nac).strip():
            try:
                cliente.fecha_nacimiento = datetime.strptime(str(fecha_nac).strip(), "%Y-%m-%d").date()
            except ValueError:
                pass
                
        cbu_val = str(row.get("cbu", "")).strip()
        if cbu_val and cbu_val != "nan":
            cliente.cbu = cbu_val.zfill(22)
            
        cliente.telefono = str(row.get("telefono_1", "")).strip()
        cliente.telefono_2 = str(row.get("telefono_2", "")).strip()
        cliente.mail = str(row.get("email", "")).strip()
        
        cliente.calle = str(row.get("calle", "")).strip()
        
        calle_nro = str(row.get("calle_nro", ""))
        if calle_nro.isdigit():
            cliente.calle_nro = int(calle_nro)
            
        cliente.piso = str(row.get("piso", "")).strip()
        cliente.depto = str(row.get("depto", "")).strip()
        cliente.localidad = str(row.get("localidad", "")).strip()
        cliente.id_codigo_postal = str(row.get("codigo_postal", "")).strip()

        id_prov = str(row.get("id_provincia", "")).strip()
        if id_prov and id_prov in mapeos["provincias"]:
            cliente.id_provincia = mapeos["provincias"][id_prov]

        id_organismo = str(row.get("id_organismo", "")).strip()
        if id_organismo and id_organismo in mapeos["empleadores"]:
            cliente.empleador_id = mapeos["empleadores"][id_organismo]
            
        cliente.cargo = str(row.get("cargo", "")).strip()
        
        ingreso = row.get("ingreso_mensual")
        if pd.notna(ingreso):
            try:
                cliente.remuneracion = float(ingreso)
            except ValueError:
                pass

        if es_nuevo:
            db_session.add(cliente)
            nuevos += 1
        else:
            actualizados += 1

    db_session.flush()
    return nuevos, actualizados

def verificar_cuotas(credito: Credito, df_cuotas: pd.DataFrame):
    """
    Verifica que las cuotas generadas por LoanOriginator coincidan con las del archivo.
    """
    cuotas_archivo = df_cuotas[df_cuotas["id_web_carga"] == credito.id_externo]
    
    if cuotas_archivo.empty:
        logger.warning(f"Crédito {credito.id_externo}: No se encontraron cuotas en el archivo para verificar.")
        return

    cuotas_archivo_dict = {}
    for _, row in cuotas_archivo.iterrows():
        try:
            nro = int(row["nro_cuota"])
            cuotas_archivo_dict[nro] = {
                "capital": float(row["capital"]),
                "interes": float(row["interes"])
            }
        except (ValueError, TypeError):
            continue

    diferencias = []
    for c_generada in credito.cuotas:
        c_arch = cuotas_archivo_dict.get(c_generada.nro_cuota)
        if c_arch:
            diff_cap = abs(float(c_generada.capital) - c_arch["capital"])
            diff_int = abs(float(c_generada.interes) - c_arch["interes"])
            
            if diff_cap > 0.01 or diff_int > 0.01:
                diferencias.append(
                    f"Cuota {c_generada.nro_cuota}: "
                    f"Calculado (Cap: {c_generada.capital:.2f}, Int: {c_generada.interes:.2f}) vs "
                    f"Archivo (Cap: {c_arch['capital']:.2f}, Int: {c_arch['interes']:.2f})"
                )

    if diferencias:
        logger.warning(f"Crédito {credito.id_externo}: Diferencias matemáticas:\n" + "\n".join(diferencias))

def importar_creditos_y_transferencias(df_creditos: pd.DataFrame, df_transferencias: pd.DataFrame, df_clientes: pd.DataFrame, db_session: Session, mapeos: dict):
    originator = LoanOriginator(db_session)
    nuevos_creditos = 0
    creditos_existentes = 0

    # Crear diccionario para buscar el cuil por id_web_carga (usando la relación armada en el parser)
    cuil_by_id_web_carga = {}
    for _, row in df_clientes.iterrows():
        id_wc = str(row.get("id_web_carga", "")).strip()
        cuil = str(row.get("cuil", "")).strip()
        if id_wc and cuil and cuil != "nan":
            cuil_by_id_web_carga[id_wc] = cuil

    for _, row in df_creditos.iterrows():
        id_externo = str(row.get("id_web_carga", "")).strip()
        if not id_externo or id_externo == "nan":
            continue

        # Verificar si existe
        credito = db_session.query(Credito).filter_by(id_externo=id_externo).first()
        if credito:
            creditos_existentes += 1
            continue

        cuil = cuil_by_id_web_carga.get(id_externo)
        if not cuil:
            # Fallback buscar por id_solicitante si cuil no estaba en dict
            id_sol = str(row.get("id_solicitante", "")).strip()
            cliente_fb = db_session.query(Cliente).filter(Cliente.cuil.contains(id_sol)).first()
            if cliente_fb:
                cuil = cliente_fb.cuil
            else:
                logger.error(f"No se encontró CUIL para el crédito {id_externo}. Saltando.")
                continue

        capital = float(row.get("capital", 0.0))
        plazo = int(row.get("plazo", 1))
        tna = float(row.get("tna_con_iva", 0.0))
        if tna > 2:
            tna = tna / 100.0

        fecha_emision = row.get("fecha")
        if pd.notna(fecha_emision) and str(fecha_emision).strip():
            try:
                fecha_emision = datetime.strptime(str(fecha_emision).strip(), "%Y-%m-%d").date()
            except ValueError:
                fecha_emision = date.today()
        else:
            fecha_emision = date.today()

        # Mapear originador real (ahora Línea es el socio originador)
        id_linea = str(row.get("id_linea", "")).strip()
        partner_id = mapeos["socios"].get(id_linea)

        id_comercializador = str(row.get("id_comercializador", "")).strip()
        comercializador_id = mapeos["comercializadores"].get(id_comercializador)

        # Filtrar transferencias de este crédito
        transferencias_cr = df_transferencias[df_transferencias["id_web_carga"].astype(str).str.strip() == id_externo]
        t_data_list = []
        for _, t_row in transferencias_cr.iterrows():
            cbu_val = str(t_row.get("cbu", "")).strip()
            if cbu_val.endswith(".0"):
                cbu_val = cbu_val[:-2]
            t_data_list.append({
                "cbu": cbu_val.zfill(22) if cbu_val and cbu_val != "nan" else "",
                "monto": float(t_row.get("monto", 0.0)),
                "cuit": str(t_row.get("cuit_destinatario", "")).strip() if pd.notna(t_row.get("cuit_destinatario")) else "",
                "razon_social": str(t_row.get("destinatario", "")).strip()
            })

        try:
            nuevo_credito = originator.originate(
                client_cuil=cuil,
                capital=capital,
                tna_c_iva=tna,
                term=plazo,
                partner_id=partner_id,
                comercializador_id=comercializador_id,
                issuance_date=fecha_emision,
                due_day=28,
                type=TipoCredito.FRANCES,
                comision_id=None,
                id_externo=id_externo,
                transferencias_data=t_data_list,
                commit=False
            )
            nuevos_creditos += 1
            
            # Devolvemos el credito originado
            # originator.credit tiene el crédito generado en estado Pendiente
            # La verificación de cuotas la ejecutamos pasando el DataFrame de cuotas
        except Exception as e:
            logger.error(f"Error generando crédito {id_externo}: {e}")

    db_session.flush()
    return nuevos_creditos, creditos_existentes

def procesar_documentos_web_carga(file_paths: list, db_session: Session, upload_dir: str):
    """
    Procesa PDFs/Imágenes subidos, los asocia a Credito/Transferencia según regex de nombres,
    y actualiza el estado de los Créditos correspondientes.
    """
    os.makedirs(upload_dir, exist_ok=True)
    procesados = []
    errores = []
    creditos_afectados = set()

    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            name_without_ext, ext = os.path.splitext(filename)
            
            # Formatos esperados:
            # Transferencia: ID_WEB_CARGA.INDEX.ext
            # Legajo: ID_WEB_CARGA - LINEA - NOMBRE.ext
            transfer_match = re.search(r"^(\d+)\.(\d+)$", name_without_ext)
            legajo_match = re.search(r"^(\d+)\s*-\s*", name_without_ext)

            id_externo = None
            transf_index = None
            is_legajo = False

            if transfer_match:
                id_externo = transfer_match.group(1)
                transf_index = int(transfer_match.group(2))
            elif legajo_match:
                id_externo = legajo_match.group(1)
                is_legajo = True
            else:
                errores.append(f"Archivo {filename}: Formato no reconocido")
                continue

            credito = db_session.query(Credito).filter_by(id_externo=id_externo).first()
            if not credito:
                errores.append(f"Archivo {filename}: Crédito ID {id_externo} no encontrado en BD")
                continue

            creditos_afectados.add(credito.id)
            transferencia = None

            if transfer_match:
                transferencias = db_session.query(Transferencia).filter_by(credito_id=credito.id).order_by(Transferencia.id).all()
                if 1 <= transf_index <= len(transferencias):
                    transferencia = transferencias[transf_index - 1]
                else:
                    errores.append(f"Archivo {filename}: Índice de transferencia {transf_index} inválido")
                    continue

            dest_path = os.path.join(upload_dir, filename)
            shutil.copy2(file_path, dest_path)

            doc = DocumentoLegajo(
                nombre_archivo=filename,
                ruta_archivo=dest_path,
                tipo_archivo="application/pdf" if ext.lower() == ".pdf" else "application/octet-stream",
                credito_id=credito.id,
                transferencia_id=transferencia.id if transferencia else None
            )
            db_session.add(doc)
            procesados.append(filename)

        except Exception as e:
            errores.append(f"Archivo {file_path}: {str(e)}")

    db_session.flush()
    
    pasados_a_firmado = 0
    pasados_a_activo = 0

    # Actualizar estados de los créditos afectados
    for c_id in creditos_afectados:
        c = db_session.query(Credito).get(c_id)
        if not c:
            continue
            
        legajo = db_session.query(DocumentoLegajo).filter_by(credito_id=c.id, transferencia_id=None).first()
        if not legajo:
            continue
            
        estado_actual = c.estado.value if hasattr(c.estado, 'value') else c.estado
        if estado_actual == "APROBADO":
            c.estado = EstadoCredito.FIRMADO
            estado_actual = "FIRMADO"
            pasados_a_firmado += 1
            
        if estado_actual == "FIRMADO":
            # Verificar si todas sus transferencias tienen documento
            transferencias = db_session.query(Transferencia).filter_by(credito_id=c.id).all()
            if transferencias:
                todas_con_comprobante = True
                for transf in transferencias:
                    comprob = db_session.query(DocumentoLegajo).filter_by(transferencia_id=transf.id).first()
                    if not comprob:
                        todas_con_comprobante = False
                        break
                        
                if todas_con_comprobante:
                    c.estado = EstadoCredito.ACTIVO
                    pasados_a_activo += 1
                    
    db_session.flush()
    return {
        "procesados": procesados, 
        "errores": errores,
        "pasados_a_firmado": pasados_a_firmado,
        "pasados_a_activo": pasados_a_activo
    }

def importar_datos_web_carga(filepath: str, db_session: Session, socio_id_web_carga: int, file_paths_docs: list = None, upload_dir: str = None):
    """
    Función principal que orquesta la importación.
    """
    # 1. Leer DataFrames
    dataframes = leer_archivo_web_carga(filepath)
    df_clientes = dataframes["clientes"]
    df_creditos = dataframes["creditos"]
    df_transferencias = dataframes["transferencias"]
    df_cuotas = dataframes["cuotas"]

    # 2. Fase Cero (Validación de Mapeos Estricta)
    # Lanza ImportValidationError si falla algo.
    mapeos = validar_mapeos_web_carga(df_clientes, df_creditos, db_session, socio_id_web_carga)

    # 3. Importar Clientes
    clientes_nuevos, clientes_act = importar_clientes(df_clientes, db_session, mapeos)

    # 4. Importar Créditos y Transferencias
    creditos_nuevos, creditos_existentes = importar_creditos_y_transferencias(
        df_creditos, df_transferencias, df_clientes, db_session, mapeos
    )

    # 5. Verificar Cuotas (Itera sobre los créditos insertados en esta sesión)
    creditos_agregados = [obj for obj in db_session.new if isinstance(obj, Credito)]
    for c in creditos_agregados:
        verificar_cuotas(c, df_cuotas)

    # 6. Documentos
    docs_result = {}
    if file_paths_docs and upload_dir:
        docs_result = procesar_documentos_web_carga(file_paths_docs, db_session, upload_dir)

    # Si todo salió bien hasta acá, se hace commit en el nivel superior, no acá.
    
    return {
        "clientes": {"nuevos": clientes_nuevos, "actualizados": clientes_act},
        "creditos": {"nuevos": creditos_nuevos, "existentes": creditos_existentes},
        "documentos": docs_result
    }
