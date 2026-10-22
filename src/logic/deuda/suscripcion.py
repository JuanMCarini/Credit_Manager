import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, Any

from src.database import SessionLocal
from src.database.models.deuda.series import Serie
from src.database.models.deuda.inversores import Inversor, CuentaComitente
from src.database.models.deuda.movimientos import TipoMovimiento

from .utils import read_file
from src.logic.deuda.commit import new_serie, new_cta_cte, new_inversor, new_titular, new_movimiento


def validar_y_leer_suscripcion(nombre: str, fecha: str | date, tna: float, plazo: int, path: Path | None, db):
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()

    # Verificar si la serie ya existe
    serie_existente = db.query(Serie).filter(Serie.name == nombre).first()
    if serie_existente:
        raise ValueError(f"Ya existe una serie registrada con el nombre '{nombre}'.")

    df = read_file(path)

    # Validar consistencia de fórmulas de intereses y totales
    error_int = df["Interés"] - (df["Capital"] * (tna / 365) * plazo)
    error_total = df["Total"] - (df["Capital"] + df["Interés"])
    if error_int.abs().max() > 0.05 or error_total.abs().max() > 0.05:
        err_msg = "Error en el cálculo de totales o intereses del archivo. "
        int_err_mask = error_int.abs() > 0.05
        if int_err_mask.any():
            bad_int_rows = df.loc[int_err_mask]
            detalles = [
                f"Cta {r['ID Cta. Cte.']}: esperado {(r['Capital'] * (tna / 365) * plazo):.2f} vs archivo {r['Interés']:.2f}"
                for _, r in bad_int_rows.iterrows()
            ]
            err_msg += f"Dif. Int: {'; '.join(detalles[:5])}. "
        tot_err_mask = error_total.abs() > 0.05
        if tot_err_mask.any():
            bad_tot_rows = df.loc[tot_err_mask]
            detalles = [
                f"Cta {r['ID Cta. Cte.']}: esperado {(r['Capital'] + r['Interés']):.2f} vs archivo {r['Total']:.2f}"
                for _, r in bad_tot_rows.iterrows()
            ]
            err_msg += f"Dif. Total: {'; '.join(detalles[:5])}."
        raise ValueError(err_msg)

    return df, fecha


def preview_nueva_serie(nombre: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        df, fecha_dt = validar_y_leer_suscripcion(nombre, fecha, tna, plazo, path, db)

        # Cuentas comitentes existentes vs nuevas
        ctas_externas = [str(r["ID Cta. Cte."]) for _, r in df.iterrows()]
        cuentas_existentes = set(
            c[0] for c in db.query(CuentaComitente.id_externo).filter(CuentaComitente.id_externo.in_(ctas_externas)).all()
        )

        # CUITs existentes vs nuevos
        todos_los_cuits = []
        for cuits in df["CUIT/CUIL"]:
            c_list = cuits if isinstance(cuits, list) else [cuits]
            for c in c_list:
                clean_c = str(c).strip().replace("-", "")
                if clean_c.endswith(".0"):
                    clean_c = clean_c[:-2]
                todos_los_cuits.append(clean_c)

        inversores_existentes = set(
            inv[0] for inv in db.query(Inversor.cuit).filter(Inversor.cuit.in_(todos_los_cuits)).all()
        )

        filas = []
        for _, row in df.iterrows():
            id_ext = str(row["ID Cta. Cte."])
            cuits_row = row["CUIT/CUIL"] if isinstance(row["CUIT/CUIL"], list) else [row["CUIT/CUIL"]]
            clean_cuits = [str(c).strip().replace("-", "").removesuffix(".0") for c in cuits_row]
            es_cta_nueva = id_ext not in cuentas_existentes
            inversores_nuevos_count = sum(1 for c in clean_cuits if c not in inversores_existentes)

            capital = round(float(row["Capital"]), 2)
            capital = 0.0 if abs(capital) < 0.005 else capital
            interes = round(float(row["Interés"]), 2)
            interes = 0.0 if abs(interes) < 0.005 else interes
            total = round(float(row["Total"]), 2)
            total = 0.0 if abs(total) < 0.005 else total

            filas.append({
                "id_cuenta": id_ext,
                "razon_social": " Y/O ".join(row["Razón Social"]) if isinstance(row["Razón Social"], list) else str(row["Razón Social"]),
                "cuit": " - ".join(row["CUIT/CUIL"]) if isinstance(row["CUIT/CUIL"], list) else str(row["CUIT/CUIL"]),
                "direccion": str(row["Dirección"]) if pd.notna(row["Dirección"]) else "",
                "capital": capital,
                "interes": interes,
                "total": total,
                "es_cuenta_nueva": es_cta_nueva,
                "inversores_nuevos": inversores_nuevos_count
            })

        total_capital = float(df["Capital"].sum())
        total_interes = float(df["Interés"].sum())
        total_monto = float(df["Total"].sum())

        return {
            "serie": {
                "name": nombre,
                "fecha_suscripcion": str(fecha_dt),
                "tna": float(tna),
                "plazo": int(plazo)
            },
            "resumen": {
                "total_capital": 0.0 if abs(total_capital) < 0.005 else round(total_capital, 2),
                "total_interes": 0.0 if abs(total_interes) < 0.005 else round(total_interes, 2),
                "total_monto": 0.0 if abs(total_monto) < 0.005 else round(total_monto, 2),
                "cantidad_cuentas": len(df),
                "cuentas_nuevas": sum(1 for f in filas if f["es_cuenta_nueva"]),
                "cuentas_existentes": sum(1 for f in filas if not f["es_cuenta_nueva"]),
                "total_inversores": len(todos_los_cuits),
                "inversores_nuevos": len(set(todos_los_cuits) - inversores_existentes),
                "inversores_existentes": len(set(todos_los_cuits) & inversores_existentes)
            },
            "filas": filas
        }
    finally:
        db.close()


def nueva_serie(nombre: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None, comision: bool = False):
    db = SessionLocal()
    try:
        df, fecha_dt = validar_y_leer_suscripcion(nombre, fecha, tna, plazo, path, db)

        # 1. Crear o buscar la Serie (una sola vez)
        serie = new_serie(db, nombre, fecha_dt, tna, plazo, comision)

        # 2. Iterar las filas del DataFrame
        for _, row in df.iterrows():
            id_externo_cta = row["ID Cta. Cte."]

            # Buscar o crear Cuenta Comitente
            cuenta = new_cta_cte(db, id_externo_cta, row)

            inversores_de_la_fila = []

            # Procesar inversores de la fila
            cuits = row["CUIT/CUIL"]
            razones_sociales = row["Razón Social"]
            direccion = row["Dirección"] if pd.notna(row["Dirección"]) else None

            for i in range(len(cuits)):
                cuit = cuits[i]
                rs = razones_sociales[i] if i < len(razones_sociales) else "Desconocido"
                inversor = new_inversor(db, cuit, rs, direccion)
                inversores_de_la_fila.append(inversor)

                # Asociar Inversor con la Cuenta Comitente (si no existe ya)
                new_titular(db, cuenta.id, inversor.id)

            capital = round(float(row["Capital"]), 2)
            if abs(capital) < 0.005:
                capital = 0.0
            if capital >= 0.01:
                new_movimiento(db, cuenta.id, serie.id, fecha_dt, capital, TipoMovimiento.SUSCRIPCION, inversores_de_la_fila)

        # 3. Guardar todos los cambios juntos al final de procesar el archivo
        db.commit()

        return df

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()