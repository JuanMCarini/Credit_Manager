import pandas as pd
import numpy as np

def parse_operaciones_txt(file_path: str) -> pd.DataFrame:
    """
    Parsea un archivo TXT con el formato de operaciones de IQUA
    y lo transforma a un DataFrame con la estructura de la tabla creditos
    de la base de datos.
    """
    colspecs = [
        (0, 11),     # CUIL
        (11, 21),    # Nro. de préstamo
        (21, 33),    # Capital vendido
        (33, 45),    # Interés vendido
        (45, 53),    # Fecha de liquidación
        (53, 65),    # Capital solicitado
        (65, 77),    # Capital otorgado
        (77, 89),    # Capital neto
        (89, 91),    # Plazo
        (91, 93),    # Cantidad de cuotas cedidas
        (93, 105),   # Valor de la cuota
        (105, 127),  # Texto clave
        (127, 135),  # Fecha del primer vencimiento
        (135, 141),  # Haberes del primer vencimiento
        (141, 155),  # TEM
        (155, 169),  # TNA
        (169, 183),  # CFTEA
        (183, 197),  # CFTEA sin IVA
        (197, 202),  # ID del organismo
        (202, 216)   # Tasa de la Venta
    ]
    
    names = [
        "cuil", "nro_prestamo", "capital_vendido", "interes_vendido", 
        "fecha_liquidacion", "capital_solicitado", "capital_otorgado", 
        "capital_neto", "plazo", "cantidad_cuotas_cedidas", "valor_cuota", 
        "texto_clave", "fecha_primer_vencimiento", "haberes_primer_vencimiento",
        "tem", "tna", "cftea", "cftea_sin_iva", "id_organismo", "tasa_venta"
    ]
    
    # Leer el archivo de ancho fijo
    df = pd.read_fwf(file_path, colspecs=colspecs, names=names, dtype=str, encoding='latin1')
    
    # Limpiar espacios en blanco y descartar filas vacías
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df.dropna(how='all', inplace=True)
    
    # DataFrame con la estructura de la tabla creditos
    df_db = pd.DataFrame()
    
    df_db['id_externo'] = df['nro_prestamo'].str.lstrip('0').astype('string')
    df_db['cliente_cuil'] = df['cuil'].str.zfill(11).astype('string')
    
    df_db['socio_originador_id'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    df_db['comercializador_id'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    df_db['cartera_id'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    df_db['comision_id'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    
    # Valores monetarios (divididos por 100 según el instructivo)
    df_db['capital'] = (pd.to_numeric(df['capital_otorgado'], errors='coerce') / 100.0).astype('Float64')
    
    # Tasas (divididas por 10000 según el instructivo)
    df_db['tna_c_iva'] = (pd.to_numeric(df['tna'], errors='coerce') / 10000.0).astype('Float64')
    
    df_db['plazo'] = pd.to_numeric(df['plazo'], errors='coerce').astype('Int64')
    
    df_db['fecha_emision'] = pd.to_datetime(df['fecha_liquidacion'], format='%Y%m%d', errors='coerce').dt.date
    
    # Enums y campos por defecto para la carga de nuevos créditos
    df_db['estado'] = pd.Series('APROBADO', index=df.index, dtype='string')
    df_db['tipo_credito'] = pd.Series('SISTEMA FRANCES', index=df.index, dtype='string')
    
    # Extraer el día de vencimiento de la fecha del primer vencimiento
    df_db['dia_vencimiento'] = pd.to_datetime(df['fecha_primer_vencimiento'], format='%Y%m%d', errors='coerce').dt.day.astype('Int64')

    # Columnas extras que pueden ser útiles posteriormente para crear OperacionCartera y Cuotas
    df_db['capital_vendido'] = (pd.to_numeric(df['capital_vendido'], errors='coerce') / 100.0).astype('Float64')
    df_db['interes_vendido'] = (pd.to_numeric(df['interes_vendido'], errors='coerce') / 100.0).astype('Float64')
    df_db['valor_cuota'] = (pd.to_numeric(df['valor_cuota'], errors='coerce') / 100.0).astype('Float64')
    df_db['cantidad_cuotas_cedidas'] = pd.to_numeric(df['cantidad_cuotas_cedidas'], errors='coerce').astype('Int64')
    df_db['fecha_primer_vencimiento_raw'] = pd.to_datetime(df['fecha_primer_vencimiento'], format='%Y%m%d', errors='coerce').dt.date
    
    return df_db
