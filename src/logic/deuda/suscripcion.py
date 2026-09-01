import pandas as pd

from datetime import date
from pathlib import Path

from src.database import SessionLocal
from src.database.models.deuda.movimientos import TipoMovimiento

from .utils import read_file
from src.logic.deuda.commit import new_serie, new_cta_cte, new_inversor, new_titular, new_movimiento

def nueva_serie(nombre: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None):

    df = read_file(path)

    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()

    error_int = df["Interés"] - (df["Capital"] * (tna / 365) * plazo)
    error_total = df["Total"] - (df["Capital"] + df["Interés"])
    if error_int.abs().max() > 0.01 or error_total.abs().max() > 0.01:
        raise ValueError("Error en el cálculo de totales o intereses. Verifique las fórmulas del archivo.")

    db = SessionLocal()
    try:
        # 1. Crear o buscar la Serie (una sola vez)
        serie = new_serie(db, nombre, fecha, tna, plazo)

        # 2. Iterar las filas del DataFrame
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

            new_movimiento(db, cuenta.id, serie.id, fecha, row["Capital"], TipoMovimiento.SUSCRIPCION, inversores_de_la_fila)

        # 3. Guardar todos los cambios juntos al final de procesar el archivo
        db.commit()

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return df