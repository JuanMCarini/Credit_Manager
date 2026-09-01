import pandas as pd

from sqlalchemy import or_

from src.database import SessionLocal
from src.database.models.deuda.series import Serie
from .ctas_ctes import buscar

def resumen(serie: int | str):
    
    try:
        db = SessionLocal()
        
        filters = [Serie.name == str(serie)]
        try:
            filters.append(Serie.id == int(serie))
        except ValueError:
            pass
            
        serie_obj = db.query(Serie).filter(or_(*filters)).first()
        if not serie_obj:
            raise ValueError(f"Serie {serie} no encontrada")

        cuentas_ids = list(set([mov.id_cuenta_comitente for mov in serie_obj.movimientos]))
        if not cuentas_ids:
            return pd.DataFrame()
            
        ctas_ctes_data = []
        for ctas_cte in cuentas_ids:
            df_inv, df_mov = buscar(ctas_cte)
            # Filter the movements only for the current series
            df_mov_serie = df_mov[df_mov['Serie'] == serie_obj.name]
            if not df_mov_serie.empty:
                ctas_ctes_data.append(df_mov_serie)
                
        if not ctas_ctes_data:
            return pd.DataFrame()
            
        return pd.concat(ctas_ctes_data, ignore_index=True)

    finally:
        db.close()