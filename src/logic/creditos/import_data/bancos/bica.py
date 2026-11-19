import pandas as pd
from typing import List
from src.database import SessionLocal
from src.database.models.finance.bancos import Movimiento
from src.logic.creditos.import_data.bancos import load_bank_concepto_resolver
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
    try:
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

        # Cargamos el resolver de conceptos basado en la tabla de relaciones del banco
        resolve_concepto_id = load_bank_concepto_resolver(session, cuenta_id)

        movimientos = []
        
        for _, row in df.iterrows():
            # Ajustamos el signo del monto 
            monto = abs(row["Importe"])
            
            # Ignoramos movimientos de $0
            if monto == 0:
                continue
                
            transaccion = str(row["Transacción"]).strip()

            info_adicional = None
            if "Info Adicional" in row and pd.notna(row["Info Adicional"]):
                info_val = str(row["Info Adicional"]).strip()
                if info_val:
                    info_adicional = info_val[:255]

            concepto_id = resolve_concepto_id(
                transaccion=transaccion,
                importe=row["Importe"],
                desc=transaccion,
            )
                
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
                descripcion=transaccion[:255],
                info_adicional=info_adicional,
            )
            movimientos.append(nuevo_movimiento)
        
        session.add_all(movimientos)
        session.flush()

        # Commiteamos para guardar en la base de datos
        session.commit()
        
        print(f"Se subieron {len(movimientos)} movimientos nuevos a la cuenta {cuenta_id}.")

        return df
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
