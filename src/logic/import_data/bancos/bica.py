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
    Lee un archivo Excel con el extracto del banco BICA, lo parsea, 
    clasifica sus movimientos y los prepara para insertar en la base de datos.
    Permite filtrar los movimientos importados por un rango de fechas.
    """

    # 1. Instanciamos la sesión y la guardamos en una variable
    session = SessionLocal()

    df_org = pd.read_excel(file_or_path)
    df = df_org.copy()
    
    # Parseo de fechas
    for col in ["Fec.Operación", "Fecha Real"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True)
        
    # Filtro por fechas si es requerido
    if fecha_desde:
        df = df.loc[df["Fec.Operación"] >= pd.to_datetime(fecha_desde)]
    if fecha_hasta:
        df = df.loc[df["Fec.Operación"] <= pd.to_datetime(fecha_hasta)]
        
    # Limpieza de importe
    df["Importe"] = df["Importe"].astype(str).str.replace(",", "").astype(float)

    # Ordenar cronológicamente
    df = df.sort_values(by=["Fec.Operación", "Fecha Real"])

    # 1. Cargamos el mapa de conceptos desde la base de datos
    conceptos_db = session.query(Concepto).all()
    mapa_conceptos = {c.name: c.id for c in conceptos_db}
    
    id_ingreso_nc = mapa_conceptos.get("Ingreso NO CLASIFICADO")
    id_egreso_nc = mapa_conceptos.get("EGRESO NO CLASIFICADO")
    
    if not id_ingreso_nc or not id_egreso_nc:
        raise ValueError("Faltan los conceptos de 'NO CLASIFICADO' en la base de datos.")

    movimientos = []
    
    for _, row in df.iterrows():
        # Ajustamos el signo del monto 
        monto = abs(row["Importe"])
        
        # Ignoramos movimientos de $0
        if monto == 0:
            continue
            
        transaccion = str(row["Transacción"]).strip()
        
        # 2. Intentamos matchear la transacción con un nombre de concepto exacto
        concepto_id = mapa_conceptos.get(transaccion)
        
        # 3. Si no existe (es genérica), lo mandamos a los no clasificados
        if "Solicitud de Rescate a FCI" in transaccion:
            concepto_id = mapa_conceptos.get("Rescate FCI")
        elif ("Suscripcion a FCI" in transaccion):
            concepto_id = mapa_conceptos.get("Suscripción FCI")
        elif "VEP ARCA" in transaccion:
            concepto_id = mapa_conceptos.get("VEP ARCA")
        elif "Comisión por Servicio de Cuenta" in transaccion:
            concepto_id = mapa_conceptos.get("Servicio de Cuenta")
        elif not concepto_id:
            if row["Importe"] < 0:
                concepto_id = id_egreso_nc
            else:
                concepto_id = id_ingreso_nc

        # 4. Armamos la descripción
        desc = transaccion
        if "Info Adicional" in row and pd.notna(row["Info Adicional"]):
            desc += f" - {row['Info Adicional']}"
            
        # 5. Verificamos que no exista ya en la base de datos
        fecha_mov = row["Fec.Operación"].date()
        nro_comprobante = str(row["Comprobante"])
        
        duplicado = session.query(Movimiento).filter(
            Movimiento.cuenta_id == cuenta_id,
            Movimiento.fecha == fecha_mov,
            Movimiento.nro_comprobante == nro_comprobante,
            func.abs(Movimiento.monto) == abs(monto)
        ).first()
        
        if duplicado:
            continue
            
        # 6. Instanciamos
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

    # Commiteamos para guardar en la base de datos
    session.commit()
    # Por último, es buena práctica cerrarla
    session.close()
    
    print(f"Se subieron {len(movimientos)} movimientos nuevos a la cuenta {cuenta_id}.")

    return df
