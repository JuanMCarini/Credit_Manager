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
    Lee un archivo "Excel" con el extracto del banco Santander, lo parsea, 
    clasifica sus movimientos y los prepara para insertar en la base de datos.
    Permite filtrar los movimientos importados por un rango de fechas.
    """

    session = SessionLocal()
    try:
        # Función auxiliar para leer y rebobinar si es un archivo en memoria
        def read_format(sep, skiprows, encoding):
            if hasattr(file_or_path, 'seek'):
                file_or_path.seek(0)
            return pd.read_csv(file_or_path, sep=sep, encoding=encoding, skiprows=skiprows)

        df_org = None
        
        # Intentamos varias combinaciones de formato (viejo TSV vs nuevo CSV)
        formatos = [
            {'sep': '\t', 'skiprows': 6, 'encoding': 'latin1'}, # Nuevo formato excel con saltos de linea
            {'sep': '\t', 'skiprows': 4, 'encoding': 'latin1'}, # Formato viejo histórico
            {'sep': ';', 'skiprows': 4, 'encoding': 'latin1'},  # Formato CSV nuevo (;) con 4 filas de cabecera
            {'sep': ';', 'skiprows': 0, 'encoding': 'latin1'},  # Formato CSV nuevo estándar (;)
            {'sep': ',', 'skiprows': 0, 'encoding': 'latin1'},  # Formato CSV alternativo (,)
            {'sep': ';', 'skiprows': 4, 'encoding': 'utf-8'},   # Formato CSV utf-8 con cabeceras
        ]

        for fmt in formatos:
            try:
                df_tmp = read_format(**fmt)
                # Limpiamos nombres de columnas por si vienen con espacios
                df_tmp.columns = df_tmp.columns.str.strip()
                if "Fecha" in df_tmp.columns:
                    df_org = df_tmp
                    break
            except Exception:
                continue
                
        if df_org is None:
            # Fallback para mostrar el error real de qué columnas encontró
            if hasattr(file_or_path, 'seek'): file_or_path.seek(0)
            df_fall = pd.read_csv(file_or_path, sep=';', encoding='latin1')
            raise ValueError(f"No se encontró la columna 'Fecha'. Columnas detectadas: {list(df_fall.columns)}")

        # Ignoramos filas que no tengan Fecha válida o que sean encabezados intermedios
        df = df_org.dropna(subset=["Fecha"]).copy()
        df = df[df["Fecha"].astype(str).str.strip() != "Fecha"]
        
        # Ignoramos filas que no tengan un importe válido (elimina filas de "Saldo al...")
        df = df.dropna(subset=["Importe"]).copy()
        df = df[df["Importe"].astype(str).str.strip() != ""]

        # Parseo de fechas. Usamos format='mixed' para soportar fechas con horas como "30/07/2026 16:45"
        df["Fecha"] = pd.to_datetime(df["Fecha"].astype(str).str.strip(), format='mixed', dayfirst=True)
            
        # Filtro por fechas si es requerido
        if fecha_desde:
            df = df.loc[df["Fecha"] >= pd.to_datetime(fecha_desde)]
        if fecha_hasta:
            df = df.loc[df["Fecha"] <= pd.to_datetime(fecha_hasta)]
            
        # Limpieza de importe (remueve paréntesis de negativos, quita puntos de miles y cambia coma por punto)
        # Ejemplo: "(388.261,50)" -> "-388261.50"
        df["Importe"] = df["Importe"].astype(str).str.replace(r'^\((.*)\)$', r'-\1', regex=True).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)

        # Ordenar cronológicamente
        df = df.sort_values(by=["Fecha"])

        # Cargamos el resolver de conceptos basado en la tabla de relaciones del banco
        resolve_concepto_id = load_bank_concepto_resolver(session, cuenta_id)

        movimientos = []
        
        for _, row in df.iterrows():
            # Ajustamos el signo del monto 
            monto = abs(row["Importe"])
            
            # Ignoramos movimientos de $0
            if monto == 0:
                continue
                
            transaccion = str(row["Concepto"]).strip()

            info_adicional = None
            if "Referencia" in row and pd.notna(row["Referencia"]):
                ref = str(row["Referencia"]).strip()
                if ref and ref != "0":
                    info_adicional = f"Ref: {ref}"[:255]

            concepto_id = resolve_concepto_id(
                transaccion=transaccion,
                importe=row["Importe"],
                desc=transaccion,
            )

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
                descripcion=transaccion[:255],
                info_adicional=info_adicional,
            )
            movimientos.append(nuevo_movimiento)
        
        session.add_all(movimientos)
        session.flush()

        session.commit()
        
        print(f"Se subieron {len(movimientos)} movimientos nuevos a la cuenta {cuenta_id} (Santander).")

        return df
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
