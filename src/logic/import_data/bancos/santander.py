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
    Lee un archivo "Excel" con el extracto del banco Santander, lo parsea, 
    clasifica sus movimientos y los prepara para insertar en la base de datos.
    Permite filtrar los movimientos importados por un rango de fechas.
    """

    session = SessionLocal()

    # Santander usa un archivo de texto separado por tabs con extensión .xls
    # y encoding latin1, ignorando las primeras 4 filas de cabecera.
    df_org = pd.read_csv(file_or_path, sep='\t', encoding='latin1', skiprows=4)
    # Ignoramos filas que no tengan Fecha válida (pueden ser totales al final)
    df = df_org.dropna(subset=["Fecha"]).copy()
    
    # Parseo de fechas. Usamos format='mixed' para soportar fechas con horas como "30/07/2026 16:45"
    df["Fecha"] = pd.to_datetime(df["Fecha"], format='mixed', dayfirst=True)
        
    # Filtro por fechas si es requerido
    if fecha_desde:
        df = df.loc[df["Fecha"] >= pd.to_datetime(fecha_desde)]
    if fecha_hasta:
        df = df.loc[df["Fecha"] <= pd.to_datetime(fecha_hasta)]
        
    # Limpieza de importe (remueve puntos de miles y cambia coma por punto)
    df["Importe"] = df["Importe"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)

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
        
        # Si no existe, usamos reglas para Santander o lo mandamos a los no clasificados
        if not concepto_id:
            if "Rescate" in transaccion and "FCI" in transaccion:
                concepto_id = mapa_conceptos.get("Rescate FCI")
            elif "Suscrip" in transaccion and "FCI" in transaccion:
                concepto_id = mapa_conceptos.get("Suscripción FCI")
            elif "Mantenimiento" in transaccion or "Comision" in transaccion:
                concepto_id = mapa_conceptos.get("Servicio de Cuenta")
            
            if not concepto_id:
                if row["Importe"] < 0:
                    concepto_id = id_egreso_nc
                else:
                    concepto_id = id_ingreso_nc

        # Armamos la descripción
        desc = transaccion
        
        if "Referencia" in row and pd.notna(row["Referencia"]):
            ref = str(row["Referencia"]).strip()
            if ref and ref != "0":
                desc += f" - Ref: {ref}"

        # Verificamos que no exista ya en la base de datos
        fecha_mov = row["Fecha"].date()
        # En Santander el comprobante es la Referencia, o el Cod. Operativo si no hay Referencia
        nro_comprobante = str(row["Referencia"]).strip() if pd.notna(row["Referencia"]) and str(row["Referencia"]).strip() != "0" else str(row["Cod. Operativo"]).strip()
        
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
    
    print(f"Se subieron {len(movimientos)} movimientos nuevos a la cuenta {cuenta_id} (Santander).")

    return df
