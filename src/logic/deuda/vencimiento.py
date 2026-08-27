import pandas as pd

from datetime import date
from pathlib import Path

from src.utils import select_file
from src.database import SessionLocal
from src.database.models.deuda import Inversor, CuentaComitente, TitularidadCuentaComitente, Serie, MovimientoDeuda
from src.database.models.deuda.movimientos import TipoMovimiento
    
from src.services.arca_consulta import validar_datos_arca


from sqlalchemy import or_

def cerrar_serie(nombre: str, fecha: str | date):

    with SessionLocal() as db:
        serie = db.query(Serie).filter(Serie.name == nombre).first()
        if not serie:
            raise ValueError(f"Serie {nombre} no encontrada")
        
        movimientos = db.query(MovimientoDeuda.fecha, MovimientoDeuda.id_cuenta_comitente, MovimientoDeuda.id_serie, MovimientoDeuda.id_serie_destino, MovimientoDeuda.tipo_movimiento, MovimientoDeuda.monto).filter(
            or_(
                MovimientoDeuda.id_serie == serie.id,
                MovimientoDeuda.id_serie_destino == serie.id
            )
        ).all()

        df = pd.DataFrame(movimientos, columns=['fecha', 'cuenta_comitente', 'id_serie', 'id_serie_destino', 'tipo_movimiento', 'monto'])
        
        if not df.empty:
            from IPython.display import display
            display(df)
            df['fecha'] = fecha
            df['tipo_movimiento'] = TipoMovimiento.VENCIMIENTO
            df['monto'] = round(df['monto'] * (1+serie.tna/365 * serie.plazo), 2)
        
        nuevos_movimientos = df.to_dict(orient='records')
        
        for movimiento in nuevos_movimientos:
            db.add(MovimientoDeuda(**movimiento))

        db.commit()

    return df

def renovacion_serie(serie_vieja: str, serie_nueva: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None):

    if path == None:
        path = select_file()

    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    
    if path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("El archivo debe ser Excel o CSV")

    if len(df.columns) == 9:
        df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total", "Rescate", "Suscripción"]
        df["Observaciones"] = None
    elif len(df.columns) == 10:
        df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total", "Rescate", "Suscripción", "Observaciones"]
    else:
        raise ValueError(f"El archivo tiene {len(df.columns)} columnas, pero se esperaban 9 o 10.")
    
    # Limpiamos filas completamente vacías al final del archivo
    df = df.dropna(subset=["ID Cta. Cte.", "CUIT/CUIL", "Capital"])
    df[['Capital', 'Interés', 'Total', 'Rescate', 'Suscripción']] = df[['Capital', 'Interés', 'Total', 'Rescate', 'Suscripción']].fillna(0.0)

    # Estandarizamos el CUIT/CUIL a nivel de todo el DataFrame
    df["CUIT/CUIL"] = df["CUIT/CUIL"].astype(str).str.replace("-", "", regex=False).str.strip()
    df["CUIT/CUIL"] = df["CUIT/CUIL"].str.replace(r"\.0$", "", regex=True)

    # Control del cálculo de intereses
    # Calculamos la diferencia (error) sin modificar las columnas originales
    db = SessionLocal()
    serie_vieja = db.query(Serie).filter(Serie.name == serie_vieja).first()
    error_interes = df["Interés"] - (df["Capital"] * float(serie_vieja.tna)/365 * int(serie_vieja.plazo))

    # Comprobamos que en NINGUNA fila el error sea mayor a 1 centavo usando .abs().max()
    if error_interes.abs().max() > 0.01:
        raise ValueError("Error en el cálculo de totales o intereses. Verifique las fórmulas del archivo.")

    df_invs = df[["CUIT/CUIL", "Razón Social", "Dirección"]].copy()
    df_invs = df_invs.drop_duplicates()
    validar_datos_arca(df_invs)

    # ---------------------------------------------------------
    # Preparación de DataFrames
    # ---------------------------------------------------------
    df_ctas = df[["ID Cta. Cte.", "CUIT/CUIL"]].copy()
    df_ctas = df_ctas.drop_duplicates()

    df_egr_ing = df.loc[(df["Rescate"] > 0) | (df["Suscripción"] > 0)].copy()
    df_egr_ing = df_egr_ing.sort_values(by=["Rescate", "Suscripción"])
    df_egr_ing[['Capital', 'Interés', 'Total', 'Rescate', 'Suscripción']] = df_egr_ing[['Capital', 'Interés', 'Total', 'Rescate', 'Suscripción']].map("${:,.2f}".format)

    return df_egr_ing