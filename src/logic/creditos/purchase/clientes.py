import pandas as pd
import numpy as np
from pathlib import Path

def parse_clientes_txt(file_path: str | Path) -> pd.DataFrame:
    """
    Parsea un archivo TXT con el formato de clientes de IQUA
    y lo transforma a un DataFrame con la estructura de la tabla clientes
    de la base de datos.
    """
    colspecs = [
        (0, 11),     # CUIL
        (11, 41),    # Apellido
        (41, 71),    # Nombre
        (71, 73),    # ID tipo de documento
        (73, 81),    # Nro. de documento
        (81, 89),    # Fecha de nacimiento
        (89, 92),    # ID de país
        (92, 94),    # ID de estado civil
        (94, 95),    # Sexo
        (95, 117),   # CBU
        (117, 121),  # Código postal
        (121, 201),  # Domicilio
        (201, 206),  # Domicilio número
        (206, 211),  # Piso
        (211, 216),  # Depto.
        (216, 218),  # ID de provincia
        (218, 220),  # ID tipo de teléfono
        (220, 222),  # ID tipo relación teléfono
        (222, 227),  # DDN
        (227, 237),  # Nro. de línea
        (237, 247),  # Filler
        (247, 257),  # Interno
        (257, 258)   # Es PEP
    ]
    
    names = [
        "cuil", "apellido", "nombre", "id_tipo_documento", "documento", 
        "fecha_nacimiento", "id_pais", "id_estado_civil", "sexo", "cbu", 
        "id_codigo_postal", "calle", "calle_nro", "piso", "depto", 
        "id_provincia", "id_tipo_telefono", "id_tipo_relacion_telefono", 
        "ddn", "nro_linea", "filler", "interno", "pep_raw"
    ]
    
    # Leer el archivo de ancho fijo
    df = pd.read_fwf(file_path, colspecs=colspecs, names=names, dtype=str, encoding='latin1')
    
    # Limpiar espacios en blanco
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # DataFrame con la estructura de la tabla clientes
    df_db = pd.DataFrame()
    
    df_db['cuil'] = df['cuil'].str.zfill(11).astype('string')
    df_db['documento'] = df['documento'].str.lstrip('0').astype('string')
    df_db['apellido'] = df['apellido'].astype('string')
    df_db['nombre'] = df['nombre'].astype('string')
    
    df_db['fecha_nacimiento'] = pd.to_datetime(df['fecha_nacimiento'], format='%Y%m%d', errors='coerce').dt.date
    df_db['sexo'] = df['sexo'].astype('string')
    
    estado_civil_map = {
        '01': 'Soltero',
        '02': 'Casado C/Com de Bienes',
        '03': 'Separado',
        '04': 'Divorciado',
        '05': 'Viudo',
        '06': 'En Tránsito',
        '08': 'Conviviente C/Sep de Bienes',
        '09': 'Casado C/Sep de Bienes',
        '10': 'Conviviente C/Com de Bienes'
    }
    df_db['estado_civil'] = df['id_estado_civil'].map(estado_civil_map).astype('string')
    
    pais_map = {
        '001': 'ARGENTINA',
        '002': 'ESPAÑA',
        '003': 'ITALIA',
        '004': 'URUGUAY',
        '005': 'BOLIVIA',
        '006': 'PARAGUAY',
        '007': 'BRASIL',
        '009': 'CHILE',
        '010': 'BULGARIA',
        '011': 'SIRIA',
        '012': 'ESTADOS UNIDOS',
        '013': 'VENEZUELA',
        '014': 'PERU',
        '015': 'SUIZA',
        '016': 'MEXICO',
        '017': 'CANADA',
        '018': 'FRANCIA',
        '019': 'PORTUGAL',
        '020': 'ECUADOR',
        '021': 'COLOMBIA',
        '022': 'GUATEMALA'
    }
    df_db['nacionalidad'] = df['id_pais'].map(pais_map).astype('string')
    
    df_db['legajo'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['estado'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['fecha_estado'] = pd.Series(None, index=df.index, dtype='object')
    
    df_db['cbu'] = df['cbu'].str.zfill(22)
    df_db['cbu'] = df_db['cbu'].apply(lambda x: pd.NA if x == '0'*22 else x).astype('string')
    
    df_db['cuenta_bancaria'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['banco'] = pd.Series(pd.NA, index=df.index, dtype='string')
    
    df_db['calle'] = df['calle'].astype('string')
    df_db['calle_nro'] = pd.to_numeric(df['calle_nro'], errors='coerce').astype('Int64')
    df_db['piso'] = df['piso'].replace('', pd.NA).astype('string')
    df_db['depto'] = df['depto'].replace('', pd.NA).astype('string')
    
    df_db['id_provincia'] = pd.to_numeric(df['id_provincia'], errors='coerce').astype('Int64')
    df_db['id_codigo_postal'] = df['id_codigo_postal'].apply(lambda x: pd.NA if x == '0' or x == '0000' else x).astype('string')
    df_db['localidad'] = pd.Series(pd.NA, index=df.index, dtype='string')
    
    # Armar el teléfono uniendo DDN y número de línea, quitando ceros a la izquierda
    def format_telefono(row):
        ddn = str(row['ddn']).lstrip('0') if pd.notna(row['ddn']) and row['ddn'] else ""
        nro = str(row['nro_linea']).lstrip('0') if pd.notna(row['nro_linea']) and row['nro_linea'] else ""
        tel = f"{ddn}{nro}"
        return tel if tel else pd.NA

    df_db['telefono'] = df.apply(format_telefono, axis=1).astype('string')
    df_db['telefono_2'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['mail'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['empleador_id'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    df_db['cargo'] = pd.Series(pd.NA, index=df.index, dtype='string')
    df_db['fecha_ingreso'] = pd.Series(None, index=df.index, dtype='object')
    df_db['remuneracion'] = pd.Series(0.0, index=df.index, dtype='float64')
    
    df_db['pep'] = (df['pep_raw'] == '1').astype('boolean')
    df_db['repet'] = pd.Series(False, index=df.index, dtype='boolean')
    
    return df_db
