import pandas as pd

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from src.database import SessionLocal
from src.database.models.deuda.series import Serie
from src.database.models.deuda.inversores import CuentaComitente, Inversor, TitularidadCuentaComitente
from src.database.models.deuda.movimientos import MovimientoDeuda, TitularidadMovimientoDeuda
from src.logic.deuda.utils import mov_exp

def buscar(id_cuenta_comitente: str | int):

    try:
        db = SessionLocal()
        rows = (db.query(CuentaComitente, Inversor.id, Inversor.razon_social, Inversor.cuit, Inversor.domicilio_legal, TitularidadCuentaComitente.orden)
               .join(TitularidadCuentaComitente, TitularidadCuentaComitente.id_cuenta_comitente == CuentaComitente.id)
               .join(Inversor, Inversor.id == TitularidadCuentaComitente.id_inversor)
               .filter(or_(CuentaComitente.id == id_cuenta_comitente, CuentaComitente.id_externo == id_cuenta_comitente)).all())
        
        if not rows:
            raise ValueError(f"Cuenta comitente {id_cuenta_comitente} no encontrada")
            
        cc_obj = rows[0][0]
        
        data = [
            {"ID Cta. Cte.": cc.id, "ID Externo": cc.id_externo, "ID Inversor": id_inv, "Orden": orden, "Nombre Inversor": nombre, "CUIL/CUIT": cuit, "Domicilio": dom}
            for cc, id_inv, nombre, cuit, dom, orden in rows
        ]
        df_inversor = pd.DataFrame(data)
        df_inversor.sort_values(by="Orden", inplace=True)
        df_inversor.set_index(["ID Cta. Cte.", "ID Externo", "ID Inversor"], inplace=True)

        movs = (db.query(MovimientoDeuda).options(
            joinedload(MovimientoDeuda.serie),
            joinedload(MovimientoDeuda.titulares_assoc).joinedload(TitularidadMovimientoDeuda.inversor),
            joinedload(MovimientoDeuda.cuenta_comitente).joinedload(CuentaComitente.titulares_assoc).joinedload(TitularidadCuentaComitente.inversor)
        ).filter(MovimientoDeuda.id_cuenta_comitente == cc_obj.id).all())

        mov_data = []
        for m in movs:
            if m.titulares_assoc:
                inversores_nombres = ", ".join([t.inversor.razon_social for t in m.titulares_assoc])
            elif m.cuenta_comitente and m.cuenta_comitente.titulares_assoc:
                inversores_nombres = ", ".join([t.inversor.razon_social for t in m.cuenta_comitente.titulares_assoc])
            else:
                inversores_nombres = ""
                
            mov_data.append({
                "id": m.id,
                "name": m.serie.name,
                "fecha_suscripcion": m.serie.fecha_suscripcion,
                "tna": float(m.serie.tna) if m.serie.tna else 0.0,
                "plazo": m.serie.plazo,
                "id_cuenta_comitente": m.id_cuenta_comitente,
                "fecha": m.fecha,
                "tipo_movimiento": m.tipo_movimiento,
                "monto": m.monto,
                "inversores": inversores_nombres
            })

        df = pd.DataFrame(mov_data)
        if df.empty:
            # Handle empty dataframe gracefully with required columns
            df = pd.DataFrame(columns=['ID', 'Serie', 'Fecha Suscripción', 'Fecha Vencimiento', 'Fecha', 'Cta. Cte.', 'Tipo Movimiento', 'Inversores', 'Capital', "Interés", "Total"])
            return df_inversor, df

        df["fecha_vencimiento"] = pd.to_datetime(df["fecha_suscripcion"]) + pd.to_timedelta(df["plazo"], unit="d")
        df["monto"] = df["monto"].astype(float) * df["tipo_movimiento"].map(mov_exp)
        df["tipo_movimiento"] = df["tipo_movimiento"].apply(lambda x: x.name)
        df.rename(columns={
                  'id': "ID",
                  'name': "Serie",
                  'id_cuenta_comitente': "Cta. Cte.",
                  'fecha_suscripcion': "Fecha Suscripción",
                  'fecha_vencimiento': "Fecha Vencimiento",
                  'fecha': "Fecha",
                  'tipo_movimiento': "Tipo Movimiento",
                  'inversores': "Inversores",
                  'monto': "Movimiento"},
                  inplace=True)

        df["Capital"] = df.apply(lambda row: row["Movimiento"] if row["Tipo Movimiento"] in ["SUSCRIPCION", "RENOVACION_SUSCRIPCION"] else row["Movimiento"] / (1 + row['tna']/365 * row['plazo']), axis=1)
        df["Interés"] = df["Capital"] * df["tna"]/365 * df["plazo"]
        df["Total"] = df[["Capital", "Interés"]].sum(axis=1)
        df.sort_values(by="Fecha", inplace=True)
        df = df[['ID', 'Serie', 'Fecha Suscripción', 'Fecha Vencimiento', 'Fecha', 'Cta. Cte.', 'Inversores', 'Tipo Movimiento', 'Capital', "Interés", "Total"]]

        return df_inversor, df

    except Exception as e:
        raise e

    finally:
        db.close()