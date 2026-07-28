import csv
import os
import pandas as pd

def leer_archivo_web_carga(filepath: str) -> dict:
    """
    Lee un archivo de texto extraído del sistema "Web Carga" (delimitado por tabulaciones).
    Agrupa la información en cuatro DataFrames de Pandas.
    
    Retorna un diccionario con la siguiente estructura:
    {
        "clientes": pd.DataFrame,
        "creditos": pd.DataFrame,
        "transferencias": pd.DataFrame,
        "cuotas": pd.DataFrame
    }
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"El archivo {filepath} no existe.")

    clientes_list = []
    creditos_list = []
    transferencias_list = []
    cuotas_list = []

    cliente_actual = None

    # Se utiliza encoding latin-1 para soportar caracteres como '' (ej: ESCUELA N 71)
    with open(filepath, 'r', encoding='latin-1') as f:
        reader = csv.reader(f, delimiter='\t')
        
        for row in reader:
            if not row or len(row) < 2:
                continue
                
            tipo_registro = row[1]
            
            if tipo_registro == '1':
                # Inicia un nuevo registro de cliente
                cliente_actual = parsear_cliente(row)
                clientes_list.append(cliente_actual)
                
            elif tipo_registro == '2':
                credito = parsear_credito(row)
                creditos_list.append(credito)
                
                # Añadimos el id_web_carga al cliente para poder relacionar las tablas después
                if cliente_actual is not None:
                    cliente_actual['id_web_carga'] = credito.get('id_web_carga')
                    
            elif tipo_registro == '3':
                transferencias_list.append(parsear_desembolso(row))
                
            elif tipo_registro == '4':
                cuotas_list.append(parsear_cuota(row))

    return {
        "clientes": pd.DataFrame(clientes_list),
        "creditos": pd.DataFrame(creditos_list),
        "transferencias": pd.DataFrame(transferencias_list),
        "cuotas": pd.DataFrame(cuotas_list)
    }


def parsear_cliente(row: list) -> dict:
    """Extrae TODOS los campos del registro tipo 1 (Cliente), asignando nombres genéricos a los desconocidos."""
    data = {}
    known_fields = {
        0: 'prefijo',
        1: 'tipo_registro',
        2: 'apellido',
        3: 'nombre',
        4: 'id_tipo_documento',
        5: 'tipo_documento',
        6: 'nro_documento',
        7: 'cuil',
        8: 'fecha_nacimiento',
        9: 'sexo',
        10: 'id_pais',
        11: 'pais',
        12: 'calle',
        13: 'calle_nro',
        14: 'piso',
        15: 'depto',
        16: 'direccion_adicional',
        17: 'localidad',
        18: 'codigo_postal',
        19: 'id_provincia',
        20: 'provincia',
        21: 'telefono_1',
        22: 'telefono_2',
        23: 'email',
        24: 'calle_trabajo',
        25: 'calle_nro_trabajo',
        26: 'piso_trabajo',
        27: 'depto_trabajo',
        28: 'codigo_postal_trabajo',
        29: 'localidad_trabajo',
        30: 'id_provincia_trabajo',
        31: 'provincia_trabajo',
        32: 'telefono_trabajo',
        33: 'id_organismo',
        34: 'organismo',
        35: 'cargo',
        36: 'nro_legajo',
        37: 'ingreso_mensual',
        38: 'id_estado_civil',
        39: 'estado_civil',
        40: 'cbu',
        41: 'dni_repetido',
        42: 'empleador',
        43: 'fecha_ingreso',
        44: 'referencia_1',
        45: 'referencia_2',
        46: 'telefono_referencia_1',
        47: 'telefono_referencia_2',
        48: 'email_referencia_1',
        49: 'email_referencia_2',
        50: 'nro_cuenta_bancaria',
        51: 'banco',
        52: 'empleador_banco',
        53: 'id_provincia_empleador',
        54: 'id_solicitante'
    }
    for i, val in enumerate(row):
        key = known_fields.get(i, f'campo_{i}')
        data[key] = val
    return data


def parsear_credito(row: list) -> dict:
    """Extrae TODOS los campos del registro tipo 2 (Crédito), asignando nombres genéricos a los desconocidos."""
    data = {}
    known_fields = {
        0: 'prefijo',
        1: 'tipo_registro',
        2: 'id_web_carga',
        3: 'id_provincia',
        4: 'fecha',
        5: 'id_solicitante',
        6: 'id_linea',
        7: 'linea',
        8: 'id_fondeador',
        9: 'fondeador',
        10: 'id_organismo',
        11: 'organismo',
        13: 'plazo',
        14: 'monto_total',
        15: 'comision_linea',
        17: 'capital',
        18: 'valor_cuota',
        21: 'tna_con_iva',
        23: 'id_comercializador',
        24: 'comercializador',
        33: 'tna_sin_iva'
    }
    for i, val in enumerate(row):
        key = known_fields.get(i, f'campo_{i}')
        if i in (14, 15, 17, 18, 21, 33) and val:
            data[key] = float(val)
        elif i == 13 and val:
            data[key] = int(val)
        else:
            data[key] = val
    return data


def parsear_desembolso(row: list) -> dict:
    """Extrae TODOS los campos del registro tipo 3 (Transferencia), asignando nombres genéricos a los desconocidos."""
    data = {}
    known_fields = {
        0: 'prefijo',
        1: 'tipo_registro',
        2: 'id_transaccion',
        3: 'id_web_carga',
        4: 'monto',
        5: 'id_destinatario',
        6: 'destinatario',
        7: 'cbu',
        8: 'cuit_destinatario'
    }
    for i, val in enumerate(row):
        key = known_fields.get(i, f'campo_{i}')
        if i == 4 and val:
            data[key] = float(val)
        else:
            data[key] = val
    return data


def parsear_cuota(row: list) -> dict:
    """Extrae TODOS los campos del registro tipo 4 (Cuota), asignando nombres genéricos a los desconocidos."""
    data = {}
    known_fields = {
        0: 'prefijo',
        1: 'tipo_registro',
        2: 'id_web_carga',
        3: 'nro_cuota',
        4: 'capital',
        5: 'interes',
        6: 'iva'
    }
    for i, val in enumerate(row):
        key = known_fields.get(i, f'campo_{i}')
        if i in (4, 5, 6) and val:
            data[key] = float(val)
        elif i == 3 and val:
            data[key] = int(val)
        else:
            data[key] = val
    return data
