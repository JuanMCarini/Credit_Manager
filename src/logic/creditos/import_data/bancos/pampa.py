import pandas as pd
from typing import List
from src.database import SessionLocal
from src.database.models.finance.bancos import Movimiento, Concepto
from sqlalchemy import func
import typing

def import_extract(
    file_or_path: typing.Union[str, typing.BinaryIO], 
    cuenta_id: int, 
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None
):
    """
    Lee un archivo CSV con el extracto del banco Pampa, lo parsea, 
    clasifica sus movimientos y los prepara para insertar en la base de datos.
    Permite filtrar los movimientos importados por un rango de fechas.
    """

    session = SessionLocal()

    # Función auxiliar para leer y rebobinar si es un archivo en memoria
    def read_format(sep, skiprows, encoding):
        if hasattr(file_or_path, 'seek'):
            file_or_path.seek(0)
        return pd.read_csv(file_or_path, sep=sep, encoding=encoding, skiprows=skiprows)

    df = None
    
    # Formato esperado para Banco Pampa
    formatos = [
        {'sep': ';', 'skiprows': 4, 'encoding': 'latin1'},
        {'sep': ';', 'skiprows': 4, 'encoding': 'utf-8'},
        {'sep': ';', 'skiprows': 0, 'encoding': 'latin1'}, 
    ]

    for fmt in formatos:
        try:
            df_tmp = read_format(**fmt)
            df_tmp.columns = df_tmp.columns.str.strip()
            if "Fecha" in df_tmp.columns and "Importe" in df_tmp.columns:
                df = df_tmp
                break
        except Exception:
            continue
            
    if df is None:
        if hasattr(file_or_path, 'seek'): file_or_path.seek(0)
        df_fall = pd.read_csv(file_or_path, sep=';', encoding='latin1', skiprows=4)
        raise ValueError(f"No se encontró la columna 'Fecha' o 'Importe'. Columnas detectadas: {list(df_fall.columns)}")

    # Ignoramos filas vacías o que sean encabezados intermedios
    df = df.dropna(subset=["Fecha", "Importe"]).copy()
    df = df[df["Fecha"].astype(str).str.strip() != "Fecha"]
    
    # Parseo de fechas
    df["Fecha"] = pd.to_datetime(df["Fecha"].astype(str).str.strip(), format='%d/%m/%Y', dayfirst=True)
        
    # Filtro por fechas si es requerido
    if fecha_desde:
        df = df.loc[df["Fecha"] >= pd.to_datetime(fecha_desde)]
    if fecha_hasta:
        df = df.loc[df["Fecha"] <= pd.to_datetime(fecha_hasta)]
        
    # Limpieza de importe (remueve '$ ', quita puntos de miles y cambia coma por punto)
    # Ejemplo: "$ 8.000.000,00" -> "8000000.00", "$ -48.000,00" -> "-48000.00"
    df["Importe"] = df["Importe"].astype(str).str.replace("$", "", regex=False).str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)

    # Ordenar cronológicamente
    df = df.sort_values(by=["Fecha"])

    # Cargamos el mapa de conceptos desde la base de datos
    conceptos_db = session.query(Concepto).all()
    mapa_conceptos = {c.name: c.id for c in conceptos_db}
    
    id_ingreso_nc = mapa_conceptos.get("Ingreso NO CLASIFICADO")
    id_egreso_nc = mapa_conceptos.get("EGRESO NO CLASIFICADO")
    
    if not id_ingreso_nc or not id_egreso_nc:
        session.close()
        raise ValueError("Faltan los conceptos de 'NO CLASIFICADO' en la base de datos.")

    movimientos = []
    
    for _, row in df.iterrows():
        # Ajustamos el signo del monto 
        monto = abs(row["Importe"])
        
        # Ignoramos movimientos de $0
        if monto == 0:
            continue
            
        transaccion = str(row["Concepto"]).strip()
        
        # Intentamos matchear la transacción con un nombre de concepto exacto
        concepto_id = mapa_conceptos.get(transaccion)
        
        # Si no existe, usamos reglas para Pampa o lo mandamos a los no clasificados
        if not concepto_id:
            if "MANTENIMIENTO DE CUENTA" in transaccion.upper() or "COM." in transaccion.upper():
                concepto_id = mapa_conceptos.get("Servicio de Cuenta")
            elif "IVA" in transaccion.upper() or "IMP. DEBITOS Y CRED" in transaccion.upper():
                concepto_id = mapa_conceptos.get("ARCA - IVA")
                
            if not concepto_id:
                if row["Importe"] < 0:
                    concepto_id = id_egreso_nc
                else:
                    concepto_id = id_ingreso_nc

        # Armamos la descripción
        desc = transaccion
            
        # Verificamos que no exista ya en la base de datos
        fecha_mov = row["Fecha"].date()
        nro_comprobante = str(row["Comprobante"]).strip()
        
        duplicado = session.query(Movimiento).filter(
            Movimiento.cuenta_id == cuenta_id,
            Movimiento.fecha == fecha_mov,
            Movimiento.nro_comprobante == nro_comprobante,
            func.abs(Movimiento.monto) == abs(monto)
        ).first()
        
        if duplicado:
            continue
            
        nuevo_movimiento = Movimiento(
            cuenta_id=cuenta_id,
            fecha=fecha_mov,
            nro_comprobante=nro_comprobante,
            monto=monto,
            concepto_id=concepto_id,
            descripcion=desc[:255]
        )
        movimientos.append(nuevo_movimiento)
    
    session.add_all(movimientos)
    session.flush()

    session.commit()
    session.close()
    
    print(f"Se subieron {len(movimientos)} movimientos nuevos a la cuenta {cuenta_id} (Pampa).")

    return df
