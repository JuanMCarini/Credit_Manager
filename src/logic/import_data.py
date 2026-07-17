import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import math
from datetime import date
from src.database.models.clientes import Cliente, SexoEnum, EstadoClienteEnum, Provincia, Empleador
from src.database.models.creditos import Credito, Cuota, TipoCredito, EstadoCredito, EstadoCuota
from src.logic.amortization import AmortizationEngine

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

def import_credits_from_dataframe(df: pd.DataFrame, session: Session):
    """
    Importa créditos y sus respectivas cuotas a partir de un DataFrame de créditos.
    Las cuotas se calculan utilizando AmortizationEngine.
    """
    nuevos_creditos = 0
    creditos_existentes = 0
    errores = []

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
                dia_vencimiento=28
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
            session.commit()
            
        except Exception as e:
            session.rollback()
            errores.append(f"Error procesando fila {index} (ID Externo {row.get('ID Externo')}): {str(e)}")

    return {
        "nuevos_creditos": nuevos_creditos,
        "creditos_existentes": creditos_existentes,
        "errores": errores
    }
