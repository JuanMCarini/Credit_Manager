from dateutil.relativedelta import relativedelta
from datetime import date
import pandas as pd
import src.reports.finance.bancos as bancos
import src.reports.balances as balances
import src.reports.finance.comprobantes as comprobantes
import src.reports.finance.cartera as cartera

def reporte(fecha_corte: str | date, n_periodos: int = 2, salto_meses: int = 1, tna_descuento: float = 0.0) -> pd.DataFrame:
    
    df_comp = comprobantes.df_comprobantes.copy ()
    df_pagos = comprobantes.df_pagos.copy()
    df_carteras = cartera.resumen.copy()
    
    fecha_corte = pd.to_datetime(fecha_corte).date()

    datos = []
    for i in range(n_periodos - 1, -1, -1):

        fecha = fecha_corte - relativedelta(months=i * salto_meses)       

        filtro_cartera = df_carteras["fecha_compra"] <= pd.to_datetime(fecha)
        tna_series = df_carteras.loc[filtro_cartera, "tna_descuento"]
        
        if not tna_series.empty:
            tna = tna_series.iloc[-1]
        else:
            filtro_siguiente = df_carteras["fecha_compra"] > pd.to_datetime(fecha)
            tna_siguiente = df_carteras.loc[filtro_siguiente, "tna_descuento"]
            tna = tna_siguiente.iloc[0] if not tna_siguiente.empty else tna_descuento
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
    
    
        carteras_vendidas = df_carteras.loc[filtro_cartera, 'valor_actual_total'].sum()
        venta_cartera_cobradas = df_bcos.loc[df_bcos["concepto_nombre"] == "Venta Cartera", "monto"].sum()
        filtro_comp = (df_comp["fecha_emision"] <= fecha) & (df_comp["concepto"] == 'Venta Cartera')
        iva_venta = df_comp.loc[filtro_comp, "iva_21"].sum()
        importe_venta = df_comp.loc[filtro_comp, "importe_total"].sum()
        filtro_pagos = (df_pagos["fecha_cancelacion"] <= fecha) & (df_pagos["comprobante_id"].isin(df_comp.loc[filtro_comp, "comprobante_id"]))
        comprobantes_cobrados = df_pagos.loc[filtro_pagos, "importe"].sum()
        carteras_vendidas -= comprobantes_cobrados
        if round(importe_venta, 0) == round(comprobantes_cobrados, 0):
            venta_cartera_cobradas -= (comprobantes_cobrados - iva_venta)
    
        if round(carteras_vendidas, 2) != 0.0:
            datos.append(
                {"Categoria": "Activos", "Detalle": "Ventas de Cartera a Cobrar", periodo: carteras_vendidas})
        if venta_cartera_cobradas != 0.0:
            datos.append(
                {"Categoria": "Pasivos", "Detalle": "Valor Actual de Cartera a Ceder", periodo: venta_cartera_cobradas})
    
    df = pd.DataFrame(datos)
    df = df.groupby(["Categoria", "Detalle"]).sum()
    df.loc["Pasivos"] *= -1
    
    df.loc[("", "Total"), :] = df.sum()
    df.loc[("Activos", "Total"), :] = df.loc["Activos"].sum()
    df.loc[("Pasivos", "Total"), :] = df.loc["Pasivos"].sum()
    
    df = df.reset_index()
    df['cat_order'] = df['Categoria'].map({'Activos': 0, 'Pasivos': 1, '': 2}).fillna(3)
    df['det_order'] = df['Detalle'].apply(lambda x: 1 if x == 'Total' else 0)
    
    df = df.sort_values(['cat_order', 'det_order', 'Detalle'])
    df = df.drop(columns=['cat_order', 'det_order'])
    df = df.set_index(['Categoria', 'Detalle'])

    return df