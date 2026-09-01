import pandas as pd

from datetime import date
from pathlib import Path

from src.database import SessionLocal
from src.database.models.deuda.series import Serie
from src.database.models.deuda.movimientos import TipoMovimiento

from .utils import read_file
from src.logic.deuda.commit import new_serie, new_cta_cte, new_inversor, new_titular, new_movimiento
from src.logic.deuda.series import resumen

def renovación(serie_vieja: str, serie_nueva: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None):

    df = read_file(path)

    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()

    db = SessionLocal()
    try:
        old_serie = db.query(Serie).filter(Serie.name == serie_vieja).one_or_none()
        if old_serie is None:
            raise ValueError(f"No se encontró la serie {serie_vieja}")

        df_vieja = resumen(serie_vieja)
        errores = df_vieja[["Capital", "Interés"]].sum() - df[["Capital", "Interés"]].sum()
        error_int = df["Interés"] - (df["Capital"] * (float(old_serie.tna) / 365) * int(old_serie.plazo))
        error_total = df["Total"] - (df["Capital"] + df["Interés"] - df["Rescate"] + df["Suscripción"])
        if error_int.abs().max() > 0.05 or error_total.abs().max() > 0.01:
            err_msg = "Error en el cálculo de totales o intereses. "
            
            int_err_mask = error_int.abs() > 0.05
            if int_err_mask.any():
                bad_int_rows = df.loc[int_err_mask]
                detalles = [f"Cta {r['ID Cta. Cte.']}: esperado {(r['Capital'] * (float(old_serie.tna) / 365) * int(old_serie.plazo)):.2f} vs archivo {r['Interés']:.2f}" for _, r in bad_int_rows.iterrows()]
                err_msg += f"Dif. Int: {'; '.join(detalles)}. "
                
            tot_err_mask = error_total.abs() > 0.05
            if tot_err_mask.any():
                bad_tot_rows = df.loc[tot_err_mask]
                detalles = [f"Cta {r['ID Cta. Cte.']}: esperado {(r['Capital'] + r['Interés'] - r['Rescate'] + r['Suscripción']):.2f} vs archivo {r['Total']:.2f}" for _, r in bad_tot_rows.iterrows()]
                err_msg += f"Dif. Total: {'; '.join(detalles)}."

            raise ValueError(err_msg)

        if errores.abs().max() > 0.05:
            diferencias = []
            for col, diff in errores.items():
                if abs(diff) > 0.05:
                    val_base = df_vieja[col].sum()
                    val_archivo = df[col].sum()
                    diferencias.append(f"{col}: Base={val_base:.2f} vs Archivo={val_archivo:.2f} (Dif={diff:.2f})")
            
            raise ValueError(f"Error en el cálculo de totales del archivo con los de la base. Detalles: {', '.join(diferencias)}")

        df_ei = df.loc[(df["Rescate"] > 0) | (df["Suscripción"] > 0)]

        nueva_serie = new_serie(db, serie_nueva, fecha, tna, plazo)
        for _, row in df.iterrows():

            id_externo_cta = row["ID Cta. Cte."]

            # Buscar o crear Cuenta Comitente
            cuenta = new_cta_cte(db, id_externo_cta, row)

            inversores_de_la_fila = []

            # Procesar inversores de la fila
            cuits = row["CUIT/CUIL"]
            razones_sociales = row["Razón Social"]
            # Extraemos la dirección, manejando posibles valores nulos de pandas
            direccion = row["Dirección"] if pd.notna(row["Dirección"]) else None

            for i in range(len(cuits)):
                cuit = cuits[i]
                # Fallback por si Razón Social tiene menos elementos que CUITs
                rs = razones_sociales[i] if i < len(razones_sociales) else "Desconocido"
                inversor = new_inversor(db, cuit, rs, direccion)
                inversores_de_la_fila.append(inversor)

                # Asociar Inversor con la Cuenta Comitente (si no existe ya)
                new_titular(db, cuenta.id, inversor.id)

            rescate = row["Rescate"]
            if rescate > 0:
                new_movimiento(db, cuenta.id, old_serie.id, fecha, rescate, TipoMovimiento.RESCATE, inversores_de_la_fila)

            renovacion = row["Capital"] + row["Interés"] - rescate
            if renovacion > 0:
                new_movimiento(db, cuenta.id, old_serie.id, fecha, renovacion, TipoMovimiento.RENOVACION_RESCATE, inversores_de_la_fila)
                new_movimiento(db, cuenta.id, nueva_serie.id, fecha, renovacion, TipoMovimiento.RENOVACION_SUSCRIPCION, inversores_de_la_fila)
            
            suscripcion = row["Suscripción"]
            if suscripcion > 0:
                new_movimiento(db, cuenta.id, nueva_serie.id, fecha, suscripcion, TipoMovimiento.SUSCRIPCION, inversores_de_la_fila)

        # 3. Guardar todos los cambios juntos al final de procesar el archivo
        db.commit()

        df_ei.sort_values(by=["Rescate", "Suscripción", "ID Cta. Cte."], inplace=True)
        return df_ei

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
