from dateutil.relativedelta import relativedelta
from datetime import date
from sqlalchemy import select, func

import pandas as pd

import src.reports.finance.bancos as bancos
import src.reports.balances as balances
import src.reports.finance.comprobantes as comprobantes
import src.reports.finance.cartera as cartera

from src.database import SessionLocal
from src.database.models.finance.posicion_iva import PosicionIva
from src.database.models.cheques.main import Cheque, OperacionCheque, TipoOperacionCheque


def reporte(fecha_corte: str | date, n_periodos: int = 2, salto_meses: int = 1, tna_descuento: float = 0.0) -> pd.DataFrame:
    
    df_comp = comprobantes.df_comprobantes.copy ()
    df_pagos = comprobantes.df_pagos.copy()
    df_carteras = cartera.resumen.copy()
    
    fecha_corte = pd.to_datetime(fecha_corte).date()

    datos = []
    for i in range(n_periodos - 1, -1, -1):

        fecha = fecha_corte - relativedelta(months=i * salto_meses)       

        filtro_cartera = (df_carteras["fecha_compra"] <= pd.to_datetime(fecha))
        tna_series = df_carteras.loc[filtro_cartera, "tna_descuento"]
        
        if not tna_series.empty:
            tna = tna_series.mean()
        else:
            filtro_siguiente = df_carteras["fecha_compra"] < pd.to_datetime(fecha) - relativedelta(months=1)
            tna_siguiente = df_carteras.loc[filtro_siguiente, "tna_descuento"]
            tna = tna_siguiente.mean() if not tna_siguiente.empty else tna_descuento
        periodo = f"{pd.Period(fecha, freq='M')} - ({tna:.0%})"
        df_bcos = bancos.df.loc[bancos.df["fecha"] <= fecha].copy()
        caja = df_bcos["monto"].sum()
        datos.append(
            {"Categoria": "Activos", "Detalle": "Bancos/Caja", periodo: caja})
    
        fci = -bancos.resumen(fecha).get("FCI", 0.0)
        datos.append(
            {"Categoria": "Activos", "Detalle": "Inversiones (FCI)", periodo: fci})
    
        df_comp_pend = comprobantes.pendientes(fecha)
        pendientes = df_comp_pend.groupby("concepto")["saldo"].sum()
        planes_ganancias = pendientes.get("Ganancias", 0.0)
        datos.append(
            {"Categoria": "Pasivos", "Detalle": "Planes de Ganancias", periodo: planes_ganancias})
    
        df_saldos = balances.saldos(fecha, propias=True)
        df_saldos["Días"] = (df_saldos["Fecha Vencimiento"] - pd.to_datetime(fecha)).dt.days
        df_saldos["Días"] = df_saldos["Días"].clip(lower=0)
        tasa_mensual_efectiva = 1 + (tna * 30 / 365)
        exponente = df_saldos["Días"] / 30
        
        df_saldos["VA Capital"] = df_saldos["Capital"] / (tasa_mensual_efectiva ** exponente)
        df_saldos["VA Interés"] = df_saldos["Interés"] / (tasa_mensual_efectiva ** exponente)
        datos.append(
            {"Categoria": "Activos", "Detalle": "Capital (Cartera Activa)", periodo: df_saldos["VA Capital"].sum()})
        datos.append(
            {"Categoria": "Activos", "Detalle": "Interés (Cartera Activa)", periodo: df_saldos["VA Interés"].sum()})
    
    
        carteras_vendidas_a_cobrar = df_carteras.loc[filtro_cartera, 'valor_actual_total'].sum()
        filtro_bcos_cartera = (df_bcos["fecha"] <= fecha) & (df_bcos["concepto_nombre"] == "Venta Cartera")
        carteras_vendidas_a_cobrar -= df_bcos.loc[filtro_bcos_cartera, "monto"].sum()
        filtro_comp_venta = (df_comp["fecha_emision"] <= fecha) & (df_comp["concepto"] == "Venta Cartera")
        carteras_vendidas_a_cobrar -= df_comp.loc[filtro_comp_venta, "iva_21"].sum()
        if round(carteras_vendidas_a_cobrar, 0) != 0.0:
            datos.append(
                {"Categoria": "Activos", "Detalle": "Ventas de Cartera a Cobrar", periodo: carteras_vendidas_a_cobrar})

        venta_cartera_a_ceder = df_bcos.loc[filtro_bcos_cartera, "monto"].sum() - (df_carteras.loc[filtro_cartera, 'valor_actual_total'].sum() + df_comp.loc[filtro_comp_venta, "iva_21"].sum())
        if round(-venta_cartera_a_ceder, 0) < 0.0:
            datos.append(
                {"Categoria": "Pasivos", "Detalle": "Valor Actual de Cartera a Ceder", periodo: -venta_cartera_a_ceder})

        saldo_iva = 0.0
        db_session = SessionLocal()
        try:
            posicion = db_session.query(PosicionIva).filter(
                PosicionIva.anio == fecha.year,
                PosicionIva.mes == fecha.month
            ).first()
            if posicion:
                saldo_iva = float(posicion.saldo_a_pagar)


            vendidos_stmt = select(OperacionCheque.cheque_id).filter(
                OperacionCheque.tipo_operacion == TipoOperacionCheque.VENTA,
                OperacionCheque.fecha_operacion <= fecha
            )

            cheques_a_cobrar = db_session.query(func.sum(Cheque.monto)).join(OperacionCheque).filter(
                OperacionCheque.tipo_operacion == TipoOperacionCheque.COMPRA,
                OperacionCheque.fecha_operacion <= fecha,
                Cheque.fecha_pago > fecha,
                ~Cheque.id.in_(vendidos_stmt)
            ).scalar()

            cheques_a_pagar = db_session.query(func.sum(Cheque.monto)).join(OperacionCheque).filter(
                OperacionCheque.tipo_operacion == TipoOperacionCheque.VENTA,
                OperacionCheque.fecha_operacion <= fecha,
                Cheque.fecha_pago > fecha,
                ~Cheque.id.in_(vendidos_stmt)
            ).scalar()

            cheques_a_cobrar = float(cheques_a_cobrar or 0.0)
            cheques_a_pagar = float(cheques_a_pagar or 0.0)

    
        finally:
            db_session.close()
        
        datos.append(
            {"Categoria": "Pasivos", "Detalle": "IVA Adeudado", periodo: saldo_iva})

        datos.append(
                {"Categoria": "Activos", "Detalle": "Cheques a Cobrar", periodo: cheques_a_cobrar})
        
        datos.append(
                {"Categoria": "Pasivos", "Detalle": "Cheques a Pagar", periodo: cheques_a_pagar})
    

    df = pd.DataFrame(datos)
    df = df.groupby(["Categoria", "Detalle"]).sum()
    df.loc["Pasivos"] *= -1
    
    df.loc[("", "Total"), :] = df.sum()
    df.loc[("Activos", "Total"), :] = df.loc["Activos"].sum()
    df.loc[("Pasivos", "Total"), :] = df.loc["Pasivos"].sum()
    
    df = df.reset_index()
    df['cat_order'] = df['Categoria'].map({'Activos': 0, 'Pasivos': 1, '': 2}).fillna(3)
    
    detalle_order_map = {
        'Bancos/Caja': 1,
        'Inversiones (FCI)': 2,
        'Cheques a Cobrar': 3,
        'Capital (Cartera Activa)': 4,
        'Interés (Cartera Activa)': 5,
        'Ventas de Cartera a Cobrar': 6,
        'Cheques a Pagar': 1,
        'Valor Actual de Cartera a Ceder': 2,
        'IVA Adeudado': 3,
        'Planes de Ganancias': 4,
    }

    # Asignar orden por detalle, o 99 si no está mapeado. 'Total' va siempre al final (100)
    df['det_order'] = df['Detalle'].map(detalle_order_map).fillna(99)
    df.loc[df['Detalle'] == 'Total', 'det_order'] = 100
    
    df = df.sort_values(['cat_order', 'det_order', 'Detalle'])
    df = df.drop(columns=['cat_order', 'det_order'])
    df = df.set_index(['Categoria', 'Detalle'])

    return df