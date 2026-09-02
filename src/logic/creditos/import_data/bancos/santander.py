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
            trans_lower = transaccion.lower()
            if "rescate" in trans_lower and "fci" in trans_lower:
                concepto_id = mapa_conceptos.get("Rescate FCI")
            elif "suscrip" in trans_lower and "fci" in trans_lower:
                concepto_id = mapa_conceptos.get("Suscripción FCI")
            elif "mantenimiento" in trans_lower or "comision" in trans_lower:
                concepto_id = mapa_conceptos.get("Servicio de Cuenta")
            elif "iva " in trans_lower:
                concepto_id = mapa_conceptos.get("ARCA - IVA")
            elif "ley 25.413" in trans_lower:
                concepto_id = mapa_conceptos.get("Impuesto Débito") or mapa_conceptos.get("ARCA - IVA")
            elif "iibb" in trans_lower:
                concepto_id = mapa_conceptos.get("ARBA - IIBB")
            
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
